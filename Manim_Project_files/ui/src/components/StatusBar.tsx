import type { RenderStatus, SystemInfo } from '../types';
import { Dropdown } from './shared/Dropdown';

interface StatusBarProps {
  status: RenderStatus;
  systemInfo: SystemInfo | null;
  quality: string;
  fps: string;
  opengl: boolean;
  outputDir: string;
  onQualityChange: (q: string) => void;
  onFpsChange: (f: string) => void;
  onOpenglChange: (v: boolean) => void;
  onBrowseOutput: () => void;
  onRender: () => void;
  onStop: () => void;
  onLatexNotice: () => void;
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
  status, systemInfo, quality, fps, opengl, outputDir,
  onQualityChange, onFpsChange, onOpenglChange, onBrowseOutput, onRender, onStop, onLatexNotice,
}: StatusBarProps) {
  const isRendering = status === 'rendering';
  const qualities = systemInfo?.qualities ?? ['Med  720p'];
  const fpsList   = systemInfo?.fpsList   ?? ['30'];
  const dirLabel  = outputDir ? outputDir.split(/[\\/]/).filter(Boolean).pop() ?? outputDir : '…';

  return (
    <div className="status-bar">
      <span className={`status-bar__text ${STATUS_CLASS[status]}`}>
        {STATUS_TEXT[status]}
      </span>

      <div className="status-bar__sep" />

      <Dropdown value={quality} options={qualities} onChange={onQualityChange} disabled={isRendering} />

      <Dropdown value={fps} options={fpsList} onChange={onFpsChange} disabled={isRendering}
        renderLabel={f => `${f} fps`} />

      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text)', cursor: 'pointer', userSelect: 'none' }}>
        <input type="checkbox" style={{ accentColor: 'var(--blue)' }}
          checked={opengl} disabled={isRendering}
          onChange={e => onOpenglChange(e.target.checked)} />
        OpenGL
      </label>

      <button
        onClick={onBrowseOutput}
        disabled={isRendering}
        title={outputDir || 'Select output folder'}
        style={{
          display: 'flex', alignItems: 'center', gap: 4,
          background: 'transparent', border: '1px solid var(--border)',
          borderRadius: 3, color: 'var(--text)', fontSize: 11,
          cursor: isRendering ? 'default' : 'pointer',
          padding: '2px 7px', maxWidth: 160, opacity: isRendering ? 0.5 : 1,
        }}
      >
        <span>📁</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {dirLabel}
        </span>
      </button>

      {systemInfo && !systemInfo.latexOk && (
        <button
          onClick={onLatexNotice}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--yellow)',
            fontSize: 11,
            cursor: 'pointer',
            padding: '0 6px',
            opacity: 0.85,
          }}
          title={`LaTeX not found: ${systemInfo.latexMissing.join(', ')} — click for install instructions`}
        >
          ⚠ LaTeX
        </button>
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
