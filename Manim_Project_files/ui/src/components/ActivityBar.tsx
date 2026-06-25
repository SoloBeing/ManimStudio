import { memo } from 'react';
import type { Mode } from '../types';

interface ActivityBarProps {
  active: Mode;
  onChange: (m: Mode) => void;
}

const ITEMS: Array<{ mode: Mode; icon: string; label: string }> = [
  { mode: 'trig',        icon: '∿',   label: 'Trig' },
  { mode: 'funcgraph',   icon: 'ƒ',   label: 'Graph' },
  { mode: 'complex',     icon: 'ℂ',   label: 'Cplx' },
  { mode: 'linear',      icon: 'Mx',  label: 'LinAlg' },
  { mode: 'code',        icon: '</>',  label: 'Code' },
  { mode: 'streamlines', icon: '≋',   label: 'Flow' },
  { mode: 'geometry',    icon: '⬡',   label: 'Geo' },
  { mode: 'barchart',    icon: '▦',   label: 'Chart' },
  { mode: 'surface3d',   icon: '⬙',   label: '3D' },
  { mode: 'numberline',  icon: '⟺',   label: 'NLine' },
  { mode: 'playground',  icon: '▶',   label: 'Play' },
];

export const ActivityBar = memo(function ActivityBar({ active, onChange }: ActivityBarProps) {
  return (
    <div className="activity-bar">
      {ITEMS.map(({ mode, icon, label }) => (
        <button
          key={mode}
          className={`activity-bar__btn${active === mode ? ' active' : ''}`}
          onClick={() => onChange(mode)}
          title={label}
        >
          <span className="activity-bar__icon">{icon}</span>
          <span className="activity-bar__label">{label}</span>
        </button>
      ))}
    </div>
  );
});
