"""
Redaction engine.

GOLDEN RULE: EDIT THE ORIGINAL FILE OBJECT IN PLACE — never rebuild
the document from scratch.  Rebuilding loses formatting, fonts, styles,
images, and layout.  Editing in place keeps everything except the PII.

MASK TEXT
---------
PII spans are replaced with the literal string "[REDACTED]".  For PDFs
we draw a true redaction annotation (black box) that permanently
removes the underlying text — not just a visual overlay that can still
be copy-pasted.

DOCX TABLE SUPPORT
------------------
The previous version only iterated `document.paragraphs`, so any PII
inside a DOCX table was silently ignored.  The updated `redact_docx()`
uses the extended structure_map returned by the new docx_parser and
also edits table cell paragraphs.

WHY THE "RUNS" TRICK
--------------------
A python-docx paragraph is made of one or more "runs", each of which can
carry its own character formatting (bold, italic, font size, colour …).
The safest way to overwrite text without rebuilding all run objects is:
  1. Read `paragraph.text` (concatenation of all runs).
  2. Perform replacements on that string.
  3. Write the result into run[0].text.
  4. Clear every other run (run[1:] .text = "").
This preserves the paragraph's structural style (heading level, spacing,
indentation) while replacing only the character content.  Per-run
character formatting on runs 1+ is lost, but that is an acceptable
trade-off for correct redaction.
"""

import shutil
from typing import Optional

import pymupdf as fitz  # PyMuPDF (modern import path)
from docx import Document
from openpyxl import load_workbook

from parsers.ocr_parser import redact_docx_images, redact_pdf_ocr_regions

MASK_TEXT = "[REDACTED]"


# ---------------------------------------------------------------------------
# Plain-text redaction
# ---------------------------------------------------------------------------

def redact_txt(filepath: str, entities: list[dict], output_path: str) -> None:
    """
    Redact a .txt file by replacing matched substrings at their exact offsets.

    We replace from the END of the text backward.  If we replaced from the
    start forward, an earlier replacement would shift every later offset,
    making the stored positions wrong.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    for entity in sorted(entities, key=lambda e: e["start"], reverse=True):
        text = text[:entity["start"]] + MASK_TEXT + text[entity["end"]:]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# DOCX redaction
# ---------------------------------------------------------------------------

def _get_paragraph_obj(document: Document, info: dict):
    """
    Resolve a structure_map entry back to the live python-docx Paragraph
    object that should be edited.

    Standalone paragraphs live in `document.paragraphs`.
    Table-cell paragraphs live in
        `document.tables[t].rows[r].cells[c].paragraphs[p]`.
    """
    if info["paragraph_index"] is not None:
        return document.paragraphs[info["paragraph_index"]]
    else:
        return (
            document.tables[info["table_index"]]
                    .rows[info["row_index"]]
                    .cells[info["cell_index"]]
                    .paragraphs[info["para_in_cell"]]
        )


def redact_docx(
    filepath: str,
    entities: list[dict],
    structure_map: list[dict],
    output_path: str,
) -> None:
    """
    Redact a .docx file — covering both standalone paragraphs and
    table cells — by editing text directly inside the original paragraph
    objects, so Word formatting stays exactly as it was.
    """
    document = Document(filepath)

    for element_info in structure_map:
        if element_info.get("kind"):
            continue

        # Find entities that fall inside this element.
        elem_entities = [
            e for e in entities
            if element_info["start"] <= e["start"] < element_info["end"]
        ]
        if not elem_entities:
            continue

        paragraph = _get_paragraph_obj(document, element_info)
        new_text = paragraph.text

        # Replace within the element's own local offsets
        # (global entity offset − this element's start in full_text).
        for entity in sorted(elem_entities, key=lambda e: e["start"], reverse=True):
            local_start = entity["start"] - element_info["start"]
            local_end   = entity["end"]   - element_info["start"]
            new_text = new_text[:local_start] + MASK_TEXT + new_text[local_end:]

        # Write the modified text back into the paragraph in place.
        if paragraph.runs:
            paragraph.runs[0].text = new_text
            for extra_run in paragraph.runs[1:]:
                extra_run.text = ""
        else:
            paragraph.text = new_text

    redact_docx_images(document, structure_map, entities)
    document.save(output_path)


# ---------------------------------------------------------------------------
# PDF redaction
# ---------------------------------------------------------------------------

STOPWORDS = {
    "and", "to", "the", "of", "in", "for", "on", "with", "at", "by", "from",
    "up", "about", "into", "over", "after", "or", "an", "a", "is", "it", "be",
    "are", "was", "were", "this", "that", "these", "those", "have", "has",
    "had", "been", "will", "would", "shall", "should", "may", "might", "can",
    "could", "page", "rev", "doc", "app", "status", "date"
}


def redact_pdf(
    filepath: str,
    entities: list[dict],
    structure_map: Optional[list[dict]],
    output_path: str,
) -> None:
    """
    Redact a .pdf file by drawing true redaction annotations over the
    matched text's bounding boxes on the specific page where the entity was found.

    apply_redactions() permanently removes the text under each box.
    """
    doc = fitz.open(filepath)

    for page_number, page in enumerate(doc):
        # Determine entities detected specifically on this page.
        if structure_map and page_number < len(structure_map):
            page_info = structure_map[page_number]
            p_start, p_end = page_info["start"], page_info["end"]
            page_entities = [
                e for e in entities
                if p_start <= e["start"] < p_end
            ]
        else:
            page_entities = entities

        if not page_entities:
            continue

        seen_texts: set[str] = set()
        for entity in page_entities:
            matched_text = entity.get("text", "").strip()
            if not matched_text or matched_text in seen_texts:
                continue
            seen_texts.add(matched_text)
            rects = _search_text_on_page(page, matched_text)
            for rect in rects:
                page.add_redact_annot(rect, text="", fill=(0, 0, 0))

        if structure_map and page_number < len(structure_map):
            redact_pdf_ocr_regions(page, page_info, page_entities)

        page.apply_redactions()

    doc.save(output_path)
    doc.close()


def _search_text_on_page(page, text: str) -> list:
    """
    Safely search for text on a page enforcing whole-word boundaries
    so short words/entities do NOT redact substrings inside larger words.
    Supports multi-line wrapped table cell text fallbacks.
    """
    text = text.strip()
    if not text:
        return []

    words = text.split()
    page_words = page.get_text("words")  # tuples: (x0, y0, x1, y1, word_str, block_no, line_no, word_no)

    # 1. Single-word entity: match against page_words using exact word token comparison
    if len(words) == 1:
        target_lower = text.strip(".,;:()[]{}'\"-—").lower()
        matched_rects = []
        for w in page_words:
            w_text = w[4]
            clean_w = w_text.strip(".,;:()[]{}'\"-—").lower()
            if clean_w == target_lower:
                matched_rects.append(fitz.Rect(w[0], w[1], w[2], w[3]))
            else:
                # Also check subtokens if punctuation connects words without space (e.g., 'VIIT,Pune' or 'VIIT/')
                import re
                subtokens = [st.lower() for st in re.split(r'[^a-zA-Z0-9]', w_text) if st]
                if target_lower in subtokens:
                    matched_rects.append(fitz.Rect(w[0], w[1], w[2], w[3]))
        if matched_rects:
            return matched_rects
        return page.search_for(text)

    # 2. Multi-word phrase: search using page.search_for
    raw_rects = page.search_for(text)
    if not raw_rects and len(words) > 1:
        normalized = " ".join(words)
        if normalized != text:
            raw_rects = page.search_for(normalized)

    # 3. Fallback for wrapped multi-line text (e.g. table cells with name split across lines)
    if not raw_rects and len(words) > 1:
        word_rects = []
        for word in words:
            clean_word = word.strip(".,;:()[]{}'\"-—")
            if len(clean_word) >= 2 and clean_word.lower() not in {"dr", "mr", "ms", "mrs", "prof"}:
                w_rects = _search_text_on_page(page, clean_word)
                word_rects.extend(w_rects)
        if word_rects:
            return word_rects

    if not raw_rects:
        return []

    # Filter raw_rects to ensure they don't break mid-word
    valid_rects = []
    import re
    target_clean = text.strip(".,;:()[]{}'\"-—").lower()
    target_clean_len = len(target_clean)
    for r in raw_rects:
        is_subword = False
        for w in page_words:
            word_rect = fitz.Rect(w[0], w[1], w[2], w[3])
            word_area = word_rect.width * word_rect.height
            intersect = r & word_rect
            intersect_area = intersect.width * intersect.height
            if not intersect.is_empty and intersect_area > 0:
                subtokens = [st.lower() for st in re.split(r'[^a-zA-Z0-9]', w[4]) if st]
                if target_clean in subtokens:
                    continue  # Target is an exact subtoken (e.g. 'VIIT' in 'VIIT,Pune')
                clean_w = w[4].strip(".,;:()[]{}'\"-—")
                # If target text is shorter than clean_w and rect only covers a slice of clean_w
                if target_clean_len < len(clean_w):
                    overlap_ratio = intersect_area / max(1.0, word_area)
                    if overlap_ratio < 0.80:
                        is_subword = True
                        break
        if not is_subword and r.height <= 2.8 * r.width and r.width <= 100 * r.height:
            valid_rects.append(r)

    return valid_rects






# ---------------------------------------------------------------------------
# XLSX redaction
# ---------------------------------------------------------------------------

def redact_xlsx(
    filepath: str,
    entities: list[dict],
    cell_map: list[dict],
    output_path: str,
) -> None:
    """
    Redact an .xlsx file by overwriting only the specific cells that
    contained PII, leaving every other cell, formula, and formatting
    untouched.

    Detections carry character offsets into the combined full_text.
    We use `cell_map` (produced by xlsx_parser.parse_xlsx) to translate
    those offsets back into (sheet_name, coordinate) pairs — the same
    pattern redact_docx uses with structure_map.
    """
    shutil.copy(filepath, output_path)
    workbook = load_workbook(output_path)

    cells_to_redact: set[tuple[str, str]] = set()
    for cell_info in cell_map:
        has_entity = any(
            cell_info["start"] <= e["start"] < cell_info["end"]
            for e in entities
        )
        if has_entity:
            cells_to_redact.add(
                (cell_info["sheet_name"], cell_info["coordinate"])
            )

    for sheet_name, coordinate in cells_to_redact:
        workbook[sheet_name][coordinate] = MASK_TEXT

    workbook.save(output_path)
