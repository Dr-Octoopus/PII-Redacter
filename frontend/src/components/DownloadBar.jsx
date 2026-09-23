import React from 'react';
import { Download, FileJson, ArrowLeft } from 'lucide-react';

export default function DownloadBar({ jobId, filename, onReset }) {
  const handleDownloadRedacted = () => {
    window.open(`/api/download/${jobId}`, '_blank');
  };

  const handleDownloadReport = () => {
    window.open(`/api/download-report/${jobId}`, '_blank');
  };

  return (
    <div className="glass-card" style={{ padding: '1.35rem 1.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
      <button className="btn btn-outline" onClick={onReset}>
        <ArrowLeft size={17} /> Redact Another Document
      </button>

      <div style={{ display: 'flex', gap: '0.85rem', flexWrap: 'wrap' }}>
        <button className="btn btn-secondary" onClick={handleDownloadReport}>
          <FileJson size={17} color="var(--info)" /> Download JSON Audit Report
        </button>

        <button className="btn btn-primary" onClick={handleDownloadRedacted}>
          <Download size={17} /> Download Redacted File
        </button>
      </div>
    </div>
  );
}
