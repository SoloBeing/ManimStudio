import os, shutil, platform

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QTextEdit,
    QScrollArea, QComboBox, QSizePolicy, QStatusBar,
    QFileDialog, QMessageBox, QCheckBox, QStyle,
    QStackedLayout, QFrame,
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
        self.selector.setObjectName("modeSelector")
        self.selector.addItems([
            "Trigonometry",
            "Complex Plane",
            "Linear Algebra",
            "Code Animation",
            "StreamLines",
            "Playground",
        ])
        self.selector.currentIndexChanged.connect(self._switch)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_label = QLabel("MODE")
        mode_label.setObjectName("comboLabel")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.selector, stretch=1)
        root.addLayout(mode_row)

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
        self.dir_label = QLabel(self._short_path(self.output_dir))
        self.dir_label.setObjectName("dim")
        self.dir_label.setToolTip(self.output_dir)
        btn_browse = QPushButton("Output")
        btn_browse.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        btn_browse.setFixedSize(108, 32)
        btn_browse.clicked.connect(self._browse_output)
        dir_row.addWidget(self.dir_label, stretch=1)
        dir_row.addWidget(btn_browse)
        root.addLayout(dir_row)

        root.addWidget(sep())
        bar = QHBoxLayout()
        bar.setSpacing(6)

        self.quality = QComboBox()
        self.quality.addItems(list(QUALITY.keys()))
        self.quality.setFixedWidth(120)

        self.btn_run = QPushButton("Render")
        self.btn_run.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_run.setObjectName("run")
        self.btn_run.setFixedHeight(36)
        self.btn_run.clicked.connect(self._render)

        self.btn_stop = QPushButton("")
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_stop.setToolTip("Stop render")
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
        return path if len(path) <= max_len else "..." + path[-(max_len - 3):]

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
        self.status_lbl = QLabel("Idle")
        self.status_lbl.setStyleSheet(f"color:{C['dim']};font-size:10px;")
        top.addWidget(lbl); top.addStretch(); top.addWidget(self.status_lbl)
        self.btn_save = QPushButton("Save")
        self.btn_save.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_save.setEnabled(False)
        self.btn_save.setToolTip("Save the current preview")
        self.btn_discard = QPushButton("Discard")
        self.btn_discard.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_discard.setEnabled(False)
        self.btn_discard.setToolTip("Discard the current preview")
        top.addWidget(self.btn_save)
        top.addWidget(self.btn_discard)
        root.addLayout(top)

        self.preview_stack = QStackedLayout()
        self.preview_stack.setContentsMargins(0, 0, 0, 0)
        empty_frame = QFrame()
        empty_frame.setObjectName("emptyPreview")
        empty_layout = QVBoxLayout(empty_frame)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = QLabel("Render preview")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_note = QLabel("Choose a mode, adjust parameters, then render.")
        self.empty_note.setObjectName("dim")
        self.empty_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_note, alignment=Qt.AlignmentFlag.AlignCenter)

        self.video = QVideoWidget()
        self.video.setStyleSheet(
            f"background:{C['bg0']};border:1px solid {C['border']};border-radius:8px;"
        )
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.player = QMediaPlayer()
        self.audio  = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.preview_stack.addWidget(empty_frame)
        self.preview_stack.addWidget(self.video)
        root.addLayout(self.preview_stack, stretch=1)

        pb = QHBoxLayout()
        for icon, tip, fn in [
            (QStyle.StandardPixmap.SP_MediaSkipBackward, "Restart", lambda: self.player.setPosition(0)),
            (QStyle.StandardPixmap.SP_MediaPlay, "Play", self.player.play),
            (QStyle.StandardPixmap.SP_MediaPause, "Pause", self.player.pause),
            (QStyle.StandardPixmap.SP_MediaStop, "Stop", self.player.stop),
        ]:
            b = QPushButton("")
            b.setIcon(self.style().standardIcon(icon))
            b.setToolTip(tip)
            b.setFixedSize(36, 30)
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

        self.latex_notice = QPushButton(
            "⚠  LaTeX not installed — MathTex / Tex objects unavailable. "
            "Install TinyTeX to enable math rendering.  (Click for details)"
        )
        self.latex_notice.setFlat(True)
        self.latex_notice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.latex_notice.setStyleSheet(
            "QPushButton {"
            " background:#2a1800; color:#e8a020;"
            " border:1px solid #6b3a00; border-radius:4px;"
            " padding:5px 8px; font-size:10px;"
            " text-align:left;"
            "}"
            "QPushButton:hover {"
            " background:#3a2200; border-color:#a05800;"
            "}"
        )
        self.latex_notice.hide()
        root.addWidget(self.latex_notice)

    def show_latex_notice(self):
        self.latex_notice.show()

    def set_empty_state(self, title, note):
        self.empty_title.setText(title)
        self.empty_note.setText(note)
        self.preview_stack.setCurrentIndex(0)

    def set_pending_actions(self, enabled):
        self.btn_save.setEnabled(enabled)
        self.btn_discard.setEnabled(enabled)

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.set_status("Playing", C['green'])
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.set_status("Paused", C['accent3'])
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.set_status("Stopped", C['accent2'])

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
        self.preview_stack.setCurrentIndex(1)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def release_media(self):
        self.player.stop()
        self.player.setSource(QUrl())

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
        self._pending_render_path = ""
        self._pending_render_stem = ""

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
        self._sb.showMessage("Ready - adjust parameters and hit Render")
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
        self.right.btn_save.clicked.connect(self._save_pending_render)
        self.right.btn_discard.clicked.connect(self._discard_pending_render)

        QTimer.singleShot(300, self._check_latex)

    def _check_latex(self):
        latex_ok = bool(shutil.which("latex") and shutil.which("dvisvgm"))

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
                self.right.latex_notice.clicked.connect(self._reshow_latex_dialog)
                return
            self._show_latex_missing_dialog(with_checkbox=True)
            self.right.show_latex_notice()
            self.right.latex_notice.clicked.connect(self._reshow_latex_dialog)

    def _show_latex_missing_dialog(self, with_checkbox):
        missing = [t for t in ("latex", "dvisvgm") if not shutil.which(t)]
        sys_name = platform.system()
        if sys_name == "Windows":
            cmd = "winget install TinyTeX-org.TinyTeX"
        elif sys_name == "Darwin":
            cmd = 'curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
        else:
            cmd = 'wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh'
        msg = QMessageBox(self)
        if with_checkbox:
            msg.setWindowTitle("LaTeX Not Found")
            msg.setIcon(QMessageBox.Icon.Warning)
        else:
            msg.setWindowTitle("LaTeX Setup")
            msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            f"<b>{', '.join(missing)}</b> not found on PATH.<br><br>"
            "<tt>Text()</tt> animations work fine without it — LaTeX is only needed "
            "for <tt>MathTex()</tt> and <tt>Tex()</tt> objects.<br><br>"
            "Install <b>TinyTeX</b> to enable math rendering:<br>"
            f"<tt>{cmd}</tt>"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        if with_checkbox:
            cb = QCheckBox("Don't show this again")
            msg.setCheckBox(cb)
            msg.exec()
            if cb.isChecked():
                _dir = os.path.dirname(_LATEX_WARNED_FLAG)
                os.makedirs(_dir, exist_ok=True)
                open(_LATEX_WARNED_FLAG, "w").close()
        else:
            msg.exec()

    def _reshow_latex_dialog(self):
        self._show_latex_missing_dialog(with_checkbox=False)

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
        self._clear_pending_render(delete=True)
        self._render_stopped = False
        flags = QUALITY[self.left.quality.currentText()]
        self.right.log.clear()
        self.right.set_pending_actions(False)
        self.right.set_status("Rendering...", C['accent3'])
        self.left.btn_run.setEnabled(False)
        self.left.btn_stop.setEnabled(True)
        self._sb.showMessage("Rendering...")

        self._render_label = self.left.current_label()
        self._thread = RenderThread(source, flags, self.left.output_dir)
        self._thread.log.connect(self.right.append_log)
        self._thread.done.connect(self._done)
        self._thread.start()

    def _stop(self):
        self._render_stopped = True
        stem = self._thread.render_stem if self._thread else ""
        if self._thread:
            try:
                self._thread.done.disconnect(self._done)
            except TypeError:
                pass
            self._thread.stop()
            self._thread.wait(5000)
            if not stem:
                stem = self._thread.render_stem or ""
        self._cleanup_render_artifacts(stem)
        self.left.btn_run.setEnabled(True)
        self.left.btn_stop.setEnabled(False)
        self.right.set_status("Stopped", C['accent2'])
        self._sb.showMessage("Stopped")

    def closeEvent(self, event):
        if self._has_unsaved_render():
            choice = self._confirm_unsaved_render_exit()
            if choice == "cancel":
                event.ignore()
                return
            if choice == "save" and not self._save_pending_render():
                event.ignore()
                return
            if choice == "discard":
                self._clear_pending_render(delete=True)

        if self._thread and self._thread.isRunning():
            try:
                self._thread.done.disconnect(self._done)
            except TypeError:
                pass
            self._thread.stop()
            self._thread.wait()
        self._clear_pending_render(delete=True)
        event.accept()

    def _done(self, path: str):
        if self._render_stopped:
            return
        self.left.btn_run.setEnabled(True)
        self.left.btn_stop.setEnabled(False)
        if not (path and os.path.exists(path)):
            self.right.set_pending_actions(False)
            self.right.set_empty_state("Render failed", "Open the build log for details.")
            self.right.set_status("Failed", C['red'])
            self._sb.showMessage("Render failed - see log")
            return

        self._pending_render_path = path
        self._pending_render_stem = self._thread.render_stem if self._thread else ""
        self.right.load(path)
        self.right.set_pending_actions(True)
        self.right.set_status("Preview ready", C['green'])
        self._sb.showMessage("Preview ready - save or discard the render")

    def _save_pending_render(self):
        path = self._pending_render_path
        if not (path and os.path.exists(path)):
            self._clear_pending_render(delete=False)
            self._sb.showMessage("No render available to save")
            return False

        ext      = os.path.splitext(path)[1].lower()
        filt     = "GIF (*.gif)" if ext == ".gif" else "MP4 Video (*.mp4)"
        default  = os.path.join(self.left.output_dir, f"{self._render_label}{ext}")
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Render As", default, filt)

        if save_path:
            stem = self._pending_render_stem
            self.right.release_media()
            try:
                shutil.move(path, save_path)
                path = save_path
            except OSError as e:
                self.right.append_log(f"[WARN] could not move file: {e}")
                self.right.load(path)
                return False
            self.right.load(path)
            self._cleanup_render_artifacts(stem, keep_path=path)
            self.right.set_pending_actions(False)
            self._pending_render_path = ""
            self._pending_render_stem = ""
            self.right.set_status("Playing", C['green'])
            self._sb.showMessage(f"Saved  {path}")
            return True
        else:
            self._sb.showMessage("Save cancelled - preview still available")
            return False

    def _has_unsaved_render(self):
        return bool(self._pending_render_path and os.path.exists(self._pending_render_path))

    def _confirm_unsaved_render_exit(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Render")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("You're exiting without saving.")
        msg.setInformativeText("Do you want to save?")
        msg.setWindowModality(Qt.WindowModality.ApplicationModal)

        btn_save = msg.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_save:
            return "save"
        if clicked == btn_discard:
            return "discard"
        if clicked == btn_cancel:
            return "cancel"
        return "cancel"

    def _discard_pending_render(self):
        self._clear_pending_render(delete=True)
        self.right.set_empty_state("Render discarded", "Adjust parameters and render again.")
        self.right.set_status("Idle", C['dim'])
        self._sb.showMessage("Render discarded")

    def _clear_pending_render(self, delete):
        path = self._pending_render_path
        stem = self._pending_render_stem
        self.right.set_pending_actions(False)
        self._pending_render_path = ""
        self._pending_render_stem = ""
        if delete and path and os.path.exists(path):
            self.right.release_media()
            try:
                os.unlink(path)
            except OSError:
                pass
        if delete and stem:
            self._cleanup_render_artifacts(stem)

    def _cleanup_render_artifacts(self, stem="", keep_path=""):
        media_dirs = ("videos", "images", "texts", "Tex")
        keep_path = os.path.abspath(keep_path) if keep_path else ""
        if stem:
            for subdir in media_dirs:
                d = os.path.join(self.left.output_dir, subdir, stem)
                if keep_path and self._is_relative_to(keep_path, d):
                    continue
                shutil.rmtree(d, ignore_errors=True)

        for root, dirs, _ in os.walk(self.left.output_dir, topdown=False):
            for name in dirs:
                if (
                    name != stem
                    and not name.startswith("tmp")
                    and name not in media_dirs
                ):
                    continue
                path = os.path.join(root, name)
                try:
                    os.rmdir(path)
                except OSError:
                    pass

        for subdir in media_dirs:
            d = os.path.join(self.left.output_dir, subdir)
            if keep_path and self._is_relative_to(keep_path, d):
                continue
            shutil.rmtree(d, ignore_errors=True)

    @staticmethod
    def _is_relative_to(path, parent):
        try:
            return os.path.commonpath([path, os.path.abspath(parent)]) == os.path.abspath(parent)
        except ValueError:
            return False
