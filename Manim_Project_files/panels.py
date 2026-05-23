import ast

from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QCheckBox, QLineEdit, QTextEdit, QPushButton, QSizePolicy,
    QGraphicsOpacityEffect, QComboBox,
)
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QBrush, QFontDatabase
from PyQt6.QtCore import Qt, QPointF, pyqtSignal

from theme import C
from widgets import sep, hdr, Knob, SpinBox, ComboBox
from renderer import find_all_scene_classes
from builders import (
    build_trig_source, build_complex_source,
    build_linear_source, build_nonlinear_source, build_code_source,
    build_streamlines_source,
)


TEXT_POSITION_OPTIONS = [
    ("Top Left",      "top_left"),
    ("Top Center",    "top_center"),
    ("Top Right",     "top_right"),
    ("Center Left",   "center_left"),
    ("Center",        "center"),
    ("Center Right",  "center_right"),
    ("Bottom Left",   "bottom_left"),
    ("Bottom Center", "bottom_center"),
    ("Bottom Right",  "bottom_right"),
    ("Free (X/Y)",    "free"),
]

TEXT_COLOR_OPTIONS = [
    ("White",       "white"),
    ("Blue",        "blue"),
    ("Teal",        "teal"),
    ("Green",       "green"),
    ("Yellow",      "yellow"),
    ("Orange",      "orange"),
    ("Red",         "red"),
    ("Purple",      "purple"),
    ("Pink",        "pink"),
    ("Gold",        "gold"),
    ("Maroon",      "maroon"),
    ("Light Blue",  "light_blue"),
    ("Light Green", "light_green"),
    ("Grey",        "grey"),
    ("Black",       "black"),
    ("Teal B",      "teal_b"),
]

FONT_OPTIONS = [
    "Arial",
    "DejaVu Sans",
    "Liberation Sans",
    "Noto Sans",
    "Consolas",
    "Courier New",
    "Georgia",
    "Times New Roman",
    "Verdana",
    "Helvetica",
    "Ubuntu",
    "Fira Code",
    "JetBrains Mono",
    "Impact",
    "Comic Sans MS",
]


def _available_fonts():
    """Filter FONT_OPTIONS to fonts actually installed on this machine.
    Must be called after QApplication is constructed."""
    installed = set(QFontDatabase.families())
    found = [f for f in FONT_OPTIONS if f in installed]
    return found if found else ["serif"]

# Approximate Manim-space anchor for each preset (frame is ±7.11 × ±4.0)
_PRESET_XY = {
    "top_left":      (-5.8,  3.3),
    "top_center":    ( 0.0,  3.3),
    "top_right":     ( 5.8,  3.3),
    "center_left":   (-5.8,  0.0),
    "center":        ( 0.0,  0.0),
    "center_right":  ( 5.8,  0.0),
    "bottom_left":   (-5.8, -3.3),
    "bottom_center": ( 0.0, -3.3),
    "bottom_right":  ( 5.8, -3.3),
    "free":          ( 0.0,  0.0),
}

_MANIM_W = 14.222
_MANIM_H = 8.0


class PositionPreview(QWidget):
    """Live canvas showing where text lands; draggable in Free mode."""
    position_dragged = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._mx = 0.0
        self._my = 0.0
        self._free = False
        self._dragging = False

    def set_free_mode(self, enabled):
        self._free = enabled
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.update()

    def set_position(self, mx, my):
        self._mx = float(mx)
        self._my = float(my)
        self.update()

    def _to_px(self, mx, my):
        w, h = self.width(), self.height()
        return (mx / _MANIM_W + 0.5) * w, (0.5 - my / _MANIM_H) * h

    def _to_manim(self, px, py):
        w, h = self.width(), self.height()
        mx = round((px / w - 0.5) * _MANIM_W, 2)
        my = round((0.5 - py / h) * _MANIM_H, 2)
        return (max(-_MANIM_W / 2, min(_MANIM_W / 2, mx)),
                max(-_MANIM_H / 2, min(_MANIM_H / 2, my)))

    def mousePressEvent(self, event):
        if self._free and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._handle_drag(event.position())

    def mouseMoveEvent(self, event):
        if self._dragging and self._free:
            self._handle_drag(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def _handle_drag(self, qpos):
        mx, my = self._to_manim(qpos.x(), qpos.y())
        self._mx, self._my = mx, my
        self.update()
        self.position_dragged.emit(mx, my)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.fillRect(self.rect(), QColor("#09111a"))

        # 3×3 grid — cells match the 9 preset positions
        grid_pen = QPen(QColor("#1c2e40"))
        grid_pen.setWidth(1)
        p.setPen(grid_pen)
        for i in (1, 2):
            p.drawLine(int(w * i / 3), 0, int(w * i / 3), h)
            p.drawLine(0, int(h * i / 3), w, int(h * i / 3))

        # Axis cross
        axis_pen = QPen(QColor("#1e3a52"))
        axis_pen.setWidth(1)
        p.setPen(axis_pen)
        p.drawLine(w // 2, 0, w // 2, h)
        p.drawLine(0, h // 2, w, h // 2)

        # Frame border — brighter when interactive
        border_pen = QPen(QColor("#3a70a0") if self._free else QColor("#2a4560"))
        border_pen.setWidth(1)
        p.setPen(border_pen)
        p.drawRect(0, 0, w - 1, h - 1)

        # Clamp marker to visible area
        mx_px, my_px = self._to_px(self._mx, self._my)
        mx_px = max(4.0, min(w - 4.0, mx_px))
        my_px = max(4.0, min(h - 4.0, my_px))

        accent = QColor("#33aaff") if self._free else QColor("#2277aa")

        # Crosshair lines extending to widget edges
        ch_pen = QPen(accent)
        ch_pen.setWidth(1)
        p.setPen(ch_pen)
        p.drawLine(0, int(my_px), w, int(my_px))
        p.drawLine(int(mx_px), 0, int(mx_px), h)

        # Dot
        p.setBrush(QBrush(accent))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(mx_px, my_px), 4.0, 4.0)

        p.end()


GRADIENT_OPTIONS = [
    ("None",        "none"),
    ("Red → Blue",  "red_blue"),
    ("Blue → Green","blue_green"),
    ("Gold → White","gold_white"),
    ("Teal → Yellow","teal_yellow"),
    ("Rainbow",     "rainbow"),
    ("Orange → Red","orange_red"),
]


def add_text_controls(layout, default_position="top_left", default_color="white"):
    layout.addWidget(sep())
    layout.addWidget(hdr("TEXT"))
    row = QGridLayout()
    row.setSpacing(6)

    text_inp = QLineEdit()
    text_inp.setPlaceholderText("Custom label…")

    pos  = ComboBox()
    col  = ComboBox()
    font = ComboBox()
    gradient = ComboBox()
    stroke_col = ComboBox()

    for label, key in TEXT_POSITION_OPTIONS:
        pos.addItem(label, key)
    for label, key in TEXT_COLOR_OPTIONS:
        col.addItem(label, key)
        stroke_col.addItem(label, key)
    font.addItems(_available_fonts())
    for label, key in GRADIENT_OPTIONS:
        gradient.addItem(label, key)

    for combo, default in [(pos, default_position), (col, default_color)]:
        idx = combo.findData(default)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    size_inp = SpinBox()
    size_inp.setRange(8, 72)
    size_inp.setDecimals(0)
    size_inp.setSingleStep(1)
    size_inp.setValue(22)
    size_inp.setFixedWidth(72)

    stroke_w = SpinBox()
    stroke_w.setRange(0, 20)
    stroke_w.setDecimals(1)
    stroke_w.setSingleStep(0.5)
    stroke_w.setValue(0)
    stroke_w.setFixedWidth(72)

    x_off = SpinBox()
    x_off.setRange(-8, 8)
    x_off.setDecimals(2)
    x_off.setSingleStep(0.1)
    x_off.setValue(0)
    x_off.setFixedWidth(72)

    y_off = SpinBox()
    y_off.setRange(-5, 5)
    y_off.setDecimals(2)
    y_off.setSingleStep(0.1)
    y_off.setValue(0)
    y_off.setFixedWidth(72)

    bold_cb   = QCheckBox("Bold")
    italic_cb = QCheckBox("Italic")
    cb_labels = QCheckBox("Preset Labels")
    cb_labels.setChecked(True)

    col_lbl = QLabel("Color")
    _col_lbl_fx = QGraphicsOpacityEffect(); col_lbl.setGraphicsEffect(_col_lbl_fx)
    _col_fx     = QGraphicsOpacityEffect(); col.setGraphicsEffect(_col_fx)

    row.addWidget(QLabel("Label"),    0, 0); row.addWidget(text_inp,   0, 1)
    row.addWidget(QLabel("Position"), 1, 0); row.addWidget(pos,        1, 1)
    row.addWidget(col_lbl,            2, 0); row.addWidget(col,        2, 1)
    row.addWidget(QLabel("Font"),     3, 0); row.addWidget(font,       3, 1)
    row.addWidget(QLabel("Size"),     4, 0); row.addWidget(size_inp,   4, 1)
    row.addWidget(QLabel("Gradient"), 5, 0); row.addWidget(gradient,   5, 1)

    style_row = QHBoxLayout()
    style_row.addWidget(bold_cb)
    style_row.addWidget(italic_cb)
    style_row.addStretch()
    style_widget = QWidget()
    style_widget.setLayout(style_row)
    row.addWidget(QLabel("Style"),    6, 0); row.addWidget(style_widget, 6, 1)

    row.addWidget(QLabel("Stroke W"), 7, 0); row.addWidget(stroke_w,  7, 1)
    row.addWidget(QLabel("Stroke C"), 8, 0); row.addWidget(stroke_col, 8, 1)
    x_lbl = QLabel("X Offset")
    y_lbl = QLabel("Y Offset")

    preview = PositionPreview()
    hint_lbl = QLabel()
    hint_lbl.setWordWrap(True)

    def _sync_all():
        is_free     = pos.currentData() == "free"
        is_gradient = gradient.currentData() != "none"

        # Color and gradient are mutually exclusive
        col.setEnabled(not is_gradient)
        if is_gradient:
            _col_lbl_fx.setOpacity(0.3)
            _col_fx.setOpacity(0.3)
        else:
            _col_lbl_fx.setOpacity(1.0)
            _col_fx.setOpacity(1.0)

        x_lbl.setText("X Pos" if is_free else "X Offset")
        y_lbl.setText("Y Pos" if is_free else "Y Offset")
        preview.set_free_mode(is_free)
        if is_free:
            hint_lbl.setText("Drag crosshair to set position")
            hint_lbl.setStyleSheet("font-size:9px; color:#33aaff;")
            preview.set_position(x_off.value(), y_off.value())
        else:
            hint_lbl.setText("Crosshair drag only available in Free (X/Y) mode")
            hint_lbl.setStyleSheet("font-size:9px; color:#4a6a8a;")
            bx, by = _PRESET_XY.get(pos.currentData() or "center", (0.0, 0.0))
            preview.set_position(bx + x_off.value(), by + y_off.value())

    def _on_dragged(mx, my):
        x_off.blockSignals(True)
        y_off.blockSignals(True)
        x_off.setValue(mx)
        y_off.setValue(my)
        x_off.blockSignals(False)
        y_off.blockSignals(False)

    pos.currentIndexChanged.connect(lambda _: _sync_all())
    gradient.currentIndexChanged.connect(lambda _: _sync_all())
    x_off.valueChanged.connect(lambda _: _sync_all())
    y_off.valueChanged.connect(lambda _: _sync_all())
    preview.position_dragged.connect(_on_dragged)
    _sync_all()

    row.addWidget(x_lbl,      9, 0); row.addWidget(x_off,      9, 1)
    row.addWidget(y_lbl,     10, 0); row.addWidget(y_off,     10, 1)
    row.addWidget(cb_labels, 11, 0, 1, 2)
    row.addWidget(preview,   12, 0, 1, 2)
    row.addWidget(hint_lbl,  13, 0, 1, 2)

    layout.addLayout(row)
    return pos, col, font, text_inp, size_inp, cb_labels, bold_cb, italic_cb, stroke_w, stroke_col, x_off, y_off, gradient


class TrigPanel(QGroupBox):
    def __init__(self):
        super().__init__("Trigonometric Functions")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("FUNCTIONS"))
        fn_row = QHBoxLayout()
        self.cb_sin = QCheckBox("Sin(x)"); self.cb_sin.setChecked(True)
        self.cb_cos = QCheckBox("Cos(x)"); self.cb_cos.setChecked(True)
        self.cb_tan = QCheckBox("Tan(x)")
        for cb in [self.cb_sin, self.cb_cos, self.cb_tan]:
            fn_row.addWidget(cb)
        fn_row.addStretch()
        v.addLayout(fn_row)

        v.addWidget(sep())
        v.addWidget(hdr("PARAMETERS"))
        self.amp   = Knob("Amplitude A",  0.1, 4.0, 1.0)
        self.freq  = Knob("Frequency w",  0.1, 5.0, 1.0)
        self.phase = Knob("Phase p",     -6.3, 6.3, 0.0)
        self.vsh   = Knob("Vertical D",  -3.0, 3.0, 0.0)
        self.xrng  = Knob("X Range",      1.0, 8.0, 4.0, decimals=1, step=0.5)
        for k in [self.amp, self.freq, self.phase, self.vsh, self.xrng]:
            v.addWidget(k)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))
        d_row = QHBoxLayout()
        self.cb_grid = QCheckBox("Grid")
        self.cb_grid.setChecked(True)
        d_row.addWidget(self.cb_grid)
        d_row.addStretch()
        v.addLayout(d_row)

        a_row = QHBoxLayout()
        anim_lbl = QLabel("Animation style")
        anim_lbl.setObjectName("comboLabel")
        a_row.addWidget(anim_lbl)
        self.anim = ComboBox()
        self.anim.setObjectName("animationCombo")
        self.anim.addItems(["Create", "FadeIn", "Write"])
        a_row.addWidget(self.anim)
        a_row.addStretch()
        v.addLayout(a_row)
        (self.text_pos, self.text_col, self.text_font, self.text_inp, self.text_size,
         self.text_labels, self.text_bold, self.text_italic, self.text_stroke_w,
         self.text_stroke_col, self.text_x_off, self.text_y_off,
         self.text_gradient) = add_text_controls(v, "top_right", "white")
        v.addStretch()

    def source(self):
        return build_trig_source(
            show_sin  = self.cb_sin.isChecked(),
            show_cos  = self.cb_cos.isChecked(),
            show_tan  = self.cb_tan.isChecked(),
            A  = self.amp.value(),
            w  = self.freq.value(),
            ph = self.phase.value(),
            D  = self.vsh.value(),
            xr = self.xrng.value(),
            show_grid = self.cb_grid.isChecked(),
            anim      = self.anim.currentText(),
            text_position      = self.text_pos.currentData(),
            text_color         = self.text_col.currentData(),
            text_font          = self.text_font.currentText(),
            text_content       = self.text_inp.text(),
            text_font_size     = int(self.text_size.value()),
            show_preset_labels = self.text_labels.isChecked(),
            bold         = self.text_bold.isChecked(),
            italic       = self.text_italic.isChecked(),
            stroke_width = self.text_stroke_w.value(),
            stroke_color = self.text_stroke_col.currentData(),
            x_offset     = self.text_x_off.value(),
            y_offset     = self.text_y_off.value(),
            gradient     = self.text_gradient.currentData(),
        )


class ComplexPanel(QGroupBox):
    def __init__(self):
        super().__init__("Complex Plane")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("FUNCTION MODE"))
        self.mode = ComboBox()
        self.mode.addItems([
            "f(z) = z^2",
            "f(z) = z^3 - 1",
            "f(z) = 1/z",
            "f(z) = e^z",
            "Mobius Transform",
        ])
        v.addWidget(self.mode)

        v.addWidget(sep())
        v.addWidget(hdr("PARAMETERS"))
        self.re_c  = Knob("Re(c)",      -2.0, 2.0, -0.5)
        self.im_c  = Knob("Im(c)",      -2.0, 2.0,  0.5)
        self.scale = Knob("View Scale",  0.5, 4.0,  2.0, decimals=1, step=0.1)
        self.n_pts = Knob("Num Points",  4.0,24.0, 12.0, decimals=0, step=1.0)
        for k in [self.re_c, self.im_c, self.scale, self.n_pts]:
            v.addWidget(k)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))
        d_row = QHBoxLayout()
        self.cb_arrows = QCheckBox("Show Arrows")
        self.cb_arrows.setChecked(True)
        d_row.addWidget(self.cb_arrows)
        d_row.addStretch()
        v.addLayout(d_row)
        (self.text_pos, self.text_col, self.text_font, self.text_inp, self.text_size,
         self.text_labels, self.text_bold, self.text_italic, self.text_stroke_w,
         self.text_stroke_col, self.text_x_off, self.text_y_off,
         self.text_gradient) = add_text_controls(v, "top_left", "teal")
        v.addStretch()

    def source(self):
        return build_complex_source(
            mode        = self.mode.currentText(),
            re_c        = self.re_c.value(),
            im_c        = self.im_c.value(),
            scale       = self.scale.value(),
            n_pts       = self.n_pts.value(),
            show_arrows = self.cb_arrows.isChecked(),
            text_position      = self.text_pos.currentData(),
            text_color         = self.text_col.currentData(),
            text_font          = self.text_font.currentText(),
            text_content       = self.text_inp.text(),
            text_font_size     = int(self.text_size.value()),
            show_preset_labels = self.text_labels.isChecked(),
            bold         = self.text_bold.isChecked(),
            italic       = self.text_italic.isChecked(),
            stroke_width = self.text_stroke_w.value(),
            stroke_color = self.text_stroke_col.currentData(),
            x_offset     = self.text_x_off.value(),
            y_offset     = self.text_y_off.value(),
            gradient     = self.text_gradient.currentData(),
        )


class LinearPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        linear_box = QGroupBox("Linear Algebra")
        v = QVBoxLayout(linear_box)
        v.setSpacing(6)

        v.addWidget(hdr("PRESET ANIMATION"))
        self.preset = ComboBox()
        for label, values in [
            ("Custom", None),
            ("Rotate 45 deg", (0.71, -0.71, 0.71, 0.71, 2.0, 1.0)),
            ("Shear X", (1.0, 1.25, 0.0, 1.0, 1.0, 1.5)),
            ("Shear Y", (1.0, 0.0, 1.25, 1.0, 1.5, 1.0)),
            ("Reflect X Axis", (1.0, 0.0, 0.0, -1.0, 1.5, 1.0)),
            ("Reflect Y Axis", (-1.0, 0.0, 0.0, 1.0, 1.5, 1.0)),
            ("Projection X", (1.0, 0.0, 0.0, 0.0, 1.5, 1.5)),
            ("Scale Stretch", (2.0, 0.0, 0.0, 0.5, 1.0, 1.5)),
            ("Collapse Line", (1.0, 1.0, 0.5, 0.5, 1.0, 2.0)),
        ]:
            self.preset.addItem(label, values)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        v.addWidget(self.preset)

        v.addWidget(sep())
        v.addWidget(hdr("2x2 MATRIX"))
        g = QGridLayout()
        g.setSpacing(6)
        self.spins = {}
        defaults   = {"a": 2.0, "b": 0.5, "c": 0.5, "d": 2.0}
        positions  = [("a",0,0), ("b",0,2), ("c",1,0), ("d",1,2)]
        for key, row_, col_ in positions:
            g.addWidget(QLabel(key), row_, col_)
            s = SpinBox()
            s.setRange(-9, 9); s.setSingleStep(0.25); s.setDecimals(2)
            s.setValue(defaults[key])
            self.spins[key] = s
            g.addWidget(s, row_, col_ + 1)
        v.addLayout(g)

        v.addWidget(sep())
        v.addWidget(hdr("INPUT VECTOR"))
        vrow = QHBoxLayout()
        self.vx = SpinBox(); self.vx.setRange(-5, 5); self.vx.setValue(1.0); self.vx.setSingleStep(0.5)
        self.vy = SpinBox(); self.vy.setRange(-5, 5); self.vy.setValue(1.0); self.vy.setSingleStep(0.5)
        vrow.addWidget(QLabel("Vx")); vrow.addWidget(self.vx)
        vrow.addWidget(QLabel("Vy")); vrow.addWidget(self.vy)
        vrow.addStretch()
        v.addLayout(vrow)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))
        d_row = QHBoxLayout()
        self.cb_det   = QCheckBox("Det");   self.cb_det.setChecked(True)
        self.cb_basis = QCheckBox("Basis"); self.cb_basis.setChecked(True)
        self.cb_grid  = QCheckBox("Grid");  self.cb_grid.setChecked(True)
        for cb in [self.cb_det, self.cb_basis, self.cb_grid]:
            d_row.addWidget(cb)
        d_row.addStretch()
        v.addLayout(d_row)

        (self.text_pos, self.text_col, self.text_font, self.text_inp, self.text_size,
         self.text_labels, self.text_bold, self.text_italic, self.text_stroke_w,
         self.text_stroke_col, self.text_x_off, self.text_y_off,
         self.text_gradient) = add_text_controls(v, "top_left", "white")
        root.addWidget(linear_box)

        nonlinear_box = QGroupBox("Non-Linear Transformations")
        nv = QVBoxLayout(nonlinear_box)
        nv.setSpacing(6)

        self.cb_nonlinear = QCheckBox("Render Non-Linear Transformation")
        nv.addWidget(self.cb_nonlinear)

        nv.addWidget(sep())
        nv.addWidget(hdr("PRESET"))
        self.nl_preset = ComboBox()
        for label, key in [
            ("Swirl", "swirl"),
            ("Wave Warp", "wave"),
            ("Bulge", "bulge"),
            ("Pinch", "pinch"),
            ("Complex Square", "complex_square"),
        ]:
            self.nl_preset.addItem(label, key)
        nv.addWidget(self.nl_preset)

        nv.addWidget(sep())
        nv.addWidget(hdr("PARAMETERS"))
        self.nl_intensity = Knob("Intensity", 0.2, 3.0, 1.0, decimals=1, step=0.1)
        self.nl_scale     = Knob("View Scale", 2.0, 6.0, 4.0, decimals=1, step=0.5)
        nv.addWidget(self.nl_intensity)
        nv.addWidget(self.nl_scale)

        nv.addWidget(sep())
        nv.addWidget(hdr("DISPLAY"))
        nl_row = QHBoxLayout()
        self.cb_nl_grid = QCheckBox("Grid")
        self.cb_nl_grid.setChecked(True)
        self.cb_nl_points = QCheckBox("Points")
        self.cb_nl_points.setChecked(True)
        nl_row.addWidget(self.cb_nl_grid)
        nl_row.addWidget(self.cb_nl_points)
        nl_row.addStretch()
        nv.addLayout(nl_row)

        (self.nl_text_pos, self.nl_text_col, self.nl_text_font, self.nl_text_inp, self.nl_text_size,
         self.nl_text_labels, self.nl_text_bold, self.nl_text_italic, self.nl_text_stroke_w,
         self.nl_text_stroke_col, self.nl_text_x_off, self.nl_text_y_off,
         self.nl_text_gradient) = add_text_controls(nv, "top_right", "teal")

        root.addWidget(nonlinear_box)
        root.addStretch()

    def _apply_preset(self, idx):
        values = self.preset.itemData(idx)
        if values is None:
            return
        a, b, c, d, vx, vy = values
        for key, val in [("a", a), ("b", b), ("c", c), ("d", d)]:
            self.spins[key].setValue(val)
        self.vx.setValue(vx)
        self.vy.setValue(vy)

    def source(self):
        if self.cb_nonlinear.isChecked():
            return build_nonlinear_source(
                mode        = self.nl_preset.currentData(),
                intensity   = self.nl_intensity.value(),
                scale       = self.nl_scale.value(),
                show_grid   = self.cb_nl_grid.isChecked(),
                show_points = self.cb_nl_points.isChecked(),
                text_position      = self.nl_text_pos.currentData(),
                text_color         = self.nl_text_col.currentData(),
                text_font          = self.nl_text_font.currentText(),
                text_content       = self.nl_text_inp.text(),
                text_font_size     = int(self.nl_text_size.value()),
                show_preset_labels = self.nl_text_labels.isChecked(),
                bold         = self.nl_text_bold.isChecked(),
                italic       = self.nl_text_italic.isChecked(),
                stroke_width = self.nl_text_stroke_w.value(),
                stroke_color = self.nl_text_stroke_col.currentData(),
                x_offset     = self.nl_text_x_off.value(),
                y_offset     = self.nl_text_y_off.value(),
                gradient     = self.nl_text_gradient.currentData(),
            )

        return build_linear_source(
            a = self.spins["a"].value(), b = self.spins["b"].value(),
            c = self.spins["c"].value(), d = self.spins["d"].value(),
            vx = self.vx.value(),        vy = self.vy.value(),
            show_det   = self.cb_det.isChecked(),
            show_basis = self.cb_basis.isChecked(),
            show_grid  = self.cb_grid.isChecked(),
            text_position      = self.text_pos.currentData(),
            text_color         = self.text_col.currentData(),
            text_font          = self.text_font.currentText(),
            text_content       = self.text_inp.text(),
            text_font_size     = int(self.text_size.value()),
            show_preset_labels = self.text_labels.isChecked(),
            bold         = self.text_bold.isChecked(),
            italic       = self.text_italic.isChecked(),
            stroke_width = self.text_stroke_w.value(),
            stroke_color = self.text_stroke_col.currentData(),
            x_offset     = self.text_x_off.value(),
            y_offset     = self.text_y_off.value(),
            gradient     = self.text_gradient.currentData(),
        )


class CodePanel(QGroupBox):
    def __init__(self):
        super().__init__("Code Animation")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("CODE EDITOR"))
        self.editor = QTextEdit()
        self.editor.setFont(QFont("JetBrains Mono,Fira Code,Consolas", 10))
        self.editor.setPlaceholderText("# Write your code here…")
        self.editor.setMinimumHeight(220)
        self.editor.setStyleSheet(
            f"QTextEdit {{ background:#060d14; color:{C['text']};"
            f" border:1px solid {C['border']}; border-radius:6px;"
            f" font-family:'JetBrains Mono','Fira Code','Consolas',monospace;"
            f" font-size:11px; padding:6px; }}"
        )
        self.editor.setText(
            "def fibonacci(n):\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return fibonacci(n-1) + fibonacci(n-2)\n"
            "\n"
            "print(fibonacci(10))"
        )
        v.addWidget(self.editor)

        v.addWidget(sep())
        v.addWidget(hdr("LANGUAGE"))
        self.lang = ComboBox()
        self.lang.addItems([
            "Python", "C", "Cpp", "Java", "JavaScript",
            "TypeScript", "Rust", "Go", "Bash", "SQL",
        ])
        v.addWidget(self.lang)

        v.addWidget(sep())
        v.addWidget(hdr("ANIMATION STYLE"))
        self.anim = ComboBox()
        self.anim.setObjectName("animationCombo")
        self.anim.addItems(["Write", "FadeIn", "FadeIn Up", "Create", "Typewriter"])
        v.addWidget(self.anim)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))

        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("Background"))
        self.bg = ComboBox()
        self.bg.addItems(["Window", "Rectangle"])
        bg_row.addWidget(self.bg)
        bg_row.addStretch()
        v.addLayout(bg_row)

        ln_row = QHBoxLayout()
        self.cb_lineno = QCheckBox("Line numbers")
        self.cb_lineno.setChecked(True)
        ln_row.addWidget(self.cb_lineno)
        ln_row.addStretch()
        v.addLayout(ln_row)

        self.font_size = Knob("Font size",    8.0, 32.0, 16.0, decimals=0, step=1.0)
        self.run_time  = Knob("Duration (s)",  0.5, 15.0,  4.0, decimals=1, step=0.5)
        v.addWidget(self.font_size)
        v.addWidget(self.run_time)
        (self.text_pos, self.text_col, self.text_font, self.text_inp, self.text_size,
         self.text_labels, self.text_bold, self.text_italic, self.text_stroke_w,
         self.text_stroke_col, self.text_x_off, self.text_y_off,
         self.text_gradient) = add_text_controls(v, "top_left", "white")
        v.addStretch()

    def source(self):
        return build_code_source(
            code_str         = self.editor.toPlainText(),
            language         = self.lang.currentText(),
            anim             = self.anim.currentText(),
            background       = self.bg.currentText(),
            add_line_numbers = self.cb_lineno.isChecked(),
            font_size        = self.font_size.value(),
            run_time         = self.run_time.value(),
            text_position      = self.text_pos.currentData(),
            text_color         = self.text_col.currentData(),
            text_font          = self.text_font.currentText(),
            text_content       = self.text_inp.text(),
            text_font_size     = int(self.text_size.value()),
            show_preset_labels = self.text_labels.isChecked(),
            bold         = self.text_bold.isChecked(),
            italic       = self.text_italic.isChecked(),
            stroke_width = self.text_stroke_w.value(),
            stroke_color = self.text_stroke_col.currentData(),
            x_offset     = self.text_x_off.value(),
            y_offset     = self.text_y_off.value(),
            gradient     = self.text_gradient.currentData(),
        )


class StreamLinesPanel(QGroupBox):
    def __init__(self):
        super().__init__("StreamLines")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("VECTOR FIELD"))
        self.mode = ComboBox()
        for label, key in [
            ("Vortex", "vortex"),
            ("Source", "source"),
            ("Sink", "sink"),
            ("Saddle", "saddle"),
            ("Wave", "wave"),
        ]:
            self.mode.addItem(label, key)
        v.addWidget(self.mode)

        v.addWidget(sep())
        v.addWidget(hdr("PARAMETERS"))
        self.scale        = Knob("View Scale",    2.0, 7.0, 4.0, decimals=1, step=0.5)
        self.spacing      = Knob("Line Spacing",  0.2, 1.2, 0.5, decimals=1, step=0.1)
        self.flow_speed   = Knob("Flow Speed",    0.2, 4.0, 1.4, decimals=1, step=0.1)
        self.virtual_time = Knob("Trail Length",  1.0, 8.0, 4.0, decimals=1, step=0.5)
        self.stroke_width = Knob("Line Width",    0.5, 5.0, 1.6, decimals=1, step=0.1)
        for k in [self.scale, self.spacing, self.flow_speed, self.virtual_time, self.stroke_width]:
            v.addWidget(k)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))
        d_row = QHBoxLayout()
        self.cb_axes = QCheckBox("Grid")
        self.cb_axes.setChecked(True)
        self.cb_animate = QCheckBox("Animate Flow")
        self.cb_animate.setChecked(True)
        d_row.addWidget(self.cb_axes)
        d_row.addWidget(self.cb_animate)
        d_row.addStretch()
        v.addLayout(d_row)
        (self.text_pos, self.text_col, self.text_font, self.text_inp, self.text_size,
         self.text_labels, self.text_bold, self.text_italic, self.text_stroke_w,
         self.text_stroke_col, self.text_x_off, self.text_y_off,
         self.text_gradient) = add_text_controls(v, "top_left", "teal")
        v.addStretch()

    def source(self):
        return build_streamlines_source(
            mode           = self.mode.currentData(),
            scale          = self.scale.value(),
            spacing        = self.spacing.value(),
            flow_speed     = self.flow_speed.value(),
            virtual_time   = self.virtual_time.value(),
            stroke_width_sl= self.stroke_width.value(),
            show_axes      = self.cb_axes.isChecked(),
            animate        = self.cb_animate.isChecked(),
            text_position      = self.text_pos.currentData(),
            text_color         = self.text_col.currentData(),
            text_font          = self.text_font.currentText(),
            text_content       = self.text_inp.text(),
            text_font_size     = int(self.text_size.value()),
            show_preset_labels = self.text_labels.isChecked(),
            bold         = self.text_bold.isChecked(),
            italic       = self.text_italic.isChecked(),
            stroke_width = self.text_stroke_w.value(),
            stroke_color = self.text_stroke_col.currentData(),
            x_offset     = self.text_x_off.value(),
            y_offset     = self.text_y_off.value(),
            gradient     = self.text_gradient.currentData(),
        )


_PLAYGROUND_TEMPLATE = """\
from manim import *

class ManimScene(Scene):
    def construct(self):
        # Write any Manim code here — name the class anything you like

        circle = Circle(radius=1.5, color=BLUE)
        square = Square(side_length=2.5, color=RED)

        self.play(Create(circle), run_time=1.2)
        self.play(Transform(circle, square), run_time=1.5)
        self.play(FadeOut(circle), run_time=0.8)
        self.wait(1)
"""


class PlaygroundPanel(QGroupBox):
    def __init__(self):
        super().__init__("Playground")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        hdr_row = QHBoxLayout()
        hdr_row.addWidget(hdr("MANIM SOURCE"))
        hdr_row.addStretch()
        btn_reset = QPushButton("Reset")
        btn_reset.setFixedSize(64, 24)
        btn_reset.clicked.connect(self._reset)
        hdr_row.addWidget(btn_reset)
        v.addLayout(hdr_row)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("JetBrains Mono,Fira Code,Consolas", 10))
        self.editor.setStyleSheet(
            f"QTextEdit {{ background:#060d14; color:{C['text']};"
            f" border:1px solid {C['border']}; border-radius:6px;"
            f" font-family:'JetBrains Mono','Fira Code','Consolas',monospace;"
            f" font-size:11px; padding:6px; }}"
        )
        self.editor.setText(_PLAYGROUND_TEMPLATE)
        self.editor.textChanged.connect(self._refresh_scenes)
        v.addWidget(self.editor, stretch=1)

        scene_row = QHBoxLayout()
        scene_lbl = QLabel("SCENE")
        scene_lbl.setObjectName("dim")
        scene_lbl.setStyleSheet(f"color:{C['accent3']};font-size:10px;font-weight:700;")
        self._scene_combo = QComboBox()
        self._scene_combo.setObjectName("statusCombo")
        self._scene_combo.setToolTip("Select which scene class to render")
        scene_row.addWidget(scene_lbl)
        scene_row.addWidget(self._scene_combo, stretch=1)
        v.addLayout(scene_row)

        self._refresh_scenes()

    def _refresh_scenes(self):
        current = self._scene_combo.currentText()
        try:
            tree = ast.parse(self.editor.toPlainText())
            names = find_all_scene_classes(tree)
        except SyntaxError:
            names = []
        self._scene_combo.blockSignals(True)
        self._scene_combo.clear()
        if names:
            self._scene_combo.addItems(names)
            idx = self._scene_combo.findText(current)
            self._scene_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._scene_combo.setEnabled(True)
        else:
            self._scene_combo.addItem("No scene detected")
            self._scene_combo.setEnabled(False)
        self._scene_combo.blockSignals(False)

    def _reset(self):
        self.editor.setText(_PLAYGROUND_TEMPLATE)

    def source(self):
        return self.editor.toPlainText()

    def scene_name(self) -> str:
        if self._scene_combo.isEnabled():
            return self._scene_combo.currentText()
        return ""
