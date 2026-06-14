import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const CURVE_COLORS = [
  ['Blue',        'blue'],  ['Red',     'red'],   ['Green',       'green'],
  ['Yellow',      'yellow'],['Orange',  'orange'],['Teal',        'teal'],
  ['Purple',      'purple'],['Pink',    'pink'],  ['Gold',        'gold'],
  ['White',       'white'], ['Lt Blue', 'light_blue'], ['Lt Green', 'light_green'],
];

const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

export function TrigPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [showSin, setShowSin] = useState(true);
  const [showCos, setShowCos] = useState(true);
  const [showTan, setShowTan] = useState(false);
  const [A, setA] = useState(1.0);
  const [w, setW] = useState(1.0);
  const [ph, setPh] = useState(0.0);
  const [D, setD] = useState(0.0);
  const [xr, setXr] = useState(4.0);
  const [yr, setYr] = useState(4.5);
  const [showGrid, setShowGrid] = useState(true);
  const [anim, setAnim] = useState('Create');
  const [sinColor, setSinColor] = useState('blue');
  const [cosColor, setCosColor] = useState('red');
  const [tanColor, setTanColor] = useState('green');
  const [sinPhase, setSinPhase] = useState(0.0);
  const [cosPhase, setCosPhase] = useState(0.0);
  const [tanPhase, setTanPhase] = useState(0.0);
  const [curveStroke, setCurveStroke] = useState(2.5);
  const [sinLabel, setSinLabel] = useState('');
  const [cosLabel, setCosLabel] = useState('');
  const [tanLabel, setTanLabel] = useState('');
  const [camZoom, setCamZoom] = useState(1.0);
  const [text, setText] = useState<TextParams>({ ...DEFAULT_TEXT, text_position: 'top_right' });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'trig',
      params: {
        show_sin: showSin, show_cos: showCos, show_tan: showTan,
        A, w, ph, D, xr, yr,
        show_grid: showGrid, anim,
        sin_color: sinColor, cos_color: cosColor, tan_color: tanColor,
        sin_phase: sinPhase, cos_phase: cosPhase, tan_phase: tanPhase,
        curve_stroke: curveStroke,
        sin_label: sinLabel, cos_label: cosLabel, tan_label: tanLabel,
        cam_zoom: camZoom,
        ...text,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Functions</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showSin} onChange={e => setShowSin(e.target.checked)} /> Sin(x)</label>
        <label className="app-check"><input type="checkbox" checked={showCos} onChange={e => setShowCos(e.target.checked)} /> Cos(x)</label>
        <label className="app-check"><input type="checkbox" checked={showTan} onChange={e => setShowTan(e.target.checked)} /> Tan(x)</label>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Curve Colors</div>
      {showSin && (
        <div className="field-row">
          <label>Sin</label>
          <select className="app-select" value={sinColor} onChange={e => setSinColor(e.target.value)}>
            {CURVE_COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      )}
      {showCos && (
        <div className="field-row">
          <label>Cos</label>
          <select className="app-select" value={cosColor} onChange={e => setCosColor(e.target.value)}>
            {CURVE_COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      )}
      {showTan && (
        <div className="field-row">
          <label>Tan</label>
          <select className="app-select" value={tanColor} onChange={e => setTanColor(e.target.value)}>
            {CURVE_COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Parameters</div>
      <Knob label="Amplitude A" min={0.1} max={4.0} value={A}  onChange={setA} />
      <Knob label="Frequency w" min={0.1} max={5.0} value={w}  onChange={setW} />
      <Knob label="Phase p"     min={-6.3} max={6.3} value={ph} onChange={setPh} />
      <Knob label="Vertical D"  min={-3.0} max={3.0} value={D}  onChange={setD} />
      <Knob label="X Range"     min={1.0}  max={8.0}  value={xr} onChange={setXr} decimals={1} step={0.5} />
      <Knob label="Y Range"     min={0.5}  max={8.0}  value={yr} onChange={setYr} decimals={1} step={0.5} />
      <Knob label="Curve Width" min={0.5}  max={8.0}  value={curveStroke} onChange={setCurveStroke} decimals={1} step={0.5} />

      {(showSin || showCos || showTan) && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Per-Curve Phase</div>
          {showSin && <Knob label="Sin Δp" min={-6.3} max={6.3} value={sinPhase} onChange={setSinPhase} />}
          {showCos && <Knob label="Cos Δp" min={-6.3} max={6.3} value={cosPhase} onChange={setCosPhase} />}
          {showTan && <Knob label="Tan Δp" min={-6.3} max={6.3} value={tanPhase} onChange={setTanPhase} />}
        </>
      )}

      {text.show_preset_labels && (showSin || showCos || showTan) && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Curve Labels</div>
          {showSin && (
            <div className="field-row">
              <label>Sin</label>
              <input className="app-input" placeholder="sin" value={sinLabel} onChange={e => setSinLabel(e.target.value)} />
            </div>
          )}
          {showCos && (
            <div className="field-row">
              <label>Cos</label>
              <input className="app-input" placeholder="cos" value={cosLabel} onChange={e => setCosLabel(e.target.value)} />
            </div>
          )}
          {showTan && (
            <div className="field-row">
              <label>Tan</label>
              <input className="app-input" placeholder="tan" value={tanLabel} onChange={e => setTanLabel(e.target.value)} />
            </div>
          )}
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Display</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} /> Grid</label>
      </div>
      <div className="field-row">
        <label>Animation</label>
        <select className="app-select" value={anim} onChange={e => setAnim(e.target.value)}>
          {ANIMS.map(a => <option key={a}>{a}</option>)}
        </select>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Camera</div>
      <Knob label="Zoom" min={0.5} max={3.0} value={camZoom} onChange={setCamZoom} decimals={2} step={0.1} />

      <TextControls value={text} onChange={setText} />
    </>
  );
}
