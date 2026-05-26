import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const SURFACES = [
  ['Sine Wave',  'sine_wave'],
  ['Paraboloid', 'paraboloid'],
  ['Saddle',     'saddle'],
  ['Torus',      'torus'],
  ['Sphere',     'sphere'],
  ['Ripple',     'ripple'],
  ['Möbius Strip', 'mobius'],
];

const COLOR_MODES = [
  ['Checkerboard Blue',  'checkerboard_blue'],
  ['Checkerboard Teal',  'checkerboard_teal'],
  ['Checkerboard Green', 'checkerboard_green'],
  ['Solid Blue',         'solid_blue'],
  ['Solid Red',          'solid_red'],
  ['Solid Orange',       'solid_orange'],
  ['Rainbow',            'rainbow'],
];

export function Surface3DPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [surfaceType, setSurfaceType]     = useState('sine_wave');
  const [theta, setTheta]                 = useState(70);
  const [phi, setPhi]                     = useState(75);
  const [camZoom, setCamZoom]             = useState(1.0);
  const [showAxes, setShowAxes]           = useState(true);
  const [colorMode, setColorMode]         = useState('checkerboard_blue');
  const [resolution, setResolution]       = useState(8);
  const [animateCamera, setAnimateCamera] = useState(false);
  const [text, setText]                   = useState<TextParams>({ ...DEFAULT_TEXT });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'surface3d',
      params: {
        surface_type: surfaceType,
        theta, phi, cam_zoom: camZoom,
        show_axes: showAxes,
        color_mode: colorMode,
        resolution,
        animate_camera: animateCamera,
        ...text,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Surface</div>
      <select className="app-select" value={surfaceType} onChange={e => setSurfaceType(e.target.value)}>
        {SURFACES.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Colors</div>
      <select className="app-select" value={colorMode} onChange={e => setColorMode(e.target.value)}>
        {COLOR_MODES.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Camera</div>
      <Knob label="Theta °" min={0}   max={360} value={theta}    onChange={v => setTheta(Math.round(v))}   decimals={0} step={5} />
      <Knob label="Phi °"   min={0}   max={180} value={phi}      onChange={v => setPhi(Math.round(v))}     decimals={0} step={5} />
      <Knob label="Zoom"    min={0.3} max={3.0} value={camZoom}  onChange={setCamZoom}                     decimals={2} step={0.1} />

      <div className="sec-sep" />
      <div className="sec-hdr">Quality</div>
      <Knob label="Resolution" min={4} max={16} value={resolution} onChange={v => setResolution(Math.round(v))} decimals={0} step={1} />

      <div className="sec-sep" />
      <div className="sec-hdr">Display</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showAxes}      onChange={e => setShowAxes(e.target.checked)}       /> Axes</label>
        <label className="app-check"><input type="checkbox" checked={animateCamera} onChange={e => setAnimateCamera(e.target.checked)}   /> Rotate Cam</label>
      </div>

      <TextControls value={text} onChange={setText} />
    </>
  );
}
