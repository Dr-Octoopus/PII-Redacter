"""
Parser for .pdf files, using PyMuPDF (imported as `fitz`).

Design choice: we extract text PER PAGE (not the whole PDF as one
string) because redaction on a PDF happens per page too -- we need
to know which page a piece of text was found on so we can draw the
black-out box on that exact page later.

We don't compute character offsets for PDFs the way we do for txt/
docx. Instead, the redactor re-locates matched text on the page
using PyMuPDF's `page.search_for()`, which returns the exact pixel
coordinates (a "bounding box") of that text on the page. This is
more reliable for PDFs, where visual layout matters more than raw
character position.
"""

import pymupdf as fitz  # PyMuPDF (modern import path)


def parse_pdf(filepath: str) -> tuple[str, list[dict]]:
    """
    Extract text from a PDF, page by page.

    Args:
        filepath: Path to the .pdf file on disk.

    Returns:
        A tuple of:
          - full_text: all pages' text joined with newlines (used
            for running detection across the whole document).
          - page_map: a list of dicts, one per page, containing the
            page number and that page's raw text. The redactor uses
            page numbers (not offsets) to locate where to redact.
    """
    doc = fitz.open(filepath)

    full_text_parts = []
    page_map = []

    for page_number, page in enumerate(doc):
        page_text = page.get_text("text")
        page_map.append({
            "page_number": page_number,
            "text": page_text,
        })
        full_text_parts.append(page_text)

    doc.close()

    full_text = "\n".join(full_text_parts)
    return full_text, page_map
