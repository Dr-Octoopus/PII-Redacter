"""
Contextual and pattern-assisted PII detector for Names and Organizations.

Complements spaCy NER by catching names and company names in structured
documents, tables, revision histories, headers, and copyright blocks that
statistical NER models may miss or group together.
"""

import re

# Non-name technical terms to reject if matched by title-case patterns
REJECT_TITLE_WORDS = {
    "revision history", "user manual", "system requirements", "installation steps",
    "execution workflow", "landing page", "security considerations", "contact information",
    "document status", "customer reference", "not applicable", "initial revision",
    "for review", "for approval", "internal review", "issued for", "preliminary",
    "tools factory", "tool owner", "factory lead", "factory manager", "general information",
    "table contents", "project code", "file name", "page number", "all rights",
    "confidential proprietary", "technical specification", "functional requirement",
    "confidential and proprietary", "rights reserved", "unauthorized duplication",
    "tools factory lead", "tools factory manager", "tool owner"
}

FALSE_ORG_TERMS = {
    "signal", "signals", "process", "processes", "excel", "workbook", "workbooks",
    "configuration", "configurations", "application", "applications", "manual",
    "repository", "api", "page", "revision", "status", "description"
}

NON_PERSON_WORDS = FALSE_ORG_TERMS | {
    "proprietary", "document", "filename", "customer", "reference", "applicable",
    "function", "name", "export", "engineering", "automation", "solutions",
    "near", "college", "revision", "review", "issued", "approval",
    "preliminary", "initial", "internal", "rights", "reserved", "tools",
    "factory", "getting", "started", "custom", "block", "variables", "valid",
    "credentials", "open", "web", "click", "generate", "execution", "workflow",
    "schedule", "creator", "tool", "error", "log", "read", "back", "map",
    "perform", "select", "task", "project", "troubleshooting", "issue",
    "possible", "cause", "resolution", "unable", "scope", "security",
    "considerations", "limitations", "conclusion", "support", "portal", "its",
    "the", "status", "description", "date", "page", "manual", "owner",
    "manager", "lead"
}

# Role label prefixes for name extraction
ROLE_KEYWORDS = {
    "reviewed", "released", "developed", "prepared", "approved", "submitted",
    "author", "lead", "manager", "owner", "designer", "tester", "reviewer", "approver"
}

ROLE_NAME_PATTERN = re.compile(
    r"(?i)\b(?:developed\s+by|reviewed\s+by|released\s+by|prepared\s+by|approved\s+by|"
    r"submitted\s+by|author|lead|manager|owner)\s*[:\-]?\s*"
    r"(?:Tool\s+Owner|Tools\s+Factory\s+Lead|Tools\s+Factory\s+Manager|Lead|Manager|Owner)?\s*"
    r"([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)

PERSON_NAME_PATTERN = re.compile(r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b")
ROLE_LINE_PATTERN = re.compile(
    r"(?i)\b(?:developed\s+by|reviewed\s+by|released\s+by|prepared\s+by|approved\s+by|"
    r"submitted\s+by|author|lead|manager|owner)\b\s*[:\-]?\s*(.*)$"
)

# Copyright and ownership organization patterns
COPYRIGHT_ORG_PATTERN = re.compile(
    r"(?i)(?:©|copyright|owned\s+by|permission\s+of|trademarks\s+identified\s+in\s+this\s+document\s+are\s+owned\s+by\s+one\s+of\s+the)\s+"
    r"([A-Z][A-Za-z0-9&\-\s]{2,50}?(?:Solutions|Systems|Centre|Center|Technologies|Services|Group|Holdings|Inc|Ltd|Limited|Corp|Corporation|Pvt|LLC|PLC|companies)?)\b"
)

# Known company legal suffixes and brand indicator pattern
ORG_SUFFIX_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&\.\-]+(?:\s+[A-Z][A-Za-z0-9&\.\-]+){0,4}\s+"
    r"(?:Automation\s+Solutions|Process\s+Systems(?:\s+and\s+Solutions)?|Engineering\s+Centre|Export\s+Engineering|"
    r"Solutions|Systems|Technologies|Services|Group|Holdings|Inc\.?|Ltd\.?|Limited|Corp\.?|Corporation|Pvt\.?\s+Ltd\.?|LLC|PLC))\b"
)


def detect_context_pii(text: str) -> list[dict]:
    """
    Scan text using context rules for PERSON_NAME and ORGANIZATION entities.
    """
    detections = []

    def add_detection(entity: dict) -> None:
        duplicate = any(
            d["start"] == entity["start"]
            and d["end"] == entity["end"]
            and d["category"] == entity["category"]
            for d in detections
        )
        if not duplicate:
            detections.append(entity)

    def is_valid_person_name(name_text: str) -> bool:
        normalized = " ".join(name_text.split())
        lower = normalized.lower()
        words = normalized.split()
        if lower in REJECT_TITLE_WORDS or len(words) not in (2, 3):
            return False
        if any(w.lower() in ROLE_KEYWORDS for w in words):
            return False
        if any(w.lower() in NON_PERSON_WORDS for w in words):
            return False
        return all(w[:1].isupper() and w[1:].islower() for w in words)

    def add_person(name_text: str, start: int, confidence: float = 0.90) -> None:
        normalized = " ".join(name_text.split())
        if not is_valid_person_name(normalized):
            return
        add_detection({
            "text": normalized,
            "category": "PERSON_NAME",
            "start": start,
            "end": start + len(normalized),
            "detection_method": "context_rule",
            "confidence": confidence,
        })

    # 1. Role-based names, including table layouts where the role title and
    # name are on separate extracted lines.
    lines = list(re.finditer(r"[^\n]+", text))
    for idx, line_match in enumerate(lines):
        line = line_match.group().strip()
        role_match = ROLE_LINE_PATTERN.search(line)
        if not role_match:
            continue

        trailing = role_match.group(1).strip()
        trailing_match = PERSON_NAME_PATTERN.search(trailing)
        if trailing_match:
            start = line_match.start() + role_match.start(1) + trailing_match.start(1)
            add_person(trailing_match.group(1), start, confidence=0.92)
            continue

        # Look a few extracted lines ahead. This covers:
        #   Released By:
        #   Tools Factory Manager
        #   Vishal Randhave
        for lookahead in lines[idx + 1:idx + 4]:
            candidate_line = lookahead.group().strip()
            if candidate_line.lower() in REJECT_TITLE_WORDS:
                continue
            candidate_match = PERSON_NAME_PATTERN.search(candidate_line)
            if candidate_match:
                add_person(candidate_match.group(1), lookahead.start() + candidate_match.start(1), confidence=0.92)
                break

    # 1b. Revision-history tables often contain names under Developed By /
    # Reviewed By columns without repeating the labels on every row.
    for revision_match in re.finditer(r"(?i)\brevision\s+history\b", text):
        block_start = revision_match.end()
        block_end = min(len(text), block_start + 1200)
        next_header = re.search(r"\n\s*Tools\s+Factory\s+Repository\b", text[block_start:block_end])
        if next_header:
            block_end = block_start + next_header.start()
        block = text[block_start:block_end]
        if not (re.search(r"(?i)\bdeveloped\s+by\b", block) and re.search(r"(?i)\breviewed\s+by\b", block)):
            continue
        for m in PERSON_NAME_PATTERN.finditer(block):
            add_person(m.group(1), block_start + m.start(1), confidence=0.89)


    # 2. Copyright / Ownership Org detections
    for m in COPYRIGHT_ORG_PATTERN.finditer(text):
        org_text = m.group(1).strip(" .,;:\n\r")
        # Clean trailing 'group of companies' or artifacts
        if org_text.lower().endswith(" group of companies"):
            org_text = org_text[:-19].strip()
        if org_text.lower().endswith(" group of"):
            org_text = org_text[:-9].strip()
        if org_text.lower() not in REJECT_TITLE_WORDS and len(org_text) >= 3:
            add_detection({
                "text": org_text,
                "category": "ORGANIZATION",
                "start": m.start(1),
                "end": m.start(1) + len(org_text),
                "detection_method": "context_rule",
                "confidence": 0.90,
            })

    # 3. Known Company Suffix / Pattern Orgs
    for m in ORG_SUFFIX_PATTERN.finditer(text):
        org_text = m.group(1).strip()
        words = [w.strip(".,;:()[]{}'\"").lower() for w in org_text.split()]
        if (
            org_text.lower() not in REJECT_TITLE_WORDS
            and len(org_text) >= 3
            and not all(w in FALSE_ORG_TERMS for w in words)
        ):
            # Check if this isn't inside a false positive phrase
            if not any(stop in org_text.lower() for stop in ["unauthorized", "prohibited", "trademarks"]):
                add_detection({
                    "text": org_text,
                    "category": "ORGANIZATION",
                    "start": m.start(1),
                    "end": m.end(1),
                    "detection_method": "context_rule",
                    "confidence": 0.88,
                })

    return detections
