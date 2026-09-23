"""
Parser for .docx (Word) files.

WHAT THIS RETURNS
-----------------
Instead of one giant text blob, we return text PER ELEMENT along with
the element's index in the document.  This is what lets the redactor
later go back and edit the exact same object in the original document,
rather than rebuilding the file from scratch (which would strip all
the original formatting).

WHAT IS PARSED
--------------
A Word document has two top-level containers that hold human-visible text:

  1. Paragraphs  – `document.paragraphs`
     Headings, body text, list items, captions, etc.

  2. Table cells – `document.tables[*].rows[*].cells[*].paragraphs[*]`
     Every cell in every table is itself a list of paragraphs.

Previously only (1) was parsed, so any PII inside a table was invisible
to the detectors -- and obviously also never redacted.

HOW THE STRUCTURE MAP WORKS
---------------------------
The returned `structure_map` is a flat list of dicts.  Each dict covers
one paragraph (either a standalone paragraph OR a paragraph inside a
table cell) and contains:

    paragraph_index  – the 0-based index in `document.paragraphs` (None
                       for table paragraphs, which live outside that list)
    table_index      – index in `document.tables` (None for standalone paras)
    row_index        – row inside the table (None for standalone paras)
    cell_index       – column inside the row (None for standalone paras)
    para_in_cell     – paragraph index inside the cell (None for standalone)
    text             – the paragraph's text
    start / end      – character offsets of this text in *full_text*

The redactor uses `start`/`end` to find which element a detected entity
falls into, then uses the index fields to locate the exact python-docx
object it needs to edit in place.
"""

from docx import Document

from parsers.ocr_parser import extract_docx_image_ocr


def parse_docx(filepath: str) -> tuple[str, list[dict]]:
    """
    Extract text from a .docx file — paragraphs AND table cells.

    Args:
        filepath: Path to the .docx file on disk.

    Returns:
        A tuple of:
          - full_text: all text joined with newlines (used for detection).
          - structure_map: a list of dicts, one per paragraph/cell-paragraph,
            each containing offset and location info so the redactor can
            find and edit the exact object in the original document.
    """
    document = Document(filepath)

    full_text_parts: list[str] = []
    structure_map:  list[dict] = []
    running_offset = 0

    # ------------------------------------------------------------------ #
    # 1. Standalone paragraphs                                            #
    # ------------------------------------------------------------------ #
    for para_index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text
        start = running_offset
        end   = start + len(text)

        structure_map.append({
            "paragraph_index": para_index,
            "table_index":     None,
            "row_index":       None,
            "cell_index":      None,
            "para_in_cell":    None,
            "text":            text,
            "start":           start,
            "end":             end,
        })

        full_text_parts.append(text)
        # +1 accounts for the "\n" we join parts with below.
        running_offset = end + 1

    # ------------------------------------------------------------------ #
    # 2. Table cells                                                      #
    #    We iterate table → row → cell → paragraph so the redactor has   #
    #    exact coordinates to reach back into the live document object.   #
    # ------------------------------------------------------------------ #
    for t_idx, table in enumerate(document.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                for p_idx, paragraph in enumerate(cell.paragraphs):
                    text = paragraph.text
                    start = running_offset
                    end   = start + len(text)

                    structure_map.append({
                        "paragraph_index": None,
                        "table_index":     t_idx,
                        "row_index":       r_idx,
                        "cell_index":      c_idx,
                        "para_in_cell":    p_idx,
                        "text":            text,
                        "start":           start,
                        "end":             end,
                    })

                    full_text_parts.append(text)
                    running_offset = end + 1

    image_text, image_entries = extract_docx_image_ocr(document, running_offset)
    if image_text:
        full_text_parts.append(image_text)
        structure_map.extend(image_entries)

    full_text = "\n".join(full_text_parts)
    return full_text, structure_map
