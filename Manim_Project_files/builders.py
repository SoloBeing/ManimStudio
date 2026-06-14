import ast as _ast
from renderer import _BLOCKED_CALLS, _BLOCKED_ATTRS

def _join(lines):
    return "\n".join(lines) + "\n"


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
        fn = (custom_fn or "z**2").strip()
        try:
            tree = _ast.parse(fn, mode="eval")
        except SyntaxError as e:
            raise ValueError(
                f"Custom f(z) expression has invalid syntax: {e.msg} "
                f"(use Python syntax, e.g. z**2, cmath.sin(z))"
            ) from None
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Call):
                if isinstance(node.func, _ast.Name) and node.func.id in _BLOCKED_CALLS:
                    raise ValueError(f"Call not allowed in f(z): {node.func.id}()")
            elif isinstance(node, _ast.Attribute):
                if node.attr in _BLOCKED_ATTRS:
                    raise ValueError(f"Attribute not allowed in f(z): .{node.attr}")
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
    "green_gold": "GREEN_E, GREEN, YELLOW_GREEN, GOLD, YELLOW",
}


def build_streamlines_source(
    mode, scale, spacing, flow_speed, virtual_time, stroke_width_sl, show_axes, animate,
    color_scheme="default", cam_zoom=1.0,
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
    }
    title, expr, subtitle = field_map[mode]
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
        f"            return {expr}",
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
        "            opacity=0.9,",
        "        )",
    ]

    if animate:
        L += [
            "        self.add(stream_lines)",
            "        stream_lines.start_animation(",
            "            warm_up=False,",
            f"            flow_speed={flow_speed:.2f},",
            "            time_width=0.45,",
            "        )",
            "        self.wait(4)",
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
