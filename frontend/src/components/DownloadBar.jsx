import React from 'react';
import { Download, FileJson, ArrowLeft } from 'lucide-react';

export default function DownloadBar({ jobId, filename, onReset }) {
  const triggerDownload = (url, defaultName) => {
    const link = document.createElement('a');
    link.href = url;
    if (defaultName) {
      link.setAttribute('download', defaultName);
    }
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadRedacted = () => {
    triggerDownload(`/api/download/${jobId}`, filename ? `redacted_${filename}` : undefined);
  };

  const handleDownloadReport = () => {
    triggerDownload(`/api/download-report/${jobId}`, `pii_redaction_report_${jobId?.slice(0, 8)}.json`);
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
