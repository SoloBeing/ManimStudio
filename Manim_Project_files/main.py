import sys, signal

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer

from window import MainWindow


def main():
    if "--run-manim" in sys.argv:
        sys.argv.remove("--run-manim")
        sys.argv[0] = "manim"
        import runpy
        runpy.run_module("manim", run_name="__main__", alter_sys=True)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setFont(QFont("JetBrains Mono,Fira Code,Consolas", 10))
    win = MainWindow()
    win.show()

    # SIGTERM / SIGHUP close the window gracefully (triggers closeEvent cleanup).
    def _quit(*_):
        win.close()

    signal.signal(signal.SIGTERM, _quit)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _quit)

    # Qt's C++ event loop doesn't yield to Python between ticks, so OS signals
    # would be delayed indefinitely. This no-op timer fires every 200 ms and
    # forces a return to the Python interpreter, keeping signal delivery prompt.
    _signal_timer = QTimer()
    _signal_timer.start(200)
    _signal_timer.timeout.connect(lambda: None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
