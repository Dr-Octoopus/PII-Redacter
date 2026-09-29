import React, { useRef, useState } from 'react';

export default function DocumentViewer({ renderType, imageSrc, textContent, pageNum, totalPages, title, zoomLevel = 100 }) {
  const containerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startY, setStartY] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);

  const handleMouseDown = (e) => {
    if (renderType !== 'image') return;
    setIsDragging(true);
    setStartX(e.pageX - containerRef.current.offsetLeft);
    setStartY(e.pageY - containerRef.current.offsetTop);
    setScrollLeft(containerRef.current.scrollLeft);
    setScrollTop(containerRef.current.scrollTop);
  };

  const handleMouseLeave = () => setIsDragging(false);
  const handleMouseUp = () => setIsDragging(false);

  const handleMouseMove = (e) => {
    if (!isDragging || renderType !== 'image') return;
    e.preventDefault();
    const x = e.pageX - containerRef.current.offsetLeft;
    const y = e.pageY - containerRef.current.offsetTop;
    const walkX = (x - startX) * 1.5; // Drag speed multiplier
    const walkY = (y - startY) * 1.5;
    containerRef.current.scrollLeft = scrollLeft - walkX;
    containerRef.current.scrollTop = scrollTop - walkY;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="pane-header">
        <span>{title}</span>
        {renderType === 'image' && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Page {pageNum + 1} of {totalPages}
          </span>
        )}
      </div>

      <div
        ref={containerRef}
        className="pane-body"
        onMouseDown={handleMouseDown}
        onMouseLeave={handleMouseLeave}
        onMouseUp={handleMouseUp}
        onMouseMove={handleMouseMove}
        style={{
          height: '720px',
          maxHeight: '72vh',
          overflow: 'auto',
          position: 'relative',
          width: '100%',
          padding: '1.25rem',
          background: 'var(--pane-bg)',
          cursor: renderType === 'image' ? (isDragging ? 'grabbing' : 'grab') : 'auto',
        }}
      >
        {renderType === 'image' && imageSrc && (
          <div
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'flex-start',
              minHeight: '100%',
            }}
          >
            <img
              src={imageSrc}
              alt={`${title} page ${pageNum + 1}`}
              className="document-page-image"
              style={{
                width: `${zoomLevel}%`,
                maxWidth: 'none',
                height: 'auto',
                boxShadow: 'var(--shadow-lg)',
                borderRadius: '6px',
                transition: 'width 0.15s ease-out',
                display: 'block',
              }}
            />
          </div>
        )}

        {renderType === 'text' && (
          <div
            className="document-text-container"
            style={{
              fontSize: `${(zoomLevel / 100) * 0.925}rem`,
              lineHeight: 1.7,
              width: '100%',
              minHeight: '100%',
            }}
          >
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


