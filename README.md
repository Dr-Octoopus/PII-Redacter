<div align="center">

# PII Redactor

**Detect and redact Personally Identifiable Information from documents — fully offline, no LLMs, no API calls.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)](https://react.dev)
[![spaCy](https://img.shields.io/badge/spaCy-3.7-09a3d5?logo=spacy&logoColor=white)](https://spacy.io)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## ✨ What It Does

**PII Redactor** scans `.txt`, `.docx`, `.pdf`, `.xlsx`, and common image files for sensitive personal data using a combination of **rule-based regex**, **local spaCy NER** (Named Entity Recognition), and optional OCR for image-only text. It produces two outputs for every document:

| Output | Description |
|---|---|
| `{filename}_masked{ext}` | Redacted copy of the document — PII replaced with `[REDACTED]`, original formatting preserved |
| `{filename}_report.json` | Structured JSON report — every entity found with category, text, offsets, detection method, and confidence score |

> No data ever leaves your machine. Everything runs locally.

---

## 🛡️ Supported PII Categories

| Category | Detection Method | Confidence Range |
|---|---|---|
| `EMAIL` | Regex | ~0.98 |
| `PAN_NUMBER` | Regex | ~0.97 |
| `PHONE_NUMBER` | Regex | ~0.93 |
| `IP_ADDRESS` | Regex | ~0.92 |
| `DATE_OF_BIRTH` | Regex | ~0.90 |
| `AADHAAR_NUMBER` | Regex | ~0.85 |
| `CREDIT_CARD` | Regex | ~0.82 |
| `PINCODE` | Regex | ~0.78 |
| `PERSON_NAME` | NER (spaCy) + Context rules | 0.60 – 0.92 |
| `ORGANIZATION` | NER (spaCy) + Context rules | 0.70 – 0.92 |
| `LOCATION` | NER (spaCy) | 0.60 – 0.93 |

> Confidence scores are pattern-specific and heuristic-based. The JSON report lists the individual score for every detection. Any detection below **0.75** generates a warning so a human reviewer knows exactly which match to double-check.


---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/pii-redactor.git
cd pii-redactor
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

For OCR on images, scanned PDF regions, or images embedded in DOCX files, install the Tesseract system package too:

```bash
sudo apt-get install tesseract-ocr
```

If Tesseract is not installed, normal text redaction still works and the JSON report includes an OCR warning.

### 3. Install & run the frontend (optional)

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server starts at **http://localhost:5173**.

### 4. Start the API server

```bash
uvicorn api:app --reload
```

API runs at **http://localhost:8000** · Swagger docs at **http://localhost:8000/docs**

---

## 🖥️ Usage — CLI

### Basic

```bash
python cli.py path/to/document.pdf --output-dir ./output
```

### Detect only specific PII types

```bash
python cli.py document.pdf --include EMAIL,PHONE_NUMBER
```

### Detect everything except certain types

```bash
python cli.py document.pdf --exclude PINCODE,LOCATION
```

### All options

```
positional arguments:
  filepath              Path to the input document (.txt, .docx, .pdf, .xlsx, or image)

options:
  --output-dir OUTDIR   Directory for output files (default: ./output)
  --include TYPES       Comma-separated PII types to detect (all others skipped)
  --exclude TYPES       Comma-separated PII types to skip (ignored if --include set)
```

### Sample output

```
────────────────────────────────────────────────────
  PII Redaction Summary — invoice.pdf
────────────────────────────────────────────────────
  Category               Count   Avg Confidence
  ────────────────────── ─────   ──────────────
  AADHAAR_NUMBER             1          85.0%
  EMAIL                      3          98.1%
  PERSON_NAME                2          77.5%
  PHONE_NUMBER               2          93.2%
  ──────────────────────
  TOTAL                      8
────────────────────────────────────────────────────

Redacted document : ./output/invoice_masked.pdf
JSON report       : ./output/invoice_report.json
```

---

## 🌐 Usage — REST API

### Swagger UI (recommended)

1. Open **http://localhost:8000/docs**
2. Expand **POST /redact** → click **"Try it out"**
3. Upload your file, optionally set `include` / `exclude` filters, click **Execute**
4. Download the returned `.zip` → unzip to get the masked document + JSON report

### curl

```bash
# Redact everything
curl -X POST http://localhost:8000/redact \
     -F "file=@/path/to/document.pdf" \
     --output result.zip

# Only redact specific PII types
curl -X POST http://localhost:8000/redact \
     -F "file=@/path/to/document.pdf" \
     -F "include=EMAIL,PHONE_NUMBER" \
     --output result.zip

# Exclude certain types
curl -X POST http://localhost:8000/redact \
     -F "file=@/path/to/document.pdf" \
     -F "exclude=PINCODE,LOCATION" \
     --output result.zip

# Unzip the result
unzip result.zip -d ./output
```

### Postman

1. `POST http://localhost:8000/redact`
2. Body → **form-data**
3. Add keys:

| Key | Type | Value |
|---|---|---|
| `file` | File | Your document |
| `include` | Text | e.g. `EMAIL,PHONE_NUMBER` (optional) |
| `exclude` | Text | e.g. `PINCODE` (optional) |

4. Click **Send and Download** → save with `.zip` extension → unzip

---

## 📄 JSON Report Structure

```json
{
  "source_file": "invoice.pdf",
  "total_entities_found": 4,
  "entities": [
    {
      "text": "john@example.com",
      "category": "EMAIL",
      "start": 142,
      "end": 158,
      "detection_method": "regex",
      "confidence": 0.9818
    },
    {
      "text": "9876543210",
      "category": "PHONE_NUMBER",
      "start": 201,
      "end": 211,
      "detection_method": "regex",
      "confidence": 0.9400
    }
  ],
  "warnings": [
    "Low-confidence PERSON_NAME detection ('Mr J') at offset 88 — please verify manually."
  ]
}
```

---

## 📁 Project Structure

```
pii-redactor/
├── api.py                  # FastAPI application & REST endpoints
├── cli.py                  # Command-line interface
├── requirements.txt        # Python dependencies
├── core/                   # Core redaction engine
├── detectors/              # PII detector modules (regex + NER)
├── parsers/                # Document parsers (PDF, DOCX, XLSX, TXT)
├── frontend/               # React + Vite web interface
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   └── package.json
└── output/                 # Default output directory (git-ignored)
```

---

## ⚠️ Known Limitations

- **Scanned PDFs**: Image-only PDFs have no extractable text — OCR is not yet supported, so they produce a warning and no detections.
- **NER confidence**: spaCy's `en_core_web_sm` does not expose per-entity prediction probabilities. Confidence scores for `PERSON_NAME` and `LOCATION` are heuristic (based on capitalisation, token count, etc.) and may not perfectly reflect the model's internal certainty.
- **DOCX multi-run formatting**: Redacting a paragraph clears its per-run character formatting (bold, italic within the span) while preserving paragraph-level styles (heading level, spacing, indentation).

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to your branch: `git push origin feature/your-feature-name`
5. Open a Pull Request against `main`

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
