import type { RenderStatus, SystemInfo } from '../types';

interface StatusBarProps {
  status: RenderStatus;
  systemInfo: SystemInfo | null;
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

export function StatusBar({ status, systemInfo, onRender, onStop, onLatexNotice }: StatusBarProps) {
  const isRendering = status === 'rendering';

  return (
    <div className="status-bar">
      <span className={`status-bar__text ${STATUS_CLASS[status]}`}>
        {STATUS_TEXT[status]}
      </span>

      {systemInfo && !systemInfo.latexOk && (
        <>
          <div className="status-bar__sep" />
          <button
            onClick={onLatexNotice}
            style={{
              background: 'transparent', border: 'none',
              color: 'var(--yellow)', fontSize: 11,
              cursor: 'pointer', padding: '0 6px', opacity: 0.85,
            }}
            title={`LaTeX not found: ${systemInfo.latexMissing.join(', ')} — click for install instructions`}
          >
            ⚠ LaTeX
          </button>
        </>
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
