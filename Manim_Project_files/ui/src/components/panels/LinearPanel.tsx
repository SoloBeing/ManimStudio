import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { NumInput } from '../shared/NumInput';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const PRESETS: Array<[string, number[] | null]> = [
  ['Custom', null],
  ['Rotate 45°', [0.71, -0.71, 0.71, 0.71, 2.0, 1.0]],
  ['Shear X',    [1.0, 1.25, 0.0, 1.0, 1.0, 1.5]],
  ['Shear Y',    [1.0, 0.0, 1.25, 1.0, 1.5, 1.0]],
  ['Reflect X',  [1.0, 0.0, 0.0, -1.0, 1.5, 1.0]],
  ['Reflect Y',  [-1.0, 0.0, 0.0, 1.0, 1.5, 1.0]],
  ['Project X',  [1.0, 0.0, 0.0, 0.0, 1.5, 1.5]],
  ['Scale Stretch', [2.0, 0.0, 0.0, 0.5, 1.0, 1.5]],
  ['Collapse Line', [1.0, 1.0, 0.5, 0.5, 1.0, 2.0]],
];

const NL_PRESETS = [
  ['Swirl', 'swirl'], ['Wave Warp', 'wave'], ['Bulge', 'bulge'],
  ['Pinch', 'pinch'], ['Complex Square', 'complex_square'],
];

export function LinearPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [subMode, setSubMode] = useState<'linear' | 'nonlinear'>('linear');

  // Linear state
  const [preset, setPreset] = useState('Custom');
  const [a, setA] = useState(2.0); const [b, setB] = useState(0.5);
  const [c, setC] = useState(0.5); const [d, setD] = useState(2.0);
  const [vx, setVx] = useState(1.0); const [vy, setVy] = useState(1.0);
  const [showDet, setShowDet] = useState(true);
  const [showBasis, setShowBasis] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [transformGrid, setTransformGrid] = useState(false);
  const [keepOriginalGrid, setKeepOriginalGrid] = useState(false);
  const [camZoom, setCamZoom] = useState(1.0);
  const [e1Label, setE1Label] = useState('');
  const [e2Label, setE2Label] = useState('');
  const [text, setText] = useState<TextParams>({ ...DEFAULT_TEXT });

  // Nonlinear state
  const [nlMode, setNlMode] = useState('swirl');
  const [intensity, setIntensity] = useState(1.0);
  const [nlScale, setNlScale] = useState(4.0);
  const [nlGrid, setNlGrid] = useState(true);
  const [nlPoints, setNlPoints] = useState(true);
  const [nlText, setNlText] = useState<TextParams>({ ...DEFAULT_TEXT, text_position: 'top_right', text_color: 'teal' });

  function applyPreset(name: string) {
    setPreset(name);
    const entry = PRESETS.find(([l]) => l === name);
    if (!entry || !entry[1]) return;
    const [pa, pb, pc, pd, pvx, pvy] = entry[1];
    setA(pa); setB(pb); setC(pc); setD(pd); setVx(pvx); setVy(pvy);
  }

  useImperativeHandle(ref, () => ({
    getParams: () => subMode === 'nonlinear'
      ? {
          mode: 'nonlinear',
          params: {
            mode: nlMode, intensity, scale: nlScale,
            show_grid: nlGrid, show_points: nlPoints,
            ...nlText,
          },
        }
      : {
          mode: 'linear',
          params: {
            a, b, c, d, vx, vy,
            show_det: showDet, show_basis: showBasis, show_grid: showGrid,
            transform_grid: transformGrid, keep_original_grid: keepOriginalGrid,
            cam_zoom: camZoom, e1_label: e1Label, e2_label: e2Label,
            ...text,
          },
        },
  }));

  return (
    <>
      <div className="mode-toggle">
        <button className={`mode-toggle__btn${subMode === 'linear' ? ' active' : ''}`}
          onClick={() => setSubMode('linear')}>Linear</button>
        <button className={`mode-toggle__btn${subMode === 'nonlinear' ? ' active' : ''}`}
          onClick={() => setSubMode('nonlinear')}>Non-Linear</button>
      </div>

      {subMode === 'linear' && (
        <>
          <div className="sec-hdr">Preset</div>
          <select className="app-select" value={preset}
            onChange={e => applyPreset(e.target.value)}>
            {PRESETS.map(([l]) => <option key={l}>{l}</option>)}
          </select>

          <div className="sec-sep" />
          <div className="sec-hdr">2×2 Matrix</div>
          <div className="matrix-grid">
            <label>a</label>
            <NumInput className="knob__num" style={{ width: '100%' }} min={-9} max={9} step={0.25} decimals={2} value={a} onChange={v => { setA(v); setPreset('Custom'); }} />
            <label>b</label>
            <NumInput className="knob__num" style={{ width: '100%' }} min={-9} max={9} step={0.25} decimals={2} value={b} onChange={v => { setB(v); setPreset('Custom'); }} />
            <label>c</label>
            <NumInput className="knob__num" style={{ width: '100%' }} min={-9} max={9} step={0.25} decimals={2} value={c} onChange={v => { setC(v); setPreset('Custom'); }} />
            <label>d</label>
            <NumInput className="knob__num" style={{ width: '100%' }} min={-9} max={9} step={0.25} decimals={2} value={d} onChange={v => { setD(v); setPreset('Custom'); }} />
          </div>

          <div className="sec-sep" />
          <div className="sec-hdr">Input Vector</div>
          <div className="field-row">
            <label>Vx</label>
            <NumInput className="knob__num" style={{ flex: 1, width: 'auto' }} min={-5} max={5} step={0.5} decimals={2} value={vx} onChange={setVx} />
            <label style={{ minWidth: 24, textAlign: 'center' }}>Vy</label>
            <NumInput className="knob__num" style={{ flex: 1, width: 'auto' }} min={-5} max={5} step={0.5} decimals={2} value={vy} onChange={setVy} />
          </div>

          <div className="sec-sep" />
          <div className="sec-hdr">Display</div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={showDet} onChange={e => setShowDet(e.target.checked)} /> Det</label>
            <label className="app-check"><input type="checkbox" checked={showBasis} onChange={e => setShowBasis(e.target.checked)} /> Basis</label>
            <label className="app-check"><input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} /> Grid</label>
          </div>
          {showGrid && (
            <div className="check-row">
              <label className="app-check"><input type="checkbox" checked={transformGrid} onChange={e => setTransformGrid(e.target.checked)} /> Warp grid under M</label>
              {transformGrid && (
                <label className="app-check"><input type="checkbox" checked={keepOriginalGrid} onChange={e => setKeepOriginalGrid(e.target.checked)} /> Keep original (ghost)</label>
              )}
            </div>
          )}

          {showBasis && text.show_preset_labels && (
            <>
              <div className="sec-sep" />
              <div className="sec-hdr">Basis Labels</div>
              <div className="field-row">
                <label>î</label>
                <input className="app-input" placeholder="e1" value={e1Label} onChange={e => setE1Label(e.target.value)} />
                <label style={{ minWidth: 24, textAlign: 'center' }}>ĵ</label>
                <input className="app-input" placeholder="e2" value={e2Label} onChange={e => setE2Label(e.target.value)} />
              </div>
            </>
          )}

          <div className="sec-sep" />
          <div className="sec-hdr">Camera</div>
          <Knob label="Zoom" min={0.5} max={3.0} value={camZoom} onChange={setCamZoom} decimals={2} step={0.1} />

          <TextControls value={text} onChange={setText} />
        </>
      )}

      {subMode === 'nonlinear' && (
        <>
          <div className="sec-hdr">Preset</div>
          <select className="app-select" value={nlMode}
            onChange={e => setNlMode(e.target.value)}>
            {NL_PRESETS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>

          <div className="sec-sep" />
          <div className="sec-hdr">Parameters</div>
          <Knob label="Intensity"  min={0.2} max={3.0} value={intensity} onChange={setIntensity} decimals={1} step={0.1} />
          <Knob label="View Scale" min={2.0} max={6.0} value={nlScale}   onChange={setNlScale}   decimals={1} step={0.5} />

          <div className="sec-sep" />
          <div className="sec-hdr">Display</div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={nlGrid} onChange={e => setNlGrid(e.target.checked)} /> Grid</label>
            <label className="app-check"><input type="checkbox" checked={nlPoints} onChange={e => setNlPoints(e.target.checked)} /> Points</label>
          </div>
          <TextControls value={nlText} onChange={setNlText} />
        </>
      )}
    </>
  );
}
