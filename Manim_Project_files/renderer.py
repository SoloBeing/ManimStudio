import sys, os, ast, subprocess, tempfile, shutil, signal, threading, json

# Quality presets are resolution/fps only — the output container is chosen
# separately via FORMATS so any resolution can be rendered to any format.
QUALITY = {
    "Low  480p" : ["-ql"],
    "Med  720p" : ["-qm"],
    "High 1080p": ["-qh"],
}

# Output format -> (extra manim flags, file extension, needs_webm_preview_proxy).
# The preview pane is Qt WebEngine, which can only decode VP8/VP9 (webm) plus
# gif/png — NOT H.264 mp4 or mov. Those are flagged for a transcoded webm
# proxy so the in-app preview still works while the saved file stays mp4/mov.
FORMATS = {
    "mp4" : (["--format", "mp4"],  ".mp4",  True),
    "webm": (["--format", "webm"], ".webm", False),
    "mov" : (["--format", "mov"],  ".mov",  True),
    "gif" : (["--format", "gif"],  ".gif",  False),
    "png" : (["-s"],               ".png",  False),
}
DEFAULT_FORMAT = "mp4"

RENDERS_DIR = os.path.join(os.path.expanduser("~"), "ManimStudio", "renders")
try:
    os.makedirs(RENDERS_DIR, exist_ok=True)
except OSError:
    RENDERS_DIR = tempfile.gettempdir()

# ---------------------------------------------------------------------------
# Playground source validator
# ---------------------------------------------------------------------------

# Modules that grant file-system, network, process, or code-execution access.
_BLOCKED_IMPORT_ROOTS = frozenset({
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "glob", "tempfile", "builtins", "importlib", "ctypes",
    "pickle", "shelve", "multiprocessing", "threading",
    "concurrent", "asyncio", "http", "urllib", "requests",
    "ftplib", "smtplib", "telnetlib", "xmlrpc",
    "io", "zipfile", "tarfile", "gzip", "bz2", "lzma", "mmap",
    "pty", "tty", "fcntl", "resource", "signal",
    "sysconfig", "site", "runpy", "inspect", "dis", "gc",
    "dbm", "sqlite3",
    # GUI libraries — spawn windows inside the render subprocess, causing hangs
    "matplotlib", "tkinter", "wx",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "gi", "pygame", "pyglet", "kivy", "toga", "dearpygui",
    "cv2",        # cv2.imshow() also creates windows
    # stdlib window/browser spawners
    "turtle",     # Tkinter-based, creates a window
    "webbrowser", # opens a browser tab
    "idlelib",    # IDLE GUI
    "antigravity",# opens a browser (Easter egg)
    # visualization libs that transitively import matplotlib or open a browser
    "seaborn", "plotly", "bokeh", "altair",
    "vispy", "mayavi", "vtk", "open3d", "vpython",
    # stdlib network modules not covered above
    "urllib3", "ssl", "select", "selectors",
    "imaplib", "poplib", "nntplib",
    # third-party HTTP / WebSocket / RPC / SSH clients
    "httpx", "aiohttp", "httplib2", "httpcore", "pycurl",
    "websocket", "websockets", "grpc", "paramiko", "requests_html",
    # cloud SDKs (all make outbound network calls)
    "boto3", "botocore", "google", "azure",
    # DNS
    "dns",
    # Python git libraries — can commit, clone, push without subprocess
    "git", "dulwich", "pygit2",
    # image/audio I/O with write capability
    "imageio",
})

_BLOCKED_CALLS = frozenset({
    "exec", "eval", "compile", "__import__", "open", "input", "breakpoint",
    # introspection builtins — getattr(obj, '__builtins__') bypasses _BLOCKED_ATTRS
    # because the attr name is a string argument, not dot-syntax in the AST
    "getattr", "setattr", "delattr", "vars", "globals", "locals",
})

_BLOCKED_ATTRS = frozenset({
    "__builtins__", "__globals__", "__subclasses__", "__code__", "__import__",
    "show",    # PIL.Image.show() — spawns OS image viewer
    "write",   # file object write — bypasses blocked open()
    # numpy / scipy file-write methods
    "save", "savetxt", "savez", "savez_compressed", "savemat",
    # pandas file-write methods
    "to_csv", "to_json", "to_excel", "to_parquet",
    "to_pickle", "to_sql", "to_hdf", "to_feather",
    # skimage / imageio write methods
    "imsave", "imwrite",
    # numpy memory-mapped file (mode='w+' creates/overwrites files)
    "memmap",
    # Manim interactive mode — hangs subprocess waiting for IPython input
    "interactive_embed",
})


def validate_playground_source(source: str) -> "str | None":
    """Return an error string if the source uses disallowed constructs, else None."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"Syntax error line {e.lineno}: {e.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORT_ROOTS:
                    return f"Import not allowed: {alias.name}"

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _BLOCKED_IMPORT_ROOTS:
                    return f"Import not allowed: from {node.module}"

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_CALLS:
                return f"Call not allowed: {node.func.id}()"

        elif isinstance(node, ast.Attribute):
            if node.attr in _BLOCKED_ATTRS:
                return f"Attribute access not allowed: .{node.attr}"

    return None


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):      return base.id
    if isinstance(base, ast.Attribute): return base.attr
    return ""

def find_all_scene_classes(tree: ast.AST) -> list[str]:
    """Return scene class names in source order (bases containing 'Scene')."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if any("Scene" in _base_name(b) for b in node.bases):
                names.append(node.name)
    return names

def _find_scene_class(tree: ast.AST) -> str | None:
    """Single-scene fallback: first Scene subclass, else last class defined."""
    found = find_all_scene_classes(tree)
    if found:
        return found[0]
    any_cls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            any_cls = node.name
    return any_cls


class RenderThread(threading.Thread):
    def __init__(self, source: str, flags: list, output_dir: str, scene_name: str = "",
                 on_log=None, on_done=None):
        super().__init__(daemon=True)
        self.source      = source
        self.flags       = flags
        self.output_dir  = output_dir
        self._scene_name = scene_name
        self._proc       = None
        self._worker     = None   # set when dispatched to the warm worker
        self._stopped    = False
        self.render_stem = None
        self.on_log  = on_log  or (lambda msg: None)
        self.on_done = on_done or (lambda path: None)

    def run(self):
        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            self.on_log(f"[SYNTAX ERROR] line {e.lineno}: {e.msg}")
            self.on_done("")
            return

        scene_name = self._scene_name or _find_scene_class(tree)
        if not scene_name:
            self.on_log("[ERROR] No scene class found in source.")
            self.on_done("")
            return

        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(self.source)
            tmp = f.name
        self.render_stem = os.path.splitext(os.path.basename(tmp))[0]

        argv = list(self.flags) + ["--media_dir", self.output_dir, tmp, scene_name]
        full_output = []
        try:
            os.makedirs(self.output_dir, exist_ok=True)

            # POSIX: dispatch to the warm worker (manim already imported, forks
            # per render) to skip the ~1s+ cold import cost. Fall back to a fresh
            # subprocess on Windows or if the worker is unavailable/unhealthy.
            worker = get_worker() if sys.platform != "win32" else None
            if worker is not None:
                try:
                    self._worker = worker
                    _, full_output = worker.submit(
                        argv, self.on_log, stop_check=lambda: self._stopped)
                except WorkerUnavailable as e:
                    self._worker = None
                    self.on_log(f"[INFO] warm worker unavailable ({e}); cold render")
                    full_output = self._run_cold(argv)
            else:
                full_output = self._run_cold(argv)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

        video = self._resolve_video(full_output)
        if not self._stopped:
            self.on_done(video)

    def _run_cold(self, argv: list) -> list:
        """Spawn a fresh manim subprocess (Windows path / worker fallback)."""
        full_output = []
        # Cancelled before we even spawned — don't start the render at all.
        if self._stopped:
            return full_output
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--run-manim"] + argv
        else:
            cmd = ["manim"] + argv
        kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
            **kw
        )
        # If stop() raced us between the check above and Popen, its kill targeted
        # a proc that didn't exist yet — so kill now that we have a handle.
        if self._stopped:
            self.stop()
        for line in self._proc.stdout:
            stripped = line.rstrip()
            if "format set as webm" not in stripped and "format changed to '.webm'" not in stripped:
                self.on_log(stripped)
            full_output.append(stripped)
        self._proc.wait()
        return full_output

    def _resolve_video(self, full_output: list) -> str:
        # Manim's rich formatter column-wraps the path, injecting alignment
        # spaces inside the quoted string.  Split on the surrounding quotes
        # and collapse all whitespace to reconstruct the real path.
        video = ""
        combined = " ".join(full_output)
        if "File ready at" in combined:
            after = combined.split("File ready at", 1)[1]
            parts = after.split("'")
            if len(parts) > 1:
                candidate = "".join(parts[1].split())
                if candidate and os.path.exists(candidate):
                    video = candidate

        # Fallback: newest output file belonging to THIS render. Manim writes
        # under a directory named after the input temp file's stem
        # (media_dir/videos/<stem>/... and media_dir/images/<stem>/...), so we
        # scope to self.render_stem. Without this scope, a render that produced
        # nothing (e.g. it failed) would grab a stale file from a prior render
        # and report a false "done".
        if not video and self.render_stem:
            candidates = []
            for root_, _, files in os.walk(self.output_dir):
                if "partial_movie_files" in root_:
                    continue
                if self.render_stem not in root_.split(os.sep):
                    continue
                for fname in files:
                    if fname.endswith((".mp4", ".webm", ".gif", ".png")):
                        fp = os.path.join(root_, fname)
                        candidates.append((os.path.getmtime(fp), fp))
            if candidates:
                video = max(candidates)[1]
                self.on_log(f"[INFO] resolved via newest file: {video}")
        return video

    def stop(self):
        self._stopped = True
        worker = self._worker
        if worker is not None:
            worker.cancel()
            return
        if self._proc:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self._proc.pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                try:
                    os.killpg(self._proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass


# ---------------------------------------------------------------------------
# Warm Manim worker (POSIX only)
# ---------------------------------------------------------------------------
#
# A render normally spawns a fresh process that imports the whole Manim stack
# from cold (~1s+ in dev, more when frozen) on every run. The warm worker pays
# that import cost ONCE: a long-lived process imports manim, then os.fork()s a
# child per render. The child inherits the imported modules via copy-on-write
# (no re-import) and runs exactly the normal manim CLI, then exits — so each
# render keeps pristine, isolated global state, just without the import latency.
#
# Control protocol (all over the worker's single stdout stream, so log lines and
# control frames can never desync): the worker prefixes control frames with a
# NUL sentinel "\x00CTL" + JSON. Because the worker writes the "done" frame only
# after reaping the render child, all of that render's log lines are guaranteed
# to precede "done" in the stream — the reader sees every log before completing.

_CTL_PREFIX = "\x00CTL"


class WorkerUnavailable(Exception):
    """Raised when the warm worker can't accept/finish a job; caller cold-renders."""


class WarmWorker:
    def __init__(self):
        self._proc          = None
        self._lock          = threading.Lock()
        self._job_id        = 0
        self._cur_job       = None
        self._current_on_log = None
        self._current_output = None
        self._ready_evt     = threading.Event()
        self._done_evt      = threading.Event()
        self._done_code     = None
        self._done_job      = None
        self._alive         = False
        self._reader        = None

    # -- lifecycle ----------------------------------------------------------

    def ensure_started(self):
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return
            self._start_locked()

    def _start_locked(self):
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--warm-worker"]
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            cmd = [sys.executable, "-c",
                   f"import sys; sys.path.insert(0, {here!r}); "
                   f"from renderer import worker_main; worker_main()"]
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        self._ready_evt.clear()
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1, env=env,
            start_new_session=True,
        )
        self._alive  = True
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def is_healthy(self) -> bool:
        p = self._proc
        return bool(p is not None and p.poll() is None)

    def shutdown(self):
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None and proc.stdin:
                proc.stdin.write(json.dumps({"cmd": "shutdown"}) + "\n")
                proc.stdin.flush()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # -- reader -------------------------------------------------------------

    def _read_stdout(self):
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                s = line.rstrip("\n")
                # A control frame normally arrives on its own line, but a render
                # child killed mid-write can leave a partial line with no trailing
                # newline — so the worker's "done" frame gets glued onto the end of
                # it (e.g. "Animation 3:  50%\x00CTL{...}"). The \x00CTL sentinel
                # can't occur in normal output, so split on it wherever it lands
                # and treat anything before it as a (partial) log line.
                if _CTL_PREFIX in s:
                    pre, _, ctl = s.partition(_CTL_PREFIX)
                    if pre:
                        self._emit_log(pre)
                    self._handle_ctl(ctl)
                    continue
                self._emit_log(s)
        except (ValueError, OSError):
            pass
        # stdout closed → worker exited; unblock any waiter as a failure
        self._alive = False
        self._done_evt.set()

    def _emit_log(self, s: str):
        out = self._current_output
        if out is not None:
            out.append(s)
        if "format set as webm" in s or "format changed to '.webm'" in s:
            return
        cb = self._current_on_log
        if cb is not None:
            cb(s)

    def _handle_ctl(self, payload: str):
        try:
            msg = json.loads(payload)
        except ValueError:
            return
        ev = msg.get("event")
        if ev == "ready":
            self._ready_evt.set()
        elif ev == "done":
            self._done_code = msg.get("code")
            self._done_job  = msg.get("id")
            self._done_evt.set()

    # -- job dispatch -------------------------------------------------------

    def submit(self, argv: list, on_log, stop_check=None) -> "tuple[int, list]":
        """Run one render on the worker; block until it finishes.

        Returns (exit_code, full_output). Raises WorkerUnavailable if the worker
        isn't running or dies mid-job, so the caller can fall back to a cold
        render. Jobs are serialized by the caller (one render at a time).

        ``stop_check`` is an optional predicate. A cancel that lands *before* the
        render is dispatched (e.g. while we're still waiting on the manim import)
        can't be delivered to a child that doesn't exist yet — so we check it
        right before dispatch and skip the render entirely. A cancel that lands
        *after* dispatch is handled by the worker: stdin is FIFO and processed in
        order, so the cancel is always read after the render command and reliably
        kills the just-forked child.
        """
        self.ensure_started()
        # Only the very first render waits on the manim import; later ones are
        # already ready and return immediately.
        if not self._ready_evt.wait(timeout=120):
            raise WorkerUnavailable("worker did not become ready")
        with self._lock:
            proc = self._proc
            if proc is None or proc.poll() is not None:
                raise WorkerUnavailable("worker not running")
            if stop_check is not None and stop_check():
                # Cancelled before we ever dispatched — nothing rendered.
                return -1, []
            self._job_id += 1
            jid = self._job_id
            self._cur_job        = jid
            self._current_on_log = on_log
            self._current_output = []
            self._done_evt.clear()
            self._done_code = None
            self._done_job  = None
            try:
                proc.stdin.write(json.dumps({"cmd": "render", "id": jid, "argv": argv}) + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                raise WorkerUnavailable(f"write failed: {e}")
        # No timeout — a render can legitimately take minutes.
        self._done_evt.wait()
        output = self._current_output or []
        if not self._alive or self._done_job != jid:
            raise WorkerUnavailable("worker exited during render")
        return self._done_code, output

    def cancel(self):
        with self._lock:
            proc = self._proc
            if proc is None or proc.poll() is not None or proc.stdin is None:
                return
            try:
                proc.stdin.write(json.dumps({"cmd": "cancel", "id": self._cur_job}) + "\n")
                proc.stdin.flush()
            except OSError:
                pass


_worker      = None
_worker_lock = threading.Lock()


def get_worker():
    """Return the process-wide warm worker (None on Windows)."""
    if sys.platform == "win32":
        return None
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = WarmWorker()
        return _worker


def shutdown_worker():
    global _worker
    with _worker_lock:
        w = _worker
        _worker = None
    if w is not None:
        w.shutdown()


def worker_main():
    """Entry point for the warm worker subprocess (POSIX only).

    Imports manim once, then loops reading JSON commands on stdin and forks a
    child per render. Control frames are written to stdout with the _CTL_PREFIX
    sentinel; render logs are the child's plain stdout.
    """
    import json as _json, runpy as _runpy, select as _select, time as _time

    import manim  # noqa: F401  — pay the import cost once for the whole session

    out = sys.stdout

    def _ctl(obj):
        try:
            out.write(_CTL_PREFIX + _json.dumps(obj) + "\n")
            out.flush()
        except Exception:
            pass

    _ctl({"event": "ready"})

    stdin_fd = sys.stdin.fileno()
    devnull  = os.open(os.devnull, os.O_RDONLY)
    child    = None   # pid (== pgid) of the running render child
    job      = None
    buf      = b""
    cancel_deadline = None   # monotonic time after which a cancel escalates to SIGKILL

    while True:
        # Block until a command arrives when idle; poll the child while a render
        # is running so we stay responsive to cancel without forking a thread.
        timeout = 0.05 if child is not None else None
        try:
            r, _, _ = _select.select([stdin_fd], [], [], timeout)
        except (OSError, ValueError):
            break

        if child is not None:
            try:
                pid, status = os.waitpid(child, os.WNOHANG)
            except ChildProcessError:
                pid, status = child, 0
            if pid != 0:
                if os.WIFSIGNALED(status):
                    code = -os.WTERMSIG(status)
                elif os.WIFEXITED(status):
                    code = os.WEXITSTATUS(status)
                else:
                    code = 1
                _ctl({"id": job, "event": "done", "code": code})
                child = None
                job   = None
                cancel_deadline = None
            elif cancel_deadline is not None and _time.monotonic() >= cancel_deadline:
                # SIGTERM didn't take (manim/ffmpeg can ignore it); force-kill so
                # the cancelled render can't hang the worker — and the UI — forever.
                try:
                    os.killpg(child, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                cancel_deadline = None

        if not r:
            continue

        try:
            chunk = os.read(stdin_fd, 65536)
        except OSError:
            break
        if not chunk:
            break  # stdin closed → parent gone → shut down
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                cmd = _json.loads(line)
            except ValueError:
                continue
            action = cmd.get("cmd")
            if action == "shutdown":
                child_to_kill = child
                if child_to_kill is not None:
                    try:
                        os.killpg(child_to_kill, signal.SIGTERM)
                        os.waitpid(child_to_kill, 0)
                    except OSError:
                        pass
                os._exit(0)
            elif action == "cancel":
                if child is not None:
                    try:
                        os.killpg(child, signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass
                    # Give SIGTERM a brief grace, then escalate (see child poll above).
                    cancel_deadline = _time.monotonic() + 2.0
            elif action == "render":
                if child is not None:
                    _ctl({"id": cmd.get("id"), "event": "done", "code": 1})
                    continue
                job  = cmd.get("id")
                argv = cmd.get("argv", [])
                pid  = os.fork()
                if pid == 0:
                    # ---- render child ----
                    try:
                        os.setpgid(0, 0)
                    except OSError:
                        pass
                    try:
                        os.dup2(devnull, 0)   # detach stdin (never read commands)
                    except OSError:
                        pass
                    sys.argv = ["manim"] + list(argv)
                    code = 0
                    try:
                        _runpy.run_module("manim", run_name="__main__", alter_sys=True)
                    except SystemExit as e:
                        code = e.code if isinstance(e.code, int) else (0 if e.code in (None, "") else 1)
                    except BaseException:
                        import traceback
                        traceback.print_exc()
                        code = 1
                    try:
                        sys.stdout.flush()
                    except Exception:
                        pass
                    os._exit(code if isinstance(code, int) else 1)
                else:
                    # ---- worker parent ----
                    try:
                        os.setpgid(pid, pid)   # race-free with child's setpgid
                    except OSError:
                        pass
                    child = pid
