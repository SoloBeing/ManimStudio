# Calculus Toolkit — Design Spec

**Mode key:** `calculus`  ·  **Date:** 2026-06-25  ·  **Tier:** 1 #2 (after funcgraph)
**Builds on / mirrors:** [`2026-06-25-function-grapher-design.md`](./2026-06-25-function-grapher-design.md)

A dedicated point-and-click calculus visualizer: pick a function and an interval,
then toggle on Riemann sums, area under/between curves, a tangent (with optional
secant→tangent animation), and a derivative overlay. Generates a LaTeX-free Manim
`Scene` by default, with an opt-in LaTeX mode for accurate math notation.

---

## 1. Goal & Scope

### In scope (v1)
A new **dedicated mode** (Approach B — its own builder + panel, NOT an extension of
funcgraph) covering four independently-toggleable overlays over a single analysis
function `f(x)` on a bounded interval `[a, b]`:

1. **Riemann sums** — left / right / mid / **trapezoid**, `n`-slider, signed-area coloring, optional `Σ` value readout.
2. **Area** — under `f` (f↔x-axis) **or** between `f` and a second function `g`, with optional area-value readout.
3. **Tangent + secant** — tangent line at `x0`; optional animated secant collapsing into the tangent; optional slope readout.
4. **Derivative overlay** — `f'(x)` plotted as a second curve (numeric derivative).

Plus: reused axes/grid/zoom/labels/animation controls, and a **`use_latex` toggle**
(default off) that switches *only the text readouts/legends* between `Text` and
`MathTex`/`DecimalNumber`.

### Out of scope (explicit — future specs)
- Symbolic calculus (sympy): exact derivative/antiderivative expressions, symbolic
  area. v1 is **numeric throughout**. (sympy is bundled but deliberately unused here.)
- Higher derivatives (f''), partial derivatives, multivariable.
- Polar/parametric calculus (those are their own Tier-1 modes).
- Solids of revolution, arc length, Taylor series, slope fields.
- Targeting funcgraph's multi-curve display (calculus owns its own f/g).

---

## 2. Key decisions (brainstorming log)

- **Approach B — dedicated `calculus` mode with its own function builder.** Rejected
  A (extend funcgraph: would balloon the just-released ~145-line `build_funcgraph_source`
  and conflate "display N curves" with "analyze 1 function") and C (refactor-first:
  speculative churn on freshly-shipped code). Calculus reuses funcgraph's **module-level**
  helpers (`_funcgraph_expr`/`_validate_expr`, color helpers, `_FG_ANIMS`) directly; the
  shared-scaffolding extraction is deferred to when polar/parametric prove the surface.
- **All four overlays in v1** (user chose the full toolkit — integral + differential).
- **LaTeX-free default + optional LaTeX.** Labels default to `Text` (no install, never
  trips the preflight dialog); a `use_latex` checkbox opts into `MathTex`/`DecimalNumber`
  for accurate notation (∫, f′, Σ). Geometry is identical either way — `use_latex` changes
  **only** the text readouts/legends.
- **`axes.plot()` graph seam.** Calculus creates a real `graph_f = axes.plot(_f,
  x_range=[a,b])` (a `ParametricFunction` with `underlying_function`) because every Manim
  calculus helper requires it. This is safe on a bounded interval (calculus across an
  asymptote is ill-posed); funcgraph's `_fg_plot` segment trick is intentionally NOT used.
- **Numeric derivative** (central finite difference) for tangent slope and the overlay
  (`plot_derivative_graph` is numeric internally too). No sympy.
- **Trapezoid is built manually** (`get_riemann_rectangles` only does left/right/center) as
  a `VGroup` of `Polygon`s.

---

## 3. Architecture — the 6 seams (mirrors funcgraph)

| # | Seam | File | Change |
|---|------|------|--------|
| 1 | Mode button | `ui/src/components/ActivityBar.tsx` | add `{ mode:'calculus', icon:'∫', label:'Calc' }` |
| 2 | Mode type | `ui/src/types.ts` | add `'calculus'` to the `Mode` union |
| 3 | App wiring | `ui/src/App.tsx` | render `<CalculusPanel>` for the mode, pass panel ref |
| 4 | Builder registry | `api.py` | `_BUILDERS["calculus"] = builders.build_calculus_source` |
| 5 | Generator | `builders.py` | new `build_calculus_source(...)` |
| 6 | Generated scene | (string output) | `Axes` + `graph_f` + overlays + readouts |

New frontend file: `ui/src/components/panels/CalculusPanel.tsx`.
New test file: `Manim_Project_files/test_calculus.py` (tracked).

---

## 4. Data model (`params` payload → builder signature)

`CalculusPanel.getParams()` returns `{ mode: 'calculus', params: {...} }` with this
nested shape (builder destructures it; all keys have defaults):

```jsonc
{
  "f_expr": "x^2",            // required; friendly syntax
  "g_expr": "",              // optional; for area-between / comparison
  "a": -1.0, "b": 2.0,       // analysis interval (enforced a < b)
  "x0": 1.0,                 // tangent point

  "riemann":    { "on": true,  "method": "left",   "n": 10,   "show_value": true },
  "area":       { "on": false, "mode": "under",    "color": "teal", "show_value": true },
  "tangent":    { "on": false, "animate_secant": true, "show_slope": true },
  "derivative": { "on": false, "color": "red",     "show_legend": true },

  "x_min": -5, "x_max": 5, "y_min": -4, "y_max": 4,
  "x_step": 1, "y_step": 1, "show_grid": false, "cam_zoom": 1.0,
  "axis_label_x": "x", "axis_label_y": "y", "title": "",

  "use_latex": false,
  "anim": "Create"
}
```

**Builder signature:**
```python
def build_calculus_source(
    f_expr, g_expr="",
    a=-1.0, b=2.0, x0=1.0,
    riemann=None, area=None, tangent=None, derivative=None,   # dicts (defaults applied)
    x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0,
    x_step=None, y_step=None, show_grid=False, cam_zoom=1.0,
    axis_label_x="x", axis_label_y="y", title="",
    use_latex=False, anim="Create",
): -> str
```

- `riemann.method ∈ {left, right, mid, trapezoid}` → `input_sample_type ∈ {left,right,center}` (trapezoid = manual).
- `area.mode ∈ {under, between}`; `between` with empty `g_expr` → falls back to `under`.
- Defaults applied via `{**DEFAULT, **(riemann or {})}` so partial dicts are safe.

---

## 5. Expression pipeline (reused from funcgraph)

`f_expr`/`g_expr` → `_funcgraph_expr(expr, label)` (translates `^`→`**`, then
`_validate_expr` against the shared blocklists) → emitted as `def _f(x): return <body>`
inside the scene, with the friendly-math numpy namespace (`from numpy import (...)`,
`_FG_NAMESPACE`). No new validation surface. A blocked token raises and `api.render`
returns a clean error, exactly as funcgraph.

---

## 6. Generated scene shape (LaTeX-free by default)

```python
from manim import *
import numpy as np
from numpy import (<_FG_NAMESPACE>)

# (optional config.frame_width/height block for cam_zoom, exactly like funcgraph)

class ManimScene(Scene):
    def construct(self):
        axes = Axes(x_range=[...], y_range=[...], x_length=11, y_length=6,
                    axis_config=dict(color=GREY, include_tip=True))
        # optional NumberPlane grid; axis labels + title via Text(); play(Create(axes))

        def _f(x): return <validated f body>
        # finiteness pre-check over [a,b] → optional Text("⚠ f(x) not finite on [a,b]")
        graph_f = axes.plot(_f, x_range=[a, b], color=BLUE)
        self.play(Create(graph_f), run_time=...)   # animation per `anim`

        # --- overlays (each emitted only when its .on is true) ---
        # Riemann: axes.get_riemann_rectangles(graph_f, x_range=[a,b], dx=(b-a)/n,
        #          input_sample_type=..., show_signed_area=True, color=(POS, NEG))
        #          OR manual VGroup(Polygon...) for trapezoid
        # Area:    axes.get_area(graph_f, x_range=[a,b], color=..., opacity=...,
        #          bounded_graph=graph_g if between)
        # Tangent: tangent line at x0 (slope = central difference); optional
        #          ValueTracker(dx) + updater secant via get_secant_slope_group(...)
        # Deriv:   axes.plot_derivative_graph(graph_f, color=...)  + Text/MathTex legend

        # --- numeric readouts (Text by default; MathTex when use_latex) ---
        # Σ ≈ <sum>, Area ≈ <trapz integral>, slope = <f'(x0)>  → "—" if non-finite
        self.wait(1.5)
```

**Numeric readouts** are computed *in-scene* from `_f`:
- Riemann `Σ` = `sum(_f(sample_k) * dx for k in range(n))` (sample per method).
- Area = trapezoidal numeric integral of `_f` (and `−_g`) over `[a,b]`.
- Slope = central difference `(_f(x0+h) − _f(x0−h)) / (2h)`, `h = 1e-4`.
Each wrapped in `try/except` + `np.isfinite` → renders the value or `"—"`. Readouts are
stacked in the upper-right corner (`to_corner(UR)`, then `next_to(..., DOWN)`), below the
derivative legend chip if present, so multiple enabled overlays don't overlap.

**LaTeX branch (the only place `use_latex` matters):** a small emit-helper chooses
`Text(f"Area ≈ {v:.3f}")` vs `MathTex(rf"\int_{{{a:g}}}^{{{b:g}}} f\,dx \approx {v:.3f}")`
(and `Text("f'(x)")` vs `MathTex("f'(x)")`, `Text(f"n = {n}")` vs `MathTex`). When
`use_latex` is false the source contains **no** `MathTex`/`DecimalNumber`, so
`_source_needs_latex` returns false and the preflight dialog never fires.

---

## 7. Panel UI (`CalculusPanel.tsx`)

Mirrors funcgraph idioms (`sec-hdr`/`sec-sep`, `Knob`, `app-select`, `app-input`,
`check-row`); reuses funcgraph's `PRESETS`/`COLORS`/`ANIMS` constants. Sections:

- **Function** — `f(x)` (preset dropdown + text); `g(x)` (optional, "for area-between").
- **Interval & Point** — `Knob` a, `Knob` b, `Knob` x₀.
- **Overlays** (each a lead checkbox; options apply when on):
  - ☐ Riemann → method `select` (Left/Right/Mid/Trapezoid), `Knob` n (2–200), ☐ show Σ.
  - ☐ Area → mode `select` (Under f / Between f & g), color `select`, ☐ show area.
  - ☐ Tangent → ☐ animate secant→tangent, ☐ show slope.
  - ☐ Derivative f′ → color `select`, ☐ show legend.
- **Axes** — X/Y min·max·step `Knob`s, ☐ Grid, Zoom `Knob`.
- **Labels** — X axis / Y axis / Title `app-input`s.
- **Options** — ☐ Use LaTeX labels (default off); Animation `select`.

Sensible defaults: bare render (`f(x)=x²`, Riemann on, `[a,b]=[-1,2]`) produces a
visible result immediately.

---

## 8. Error handling & robustness

- **Expr safety:** `_funcgraph_expr`/`_validate_expr` (shared); blocked tokens raise → clean api error.
- **Builder guards:** `a < b` else default `[-1, 2]`; clamp `n` to 2–200; `dx = max(eps, (b−a)/n)`; keep `x0` within `[x_min, x_max]`; `between` + empty `g` → `under`.
- **Finiteness pre-check:** sample `_f` across `[a,b]`; if a meaningful fraction is non-finite, still render but add a `Text` warning (don't silently emit a broken graph).
- **Independent overlays:** any subset enabled (or none → just `f`); each readout try/except → `"—"`.
- **LaTeX isolation:** `MathTex`/`DecimalNumber` emitted only under `use_latex`.

---

## 9. Testing

- **`test_calculus.py`** (tracked unit tests):
  - Each overlay on → source contains the right call (`get_riemann_rectangles`,
    `get_area`, `plot_derivative_graph`, tangent/secant group, manual `Polygon` for trapezoid).
  - `use_latex=False` → **no** `MathTex`/`DecimalNumber`; `use_latex=True` → present;
    `_source_needs_latex` agrees with the flag both ways.
  - Expr validation rejects a blocked token; `a<b`, `n`-clamp, and `between`→`under`
    fallback guards hold; partial overlay dicts get defaults.
- **`smoke_test_v2.py`** — add gitignored `[27] Calculus render → video` (real Manim
  render with ≥2 overlays enabled produces a video).
- **`npm run build`** clean (`tsc -b`) for panel/types/App wiring.

---

## 10. Risks / verification items

- **Still-frame verification (the funcgraph lesson).** The automated "video produced"
  test missed funcgraph's silent 3-of-4-curves-missing bug. Render PNG stills
  (`manim -s -ql … ManimScene`) and **view them** to confirm each overlay actually
  appears: Riemann rectangles present; **signed-area coloring** correct for an `f` that
  dips below the axis; area shaded (under and between); tangent slope visually correct;
  secant collapsing into the tangent; `f′` plotted.
- **`get_riemann_rectangles` API drift.** Verify the Manim 0.20.1 signature
  (`input_sample_type`, `show_signed_area`, `color` tuple) against the installed version
  during implementation; adjust kwargs if needed.
- **Secant animation updater.** A `ValueTracker(dx)` + updater rebuilding
  `get_secant_slope_group` each frame is the riskiest piece; if it's fiddly, fall back to
  a discrete few-step secant (dx = d, d/2, d/4 …) — still conveys the limit.
- **`plot_derivative_graph` steepness.** A steep `f′` may exit the y-range; acceptable for
  v1 (user controls axes), but note it.
- **Tangent at a non-finite `x0`** → readout `"—"` and skip the tangent line.

---

## 11. Future extensions (not this spec)
Symbolic mode (sympy: exact f′, antiderivative, ∫ value), f''/concavity, Taylor series,
solids of revolution, arc length, slope fields, and reusing extracted axes/label
scaffolding for polar/parametric modes.
