import type { ReactNode } from 'react';
import type { SystemInfo } from '../../types';
import { Dropdown } from '../shared/Dropdown';

export function loadStoredSettings(): { quality?: string; fps?: string; opengl?: boolean } {
  try {
    return JSON.parse(localStorage.getItem('manim_settings') ?? '{}');
  } catch {
    return {};
  }
}

interface SettingsPanelProps {
  systemInfo: SystemInfo | null;
  quality: string;
  fps: string;
  opengl: boolean;
  outputDir: string;
  onQualityChange: (q: string) => void;
  onFpsChange: (f: string) => void;
  onOpenglChange: (v: boolean) => void;
  onBrowseOutput: () => void;
}

export function SettingsPanel({
  systemInfo, quality, fps, opengl, outputDir,
  onQualityChange, onFpsChange, onOpenglChange, onBrowseOutput,
}: SettingsPanelProps) {
  const qualities = systemInfo?.qualities ?? [];
  const fpsList   = systemInfo?.fpsList   ?? [];

  return (
    <div style={{ padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 20 }}>

      <section>
        <SectionHeader>Render Defaults</SectionHeader>
        <Row label="Quality">
          <Dropdown value={quality} options={qualities} onChange={onQualityChange} direction="down" />
        </Row>
        <Row label="FPS">
          <Dropdown value={fps} options={fpsList} onChange={onFpsChange} renderLabel={f => `${f} fps`} direction="down" />
        </Row>
        <Row label="OpenGL">
          <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={opengl}
              onChange={e => onOpenglChange(e.target.checked)}
              style={{ accentColor: 'var(--blue)', width: 13, height: 13, cursor: 'pointer' }}
            />
            <span style={{ fontSize: 12, color: 'var(--text)' }}>Enable OpenGL renderer</span>
          </label>
        </Row>
      </section>

      <section>
        <SectionHeader>Output</SectionHeader>
        <Row label="Directory">
          <div style={{ display: 'flex', gap: 6, width: '100%' }}>
            <span style={{
              flex: 1, fontSize: 11, color: 'var(--text)',
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 3, padding: '3px 7px',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {outputDir || '—'}
            </span>
            <button onClick={onBrowseOutput} style={btnStyle}>Browse</button>
          </div>
        </Row>
      </section>

      <div style={{ fontSize: 11, color: 'var(--dim)', lineHeight: 1.5, marginTop: 4 }}>
        Changes apply immediately and persist across sessions.
      </div>
    </div>
  );
}

function SectionHeader({ children }: { children: ReactNode }) {
  return (
    <div style={{
      fontSize: 10, color: 'var(--dim)', textTransform: 'uppercase',
      letterSpacing: 1, marginBottom: 12,
    }}>
      {children}
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
      <span style={{ fontSize: 11, color: 'var(--dim)', width: 68, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: 'var(--panel)', border: '1px solid var(--border)',
  borderRadius: 3, color: 'var(--text)', fontSize: 11,
  cursor: 'pointer', padding: '3px 9px', flexShrink: 0,
};
