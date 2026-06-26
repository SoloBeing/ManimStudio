import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface PCurve { expr: string; color: string; label: string }

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];
const PRESETS: [string, string][] = [
  ['Preset…', ''],
  ['Rose', 'cos(3*theta)'], ['Cardioid', '1 + cos(theta)'], ['Spiral', '0.5*theta'],
  ['Limaçon', '1 + 2*cos(theta)'], ['Circle', '2'],
];
const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];
const DEFAULT_CURVES: PCurve[] = [{ expr: '1 + cos(theta)', color: 'blue', label: 'cardioid' }];

export function PolarPlanePanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [curves, setCurves]       = useState<PCurve[]>(DEFAULT_CURVES);
  const [radiusMax, setRadiusMax] = useState(4);
  const [radiusStep, setRadiusStep] = useState(1);
  const [azDiv, setAzDiv]         = useState(12);
  const [size, setSize]           = useState(6);
  const [zoom, setZoom]           = useState(1.0);
  const [thetaMin, setThetaMin]   = useState(0);
  const [thetaMax, setThetaMax]   = useState(6.2832);
  const [showLabels, setShowLabels] = useState(true);

  const [ptOn, setPtOn]       = useState(false);
  const [ptCoords, setPtCoords] = useState('2,45; 3,135');
  const [ptColor, setPtColor] = useState('yellow');

  const [seOn, setSeOn]       = useState(false);
  const [seStart, setSeStart] = useState(0);
  const [seEnd, setSeEnd]     = useState(90);
  const [seColor, setSeColor] = useState('teal');

  const [rlOn, setRlOn]       = useState(false);
  const [rlAngle, setRlAngle] = useState(30);
  const [rlColor, setRlColor] = useState('red');

  const [title, setTitle]     = useState('');
  const [useLatex, setUseLatex] = useState(false);
  const [anim, setAnim]       = useState('Create');

  function updateCurve(i: number, field: keyof PCurve, val: string) {
    setCurves(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: val } : c));
  }
  function addCurve() {
    if (curves.length >= 3) return;
    const defaults = ['blue', 'red', 'green'];
    setCurves(prev => [...prev, { expr: '', color: defaults[prev.length % 3], label: '' }]);
  }
  function removeCurve(i: number) {
    if (curves.length <= 1) return;
    setCurves(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'polar',
      params: {
        curves: curves.map(c => ({ expr: c.expr, color: c.color, label: c.label })),
        radius_max: radiusMax, radius_step: radiusStep,
        azimuth_divisions: azDiv, size,
        theta_min: thetaMin, theta_max: thetaMax, show_curve_labels: showLabels,
        points:      { on: ptOn, coords: ptCoords, color: ptColor },
        sector:      { on: seOn, start_deg: seStart, end_deg: seEnd, color: seColor },
        radial_line: { on: rlOn, angle_deg: rlAngle, color: rlColor },
        cam_zoom: zoom, title,
        use_latex: useLatex, anim,
      },
    }),
  }));

  return (
    <>
      <div style={{ fontSize: 11, color: 'var(--text-dim, #9aa)', lineHeight: 1.4, marginBottom: 8 }}>
        Curve formulas use <b>θ in radians</b> (e.g. <code>cos(3*theta)</code>).
        Overlay angles below are in <b>degrees</b>.
      </div>

      <div className="sec-hdr">Curves (up to 3)</div>
      {curves.map((c, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
            <select className="app-select" style={{ width: 70 }} value=""
              onChange={e => { if (e.target.value) updateCurve(i, 'expr', e.target.value); }}>
              {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
            </select>
            <input className="app-input" style={{ flex: 1 }} value={c.expr}
              onChange={e => updateCurve(i, 'expr', e.target.value.slice(0, 120))}
              placeholder="r = f(theta), e.g. cos(3*theta)" />
            <button className="mode-toggle__btn"
              style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
              onClick={() => removeCurve(i)} title="Remove curve">×</button>
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <select className="app-select" style={{ flex: 1 }} value={c.color}
              onChange={e => updateCurve(i, 'color', e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input className="knob__num" style={{ width: 60, textAlign: 'center' }} value={c.label}
              onChange={e => updateCurve(i, 'label', e.target.value.slice(0, 12))} placeholder="lbl" />
          </div>
        </div>
      ))}
      {curves.length < 3 && (
        <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addCurve}>
          + Add Curve
        </button>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Grid</div>
      <Knob label="Radius Max"  min={1}   max={20} value={radiusMax}  onChange={v => setRadiusMax(Math.round(v))} decimals={0} step={1} />
      <Knob label="Radius Step" min={0.5} max={5}  value={radiusStep} onChange={setRadiusStep} decimals={1} step={0.5} />
      <Knob label="Spokes"      min={2}   max={48} value={azDiv}      onChange={v => setAzDiv(Math.round(v))}     decimals={0} step={1} />
      <Knob label="Size"        min={3}   max={10} value={size}       onChange={setSize} decimals={1} step={0.5} />
      <Knob label="Zoom"        min={0.3} max={3}  value={zoom}       onChange={setZoom} decimals={2} step={0.05} />

      <div className="sec-sep" />
      <div className="sec-hdr">Curve Range (radians)</div>
      <Knob label="θ Min" min={0}    max={6.2832}  value={thetaMin} onChange={setThetaMin} decimals={2} step={0.1} />
      <Knob label="θ Max" min={0.1}  max={25.133}  value={thetaMax} onChange={setThetaMax} decimals={2} step={0.1} />
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showLabels}
          onChange={e => setShowLabels(e.target.checked)} /> Show curve labels</label>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Overlays</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={ptOn}
          onChange={e => setPtOn(e.target.checked)} /> Points</label>
      </div>
      {ptOn && (
        <>
          <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
            value={ptCoords} onChange={e => setPtCoords(e.target.value.slice(0, 120))}
            placeholder="r,θ° pairs — e.g. 2,45; 3,135" />
          <select className="app-select" style={{ width: '100%' }} value={ptColor}
            onChange={e => setPtColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={seOn}
          onChange={e => setSeOn(e.target.checked)} /> Angular sector</label>
      </div>
      {seOn && (
        <>
          <Knob label="Start°" min={0} max={360} value={seStart} onChange={v => setSeStart(Math.round(v))} decimals={0} step={5} />
          <Knob label="End°"   min={0} max={360} value={seEnd}   onChange={v => setSeEnd(Math.round(v))}   decimals={0} step={5} />
          <select className="app-select" style={{ width: '100%' }} value={seColor}
            onChange={e => setSeColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={rlOn}
          onChange={e => setRlOn(e.target.checked)} /> Radial line</label>
      </div>
      {rlOn && (
        <>
          <Knob label="Angle°" min={0} max={360} value={rlAngle} onChange={v => setRlAngle(Math.round(v))} decimals={0} step={5} />
          <select className="app-select" style={{ width: '100%' }} value={rlColor}
            onChange={e => setRlColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Options</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={useLatex}
          onChange={e => setUseLatex(e.target.checked)} /> Use LaTeX labels (π-radian)</label>
      </div>
      <select className="app-select" style={{ width: '100%', marginTop: 4 }} value={anim}
        onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(x => <option key={x} value={x}>{x}</option>)}
      </select>
    </>
  );
}
