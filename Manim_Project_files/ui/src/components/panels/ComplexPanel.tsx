import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const MODES = ['f(z) = z^2', 'f(z) = z^3 - 1', 'f(z) = 1/z', 'f(z) = e^z', 'Mobius Transform', 'Custom'];

const ANIM_STYLES = [
  ['Vectors',  'vectors'],
  ['Morph',    'morph'],
];

export function ComplexPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [mode, setMode] = useState(MODES[0]);
  const [customFn, setCustomFn] = useState('z**2 + 0.5');
  const [reC, setReC] = useState(-0.5);
  const [imC, setImC] = useState(0.5);
  const [scale, setScale] = useState(2.0);
  const [nPts, setNPts] = useState(12);
  const [showArrows, setShowArrows] = useState(true);
  const [animStyle, setAnimStyle] = useState('vectors');
  const [camZoom, setCamZoom] = useState(1.0);
  const [text, setText] = useState<TextParams>({ ...DEFAULT_TEXT, text_position: 'top_left', text_color: 'teal' });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'complex',
      params: {
        mode, re_c: reC, im_c: imC, scale, n_pts: nPts, show_arrows: showArrows,
        custom_fn: customFn, anim_style: animStyle, cam_zoom: camZoom,
        ...text,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Function Mode</div>
      <select className="app-select" value={mode} onChange={e => setMode(e.target.value)}>
        {MODES.map(m => <option key={m}>{m}</option>)}
      </select>

      {mode === 'Custom' && (
        <div style={{ marginTop: 8 }}>
          <div className="sec-hdr">f(z) =</div>
          <input
            className="app-input"
            style={{ width: '100%', boxSizing: 'border-box', fontFamily: 'monospace' }}
            value={customFn}
            onChange={e => setCustomFn(e.target.value)}
            placeholder="e.g. z**2 + 1"
            spellCheck={false}
          />
          <div style={{ fontSize: 10, color: 'var(--dim)', marginTop: 4, lineHeight: 1.4 }}>
            Variable: z (complex). Available: cmath, np
          </div>
        </div>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Parameters</div>
      <Knob label="Re(c)"       min={-2.0} max={2.0} value={reC}   onChange={setReC} />
      <Knob label="Im(c)"       min={-2.0} max={2.0} value={imC}   onChange={setImC} />
      <Knob label="View Scale"  min={0.5}  max={4.0}  value={scale} onChange={setScale} decimals={1} step={0.1} />
      <Knob label="Num Points"  min={4}    max={24}   value={nPts}  onChange={v => setNPts(Math.round(v))} decimals={0} step={1} />
      <Knob label="Cam Zoom"    min={0.5}  max={3.0}  value={camZoom} onChange={setCamZoom} decimals={2} step={0.1} />

      <div className="sec-sep" />
      <div className="sec-hdr">Animation</div>
      <select className="app-select" value={animStyle} onChange={e => setAnimStyle(e.target.value)}>
        {ANIM_STYLES.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Display</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showArrows} onChange={e => setShowArrows(e.target.checked)} /> Show Arrows</label>
      </div>

      <TextControls value={text} onChange={setText} />
    </>
  );
}
