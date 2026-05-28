import sys, os, signal, runpy, atexit, threading

# console=False hides all output on Windows — write to ~/ManimStudio/crash.log
# so launch failures are visible. Must come before any import that could fail.
if getattr(sys, "frozen", False) and sys.platform == "win32":
    _log_dir = os.path.join(os.path.expanduser("~"), "ManimStudio")
    os.makedirs(_log_dir, exist_ok=True)
    _log = open(os.path.join(_log_dir, "crash.log"), "w", buffering=1, encoding="utf-8")
    sys.stdout = _log
    sys.stderr = _log

    def _win_excepthook(exc_type, exc_value, exc_tb):
        import traceback, ctypes
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(tb, flush=True)
        ctypes.windll.user32.MessageBoxW(
            0,
            f"ManimStudio failed to start.\n\nSee crash.log in:\n{_log_dir}\n\n{tb[:600]}",
            "ManimStudio Error",
            0x10,
        )
    sys.excepthook = _win_excepthook

# Qt WebEngine sandbox is incompatible with frozen PyInstaller bundles on
# Windows — the renderer subprocess can't locate its resources and shows a
# white screen. Must be set before any Qt import occurs.
if sys.platform == "win32":
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

# Windows: Qt WebEngine needs its subprocess exe. In a frozen PyInstaller
# bundle PyInstaller's Qt hook puts it at PyQt6/Qt6/bin/QtWebEngineProcess.exe
# but Qt's default search may not find it without a qt.conf. Set the env var
# so Qt locates it regardless of working directory.
if getattr(sys, "frozen", False) and sys.platform == "win32":
    import glob as _glob, platform as _platform
    print(f"ManimStudio starting — {_platform.platform()} — Python {sys.version}", flush=True)
    print(f"Bundle root: {sys._MEIPASS}", flush=True)
    _proc_hits = _glob.glob(
        os.path.join(sys._MEIPASS, "**", "QtWebEngineProcess.exe"),
        recursive=True,
    )
    if _proc_hits:
        os.environ.setdefault("QTWEBENGINEPROCESS_PATH", _proc_hits[0])
        print(f"QtWebEngineProcess.exe -> {_proc_hits[0]}", flush=True)
    else:
        print("WARNING: QtWebEngineProcess.exe not found in bundle", flush=True)

import webview
from api import Api


def _ui_url(api) -> str:
    if "--dev" in sys.argv:
        return "http://localhost:5173"
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    dist_index = os.path.join(base, "ui", "dist", "index.html")
    return api.ui_url(dist_index)


def main():
    if "--run-manim" in sys.argv:
        sys.argv.remove("--run-manim")
        sys.argv[0] = "manim"
        # Manim spawns ffmpeg (and LaTeX tools) via subprocess without
        # CREATE_NO_WINDOW, which flashes cmd windows on Windows.
        # Patch Popen here so every child process Manim creates is windowless.
        if sys.platform == "win32":
            import subprocess as _sp
            _OrigPopen = _sp.Popen
            class _NoCmdPopen(_OrigPopen):
                def __init__(self, *a, **kw):
                    kw.setdefault("creationflags", 0)
                    kw["creationflags"] |= _sp.CREATE_NO_WINDOW
                    super().__init__(*a, **kw)
            _sp.Popen = _NoCmdPopen
        runpy.run_module("manim", run_name="__main__", alter_sys=True)
        sys.exit(0)

    api = Api()
    window = webview.create_window(
        title="Manim Studio",
        url=_ui_url(api),
        js_api=api,
        width=1400,
        height=860,
        min_size=(900, 600),
        background_color="#282c34",
    )
    api._set_window(window)
    atexit.register(api.cleanup)

    def _on_closing():
        with api._lock:
            has_unsaved = bool(api._video_path and os.path.exists(api._video_path))
        if has_unsaved:
            # Push dialog to JS from a thread — avoid calling evaluate_js
            # synchronously inside Qt's closeEvent handler.
            threading.Thread(
                target=lambda: api._push({"showCloseDialog": True}),
                daemon=True,
            ).start()
            return False  # cancel the close; JS will call confirm_close()

    window.events.closing += _on_closing

    def _quit(*_):
        api.cleanup()
        for w in webview.windows:
            w.destroy()

    signal.signal(signal.SIGTERM, _quit)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _quit)

    # PyWebView calls deleteLater() on the WebEnginePage then immediately exits
    # the event loop, so the deletion never runs before the profile destructor.
    # Suppress that specific Qt warning — it is a PyWebView bug, not ours.
    try:
        from qtpy.QtCore import qInstallMessageHandler
        def _qt_msg_handler(msg_type, context, message):
            if 'WebEnginePage still not deleted' not in message:
                print(message, file=sys.stderr)
        qInstallMessageHandler(_qt_msg_handler)
    except Exception:
        pass

    # Force Qt backend on all platforms — pywebview's Windows-native backends
    # (edgechromium, winforms) both require pythonnet/.NET interop which
    # crashes in frozen PyInstaller builds.
    webview.start(debug="--debug" in sys.argv, gui="qt")


if __name__ == "__main__":
    main()
