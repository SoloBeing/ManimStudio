import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
