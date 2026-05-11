import os, shutil, platform

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QTextEdit,
    QScrollArea, QComboBox, QSizePolicy, QStatusBar,
    QFileDialog, QMessageBox, QCheckBox,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QFont

from theme import C, STYLE

_LATEX_WARNED_FLAG = os.path.join(os.path.expanduser("~"), "ManimStudio", "latex_warned")
_LATEX_READY_FLAG  = os.path.join(os.path.expanduser("~"), "ManimStudio", "latex_ready_shown")
from widgets import sep
from renderer import QUALITY, RENDERS_DIR, RenderThread
from panels import TrigPanel, ComplexPanel, LinearPanel, CodePanel, StreamLinesPanel, PlaygroundPanel


class LeftPanel(QWidget):
    render_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 4, 8)
        root.setSpacing(4)

        brand = QLabel("MANIM STUDIO")
        brand.setStyleSheet(
            f"color:{C['accent']};font-size:14px;font-weight:900;"
            f"letter-spacing:3px;padding:4px 0;"
        )
        root.addWidget(brand)
        root.addWidget(sep())

        self.selector = QComboBox(self)
        self.selector.addItems([
            "Trigonometry",
            "Complex Plane",
            "Linear Algebra",
            "Code Animation",
            "StreamLines",
            "Playground",
        ])
        self.selector.currentIndexChanged.connect(self._switch)
        self.selector.hide()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 4, 4, 4)
        iv.setSpacing(8)

        self.trig       = TrigPanel()
        self.complex    = ComplexPanel()
        self.linear     = LinearPanel()
        self.code       = CodePanel()
        self.streams    = StreamLinesPanel()
        self.playground = PlaygroundPanel()
        for p in [self.trig, self.complex, self.linear, self.code, self.streams, self.playground]:
            iv.addWidget(p)
        iv.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

        root.addWidget(sep())

        # Output directory picker
        self.output_dir = RENDERS_DIR
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        dir_icon = QLabel("📁")
        self.dir_label = QLabel(self._short_path(self.output_dir))
        self.dir_label.setObjectName("dim")
        self.dir_label.setToolTip(self.output_dir)
        btn_browse = QPushButton("Browse…")
        btn_browse.setFixedSize(100, 32)
        btn_browse.clicked.connect(self._browse_output)
        dir_row.addWidget(dir_icon)
        dir_row.addWidget(self.dir_label, stretch=1)
        dir_row.addWidget(btn_browse)
        root.addLayout(dir_row)

        root.addWidget(sep())
        bar = QHBoxLayout()
        bar.setSpacing(6)

        self.quality = QComboBox()
        self.quality.addItems(list(QUALITY.keys()))
        self.quality.setFixedWidth(120)

        self.btn_run = QPushButton("▶  Render")
        self.btn_run.setObjectName("run")
        self.btn_run.setFixedHeight(36)
        self.btn_run.clicked.connect(self._render)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("stop")
        self.btn_stop.setFixedWidth(38)
        self.btn_stop.setStyleSheet(
            "font-family:'Segoe UI Symbol','Apple Symbols',"
            "'Noto Sans Symbols 2','DejaVu Sans',sans-serif;"
            "font-size:14px;"
        )
        self.btn_stop.setEnabled(False)

        bar.addWidget(self.quality)
        bar.addStretch()
        bar.addWidget(self.btn_stop)
        bar.addWidget(self.btn_run)
        root.addLayout(bar)

        self._switch(0)

    def _short_path(self, path, max_len=32):
        return path if len(path) <= max_len else "…" + path[-(max_len - 1):]

    def _browse_output(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_dir)
        if chosen:
            self.output_dir = chosen
            self.dir_label.setText(self._short_path(chosen))
            self.dir_label.setToolTip(chosen)

    def _switch(self, idx):
        self.trig      .setVisible(idx == 0)
        self.complex   .setVisible(idx == 1)
        self.linear    .setVisible(idx == 2)
        self.code      .setVisible(idx == 3)
        self.streams   .setVisible(idx == 4)
        self.playground.setVisible(idx == 5)

    def _active(self):
        return [
            self.trig,
            self.complex,
            self.linear,
            self.code,
            self.streams,
            self.playground,
        ][self.selector.currentIndex()]

    def current_label(self):
        return [
            "trigonometry",
            "complex_plane",
            "linear_algebra",
            "code_animation",
            "streamlines",
            "playground",
        ][self.selector.currentIndex()]

    def _render(self):
        self.render_requested.emit(self._active().source())


class RightPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 8, 8, 8)
        root.setSpacing(6)

        top = QHBoxLayout()
        lbl = QLabel("PREVIEW")
        lbl.setStyleSheet(
            f"color:{C['accent3']};font-size:10px;font-weight:700;letter-spacing:2px;"
        )
        self.status_lbl = QLabel("● Idle")
        self.status_lbl.setStyleSheet(f"color:{C['dim']};font-size:10px;")
        top.addWidget(lbl); top.addStretch(); top.addWidget(self.status_lbl)
        root.addLayout(top)

        self.video = QVideoWidget()
        self.video.setStyleSheet(
            f"background:{C['bg0']};border:1px solid {C['border']};border-radius:8px;"
        )
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.player = QMediaPlayer()
        self.audio  = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        root.addWidget(self.video, stretch=1)

        _sym_font = (
            "font-family:'Segoe UI Symbol','Apple Symbols',"
            "'Noto Sans Symbols 2','DejaVu Sans',sans-serif;"
            "font-size:14px;"
        )
        pb = QHBoxLayout()
        for icon, fn in [
            ("⏮", lambda: self.player.setPosition(0)),
            ("⏵", self.player.play),
            ("⏸", self.player.pause),
            ("⏹", self.player.stop),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(36, 30)
            b.setStyleSheet(_sym_font)
            b.clicked.connect(fn)
            pb.addWidget(b)
        self.loop = QCheckBox("Loop")
        self.loop.setChecked(True)
        pb.addStretch()
        pb.addWidget(self.loop)
        root.addLayout(pb)

        self.player.mediaStatusChanged.connect(self._loop_check)
        self.player.playbackStateChanged.connect(self._on_playback_state)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(QLabel("BUILD LOG"))
        self.btn_log = QPushButton("Hide")
        self.btn_log.setFixedWidth(60)
        self.btn_log.clicked.connect(self._toggle_log)
        log_hdr.addStretch()
        log_hdr.addWidget(self.btn_log)
        root.addLayout(log_hdr)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        self.log.setStyleSheet(
            f"background:#060d14;color:{C['teal']};"
            f"border:1px solid {C['border']};border-radius:6px;"
        )
        self.log.setFont(QFont("Fira Code,Courier New", 9))
        root.addWidget(self.log)

        self.latex_notice = QLabel(
            "⚠  LaTeX not installed — MathTex / Tex objects unavailable. "
            "Install TinyTeX to enable math rendering."
        )
        self.latex_notice.setWordWrap(True)
        self.latex_notice.setStyleSheet(
            "background:#2a1800; color:#e8a020;"
            " border:1px solid #6b3a00; border-radius:4px;"
            " padding:5px 8px; font-size:10px;"
        )
        self.latex_notice.hide()
        root.addWidget(self.latex_notice)

    def show_latex_notice(self):
        self.latex_notice.show()

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.set_status("● Playing", C['green'])
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.set_status("● Paused", C['accent3'])
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.set_status("● Stopped", C['accent2'])

    def _loop_check(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.loop.isChecked():
            self.player.setPosition(0)
            self.player.play()

    def _toggle_log(self):
        self.set_log_visible(not self.log.isVisible())

    def set_log_visible(self, visible):
        self.log.setVisible(visible)
        self.btn_log.setText("Hide" if visible else "Show")

    def load(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def append_log(self, msg):
        self.log.append(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_status(self, msg, color=None):
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color:{color or C['dim']};font-size:10px;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manim Studio")
        self.resize(1400, 860)
        self.setStyleSheet(STYLE)
        self._thread         = None
        self._render_stopped = False
        self._render_label   = "render"

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background:{C['border']}; }}")

        self.left  = LeftPanel()
        self.right = RightPanel()
        self.splitter.addWidget(self.left)
        self.splitter.addWidget(self.right)
        self.splitter.setSizes([420, 980])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self._panel_sizes = [420, 980]

        self.setCentralWidget(self.splitter)

        self._sb = QStatusBar()
        self._sb.showMessage("Ready — adjust parameters and hit Render")
        self.panel_selector = QComboBox()
        self.panel_selector.setObjectName("statusCombo")
        for i in range(self.left.selector.count()):
            self.panel_selector.addItem(self.left.selector.itemText(i))
        self.panel_selector.setFixedWidth(165)
        self.panel_selector.currentIndexChanged.connect(self._select_panel)
        self.left.selector.currentIndexChanged.connect(self._sync_panel_selector)

        self.view_menu = QComboBox()
        self.view_menu.setObjectName("statusCombo")
        self.view_menu.addItems([
            "View",
            "Open Panels",
            "Close Panels",
            "Open Build Log",
            "Close Build Log",
        ])
        self.view_menu.setFixedWidth(150)
        self.view_menu.activated.connect(self._view_action)

        self._sb.addPermanentWidget(self.panel_selector)
        self._sb.addPermanentWidget(self.view_menu)
        self.setStatusBar(self._sb)

        self.left.render_requested.connect(self._render)
        self.left.btn_stop.clicked.connect(self._stop)

        QTimer.singleShot(300, self._check_latex)

    def _check_latex(self):
        latex_ok = bool(shutil.which("latex") and shutil.which("dvisvgm"))
        _dir = os.path.dirname(_LATEX_WARNED_FLAG)

        if latex_ok:
            if os.path.exists(_LATEX_READY_FLAG):
                return
            msg = QMessageBox(self)
            msg.setWindowTitle("LaTeX Ready")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(
                "LaTeX is installed and ready.<br><br>"
                "<tt>MathTex()</tt> and <tt>Tex()</tt> objects are fully supported."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            cb = QCheckBox("Don't show this again")
            msg.setCheckBox(cb)
            msg.exec()
            if cb.isChecked():
                os.makedirs(_dir, exist_ok=True)
                open(_LATEX_READY_FLAG, "w").close()
        else:
            if os.path.exists(_LATEX_WARNED_FLAG):
                self.right.show_latex_notice()
                return
            missing = [t for t in ("latex", "dvisvgm") if not shutil.which(t)]
            sys_name = platform.system()
            if sys_name == "Windows":
                cmd = "winget install TinyTeX-org.TinyTeX"
            elif sys_name == "Darwin":
                cmd = 'curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
            else:
                cmd = 'wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
            msg = QMessageBox(self)
            msg.setWindowTitle("LaTeX Not Found")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(
                f"<b>{', '.join(missing)}</b> not found on PATH.<br><br>"
                "<tt>Text()</tt> animations work fine without it — LaTeX is only needed "
                "for <tt>MathTex()</tt> and <tt>Tex()</tt> objects.<br><br>"
                "Install <b>TinyTeX</b> to enable math rendering:<br>"
                f"<tt>{cmd}</tt>"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            cb = QCheckBox("Don't show this again")
            msg.setCheckBox(cb)
            msg.exec()
            if cb.isChecked():
                os.makedirs(_dir, exist_ok=True)
                open(_LATEX_WARNED_FLAG, "w").close()
            self.right.show_latex_notice()

    def _select_panel(self, idx):
        self.left.selector.setCurrentIndex(idx)
        if not self.left.isVisible():
            self.left.setVisible(True)
            self.splitter.setSizes(self._panel_sizes)
        self._sb.showMessage(f"Panel: {self.panel_selector.currentText()}")

    def _sync_panel_selector(self, idx):
        if self.panel_selector.currentIndex() == idx:
            return
        self.panel_selector.blockSignals(True)
        self.panel_selector.setCurrentIndex(idx)
        self.panel_selector.blockSignals(False)

    def _view_action(self, idx):
        action = self.view_menu.itemText(idx)
        self.view_menu.setCurrentIndex(0)
        if action == "Open Panels":
            self.left.setVisible(True)
            self.splitter.setSizes(self._panel_sizes)
            self._sb.showMessage("Panels opened")
        elif action == "Close Panels":
            if self.left.isVisible():
                sizes = self.splitter.sizes()
                if sizes and sizes[0] > 0:
                    self._panel_sizes = sizes
            self.left.setVisible(False)
            self._sb.showMessage("Panels closed")
        elif action == "Open Build Log":
            self.right.set_log_visible(True)
            self._sb.showMessage("Build Log opened")
        elif action == "Close Build Log":
            self.right.set_log_visible(False)
            self._sb.showMessage("Build Log closed")

    def _render(self, source: str):
        if self._thread and self._thread.isRunning():
            return
        self._render_stopped = False
        flags = QUALITY[self.left.quality.currentText()]
        self.right.log.clear()
        self.right.set_status("● Rendering…", C['accent3'])
        self.left.btn_run.setEnabled(False)
        self.left.btn_stop.setEnabled(True)
        self._sb.showMessage("Rendering…")

        self._render_label = self.left.current_label()
        self._thread = RenderThread(source, flags, self.left.output_dir)
        self._thread.log.connect(self.right.append_log)
        self._thread.done.connect(self._done)
        self._thread.start()

    def _stop(self):
        self._render_stopped = True
        if self._thread:
            try:
                self._thread.done.disconnect(self._done)
            except TypeError:
                pass
            self._thread.stop()
        self.left.btn_run.setEnabled(True)
        self.left.btn_stop.setEnabled(False)
        self.right.set_status("● Stopped", C['accent2'])
        self._sb.showMessage("Stopped")

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            try:
                self._thread.done.disconnect(self._done)
            except TypeError:
                pass
            self._thread.stop()
            self._thread.wait()
        event.accept()

    def _done(self, path: str):
        if self._render_stopped:
            return
        self.left.btn_run.setEnabled(True)
        self.left.btn_stop.setEnabled(False)
        if not (path and os.path.exists(path)):
            self.right.set_status("● Failed", C['red'])
            self._sb.showMessage("Render failed — see log")
            return

        ext      = os.path.splitext(path)[1].lower()
        filt     = "GIF (*.gif)" if ext == ".gif" else "MP4 Video (*.mp4)"
        default  = os.path.join(self.left.output_dir, f"{self._render_label}{ext}")
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Render As", default, filt)

        if save_path:
            try:
                shutil.move(path, save_path)
                path = save_path
            except OSError as e:
                self.right.append_log(f"[WARN] could not move file: {e}")
            self.right.load(path)
            self.right.set_status("● Playing", C['green'])
            self._sb.showMessage(f"Saved  {path}")
        else:
            try:
                # Manim layout: output_dir/videos/<stem>/<quality>/ManimScene.mp4
                # Two levels up is the per-script temp dir; rmtree it only when
                # it is provably inside output_dir/videos/ to stay safe.
                render_tree = os.path.dirname(os.path.dirname(path))
                videos_dir  = os.path.join(os.path.abspath(self.left.output_dir), "videos")
                if os.path.abspath(render_tree).startswith(videos_dir + os.sep):
                    shutil.rmtree(render_tree, ignore_errors=True)
                else:
                    os.unlink(path)
            except OSError:
                pass
            self.right.set_status("● Idle", C['dim'])
            self._sb.showMessage("Render discarded")
