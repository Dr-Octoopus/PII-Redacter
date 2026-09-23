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
          <div style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-secondary)' }}>
            <p style={{ marginBottom: '1rem', fontWeight: 600 }}>⚠️ Preview rendering unavailable for this office file format.</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '400px', margin: '0 auto' }}>
              Install LibreOffice (`sudo pacman -S libreoffice-fresh`) for office document page rendering, or download the redacted output directly below.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
