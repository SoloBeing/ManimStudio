import { NumInput } from './NumInput';

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
      <NumInput
        className="knob__num"
        min={min}
        max={max}
        step={s}
        decimals={decimals}
        value={value}
        onChange={onChange}
      />
    </div>
  );
}
