import sys, os, signal, runpy, atexit, threading

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

    webview.start(debug="--debug" in sys.argv)

    # PyWebView schedules QWebEnginePage.deleteLater() then immediately calls
    # _app.exit(), so the deletion never runs before the profile destructor.
    # Drain pending events here to avoid the "WebEnginePage still not deleted" warning.
    try:
        from qtpy.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()
    except Exception:
        pass


if __name__ == "__main__":
    main()
