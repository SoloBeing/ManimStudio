import { useEffect, useRef, useState, type MouseEvent } from 'react';

interface BottomPanelProps {
  lines: string[];
  logHeight: number;
  onResizeStart: (e: MouseEvent<HTMLDivElement>) => void;
}

function lineClass(line: string): string {
  if (/\[SYNTAX ERROR\]|\[ERROR\]/.test(line)) return 'log-line log-line--error';
  if (/\[WARN\]/.test(line))  return 'log-line log-line--warn';
  if (/\[INFO\]/.test(line))  return 'log-line log-line--info';
  if (!line.trim())            return 'log-line log-line--dim';
  return 'log-line';
}

export function BottomPanel({ lines, logHeight, onResizeStart }: BottomPanelProps) {
  const [open, setOpen] = useState(true);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [lines, open]);

  return (
    <div className="bottom-panel">
      {open && (
        <div className="resize-handle resize-handle--horizontal" onMouseDown={onResizeStart} />
      )}
      <div className="bottom-panel__header" onClick={() => setOpen(o => !o)}>
        <span className="bottom-panel__title">Build Log</span>
        <span style={{ fontSize: 10, color: 'var(--dim)' }}>{lines.length} lines</span>
        <span className={`bottom-panel__arrow${open ? ' open' : ''}`}>▲</span>
      </div>
      {open && (
        <div className="bottom-panel__log" style={{ height: logHeight }} ref={logRef}>
          {lines.length === 0
            ? <div className="log-line log-line--dim">No output yet.</div>
            : lines.map((l, i) => (
                <div key={i} className={lineClass(l)}>{l || ' '}</div>
              ))
          }
        </div>
      )}
    </div>
  );
}
