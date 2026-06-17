import { useEffect, useRef, useState } from 'react';

interface NumInputProps {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number | string;
  /** Decimal places used when formatting the committed value. Omit for integers. */
  decimals?: number;
  className?: string;
  style?: React.CSSProperties;
  placeholder?: string;
}

const clamp = (v: number, min?: number, max?: number) => {
  if (min !== undefined && v < min) return min;
  if (max !== undefined && v > max) return max;
  return v;
};

const fmt = (v: number, decimals?: number) =>
  decimals === undefined ? String(v) : v.toFixed(decimals);

/**
 * Robust numeric input. Keeps a local text draft while focused so the user can
 * type freely ("", "-", "1.", "-0.05") without the value snapping or the cursor
 * jumping. Pushes live numeric updates as soon as the draft parses, and clamps +
 * formats only on blur / Enter. Re-syncs from the prop when not focused.
 */
export function NumInput({
  value, onChange, min, max, step, decimals, className, style, placeholder,
}: NumInputProps) {
  const [draft, setDraft] = useState(() => fmt(value, decimals));
  const focused = useRef(false);

  // Keep the displayed text in sync with external changes (slider drag, presets,
  // localStorage restore) while the user is not actively editing this field.
  useEffect(() => {
    if (!focused.current) setDraft(fmt(value, decimals));
  }, [value, decimals]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const text = e.target.value;
    setDraft(text);
    // Push through intermediate-but-parseable values so live previews track the
    // input, but don't reformat or clamp mid-edit (clamping happens on commit).
    const v = parseFloat(text);
    if (text.trim() !== '' && Number.isFinite(v)) onChange(v);
  }

  function commit() {
    focused.current = false;
    const v = parseFloat(draft);
    if (draft.trim() === '' || !Number.isFinite(v)) {
      // Unparseable / empty → revert to the last good value.
      setDraft(fmt(value, decimals));
      return;
    }
    const finalV = clamp(decimals !== undefined ? parseFloat(v.toFixed(decimals)) : v, min, max);
    onChange(finalV);
    setDraft(fmt(finalV, decimals));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
  }

  return (
    <input
      className={className}
      style={style}
      type="number"
      inputMode="decimal"
      min={min}
      max={max}
      step={step}
      value={draft}
      placeholder={placeholder}
      onFocus={() => { focused.current = true; }}
      onChange={handleChange}
      onBlur={commit}
      onKeyDown={handleKeyDown}
    />
  );
}
