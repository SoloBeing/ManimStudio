import { useRef, useState } from 'react';
import type { TextParams } from '../../types';
import { NumInput } from './NumInput';

const POSITIONS = [
  ['Top Left', 'top_left'], ['Top Center', 'top_center'], ['Top Right', 'top_right'],
  ['Center Left', 'center_left'], ['Center', 'center'], ['Center Right', 'center_right'],
  ['Bottom Left', 'bottom_left'], ['Bottom Center', 'bottom_center'],
  ['Bottom Right', 'bottom_right'], ['Free (X/Y)', 'free'],
];
const COLORS = [
  ['White', 'white'], ['Blue', 'blue'], ['Teal', 'teal'], ['Green', 'green'],
  ['Yellow', 'yellow'], ['Orange', 'orange'], ['Red', 'red'], ['Purple', 'purple'],
  ['Pink', 'pink'], ['Gold', 'gold'], ['Maroon', 'maroon'],
  ['Light Blue', 'light_blue'], ['Light Green', 'light_green'],
  ['Grey', 'grey'], ['Black', 'black'], ['Teal B', 'teal_b'],
];
const FONTS = [
  'Arial', 'DejaVu Sans', 'Liberation Sans', 'Noto Sans', 'Consolas',
  'Courier New', 'Georgia', 'Times New Roman', 'Verdana', 'Ubuntu',
  'Fira Code', 'JetBrains Mono',
];
const GRADIENTS = [
  ['None', 'none'], ['Red → Blue', 'red_blue'], ['Blue → Green', 'blue_green'],
  ['Gold → White', 'gold_white'], ['Teal → Yellow', 'teal_yellow'],
  ['Rainbow', 'rainbow'], ['Orange → Red', 'orange_red'],
];

const PRESET_XY: Record<string, [number, number]> = {
  top_left: [-5.8, 3.3], top_center: [0, 3.3], top_right: [5.8, 3.3],
  center_left: [-5.8, 0], center: [0, 0], center_right: [5.8, 0],
  bottom_left: [-5.8, -3.3], bottom_center: [0, -3.3], bottom_right: [5.8, -3.3],
  free: [0, 0],
};
const MW = 14.222, MH = 8.0;

function PositionPreview({
  mx, my, isFree, onDrag,
}: { mx: number; my: number; isFree: boolean; onDrag: (x: number, y: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const xPct = Math.max(0, Math.min(100, (mx / MW + 0.5) * 100));
  const yPct = Math.max(0, Math.min(100, (0.5 - my / MH) * 100));
  const accent = isFree ? '#33aaff' : '#2277aa';

  function calcPos(e: React.MouseEvent) {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const nx = Math.round(((px / r.width) - 0.5) * MW * 100) / 100;
    const ny = Math.round((0.5 - py / r.height) * MH * 100) / 100;
    onDrag(Math.max(-MW / 2, Math.min(MW / 2, nx)), Math.max(-MH / 2, Math.min(MH / 2, ny)));
  }

  return (
    <div
      ref={ref}
      className={`pos-preview${isFree ? ' pos-preview--free' : ''}`}
      onMouseDown={isFree ? calcPos : undefined}
      onMouseMove={isFree ? (e) => { if (e.buttons) calcPos(e); } : undefined}
    >
      {/* grid lines */}
      {[33.33, 66.66].map(p => (
        <div key={`v${p}`} style={{ position: 'absolute', left: `${p}%`, top: 0, bottom: 0, width: 1, background: '#1c2e40' }} />
      ))}
      {[33.33, 66.66].map(p => (
        <div key={`h${p}`} style={{ position: 'absolute', top: `${p}%`, left: 0, right: 0, height: 1, background: '#1c2e40' }} />
      ))}
      {/* crosshair */}
      <div style={{ position: 'absolute', top: `${yPct}%`, left: 0, right: 0, height: 1, background: accent, opacity: 0.7 }} />
      <div style={{ position: 'absolute', left: `${xPct}%`, top: 0, bottom: 0, width: 1, background: accent, opacity: 0.7 }} />
      {/* dot */}
      <div style={{
        position: 'absolute', left: `${xPct}%`, top: `${yPct}%`,
        transform: 'translate(-50%,-50%)', width: 8, height: 8,
        borderRadius: '50%', background: accent,
      }} />
    </div>
  );
}

interface TextControlsProps {
  value: TextParams;
  onChange: (v: TextParams) => void;
}

export function TextControls({ value, onChange }: TextControlsProps) {
  const [open, setOpen] = useState(false);
  const isFree = value.text_position === 'free';
  const hasGradient = value.gradient !== 'none';

  function set<K extends keyof TextParams>(key: K, v: TextParams[K]) {
    onChange({ ...value, [key]: v });
  }

  function handleDrag(x: number, y: number) {
    onChange({ ...value, x_offset: x, y_offset: y });
  }

  const previewX = isFree
    ? value.x_offset
    : (PRESET_XY[value.text_position]?.[0] ?? 0) + value.x_offset;
  const previewY = isFree
    ? value.y_offset
    : (PRESET_XY[value.text_position]?.[1] ?? 0) + value.y_offset;

  return (
    <div>
      <div className="sec-sep" />
      <div className="text-controls__toggle" onClick={() => setOpen(o => !o)}>
        <span className={`text-controls__arrow${open ? ' open' : ''}`}>▶</span>
        TEXT
      </div>

      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div className="field-row">
            <label>Label</label>
            <input className="app-input" placeholder="Custom label…"
              value={value.text_content}
              onChange={e => set('text_content', e.target.value)} />
          </div>
          {value.show_preset_labels && (
            <>
              <div className="field-row">
                <label>Title</label>
                <input className="app-input" placeholder="Override preset title…"
                  value={value.preset_title}
                  onChange={e => set('preset_title', e.target.value)} />
              </div>
              <div className="field-row">
                <label>Subtitle</label>
                <input className="app-input" placeholder="Where applicable…"
                  value={value.preset_subtitle}
                  onChange={e => set('preset_subtitle', e.target.value)} />
              </div>
            </>
          )}
          <div className="field-row">
            <label>Position</label>
            <select className="app-select" value={value.text_position}
              onChange={e => set('text_position', e.target.value)}>
              {POSITIONS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="field-row" style={{ opacity: hasGradient ? 0.4 : 1 }}>
            <label>Color</label>
            <select className="app-select" value={value.text_color}
              disabled={hasGradient}
              onChange={e => set('text_color', e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="field-row">
            <label>Font</label>
            <select className="app-select" value={value.text_font}
              onChange={e => set('text_font', e.target.value)}>
              {FONTS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div className="field-row">
            <label>Size</label>
            <NumInput className="knob__num" style={{ flex: 1, width: 'auto' }}
              min={8} max={72} decimals={0} value={value.text_font_size}
              onChange={v => set('text_font_size', v)} />
          </div>
          <div className="field-row">
            <label>Gradient</label>
            <select className="app-select" value={value.gradient}
              onChange={e => set('gradient', e.target.value)}>
              {GRADIENTS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="check-row">
            <label className="app-check">
              <input type="checkbox" checked={value.bold}
                onChange={e => set('bold', e.target.checked)} /> Bold
            </label>
            <label className="app-check">
              <input type="checkbox" checked={value.italic}
                onChange={e => set('italic', e.target.checked)} /> Italic
            </label>
            <label className="app-check">
              <input type="checkbox" checked={value.show_preset_labels}
                onChange={e => set('show_preset_labels', e.target.checked)} /> Preset Labels
            </label>
          </div>
          <div className="field-row">
            <label>Stroke W</label>
            <NumInput className="knob__num" style={{ flex: 1, width: 'auto' }}
              min={0} max={20} step={0.5} decimals={1} value={value.stroke_width}
              onChange={v => set('stroke_width', v)} />
          </div>
          <div className="field-row">
            <label>Stroke C</label>
            <select className="app-select" value={value.stroke_color}
              onChange={e => set('stroke_color', e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="field-row">
            <label>{isFree ? 'X Pos' : 'X Offset'}</label>
            <NumInput className="knob__num" style={{ flex: 1, width: 'auto' }}
              min={-8} max={8} step={0.1} decimals={1} value={value.x_offset}
              onChange={v => set('x_offset', v)} />
          </div>
          <div className="field-row">
            <label>{isFree ? 'Y Pos' : 'Y Offset'}</label>
            <NumInput className="knob__num" style={{ flex: 1, width: 'auto' }}
              min={-5} max={5} step={0.1} decimals={1} value={value.y_offset}
              onChange={v => set('y_offset', v)} />
          </div>
          <PositionPreview mx={previewX} my={previewY} isFree={isFree} onDrag={handleDrag} />
          <div className="pos-preview__hint">
            {isFree ? 'Drag crosshair to set position' : 'Switch to Free (X/Y) to drag'}
          </div>
        </div>
      )}
    </div>
  );
}
