import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface Highlight { row: number; col: number; color: string }

const COLORS: [string, string][] = [
  ['Yellow', 'yellow'], ['Red', 'red'], ['Green', 'green'], ['Blue', 'blue'],
  ['Teal', 'teal'], ['Orange', 'orange'], ['Purple', 'purple'], ['Gold', 'gold'],
];
const ANIMS = ['Create', 'Write', 'FadeIn'];
const BRACKETS: [string, string][] = [['[ ]', '[]'], ['( )', '()'], ['{ }', '{}']];
const OPERATIONS: [string, string][] = [
  ['None (static)', 'none'], ['Scalar multiply', 'scalar'], ['Add (A + B)', 'add'],
  ['Transpose', 'transpose'], ['Determinant', 'determinant'],
];
const MTARGETS: [string, string][] = [['Row', 'row'], ['Column', 'col'], ['Entry', 'entry']];

export function TablePanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [kind, setKind]   = useState<'table' | 'matrix'>('table');
  const [data, setData]   = useState('1, 2, 3\n4, 5, 6');
  const [title, setTitle] = useState('');
  const [anim, setAnim]   = useState('Create');
  const [zoom, setZoom]   = useState(1.0);

  // table-only
  const [rowLabels, setRowLabels] = useState('');
  const [colLabels, setColLabels] = useState('');
  const [useLatex, setUseLatex]   = useState(false);
  const [outerLines, setOuterLines] = useState(true);
  const [highlights, setHighlights] = useState<Highlight[]>([]);

  // matrix-only
  const [bracket, setBracket]     = useState('[]');
  const [operation, setOperation] = useState('none');
  const [scalar, setScalar]       = useState(2);
  const [data2, setData2]         = useState('1, 0\n0, 1');
  const [mhOn, setMhOn]           = useState(false);
  const [mhTarget, setMhTarget]   = useState('row');
  const [mhIndex, setMhIndex]     = useState(1);
  const [mhColor, setMhColor]     = useState('yellow');

  function addHighlight() {
    setHighlights(prev => [...prev, { row: 1, col: 1, color: 'yellow' }]);
  }
  function updateHighlight(i: number, field: keyof Highlight, val: string | number) {
    setHighlights(prev => prev.map((h, idx) => idx === i ? { ...h, [field]: val } : h));
  }
  function removeHighlight(i: number) {
    setHighlights(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'table',
      params: {
        kind, data, title, anim, cam_zoom: zoom,
        row_labels: rowLabels, col_labels: colLabels,
        use_latex: useLatex, include_outer_lines: outerLines,
        highlights: highlights.map(h => ({ row: h.row, col: h.col, color: h.color })),
        bracket, operation, scalar, data2,
        mhighlight: { on: mhOn, target: mhTarget, index: mhIndex, color: mhColor },
      },
    }),
  }));

  return (
    <>
      <div className="mode-toggle" style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        <button className={`mode-toggle__btn${kind === 'table' ? ' active' : ''}`}
          style={{ flex: 1 }} onClick={() => setKind('table')}>Table</button>
        <button className={`mode-toggle__btn${kind === 'matrix' ? ' active' : ''}`}
          style={{ flex: 1 }} onClick={() => setKind('matrix')}>Matrix</button>
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-dim, #9aa)', lineHeight: 1.4, marginBottom: 8 }}>
        One <b>row per line</b>; separate cells with <b>,</b> or <b>|</b>. Max 8×8.
      </div>

      <div className="sec-hdr">Data</div>
      <textarea className="app-input" style={{ width: '100%', boxSizing: 'border-box', minHeight: 70, fontFamily: 'monospace' }}
        value={data} onChange={e => setData(e.target.value)} placeholder="1, 2, 3&#10;4, 5, 6" />

      {kind === 'table' && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Labels</div>
          <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
            value={rowLabels} onChange={e => setRowLabels(e.target.value)} placeholder="Row labels (comma-sep)" />
          <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
            value={colLabels} onChange={e => setColLabels(e.target.value)} placeholder="Column labels (comma-sep)" />

          <div className="sec-sep" />
          <div className="sec-hdr">Highlights (1-based; counts label row/col)</div>
          {highlights.map((h, i) => (
            <div key={i} style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
              <input className="knob__num" style={{ width: 40, textAlign: 'center' }} type="number" value={h.row}
                onChange={e => updateHighlight(i, 'row', Number(e.target.value))} title="row" />
              <input className="knob__num" style={{ width: 40, textAlign: 'center' }} type="number" value={h.col}
                onChange={e => updateHighlight(i, 'col', Number(e.target.value))} title="col" />
              <select className="app-select" style={{ flex: 1 }} value={h.color}
                onChange={e => updateHighlight(i, 'color', e.target.value)}>
                {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button className="mode-toggle__btn" style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
                onClick={() => removeHighlight(i)} title="Remove">×</button>
            </div>
          ))}
          <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addHighlight}>+ Add Highlight</button>

          <div className="sec-sep" />
          <div className="sec-hdr">Options</div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={useLatex}
              onChange={e => setUseLatex(e.target.checked)} /> Math cells (LaTeX / MathTable)</label>
          </div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={outerLines}
              onChange={e => setOuterLines(e.target.checked)} /> Outer lines</label>
          </div>
        </>
      )}

      {kind === 'matrix' && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Brackets</div>
          <select className="app-select" style={{ width: '100%' }} value={bracket}
            onChange={e => setBracket(e.target.value)}>
            {BRACKETS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>

          <div className="sec-sep" />
          <div className="sec-hdr">Operation</div>
          <select className="app-select" style={{ width: '100%' }} value={operation}
            onChange={e => setOperation(e.target.value)}>
            {OPERATIONS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>

          {operation === 'scalar' && (
            <Knob label="Scalar k" min={-10} max={10} value={scalar} onChange={setScalar} decimals={1} step={0.5} />
          )}
          {operation === 'add' && (
            <>
              <div className="sec-hdr" style={{ marginTop: 6 }}>Second matrix (B)</div>
              <textarea className="app-input" style={{ width: '100%', boxSizing: 'border-box', minHeight: 50, fontFamily: 'monospace' }}
                value={data2} onChange={e => setData2(e.target.value)} placeholder="1, 0&#10;0, 1" />
            </>
          )}
          {operation === 'none' && (
            <>
              <div className="check-row" style={{ marginTop: 6 }}>
                <label className="app-check"><input type="checkbox" checked={mhOn}
                  onChange={e => setMhOn(e.target.checked)} /> Highlight</label>
              </div>
              {mhOn && (
                <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  <select className="app-select" style={{ flex: 1 }} value={mhTarget}
                    onChange={e => setMhTarget(e.target.value)}>
                    {MTARGETS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                  <input className="knob__num" style={{ width: 44, textAlign: 'center' }} type="number" value={mhIndex}
                    onChange={e => setMhIndex(Number(e.target.value))} title="index (1-based)" />
                  <select className="app-select" style={{ flex: 1 }} value={mhColor}
                    onChange={e => setMhColor(e.target.value)}>
                    {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
              )}
            </>
          )}
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Title & Animation</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />
      <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={anim}
        onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(x => <option key={x} value={x}>{x}</option>)}
      </select>
      <Knob label="Zoom" min={0.3} max={3} value={zoom} onChange={setZoom} decimals={2} step={0.05} />
    </>
  );
}
