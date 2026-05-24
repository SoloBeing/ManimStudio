import sys, os, json, shutil, threading, http.server, socket

import webview

from renderer import QUALITY, RENDERS_DIR, RenderThread
import builders

_FPS_LIST = ["60", "30", "24", "15"]

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


class Api:
    def __init__(self):
        self._window     = None
        self._thread     = None
        self._lock       = threading.Lock()
        self._log_lines  = []
        self._status     = "idle"   # idle | rendering | done | error | stopped
        self._video_path = ""
        self._output_dir = RENDERS_DIR

        self._http_port = _free_port()
        handler = lambda *a, **kw: _SilentHandler(
            *a, directory=os.path.expanduser("~"), **kw
        )
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
        latex_ok = bool(shutil.which("latex") or shutil.which("pdflatex"))
        try:
            import glfw
            opengl_ok = True
        except ImportError:
            opengl_ok = False
        return {
            "latexOk":   latex_ok,
            "openglOk":  opengl_ok,
            "outputDir": self._output_dir,
            "qualities": list(QUALITY.keys()),
            "fpsList":   _FPS_LIST,
            "httpPort":  self._http_port,
        }

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
            self._log_lines.clear()
            self._status     = "rendering"
            self._video_path = ""

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
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
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
            webview.SAVE_DIALOG,
            save_filename=name,
            file_types=(f"Video (*{ext})",),
        )
        if not result:
            return {"ok": False, "error": "Cancelled"}
        dest = result if isinstance(result, str) else result[0]
        try:
            shutil.copy2(path, dest)
            return {"ok": True, "path": dest}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def discard_render(self) -> dict:
        with self._lock:
            path             = self._video_path
            self._video_path = ""
            self._status     = "idle"
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass
        return {"ok": True}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_log(self, msg: str):
        with self._lock:
            self._log_lines.append(msg)
        self._push({"status": "rendering", "logLine": msg})

    def _on_done(self, video_path: str):
        if video_path:
            with self._lock:
                self._video_path = video_path
                self._status     = "done"
            self._push({"status": "done", "videoUrl": self._video_url(video_path)})
        else:
            with self._lock:
                status = self._status
            if status != "stopped":
                with self._lock:
                    self._status = "error"
                self._push({"status": "error"})

    def _video_url(self, path: str) -> str:
        if not path:
            return ""
        try:
            rel = os.path.relpath(path, os.path.expanduser("~"))
            return f"http://127.0.0.1:{self._http_port}/{rel}"
        except ValueError:
            return ""

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
