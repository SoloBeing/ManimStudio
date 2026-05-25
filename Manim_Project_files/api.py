import sys, os, json, shutil, threading, http.server, socket, platform

import webview

from renderer import QUALITY, RENDERS_DIR, RenderThread, validate_playground_source
import builders

_FPS_LIST = ["60", "30", "24", "15"]

_LATEX_WARNED_FLAG = os.path.join(os.path.expanduser("~"), "ManimStudio", "latex_warned")

_BUILDERS = {
    "trig":        builders.build_trig_source,
    "complex":     builders.build_complex_source,
    "linear":      builders.build_linear_source,
    "nonlinear":   builders.build_nonlinear_source,
    "code":        builders.build_code_source,
    "streamlines": builders.build_streamlines_source,
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


_MEDIA_SUBDIRS = ("videos", "images", "texts", "Tex")


class Api:
    def __init__(self):
        self._window      = None
        self._thread      = None
        self._lock        = threading.Lock()
        self._log_lines   = []
        self._status      = "idle"   # idle | rendering | done | error | stopped
        self._video_path  = ""
        self._render_stem = ""       # temp-file stem of the current/last render
        self._output_dir  = RENDERS_DIR

        self._http_port = _free_port()
        handler = lambda *a, **kw: _SilentHandler(*a, directory="/", **kw)
        srv = http.server.HTTPServer(("127.0.0.1", self._http_port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

    # ------------------------------------------------------------------
    # Called by app.py after window creation
    # ------------------------------------------------------------------

    def _set_window(self, window):
        self._window = window

    # ------------------------------------------------------------------
    # JS API
    # ------------------------------------------------------------------

    def get_system_info(self) -> dict:
        missing = [t for t in ("latex", "dvisvgm") if not shutil.which(t)]
        sys_name = platform.system()
        if sys_name == "Windows":
            install_cmd = "winget install TinyTeX-org.TinyTeX"
        elif sys_name == "Darwin":
            install_cmd = 'curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
        else:
            install_cmd = 'wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
        try:
            import glfw
            opengl_ok = True
        except ImportError:
            opengl_ok = False
        return {
            "latexOk":           len(missing) == 0,
            "latexMissing":      missing,
            "latexInstallCmd":   install_cmd,
            "latexWarnedBefore": os.path.exists(_LATEX_WARNED_FLAG),
            "openglOk":          opengl_ok,
            "outputDir":         self._output_dir,
            "qualities":         list(QUALITY.keys()),
            "fpsList":           _FPS_LIST,
            "httpPort":          self._http_port,
        }

    def dismiss_latex_warning(self) -> dict:
        try:
            os.makedirs(os.path.dirname(_LATEX_WARNED_FLAG), exist_ok=True)
            open(_LATEX_WARNED_FLAG, "w").close()
            return {"ok": True}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def render(self, mode: str, params_json: str, scene_name: str = "",
               quality: str = "Med  720p", fps: str = "30",
               opengl: bool = False) -> dict:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"ok": False, "error": "Render already in progress"}

        try:
            params = json.loads(params_json)
        except Exception as e:
            return {"ok": False, "error": f"Bad params: {e}"}

        if mode == "playground":
            source = params.get("source", "")
            if not source.strip():
                return {"ok": False, "error": "No source code provided"}
            err = validate_playground_source(source)
            if err:
                return {"ok": False, "error": f"[BLOCKED] {err}"}
        else:
            builder = _BUILDERS.get(mode)
            if not builder:
                return {"ok": False, "error": f"Unknown mode: {mode}"}
            try:
                source = builder(**params)
            except Exception as e:
                return {"ok": False, "error": f"Build error: {e}"}

        flags = list(QUALITY.get(quality, QUALITY["Med  720p"]))
        flags += ["--fps", fps.split()[0]]
        if opengl:
            flags += ["--renderer", "opengl", "--write_to_movie"]

        with self._lock:
            prev_stem        = self._render_stem
            self._log_lines.clear()
            self._status      = "rendering"
            self._video_path  = ""
            self._render_stem = ""

        self._cleanup_render_artifacts(prev_stem)
        self._push({"status": "rendering", "logLines": [], "videoUrl": ""})

        self._thread = RenderThread(
            source, flags, self._output_dir,
            scene_name=scene_name,
            on_log=self._on_log,
            on_done=self._on_done,
        )
        self._thread.start()
        return {"ok": True}

    def stop_render(self) -> dict:
        with self._lock:
            t = self._thread
        if t and t.is_alive():
            t.stop()
            t.join(timeout=5)
            with self._lock:
                self._status = "stopped"
            self._push({"status": "stopped"})
        return {"ok": True}

    def get_state(self) -> dict:
        with self._lock:
            lines            = list(self._log_lines)
            self._log_lines.clear()
            status     = self._status
            video_path = self._video_path
        return {
            "status":       status,
            "logLines":     lines,
            "videoPending": bool(video_path),
            "videoUrl":     self._video_url(video_path),
            "outputDir":    self._output_dir,
        }

    def browse_output_dir(self) -> str:
        if not self._window:
            return ""
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if result and len(result):
            self._output_dir = result[0]
            return result[0]
        return ""

    def save_render(self) -> dict:
        with self._lock:
            path = self._video_path
        if not path or not os.path.exists(path):
            return {"ok": False, "error": "No rendered video available"}
        if not self._window:
            return {"ok": False, "error": "No window"}
        ext  = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=name,
            file_types=(f"Video (*{ext})",),
        )
        if not result:
            return {"ok": False, "error": "Cancelled"}
        dest = result if isinstance(result, str) else result[0]
        try:
            shutil.copy2(path, dest)
        except OSError as e:
            return {"ok": False, "error": str(e)}
        with self._lock:
            stem              = self._render_stem
            self._video_path  = ""
            self._render_stem = ""
            self._status      = "idle"
        self._cleanup_render_artifacts(stem, keep_path=dest)
        return {"ok": True, "path": dest}

    def discard_render(self) -> dict:
        with self._lock:
            path              = self._video_path
            stem              = self._render_stem
            self._video_path  = ""
            self._render_stem = ""
            self._status      = "idle"
        self._cleanup_render_artifacts(stem)
        return {"ok": True}

    def confirm_close(self) -> dict:
        if self._window:
            self._window.destroy()
        return {"ok": True}

    # ------------------------------------------------------------------
    def cleanup(self):
        with self._lock:
            t    = self._thread
            stem = self._render_stem
        # During a render _render_stem is "", so fall back to the thread's stem
        if not stem and t is not None:
            stem = t.render_stem or ""
        if t and t.is_alive():
            t.stop()
            t.join(timeout=5)
        self._cleanup_render_artifacts(stem)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cleanup_render_artifacts(self, stem: str, keep_path: str = ""):
        if not stem:
            return
        keep = os.path.abspath(keep_path) if keep_path else ""
        out  = self._output_dir

        def _under(parent):
            try:
                return os.path.commonpath([keep, os.path.abspath(parent)]) == os.path.abspath(parent)
            except ValueError:
                return False

        for subdir in _MEDIA_SUBDIRS:
            d = os.path.join(out, subdir, stem)
            if keep and _under(d):
                continue
            shutil.rmtree(d, ignore_errors=True)

        # remove any empty parent dirs (videos/, images/, etc.) unless keep_path is inside
        for subdir in _MEDIA_SUBDIRS:
            d = os.path.join(out, subdir)
            if keep and _under(d):
                continue
            shutil.rmtree(d, ignore_errors=True)

    def _on_log(self, msg: str):
        with self._lock:
            self._log_lines.append(msg)
        self._push({"status": "rendering", "logLine": msg})

    def _on_done(self, video_path: str):
        stem = self._thread.render_stem if self._thread else ""
        if video_path:
            with self._lock:
                self._video_path  = video_path
                self._render_stem = stem
                self._status      = "done"
            self._push({"status": "done", "videoUrl": self._video_url(video_path)})
        else:
            with self._lock:
                status = self._status
            if status != "stopped":
                with self._lock:
                    self._status = "error"
                self._push({"status": "error"})
            self._cleanup_render_artifacts(stem)

    def _video_url(self, path: str) -> str:
        if not path:
            return ""
        return f"http://127.0.0.1:{self._http_port}{os.path.abspath(path)}"

    def ui_url(self, dist_index: str) -> str:
        return f"http://127.0.0.1:{self._http_port}{os.path.abspath(dist_index)}"

    def _push(self, state: dict):
        if not self._window:
            return
        try:
            payload = json.dumps(json.dumps(state))
            self._window.evaluate_js(
                f"window.__manimState && window.__manimState(JSON.parse({payload}))"
            )
        except Exception:
            pass
