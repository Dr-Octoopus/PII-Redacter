import React from 'react';

export default function DocumentViewer({ renderType, imageSrc, textContent, pageNum, totalPages, title }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="pane-header">
        <span>{title}</span>
        {renderType === 'image' && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Page {pageNum + 1} of {totalPages}
          </span>
        )}
      </div>

      <div className="pane-body">
        {renderType === 'image' && imageSrc && (
          <img
            src={imageSrc}
            alt={`${title} page ${pageNum + 1}`}
            className="document-page-image"
          />
        )}

        {renderType === 'text' && (
          <div className="document-text-container">
            {textContent || 'No text content available.'}
          </div>
        )}

        {renderType === 'error' && (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <p style={{ marginBottom: '1rem' }}>⚠️ Preview rendering unavailable for this office file type.</p>
            <p style={{ fontSize: '0.85rem' }}>Install LibreOffice (`sudo pacman -S libreoffice-fresh`) for DOCX/XLSX page rendering, or download the redacted file directly below.</p>
          </div>
        )}
      </div>
    </div>
  );
}
