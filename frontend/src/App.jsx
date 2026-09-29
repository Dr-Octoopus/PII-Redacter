import React, { useState, useEffect } from 'react';
import { ShieldCheck, Sun, Moon } from 'lucide-react';
import FileDropzone from './components/FileDropzone';
import ComparisonView from './components/ComparisonView';
import DetectionSummary from './components/DetectionSummary';
import DownloadBar from './components/DownloadBar';
import ThreeBackground from './components/ThreeBackground';

export default function App() {
  const [jobData, setJobData] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('pii_theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('pii_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'dark' ? 'light' : 'dark'));
  };

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
    <div style={{ position: 'relative', minHeight: '100vh' }}>
      {/* Sleek 3D Globe Background */}
      <ThreeBackground theme={theme} />

      {/* Clean & Glamorous Header */}
      <header className="app-header">
        <div className="logo-container">
          <ShieldCheck size={26} color="var(--accent-primary)" />
          <span className="brand-gradient-text">PII Redactor</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <>
              <Moon size={15} color="#818cf8" />
              <span>Dark</span>
            </>
          ) : (
            <>
              <Sun size={15} color="#f59e0b" />
              <span>Light</span>
            </>
          )}
          <div className="theme-toggle-track">
            <div className="theme-toggle-thumb" />
          </div>
        </button>
      </header>

      {/* Main Container */}
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
