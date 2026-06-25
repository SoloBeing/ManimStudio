# Calculus Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `calculus` mode — pick a function and interval, then toggle Riemann sums, area under/between curves, a tangent (with optional secant→tangent animation), and a numeric derivative overlay.

**Architecture:** Approach B from the spec — a self-contained `build_calculus_source(...)` generator in `builders.py` (reusing funcgraph's module-level helpers) plus a new `CalculusPanel.tsx`. The builder emits a `Scene` that plots the analysis function via `axes.plot(_f, x_range=[a,b])` (a real graph object the Manim calculus helpers require) and layers the four overlays. Labels are LaTeX-free `Text` by default; a `use_latex` flag switches readouts/legends to `MathTex`.

**Tech Stack:** Python (string-emitting builder), Manim CE 0.20.1, React + TypeScript (Vite), plain-Python test harness (no pytest).

**Spec:** `docs/superpowers/specs/2026-06-25-calculus-toolkit-design.md`

## Global Constraints

- **LaTeX-free by default.** Emit `MathTex`/`DecimalNumber` **only** when `use_latex=True`. With `use_latex=False`, `api._source_needs_latex(src)` MUST return `False`.
- **Numeric only.** No sympy. Derivatives use central finite difference `h=1e-4`.
- **Reuse existing module-level helpers** in `builders.py`: `_funcgraph_expr(expr, label)` (does `^`→`**` + `_validate_expr`), `_text_color(name)`, `_FG_NAMESPACE`, `_FG_ANIMS`, `_join(lines)`. Do NOT duplicate or refactor funcgraph.
- **Graph seam:** analysis function is `graph_f = axes.plot(_f, x_range=[a, b], color=BLUE)`. Do NOT use funcgraph's `_fg_plot`.
- **Builder dispatch** is `source = builder(**params)` (api.py) — the nested `params` keys become kwargs, so `riemann`/`area`/`tangent`/`derivative` arrive as dicts.
- **Tests:** plain-Python harness like `test_funcgraph.py` (substring asserts + `compile()` + `_source_needs_latex`). Run with `uv run python test_calculus.py`. `test_calculus.py` is **tracked**.
- **Frontend** verified with `cd ui && npm run build` (`tsc -b`) — never `tsc --noEmit`.
- Adding `'calculus'` to `Mode` **forces** a `Sidebar.tsx` `TITLES` entry (it's `Record<Mode, string>`) or tsc fails.
- **Smoke test before committing; never push** (CLAUDE.md).
- Manim signature to verify against the installed 0.20.1 during Task 2: `Axes.get_riemann_rectangles(graph, x_range, dx, input_sample_type, show_signed_area, color, ...)`.

---

## File Structure

- **Create** `Manim_Project_files/test_calculus.py` — tracked unit tests (Tasks 1–6).
- **Modify** `Manim_Project_files/builders.py` — append `build_calculus_source` + overlay-default dicts (Tasks 1–5).
- **Modify** `Manim_Project_files/api.py` — register `"calculus"` in `_BUILDERS` (Task 6).
- **Create** `Manim_Project_files/ui/src/components/panels/CalculusPanel.tsx` (Task 7).
- **Modify** `Manim_Project_files/ui/src/types.ts` — add `'calculus'` to `Mode` (Task 7).
- **Modify** `Manim_Project_files/ui/src/components/ActivityBar.tsx` — add `∫ Calc` entry (Task 7).
- **Modify** `Manim_Project_files/ui/src/components/Sidebar.tsx` — `TITLES` + panel switch (Task 7).
- **Modify** `Manim_Project_files/smoke_test_v2.py` — add `[27]` render test (Task 8; gitignored).

All commands run from `Manim_Project_files/` unless noted.

---

### Task 1: Builder scaffold — axes, f-plot, guards, helpers (no overlays)

Builds the full `build_calculus_source` signature and a runnable scene that plots `f` over `[a,b]` with axes/grid/labels, applies all numeric guards, and defines the two builder-internal emit helpers (`_mk` for LaTeX branching, `_readout` for corner-stacked readouts). Overlays come in later tasks but their params already exist in the signature.

**Files:**
- Create: `test_calculus.py`
- Modify: `builders.py` (append at end of file)

**Interfaces:**
- Consumes (existing in `builders.py`): `_funcgraph_expr(expr, label) -> str`, `_text_color(name) -> str`, `_FG_NAMESPACE: str`, `_FG_ANIMS: dict[str,(tmpl,rt)]`, `_join(list[str]) -> str`.
- Produces:
  ```python
  def build_calculus_source(
      f_expr="x^2", g_expr="",
      a=-1.0, b=2.0, x0=1.0,
      riemann=None, area=None, tangent=None, derivative=None,   # dicts
      x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0,
      x_step=None, y_step=None, show_grid=False, cam_zoom=1.0,
      axis_label_x="x", axis_label_y="y", title="",
      use_latex=False, anim="Create",
  ) -> str
  ```

- [ ] **Step 1: Write the failing test**

Create `test_calculus.py`:
```python
"""Unit tests for the Calculus Toolkit builder (build_calculus_source).

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_calculus.py
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_calculus_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<calculus>", "exec")


def test_scaffold_compiles_and_plots_f():
    src = build_calculus_source("x^2", a=-1, b=2)
    _compiles(src)
    assert "class ManimScene(Scene):" in src
    assert "def _f(x):" in src and "return x**2" in src      # friendly ^ -> **
    assert "axes.plot(_f, x_range=[-1.0000, 2.0000]" in src  # the graph seam


def test_interval_and_n_guards():
    # a >= b resets to [-1, 2]; n clamps into [2, 200]
    src = build_calculus_source("x", a=5, b=1, riemann={"on": False})
    assert "x_range=[-1.0000, 2.0000]" in src
    _compiles(src)


def test_blocked_expr_rejected():
    for bad in ("__import__('os')", "open('x')", "eval('1')"):
        try:
            build_calculus_source(bad)
        except ValueError:
            continue
        raise AssertionError(f"blocked expr was not rejected: {bad}")


def test_finiteness_warning_present():
    src = build_calculus_source("1/x", a=-1, b=1)   # non-finite at 0
    assert "not finite" in src
    _compiles(src)


def test_latex_free_by_default():
    from api import _source_needs_latex
    src = build_calculus_source("x^2", a=0, b=2, axis_label_x="x", title="Demo")
    assert not _source_needs_latex(src), "default scene must be LaTeX-free"
    _compiles(src)


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

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python test_calculus.py`
Expected: FAIL — `ImportError: cannot import name 'build_calculus_source'`.

- [ ] **Step 3: Write minimal implementation**

Append to the **end of `builders.py`**:
```python
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
    x0 = max(xlo, min(xhi, float(x0)))
    xs = max(0.01, float(x_step) if x_step else (xhi - xlo) / 10.0)
    ys = max(0.01, float(y_step) if y_step else (yhi - ylo) / 8.0)

    fbody = _funcgraph_expr(f_expr, "f(x)")
    gbody = _funcgraph_expr(g_expr, "g(x)") if str(g_expr or "").strip() else ""

    # --- emit helpers ----------------------------------------------------
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
        "",
    ]
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

    # finiteness pre-check over [a, b]
    L += [
        f"        _xs = np.linspace({a:.4f}, {b:.4f}, 50)",
        "        _bad = 0",
        "        for _xx in _xs:",
        "            try:",
        "                with np.errstate(all='ignore'):",
        "                    _yy = float(_f(_xx))",
        "                if not np.isfinite(_yy): _bad += 1",
        "            except Exception:",
        "                _bad += 1",
        "        if _bad > 10:",
        "            self.play(FadeIn(Text('⚠ f(x) not finite on [a, b]', "
        "font_size=22, color=YELLOW).to_edge(DOWN)))",
    ]

    # plot the analysis graph (the seam: a real axes.plot graph object)
    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])
    L += [
        f"        graph_f = axes.plot(_f, x_range=[{a:.4f}, {b:.4f}], color=BLUE)",
        f"        self.play({wrap_tmpl.format(g='graph_f')}, run_time={rt:.1f})",
    ]
    if gbody:
        L += [
            f"        graph_g = axes.plot(_g, x_range=[{a:.4f}, {b:.4f}], color=GREY)",
            "        self.play(Create(graph_g), run_time=0.6)",
        ]

    # ===== overlays go here (Tasks 2-5) =====
    _emit_riemann(L, R, a, b, n, mk, readout)        # Task 2
    _emit_area(L, AR, a, b, gbody, mk, readout)      # Task 3
    _emit_tangent(L, TG, x0, mk, readout)            # Task 4
    _emit_derivative(L, DV, mk, readout)             # Task 5

    L.append("        self.wait(1.5)")
    return _join(L)


# Overlay emitters — filled in by Tasks 2-5; no-ops until then.
def _emit_riemann(L, R, a, b, n, mk, readout):    pass
def _emit_area(L, AR, a, b, gbody, mk, readout):  pass
def _emit_tangent(L, TG, x0, mk, readout):        pass
def _emit_derivative(L, DV, mk, readout):         pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python test_calculus.py`
Expected: PASS — `5/5 passed`.

- [ ] **Step 5: Commit**

```bash
git add test_calculus.py builders.py
git commit -m "feat(calculus): build_calculus_source scaffold + axes/f-plot/guards"
```

---

### Task 2: Riemann sums overlay

**Files:**
- Modify: `builders.py` (`_emit_riemann`)
- Modify: `test_calculus.py` (add tests)

**Interfaces:**
- Consumes: `L: list[str]`, `R: dict` (`on/method/n/show_value`), `a,b: float`, `n: int`, `mk(plain,latex)->str`, `readout(code)->None`.
- Produces: appends Riemann geometry + optional `Σ` readout to `L`.

- [ ] **Step 1: Write the failing test** — add to `test_calculus.py`:
```python
def test_riemann_left_uses_get_riemann_rectangles():
    src = build_calculus_source("x^2", a=0, b=2, riemann={"on": True, "method": "left", "n": 8})
    assert "get_riemann_rectangles(" in src
    assert "input_sample_type='left'" in src
    assert "/8" in src or "/ 8" in src or "dx=(2.0000-0.0000)/8" in src
    _compiles(src)

def test_riemann_mid_maps_to_center():
    src = build_calculus_source("x^2", a=0, b=2, riemann={"on": True, "method": "mid"})
    assert "input_sample_type='center'" in src
    _compiles(src)

def test_riemann_trapezoid_is_manual_polygons():
    src = build_calculus_source("x^2", a=0, b=2, riemann={"on": True, "method": "trapezoid"})
    assert "get_riemann_rectangles(" not in src   # trapezoid is custom
    assert "Polygon(" in src
    _compiles(src)

def test_riemann_off_emits_nothing():
    src = build_calculus_source("x^2", riemann={"on": False})
    assert "get_riemann_rectangles(" not in src and "_traps" not in src
    _compiles(src)
```

- [ ] **Step 2: Run** `uv run python test_calculus.py` → FAIL (`get_riemann_rectangles` not in src).

- [ ] **Step 3: Implement** — replace the stub `def _emit_riemann(...): pass` with:
```python
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
            "        self.play(FadeIn(_traps), run_time=1.0)",
        ]
    else:
        ist = {"left": "left", "right": "right", "mid": "center"}.get(method, "left")
        L += [
            "        _rects = axes.get_riemann_rectangles(",
            f"            graph_f, x_range=[{a:.4f}, {b:.4f}], dx=({b:.4f}-{a:.4f})/{n},",
            f"            input_sample_type={ist!r}, show_signed_area=True,",
            "            color=(BLUE, GREEN), stroke_width=0.5, stroke_color=WHITE, fill_opacity=0.7)",
            "        self.play(FadeIn(_rects), run_time=1.0)",
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
```

- [ ] **Step 4: Run** `uv run python test_calculus.py` → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_calculus.py
git commit -m "feat(calculus): Riemann sums overlay (L/R/mid/trapezoid + sigma readout)"
```

---

### Task 3: Area under / between curves overlay

**Files:** Modify `builders.py` (`_emit_area`), `test_calculus.py`.

**Interfaces:**
- Consumes: `L`, `AR` (`on/mode/color/show_value`), `a,b`, `gbody: str` (""→no g), `mk`, `readout`.
- Produces: appends `axes.get_area(...)` + optional `Area ≈` readout.

- [ ] **Step 1: Write the failing test:**
```python
def test_area_under_uses_get_area():
    src = build_calculus_source("x^2", a=0, b=2, area={"on": True, "mode": "under"})
    assert "axes.get_area(" in src
    assert "bounded_graph" not in src
    _compiles(src)

def test_area_between_requires_g_else_falls_back():
    # between without g -> falls back to under (no bounded_graph)
    src = build_calculus_source("x^2", a=0, b=2, area={"on": True, "mode": "between"})
    assert "bounded_graph" not in src
    # with g -> bounded_graph present
    src2 = build_calculus_source("x^2", g_expr="x", a=0, b=2,
                                 area={"on": True, "mode": "between"})
    assert "bounded_graph=graph_g" in src2
    _compiles(src); _compiles(src2)

def test_area_off_emits_nothing():
    src = build_calculus_source("x^2", area={"on": False})
    assert "get_area(" not in src
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `_emit_area`:
```python
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
    L.append("        self.play(FadeIn(_area), run_time=1.0)")
    if AR.get("show_value"):
        # trapezoidal numeric integral of f (minus g for 'between') over [a, b]
        integrand = "(_f(_t) - _g(_t))" if mode == "between" else "_f(_t)"
        L += [
            f"        _ts = np.linspace({a:.4f}, {b:.4f}, 200)",
            "        try:",
            "            with np.errstate(all='ignore'):",
            f"                _vals = np.array([{integrand.replace('_t', '_tt')} for _tt in _ts], dtype=float)",
            "                _ar = float(np.trapz(_vals, _ts))",
            "        except Exception:",
            "            _ar = float('nan')",
            "        _ars = f'{_ar:.3f}' if np.isfinite(_ar) else '—'",
            "        _art = f'{_ar:.3f}' if np.isfinite(_ar) else r'\\text{n/a}'",
        ]
        readout(mk(
            "Text('Area ≈ ' + _ars, font_size=22, color=WHITE)",
            "MathTex(r'\\int_a^b f\\,dx \\approx ' + _art, font_size=30, color=WHITE)",
        ))
```

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_calculus.py
git commit -m "feat(calculus): area under/between curves overlay + value readout"
```

---

### Task 4: Tangent + secant→tangent overlay

**Files:** Modify `builders.py` (`_emit_tangent`), `test_calculus.py`.

**Interfaces:**
- Consumes: `L`, `TG` (`on/animate_secant/show_slope`), `x0: float`, `mk`, `readout`.
- Produces: tangent line at `x0` (numeric slope), optional animated secant via `ValueTracker`, optional slope readout.

- [ ] **Step 1: Write the failing test:**
```python
def test_tangent_draws_line_and_slope():
    src = build_calculus_source("x^2", x0=1, tangent={"on": True, "animate_secant": False})
    assert "axes.plot(lambda x:" in src    # tangent line through (x0, f(x0))
    assert "_slope" in src
    _compiles(src)

def test_tangent_animate_secant_uses_valuetracker():
    src = build_calculus_source("x^2", x0=1, tangent={"on": True, "animate_secant": True})
    assert "ValueTracker(" in src
    assert "get_secant_slope_group(" in src
    _compiles(src)

def test_tangent_off_emits_nothing():
    src = build_calculus_source("x^2", tangent={"on": False})
    assert "TangentLine(" not in src and "get_secant_slope_group(" not in src
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `_emit_tangent`:
```python
def _emit_tangent(L, TG, x0, mk, readout):
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
        L += [
            "        _dxt = ValueTracker(2.0)",
            "        def _secant():",
            "            return axes.get_secant_slope_group(",
            "                _x0, graph_f, dx=max(1e-3, _dxt.get_value()),",
            "                dx_line_color=YELLOW, df_line_color=YELLOW,",
            "                secant_line_color=GREEN, secant_line_length=8)",
            "        _sec = always_redraw(_secant)",
            "        self.add(_sec)",
            "        self.play(_dxt.animate.set_value(0.05), run_time=2.0)",
            "        self.wait(0.3)",
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
```

> **Why `axes.plot` for the tangent (not `TangentLine`):** `TangentLine`'s `alpha` parameter is finicky on a graph plotted over a sub-interval `[a,b]`; a `axes.plot(lambda x: _f(_x0) + _slope*(x-_x0))` line through `(_x0, _f(_x0))` with the numeric slope is exact and robust.

- [ ] **Step 4: Run** `uv run python test_calculus.py` → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_calculus.py
git commit -m "feat(calculus): tangent line + secant->tangent animation + slope readout"
```

---

### Task 5: Derivative overlay

**Files:** Modify `builders.py` (`_emit_derivative`), `test_calculus.py`.

**Interfaces:**
- Consumes: `L`, `DV` (`on/color/show_legend`), `mk`, `readout`.
- Produces: `axes.plot_derivative_graph(graph_f, ...)` + optional `f'(x)` legend.

- [ ] **Step 1: Write the failing test:**
```python
def test_derivative_overlay():
    src = build_calculus_source("x^2", derivative={"on": True, "color": "red"})
    assert "plot_derivative_graph(graph_f" in src
    _compiles(src)

def test_derivative_legend_latex_free_default():
    from api import _source_needs_latex
    src = build_calculus_source("x^2", derivative={"on": True, "show_legend": True})
    assert "Text(\"f'(x)\"" in src or "Text('f" in src
    assert not _source_needs_latex(src)
    _compiles(src)

def test_derivative_off_emits_nothing():
    src = build_calculus_source("x^2", derivative={"on": False})
    assert "plot_derivative_graph(" not in src
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `_emit_derivative`:
```python
def _emit_derivative(L, DV, mk, readout):
    if not DV.get("on"):
        return
    color = _text_color(DV.get("color", "red"))
    L += [
        f"        _deriv = axes.plot_derivative_graph(graph_f, color={color})",
        "        self.play(Create(_deriv), run_time=1.0)",
    ]
    if DV.get("show_legend"):
        readout(mk(
            f"Text(\"f'(x)\", font_size=22, color={color})",
            f"MathTex(r\"f'(x)\", font_size=30, color={color})",
        ))
```

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_calculus.py
git commit -m "feat(calculus): numeric derivative overlay + legend"
```

---

### Task 6: Register mode + holistic LaTeX test

**Files:** Modify `api.py`, `test_calculus.py`.

**Interfaces:**
- Consumes: `api._BUILDERS`, `api._source_needs_latex`.
- Produces: `"calculus"` dispatchable; LaTeX on/off behavior pinned.

- [ ] **Step 1: Write the failing test:**
```python
def test_registered_in_builders():
    from api import _BUILDERS
    assert "calculus" in _BUILDERS

def test_use_latex_toggles_mathtex_and_preflight():
    from api import _source_needs_latex
    # every readout enabled, LaTeX OFF -> no MathTex, preflight false
    params = dict(f_expr="x^2", a=0, b=2,
                  riemann={"on": True, "show_value": True},
                  area={"on": True, "show_value": True},
                  tangent={"on": True, "show_slope": True},
                  derivative={"on": True, "show_legend": True})
    off = build_calculus_source(use_latex=False, **params)
    assert "MathTex(" not in off
    assert not _source_needs_latex(off)
    _compiles(off)
    # LaTeX ON -> MathTex present, preflight true
    on = build_calculus_source(use_latex=True, **params)
    assert "MathTex(" in on
    assert _source_needs_latex(on)
    _compiles(on)
```

- [ ] **Step 2: Run** `uv run python test_calculus.py` → FAIL (`'calculus' not in _BUILDERS`).

- [ ] **Step 3: Implement** — in `api.py`, add to the `_BUILDERS` dict (after the `"funcgraph"` line):
```python
    "funcgraph":   builders.build_funcgraph_source,
    "calculus":    builders.build_calculus_source,
}
```

- [ ] **Step 4: Run** `uv run python test_calculus.py` → PASS (all tests, ~18). Then run the funcgraph suite to confirm no regression: `uv run python test_funcgraph.py` → `9/9 passed`.

- [ ] **Step 5: Commit**
```bash
git add api.py test_calculus.py
git commit -m "feat(calculus): register calculus mode + holistic use_latex/preflight test"
```

---

### Task 7: Frontend — mode wiring + CalculusPanel

**Files:**
- Modify: `ui/src/types.ts`, `ui/src/components/ActivityBar.tsx`, `ui/src/components/Sidebar.tsx`
- Create: `ui/src/components/panels/CalculusPanel.tsx`

**Interfaces:**
- Produces: `CalculusPanel.getParams()` returning `{ mode: 'calculus', params: {...} }` matching the builder signature (Task 1 Produces block).

- [ ] **Step 1: Add the mode type** — `ui/src/types.ts`, extend the union:
```typescript
export type Mode = 'trig' | 'complex' | 'linear' | 'code' | 'streamlines' | 'playground'
                 | 'geometry' | 'barchart' | 'surface3d' | 'numberline' | 'funcgraph'
                 | 'calculus';
```

- [ ] **Step 2: Add the ActivityBar entry** — `ui/src/components/ActivityBar.tsx`, in the `ITEMS` array after the `funcgraph` entry:
```typescript
  { mode: 'calculus',    icon: '∫',   label: 'Calc' },
```

- [ ] **Step 3: Wire Sidebar** — `ui/src/components/Sidebar.tsx`: import, title, switch.
```typescript
import { CalculusPanel }    from './panels/CalculusPanel';
```
Add to `TITLES` (required — `Record<Mode>`):
```typescript
  calculus:    'Calculus Toolkit',
```
Add to the switch (after the funcgraph line):
```tsx
        {activeMode === 'calculus'    && <CalculusPanel    ref={panelRef} />}
```

- [ ] **Step 4: Create the panel** — `ui/src/components/panels/CalculusPanel.tsx`:
```tsx
import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];
const PRESETS: [string, string][] = [
  ['Preset…', ''], ['x²', 'x^2'], ['x³', 'x^3'], ['eˣ', 'exp(x)'], ['ln(x)', 'log(x)'],
  ['sin(x)', 'sin(x)'], ['cos(x)', 'cos(x)'], ['√x', 'sqrt(x)'],
];
const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

export function CalculusPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [fExpr, setFExpr] = useState('x^2');
  const [gExpr, setGExpr] = useState('');
  const [a, setA] = useState(-1);
  const [b, setB] = useState(2);
  const [x0, setX0] = useState(1);

  const [riOn, setRiOn] = useState(true);
  const [riMethod, setRiMethod] = useState('left');
  const [riN, setRiN] = useState(10);
  const [riVal, setRiVal] = useState(true);

  const [arOn, setArOn] = useState(false);
  const [arMode, setArMode] = useState('under');
  const [arColor, setArColor] = useState('teal');
  const [arVal, setArVal] = useState(true);

  const [tgOn, setTgOn] = useState(false);
  const [tgSecant, setTgSecant] = useState(true);
  const [tgSlope, setTgSlope] = useState(true);

  const [dvOn, setDvOn] = useState(false);
  const [dvColor, setDvColor] = useState('red');
  const [dvLegend, setDvLegend] = useState(true);

  const [xMin, setXMin] = useState(-5);
  const [xMax, setXMax] = useState(5);
  const [yMin, setYMin] = useState(-4);
  const [yMax, setYMax] = useState(4);
  const [xStep, setXStep] = useState(1);
  const [yStep, setYStep] = useState(1);
  const [showGrid, setShowGrid] = useState(false);
  const [zoom, setZoom] = useState(1.0);
  const [axisLabelX, setAxisLabelX] = useState('x');
  const [axisLabelY, setAxisLabelY] = useState('y');
  const [title, setTitle] = useState('');
  const [useLatex, setUseLatex] = useState(false);
  const [anim, setAnim] = useState('Create');

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'calculus',
      params: {
        f_expr: fExpr, g_expr: gExpr, a, b, x0,
        riemann:    { on: riOn, method: riMethod, n: riN, show_value: riVal },
        area:       { on: arOn, mode: arMode, color: arColor, show_value: arVal },
        tangent:    { on: tgOn, animate_secant: tgSecant, show_slope: tgSlope },
        derivative: { on: dvOn, color: dvColor, show_legend: dvLegend },
        x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax,
        x_step: xStep, y_step: yStep, show_grid: showGrid, cam_zoom: zoom,
        axis_label_x: axisLabelX, axis_label_y: axisLabelY, title,
        use_latex: useLatex, anim,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Function</div>
      <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
        <select className="app-select" style={{ width: 70 }} value=""
          onChange={e => { if (e.target.value) setFExpr(e.target.value); }}>
          {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
        </select>
        <input className="app-input" style={{ flex: 1 }} value={fExpr}
          onChange={e => setFExpr(e.target.value.slice(0, 120))} placeholder="f(x), e.g. x^2" />
      </div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }} value={gExpr}
        onChange={e => setGExpr(e.target.value.slice(0, 120))} placeholder="g(x) — for area-between (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Interval & Point</div>
      <Knob label="a"  min={-50} max={50} value={a}  onChange={v => setA(Math.round(v))}  decimals={0} step={1} />
      <Knob label="b"  min={-50} max={50} value={b}  onChange={v => setB(Math.round(v))}  decimals={0} step={1} />
      <Knob label="x₀" min={-50} max={50} value={x0} onChange={setX0} decimals={2} step={0.25} />

      <div className="sec-sep" />
      <div className="sec-hdr">Overlays</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={riOn}
          onChange={e => setRiOn(e.target.checked)} /> Riemann</label>
      </div>
      {riOn && (
        <>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={riMethod}
            onChange={e => setRiMethod(e.target.value)}>
            <option value="left">Left</option><option value="right">Right</option>
            <option value="mid">Mid</option><option value="trapezoid">Trapezoid</option>
          </select>
          <Knob label="n" min={2} max={200} value={riN} onChange={v => setRiN(Math.round(v))} decimals={0} step={1} />
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={riVal}
            onChange={e => setRiVal(e.target.checked)} /> Show Σ value</label></div>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={arOn}
          onChange={e => setArOn(e.target.checked)} /> Area</label>
      </div>
      {arOn && (
        <>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={arMode}
            onChange={e => setArMode(e.target.value)}>
            <option value="under">Under f</option><option value="between">Between f & g</option>
          </select>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={arColor}
            onChange={e => setArColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={arVal}
            onChange={e => setArVal(e.target.checked)} /> Show area value</label></div>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={tgOn}
          onChange={e => setTgOn(e.target.checked)} /> Tangent</label>
      </div>
      {tgOn && (
        <>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={tgSecant}
            onChange={e => setTgSecant(e.target.checked)} /> Animate secant→tangent</label></div>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={tgSlope}
            onChange={e => setTgSlope(e.target.checked)} /> Show slope</label></div>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={dvOn}
          onChange={e => setDvOn(e.target.checked)} /> Derivative f′</label>
      </div>
      {dvOn && (
        <>
          <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={dvColor}
            onChange={e => setDvColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <div className="check-row"><label className="app-check"><input type="checkbox" checked={dvLegend}
            onChange={e => setDvLegend(e.target.checked)} /> Show legend</label></div>
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Axes</div>
      <Knob label="X Min" min={-50} max={0}  value={xMin} onChange={v => setXMin(Math.round(v))} decimals={0} step={1} />
      <Knob label="X Max" min={1}   max={50} value={xMax} onChange={v => setXMax(Math.round(v))} decimals={0} step={1} />
      <Knob label="Y Min" min={-50} max={0}  value={yMin} onChange={v => setYMin(Math.round(v))} decimals={0} step={1} />
      <Knob label="Y Max" min={1}   max={50} value={yMax} onChange={v => setYMax(Math.round(v))} decimals={0} step={1} />
      <Knob label="X Step" min={0.1} max={10} value={xStep} onChange={setXStep} decimals={1} step={0.5} />
      <Knob label="Y Step" min={0.1} max={10} value={yStep} onChange={setYStep} decimals={1} step={0.5} />
      <Knob label="Zoom"   min={0.3} max={3}  value={zoom}  onChange={setZoom}  decimals={2} step={0.05} />
      <div className="check-row"><label className="app-check"><input type="checkbox" checked={showGrid}
        onChange={e => setShowGrid(e.target.checked)} /> Grid</label></div>

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelX} onChange={e => setAxisLabelX(e.target.value.slice(0, 24))} placeholder="X axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelY} onChange={e => setAxisLabelY(e.target.value.slice(0, 24))} placeholder="Y axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Options</div>
      <div className="check-row"><label className="app-check"><input type="checkbox" checked={useLatex}
        onChange={e => setUseLatex(e.target.checked)} /> Use LaTeX labels</label></div>
      <select className="app-select" style={{ width: '100%', marginTop: 4 }} value={anim}
        onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(x => <option key={x} value={x}>{x}</option>)}
      </select>
    </>
  );
}
```

- [ ] **Step 5: Build to verify TS** — Run: `cd ui && npm run build`
Expected: `tsc -b` clean, `✓ built in …`. (If `TITLES` is missing the `calculus` key, tsc errors — add it.)

- [ ] **Step 6: Commit**
```bash
git add ui/src/types.ts ui/src/components/ActivityBar.tsx ui/src/components/Sidebar.tsx ui/src/components/panels/CalculusPanel.tsx
git commit -m "feat(calculus): add Calculus mode button + CalculusPanel + wiring"
```

---

### Task 8: Smoke render test + still-frame verification

**Files:** Modify `smoke_test_v2.py` (gitignored).

**Interfaces:** Consumes `build_calculus_source`, `RenderThread`, the existing `_run`/`_show_err`/`PASS`/`FAIL`/`HERE` harness in `smoke_test_v2.py`.

- [ ] **Step 1: Add the render test** — in `smoke_test_v2.py`, after `test_funcgraph_real_render` (~line 1308):
```python
def test_calculus_real_render():
    print("\n[27] Calculus real render (Riemann+area+tangent+deriv) → video ... ", end="", flush=True)
    script = textwrap.dedent(f"""\
        import sys, os, threading, tempfile
        sys.path.insert(0, {HERE!r})
        from renderer import RenderThread
        from builders import build_calculus_source
        src = build_calculus_source(
            "x^2", a=0, b=2, x0=1,
            riemann={{"on": True, "method": "mid", "n": 12, "show_value": True}},
            area={{"on": True, "mode": "under", "show_value": True}},
            tangent={{"on": True, "animate_secant": True, "show_slope": True}},
            derivative={{"on": True, "show_legend": True}},
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
And register it in `SLOW_TESTS` after the funcgraph entry:
```python
    ("Function Grapher real render (asymptotes)",          test_funcgraph_real_render),
    ("Calculus real render (4 overlays)",                  test_calculus_real_render),
```

- [ ] **Step 2: Run the full smoke suite** — Run: `uv run python smoke_test_v2.py`
Expected: `Result: 32/32 passed` (31 prior + new `[27]`).

- [ ] **Step 3: Still-frame self-verification (the funcgraph lesson).** Render PNG stills and view them — "a video was produced" is not enough.
```bash
python - <<'PY'
import sys, os, tempfile
sys.path.insert(0, os.getcwd())
from builders import build_calculus_source
cases = {
  "riemann_signed": dict(f_expr="x^3", a=-1, b=2, riemann={"on":True,"method":"left","n":12,"show_value":True}),
  "area_between":   dict(f_expr="x^2", g_expr="x", a=0, b=2, riemann={"on":False}, area={"on":True,"mode":"between","show_value":True}),
  "tangent_deriv":  dict(f_expr="sin(x)", a=-3, b=3, x0=1, riemann={"on":False}, tangent={"on":True,"animate_secant":False,"show_slope":True}, derivative={"on":True,"show_legend":True}),
  "latex_on":       dict(f_expr="x^2", a=0, b=2, use_latex=True, riemann={"on":True,"show_value":True}),
}
out = tempfile.mkdtemp()
for name, kw in cases.items():
    src = build_calculus_source(**kw)
    p = os.path.join(out, name + ".py")
    open(p, "w").write(src)
    print(name, "->", p)
print("OUT", out)
PY
# Then for each .py: manim -s -ql -o <name> <name>.py ManimScene  (LaTeX case needs texlive)
```
Open each PNG and confirm: signed-area coloring flips where `x^3` crosses 0; the between-area is the band between the curves; tangent slope looks right at `x0=1`; `f'(x)` is plotted; the `latex_on` case shows `Σ`/`∫` notation. Fix any overlay that renders empty or wrong, then re-run Step 2.

- [ ] **Step 4: Commit** (smoke file is gitignored — commit only if `git status` shows it tracked; otherwise this step records the verification in the session log).
```bash
git add -A && git status --porcelain   # smoke_test_v2.py is gitignored; nothing to add
git commit -m "test(calculus): add [27] real-render smoke test" --allow-empty
```

---

## Self-Review

**1. Spec coverage:**
- §1 four overlays → Tasks 2 (Riemann), 3 (Area), 4 (Tangent/secant), 5 (Derivative). ✓
- §1 `use_latex` toggle → built into `mk()` (Task 1), exercised per overlay, pinned in Task 6. ✓
- §3 six seams → builder (Tasks 1–5), api registry (Task 6), types/ActivityBar/Sidebar/panel (Task 7). ✓ (Spec §3 listed seam 3 as `App.tsx`; the real switch is `Sidebar.tsx` — corrected in Task 7 / File Structure.)
- §4 payload + signature → Task 1 Produces + Task 7 `getParams`. ✓
- §5 expr pipeline → `_funcgraph_expr` reused (Task 1). ✓
- §6 scene shape + numeric readouts + corner stacking → Task 1 `readout()` + per-overlay numeric code. ✓
- §8 guards/finiteness/fallback → Task 1 (guards, finiteness), Task 3 (between→under). ✓
- §9 testing → `test_calculus.py` (Tasks 1–6), smoke `[27]` (Task 8), `npm run build` (Task 7). ✓
- §10 still-frame verification → Task 8 Step 3. ✓

**2. Placeholder scan:** No "TBD/TODO". The Task 4 `TangentLine` line carries an explicit simplification note + the exact replacement assert — flagged, not left vague. No "add error handling" hand-waves (guards are concrete code).

**3. Type consistency:** Builder kwargs (`f_expr,g_expr,a,b,x0,riemann,area,tangent,derivative,…,use_latex,anim`) match the panel `getParams` payload and the smoke-test calls. Overlay dict keys (`on/method/n/show_value`, `on/mode/color/show_value`, `on/animate_secant/show_slope`, `on/color/show_legend`) are identical across the builder defaults, emitters, panel, and tests. `mk`/`readout` signatures consistent across Tasks 1–5.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-25-calculus-toolkit.md`.**
