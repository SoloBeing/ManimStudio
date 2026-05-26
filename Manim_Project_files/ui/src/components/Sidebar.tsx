import type { RefObject } from 'react';
import type { Mode, PanelHandle } from '../types';
import { TrigPanel }         from './panels/TrigPanel';
import { ComplexPanel }      from './panels/ComplexPanel';
import { LinearPanel }       from './panels/LinearPanel';
import { CodePanel }         from './panels/CodePanel';
import { StreamLinesPanel }  from './panels/StreamLinesPanel';
import { PlaygroundPanel }   from './panels/PlaygroundPanel';
import { GeometryPanel }     from './panels/GeometryPanel';
import { BarChartPanel }     from './panels/BarChartPanel';
import { Surface3DPanel }    from './panels/Surface3DPanel';
import { NumberLinePanel }   from './panels/NumberLinePanel';

const TITLES: Record<Mode, string> = {
  trig:        'Trigonometric Functions',
  complex:     'Complex Plane',
  linear:      'Linear Algebra',
  code:        'Code Animation',
  streamlines: 'StreamLines',
  playground:  'Playground',
  geometry:    'Geometry',
  barchart:    'Bar Chart',
  surface3d:   '3D Surface',
  numberline:  'Number Line',
};

interface SidebarProps {
  activeMode: Mode;
  panelRef: RefObject<PanelHandle | null>;
}

export function Sidebar({ activeMode, panelRef }: SidebarProps) {
  return (
    <div className="sidebar">
      <div className="sidebar__title">{TITLES[activeMode]}</div>
      <div className="sidebar__content">
        {activeMode === 'trig'        && <TrigPanel        ref={panelRef} />}
        {activeMode === 'complex'     && <ComplexPanel     ref={panelRef} />}
        {activeMode === 'linear'      && <LinearPanel      ref={panelRef} />}
        {activeMode === 'code'        && <CodePanel        ref={panelRef} />}
        {activeMode === 'streamlines' && <StreamLinesPanel ref={panelRef} />}
        {activeMode === 'playground'  && <PlaygroundPanel  ref={panelRef} />}
        {activeMode === 'geometry'    && <GeometryPanel    ref={panelRef} />}
        {activeMode === 'barchart'    && <BarChartPanel    ref={panelRef} />}
        {activeMode === 'surface3d'   && <Surface3DPanel   ref={panelRef} />}
        {activeMode === 'numberline'  && <NumberLinePanel  ref={panelRef} />}
      </div>
    </div>
  );
}
