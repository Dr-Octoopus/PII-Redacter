"""
The pipeline orchestrator.

This is the ONE function that ties every other module together.
Both cli.py and api.py call this same function, so detection and
redaction logic is NEVER duplicated between them -- ensuring that the
CLI and the API always produce identical output.

OUTPUT FILE NAMING
------------------
Old (bad):  redacted_{filename}   and   report.json
            → every run overwrites the same report.json

New (good): {stem}_masked{ext}    and   {stem}_report.json
            → each input file gets its own uniquely-named pair

Example: uploading "invoice_march.pdf" produces:
    output/invoice_march_masked.pdf
    output/invoice_march_report.json

INCLUDE / EXCLUDE
-----------------
Both detectors support include/exclude lists so callers can control
which PII entity types are checked.  The pipeline accepts these lists
and passes them straight through to each detector.

Valid category names (case-insensitive):
  Regex detector : EMAIL, PAN_NUMBER, PHONE_NUMBER, DATE_OF_BIRTH,
                   IP_ADDRESS, AADHAAR_NUMBER, CREDIT_CARD, PINCODE,
                   BANK_ACCOUNT_NUMBER, IFSC_CODE, GSTIN
  NER detector   : PERSON_NAME, LOCATION, ORGANIZATION
"""

import os
import re
from collections import Counter
from typing import Optional

from detectors.ner_detector import detect_ner_pii, cleanup_gpu
from detectors.regex_detector import detect_regex_pii
from core.merge import merge_detections
from core.redactor import redact_docx, redact_pdf, redact_txt, redact_xlsx
from core.report import build_json_report, save_report
from parsers.docx_parser import parse_docx
from parsers.ocr_parser import IMAGE_EXTENSIONS, get_ocr_status, parse_image_ocr, redact_image
from parsers.pdf_parser import parse_pdf
from parsers.txt_parser import parse_txt
from parsers.xlsx_parser import parse_xlsx

SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf", ".xlsx"} | IMAGE_EXTENSIONS


def process_document(
    filepath: str,
    output_dir: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> tuple[str, str]:
    """
    Run the full PII detection + redaction pipeline on one document.

    Args:
        filepath:   Path to the input document.
        output_dir: Directory to write the redacted file + report into.
                    Created if it doesn't already exist.
        include:    Optional list of entity category names to detect.
                    Only these types will be checked; everything else is
                    skipped.  Example: ["EMAIL", "PHONE_NUMBER"]
        exclude:    Optional list of entity category names to SKIP.
                    Ignored when *include* is also provided.
                    Example: ["PINCODE", "LOCATION"]

    Returns:
        A tuple of (redacted_file_path, report_json_path).

    Raises:
        ValueError: If the file extension isn't supported.
    """
    os.makedirs(output_dir, exist_ok=True)

    filename  = os.path.basename(filepath)
    stem      = os.path.splitext(filename)[0]          # e.g. "invoice_march"
    extension = os.path.splitext(filename)[1].lower()  # e.g. ".pdf"

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{extension}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    warnings: list[str] = []

    # ------------------------------------------------------------------ #
    # Step 1 — Parse the document into plain text                         #
    # ------------------------------------------------------------------ #
    if extension in {".pdf", ".docx"} | IMAGE_EXTENSIONS:
        ocr_status = get_ocr_status()
        if not ocr_status.available and ocr_status.warning:
            warnings.append(ocr_status.warning)

    if extension == ".txt":
        text = parse_txt(filepath)
        structure_map = None
    elif extension == ".docx":
        text, structure_map = parse_docx(filepath)
    elif extension == ".xlsx":
        text, structure_map = parse_xlsx(filepath)
    elif extension == ".pdf":
        text, structure_map = parse_pdf(filepath)
        if len(text.strip()) < 20:
            warnings.append(
                "Very little text could be extracted from this PDF. "
                "It may be a scanned/image-only document. Please review "
                "it manually if OCR did not recover the expected text."
            )
    else:  # image file
        text, structure_map = parse_image_ocr(filepath)
        if len(text.strip()) < 1:
            warnings.append(
                "No text could be extracted from this image. If OCR is "
                "available, please check the image quality and language."
            )

    # ------------------------------------------------------------------ #
    # Step 2 — Run both detectors and merge their results                 #
    # ------------------------------------------------------------------ #
    regex_hits = detect_regex_pii(text, include=include, exclude=exclude)
    ner_hits   = detect_ner_pii(text,   include=include, exclude=exclude)
    entities   = merge_detections(regex_hits, ner_hits)
    entities   = _expand_consistent_entities(text, entities)

    # ------------------------------------------------------------------ #
    # Step 3 — Redact, dispatching to the format-specific redactor       #
    # ------------------------------------------------------------------ #
    redacted_filename = f"{stem}_masked{extension}"
    redacted_path     = os.path.join(output_dir, redacted_filename)

    if extension == ".txt":
        redact_txt(filepath, entities, redacted_path)
    elif extension == ".docx":
        redact_docx(filepath, entities, structure_map, redacted_path)
    elif extension == ".xlsx":
        redact_xlsx(filepath, entities, structure_map, redacted_path)
    elif extension == ".pdf":
        redact_pdf(filepath, entities, structure_map, redacted_path)
    else:  # image file
        redact_image(filepath, entities, structure_map, redacted_path)

    # ------------------------------------------------------------------ #
    # Step 4 — Build and save the JSON report                             #
    # ------------------------------------------------------------------ #
    report      = build_json_report(entities, filename, extra_warnings=warnings)
    report_path = os.path.join(output_dir, f"{stem}_report.json")
    save_report(report, report_path)

    # ------------------------------------------------------------------ #
    # Step 5 — Release GPU memory                                         #
    #          Ensures VRAM is freed between documents / requests.        #
    # ------------------------------------------------------------------ #
    cleanup_gpu()

    # ------------------------------------------------------------------ #
    # Step 6 — Print a human-readable summary to stdout                   #
    #          (CLI reads this; FastAPI logs capture it too)              #
    # ------------------------------------------------------------------ #
    _print_summary(filename, entities, warnings)

    return redacted_path, report_path


def _expand_consistent_entities(text: str, entities: list[dict]) -> list[dict]:
    """
    Redact exact repeated occurrences of high-confidence semantic entities.

    NER can catch a person or organization in one layout location and miss
    the same literal string elsewhere. Propagating exact matches keeps the
    document consistent while avoiding fuzzy guesses.
    """
    from detectors.ner_detector import _should_skip_entity

    semantic_categories = {"PERSON_NAME", "ORGANIZATION", "LOCATION"}
    expanded = list(entities)

    def overlaps_existing(start: int, end: int) -> bool:
        return any(start < e["end"] and e["start"] < end for e in expanded)

    seed_entities = [
        e for e in entities
        if e["category"] in semantic_categories
        and e.get("confidence", 0) >= 0.85
        and len(e.get("text", "").strip()) >= 4
        and (len(e.get("text", "").split()) >= 2 or e["category"] == "LOCATION")
        and not _should_skip_entity(e.get("text", ""), e["category"])
    ]

    seen_seeds: set[tuple[str, str]] = set()
    for entity in seed_entities:
        literal = " ".join(entity["text"].split())
        seed_key = (entity["category"], literal.casefold())
        if seed_key in seen_seeds:
            continue
        seen_seeds.add(seed_key)

        pattern_text = re.escape(literal)
        if literal[0].isalnum():
            pattern_text = r"(?<!\w)" + pattern_text
        if literal[-1].isalnum():
            pattern_text = pattern_text + r"(?!\w)"

        for match in re.finditer(pattern_text, text, flags=re.IGNORECASE):
            matched_str = match.group()
            if _should_skip_entity(matched_str, entity["category"]):
                continue
            if overlaps_existing(match.start(), match.end()):
                continue
            expanded.append({
                "text": matched_str,
                "category": entity["category"],
                "start": match.start(),
                "end": match.end(),
                "detection_method": "consistency_rule",
                "confidence": min(entity["confidence"], 0.88),
            })

    expanded.sort(key=lambda e: e["start"])
    return expanded


def _print_summary(
    filename: str,
    entities: list[dict],
    warnings: list[str],
) -> None:
    """
    Print a concise, human-readable summary of what was detected.

    This makes the CLI output informative without duplicating any
    report-building logic — it just reads the merged entity list.
    """
    sep = "─" * 52
    print(sep)
    print(f"  PII Redaction Summary — {filename}")
    print(sep)

    if entities:
        counts: Counter = Counter(e["category"] for e in entities)
        print(f"  {'Category':<22} {'Count':>5}   {'Avg Confidence':>14}")
        print(f"  {'─'*22} {'─'*5}   {'─'*14}")
        for category in sorted(counts):
            cat_entities = [e for e in entities if e["category"] == category]
            avg_conf = sum(e["confidence"] for e in cat_entities) / len(cat_entities)
            print(f"  {category:<22} {counts[category]:>5}   {avg_conf:>13.1%}")
        print(f"  {'─'*22}")
        print(f"  {'TOTAL':<22} {len(entities):>5}")
    else:
        print("  No PII entities detected.")

    if warnings:
        print()
        print("  Warnings:")
        for w in warnings:
            print(f"    ⚠  {w}")

    print(sep)
