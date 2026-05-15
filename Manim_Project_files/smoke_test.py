#!/usr/bin/env python3
"""
Smoke tests — Manim Studio signal handling, process cleanup, and UI state.

Run from Manim_Project_files/:
    python3 smoke_test.py
"""

import os, sys, signal, subprocess, time, textwrap, shutil

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

def _run(script: str, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-c", script], cwd=HERE,
        capture_output=True, text=True, timeout=timeout,
    )

def _ok(result: subprocess.CompletedProcess) -> bool:
    return result.returncode == 0 and "ok" in result.stdout

def _show_err(result: subprocess.CompletedProcess, n: int = 8) -> None:
    for line in (result.stdout + result.stderr).strip().splitlines()[-n:]:
        print("   ", line)

# ---------------------------------------------------------------------------
# Shared manim sources
# ---------------------------------------------------------------------------

LONG_SCENE = textwrap.dedent("""\
    from manim import *
    class ManimScene(Scene):
        def construct(self):
            c = Circle()
            self.play(Create(c), run_time=12)
            self.wait(3)
""")

FAST_SCENE = textwrap.dedent("""\
    from manim import *
    class ManimScene(Scene):
        def construct(self):
            self.add(Circle())
            self.wait(0.1)
""")


# ===========================================================================
# [1] RenderThread.stop() kills the entire process group (incl. ffmpeg)
# ===========================================================================

def test_render_stop():
    print("\n[1]  RenderThread.stop() kills entire process group ... ", end="", flush=True)

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
        time.sleep(2)
        t.stop()
        t.wait(8000)
        time.sleep(0.3)
        sys.exit(0)
    """)

    proc = subprocess.Popen([PY, "-c", script], cwd=HERE)
    pid  = proc.pid
    time.sleep(2.5)
    snap = set(descendants(pid))

    try:
        proc.wait(timeout=14)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(FAIL + "  (helper hung)")
        return False

    time.sleep(0.5)
    orphans = [p for p in snap if pid_alive(p)]
    if proc.returncode == 0 and not orphans:
        print(PASS)
        return True
    print(FAIL + f"  rc={proc.returncode}  orphans={orphans}")
    kill_stragglers(orphans)
    return False


# ===========================================================================
# [2] SIGTERM while render is running → clean exit, no orphans
# ===========================================================================

def test_sigterm_mid_render():
    print("\n[2]  SIGTERM mid-render → clean exit, no orphans ... ", end="", flush=True)

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
    time.sleep(3)
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
    print(FAIL + f"  rc={proc.returncode}  orphans={orphans}")
    kill_stragglers(orphans)
    return False


# ===========================================================================
# [3] Discard pending render → artifacts wiped, status updated
# ===========================================================================

def test_discard_pending():
    print("\n[3]  Discard pending render → artifacts wiped, status updated ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile, shutil, types
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        out_dir  = tempfile.mkdtemp()
        stem     = 'tmpFAKE'
        qual_dir = os.path.join(out_dir, 'videos', stem, '480p15')
        os.makedirs(qual_dir)
        partial  = os.path.join(qual_dir, 'partial_movie_files')
        os.makedirs(partial)
        open(os.path.join(partial, 'clip.mp4'), 'wb').close()
        fake_video = os.path.join(qual_dir, 'ManimScene.mp4')
        open(fake_video, 'wb').write(b'\\x00' * 512)
        os.makedirs(os.path.join(out_dir, 'images', stem))
        win.left.output_dir = out_dir
        win._thread = types.SimpleNamespace(render_stem=stem)
        win._done(fake_video)
        assert win.left.btn_run.isEnabled(),       "run button not re-enabled"
        assert not win.left.btn_stop.isEnabled(),  "stop button still enabled"
        win._discard_pending_render()
        assert not os.path.exists(os.path.join(out_dir, 'videos', stem)), "videos/<stem> not deleted"
        assert not os.path.exists(os.path.join(out_dir, 'images', stem)), "images/<stem> not deleted"
        assert not os.path.exists(os.path.join(out_dir, 'videos')),       "videos/ dir not wiped"
        assert not os.path.exists(os.path.join(out_dir, 'images')),       "images/ dir not wiped"
        assert "discarded" in win._sb.currentMessage().lower(),            "status bar not updated"
        shutil.rmtree(out_dir, ignore_errors=True)
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [4] Normal render completion → save dialog → file moved, window closes
# ===========================================================================

def test_save_pending():
    print("\n[4]  Normal completion → save file, clean exit ... ", end="", flush=True)

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
        win._save_pending_render()
        assert os.path.exists(save_path),      "saved file missing"
        assert not os.path.exists(fake_video), "original not moved"
        assert win.left.btn_run.isEnabled(),   "run button not re-enabled"
        assert win._pending_render_path == "", "pending path not cleared"
        win.close()
        app.quit()
        shutil.rmtree(save_dir)
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [5] Failed render (empty path) → error state, save/discard disabled
# ===========================================================================

def test_failed_render():
    print("\n[5]  Failed render → error state, buttons reset ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        win.left.btn_run.setEnabled(False)
        win.left.btn_stop.setEnabled(True)
        win._done("")   # empty path = render produced no video
        assert win.left.btn_run.isEnabled(),          "run button not re-enabled after failure"
        assert not win.left.btn_stop.isEnabled(),     "stop button still enabled after failure"
        assert not win.right.btn_save.isEnabled(),    "save button should be disabled"
        assert not win.right.btn_discard.isEnabled(), "discard button should be disabled"
        assert "fail" in win._sb.currentMessage().lower(), "status bar should mention failure"
        assert win._pending_render_path == "",         "no pending path on failure"
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [6] _stop() mid-render → stopped status, buttons reset, artifacts cleaned
# ===========================================================================

def test_stop_ui_state():
    print("\n[6]  _stop() → stopped status, buttons reset ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile, types, shutil
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        out_dir = tempfile.mkdtemp()
        win.left.output_dir = out_dir
        win.left.btn_run.setEnabled(False)
        win.left.btn_stop.setEnabled(True)
        win._render_stopped = False
        win._thread = types.SimpleNamespace(
            render_stem='tmpFAKE',
            stop=lambda: None,
            wait=lambda t: None,
            done=types.SimpleNamespace(disconnect=lambda f: None),
        )
        win._stop()
        assert win._render_stopped,               "_render_stopped not set"
        assert win.left.btn_run.isEnabled(),      "run button not re-enabled"
        assert not win.left.btn_stop.isEnabled(), "stop button still enabled"
        assert "stopped" in win._sb.currentMessage().lower(), "status should say Stopped"
        shutil.rmtree(out_dir, ignore_errors=True)
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [7] Save dialog cancelled → pending render still available
# ===========================================================================

def test_save_cancelled():
    print("\n[7]  Save dialog cancelled → pending still available ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QFileDialog
        from PyQt6.QtGui import QFont
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
        win._save_pending_render()   # dialog returns ("", "") → cancelled
        assert os.path.exists(fake_video),             "file should still exist after cancel"
        assert win._pending_render_path == fake_video, "pending path should be unchanged"
        assert "cancelled" in win._sb.currentMessage().lower(), "status should say cancelled"
        assert win.right.btn_save.isEnabled(),    "save button should still be enabled"
        assert win.right.btn_discard.isEnabled(), "discard button should still be enabled"
        os.unlink(fake_video)
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [8] Quit with unsaved render → Cancel → close event ignored, file intact
# ===========================================================================

def test_quit_unsaved_cancel():
    print("\n[8]  Quit with unsaved render → Cancel → event ignored ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont, QCloseEvent
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        tmp.write(b'\\x00' * 512)
        tmp.close()
        win._pending_render_path = tmp.name
        win._confirm_unsaved_render_exit = lambda: "cancel"
        event = QCloseEvent()
        win.closeEvent(event)
        assert not event.isAccepted(),   "close event should be ignored on Cancel"
        assert os.path.exists(tmp.name), "file should not be deleted on Cancel"
        os.unlink(tmp.name)
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [9] Quit with unsaved render → Discard → file deleted, event accepted
# ===========================================================================

def test_quit_unsaved_discard():
    print("\n[9]  Quit with unsaved render → Discard → file deleted ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont, QCloseEvent
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        tmp.write(b'\\x00' * 512)
        tmp.close()
        win._pending_render_path = tmp.name
        win._confirm_unsaved_render_exit = lambda: "discard"
        event = QCloseEvent()
        win.closeEvent(event)
        assert event.isAccepted(),           "close event should be accepted on Discard"
        assert not os.path.exists(tmp.name), "pending render file should be deleted"
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [10] Quit with unsaved render → Save → file at target, event accepted
# ===========================================================================

def test_quit_unsaved_save():
    print("\n[10] Quit with unsaved render → Save → file saved, event accepted ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile, shutil
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QFileDialog
        from PyQt6.QtGui import QFont, QCloseEvent
        save_dir  = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, 'quit_save.mp4')
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
        win._pending_render_path = tmp.name
        win._confirm_unsaved_render_exit = lambda: "save"
        event = QCloseEvent()
        win.closeEvent(event)
        assert event.isAccepted(),        "close event should be accepted after Save"
        assert os.path.exists(save_path), "saved file should exist"
        shutil.rmtree(save_dir)
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [11] New render clears stale pending render
# ===========================================================================

def test_new_render_clears_pending():
    print("\n[11] New render clears stale pending render ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        from renderer import RenderThread
        win = MainWindow()
        win.show()
        stale = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        stale.write(b'\\x00' * 512)
        stale.close()
        win._pending_render_path = stale.name
        win._pending_render_stem = "stale_stem"
        # Prevent the thread from actually running manim
        RenderThread.start = lambda self: None
        source = "from manim import *\\nclass ManimScene(Scene):\\n    def construct(self): pass"
        win._render(source)
        assert not os.path.exists(stale.name), "stale pending file should be deleted on new render"
        assert win._pending_render_path == "", "pending path should be cleared"
        assert win._pending_render_stem == "", "pending stem should be cleared"
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [12] Quit with no pending render → instant clean close
# ===========================================================================

def test_quit_clean():
    print("\n[12] Quit with no pending render → instant clean close ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont, QCloseEvent
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()
        assert win._pending_render_path == "", "should start with no pending render"
        event = QCloseEvent()
        win.closeEvent(event)
        assert event.isAccepted(), "clean quit should accept close event immediately"
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [13] Full real render → video file produced (RenderThread pipeline)
# ===========================================================================

def test_real_render_produces_video():
    print("\n[13] Full real render → video produced ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, threading, tempfile
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        app = QApplication(sys.argv)
        from renderer import RenderThread
        out    = tempfile.mkdtemp()
        result = []
        event  = threading.Event()
        def on_done(path):
            result.append(path)
            event.set()
        thread = RenderThread({FAST_SCENE!r}, ['-ql'], out)
        thread.done.connect(on_done, Qt.ConnectionType.DirectConnection)
        thread.start()
        ok = event.wait(timeout=60)
        thread.wait(5000)
        if not ok or not result:
            print("TIMEOUT"); sys.exit(1)
        video = result[0]
        assert video,                 "done emitted empty path"
        assert os.path.exists(video), f"video file not found: {{video}}"
        print("ok:" + video)
    """)

    r = _run(script, timeout=90)
    if r.returncode == 0 and "ok:" in r.stdout:
        print(PASS); return True
    print(FAIL)
    if "TIMEOUT" in r.stdout:
        print("    (render timed out after 60 s)")
    _show_err(r)
    return False


# ===========================================================================
# [14] Full real render → MainWindow flow → save to disk
# ===========================================================================

def test_real_render_save():
    print("\n[14] Full real render → MainWindow save workflow ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, tempfile, shutil
        sys.path.insert(0, {HERE!r})
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QFileDialog
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QTimer

        save_dir  = tempfile.mkdtemp()
        save_path = os.path.join(save_dir, 'render_result.mp4')
        QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **kw: (save_path, "MP4 Video (*.mp4)")
        )

        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()

        done_result = []
        save_result = []
        orig_done   = win._done

        # Bypass QMediaPlayer to avoid a VA-API symbol crash when loading
        # a real video (libavutil vaMapBuffer2 missing on this system).
        # Player functionality is covered by tests 3 and 4; here we only
        # care that the file is saved to the right path.
        win.right.load         = lambda path: None
        win.right.release_media = lambda: None

        def patched_done(path):
            orig_done(path)
            done_result.append(path)
            ok = win._save_pending_render()
            save_result.append(ok)
            QTimer.singleShot(100, app.quit)

        win._done           = patched_done
        render_out          = tempfile.mkdtemp()
        win.left.output_dir = render_out

        QTimer.singleShot(100, lambda: win._render({FAST_SCENE!r}))
        app.exec()

        assert done_result,                          "done never called"
        video = done_result[0]
        assert video,                                "render produced no video"
        assert save_result and save_result[0],       "save returned False"
        assert os.path.exists(save_path),            "saved file missing after save"
        assert win._pending_render_path == "",        "pending path not cleared after save"
        shutil.rmtree(save_dir,   ignore_errors=True)
        shutil.rmtree(render_out, ignore_errors=True)
        print("ok")
    """)

    r = _run(script, timeout=90)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [15] Free-position preset labels → builders never emit .__FREE__ sentinel
# ===========================================================================

def test_free_position_preset_labels():
    print("\n[15] Free-position preset labels → no .__FREE__ in generated source ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys
        sys.path.insert(0, {HERE!r})
        from builders import (
            build_trig_source, build_complex_source, build_linear_source,
            build_nonlinear_source, build_streamlines_source,
        )

        COMMON = dict(
            text_position="free", show_preset_labels=True,
            x_offset=1.5, y_offset=2.0,
        )

        sources = {{
            "trig":        build_trig_source(
                                True, False, False, 1, 1, 0, 0, 4, False, "Create",
                                **COMMON),
            "complex":     build_complex_source("roots", 0, 0, 1, 6, True, **COMMON),
            "linear":      build_linear_source(1, 0, 0, 1, 1, 1, True, True, True, **COMMON),
            "nonlinear":   build_nonlinear_source("swirl", 1, 1, False, False, **COMMON),
            "streamlines": build_streamlines_source("vortex", 1, 0.5, 1, 1, 2, True, True, **COMMON),
        }}

        for name, src in sources.items():
            assert ".__FREE__" not in src, f"{{name}} builder emitted .__FREE__ in output"
            assert "move_to" in src,       f"{{name}} builder missing move_to for free position"

        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# [16] latex_notice is a clickable QPushButton with pointer cursor
# ===========================================================================

def test_latex_notice_is_clickable():
    print("\n[16] latex_notice is QPushButton with pointer cursor ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys
        sys.path.insert(0, {HERE!r})
        import os
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QPushButton
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt
        app = QApplication(sys.argv)
        app.setFont(QFont("Monospace", 10))
        from window import MainWindow
        win = MainWindow()
        win.show()

        notice = win.right.latex_notice
        assert isinstance(notice, QPushButton), \
            f"latex_notice is {{type(notice).__name__}}, expected QPushButton"
        assert notice.isFlat(), \
            "latex_notice QPushButton should be flat"
        assert notice.cursor().shape() == Qt.CursorShape.PointingHandCursor, \
            "latex_notice should have PointingHandCursor"
        assert "(click" in notice.text().lower(), \
            "latex_notice text should hint that it is clickable"
        print("ok")
    """)

    r = _run(script)
    if _ok(r):
        print(PASS); return True
    print(FAIL); _show_err(r); return False


# ===========================================================================
# Known gap
# ===========================================================================

def note_file_dialog_sigterm():
    print(f"\n[*]  SIGTERM while save dialog is open ... {SKIP}")
    print("     The native Qt file dialog runs a blocking nested event loop.")
    print("     Python signal handlers cannot fire until the dialog is dismissed,")
    print("     so the app will hang until the user closes the dialog manually.")
    print("     No process leak risk: the render subprocess is already dead by")
    print("     the time the dialog opens, so there is nothing left to clean up.")


# ===========================================================================
# Runner
# ===========================================================================

FAST_TESTS = [
    ("RenderThread.stop() kills process group",   test_render_stop),
    ("SIGTERM mid-render → no orphans",           test_sigterm_mid_render),
    ("Discard pending render → wipe + status",    test_discard_pending),
    ("Normal completion → save + clean exit",     test_save_pending),
    ("Failed render → error state",               test_failed_render),
    ("_stop() → stopped status, buttons reset",   test_stop_ui_state),
    ("Save dialog cancelled → pending active",    test_save_cancelled),
    ("Quit unsaved → Cancel → event ignored",     test_quit_unsaved_cancel),
    ("Quit unsaved → Discard → file deleted",     test_quit_unsaved_discard),
    ("Quit unsaved → Save → file saved",          test_quit_unsaved_save),
    ("New render clears stale pending",           test_new_render_clears_pending),
    ("Quit clean (no pending) → instant close",   test_quit_clean),
    ("Free-position preset labels → no __FREE__", test_free_position_preset_labels),
    ("latex_notice is clickable QPushButton",     test_latex_notice_is_clickable),
]

SLOW_TESTS = [
    ("Full real render → video produced",         test_real_render_produces_video),
    ("Full real render → MainWindow save flow",   test_real_render_save),
]

if __name__ == "__main__":
    print("=" * 62)
    print("  Manim Studio — Full Smoke Test Suite")
    print("=" * 62)

    outcomes = []

    print("\n── UI state-machine tests ──")
    for _name, fn in FAST_TESTS:
        outcomes.append(fn())

    print("\n── Real render tests (manim) ──")
    for _name, fn in SLOW_TESTS:
        outcomes.append(fn())

    note_file_dialog_sigterm()

    passed = sum(outcomes)
    total  = len(outcomes)
    print()
    print("=" * 62)
    color = GREEN if passed == total else RED
    print(f"  Result: {color}{passed}/{total}{RESET} passed")
    print("=" * 62)

    sys.exit(0 if passed == total else 1)
