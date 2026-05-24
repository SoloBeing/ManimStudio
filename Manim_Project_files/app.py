import sys, os, signal, runpy

import webview
from api import Api


def _ui_url() -> str:
    if "--dev" in sys.argv:
        return "http://localhost:5173"
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "ui", "dist", "index.html")


def main():
    if "--run-manim" in sys.argv:
        sys.argv.remove("--run-manim")
        sys.argv[0] = "manim"
        runpy.run_module("manim", run_name="__main__", alter_sys=True)
        sys.exit(0)

    api = Api()
    window = webview.create_window(
        title="Manim Studio",
        url=_ui_url(),
        js_api=api,
        width=1400,
        height=860,
        min_size=(900, 600),
        background_color="#282c34",
    )
    api._set_window(window)

    def _quit(*_):
        for w in webview.windows:
            w.destroy()

    signal.signal(signal.SIGTERM, _quit)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _quit)

    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
