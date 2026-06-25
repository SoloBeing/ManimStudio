import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];
const PRESETS: [string, string][] = [
  ['Preset…', ''], ['x²', 'x^2'], ['x³', 'x^3'], ['eˣ', 'exp(x)'], ['ln(x)', 'log(x)'],
  ['sin(x)', 'sin(x)'], ['cos(x)', 'cos(x)'], ['√x', 'sqrt(x)'],
];
const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

export function CalculusPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [fExpr, setFExpr] = useState('x^2');
  const [gExpr, setGExpr] = useState('');
  const [a, setA] = useState(-1);
  const [b, setB] = useState(2);
  const [x0, setX0] = useState(1);

  const [riOn, setRiOn] = useState(true);
  const [riMethod, setRiMethod] = useState('left');
  const [riN, setRiN] = useState(10);
  const [riVal, setRiVal] = useState(true);

  const [arOn, setArOn] = useState(false);
  const [arMode, setArMode] = useState('under');
  const [arColor, setArColor] = useState('teal');
  const [arVal, setArVal] = useState(true);

  const [tgOn, setTgOn] = useState(false);
  const [tgSecant, setTgSecant] = useState(true);
  const [tgSlope, setTgSlope] = useState(true);

  const [dvOn, setDvOn] = useState(false);
  const [dvColor, setDvColor] = useState('red');
  const [dvLegend, setDvLegend] = useState(true);

  const [xMin, setXMin] = useState(-5);
  const [xMax, setXMax] = useState(5);
  const [yMin, setYMin] = useState(-4);
  const [yMax, setYMax] = useState(4);
  const [xStep, setXStep] = useState(1);
  const [yStep, setYStep] = useState(1);
  const [showGrid, setShowGrid] = useState(false);
  const [zoom, setZoom] = useState(1.0);
  const [axisLabelX, setAxisLabelX] = useState('x');
  const [axisLabelY, setAxisLabelY] = useState('y');
  const [title, setTitle] = useState('');
  const [useLatex, setUseLatex] = useState(false);
  const [anim, setAnim] = useState('Create');

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'calculus',
      params: {
        f_expr: fExpr, g_expr: gExpr, a, b, x0,
        riemann:    { on: riOn, method: riMethod, n: riN, show_value: riVal },
        area:       { on: arOn, mode: arMode, color: arColor, show_value: arVal },
        tangent:    { on: tgOn, animate_secant: tgSecant, show_slope: tgSlope },
        derivative: { on: dvOn, color: dvColor, show_legend: dvLegend },
        x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax,
        x_step: xStep, y_step: yStep, show_grid: showGrid, cam_zoom: zoom,
        axis_label_x: axisLabelX, axis_label_y: axisLabelY, title,
        use_latex: useLatex, anim,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Function</div>
      <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
        <select className="app-select" style={{ width: 70 }} value=""
          onChange={e => { if (e.target.value) setFExpr(e.target.value); }}>
          {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
        </select>
        <input className="app-input" style={{ flex: 1 }} value={fExpr}
          onChange={e => setFExpr(e.target.value.slice(0, 120))} placeholder="f(x), e.g. x^2" />
      </div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }} value={gExpr}
        onChange={e => setGExpr(e.target.value.slice(0, 120))} placeholder="g(x) — for area-between (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Interval & Point</div>
      <Knob label="a"  min={-50} max={50} value={a}  onChange={v => setA(Math.round(v))}  decimals={0} step={1} />
      <Knob label="b"  min={-50} max={50} value={b}  onChange={v => setB(Math.round(v))}  decimals={0} step={1} />
      <Knob label="x₀" min={-50} max={50} value={x0} onChange={setX0} decimals={2} step={0.25} />

      <div className="sec-sep" />
      <div className="sec-hdr">Overlays</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={riOn}
          onChange={e => setRiOn(e.target.checked)} /> Riemann</label>
      </div>
      {riOn && (
        <>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={riMethod}
            onChange={e => setRiMethod(e.target.value)}>
            <option value="left">Left</option><option value="right">Right</option>
            <option value="mid">Mid</option><option value="trapezoid">Trapezoid</option>
          </select>
          <Knob label="n" min={2} max={200} value={riN} onChange={v => setRiN(Math.round(v))} decimals={0} step={1} />
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={riVal}
            onChange={e => setRiVal(e.target.checked)} /> Show Σ value</label></div>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={arOn}
          onChange={e => setArOn(e.target.checked)} /> Area</label>
      </div>
      {arOn && (
        <>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={arMode}
            onChange={e => setArMode(e.target.value)}>
            <option value="under">Under f</option><option value="between">Between f & g</option>
          </select>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={arColor}
            onChange={e => setArColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={arVal}
            onChange={e => setArVal(e.target.checked)} /> Show area value</label></div>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={tgOn}
          onChange={e => setTgOn(e.target.checked)} /> Tangent</label>
      </div>
      {tgOn && (
        <>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={tgSecant}
            onChange={e => setTgSecant(e.target.checked)} /> Animate secant→tangent</label></div>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={tgSlope}
            onChange={e => setTgSlope(e.target.checked)} /> Show slope</label></div>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={dvOn}
          onChange={e => setDvOn(e.target.checked)} /> Derivative f′</label>
      </div>
      {dvOn && (
        <>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={dvColor}
            onChange={e => setDvColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={dvLegend}
            onChange={e => setDvLegend(e.target.checked)} /> Show legend</label></div>
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Axes</div>
      <Knob label="X Min" min={-50} max={0}  value={xMin} onChange={v => setXMin(Math.round(v))} decimals={0} step={1} />
      <Knob label="X Max" min={1}   max={50} value={xMax} onChange={v => setXMax(Math.round(v))} decimals={0} step={1} />
      <Knob label="Y Min" min={-50} max={0}  value={yMin} onChange={v => setYMin(Math.round(v))} decimals={0} step={1} />
      <Knob label="Y Max" min={1}   max={50} value={yMax} onChange={v => setYMax(Math.round(v))} decimals={0} step={1} />
      <Knob label="X Step" min={0.1} max={10} value={xStep} onChange={setXStep} decimals={1} step={0.5} />
      <Knob label="Y Step" min={0.1} max={10} value={yStep} onChange={setYStep} decimals={1} step={0.5} />
      <Knob label="Zoom"   min={0.3} max={3}  value={zoom}  onChange={setZoom}  decimals={2} step={0.05} />
      <div className="check-row"><label className="app-check"><input type="checkbox" checked={showGrid}
        onChange={e => setShowGrid(e.target.checked)} /> Grid</label></div>

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelX} onChange={e => setAxisLabelX(e.target.value.slice(0, 24))} placeholder="X axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelY} onChange={e => setAxisLabelY(e.target.value.slice(0, 24))} placeholder="Y axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Options</div>
      <div className="check-row"><label className="app-check"><input type="checkbox" checked={useLatex}
        onChange={e => setUseLatex(e.target.checked)} /> Use LaTeX labels</label></div>
      <select className="app-select" style={{ width: '100%', marginTop: 4 }} value={anim}
        onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(x => <option key={x} value={x}>{x}</option>)}
      </select>
    </>
  );
}
