import sys, os, ast, subprocess, tempfile, shutil, signal

from PyQt6.QtCore import QThread, pyqtSignal

QUALITY = {
    "Low  480p" : ["-ql"],
    "Med  720p" : ["-qm"],
    "High 1080p": ["-qh"],
    "GIF"       : ["-ql", "--format", "gif"],
}

RENDERS_DIR = os.path.join(os.path.expanduser("~"), "ManimStudio", "renders")
try:
    os.makedirs(RENDERS_DIR, exist_ok=True)
except OSError:
    RENDERS_DIR = tempfile.gettempdir()


def _find_scene_class(tree: ast.AST) -> str | None:
    """Return the last class whose base contains 'Scene', else the last class."""
    scene_cls = None
    any_cls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            any_cls = node.name
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else (
                    base.attr if isinstance(base, ast.Attribute) else "")
                if "Scene" in base_name:
                    scene_cls = node.name
                    break
    return scene_cls or any_cls


class RenderThread(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self, source: str, flags: list, output_dir: str):
        super().__init__()
        self.source      = source
        self.flags       = flags
        self.output_dir  = output_dir
        self._proc       = None
        self._stopped    = False
        self.render_stem = None  # stem of the temp script; set in run() for cleanup

    def run(self):
        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            self.log.emit(f"[SYNTAX ERROR] line {e.lineno}: {e.msg}")
            self.done.emit("")
            return

        scene_name = _find_scene_class(tree)
        if not scene_name:
            self.log.emit("[ERROR] No scene class found in source.")
            self.done.emit("")
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
                self.log.emit(stripped)
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
                    if fname.endswith((".mp4", ".gif")):
                        fp = os.path.join(root_, fname)
                        candidates.append((os.path.getmtime(fp), fp))
            if candidates:
                video = max(candidates)[1]
                self.log.emit(f"[INFO] resolved via newest file: {video}")

        if not self._stopped:
            self.done.emit(video)

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
