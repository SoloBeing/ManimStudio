import sys, os, re, json, shutil, threading, http.server, socket, platform
import hashlib, time

import webview

from renderer import (
    QUALITY, FORMATS, DEFAULT_FORMAT, RENDERS_DIR, RenderThread,
    validate_playground_source, get_worker, shutdown_worker,
)
import builders

# Transcoded webm previews for formats Qt WebEngine can't decode (mp4/mov)
# live here, keyed by source path+mtime+size so they can be reused and are
# easy to purge wholesale on shutdown.
_PREVIEW_DIR = os.path.join(os.path.expanduser("~"), "ManimStudio", "previews")

# User-facing activity log: every action that crosses the JS→Python bridge
# (renders, saves, discards, loads, setting changes) gets a timestamped line,
# appended across sessions. Distinct from crash.log (startup/exceptions) and
# the per-render build log (Manim output).
_ACTIVITY_LOG = os.path.join(os.path.expanduser("~"), "ManimStudio", "activity.log")
_ACTIVITY_CAP = 1_000_000  # bytes; above this the oldest half is trimmed at startup

_activity_lock = threading.Lock()


def _log_activity(msg: str):
    """Append a timestamped line to the activity log. Never raises — a logging
    failure must not break the user action being logged."""
    try:
        with _activity_lock:
            os.makedirs(os.path.dirname(_ACTIVITY_LOG), exist_ok=True)
            with open(_ACTIVITY_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _trim_activity_log():
    """Keep activity.log bounded: once it grows past _ACTIVITY_CAP, drop the
    oldest entries and keep the most recent ~half, starting at a line boundary."""
    try:
        with _activity_lock:
            if os.path.getsize(_ACTIVITY_LOG) <= _ACTIVITY_CAP:
                return
            with open(_ACTIVITY_LOG, "rb") as f:
                f.seek(-(_ACTIVITY_CAP // 2), os.SEEK_END)
                tail = f.read()
            tail = tail[tail.find(b"\n") + 1:]
            with open(_ACTIVITY_LOG, "wb") as f:
                f.write(b"[older entries trimmed]\n" + tail)
    except OSError:
        pass


_FPS_LIST = ["60", "30", "24", "15"]

def _fs_to_url_path(path: str) -> str:
    """Convert a filesystem path to a URL path component.

    On Linux/macOS, os.path.abspath already starts with '/'.
    On Windows it starts with 'C:\\...' — no leading slash and backslashes —
    producing a malformed URL like 'http://host:portC:\\...'.
    Fix: forward-slash the path and ensure a leading '/'.
    """
    p = os.path.abspath(path).replace("\\", "/")
    return p if p.startswith("/") else "/" + p

_LATEX_WARNED_FLAG  = os.path.join(os.path.expanduser("~"), "ManimStudio", "latex_warned")
_RECENT_RENDERS_FILE = os.path.join(os.path.expanduser("~"), "ManimStudio", "recent_renders.json")

# Manim objects/methods that render text through LaTeX (latex + dvisvgm). A
# scene using any of these will fail at render time if LaTeX isn't installed,
# so we preflight the generated source for them. Plain Text()/MarkupText() use
# Pango and need no LaTeX, so they're intentionally absent. Word boundaries
# keep Text/MarkupText from matching the bare "Tex" token.
_LATEX_TOKENS = (
    "MathTex", "Tex", "SingleStringMathTex",
    "DecimalNumber", "Integer", "Variable", "Title",
    "Matrix", "IntegerMatrix", "DecimalMatrix",
    "BraceLabel", "BraceText",
    "MathTable", "IntegerTable", "DecimalTable",
    "add_coordinates", "add_numbers",
    "get_axis_labels", "get_axis_label",
    "get_x_axis_label", "get_y_axis_label", "get_graph_label",
)
_LATEX_RE = re.compile(r"\b(?:" + "|".join(_LATEX_TOKENS) + r")\b")


def _source_needs_latex(source: str) -> bool:
    """True if the generated Manim source uses any LaTeX-rendered construct."""
    return bool(_LATEX_RE.search(source or ""))


def _latex_install_cmd() -> str:
    sys_name = platform.system()
    if sys_name == "Windows":
        return "winget install TinyTeX-org.TinyTeX"
    if sys_name == "Darwin":
        return 'curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
    return 'wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh'

_BUILDERS = {
    "trig":        builders.build_trig_source,
    "complex":     builders.build_complex_source,
    "linear":      builders.build_linear_source,
    "nonlinear":   builders.build_nonlinear_source,
    "code":        builders.build_code_source,
    "streamlines": builders.build_streamlines_source,
    "geometry":    builders.build_geometry_source,
    "barchart":    builders.build_barchart_source,
    "surface3d":   builders.build_surface3d_source,
    "numberline":  builders.build_numberline_source,
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
        _trim_activity_log()
        _log_activity(f"=== Session started ({platform.platform()}) ===")
        self._window      = None
        self._thread      = None
        self._lock        = threading.Lock()
        self._session_ended = False  # one-shot guard for the session-end log line
        self._log_lines   = []
        self._status      = "idle"   # idle | rendering | done | error | stopped
        self._video_path  = ""       # real output file (what Save copies)
        self._preview_path = ""      # WebEngine-playable file the preview loads
        self._render_stem = ""       # temp-file stem of the current/last render
        self._render_saved = False   # True once the current render has been saved
        self._render_needs_proxy = False  # current format needs a webm preview
        self._render_is_loaded = False    # current item was opened via load_render
        self._render_opengl = False       # OpenGL renderer requested for current render
        self._init_hint_emitted = False   # one-shot guard for the OpenGL __init__ hint
        self._output_dir  = RENDERS_DIR
        # Directories the HTTP server is allowed to serve; updated when the
        # output dir changes or the UI dist path is registered via ui_url().
        self._allowed_dirs = [os.path.abspath(RENDERS_DIR), os.path.abspath(_PREVIEW_DIR)]

        self._latex_missing = [t for t in ("latex", "dvisvgm") if not shutil.which(t)]

        self._http_port = _free_port()
        _allowed = self._allowed_dirs  # closure reference — stays live as list mutates

        class _RestrictedHandler(_SilentHandler):
            if sys.platform == "win32":
                def translate_path(self, path):
                    # SimpleHTTPRequestHandler.translate_path with directory="/"
                    # breaks on Windows: os.path.join("/", "C:") gives "C:" (relative)
                    # not "C:\" (absolute). Handle drive-letter URLs directly.
                    import urllib.parse, posixpath
                    path = path.split('?', 1)[0].split('#', 1)[0]
                    path = urllib.parse.unquote(path)
                    path = posixpath.normpath(path).lstrip('/')
                    return path.replace('/', os.sep)

            def _is_allowed(self) -> bool:
                # Every entry in _allowed is stored already-absolute (see Api
                # __init__, browse_output_dir, ui_url, load_render), so there's
                # no need to re-abspath each one on every request.
                fs = os.path.abspath(self.translate_path(self.path))
                return any(fs == d or fs.startswith(d + os.sep) for d in _allowed)
            def do_GET(self):
                if not self._is_allowed(): self.send_error(403); return
                super().do_GET()
            def do_HEAD(self):
                if not self._is_allowed(): self.send_error(403); return
                super().do_HEAD()
            def send_response(self, code, message=None):
                self._status_code = code
                super().send_response(code, message)
            def end_headers(self):
                # Let the browser cache served media so replay/scrubbing (Range
                # requests) doesn't refetch from disk each time. Only on success
                # responses — never cache a 403/404.
                if getattr(self, "_status_code", None) in (200, 206, 304):
                    self.send_header("Cache-Control", "max-age=600")
                super().end_headers()

        handler = lambda *a, **kw: _RestrictedHandler(*a, directory="/", **kw)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", self._http_port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        # Pre-warm the Manim worker in the background so the ~1s+ import cost is
        # paid before the first render (POSIX only; Windows uses the cold path).
        threading.Thread(target=self._prewarm_worker, daemon=True).start()

    def _prewarm_worker(self):
        try:
            w = get_worker()
            if w is not None:
                w.ensure_started()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Called by app.py after window creation
    # ------------------------------------------------------------------

    def _set_window(self, window):
        self._window = window

    # ------------------------------------------------------------------
    # JS API
    # ------------------------------------------------------------------

    def get_system_info(self) -> dict:
        missing = self._latex_missing
        return {
            "latexOk":           len(missing) == 0,
            "latexMissing":      missing,
            "latexInstallCmd":   _latex_install_cmd(),
            "latexWarnedBefore": os.path.exists(_LATEX_WARNED_FLAG),
            "outputDir":         self._output_dir,
            "qualities":         list(QUALITY.keys()),
            "formats":           list(FORMATS.keys()),
            "defaultFormat":     DEFAULT_FORMAT,
            "fpsList":           _FPS_LIST,
            "httpPort":          self._http_port,
        }

    def dismiss_latex_warning(self) -> dict:
        try:
            os.makedirs(os.path.dirname(_LATEX_WARNED_FLAG), exist_ok=True)
            open(_LATEX_WARNED_FLAG, "w").close()
            _log_activity("LaTeX warning dismissed")
            return {"ok": True}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def render(self, mode: str, params_json: str, scene_name: str = "",
               quality: str = "Med  720p", fps: str = "30",
               opengl: bool = False, fmt: str = DEFAULT_FORMAT) -> dict:
        _log_activity(
            f"Render requested: mode={mode}, scene={scene_name or '(default)'}, "
            f"quality={quality}, fps={fps}, format={fmt}, opengl={opengl}"
        )
        result = self._render_impl(mode, params_json, scene_name, quality, fps,
                                   opengl, fmt)
        if result.get("ok"):
            _log_activity("Render started")
        else:
            _log_activity(f"Render rejected: {result.get('error', 'unknown')}")
        return result

    # Underscore prefix keeps this off the JS bridge — render() above is the
    # public entry point and logs the request/outcome around it.
    def _render_impl(self, mode: str, params_json: str, scene_name: str,
                     quality: str, fps: str, opengl: bool, fmt: str) -> dict:
        with self._lock:
            t = self._thread
        if t and t.is_alive():
            if not getattr(t, "_stopped", False):
                return {"ok": False, "error": "Render already in progress"}
            # A previous render was cancelled but hasn't fully wound down yet.
            # Re-assert the cancel (idempotent) and wait it out — the worker
            # force-kills within ~2s, so this returns promptly rather than
            # rejecting the user's re-run.
            t.stop()
            t.join(timeout=8)
            if t.is_alive():
                return {"ok": False,
                        "error": "Previous render did not stop; please retry"}

        try:
            params = json.loads(params_json)
        except Exception as e:
            return {"ok": False, "error": f"Bad params: {e}"}

        if scene_name and not re.match(r'^[A-Za-z_]\w*$', scene_name):
            return {"ok": False, "error": f"Invalid scene name: {scene_name!r}"}

        fps_val = fps.split()[0] if fps.split() else ""
        if fps_val not in set(_FPS_LIST):
            return {"ok": False, "error": f"Invalid fps: {fps_val!r}"}

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

        # Preflight: a scene using MathTex/Tex/coordinates needs LaTeX. Block it
        # up front (rather than letting Manim fail mid-render) so the UI can show
        # the install instructions instead of a cryptic LaTeX traceback.
        if self._latex_missing and _source_needs_latex(source):
            return {
                "ok":              False,
                "latexRequired":   True,
                "latexMissing":    self._latex_missing,
                "latexInstallCmd": _latex_install_cmd(),
                "error":           "This animation uses LaTeX (MathTex/Tex/coordinate "
                                   "labels), but LaTeX is not installed.",
            }

        if fmt not in FORMATS:
            return {"ok": False, "error": f"Invalid format: {fmt!r}"}
        fmt_flags, _ext, needs_proxy = FORMATS[fmt]

        flags = list(QUALITY.get(quality, QUALITY["Med  720p"])) + list(fmt_flags)
        flags += ["--fps", fps_val]
        if opengl:
            flags += ["--renderer", "opengl", "--write_to_movie"]

        with self._lock:
            prev_stem        = "" if self._render_is_loaded else self._render_stem
            self._log_lines.clear()
            self._status      = "rendering"
            self._video_path  = ""
            self._preview_path = ""
            self._render_needs_proxy = needs_proxy
            self._render_is_loaded = False
            self._render_opengl = opengl
            self._init_hint_emitted = False
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
            t.join(timeout=6)
            dead = not t.is_alive()
            with self._lock:
                self._status = "stopped"
                # Drop the reference once it's actually dead so a re-run isn't
                # blocked by a stale "in progress" check on a finished thread.
                if dead:
                    self._thread = None
            self._push({"status": "stopped"})
            # _on_done never runs on a cancelled render, so its partial movie
            # files would otherwise leak (self._render_stem is "" mid-render).
            # Clean them up here using the thread's real stem, once the render
            # child is confirmed dead and can no longer be writing to them.
            if dead:
                self._cleanup_render_artifacts(getattr(t, "render_stem", "") or "")
            _log_activity("Render stopped by user")
        return {"ok": True}

    def get_state(self) -> dict:
        with self._lock:
            lines            = list(self._log_lines)
            self._log_lines.clear()
            status       = self._status
            video_path   = self._video_path
            preview_path = self._preview_path or self._video_path
        return {
            "status":       status,
            "logLines":     lines,
            "videoPending": bool(video_path),
            "videoUrl":     self._video_url(preview_path),
            "outputDir":    self._output_dir,
        }

    def browse_output_dir(self) -> str:
        if not self._window:
            return ""
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if result and len(result):
            new_dir = os.path.abspath(result[0])
            old_dir = os.path.abspath(self._output_dir)
            if old_dir in self._allowed_dirs:
                self._allowed_dirs.remove(old_dir)
            if new_dir not in self._allowed_dirs:
                self._allowed_dirs.append(new_dir)
            self._output_dir = result[0]
            _log_activity(f"Output directory changed: {result[0]}")
            return result[0]
        return ""

    def save_render(self) -> dict:
        with self._lock:
            path = self._video_path
        if not path or not os.path.exists(path):
            return {"ok": False, "error": "No rendered video available"}
        if not self._window:
            return {"ok": False, "error": "No window"}
        ext   = os.path.splitext(path)[1].lower()
        name  = os.path.basename(path)
        label = "Image" if ext in (".png", ".gif", ".jpg", ".jpeg") else "Video"
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=name,
            file_types=(f"{label} (*{ext})",),
        )
        if not result:
            _log_activity("Save cancelled")
            return {"ok": False, "error": "Cancelled"}
        dest = result if isinstance(result, str) else result[0]
        try:
            shutil.copy2(path, dest)
        except OSError as e:
            _log_activity(f"Save failed: {e}")
            return {"ok": False, "error": str(e)}
        # Keep the render available so it can be saved again (e.g. to another
        # location). State and temp artifacts are cleared by discard_render,
        # the next render, or app cleanup.
        with self._lock:
            self._render_saved = True
        _log_activity(f"Render saved to {dest}")
        return {"ok": True, "path": dest}

    def discard_render(self) -> dict:
        with self._lock:
            # A loaded item is an external file we don't own — never clean it up.
            stem               = "" if self._render_is_loaded else self._render_stem
            self._video_path   = ""
            self._preview_path = ""
            self._render_stem  = ""
            self._render_is_loaded = False
            self._status       = "idle"
        self._cleanup_render_artifacts(stem)
        _log_activity("Render discarded")
        return {"ok": True}

    def confirm_close(self) -> dict:
        _log_activity("Window close confirmed (unsaved render abandoned)")
        if self._window:
            self._window.destroy()
        return {"ok": True}

    def get_recent_renders(self) -> list:
        try:
            with open(_RECENT_RENDERS_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def add_recent_render(self, entry_json: str) -> dict:
        try:
            entry   = json.loads(entry_json)
            renders = self.get_recent_renders()
            renders = [entry] + renders
            renders = renders[:20]
            os.makedirs(os.path.dirname(_RECENT_RENDERS_FILE), exist_ok=True)
            with open(_RECENT_RENDERS_FILE, "w") as f:
                json.dump(renders, f)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_recent_renders(self) -> dict:
        try:
            if os.path.exists(_RECENT_RENDERS_FILE):
                os.remove(_RECENT_RENDERS_FILE)
            _log_activity("Recent renders cleared")
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_render(self, path: str) -> dict:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            _log_activity(f"Load recent render failed (file not found): {path}")
            return {"ok": False, "error": "File not found"}
        with self._lock:
            if self._thread and self._thread.is_alive():
                _log_activity("Load recent render refused: render in progress")
                return {"ok": False, "error": "Stop the current render before loading"}
        abs_path = os.path.abspath(path)
        is_image = abs_path.lower().endswith((".png", ".gif", ".jpg", ".jpeg"))
        # mp4/mov can't play in the preview pane — load a webm proxy instead.
        disp_path = self._previewable_path(abs_path)
        for d in {os.path.dirname(abs_path), os.path.dirname(disp_path)}:
            if d not in self._allowed_dirs:
                self._allowed_dirs.append(d)
        # Adopt the loaded file as the current item so Save/Discard act on what
        # is actually shown. It already exists on disk (an external user file),
        # so mark it saved (no unsaved-close prompt) and loaded (Discard/cleanup
        # must never delete it — only renders own their temp artifacts).
        with self._lock:
            prev_stem            = "" if self._render_is_loaded else self._render_stem
            self._video_path     = abs_path
            self._preview_path   = disp_path
            self._render_stem    = ""
            self._render_is_loaded = True
            self._render_saved   = True
            self._status         = "done"
        # keep_path guards the rare case of loading a file that lives under the
        # previous render's own stem (don't delete what we're about to show).
        self._cleanup_render_artifacts(prev_stem, keep_path=abs_path)
        _log_activity(f"Loaded recent render: {abs_path}")
        return {"ok": True, "videoUrl": self._video_url(disp_path), "isImage": is_image}

    # ------------------------------------------------------------------
    def cleanup(self):
        with self._lock:
            t    = self._thread
            stem = self._render_stem
            already_ended = self._session_ended
            self._session_ended = True
        # cleanup can run twice (atexit + SIGTERM handler) — log the end once
        if not already_ended:
            _log_activity("=== Session ended ===")
        # During a render _render_stem is "", so fall back to the thread's stem
        if not stem and t is not None:
            stem = t.render_stem or ""
        if t and t.is_alive():
            t.stop()
            t.join(timeout=5)
        self._cleanup_render_artifacts(stem)
        shutil.rmtree(_PREVIEW_DIR, ignore_errors=True)
        try:
            shutdown_worker()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _previewable_path(self, path: str) -> str:
        """Return a path the Qt WebEngine preview can display.

        mp4/mov carry H.264 the preview pane can't decode, so they're
        transcoded to a cached webm. Everything else (webm/gif/png) plays
        natively and is returned unchanged. On any failure the original
        path is returned — the file still Saves fine, only preview is lost.
        """
        if not path:
            return path
        if os.path.splitext(path)[1].lower() not in (".mp4", ".mov"):
            return path
        try:
            st  = os.stat(path)
            key = hashlib.md5(
                f"{os.path.abspath(path)}|{st.st_mtime_ns}|{st.st_size}".encode()
            ).hexdigest()
        except OSError:
            return path
        proxy = os.path.join(_PREVIEW_DIR, key + ".webm")
        if os.path.exists(proxy):
            return proxy
        return proxy if self._transcode_webm(path, proxy) else path

    def _transcode_webm(self, src: str, dst: str) -> bool:
        # Transcode via PyAV (bundled by manim — manim v0.20 encodes through
        # `av`, so libvpx VP8/VP9 + H.264 decode are guaranteed present in the
        # frozen build). Deliberately NOT shelling out to an ffmpeg binary: the
        # PyInstaller bundle ships none, so a CLI call would leave mp4/mov
        # preview blank on end-user machines without system ffmpeg.
        try:
            import av
        except Exception:
            self._on_log("[WARN] PyAV unavailable — preview unavailable for this format")
            return False
        try:
            os.makedirs(_PREVIEW_DIR, exist_ok=True)
        except OSError:
            return False
        tmp = dst + ".part"
        self._on_log("[INFO] generating preview…")
        ok = False
        try:
            with av.open(src) as inp, av.open(tmp, mode="w", format="webm") as out:
                ist = inp.streams.video[0]
                w, h = ist.codec_context.width, ist.codec_context.height
                ost = out.add_stream("libvpx", rate=ist.average_rate or 30)
                ost.width, ost.height, ost.pix_fmt = w, h, "yuv420p"
                ost.options = {"deadline": "realtime", "cpu-used": "5", "b": "1M"}
                for frame in inp.decode(ist):
                    frame = frame.reformat(width=w, height=h, format="yuv420p")
                    for pkt in ost.encode(frame):
                        out.mux(pkt)
                for pkt in ost.encode():
                    out.mux(pkt)
            ok = os.path.exists(tmp)
        except Exception as e:
            self._on_log(f"[WARN] preview transcode failed: {e}")
            ok = False
        if ok:
            try:
                os.replace(tmp, dst)
            except OSError:
                ok = False
        if not ok:
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            except OSError:
                pass
            self._on_log("[WARN] preview transcode failed — file still saves correctly")
        return ok

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

        # Remove the now-empty parent dirs (videos/, images/, etc.) unless
        # keep_path is inside. os.rmdir — NOT shutil.rmtree — so a parent that
        # still holds other renders' output, or a user-chosen output dir that
        # already contains its own same-named videos/images/texts/Tex folder, is
        # never wiped: rmdir only succeeds on an empty dir and is a no-op otherwise.
        for subdir in _MEDIA_SUBDIRS:
            d = os.path.join(out, subdir)
            if keep and _under(d):
                continue
            try:
                os.rmdir(d)
            except OSError:
                pass  # non-empty (siblings / user files) or missing — leave it

    @staticmethod
    def _stamp(msg: str) -> str:
        # Prefix a [HH:MM:SS] timestamp so build-log lines can be correlated.
        # Blank/whitespace spacer lines (manim emits many for formatting) are
        # left untouched so they stay visually dim and uncluttered.
        if not msg.strip():
            return msg
        return f"[{time.strftime('%H:%M:%S')}] {msg}"

    def _on_log(self, msg: str):
        with self._lock:
            self._log_lines.append(self._stamp(msg))
            # The OpenGL render path constructs scenes as SceneClass(renderer),
            # passing renderer positionally — so a custom __init__ that doesn't
            # accept a positional arg fails with this exact TypeError. Cairo
            # doesn't, so the same scene works from the CLI. Turn the cryptic
            # traceback into an actionable hint.
            if (self._render_opengl and not self._init_hint_emitted
                    and "__init__()" in msg and "positional argument" in msg):
                self._init_hint_emitted = True
                self._log_lines.append(self._stamp(
                    "[HINT] OpenGL passes the renderer to your scene positionally. "
                    "Give your scene 'def __init__(self, *args, **kwargs): "
                    "super().__init__(*args, ...)', or turn off OpenGL in Settings."
                ))

    def _on_done(self, video_path: str):
        stem = self._thread.render_stem if self._thread else ""
        if video_path:
            with self._lock:
                need_proxy = self._render_needs_proxy
            preview_path = self._previewable_path(video_path) if need_proxy else video_path
            with self._lock:
                self._video_path   = video_path
                self._preview_path = preview_path
                self._render_stem  = stem
                self._render_saved = False
                self._status       = "done"
            self._push({"status": "done", "videoUrl": self._video_url(preview_path)})
            _log_activity(f"Render finished: {video_path}")
        else:
            with self._lock:
                status = self._status
            if status != "stopped":
                with self._lock:
                    self._status = "error"
                self._push({"status": "error"})
                _log_activity("Render failed")
            self._cleanup_render_artifacts(stem)

    def _video_url(self, path: str) -> str:
        if not path:
            return ""
        return f"http://127.0.0.1:{self._http_port}{_fs_to_url_path(path)}"

    def ui_url(self, dist_index: str) -> str:
        dist_dir = os.path.abspath(os.path.dirname(dist_index))
        if dist_dir not in self._allowed_dirs:
            self._allowed_dirs.append(dist_dir)
        return f"http://127.0.0.1:{self._http_port}{_fs_to_url_path(dist_index)}"

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
