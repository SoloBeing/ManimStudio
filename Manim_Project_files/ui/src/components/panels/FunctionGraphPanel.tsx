import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface Curve { expr: string; color: string; label: string; style: string; width: string }
interface PCurve { xExpr: string; yExpr: string; color: string; label: string }

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];

const PRESETS: [string, string][] = [
  ['Preset…', ''],
  ['x²', 'x^2'], ['x³', 'x^3'], ['eˣ', 'exp(x)'], ['ln(x)', 'log(x)'],
  ['|x|', 'abs(x)'], ['√x', 'sqrt(x)'], ['1/x', '1/x'], ['sin(x)', 'sin(x)'],
];

// Parametric presets: [label, x(t), y(t)]
const PARAM_PRESETS: [string, string, string][] = [
  ['Preset…', '', ''],
  ['Circle', '3*cos(t)', '3*sin(t)'],
  ['Ellipse', '4*cos(t)', '2*sin(t)'],
  ['Lissajous', '3*sin(3*t)', '3*sin(2*t)'],
  ['Spiral', '0.4*t*cos(t)', '0.4*t*sin(t)'],
  ['Astroid', '3*cos(t)^3', '3*sin(t)^3'],
  ['Rose', '3*cos(3*t)*cos(t)', '3*cos(3*t)*sin(t)'],
  ['Cycloid', 't - sin(t)', '1 - cos(t)'],
  ['Lemniscate', '3*cos(t)/(1+sin(t)^2)', '3*sin(t)*cos(t)/(1+sin(t)^2)'],
];

const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

const DEFAULT_CURVES: Curve[] = [
  { expr: 'x^2', color: 'blue', label: 'f', style: 'solid', width: '2.5' },
];
const DEFAULT_PCURVES: PCurve[] = [
  { xExpr: '3*cos(t)', yExpr: '3*sin(t)', color: 'blue', label: 'circle' },
];

export function FunctionGraphPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [plotKind, setPlotKind]     = useState<'function' | 'parametric'>('function');

  // function-mode state (unchanged)
  const [curves, setCurves]         = useState<Curve[]>(DEFAULT_CURVES);
  // parametric-mode state
  const [pCurves, setPCurves]       = useState<PCurve[]>(DEFAULT_PCURVES);
  const [tMin, setTMin]             = useState(0);
  const [tMax, setTMax]             = useState(6.2832);

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
  const [useLatex, setUseLatex]     = useState(false);

  // parametric extras
  const [trOn, setTrOn]       = useState(true);
  const [trColor, setTrColor] = useState('yellow');
  const [veOn, setVeOn]       = useState(false);
  const [veColor, setVeColor] = useState('green');
  const [veScale, setVeScale] = useState(1.0);
  const [tmOn, setTmOn]       = useState(false);
  const [tmValues, setTmValues] = useState('0; 1.57; 3.14');
  const [tmColor, setTmColor] = useState('pink');

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

  function updatePCurve(i: number, field: keyof PCurve, val: string) {
    setPCurves(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: val } : c));
  }
  function addPCurve() {
    if (pCurves.length >= 3) return;
    const defaults = ['blue', 'red', 'green'];
    setPCurves(prev => [...prev, { xExpr: '', yExpr: '', color: defaults[prev.length % 3], label: '' }]);
  }
  function removePCurve(i: number) {
    if (pCurves.length <= 1) return;
    setPCurves(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => {
      if (plotKind === 'parametric') {
        return {
          mode: 'funcgraph',
          params: {
            plot_kind: 'parametric',
            param_curves: pCurves.map(c => ({
              x_expr: c.xExpr, y_expr: c.yExpr, color: c.color, label: c.label,
            })),
            t_min: tMin, t_max: tMax,
            x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax,
            x_step: xStep, y_step: yStep,
            show_grid: showGrid, cam_zoom: zoom,
            axis_label_x: axisLabelX, axis_label_y: axisLabelY, title,
            anim,
            tracer:    { on: trOn, color: trColor },
            velocity:  { on: veOn, color: veColor, scale: veScale },
            t_markers: { on: tmOn, values: tmValues, color: tmColor },
            use_latex: useLatex,
          },
        };
      }
      return {
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
      };
    },
  }));

  return (
    <>
      <div className="mode-toggle" style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        <button
          className="mode-toggle__btn"
          style={{ flex: 1, fontWeight: plotKind === 'function' ? 700 : 400,
                   opacity: plotKind === 'function' ? 1 : 0.6 }}
          onClick={() => setPlotKind('function')}
        >y = f(x)</button>
        <button
          className="mode-toggle__btn"
          style={{ flex: 1, fontWeight: plotKind === 'parametric' ? 700 : 400,
                   opacity: plotKind === 'parametric' ? 1 : 0.6 }}
          onClick={() => setPlotKind('parametric')}
        >Parametric</button>
      </div>

      {plotKind === 'function' ? (
        <>
          <div className="sec-hdr">Curves (up to 4)</div>
          {curves.map((c, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <select className="app-select" style={{ width: 70 }} value=""
                  onChange={e => { if (e.target.value) updateCurve(i, 'expr', e.target.value); }}>
                  {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
                </select>
                <input className="app-input" style={{ flex: 1 }} value={c.expr}
                  onChange={e => updateCurve(i, 'expr', e.target.value.slice(0, 120))}
                  placeholder="f(x), e.g. sin(x) + x^2" />
                <button className="mode-toggle__btn"
                  style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
                  onClick={() => removeCurve(i)} title="Remove curve">×</button>
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
                <input className="knob__num" style={{ width: 44, textAlign: 'center' }} value={c.label}
                  onChange={e => updateCurve(i, 'label', e.target.value.slice(0, 12))} placeholder="lbl" />
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
        </>
      ) : (
        <>
          <div style={{ fontSize: 11, color: 'var(--text-dim, #9aa)', lineHeight: 1.4, marginBottom: 8 }}>
            Curves are <b>(x(t), y(t))</b>; <b>t in radians</b> (e.g. <code>cos(t)</code>).
            The range below sets how far <b>t</b> sweeps.
          </div>
          <div className="sec-hdr">Curves (up to 3)</div>
          {pCurves.map((c, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <select className="app-select" style={{ width: 70 }} value=""
                  onChange={e => {
                    const p = PARAM_PRESETS.find(([l]) => l === e.target.value);
                    if (p && p[0] !== 'Preset…') { updatePCurve(i, 'xExpr', p[1]); updatePCurve(i, 'yExpr', p[2]); }
                  }}>
                  {PARAM_PRESETS.map(([l]) => <option key={l} value={l}>{l}</option>)}
                </select>
                <button className="mode-toggle__btn"
                  style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4, marginLeft: 'auto' }}
                  onClick={() => removePCurve(i)} title="Remove curve">×</button>
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <span style={{ width: 28, fontSize: 12, color: 'var(--text-dim, #9aa)' }}>x(t)</span>
                <input className="app-input" style={{ flex: 1 }} value={c.xExpr}
                  onChange={e => updatePCurve(i, 'xExpr', e.target.value.slice(0, 120))}
                  placeholder="x(t), e.g. cos(t)" />
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <span style={{ width: 28, fontSize: 12, color: 'var(--text-dim, #9aa)' }}>y(t)</span>
                <input className="app-input" style={{ flex: 1 }} value={c.yExpr}
                  onChange={e => updatePCurve(i, 'yExpr', e.target.value.slice(0, 120))}
                  placeholder="y(t), e.g. sin(t)" />
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <select className="app-select" style={{ flex: 1 }} value={c.color}
                  onChange={e => updatePCurve(i, 'color', e.target.value)}>
                  {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <input className="knob__num" style={{ width: 60, textAlign: 'center' }} value={c.label}
                  onChange={e => updatePCurve(i, 'label', e.target.value.slice(0, 12))} placeholder="lbl" />
              </div>
            </div>
          ))}
          {pCurves.length < 3 && (
            <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addPCurve}>
              + Add Curve
            </button>
          )}

          <div className="sec-sep" />
          <div className="sec-hdr">t-Range (radians)</div>
          <Knob label="t Min" min={-25.133} max={0}      value={tMin} onChange={setTMin} decimals={2} step={0.1} />
          <Knob label="t Max" min={0.1}     max={25.133} value={tMax} onChange={setTMax} decimals={2} step={0.1} />
        </>
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

      {plotKind === 'parametric' && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Extras</div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={trOn}
              onChange={e => setTrOn(e.target.checked)} /> Tracing dot</label>
          </div>
          {trOn && (
            <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={trColor}
              onChange={e => setTrColor(e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          )}
          {trOn && (
            <>
              <div className="check-row">
                <label className="app-check"><input type="checkbox" checked={veOn}
                  onChange={e => setVeOn(e.target.checked)} /> Velocity vector</label>
              </div>
              {veOn && (
                <>
                  <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={veColor}
                    onChange={e => setVeColor(e.target.value)}>
                    {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                  <Knob label="Scale" min={0.1} max={3} value={veScale} onChange={setVeScale} decimals={1} step={0.1} />
                </>
              )}
            </>
          )}
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={tmOn}
              onChange={e => setTmOn(e.target.checked)} /> t-markers</label>
          </div>
          {tmOn && (
            <>
              <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
                value={tmValues} onChange={e => setTmValues(e.target.value.slice(0, 120))}
                placeholder="t values — e.g. 0; 1.57; 3.14" />
              <select className="app-select" style={{ width: '100%' }} value={tmColor}
                onChange={e => setTmColor(e.target.value)}>
                {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </>
          )}
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelX} onChange={e => setAxisLabelX(e.target.value.slice(0, 24))} placeholder="X axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelY} onChange={e => setAxisLabelY(e.target.value.slice(0, 24))} placeholder="Y axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">{plotKind === 'parametric' ? 'Options' : 'Animation'}</div>
      {plotKind === 'parametric' && (
        <div className="check-row">
          <label className="app-check"><input type="checkbox" checked={useLatex}
            onChange={e => setUseLatex(e.target.checked)} /> Use LaTeX tick labels</label>
        </div>
      )}
      <select className="app-select" style={{ width: '100%', marginTop: 4 }} value={anim} onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(a => <option key={a} value={a}>{a}</option>)}
      </select>
    </>
  );
}
