import React, { useState } from 'react';
import { Upload, CheckSquare, Square, Shield, Play, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

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
  { id: 'URL', name: 'Website / URL' },
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
    <div style={{ maxWidth: '860px', margin: '0 auto', position: 'relative', zIndex: 1 }}>
      <div className="glass-card" style={{ padding: '2.5rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2.25rem' }}>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.025em', marginBottom: '0.4rem' }}>
            Automated PII Detection & Redaction
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem', maxWidth: '560px', margin: '0 auto' }}>
            Upload sensitive documents or images to automatically identify, catalog, and redact PII using Regex pattern matchers & Transformer NER models.
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
            accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg,.bmp,.tif,.tiff"
            onChange={handleChange}
            style={{ display: 'none' }}
          />

          <div className="icon-wrapper">
            {selectedFile ? <FileText size={32} /> : <Upload size={32} />}
          </div>

          {selectedFile ? (
            <div>
              <p style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={20} color="var(--success)" /> {selectedFile.name}
              </p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Click to choose a different file
              </p>
            </div>
          ) : (
            <div>
              <p style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '0.4rem' }}>
                Drop your document or image here, or click to browse
              </p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Supported formats: <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>PDF, DOCX, XLSX, TXT, Images (PNG, JPG, BMP, TIFF)</span>
              </p>
            </div>
          )}
        </div>

        {error && (
          <div style={{
            marginTop: '1.25rem',
            padding: '0.85rem 1.15rem',
            background: 'var(--danger-bg)',
            border: '1px solid var(--danger)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--danger)',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* Target Categories Selection */}
        <div style={{ marginTop: '2.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
            <label style={{ fontWeight: 700, fontSize: '0.925rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <Shield size={17} color="var(--accent-primary)" /> Target PII Categories ({selectedCategories.length}/{CATEGORIES.length})
            </label>
            <div style={{ display: 'flex', gap: '0.45rem' }}>
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
                  {isSelected ? (
                    <CheckSquare size={16} color="var(--accent-primary)" />
                  ) : (
                    <Square size={16} color="var(--text-muted)" />
                  )}
                  <span>{cat.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Process Button */}
        <div style={{ marginTop: '2.25rem', textAlign: 'center' }}>
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '0.9rem 1.75rem', fontSize: '0.95rem', borderRadius: 'var(--radius-sm)' }}
            disabled={!selectedFile || isUploading}
            onClick={handleSubmit}
          >
            {isUploading ? (
              <>
                <div className="spinner" />
                <span>Processing Document & Masking Entities...</span>
              </>
            ) : (
              <>
                <Play size={17} />
                <span>Redact Document</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
