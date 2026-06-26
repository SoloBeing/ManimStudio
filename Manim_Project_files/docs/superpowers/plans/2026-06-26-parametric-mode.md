# Parametric Curves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add parametric curves `(x(t), y(t))` to the existing Function Grapher (`funcgraph`) mode — paired expressions, a `t`-range, classic presets, and three extras (animated tracer, velocity vector, t-markers) — without adding a new mode/button and without altering the shipped `y=f(x)` output.

**Architecture:** A panel-level **Function ⇄ Parametric** toggle switches `FunctionGraphPanel`; the builder `build_funcgraph_source` gains a `plot_kind` switch that delegates to a new `_build_parametric_source`. The Cartesian axes block is extracted to a shared `_emit_cartesian_axes` helper used by both paths (regression-locked so the function output stays byte-identical). The generated parametric scene reuses funcgraph's friendly-math namespace and segment-plot robustness via a t-driven `_param_plot` twin of `_fg_plot`.

**Tech Stack:** Python (Manim 0.20.1 codegen via string-list builder), React + TypeScript (Vite) panel, pure-`compile()` unit tests.

## Global Constraints

- **Manim 0.20.1.** Generated scenes must `compile()` and render under it.
- **Mode key stays `funcgraph`.** No new activity-bar button; no changes to `ActivityBar.tsx`, `types.ts`, `Sidebar.tsx`, `App.tsx`, or `api.py`.
- **Function path is byte-identical.** With `plot_kind="function"` (default), `build_funcgraph_source` output is unchanged. Proven by `test_funcgraph.py` **9/9 unchanged** after every task.
- **LaTeX-free except `use_latex`.** The only LaTeX token ever emitted is `axes.add_coordinates()`, only under `use_latex=True`. All other labels are `Text`. The function path never emits it (deferred per spec §1).
- **Parameter is `t`** (radians); friendly syntax translates `^`→`**`; all exprs pass `_validate_expr` (shared blocklists). Blocked tokens raise `ValueError`.
- **Up to 3 parametric curves;** extras ride curve 0 only. Velocity requires the tracer.
- **Workflow:** smoke test before committing; **never push automatically** (user-confirmed step). Verify UI with `cd ui && npm run build` (not `tsc --noEmit`).
- **Run tests with:** `uv run python <test_file>.py` from `Manim_Project_files/`.

---

## File Structure

- **`builders.py`** (modify) — extract `_emit_cartesian_axes`; add parametric default dicts, `_param_expr`, `_PARAM_PLOT_SRC`, `_VEL_ARROW_SRC`, `_parse_t_values`, `_build_parametric_source`, `_emit_param_tracer_velocity`, `_emit_param_markers`; add `plot_kind` + parametric kwargs to `build_funcgraph_source`.
- **`ui/src/components/panels/FunctionGraphPanel.tsx`** (modify) — add Function⇄Parametric toggle, separate `paramCurves` state, parametric sub-UI, branched `getParams()`.
- **`test_parametric.py`** (create, tracked) — unit tests mirroring `test_polar.py`.
- **`smoke_test_v2.py`** (modify) — add `[29]` parametric real-render + register it.

All builder helpers reused as-is: `_join`, `_validate_expr`, `_text_color`, `_FG_NAMESPACE`, `_FG_ANIMS`, `api._BUILDERS["funcgraph"]`, `api._source_needs_latex`.

---

### Task 1: Extract `_emit_cartesian_axes` (regression-locked)

Pull the funcgraph axes/grid/Create block into a shared helper that both the function and (future) parametric paths use. Output for the function path must stay byte-identical.

**Files:**
- Modify: `builders.py` (add helper before `build_funcgraph_source` at ~line 1591; replace the inline axes block at ~lines 1672-1693)
- Test: `test_funcgraph.py` (existing, must stay 9/9)

**Interfaces:**
- Produces: `_emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=False) -> None` — appends the axes definition, optional `add_coordinates()` (when `use_latex`), optional grid, and `Create(axes)` to list `L`. Caller emits `class ManimScene(Scene):` / `    def construct(self):` first.

- [ ] **Step 1: Run the funcgraph baseline to confirm it's green before touching it**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_funcgraph.py`
Expected: `9/9 passed`

- [ ] **Step 2: Add the helper** (insert immediately after `_funcgraph_expr` / before `def build_funcgraph_source(`)

```python
def _emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=False):
    """Append the shared Cartesian axes block to L (used by funcgraph + parametric).

    Emits the Axes definition, optional MathTex tick labels (use_latex only), an
    optional NumberPlane grid, then Create(axes). The caller emits the
    `class ManimScene(Scene):` / `def construct(self):` header first.
    """
    L += [
        "        axes = Axes(",
        f"            x_range=[{xlo:.4f}, {xhi:.4f}, {xs:.4f}],",
        f"            y_range=[{ylo:.4f}, {yhi:.4f}, {ys:.4f}],",
        "            x_length=11, y_length=6,",
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
            "            background_line_style=dict(stroke_color=BLUE_E, stroke_opacity=0.25),",
            "        )",
            "        self.play(FadeIn(grid), run_time=0.6)",
        ]
    L.append("        self.play(Create(axes), run_time=0.8)")
```

- [ ] **Step 3: Replace the inline axes block in `build_funcgraph_source`**

Find this block (currently ~lines 1672-1693):

```python
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
```

Replace it with:

```python
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
    ]
    _emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=False)
```

- [ ] **Step 4: Run the funcgraph suite to verify byte-identical output**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_funcgraph.py`
Expected: `9/9 passed` (unchanged — proves the extraction preserved output)

- [ ] **Step 5: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/builders.py
git commit -m "refactor(funcgraph): extract _emit_cartesian_axes (shared, use_latex-ready)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Parametric builder scaffold + `use_latex`

Add the parametric builder: defaults, expr helper, the `_param_plot` source, `_build_parametric_source` (curves + axes via the Task 1 helper + labels + animated draw), and the `plot_kind` switch in `build_funcgraph_source`. No extras yet.

**Files:**
- Modify: `builders.py` (add constants/helpers + `_build_parametric_source` after the funcgraph section ~line 1737; edit `build_funcgraph_source` signature + add branch)
- Create: `test_parametric.py`

**Interfaces:**
- Consumes: `_emit_cartesian_axes` (Task 1), `_validate_expr`, `_text_color`, `_FG_NAMESPACE`, `_FG_ANIMS`, `_join`.
- Produces:
  - `build_funcgraph_source(..., plot_kind="function", param_curves=None, t_min=0.0, t_max=6.2832, tracer=None, velocity=None, t_markers=None, use_latex=False)` — when `plot_kind=="parametric"`, returns `_build_parametric_source(...)`.
  - `_build_parametric_source(param_curves, x_min, x_max, y_min, y_max, x_step, y_step, show_grid, cam_zoom, anim, axis_label_x, axis_label_y, title, t_min, t_max, tracer, velocity, t_markers, use_latex) -> str`
  - `_param_expr(expr, label, default) -> str`
  - Module constants `_PARAM_TRACER_DEFAULT`, `_PARAM_VELOCITY_DEFAULT`, `_PARAM_MARKERS_DEFAULT`, `_PARAM_PLOT_SRC`.
  - Generated scene defines `def _p{i}_x(t)` / `def _p{i}_y(t)` and `_param_plot(axes, fx, fy, t0, t1, dt, color, width)`.

- [ ] **Step 1: Write the failing test** (create `test_parametric.py`)

```python
"""Unit tests for the parametric path of build_funcgraph_source.

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_parametric.py
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_funcgraph_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<parametric>", "exec")


def _param(**kw):
    kw.setdefault("plot_kind", "parametric")
    return build_funcgraph_source(**kw)


def test_scaffold_compiles_and_builds_axes():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)", "color": "blue"}])
    _compiles(src)
    assert "class ManimScene(Scene):" in src
    assert "axes = Axes(" in src
    assert "def _param_plot(" in src and "axes.c2p" in src
    assert "def _p0_x(t):" in src and "return cos(t)" in src
    assert "def _p0_y(t):" in src and "return sin(t)" in src


def test_default_circle_fallback():
    src = _param(param_curves=[])
    assert "return cos(t)" in src and "return sin(t)" in src
    _compiles(src)
    src2 = _param(param_curves=[{"x_expr": "   ", "y_expr": ""}])
    assert "return cos(t)" in src2 and "return sin(t)" in src2
    _compiles(src2)


def test_friendly_syntax_and_namespace():
    src = _param(param_curves=[{"x_expr": "cos(t)^3", "y_expr": "sin(t)^3"}])
    assert "return cos(t)**3" in src and "return sin(t)**3" in src
    assert "from numpy import (" in src
    _compiles(src)


def test_curves_capped_at_3():
    src = _param(param_curves=[
        {"x_expr": "cos(t)", "y_expr": "sin(t)"},
        {"x_expr": "2*cos(t)", "y_expr": "2*sin(t)"},
        {"x_expr": "3*cos(t)", "y_expr": "3*sin(t)"},
        {"x_expr": "4*cos(t)", "y_expr": "4*sin(t)"},
    ])
    assert "def _p0_x(t):" in src and "def _p2_x(t):" in src
    assert "def _p3_x(t):" not in src
    _compiles(src)


def test_blocked_expr_rejected():
    for bad in ("__import__('os')", "open('x')", "eval('1')"):
        try:
            _param(param_curves=[{"x_expr": bad, "y_expr": "sin(t)"}])
        except ValueError:
            continue
        raise AssertionError(f"blocked expr was not rejected: {bad}")


def test_all_animation_styles_compile():
    for a in ("Create", "FadeIn", "Write", "GrowFromEdge", "DrawBorderThenFill"):
        _compiles(_param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}], anim=a))


def test_latex_free_by_default():
    from api import _source_needs_latex
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}], title="Demo")
    assert "add_coordinates" not in src
    assert not _source_needs_latex(src), "default parametric scene must be LaTeX-free"
    _compiles(src)


def test_use_latex_toggles_add_coordinates_and_preflight():
    from api import _source_needs_latex
    base = dict(plot_kind="parametric",
                param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}])
    off = build_funcgraph_source(use_latex=False, **base)
    assert "add_coordinates" not in off
    assert not _source_needs_latex(off)
    _compiles(off)
    on = build_funcgraph_source(use_latex=True, **base)
    assert "axes.add_coordinates()" in on
    assert _source_needs_latex(on)
    _compiles(on)


def test_function_path_unchanged():
    # plot_kind defaults to "function"; the parametric helper must not leak in.
    src = build_funcgraph_source([{"expr": "x^2"}])
    assert "_fg_plot(" in src and "def _f0(x):" in src
    assert "_param_plot(" not in src and "_p0_x" not in src
    _compiles(src)


def test_registered_under_funcgraph():
    from api import _BUILDERS
    assert _BUILDERS["funcgraph"] is build_funcgraph_source


TESTS = [v for k, v in sorted(globals().items())
         if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    ok = 0
    for t in TESTS:
        try:
            t(); print(f"{PASS}  {t.__name__}"); ok += 1
        except Exception as e:
            print(f"{FAIL}  {t.__name__}: {e}")
    print(f"\n{ok}/{len(TESTS)} passed")
    sys.exit(0 if ok == len(TESTS) else 1)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py`
Expected: FAIL — `build_funcgraph_source` raises `TypeError` on unexpected kwarg `plot_kind` (signature not yet extended).

- [ ] **Step 3: Add the constants + `_param_plot` source** (in `builders.py`, after the funcgraph section, ~line 1737, before the Calculus Toolkit block)

```python
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
```

- [ ] **Step 4: Add `_build_parametric_source`** (immediately after `_param_expr`)

```python
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
    if need_vel:
        L += _VEL_ARROW_SRC
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
    _emit_cartesian_axes(L, xlo, xhi, xs, ylo, yhi, ys, show_grid, use_latex=use_latex)

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
        if label:
            lv = f"lbl{i}"
            L.append(f"        {lv} = Text({label!r}, font_size=22, color={color})")
            if i == 0:
                L.append(f"        {lv}.to_corner(UR, buff=0.4)")
            else:
                L.append(f"        {lv}.next_to(lbl{i - 1}, DOWN, buff=0.15, aligned_edge=LEFT)")
            L.append(f"        self.play({play}, FadeIn({lv}), run_time={rt:.1f})")
        else:
            L.append(f"        self.play({play}, run_time={rt:.1f})")

    # extras (Tasks 3-4 add their emitters here)
    _emit_param_tracer_velocity(L, TR, VE, t0, t1)
    _emit_param_markers(L, TM)

    L.append("        self.wait(1.5)")
    return _join(L)
```

> **Note:** `_VEL_ARROW_SRC`, `_emit_param_tracer_velocity`, and `_emit_param_markers` are added in Tasks 3-4. For Task 2 to import cleanly, add these three temporary stubs directly below `_build_parametric_source` (Tasks 3-4 replace them):

```python
_VEL_ARROW_SRC = []


def _emit_param_tracer_velocity(L, TR, VE, t0, t1):
    return None


def _emit_param_markers(L, TM):
    return None
```

- [ ] **Step 5: Extend `build_funcgraph_source` signature + add the branch**

Change the signature from:

```python
def build_funcgraph_source(
    curves,
    x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0,
    x_step=None, y_step=None,
    show_grid=False, cam_zoom=1.0,
    anim="Create",
    axis_label_x="x", axis_label_y="y", title="",
):
```

to:

```python
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
```

(The existing function-path body follows unchanged, starting at `# --- numeric ranges ...`.)

- [ ] **Step 6: Run the parametric + funcgraph suites**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py && uv run python test_funcgraph.py`
Expected: `test_parametric.py` → all passed (10/10); `test_funcgraph.py` → `9/9 passed`.

- [ ] **Step 7: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/builders.py Manim_Project_files/test_parametric.py
git commit -m "feat(parametric): build_parametric_source scaffold + curves + use_latex

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Tracer + velocity extras

Animated tracing dot (signature) and an optional velocity vector that rides it. Replace the Task 2 stubs `_VEL_ARROW_SRC` and `_emit_param_tracer_velocity`.

**Files:**
- Modify: `builders.py` (replace the two stubs)
- Test: `test_parametric.py` (add cases)

**Interfaces:**
- Consumes: `_text_color`; generated scene's `_p0_x` / `_p0_y` (always defined).
- Produces:
  - `_VEL_ARROW_SRC` (list of source lines defining `def _vel_arrow(axes, fx, fy, t, k, color)`), emitted in the header only when tracer+velocity are both on.
  - `_emit_param_tracer_velocity(L, TR, VE, t0, t1) -> None` — emits a `ValueTracker`, an `always_redraw` `Dot` (tracer), an optional `always_redraw` `_vel_arrow` (velocity), and the single sweep `self.play(_tval.animate.set_value(...))`. Emits nothing when `TR["on"]` is false.

- [ ] **Step 1: Write the failing tests** (append to `test_parametric.py`, before the `TESTS = [...]` line)

```python
def test_tracer_emits_valuetracker():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 tracer={"on": True, "color": "yellow"})
    assert "_tval = ValueTracker(" in src
    assert "always_redraw(lambda: Dot(axes.c2p(_p0_x(_tval.get_value())" in src
    assert "_tval.animate.set_value(" in src
    _compiles(src)


def test_tracer_off_emits_nothing():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 tracer={"on": False})
    assert "ValueTracker(" not in src
    _compiles(src)


def test_velocity_requires_tracer():
    # velocity on but tracer off -> no vector, no sweep
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 tracer={"on": False}, velocity={"on": True})
    assert "_vel_arrow" not in src and "_vec" not in src
    assert "ValueTracker(" not in src
    _compiles(src)


def test_velocity_with_tracer_emits_arrow():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 tracer={"on": True}, velocity={"on": True, "color": "green", "scale": 1.0})
    assert "def _vel_arrow(" in src
    assert "_vec = always_redraw(lambda: _vel_arrow(axes, _p0_x, _p0_y" in src
    _compiles(src)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py`
Expected: the 4 new tests FAIL (stubs emit nothing).

- [ ] **Step 3: Replace the `_VEL_ARROW_SRC` stub** with the real source-line list

```python
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
```

- [ ] **Step 4: Replace the `_emit_param_tracer_velocity` stub** with the real emitter

```python
def _emit_param_tracer_velocity(L, TR, VE, t0, t1):
    # Tracer + velocity share ONE ValueTracker/sweep; velocity requires the tracer.
    if not TR.get("on"):
        return
    tcolor = _text_color(TR.get("color", "yellow"))
    L.append(f"        _tval = ValueTracker({t0:.4f})")
    L.append(
        f"        _dot = always_redraw(lambda: Dot(axes.c2p(_p0_x(_tval.get_value()), "
        f"_p0_y(_tval.get_value())), radius=0.08, color={tcolor}))"
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
```

- [ ] **Step 5: Run the parametric + funcgraph suites**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py && uv run python test_funcgraph.py`
Expected: `test_parametric.py` all passed (14/14); `test_funcgraph.py` `9/9 passed`.

- [ ] **Step 6: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/builders.py Manim_Project_files/test_parametric.py
git commit -m "feat(parametric): animated tracer dot + velocity vector overlays

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: t-value markers extra

Static labeled dots at user-given `t` values. Adds `_parse_t_values` and replaces the Task 2 `_emit_param_markers` stub.

**Files:**
- Modify: `builders.py`
- Test: `test_parametric.py` (add cases)

**Interfaces:**
- Produces:
  - `_parse_t_values(s) -> list[float]` — splits on `;`/newline, floats each, skips malformed, caps at 12.
  - `_emit_param_markers(L, TM) -> None` — emits a `Dot` + `Text("t=…")` at each value on curve 0; nothing when `TM["on"]` is false or no valid values.

- [ ] **Step 1: Write the failing tests** (append to `test_parametric.py`, before `TESTS = [...]`)

```python
def test_markers_emit_dots():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 t_markers={"on": True, "values": "0; 1.57", "color": "pink"})
    assert "Dot(axes.c2p(_p0_x(" in src
    assert src.count("Dot(axes.c2p(_p0_x(") == 2
    assert "t=0" in src and "t=1.57" in src
    _compiles(src)


def test_markers_malformed_skipped():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 t_markers={"on": True, "values": "0; garbage; 3.14"})
    assert src.count("Dot(axes.c2p(_p0_x(") == 2  # only 0 and 3.14 survive
    _compiles(src)


def test_markers_off_emits_nothing():
    src = _param(param_curves=[{"x_expr": "cos(t)", "y_expr": "sin(t)"}],
                 t_markers={"on": False, "values": "0; 1"})
    assert "_tm" not in src
    _compiles(src)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py`
Expected: the 3 new tests FAIL (stub emits nothing).

- [ ] **Step 3: Add `_parse_t_values` and replace the `_emit_param_markers` stub**

```python
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
            f"        _tm.add(Dot(axes.c2p(_p0_x({tv:.5f}), _p0_y({tv:.5f})), "
            f"radius=0.07, color={color}))"
        )
        L.append(
            f"        _tm.add(Text('t={tv:g}', font_size=16, color={color})"
            f".next_to(axes.c2p(_p0_x({tv:.5f}), _p0_y({tv:.5f})), UR, buff=0.05))"
        )
    L.append("        self.play(FadeIn(_tm), run_time=0.6)")
```

- [ ] **Step 4: Run the parametric + funcgraph suites**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py && uv run python test_funcgraph.py`
Expected: `test_parametric.py` all passed (17/17); `test_funcgraph.py` `9/9 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/builders.py Manim_Project_files/test_parametric.py
git commit -m "feat(parametric): t-value marker overlay

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Panel — Function ⇄ Parametric toggle + parametric UI

Add the panel toggle, separate `paramCurves` state, the parametric sub-UI, and a branched `getParams()`. Function mode renders verbatim and emits the identical payload.

**Files:**
- Modify: `ui/src/components/panels/FunctionGraphPanel.tsx` (full replacement)

**Interfaces:**
- Consumes: `Knob`, `PanelHandle` (existing imports).
- Produces: `getParams()` returns `{ mode: 'funcgraph', params: { plot_kind, ... } }` — function payload byte-identical when toggle is on Function; parametric payload per spec §4 when on Parametric.

- [ ] **Step 1: Verify the current panel builds clean (baseline)**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files/ui && npm run build`
Expected: `tsc -b` succeeds, no errors.

- [ ] **Step 2: Replace `FunctionGraphPanel.tsx` entirely** with:

```tsx
import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface Curve { expr: string; color: string; label: string; style: string; width: string }
interface PCurve { xExpr: string; yExpr: string; color: string; label: string }

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];

const PRESETS: [string, string][] = [
  ['Preset…', ''],
  ['x²', 'x^2'], ['x³', 'x^3'], ['eˣ', 'exp(x)'], ['ln(x)', 'log(x)'],
  ['|x|', 'abs(x)'], ['√x', 'sqrt(x)'], ['1/x', '1/x'], ['sin(x)', 'sin(x)'],
];

// Parametric presets: [label, x(t), y(t)]
const PARAM_PRESETS: [string, string, string][] = [
  ['Preset…', '', ''],
  ['Circle', '3*cos(t)', '3*sin(t)'],
  ['Ellipse', '4*cos(t)', '2*sin(t)'],
  ['Lissajous', '3*sin(3*t)', '3*sin(2*t)'],
  ['Spiral', '0.4*t*cos(t)', '0.4*t*sin(t)'],
  ['Astroid', '3*cos(t)^3', '3*sin(t)^3'],
  ['Rose', '3*cos(3*t)*cos(t)', '3*cos(3*t)*sin(t)'],
  ['Cycloid', 't - sin(t)', '1 - cos(t)'],
  ['Lemniscate', '3*cos(t)/(1+sin(t)^2)', '3*sin(t)*cos(t)/(1+sin(t)^2)'],
];

const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

const DEFAULT_CURVES: Curve[] = [
  { expr: 'x^2', color: 'blue', label: 'f', style: 'solid', width: '2.5' },
];
const DEFAULT_PCURVES: PCurve[] = [
  { xExpr: '3*cos(t)', yExpr: '3*sin(t)', color: 'blue', label: 'circle' },
];

export function FunctionGraphPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [plotKind, setPlotKind]     = useState<'function' | 'parametric'>('function');

  // function-mode state (unchanged)
  const [curves, setCurves]         = useState<Curve[]>(DEFAULT_CURVES);
  // parametric-mode state
  const [pCurves, setPCurves]       = useState<PCurve[]>(DEFAULT_PCURVES);
  const [tMin, setTMin]             = useState(0);
  const [tMax, setTMax]             = useState(6.2832);

  const [xMin, setXMin]             = useState(-5);
  const [xMax, setXMax]             = useState(5);
  const [yMin, setYMin]             = useState(-4);
  const [yMax, setYMax]             = useState(4);
  const [xStep, setXStep]           = useState(1);
  const [yStep, setYStep]           = useState(1);
  const [showGrid, setShowGrid]     = useState(false);
  const [zoom, setZoom]             = useState(1.0);
  const [anim, setAnim]             = useState('Create');
  const [axisLabelX, setAxisLabelX] = useState('x');
  const [axisLabelY, setAxisLabelY] = useState('y');
  const [title, setTitle]           = useState('');
  const [useLatex, setUseLatex]     = useState(false);

  // parametric extras
  const [trOn, setTrOn]       = useState(true);
  const [trColor, setTrColor] = useState('yellow');
  const [veOn, setVeOn]       = useState(false);
  const [veColor, setVeColor] = useState('green');
  const [veScale, setVeScale] = useState(1.0);
  const [tmOn, setTmOn]       = useState(false);
  const [tmValues, setTmValues] = useState('0; 1.57; 3.14');
  const [tmColor, setTmColor] = useState('pink');

  function updateCurve(i: number, field: keyof Curve, val: string) {
    setCurves(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: val } : c));
  }
  function addCurve() {
    if (curves.length >= 4) return;
    const defaults = ['blue', 'red', 'green', 'yellow'];
    setCurves(prev => [...prev, { expr: '', color: defaults[prev.length % 4], label: '', style: 'solid', width: '2.5' }]);
  }
  function removeCurve(i: number) {
    if (curves.length <= 1) return;
    setCurves(prev => prev.filter((_, idx) => idx !== i));
  }

  function updatePCurve(i: number, field: keyof PCurve, val: string) {
    setPCurves(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: val } : c));
  }
  function addPCurve() {
    if (pCurves.length >= 3) return;
    const defaults = ['blue', 'red', 'green'];
    setPCurves(prev => [...prev, { xExpr: '', yExpr: '', color: defaults[prev.length % 3], label: '' }]);
  }
  function removePCurve(i: number) {
    if (pCurves.length <= 1) return;
    setPCurves(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => {
      if (plotKind === 'parametric') {
        return {
          mode: 'funcgraph',
          params: {
            plot_kind: 'parametric',
            param_curves: pCurves.map(c => ({
              x_expr: c.xExpr, y_expr: c.yExpr, color: c.color, label: c.label,
            })),
            t_min: tMin, t_max: tMax,
            x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax,
            x_step: xStep, y_step: yStep,
            show_grid: showGrid, cam_zoom: zoom,
            axis_label_x: axisLabelX, axis_label_y: axisLabelY, title,
            anim,
            tracer:    { on: trOn, color: trColor },
            velocity:  { on: veOn, color: veColor, scale: veScale },
            t_markers: { on: tmOn, values: tmValues, color: tmColor },
            use_latex: useLatex,
          },
        };
      }
      return {
        mode: 'funcgraph',
        params: {
          curves: curves.map(c => ({
            expr: c.expr, color: c.color, label: c.label,
            style: c.style, width: parseFloat(c.width) || 2.5,
          })),
          x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax,
          x_step: xStep, y_step: yStep,
          show_grid: showGrid, cam_zoom: zoom,
          anim,
          axis_label_x: axisLabelX, axis_label_y: axisLabelY, title,
        },
      };
    },
  }));

  return (
    <>
      <div className="mode-toggle" style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        <button
          className="mode-toggle__btn"
          style={{ flex: 1, fontWeight: plotKind === 'function' ? 700 : 400,
                   opacity: plotKind === 'function' ? 1 : 0.6 }}
          onClick={() => setPlotKind('function')}
        >y = f(x)</button>
        <button
          className="mode-toggle__btn"
          style={{ flex: 1, fontWeight: plotKind === 'parametric' ? 700 : 400,
                   opacity: plotKind === 'parametric' ? 1 : 0.6 }}
          onClick={() => setPlotKind('parametric')}
        >Parametric</button>
      </div>

      {plotKind === 'function' ? (
        <>
          <div className="sec-hdr">Curves (up to 4)</div>
          {curves.map((c, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <select className="app-select" style={{ width: 70 }} value=""
                  onChange={e => { if (e.target.value) updateCurve(i, 'expr', e.target.value); }}>
                  {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
                </select>
                <input className="app-input" style={{ flex: 1 }} value={c.expr}
                  onChange={e => updateCurve(i, 'expr', e.target.value.slice(0, 120))}
                  placeholder="f(x), e.g. sin(x) + x^2" />
                <button className="mode-toggle__btn"
                  style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
                  onClick={() => removeCurve(i)} title="Remove curve">×</button>
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <select className="app-select" style={{ flex: 1 }} value={c.color}
                  onChange={e => updateCurve(i, 'color', e.target.value)}>
                  {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <select className="app-select" style={{ width: 76 }} value={c.style}
                  onChange={e => updateCurve(i, 'style', e.target.value)}>
                  <option value="solid">Solid</option>
                  <option value="dashed">Dashed</option>
                </select>
                <input className="knob__num" style={{ width: 44, textAlign: 'center' }} value={c.label}
                  onChange={e => updateCurve(i, 'label', e.target.value.slice(0, 12))} placeholder="lbl" />
              </div>
              <Knob label="Width" min={0.5} max={8} value={parseFloat(c.width) || 2.5}
                onChange={v => updateCurve(i, 'width', String(v))} decimals={1} step={0.5} />
            </div>
          ))}
          {curves.length < 4 && (
            <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addCurve}>
              + Add Curve
            </button>
          )}
        </>
      ) : (
        <>
          <div style={{ fontSize: 11, color: 'var(--text-dim, #9aa)', lineHeight: 1.4, marginBottom: 8 }}>
            Curves are <b>(x(t), y(t))</b>; <b>t in radians</b> (e.g. <code>cos(t)</code>).
            The range below sets how far <b>t</b> sweeps.
          </div>
          <div className="sec-hdr">Curves (up to 3)</div>
          {pCurves.map((c, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <select className="app-select" style={{ width: 70 }} value=""
                  onChange={e => {
                    const p = PARAM_PRESETS.find(([l]) => l === e.target.value);
                    if (p && p[0] !== 'Preset…') { updatePCurve(i, 'xExpr', p[1]); updatePCurve(i, 'yExpr', p[2]); }
                  }}>
                  {PARAM_PRESETS.map(([l]) => <option key={l} value={l}>{l}</option>)}
                </select>
                <button className="mode-toggle__btn"
                  style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4, marginLeft: 'auto' }}
                  onClick={() => removePCurve(i)} title="Remove curve">×</button>
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <span style={{ width: 28, fontSize: 12, color: 'var(--text-dim, #9aa)' }}>x(t)</span>
                <input className="app-input" style={{ flex: 1 }} value={c.xExpr}
                  onChange={e => updatePCurve(i, 'xExpr', e.target.value.slice(0, 120))}
                  placeholder="x(t), e.g. cos(t)" />
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
                <span style={{ width: 28, fontSize: 12, color: 'var(--text-dim, #9aa)' }}>y(t)</span>
                <input className="app-input" style={{ flex: 1 }} value={c.yExpr}
                  onChange={e => updatePCurve(i, 'yExpr', e.target.value.slice(0, 120))}
                  placeholder="y(t), e.g. sin(t)" />
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <select className="app-select" style={{ flex: 1 }} value={c.color}
                  onChange={e => updatePCurve(i, 'color', e.target.value)}>
                  {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <input className="knob__num" style={{ width: 60, textAlign: 'center' }} value={c.label}
                  onChange={e => updatePCurve(i, 'label', e.target.value.slice(0, 12))} placeholder="lbl" />
              </div>
            </div>
          ))}
          {pCurves.length < 3 && (
            <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addPCurve}>
              + Add Curve
            </button>
          )}

          <div className="sec-sep" />
          <div className="sec-hdr">t-Range (radians)</div>
          <Knob label="t Min" min={-25.133} max={0}      value={tMin} onChange={setTMin} decimals={2} step={0.1} />
          <Knob label="t Max" min={0.1}     max={25.133} value={tMax} onChange={setTMax} decimals={2} step={0.1} />
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Axes</div>
      <Knob label="X Min"  min={-50} max={0}  value={xMin}  onChange={v => setXMin(Math.round(v))}  decimals={0} step={1} />
      <Knob label="X Max"  min={1}   max={50} value={xMax}  onChange={v => setXMax(Math.round(v))}  decimals={0} step={1} />
      <Knob label="Y Min"  min={-50} max={0}  value={yMin}  onChange={v => setYMin(Math.round(v))}  decimals={0} step={1} />
      <Knob label="Y Max"  min={1}   max={50} value={yMax}  onChange={v => setYMax(Math.round(v))}  decimals={0} step={1} />
      <Knob label="X Step" min={0.1} max={10} value={xStep} onChange={setXStep} decimals={1} step={0.5} />
      <Knob label="Y Step" min={0.1} max={10} value={yStep} onChange={setYStep} decimals={1} step={0.5} />
      <Knob label="Zoom"   min={0.3} max={3}  value={zoom}  onChange={setZoom}  decimals={2} step={0.05} />
      <div className="check-row">
        <label className="app-check">
          <input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} /> Grid
        </label>
      </div>

      {plotKind === 'parametric' && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Extras</div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={trOn}
              onChange={e => setTrOn(e.target.checked)} /> Tracing dot</label>
          </div>
          {trOn && (
            <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={trColor}
              onChange={e => setTrColor(e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
          )}
          {trOn && (
            <>
              <div className="check-row">
                <label className="app-check"><input type="checkbox" checked={veOn}
                  onChange={e => setVeOn(e.target.checked)} /> Velocity vector</label>
              </div>
              {veOn && (
                <>
                  <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={veColor}
                    onChange={e => setVeColor(e.target.value)}>
                    {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                  <Knob label="Scale" min={0.1} max={3} value={veScale} onChange={setVeScale} decimals={1} step={0.1} />
                </>
              )}
            </>
          )}
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={tmOn}
              onChange={e => setTmOn(e.target.checked)} /> t-markers</label>
          </div>
          {tmOn && (
            <>
              <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
                value={tmValues} onChange={e => setTmValues(e.target.value.slice(0, 120))}
                placeholder="t values — e.g. 0; 1.57; 3.14" />
              <select className="app-select" style={{ width: '100%' }} value={tmColor}
                onChange={e => setTmColor(e.target.value)}>
                {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </>
          )}
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelX} onChange={e => setAxisLabelX(e.target.value.slice(0, 24))} placeholder="X axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelY} onChange={e => setAxisLabelY(e.target.value.slice(0, 24))} placeholder="Y axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">{plotKind === 'parametric' ? 'Options' : 'Animation'}</div>
      {plotKind === 'parametric' && (
        <div className="check-row">
          <label className="app-check"><input type="checkbox" checked={useLatex}
            onChange={e => setUseLatex(e.target.checked)} /> Use LaTeX tick labels</label>
        </div>
      )}
      <select className="app-select" style={{ width: '100%', marginTop: 4 }} value={anim} onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(a => <option key={a} value={a}>{a}</option>)}
      </select>
    </>
  );
}
```

- [ ] **Step 3: Build the UI to verify it compiles**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files/ui && npm run build`
Expected: `tsc -b` succeeds, no errors.

- [ ] **Step 4: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/ui/src/components/panels/FunctionGraphPanel.tsx
git commit -m "feat(parametric): Function/Parametric panel toggle + parametric UI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Smoke test `[29]` + full regression gate + still-frame verification

Add a real-Manim parametric render to the smoke suite, run all gates, and visually verify stills (the funcgraph lesson: "video produced" missed a silent missing-curves bug).

**Files:**
- Modify: `smoke_test_v2.py` (add `test_parametric_real_render` + register it)

**Interfaces:**
- Consumes: `RenderThread`, `build_funcgraph_source`, the `_run` / `_show_err` smoke helpers.

- [ ] **Step 1: Add the render test** (insert after `test_polar_real_render`, ~line 1377)

```python
def test_parametric_real_render():
    print("\n[29] Parametric real render (curve+tracer+vector+markers) → video ... ", end="", flush=True)
    script = textwrap.dedent(f"""\
        import sys, os, threading, tempfile
        sys.path.insert(0, {HERE!r})
        from renderer import RenderThread
        from builders import build_funcgraph_source
        src = build_funcgraph_source(
            plot_kind="parametric",
            param_curves=[{{"x_expr": "3*sin(3*t)", "y_expr": "3*sin(2*t)", "label": "lissajous"}}],
            tracer={{"on": True}},
            velocity={{"on": True}},
            t_markers={{"on": True, "values": "0; 1.57; 3.14"}},
        )
        out, result, event = tempfile.mkdtemp(), [], threading.Event()
        def on_done(p):
            result.append(p); event.set()
        t = RenderThread(src, ['-ql'], out, on_done=on_done)
        t.start()
        ok = event.wait(timeout=120); t.join(5)
        if not ok or not result:
            print("TIMEOUT"); sys.exit(1)
        assert os.path.exists(result[0]), "video not found"
        print("ok:" + result[0])
    """)
    r = _run(script, timeout=150)
    if r.returncode == 0 and "ok:" in r.stdout:
        print(PASS); return True
    print(FAIL)
    if "TIMEOUT" in r.stdout:
        print("    (render timed out)")
    _show_err(r)
    return False
```

- [ ] **Step 2: Register it** (in the `PROCESS_TESTS` list, after the Polar entry at ~line 1418)

Find:
```python
    ("Polar real render (grid+curve+extras)",              test_polar_real_render),
```
Add immediately below:
```python
    ("Parametric real render (curve+tracer+vector+markers)", test_parametric_real_render),
```

- [ ] **Step 3: Run the full unit-test regression**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_parametric.py && uv run python test_funcgraph.py && uv run python test_polar.py && uv run python test_calculus.py`
Expected: parametric all passed (17/17); funcgraph `9/9`; polar `16/16`; calculus `20/20`.

- [ ] **Step 4: Run the smoke suite**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python smoke_test_v2.py`
Expected: all pass, including the new `[29] Parametric real render`.

- [ ] **Step 5: Still-frame verification (view the images)**

Render PNG stills for at least: (a) Lissajous + tracer + velocity + markers, (b) a Circle (round-ness check), (c) `use_latex=True` (tick numbers present), and (d) a **mid-sweep** frame. Example:

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files
python -c "from builders import build_funcgraph_source; open('/tmp/p.py','w').write(build_funcgraph_source(plot_kind='parametric', param_curves=[{'x_expr':'3*cos(3*t)*cos(t)','y_expr':'3*cos(3*t)*sin(t)','label':'rose'}], t_markers={'on':True,'values':'0; 1.05; 2.1'}))"
uv run manim -s -ql /tmp/p.py ManimScene
```

Open each generated PNG (under `media/images/`) and confirm: curve shape is correct (rose petal count, circle round, Lissajous lobes), axes/tick numbers render when LaTeX on, and tracer/vector/markers land on the curve. Fix any visual defect before proceeding (re-run the relevant task's tests after any builder change).

- [ ] **Step 6: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/smoke_test_v2.py
git commit -m "test(parametric): [29] real-render smoke + full regression gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification checklist (before declaring done)

- [ ] `test_parametric.py` 17/17, `test_funcgraph.py` 9/9 (byte-identical function path), `test_polar.py` 16/16, `test_calculus.py` 20/20.
- [ ] `smoke_test_v2.py` green incl. `[29]`.
- [ ] `cd ui && npm run build` clean.
- [ ] Still-frames visually verified (circle round, Lissajous/rose correct, LaTeX ticks, mid-sweep tracer/vector/markers correct).
- [ ] No new activity-bar button; `api.py`/`types.ts`/`Sidebar.tsx`/`ActivityBar.tsx` untouched.
- [ ] Branch not pushed (await explicit user confirmation).
