import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface Curve { expr: string; color: string; label: string; style: string; width: string }

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];

const PRESETS: [string, string][] = [
  ['Preset…', ''],
  ['x²', 'x^2'], ['x³', 'x^3'], ['eˣ', 'exp(x)'], ['ln(x)', 'log(x)'],
  ['|x|', 'abs(x)'], ['√x', 'sqrt(x)'], ['1/x', '1/x'], ['sin(x)', 'sin(x)'],
];

const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

const DEFAULT_CURVES: Curve[] = [
  { expr: 'x^2', color: 'blue', label: 'f', style: 'solid', width: '2.5' },
];

export function FunctionGraphPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [curves, setCurves]         = useState<Curve[]>(DEFAULT_CURVES);
  const [xMin, setXMin]             = useState(-5);
  const [xMax, setXMax]             = useState(5);
  const [yMin, setYMin]             = useState(-4);
  const [yMax, setYMax]             = useState(4);
  const [xStep, setXStep]           = useState(1);
  const [yStep, setYStep]           = useState(1);
  const [showGrid, setShowGrid]     = useState(false);
  const [zoom, setZoom]             = useState(1.0);
  const [anim, setAnim]             = useState('Create');
  const [axisLabelX, setAxisLabelX] = useState('x');
  const [axisLabelY, setAxisLabelY] = useState('y');
  const [title, setTitle]           = useState('');

  function updateCurve(i: number, field: keyof Curve, val: string) {
    setCurves(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: val } : c));
  }
  function addCurve() {
    if (curves.length >= 4) return;
    const defaults = ['blue', 'red', 'green', 'yellow'];
    setCurves(prev => [...prev, { expr: '', color: defaults[prev.length % 4], label: '', style: 'solid', width: '2.5' }]);
  }
  function removeCurve(i: number) {
    if (curves.length <= 1) return;
    setCurves(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'funcgraph',
      params: {
        curves: curves.map(c => ({
          expr: c.expr, color: c.color, label: c.label,
          style: c.style, width: parseFloat(c.width) || 2.5,
        })),
        x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax,
        x_step: xStep, y_step: yStep,
        show_grid: showGrid, cam_zoom: zoom,
        anim,
        axis_label_x: axisLabelX, axis_label_y: axisLabelY, title,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Curves (up to 4)</div>
      {curves.map((c, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
            <select
              className="app-select"
              style={{ width: 70 }}
              value=""
              onChange={e => { if (e.target.value) updateCurve(i, 'expr', e.target.value); }}
            >
              {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
            </select>
            <input
              className="app-input"
              style={{ flex: 1 }}
              value={c.expr}
              onChange={e => updateCurve(i, 'expr', e.target.value.slice(0, 120))}
              placeholder="f(x), e.g. sin(x) + x^2"
            />
            <button
              className="mode-toggle__btn"
              style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
              onClick={() => removeCurve(i)}
              title="Remove curve"
            >×</button>
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <select className="app-select" style={{ flex: 1 }} value={c.color}
              onChange={e => updateCurve(i, 'color', e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <select className="app-select" style={{ width: 76 }} value={c.style}
              onChange={e => updateCurve(i, 'style', e.target.value)}>
              <option value="solid">Solid</option>
              <option value="dashed">Dashed</option>
            </select>
            <input
              className="knob__num"
              style={{ width: 44, textAlign: 'center' }}
              value={c.label}
              onChange={e => updateCurve(i, 'label', e.target.value.slice(0, 12))}
              placeholder="lbl"
            />
          </div>
          <Knob label="Width" min={0.5} max={8} value={parseFloat(c.width) || 2.5}
            onChange={v => updateCurve(i, 'width', String(v))} decimals={1} step={0.5} />
        </div>
      ))}
      {curves.length < 4 && (
        <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addCurve}>
          + Add Curve
        </button>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Axes</div>
      <Knob label="X Min"  min={-50} max={0}  value={xMin}  onChange={v => setXMin(Math.round(v))}  decimals={0} step={1} />
      <Knob label="X Max"  min={1}   max={50} value={xMax}  onChange={v => setXMax(Math.round(v))}  decimals={0} step={1} />
      <Knob label="Y Min"  min={-50} max={0}  value={yMin}  onChange={v => setYMin(Math.round(v))}  decimals={0} step={1} />
      <Knob label="Y Max"  min={1}   max={50} value={yMax}  onChange={v => setYMax(Math.round(v))}  decimals={0} step={1} />
      <Knob label="X Step" min={0.1} max={10} value={xStep} onChange={setXStep} decimals={1} step={0.5} />
      <Knob label="Y Step" min={0.1} max={10} value={yStep} onChange={setYStep} decimals={1} step={0.5} />
      <Knob label="Zoom"   min={0.3} max={3}  value={zoom}  onChange={setZoom}  decimals={2} step={0.05} />
      <div className="check-row">
        <label className="app-check">
          <input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} /> Grid
        </label>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelX} onChange={e => setAxisLabelX(e.target.value.slice(0, 24))} placeholder="X axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelY} onChange={e => setAxisLabelY(e.target.value.slice(0, 24))} placeholder="Y axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Animation</div>
      <select className="app-select" style={{ width: '100%' }} value={anim} onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(a => <option key={a} value={a}>{a}</option>)}
      </select>
    </>
  );
}
