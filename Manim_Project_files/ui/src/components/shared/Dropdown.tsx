import { useEffect, useRef, useState } from 'react';

interface DropdownProps {
  value: string;
  options: string[];
  onChange: (v: string) => void;
  disabled?: boolean;
  renderLabel?: (v: string) => string;
  direction?: 'up' | 'down';
}

export function Dropdown({ value, options, onChange, disabled, renderLabel, direction = 'up' }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onOutsideClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onOutsideClick);
    return () => document.removeEventListener('mousedown', onOutsideClick);
  }, [open]);

  const label = renderLabel ? renderLabel(value) : value;

  return (
    <div ref={ref} style={{ position: 'relative', flexShrink: 0 }}>
      <button
        disabled={disabled}
        onMouseDown={() => !disabled && setOpen(o => !o)}
        style={{
          background: 'transparent',
          border: `1px solid ${open ? 'var(--blue)' : 'var(--accent-border)'}`,
          color: 'var(--text)',
          borderRadius: 4,
          padding: '2px 6px',
          fontSize: 11,
          fontFamily: 'inherit',
          cursor: disabled ? 'default' : 'pointer',
          outline: 'none',
          opacity: disabled ? 0.5 : 1,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          whiteSpace: 'nowrap',
          userSelect: 'none',
        }}
      >
        {label}
        <span style={{ fontSize: 8, opacity: 0.5, marginLeft: 2 }}>▾</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          ...(direction === 'up'
            ? { bottom: 'calc(100% + 4px)', boxShadow: '0 -4px 16px rgba(0,0,0,0.5)' }
            : { top: 'calc(100% + 4px)',    boxShadow: '0  4px 16px rgba(0,0,0,0.5)' }),
          left: 0,
          background: 'var(--panel)',
          border: '1px solid var(--accent-border)',
          borderRadius: 4,
          zIndex: 9999,
          minWidth: '100%',
          overflow: 'hidden',
        }}>
          {options.map(opt => (
            <div
              key={opt}
              onMouseDown={() => { onChange(opt); setOpen(false); }}
              style={{
                padding: '5px 10px',
                fontSize: 11,
                color: opt === value ? 'var(--blue)' : 'var(--text)',
                background: opt === value ? 'var(--active)' : 'transparent',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                userSelect: 'none',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'var(--hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = opt === value ? 'var(--active)' : 'transparent'; }}
            >
              {renderLabel ? renderLabel(opt) : opt}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
