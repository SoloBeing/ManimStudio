export type Mode = 'trig' | 'complex' | 'linear' | 'code' | 'streamlines' | 'playground';
export type RenderStatus = 'idle' | 'rendering' | 'done' | 'error' | 'stopped';

export interface SystemInfo {
  latexOk: boolean;
  latexMissing: string[];
  latexInstallCmd: string;
  latexWarnedBefore: boolean;
  openglOk: boolean;
  outputDir: string;
  qualities: string[];
  fpsList: string[];
  httpPort: number;
}

export interface TextParams {
  text_content: string;
  text_position: string;
  text_color: string;
  text_font: string;
  text_font_size: number;
  show_preset_labels: boolean;
  bold: boolean;
  italic: boolean;
  stroke_width: number;
  stroke_color: string;
  x_offset: number;
  y_offset: number;
  gradient: string;
}

export const DEFAULT_TEXT: TextParams = {
  text_content: '',
  text_position: 'top_left',
  text_color: 'white',
  text_font: 'Arial',
  text_font_size: 22,
  show_preset_labels: true,
  bold: false,
  italic: false,
  stroke_width: 0,
  stroke_color: 'white',
  x_offset: 0,
  y_offset: 0,
  gradient: 'none',
};

export interface PanelHandle {
  getParams(): { mode: string; params: object; sceneName?: string };
}

export interface PyWebViewApi {
  get_system_info: () => Promise<SystemInfo>;
  render: (
    mode: string,
    params_json: string,
    scene_name?: string,
    quality?: string,
    fps?: string,
    opengl?: boolean,
  ) => Promise<{ ok: boolean; error?: string }>;
  stop_render: () => Promise<{ ok: boolean }>;
  get_state: () => Promise<{
    status: RenderStatus;
    logLines: string[];
    videoPending: boolean;
    videoUrl: string;
    outputDir: string;
  }>;
  browse_output_dir: () => Promise<string>;
  save_render: () => Promise<{ ok: boolean; path?: string; error?: string }>;
  discard_render: () => Promise<{ ok: boolean }>;
  confirm_close: () => Promise<{ ok: boolean }>;
  dismiss_latex_warning: () => Promise<{ ok: boolean; error?: string }>;
}

declare global {
  interface Window {
    pywebview?: { api: PyWebViewApi };
    __manimState?: (state: {
      status?: RenderStatus;
      logLine?: string;
      logLines?: string[];
      videoUrl?: string;
      showCloseDialog?: boolean;
    }) => void;
  }
}
