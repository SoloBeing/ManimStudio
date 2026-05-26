import sys, os, ast, subprocess, tempfile, shutil, signal, threading

QUALITY = {
    "Low  480p" : ["-ql", "--format", "webm"],
    "Med  720p" : ["-qm", "--format", "webm"],
    "High 1080p": ["-qh", "--format", "webm"],
    "GIF"       : ["-ql", "--format", "gif"],
}

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
})

_BLOCKED_CALLS = frozenset({
    "exec", "eval", "compile", "__import__", "open", "input", "breakpoint",
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

        full_output = []
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--run-manim"] + self.flags + ["--media_dir", self.output_dir, tmp, scene_name]
            else:
                cmd = ["manim"] + self.flags + ["--media_dir", self.output_dir, tmp, scene_name]
            kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace",
                **kw
            )
            for line in self._proc.stdout:
                stripped = line.rstrip()
                if "format set as webm" not in stripped and "format changed to '.webm'" not in stripped:
                    self.on_log(stripped)
                full_output.append(stripped)
            self._proc.wait()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

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

        # Fallback: newest mp4/gif in output_dir
        if not video:
            candidates = []
            for root_, _, files in os.walk(self.output_dir):
                if "partial_movie_files" in root_:
                    continue
                for fname in files:
                    if fname.endswith((".mp4", ".webm", ".gif")):
                        fp = os.path.join(root_, fname)
                        candidates.append((os.path.getmtime(fp), fp))
            if candidates:
                video = max(candidates)[1]
                self.on_log(f"[INFO] resolved via newest file: {video}")

        if not self._stopped:
            self.on_done(video)

    def stop(self):
        self._stopped = True
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
