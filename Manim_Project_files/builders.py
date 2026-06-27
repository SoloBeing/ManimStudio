import ast as _ast
import math
from renderer import _BLOCKED_CALLS, _BLOCKED_ATTRS

def _join(lines):
    return "\n".join(lines) + "\n"


def _validate_expr(expr, label, default=""):
    """Validate a user-supplied Python expression destined for generated source.

    Parses it (mode="eval") and walks the AST against the shared security
    blocklists. Returns the cleaned expression; raises ValueError with a
    friendly message on bad syntax or a blocked call/attribute. An empty
    expression falls back to ``default`` if one is given.
    """
    expr = (expr or "").strip()
    if not expr:
        if default:
            return default
        raise ValueError(f"{label} cannot be empty.")
    try:
        tree = _ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(
            f"{label} has invalid syntax: {e.msg} (use Python syntax)"
        ) from None
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Name) and node.func.id in _BLOCKED_CALLS:
                raise ValueError(f"Call not allowed in {label}: {node.func.id}()")
        elif isinstance(node, _ast.Attribute):
            if node.attr in _BLOCKED_ATTRS:
                raise ValueError(f"Attribute not allowed in {label}: .{node.attr}")
    return expr


# ---------------------------------------------------------------------------
# Position → (placement_call, secondary_call, stack_direction)
# placement_call is the full method call appended to the mobject, e.g.
# "to_corner(UL)" or "to_edge(UP)" or "move_to(ORIGIN)"
# ---------------------------------------------------------------------------

TEXT_POSITIONS = {
    "top_left":      ("to_corner(UL)", "to_corner(UR)", "DOWN"),
    "top_center":    ("to_edge(UP)",   "to_edge(DOWN)", "DOWN"),
    "top_right":     ("to_corner(UR)", "to_corner(UL)", "DOWN"),
    "center_left":   ("to_edge(LEFT)", "to_edge(RIGHT)", "DOWN"),
    "center":        ("move_to(ORIGIN)", "to_edge(RIGHT)", "DOWN"),
    "center_right":  ("to_edge(RIGHT)", "to_edge(LEFT)", "DOWN"),
    "bottom_left":   ("to_corner(DL)", "to_corner(DR)", "UP"),
    "bottom_center": ("to_edge(DOWN)", "to_edge(UP)",   "UP"),
    "bottom_right":  ("to_corner(DR)", "to_corner(DL)", "UP"),
    # sentinel — x/y coords are used as absolute move_to target
    "free":          ("__FREE__", "__FREE__", "DOWN"),
}

def _place_label(varname, pos_call, x_offset, y_offset, suffix=None):
    """Emit a placement line for a preset label, handling the __FREE__ sentinel."""
    if pos_call == "__FREE__":
        x, y = float(x_offset or 0), float(y_offset or 0)
        line = f"        {varname}.move_to(RIGHT * {x:.2f} + UP * {y:.2f})"
    else:
        line = f"        {varname}.{pos_call}"
    if suffix:
        line += f".{suffix}"
    return line


TEXT_COLORS = {
    "white":       "WHITE",
    "blue":        "BLUE",
    "teal":        "TEAL",
    "green":       "GREEN",
    "yellow":      "YELLOW",
    "orange":      "ORANGE",
    "red":         "RED",
    "purple":      "PURPLE",
    "pink":        "PINK",
    "gold":        "GOLD",
    "maroon":      "MAROON",
    "light_blue":  "BLUE_B",
    "light_green": "GREEN_B",
    "grey":        "GREY",
    "black":       "BLACK",
    "teal_b":      "TEAL_B",
}

GRADIENTS = {
    "none":        None,
    "red_blue":    "RED, BLUE",
    "blue_green":  "BLUE, GREEN",
    "gold_white":  "GOLD, WHITE",
    "teal_yellow": "TEAL, YELLOW",
    "rainbow":     "RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE",
    "orange_red":  "ORANGE, RED",
}


def _text_position(value):
    return TEXT_POSITIONS.get(str(value or "").strip().lower(), TEXT_POSITIONS["top_left"])


def _text_color(value):
    v = str(value or "").strip()
    if v.startswith("#"):
        return repr(v.upper())
    return TEXT_COLORS.get(v.lower(), "WHITE")


def _text_kwargs(font, fs, color, bold=False, italic=False,
                 stroke_width=0, stroke_color=None):
    kw = [f"font_size={fs}", f"color={color}", f"font={repr(font)}"]
    if bold:
        kw.append("weight=BOLD")
    if italic:
        kw.append("slant=ITALIC")
    sw = float(stroke_width or 0)
    if sw > 0:
        kw.append(f"stroke_width={sw:.1f}")
        kw.append(f"stroke_color={stroke_color or color}")
    return ", ".join(kw)


def _offset_line(varname, x, y):
    x, y = float(x or 0), float(y or 0)
    if abs(x) > 0.005 or abs(y) > 0.005:
        return f"        {varname}.shift(RIGHT * {x:.2f} + UP * {y:.2f})"
    return None


def _text_line(varname, content, font, fs, color, bold, italic, stroke_width, stroke_col, gradient=None):
    """Return a Text or MarkupText assignment line; uses MarkupText when gradient is active."""
    g = GRADIENTS.get(str(gradient or "none").strip().lower())
    sw = float(stroke_width or 0)
    if g:
        kw = [f"font_size={fs}", f"font={repr(font)}", f"gradient=({g},)"]
        if bold:   kw.append("weight=BOLD")
        if italic: kw.append("slant=ITALIC")
        if sw > 0:
            kw.append(f"stroke_width={sw:.1f}")
            kw.append(f"stroke_color={stroke_col or color}")
        return f"        {varname} = MarkupText({repr(content)}, {', '.join(kw)})"
    tkw = _text_kwargs(font, fs, color, bold, italic, stroke_width, stroke_col)
    return f"        {varname} = Text({repr(content)}, {tkw})"


def _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                      stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset):
    if not text_content:
        return
    L.append(_text_line("custom_lbl", text_content, font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
    if pos_call == "__FREE__":
        x, y = float(x_offset or 0), float(y_offset or 0)
        L.append(f"        custom_lbl.move_to(RIGHT * {x:.2f} + UP * {y:.2f})")
    else:
        L.append(f"        custom_lbl.{pos_call}")
        o = _offset_line("custom_lbl", x_offset, y_offset)
        if o:
            L.append(o)


# ===========================================================================
# Trig
# ===========================================================================

def build_trig_source(
    show_sin, show_cos, show_tan, A, w, ph, D, xr, show_grid, anim,
    sin_color="blue", cos_color="red", tan_color="green",
    yr=4.5, cam_zoom=1.0,
    sin_phase=0.0, cos_phase=0.0, tan_phase=0.0, curve_stroke=2.5,
    sin_label="", cos_label="", tan_label="",
    text_position="top_right", text_color="white", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    pos_call, _, stack_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font = text_font or "Arial"
    fs   = max(8, int(text_font_size))
    yr_f = max(0.5, float(yr or 4.5))

    L = ["from manim import *", "import numpy as np", ""]
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0    / zoom_f:.3f}",
            "",
        ]
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        axes = Axes(",
        f"            x_range=[{-xr:.2f}, {xr:.2f}, {xr/4:.2f}],",
        f"            y_range=[{-yr_f:.2f}, {yr_f:.2f}, 1.0],",
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

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)
        L.append("        self.play(FadeIn(custom_lbl), run_time=0.4)")

    c_sin = _text_color(sin_color or "blue")
    c_cos = _text_color(cos_color or "red")
    c_tan = _text_color(tan_color or "green")

    # Each curve can carry its own phase offset on top of the shared phase `ph`,
    # so relationships like cos = sin shifted by pi/2 can be shown directly.
    ph_sin = float(ph) + float(sin_phase or 0.0)
    ph_cos = float(ph) + float(cos_phase or 0.0)
    ph_tan = float(ph) + float(tan_phase or 0.0)
    cs = max(0.5, float(curve_stroke or 2.5))

    graphs = []
    if show_sin:
        graphs.append((f"{A:.4f}*np.sin({w:.4f}*x + {ph_sin:.4f}) + {D:.4f}", c_sin, sin_label or "sin"))
    if show_cos:
        graphs.append((f"{A:.4f}*np.cos({w:.4f}*x + {ph_cos:.4f}) + {D:.4f}", c_cos, cos_label or "cos"))
    if show_tan:
        graphs.append((f"{A:.4f}*np.tan({w:.4f}*x + {ph_tan:.4f}) + {D:.4f}", c_tan, tan_label or "tan"))

    tkw = _text_kwargs(font, fs, txt_col, bold, italic, stroke_width, stroke_col)
    for i, (expr, color, name) in enumerate(graphs):
        g  = f"g{i}"
        lv = f"lbl{i}"
        L += [
            f"        {g} = axes.plot(",
            f"            lambda x: {expr},",
            f"            x_range=[{-xr:.2f}, {xr:.2f}, 0.05],",
            f"            color={color}, stroke_width={cs:.2f}, use_smoothing=True,",
            "        )",
        ]
        if show_preset_labels:
            L.append(_text_line(lv, name, font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
            if i == 0:
                if text_content:
                    L.append(f"        {lv}.next_to(custom_lbl, {stack_dir}, buff=0.12)")
                else:
                    L.append(_place_label(lv, pos_call, x_offset, y_offset))
            else:
                L.append(f"        {lv}.next_to(lbl{i - 1}, {stack_dir}, buff=0.12)")
        anim_s = str(anim or "Create")
        if anim_s == "FadeIn":
            graph_anim = f"FadeIn({g})"
            rt = 1.2
        elif anim_s == "Write":
            graph_anim = f"Create({g})"
            rt = 2.0
        elif anim_s == "GrowFromEdge":
            graph_anim = f"GrowFromEdge({g}, LEFT)"
            rt = 1.8
        elif anim_s == "DrawBorderThenFill":
            graph_anim = f"Create({g})"
            rt = 1.8
        else:  # Create (default)
            graph_anim = f"Create({g})"
            rt = 1.5
        if show_preset_labels:
            lbl_anim = "Write" if anim_s == "Write" else "FadeIn"
            L.append(f"        self.play({graph_anim}, {lbl_anim}({lv}), run_time={rt:.1f})")
        else:
            L.append(f"        self.play({graph_anim}, run_time={rt:.1f})")

    L.append("        self.wait(1.5)")
    return _join(L)


# ===========================================================================
# Complex Plane
# ===========================================================================

def build_complex_source(
    mode, re_c, im_c, scale, n_pts, show_arrows,
    text_position="top_left", text_color="teal", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
    custom_fn="z**2", cam_zoom=1.0, anim_style="vectors",
):
    pos_call, _, stack_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font   = text_font or "Arial"
    fs     = max(8, int(text_font_size))
    fs_sub = max(8, fs - 4)

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
    if mode == "Custom":
        fn = _validate_expr(custom_fn, "f(z) expression", default="z**2")
    else:
        fn = fn_map.get(mode, "z**2")
    r_sample = min(float(scale) * 0.6, 1.8)
    n        = max(4, int(n_pts))

    tkw     = _text_kwargs(font, fs,     txt_col, bold, italic, stroke_width, stroke_col)
    tkw_sub = _text_kwargs(font, fs_sub, txt_col, bold, italic, stroke_width, stroke_col)

    L = [
        "from manim import *",
        "import numpy as np",
        "import cmath",
        "",
    ]
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0    / zoom_f:.3f}",
            "",
        ]
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        plane = ComplexPlane(",
        f"            x_range=[{-scale:.2f}, {scale:.2f}],",
        f"            y_range=[{-scale:.2f}, {scale:.2f}],",
        "            background_line_style=dict(",
        "                stroke_color=TEAL_E, stroke_opacity=0.25",
        "            ),",
        "        ).add_coordinates()",
    ]

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)
        if show_preset_labels:
            L.append(_text_line("title", (preset_title or mode), font, fs_sub, txt_col, bold, italic, stroke_width, stroke_col, gradient))
            L.append(f"        title.next_to(custom_lbl, {stack_dir}, buff=0.12)")
            L.append("        self.play(Create(plane), FadeIn(custom_lbl), FadeIn(title), run_time=1.2)")
        else:
            L.append("        self.play(Create(plane), FadeIn(custom_lbl), run_time=1.2)")
    else:
        if show_preset_labels:
            L.append(_text_line("title", (preset_title or mode), font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
            L.append(_place_label("title", pos_call, x_offset, y_offset))
            L.append("        self.play(Create(plane), FadeIn(title), run_time=1.2)")
        else:
            L.append("        self.play(Create(plane), run_time=1.2)")

    L += [
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
    ]
    if str(anim_style or "vectors").strip().lower() == "morph":
        # Animate copies of the input dots travelling to their image points,
        # leaving the input ring in place and the mapped ring revealed.
        L.append("        self.play(TransformFromCopy(in_dots, out_dots), run_time=2.0)")
    else:
        L.append("        self.play(FadeIn(out_dots), run_time=0.8)")
    L.append("        self.wait(1.5)")
    return _join(L)


# ===========================================================================
# Linear Algebra
# ===========================================================================

def build_linear_source(
    a, b, c, d, vx, vy, show_det, show_basis, show_grid,
    cam_zoom=1.0, transform_grid=False, keep_original_grid=False,
    e1_label="", e2_label="",
    text_position="top_left", text_color="white", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    det     = a*d - b*c
    tvx     = a*vx + b*vy
    tvy     = c*vx + d*vy
    det_col = "GREEN" if abs(det) > 1e-9 else "RED"

    pos_call, sec_call, det_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font  = text_font or "Arial"
    fs    = max(8, int(text_font_size))
    fs_sm = max(8, fs - 4)

    tkw     = _text_kwargs(font, fs,    txt_col, bold, italic, stroke_width, stroke_col)
    tkw_sm  = _text_kwargs(font, fs_sm, txt_col, bold, italic, stroke_width, stroke_col)
    tkw_det = _text_kwargs(font, fs,    det_col, bold, italic, stroke_width, stroke_col)

    L = ["from manim import *", "import numpy as np", ""]
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0    / zoom_f:.3f}",
            "",
        ]
    L += [
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
        ]
        if show_preset_labels:
            L.append(_text_line("e1_lbl", e1_label or "e1", font, fs_sm, txt_col, bold, italic, stroke_width, stroke_col, gradient))
            L.append("        e1_lbl.next_to(axes.c2p(1,0), UR, buff=0.1)")
            L.append(_text_line("e2_lbl", e2_label or "e2", font, fs_sm, txt_col, bold, italic, stroke_width, stroke_col, gradient))
            L.append("        e2_lbl.next_to(axes.c2p(0,1), UR, buff=0.1)")
            L.append("        self.play(GrowArrow(e1), GrowArrow(e2), FadeIn(e1_lbl, e2_lbl), run_time=0.8)")
        else:
            L.append("        self.play(GrowArrow(e1), GrowArrow(e2), run_time=0.8)")

    L += [
        f"        vec_start = axes.c2p(0, 0)",
        f"        vec_end   = axes.c2p({vx:.6f}, {vy:.6f})",
        "        vec = Arrow(vec_start, vec_end, color=YELLOW, buff=0,",
        "                    stroke_width=5, max_tip_length_to_length_ratio=0.2)",
    ]
    if show_preset_labels:
        L.append(_text_line("vec_lbl", f"v=({vx:.2f},{vy:.2f})", font, fs_sm, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        L.append("        vec_lbl.next_to(vec.get_end(), UR, buff=0.1)")
        L.append("        self.play(GrowArrow(vec), FadeIn(vec_lbl), run_time=0.8)")
    else:
        L.append("        self.play(GrowArrow(vec), run_time=0.8)")

    L.append("")

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)
        L.append("        self.play(FadeIn(custom_lbl), run_time=0.4)")

    if show_preset_labels:
        L.append(_text_line("mat_lbl", f"M = [[{a:.2f}, {b:.2f}], [{c:.2f}, {d:.2f}]]", font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        if text_content:
            L.append(f"        mat_lbl.next_to(custom_lbl, {det_dir}, buff=0.12).add_background_rectangle()")
        else:
            L.append(_place_label("mat_lbl", pos_call, x_offset, y_offset, "add_background_rectangle()"))
        L += [
            f'        det_lbl = Text("det = {det:.3f}", {tkw_det})',
            f"        det_lbl.next_to(mat_lbl, {det_dir}, buff=0.15).add_background_rectangle()",
        ]
        L.append(_text_line("res_lbl", f"Mv = ({tvx:.2f}, {tvy:.2f})", font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        L += [
            _place_label("res_lbl", sec_call, x_offset, y_offset, "add_background_rectangle()"),
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
    ]
    if show_preset_labels:
        L.append(_text_line("tvec_lbl", f"Mv=({tvx:.2f},{tvy:.2f})", font, fs_sm, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        L.append("        tvec_lbl.next_to(tvec.get_end(), UR, buff=0.1)")

    if show_basis:
        L += [
            f"        te1 = M @ np.array([1.0, 0.0])",
            f"        te2 = M @ np.array([0.0, 1.0])",
            "        e1_t = Arrow(axes.c2p(0,0), axes.c2p(te1[0], te1[1]), color=GREEN_B,",
            "                     buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.2)",
            "        e2_t = Arrow(axes.c2p(0,0), axes.c2p(te2[0], te2[1]), color=RED_B,",
            "                     buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.2)",
        ]
    if show_grid and transform_grid:
        if keep_original_grid:
            # Leave a faded static copy of the pre-transform grid behind the
            # warped one, so the before/after relationship stays visible.
            L += [
                "        ghost_grid = grid.copy().set_opacity(0.18)",
                "        self.add(ghost_grid)",
                "        self.bring_to_back(ghost_grid)",
            ]
        L.append("        warped_grid = grid.copy().apply_function(apply_M)")

    # Build the transform animation as a list so optional pieces (basis vectors,
    # the warped grid, label fade-outs) can be composed without branching twice.
    transforms = ["Transform(vec, tvec)"]
    if show_basis:
        transforms += ["Transform(e1, e1_t)", "Transform(e2, e2_t)"]
    if show_grid and transform_grid:
        transforms.append("Transform(grid, warped_grid)")
    if show_preset_labels:
        transforms.append("FadeOut(vec_lbl)")
        if show_basis:
            transforms += ["FadeOut(e1_lbl)", "FadeOut(e2_lbl)"]

    L.append("        self.play(")
    for t in transforms:
        L.append(f"            {t},")
    L += ["            run_time=1.8,", "        )"]

    if show_preset_labels:
        L.append("        self.play(FadeIn(tvec_lbl), FadeIn(res_lbl), run_time=0.5)")
    L.append("        self.wait(1.5)")
    return _join(L)


# ===========================================================================
# Non-Linear Transformations
# ===========================================================================

def build_nonlinear_source(
    mode, intensity, scale, show_grid, show_points,
    text_position="top_left", text_color="teal", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    mode = str(mode or "swirl").strip().lower()
    pos_call, _, subtitle_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font   = text_font or "Arial"
    fs     = max(8, int(text_font_size))
    fs_sub = max(8, fs - 8)

    preset_map = {
        "swirl": (
            "Swirl",
            "Nonlinear rotation that increases with radius",
            [
                "            r = np.linalg.norm(p[:2])",
                f"            angle = {intensity:.4f} * r * 0.35",
                "            c, s = np.cos(angle), np.sin(angle)",
                "            x, y = p[0], p[1]",
                "            return np.array([c*x - s*y, s*x + c*y, 0])",
            ],
        ),
        "wave": (
            "Wave Warp",
            "Sinusoidal displacement across the grid",
            [
                f"            x = p[0] + {intensity:.4f} * 0.35 * np.sin(1.4 * p[1])",
                f"            y = p[1] + {intensity:.4f} * 0.35 * np.sin(1.4 * p[0])",
                "            return np.array([x, y, 0])",
            ],
        ),
        "bulge": (
            "Bulge",
            "Radial expansion strongest near the origin",
            [
                "            r2 = p[0]*p[0] + p[1]*p[1]",
                f"            factor = 1 + {intensity:.4f} * np.exp(-0.18 * r2)",
                "            return np.array([factor*p[0], factor*p[1], 0])",
            ],
        ),
        "pinch": (
            "Pinch",
            "Radial compression strongest near the origin",
            [
                "            r2 = p[0]*p[0] + p[1]*p[1]",
                f"            factor = 1 - 0.65 * {intensity:.4f} * np.exp(-0.20 * r2)",
                "            return np.array([factor*p[0], factor*p[1], 0])",
            ],
        ),
        "complex_square": (
            "Complex Square",
            "Maps z to a scaled z squared shape",
            [
                "            z = complex(p[0], p[1])",
                f"            w = {0.18 * intensity:.4f} * z*z",
                "            return np.array([w.real, w.imag, 0])",
            ],
        ),
    }
    title, subtitle, body = preset_map[mode]
    title    = preset_title    or title
    subtitle = preset_subtitle or subtitle

    tkw     = _text_kwargs(font, fs,     txt_col, bold, italic, stroke_width, stroke_col)
    tkw_sub = _text_kwargs(font, fs_sub, txt_col, bold, italic, stroke_width, stroke_col)

    L = [
        "from manim import *",
        "import numpy as np",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
    ]

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)

    if show_preset_labels:
        title_fs = fs_sub if text_content else fs
        L.append(_text_line("title", title, font, title_fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        if text_content:
            L.append(f"        title.next_to(custom_lbl, {subtitle_dir}, buff=0.12)")
        else:
            L.append(_place_label("title", pos_call, x_offset, y_offset))
        L.append(_text_line("subtitle", subtitle, font, fs_sub, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        L.append(f"        subtitle.next_to(title, {subtitle_dir}, buff=0.12)")
        if text_content:
            L.append("        self.play(FadeIn(custom_lbl), FadeIn(title), FadeIn(subtitle), run_time=0.7)")
        else:
            L.append("        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)")
    else:
        if text_content:
            L.append("        self.play(FadeIn(custom_lbl), run_time=0.7)")
        else:
            L.append("        self.play(run_time=0.01)")

    L += [
        "",
        "        def warp(p):",
        *body,
        "",
        "        grid = NumberPlane(",
        f"            x_range=[{-scale:.2f}, {scale:.2f}, 1],",
        f"            y_range=[{-scale:.2f}, {scale:.2f}, 1],",
        "            background_line_style=dict(stroke_color=BLUE_E, stroke_opacity=0.45),",
        "        )",
        "        warped_grid = grid.copy().apply_function(warp)",
        "        warped_grid.set_style(stroke_color=TEAL, stroke_opacity=0.75)",
    ]

    if show_grid:
        L.append("        self.play(Create(grid), run_time=0.8)")

    if show_points:
        L += [
            "        pts = VGroup()",
            f"        for x in np.linspace({-scale + 1:.2f}, {scale - 1:.2f}, 5):",
            f"            for y in np.linspace({-scale + 1:.2f}, {scale - 1:.2f}, 5):",
            "                pts.add(Dot(grid.c2p(x, y), radius=0.045, color=YELLOW))",
            "        warped_pts = pts.copy().apply_function(warp)",
            "        self.play(FadeIn(pts), run_time=0.5)",
            "        self.play(Transform(grid, warped_grid), Transform(pts, warped_pts), run_time=2.4)",
        ]
    else:
        L.append("        self.play(Transform(grid, warped_grid), run_time=2.4)")

    L.append("        self.wait(1.5)")
    return _join(L)


# ===========================================================================
# Code Animation
# ===========================================================================

def build_code_source(
    code_str, language, anim, background, add_line_numbers, font_size, run_time,
    text_position="top_left", text_color="white", text_font="Consolas",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    safe       = repr(code_str)
    language   = str(language   or "python").lower()
    background = str(background or "window").lower()
    font       = text_font or "Consolas"
    fs         = max(8, int(text_font_size))

    if anim == "Write":
        anim_lines = [f"            self.play(Write(code), run_time={run_time:.1f})"]
    elif anim == "FadeIn":
        anim_lines = [f"            self.play(FadeIn(code), run_time={run_time:.1f})"]
    elif anim == "FadeIn Up":
        anim_lines = [f"            self.play(FadeIn(code, shift=UP * 0.4), run_time={run_time:.1f})"]
    elif anim == "Create":
        anim_lines = [f"            self.play(Create(code), run_time={run_time:.1f})"]
    elif anim == "Typewriter":
        anim_lines = [
            "            self.play(FadeIn(code.background), run_time=0.4)",
            "            self.play(",
            "                LaggedStart(",
            "                    *[Write(line) for line in code.code_lines],",
            "                    lag_ratio=0.5,",
            "                ),",
            f"                run_time={run_time:.1f},",
            "            )",
        ]
    else:
        anim_lines = [f"            self.play(FadeIn(code), run_time={run_time:.1f})"]

    pos_call, _, _ = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)

    L = [
        "from manim import *",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
    ]

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)
        L.append("        self.add(custom_lbl)")

    L += [
        f"        _raw = {safe}",
        "        _lines = _raw.split('\\n')",
        "        _chunks = ['\\n'.join(_lines[i:i+13]) for i in range(0, len(_lines), 13)]",
        "        _prev = None",
        "        for _i, _chunk_str in enumerate(_chunks):",
        "            code = Code(",
        "                code_string=_chunk_str,",
        f"                language={repr(language)},",
        f"                background={repr(background)},",
        f"                add_line_numbers={add_line_numbers},",
        "                line_numbers_from=_i * 13 + 1,",
        f"                paragraph_config={{'font_size': {font_size:.0f}, 'font': {repr(font)}}},",
        "            )",
        "            code.scale_to_fit_width(13)",
        "            if code.height > 7.2:",
        "                code.scale_to_fit_height(7.2)",
        "            code.center()",
        "            if _prev is not None:",
        "                self.play(FadeOut(_prev), run_time=0.5)",
    ] + anim_lines + [
        "            self.wait(1.5)",
        "            _prev = code",
    ]

    return _join(L)


# ===========================================================================
# StreamLines
# ===========================================================================

_SL_COLOR_SCHEMES = {
    "default":    "BLUE, TEAL, GREEN, YELLOW, RED",
    "hot":        "RED, ORANGE, YELLOW, WHITE",
    "cool":       "BLUE, TEAL, TEAL_B, WHITE",
    "mono":       "BLUE_E, BLUE_C, BLUE_A, WHITE",
    "rainbow":    "RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE",
    "green_gold": "GREEN_E, GREEN, GREEN_A, GOLD, YELLOW",
}


def build_streamlines_source(
    mode, scale, spacing, flow_speed, virtual_time, stroke_width_sl, show_axes, animate,
    color_scheme="default", cam_zoom=1.0,
    line_opacity=0.9, pulse_width=0.45, hold_duration=4.0,
    custom_fx="-y", custom_fy="x",
    custom_field_raw="np.array([-p[1], p[0], 0])", field_advanced=False,
    text_position="top_left", text_color="teal", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    mode = str(mode or "vortex").strip().lower()
    pos_call, _, subtitle_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font   = text_font or "Arial"
    fs     = max(8, int(text_font_size))
    fs_sub = max(8, fs - 8)
    sl_colors = _SL_COLOR_SCHEMES.get(str(color_scheme or "default").strip().lower(),
                                      _SL_COLOR_SCHEMES["default"])

    field_map = {
        "vortex": (
            "Vortex",
            "np.array([-p[1], p[0], 0])",
            "Rotating field around the origin",
        ),
        "source": (
            "Source",
            "np.array([p[0], p[1], 0]) / (np.linalg.norm(p[:2]) + 0.6)",
            "Outward radial flow",
        ),
        "sink": (
            "Sink",
            "-np.array([p[0], p[1], 0]) / (np.linalg.norm(p[:2]) + 0.6)",
            "Inward radial flow",
        ),
        "saddle": (
            "Saddle",
            "np.array([p[0], -p[1], 0])",
            "Hyperbolic saddle field",
        ),
        "wave": (
            "Wave",
            "np.array([np.sin(p[1]), np.cos(p[0]), 0])",
            "Sinusoidal wave field",
        ),
        "shear": (
            "Shear",
            "np.array([p[1], 0, 0])",
            "Horizontal shear flow",
        ),
        "spiral": (
            "Spiral",
            "np.array([-p[1] - 0.3 * p[0], p[0] - 0.3 * p[1], 0])",
            "Spiral sink (rotation + inward pull)",
        ),
        "dipole": (
            "Dipole",
            "np.array([p[1] ** 2 - p[0] ** 2, -2 * p[0] * p[1], 0]) "
            "/ (np.linalg.norm(p[:2]) ** 4 + 0.6)",
            "Dipole (doublet) flow",
        ),
    }
    if mode == "custom":
        title, subtitle = "Custom", "Custom vector field"
        if field_advanced:
            raw = _validate_expr(custom_field_raw, "Field f(p) expression",
                                 default="np.array([-p[1], p[0], 0])")
            field_body = [f"            return {raw}"]
        else:
            fx = _validate_expr(custom_fx, "Fx(x, y) expression", default="-y")
            fy = _validate_expr(custom_fy, "Fy(x, y) expression", default="x")
            field_body = [
                "            x, y = p[0], p[1]",
                f"            return np.array([{fx}, {fy}, 0])",
            ]
    else:
        title, expr, subtitle = field_map[mode]
        field_body = [f"            return {expr}"]
    subtitle = preset_subtitle or subtitle
    step = max(0.2, float(spacing))

    tkw     = _text_kwargs(font, fs,     txt_col, bold, italic, stroke_width, stroke_col)
    tkw_sub = _text_kwargs(font, fs_sub, txt_col, bold, italic, stroke_width, stroke_col)

    L = ["from manim import *", "import numpy as np", ""]
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0    / zoom_f:.3f}",
            "",
        ]
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
    ]

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)

    if show_preset_labels:
        title_fs = fs_sub if text_content else fs
        L.append(_text_line("title", preset_title or f"{title} StreamLines", font, title_fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        if text_content:
            L.append(f"        title.next_to(custom_lbl, {subtitle_dir}, buff=0.12)")
        else:
            L.append(_place_label("title", pos_call, x_offset, y_offset))
        L.append(_text_line("subtitle", subtitle, font, fs_sub, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        L.append(f"        subtitle.next_to(title, {subtitle_dir}, buff=0.12)")
        if text_content:
            L.append("        self.play(FadeIn(custom_lbl), FadeIn(title), FadeIn(subtitle), run_time=0.7)")
        else:
            L.append("        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)")
    else:
        if text_content:
            L.append("        self.play(FadeIn(custom_lbl), run_time=0.7)")
        else:
            L.append("        self.play(run_time=0.01)")

    L += [
        "",
        "        def field(p):",
        *field_body,
        "",
        "        plane = NumberPlane(",
        f"            x_range=[{-scale:.2f}, {scale:.2f}, 1],",
        f"            y_range=[{-scale:.2f}, {scale:.2f}, 1],",
        "            background_line_style=dict(stroke_color=BLUE_E, stroke_opacity=0.25),",
        "        )",
    ]

    if show_axes:
        L.append("        self.play(FadeIn(plane), run_time=0.6)")

    L += [
        "        stream_lines = StreamLines(",
        "            field,",
        f"            x_range=[{-scale:.2f}, {scale:.2f}, {step:.2f}],",
        f"            y_range=[{-scale:.2f}, {scale:.2f}, {step:.2f}],",
        f"            colors=[{sl_colors}],",
        "            min_color_scheme_value=0,",
        f"            max_color_scheme_value={max(1.0, scale):.2f},",
        "            color_scheme=lambda p: np.linalg.norm(field(p)),",
        "            dt=0.05,",
        f"            virtual_time={virtual_time:.2f},",
        "            max_anchors_per_line=70,",
        f"            stroke_width={stroke_width_sl:.2f},",
        f"            opacity={max(0.05, min(1.0, float(line_opacity))):.2f},",
        "        )",
    ]

    if animate:
        L += [
            "        self.add(stream_lines)",
            "        stream_lines.start_animation(",
            "            warm_up=False,",
            f"            flow_speed={flow_speed:.2f},",
            f"            time_width={max(0.05, min(1.0, float(pulse_width))):.2f},",
            "        )",
            f"        self.wait({max(0.5, float(hold_duration)):.2f})",
            "        self.play(stream_lines.end_animation(), run_time=0.8)",
        ]
    else:
        L.append("        self.play(stream_lines.create(), run_time=2.5)")

    L.append("        self.wait(1.5)")
    return _join(L)


# ===========================================================================
# Geometry
# ===========================================================================

_SHAPE_ANIMS = {
    "Create":            ("Create(obj)", 1.5),
    "DrawBorderThenFill":("DrawBorderThenFill(obj)", 2.0),
    "FadeIn":            ("FadeIn(obj)", 1.2),
    "GrowFromCenter":    ("GrowFromCenter(obj)", 1.5),
    "SpinInFromNothing": ("SpinInFromNothing(obj)", 1.8),
    "FadeInFromLarge":   ("FadeInFromLarge(obj)", 1.5),
    "Write":             ("Write(obj)", 2.0),
    "SpiralIn":          ("SpiralIn(obj)", 2.0),
    "ShowIncreasingSubsets": ("ShowIncreasingSubsets(obj)", 2.0),
}


def build_geometry_source(
    shape, size, shape_fill_color, shape_stroke_color, fill_opacity,
    shape_stroke_width, anim, cam_zoom=1.0, count=1, arrangement="row",
    text_position="top_left", text_color="white", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    pos_call, _, stack_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    fill_col   = _text_color(shape_fill_color or "blue")
    str_col    = _text_color(shape_stroke_color or "white")
    font = text_font or "Arial"
    fs   = max(8, int(text_font_size))

    s    = max(0.3, float(size or 1.5))
    fop  = max(0.0, min(1.0, float(fill_opacity if fill_opacity is not None else 0.6)))
    gsw  = max(0.0, float(shape_stroke_width or 3.0))
    shape_lower = str(shape or "circle").strip().lower()

    base_kw = (
        f"fill_color={fill_col}, fill_opacity={fop:.2f}, "
        f"stroke_color={str_col}, stroke_width={gsw:.1f}"
    )

    shape_code = {
        "circle":      f"        obj = Circle(radius={s:.2f}, {base_kw})",
        "square":      f"        obj = Square(side_length={s*2:.2f}, {base_kw})",
        "rectangle":   f"        obj = Rectangle(width={s*1.6:.2f}, height={s:.2f}, {base_kw})",
        "triangle":    f"        obj = Triangle({base_kw}).scale({s:.2f})",
        "pentagon":    f"        obj = RegularPolygon(n=5, {base_kw}).scale({s:.2f})",
        "hexagon":     f"        obj = RegularPolygon(n=6, {base_kw}).scale({s:.2f})",
        "star":        f"        obj = Star(n=5, outer_radius={s:.2f}, inner_radius={s*0.45:.2f}, {base_kw})",
        "arrow":       f"        obj = Arrow(start=LEFT*{s:.2f}, end=RIGHT*{s:.2f}, color={str_col}, stroke_width={gsw:.1f})",
        "doublearrow": f"        obj = DoubleArrow(start=LEFT*{s:.2f}, end=RIGHT*{s:.2f}, color={str_col}, stroke_width={gsw:.1f})",
        "annulus":     f"        obj = Annulus(inner_radius={s*0.35:.2f}, outer_radius={s:.2f}, {base_kw})",
    }.get(shape_lower, f"        obj = Circle(radius={s:.2f}, {base_kw})")

    n_shapes = max(1, min(8, int(count or 1)))
    arr      = str(arrangement or "row").strip().lower()

    anim_call, anim_rt = _SHAPE_ANIMS.get(str(anim or "Create"), ("Create(obj)", 1.5))
    # GrowArrow only accepts a single Arrow — skip the override for multi-shape groups.
    if n_shapes == 1 and shape_lower in ("arrow", "doublearrow") \
            and str(anim or "") in ("Create", "GrowFromCenter", "Write"):
        anim_call, anim_rt = "GrowArrow(obj)", 1.2

    L = ["from manim import *", ""]
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0    / zoom_f:.3f}",
            "",
        ]
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
        shape_code,
    ]

    if n_shapes > 1:
        # Replicate the base shape into a colour-cycled VGroup, then lay it out.
        L += [
            f"        obj = VGroup(*[obj.copy() for _ in range({n_shapes})])",
            f"        _pal = color_gradient([BLUE, TEAL, GREEN, YELLOW, ORANGE, RED, PURPLE], {n_shapes})",
            "        for _i, _m in enumerate(obj):",
            "            _m.set_color(_pal[_i])",
        ]
        if arr == "circle":
            L += [
                "        for _i, _m in enumerate(obj):",
                "            _m.move_to(RIGHT * 2.3)",
                f"            _m.rotate(TAU * _i / {n_shapes}, about_point=ORIGIN)",
            ]
        elif arr == "column":
            L.append("        obj.arrange(DOWN, buff=0.4)")
        elif arr == "grid":
            L.append("        obj.arrange_in_grid(buff=0.45)")
        else:  # row
            L.append("        obj.arrange(RIGHT, buff=0.45)")
        # Shrink (never enlarge) to keep the group inside the frame.
        L.append("        obj.scale(min(1.0, 12.0 / max(obj.width, 0.1), 6.5 / max(obj.height, 0.1)))")

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)

    if show_preset_labels:
        name_map = {"doublearrow": "Double Arrow"}
        disp = preset_title or name_map.get(shape_lower, shape_lower.replace("_", " ").title())
        L.append(_text_line("lbl", disp, font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        if text_content:
            L.append(f"        lbl.next_to(custom_lbl, {stack_dir}, buff=0.12)")
        else:
            L.append(_place_label("lbl", pos_call, x_offset, y_offset))

    parts = [anim_call]
    if text_content:       parts.append("FadeIn(custom_lbl)")
    if show_preset_labels: parts.append("FadeIn(lbl)")
    L.append(f"        self.play({', '.join(parts)}, run_time={anim_rt:.1f})")
    L.append("        self.wait(1.5)")
    return _join(L)


# ===========================================================================
# Bar Chart
# ===========================================================================

def build_barchart_source(
    bar_labels, bar_values, bar_colors,
    auto_y=True, y_min=0, y_max=30, y_step=5,
    animate=True, show_labels=True,
    x_label="", y_label="", bar_width=0.6,
    text_position="top_left", text_color="white", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    pos_call, _, stack_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font = text_font or "Arial"
    fs   = max(8, int(text_font_size))

    labels = [str(l)[:24] for l in (bar_labels or ["A", "B", "C"])][:5]
    values = [float(v) for v in (bar_values or [10, 20, 15])][:5]
    n = min(len(labels), len(values))
    labels, values = labels[:n], values[:n]

    raw_colors = list(bar_colors or [])[:5]
    manim_colors = [_text_color(c) for c in raw_colors]
    defaults = ["BLUE", "RED", "GREEN", "YELLOW", "PURPLE"]
    while len(manim_colors) < n:
        manim_colors.append(defaults[len(manim_colors) % 5])
    manim_colors = manim_colors[:n]

    if auto_y or y_min is None or y_max is None:
        import math as _math
        lo = min(min(values, default=0), 0)
        hi = max(values, default=10) * 1.3 + 2
        st = max(1.0, (hi - lo) / 6)
        magnitude = 10 ** _math.floor(_math.log10(max(st, 0.5)))
        st = _math.ceil(st / magnitude) * magnitude
        hi = _math.ceil(hi / st) * st
        lo = _math.floor(lo / st) * st
    else:
        lo, hi, st = float(y_min), float(y_max), max(0.1, float(y_step))
    if lo >= hi:
        hi = lo + 10

    colors_str = f"[{', '.join(manim_colors)}]"
    bw = max(0.1, min(1.0, float(bar_width if bar_width is not None else 0.6)))
    xlab = str(x_label or "").strip()[:48]
    ylab = str(y_label or "").strip()[:48]

    L = [
        "from manim import *",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        f"        chart = BarChart(",
        f"            values={values!r},",
        f"            bar_names={labels!r},",
        f"            y_range=[{lo:.1f}, {hi:.1f}, {st:.1f}],",
        f"            bar_colors={colors_str},",
        f"            bar_width={bw:.2f},",
        "            x_length=8, y_length=5,",
        "            axis_config=dict(color=GREY_B),",
        "        )",
    ]

    # Axis titles use Text() (Pango) — never Tex — so they don't pull in LaTeX.
    if xlab:
        L.append(f"        x_axis_lbl = Text({xlab!r}, font_size=24, color=WHITE).next_to(chart.x_axis, DOWN, buff=0.35)")
    if ylab:
        L.append(f"        y_axis_lbl = Text({ylab!r}, font_size=24, color=WHITE).rotate(PI/2).next_to(chart.y_axis, LEFT, buff=0.35)")

    if show_labels:
        L.append("        bar_lbl = chart.get_bar_labels(font_size=20, color=WHITE)")

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)

    if show_preset_labels:
        L.append(_text_line("title", preset_title or "Bar Chart", font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        if text_content:
            L.append(f"        title.next_to(custom_lbl, {stack_dir}, buff=0.12)")
        else:
            L.append(_place_label("title", pos_call, x_offset, y_offset))

    if animate:
        parts = ["Create(chart)"]
        if xlab:               parts.append("FadeIn(x_axis_lbl)")
        if ylab:               parts.append("FadeIn(y_axis_lbl)")
        if text_content:       parts.append("FadeIn(custom_lbl)")
        if show_preset_labels: parts.append("FadeIn(title)")
        L.append(f"        self.play({', '.join(parts)}, run_time=2.0)")
        if show_labels:
            L.append("        self.play(FadeIn(bar_lbl), run_time=0.8)")
    else:
        add_parts = ["chart"]
        if xlab:               add_parts.append("x_axis_lbl")
        if ylab:               add_parts.append("y_axis_lbl")
        if text_content:       add_parts.append("custom_lbl")
        if show_preset_labels: add_parts.append("title")
        if show_labels:        add_parts.append("bar_lbl")
        L.append(f"        self.add({', '.join(add_parts)})")

    L.append("        self.wait(2.0)")
    return _join(L)


# ===========================================================================
# 3D Surface
# ===========================================================================

_SURFACES = {
    "sine_wave": {
        "title":   "Sine Wave Surface",
        "func":    "np.array([u, v, np.sin(u) * np.cos(v)])",
        "u_range": [-3.14159, 3.14159],
        "v_range": [-3.14159, 3.14159],
    },
    "paraboloid": {
        "title":   "Paraboloid",
        "func":    "np.array([u, v, 0.3*(u**2 + v**2)])",
        "u_range": [-2.5, 2.5],
        "v_range": [-2.5, 2.5],
    },
    "saddle": {
        "title":   "Saddle Surface",
        "func":    "np.array([u, v, 0.3*(u**2 - v**2)])",
        "u_range": [-2.5, 2.5],
        "v_range": [-2.5, 2.5],
    },
    "torus": {
        "title":   "Torus",
        "func":    "np.array([(2 + np.cos(v)) * np.cos(u), (2 + np.cos(v)) * np.sin(u), np.sin(v)])",
        "u_range": [0, 6.28318],
        "v_range": [0, 6.28318],
    },
    "sphere": {
        "title":   "Sphere",
        "func":    "np.array([1.8*np.cos(u)*np.cos(v), 1.8*np.cos(u)*np.sin(v), 1.8*np.sin(u)])",
        "u_range": [-1.5708, 1.5708],
        "v_range": [0, 6.28318],
    },
    "ripple": {
        "title":   "Ripple Surface",
        "func":    "np.array([u, v, np.sin(np.sqrt(u**2 + v**2 + 0.001))])",
        "u_range": [-3.5, 3.5],
        "v_range": [-3.5, 3.5],
    },
    "mobius": {
        "title":   "Möbius Strip",
        "func":    "np.array([(1 + v/2*np.cos(u/2))*np.cos(u), (1 + v/2*np.cos(u/2))*np.sin(u), v/2*np.sin(u/2)])",
        "u_range": [0, 6.28318],
        "v_range": [-0.5, 0.5],
    },
    "cone": {
        "title":   "Cone",
        "func":    "np.array([(2 - v)*np.cos(u), (2 - v)*np.sin(u), v])",
        "u_range": [0, 6.28318],
        "v_range": [0, 2],
    },
    "cylinder": {
        "title":   "Cylinder",
        "func":    "np.array([1.5*np.cos(u), 1.5*np.sin(u), v])",
        "u_range": [0, 6.28318],
        "v_range": [-2, 2],
    },
    "hyperboloid": {
        "title":   "Hyperboloid",
        "func":    "np.array([np.cosh(v)*np.cos(u), np.cosh(v)*np.sin(u), 1.5*np.sinh(v)])",
        "u_range": [0, 6.28318],
        "v_range": [-1.3, 1.3],
    },
    "monkey_saddle": {
        "title":   "Monkey Saddle",
        "func":    "np.array([u, v, 0.18*(u**3 - 3*u*v**2)])",
        "u_range": [-2, 2],
        "v_range": [-2, 2],
    },
    "helicoid": {
        "title":   "Helicoid",
        "func":    "np.array([v*np.cos(u), v*np.sin(u), 0.4*u])",
        "u_range": [0, 12.56637],
        "v_range": [-2, 2],
    },
}

_SURF_COLORS = {
    "checkerboard_blue":  "[BLUE_D, BLUE_E]",
    "checkerboard_teal":  "[TEAL_D, TEAL_E]",
    "checkerboard_green": "[GREEN_D, GREEN_E]",
    "solid_blue":         "[BLUE, BLUE]",
    "solid_red":          "[RED_D, RED_E]",
    "solid_orange":       "[ORANGE, GOLD_D]",
    "rainbow":            "[RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]",
}


def build_surface3d_source(
    surface_type, theta, phi, cam_zoom,
    show_axes, color_mode, resolution, animate_camera,
    fill_opacity=1.0, surf_stroke_width=0.5,
    text_position="top_left", text_color="white", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    pos_call, _, stack_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    font = text_font or "Arial"
    fs   = max(8, int(text_font_size))

    surf_key = str(surface_type or "sine_wave").strip().lower()
    surf     = _SURFACES.get(surf_key, _SURFACES["sine_wave"])
    colors   = _SURF_COLORS.get(str(color_mode or "checkerboard_blue").strip().lower(),
                                 _SURF_COLORS["checkerboard_blue"])
    res      = max(4, min(16, int(resolution or 8)))
    theta_d  = float(theta if theta is not None else 70)
    phi_d    = float(phi   if phi   is not None else 75)
    zoom_f   = float(cam_zoom or 1.0)
    fop      = max(0.0, min(1.0, float(fill_opacity if fill_opacity is not None else 1.0)))
    sw       = max(0.0, float(surf_stroke_width if surf_stroke_width is not None else 0.5))

    ur = surf["u_range"]
    vr = surf["v_range"]

    L = [
        "from manim import *",
        "import numpy as np",
        "",
        "class ManimScene(ThreeDScene):",
        "    def construct(self):",
    ]

    if show_axes:
        L += [
            "        axes = ThreeDAxes(x_range=[-4,4], y_range=[-4,4], z_range=[-3,3],",
            "                          x_length=8, y_length=8, z_length=5)",
            "        self.play(Create(axes), run_time=0.8)",
        ]

    L += [
        "        surface = Surface(",
        f"            lambda u, v: {surf['func']},",
        f"            u_range=[{ur[0]:.5f}, {ur[1]:.5f}],",
        f"            v_range=[{vr[0]:.5f}, {vr[1]:.5f}],",
        f"            resolution=({res}, {res}),",
        f"            checkerboard_colors={colors},",
        f"            fill_opacity={fop:.2f},",
        f"            stroke_width={sw:.2f}, stroke_color=GREY_A,",
        "        )",
        f"        self.set_camera_orientation(theta={theta_d:.1f}*DEGREES, phi={phi_d:.1f}*DEGREES, zoom={zoom_f:.2f})",
        "        self.play(Create(surface), run_time=2.5)",
    ]

    if text_content or show_preset_labels:
        if text_content:
            _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                              stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)
        if show_preset_labels:
            L.append(_text_line("title", preset_title or surf["title"], font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
            if text_content:
                L.append(f"        title.next_to(custom_lbl, {stack_dir}, buff=0.12)")
            else:
                L.append(_place_label("title", pos_call, x_offset, y_offset))
        fade_parts = []
        if text_content:       fade_parts.append("FadeIn(custom_lbl)")
        if show_preset_labels: fade_parts.append("FadeIn(title)")
        if fade_parts:
            mob_names = [p.split("FadeIn(")[1].rstrip(")") for p in fade_parts]
            L.append(f"        self.add_fixed_in_frame_mobjects({', '.join(mob_names)})")
            L.append(f"        self.play({', '.join(fade_parts)}, run_time=0.6)")

    if animate_camera:
        L += [
            "        self.begin_ambient_camera_rotation(rate=0.15)",
            "        self.wait(5)",
            "        self.stop_ambient_camera_rotation()",
        ]
    else:
        L.append("        self.wait(2.0)")

    return _join(L)


# ===========================================================================
# Number Line / ValueTracker
# ===========================================================================

_NL_FUNC_EVAL = {
    'x':       lambda x: x,
    'x^2':     lambda x: x**2,
    'x^3':     lambda x: x**3,
    'sin(x)':  lambda x: __import__('math').sin(x),
    'cos(x)':  lambda x: __import__('math').cos(x),
    '|x|':     lambda x: abs(x),
    'sqrt|x|': lambda x: __import__('math').sqrt(abs(x)),
    '1/x':     lambda x: (1.0 / x if abs(x) > 0.05 else 0),
}

_NL_FUNC_BODY = {
    'x':       'x',
    'x^2':     'x**2',
    'x^3':     'x**3',
    'sin(x)':  'math.sin(x)',
    'cos(x)':  'math.cos(x)',
    '|x|':     'abs(x)',
    'sqrt|x|': 'math.sqrt(abs(x))',
    '1/x':     '(1.0 / x if abs(x) > 0.05 else 0)',
}


def build_numberline_source(
    x_min, x_max, tick_step, start_val, target_vals,
    run_time_per_step, dot_color, show_label,
    show_func=False, func_expr='x^2', func_color='yellow', show_vline=True,
    text_position="top_left", text_color="white", text_font="Arial",
    text_content="", text_font_size=22, show_preset_labels=True,
    preset_title="", preset_subtitle="",
    bold=False, italic=False, stroke_width=0, stroke_color="white",
    x_offset=0, y_offset=0, gradient="none",
):
    pos_call, _, stack_dir = _text_position(text_position)
    txt_col    = _text_color(text_color)
    stroke_col = _text_color(stroke_color)
    dot_col    = _text_color(dot_color or "blue")
    func_col   = _text_color(func_color or "yellow")
    font = text_font or "Arial"
    fs   = max(8, int(text_font_size))

    x0   = float(x_min       if x_min       is not None else -5)
    x1   = float(x_max       if x_max       is not None else  5)
    step = max(0.1, float(tick_step         if tick_step is not None else 1))
    sv   = float(start_val   if start_val   is not None else 0)
    rt   = max(0.3, float(run_time_per_step if run_time_per_step is not None else 1.5))
    if x0 >= x1:
        x1 = x0 + 10

    # Pre-compute y_scale for the function overlay
    y_scale = 1.0
    if show_func:
        fn_key  = func_expr if func_expr in _NL_FUNC_EVAL else 'x^2'
        fn_eval = _NL_FUNC_EVAL[fn_key]
        import math as _m
        xs = [x0 + (x1 - x0) * i / 40 for i in range(41)]
        try:
            ys = []
            for xv in xs:
                try:
                    ys.append(abs(fn_eval(xv)))
                except Exception:
                    pass
            y_max = max(ys) if ys else 1.0
            y_scale = round(1.8 / max(y_max, 0.001), 6)
        except Exception:
            y_scale = 1.0
        func_body = _NL_FUNC_BODY.get(fn_key, 'x**2')

    targets = []
    for v in (target_vals or []):
        try:
            targets.append(float(v))
        except (TypeError, ValueError):
            pass
    targets = targets[:4]

    L = [
        "from manim import *",
        *(["import numpy as np"] if show_func else []),
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        nl = NumberLine(",
        f"            x_range=[{x0:.2f}, {x1:.2f}, {step:.2f}],",
        "            length=10,",
        "            include_numbers=True,",
        "            label_direction=DOWN,",
        "            font_size=24,",
        "        )",
        f"        tracker = ValueTracker({sv:.4f})",
        f"        dot = always_redraw(lambda: Dot(nl.n2p(tracker.get_value()), color={dot_col}, radius=0.14))",
    ]

    if show_label:
        L += [
            "        val_lbl = always_redraw(",
            f'            lambda: Text(f"{{tracker.get_value():.2f}}", font_size=22, color={dot_col})',
            "            .next_to(nl.n2p(tracker.get_value()), UP, buff=0.25)",
            "        )",
        ]

    if show_func:
        L += [
            "        import math",
            f"        def _f(x):",
            f"            try: return {func_body}",
            f"            except Exception: return 0",
            f"        _ys = {y_scale}",
            f"        curve = ParametricFunction(",
            f"            lambda t: nl.n2p(t) + np.array([0, _f(t) * _ys, 0]),",
            f"            t_range=[{x0:.4f}, {x1:.4f}, {max(0.02, (x1-x0)/200):.4f}],",
            f"            color={func_col},",
            f"            stroke_width=2.5,",
            f"        )",
        ]
        if show_vline:
            L += [
                f"        v_ind = always_redraw(lambda: DashedLine(",
                f"            nl.n2p(tracker.get_value()),",
                f"            nl.n2p(tracker.get_value()) + np.array([0, _f(tracker.get_value()) * _ys, 0]),",
                f"            color={func_col}, dash_length=0.08, stroke_width=1.5,",
                f"        ))",
                f"        curve_dot = always_redraw(lambda: Dot(",
                f"            nl.n2p(tracker.get_value()) + np.array([0, _f(tracker.get_value()) * _ys, 0]),",
                f"            color={func_col}, radius=0.1,",
                f"        ))",
            ]

    if text_content:
        _place_custom_lbl(L, text_content, font, fs, txt_col, bold, italic,
                          stroke_width, stroke_col, pos_call, gradient, x_offset, y_offset)

    if show_preset_labels:
        L.append(_text_line("title", preset_title or "Number Line", font, fs, txt_col, bold, italic, stroke_width, stroke_col, gradient))
        if text_content:
            L.append(f"        title.next_to(custom_lbl, {stack_dir}, buff=0.12)")
        else:
            L.append(_place_label("title", pos_call, x_offset, y_offset))

    L.append("        self.play(Create(nl), run_time=0.8)")
    if show_func:
        L.append("        self.play(Create(curve), run_time=1.0)")
    fade_parts = ["FadeIn(dot)"]
    if show_label:         fade_parts.append("FadeIn(val_lbl)")
    if show_func and show_vline:
        fade_parts += ["FadeIn(v_ind)", "FadeIn(curve_dot)"]
    if text_content:       fade_parts.append("FadeIn(custom_lbl)")
    if show_preset_labels: fade_parts.append("FadeIn(title)")
    L.append(f"        self.play({', '.join(fade_parts)}, run_time=0.5)")

    for tv in targets:
        L.append(f"        self.play(tracker.animate.set_value({tv:.4f}), run_time={rt:.2f})")
        L.append("        self.wait(0.4)")

    L.append("        self.wait(1.0)")
    return _join(L)


# ===========================================================================
# Function Grapher
# ===========================================================================

_FG_NAMESPACE = ("sin, cos, tan, exp, log, log10, sqrt, "
                 "sinh, cosh, tanh, arcsin, arccos, arctan, floor, ceil, pi, e")

# anim name -> (play-wrapper template applied to the curve var `{g}`, run_time)
_FG_ANIMS = {
    "Create":             ("Create({g})",             1.5),
    "FadeIn":             ("FadeIn({g})",             1.2),
    "Write":              ("Create({g})",             2.0),
    "GrowFromEdge":       ("GrowFromEdge({g}, LEFT)", 1.8),
    "DrawBorderThenFill": ("Create({g})",             1.8),
}


def _funcgraph_expr(expr, label):
    """Friendly-syntax translate (^ -> **) then validate against the blocklists."""
    return _validate_expr(str(expr or "").replace("^", "**"), label, default="x**2")


def _emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=False,
                         x_length=11.0, y_length=6.0,
                         grid_x_length=None, grid_y_length=None):
    """Append the shared Cartesian axes block to L (used by funcgraph + parametric).

    Emits the Axes definition, optional MathTex tick labels (use_latex only), an
    optional NumberPlane grid, then Create(axes). The caller emits the
    `class ManimScene(Scene):` / `def construct(self):` header first.

    grid_x_length / grid_y_length, when not None, size the NumberPlane to match
    the (possibly equal-aspect) axes so the grid lattice coincides with the axis
    ticks. funcgraph leaves them None → grid output is byte-identical.
    """
    L += [
        "        axes = Axes(",
        f"            x_range=[{xlo:.4f}, {xhi:.4f}, {xs:.4f}],",
        f"            y_range=[{ylo:.4f}, {yhi:.4f}, {ys:.4f}],",
        f"            x_length={x_length:g}, y_length={y_length:g},",
        "            axis_config=dict(color=GREY, include_tip=True),",
        "        )",
    ]
    if use_latex:
        L.append("        axes.add_coordinates()")
    if show_grid:
        L += [
            "        grid = NumberPlane(",
            f"            x_range=[{xlo:.4f}, {xhi:.4f}],",
            f"            y_range=[{ylo:.4f}, {yhi:.4f}],",
        ]
        if grid_x_length is not None and grid_y_length is not None:
            L.append(f"            x_length={grid_x_length:g}, y_length={grid_y_length:g},")
        L += [
            "            background_line_style=dict(stroke_color=BLUE_E, stroke_opacity=0.25),",
            "        )",
            "        self.play(FadeIn(grid), run_time=0.6)",
        ]
    L.append("        self.play(Create(axes), run_time=0.8)")


def _emit_curve_label(L, i, want_label, label, color, play, rt, prev_lbl):
    """Emit a curve's play() call, with an optional stacked corner label.

    The first *labeled* curve goes to the upper-right corner; each later label
    stacks under the previous EMITTED label (``prev_lbl``) — never ``lbl{i-1}``,
    which may not exist when an earlier curve was unlabeled (that produced a
    NameError at render time; audit C1). Returns the var name to use as the next
    curve's stacking anchor (unchanged when this curve has no label).
    """
    if want_label and label:
        lv = f"lbl{i}"
        L.append(f"        {lv} = Text({label!r}, font_size=22, color={color})")
        if prev_lbl is None:
            L.append(f"        {lv}.to_corner(UR, buff=0.4)")
        else:
            L.append(f"        {lv}.next_to({prev_lbl}, DOWN, buff=0.15, aligned_edge=LEFT)")
        L.append(f"        self.play({play}, FadeIn({lv}), run_time={rt:.1f})")
        return lv
    L.append(f"        self.play({play}, run_time={rt:.1f})")
    return prev_lbl


# Segmented sampler shared by funcgraph and calculus: it samples f over [x0, x1]
# and breaks the path at any non-finite or out-of-band point, so asymptotes render
# as gaps instead of off-screen spikes (a nan would otherwise void axes.plot).
_FG_PLOT_SRC = [
    "def _fg_plot(axes, f, x0, x1, dx, color, width, ymin, ymax, dashed=False):",
    "    # Sample f over [x0, x1]; split into continuous, finite, in-band runs so",
    "    # asymptotes and out-of-domain gaps render as breaks (a nan voids axes.plot).",
    "    grp = VGroup()",
    "    pts = []",
    "    n = int(round((x1 - x0) / dx)) + 1",
    "    for k in range(n):",
    "        xx = x0 + k * dx",
    "        try:",
    "            with np.errstate(all='ignore'):",
    "                yy = float(f(xx))",
    "        except Exception:",
    "            yy = float('nan')",
    "        if (not np.isfinite(yy)) or yy < ymin or yy > ymax:",
    "            if len(pts) >= 2:",
    "                m = VMobject(color=color, stroke_width=width)",
    "                m.set_points_as_corners([axes.c2p(px, py) for px, py in pts])",
    "                grp.add(DashedVMobject(m, num_dashes=max(8, len(pts) // 12)) if dashed else m)",
    "            pts = []",
    "        else:",
    "            pts.append((xx, yy))",
    "    if len(pts) >= 2:",
    "        m = VMobject(color=color, stroke_width=width)",
    "        m.set_points_as_corners([axes.c2p(px, py) for px, py in pts])",
    "        grp.add(DashedVMobject(m, num_dashes=max(8, len(pts) // 12)) if dashed else m)",
    "    return grp",
    "",
]


def build_funcgraph_source(
    curves=None,
    x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0,
    x_step=None, y_step=None,
    show_grid=False, cam_zoom=1.0,
    anim="Create",
    axis_label_x="x", axis_label_y="y", title="",
    plot_kind="function",
    param_curves=None, t_min=0.0, t_max=6.2832,
    tracer=None, velocity=None, t_markers=None,
    use_latex=False,
):
    if str(plot_kind) == "parametric":
        return _build_parametric_source(
            param_curves, x_min, x_max, y_min, y_max, x_step, y_step,
            show_grid, cam_zoom, anim, axis_label_x, axis_label_y, title,
            t_min, t_max, tracer, velocity, t_markers, use_latex,
        )
    # --- numeric ranges (sane + ordered) ---------------------------------
    xlo, xhi = float(x_min), float(x_max)
    if xlo >= xhi:
        xlo, xhi = -5.0, 5.0
    ylo, yhi = float(y_min), float(y_max)
    if ylo >= yhi:
        ylo, yhi = -4.0, 4.0
    xs = max(0.01, float(x_step) if x_step else (xhi - xlo) / 10.0)
    ys = max(0.01, float(y_step) if y_step else (yhi - ylo) / 8.0)
    dx = max(0.005, (xhi - xlo) / 400.0)
    yspan = yhi - ylo
    ymargin = max(2.0, 0.5 * yspan)
    ymin_break, ymax_break = ylo - ymargin, yhi + ymargin

    # --- curves (validate exprs, fill per-curve defaults) ----------------
    clean = []
    for i, c in enumerate(curves or []):
        c = c or {}
        raw = str(c.get("expr", "")).strip()
        if not raw:
            continue
        body  = _funcgraph_expr(raw, f"Curve {i + 1} f(x)")
        color = _text_color(c.get("color", "blue"))
        label = str(c.get("label", "")).strip()[:24]
        style = str(c.get("style", "solid")).strip().lower()
        width = max(0.5, float(c.get("width", 2.5) or 2.5))
        clean.append((body, color, label, style, width))
    if not clean:
        clean = [("x**2", "BLUE", "", "solid", 2.5)]

    # --- header + friendly-math namespace + safe segment-plot helper -----
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
        "",
    ]
    L += _FG_PLOT_SRC
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0 / zoom_f:.3f}",
            "",
        ]

    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
    ]
    _emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=False)

    # axis labels + title — Text(), never Tex, so the scene stays LaTeX-free
    intro = []
    xlab = str(axis_label_x or "").strip()[:24]
    ylab = str(axis_label_y or "").strip()[:24]
    ttl  = str(title or "").strip()[:48]
    if xlab:
        L.append(f"        x_axis_lbl = Text({xlab!r}, font_size=24, color=WHITE).next_to(axes.x_axis, RIGHT, buff=0.2)")
        intro.append("FadeIn(x_axis_lbl)")
    if ylab:
        L.append(f"        y_axis_lbl = Text({ylab!r}, font_size=24, color=WHITE).next_to(axes.y_axis.get_top(), RIGHT, buff=0.2)")
        intro.append("FadeIn(y_axis_lbl)")
    if ttl:
        L.append(f"        plot_title = Text({ttl!r}, font_size=30, color=WHITE).to_edge(UP, buff=0.3)")
        intro.append("FadeIn(plot_title)")
    if intro:
        L.append(f"        self.play({', '.join(intro)}, run_time=0.5)")

    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])

    prev_lbl = None  # stacking anchor: the previous emitted label (audit C1)
    for i, (body, color, label, style, width) in enumerate(clean):
        g, fn = f"g{i}", f"_f{i}"
        dashed = "True" if style == "dashed" else "False"
        L += [
            f"        def {fn}(x):",
            f"            return {body}",
            f"        {g} = _fg_plot(axes, {fn}, {xlo:.4f}, {xhi:.4f}, {dx:.4f}, "
            f"{color}, {width:.2f}, {ymin_break:.4f}, {ymax_break:.4f}, dashed={dashed})",
        ]
        play = wrap_tmpl.format(g=g)
        prev_lbl = _emit_curve_label(L, i, True, label, color, play, rt, prev_lbl)

    L.append("        self.wait(1.5)")
    return _join(L)


# ── Parametric curves (extends the funcgraph mode) ─────────────────────────
_PARAM_TRACER_DEFAULT   = {"on": False, "color": "yellow"}
_PARAM_VELOCITY_DEFAULT = {"on": False, "color": "green", "scale": 1.0}
_PARAM_MARKERS_DEFAULT  = {"on": False, "values": "", "color": "pink"}

_PARAM_PLOT_SRC = [
    "def _param_plot(axes, fx, fy, t0, t1, dt, color, width):",
    "    # t-driven twin of _fg_plot: sample t, compute (fx,fy), break the path on",
    "    # any non-finite coord so a divergent curve renders as a gap, not a crash.",
    "    grp = VGroup()",
    "    pts = []",
    "    n = int(round((t1 - t0) / dt)) + 1",
    "    for k in range(n):",
    "        tt = t0 + k * dt",
    "        try:",
    "            with np.errstate(all='ignore'):",
    "                xx = float(fx(tt)); yy = float(fy(tt))",
    "        except Exception:",
    "            xx = yy = float('nan')",
    "        if not (np.isfinite(xx) and np.isfinite(yy)):",
    "            if len(pts) >= 2:",
    "                m = VMobject(color=color, stroke_width=width)",
    "                m.set_points_as_corners([axes.c2p(px, py) for px, py in pts])",
    "                grp.add(m)",
    "            pts = []",
    "        else:",
    "            pts.append((xx, yy))",
    "    if len(pts) >= 2:",
    "        m = VMobject(color=color, stroke_width=width)",
    "        m.set_points_as_corners([axes.c2p(px, py) for px, py in pts])",
    "        grp.add(m)",
    "    return grp",
    "",
]


def _param_expr(expr, label, default):
    """Friendly-syntax translate (^ -> **) then validate against the blocklists."""
    return _validate_expr(str(expr or "").replace("^", "**"), label, default=default)


def _build_parametric_source(
    param_curves, x_min, x_max, y_min, y_max, x_step, y_step,
    show_grid, cam_zoom, anim, axis_label_x, axis_label_y, title,
    t_min, t_max, tracer, velocity, t_markers, use_latex,
):
    TR = {**_PARAM_TRACER_DEFAULT, **(tracer or {})}
    VE = {**_PARAM_VELOCITY_DEFAULT, **(velocity or {})}
    TM = {**_PARAM_MARKERS_DEFAULT, **(t_markers or {})}

    # --- axes ranges (same guards as funcgraph) --------------------------
    xlo, xhi = float(x_min), float(x_max)
    if xlo >= xhi:
        xlo, xhi = -5.0, 5.0
    ylo, yhi = float(y_min), float(y_max)
    if ylo >= yhi:
        ylo, yhi = -4.0, 4.0
    xs = max(0.01, float(x_step) if x_step else (xhi - xlo) / 10.0)
    ys = max(0.01, float(y_step) if y_step else (yhi - ylo) / 8.0)

    # --- t sampling range ------------------------------------------------
    t0, t1 = float(t_min), float(t_max)
    if t0 >= t1:
        t0, t1 = 0.0, 6.2832
    dt = max(0.005, (t1 - t0) / 400.0)
    zoom_f = float(cam_zoom or 1.0)

    # --- curves (validate x/y, fill defaults, cap at 3) ------------------
    clean = []
    for i, c in enumerate(param_curves or []):
        c = c or {}
        xr = str(c.get("x_expr", "")).strip()
        yr = str(c.get("y_expr", "")).strip()
        if not xr and not yr:
            continue
        xbody = _param_expr(xr or "cos(t)", f"Curve {i + 1} x(t)", "cos(t)")
        ybody = _param_expr(yr or "sin(t)", f"Curve {i + 1} y(t)", "sin(t)")
        color = _text_color(c.get("color", "blue"))
        label = str(c.get("label", "")).strip()[:24]
        clean.append((xbody, ybody, color, label))
        if len(clean) >= 3:
            break
    if not clean:
        clean = [("cos(t)", "sin(t)", "BLUE", "")]

    need_vel = bool(TR.get("on") and VE.get("on"))

    # --- header: namespace + helpers -------------------------------------
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
        "",
    ]
    L += _PARAM_PLOT_SRC
    if TR.get("on"):
        L += _TRACER_DOT_SRC
    if need_vel:
        L += _VEL_ARROW_SRC
    if TM.get("on"):
        L += _T_MARKER_SRC
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0 / zoom_f:.3f}",
            "",
        ]

    # --- scene -----------------------------------------------------------
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
    ]
    # Equal-aspect axis lengths so parametric shapes are geometrically faithful
    # (a data-circle renders round). scale = screen-units per data-unit, the
    # smaller of the two axis budgets (11 wide / 6 tall) so the plot still fits.
    _xspan, _yspan = xhi - xlo, yhi - ylo
    _scale = min(11.0 / _xspan, 6.0 / _yspan)
    # Floor each axis length so an extreme aspect ratio (e.g. a 1×100 window) can't
    # collapse an axis to an invisible sliver. Equal-aspect is preserved in normal
    # windows where both lengths already exceed the floor (audit C6).
    _plen_x = max(2.0, _scale * _xspan)
    _plen_y = max(2.0, _scale * _yspan)
    _emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=use_latex,
                         x_length=_plen_x, y_length=_plen_y,
                         grid_x_length=_plen_x, grid_y_length=_plen_y)

    # axis labels + title (Text — never Tex), identical idiom to funcgraph
    intro = []
    xlab = str(axis_label_x or "").strip()[:24]
    ylab = str(axis_label_y or "").strip()[:24]
    ttl = str(title or "").strip()[:48]
    if xlab:
        L.append(f"        x_axis_lbl = Text({xlab!r}, font_size=24, color=WHITE).next_to(axes.x_axis, RIGHT, buff=0.2)")
        intro.append("FadeIn(x_axis_lbl)")
    if ylab:
        L.append(f"        y_axis_lbl = Text({ylab!r}, font_size=24, color=WHITE).next_to(axes.y_axis.get_top(), RIGHT, buff=0.2)")
        intro.append("FadeIn(y_axis_lbl)")
    if ttl:
        L.append(f"        plot_title = Text({ttl!r}, font_size=30, color=WHITE).to_edge(UP, buff=0.3)")
        intro.append("FadeIn(plot_title)")
    if intro:
        L.append(f"        self.play({', '.join(intro)}, run_time=0.5)")

    # curves (1..3)
    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])
    prev_lbl = None  # stacking anchor: the previous emitted label (audit C1)
    for i, (xbody, ybody, color, label) in enumerate(clean):
        g = f"g{i}"
        L += [
            f"        def _p{i}_x(t):",
            f"            return {xbody}",
            f"        def _p{i}_y(t):",
            f"            return {ybody}",
            f"        {g} = _param_plot(axes, _p{i}_x, _p{i}_y, {t0:.4f}, {t1:.4f}, {dt:.4f}, {color}, 2.5)",
        ]
        play = wrap_tmpl.format(g=g)
        prev_lbl = _emit_curve_label(L, i, True, label, color, play, rt, prev_lbl)

    # extras (Tasks 3-4 add their emitters here)
    _emit_param_tracer_velocity(L, TR, VE, t0, t1)
    _emit_param_markers(L, TM)

    L.append("        self.wait(1.5)")
    return _join(L)


_VEL_ARROW_SRC = [
    "def _vel_arrow(axes, fx, fy, t, k, color):",
    "    # Central-difference velocity (x'(t), y'(t)); skip a degenerate (~0) vector.",
    "    h = 1e-3",
    "    try:",
    "        with np.errstate(all='ignore'):",
    "            vx = (fx(t + h) - fx(t - h)) / (2 * h)",
    "            vy = (fy(t + h) - fy(t - h)) / (2 * h)",
    "            x0 = float(fx(t)); y0 = float(fy(t))",
    "    except Exception:",
    "        return VGroup()",
    "    if not all(np.isfinite(v) for v in (vx, vy, x0, y0)):",
    "        return VGroup()",
    "    p = axes.c2p(x0, y0)",
    "    q = axes.c2p(x0 + vx * k, y0 + vy * k)",
    "    if np.linalg.norm(np.array(q) - np.array(p)) < 1e-3:",
    "        return VGroup()",
    "    return Arrow(p, q, buff=0, color=color, stroke_width=4)",
    "",
]

# Guarded tracer dot / t-marker: like _vel_arrow, evaluate the param fns inside a
# try/finiteness guard so a divergent curve (e.g. 1/t at t=0) yields an empty group
# instead of crashing always_redraw / FadeIn with ZeroDivisionError or c2p(inf) (audit C3).
_TRACER_DOT_SRC = [
    "def _tracer_dot(axes, fx, fy, t, radius, color):",
    "    try:",
    "        with np.errstate(all='ignore'):",
    "            x0 = float(fx(t)); y0 = float(fy(t))",
    "    except Exception:",
    "        return VGroup()",
    "    if not (np.isfinite(x0) and np.isfinite(y0)):",
    "        return VGroup()",
    "    return Dot(axes.c2p(x0, y0), radius=radius, color=color)",
    "",
]

_T_MARKER_SRC = [
    "def _t_marker(axes, fx, fy, t, color):",
    "    try:",
    "        with np.errstate(all='ignore'):",
    "            x0 = float(fx(t)); y0 = float(fy(t))",
    "    except Exception:",
    "        return VGroup()",
    "    if not (np.isfinite(x0) and np.isfinite(y0)):",
    "        return VGroup()",
    "    p = axes.c2p(x0, y0)",
    "    return VGroup(Dot(p, radius=0.07, color=color),",
    "                  Text('t=%g' % t, font_size=16, color=color).next_to(p, UR, buff=0.05))",
    "",
]


def _emit_param_tracer_velocity(L, TR, VE, t0, t1):
    # Tracer + velocity share ONE ValueTracker/sweep; velocity requires the tracer.
    if not TR.get("on"):
        return
    tcolor = _text_color(TR.get("color", "yellow"))
    L.append(f"        _tval = ValueTracker({t0:.4f})")
    L.append(
        f"        _dot = always_redraw(lambda: _tracer_dot(axes, _p0_x, _p0_y, "
        f"_tval.get_value(), 0.08, {tcolor}))"
    )
    L.append("        self.add(_dot)")
    if VE.get("on"):
        vcolor = _text_color(VE.get("color", "green"))
        scale = max(0.01, float(VE.get("scale", 1.0) or 1.0))
        k = 0.3 * scale
        L.append(
            f"        _vec = always_redraw(lambda: _vel_arrow(axes, _p0_x, _p0_y, "
            f"_tval.get_value(), {k:.4f}, {vcolor}))"
        )
        L.append("        self.add(_vec)")
    L.append(
        f"        self.play(_tval.animate.set_value({t1:.4f}), run_time=3.0, rate_func=linear)"
    )


def _parse_t_values(s):
    """Parse '0; 1.57; 3.14' (or newline-separated) into a capped list of floats."""
    out = []
    for chunk in str(s or "").replace("\n", ";").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(float(chunk))
        except ValueError:
            continue
        if len(out) >= 12:
            break
    return out


def _emit_param_markers(L, TM):
    if not TM.get("on"):
        return
    vals = _parse_t_values(TM.get("values", ""))
    if not vals:
        return
    color = _text_color(TM.get("color", "pink"))
    L.append("        _tm = VGroup()")
    for tv in vals:
        L.append(
            f"        _tm.add(_t_marker(axes, _p0_x, _p0_y, {tv:.5f}, {color}))"
        )
    L.append("        self.play(FadeIn(_tm), run_time=0.6)")


# ── Calculus Toolkit ──────────────────────────────────────────────────────
_CALC_RIEMANN_DEFAULT = {"on": True,  "method": "left", "n": 10,   "show_value": True}
_CALC_AREA_DEFAULT    = {"on": False, "mode": "under",  "color": "teal", "show_value": True}
_CALC_TANGENT_DEFAULT = {"on": False, "animate_secant": True, "show_slope": True}
_CALC_DERIV_DEFAULT   = {"on": False, "color": "red",  "show_legend": True}


def build_calculus_source(
    f_expr="x^2", g_expr="",
    a=-1.0, b=2.0, x0=1.0,
    riemann=None, area=None, tangent=None, derivative=None,
    x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0,
    x_step=None, y_step=None, show_grid=False, cam_zoom=1.0,
    axis_label_x="x", axis_label_y="y", title="",
    use_latex=False, anim="Create",
):
    R  = {**_CALC_RIEMANN_DEFAULT, **(riemann or {})}
    AR = {**_CALC_AREA_DEFAULT,    **(area or {})}
    TG = {**_CALC_TANGENT_DEFAULT, **(tangent or {})}
    DV = {**_CALC_DERIV_DEFAULT,   **(derivative or {})}

    # --- numeric guards --------------------------------------------------
    a, b = float(a), float(b)
    if a >= b:
        a, b = -1.0, 2.0
    n = max(2, min(200, int(R.get("n", 10) or 10)))
    xlo, xhi = float(x_min), float(x_max)
    if xlo >= xhi:
        xlo, xhi = -5.0, 5.0
    ylo, yhi = float(y_min), float(y_max)
    if ylo >= yhi:
        ylo, yhi = -4.0, 4.0
    x0 = max(a, min(b, float(x0)))   # clamp onto [a, b] where graph_f is drawn (audit C4)
    xs = max(0.01, float(x_step) if x_step else (xhi - xlo) / 10.0)
    ys = max(0.01, float(y_step) if y_step else (yhi - ylo) / 8.0)

    fbody = _funcgraph_expr(f_expr, "f(x)")
    gbody = _funcgraph_expr(g_expr, "g(x)") if str(g_expr or "").strip() else ""
    # graph_g is only used as the bounded_graph for area 'between'; don't draw it for
    # a bare g_expr or area 'under' (audit C7)
    need_g = bool(gbody and AR.get("on") and str(AR.get("mode", "under")).lower() == "between")

    # --- emit helpers ----------------------------------------------------
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
        "",
    ]
    L += _FG_PLOT_SRC   # segmented sampler for the visible curve (audit C2)
    ro = {"i": 0}  # readout chaining counter

    def mk(plain, latex):
        """Return the in-scene code that builds a Text (default) or MathTex label."""
        return latex if use_latex else plain

    def readout(code):
        """Emit a label mobject (code string) stacked in the upper-right corner."""
        i = ro["i"]; ro["i"] += 1
        nm = f"_ro{i}"
        L.append(f"        {nm} = {code}")
        if i == 0:
            L.append(f"        {nm}.to_corner(UR, buff=0.4)")
        else:
            L.append(f"        {nm}.next_to(_ro{i-1}, DOWN, buff=0.15, aligned_edge=RIGHT)")
        L.append(f"        self.play(FadeIn({nm}), run_time=0.4)")

    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L += [f"config.frame_width  = {14.222 / zoom_f:.3f}",
              f"config.frame_height = {8.0 / zoom_f:.3f}", ""]

    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        axes = Axes(",
        f"            x_range=[{xlo:.4f}, {xhi:.4f}, {xs:.4f}],",
        f"            y_range=[{ylo:.4f}, {yhi:.4f}, {ys:.4f}],",
        "            x_length=11, y_length=6,",
        "            axis_config=dict(color=GREY, include_tip=True),",
        "        )",
    ]
    if show_grid:
        L += [
            "        grid = NumberPlane(",
            f"            x_range=[{xlo:.4f}, {xhi:.4f}],",
            f"            y_range=[{ylo:.4f}, {yhi:.4f}],",
            "            background_line_style=dict(stroke_color=BLUE_E, stroke_opacity=0.25),",
            "        )",
            "        self.play(FadeIn(grid), run_time=0.6)",
        ]
    L.append("        self.play(Create(axes), run_time=0.8)")

    # axis labels + title — Text(), never Tex, so the scene stays LaTeX-free
    intro = []
    xlab = str(axis_label_x or "").strip()[:24]
    ylab = str(axis_label_y or "").strip()[:24]
    ttl  = str(title or "").strip()[:48]
    if xlab:
        L.append(f"        x_axis_lbl = Text({xlab!r}, font_size=24, color=WHITE).next_to(axes.x_axis, RIGHT, buff=0.2)")
        intro.append("FadeIn(x_axis_lbl)")
    if ylab:
        L.append(f"        y_axis_lbl = Text({ylab!r}, font_size=24, color=WHITE).next_to(axes.y_axis.get_top(), RIGHT, buff=0.2)")
        intro.append("FadeIn(y_axis_lbl)")
    if ttl:
        L.append(f"        plot_title = Text({ttl!r}, font_size=30, color=WHITE).to_edge(UP, buff=0.3)")
        intro.append("FadeIn(plot_title)")
    if intro:
        L.append(f"        self.play({', '.join(intro)}, run_time=0.5)")

    # define analysis functions
    L += ["        def _f(x):", f"            return {fbody}"]
    if gbody:
        L += ["        def _g(x):", f"            return {gbody}"]

    # finiteness + in-band pre-check over [a, b]; _ok gates the area-style overlays
    # so a divergent f (pole inside [a, b]) suppresses spiking Riemann/area/derivative
    # overlays instead of rendering garbage (audit C2).
    yband = max(abs(ylo), abs(yhi))
    L += [
        f"        _xs = np.linspace({a:.4f}, {b:.4f}, 200)",
        f"        _yband = {yband:.4f}",
        "        _bad = 0",
        "        for _xx in _xs:",
        "            try:",
        "                with np.errstate(all='ignore'):",
        "                    _yy = float(_f(_xx))",
        "                if (not np.isfinite(_yy)) or abs(_yy) > _yband: _bad += 1",
        "            except Exception:",
        "                _bad += 1",
        "        _ok = (_bad == 0)",
        "        if not _ok:",
        "            self.play(FadeIn(Text('⚠ f(x) not finite / out of view on [a, b]', "
        "font_size=22, color=YELLOW).to_edge(DOWN)))",
    ]

    # Analysis graph (graph_f) is the real axes.plot object the overlays read from;
    # it is created but NOT shown. The VISIBLE curve is drawn with the segmented
    # sampler so it gaps at asymptotes instead of spiking off-screen (audit C2).
    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])
    dxc = max(0.002, (b - a) / 400.0)
    ymargin = max(2.0, 0.5 * (yhi - ylo))
    ymin_break, ymax_break = ylo - ymargin, yhi + ymargin
    L += [
        f"        graph_f = axes.plot(_f, x_range=[{a:.4f}, {b:.4f}], color=BLUE)",
        f"        _curve = _fg_plot(axes, _f, {a:.4f}, {b:.4f}, {dxc:.4f}, BLUE, 2.5, "
        f"{ymin_break:.4f}, {ymax_break:.4f})",
        f"        self.play({wrap_tmpl.format(g='_curve')}, run_time={rt:.1f})",
    ]
    if need_g:
        L += [
            f"        graph_g = axes.plot(_g, x_range=[{a:.4f}, {b:.4f}], color=GREY)",
            f"        _curve_g = _fg_plot(axes, _g, {a:.4f}, {b:.4f}, {dxc:.4f}, GREY, 2.5, "
            f"{ymin_break:.4f}, {ymax_break:.4f})",
            "        self.play(Create(_curve_g), run_time=0.6)",
        ]

    # ===== overlays go here (Tasks 2-5) =====
    _emit_riemann(L, R, a, b, n, mk, readout)        # Task 2
    _emit_area(L, AR, a, b, gbody, mk, readout)      # Task 3
    _emit_tangent(L, TG, x0, a, b, mk, readout)      # Task 4
    _emit_derivative(L, DV, mk, readout)             # Task 5

    L.append("        self.wait(1.5)")
    return _join(L)


# Overlay emitters — filled in by Tasks 2-5; no-ops until then.
def _emit_riemann(L, R, a, b, n, mk, readout):
    if not R.get("on"):
        return
    method = str(R.get("method", "left")).lower()
    if method == "trapezoid":
        L += [
            f"        _dx = ({b:.4f} - {a:.4f}) / {n}",
            "        _traps = VGroup()",
            f"        for _k in range({n}):",
            f"            _xa = {a:.4f} + _k * _dx",
            "            _xb = _xa + _dx",
            "            try:",
            "                with np.errstate(all='ignore'):",
            "                    _ya = float(_f(_xa)); _yb = float(_f(_xb))",
            "            except Exception:",
            "                continue",
            "            if not (np.isfinite(_ya) and np.isfinite(_yb)):",
            "                continue",
            "            _traps.add(Polygon(",
            "                axes.c2p(_xa, 0), axes.c2p(_xa, _ya),",
            "                axes.c2p(_xb, _yb), axes.c2p(_xb, 0),",
            "                stroke_width=1, stroke_color=WHITE,",
            "                fill_color=BLUE, fill_opacity=0.6))",
            "        if _ok:",
            "            self.play(FadeIn(_traps), run_time=1.0)",
        ]
    else:
        ist = {"left": "left", "right": "right", "mid": "center"}.get(method, "left")
        L += [
            "        _rects = axes.get_riemann_rectangles(",
            f"            graph_f, x_range=[{a:.4f}, {b:.4f}], dx=({b:.4f}-{a:.4f})/{n},",
            f"            input_sample_type={ist!r}, show_signed_area=True,",
            "            color=(BLUE, GREEN), stroke_width=0.5, stroke_color=WHITE, fill_opacity=0.7)",
            "        if _ok:",
            "            self.play(FadeIn(_rects), run_time=1.0)",
        ]
    if R.get("show_value"):
        # numeric Riemann sum in-scene (sample per method; trapezoid uses the rule)
        if method == "right":
            samp = f"_f({a:.4f} + (_k + 1) * _dxv)"
        elif method == "mid":
            samp = f"_f({a:.4f} + (_k + 0.5) * _dxv)"
        else:  # left (and a safe default)
            samp = f"_f({a:.4f} + _k * _dxv)"
        L += [
            f"        _dxv = ({b:.4f} - {a:.4f}) / {n}",
            "        try:",
            "            with np.errstate(all='ignore'):",
        ]
        if method == "trapezoid":
            L += [
                f"                _sig = float(_dxv * (0.5 * _f({a:.4f}) + 0.5 * _f({b:.4f}) "
                f"+ sum(_f({a:.4f} + _k * _dxv) for _k in range(1, {n}))))",
            ]
        else:
            L += [f"                _sig = float(sum({samp} for _k in range({n})) * _dxv)"]
        L += [
            "        except Exception:",
            "            _sig = float('nan')",
            "        _sigs = f'{_sig:.3f}' if np.isfinite(_sig) else '—'",
            "        _sigt = f'{_sig:.3f}' if np.isfinite(_sig) else r'\\text{n/a}'",
        ]
        readout(mk(
            "Text('Σ ≈ ' + _sigs, font_size=22, color=WHITE)",
            "MathTex(r'\\sum \\approx ' + _sigt, font_size=30, color=WHITE)",
        ))
def _emit_area(L, AR, a, b, gbody, mk, readout):
    if not AR.get("on"):
        return
    mode = str(AR.get("mode", "under")).lower()
    if mode == "between" and not gbody:
        mode = "under"
    color = _text_color(AR.get("color", "teal"))
    if mode == "between":
        L += [
            f"        _area = axes.get_area(graph_f, x_range=[{a:.4f}, {b:.4f}], "
            f"color={color}, opacity=0.5, bounded_graph=graph_g)",
        ]
    else:
        L += [
            f"        _area = axes.get_area(graph_f, x_range=[{a:.4f}, {b:.4f}], "
            f"color={color}, opacity=0.5)",
        ]
    L += ["        if _ok:",
          "            self.play(FadeIn(_area), run_time=1.0)"]
    if AR.get("show_value"):
        # trapezoidal numeric integral of f (minus g for 'between') over [a, b]
        integrand = "(_f(_tt) - _g(_tt))" if mode == "between" else "_f(_tt)"
        L += [
            f"        _ts = np.linspace({a:.4f}, {b:.4f}, 200)",
            "        try:",
            "            with np.errstate(all='ignore'):",
            f"                _vals = np.array([{integrand} for _tt in _ts], dtype=float)",
            "                _ar = float(np.trapezoid(_vals, _ts))",
            "        except Exception:",
            "            _ar = float('nan')",
            "        _ars = f'{_ar:.3f}' if np.isfinite(_ar) else '—'",
            "        _art = f'{_ar:.3f}' if np.isfinite(_ar) else r'\\text{n/a}'",
        ]
        readout(mk(
            "Text('Area ≈ ' + _ars, font_size=22, color=WHITE)",
            "MathTex(r'\\int_a^b f\\,dx \\approx ' + _art, font_size=30, color=WHITE)",
        ))
def _emit_tangent(L, TG, x0, a, b, mk, readout):
    if not TG.get("on"):
        return
    # numeric central-difference slope at x0
    L += [
        f"        _x0 = {x0:.4f}; _h = 1e-4",
        "        try:",
        "            with np.errstate(all='ignore'):",
        "                _slope = float((_f(_x0 + _h) - _f(_x0 - _h)) / (2 * _h))",
        "        except Exception:",
        "            _slope = float('nan')",
    ]
    if TG.get("animate_secant"):
        # start the secant wide but within [a, b] so x0+dx samples the drawn graph
        # (was a fixed 2.0 that sat off the interval until convergence) — audit C5
        _dx0 = max(0.1, min(b - x0, x0 - a))
        L += [
            f"        _dxt = ValueTracker({_dx0:.4f})",
            "        def _secant():",
            "            return axes.get_secant_slope_group(",
            "                _x0, graph_f, dx=max(1e-3, _dxt.get_value()),",
            "                dx_line_color=YELLOW, dy_line_color=YELLOW,",
            "                secant_line_color=GREEN, secant_line_length=8)",
            "        _sec = always_redraw(_secant)",
            "        self.add(_sec)",
            "        self.play(_dxt.animate.set_value(0.05), run_time=2.0)",
            "        self.wait(0.3)",
            "        # converge to the exact tangent line at x0 (persists)",
            "        if np.isfinite(_slope):",
            "            _sec.clear_updaters()",
            "            self.remove(_sec)",
            "            _tan = axes.plot(lambda x: _f(_x0) + _slope * (x - _x0), color=GREEN)",
            "            self.play(Create(_tan), run_time=0.6)",
            "            self.wait(0.2)",
        ]
    else:
        # static tangent: a clean line through (x0, f(x0)) with the numeric slope
        L += [
            "        if np.isfinite(_slope):",
            "            _tan = axes.plot(lambda x: _f(_x0) + _slope * (x - _x0), color=GREEN)",
            "            self.play(Create(_tan), run_time=1.0)",
        ]
    if TG.get("show_slope"):
        L += [
            "        _sls = f'{_slope:.3f}' if np.isfinite(_slope) else '—'",
            "        _slt = f'{_slope:.3f}' if np.isfinite(_slope) else r'\\text{n/a}'",
        ]
        readout(mk(
            "Text('slope = ' + _sls, font_size=22, color=GREEN)",
            "MathTex(r\"f'(x_0) = \" + _slt, font_size=30, color=GREEN)",
        ))
def _emit_derivative(L, DV, mk, readout):
    if not DV.get("on"):
        return
    color = _text_color(DV.get("color", "red"))
    L += [
        f"        _deriv = axes.plot_derivative_graph(graph_f, color={color})",
        "        if _ok:",
        "            self.play(Create(_deriv), run_time=1.0)",
    ]
    if DV.get("show_legend"):
        readout(mk(
            f"Text(\"f'(x)\", font_size=22, color={color})",
            f"MathTex(r\"f'(x)\", font_size=30, color={color})",
        ))


# ── Polar Plane ────────────────────────────────────────────────────────────
_DEG2RAD = 3.141592653589793 / 180.0
_POLAR_LABEL_DEGS = (0, 45, 90, 135, 180, 225, 270, 315)
_POLAR_POINTS_DEFAULT = {"on": False, "coords": "",  "color": "yellow"}
_POLAR_SECTOR_DEFAULT = {"on": False, "start_deg": 0.0, "end_deg": 90.0, "color": "teal"}
_POLAR_RADIAL_DEFAULT = {"on": False, "angle_deg": 30.0, "color": "red"}


def _polar_expr(expr, label):
    """Friendly-syntax translate (^ -> **) then validate; default cardioid."""
    return _validate_expr(str(expr or "").replace("^", "**"), label, default="1 + cos(theta)")


def _parse_polar_points(s):
    """Parse 'r,deg; r,deg' text into a capped list of (r, deg) float pairs."""
    out = []
    for chunk in str(s or "").replace("\n", ";").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split(",")
        if len(parts) != 2:
            continue
        try:
            out.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
        if len(out) >= 12:
            break
    return out


def build_polar_source(
    curves,
    radius_max=4.0, radius_step=1.0, azimuth_divisions=12, size=6.0,
    theta_min=0.0, theta_max=6.2832, show_curve_labels=True,
    points=None, sector=None, radial_line=None,
    cam_zoom=1.0, title="",
    use_latex=False, anim="Create",
):
    P  = {**_POLAR_POINTS_DEFAULT, **(points or {})}
    S  = {**_POLAR_SECTOR_DEFAULT, **(sector or {})}
    RL = {**_POLAR_RADIAL_DEFAULT, **(radial_line or {})}

    # --- numeric guards --------------------------------------------------
    rmax  = float(radius_max)  if float(radius_max)  > 0 else 4.0
    rstep = float(radius_step) if float(radius_step) > 0 else 1.0
    adiv  = max(2, min(48, int(azimuth_divisions or 12)))
    sz    = float(size) if float(size) > 0 else 6.0
    t0, t1 = float(theta_min), float(theta_max)
    if t0 >= t1:
        t0, t1 = 0.0, 6.2832
    dt = max(0.005, (t1 - t0) / 400.0)
    zoom_f = float(cam_zoom or 1.0)

    # --- curves (validate, fill defaults, cap at 3) ----------------------
    clean = []
    for i, c in enumerate(curves or []):
        c = c or {}
        raw = str(c.get("expr", "")).strip()
        if not raw:
            continue
        body  = _polar_expr(raw, f"Curve {i + 1} r(theta)")
        color = _text_color(c.get("color", "blue"))
        label = str(c.get("label", "")).strip()[:24]
        clean.append((body, color, label))
        if len(clean) >= 3:
            break
    if not clean:
        clean = [("1 + cos(theta)", "BLUE", "")]

    # --- header + namespace + robust polar-plot helper -------------------
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
        "",
        "def _polar_plot(plane, r_func, t0, t1, dt, color, width):",
        "    # Sample theta over [t0, t1]; break the path on non-finite r so a",
        "    # divergent r renders as a gap (mirrors funcgraph's _fg_plot).",
        "    grp = VGroup()",
        "    pts = []",
        "    n = int(round((t1 - t0) / dt)) + 1",
        "    for k in range(n):",
        "        th = t0 + k * dt",
        "        try:",
        "            with np.errstate(all='ignore'):",
        "                rr = float(r_func(th))",
        "        except Exception:",
        "            rr = float('nan')",
        "        if not np.isfinite(rr):",
        "            if len(pts) >= 2:",
        "                m = VMobject(color=color, stroke_width=width)",
        "                m.set_points_as_corners(pts)",
        "                grp.add(m)",
        "            pts = []",
        "        else:",
        "            pts.append(plane.polar_to_point(rr, th))",
        "    if len(pts) >= 2:",
        "        m = VMobject(color=color, stroke_width=width)",
        "        m.set_points_as_corners(pts)",
        "        grp.add(m)",
        "    return grp",
        "",
    ]
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0 / zoom_f:.3f}",
            "",
        ]

    # --- scene: PolarPlane ----------------------------------------------
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        plane = PolarPlane(",
        f"            size={sz:.4f}, radius_max={rmax:.4f}, radius_step={rstep:.4f},",
        f"            azimuth_step={adiv}, azimuth_units='PI radians',",
        "            radius_config={'stroke_color': GREY, 'font_size': 28},",
        "        )",
    ]
    # labels: add_coordinates (MathTex) under use_latex, else manual Text degrees
    if use_latex:
        L.append("        plane.add_coordinates()")
    L.append("        self.play(Create(plane), run_time=0.9)")
    if not use_latex:
        L.append("        _lbls = VGroup()")
        for d in _POLAR_LABEL_DEGS:
            rad = d * _DEG2RAD
            L.append(
                f"        _lbls.add(Text('{d}°', font_size=20, color=GREY_B)"
                f".move_to(plane.polar_to_point({rmax * 1.08:.4f}, {rad:.4f})))"
            )
        L.append("        self.play(FadeIn(_lbls), run_time=0.5)")

    # optional title (Text — LaTeX-free)
    ttl = str(title or "").strip()[:48]
    if ttl:
        L.append(f"        _title = Text({ttl!r}, font_size=30, color=WHITE).to_edge(UP, buff=0.3)")
        L.append("        self.play(FadeIn(_title), run_time=0.4)")

    # --- curves (1..3) ---------------------------------------------------
    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])
    prev_lbl = None  # stacking anchor: the previous emitted label (audit C1)
    for i, (body, color, label) in enumerate(clean):
        g, fn = f"g{i}", f"_r{i}"
        L += [
            f"        def {fn}(theta):",
            f"            return {body}",
            f"        {g} = _polar_plot(plane, {fn}, {t0:.4f}, {t1:.4f}, {dt:.4f}, {color}, 3.0)",
        ]
        play = wrap_tmpl.format(g=g)
        prev_lbl = _emit_curve_label(L, i, show_curve_labels, label, color, play, rt, prev_lbl)

    # --- extras (Tasks 2-4) ----------------------------------------------
    _emit_polar_points(L, P)          # Task 2
    _emit_polar_sector(L, S, rmax)    # Task 3
    _emit_polar_radial(L, RL, rmax)   # Task 4

    L.append("        self.wait(1.5)")
    return _join(L)


# Overlay emitters — each appends its geometry to L only when its dict's "on" is set.
def _emit_polar_points(L, P):
    if not P.get("on"):
        return
    pts = _parse_polar_points(P.get("coords", ""))
    if not pts:
        return
    color = _text_color(P.get("color", "yellow"))
    L.append("        _pts = VGroup()")
    for (r, d) in pts:
        rad = d * _DEG2RAD
        L.append(
            f"        _pts.add(Dot(plane.polar_to_point({r:.4f}, {rad:.5f}), "
            f"radius=0.07, color={color}))"
        )
        L.append(
            f"        _pts.add(Text('({r:g}, {d:g}°)', font_size=16, color={color})"
            f".next_to(plane.polar_to_point({r:.4f}, {rad:.5f}), UR, buff=0.05))"
        )
    L.append("        self.play(FadeIn(_pts), run_time=0.6)")


def _emit_polar_sector(L, S, rmax):
    if not S.get("on"):
        return
    color = _text_color(S.get("color", "teal"))
    a0 = float(S.get("start_deg", 0.0)) * _DEG2RAD
    a1 = float(S.get("end_deg", 90.0)) * _DEG2RAD
    if a0 == a1:
        return                 # zero-width sector -> draw nothing (audit C8)
    if a1 < a0:
        a0, a1 = a1, a0
    L += [
        f"        _arc_ts = np.linspace({a0:.5f}, {a1:.5f}, 60)",
        f"        _wedge_pts = [plane.polar_to_point(0, {a0:.5f})] + "
        f"[plane.polar_to_point({rmax:.4f}, _a) for _a in _arc_ts]",
        f"        _wedge = Polygon(*_wedge_pts, stroke_width=2, stroke_color={color}, "
        f"fill_color={color}, fill_opacity=0.35)",
        "        self.play(FadeIn(_wedge), run_time=0.8)",
    ]


def _emit_polar_radial(L, RL, rmax):
    if not RL.get("on"):
        return
    color = _text_color(RL.get("color", "red"))
    rad = float(RL.get("angle_deg", 30.0)) * _DEG2RAD
    L += [
        f"        _radial = Line(plane.polar_to_point(0, {rad:.5f}), "
        f"plane.polar_to_point({rmax:.4f}, {rad:.5f}), color={color}, stroke_width=4)",
        "        self.play(Create(_radial), run_time=0.6)",
    ]


# ====================================================================
#  Tables & Matrices  (mode "table")  — Table/Matrix toggle via `kind`
# ====================================================================

_TABLE_ANIMS = {
    "Create": ("Create", 1.5),
    "Write":  ("Write",  2.0),
    "FadeIn": ("FadeIn", 1.0),
}
_BRACKETS = {"[]": ("[", "]"), "()": ("(", ")"), "{}": (r"\{", r"\}")}
_TABLE_SAMPLE = [["1", "2"], ["3", "4"]]


def _parse_grid(s, max_r=8, max_c=8):
    """CSV-ish text -> padded list[list[str]], capped max_r x max_c.

    Rows split on newlines; cells split on '|' if the row contains one, else
    on ','. Whitespace stripped. Ragged rows padded with '' to the widest
    (capped) column. Empty input -> []."""
    rows = []
    for line in str(s or "").splitlines():
        line = line.strip()
        if not line:
            continue
        sep = "|" if "|" in line else ","
        cells = [c.strip() for c in line.split(sep)]
        rows.append(cells[:max_c])
        if len(rows) >= max_r:
            break
    if not rows:
        return []
    width = min(max_c, max(len(r) for r in rows))
    return [r[:width] + [""] * (width - len(r)) for r in rows]


def _matrix_literal(grid):
    """2D string grid -> Python list literal source, e.g. [['1', '2'], ...]."""
    return "[" + ", ".join(
        "[" + ", ".join(repr(c) for c in row) + "]" for row in grid
    ) + "]"


def build_table_source(
    kind="table",
    data="", title="", anim="Create", cam_zoom=1.0,
    # ---- table-only ----
    row_labels="", col_labels="", use_latex=False, include_outer_lines=True,
    highlights=None,
    # ---- matrix-only ----
    bracket="[]", operation="none", scalar=2.0, data2="", mhighlight=None,
):
    grid = _parse_grid(data) or [row[:] for row in _TABLE_SAMPLE]
    if str(kind) == "matrix":
        return _build_matrix_kind(grid, bracket, operation, scalar, data2,
                                  mhighlight, title, anim, cam_zoom)
    return _build_table_kind(grid, row_labels, col_labels, use_latex,
                             include_outer_lines, highlights, title, anim, cam_zoom)


def _build_table_kind(grid, row_labels, col_labels, use_latex,
                      include_outer_lines, highlights, title, anim, cam_zoom):
    cls    = "MathTable" if use_latex else "Table"
    lblcls = "MathTex"   if use_latex else "Text"
    rl = [x.strip() for x in str(row_labels or "").split(",") if x.strip()]
    cl = [x.strip() for x in str(col_labels or "").split(",") if x.strip()]

    args = [_matrix_literal(grid)]
    if rl:
        args.append("row_labels=[" + ", ".join(f"{lblcls}({x!r})" for x in rl) + "]")
    if cl:
        args.append("col_labels=[" + ", ".join(f"{lblcls}({x!r})" for x in cl) + "]")
    if include_outer_lines:
        args.append("include_outer_lines=True")

    L = ["from manim import *", "", "", "class ManimScene(Scene):",
         "    def construct(self):"]
    L.append(f"        t = {cls}(" + ", ".join(args) + ")")

    # highlights — 1-based, label-aware. Skip out-of-range (never crash).
    n_rows = len(grid) + (1 if cl else 0)
    n_cols = len(grid[0]) + (1 if rl else 0)
    for h in (highlights or []):
        h = h or {}
        try:
            r = int(h.get("row")); c = int(h.get("col"))
        except (TypeError, ValueError):
            continue
        if not (1 <= r <= n_rows and 1 <= c <= n_cols):
            continue
        color = _text_color(h.get("color", "yellow"))
        L.append(f"        t.add_highlighted_cell(({r}, {c}), color={color})")

    if str(title or "").strip():
        ttl = str(title).strip()[:48]
        L.append(f"        _title = Text({ttl!r}, font_size=32, color=WHITE)")
        L.append("        grp = VGroup(_title, t).arrange(DOWN, buff=0.4)")
    else:
        L.append("        grp = VGroup(t)")
    L.append("        grp.scale(min(1.0, 6.5 / max(grp.width, 1e-6), 7.0 / max(grp.height, 1e-6)))")
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L.append(f"        grp.scale({zoom_f:.3f})")
    intro, rt = _TABLE_ANIMS.get(str(anim), _TABLE_ANIMS["Create"])
    L.append(f"        self.play({intro}(grp), run_time={rt})")
    L.append("        self.wait(1.5)")
    return _join(L)


def _build_matrix_kind(grid, bracket, operation, scalar, data2, mhighlight,
                       title, anim, cam_zoom):
    lb, rb = _BRACKETS.get(str(bracket), _BRACKETS["[]"])
    op = str(operation or "none")
    zoom_f = float(cam_zoom or 1.0)
    L = ["from manim import *", ""]
    if abs(zoom_f - 1.0) > 0.02:
        L += [f"config.frame_width  = {14.222 / zoom_f:.3f}",
              f"config.frame_height = {8.0 / zoom_f:.3f}", ""]
    L += ["", "class ManimScene(Scene):", "    def construct(self):"]
    if str(title or "").strip():
        ttl = str(title).strip()[:48]
        L.append(f"        _title = Text({ttl!r}, font_size=32, color=WHITE).to_edge(UP, buff=0.4)")
        L.append("        self.play(FadeIn(_title), run_time=0.4)")
    intro, rt = _TABLE_ANIMS.get(str(anim), _TABLE_ANIMS["Create"])

    if op == "scalar":
        _emit_scalar_mul(L, grid, lb, rb, scalar, intro, rt)
    elif op == "add":
        _emit_matrix_add(L, grid, data2, lb, rb, intro, rt)
    elif op == "transpose":
        _emit_transpose(L, grid, lb, rb, intro, rt)
    elif op == "determinant":
        _emit_determinant(L, grid, lb, rb, intro, rt)
    else:
        _emit_matrix_static(L, grid, lb, rb, mhighlight, intro, rt)

    L.append("        self.wait(1.5)")
    return _join(L)


def _fmt_num(v):
    """Float -> compact string: integral values lose the decimal point."""
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:.4g}"


def _grid_to_floats(grid, label):
    """2D string grid -> list[list[float]]; raise ValueError on any non-number."""
    out = []
    for row in grid:
        frow = []
        for c in row:
            try:
                v = float(c)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{label} requires numeric entries; got {c!r}.")
            if not math.isfinite(v):
                raise ValueError(
                    f"{label} requires numeric entries; got {c!r}.")
            frow.append(v)
        out.append(frow)
    return out


def _emit_scalar_mul(L, grid, lb, rb, scalar, intro, rt):
    nums = _grid_to_floats(grid, "Scalar multiply")
    k = float(scalar)
    src_grid = [[_fmt_num(v) for v in row] for row in nums]
    res_grid = [[_fmt_num(k * v) for v in row] for row in nums]
    L.append(f"        m = Matrix({_matrix_literal(src_grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        _k = MathTex(r'{_fmt_num(k)} \\cdot')")
    L.append("        _row = VGroup(_k, m).arrange(RIGHT, buff=0.25)")
    L.append("        _sf = min(1.0, 11.5 / _row.width, 5.5 / _row.height)")
    L.append("        _row.scale(_sf)")
    L.append(f"        self.play({intro}(_row), run_time={rt})")
    L.append("        self.wait(0.5)")
    L.append(f"        res = Matrix({_matrix_literal(res_grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        res.scale(_sf)")
    L.append("        res.move_to(m)")
    L.append("        self.play(FadeOut(_k), Transform(m, res), run_time=1.2)")


def _emit_matrix_add(L, grid, data2, lb, rb, intro, rt):
    A = _grid_to_floats(grid, "Matrix addition (A)")
    gridB = _parse_grid(data2)
    if not gridB:
        raise ValueError("Matrix addition needs a second matrix (B).")
    B = _grid_to_floats(gridB, "Matrix addition (B)")
    if len(A) != len(B) or any(len(ra) != len(rb_) for ra, rb_ in zip(A, B)):
        raise ValueError(
            "Matrix addition requires both matrices to have the same shape.")
    aS = [[_fmt_num(v) for v in row] for row in A]
    bS = [[_fmt_num(v) for v in row] for row in B]
    C  = [[_fmt_num(a + b) for a, b in zip(ra, rb_)] for ra, rb_ in zip(A, B)]
    L.append(f"        mA = Matrix({_matrix_literal(aS)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        mB = Matrix({_matrix_literal(bS)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _plus = MathTex('+')")
    L.append("        _eq = MathTex('=')")
    L.append(f"        mC = Matrix({_matrix_literal(C)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _row = VGroup(mA, _plus, mB, _eq, mC).arrange(RIGHT, buff=0.3)")
    L.append("        _row.scale(min(1.0, 11.5 / _row.width, 5.5 / _row.height))")
    L.append(f"        self.play({intro}(mA), {intro}(mB), FadeIn(_plus), run_time={rt})")
    L.append("        self.play(Write(_eq), FadeIn(mC), run_time=1.0)")


def _emit_transpose(L, grid, lb, rb, intro, rt):
    T = [list(col) for col in zip(*grid)]   # grid is rectangular (padded)
    L.append(f"        m = Matrix({_matrix_literal(grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _sf = min(1.0, 11.5 / m.width, 5.5 / m.height)")
    L.append("        m.scale(_sf)")
    L.append(f"        self.play({intro}(m), run_time={rt})")
    L.append("        self.wait(0.4)")
    L.append(f"        mT = Matrix({_matrix_literal(T)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        mT.scale(_sf)")
    L.append("        mT.move_to(m)")
    L.append("        _lbl = MathTex('A^T').next_to(mT, UP, buff=0.3)")
    L.append("        self.play(Transform(m, mT), FadeIn(_lbl), run_time=1.2)")


def _det(m):
    """Determinant of a 2x2 or 3x3 numeric matrix."""
    if len(m) == 2:
        return m[0][0] * m[1][1] - m[0][1] * m[1][0]
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _emit_determinant(L, grid, lb, rb, intro, rt):
    n = len(grid)
    if n not in (2, 3) or any(len(r) != n for r in grid):
        raise ValueError("Determinant requires a square 2x2 or 3x3 matrix.")
    M = _grid_to_floats(grid, "Determinant")
    dstr = _fmt_num(_det(M))
    L.append(f"        m = Matrix({_matrix_literal(grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _sf = min(1.0, 11.5 / m.width, 5.5 / m.height)")
    L.append("        m.scale(_sf)")
    L.append(f"        self.play({intro}(m), run_time={rt})")
    L.append(f"        _det = MathTex(r'\\det(A) = {dstr}', font_size=44)")
    L.append("        _det.next_to(m, DOWN, buff=0.5)")
    L.append("        self.play(Write(_det), run_time=1.0)")


def _emit_matrix_static(L, grid, lb, rb, mhighlight, intro, rt):
    L.append(f"        m = Matrix({_matrix_literal(grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _sf = min(1.0, 11.5 / m.width, 5.5 / m.height)")
    L.append("        m.scale(_sf)")
    L.append(f"        self.play({intro}(m), run_time={rt})")
    H = mhighlight or {}
    if not H.get("on"):
        return
    target = str(H.get("target", "row"))
    try:
        idx = int(H.get("index", 1))
    except (TypeError, ValueError):
        return
    color = _text_color(H.get("color", "yellow"))
    n_rows, n_cols = len(grid), len(grid[0])
    if target == "row" and 1 <= idx <= n_rows:
        sel = f"m.get_rows()[{idx - 1}]"
    elif target == "col" and 1 <= idx <= n_cols:
        sel = f"m.get_columns()[{idx - 1}]"
    elif target == "entry" and 1 <= idx <= n_rows * n_cols:
        sel = f"m.get_entries()[{idx - 1}]"
    else:
        return
    L.append(f"        _sel = {sel}")
    L.append(f"        self.play(Indicate(_sel, color={color}), run_time=0.8)")
