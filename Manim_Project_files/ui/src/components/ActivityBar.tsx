import type { Mode } from '../types';

interface ActivityBarProps {
  active: Mode;
  onChange: (m: Mode) => void;
}

const ITEMS: Array<{ mode: Mode; icon: string; label: string }> = [
  { mode: 'trig',        icon: '∿',   label: 'Trig' },
  { mode: 'complex',     icon: 'ℂ',   label: 'Cplx' },
  { mode: 'linear',      icon: 'Mx',  label: 'LinAlg' },
  { mode: 'code',        icon: '</>',  label: 'Code' },
  { mode: 'streamlines', icon: '≋',   label: 'Flow' },
  { mode: 'playground',  icon: '▶',   label: 'Play' },
];

export function ActivityBar({ active, onChange }: ActivityBarProps) {
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
}
