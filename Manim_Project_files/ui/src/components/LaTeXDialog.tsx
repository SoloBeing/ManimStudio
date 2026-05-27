import { useState } from 'react';

interface LaTeXDialogProps {
  missing: string[];
  installCmd: string;
  withDontShow: boolean;
  onDismiss: (dontShowAgain: boolean) => void;
}

export function LaTeXDialog({ missing, installCmd, withDontShow, onDismiss }: LaTeXDialogProps) {
  const [dontShow, setDontShow] = useState(false);
  return (
    <div className="close-dialog__overlay">
      <div className="close-dialog" style={{ maxWidth: 480 }}>
        <div className="close-dialog__title">LaTeX Not Found</div>
        <div className="close-dialog__body" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <p style={{ margin: 0 }}>
            <strong style={{ color: 'var(--yellow)' }}>{missing.join(', ')}</strong> not found on PATH.
          </p>
          <p style={{ margin: 0 }}>
            <code>Text()</code> animations work fine without it — LaTeX is only needed
            for <code>MathTex()</code> and <code>Tex()</code> objects.
          </p>
          <p style={{ margin: 0 }}>Install <strong>TinyTeX</strong> to enable math rendering:</p>
          <div style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            padding: '6px 10px',
            fontFamily: 'monospace',
            fontSize: 11,
            color: 'var(--green)',
            wordBreak: 'break-all',
            userSelect: 'text',
          }}>
            {installCmd}
          </div>
        </div>
        {withDontShow && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--dim)', cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox"
              checked={dontShow} onChange={e => setDontShow(e.target.checked)} />
            Don't show this again
          </label>
        )}
        <div className="close-dialog__actions">
          <button className="btn btn--cancel" onClick={() => onDismiss(dontShow)}>OK</button>
        </div>
      </div>
    </div>
  );
}
