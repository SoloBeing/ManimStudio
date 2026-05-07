import os, shutil

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QTextEdit,
    QScrollArea, QComboBox, QSizePolicy, QStatusBar,
    QFileDialog,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont

from theme import C, STYLE
from widgets import sep
from renderer import QUALITY, RENDERS_DIR, RenderThread
from panels import TrigPanel, ComplexPanel, LinearPanel, CodePanel, PlaygroundPanel


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

        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Panel"))
        self.selector = QComboBox()
        self.selector.addItems(["Trigonometry", "Complex Plane", "Linear Algebra", "Code Animation", "Playground"])
        self.selector.currentIndexChanged.connect(self._switch)
        sel_row.addWidget(self.selector)
        sel_row.addStretch()
        root.addLayout(sel_row)

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
        self.playground = PlaygroundPanel()
        for p in [self.trig, self.complex, self.linear, self.code, self.playground]:
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
        self.playground.setVisible(idx == 4)

    def _active(self):
        return [self.trig, self.complex, self.linear, self.code, self.playground][self.selector.currentIndex()]

    def current_label(self):
        return ["trigonometry", "complex_plane", "linear_algebra", "code_animation", "playground"][self.selector.currentIndex()]

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

        pb = QHBoxLayout()
        for icon, fn in [
            ("⏮", lambda: self.player.setPosition(0)),
            ("⏵", self.player.play),
            ("⏸", self.player.pause),
            ("⏹", self.player.stop),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(36, 30)
            b.clicked.connect(fn)
            pb.addWidget(b)
        from PyQt6.QtWidgets import QCheckBox
        self.loop = QCheckBox("Loop")
        self.loop.setChecked(True)
        pb.addStretch()
        pb.addWidget(self.loop)
        root.addLayout(pb)

        self.player.mediaStatusChanged.connect(self._loop_check)
        self.player.playbackStateChanged.connect(self._on_playback_state)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(QLabel("BUILD LOG"))
        self.btn_log = QPushButton("hide")
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
        self.btn_log.setText("hide" if visible else "show")

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
        self._sb.addPermanentWidget(self.view_menu)
        self.setStatusBar(self._sb)

        self.left.render_requested.connect(self._render)
        self.left.btn_stop.clicked.connect(self._stop)

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
