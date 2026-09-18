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


from detectors.context_detector import detect_context_pii, REJECT_TITLE_WORDS, FALSE_ORG_TERMS


_ORG_SUSPICION_TERMS = {
    "api", "repository", "factory", "tool", "tools", "manual", "page",
    "configuration", "config", "workflow", "module"
}

_ORG_LEGAL_OR_BRAND_TERMS = {
    "emerson", "microsoft", "inc", "ltd", "limited", "corp", "corporation",
    "llc", "plc", "solutions", "systems", "technologies", "services",
    "group", "holdings", "centre", "center"
}


def _normalized_words(text: str) -> list[str]:
    return [w.strip(".,;:()[]{}'\"").lower() for w in text.split() if w.strip(".,;:()[]{}'\"")]


def _should_skip_entity(text: str, category: str) -> bool:
    normalized = " ".join(text.split())
    lower = normalized.lower()
    words = _normalized_words(normalized)

    if not normalized or lower in REJECT_TITLE_WORDS:
        return True

    if category == "ORGANIZATION":
        if lower in FALSE_ORG_TERMS:
            return True
        if words and all(w in FALSE_ORG_TERMS for w in words):
            return True

    if category == "PERSON_NAME":
        if any(w in FALSE_ORG_TERMS for w in words):
            return True
        if any(w in _ORG_SUSPICION_TERMS for w in words):
            return True

    return False


def _adjust_confidence(category: str, text: str, score: float) -> float:
    """
    Lower confidence for entity shapes that spaCy often over-labels in
    technical manuals. They remain visible to reviewers instead of looking
    like certain high-confidence PII.
    """
    if category != "ORGANIZATION":
        return score

    words = _normalized_words(text)
    if not words:
        return score

    has_brand_signal = any(w in _ORG_LEGAL_OR_BRAND_TERMS for w in words)
    has_suspicion = any(w in _ORG_SUSPICION_TERMS or w in FALSE_ORG_TERMS for w in words)

    if has_suspicion and not has_brand_signal:
        return min(score, 0.68)
    if len(words) == 1 and not has_brand_signal:
        return min(score, 0.70)
    return score


def detect_ner_pii(
    text: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> list[dict]:
    """
    Run spaCy NER and context rules over *text* and return name, location,
    and organization detections.

    Args:
        text:    The full document text to scan.
        include: If provided, ONLY these output category names are returned.
                 Example: ["PERSON_NAME", "ORGANIZATION"]
        exclude: If provided, these output category names are skipped.
                 Example: ["LOCATION"]
                 Ignored when *include* is also supplied.

    Returns:
        A list of detection dicts (text, category, start, end,
        detection_method, confidence) — ready to be merged.

    Category names (pass these to include/exclude):
        PERSON_NAME, LOCATION, ORGANIZATION
    """
    all_output_labels = set(LABEL_MAP.values())   # {"PERSON_NAME", "LOCATION", "ORGANIZATION"}

    if include:
        active = {c.upper() for c in include} & all_output_labels
    elif exclude:
        active = all_output_labels - {c.upper() for c in exclude}
    else:
        active = all_output_labels

    if not active:
        return []

    detections = []

    # 1. Run contextual / rule-assisted detector first
    context_hits = detect_context_pii(text)
    for hit in context_hits:
        if hit["category"] in active:
            detections.append(hit)

    # 2. Run spaCy NER
    doc = _nlp(text)

    for ent in doc.ents:
        output_category = LABEL_MAP.get(ent.label_)
        if output_category is None or output_category not in active:
            continue

        ent_text = ent.text.strip()

        # Skip rejection words and common technical false positives.
        if _should_skip_entity(ent_text, output_category):
            continue

        # Handle concatenated Person Names (e.g., "Atharva Khole Amar Bagal" -> 2 distinct 2-word names)
        if output_category == "PERSON_NAME":
            words = ent_text.split()
            # If 4 capitalized words (e.g. Atharva Khole Amar Bagal in tabular layout)
            if len(words) == 4 and all(w[0].isupper() for w in words):
                name1 = f"{words[0]} {words[1]}"
                name2 = f"{words[2]} {words[3]}"
                idx1 = text.find(name1, ent.start_char)
                idx2 = text.find(name2, ent.start_char)

                if idx1 != -1:
                    detections.append({
                        "text": name1,
                        "category": "PERSON_NAME",
                        "start": idx1,
                        "end": idx1 + len(name1),
                        "detection_method": "ner",
                        "confidence": _compute_confidence(ent),
                    })
                if idx2 != -1:
                    detections.append({
                        "text": name2,
                        "category": "PERSON_NAME",
                        "start": idx2,
                        "end": idx2 + len(name2),
                        "detection_method": "ner",
                        "confidence": _compute_confidence(ent),
                    })
                continue

        # Handle multiline ORG text (e.g., "Emerson Automation Solutions \nProcess Systems and Solutions")
        if "\n" in ent_text:
            lines = [l.strip() for l in ent_text.splitlines() if l.strip()]
            for line in lines:
                if len(line) >= 3 and not _should_skip_entity(line, output_category):
                    idx = text.find(line, ent.start_char)
                    if idx != -1:
                        confidence = _adjust_confidence(output_category, line, _compute_confidence(ent))
                        detections.append({
                            "text": line,
                            "category": output_category,
                            "start": idx,
                            "end": idx + len(line),
                            "detection_method": "ner",
                            "confidence": confidence,
                        })
            continue

        confidence = _adjust_confidence(output_category, ent_text, _compute_confidence(ent))
        detections.append({
            "text":             ent_text,
            "category":         output_category,
            "start":            ent.start_char,
            "end":              ent.start_char + len(ent_text),
            "detection_method": "ner",
            "confidence":       confidence,
        })

    return detections
