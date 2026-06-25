# Function Grapher — Design Spec

- **Date:** 2026-06-25
- **Status:** Approved (design) — ready for implementation planning
- **Branch:** `ui/editor-redesign`
- **Roadmap item:** TIER 1 #1 (general Cartesian function grapher) — see `feature_coverage_audit`
- **Mode id:** `funcgraph`

---

## 1. Goal & Scope

Add a dedicated point-and-click mode that plots **multiple arbitrary `f(x)` curves** on
labeled Cartesian axes. It generalizes the existing trig panel — which is hardcoded to
sin/cos/tan — into an arbitrary-expression grapher, while leaving trig untouched.

### In scope (v1)
- Multiple `f(x)` curves (cap **4**).
- **Friendly math syntax** (`sin(x)`, `x^2`, `pi`, `e`, …); strict `np.sin(x)`/`x**2` also works.
- Per-curve: **color**, **legend label**, **line style** (solid/dashed), **stroke width**.
- **Preset function quick-picks** that fill the expression box.
- X/Y ranges + tick steps, **grid** toggle, **camera zoom**.
- **Axis labels** (x, y) + optional **title**.
- **Animation style** selector (reusing the trig set).

### Out of scope (explicit — future specs)
- **Calculus toolkit** (Riemann sums, area under/between curves, tangent/secant, derivative
  overlay) — roadmap #2. It will *extend this panel* in a later spec.
- **Numeric tick labels on axes** — `add_coordinates`/`add_numbers`/`DecimalNumber` pull in
  LaTeX (see §5). Deferred to keep the grapher LaTeX-free out of the box.
- Implicit multiplication, multi-variable, parametric/polar (separate roadmap items).

---

## 2. Key decisions (brainstorming log)

| Decision | Choice | Why |
|----------|--------|-----|
| Scope | Grapher only; calculus deferred | Clean shippable unit; matches roadmap #1/#2 split; calculus extends this later |
| Architecture | New dedicated `funcgraph` mode | Zero regression risk to trig; matches the per-mode pattern; lowest risk |
| Expr syntax | Friendly math (`^`→`**`, numpy namespace); strict `np.` still works | Accessibility is the point of a panel vs. the Playground |
| Extras included | All four: axis/title labels, legend labels, presets, line style | User-selected |
| Curve data shape | Cohesive `curves` list-of-dicts | Avoids BarChart's index-aligned parallel-array fragility |
| Curve cap | 4 | Between trig (3) and barchart (5) |
| Labels | `Text`-based — **not** `MathTex`/`get_axis_labels`/`Title` | Keeps the grapher LaTeX-free out of the box (preflight constraint, §5) |
| Smoothing | `use_smoothing=False` | More faithful for arbitrary `f(x)` with kinks/asymptotes |

---

## 3. Architecture — the 6 seams

A new mode in ManimStudio touches exactly six well-defined seams:

| Seam | File | Change |
|------|------|--------|
| Builder | `builders.py` | new `build_funcgraph_source(...)` |
| Registry | `api.py` | `"funcgraph": builders.build_funcgraph_source` in `_BUILDERS` |
| Mode type | `ui/src/types.ts` | add `'funcgraph'` to the `Mode` union |
| Activity bar | `ui/src/components/ActivityBar.tsx` | `{ mode: 'funcgraph', icon: 'ƒ', label: 'Graph' }` |
| Sidebar | `ui/src/components/Sidebar.tsx` | `TITLES.funcgraph = 'Function Grapher'`, import + conditional render line |
| Panel | `ui/src/components/panels/FunctionGraphPanel.tsx` | **new** — exposes `getParams()` via the ref handle |

The panel contract is uniform across the app: every panel exposes
`getParams() → { mode, params, sceneName }`, and `App.tsx` pipes that into
`getApi().render(...)`. `api.py` calls `builder(**params)`, so **the panel's JSON `params`
keys are exactly the builder's keyword arguments** — no glue layer.

---

## 4. Data model (`params` payload → builder signature)

The panel emits a cohesive `curves` list (preferred over BarChart's parallel arrays):

```jsonc
{
  "curves": [
    { "expr": "x^2",    "color": "blue", "label": "f", "style": "solid",  "width": 2.5 },
    { "expr": "sin(x)", "color": "red",  "label": "g", "style": "dashed", "width": 2.0 }
  ],
  "x_min": -5, "x_max": 5, "y_min": -4, "y_max": 4,
  "x_step": 1, "y_step": 1,
  "show_grid": false, "cam_zoom": 1.0,
  "anim": "Create",
  "axis_label_x": "x", "axis_label_y": "y", "title": ""
}
```

Builder signature (keyword args mirror the keys above):

```python
def build_funcgraph_source(
    curves,
    x_min=-5, x_max=5, y_min=-4, y_max=4,
    x_step=None, y_step=None,
    show_grid=False, cam_zoom=1.0,
    anim="Create",
    axis_label_x="x", axis_label_y="y", title="",
):
    ...
```

Per-curve dict fields: `expr` (str), `color` (key into the existing `TEXT_COLORS` map),
`label` (str, legend), `style` (`"solid"`|`"dashed"`), `width` (float stroke width).
Missing fields fall back to sensible defaults; `x_step`/`y_step` auto-derive from the range
when `None`.

---

## 5. Expression pipeline (the heart) — friendly syntax → validate → safe eval

For each curve's `expr`:

1. **Translate** `^` → `**` with a string-level pre-pass (users mean power, not XOR).
2. **Validate** via the existing `_validate_expr(expr, f"Curve {i} f(x)", default="x**2")`.
   This reuses the shared AST blocklist (rejects `open`/`eval`/`getattr`/`__…__`/etc.).
   Bad syntax or a blocked token raises `ValueError`, which `api.py` already surfaces as
   `"Build error: …"`.
3. **Namespace**: the generated source does both `import numpy as np` **and**
   `from numpy import sin, cos, tan, exp, log, log10, sqrt, sinh, cosh, tanh, arcsin,
   arccos, arctan, floor, ceil, pi, e` — so bare `sin(x)`/`pi` resolve *and* strict
   `np.sin(x)` still works. (`log` = natural log; `log10` for base-10 — stated in the panel
   hint. `abs(x)` is the Python builtin, no import needed.)

### LaTeX-free constraint

`api._source_needs_latex` blocks a render when the generated source contains any of:
`MathTex`, `Tex`, `SingleStringMathTex`, `DecimalNumber`, `Integer`, `Variable`, `Title`,
`Matrix*`, `Brace*`, `*Table`, `add_coordinates`, `add_numbers`, `get_axis_labels`,
`get_axis_label`, `get_x_axis_label`, `get_y_axis_label`, `get_graph_label`.

Therefore the grapher builds **all** labels (axis labels, title, legend) with `Text`, and
positions them with `.next_to(...)` — never `axes.get_axis_labels(...)` or `Title(...)`.
This keeps the feature working for users without LaTeX installed, exactly like trig.

### Safe evaluation wrapper (per curve)

```python
def _f0(x):
    try:
        with np.errstate(all="ignore"):
            y = x**2            # <- the validated, translated expr
    except Exception:
        return np.nan
    return y if np.isfinite(y) else np.nan
```

numpy under `errstate(all="ignore")` turns domain errors into `nan`/`inf` (no warning spam);
the `try/except` catches literal blow-ups (e.g. `1/0`); the `isfinite` check converts both
to `nan`. With `use_smoothing=False`, a single bad point can't smear across the whole curve.

---

## 6. Generated scene shape (LaTeX-free, mirrors trig)

```python
from manim import *
import numpy as np
from numpy import (sin, cos, tan, exp, log, log10, sqrt,
                   sinh, cosh, tanh, arcsin, arccos, arctan, floor, ceil, pi, e)
# (optional config.frame_width/height block for cam_zoom, exactly like trig)

class ManimScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-5, 5, 1], y_range=[-4, 4, 1],
            x_length=11, y_length=6,
            axis_config=dict(color=GREY, include_tip=True),
        )
        # optional NumberPlane grid here when show_grid
        self.play(Create(axes), run_time=0.8)

        xlab = Text("x", font_size=24).next_to(axes.x_axis, RIGHT, buff=0.2)
        ylab = Text("y", font_size=24).next_to(axes.y_axis, UP,    buff=0.2)
        self.play(FadeIn(xlab), FadeIn(ylab), run_time=0.4)
        # optional Text title to_edge(UP)

        def _f0(x):
            try:
                with np.errstate(all="ignore"):
                    y = x**2
            except Exception:
                return np.nan
            return y if np.isfinite(y) else np.nan

        g0 = axes.plot(_f0, x_range=[-5, 5, 0.025], color=BLUE,
                       stroke_width=2.5, use_smoothing=False)
        # dashed curve: wrap with DashedVMobject(g0)
        lbl0 = Text("f", font_size=22, color=BLUE)  # legend, positioned via next_to
        self.play(Create(g0), FadeIn(lbl0), run_time=1.5)
        # ...repeat per curve...
        self.wait(1.5)
```

Sampling step `dx ≈ (x_max - x_min) / 400` (≈0.025 for the default range). Dashed style is
applied by wrapping the plotted curve in `DashedVMobject(...)`. Animation styles reuse the
trig set (`Create`/`FadeIn`/`Write`/`GrowFromEdge`/`DrawBorderThenFill`) with the same
per-style `run_time`.

---

## 7. Panel UI (mirrors trig/barchart; shared `Dropdown`/`Knob`/`TextControls`)

```
Function Grapher
┌─ Curves (up to 4) ───────────────────────────┐
│ [preset ▾] [ x^2          ] [blue ▾]          │
│ [solid ▾]  width◉  label[ f ]            [✕]  │
│ ───                                           │
│ [preset ▾] [ sin(x)       ] [red ▾]           │
│ [dashed▾]  width◉  label[ g ]            [✕]  │
│ [ + Add curve ]                               │
├─ Axes ───────────────────────────────────────┤
│ X range [-5][5]   Y range [-4][4]             │
│ X step [1]  Y step [1]   ☐ Grid   Zoom ◉      │
│ x-label[ x ]  y-label[ y ]  Title[        ]   │
├─ Animation ──────────────────────────────────┤
│ Style [Create ▾]                              │
└──────────────────────────────────────────────┘
```

- **Preset quick-pick** fills the expr box: `x^2`, `x^3`, `e^x`→`exp(x)`, `ln(x)`→`log(x)`,
  `|x|`→`abs(x)`, `√x`→`sqrt(x)`, `1/x`, `sin(x)`.
- **Curve 1 pre-filled** with `x^2` so the very first render "just works."
- Add/remove curves up to the cap of 4.

---

## 8. Error handling & robustness

- **Validation errors** → friendly `ValueError` from `_validate_expr` (already wired through
  `api.py` → UI as `"Build error: …"`).
- **Domain/asymptote values** → `nan` via the `_f0` wrapper; the render never crashes.
- **Empty / all-blank curves** → builder falls back to a single `x**2` curve so the scene is
  never empty.
- **Numeric discipline** → all numeric params interpolated with explicit formatting
  (`:.4f` / `repr()` style), matching every existing builder.

---

## 9. Testing

- Extend the smoke harness (`smoke_test.py` / `smoke_test_v2.py`) with a `funcgraph` case:
  **compile + a real render** of a multi-curve scene including an asymptote curve and a
  dashed curve. Assert:
  - friendly syntax (`x^2`, `sin(x)`) compiles and renders,
  - strict syntax (`np.exp(x)`) compiles and renders,
  - a blocked expr (`open('x')`) is **rejected** by `_validate_expr`,
  - the LaTeX-free invariant holds (`_source_needs_latex(source)` is `False` for a default
    grapher scene).
- `cd ui && npm run build` (`tsc -b`) — per the project rule (`tsc --noEmit` gives false
  passes).

---

## 10. Risks / verification items

1. **Manim `nan` rendering behavior (the one empirical unknown).** Exactly how Manim 0.20.1's
   `axes.plot` draws a curve containing `nan` points (clean gap vs. visual glitch) is **not
   yet verified**. The implementation plan must smoke-render `1/x`, `tan(x)`, `log(x)`, and
   `sqrt(x)` and inspect the output. If `nan` misbehaves, fall back to **clamping `y` to a
   bounded band** (e.g. ±1.5 × the y-span) and/or passing `discontinuities=[...]` to
   `axes.plot`. Do not assert the `nan`-gap approach works until this render is observed.
2. **LaTeX-free invariant.** Guaranteed only by avoiding the token list in §5; the smoke test
   asserts `_source_needs_latex` returns `False` to prevent regressions (e.g. someone later
   switching to `get_axis_labels`).

---

## 11. Future extensions (not this spec)

- **Calculus panel** (roadmap #2) building directly on this mode's axes + expression infra:
  Riemann sums, area under/between curves, tangent/secant slope, derivative overlay.
- **Numeric axis ticks** as an opt-in toggle (LaTeX-gated via `add_coordinates`).
- **`log2`** / additional namespace helpers if requested.
