import { useEffect, useRef, useState } from 'react';
import type { Mode, PanelHandle, RenderStatus, SystemInfo } from './types';
import { ActivityBar } from './components/ActivityBar';
import { Sidebar }     from './components/Sidebar';
import { MainArea }    from './components/MainArea';
import { BottomPanel } from './components/BottomPanel';
import { StatusBar }   from './components/StatusBar';
import './App.css';

function getApi() {
  if (window.pywebview) return window.pywebview.api;
  // dev stub — used when running in a plain browser without PyWebView
  return {
    get_system_info: async () => ({
      latexOk: true, openglOk: true,
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
  };
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

  const panelRef = useRef<PanelHandle>(null);

  // Register push callback and initialise system info
  useEffect(() => {
    window.__manimState = (state) => {
      if (state.status)  setStatus(state.status);
      if (state.videoUrl !== undefined) setVideoUrl(state.videoUrl);
      if (state.logLine)  setLogLines(prev => [...prev, state.logLine!]);
      if (state.logLines?.length) setLogLines(prev => [...prev, ...state.logLines!]);
    };

    function init() {
      getApi().get_system_info().then(info => {
        setSystemInfo(info);
        setQuality(info.qualities[1] ?? info.qualities[0]);
        setFps(info.fpsList[1] ?? info.fpsList[0]);
      });
    }

    if (window.pywebview) {
      // pywebview exists but bridge may not be ready — always wait for the event
      window.addEventListener('pywebviewready', init, { once: true } as EventListenerOptions);
    } else {
      // plain browser / dev mode — call immediately
      init();
    }

    return () => { window.__manimState = undefined; };
  }, []);

  async function handleRender() {
    const handle = panelRef.current;
    if (!handle) return;
    const { mode, params, sceneName } = handle.getParams();

    setLogLines([]);
    setVideoUrl('');
    setStatus('rendering');

    const result = await getApi().render(
      mode,
      JSON.stringify(params),
      sceneName ?? '',
      quality,
      fps.split(' ')[0],
      opengl,
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
    if (!result.ok && result.error !== 'Cancelled') {
      setLogLines(prev => [...prev, `[WARN] Save failed: ${result.error}`]);
    }
  }

  async function handleDiscard() {
    await getApi().discard_render();
    setVideoUrl('');
    setStatus('idle');
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div className="app-body">
        <ActivityBar active={activeMode} onChange={setActiveMode} />
        <Sidebar activeMode={activeMode} panelRef={panelRef} />
        <div className="main-content">
          <MainArea
            status={status}
            videoUrl={videoUrl}
            onSave={handleSave}
            onDiscard={handleDiscard}
          />
        </div>
      </div>
      <BottomPanel lines={logLines} />
      <StatusBar
        status={status}
        systemInfo={systemInfo}
        quality={quality}
        fps={fps}
        opengl={opengl}
        onQualityChange={setQuality}
        onFpsChange={setFps}
        onOpenglChange={setOpengl}
        onRender={handleRender}
        onStop={handleStop}
      />
    </div>
  );
}
