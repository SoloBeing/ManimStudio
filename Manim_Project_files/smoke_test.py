#!/usr/bin/env python3
"""
Smoke tests — Manim Studio signal handling & process cleanup.

Run from Manim_Project_files/:
    python3 smoke_test.py
"""

import os, sys, signal, subprocess, time, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
PY   = sys.executable

GREEN = "\033[32m"
RED   = "\033[31m"
YELLOW= "\033[33m"
RESET = "\033[0m"
PASS  = f"{GREEN}PASS{RESET}"
FAIL  = f"{RED}FAIL{RESET}"
SKIP  = f"{YELLOW}SKIP{RESET}"

# ---------------------------------------------------------------------------
# Process helpers (no psutil — use /proc directly)
# ---------------------------------------------------------------------------

def pid_alive(pid: int) -> bool:
    return os.path.exists(f"/proc/{pid}")

def descendants(pid: int) -> list[int]:
    try:
        with open(f"/proc/{pid}/task/{pid}/children") as f:
            children = [int(p) for p in f.read().split() if p]
    except (FileNotFoundError, PermissionError):
        return []
    result = []
    for c in children:
        result.append(c)
        result.extend(descendants(c))
    return result

def wait_gone(pid: int, timeout: float = 6.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not pid_alive(pid):
            return True
        time.sleep(0.1)
    return False

def all_dead(pids: list[int], timeout: float = 4.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(pid_alive(p) for p in pids):
            return True
        time.sleep(0.2)
    return False

def kill_stragglers(pids: list[int]) -> None:
    for p in pids:
        try:
            os.kill(p, signal.SIGKILL)
        except ProcessLookupError:
            pass

# ---------------------------------------------------------------------------
# Shared manim source (long enough to stay alive during the signal tests)
# ---------------------------------------------------------------------------

LONG_SCENE = textwrap.dedent("""\
    from manim import *
    class ManimScene(Scene):
        def construct(self):
            c = Circle()
            self.play(Create(c), run_time=12)
            self.wait(3)
""")


# ===========================================================================
# Test 1: RenderThread.stop() kills the entire process group (incl. ffmpeg)
# ===========================================================================

def test_render_stop():
    print("\n[1] RenderThread.stop() kills entire process group ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, time
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        from renderer import RenderThread
        import tempfile
        out = tempfile.mkdtemp()
        t = RenderThread({LONG_SCENE!r}, ['-ql'], out)
        t.start()
        time.sleep(2)      # let manim + ffmpeg spin up
        t.stop()
        t.wait(8000)       # wait up to 8 s for thread to finish
        time.sleep(0.3)    # let OS reap children
        sys.exit(0)
    """)

    proc = subprocess.Popen([PY, "-c", script], cwd=HERE)
    pid  = proc.pid

    # snapshot child PIDs while render is running (give it 2.5 s head start)
    time.sleep(2.5)
    snap = set(descendants(pid))

    try:
        proc.wait(timeout=14)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(FAIL + "  (helper hung)")
        return False

    time.sleep(0.5)  # OS reap settle
    orphans = [p for p in snap if pid_alive(p)]

    if proc.returncode == 0 and not orphans:
        print(PASS)
        return True
    else:
        print(FAIL + f"  rc={proc.returncode}  orphans={orphans}")
        kill_stragglers(orphans)
        return False


# ===========================================================================
# Test 2: SIGTERM while render is running → clean exit, no orphans
# ===========================================================================

def test_sigterm_mid_render():
    print("\n[2] SIGTERM mid-render → clean exit, no orphans ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, signal
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QTimer
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        def _quit(*_):
            win.close()
        signal.signal(signal.SIGTERM, _quit)
        signal.signal(signal.SIGHUP,  _quit)
        _t = QTimer()
        _t.start(200)
        _t.timeout.connect(lambda: None)
        QTimer.singleShot(400, lambda: win._render({LONG_SCENE!r}))
        sys.exit(app.exec())
    """)

    proc = subprocess.Popen([PY, "-c", script], cwd=HERE)
    pid  = proc.pid

    time.sleep(3)               # let the render subprocess spawn
    snap = set(descendants(pid))

    os.kill(pid, signal.SIGTERM)

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(FAIL + "  (app did not exit after SIGTERM)")
        kill_stragglers(list(snap))
        return False

    time.sleep(0.5)
    orphans = [p for p in snap if pid_alive(p)]

    if proc.returncode == 0 and not orphans:
        print(PASS)
        return True
    else:
        print(FAIL + f"  rc={proc.returncode}  orphans={orphans}")
        kill_stragglers(orphans)
        return False


# ===========================================================================
# Test 3: Cancel on save dialog → app keeps running, video still loads
# ===========================================================================

def test_cancel_save_dialog():
    print("\n[3] Cancel on save dialog → app still alive, video loads ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QFileDialog
        from PyQt6.QtGui import QFont
        # Patch before MainWindow imports it so the dialog never blocks
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: ("", ""))
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        tmp.write(b'\\x00' * 512)
        tmp.close()
        fake_video = tmp.name
        win._done(fake_video)
        assert win.left.btn_run.isEnabled(),       "run button not re-enabled"
        assert not win.left.btn_stop.isEnabled(),  "stop button still enabled"
        assert not os.path.exists(fake_video),     "temp render file not deleted on cancel"
        assert "discarded" in win._sb.currentMessage().lower(), "status bar not updated"
        print("ok")
    """)

    result = subprocess.run(
        [PY, "-c", script], cwd=HERE,
        capture_output=True, text=True, timeout=15,
    )

    if result.returncode == 0 and "ok" in result.stdout:
        print(PASS)
        return True
    else:
        print(FAIL)
        for line in result.stderr.strip().splitlines()[-6:]:
            print("   ", line)
        return False


# ===========================================================================
# Test 4: Normal render completion → file saved, window closes cleanly
# ===========================================================================

def test_normal_completion_and_exit():
    print("\n[4] Normal render completion → save file, clean exit ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile, shutil
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QFileDialog
        from PyQt6.QtGui import QFont
        save_dir  = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, 'result.mp4')
        QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **kw: (save_path, "MP4 Video (*.mp4)")
        )
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        tmp.write(b'\\x00' * 512)
        tmp.close()
        fake_video = tmp.name
        win._done(fake_video)
        assert os.path.exists(save_path),    "saved file missing"
        assert not os.path.exists(fake_video), "original not moved"
        assert win.left.btn_run.isEnabled(),  "run button not re-enabled"
        win.close()   # triggers closeEvent — no thread running, should be instant
        app.quit()
        shutil.rmtree(save_dir)
        print("ok")
    """)

    result = subprocess.run(
        [PY, "-c", script], cwd=HERE,
        capture_output=True, text=True, timeout=15,
    )

    if result.returncode == 0 and "ok" in result.stdout:
        print(PASS)
        return True
    else:
        print(FAIL)
        for line in result.stderr.strip().splitlines()[-6:]:
            print("   ", line)
        return False


# ===========================================================================
# Known gap note
# ===========================================================================

def note_file_dialog_sigterm():
    print(f"\n[*] SIGTERM while save dialog is open ... {SKIP}")
    print("    The native Qt file dialog runs a blocking nested event loop.")
    print("    Python signal handlers cannot fire until the dialog is dismissed,")
    print("    so the app will hang until the user closes the dialog manually.")
    print("    No process leak risk: the render subprocess is already dead by")
    print("    the time the dialog opens, so there is nothing left to clean up.")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    print("=" * 56)
    print("  Manim Studio — Smoke Test Suite")
    print("=" * 56)

    results = [
        ("RenderThread.stop() kills process group", test_render_stop),
        ("SIGTERM mid-render → no orphans",         test_sigterm_mid_render),
        ("Cancel save dialog → app keeps running",  test_cancel_save_dialog),
        ("Normal completion → save + clean exit",   test_normal_completion_and_exit),
    ]

    outcomes = []
    for _name, fn in results:
        outcomes.append(fn())

    note_file_dialog_sigterm()

    passed = sum(outcomes)
    total  = len(outcomes)
    print()
    print("=" * 56)
    color = GREEN if passed == total else RED
    print(f"  Result: {color}{passed}/{total}{RESET} passed")
    print("=" * 56)

    sys.exit(0 if passed == total else 1)
