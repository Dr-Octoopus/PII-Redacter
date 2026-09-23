import React, { useState } from 'react';
import { BarChart3, Search, ShieldAlert, Cpu, Sparkles, CheckCircle } from 'lucide-react';

export default function DetectionSummary({ report }) {
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');

  if (!report) return null;

  const entities = report.entities || [];
  const summary = report.summary || {};

  const regexCount = entities.filter(e => e.detection_method === 'regex').length;
  const nerCount = entities.filter(e => e.detection_method === 'ner').length;
  const highConfCount = entities.filter(e => e.confidence >= 0.90).length;

  const filteredEntities = entities.filter(ent => {
    const matchesCategory = filter === 'ALL' || ent.category === filter;
    const matchesSearch = search === '' || ent.text.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categories = Object.keys(summary);

  return (
    <div className="glass-card" style={{ padding: '1.75rem', marginBottom: '2rem', position: 'relative', zIndex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.35rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
            <BarChart3 size={20} color="var(--accent-primary)" /> Detection & Classification Summary
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Comprehensive overview of identified PII entities, confidence ratings, and detection methods.
          </p>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary)' }}>
            <ShieldAlert size={24} />
          </div>
          <div>
            <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{entities.length}</div>
            <div className="stat-label">Total Entities</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'var(--info-bg)', color: 'var(--info)' }}>
            <Sparkles size={24} />
          </div>
          <div>
            <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{regexCount}</div>
            <div className="stat-label">Regex Matches</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(192, 132, 252, 0.15)', color: '#c084fc' }}>
            <Cpu size={24} />
          </div>
          <div>
            <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{nerCount}</div>
            <div className="stat-label">NER Model Hits</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
            <CheckCircle size={24} />
          </div>
          <div>
            <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{highConfCount}</div>
            <div className="stat-label">≥ 90% Confidence</div>
          </div>
        </div>
      </div>

      {/* Category Pills & Filters */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.15rem', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
          <button
            className={`btn btn-sm ${filter === 'ALL' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFilter('ALL')}
          >
            All ({entities.length})
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              className={`btn btn-sm ${filter === cat ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setFilter(cat)}
            >
              {cat} ({summary[cat].count})
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', minWidth: '250px' }}>
          <input
            type="text"
            placeholder="Search detected entities..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem 0.85rem 0.5rem 2.35rem',
              background: 'var(--input-bg)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              outline: 'none',
              transition: 'border-color var(--transition-fast)'
            }}
          />
          <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 10, top: 11 }} />
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto', maxHeight: '420px', overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
        <table className="summary-table">
          <thead>
            <tr>
              <th>Detected Entity Value</th>
              <th>Category</th>
              <th>Method</th>
              <th>Confidence Level</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntities.length > 0 ? (
              filteredEntities.map((ent, idx) => (
                <tr key={idx}>
                  <td>
                    <span className="redacted-entity-tag">
                      {ent.text}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-cat">{ent.category}</span>
                  </td>
                  <td>
                    <span className={`badge ${ent.detection_method === 'ner' ? 'badge-ner' : 'badge-regex'}`}>
                      {ent.detection_method.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div style={{
                        width: '70px',
                        height: '7px',
                        background: 'var(--border-subtle)',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${(ent.confidence * 100).toFixed(0)}%`,
                          height: '100%',
                          background: ent.confidence >= 0.90 ? 'var(--success)' : 'var(--warning)',
                          borderRadius: '4px',
                        }} />
                      </div>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {(ent.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                  No entities match the current search or category filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
