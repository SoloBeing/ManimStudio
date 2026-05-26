import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

interface Bar { label: string; value: string; color: string }

const BAR_COLORS = [
  ['Blue',   'blue'],   ['Red',    'red'],   ['Green', 'green'],
  ['Yellow', 'yellow'], ['Purple', 'purple'],['Orange','orange'],
  ['Teal',   'teal'],   ['Pink',   'pink'],  ['Gold',  'gold'],
];

const DEFAULT_BARS: Bar[] = [
  { label: 'A', value: '10', color: 'blue'   },
  { label: 'B', value: '20', color: 'red'    },
  { label: 'C', value: '15', color: 'green'  },
];

export function BarChartPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [bars, setBars]         = useState<Bar[]>(DEFAULT_BARS);
  const [autoY, setAutoY]       = useState(true);
  const [yMin, setYMin]         = useState(0);
  const [yMax, setYMax]         = useState(30);
  const [yStep, setYStep]       = useState(5);
  const [animate, setAnimate]   = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [text, setText]         = useState<TextParams>({ ...DEFAULT_TEXT });

  function updateBar(i: number, field: keyof Bar, val: string) {
    setBars(prev => prev.map((b, idx) => idx === i ? { ...b, [field]: val } : b));
  }

  function addBar() {
    if (bars.length >= 5) return;
    const defaults = ['blue', 'red', 'green', 'yellow', 'purple'];
    setBars(prev => [...prev, { label: String.fromCharCode(65 + prev.length), value: '10', color: defaults[prev.length % 5] }]);
  }

  function removeBar(i: number) {
    if (bars.length <= 1) return;
    setBars(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'barchart',
      params: {
        bar_labels: bars.map(b => b.label),
        bar_values: bars.map(b => parseFloat(b.value) || 0),
        bar_colors: bars.map(b => b.color),
        auto_y: autoY,
        y_min: yMin, y_max: yMax, y_step: yStep,
        animate, show_labels: showLabels,
        ...text,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Bars</div>
      {bars.map((bar, i) => (
        <div key={i} style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
          <input
            className="knob__num"
            style={{ width: 36, textAlign: 'center' }}
            value={bar.label}
            onChange={e => updateBar(i, 'label', e.target.value.slice(0, 12))}
            placeholder="Label"
          />
          <input
            className="knob__num"
            style={{ width: 44, textAlign: 'center' }}
            type="number"
            value={bar.value}
            onChange={e => updateBar(i, 'value', e.target.value)}
          />
          <select
            className="app-select"
            style={{ flex: 1 }}
            value={bar.color}
            onChange={e => updateBar(i, 'color', e.target.value)}
          >
            {BAR_COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <button
            className="mode-toggle__btn"
            style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
            onClick={() => removeBar(i)}
            title="Remove bar"
          >×</button>
        </div>
      ))}
      {bars.length < 5 && (
        <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addBar}>
          + Add Bar
        </button>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Y Axis</div>
      <div className="check-row">
        <label className="app-check">
          <input type="checkbox" checked={autoY} onChange={e => setAutoY(e.target.checked)} /> Auto Range
        </label>
      </div>
      {!autoY && (
        <>
          <Knob label="Y Min"  min={-100} max={0}   value={yMin}  onChange={v => setYMin(Math.round(v))}  decimals={0} step={1} />
          <Knob label="Y Max"  min={1}    max={200}  value={yMax}  onChange={v => setYMax(Math.round(v))}  decimals={0} step={5} />
          <Knob label="Y Step" min={1}    max={50}   value={yStep} onChange={v => setYStep(Math.round(v))} decimals={0} step={1} />
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Options</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={animate}    onChange={e => setAnimate(e.target.checked)}    /> Animate</label>
        <label className="app-check"><input type="checkbox" checked={showLabels} onChange={e => setShowLabels(e.target.checked)} /> Value Labels</label>
      </div>

      <TextControls value={text} onChange={setText} />
    </>
  );
}
