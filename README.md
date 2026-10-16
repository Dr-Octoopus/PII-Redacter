<div align="center">

# PII Redactor

**Enterprise-grade, offline Personally Identifiable Information (PII) detector and surgical redactor for PDF, DOCX, XLSX, TXT, and Images — powered by rule-based Regex, Contextual heuristics, and local spaCy Transformer NER (No external LLM, No API calls).**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.0-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![spaCy](https://img.shields.io/badge/spaCy-3.7%20TRF-09a3d5?logo=spacy&logoColor=white)](https://spacy.io)
[![Tesseract OCR](https://img.shields.io/badge/Tesseract-OCR-5C6BC0?logo=tesseract&logoColor=white)](https://github.com/tesseract-ocr/tesseract)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## ✨ Overview

**PII Redactor** is a privacy-first, zero-data-leakage redaction suite designed for compliance, data privacy (GDPR, DPDP Act, HIPAA), and secure document sharing. It processes `.pdf`, `.docx`, `.xlsx`, `.txt`, and standalone images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`) entirely on your local machine.

### Core Highlights

* **100% Offline & Private:** Zero external LLM calls or cloud API dependencies. All models and regex patterns run locally with GPU acceleration support (CUDA).
* **Surgical Redaction Engine:** Edits documents in place preserving layout, styles, fonts, and structure:
  * **PDF:** True vector redaction annotations (`fitz.add_redact_annot`) permanently sanitizing underlying character streams.
  * **DOCX:** Paragraph- and table-cell run preservation keeping document styles and tables intact.
  * **XLSX:** Substring-level cell redaction using openpyxl `CellRichText`, preserving original cell formatting while styling redacted tokens in bold dark blue (`#002060`) on clean sheet backgrounds.
  * **Images & Scanned Documents:** Tesseract OCR with pixel-precise black box redaction over detected text bounding boxes.
* **Modern Web Interface:** Built with React 18 and Vite featuring side-by-side original vs. redacted comparison, page navigation, interactive zoom & drag panning, category toggles with select/deselect all, dark/light theme toggle, and 3D interactive globe canvas.
* **Dual Deliverables:** Generates both the sanitized document (`{filename}_masked.{ext}`) and an audit-ready structured report (`{filename}_report.json`).

---

## 🛡️ Supported PII Categories

PII Redactor detects **15 distinct categories** spanning financial, personal, contact, technical, and semantic identifiers:

| Category | Identifier / Entity | Detection Method | Typical Confidence |
|---|---|---|---|
| `EMAIL` | Email addresses | High-precision RFC regex | ~0.98 |
| `PAN_NUMBER` | Indian Income Tax PAN (10-char alphanumeric) | Regex with structural checksum validation | ~0.97 |
| `PHONE_NUMBER` | Domestic & international phone/mobile numbers | Regex with prefix/country code anchors | ~0.93 |
| `DATE_OF_BIRTH` | Dates (DD/MM/YYYY, ISO, Month-first, ordinals, timestamps) | Comprehensive date & timestamp regex | ~0.90 |
| `IP_ADDRESS` | IPv4 addresses | Word-bounded octet regex | ~0.92 |
| `AADHAAR_NUMBER` | 12-digit Indian Aadhaar numbers (spaced/hyphenated) | Regex with negative lookahead/lookbehind | ~0.85 |
| `CREDIT_CARD` | 16-digit credit and debit card numbers | Card grouping regex | ~0.88 |
| `PINCODE` | 6-digit Indian postal PIN codes | Boundary-constrained digit regex | ~0.78 |
| `BANK_ACCOUNT_NUMBER` | Bank account numbers (9–18 digits) | Keyword-anchored contextual regex | ~0.88 |
| `IFSC_CODE` | 11-character Indian banking IFSC codes | Bank code regex (4 letters + '0' + 6 alphanumeric) | ~0.95 |
| `GSTIN` | Indian GST Identification Numbers | 15-character statutory GST format regex | ~0.96 |
| `URL` | Web domains, HTTPS/HTTP URLs, bare domains (`.com`, `.io`, etc.) | Domain regex with negative lookbehind on `@` | ~0.91 |
| `PERSON_NAME` | Full names, person names across structured forms/tables | spaCy RoBERTa Transformer (`en_core_web_trf`) + Context rules | 0.72 – 0.94 |
| `LOCATION` | Countries (India, USA, etc.), states, cities, and regions | spaCy TRF (`GPE`, `LOC`, `NORP`) + Geographic gazetteer | 0.85 – 0.94 |
| `ORGANIZATION` | Companies, brands (Microsoft, Azure, AWS, GFG), universities, banks | spaCy TRF (`ORG`, `PRODUCT`) + Context suffix rules + Brand dictionary | 0.75 – 0.94 |

---

## 🏗️ Architecture & Redaction Pipeline

```
                              ┌───────────────────────┐
                              │   Uploaded Document   │
                              └───────────┬───────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │ Document Parsing & Structure Extraction     │
                   │ • PDF: PyMuPDF text + embedded image OCR    │
                   │ • DOCX: python-docx paragraphs + tables     │
                   │ • XLSX: openpyxl cells & coordinates        │
                   │ • Images: Tesseract OCR word bounding boxes │
                   └──────────────────────┬──────────────────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
   ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
   │ Regex Detectors │           │ Local spaCy NER │           │ Context & Brand │
   │ (12 Categories) │           │ (Transformer)   │           │ Rule Engine     │
   └────────┬────────┘           └────────┬────────┘           └────────┬────────┘
            │                             │                             │
            └─────────────────────────────┼─────────────────────────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        │ Entity Merging & Overlap Resolver │
                        │ • Confidence-based deduplication  │
                        │ • Cross-document consistency pass │
                        └─────────────────┬─────────────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        │ Format-Specific Surgical Redactor │
                        │ • PDF: True vector redactions     │
                        │ • DOCX: Paragraph run overwrite   │
                        │ • XLSX: RichText dark blue token  │
                        │ • Image: Bounding box blackout    │
                        └─────────────────┬─────────────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        │     Masked Output + JSON Report   │
                        └───────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites

* **Python 3.10+**
* **Node.js 18+** & npm (for the React web frontend)
* **Tesseract OCR** (optional, recommended for scanned documents and images):
  * **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
  * **Arch Linux:** `sudo pacman -S tesseract tesseract-data-eng`
  * **macOS:** `brew install tesseract`

### 2. Clone and Setup Backend

```bash
# Clone the repository
git clone https://github.com/<your-username>/pii-redactor.git
cd pii-redactor

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
pip install -r requirements.txt

# Download spaCy Transformer model (en_core_web_trf)
python -m spacy download en_core_web_trf
```

*(Note: If running on a resource-constrained machine without GPU, `en_core_web_sm` is supported as an automatic fallback).*

### 3. Start the Application

#### Start the FastAPI Server:
```bash
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```
* **API Documentation (Swagger):** `http://127.0.0.1:8000/docs`

#### Start the React Frontend:
```bash
cd frontend
npm install
npm run dev
```
* **Web UI:** `http://localhost:5173`

---

## 🖥️ Usage

### 1. Web Application

1. Open `http://localhost:5173` in your browser.
2. Select or toggle any of the 15 PII categories you want to include or exclude.
3. Drag and drop your `.pdf`, `.docx`, `.xlsx`, `.txt`, or image file.
4. Review original and redacted pages side-by-side with interactive zoom and pan controls.
5. Download your redacted document and structured JSON audit report.

### 2. Command Line Interface (CLI)

```bash
# Basic redaction
python cli.py sample_contract.pdf --output-dir ./output

# Redact only specific categories
python cli.py patient_record.docx --include EMAIL,PHONE_NUMBER,PERSON_NAME

# Redact everything except locations
python cli.py financial_sheet.xlsx --exclude LOCATION

# Inspect all options
python cli.py --help
```

### 3. REST API

#### Endpoint: `POST /api/redact` (Frontend & Preview API)
Accepts multipart form data (`file`, optional `include`, `exclude`) and returns a job ID with rendered page previews and detection summaries.

#### Endpoint: `POST /redact` (Standard Zip Export)
```bash
curl -X POST http://127.0.0.1:8000/redact \
     -F "file=@/path/to/document.pdf" \
     -F "include=EMAIL,PHONE_NUMBER,PERSON_NAME" \
     --output result.zip

unzip result.zip -d ./output
```

---

## 📄 JSON Report Format

Every redaction operation produces a machine-readable audit report:

```json
{
  "source_file": "financial_records.xlsx",
  "total_entities_found": 3,
  "entities": [
    {
      "text": "Atharva Jadhav",
      "category": "PERSON_NAME",
      "start": 14,
      "end": 28,
      "detection_method": "ner",
      "confidence": 0.9400
    },
    {
      "text": "Microsoft Azure",
      "category": "ORGANIZATION",
      "start": 52,
      "end": 67,
      "detection_method": "context_rule",
      "confidence": 0.9400
    },
    {
      "text": "August 15, 2024",
      "category": "DATE_OF_BIRTH",
      "start": 95,
      "end": 110,
      "detection_method": "regex",
      "confidence": 0.9000
    }
  ],
  "warnings": []
}
```

---

## 📁 Repository Structure

```
pii-redactor/
├── api.py                    # FastAPI application, streaming previews & endpoints
├── cli.py                    # Command-line interface with rich tabular summaries
├── requirements.txt          # Python library specifications
├── core/                     # Redaction & Rendering Core
│   ├── pipeline.py           # End-to-end orchestration and consistency expansion
│   ├── redactor.py           # In-place surgical document redactors (PDF/DOCX/XLSX/TXT)
│   ├── renderer.py           # Multi-page visual renderer with spreadsheet emulation
│   ├── merge.py              # Overlapping span resolver and priority merger
│   └── report.py             # CLI console formatting and JSON report generation
├── detectors/                # Detection Engines
│   ├── regex_detector.py     # High-precision patterns (Email, Phone, PAN, Aadhaar, URLs, etc.)
│   ├── ner_detector.py       # spaCy Transformer NER + Category correction heuristics
│   └── context_detector.py   # Contextual rules, role-line extractors, and gazetteers
├── parsers/                  # Format Parsers & OCR
│   ├── pdf_parser.py         # PyMuPDF text & rect extractor
│   ├── docx_parser.py        # python-docx paragraph, run, & table extractor
│   ├── xlsx_parser.py        # openpyxl multi-sheet coordinate & cell offset mapper
│   ├── txt_parser.py         # Plaintext UTF-8 scanner
│   └── ocr_parser.py         # Tesseract OCR engine with brand & location detection
└── frontend/                 # React 18 + Vite UI
    ├── src/
    │   ├── App.jsx           # Master UI workflow & state management
    │   └── components/       # ComparisonView, DocumentViewer, ThreeBackground, Dropzone
    └── package.json
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss the proposed enhancement.

1. Fork the repo: `git checkout -b feature/my-enhancement`
2. Commit your changes: `git commit -m "feat: add enhancement"`
3. Push to branch: `git push origin feature/my-enhancement`
4. Open a Pull Request

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.
