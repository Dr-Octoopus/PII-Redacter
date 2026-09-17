import React, { useState } from 'react';
import { ShieldCheck, Cpu } from 'lucide-react';
import FileDropzone from './components/FileDropzone';
import ComparisonView from './components/ComparisonView';
import DetectionSummary from './components/DetectionSummary';
import DownloadBar from './components/DownloadBar';
import ThreeBackground from './components/ThreeBackground';

export default function App() {
  const [jobData, setJobData] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleUpload = async (file, categories) => {
    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    if (categories && categories.length > 0) {
      formData.append('include', categories.join(','));
    }

    try {
      const response = await fetch('/api/redact', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Processing failed with status ${response.status}`);
      }

      const data = await response.json();
      setJobData(data);
    } catch (err) {
      setError(err.message || 'An error occurred during document processing.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setJobData(null);
    setError(null);
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh', background: 'var(--bg-dark)' }}>
      {/* 3D Three.js Interactive Particle Background */}
      <ThreeBackground />

      {/* App Header */}
      <header className="app-header" style={{ position: 'relative', zIndex: 10 }}>
        <div className="logo-container">
          <ShieldCheck size={24} color="#6366f1" />
          <span>PII Redactor Engine</span>
          <span className="badge-trf">
            <Cpu size={12} style={{ marginRight: 4, display: 'inline' }} />
            Transformer NER
          </span>
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Secure Document Processing
        </div>
      </header>

      {/* Main Layout */}
      <main className="main-container" style={{ position: 'relative', zIndex: 1 }}>
        {!jobData ? (
          <FileDropzone
            onUpload={handleUpload}
            isUploading={isUploading}
            error={error}
          />
        ) : (
          <div>
            <ComparisonView
              jobId={jobData.job_id}
              renderType={jobData.render_type}
              totalPages={jobData.original_pages}
              originalText={jobData.original_text}
              redactedText={jobData.redacted_text}
            />

            <DetectionSummary report={jobData.report} />

            <DownloadBar
              jobId={jobData.job_id}
              filename={jobData.filename}
              onReset={handleReset}
            />
          </div>
        )}
      </main>
    </div>
  );
}
