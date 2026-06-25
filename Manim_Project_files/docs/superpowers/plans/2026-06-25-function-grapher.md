# Function Grapher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `funcgraph` mode that plots multiple arbitrary `f(x)` curves on labeled Cartesian axes, generalizing the hardcoded trig panel.

**Architecture:** A new pure-Python builder `build_funcgraph_source` (params → Manim source) registered in `api._BUILDERS`, plus a React `FunctionGraphPanel` wired through the app's 6 mode seams. User expressions use friendly math syntax (`sin(x)`, `x^2`), validated by the existing `_validate_expr` AST blocklist and wrapped in a non-crashing safe-eval function. All labels are `Text` (never `MathTex`) so the mode works without LaTeX.

**Tech Stack:** Python 3.13, Manim 0.20.1 (FFmpeg required), React 19 + TypeScript + Vite, PyWebView bridge (`api.py`).

**Spec:** `docs/superpowers/specs/2026-06-25-function-grapher-design.md`

## Global Constraints

- Builders are invoked as `builder(**params)` — the panel's JSON `params` keys are exactly the builder's keyword-argument names.
- Numeric-format discipline: interpolate numbers with explicit formatting (`:.4f`), and data values with `repr()`/`!r`. Never inline an unformatted float.
- LaTeX-free: the generated source must NOT contain any token in `api._LATEX_TOKENS` (`MathTex`, `Tex`, `Title`, `get_axis_labels`, `add_coordinates`, `DecimalNumber`, …). Build all labels with `Text(...)`.
- Every user expression MUST pass `builders._validate_expr` (shared blocklist from `renderer._BLOCKED_CALLS` / `_BLOCKED_ATTRS`).
- Curve cap = 4. Default curve is `x^2`.
- Verify UI changes with `cd ui && npm run build` (`tsc -b`) — NOT `tsc --noEmit` (it gives false passes).
- Always run the relevant smoke/unit tests before each commit. NEVER push automatically (commits stay local on `ui/editor-redesign`).
- Panels use the React-19 `{ ref }`-as-prop style + `useImperativeHandle`; native `<select className="app-select">` is fine mid-panel.
- Co-author trailer on every commit: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: Builder — `build_funcgraph_source` + unit tests

**Files:**
- Modify: `builders.py` (append new section at end of file)
- Create: `test_funcgraph.py`

**Interfaces:**
- Consumes: `builders._validate_expr(expr, label, default)`, `builders._text_color(value)`, `builders._join(lines)` (all already in `builders.py`).
- Produces:
  - `_funcgraph_expr(expr, label) -> str` — friendly-syntax translate (`^`→`**`) then validate.
  - `build_funcgraph_source(curves, x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0, x_step=None, y_step=None, show_grid=False, cam_zoom=1.0, anim="Create", axis_label_x="x", axis_label_y="y", title="") -> str` where `curves` is `list[dict]` with keys `expr:str, color:str, label:str, style:str("solid"|"dashed"), width:float`.

- [ ] **Step 1: Write the failing tests** — create `test_funcgraph.py`:

```python
"""Unit tests for the Function Grapher builder (build_funcgraph_source).

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_funcgraph.py
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_funcgraph_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<funcgraph>", "exec")


def test_single_curve_compiles():
    src = build_funcgraph_source([{"expr": "x^2", "color": "blue"}])
    _compiles(src)
    assert "axes.plot(_f0" in src
    assert "y = x**2" in src              # friendly ^ translated to **
    assert "use_smoothing=False" in src


def test_namespace_injected():
    src = build_funcgraph_source([{"expr": "sin(x)"}])
    assert "from numpy import (" in src
    assert "y = sin(x)" in src
    _compiles(src)


def test_strict_numpy_still_works():
    src = build_funcgraph_source([{"expr": "np.exp(-x**2)"}])
    assert "y = np.exp(-x**2)" in src
    _compiles(src)


def test_multiple_curves_and_dashed():
    src = build_funcgraph_source([
        {"expr": "x^2",    "color": "blue", "label": "f", "style": "solid"},
        {"expr": "sin(x)", "color": "red",  "label": "g", "style": "dashed"},
    ])
    assert "axes.plot(_f0" in src and "axes.plot(_f1" in src
    assert "DashedVMobject(g1" in src         # dashed applied to 2nd curve
    assert "DashedVMobject(g0" not in src      # 1st curve stays solid
    assert "Text('f'" in src and "Text('g'" in src
    _compiles(src)


def test_empty_or_blank_curves_fallback():
    src = build_funcgraph_source([])
    assert "y = x**2" in src                   # fallback to one x**2 curve
    _compiles(src)
    src2 = build_funcgraph_source([{"expr": "   "}])  # blank expr skipped
    assert "y = x**2" in src2
    _compiles(src2)


def test_axis_labels_and_title_latex_free():
    from api import _source_needs_latex     # the REAL preflight (word-boundary regex)
    src = build_funcgraph_source(
        [{"expr": "x"}], axis_label_x="x", axis_label_y="y", title="My Plot")
    assert "Text('x'" in src and "Text('y'" in src and "Text('My Plot'" in src
    assert not _source_needs_latex(src), "grapher source must not require LaTeX"
    _compiles(src)


def test_grid_and_zoom():
    src = build_funcgraph_source([{"expr": "x"}], show_grid=True, cam_zoom=2.0)
    assert "NumberPlane(" in src
    assert "config.frame_width" in src
    _compiles(src)


def test_blocked_expr_rejected():
    for bad in ("__import__('os')", "open('x')", "eval('1')"):
        try:
            build_funcgraph_source([{"expr": bad}])
        except ValueError:
            continue
        raise AssertionError(f"blocked expr was not rejected: {bad}")


def test_all_animation_styles_compile():
    for a in ("Create", "FadeIn", "Write", "GrowFromEdge", "DrawBorderThenFill"):
        _compiles(build_funcgraph_source([{"expr": "x"}], anim=a))


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

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_funcgraph.py`
Expected: FAIL — `ImportError: cannot import name 'build_funcgraph_source' from 'builders'`.

- [ ] **Step 3: Implement the builder** — append this section to the end of `builders.py`:

```python


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


def build_funcgraph_source(
    curves,
    x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0,
    x_step=None, y_step=None,
    show_grid=False, cam_zoom=1.0,
    anim="Create",
    axis_label_x="x", axis_label_y="y", title="",
):
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

    # --- header + friendly-math namespace --------------------------------
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
    ]
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
        L.append(f"        y_axis_lbl = Text({ylab!r}, font_size=24, color=WHITE).next_to(axes.y_axis, UP, buff=0.2)")
        intro.append("FadeIn(y_axis_lbl)")
    if ttl:
        L.append(f"        plot_title = Text({ttl!r}, font_size=30, color=WHITE).to_edge(UP, buff=0.3)")
        intro.append("FadeIn(plot_title)")
    if intro:
        L.append(f"        self.play({', '.join(intro)}, run_time=0.5)")

    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])

    for i, (body, color, label, style, width) in enumerate(clean):
        g, fn = f"g{i}", f"_f{i}"
        L += [
            f"        def {fn}(x):",
            "            try:",
            "                with np.errstate(all='ignore'):",
            f"                    y = {body}",
            "            except Exception:",
            "                return np.nan",
            "            return y if np.isfinite(y) else np.nan",
            f"        {g} = axes.plot({fn}, x_range=[{xlo:.4f}, {xhi:.4f}, {dx:.4f}], "
            f"color={color}, stroke_width={width:.2f}, use_smoothing=False)",
        ]
        if style == "dashed":
            L.append(f"        {g} = DashedVMobject({g}, num_dashes=40)")
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

    L.append("        self.wait(1.5)")
    return _join(L)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_funcgraph.py`
Expected: PASS — `9/9 passed`, exit code 0.

- [ ] **Step 5: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/builders.py Manim_Project_files/test_funcgraph.py
git commit -m "feat(funcgraph): add build_funcgraph_source builder + unit tests" \
           -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Register mode + early asymptote render verification

This locks the spec's one empirical risk (Manim's `nan` rendering) **before** any UI is built.

**Files:**
- Modify: `api.py` (the `_BUILDERS` dict, around line 103-113)
- Modify: `smoke_test_v2.py` (add a render test + register it in `SLOW_TESTS`)

**Interfaces:**
- Consumes: `builders.build_funcgraph_source` (Task 1), `renderer.RenderThread(source, flags, out_dir, on_done=cb)`.
- Produces: mode id `"funcgraph"` invocable via `Api.render("funcgraph", params_json)`.

- [ ] **Step 1: Register the builder** — in `api.py`, add the `funcgraph` line to `_BUILDERS`:

```python
_BUILDERS = {
    "trig":        builders.build_trig_source,
    "complex":     builders.build_complex_source,
    "linear":      builders.build_linear_source,
    "nonlinear":   builders.build_nonlinear_source,
    "code":        builders.build_code_source,
    "streamlines": builders.build_streamlines_source,
    "geometry":    builders.build_geometry_source,
    "barchart":    builders.build_barchart_source,
    "surface3d":   builders.build_surface3d_source,
    "numberline":  builders.build_numberline_source,
    "funcgraph":   builders.build_funcgraph_source,
}
```

- [ ] **Step 2: Add the render verification test** — in `smoke_test_v2.py`, add this function immediately before the `API_TESTS = [` line (around line 1266):

```python
# ===========================================================================
# [26] Function Grapher real render → handles asymptotes / domain gaps
# ===========================================================================

def test_funcgraph_real_render():
    print("\n[26] Function Grapher real render (asymptotes) → video ... ", end="", flush=True)

    script = textwrap.dedent(f"""\
        import sys, os, threading, tempfile
        sys.path.insert(0, {HERE!r})
        from renderer import RenderThread
        from builders import build_funcgraph_source
        src = build_funcgraph_source(
            [
                {{"expr": "1/x",     "color": "red"}},
                {{"expr": "tan(x)",  "color": "blue"}},
                {{"expr": "log(x)",  "color": "green"}},
                {{"expr": "sqrt(x)", "color": "yellow"}},
            ],
            x_min=-6, x_max=6, y_min=-5, y_max=5,
        )
        out    = tempfile.mkdtemp()
        result = []
        event  = threading.Event()
        def on_done(path):
            result.append(path)
            event.set()
        t = RenderThread(src, ['-ql'], out, on_done=on_done)
        t.start()
        ok = event.wait(timeout=90)
        t.join(5)
        if not ok or not result:
            print("TIMEOUT"); sys.exit(1)
        video = result[0]
        assert video,                  "on_done called with empty path"
        assert os.path.exists(video),  f"video file not found: {{video}}"
        print("ok:" + video)
    """)

    r = _run(script, timeout=120)
    if r.returncode == 0 and "ok:" in r.stdout:
        print(PASS); return True
    print(FAIL)
    if "TIMEOUT" in r.stdout:
        print("    (render timed out)")
    _show_err(r)
    return False
```

- [ ] **Step 3: Register it in `SLOW_TESTS`** — in `smoke_test_v2.py`, add the last entry to the `SLOW_TESTS` list (around line 1297):

```python
SLOW_TESTS = [
    ("Full real render → video produced",                  test_real_render_produces_video),
    ("Full render via Api → save pipeline",                test_real_render_save),
    ("Rendered output opens over HTTP",                    test_output_opens_over_http),
    ("Full GIF render → opens as image/gif over HTTP",     test_real_gif_render_opens),
    ("Full mp4 render → webm preview proxy over HTTP",     test_mp4_preview_proxy),
    ("Function Grapher real render (asymptotes)",          test_funcgraph_real_render),
]
```

- [ ] **Step 4: Run the new render test (via the full slow suite or standalone) to verify it passes**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python -c "import smoke_test_v2 as s; raise SystemExit(0 if s.test_funcgraph_real_render() else 1)"`
Expected: prints `[26] ... PASS` and `ok:/tmp/.../*.mp4`, exit code 0. (Render takes ~20-60s at `-ql`.)

- [ ] **Step 5: Visually verify nan handling, apply clamp fallback ONLY if needed**

Open the printed video path. Expected: `1/x` and `tan(x)` show clean breaks at their asymptotes; `log(x)` and `sqrt(x)` draw only over their valid domain (x>0); no full-height vertical streaks, no corrupted curves.

IF you instead see spurious vertical streaks across asymptotes or broken curves, edit the safe-eval emission in `builders.py` `build_funcgraph_source` to clamp instead of returning `nan` for infinities. Replace the 7 emitted `def {fn}` lines in the curve loop with:

```python
            f"        def {fn}(x):",
            "            try:",
            "                with np.errstate(all='ignore'):",
            f"                    y = {body}",
            "            except Exception:",
            "                return np.nan",
            "            if np.isnan(y):",
            "                return np.nan",
            f"            return float(np.clip(y, {ylo - 1.5 * (yhi - ylo):.4f}, {yhi + 1.5 * (yhi - ylo):.4f}))",
```

Then re-run Step 4 and re-inspect. (Domain gaps stay `nan`; infinities clamp to a band edge.) Re-run `uv run python test_funcgraph.py` to confirm the unit tests still pass after the edit.

- [ ] **Step 6: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/api.py Manim_Project_files/smoke_test_v2.py Manim_Project_files/builders.py
git commit -m "feat(funcgraph): register funcgraph mode + asymptote render smoke test" \
           -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — Function Grapher panel + mode wiring

**Files:**
- Modify: `ui/src/types.ts` (the `Mode` union, line 1-2)
- Modify: `ui/src/components/ActivityBar.tsx` (the `ITEMS` array)
- Modify: `ui/src/components/Sidebar.tsx` (import + `TITLES` + conditional render)
- Create: `ui/src/components/panels/FunctionGraphPanel.tsx`

**Interfaces:**
- Consumes: `PanelHandle` (`types.ts`), `Knob` (`../shared/Knob`). Mode id `"funcgraph"` and the param keys must match `build_funcgraph_source` (Task 1).
- Produces: `getParams()` returning `{ mode: 'funcgraph', params: { curves, x_min, x_max, y_min, y_max, x_step, y_step, show_grid, cam_zoom, anim, axis_label_x, axis_label_y, title } }`.

- [ ] **Step 1: Add `funcgraph` to the `Mode` union** — in `ui/src/types.ts`, replace lines 1-2:

```typescript
export type Mode = 'trig' | 'complex' | 'linear' | 'code' | 'streamlines' | 'playground'
                 | 'geometry' | 'barchart' | 'surface3d' | 'numberline' | 'funcgraph';
```

- [ ] **Step 2: Add the ActivityBar entry** — in `ui/src/components/ActivityBar.tsx`, insert the `funcgraph` item right after the `trig` entry in `ITEMS`:

```typescript
  { mode: 'trig',        icon: '∿',   label: 'Trig' },
  { mode: 'funcgraph',   icon: 'ƒ',   label: 'Graph' },
```

- [ ] **Step 3: Wire the Sidebar** — in `ui/src/components/Sidebar.tsx` make three edits.

(a) Add the import after the `TrigPanel` import:

```typescript
import { TrigPanel }         from './panels/TrigPanel';
import { FunctionGraphPanel } from './panels/FunctionGraphPanel';
```

(b) Add the title to the `TITLES` record (after the `trig` line):

```typescript
  trig:        'Trigonometric Functions',
  funcgraph:   'Function Grapher',
```

(c) Add the conditional render (after the `trig` line):

```typescript
        {activeMode === 'trig'        && <TrigPanel        ref={panelRef} />}
        {activeMode === 'funcgraph'   && <FunctionGraphPanel ref={panelRef} />}
```

- [ ] **Step 4: Create the panel** — create `ui/src/components/panels/FunctionGraphPanel.tsx`:

```tsx
import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface Curve { expr: string; color: string; label: string; style: string; width: string }

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];

const PRESETS: [string, string][] = [
  ['Preset…', ''],
  ['x²', 'x^2'], ['x³', 'x^3'], ['eˣ', 'exp(x)'], ['ln(x)', 'log(x)'],
  ['|x|', 'abs(x)'], ['√x', 'sqrt(x)'], ['1/x', '1/x'], ['sin(x)', 'sin(x)'],
];

const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];

const DEFAULT_CURVES: Curve[] = [
  { expr: 'x^2', color: 'blue', label: 'f', style: 'solid', width: '2.5' },
];

export function FunctionGraphPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [curves, setCurves]       = useState<Curve[]>(DEFAULT_CURVES);
  const [xMin, setXMin]           = useState(-5);
  const [xMax, setXMax]           = useState(5);
  const [yMin, setYMin]           = useState(-4);
  const [yMax, setYMax]           = useState(4);
  const [xStep, setXStep]         = useState(1);
  const [yStep, setYStep]         = useState(1);
  const [showGrid, setShowGrid]   = useState(false);
  const [zoom, setZoom]           = useState(1.0);
  const [anim, setAnim]           = useState('Create');
  const [axisLabelX, setAxisLabelX] = useState('x');
  const [axisLabelY, setAxisLabelY] = useState('y');
  const [title, setTitle]         = useState('');

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

  useImperativeHandle(ref, () => ({
    getParams: () => ({
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
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Curves (up to 4)</div>
      {curves.map((c, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
            <select
              className="app-select"
              style={{ width: 70 }}
              value=""
              onChange={e => { if (e.target.value) updateCurve(i, 'expr', e.target.value); }}
            >
              {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
            </select>
            <input
              className="app-input"
              style={{ flex: 1 }}
              value={c.expr}
              onChange={e => updateCurve(i, 'expr', e.target.value.slice(0, 120))}
              placeholder="f(x), e.g. sin(x) + x^2"
            />
            <button
              className="mode-toggle__btn"
              style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
              onClick={() => removeCurve(i)}
              title="Remove curve"
            >×</button>
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
            <input
              className="knob__num"
              style={{ width: 44, textAlign: 'center' }}
              value={c.label}
              onChange={e => updateCurve(i, 'label', e.target.value.slice(0, 12))}
              placeholder="lbl"
            />
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

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelX} onChange={e => setAxisLabelX(e.target.value.slice(0, 24))} placeholder="X axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={axisLabelY} onChange={e => setAxisLabelY(e.target.value.slice(0, 24))} placeholder="Y axis label" />
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Animation</div>
      <select className="app-select" style={{ width: '100%' }} value={anim} onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(a => <option key={a} value={a}>{a}</option>)}
      </select>
    </>
  );
}
```

- [ ] **Step 5: Build the frontend to verify it compiles**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files/ui && npm run build`
Expected: `tsc -b` + Vite build succeed, exit code 0, no type errors. (If `Mode` got a member without a matching `TITLES` entry, `tsc` fails on the `Record<Mode,string>` exhaustiveness check — that's the safety net; fix the missing entry.)

- [ ] **Step 6: Commit**

```bash
cd /home/abhishek_billu/Documents/Atom/Manim_Project
git add Manim_Project_files/ui/src/types.ts \
        Manim_Project_files/ui/src/components/ActivityBar.tsx \
        Manim_Project_files/ui/src/components/Sidebar.tsx \
        Manim_Project_files/ui/src/components/panels/FunctionGraphPanel.tsx
git commit -m "feat(funcgraph): add Function Grapher panel + mode wiring" \
           -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Final integration gate

**Files:** none (verification only) — plus an auto-memory note.

**Interfaces:** Consumes everything from Tasks 1-3.

- [ ] **Step 1: Run the builder unit tests**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python test_funcgraph.py`
Expected: `9/9 passed`, exit 0.

- [ ] **Step 2: Run the full v2 smoke suite**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python smoke_test_v2.py`
Expected: `Result: 31/31 passed`, exit 0. (Was 30; +1 for the funcgraph render test.)

- [ ] **Step 3: Build the frontend**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files/ui && npm run build`
Expected: exit 0, no type errors.

- [ ] **Step 4: Manual end-to-end check in the running app**

Run: `cd /home/abhishek_billu/Documents/Atom/Manim_Project/Manim_Project_files && uv run python app.py --dev`
In the app: click the **ƒ Graph** activity-bar item. Add a second curve (`sin(x)`, dashed, red), set a title, click **Render**. Expected: a video with two curves on labeled axes, a title, and the legend labels — no LaTeX-required dialog. Close the app.

- [ ] **Step 5: Update auto-memory**

Edit `/home/abhishek_billu/.claude/projects/-home-abhishek-billu-Documents-Atom-Manim-Project/memory/feature_coverage_audit.md`: mark TIER 1 #1 (function grapher) as DONE with the commit hashes, and update `MEMORY.md` / `project_next_session.md` to point at the next Tier-1 item (calculus toolkit, which extends this panel). No git commit needed — memory lives outside the repo.

---

## Self-Review

**1. Spec coverage** (against `2026-06-25-function-grapher-design.md`):
- §3 six seams → Task 2 (builder reg, api), Task 3 (types/ActivityBar/Sidebar/panel). ✔
- §4 data model (`curves` list-of-dicts + range/grid/zoom/anim/label keys) → Task 1 signature + Task 3 `getParams`. ✔
- §5 expr pipeline (`^`→`**`, `_validate_expr`, numpy namespace, safe-eval, LaTeX-free) → Task 1 builder + `test_namespace_injected`/`test_blocked_expr_rejected`/`test_axis_labels_and_title_latex_free`. ✔
- §6 scene shape (Text labels, `use_smoothing=False`, `DashedVMobject`, anim set, zoom) → Task 1 builder + tests. ✔
- §7 panel (curves ≤4, presets, color/style/width/label, ranges/steps/grid/zoom, axis labels/title, animation) → Task 3. ✔
- §8 error handling (validation, nan wrapper, empty fallback, numeric discipline) → Task 1 builder + tests. ✔
- §9 testing (compile + real render + friendly/strict/blocked + LaTeX-free + `npm run build`) → Tasks 1, 2, 3, 4. ✔
- §10 risk (Manim nan render) → Task 2 Step 4-5 (render + eyeball + clamp fallback). ✔

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; the clamp fallback is fully written. ✔

**3. Type consistency:** Builder signature param names (`x_min`, `cam_zoom`, `axis_label_x`, `curves[].expr/color/label/style/width`) are identical in Task 1 (Python), Task 3 `getParams` (TS), and the render test (Task 2). `build_funcgraph_source` / `_funcgraph_expr` / `FunctionGraphPanel` names match across tasks. Mode id `"funcgraph"` consistent everywhere. ✔

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session via executing-plans, batched with checkpoints.
