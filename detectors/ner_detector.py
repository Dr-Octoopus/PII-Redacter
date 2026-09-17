"""
NER-based PII detector, using spaCy.

Handles PII categories that do NOT follow a fixed format -- mainly
person names and locations.  Regex can't catch "A or
"Pune" because there's no consistent character pattern to match.

MODEL SELECTION
---------------
Primary:   en_core_web_trf  (transformer-based, uses RoBERTa)
           ~400 MB download, dramatically better NER accuracy than
           the statistical models.  Runs on GPU if CUDA is available.

Fallback:  en_core_web_sm   (statistical model, ~15 MB)
           Loaded only if en_core_web_trf is not installed — with a
           console warning so the user knows accuracy is degraded.

GPU SAFETY
----------
When using en_core_web_trf with CUDA:
  - GPU memory is capped at 40% of VRAM via
    torch.cuda.set_per_process_memory_fraction().
  - After each document, the pipeline calls cleanup_gpu() to release
    GPU memory immediately (torch.cuda.empty_cache()).
  - At idle, GPU usage drops back to baseline (no persistent load).

CONFIDENCE SCORING
------------------
en_core_web_trf is much more accurate than en_core_web_sm, so the
base confidence scores are higher:

  PERSON  → 0.85  (was 0.75 with sm)
  GPE     → 0.88  (was 0.80 with sm)

The same heuristic adjustments (capitalisation bonus, length penalty,
single-character penalty) are applied on top.

INCLUDE / EXCLUDE
-----------------
Pass `include` or `exclude` to detect_ner_pii() to control which
entity types are returned.  Use the OUTPUT category names
(PERSON_NAME, LOCATION) — the same names that appear in the report.
"""

import warnings
import spacy
from typing import Optional

# ---------------------------------------------------------------------------
# GPU safety configuration (only runs if torch + CUDA are available)
# ---------------------------------------------------------------------------
_GPU_ENABLED = False

try:
    import torch

    if torch.cuda.is_available():
        # Cap GPU memory at 40% of VRAM — the model needs ~800 MB,
        # and on a 6 GB RTX 4050 this gives ~2.4 GB headroom without
        # starving the desktop compositor or other apps.
        torch.cuda.set_per_process_memory_fraction(0.4, device=0)

        # Tell spaCy to use GPU for the transformer pipeline.
        spacy.prefer_gpu()
        _GPU_ENABLED = True
except ImportError:
    # torch not installed — will use CPU-only model.
    pass


# ---------------------------------------------------------------------------
# Model loading (once at import time)
# ---------------------------------------------------------------------------
_MODEL_NAME = "en_core_web_trf"

try:
    _nlp = spacy.load(_MODEL_NAME)
except OSError:
    # en_core_web_trf not installed — fall back to the small model.
    _MODEL_NAME = "en_core_web_sm"
    warnings.warn(
        "⚠  en_core_web_trf not found — falling back to en_core_web_sm.  "
        "NER accuracy will be significantly lower.  Install the transformer "
        "model with:  python -m spacy download en_core_web_trf",
        stacklevel=2,
    )
    _nlp = spacy.load(_MODEL_NAME)


# Map spaCy entity labels → our report category names.
LABEL_MAP: dict[str, str] = {
    "PERSON": "PERSON_NAME",
    "GPE":    "LOCATION",
    "LOC":    "LOCATION",
    "ORG":    "ORGANIZATION",
}

# Base confidence score per spaCy label.
# These are higher when using the transformer model (more accurate).
_BASE_CONFIDENCE_TRF: dict[str, float] = {
    "PERSON": 0.85,
    "GPE":    0.88,
    "LOC":    0.88,
    "ORG":    0.86,
}
_BASE_CONFIDENCE_SM: dict[str, float] = {
    "PERSON": 0.75,
    "GPE":    0.80,
    "LOC":    0.80,
    "ORG":    0.78,
}
_BASE_CONFIDENCE = (
    _BASE_CONFIDENCE_TRF if _MODEL_NAME == "en_core_web_trf"
    else _BASE_CONFIDENCE_SM
)


def _compute_confidence(ent) -> float:
    """
    Produce a heuristic confidence score for a spaCy entity.

    The score is derived from:
      - a label-specific base value (higher for transformer model)
      - whether the entity text starts with a capital letter
      - the number of tokens (long spans → lower confidence)
      - whether the span is a single character
    """
    label = ent.label_
    score = _BASE_CONFIDENCE.get(label, 0.70)

    text = ent.text.strip()
    tokens = text.split()
    num_tokens = len(tokens)

    # Penalty: single-character "names" are almost always noise.
    if len(text) <= 1:
        score -= 0.10

    # Bonus: proper capitalisation is a positive signal.
    if text and text[0].isupper() and not text.isupper():
        score += 0.05

    # Penalty: very long spans are more likely to be NER errors.
    if num_tokens > 1:
        score -= 0.02 * (num_tokens - 1)

    # Clamp to a sensible range.
    return round(max(0.60, min(0.95, score)), 4)


def cleanup_gpu() -> None:
    """
    Release GPU memory after processing a document.

    Called by the pipeline after each document is done so the GPU
    doesn't hold onto cached memory between requests.  Safe to call
    even when CUDA isn't available — it's a no-op in that case.
    """
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def detect_ner_pii(
    text: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> list[dict]:
    """
    Run spaCy NER over *text* and return name / location detections.

    Args:
        text:    The full document text to scan.
        include: If provided, ONLY these output category names are returned.
                 Example: ["PERSON_NAME"]
        exclude: If provided, these output category names are skipped.
                 Example: ["LOCATION"]
                 Ignored when *include* is also supplied.

    Returns:
        A list of detection dicts in the same shape as the regex
        detector's output (text, category, start, end,
        detection_method, confidence) — ready to be merged together.

    Category names (pass these to include/exclude):
        PERSON_NAME, LOCATION
    """
    # Build the set of output category names we actually want.
    all_output_labels = set(LABEL_MAP.values())   # {"PERSON_NAME", "LOCATION"}

    if include:
        active = {c.upper() for c in include} & all_output_labels
    elif exclude:
        active = all_output_labels - {c.upper() for c in exclude}
    else:
        active = all_output_labels

    if not active:
        return []

    doc = _nlp(text)
    detections = []

    for ent in doc.ents:
        output_category = LABEL_MAP.get(ent.label_)
        if output_category is None:
            continue  # spaCy label we don't care about (DATE, ORG, MONEY …)
        if output_category not in active:
            continue

        detections.append({
            "text":             ent.text,
            "category":         output_category,
            "start":            ent.start_char,
            "end":              ent.end_char,
            "detection_method": "ner",
            "confidence":       _compute_confidence(ent),
        })

    return detections
