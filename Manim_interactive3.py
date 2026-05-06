"""
Manim Desmos Studio
═══════════════════
Architecture: Each domain panel owns a pure Python scene CLASS (not a string).
              Render writes that class to a temp file via inspect.getsource(),
              zero string templating.  Parameters are class attributes set
              before source extraction.

Layout : 30% left (params) | 70% right (video + log)
Install: pip install PyQt6 manim
Run    : python manim_desmos.py
"""

import sys, os, ast, subprocess, tempfile, shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QTextEdit, QSlider, QDoubleSpinBox,
    QGroupBox, QCheckBox, QScrollArea, QComboBox, QSizePolicy, QStatusBar,
    QFrame, QGridLayout, QFileDialog,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QFont

# ══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════
C = dict(
    bg0="#0d1117", bg1="#161b22", bg2="#1c2230", bg3="#21262d",
    border="#30363d", accent="#58a6ff", accent2="#f78166",
    accent3="#e3b341", text="#e6edf3", dim="#8b949e",
    green="#3fb950", red="#f85149", teal="#39d353",
)

STYLE = f"""
* {{ font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; color:{C['text']}; }}
QWidget {{ background:{C['bg0']}; }}
QScrollArea,QScrollBar {{ background:transparent; border:none; }}
QScrollBar:vertical {{ background:{C['bg1']}; width:5px; border-radius:2px; }}
QScrollBar::handle:vertical {{ background:{C['border']}; border-radius:2px; }}

QGroupBox {{
    border:1px solid {C['border']}; border-radius:7px;
    margin-top:16px; padding:10px 8px 8px 8px;
    background:{C['bg2']}; font-size:11px; font-weight:700;
}}
QGroupBox::title {{
    subcontrol-origin:margin; left:10px; padding:0 6px;
    color:{C['accent']}; font-size:10px; font-weight:700;
    text-transform:uppercase; letter-spacing:1px;
}}
QLabel {{ font-size:11px; }}
QLabel#dim  {{ color:{C['dim']}; font-size:10px; }}
QLabel#hdr  {{ color:{C['accent3']}; font-size:10px; font-weight:700;
               letter-spacing:1px; padding:4px 0 2px 0; }}

QDoubleSpinBox,QSpinBox,QComboBox {{
    background:{C['bg3']}; border:1px solid {C['border']};
    border-radius:5px; padding:3px 7px; font-size:11px;
}}
QDoubleSpinBox:focus,QComboBox:focus {{ border-color:{C['accent']}; }}
QComboBox QAbstractItemView {{ background:{C['bg2']}; selection-background-color:{C['accent']}; }}
QComboBox::drop-down {{ border:none; width:18px; }}

QCheckBox {{ font-size:11px; spacing:6px; }}
QCheckBox::indicator {{ width:13px; height:13px; border-radius:3px;
    border:1.5px solid {C['border']}; background:{C['bg3']}; }}
QCheckBox::indicator:checked {{ background:{C['accent']}; border-color:{C['accent']}; }}

QSlider::groove:horizontal {{ background:{C['bg3']}; height:3px; border-radius:2px; }}
QSlider::handle:horizontal {{ background:{C['accent']}; width:13px; height:13px;
    margin:-5px 0; border-radius:6px; border:2px solid {C['bg2']}; }}
QSlider::sub-page:horizontal {{ background:{C['accent']}; border-radius:2px; }}

QPushButton {{ background:{C['bg3']}; border:1px solid {C['border']};
    border-radius:6px; padding:6px 14px; font-size:11px; font-weight:600; }}
QPushButton:hover {{ border-color:{C['accent']}; color:{C['accent']}; }}
QPushButton#run {{ background:{C['accent']}; color:{C['bg0']}; border:none;
    padding:9px 28px; font-size:12px; font-weight:700; border-radius:6px; }}
QPushButton#run:hover {{ background:#79c0ff; }}
QPushButton#run:disabled {{ background:{C['bg3']}; color:{C['dim']}; }}
QPushButton#stop {{ border-color:{C['accent2']}; color:{C['accent2']}; }}
QPushButton#stop:hover {{ background:{C['accent2']}; color:{C['bg0']}; }}

QTextEdit {{ background:{C['bg1']}; border:1px solid {C['border']};
    border-radius:6px; font-size:10px; padding:4px; }}
QStatusBar {{ background:{C['bg2']}; border-top:1px solid {C['border']};
    color:{C['accent3']}; font-size:10px; }}
QVideoWidget {{ background:{C['bg0']}; border-radius:8px; }}
"""

# ══════════════════════════════════════════════════════════════
#  SHARED WIDGETS
# ══════════════════════════════════════════════════════════════

def sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{C['border']};")
    return f

def hdr(text):
    l = QLabel(text)
    l.setObjectName("hdr")
    return l


class Knob(QWidget):
    """Slider + SpinBox in one row for one float parameter."""
    changed = pyqtSignal(float)

    def __init__(self, label, lo, hi, default, decimals=2, step=0.01):
        super().__init__()
        self._decimals = decimals
        self._scale    = 10 ** decimals

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setObjectName("dim")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(lo      * self._scale))
        self.slider.setMaximum(int(hi      * self._scale))
        self.slider.setValue  (int(default * self._scale))

        self.spin = QDoubleSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step)
        self.spin.setValue(default)
        self.spin.setFixedWidth(72)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect  (self._from_spin)

        row.addWidget(lbl)
        row.addWidget(self.slider)
        row.addWidget(self.spin)

    def _from_slider(self, v):
        val = v / self._scale
        self.spin.blockSignals(True)
        self.spin.setValue(val)
        self.spin.blockSignals(False)
        self.changed.emit(val)

    def _from_spin(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(int(val * self._scale))
        self.slider.blockSignals(False)
        self.changed.emit(val)

    def value(self):
        return self.spin.value()


# ══════════════════════════════════════════════════════════════
#  SCENE SOURCE BUILDERS
#  Pure functions — build source as list-of-lines, join at end.
#  No triple-quoted f-strings. No LaTeX / MathTex anywhere.
# ══════════════════════════════════════════════════════════════

def _join(lines):
    return "\n".join(lines) + "\n"


def build_trig_source(show_sin, show_cos, show_tan,
                      A, w, ph, D, xr, show_grid, anim):
    L = [
        "from manim import *",
        "import numpy as np",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        axes = Axes(",
        f"            x_range=[{-xr:.2f}, {xr:.2f}, {xr/4:.2f}],",
        "            y_range=[-4.5, 4.5, 1.0],",
        "            x_length=11, y_length=6,",
        "            axis_config=dict(color=GREY, include_tip=True),",
        "        )",
    ]

    if show_grid:
        L += [
            "        grid = NumberPlane(",
            f"            x_range=[{-xr:.2f}, {xr:.2f}],",
            "            y_range=[-4.5, 4.5],",
            "            background_line_style=dict(",
            "                stroke_color=BLUE_E, stroke_opacity=0.25",
            "            ),",
            "        )",
            "        self.play(FadeIn(grid), run_time=0.6)",
        ]

    L.append("        self.play(Create(axes), run_time=0.8)")

    graphs = []
    if show_sin:
        graphs.append((f"{A:.4f}*np.sin({w:.4f}*x + {ph:.4f}) + {D:.4f}", "BLUE",  "sin"))
    if show_cos:
        graphs.append((f"{A:.4f}*np.cos({w:.4f}*x + {ph:.4f}) + {D:.4f}", "RED",   "cos"))
    if show_tan:
        graphs.append((f"{A:.4f}*np.tan({w:.4f}*x + {ph:.4f}) + {D:.4f}", "GREEN", "tan"))

    for i, (expr, color, name) in enumerate(graphs):
        g   = f"g{i}"
        lv  = f"lbl{i}"
        lx  = f"{xr * 0.5:.2f}"
        L += [
            f"        {g} = axes.plot(",
            f"            lambda x: {expr},",
            f"            x_range=[{-xr:.2f}, {xr:.2f}, 0.05],",
            f"            color={color}, stroke_width=2.5, use_smoothing=True,",
            "        )",
            f'        {lv} = Text("{name}", font_size=20, color={color})',
            f"        {lv}.next_to(axes.input_to_graph_point({lx}, {g}), UP, buff=0.15)",
        ]
        if anim == "Create":
            L.append(f"        self.play(Create({g}), FadeIn({lv}), run_time=1.5)")
        elif anim == "FadeIn":
            L.append(f"        self.play(FadeIn({g}), FadeIn({lv}), run_time=1.2)")
        else:
            L.append(f"        self.play(Create({g}), Write({lv}), run_time=2.0)")

    L.append("        self.wait(1.5)")
    return _join(L)


def build_complex_source(mode, re_c, im_c, scale, n_pts, show_arrows):
    fn_map = {
        "f(z) = z^2":      "z**2",
        "f(z) = z^3 - 1":  "z**3 - 1",
        "f(z) = 1/z":      "(1/z if abs(z) > 1e-9 else complex(0,0))",
        "f(z) = e^z":      "cmath.exp(z)",
        "Mobius Transform": (
            f"(z + complex({re_c:.4f},{im_c:.4f})) / "
            f"(z - complex({re_c:.4f},{im_c:.4f}) + 1e-9j)"
        ),
    }
    fn = fn_map.get(mode, "z**2")
    r_sample = min(float(scale) * 0.6, 1.8)
    n = max(4, int(n_pts))

    L = [
        "from manim import *",
        "import numpy as np",
        "import cmath",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        plane = ComplexPlane(",
        f"            x_range=[{-scale:.2f}, {scale:.2f}],",
        f"            y_range=[{-scale:.2f}, {scale:.2f}],",
        "            background_line_style=dict(",
        "                stroke_color=TEAL_E, stroke_opacity=0.25",
        "            ),",
        "        ).add_coordinates()",
        f'        title = Text("{mode}", font_size=22, color=TEAL).to_edge(UP)',
        "        self.play(Create(plane), FadeIn(title), run_time=1.2)",
        f"        angles  = np.linspace(0, 2*np.pi, {n}, endpoint=False)",
        f"        r       = {r_sample:.4f}",
        f"        palette = color_gradient([BLUE, PURPLE, RED, ORANGE, YELLOW, GREEN], {n})",
        "        in_dots  = VGroup()",
        "        out_dots = VGroup()",
        "        arrs     = VGroup()",
        "        for i, ang in enumerate(angles):",
        "            z   = complex(r*np.cos(ang), r*np.sin(ang))",
        "            try:",
        f"                fz  = {fn}",
        "            except Exception:",
        "                fz  = complex(0, 0)",
        "            col = palette[i]",
        "            ip  = plane.n2p(z)",
        "            op  = plane.n2p(fz)",
        "            in_dots.add( Dot(ip, color=col, radius=0.08))",
        "            out_dots.add(Dot(op, color=col, radius=0.08, fill_opacity=0.5))",
        f"            if {str(show_arrows).title()} and np.linalg.norm(op - ip) > 0.05:",
        "                arrs.add(Arrow(",
        "                    ip, op, color=col, buff=0.06,",
        "                    stroke_width=1.5,",
        "                    max_tip_length_to_length_ratio=0.12,",
        "                ))",
        "        self.play(FadeIn(in_dots), run_time=0.8)",
        f"        if {str(show_arrows).title()}:",
        "            self.play(Create(arrs), run_time=1.8)",
        "        self.play(FadeIn(out_dots), run_time=0.8)",
        "        self.wait(1.5)",
    ]
    return _join(L)


def build_linear_source(a, b, c, d, vx, vy, show_det, show_basis, show_grid):
    det     = a*d - b*c
    tvx     = a*vx + b*vy
    tvy     = c*vx + d*vy
    det_col = "GREEN" if abs(det) > 1e-9 else "RED"

    L = [
        "from manim import *",
        "import numpy as np",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        f"        M = np.array([[{a:.6f}, {b:.6f}], [{c:.6f}, {d:.6f}]])",
        "",
        "        axes = Axes(",
        "            x_range=[-5, 5, 1], y_range=[-4, 4, 1],",
        "            x_length=10, y_length=8,",
        "            axis_config=dict(color=GREY, include_tip=True, include_numbers=True),",
        "        )",
    ]

    if show_grid:
        L += [
            "        grid = NumberPlane(",
            "            x_range=[-5, 5], y_range=[-4, 4],",
            "            background_line_style=dict(stroke_color=BLUE_E, stroke_opacity=0.3),",
            "        )",
            "        self.play(FadeIn(grid), Create(axes), run_time=0.8)",
        ]
    else:
        L.append("        self.play(Create(axes), run_time=0.8)")

    if show_basis:
        L += [
            "        e1 = Arrow(axes.c2p(0,0), axes.c2p(1,0), color=GREEN,",
            "                   buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.2)",
            "        e2 = Arrow(axes.c2p(0,0), axes.c2p(0,1), color=RED,",
            "                   buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.2)",
            "        e1_lbl = Text('e1', font_size=16, color=GREEN).next_to(axes.c2p(1,0), UR, buff=0.1)",
            "        e2_lbl = Text('e2', font_size=16, color=RED  ).next_to(axes.c2p(0,1), UR, buff=0.1)",
            "        self.play(GrowArrow(e1), GrowArrow(e2), FadeIn(e1_lbl, e2_lbl), run_time=0.8)",
        ]

    L += [
        f"        vec_start = axes.c2p(0, 0)",
        f"        vec_end   = axes.c2p({vx:.6f}, {vy:.6f})",
        "        vec = Arrow(vec_start, vec_end, color=YELLOW, buff=0,",
        "                    stroke_width=5, max_tip_length_to_length_ratio=0.2)",
        f"        vec_lbl = Text('v=({vx:.2f},{vy:.2f})', font_size=16, color=YELLOW)",
        "        vec_lbl.next_to(vec.get_end(), UR, buff=0.1)",
        "        self.play(GrowArrow(vec), FadeIn(vec_lbl), run_time=0.8)",
        "",
        f'        mat_lbl = Text("M = [[{a:.2f}, {b:.2f}], [{c:.2f}, {d:.2f}]]",',
        "                        font_size=18, color=WHITE)",
        "        mat_lbl.to_corner(UL).add_background_rectangle()",
        f'        det_lbl = Text("det = {det:.3f}", font_size=18, color={det_col})',
        "        det_lbl.next_to(mat_lbl, DOWN, buff=0.15).add_background_rectangle()",
        f'        res_lbl = Text("Mv = ({tvx:.2f}, {tvy:.2f})", font_size=18, color=YELLOW)',
        "        res_lbl.to_corner(UR).add_background_rectangle()",
        "        self.play(FadeIn(mat_lbl), run_time=0.6)",
    ]

    if show_det:
        L.append("        self.play(FadeIn(det_lbl), run_time=0.4)")

    L += [
        "",
        "        def apply_M(p):",
        "            xy = axes.p2c(p)",
        "            txy = M @ np.array([xy[0], xy[1]])",
        "            return axes.c2p(txy[0], txy[1])",
        "",
        f"        tvec_end = axes.c2p({tvx:.6f}, {tvy:.6f})",
        "        tvec = Arrow(vec_start, tvec_end, color=ORANGE, buff=0,",
        "                     stroke_width=5, max_tip_length_to_length_ratio=0.2)",
        f"        tvec_lbl = Text('Mv=({tvx:.2f},{tvy:.2f})', font_size=16, color=ORANGE)",
        "        tvec_lbl.next_to(tvec.get_end(), UR, buff=0.1)",
    ]

    if show_basis:
        L += [
            f"        te1 = M @ np.array([1.0, 0.0])",
            f"        te2 = M @ np.array([0.0, 1.0])",
            "        e1_t = Arrow(axes.c2p(0,0), axes.c2p(te1[0], te1[1]), color=GREEN_B,",
            "                     buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.2)",
            "        e2_t = Arrow(axes.c2p(0,0), axes.c2p(te2[0], te2[1]), color=RED_B,",
            "                     buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.2)",
            "        self.play(",
            "            Transform(vec, tvec),",
            "            Transform(e1, e1_t), Transform(e2, e2_t),",
            "            FadeOut(vec_lbl), FadeOut(e1_lbl), FadeOut(e2_lbl),",
            "            run_time=1.8,",
            "        )",
        ]
    else:
        L += [
            "        self.play(",
            "            Transform(vec, tvec),",
            "            FadeOut(vec_lbl),",
            "            run_time=1.8,",
            "        )",
        ]

    L += [
        "        self.play(FadeIn(tvec_lbl), FadeIn(res_lbl), run_time=0.5)",
        "        self.wait(1.5)",
    ]
    return _join(L)


def build_code_source(code_str, language, anim, background, add_line_numbers, font_size, run_time):
    safe = repr(code_str)   # escapes newlines, quotes, backslashes safely
    L = [
        "from manim import *",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        code = Code(",
        f"            code_string={safe},",
        f"            language={repr(language)},",
        f"            background={repr(background)},",
        f"            add_line_numbers={add_line_numbers},",
        f"            paragraph_config={{'font_size': {font_size:.0f}}},",
        "        )",
        "        code.scale_to_fit_width(12).center()",
    ]

    if anim == "Write":
        L.append(f"        self.play(Write(code), run_time={run_time:.1f})")
    elif anim == "FadeIn":
        L.append(f"        self.play(FadeIn(code), run_time={run_time:.1f})")
    elif anim == "FadeIn Up":
        L.append(f"        self.play(FadeIn(code, shift=UP * 0.4), run_time={run_time:.1f})")
    elif anim == "Create":
        L.append(f"        self.play(Create(code), run_time={run_time:.1f})")
    elif anim == "Typewriter":
        L += [
            "        self.play(FadeIn(code.background_mobject), run_time=0.4)",
            "        self.play(",
            "            LaggedStart(",
            "                *[Write(line) for line in code.code_lines],",
            "                lag_ratio=0.5,",
            "            ),",
            f"            run_time={run_time:.1f},",
            "        )",
        ]

    L.append("        self.wait(1.5)")
    return _join(L)


# ══════════════════════════════════════════════════════════════
#  RENDER THREAD
# ══════════════════════════════════════════════════════════════

QUALITY = {
    "Low  480p" : ["-ql"],
    "Med  720p" : ["-qm"],
    "High 1080p": ["-qh"],
    "GIF"       : ["-ql", "--format", "gif"],
}

# All renders saved here permanently
RENDERS_DIR = os.path.join(os.path.expanduser("~"), "ManimStudio", "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)


class RenderThread(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self, source: str, flags: list, output_dir: str):
        super().__init__()
        self.source     = source
        self.flags      = flags
        self.output_dir = output_dir
        self._proc      = None
        self._stopped   = False

    def run(self):
        try:
            ast.parse(self.source)
        except SyntaxError as e:
            self.log.emit(f"[SYNTAX ERROR] line {e.lineno}: {e.msg}")
            self.done.emit("")
            return

        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(self.source)
            tmp = f.name

        full_output = []
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-manim"] + self.flags + ["--media_dir", self.output_dir, tmp, "ManimScene"]
            else:
                cmd = ["manim"] + self.flags + ["--media_dir", self.output_dir, tmp, "ManimScene"]
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
            )
            for line in self._proc.stdout:
                stripped = line.rstrip()
                self.log.emit(stripped)
                full_output.append(stripped)
            self._proc.wait()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

        # Manim may split the path across two log lines — join and re-scan
        video = ""
        combined = " ".join(full_output)
        if "File ready at" in combined:
            after = combined.split("File ready at", 1)[1].strip()
            token = after.split()[0].strip("'\"" ) if after.split() else ""
            if token and os.path.exists(token):
                video = token

        # Fallback: newest mp4/gif in output_dir
        if not video:
            candidates = []
            for root_, _, files in os.walk(self.output_dir):
                if "partial_movie_files" in root_:
                    continue
                for fname in files:
                    if fname.endswith((".mp4", ".gif")):
                        fp = os.path.join(root_, fname)
                        candidates.append((os.path.getmtime(fp), fp))
            if candidates:
                video = max(candidates)[1]
                self.log.emit(f"[INFO] resolved via newest file: {video}")

        if not self._stopped:
            self.done.emit(video)

    def stop(self):
        self._stopped = True
        if self._proc:
            self._proc.terminate()
        self.terminate()



# ══════════════════════════════════════════════════════════════
#  PARAMETER PANELS
# ══════════════════════════════════════════════════════════════

class TrigPanel(QGroupBox):
    def __init__(self):
        super().__init__("Trigonometric Functions")
        v = QVBoxLayout(self)
        v.setSpacing(6)

        v.addWidget(hdr("FUNCTIONS"))
        fn_row = QHBoxLayout()
        self.cb_sin = QCheckBox("sin(x)"); self.cb_sin.setChecked(True)
        self.cb_cos = QCheckBox("cos(x)"); self.cb_cos.setChecked(True)
        self.cb_tan = QCheckBox("tan(x)")
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
        a_row.addWidget(QLabel("Anim style"))
        self.anim = QComboBox()
        self.anim.addItems(["Create", "FadeIn", "Write"])
        a_row.addWidget(self.anim)
        a_row.addStretch()
        v.addLayout(a_row)
        v.addStretch()

    def source(self):
        return build_trig_source(
            show_sin = self.cb_sin.isChecked(),
            show_cos = self.cb_cos.isChecked(),
            show_tan = self.cb_tan.isChecked(),
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
        self.spins   = {}
        defaults     = {"a": 2.0, "b": 0.5, "c": 0.5, "d": 2.0}
        positions    = [("a",0,0), ("b",0,2), ("c",1,0), ("d",1,2)]
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
        vrow.addWidget(QLabel("vx")); vrow.addWidget(self.vx)
        vrow.addWidget(QLabel("vy")); vrow.addWidget(self.vy)
        vrow.addStretch()
        v.addLayout(vrow)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))
        d_row = QHBoxLayout()
        self.cb_det   = QCheckBox("det");   self.cb_det.setChecked(True)
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
            "python", "c", "cpp", "java", "javascript",
            "typescript", "rust", "go", "bash", "sql",
        ])
        v.addWidget(self.lang)

        v.addWidget(sep())
        v.addWidget(hdr("ANIMATION STYLE"))
        self.anim = QComboBox()
        self.anim.addItems(["Write", "FadeIn", "FadeIn Up", "Create", "Typewriter"])
        v.addWidget(self.anim)

        v.addWidget(sep())
        v.addWidget(hdr("DISPLAY"))

        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("Background"))
        self.bg = QComboBox()
        self.bg.addItems(["window", "rectangle"])
        bg_row.addWidget(self.bg)
        bg_row.addStretch()
        v.addLayout(bg_row)

        ln_row = QHBoxLayout()
        self.cb_lineno = QCheckBox("Line numbers")
        self.cb_lineno.setChecked(True)
        ln_row.addWidget(self.cb_lineno)
        ln_row.addStretch()
        v.addLayout(ln_row)

        self.font_size = Knob("Font size",   8.0, 32.0, 16.0, decimals=0, step=1.0)
        self.run_time  = Knob("Duration (s)", 0.5, 15.0,  4.0, decimals=1, step=0.5)
        v.addWidget(self.font_size)
        v.addWidget(self.run_time)
        v.addStretch()

    def source(self):
        return build_code_source(
            code_str        = self.editor.toPlainText(),
            language        = self.lang.currentText(),
            anim            = self.anim.currentText(),
            background      = self.bg.currentText(),
            add_line_numbers= self.cb_lineno.isChecked(),
            font_size       = self.font_size.value(),
            run_time        = self.run_time.value(),
        )


# ══════════════════════════════════════════════════════════════
#  LEFT PANEL  (30%)
# ══════════════════════════════════════════════════════════════

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
        self.selector.addItems(["Trigonometry", "Complex Plane", "Linear Algebra", "Code Animation"])
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

        self.trig    = TrigPanel()
        self.complex = ComplexPanel()
        self.linear  = LinearPanel()
        self.code    = CodePanel()
        for p in [self.trig, self.complex, self.linear, self.code]:
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
        self.trig   .setVisible(idx == 0)
        self.complex.setVisible(idx == 1)
        self.linear .setVisible(idx == 2)
        self.code   .setVisible(idx == 3)

    def _active(self):
        return [self.trig, self.complex, self.linear, self.code][self.selector.currentIndex()]

    def current_label(self):
        return ["trigonometry", "complex_plane", "linear_algebra", "code_animation"][self.selector.currentIndex()]

    def _render(self):
        self.render_requested.emit(self._active().source())


# ══════════════════════════════════════════════════════════════
#  RIGHT PANEL  (70%)
# ══════════════════════════════════════════════════════════════

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
        self.video.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
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
        vis = not self.log.isVisible()
        self.log.setVisible(vis)
        self.btn_log.setText("hide" if vis else "show")

    def load(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def append_log(self, msg):
        self.log.append(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_status(self, msg, color=None):
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(
            f"color:{color or C['dim']};font-size:10px;"
        )


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manim Studio")
        self.resize(1400, 860)
        self.setStyleSheet(STYLE)
        self._thread         = None
        self._render_stopped = False
        self._render_label   = "render"

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background:{C['border']}; }}"
        )

        self.left  = LeftPanel()
        self.right = RightPanel()
        splitter.addWidget(self.left)
        splitter.addWidget(self.right)
        splitter.setSizes([420, 980])      # 30 / 70  of 1400
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self._sb = QStatusBar()
        self._sb.showMessage("Ready — adjust parameters and hit Render")
        self.setStatusBar(self._sb)

        self.left.render_requested.connect(self._render)
        self.left.btn_stop.clicked.connect(self._stop)

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

        ext        = os.path.splitext(path)[1].lower()
        filt       = "GIF (*.gif)" if ext == ".gif" else "MP4 Video (*.mp4)"
        default    = os.path.join(self.left.output_dir, f"{self._render_label}{ext}")
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Render As", default, filt
        )

        if save_path:
            try:
                shutil.move(path, save_path)
                path = save_path
            except OSError as e:
                self.right.append_log(f"[WARN] could not move file: {e}")

        self.right.load(path)
        self.right.set_status("● Playing", C['green'])
        self._sb.showMessage(f"Saved  {path}")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
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
