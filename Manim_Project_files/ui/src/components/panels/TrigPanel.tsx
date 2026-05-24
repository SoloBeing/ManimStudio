import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

export function TrigPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [showSin, setShowSin] = useState(true);
  const [showCos, setShowCos] = useState(true);
  const [showTan, setShowTan] = useState(false);
  const [A, setA] = useState(1.0);
  const [w, setW] = useState(1.0);
  const [ph, setPh] = useState(0.0);
  const [D, setD] = useState(0.0);
  const [xr, setXr] = useState(4.0);
  const [showGrid, setShowGrid] = useState(true);
  const [anim, setAnim] = useState('Create');
  const [text, setText] = useState<TextParams>({ ...DEFAULT_TEXT, text_position: 'top_right' });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'trig',
      params: {
        show_sin: showSin, show_cos: showCos, show_tan: showTan,
        A, w, ph, D, xr,
        show_grid: showGrid, anim,
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
      <div className="sec-hdr">Parameters</div>
      <Knob label="Amplitude A" min={0.1} max={4.0} value={A} onChange={setA} />
      <Knob label="Frequency w" min={0.1} max={5.0} value={w} onChange={setW} />
      <Knob label="Phase p"    min={-6.3} max={6.3} value={ph} onChange={setPh} />
      <Knob label="Vertical D" min={-3.0} max={3.0} value={D} onChange={setD} />
      <Knob label="X Range"    min={1.0}  max={8.0}  value={xr} onChange={setXr} decimals={1} step={0.5} />

      <div className="sec-sep" />
      <div className="sec-hdr">Display</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} /> Grid</label>
      </div>
      <div className="field-row">
        <label>Animation</label>
        <select className="app-select" value={anim} onChange={e => setAnim(e.target.value)}>
          {['Create', 'FadeIn', 'Write'].map(a => <option key={a}>{a}</option>)}
        </select>
      </div>

      <TextControls value={text} onChange={setText} />
    </>
  );
}
