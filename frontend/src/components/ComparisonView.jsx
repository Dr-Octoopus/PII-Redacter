import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import DocumentViewer from './DocumentViewer';

export default function ComparisonView({ jobId, renderType, totalPages, originalText, redactedText }) {
  const [currentPage, setCurrentPage] = useState(0);

  const prevPage = () => {
    if (currentPage > 0) setCurrentPage(currentPage - 1);
  };

  const nextPage = () => {
    if (currentPage < totalPages - 1) setCurrentPage(currentPage + 1);
  };

  const originalImgUrl = `/api/preview/original/${jobId}/${currentPage}`;
  const redactedImgUrl = `/api/preview/redacted/${jobId}/${currentPage}`;

  return (
    <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Eye size={18} color="var(--accent-primary)" /> Document Side-by-Side Comparison
        </h3>

        {renderType === 'image' && totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              className="btn btn-outline btn-sm"
              onClick={prevPage}
              disabled={currentPage === 0}
            >
              <ChevronLeft size={16} /> Prev Page
            </button>

            <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              Page {currentPage + 1} / {totalPages}
            </span>

            <button
              className="btn btn-outline btn-sm"
              onClick={nextPage}
              disabled={currentPage >= totalPages - 1}
            >
              Next Page <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>

      <div className="comparison-layout">
        <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
          <DocumentViewer
            title="Original Document"
            renderType={renderType}
            imageSrc={originalImgUrl}
            textContent={originalText}
            pageNum={currentPage}
            totalPages={totalPages}
          />
        </div>

        <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
          <DocumentViewer
            title="Redacted Output"
            renderType={renderType}
            imageSrc={redactedImgUrl}
            textContent={redactedText}
            pageNum={currentPage}
            totalPages={totalPages}
          />
        </div>
      </div>
    </div>
  );
}
