import React, { useState } from 'react';
import { Upload, CheckSquare, Square, Shield, Play, FileText, CheckCircle2 } from 'lucide-react';

const CATEGORIES = [
  { id: 'EMAIL', name: 'Email Address' },
  { id: 'PAN_NUMBER', name: 'PAN Number' },
  { id: 'PHONE_NUMBER', name: 'Phone Number' },
  { id: 'DATE_OF_BIRTH', name: 'Date of Birth' },
  { id: 'IP_ADDRESS', name: 'IP Address' },
  { id: 'AADHAAR_NUMBER', name: 'Aadhaar Number' },
  { id: 'CREDIT_CARD', name: 'Credit Card' },
  { id: 'PINCODE', name: 'Pincode' },
  { id: 'BANK_ACCOUNT_NUMBER', name: 'Bank Account' },
  { id: 'IFSC_CODE', name: 'IFSC Code' },
  { id: 'GSTIN', name: 'GSTIN' },
  { id: 'PERSON_NAME', name: 'Person Name (NER)' },
  { id: 'LOCATION', name: 'Location (NER)' },
  { id: 'ORGANIZATION', name: 'Organization (NER)' },
];

export default function FileDropzone({ onUpload, isUploading, error }) {
  const [selectedCategories, setSelectedCategories] = useState(CATEGORIES.map(c => c.id));
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const toggleCategory = (catId) => {
    if (selectedCategories.includes(catId)) {
      setSelectedCategories(selectedCategories.filter(id => id !== catId));
    } else {
      setSelectedCategories([...selectedCategories, catId]);
    }
  };

  const selectAll = () => setSelectedCategories(CATEGORIES.map(c => c.id));
  const deselectAll = () => setSelectedCategories([]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleSubmit = () => {
    if (!selectedFile) return;
    onUpload(selectedFile, selectedCategories);
  };

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto', position: 'relative', zIndex: 1 }}>
      <div className="glass-card" style={{ padding: '2.25rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '0.4rem' }}>
            PII Redaction System
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Upload a document to detect and mask sensitive PII entities.
          </p>
        </div>

        {/* Drag & Drop Box */}
        <div
          className={`dropzone-container ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-upload-input').click()}
        >
          <input
            id="file-upload-input"
            type="file"
            accept=".pdf,.docx,.xlsx,.txt"
            onChange={handleChange}
            style={{ display: 'none' }}
          />

          <div className="icon-wrapper">
            {selectedFile ? <FileText size={28} color="#818cf8" /> : <Upload size={28} />}
          </div>

          {selectedFile ? (
            <div>
              <p style={{ fontWeight: 700, fontSize: '1.05rem', color: '#c7d2fe', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
                <CheckCircle2 size={18} color="#10b981" /> {selectedFile.name}
              </p>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Click to choose a different file
              </p>
            </div>
          ) : (
            <div>
              <p style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.3rem' }}>
                Drop document here or click to select
              </p>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                Supported: <span style={{ color: '#818cf8', fontWeight: 600 }}>PDF, DOCX, XLSX, TXT</span>
              </p>
            </div>
          )}
        </div>

        {error && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem 1rem',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-sm)',
            color: '#fca5a5',
            fontSize: '0.85rem'
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Categories Selection */}
        <div style={{ marginTop: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <label style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Shield size={16} color="var(--accent-primary)" /> Target PII Categories ({selectedCategories.length}/{CATEGORIES.length})
            </label>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button type="button" className="btn btn-outline btn-sm" onClick={selectAll}>Select All</button>
              <button type="button" className="btn btn-outline btn-sm" onClick={deselectAll}>Clear</button>
            </div>
          </div>

          <div className="category-grid">
            {CATEGORIES.map((cat) => {
              const isSelected = selectedCategories.includes(cat.id);
              return (
                <div
                  key={cat.id}
                  className={`category-chip ${isSelected ? 'selected' : ''}`}
                  onClick={() => toggleCategory(cat.id)}
                >
                  {isSelected ? <CheckSquare size={15} color="#818cf8" /> : <Square size={15} color="var(--text-muted)" />}
                  <span>{cat.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Button */}
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '0.85rem 1.5rem', fontSize: '0.925rem', borderRadius: 'var(--radius-sm)' }}
            disabled={!selectedFile || isUploading}
            onClick={handleSubmit}
          >
            {isUploading ? (
              <>
                <div className="spinner" />
                <span>Processing Document...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Process Document</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

