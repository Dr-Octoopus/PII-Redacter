import React, { useState } from 'react';
import { Sparkles, Sliders, Zap, Shield, Grid, Orbit, Eye, ChevronDown, ChevronUp } from 'lucide-react';

export default function ThreeControlsHUD({
  activePreset,
  onPresetChange,
  speedMultiplier,
  onSpeedChange,
  onTriggerShockwave,
  theme,
}) {
  const [isOpen, setIsOpen] = useState(true);

  const presets = [
    { id: 'lattice', label: 'Twin Cyber Cores', icon: Orbit },
    { id: 'vortex', label: 'Quantum Scan Vortex', icon: Zap },
    { id: 'shield', label: 'Holographic Shield', icon: Shield },
    { id: 'particles', label: 'Particle Constellation', icon: Grid },
  ];

  return (
    <div
      className="glass-card-interactive"
      style={{
        position: 'fixed',
        top: '88px',
        right: '24px',
        zIndex: 90,
        padding: isOpen ? '1rem 1.15rem' : '0.55rem 0.85rem',
        borderRadius: 'var(--radius-md)',
        background: 'var(--bg-glass)',
        backdropFilter: 'blur(18px)',
        WebkitBackdropFilter: 'blur(18px)',
        border: '1px solid var(--border-active)',
        boxShadow: 'var(--shadow-glow)',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        maxWidth: '300px',
        userSelect: 'none',
      }}
    >
      {/* Header Bar */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={16} color="var(--accent-primary)" />
          <span style={{ fontSize: '0.825rem', fontWeight: 700, letterSpacing: '0.02em', color: 'var(--text-primary)' }}>
            3D WebGL HUD
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span className="live-status-dot" style={{ position: 'relative', top: 'auto', right: 'auto' }} />
          {isOpen ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </div>
      </div>

      {/* Expanded Controls Panel */}
      {isOpen && (
        <div style={{ marginTop: '0.85rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border-subtle)' }}>
          {/* Preset Buttons */}
          <label style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem', display: 'block' }}>
            3D Scene Presets
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.45rem', marginBottom: '0.85rem' }}>
            {presets.map((p) => {
              const IconComp = p.icon;
              const isActive = activePreset === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onPresetChange(p.id)}
                  className={`btn btn-sm ${isActive ? 'btn-primary' : 'btn-outline'}`}
                  style={{
                    padding: '0.35rem 0.55rem',
                    fontSize: '0.735rem',
                    justifyContent: 'flex-start',
                    gap: '0.35rem',
                    width: '100%',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <IconComp size={13} color={isActive ? '#ffffff' : 'var(--accent-primary)'} />
                  <span>{p.label}</span>
                </button>
              );
            })}
          </div>

          {/* Speed Slider */}
          <div style={{ marginBottom: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '0.35rem' }}>
              <span>Animation Speed</span>
              <span style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{speedMultiplier}x</span>
            </div>
            <input
              type="range"
              min="0.2"
              max="3.0"
              step="0.1"
              value={speedMultiplier}
              onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
              style={{
                width: '100%',
                accentColor: 'var(--accent-primary)',
                cursor: 'pointer',
              }}
            />
          </div>

          {/* Impulse Action Button */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onTriggerShockwave}
            style={{ width: '100%', justifyContent: 'center', gap: '0.45rem', fontSize: '0.765rem' }}
          >
            <Zap size={14} color="var(--warning)" /> Ignite Energy Shockwave
          </button>
        </div>
      )}
    </div>
  );
}
