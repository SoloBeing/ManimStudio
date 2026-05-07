def _join(lines):
    return "\n".join(lines) + "\n"


def build_trig_source(show_sin, show_cos, show_tan, A, w, ph, D, xr, show_grid, anim):
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
