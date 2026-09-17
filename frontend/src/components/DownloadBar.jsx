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
    <div className="glass-card" style={{ padding: '1.25rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <button className="btn btn-outline" onClick={onReset}>
        <ArrowLeft size={16} /> Redact Another Document
      </button>

      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button className="btn btn-secondary" onClick={handleDownloadReport}>
          <FileJson size={16} color="#38bdf8" /> Download JSON Report
        </button>

        <button className="btn btn-primary" onClick={handleDownloadRedacted}>
          <Download size={16} /> Download Redacted File
        </button>
      </div>
    </div>
  );
}
