"""
Optional OCR parser for image-only text.

This module keeps OCR text extraction beside the other parsers. It supports:
  - embedded images inside PDFs
  - embedded images inside DOCX files
  - standalone image uploads

OCR is optional. If pytesseract or the system tesseract binary is missing,
the pipeline reports a warning and continues with normal text extraction.
"""

from __future__ import annotations

import io
import shutil
from dataclasses import dataclass
from typing import Any

import pymupdf as fitz
from PIL import Image, ImageDraw


OCR_ZOOM = 2.0
OCR_LANG = "eng"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

OCR_ORG_BRANDS = {
    # Tech companies
    "adobe", "amd", "amazon", "apple", "azure", "aws", "cisco", "cognizant", "dell",
    "emerson", "engati", "facebook", "google", "honeywell", "hp", "ibm",
    "infosys", "instagram", "intel", "linkedin", "meta", "microsoft",
    "nvidia", "oracle", "salesforce", "samsung", "siemens", "sony", "tata",
    "tesla", "whatsapp", "wipro", "youtube",
    # Financial institutions (often appear as logos on documents)
    "jpmorganchase", "jpmorgan", "goldman", "citibank", "citigroup",
    "barclays", "hsbc", "ubs", "deutsche", "wellsfargo", "blackrock",
    "mastercard", "visa", "paypal", "stripe", "hdfc", "icici", "axis",
    "kotak", "reliance", "bajaj",
}


@dataclass(frozen=True)
class OcrStatus:
    available: bool
    warning: str | None = None


def get_ocr_status() -> OcrStatus:
    """Return whether pytesseract and the tesseract binary are available."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return OcrStatus(
            False,
            "OCR is not available because the 'pytesseract' Python package "
            "is not installed. Text inside images was not scanned.",
        )

    if shutil.which("tesseract") is None:
        return OcrStatus(
            False,
            "OCR is not available because the 'tesseract' system command "
            "is not installed. Text inside images was not scanned.",
        )

    return OcrStatus(True)


def _is_line_noise(word: str, w_box: int, h_box: int) -> bool:
    """
    Check if an OCR word entry is a vertical/horizontal line, margin border,
    or Tesseract line noise character (e.g. 'I', '1', 'l', '|', '_', '-', 'III', '111').
    """
    cleaned = word.strip()
    if not cleaned:
        return True

    has_alnum = any(c.isalnum() for c in cleaned)
    if not has_alnum:
        return True

    # Check for repeated single-character line noise (e.g. "IIII", "1111", "llll", "||||", "----", "____")
    unique_chars = set(cleaned.lower())
    if unique_chars <= {"i", "l", "1", "|", "_", "-", ":", ";", ".", ",", "/", "\\", "—"}:
        return True

    # Aspect ratio check:
    # No standard English text word ever has height > 2.5 * width or width > 12 * height.
    if h_box > 2.5 * w_box or w_box > 12 * h_box:
        return True

    return False


def _ocr_image_words(image: Image.Image) -> tuple[str, list[dict[str, Any]]]:
    """
    OCR a PIL image and return text plus word-level offsets and boxes.

    Offsets are relative to the returned OCR text, so normal detector hits can
    be mapped back to image rectangles for final redaction.
    """
    import pytesseract
    from pytesseract import Output

    rgb_image = image.convert("RGB")
    orig_w, orig_h = rgb_image.size

    scale = 1.0
    if orig_w < 1600 or orig_h < 1600:
        scale = 2.0
        ocr_image = rgb_image.resize((int(orig_w * scale), int(orig_h * scale)), Image.Resampling.LANCZOS)
    else:
        ocr_image = rgb_image

    data = pytesseract.image_to_data(ocr_image, lang=OCR_LANG, output_type=Output.DICT)

    words: list[dict[str, Any]] = []
    text_parts: list[str] = []
    offset = 0

    for i, raw_text in enumerate(data.get("text", [])):
        word = str(raw_text).strip()
        if not word:
            continue

        try:
            confidence = float(data.get("conf", ["-1"])[i])
        except (TypeError, ValueError):
            confidence = -1.0
        if confidence < 30:
            continue

        left = int(int(data["left"][i]) / scale)
        top = int(int(data["top"][i]) / scale)
        right = int((int(data["left"][i]) + int(data["width"][i])) / scale)
        bottom = int((int(data["top"][i]) + int(data["height"][i])) / scale)

        w_box = max(1, right - left)
        h_box = max(1, bottom - top)

        # Skip line noise, vertical margin lines, and horizontal border rules
        if _is_line_noise(word, w_box, h_box):
            continue

        if text_parts:
            offset += 1
        start = offset
        end = start + len(word)
        text_parts.append(word)

        words.append({
            "text": word,
            "start": start,
            "end": end,
            "bbox": (left, top, right, bottom),
            "confidence": confidence / 100,
        })
        offset = end

    return " ".join(text_parts), words


def words_for_span(words: list[dict[str, Any]], local_start: int, local_end: int) -> list[dict[str, Any]]:
    """Return OCR words overlapping a local text span, excluding line/margin noise."""
    result = []
    for word in words:
        if word["start"] < local_end and local_start < word["end"]:
            left, top, right, bottom = word.get("bbox", (0, 0, 1, 1))
            w_box = max(1, right - left)
            h_box = max(1, bottom - top)
            if not _is_line_noise(word["text"], w_box, h_box):
                result.append(word)
    return result




def extract_pdf_image_ocr(page, page_start: int) -> tuple[str, list[dict[str, Any]]]:
    """OCR images embedded on a PDF page and return text plus image regions."""
    if not get_ocr_status().available:
        return "", []

    text_parts: list[str] = []
    regions: list[dict[str, Any]] = []
    running_offset = 0

    seen_regions: set[tuple[float, float, float, float]] = set()
    matrix = fitz.Matrix(OCR_ZOOM, OCR_ZOOM)

    for image_info in page.get_images(full=True):
        xref = image_info[0]
        for rect in page.get_image_rects(xref):
            key = tuple(round(v, 2) for v in (rect.x0, rect.y0, rect.x1, rect.y1))
            if key in seen_regions:
                continue
            seen_regions.add(key)

            if rect.width < 20 or rect.height < 20:
                continue

            pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            region_text, words = _ocr_image_words(image)
            if not region_text:
                continue

            if text_parts:
                running_offset += 1

            region_start = page_start + running_offset
            region_end = region_start + len(region_text)
            regions.append({
                "kind": "pdf_ocr_image",
                "start": region_start,
                "end": region_end,
                "page_rect": (rect.x0, rect.y0, rect.x1, rect.y1),
                "image_size": image.size,
                "words": words,
            })
            text_parts.append(region_text)
            running_offset += len(region_text)

    return "\n".join(text_parts), regions


def extract_docx_image_ocr(document, start_offset: int) -> tuple[str, list[dict[str, Any]]]:
    """OCR images embedded in a DOCX and return text plus image map entries."""
    if not get_ocr_status().available:
        return "", []

    text_parts: list[str] = []
    image_entries: list[dict[str, Any]] = []
    running_offset = 0

    for rel_id, rel in document.part.rels.items():
        target_part = getattr(rel, "target_part", None)
        content_type = getattr(target_part, "content_type", "")
        if not content_type.startswith("image/"):
            continue

        try:
            image = Image.open(io.BytesIO(target_part.blob))
        except Exception:
            continue

        image_text, words = _ocr_image_words(image)
        if not image_text:
            continue

        if text_parts:
            running_offset += 1

        entry_start = start_offset + running_offset
        entry_end = entry_start + len(image_text)
        image_entries.append({
            "kind": "docx_ocr_image",
            "rel_id": rel_id,
            "start": entry_start,
            "end": entry_end,
            "image_size": image.size,
            "words": words,
            "content_type": content_type,
        })
        text_parts.append(image_text)
        running_offset += len(image_text)

    return "\n".join(text_parts), image_entries


def parse_image_ocr(filepath: str) -> tuple[str, list[dict[str, Any]]]:
    """OCR a standalone image file."""
    if not get_ocr_status().available:
        return "", []

    image = Image.open(filepath)
    text, words = _ocr_image_words(image)
    if not text:
        return "", []

    return text, [{
        "kind": "image_ocr",
        "start": 0,
        "end": len(text),
        "image_size": image.size,
        "words": words,
    }]


def detect_ocr_brand_entities(
    structure_map: list[dict] | None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[dict]:
    """
    Detect clean brand/logo words from OCR regions.

    This is deliberately narrow: it only uses words already produced by OCR
    regions, and only for known organization brand tokens. It catches logos
    that spaCy sometimes misses, without broadening normal text detection.
    """
    if not structure_map:
        return []

    if include:
        active = {c.upper() for c in include}
        if "ORGANIZATION" not in active:
            return []
    elif exclude and "ORGANIZATION" in {c.upper() for c in exclude}:
        return []

    detections: list[dict] = []
    seen: set[tuple[int, int, str]] = set()

    def add_word(global_start: int, raw_word: str, confidence: float) -> None:
        word = raw_word.strip(".,;:()[]{}'\"-—")
        if len(word) < 3 or word.lower() not in OCR_ORG_BRANDS:
            return
        start = global_start
        end = start + len(word)
        key = (start, end, word.lower())
        if key in seen:
            return
        seen.add(key)
        detections.append({
            "text": word,
            "category": "ORGANIZATION",
            "start": start,
            "end": end,
            "detection_method": "ocr_brand_rule",
            "confidence": round(max(0.86, min(0.95, confidence)), 4),
        })

    for entry in structure_map:
        if "ocr_regions" in entry:
            for region in entry.get("ocr_regions", []):
                region_start = region["start"]
                for word in region.get("words", []):
                    add_word(region_start + word["start"], word["text"], word.get("confidence", 0.86))
        elif entry.get("kind") in {"docx_ocr_image", "image_ocr"}:
            entry_start = entry["start"]
            for word in entry.get("words", []):
                add_word(entry_start + word["start"], word["text"], word.get("confidence", 0.86))

    return detections


def redact_docx_images(document, structure_map: list[dict], entities: list[dict]) -> None:
    """Replace DOCX image blobs with redacted image blobs when OCR hits exist."""
    image_entries = [entry for entry in structure_map if entry.get("kind") == "docx_ocr_image"]
    if not image_entries:
        return

    rels = document.part.rels
    for entry in image_entries:
        entry_entities = [
            e for e in entities
            if entry["start"] <= e["start"] < entry["end"]
        ]
        if not entry_entities:
            continue

        rel = rels.get(entry["rel_id"])
        target_part = getattr(rel, "target_part", None) if rel else None
        if target_part is None:
            continue

        try:
            source_image = Image.open(io.BytesIO(target_part.blob))
            image_format = source_image.format or "PNG"
            image = source_image.convert("RGB")
        except Exception:
            continue

        draw = ImageDraw.Draw(image)
        for entity in entry_entities:
            local_start = entity["start"] - entry["start"]
            local_end = entity["end"] - entry["start"]
            for word in words_for_span(entry["words"], local_start, local_end):
                draw.rectangle(word["bbox"], fill="black")

        output = io.BytesIO()
        if entry["content_type"] in {"image/jpeg", "image/jpg"}:
            image_format = "JPEG"
        image.save(output, format=image_format)
        target_part._blob = output.getvalue()


def redact_pdf_ocr_regions(page, page_info: dict, page_entities: list[dict]) -> None:
    """Add PDF redaction annotations over OCR word boxes."""
    for region in page_info.get("ocr_regions", []):
        region_start = region["start"]
        region_end = region["end"]
        image_width, image_height = region["image_size"]
        page_rect = fitz.Rect(region["page_rect"])

        for entity in page_entities:
            if not (region_start <= entity["start"] < region_end):
                continue

            local_start = entity["start"] - region_start
            local_end = entity["end"] - region_start
            for word in words_for_span(region["words"], local_start, local_end):
                x0, y0, x1, y1 = word["bbox"]
                w_box = max(1, x1 - x0)
                h_box = max(1, y1 - y0)
                if _is_line_noise(word["text"], w_box, h_box):
                    continue
                rect = fitz.Rect(
                    page_rect.x0 + (x0 / image_width) * page_rect.width,
                    page_rect.y0 + (y0 / image_height) * page_rect.height,
                    page_rect.x0 + (x1 / image_width) * page_rect.width,
                    page_rect.y0 + (y1 / image_height) * page_rect.height,
                )
                if rect.height <= 2.5 * rect.width and rect.width <= 12 * rect.height:
                    page.add_redact_annot(rect, text="", fill=(0, 0, 0))


def redact_image(filepath: str, entities: list[dict], structure_map: list[dict], output_path: str) -> None:
    """Redact a standalone image by drawing black boxes over OCR word hits."""
    image = Image.open(filepath).convert("RGB")

    if structure_map:
        draw = ImageDraw.Draw(image)
        for entry in structure_map:
            if entry.get("kind") != "image_ocr":
                continue
            entry_entities = [
                e for e in entities
                if entry["start"] <= e["start"] < entry["end"]
            ]
            for entity in entry_entities:
                local_start = entity["start"] - entry["start"]
                local_end = entity["end"] - entry["start"]
                for word in words_for_span(entry["words"], local_start, local_end):
                    x0, y0, x1, y1 = word["bbox"]
                    w_box = max(1, x1 - x0)
                    h_box = max(1, y1 - y0)
                    if not _is_line_noise(word["text"], w_box, h_box):
                        draw.rectangle(word["bbox"], fill="black")

    image.save(output_path)
