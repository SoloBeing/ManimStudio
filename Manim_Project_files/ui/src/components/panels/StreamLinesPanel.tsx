import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const FIELDS = [
  ['Vortex', 'vortex'], ['Source', 'source'], ['Sink', 'sink'],
  ['Saddle', 'saddle'], ['Wave', 'wave'],
];

export function StreamLinesPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [mode, setMode] = useState('vortex');
  const [scale, setScale] = useState(4.0);
  const [spacing, setSpacing] = useState(0.5);
  const [flowSpeed, setFlowSpeed] = useState(1.4);
  const [virtualTime, setVirtualTime] = useState(4.0);
  const [strokeWidth, setStrokeWidth] = useState(1.6);
  const [showAxes, setShowAxes] = useState(true);
  const [animate, setAnimate] = useState(true);
  const [text, setText] = useState<TextParams>({ ...DEFAULT_TEXT, text_position: 'top_left', text_color: 'teal' });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'streamlines',
      params: {
        mode, scale, spacing, flow_speed: flowSpeed,
        virtual_time: virtualTime, stroke_width_sl: strokeWidth,
        show_axes: showAxes, animate,
        ...text,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Vector Field</div>
      <select className="app-select" value={mode} onChange={e => setMode(e.target.value)}>
        {FIELDS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Parameters</div>
      <Knob label="View Scale"   min={2.0} max={7.0} value={scale}       onChange={setScale}       decimals={1} step={0.5} />
      <Knob label="Line Spacing" min={0.2} max={1.2} value={spacing}     onChange={setSpacing}     decimals={1} step={0.1} />
      <Knob label="Flow Speed"   min={0.2} max={4.0} value={flowSpeed}   onChange={setFlowSpeed}   decimals={1} step={0.1} />
      <Knob label="Trail Length" min={1.0} max={8.0} value={virtualTime} onChange={setVirtualTime} decimals={1} step={0.5} />
      <Knob label="Line Width"   min={0.5} max={5.0} value={strokeWidth} onChange={setStrokeWidth} decimals={1} step={0.1} />

      <div className="sec-sep" />
      <div className="sec-hdr">Display</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showAxes}  onChange={e => setShowAxes(e.target.checked)} /> Grid</label>
        <label className="app-check"><input type="checkbox" checked={animate}   onChange={e => setAnimate(e.target.checked)}  /> Animate Flow</label>
      </div>

      <TextControls value={text} onChange={setText} />
    </>
  );
}
