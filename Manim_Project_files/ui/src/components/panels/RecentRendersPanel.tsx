import type { RecentRender } from '../../types';

const MODE_ICONS: Record<string, string> = {
  trig: '∿', complex: 'ℂ', linear: 'Mx', code: '</>',
  streamlines: '≋', geometry: '⬡', barchart: '▦',
  surface3d: '⬙', numberline: '⟺', playground: '▶',
};

function timeAgo(ts: number): string {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60)   return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

interface RecentRendersPanelProps {
  recentRenders: RecentRender[];
  onLoad: (r: RecentRender) => void;
  onClear: () => void;
}

export function RecentRendersPanel({ recentRenders, onLoad, onClear }: RecentRendersPanelProps) {
  return (
    <div style={{ padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 10 }}>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 10, color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: 1 }}>
          Saved Renders
        </div>
        {recentRenders.length > 0 && (
          <button onClick={onClear} style={{
            background: 'transparent', border: 'none',
            color: 'var(--dim)', fontSize: 10, cursor: 'pointer', padding: '2px 4px',
          }}>
            Clear all
          </button>
        )}
      </div>

      {recentRenders.length === 0 ? (
        <div style={{ fontSize: 12, color: 'var(--dim)', fontStyle: 'italic', marginTop: 4 }}>
          No saved renders yet. Renders appear here after you save them.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {recentRenders.map(r => (
            <div key={r.id} style={{
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 4, padding: '8px 10px',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{
                fontSize: 16, width: 22, textAlign: 'center',
                flexShrink: 0, color: 'var(--blue)',
              }}>
                {MODE_ICONS[r.mode] ?? '▶'}
              </span>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 12, color: 'var(--bright)',
                  textTransform: 'capitalize',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {r.mode}
                </div>
                <div style={{ fontSize: 10, color: 'var(--dim)', marginTop: 2 }}>
                  {r.quality} · {r.fps} fps · {timeAgo(r.timestamp)}
                </div>
                <div style={{
                  fontSize: 10, color: 'var(--dim)', marginTop: 1,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {r.path.split(/[\\/]/).pop()}
                </div>
              </div>

              <button onClick={() => onLoad(r)} style={{
                background: 'var(--panel)', border: '1px solid var(--border)',
                borderRadius: 3, color: 'var(--text)', fontSize: 10,
                cursor: 'pointer', padding: '3px 9px', flexShrink: 0,
              }}>
                Load
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
