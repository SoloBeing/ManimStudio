import sys, os, ast, subprocess, tempfile, shutil

from PyQt6.QtCore import QThread, pyqtSignal

QUALITY = {
    "Low  480p" : ["-ql"],
    "Med  720p" : ["-qm"],
    "High 1080p": ["-qh"],
    "GIF"       : ["-ql", "--format", "gif"],
}

RENDERS_DIR = os.path.join(os.path.expanduser("~"), "ManimStudio", "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)


class RenderThread(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self, source: str, flags: list, output_dir: str):
        super().__init__()
        self.source     = source
        self.flags      = flags
        self.output_dir = output_dir
        self._proc      = None
        self._stopped   = False

    def run(self):
        try:
            ast.parse(self.source)
        except SyntaxError as e:
            self.log.emit(f"[SYNTAX ERROR] line {e.lineno}: {e.msg}")
            self.done.emit("")
            return

        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(self.source)
            tmp = f.name

        full_output = []
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--run-manim"] + self.flags + ["--media_dir", self.output_dir, tmp, "ManimScene"]
            else:
                cmd = ["manim"] + self.flags + ["--media_dir", self.output_dir, tmp, "ManimScene"]
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
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

        # Manim may split the path across two log lines — join and re-scan
        video = ""
        combined = " ".join(full_output)
        if "File ready at" in combined:
            after = combined.split("File ready at", 1)[1].strip()
            token = after.split()[0].strip("'\"") if after.split() else ""
            if token and os.path.exists(token):
                video = token

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
            self._proc.terminate()
        self.terminate()
