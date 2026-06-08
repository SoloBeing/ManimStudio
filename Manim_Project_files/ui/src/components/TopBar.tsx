import { memo, useState, useRef, useEffect } from 'react';
import type { SystemInfo, Preset, RecentRender } from '../types';
import { SettingsPanel }      from './panels/SettingsPanel';
import { PresetsPanel }       from './panels/PresetsPanel';
import { RecentRendersPanel } from './panels/RecentRendersPanel';

type OpenPanel = 'settings' | 'presets' | 'recent' | null;

interface TopBarProps {
  systemInfo: SystemInfo | null;
  quality: string;
  format: string;
  fps: string;
  opengl: boolean;
  outputDir: string;
  onQualityChange: (q: string) => void;
  onFormatChange: (f: string) => void;
  onFpsChange: (f: string) => void;
  onOpenglChange: (v: boolean) => void;
  onBrowseOutput: () => void;
  presets: Preset[];
  onApplyPreset: (p: Preset) => void;
  onSavePreset: (name: string) => void;
  onDeletePreset: (id: string) => void;
  recentRenders: RecentRender[];
  onLoadRender: (r: RecentRender) => void;
  onClearRecent: () => void;
}

export const TopBar = memo(function TopBar({
  systemInfo, quality, format, fps, opengl, outputDir,
  onQualityChange, onFormatChange, onFpsChange, onOpenglChange, onBrowseOutput,
  presets, onApplyPreset, onSavePreset, onDeletePreset,
  recentRenders, onLoadRender, onClearRecent,
}: TopBarProps) {
  const [open, setOpen] = useState<OpenPanel>(null);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setOpen(null);
      }
    }
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);

  function toggle(p: OpenPanel) {
    setOpen(prev => prev === p ? null : p);
  }

  return (
    <div ref={barRef} style={{ position: 'relative', zIndex: 100 }}>
      <div style={{
        height: 36,
        background: 'var(--panel)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        gap: 4,
        userSelect: 'none',
      }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--bright)', marginRight: 16, letterSpacing: 0.3 }}>
          ManimStudio
        </span>

        <div style={{ display: 'flex', gap: 2 }}>
          <MenuButton label="Settings" active={open === 'settings'} onClick={() => toggle('settings')} />
          <MenuButton label="Presets"  active={open === 'presets'}  onClick={() => toggle('presets')}  />
          <MenuButton label="Recent"   active={open === 'recent'}   onClick={() => toggle('recent')}   />
        </div>
      </div>

      {open === 'settings' && (
        <Dropdown width={320}>
          <SettingsPanel
            systemInfo={systemInfo} quality={quality} format={format} fps={fps} opengl={opengl} outputDir={outputDir}
            onQualityChange={onQualityChange} onFormatChange={onFormatChange} onFpsChange={onFpsChange}
            onOpenglChange={onOpenglChange} onBrowseOutput={onBrowseOutput}
          />
        </Dropdown>
      )}
      {open === 'presets' && (
        <Dropdown width={300}>
          <PresetsPanel
            quality={quality} format={format} fps={fps} opengl={opengl}
            presets={presets}
            onApply={p => { onApplyPreset(p); setOpen(null); }}
            onSave={onSavePreset}
            onDelete={onDeletePreset}
          />
        </Dropdown>
      )}
      {open === 'recent' && (
        <Dropdown width={320}>
          <RecentRendersPanel
            recentRenders={recentRenders}
            onLoad={r => { onLoadRender(r); setOpen(null); }}
            onClear={onClearRecent}
          />
        </Dropdown>
      )}
    </div>
  );
});

function MenuButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? 'var(--active)' : 'transparent',
        border: 'none',
        borderRadius: 4,
        color: active ? 'var(--bright)' : 'var(--text)',
        fontSize: 12,
        cursor: 'pointer',
        padding: '3px 10px',
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'var(--hover)'; }}
      onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
    >
      {label}
    </button>
  );
}

function Dropdown({ children, width }: { children: React.ReactNode; width: number }) {
  return (
    <div style={{
      position: 'absolute',
      top: '100%',
      left: 0,
      width,
      background: 'var(--panel)',
      border: '1px solid var(--border)',
      borderTop: 'none',
      borderRadius: '0 0 6px 6px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
      maxHeight: '70vh',
      overflowY: 'auto',
      zIndex: 200,
    }}>
      {children}
    </div>
  );
}
