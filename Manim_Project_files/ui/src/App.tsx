import { useEffect, useRef, useState, type MouseEvent } from 'react';
import type { Mode, PanelHandle, RenderStatus, SystemInfo, Preset, RecentRender } from './types';
import { ActivityBar } from './components/ActivityBar';
import { Sidebar }     from './components/Sidebar';
import { MainArea }    from './components/MainArea';
import { BottomPanel } from './components/BottomPanel';
import { StatusBar }   from './components/StatusBar';
import { TopBar }      from './components/TopBar';
import { CloseDialog }  from './components/CloseDialog';
import { LaTeXDialog }  from './components/LaTeXDialog';
import { loadStoredSettings } from './components/panels/SettingsPanel';
import './App.css';

function getApi() {
  if (window.pywebview) return window.pywebview.api;
  return {
    get_system_info: async () => ({
      latexOk: true, latexMissing: [], latexInstallCmd: '', latexWarnedBefore: false,
      outputDir: '~/ManimStudio/renders',
      qualities: ['Low  480p', 'Med  720p', 'High 1080p', 'GIF'],
      fpsList: ['60', '30', '24', '15'],
      httpPort: 8080,
    }),
    render: async (): Promise<{ ok: boolean; error?: string }> => ({ ok: true }),
    stop_render: async () => ({ ok: true }),
    get_state: async () => ({ status: 'idle' as RenderStatus, logLines: [], videoPending: false, videoUrl: '', outputDir: '' }),
    browse_output_dir: async () => '',
    save_render: async (): Promise<{ ok: boolean; path?: string; error?: string }> => ({ ok: true }),
    discard_render: async () => ({ ok: true }),
    confirm_close: async () => ({ ok: true }),
    dismiss_latex_warning: async () => ({ ok: true }),
    load_render: async (): Promise<{ ok: boolean; videoUrl?: string; isImage?: boolean; error?: string }> => ({ ok: false }),
    get_recent_renders: async (): Promise<RecentRender[]> => [],
    add_recent_render: async (): Promise<{ ok: boolean; error?: string }> => ({ ok: true }),
    clear_recent_renders: async (): Promise<{ ok: boolean; error?: string }> => ({ ok: true }),
  };
}

function loadPresets(): Preset[] {
  try { return JSON.parse(localStorage.getItem('manim_presets') ?? '[]'); }
  catch { return []; }
}

export default function App() {
  const [activeMode, setActiveMode] = useState<Mode>('trig');
  const [status, setStatus]         = useState<RenderStatus>('idle');
  const [logLines, setLogLines]     = useState<string[]>([]);
  const [videoUrl, setVideoUrl]     = useState('');
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [quality, setQuality]       = useState('Med  720p');
  const [fps, setFps]               = useState('30');
  const [opengl, setOpengl]         = useState(false);
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const [outputDir, setOutputDir]   = useState('');
  const [latexDialog, setLatexDialog] = useState<{ missing: string[]; installCmd: string; withDontShow: boolean } | null>(null);

  const [presets, setPresets]             = useState<Preset[]>(loadPresets);
  const [recentRenders, setRecentRenders] = useState<RecentRender[]>([]);

  const panelRef      = useRef<PanelHandle>(null);
  const renderMetaRef = useRef<{ mode: string; quality: string; fps: string } | null>(null);

  const [sidebarWidth, setSidebarWidth] = useState(340);
  const [bottomHeight, setBottomHeight] = useState(160);
  const dragging    = useRef<'sidebar' | 'bottom' | null>(null);
  const dragStartX  = useRef(0);
  const dragStartY  = useRef(0);
  const dragStartW  = useRef(0);
  const dragStartH  = useRef(0);

  // Persist quality/fps/opengl on every change
  useEffect(() => {
    localStorage.setItem('manim_settings', JSON.stringify({ quality, fps, opengl }));
  }, [quality, fps, opengl]);

  useEffect(() => {
    function cancelDrag() {
      if (dragging.current) {
        dragging.current = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    }
    function onMove(e: globalThis.MouseEvent) {
      if (dragging.current === 'sidebar') {
        const w = dragStartW.current + (e.clientX - dragStartX.current);
        setSidebarWidth(Math.max(180, Math.min(600, w)));
      } else if (dragging.current === 'bottom') {
        const h = dragStartH.current - (e.clientY - dragStartY.current);
        setBottomHeight(Math.max(60, Math.min(500, h)));
      }
    }
    function onResize() {
      setSidebarWidth(w => Math.min(w, window.innerWidth - 400));
      setBottomHeight(h => Math.min(h, window.innerHeight - 160));
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', cancelDrag);
    window.addEventListener('blur', cancelDrag);
    window.addEventListener('resize', onResize);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', cancelDrag);
      window.removeEventListener('blur', cancelDrag);
      window.removeEventListener('resize', onResize);
    };
  }, []);

  function startSidebarDrag(e: MouseEvent<HTMLDivElement>) {
    dragging.current   = 'sidebar';
    dragStartX.current = e.clientX;
    dragStartW.current = sidebarWidth;
    document.body.style.cursor     = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }

  function startBottomDrag(e: MouseEvent<HTMLDivElement>) {
    dragging.current   = 'bottom';
    dragStartY.current = e.clientY;
    dragStartH.current = bottomHeight;
    document.body.style.cursor     = 'row-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }

  useEffect(() => {
    window.__manimState = (state) => {
      if (state.status)   setStatus(state.status);
      if (state.videoUrl !== undefined) setVideoUrl(state.videoUrl);
      if (state.logLine)  setLogLines(prev => [...prev, state.logLine!]);
      if (state.logLines?.length) setLogLines(prev => [...prev, ...state.logLines!]);
      if (state.showCloseDialog)  setShowCloseDialog(true);
    };

    function init() {
      Promise.all([
        getApi().get_system_info(),
        getApi().get_recent_renders(),
      ]).then(([info, recent]) => {
        setSystemInfo(info);
        setOutputDir(info.outputDir);
        setRecentRenders(recent);
        const stored = loadStoredSettings();
        setQuality(stored.quality ?? info.qualities[1] ?? info.qualities[0]);
        setFps(stored.fps ?? info.fpsList[1] ?? info.fpsList[0]);
        if (stored.opengl !== undefined) setOpengl(stored.opengl);
        if (info.latexMissing.length > 0 && !info.latexWarnedBefore) {
          setLatexDialog({ missing: info.latexMissing, installCmd: info.latexInstallCmd, withDontShow: true });
        }
      });
    }

    if (window.pywebview) {
      window.addEventListener('pywebviewready', init, { once: true } as EventListenerOptions);
    } else {
      init();
    }

    return () => { window.__manimState = undefined; };
  }, []);

  // Poll get_state() while rendering — evaluate_js from background threads is
  // unreliable on Windows while the subprocess is running, so log lines are
  // accumulated server-side and fetched here instead of pushed individually.
  useEffect(() => {
    if (status !== 'rendering') return;
    const flush = () =>
      getApi().get_state().then(s => {
        if (s.logLines?.length) setLogLines(prev => [...prev, ...s.logLines!]);
      });
    const id = setInterval(flush, 500);
    return () => { clearInterval(id); flush(); };
  }, [status]);

  async function handleRender() {
    const handle = panelRef.current;
    if (!handle) return;
    const { mode, params, sceneName } = handle.getParams();
    renderMetaRef.current = { mode, quality, fps };
    setLogLines([]);
    setVideoUrl('');
    setStatus('rendering');
    const result = await getApi().render(
      mode, JSON.stringify(params), sceneName ?? '', quality, fps.split(' ')[0], opengl,
    );
    if (!result.ok) {
      setLogLines(prev => [...prev, `[ERROR] ${result.error}`]);
      setStatus('error');
    }
  }

  async function handleStop() {
    await getApi().stop_render();
  }

  async function handleSave() {
    const result = await getApi().save_render();
    if (result.ok && result.path && renderMetaRef.current) {
      const { mode, quality: q, fps: f } = renderMetaRef.current;
      const entry: RecentRender = {
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        mode, quality: q, fps: f,
        path: result.path,
        isImage: result.path.endsWith('.png'),
      };
      await getApi().add_recent_render(JSON.stringify(entry));
      setRecentRenders(prev => [entry, ...prev].slice(0, 20));
    } else if (!result.ok && result.error !== 'Cancelled') {
      setLogLines(prev => [...prev, `[WARN] Save failed: ${result.error}`]);
    }
  }

  async function handleDiscard() {
    await getApi().discard_render();
    setVideoUrl('');
    setStatus('idle');
  }

  async function handleCloseSave() {
    setShowCloseDialog(false);
    await getApi().save_render();
    await getApi().confirm_close();
  }

  async function handleCloseDiscard() {
    setShowCloseDialog(false);
    await getApi().discard_render();
    await getApi().confirm_close();
  }

  function handleCloseCancel() {
    setShowCloseDialog(false);
  }

  async function handleBrowseOutput() {
    const chosen = await getApi().browse_output_dir();
    if (chosen) setOutputDir(chosen);
  }

  async function handleLatexDismiss(dontShowAgain: boolean) {
    if (dontShowAgain) await getApi().dismiss_latex_warning();
    setLatexDialog(null);
  }

  function handleLatexNotice() {
    const info = systemInfo;
    if (info && info.latexMissing.length > 0) {
      setLatexDialog({ missing: info.latexMissing, installCmd: info.latexInstallCmd, withDontShow: false });
    }
  }

  // Preset management
  function handleSavePreset(name: string) {
    const p: Preset = { id: crypto.randomUUID(), name, quality, fps, opengl };
    const next = [p, ...presets];
    setPresets(next);
    localStorage.setItem('manim_presets', JSON.stringify(next));
  }

  function handleDeletePreset(id: string) {
    const next = presets.filter(p => p.id !== id);
    setPresets(next);
    localStorage.setItem('manim_presets', JSON.stringify(next));
  }

  function handleApplyPreset(p: Preset) {
    setQuality(p.quality);
    setFps(p.fps);
    setOpengl(p.opengl);
  }

  // Recent renders
  async function handleLoadRender(r: RecentRender) {
    const result = await getApi().load_render(r.path);
    if (result.ok && result.videoUrl) {
      setVideoUrl(result.videoUrl);
      setStatus('done');
    } else {
      setLogLines(prev => [...prev, `[WARN] Could not load: ${result.error ?? 'File not found'}`]);
    }
  }

  async function handleClearRecent() {
    await getApi().clear_recent_renders();
    setRecentRenders([]);
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {showCloseDialog && (
        <CloseDialog onSave={handleCloseSave} onDiscard={handleCloseDiscard} onCancel={handleCloseCancel} />
      )}
      {latexDialog && (
        <LaTeXDialog
          missing={latexDialog.missing} installCmd={latexDialog.installCmd}
          withDontShow={latexDialog.withDontShow} onDismiss={handleLatexDismiss}
        />
      )}

      <TopBar
        systemInfo={systemInfo} quality={quality} fps={fps} opengl={opengl} outputDir={outputDir}
        onQualityChange={setQuality} onFpsChange={setFps} onOpenglChange={setOpengl}
        onBrowseOutput={handleBrowseOutput}
        presets={presets}
        onApplyPreset={handleApplyPreset} onSavePreset={handleSavePreset} onDeletePreset={handleDeletePreset}
        recentRenders={recentRenders} onLoadRender={handleLoadRender} onClearRecent={handleClearRecent}
      />

      <div className="app-body">
        <ActivityBar active={activeMode} onChange={setActiveMode} />
        <div style={{ width: sidebarWidth, flexShrink: 0, overflow: 'hidden', display: 'flex' }}>
          <Sidebar activeMode={activeMode} panelRef={panelRef} />
        </div>
        <div className="resize-handle resize-handle--vertical" onMouseDown={startSidebarDrag} />
        <div className="main-content">
          <MainArea status={status} videoUrl={videoUrl} onSave={handleSave} onDiscard={handleDiscard} />
        </div>
      </div>
      <BottomPanel lines={logLines} logHeight={bottomHeight} onResizeStart={startBottomDrag} />
      <StatusBar
        status={status} systemInfo={systemInfo}
        onRender={handleRender} onStop={handleStop} onLatexNotice={handleLatexNotice}
      />
    </div>
  );
}
