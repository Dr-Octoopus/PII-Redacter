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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart3 size={18} color="var(--accent-primary)" /> Detection Report
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Summary of identified PII entities and confidence scores.
          </p>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(99, 102, 241, 0.12)', color: '#818cf8' }}>
            <ShieldAlert size={22} />
          </div>
          <div>
            <div className="stat-value" style={{ color: '#c7d2fe' }}>{entities.length}</div>
            <div className="stat-label">Total Entities</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(56, 189, 248, 0.12)', color: '#38bdf8' }}>
            <Sparkles size={22} />
          </div>
          <div>
            <div className="stat-value" style={{ color: '#7dd3fc' }}>{regexCount}</div>
            <div className="stat-label">Regex Hits</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(192, 132, 252, 0.12)', color: '#c084fc' }}>
            <Cpu size={22} />
          </div>
          <div>
            <div className="stat-value" style={{ color: '#e9d5ff' }}>{nerCount}</div>
            <div className="stat-label">NER Hits</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-box" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#34d399' }}>
            <CheckCircle size={22} />
          </div>
          <div>
            <div className="stat-value" style={{ color: '#6ee7b7' }}>{highConfCount}</div>
            <div className="stat-label">≥ 90% Confidence</div>
          </div>
        </div>
      </div>

      {/* Category Pills & Filters */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
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

        <div style={{ position: 'relative', minWidth: '240px' }}>
          <input
            type="text"
            placeholder="Search entities..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem 0.85rem 0.45rem 2.25rem',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              fontSize: '0.825rem',
              outline: 'none',
            }}
          />
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: 10, top: 10 }} />
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto', maxHeight: '380px', overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
        <table className="summary-table">
          <thead>
            <tr>
              <th>Detected Entity</th>
              <th>Category</th>
              <th>Method</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntities.length > 0 ? (
              filteredEntities.map((ent, idx) => (
                <tr key={idx}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#fca5a5' }}>
                    {ent.text}
                  </td>
                  <td>
                    <span className="badge badge-cat">{ent.category}</span>
                  </td>
                  <td>
                    <span className={`badge ${ent.detection_method === 'ner' ? 'badge-ner' : 'badge-regex'}`}>
                      {ent.detection_method.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.825rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <div style={{
                        width: '60px',
                        height: '6px',
                        background: 'rgba(255,255,255,0.1)',
                        borderRadius: '3px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${(ent.confidence * 100).toFixed(0)}%`,
                          height: '100%',
                          background: ent.confidence >= 0.90 ? 'var(--success)' : 'var(--warning)',
                        }} />
                      </div>
                      <span>{(ent.confidence * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No entities match the selected filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

