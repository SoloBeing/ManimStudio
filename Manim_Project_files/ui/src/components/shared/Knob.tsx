interface KnobProps {
  label: string;
  min: number;
  max: number;
  value: number;
  onChange: (v: number) => void;
  decimals?: number;
  step?: number;
}

export function Knob({ label, min, max, value, onChange, decimals = 2, step }: KnobProps) {
  const s = step ?? (decimals === 0 ? 1 : Math.pow(10, -decimals));

  function handleSlider(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(parseFloat(e.target.value));
  }

  function handleNum(e: React.ChangeEvent<HTMLInputElement>) {
    const v = parseFloat(e.target.value);
    if (!isNaN(v)) onChange(Math.max(min, Math.min(max, v)));
  }

  return (
    <div className="knob">
      <span className="knob__label">{label}</span>
      <input
        className="knob__slider"
        type="range"
        min={min}
        max={max}
        step={s}
        value={value}
        onChange={handleSlider}
      />
      <input
        className="knob__num"
        type="number"
        min={min}
        max={max}
        step={s}
        value={value.toFixed(decimals)}
        onChange={handleNum}
      />
    </div>
  );
}
