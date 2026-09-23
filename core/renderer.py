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
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)
    doc = fitz.open()

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        pdf_page = doc.new_page(width=792, height=612)  # Landscape letter
        margin = 40
        y = margin

        # Sheet header
        pdf_page.draw_rect(fitz.Rect(margin, y, 792 - margin, y + 26), color=(0.1, 0.5, 0.3), fill=(0.9, 0.97, 0.93))
        pdf_page.insert_text(fitz.Point(margin + 10, y + 18), f"Spreadsheet Sheet: {sheet_name}", fontsize=12, fontname="helv", color=(0.05, 0.3, 0.15))
        y += 40

        max_row = min(sheet.max_row or 1, 60)
        max_col = min(sheet.max_column or 1, 10)

        col_width = (792 - 2 * margin) / max(1, max_col)
        row_height = 20

        for r in range(1, max_row + 1):
            if y + row_height > 612 - margin:
                pdf_page = doc.new_page(width=792, height=612)
                y = margin

            for c in range(1, max_col + 1):
                val = sheet.cell(row=r, column=c).value
                cell_str = str(val) if val is not None else ""

                x1 = margin + (c - 1) * col_width
                y1 = y
                x2 = x1 + col_width
                y2 = y1 + row_height

                rect = fitz.Rect(x1, y1, x2, y2)
                bg_color = (0.92, 0.95, 0.98) if r == 1 else (1.0, 1.0, 1.0)
                pdf_page.draw_rect(rect, color=(0.8, 0.8, 0.8), fill=bg_color)
                if cell_str:
                    pdf_page.insert_textbox(rect, f" {cell_str}", fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))

            y += row_height

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
