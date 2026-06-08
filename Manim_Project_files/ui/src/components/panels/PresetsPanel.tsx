import { useState } from 'react';
import type { Preset } from '../../types';

interface PresetsPanelProps {
  quality: string;
  format: string;
  fps: string;
  opengl: boolean;
  presets: Preset[];
  onApply: (p: Preset) => void;
  onSave: (name: string) => void;
  onDelete: (id: string) => void;
}

export function PresetsPanel({ quality, format, fps, opengl, presets, onApply, onSave, onDelete }: PresetsPanelProps) {
  const [newName, setNewName] = useState('');

  function handleSave() {
    const name = newName.trim();
    if (!name) return;
    onSave(name);
    setNewName('');
  }

  return (
    <div style={{ padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 20 }}>

      <section>
        <div style={headerStyle}>Save Current as Preset</div>
        <div style={{ fontSize: 11, color: 'var(--dim)', marginBottom: 8 }}>
          {quality} · {format.toUpperCase()} · {fps} fps{opengl ? ' · OpenGL' : ''}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            placeholder="Preset name…"
            style={{
              flex: 1, background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 3, color: 'var(--text)', fontSize: 12,
              padding: '4px 8px', outline: 'none',
            }}
          />
          <button
            onClick={handleSave}
            disabled={!newName.trim()}
            style={{
              background: 'var(--blue)', border: 'none', borderRadius: 3,
              color: '#fff', fontSize: 11, padding: '4px 12px', flexShrink: 0,
              cursor: newName.trim() ? 'pointer' : 'default',
              opacity: newName.trim() ? 1 : 0.4,
            }}
          >
            Save
          </button>
        </div>
      </section>

      <section>
        <div style={headerStyle}>Saved Presets</div>
        {presets.length === 0 ? (
          <div style={{ fontSize: 12, color: 'var(--dim)', fontStyle: 'italic' }}>
            No presets saved yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {presets.map(p => (
              <div key={p.id} style={{
                background: 'var(--bg)', border: '1px solid var(--border)',
                borderRadius: 4, padding: '8px 10px',
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 12, color: 'var(--bright)', fontWeight: 500,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {p.name}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--dim)', marginTop: 2 }}>
                    {p.quality}{p.format ? ` · ${p.format.toUpperCase()}` : ''} · {p.fps} fps{p.opengl ? ' · OpenGL' : ''}
                  </div>
                </div>
                <button onClick={() => onApply(p)} style={applyBtnStyle}>Apply</button>
                <button onClick={() => onDelete(p.id)} style={deleteBtnStyle}>✕</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

const headerStyle: React.CSSProperties = {
  fontSize: 10, color: 'var(--dim)', textTransform: 'uppercase',
  letterSpacing: 1, marginBottom: 10,
};

const applyBtnStyle: React.CSSProperties = {
  background: 'var(--green)', border: 'none', borderRadius: 3,
  color: '#fff', fontSize: 10, cursor: 'pointer',
  padding: '3px 9px', flexShrink: 0,
};

const deleteBtnStyle: React.CSSProperties = {
  background: 'transparent', border: '1px solid var(--border)',
  borderRadius: 3, color: 'var(--red)', fontSize: 10,
  cursor: 'pointer', padding: '3px 7px', flexShrink: 0,
};
