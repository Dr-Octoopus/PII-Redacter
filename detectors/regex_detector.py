"""
Regex-based PII detector.

Handles PII categories that follow a fixed, predictable FORMAT.
This is why regex works well here: an email always has an @ and a
domain, a PAN number is always 5 letters + 4 digits + 1 letter, etc.

Each pattern below is compiled once at import time (not inside the
detection function) for performance -- re-compiling the same regex
on every call would be wasteful if this runs on many documents.

HOW CONFIDENCE WORKS HERE
--------------------------
Instead of one flat 0.95 for every regex match, each pattern gets its
own base score that reflects how precise its regex actually is:

  - Very strict format (EMAIL, PAN)        → 0.97-0.98  (almost never wrong)
  - Good format with rare false-positives  → 0.90-0.93  (PHONE, DATE, IP)
  - Moderate — can match non-PII numbers   → 0.80-0.88  (AADHAAR, CREDIT_CARD)
  - Broad pattern — many common numbers    → 0.78        (PINCODE)

The merge step uses these scores to decide which detection wins when
two patterns overlap the same span (e.g. AADHAAR vs PINCODE).

INCLUDE / EXCLUDE
-----------------
Pass `include` or `exclude` to detect_regex_pii() to control which
entity types are checked.  Use the category names shown in PII_PATTERNS
(e.g. "PHONE_NUMBER", "EMAIL").  These same names appear in every
detection dict and in the JSON report.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------
# Format: category_name → (compiled_regex, base_confidence_score)
#
# Ordering inside the dict is insertion order (Python 3.7+). We put more
# specific / longer patterns before broader ones so that when the merge
# step sees two overlapping hits, the tighter pattern was already captured
# with its correct score before the broader one fires.
# ---------------------------------------------------------------------------

PII_PATTERNS: dict[str, tuple[re.Pattern, float]] = {

    # ------------------------------------------------------------------ #
    # Very-high-confidence patterns (strict format, rare false-positives) #
    # ------------------------------------------------------------------ #

    "EMAIL": (
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
        0.98,
    ),

    # PAN format: exactly 5 UPPERCASE letters, 4 digits, 1 UPPERCASE letter.
    # Word boundaries ensure we don't hit substrings inside longer tokens.
    "PAN_NUMBER": (
        re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
        0.97,
    ),

    # ------------------------------------------------------------------ #
    # High-confidence patterns                                            #
    # ------------------------------------------------------------------ #

    # Indian mobile numbers: supports +91 prefix, 0 prefix, hyphens/spaces.
    "PHONE_NUMBER": (
        re.compile(r"(?<!\d)(?:\+91[-\s]?|0)?[6-9]\d{4}[-\s]?\d{5}(?!\d)"),
        0.93,
    ),

    # Dates: DD/MM/YYYY, YYYY-MM-DD, DD.MM.YYYY, 15-Aug-1995, 15 Aug 1995.
    "DATE_OF_BIRTH": (
        re.compile(
            r"(?i)\b(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
            r"|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}"
            r"|\d{1,2}[\s\-\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-\.]\d{2,4})\b"
        ),
        0.90,
    ),

    # IPv4 addresses: each octet 1-3 digits.
    "IP_ADDRESS": (
        re.compile(r"(?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d])"),
        0.92,
    ),

    # Aadhaar: 12 digits, spaced 4-4-4, hyphenated 4-4-4, or unspaced 12 digits.
    "AADHAAR_NUMBER": (
        re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\s?\d)(?!\d)"),
        0.85,
    ),

    # Credit card: four groups of 4 digits separated by spaces or hyphens,
    # OR 16 digits with no separators.
    # Confidence is set ABOVE Aadhaar (0.88 > 0.85) so that when both
    # patterns fire on the same 4×4 digit string, the credit card detection
    # wins in the merge step (higher confidence takes priority).
    "CREDIT_CARD": (
        re.compile(
            r"\b(?:\d{4}[\ \-]){3}\d{4}\b"    # 4-4-4-4 with separators
            r"|\b\d{16}\b"                      # 16 digits, no separators
        ),
        0.88,
    ),

    # Indian PIN code: exactly 6 digits.
    # Negative lookbehind/lookahead: must NOT be preceded or followed by
    # another digit, so we don't match a 6-digit prefix inside a phone
    # number (10 digits) or Aadhaar (12 digits).
    "PINCODE": (
        re.compile(r"(?<!\d)\d{6}(?!\d)"),
        0.78,
    ),

    # ------------------------------------------------------------------ #
    # Banking PII                                                         #
    # ------------------------------------------------------------------ #

    # Indian bank account numbers are 9-18 digits with no fixed checksum,
    # making a pure digit pattern too noisy.  We anchor detection with a
    # keyword BEFORE the digits — only the digit group (group 1) is
    # captured, so the "Account No:" label is NOT included in the redacted
    # span (only the actual digits get masked).
    # Keyword alternatives listed explicitly to avoid partial matching.
    # [:\s]* after the optional separator handles 'Account No: 123'
    # where the colon comes after the 'No' keyword.
    "BANK_ACCOUNT_NUMBER": (
        re.compile(
            r"(?i)"
            r"(?:bank\s+acc(?:ount|t)?|account|acct|a/c|a/?c)"
            r"\s*(?:no\.?|num(?:ber)?\.?|#|:)?[:\s]*"
            r"(\d{9,18})"
            r"(?!\d)"
        ),
        0.82,
    ),

    # IFSC (Indian Financial System Code): 4 UPPERCASE letters, literal '0',
    # then 6 alphanumeric characters (e.g. SBIN0001234).
    # The format is strictly mandated by the RBI, so confidence is high.
    "IFSC_CODE": (
        re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        0.96,
    ),

    # GSTIN (Goods and Services Tax Identification Number):
    # 2 digits (state code) + 10-char PAN + 1 digit (entity number) +
    # 1 letter 'Z' + 1 alphanumeric checksum.  Exact format is mandated.
    "GSTIN": (
        re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"),
        0.97,
    ),
}

# Public list of all valid category names — useful for validation in CLI/API.
ALL_CATEGORIES: list[str] = list(PII_PATTERNS.keys())


# ---------------------------------------------------------------------------
# IP address validation
# ---------------------------------------------------------------------------

def _is_valid_ip(text: str) -> bool:
    """
    Validate that a regex-matched IP address is a *plausible* real IP
    rather than a document section header like "2.1.3.1" or "1.2.4.5".

    Rules:
      - Exactly 4 dot-separated parts (already guaranteed by regex).
      - Every octet must be in [0, 255].
      - Reject all-zero (0.0.0.0).
      - Reject section-number-like patterns (all octets <= 20) UNLESS
        it matches common IP ranges (10.x.x.x, 127.x.x.x, contains 0, etc.).
    """
    parts = text.split(".")
    if len(parts) != 4:
        return False
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return False
    if not all(0 <= o <= 255 for o in octets):
        return False
    if all(o == 0 for o in octets):
        return False
    if all(o <= 20 for o in octets):
        if octets[0] in (10, 127) or text in ("1.1.1.1", "8.8.8.8", "8.8.4.4", "9.9.9.9") or 0 in octets:
            return True
        return False
    return True


# ---------------------------------------------------------------------------
# Detection function
# ---------------------------------------------------------------------------

def detect_regex_pii(
    text: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> list[dict]:
    """
    Run regex patterns over *text* and return a list of PII detections.

    Args:
        text:    The full document text to scan.
        include: If provided, ONLY these category names are checked.
                 Example: ["EMAIL", "PHONE_NUMBER"]
        exclude: If provided, these category names are skipped.
                 Example: ["PINCODE", "IP_ADDRESS"]
                 Ignored when *include* is also supplied.

    Returns:
        A list of detection dicts.  Each dict has:
            text              – the matched substring
            category          – one of the keys in PII_PATTERNS
            start / end       – character offsets in *text*
            detection_method  – always "regex" here
            confidence        – pattern-specific float (see module docstring)

    Category names (pass these to include/exclude):
        EMAIL, PAN_NUMBER, PHONE_NUMBER, DATE_OF_BIRTH, IP_ADDRESS,
        AADHAAR_NUMBER, CREDIT_CARD, PINCODE,
        BANK_ACCOUNT_NUMBER, IFSC_CODE
    """
    # Determine which categories to actually run.
    if include:
        # Normalise to uppercase so callers can pass "email" or "EMAIL".
        active = {c.upper() for c in include}
    elif exclude:
        active = {c for c in PII_PATTERNS} - {c.upper() for c in exclude}
    else:
        active = set(PII_PATTERNS.keys())

    detections = []

    for category, (pattern, base_confidence) in PII_PATTERNS.items():
        if category not in active:
            continue

        for match in pattern.finditer(text):
            # BANK_ACCOUNT_NUMBER uses a capturing group (group 1) so that
            # only the digit string is redacted — the "Account No:" keyword
            # anchor is group 0 (full match) but we want to redact only the
            # digits (group 1).  All other patterns have no capturing groups,
            # so group(0) == group() for them.
            if category == "BANK_ACCOUNT_NUMBER" and match.lastindex:
                matched_text = match.group(1)
                start = match.start(1)
                end   = match.end(1)
            else:
                matched_text = match.group()
                start = match.start()
                end   = match.end()

            # IP validation: skip matches that look like section headers.
            if category == "IP_ADDRESS" and not _is_valid_ip(matched_text):
                continue

            # Compute a small per-match confidence adjustment.
            # A very short match of a "broad" pattern (e.g. a 6-digit
            # PINCODE) scores at the base; a longer, clean match scores
            # slightly higher (capped at 0.99 to stay below 1.0).
            length_bonus = min(0.02, len(matched_text) * 0.001)
            confidence = min(0.99, base_confidence + length_bonus)

            detections.append({
                "text":             matched_text,
                "category":         category,
                "start":            start,
                "end":              end,
                "detection_method": "regex",
                "confidence":       round(confidence, 4),
            })

    return detections
