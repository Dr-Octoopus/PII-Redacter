# PII Redactor — Frontend

A modern, privacy-focused web interface for the PII Redactor tool, built with **React 18** and **Vite**.

## Tech Stack

- [React 18](https://react.dev) — UI framework
- [Vite](https://vitejs.dev) — lightning-fast dev server & bundler
- [Three.js](https://threejs.org) — animated 3-D background
- Vanilla CSS — custom design system, no UI library dependencies

## Getting Started

```bash
# Install dependencies
npm install

# Start the development server (http://localhost:5173)
npm run dev

# Build for production
npm run build
```

> The frontend expects the FastAPI backend running at `http://localhost:8000`.  
> Start it with: `uvicorn api:app --reload` from the project root.

## Project Structure

```
frontend/
├── index.html
├── vite.config.js
├── public/
│   └── favicon.svg
└── src/
    ├── main.jsx               # App entry point
    ├── App.jsx                # Root component & routing
    ├── App.css                # Global styles & design tokens
    ├── index.css              # CSS reset & base styles
    ├── assets/                # Static assets (images, icons)
    └── components/
        ├── ThreeBackground.jsx    # Animated 3-D canvas background
        ├── FileDropzone.jsx       # Drag-and-drop file upload
        ├── ComparisonView.jsx     # Side-by-side original vs redacted view
        ├── DetectionSummary.jsx   # PII detection results table
        ├── DocumentViewer.jsx     # In-browser document preview
        └── DownloadBar.jsx        # Download redacted file & report
```
