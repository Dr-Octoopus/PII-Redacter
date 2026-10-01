"""
Contextual and pattern-assisted PII detector for Names and Organizations.

Complements spaCy NER by catching names and company names in structured
documents, tables, revision histories, headers, and copyright blocks that
statistical NER models may miss or group together.
"""

import re

# Non-name technical terms & job titles to reject if matched by title-case patterns
REJECT_TITLE_WORDS = {
    "revision history", "user manual", "system requirements", "installation steps",
    "execution workflow", "landing page", "security considerations", "contact information",
    "document status", "customer reference", "not applicable", "initial revision",
    "for review", "for approval", "internal review", "issued for", "preliminary",
    "tools factory", "tool owner", "factory lead", "factory manager", "general information",
    "table contents", "project code", "file name", "page number", "all rights",
    "confidential proprietary", "technical specification", "functional requirement",
    "confidential and proprietary", "rights reserved", "unauthorized duplication",
    "tools factory lead", "tools factory manager", "tool owner",
    "director- hr & admin", "director - hr & admin", "director- hr", "director - hr",
    "hr & admin", "director", "authorized signatory", "signatory", "signature",
    "distribution list", "contact email", "registered addresses", "ifsc code", "gstin",
    "revision history and document control", "document control", "audit committee",
    "department of compliance", "department of finance", "department of information security",
    "department of audit", "department of human resources", "department of legal",
    "legal entity details", "financial audit trail", "technical logs", "compliance audit",
    "digital personal data", "protection act", "legal entity", "audit trail",
    "chief information", "information security", "chief information officer",
    "autonomous", "affiliated", "charitable", "nomination", "certificate"
}

FALSE_ORG_TERMS = {
    "signal", "signals", "process", "processes", "excel", "workbook", "workbooks",
    "configuration", "configurations", "application", "applications", "manual",
    "repository", "api", "page", "revision", "status", "description",
    "admin", "administration", "hr", "director", "signatory", "signature",
    "schedule", "table", "figure", "section", "appendix", "chapter", "abstract",
    "pan", "dob", "name", "father", "department", "govt", "india", "tax",
    "and", "any", "the", "its", "all", "other", "such", "each", "this", "that", "which",
    "role", "registered", "city", "address", "addresses", "version", "date",
    "author", "prepared", "reviewed", "approved", "gstin", "ifsc", "code",
    "legal", "entity", "details", "financial", "audit", "trail", "technical", "logs",
    "digital", "personal", "data", "protection", "act", "compliance", "summary",
    "scope", "overview", "vendor", "report", "chief", "information", "security",
    "officer", "division", "technology"
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
    "manager", "lead", "director", "admin", "administration", "hr", "signatory",
    "signature", "authorized", "officer", "executive", "president", "contact",
    "distribution", "list", "email", "legal", "entity", "details", "financial",
    "audit", "trail", "technical", "logs", "digital", "personal", "data",
    "protection", "act", "compliance", "summary", "scope", "overview", "vendor", "report",
    "chief", "information", "security", "officer", "division", "technology",
    "institute", "university", "college", "academy", "polytechnic", "ministry", "department",
    "foundation", "trust", "cell", "hackathon", "council", "board", "association", "society",
    "autonomous", "affiliated", "charitable", "nomination", "certificate"
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
    r"((?:(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+)?[A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)

PERSON_NAME_PATTERN = re.compile(
    r"\b((?:(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+)?[A-Z][a-z]{2,}(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]{2,})\b"
)
ROLE_LINE_PATTERN = re.compile(
    r"(?i)\b(?:developed\s+by|reviewed\s+by|released\s+by|prepared\s+by|approved\s+by|"
    r"submitted\s+by|author|lead|manager|owner)\b\s*[:\-]?\s*(.*)$"
)

# Government Ministries, Educational Boards, Apex Bodies & Academic Institutions
GOVT_ACADEMIC_ORG_PATTERN = re.compile(
    r"(?i)\b("
    r"Ministry[^\S\r\n]+of[^\S\r\n]+[A-Za-z]+(?:[^\S\r\n]+[A-Za-z]+){0,3}"
    r"|Department[^\S\r\n]+of[^\S\r\n]+[A-Za-z]+(?:[^\S\r\n]+[A-Za-z]+){0,3}"
    r"|[A-Za-z0-9&\-\.']+(?:[^\S\r\n]+[A-Za-z0-9&\-\.']+){0,5}[^\S\r\n]+(?:Institute[^\S\r\n]+of[^\S\r\n]+Information[^\S\r\n]+Technology|Institute[^\S\r\n]+of[^\S\r\n]+Technology|College[^\S\r\n]+of[^\S\r\n]+Engineering|Innovation[^\S\r\n]+Cell|University|Trust|Academy|Polytechnic)"
    r"|\b(?:AICTE|A\.I\.C\.T\.E\.|UGC|NCERT|CBSE|ICSE|NTA|ISRO|DRDO|VIIT|IIT|NIT|BITS|BVP|COEP)\b"
    r")\b"
)

# Copyright and ownership organization patterns (single-line only)
COPYRIGHT_ORG_PATTERN = re.compile(
    r"(?i)(?:©|copyright|owned\s+by|permission\s+of)\s+"
    r"([A-Z][A-Za-z0-9&\-[^\S\r\n]]{2,50}?(?:Solutions|Systems|Centre|Center|Technologies|Services|Group|Holdings|Inc|Ltd|Limited|Corp|Corporation|Pvt|LLC|PLC|companies)?)\b"
)

# Known company legal suffixes and brand indicator pattern (single-line only, no newlines)
ORG_SUFFIX_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&\.\-]+(?:[^\S\r\n]+[A-Z][A-Za-z0-9&\.\-]+){0,4}[^\S\r\n]+"
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
        clean_text = re.sub(r"^(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+", "", normalized, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s+[A-Z]\.?\s+", " ", clean_text)
        words = clean_text.split()
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

        for lookahead in lines[idx + 1:idx + 4]:
            candidate_line = lookahead.group().strip()
            if candidate_line.lower() in REJECT_TITLE_WORDS:
                continue
            candidate_match = PERSON_NAME_PATTERN.search(candidate_line)
            if candidate_match:
                add_person(candidate_match.group(1), lookahead.start() + candidate_match.start(1), confidence=0.92)
                break

    # 1b. Revision-history & structured tables: sliding window token matcher
    for revision_match in re.finditer(r"(?i)\brevision\s+history\b", text):
        block_start = revision_match.end()
        block_end = min(len(text), block_start + 2500)
        block = text[block_start:block_end]
        if not any(k in block.lower() for k in ["author", "prepared", "reviewed", "approved", "developed", "released"]):
            continue
        
        words = list(re.finditer(r"\b[A-Za-z\.]+\b", block))
        for i in range(len(words) - 1):
            w1, w2 = words[i].group(), words[i+1].group()
            cand_2 = f"{w1} {w2}"
            if is_valid_person_name(cand_2):
                add_person(cand_2, block_start + words[i].start(), confidence=0.92)
            if i < len(words) - 2:
                w3 = words[i+2].group()
                cand_3 = f"{w1} {w2} {w3}"
                if is_valid_person_name(cand_3):
                    add_person(cand_3, block_start + words[i].start(), confidence=0.92)

    # 1c. General Person Name pattern scan across document
    for m in PERSON_NAME_PATTERN.finditer(text):
        add_person(m.group(0), m.start(0), confidence=0.90)

    # 2. Copyright / Ownership Org detections
    for m in COPYRIGHT_ORG_PATTERN.finditer(text):
        org_text = m.group(1).strip(" .,;:\n\r")
        if "\n" in org_text:
            org_text = org_text.split("\n")[-1].strip()
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
        raw_match = m.group(1)
        org_text = raw_match.strip()
        if "\n" in org_text:
            org_text = org_text.split("\n")[-1].strip()
        words = [w.strip(".,;:()[]{}'\"").lower() for w in org_text.split()]
        if (
            org_text.lower() not in REJECT_TITLE_WORDS
            and len(org_text) >= 3
            and not all(w in FALSE_ORG_TERMS for w in words)
        ):
            if not any(stop in org_text.lower() for stop in ["unauthorized", "prohibited", "trademarks"]):
                rel_idx = raw_match.rfind(org_text)
                start_off = m.start(1) + (rel_idx if rel_idx != -1 else 0)
                add_detection({
                    "text": org_text,
                    "category": "ORGANIZATION",
                    "start": start_off,
                    "end": start_off + len(org_text),
                    "detection_method": "context_rule",
                    "confidence": 0.88,
                })

    # 4. Government Ministries, Educational Boards, Apex Bodies & Academic Institutions
    for m in GOVT_ACADEMIC_ORG_PATTERN.finditer(text):
        raw_match = m.group(1)
        org_text = raw_match.strip(" .,;:\n\r")
        org_text = re.sub(r"^(?:organized by|affiliated to|an|the|sponsored by|held at|held on)\s+", "", org_text, flags=re.IGNORECASE)
        cleaned_org = re.sub(r"^(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)?\s*(?:[A-Z][a-z]+\s+)+(?=[A-Z][a-z]+\s+(?:Institute|College|University|Trust|Academy|Polytechnic))", "", org_text)
        if cleaned_org:
            org_text = cleaned_org
        lower_org = org_text.lower()
        if lower_org in {"government of india", "govt of india", "government of maharashtra"}:
            continue
        if lower_org not in REJECT_TITLE_WORDS and len(org_text) >= 3:
            rel_idx = raw_match.rfind(org_text)
            start_off = m.start(1) + (rel_idx if rel_idx != -1 else 0)
            add_detection({
                "text": org_text,
                "category": "ORGANIZATION",
                "start": start_off,
                "end": start_off + len(org_text),
                "detection_method": "context_rule",
                "confidence": 0.92,
            })

    return detections
