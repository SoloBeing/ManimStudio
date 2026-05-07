from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QCheckBox, QComboBox, QDoubleSpinBox, QTextEdit, QPushButton,
)
from PyQt6.QtGui import QFont

from theme import C
from widgets import sep, hdr, Knob
from builders import (
    build_trig_source, build_complex_source,
    build_linear_source, build_code_source,
    build_streamlines_source,
)


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
        self.anim = QComboBox()
        self.anim.setObjectName("animationCombo")
        self.anim.addItems(["Create", "FadeIn", "Write"])
        a_row.addWidget(self.anim)
        a_row.addStretch()
        v.addLayout(a_row)
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
        )


class ComplexPanel(QGroupBox):
    def __init__(self):
        super().__init__("Complex Plane")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("FUNCTION MODE"))
        self.mode = QComboBox()
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
        v.addStretch()

    def source(self):
        return build_complex_source(
            mode        = self.mode.currentText(),
            re_c        = self.re_c.value(),
            im_c        = self.im_c.value(),
            scale       = self.scale.value(),
            n_pts       = self.n_pts.value(),
            show_arrows = self.cb_arrows.isChecked(),
        )


class LinearPanel(QGroupBox):
    def __init__(self):
        super().__init__("Linear Algebra")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("2x2 MATRIX"))
        g = QGridLayout()
        g.setSpacing(6)
        self.spins = {}
        defaults   = {"a": 2.0, "b": 0.5, "c": 0.5, "d": 2.0}
        positions  = [("a",0,0), ("b",0,2), ("c",1,0), ("d",1,2)]
        for key, row_, col_ in positions:
            g.addWidget(QLabel(key), row_, col_)
            s = QDoubleSpinBox()
            s.setRange(-9, 9); s.setSingleStep(0.25); s.setDecimals(2)
            s.setValue(defaults[key])
            self.spins[key] = s
            g.addWidget(s, row_, col_ + 1)
        v.addLayout(g)

        v.addWidget(sep())
        v.addWidget(hdr("INPUT VECTOR"))
        vrow = QHBoxLayout()
        self.vx = QDoubleSpinBox(); self.vx.setRange(-5, 5); self.vx.setValue(1.0); self.vx.setSingleStep(0.5)
        self.vy = QDoubleSpinBox(); self.vy.setRange(-5, 5); self.vy.setValue(1.0); self.vy.setSingleStep(0.5)
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
        v.addStretch()

    def source(self):
        return build_linear_source(
            a = self.spins["a"].value(), b = self.spins["b"].value(),
            c = self.spins["c"].value(), d = self.spins["d"].value(),
            vx = self.vx.value(),        vy = self.vy.value(),
            show_det   = self.cb_det.isChecked(),
            show_basis = self.cb_basis.isChecked(),
            show_grid  = self.cb_grid.isChecked(),
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
        self.lang = QComboBox()
        self.lang.addItems([
            "Python", "C", "Cpp", "Java", "JavaScript",
            "TypeScript", "Rust", "Go", "Bash", "SQL",
        ])
        v.addWidget(self.lang)

        v.addWidget(sep())
        v.addWidget(hdr("ANIMATION STYLE"))
        self.anim = QComboBox()
        self.anim.setObjectName("animationCombo")
        self.anim.addItems(["Write", "FadeIn", "FadeIn Up", "Create", "Typewriter"])
        v.addWidget(self.anim)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))

        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("Background"))
        self.bg = QComboBox()
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
        )


class StreamLinesPanel(QGroupBox):
    def __init__(self):
        super().__init__("StreamLines")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("VECTOR FIELD"))
        self.mode = QComboBox()
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
        v.addStretch()

    def source(self):
        return build_streamlines_source(
            mode         = self.mode.currentData(),
            scale        = self.scale.value(),
            spacing      = self.spacing.value(),
            flow_speed   = self.flow_speed.value(),
            virtual_time = self.virtual_time.value(),
            stroke_width = self.stroke_width.value(),
            show_axes    = self.cb_axes.isChecked(),
            animate      = self.cb_animate.isChecked(),
        )


_PLAYGROUND_TEMPLATE = """\
from manim import *

class ManimScene(Scene):
    def construct(self):
        # Write any Manim code here — the class MUST be named ManimScene

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
        v.addWidget(self.editor, stretch=1)

        note = QLabel("The scene class must be named  ManimScene")
        note.setObjectName("dim")
        note.setStyleSheet(f"color:{C['dim']};font-size:9px;")
        v.addWidget(note)

    def _reset(self):
        self.editor.setText(_PLAYGROUND_TEMPLATE)

    def source(self):
        return self.editor.toPlainText()
