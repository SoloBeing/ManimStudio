import type { RenderStatus, SystemInfo } from '../types';

interface StatusBarProps {
  status: RenderStatus;
  systemInfo: SystemInfo | null;
  quality: string;
  fps: string;
  opengl: boolean;
  onQualityChange: (q: string) => void;
  onFpsChange: (f: string) => void;
  onOpenglChange: (v: boolean) => void;
  onRender: () => void;
  onStop: () => void;
}

const STATUS_TEXT: Record<RenderStatus, string> = {
  idle:      'Ready',
  rendering: 'Rendering…',
  done:      'Done — save or discard',
  error:     'Render failed',
  stopped:   'Stopped',
};

const STATUS_CLASS: Record<RenderStatus, string> = {
  idle:      '',
  rendering: 'status-bar__text--rendering',
  done:      'status-bar__text--done',
  error:     'status-bar__text--error',
  stopped:   '',
};

export function StatusBar({
  status, systemInfo, quality, fps, opengl,
  onQualityChange, onFpsChange, onOpenglChange, onRender, onStop,
}: StatusBarProps) {
  const isRendering = status === 'rendering';
  const qualities = systemInfo?.qualities ?? ['Med  720p'];
  const fpsList   = systemInfo?.fpsList   ?? ['30'];

  return (
    <div className="status-bar">
      <span className={`status-bar__text ${STATUS_CLASS[status]}`}>
        {STATUS_TEXT[status]}
      </span>

      <div className="status-bar__sep" />

      <select className="status-bar__select" value={quality}
        onChange={e => onQualityChange(e.target.value)} disabled={isRendering}>
        {qualities.map(q => <option key={q}>{q}</option>)}
      </select>

      <select className="status-bar__select" value={fps}
        onChange={e => onFpsChange(e.target.value)} disabled={isRendering}>
        {fpsList.map(f => <option key={f}>{f} fps</option>)}
      </select>

      {systemInfo?.openglOk && (
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text)', cursor: 'pointer', userSelect: 'none' }}>
          <input type="checkbox" style={{ accentColor: 'var(--blue)' }}
            checked={opengl} disabled={isRendering}
            onChange={e => onOpenglChange(e.target.checked)} />
          OpenGL
        </label>
      )}

      <div className="status-bar__sep" />

      <button className="btn btn--stop" disabled={!isRendering} onClick={onStop}>
        ◼ Stop
      </button>
      <button className="btn btn--primary" disabled={isRendering} onClick={onRender}>
        ▶ Render
      </button>
    </div>
  );
}
