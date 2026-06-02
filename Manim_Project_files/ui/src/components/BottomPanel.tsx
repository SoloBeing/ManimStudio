import { memo, useEffect, useRef, useState, type MouseEvent } from 'react';

interface BottomPanelProps {
  lines: string[];
  logHeight: number;
  onResizeStart: (e: MouseEvent<HTMLDivElement>) => void;
}

// Classifying a line is a handful of regex tests. The same line content
// reappears across polls as the 500-line window shifts, so memoize the result
// keyed by line text — turns the per-render regex pass into O(1) lookups.
const _classCache = new Map<string, string>();

function lineClass(line: string): string {
  const cached = _classCache.get(line);
  if (cached !== undefined) return cached;
  let cls: string;
  if (/\[SYNTAX ERROR\]|\[ERROR\]/.test(line)) cls = 'log-line log-line--error';
  else if (/\[WARN\]/.test(line)) cls = 'log-line log-line--warn';
  else if (/\[INFO\]/.test(line)) cls = 'log-line log-line--info';
  else if (!line.trim())          cls = 'log-line log-line--dim';
  else                            cls = 'log-line';
  // Bound the cache so a very long, all-unique log can't grow it without limit.
  if (_classCache.size > 2000) _classCache.clear();
  _classCache.set(line, cls);
  return cls;
}

// Memoized row: when the log is below the 500-line cap (the common case) the
// content at a given index is stable across polls, so React skips re-rendering
// every existing row and only mounts the newly appended ones.
const LogLine = memo(function LogLine({ text }: { text: string }) {
  return <div className={lineClass(text)}>{text || ' '}</div>;
});

export const BottomPanel = memo(function BottomPanel({ lines, logHeight, onResizeStart }: BottomPanelProps) {
  const [open, setOpen] = useState(true);
  const logRef = useRef<HTMLDivElement>(null);

  // requestAnimationFrame defers the scroll until after the browser paints,
  // avoiding a forced synchronous layout reflow on every log line addition.
  useEffect(() => {
    if (!open || !logRef.current) return;
    const el = logRef.current;
    const id = requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
    return () => cancelAnimationFrame(id);
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
            : lines.map((l, i) => <LogLine key={i} text={l} />)
          }
        </div>
      )}
    </div>
  );
});
