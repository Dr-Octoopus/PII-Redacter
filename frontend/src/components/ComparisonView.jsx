import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, ZoomIn, ZoomOut, RotateCcw, Columns, Maximize2 } from 'lucide-react';
import DocumentViewer from './DocumentViewer';

export default function ComparisonView({ jobId, renderType, totalPages, originalText, redactedText }) {
  const [currentPage, setCurrentPage] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'redacted-only'

  const prevPage = () => {
    if (currentPage > 0) setCurrentPage(currentPage - 1);
  };

  const nextPage = () => {
    if (currentPage < totalPages - 1) setCurrentPage(currentPage + 1);
  };

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 20, 220));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 20, 60));
  const handleZoomReset = () => setZoomLevel(100);

  const originalImgUrl = `/api/preview/original/${jobId}/${currentPage}`;
  const redactedImgUrl = `/api/preview/redacted/${jobId}/${currentPage}`;

  return (
    <div className="glass-card" style={{ padding: '1.75rem', marginBottom: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--text-primary)' }}>
          <Eye size={20} color="var(--accent-primary)" /> Document Side-by-Side Comparison
        </h3>

        {/* View Mode & Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: '0.25rem', background: 'var(--bg-surface-elevated)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <button
              type="button"
              className={`btn btn-sm ${viewMode === 'split' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setViewMode('split')}
              title="Side-by-side split view"
            >
              <Columns size={14} /> Side-by-Side
            </button>
            <button
              type="button"
              className={`btn btn-sm ${viewMode === 'redacted-only' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setViewMode('redacted-only')}
              title="Focus on redacted output"
            >
              <Maximize2 size={14} /> Redacted Only
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <button type="button" className="btn btn-outline btn-sm" onClick={handleZoomOut} title="Zoom out">
              <ZoomOut size={14} />
            </button>
            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', minWidth: '42px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)' }}>
              {zoomLevel}%
            </span>
            <button type="button" className="btn btn-outline btn-sm" onClick={handleZoomIn} title="Zoom in">
              <ZoomIn size={14} />
            </button>
            <button type="button" className="btn btn-outline btn-sm" onClick={handleZoomReset} title="Reset zoom">
              <RotateCcw size={14} />
            </button>
          </div>

          {renderType === 'image' && totalPages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={prevPage}
                disabled={currentPage === 0}
              >
                <ChevronLeft size={16} /> Prev
              </button>

              <span style={{ fontSize: '0.825rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Page {currentPage + 1} / {totalPages}
              </span>

              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={nextPage}
                disabled={currentPage >= totalPages - 1}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>
      </div>

      <div
        className="comparison-layout"
        style={{
          gridTemplateColumns: viewMode === 'split' ? '1fr 1fr' : '1fr',
        }}
      >
        {viewMode === 'split' && (
          <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
            <DocumentViewer
              title="Original Document"
              renderType={renderType}
              imageSrc={originalImgUrl}
              textContent={originalText}
              pageNum={currentPage}
              totalPages={totalPages}
              zoomLevel={zoomLevel}
            />
          </div>
        )}

        <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
          <DocumentViewer
            title="Redacted Output"
            renderType={renderType}
            imageSrc={redactedImgUrl}
            textContent={redactedText}
            pageNum={currentPage}
            totalPages={totalPages}
            zoomLevel={zoomLevel}
          />
        </div>
      </div>
    </div>
  );
}

