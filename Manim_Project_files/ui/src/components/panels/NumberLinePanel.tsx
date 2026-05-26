import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const DOT_COLORS = [
  ['Blue',   'blue'],  ['Red',    'red'],   ['Green',  'green'],
  ['Yellow', 'yellow'],['Orange', 'orange'],['Teal',   'teal'],
  ['Purple', 'purple'],['White',  'white'],
];

export function NumberLinePanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [xMin, setXMin]           = useState(-5);
  const [xMax, setXMax]           = useState(5);
  const [tickStep, setTickStep]   = useState(1);
  const [startVal, setStartVal]   = useState(0);
  const [target1, setTarget1]     = useState('3');
  const [target2, setTarget2]     = useState('-2');
  const [target3, setTarget3]     = useState('');
  const [runTime, setRunTime]     = useState(1.5);
  const [dotColor, setDotColor]   = useState('blue');
  const [showLabel, setShowLabel] = useState(true);
  const [text, setText]           = useState<TextParams>({ ...DEFAULT_TEXT });

  useImperativeHandle(ref, () => {
    const targets: number[] = [];
    [target1, target2, target3].forEach(v => {
      const n = parseFloat(v);
      if (!isNaN(n)) targets.push(n);
    });
    return {
      getParams: () => ({
        mode: 'numberline',
        params: {
          x_min: xMin, x_max: xMax,
          tick_step: tickStep,
          start_val: startVal,
          target_vals: targets,
          run_time_per_step: runTime,
          dot_color: dotColor,
          show_label: showLabel,
          ...text,
        },
      }),
    };
  });

  return (
    <>
      <div className="sec-hdr">Range</div>
      <Knob label="X Min"     min={-20} max={0}   value={xMin}     onChange={v => setXMin(Math.round(v))}     decimals={0} step={1} />
      <Knob label="X Max"     min={1}   max={20}  value={xMax}     onChange={v => setXMax(Math.round(v))}     decimals={0} step={1} />
      <Knob label="Tick Step" min={0.5} max={5}   value={tickStep} onChange={v => setTickStep(parseFloat(v.toFixed(1)))} decimals={1} step={0.5} />

      <div className="sec-sep" />
      <div className="sec-hdr">Dot</div>
      <Knob label="Start" min={xMin} max={xMax} value={startVal} onChange={v => setStartVal(parseFloat(v.toFixed(2)))} decimals={2} step={0.5} />
      <div className="field-row">
        <label>Color</label>
        <select className="app-select" value={dotColor} onChange={e => setDotColor(e.target.value)}>
          {DOT_COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showLabel} onChange={e => setShowLabel(e.target.checked)} /> Value Label</label>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Animate To (up to 3)</div>
      {([
        ['Target 1', target1, setTarget1],
        ['Target 2', target2, setTarget2],
        ['Target 3', target3, setTarget3],
      ] as [string, string, (v: string) => void][]).map(([label, val, setter]) => (
        <div className="field-row" key={label}>
          <label>{label}</label>
          <input
            className="knob__num"
            style={{ flex: 1, width: 'auto' }}
            type="number"
            step="0.5"
            value={val}
            placeholder="—"
            onChange={e => setter(e.target.value)}
          />
        </div>
      ))}
      <Knob label="Speed (s)" min={0.3} max={4.0} value={runTime} onChange={setRunTime} decimals={1} step={0.1} />

      <TextControls value={text} onChange={setText} />
    </>
  );
}
