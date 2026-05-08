def _join(lines):
    return "\n".join(lines) + "\n"


TEXT_POSITIONS = {
    "top_left": ("UL", "UR", "DOWN"),
    "top_right": ("UR", "UL", "DOWN"),
    "bottom_left": ("DL", "DR", "UP"),
    "bottom_right": ("DR", "DL", "UP"),
}


TEXT_COLORS = {
    "white": "WHITE",
    "blue": "BLUE",
    "teal": "TEAL",
    "green": "GREEN",
    "yellow": "YELLOW",
    "orange": "ORANGE",
    "red": "RED",
    "purple": "PURPLE",
}


def _text_position(value):
    return TEXT_POSITIONS.get(str(value or "").strip().lower(), TEXT_POSITIONS["top_left"])


def _text_color(value):
    return TEXT_COLORS.get(str(value or "").strip().lower(), "WHITE")


def build_trig_source(
    show_sin, show_cos, show_tan, A, w, ph, D, xr, show_grid, anim,
    text_position="top_right", text_color="white", text_font="Arial",
):
    primary_corner, _, stack_direction = _text_position(text_position)
    txt_col = _text_color(text_color)
    font_arg = repr(text_font or "Arial")
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
        g  = f"g{i}"
        lv = f"lbl{i}"
        lx = f"{xr * 0.5:.2f}"
        L += [
            f"        {g} = axes.plot(",
            f"            lambda x: {expr},",
            f"            x_range=[{-xr:.2f}, {xr:.2f}, 0.05],",
            f"            color={color}, stroke_width=2.5, use_smoothing=True,",
            "        )",
            f'        {lv} = Text("{name}", font_size=20, color={txt_col}, font={font_arg})',
        ]
        if i == 0:
            L.append(f"        {lv}.to_corner({primary_corner})")
        else:
            L.append(f"        {lv}.next_to(lbl{i - 1}, {stack_direction}, buff=0.12)")
        if anim == "Create":
            L.append(f"        self.play(Create({g}), FadeIn({lv}), run_time=1.5)")
        elif anim == "FadeIn":
            L.append(f"        self.play(FadeIn({g}), FadeIn({lv}), run_time=1.2)")
        else:
            L.append(f"        self.play(Create({g}), Write({lv}), run_time=2.0)")

    L.append("        self.wait(1.5)")
    return _join(L)


def build_complex_source(
    mode, re_c, im_c, scale, n_pts, show_arrows,
    text_position="top_left", text_color="teal", text_font="Arial",
):
    primary_corner, _, _ = _text_position(text_position)
    txt_col = _text_color(text_color)
    font_arg = repr(text_font or "Arial")
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
    fn       = fn_map.get(mode, "z**2")
    r_sample = min(float(scale) * 0.6, 1.8)
    n        = max(4, int(n_pts))

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
        f'        title = Text("{mode}", font_size=22, color={txt_col}, font={font_arg})',
        f"        title.to_corner({primary_corner})",
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


def build_linear_source(
    a, b, c, d, vx, vy, show_det, show_basis, show_grid,
    text_position="top_left", text_color="white", text_font="Arial",
):
    det     = a*d - b*c
    tvx     = a*vx + b*vy
    tvy     = c*vx + d*vy
    det_col = "GREEN" if abs(det) > 1e-9 else "RED"
    primary_corner, secondary_corner, det_direction = _text_position(text_position)
    txt_col = _text_color(text_color)
    font_arg = repr(text_font or "Arial")

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
            f"        e1_lbl = Text('e1', font_size=16, color={txt_col}, font={font_arg}).next_to(axes.c2p(1,0), UR, buff=0.1)",
            f"        e2_lbl = Text('e2', font_size=16, color={txt_col}, font={font_arg}).next_to(axes.c2p(0,1), UR, buff=0.1)",
            "        self.play(GrowArrow(e1), GrowArrow(e2), FadeIn(e1_lbl, e2_lbl), run_time=0.8)",
        ]

    L += [
        f"        vec_start = axes.c2p(0, 0)",
        f"        vec_end   = axes.c2p({vx:.6f}, {vy:.6f})",
        "        vec = Arrow(vec_start, vec_end, color=YELLOW, buff=0,",
        "                    stroke_width=5, max_tip_length_to_length_ratio=0.2)",
        f"        vec_lbl = Text('v=({vx:.2f},{vy:.2f})', font_size=16, color={txt_col}, font={font_arg})",
        "        vec_lbl.next_to(vec.get_end(), UR, buff=0.1)",
        "        self.play(GrowArrow(vec), FadeIn(vec_lbl), run_time=0.8)",
        "",
        f'        mat_lbl = Text("M = [[{a:.2f}, {b:.2f}], [{c:.2f}, {d:.2f}]]",',
        f"                        font_size=18, color={txt_col}, font={font_arg})",
        f"        mat_lbl.to_corner({primary_corner}).add_background_rectangle()",
        f'        det_lbl = Text("det = {det:.3f}", font_size=18, color={det_col}, font={font_arg})',
        f"        det_lbl.next_to(mat_lbl, {det_direction}, buff=0.15).add_background_rectangle()",
        f'        res_lbl = Text("Mv = ({tvx:.2f}, {tvy:.2f})", font_size=18, color={txt_col}, font={font_arg})',
        f"        res_lbl.to_corner({secondary_corner}).add_background_rectangle()",
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
        f"        tvec_lbl = Text('Mv=({tvx:.2f},{tvy:.2f})', font_size=16, color={txt_col}, font={font_arg})",
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


def build_nonlinear_source(
    mode, intensity, scale, show_grid, show_points,
    text_position="top_left", text_color="teal", text_font="Arial",
):
    mode = str(mode or "swirl").strip().lower()
    primary_corner, _, subtitle_direction = _text_position(text_position)
    title_color = _text_color(text_color)
    font_arg = repr(text_font or "Arial")
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

    L = [
        "from manim import *",
        "import numpy as np",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        f'        title = Text("{title}", font_size=26, color={title_color}, font={font_arg})',
        f"        title.to_corner({primary_corner})",
        f'        subtitle = Text("{subtitle}", font_size=16, color={title_color}, font={font_arg})',
        f"        subtitle.next_to(title, {subtitle_direction}, buff=0.12)",
        "        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)",
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

    L += [
        "        self.wait(1.5)",
    ]
    return _join(L)


def build_code_source(
    code_str, language, anim, background, add_line_numbers, font_size, run_time,
    text_position="top_left", text_color="white", text_font="Consolas",
):
    safe = repr(code_str)   # escapes newlines, quotes, backslashes safely
    language = str(language or "python").lower()
    background = str(background or "window").lower()
    font_arg = repr(text_font or "Consolas")

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

    L = [
        "from manim import *",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
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
        f"                paragraph_config={{'font_size': {font_size:.0f}, 'font': {font_arg}}},",
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


def build_streamlines_source(
    mode, scale, spacing, flow_speed, virtual_time, stroke_width, show_axes, animate,
    text_position="top_left", text_color="teal", text_font="Arial",
):
    mode = str(mode or "vortex").strip().lower()
    primary_corner, _, subtitle_direction = _text_position(text_position)
    txt_col = _text_color(text_color)
    font_arg = repr(text_font or "Arial")
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
    step = max(0.2, float(spacing))

    L = [
        "from manim import *",
        "import numpy as np",
        "",
        "class ManimScene(Scene):",
        "    def construct(self):",
        f'        title = Text("{title} StreamLines", font_size=26, color={txt_col}, font={font_arg})',
        f"        title.to_corner({primary_corner})",
        f'        subtitle = Text("{subtitle}", font_size=16, color={txt_col}, font={font_arg})',
        f"        subtitle.next_to(title, {subtitle_direction}, buff=0.12)",
        "        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)",
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
        "            colors=[BLUE, TEAL, GREEN, YELLOW, RED],",
        "            min_color_scheme_value=0,",
        f"            max_color_scheme_value={max(1.0, scale):.2f},",
        "            color_scheme=lambda p: np.linalg.norm(field(p)),",
        "            dt=0.05,",
        f"            virtual_time={virtual_time:.2f},",
        "            max_anchors_per_line=70,",
        f"            stroke_width={stroke_width:.2f},",
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
