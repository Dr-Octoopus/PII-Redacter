import React, { useState, useEffect } from 'react';
import { ShieldCheck, Cpu, Sun, Moon, Sparkles, Activity, FileCheck } from 'lucide-react';
import FileDropzone from './components/FileDropzone';
import ComparisonView from './components/ComparisonView';
import DetectionSummary from './components/DetectionSummary';
import DownloadBar from './components/DownloadBar';
import ThreeBackground from './components/ThreeBackground';
import ThreeControlsHUD from './components/ThreeControlsHUD';

export default function App() {
  const [jobData, setJobData] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('pii_theme') || 'dark';
  });

  // 3D HUD Controls State
  const [activePreset, setActivePreset] = useState('lattice');
  const [speedMultiplier, setSpeedMultiplier] = useState(1.0);
  const [shockwaveTrigger, setShockwaveTrigger] = useState(0);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('pii_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'dark' ? 'light' : 'dark'));
  };

  // Derive 3D WebGL background mode from application state
  const threeMode = isUploading ? 'scanning' : jobData ? 'secured' : 'idle';

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

  const triggerShockwave = () => {
    setShockwaveTrigger((prev) => prev + 1);
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh' }}>
      {/* 3D High-Performance WebGL Cyber Background */}
      <ThreeBackground
        theme={theme}
        mode={threeMode}
        preset={activePreset}
        speedMultiplier={speedMultiplier}
        shockwaveTrigger={shockwaveTrigger}
      />

      {/* Floating 3D Controls HUD Overlay */}
      <ThreeControlsHUD
        activePreset={activePreset}
        onPresetChange={setActivePreset}
        speedMultiplier={speedMultiplier}
        onSpeedChange={setSpeedMultiplier}
        onTriggerShockwave={triggerShockwave}
        theme={theme}
      />

      {/* App Header */}
      <header className="app-header">
        <div className="logo-container">
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <ShieldCheck size={28} color="var(--accent-primary)" />
            <span className="live-status-dot" title="Engine Active" />
          </div>
          <span className="brand-gradient-text">PII Redactor Engine</span>
          <span className="badge-trf">
            <Cpu size={13} />
            Transformer NER + Regex
          </span>
        </div>

        {/* Header Rightmost Menu & Theme Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div className="header-stats-pill" style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.785rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              <Activity size={14} color="var(--success)" />
              <span>Engine Ready</span>
            </div>
            <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.785rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              <FileCheck size={14} color="var(--accent-primary)" />
              <span>PDF • DOCX • XLSX • IMG</span>
            </div>
          </div>

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
        </div>
      </header>

      {/* Main Layout Container */}
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

