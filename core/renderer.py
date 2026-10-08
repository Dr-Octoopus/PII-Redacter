"""
Document-to-PNG renderer for the React UI preview.

Converts documents into page images so the frontend can show a
pixel-perfect side-by-side view of original vs redacted documents
without any formatting loss.

RENDERING STRATEGIES
--------------------
  PDF   → PyMuPDF renders each page directly to PNG (pixel-perfect).
  DOCX  → LibreOffice headless if installed, or native python-docx + PyMuPDF fallback.
  XLSX  → LibreOffice headless if installed, or native openpyxl + PyMuPDF fallback.
  TXT   → Returned as raw text (the React viewer handles display).

DPI
---
150 DPI gives a good balance between sharp text and reasonable file
size (~200-400 KB per page for typical documents).
"""

import os
import subprocess
import tempfile
from io import BytesIO

import pymupdf as fitz
from PIL import Image

from parsers.ocr_parser import IMAGE_EXTENSIONS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RENDER_DPI = 150
_ZOOM = RENDER_DPI / 72  # PyMuPDF's default is 72 DPI


# ---------------------------------------------------------------------------
# PDF → PNG (direct rendering)
# ---------------------------------------------------------------------------

def render_pdf_pages(filepath: str) -> list[bytes]:
    """
    Render each page of a PDF to a PNG image.

    Args:
        filepath: Path to the .pdf file.

    Returns:
        A list of PNG byte strings, one per page.
    """
    doc = fitz.open(filepath)
    pages = []

    for page in doc:
        mat = fitz.Matrix(_ZOOM, _ZOOM)
        pix = page.get_pixmap(matrix=mat)
        pages.append(pix.tobytes("png"))

    doc.close()
    return pages


# ---------------------------------------------------------------------------
# Office documents → PNG (via LibreOffice headless or Native Fallback)
# ---------------------------------------------------------------------------

def _convert_to_pdf_via_libreoffice(filepath: str, output_dir: str) -> str:
    """
    Convert a DOCX or XLSX to PDF using LibreOffice headless mode.

    Args:
        filepath:   Path to the source .docx or .xlsx file.
        output_dir: Directory where the temporary PDF will be written.

    Returns:
        Path to the generated PDF file.

    Raises:
        RuntimeError: If LibreOffice is not installed or conversion fails.
    """
    try:
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", output_dir,
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=60,  # generous timeout for large files
        )
    except FileNotFoundError:
        raise RuntimeError("LibreOffice command not found.")

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed:\n{result.stderr}")

    stem = os.path.splitext(os.path.basename(filepath))[0]
    pdf_path = os.path.join(output_dir, f"{stem}.pdf")

    if not os.path.exists(pdf_path):
        raise RuntimeError(f"LibreOffice output not found: {pdf_path}")

    return pdf_path


def _render_docx_native_pages(filepath: str) -> list[bytes]:
    """
    Native Python fallback: Render a .docx document into clean PNG page images
    using python-docx and PyMuPDF (fitz) when LibreOffice is absent.
    """
    import docx

    doc = fitz.open()
    pdf_page = doc.new_page(width=612, height=792)  # Letter size
    margin = 54  # 0.75 in
    y = margin
    max_y = 792 - margin
    width = 612 - 2 * margin

    docx_doc = docx.Document(filepath)
    filename = os.path.basename(filepath)

    # Document Header Box
    pdf_page.draw_rect(fitz.Rect(margin, y, 612 - margin, y + 24), color=(0.2, 0.4, 0.8), fill=(0.93, 0.95, 1.0))
    pdf_page.insert_text(fitz.Point(margin + 10, y + 16), f"Document Preview: {filename}", fontsize=11, fontname="helv", color=(0.1, 0.25, 0.55))
    y += 40

    for paragraph in docx_doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            y += 10
            continue

        style_name = getattr(paragraph.style, "name", "") or ""
        is_heading = style_name.startswith("Heading")
        font_size = 13 if is_heading else 10
        font_name = "helv"
        color = (0.05, 0.05, 0.05)

        # Estimate line wrap count
        lines = [text[i:i+80] for i in range(0, len(text), 80)]
        height_needed = max(18, len(lines) * (font_size + 4) + (8 if is_heading else 4))

        if y + height_needed > max_y:
            pdf_page = doc.new_page(width=612, height=792)
            y = margin

        rect = fitz.Rect(margin, y, margin + width, y + height_needed)
        pdf_page.insert_textbox(rect, text, fontsize=font_size, fontname=font_name, color=color)
        y += height_needed + 4

    for table in docx_doc.tables:
        for row in table.rows:
            row_text = "  |  ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if not row_text:
                continue
            if y + 22 > max_y:
                pdf_page = doc.new_page(width=612, height=792)
                y = margin

            rect = fitz.Rect(margin, y, margin + width, y + 22)
            pdf_page.draw_rect(rect, color=(0.75, 0.75, 0.75), fill=(0.97, 0.97, 0.97))
            pdf_page.insert_textbox(rect, f" {row_text}", fontsize=9, fontname="cour", color=(0.15, 0.15, 0.15))
            y += 26

    pages = []
    mat = fitz.Matrix(_ZOOM, _ZOOM)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        pages.append(pix.tobytes("png"))

    doc.close()
    return pages


def _render_xlsx_native_pages(filepath: str) -> list[bytes]:
    """
    Native Python fallback: Render an .xlsx spreadsheet into clean PNG page images
    using openpyxl and PyMuPDF (fitz) when LibreOffice is absent.

    Improvements over the old version:
    - Reads actual column widths from the workbook (proportional columns).
    - Renders [REDACTED] cells as solid black boxes with white text so the
      preview accurately reflects the redacted Excel file.
    - Alternating row stripes for readability.
    - Handles sheet overflow across multiple PDF pages.
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)
    doc = fitz.open()

    PAGE_W, PAGE_H   = 792, 612
    MARGIN           = 36
    USABLE_W         = PAGE_W - 2 * MARGIN
    ROW_H            = 20
    HEADER_H         = 28
    FONT_SIZE        = 8.5
    FONT_HDR_SIZE    = 9.5
    MAX_ROWS         = 200
    MAX_COLS         = 20

    # colours (RGB 0-1 tuples)
    COL_HEADER_BG = (0.22, 0.35, 0.55)
    COL_HEADER_FG = (1.0,  1.0,  1.0 )
    STRIPE_A      = (1.0,  1.0,  1.0 )
    STRIPE_B      = (0.96, 0.97, 0.99)
    GRID          = (0.80, 0.82, 0.85)
    REDACT_BLUE   = (0.0,  0.13, 0.48)
    REDACT_PILL_BG = (0.90, 0.94, 0.99)
    REDACT_PILL_BORDER = (0.75, 0.83, 0.95)
    TEXT_FG       = (0.08, 0.08, 0.08)
    SHEET_HDR_BG  = (0.10, 0.50, 0.30)
    SHEET_HDR_FG  = (0.90, 0.97, 0.93)

    font_norm = fitz.Font("helv")
    font_bold = fitz.Font("hebo")

    for sheet_name in wb.sheetnames:
        sheet   = wb[sheet_name]
        max_row = min(sheet.max_row   or 1, MAX_ROWS)
        max_col = min(sheet.max_column or 1, MAX_COLS)

        # Build proportional column widths from workbook hints.
        # Fall back to 8.43 (Excel default) when no explicit width is set.
        raw_widths = []
        for ci in range(1, max_col + 1):
            col_letter = openpyxl.utils.get_column_letter(ci)
            dim = sheet.column_dimensions.get(col_letter)
            w = dim.width if (dim and dim.width) else 8.43
            raw_widths.append(max(w, 2.0))

        total_raw     = sum(raw_widths)
        col_widths_px = [w / total_raw * USABLE_W for w in raw_widths]

        current_page = None
        y = 0

        def _new_page(label: str):
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            py = MARGIN
            page.draw_rect(
                fitz.Rect(MARGIN, py, PAGE_W - MARGIN, py + HEADER_H),
                color=SHEET_HDR_BG, fill=SHEET_HDR_BG,
            )
            page.insert_text(
                fitz.Point(MARGIN + 8, py + HEADER_H - 8),
                f"Sheet: {label}",
                fontsize=11, fontname="helv", color=SHEET_HDR_FG,
            )
            return page, py + HEADER_H + 4

        current_page, y = _new_page(sheet_name)

        for r in range(1, max_row + 1):
            if y + ROW_H > PAGE_H - MARGIN:
                current_page, y = _new_page(f"{sheet_name} (cont.)")

            is_header_row = (r == 1)
            row_bg = COL_HEADER_BG if is_header_row else (STRIPE_A if r % 2 == 1 else STRIPE_B)
            row_fg = COL_HEADER_FG if is_header_row else TEXT_FG

            x = MARGIN
            for ci, col_px in enumerate(col_widths_px, start=1):
                cell_val = sheet.cell(row=r, column=ci).value
                cell_str = str(cell_val).strip() if cell_val is not None else ""

                rect = fitz.Rect(x, y, x + col_px, y + ROW_H)
                current_page.draw_rect(rect, color=GRID, fill=row_bg)

                if cell_str:
                    inner = fitz.Rect(rect.x0 + 3, rect.y0 + 1, rect.x1 - 3, rect.y1 - 1)
                    if is_header_row:
                        current_page.insert_textbox(
                            inner, cell_str,
                            fontsize=FONT_HDR_SIZE, fontname="helv",
                            color=row_fg,
                        )
                    elif "[REDACTED]" not in cell_str:
                        current_page.insert_textbox(
                            inner, cell_str,
                            fontsize=FONT_SIZE, fontname="helv",
                            color=TEXT_FG,
                        )
                    elif cell_str == "[REDACTED]":
                        # Full-cell redaction: soft pill badge + bold dark blue text
                        pill = fitz.Rect(rect.x0 + 4, rect.y0 + 2, rect.x1 - 4, rect.y1 - 2)
                        current_page.draw_rect(pill, color=REDACT_PILL_BORDER, fill=REDACT_PILL_BG)
                        current_page.insert_textbox(
                            inner, "[REDACTED]",
                            fontsize=FONT_SIZE, fontname="hebo",
                            color=REDACT_BLUE, align=1,
                        )
                    else:
                        # Partial-cell redaction: normal black text + bold dark blue [REDACTED]
                        baseline_y = rect.y0 + 13
                        curr_x = inner.x0
                        parts = []
                        curr = 0
                        while True:
                            idx = cell_str.find("[REDACTED]", curr)
                            if idx == -1:
                                if curr < len(cell_str):
                                    parts.append((cell_str[curr:], False))
                                break
                            if idx > curr:
                                parts.append((cell_str[curr:idx], False))
                            parts.append(("[REDACTED]", True))
                            curr = idx + len("[REDACTED]")

                        for part_str, is_red in parts:
                            f = font_bold if is_red else font_norm
                            col = REDACT_BLUE if is_red else TEXT_FG
                            fname = "hebo" if is_red else "helv"
                            seg_w = f.text_length(part_str, fontsize=FONT_SIZE)

                            if curr_x + seg_w > inner.x1:
                                while len(part_str) > 1 and f.text_length(part_str + "…", fontsize=FONT_SIZE) > (inner.x1 - curr_x):
                                    part_str = part_str[:-1]
                                part_str = part_str + "…"
                                seg_w = f.text_length(part_str, fontsize=FONT_SIZE)

                            if is_red:
                                pill = fitz.Rect(curr_x - 1, rect.y0 + 2, min(inner.x1, curr_x + seg_w + 1), rect.y1 - 2)
                                current_page.draw_rect(pill, color=REDACT_PILL_BORDER, fill=REDACT_PILL_BG)

                            current_page.insert_text(
                                fitz.Point(curr_x, baseline_y),
                                part_str,
                                fontsize=FONT_SIZE,
                                fontname=fname,
                                color=col,
                            )
                            curr_x += seg_w
                            if curr_x >= inner.x1:
                                break

                x += col_px

            y += ROW_H

    pages = []
    mat = fitz.Matrix(_ZOOM, _ZOOM)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        pages.append(pix.tobytes("png"))

    doc.close()
    return pages


def render_office_pages(filepath: str) -> list[bytes]:
    """
    Render each page of a DOCX or XLSX file to PNG images.
    Tries LibreOffice first; if unavailable, seamlessly uses native Python renderers.
    """
    ext = os.path.splitext(filepath)[1].lower()
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = _convert_to_pdf_via_libreoffice(filepath, tmp_dir)
            return render_pdf_pages(pdf_path)
    except Exception:
        # Seamless native Python fallback when LibreOffice is absent or fails
        if ext == ".docx":
            return _render_docx_native_pages(filepath)
        elif ext == ".xlsx":
            return _render_xlsx_native_pages(filepath)
        else:
            raise


# ---------------------------------------------------------------------------
# TXT → raw text (no image rendering needed)
# ---------------------------------------------------------------------------

def render_txt_content(filepath: str) -> str:
    """
    Read raw text content for display in the React viewer.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def render_image_file(filepath: str) -> list[bytes]:
    """Normalize a standalone image into a PNG preview page."""
    with Image.open(filepath) as image:
        output = BytesIO()
        image.convert("RGB").save(output, format="PNG")
        return [output.getvalue()]


# ---------------------------------------------------------------------------
# Unified rendering dispatch
# ---------------------------------------------------------------------------

def render_document_pages(filepath: str) -> dict:
    """
    Render a document into page images (or raw text for TXT files).
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        pages = render_pdf_pages(filepath)
        return {
            "type": "image",
            "pages": pages,
            "total_pages": len(pages),
        }
    elif ext in IMAGE_EXTENSIONS:
        pages = render_image_file(filepath)
        return {
            "type": "image",
            "pages": pages,
            "total_pages": len(pages),
        }
    elif ext in (".docx", ".xlsx"):
        pages = render_office_pages(filepath)
        return {
            "type": "image",
            "pages": pages,
            "total_pages": len(pages),
        }
    elif ext == ".txt":
        text = render_txt_content(filepath)
        return {
            "type": "text",
            "text": text,
            "total_pages": 1,
        }
    else:
        raise ValueError(f"Unsupported file type for rendering: {ext}")
