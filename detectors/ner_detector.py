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
import re
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
    "configuration", "config", "workflow", "module", "platform", "deployment",
    "engineer", "intern", "internship", "messaging", "omnichannel", "computer",
    "science", "enterprise", "business", "businesses", "gtm", "fde",
    "college", "near"
}

# Specific known brand / company names that are NOT generic words.
# Generic legal suffixes (Solutions, Systems, Technologies, etc.) are intentionally
# NOT in this set — they are used to *detect* orgs in context_detector's suffix
# pattern, but should not make a single generic word pass as an org on its own.
_ORG_LEGAL_OR_BRAND_TERMS = {
    # Tech companies
    "emerson", "microsoft", "google", "apple", "amazon", "oracle", "ibm", "cisco",
    "siemens", "honeywell", "intel", "samsung", "sony", "tata", "infosys", "wipro",
    "accenture", "cognizant", "dell", "nvidia", "amd", "tesla", "meta",
    "facebook", "adobe", "salesforce", "whatsapp", "instagram", "linkedin",
    "youtube", "engati", "hp",
    # Financial institutions
    "jpmorganchase", "jpmorgan", "goldman", "citibank", "citigroup", "barclays",
    "hsbc", "ubs", "deutsche", "wellsfargo", "bofa", "blackrock", "vanguard",
    "mastercard", "visa", "paypal", "stripe",
    # Indian banks and orgs
    "hdfc", "icici", "sbi", "axis", "kotak", "reliance", "bajaj", "birla",
    "mahindra", "infosys", "hindunilvr", "adani",
    # Legal suffixes used to identify org spans (but not standalone brand tokens)
    "inc", "ltd", "limited", "corp", "corporation", "llc", "plc", "pvt",
}

GEOGRAPHIC_LOCATION_TERMS = {
    "india", "indian", "usa", "us", "america", "american", "uk", "england", "english",
    "japan", "japanese", "china", "chinese", "germany", "german", "france", "french",
    "singapore", "singaporean", "australia", "australian", "canada", "canadian",
    "brazil", "brazilian", "russia", "russian", "spain", "spanish", "italy", "italian",
    "korea", "korean", "delhi", "mumbai", "pune", "bangalore", "bengaluru", "hyderabad",
    "chennai", "kolkata", "london", "tokyo", "paris", "berlin", "beijing", "shanghai",
    "hongkong", "taiwan", "vietnam", "thailand", "malaysia", "indonesia", "mexico",
    "netherlands", "switzerland", "sweden", "norway", "denmark", "finland", "ireland"
}


def _normalized_words(text: str) -> list[str]:
    return [w.strip(".,;:()[]{}'\"").lower() for w in text.split() if w.strip(".,;:()[]{}'\"")]


def _should_skip_entity(text: str, category: str) -> bool:
    normalized = " ".join(text.split())
    lower = normalized.lower()
    words = _normalized_words(normalized)

    if not normalized or lower in REJECT_TITLE_WORDS or lower in FALSE_ORG_TERMS:
        return True

    # Reject non-alphanumeric noise symbols (e.g. '|', '_', '-', 'I', etc.)
    if not any(c.isalnum() for c in normalized):
        return True

    # Reject single-word 1 or 2 character tokens (e.g. 'ca', 'in', 'or', 'ex', 'I', 'l', 'a')
    if len(words) <= 1 and len(normalized) <= 2:
        return True

    # Reject OCR / PDF extraction fragments that contain punctuation inside
    # alphabetic tokens unless they look like a known legal suffix style.
    if category == "ORGANIZATION":
        if re.search(r"[A-Za-z],[A-Za-z]", normalized):
            return True
        # Reject spans with very short alphabetic tokens (e.g. "A B C" fragments).
        # BUT do NOT reject legitimate connectors like '&', '+', or abbreviations
        # that appear in real company names (e.g. "JPMorgan Chase & Co.").
        alpha_words = [w for w in words if any(c.isalpha() for c in w)]
        if len(words) > 1 and any(len(w) <= 1 for w in alpha_words):
            return True

    # Reject job titles, department terms, and signature block labels
    job_title_terms = {"admin", "hr", "director", "signatory", "signature", "authorized", "executive", "officer"}
    if any(w in job_title_terms for w in words) and len(words) <= 3:
        return True

    if category == "ORGANIZATION":
        if lower in {"process systems", "process systems and solutions", "microsoft excel"}:
            return True
        if lower in FALSE_ORG_TERMS or lower in GEOGRAPHIC_LOCATION_TERMS:
            return True
        if words and all(w in FALSE_ORG_TERMS for w in words):
            return True
        if any(w in _ORG_SUSPICION_TERMS for w in words) and not any(w in _ORG_LEGAL_OR_BRAND_TERMS for w in words):
            return True

    if category == "PERSON_NAME":
        # Skip single-word person names (e.g. cursive OCR noise like "Zaegark", "Admin", "Director")
        if len(words) == 1:
            return True
        if any(w in FALSE_ORG_TERMS for w in words):
            return True
        if any(w in _ORG_SUSPICION_TERMS for w in words):
            return True
        if any(w in _ORG_LEGAL_OR_BRAND_TERMS for w in words):
            return True
        if any(w in GEOGRAPHIC_LOCATION_TERMS for w in words):
            return True
        if lower in _ORG_LEGAL_OR_BRAND_TERMS or lower in GEOGRAPHIC_LOCATION_TERMS:
            return True

    return False


def _has_product_context(full_text: str, start: int, end: int, entity_text: str) -> bool:
    """Catch cases where spaCy emits only the brand word from a product name."""
    lower_entity = entity_text.lower()
    if lower_entity not in {"microsoft", "google", "apple", "facebook", "meta"}:
        return False

    window = full_text[max(0, start - 20): min(len(full_text), end + 30)].lower()
    product_phrases = {
        "microsoft excel", "microsoft word", "microsoft powerpoint",
        "google chrome", "google docs", "google sheets", "google drive",
        "apple ios", "apple macos", "facebook page", "meta ads",
    }
    return any(phrase in window for phrase in product_phrases)


# Generic legal suffix words — these identify org spans when combined with a
# name, but are NOT meaningful brand tokens on their own.
_ORG_GENERIC_SUFFIXES = {
    "solutions", "systems", "technologies", "services", "group", "holdings",
    "centre", "center", "automation", "engineering", "consulting", "management",
    "international", "global", "national", "industries", "enterprises",
    "associates", "partners", "ventures", "networks", "communications",
}


def _trim_org_to_brand(text: str) -> tuple[str, int] | None:
    """
    If spaCy returns "Brand Product Feature" as one ORG, keep only the
    brand token. This prevents masking generic product words while still
    redacting the organization itself.

    Only returns a brand token if it is a *specific* known brand name —
    generic suffix words like 'Systems' or 'Solutions' are never returned
    as stand-alone brand tokens because they are not meaningful in isolation.
    """
    words = _normalized_words(text)
    has_suspicious_tail = any(w in _ORG_SUSPICION_TERMS or w in FALSE_ORG_TERMS for w in words)
    if not has_suspicious_tail:
        return None

    for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9&.\-]*\b", text):
        token = match.group().strip(".,;:()[]{}'\"")
        token_lower = token.lower()
        # Only keep the token if it's a specific brand, not a generic suffix.
        if token_lower in _ORG_LEGAL_OR_BRAND_TERMS and token_lower not in _ORG_GENERIC_SUFFIXES:
            return token, match.start()
    return None




def _adjust_confidence(category: str, text: str, score: float) -> float:
    """
    Lower confidence for entity shapes that spaCy often over-labels in
    technical manuals. They remain visible to reviewers instead of looking
    like certain high-confidence PII.

    Key principle: when spaCy's transformer model (en_core_web_trf) confidently
    tags a span as ORG, we trust it unless we have strong counter-evidence.
    The 0.75 threshold in _should_keep_detection must be considered here:
    legitimate single-word orgs that spaCy knows (e.g. JPMorganChase) should
    stay above 0.75 so they aren't silently dropped.
    """
    if category != "ORGANIZATION":
        return score

    words = _normalized_words(text)
    if not words:
        return score

    has_brand_signal = any(w in _ORG_LEGAL_OR_BRAND_TERMS for w in words)
    has_generic_suffix_only = all(
        w in _ORG_GENERIC_SUFFIXES or w in {"inc", "ltd", "corp", "llc", "pvt", "plc", "limited", "corporation"}
        for w in words
    )
    has_suspicion = any(w in _ORG_SUSPICION_TERMS or w in FALSE_ORG_TERMS for w in words)

    if has_brand_signal and not has_generic_suffix_only:
        # Specific known brand → boost to at least 0.86.
        return max(score, 0.86)
    if has_suspicion and not has_brand_signal:
        # Technical/generic term mis-tagged as org → suppress.
        return min(score, 0.68)
    if len(words) == 1 and not has_brand_signal:
        # Single unknown word: spaCy may be right (e.g. a proper noun org).
        # Keep just above the 0.75 keep-threshold so NER judgment is trusted,
        # but below the 0.86 brand boost so it stays in the "review" zone.
        return max(min(score, 0.82), 0.76)
    return score


def _add_review_candidate(
    review_candidates: Optional[list[dict]],
    text: str,
    category: str,
    start: int,
    end: int,
    method: str,
    confidence: float,
    reason: str,
) -> None:
    if review_candidates is None:
        return
    duplicate = any(
        item["start"] == start
        and item["end"] == end
        and item["category"] == category
        for item in review_candidates
    )
    if duplicate:
        return
    review_candidates.append({
        "text": text,
        "category": category,
        "start": start,
        "end": end,
        "detection_method": method,
        "confidence": 0.50,
        "raw_confidence": round(confidence, 4),
        "review_only": True,
        "reason": reason,
    })


def _should_keep_detection(
    text: str,
    category: str,
    confidence: float,
    method: str,
    start: int,
    end: int,
    review_candidates: Optional[list[dict]] = None,
) -> bool:
    """
    Decide whether a semantic detector hit is strong enough to redact.

    Low-confidence ORG guesses cause most research-paper/JD false positives,
    so they are filtered instead of merely warned about.
    """
    if _should_skip_entity(text, category):
        return False
    if category == "ORGANIZATION" and confidence < 0.75:
        _add_review_candidate(
            review_candidates,
            text,
            category,
            start,
            end,
            method,
            confidence,
            "low-confidence organization candidate",
        )
        return False
    if category == "PERSON_NAME" and confidence < 0.72 and method == "ner":
        _add_review_candidate(
            review_candidates,
            text,
            category,
            start,
            end,
            method,
            confidence,
            "low-confidence person-name candidate",
        )
        return False
    return True


def detect_ner_pii(
    text: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    review_candidates: Optional[list[dict]] = None,
) -> list[dict]:
    """
    Run spaCy NER and context rules over *text* and return name, location,
    and organization detections.
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

    def _already_detected(start: int, end: int, category: str) -> bool:
        """Return True if an identical span+category is already in detections."""
        return any(
            d["start"] == start and d["end"] == end and d["category"] == category
            for d in detections
        )

    # 1. Run contextual / rule-assisted detector first
    context_hits = detect_context_pii(text)
    for hit in context_hits:
        if (
            hit["category"] in active
            and _should_keep_detection(
                hit["text"],
                hit["category"],
                hit.get("confidence", 0),
                hit.get("detection_method", "context_rule"),
                hit["start"],
                hit["end"],
                review_candidates,
            )
        ):
            detections.append(hit)

    # 2. Run spaCy NER
    doc = _nlp(text)

    for ent in doc.ents:
        output_category = LABEL_MAP.get(ent.label_)
        if output_category is None:
            continue

        ent_text = ent.text.strip()
        words = _normalized_words(ent_text)
        ent_start = ent.start_char

        # Smart Category Correction: Remap misclassified PERSON labels for
        # known brand / location terms, and for multi-word spans containing
        # legal suffixes (Inc, Ltd, etc.) that are clearly organizations.
        if output_category == "PERSON_NAME":
            lower_ent = ent_text.lower()
            ent_words_lower = [w.lower().strip(".,;:()[]{}'\"") for w in ent_text.split()]
            legal_suffixes = {"inc", "ltd", "limited", "corp", "corporation", "llc", "plc", "pvt",
                              "solutions", "systems", "technologies", "services", "group", "holdings"}
            if any(w in _ORG_LEGAL_OR_BRAND_TERMS for w in words):
                output_category = "ORGANIZATION"
            elif any(w in legal_suffixes for w in ent_words_lower) and len(ent_words_lower) >= 2:
                output_category = "ORGANIZATION"
            elif any(w in GEOGRAPHIC_LOCATION_TERMS for w in words):
                output_category = "LOCATION"

        if output_category not in active:
            continue

        if output_category == "ORGANIZATION":
            brand_trim = _trim_org_to_brand(ent_text)
            if brand_trim is not None:
                brand_text, rel_start = brand_trim
                ent_start = ent.start_char + rel_start
                ent_text = brand_text

        # Skip rejection words and common technical false positives.
        if _should_skip_entity(ent_text, output_category):
            continue
        if output_category == "ORGANIZATION" and _has_product_context(text, ent_start, ent_start + len(ent_text), ent_text):
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

                if idx1 != -1 and not _already_detected(idx1, idx1 + len(name1), "PERSON_NAME"):
                    detections.append({
                        "text": name1,
                        "category": "PERSON_NAME",
                        "start": idx1,
                        "end": idx1 + len(name1),
                        "detection_method": "ner",
                        "confidence": _compute_confidence(ent),
                    })
                if idx2 != -1 and not _already_detected(idx2, idx2 + len(name2), "PERSON_NAME"):
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
                        if not _should_keep_detection(
                            line,
                            output_category,
                            confidence,
                            "ner",
                            idx,
                            idx + len(line),
                            review_candidates,
                        ):
                            continue
                        if not _already_detected(idx, idx + len(line), output_category):
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
        if not _should_keep_detection(
            ent_text,
            output_category,
            confidence,
            "ner",
            ent_start,
            ent_start + len(ent_text),
            review_candidates,
        ):
            continue
        if not _already_detected(ent_start, ent_start + len(ent_text), output_category):
            detections.append({
                "text":             ent_text,
                "category":         output_category,
                "start":            ent_start,
                "end":              ent_start + len(ent_text),
                "detection_method": "ner",
                "confidence":       confidence,
            })

    # 3. Second pass for ALL CAPS text (common in ID cards / OCR)
    # If the text has significant ALL CAPS words, spaCy might miss them.
    # We title-case it and re-run.
    if text.isupper() or len(re.findall(r'\b[A-Z]{3,}\b', text)) > 2:
        title_text = text.title()
        doc_title = _nlp(title_text)
        for ent in doc_title.ents:
            output_category = LABEL_MAP.get(ent.label_)
            if output_category not in active:
                continue
            
            ent_text_title = ent.text.strip()
            ent_text_orig = text[ent.start_char:ent.start_char + len(ent_text_title)]
            
            # Make sure we got the boundaries right and it was actually all caps originally
            if ent_text_orig.upper() == ent_text_title.upper() and ent_text_orig.isupper():
                if _should_skip_entity(ent_text_orig, output_category):
                    continue
                if output_category == "ORGANIZATION" and _has_product_context(text, ent.start_char, ent.start_char + len(ent_text_orig), ent_text_orig):
                    continue
                
                # Check for duplicates
                duplicate = any(
                    d["start"] == ent.start_char and d["end"] == ent.start_char + len(ent_text_orig)
                    for d in detections
                )
                if not duplicate:
                    confidence = _adjust_confidence(output_category, ent_text_orig, _compute_confidence(ent))
                    if not _should_keep_detection(
                        ent_text_orig,
                        output_category,
                        confidence,
                        "ner",
                        ent.start_char,
                        ent.start_char + len(ent_text_orig),
                        review_candidates,
                    ):
                        continue
                    detections.append({
                        "text":             ent_text_orig,
                        "category":         output_category,
                        "start":            ent.start_char,
                        "end":              ent.start_char + len(ent_text_orig),
                        "detection_method": "ner",
                        "confidence":       min(confidence, 0.85), # slightly lower confidence for title-case hack
                    })

    return detections
