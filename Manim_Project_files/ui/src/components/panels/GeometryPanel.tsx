import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const SHAPES = [
  ['Circle',       'circle'],
  ['Square',       'square'],
  ['Rectangle',    'rectangle'],
  ['Triangle',     'triangle'],
  ['Pentagon',     'pentagon'],
  ['Hexagon',      'hexagon'],
  ['Star',         'star'],
  ['Arrow',        'arrow'],
  ['Double Arrow', 'doublearrow'],
  ['Annulus',      'annulus'],
];

const ANIMS = [
  'Create', 'DrawBorderThenFill', 'FadeIn',
  'GrowFromCenter', 'SpinInFromNothing', 'FadeInFromLarge', 'Write',
  'SpiralIn', 'ShowIncreasingSubsets',
];

const ARRANGEMENTS = [
  ['Row',    'row'],
  ['Column', 'column'],
  ['Grid',   'grid'],
  ['Circle', 'circle'],
];

const COLORS = [
  ['Blue',        'blue'],
  ['Red',         'red'],
  ['Green',       'green'],
  ['Yellow',      'yellow'],
  ['Orange',      'orange'],
  ['Teal',        'teal'],
  ['Purple',      'purple'],
  ['Pink',        'pink'],
  ['Gold',        'gold'],
  ['White',       'white'],
  ['Light Blue',  'light_blue'],
  ['Light Green', 'light_green'],
  ['Maroon',      'maroon'],
  ['Grey',        'grey'],
];

export function GeometryPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [shape, setShape]            = useState('circle');
  const [size, setSize]              = useState(1.5);
  const [fillColor, setFillColor]    = useState('blue');
  const [strokeColor, setStrokeColor]= useState('white');
  const [fillOpacity, setFillOpacity]= useState(0.6);
  const [strokeWidth, setStrokeWidth]= useState(3.0);
  const [anim, setAnim]              = useState('DrawBorderThenFill');
  const [camZoom, setCamZoom]        = useState(1.0);
  const [count, setCount]            = useState(1);
  const [arrangement, setArrangement]= useState('row');
  const [text, setText]              = useState<TextParams>({ ...DEFAULT_TEXT });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'geometry',
      params: {
        shape, size, shape_fill_color: fillColor, shape_stroke_color: strokeColor,
        fill_opacity: fillOpacity, shape_stroke_width: strokeWidth,
        anim, cam_zoom: camZoom, count, arrangement,
        ...text,
      },
    }),
  }));

  const isArrow = shape === 'arrow' || shape === 'doublearrow';

  return (
    <>
      <div className="sec-hdr">Shape</div>
      <select className="app-select" value={shape} onChange={e => setShape(e.target.value)}>
        {SHAPES.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Size & Style</div>
      <Knob label="Size"         min={0.3} max={3.5} value={size}        onChange={setSize}        decimals={2} step={0.1} />
      {!isArrow && (
        <Knob label="Fill Opacity" min={0.0} max={1.0} value={fillOpacity} onChange={setFillOpacity} decimals={2} step={0.05} />
      )}
      <Knob label="Stroke Width" min={0.5} max={10.0} value={strokeWidth} onChange={setStrokeWidth} decimals={1} step={0.5} />

      <div className="sec-sep" />
      <div className="sec-hdr">Colors</div>
      {!isArrow && (
        <div className="field-row">
          <label>Fill</label>
          <select className="app-select" value={fillColor} onChange={e => setFillColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      )}
      <div className="field-row">
        <label>Stroke</label>
        <select className="app-select" value={strokeColor} onChange={e => setStrokeColor(e.target.value)}>
          {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Animation</div>
      <select className="app-select" value={anim} onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(a => <option key={a}>{a}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Multiple Shapes</div>
      <Knob label="Count" min={1} max={8} value={count} onChange={v => setCount(Math.round(v))} decimals={0} step={1} />
      {count > 1 && (
        <>
          <div className="field-row" style={{ marginTop: 4 }}>
            <label>Layout</label>
            <select className="app-select" value={arrangement} onChange={e => setArrangement(e.target.value)}>
              {ARRANGEMENTS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div style={{ fontSize: 10, color: 'var(--dim)', marginTop: 4, lineHeight: 1.4 }}>
            Copies are auto-coloured across a rainbow palette.
          </div>
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Camera</div>
      <Knob label="Zoom" min={0.5} max={3.0} value={camZoom} onChange={setCamZoom} decimals={2} step={0.1} />

      <TextControls value={text} onChange={setText} />
    </>
  );
}
