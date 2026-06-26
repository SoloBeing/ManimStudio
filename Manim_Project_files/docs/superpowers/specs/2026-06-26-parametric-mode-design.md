# Parametric Curves — Design Spec

**Mode key:** `funcgraph` (extended — **no new mode**)  ·  **Date:** 2026-06-26  ·  **Tier:** 1 #4 (after funcgraph, calculus, polar)
**Builds on / mirrors:** [`2026-06-25-function-grapher-design.md`](./2026-06-25-function-grapher-design.md), [`2026-06-26-polar-plane-design.md`](./2026-06-26-polar-plane-design.md)

Add **parametric curves** `(x(t), y(t))` to the existing Function Grapher. A panel-level
**Function ⇄ Parametric** toggle switches the grapher between today's `y = f(x)` UI
(untouched) and a new parametric UI: paired `x(t) / y(t)` expressions, a `t`-range, a
preset menu of classics (circle, Lissajous, astroid, …), and three toggleable extras —
an **animated tracing dot**, a **velocity/tangent vector**, and **static t-markers**.
A `use_latex` toggle opts into `axes.add_coordinates()` numeric tick labels.

---

## 1. Goal & Scope

### In scope (v1)
Parametric plotting delivered as an **extension of the `funcgraph` mode** (Approach B),
**not** a new activity-bar mode. Covers:

1. **Parametric curves** — 1–3 simultaneous `(x(t), y(t))` curves on the same `Axes`,
   each with its own color/label, plus a preset menu of classics. Friendly syntax;
   parameter entered as **`t`** (radians). Animated draw.
2. **A global `t`-range** (`t_min`, `t_max`; default `[0, 2π]`) shared by all parametric
   curves in the scene.
3. **Three independently-toggleable extras** (all operate on the **first / primary**
   parametric curve):
   - **Tracing dot** — a `Dot` that sweeps along the curve as `t` runs `t_min → t_max`.
     *The signature feature.*
   - **Velocity / tangent vector** — an `Arrow` for `(x'(t), y'(t))` riding the tracer,
     direction from a numerical central difference on a shared `ValueTracker`. Depends on
     the tracer: only available when the tracing dot is on (the two share one sweep).
   - **t-value markers** — static labeled `Dot`s at user-given `t` values.
4. A **`use_latex` toggle** (default off): off → axes as funcgraph today (no tick
   numbers); on → `axes.add_coordinates()` for `MathTex` numeric tick labels. Trips the
   existing preflight automatically (`add_coordinates` is already in `api._LATEX_TOKENS`).

### Out of scope (explicit — future work)
- A `use_latex` toggle **for the function (`y = f(x)`) path** — deferred by user request
  ("we'll add that to funcgraph in the future too"). The shared axes helper this spec
  introduces pre-wires it, but the function panel/payload stays untouched in v1.
- 3D parametric curves `(x(t), y(t), z(t))` — belongs with a future 3D mode.
- Mixing a `y=f(x)` curve and a parametric curve on the same axes (the rejected
  per-curve-type variant — see §2).
- Per-curve `t`-ranges; extras on curves other than the primary; arc-length / speed
  read-outs (a possible calculus-toolkit tie-in later).
- Symbolic anything (sympy stays unused, as in funcgraph/polar/calculus).

---

## 2. Key decisions (brainstorming log)

- **Approach B — extend `funcgraph`, do NOT add a new mode.** Unlike polar (which needed
  `PolarPlane`, justifying its own mode), parametric plots on the **same `Axes`** as
  funcgraph and shares the entire Cartesian frame: axes/grid/labels/zoom, the
  `_FG_NAMESPACE` math namespace, `_validate_expr`, and `_FG_ANIMS`. Reusing it avoids a
  **12th** activity-rail button (the rail already hit a cramping problem at 11+ buttons,
  fixed by scroll in Session 25). Same `api._BUILDERS["funcgraph"]` route; no change to
  `ActivityBar.tsx`, `types.ts`, `Sidebar.tsx`, or `api.py`.
- **Panel-level toggle, NOT per-curve type.** A single **Function ⇄ Parametric** toggle
  switches the whole panel. Rejected the per-curve "type" dropdown (mix `y=f(x)` and
  parametric on one axes): it forks every curve row in both panel and builder, forces an
  awkward per-curve-vs-global `t`-range, and makes keeping the function path pristine
  harder. The toggle keeps the function code path **byte-for-byte intact** when off.
- **Function path stays byte-identical (regression-locked).** `build_funcgraph_source`
  gains a `plot_kind` switch; when `"parametric"` it delegates to a new
  `_build_parametric_source(...)`. The existing function branch is not edited; the shared
  axes emission is extracted to `_emit_cartesian_axes(...)` and both paths route through
  it, guarded by the unchanged `test_funcgraph.py` (9/9). If byte-identical matching of
  the extracted helper proves finicky, fall back to a parametric-only inline axes block
  (duplication) — the function path is the invariant, the helper is the convenience.
- **All three extras, on the primary curve.** User chose the richest extras set (tracer +
  velocity + markers), matching polar/calculus. To stay uncluttered and to a single
  `ValueTracker`, the extras ride **curve 0** only; additional curves still draw, statically.
- **Up to 3 curves** (polar's number, not funcgraph's 4) — tracers + multiple curves get
  busy quickly. Function mode keeps its 4.
- **`use_latex` toggles only `axes.add_coordinates()`** (numeric tick labels). Curve
  labels, `t=…` markers, and the title stay `Text` regardless — converting friendly
  `cos(t)` to LaTeX is fragile and arbitrary float `t` values don't render as clean
  `\frac{\pi}{2}`. Narrow, predictable, never parses user input. Default off.
- **Parameter is `t`** (radians) — funcgraph uses `x`, polar uses `theta`; polar
  deliberately rejected `t` to reserve it here.

---

## 3. Architecture — the seams

Only **two files** change (plus a new tracked test); everything else is reused.

| # | Seam | File | Change |
|---|------|------|--------|
| 1 | Panel toggle + parametric UI | `ui/src/components/panels/FunctionGraphPanel.tsx` | add Function⇄Parametric toggle; parametric sub-UI (paired exprs, t-range, extras, use_latex). Function UI untouched. |
| 2 | Builder switch | `builders.py` | `build_funcgraph_source` gains `plot_kind` + parametric kwargs; delegates to new `_build_parametric_source(...)`. |
| 3 | Shared axes helper | `builders.py` | extract `_emit_cartesian_axes(L, …, use_latex=False)`; both paths call it (regression-locked). |
| 4 | Parametric plot helper | `builders.py` | new `_param_plot(...)` (t-driven twin of `_fg_plot`) + extras emitters. |
| 5 | Generated scene | (string output) | `Axes` + curves via `_param_plot` + tracer/vector/markers. |

**No changes** to `ActivityBar.tsx`, `types.ts` (`Mode` union unchanged), `Sidebar.tsx`,
`App.tsx`, or `api.py` — `funcgraph` already routes everything.
New test file: `Manim_Project_files/test_parametric.py` (tracked).

---

## 4. Data model (`params` payload → builder signature)

`FunctionGraphPanel` keeps **separate React state** for the two modes (`curves` for
function, `paramCurves` for parametric) so the function payload is byte-identical to today.
`getParams()` always returns `{ mode: 'funcgraph', params: { plot_kind, … } }`:

```jsonc
// plot_kind === 'parametric'
{
  "plot_kind": "parametric",
  "param_curves": [
    { "x_expr": "cos(t)", "y_expr": "sin(t)", "color": "blue", "label": "circle" }
    // up to 3; x_expr/y_expr are functions of t (RADIANS), friendly syntax
  ],
  "t_min": 0.0, "t_max": 6.2832,          // global t sampling range (default 2π)

  "x_min": -5, "x_max": 5,                 // axes (reused from funcgraph)
  "y_min": -4, "y_max": 4,
  "x_step": 1, "y_step": 1,
  "show_grid": false, "cam_zoom": 1.0,
  "axis_label_x": "x", "axis_label_y": "y", "title": "",
  "anim": "Create",

  "tracer":    { "on": true,  "color": "yellow" },
  "velocity":  { "on": false, "color": "green", "scale": 1.0 },
  "t_markers": { "on": false, "values": "0; 1.57; 3.14", "color": "pink" },

  "use_latex": false
}
```

**Builder signature** (function defaults unchanged; parametric kwargs appended):
```python
def build_funcgraph_source(
    curves=None,
    x_min=-5.0, x_max=5.0, y_min=-4.0, y_max=4.0, x_step=None, y_step=None,
    show_grid=False, cam_zoom=1.0, anim="Create",
    axis_label_x="x", axis_label_y="y", title="",
    # --- parametric extension ---
    plot_kind="function",
    param_curves=None, t_min=0.0, t_max=6.2832,
    tracer=None, velocity=None, t_markers=None,   # dicts (defaults applied)
    use_latex=False,
):  # -> str
    if str(plot_kind) == "parametric":
        return _build_parametric_source(...)
    # ... existing function path, UNCHANGED ...
```

- Defaults applied via `{**DEFAULT, **(tracer or {})}` so partial dicts are safe.
- `t_markers.values` is free text of `t` values separated by `;`/newline, parsed
  defensively; malformed entries skipped; capped (≤ 12).
- Empty/blank `param_curves` → fall back to one circle `(cos(t), sin(t))`, so a bare
  render is never empty (mirrors funcgraph's `x**2` fallback).

---

## 5. Expression pipeline (reused from funcgraph)

Each `x_expr` / `y_expr` → `_param_expr(expr, label, default)` — a thin wrapper that
translates `^`→`**` and runs the existing `_validate_expr` against the shared blocklists,
then emitted as `def _p0_x(t): return <body>` / `def _p0_y(t): return <body>` inside the
scene, with the friendly-math numpy namespace (`from numpy import (…)`, `_FG_NAMESPACE`).
**No new validation surface.** A blocked token raises and `api.render` returns a clean error.

`t` is the free variable. Presets emit canonical `(x(t), y(t))` pairs (final scale factors
validated during still-frame verification so each fits the default `[-5,5]×[-4,4]` frame):

| Preset      | `x(t)`                       | `y(t)`                          |
|-------------|------------------------------|---------------------------------|
| Circle      | `3*cos(t)`                   | `3*sin(t)`                      |
| Ellipse     | `4*cos(t)`                   | `2*sin(t)`                      |
| Lissajous   | `3*sin(3*t)`                 | `3*sin(2*t)`                    |
| Spiral      | `0.4*t*cos(t)`               | `0.4*t*sin(t)`                  |
| Astroid     | `3*cos(t)^3`                 | `3*sin(t)^3`                    |
| Rose        | `3*cos(3*t)*cos(t)`          | `3*cos(3*t)*sin(t)`             |
| Cycloid     | `t - sin(t)`                 | `1 - cos(t)`                    |
| Lemniscate  | `3*cos(t)/(1+sin(t)^2)`      | `3*sin(t)*cos(t)/(1+sin(t)^2)`  |

Default `t`-range is `[0, 2π]`; Spiral and Cycloid read best with a wider `t_max`, which the
panel exposes — itself a small parametric lesson (different curves want different ranges).

---

## 6. Generated scene shape

```python
from manim import *
import numpy as np
from numpy import (<_FG_NAMESPACE>)

def _param_plot(axes, fx, fy, t0, t1, dt, color, width):
    # t-driven twin of _fg_plot: sample t over [t0,t1], compute (fx,fy), break the
    # path on any non-finite coord (divergent curve renders as a gap, never a crash).
    grp = VGroup(); pts = []
    n = int(round((t1 - t0) / dt)) + 1
    for k in range(n):
        tt = t0 + k * dt
        try:
            with np.errstate(all='ignore'):
                xx = float(fx(tt)); yy = float(fy(tt))
        except Exception:
            xx = yy = float('nan')
        if not (np.isfinite(xx) and np.isfinite(yy)):
            if len(pts) >= 2:
                m = VMobject(color=color, stroke_width=width)
                m.set_points_as_corners([axes.c2p(px, py) for px, py in pts]); grp.add(m)
            pts = []
        else:
            pts.append((xx, yy))
    if len(pts) >= 2:
        m = VMobject(color=color, stroke_width=width)
        m.set_points_as_corners([axes.c2p(px, py) for px, py in pts]); grp.add(m)
    return grp

# (optional config.frame_width/height block for cam_zoom, exactly like funcgraph)

class ManimScene(Scene):
    def construct(self):
        # --- axes (shared _emit_cartesian_axes) ---
        axes = Axes(x_range=[…], y_range=[…], x_length=11, y_length=6,
                    axis_config=dict(color=GREY, include_tip=True))
        # use_latex True only: axes.add_coordinates()   # MathTex tick numbers
        # show_grid: NumberPlane + FadeIn   →   self.play(Create(axes))
        # axis labels + title via Text() (never Tex), exactly like funcgraph

        # --- curves (1..3) ---
        def _p0_x(t): return <validated x body>
        def _p0_y(t): return <validated y body>
        g0 = _param_plot(axes, _p0_x, _p0_y, <t_min>, <t_max>, <dt>, BLUE, 2.5)
        self.play(Create(g0), run_time=1.0)   # + FadeIn(Text(label)) stacked UR
        # ... _p1_x/_p1_y, _p2_x/_p2_y likewise (static, no extras)

        # --- extras (each emitted only when its .on is true; all ride curve 0) ---
        # Tracer / velocity share ONE sweep driven by a single ValueTracker:
        #   t_val = ValueTracker(<t_min>)
        #   dot = always_redraw(lambda: Dot(                         # tracer.on
        #       axes.c2p(_p0_x(t_val.get_value()), _p0_y(t_val.get_value())),
        #       radius=0.08, color=YELLOW))
        #   vec = always_redraw(lambda: _vel_arrow(axes, _p0_x, _p0_y,  # velocity.on
        #       t_val.get_value(), scale, GREEN))   # central-difference dir
        #   self.add(dot[, vec])
        #   self.play(t_val.animate.set_value(<t_max>), run_time=3.0, rate_func=linear)
        # Markers (independent of tracer):
        #   Dot(axes.c2p(_p0_x(tv), _p0_y(tv))) + Text(f"t={tv:g}") per value

        self.wait(1.5)
```

**`dt` (sampling step)** = `max(0.005, (t_max − t_min) / 400.0)` — same density as
funcgraph/polar.

**Velocity arrow** (`_vel_arrow`, emitted only when velocity.on): central difference
`vx = (fx(t+h) − fx(t−h)) / (2h)`, `vy = (fy(t+h) − fy(t−h)) / (2h)` with `h = 1e-3`;
arrow drawn from the tracer point to `axes.c2p(x + vx*k, y + vy*k)` where `k = 0.3*scale`
(data units); rebuilt each frame via `always_redraw` off the shared `ValueTracker`.

**LaTeX branch (the only place `use_latex` matters):** emits `axes.add_coordinates()`
when true (→ `_source_needs_latex` true → preflight fires) and nothing when false (axes
exactly as funcgraph today). Curve/marker/title labels are always `Text`.

---

## 7. Panel UI (`FunctionGraphPanel.tsx`)

A **Function ⇄ Parametric** segmented toggle at the top. Function mode renders today's UI
verbatim (separate `curves` state, untouched). Parametric mode renders:

- **Heads-up note** (small muted): *"Curves are `(x(t), y(t))`; `t` in radians (e.g.
  `cos(t)`). Range below sets how far `t` sweeps."*
- **Curves (up to 3)** — per curve: preset `select` (Circle/Ellipse/Lissajous/Spiral/
  Astroid/Rose/Cycloid/Lemniscate), `x(t)=` input, `y(t)=` input, color `select`, label
  input, remove `×`; **+ Add Curve** (≤3).
- **t-Range** — `Knob` t min, `Knob` t max (radians; default 0…2π).
- **Axes** — reuses funcgraph's X/Y min/max/step, zoom, ☐ grid `Knob`s/checkbox.
- **Extras** (each a lead checkbox):
  - ☐ Tracing dot → color `select`.
  - ☐ Velocity vector → color `select`, `Knob` scale. *(shown only when Tracing dot is on —
    they share the sweep; disabled/hidden otherwise.)*
  - ☐ t-markers → values `app-input` (`t` list, e.g. `0; 1.57; 3.14`), color `select`.
- **Labels** — X axis / Y axis / Title `app-input`s (shared with function mode).
- **Options** — ☐ Use LaTeX tick labels (default off), Animation `select`.

Reuses funcgraph's `COLORS`/`ANIMS` constants and `sec-hdr`/`sec-sep`/`Knob`/`app-select`/
`app-input`/`check-row` idioms. A bare parametric render (one circle, no extras, no LaTeX)
produces a visible result immediately.

---

## 8. Error handling & robustness

- **Expr safety:** `_param_expr`/`_validate_expr` (shared); blocked tokens raise → clean api error.
- **Builder guards:** `t_min < t_max` else default `[0, 2π]`; `dt = max(0.005, span/400)`;
  axes ranges ordered/sane (funcgraph's existing guards); up to 3 curves, blanks skipped,
  empty → circle fallback; `velocity.scale > 0` else 1.0.
- **t-markers parsing:** split on `;`/newline; each value parsed as float in try/except;
  malformed skipped; capped ≤ 12.
- **Extras coupling:** tracer + velocity share one `ValueTracker`/sweep — the builder
  emits the sweep when either is on, and the velocity arrow only when `velocity.on and
  tracer.on` (panel also gates velocity on tracer). t-markers are fully independent. Any
  subset enabled (or none → just axes + curves).
- **Divergent curve:** `_param_plot` breaks the path on non-finite `(x,y)` (no crash, gaps).
- **LaTeX isolation:** `add_coordinates` emitted only under `use_latex`; everything else `Text`.
- **Function path invariant:** with `plot_kind="function"`, output is byte-identical to
  today (test_funcgraph 9/9).

---

## 9. Testing

- **`test_parametric.py`** (tracked unit tests, pure-Python `compile()` + substring asserts):
  - Default parametric render → source `compile`s, contains `_param_plot(`, `c2p`, and a
    `def _p0_x(`/`def _p0_y(`; contains **no** `add_coordinates`.
  - `use_latex=True` → source contains `add_coordinates`; `_source_needs_latex` agrees with
    the flag both ways.
  - Friendly syntax: `x_expr="cos(t)^3"` → `return cos(t)**3` (`^`→`**` translated); `t`
    is the variable.
  - Each preset emits its canonical pair.
  - Up to 3 curves emit `_p0/_p1/_p2`; blank curves skipped; empty list → circle fallback.
  - Each extra appears only when toggled: tracer → `ValueTracker(`; velocity → the arrow
    helper / `always_redraw`; markers → `Dot(` per value. Malformed marker values skipped.
  - Blocked expr (`__import__`, `open`, `eval`) rejected with `ValueError`.
  - All animation styles compile.
- **Function-path regression (critical):** `test_funcgraph.py` **9/9 unchanged** — proves
  the extracted `_emit_cartesian_axes` left the `y=f(x)` output byte-identical.
- **Other regressions:** `test_polar.py` 16/16, `test_calculus.py` 20/20 unchanged.
- **`smoke_test_v2.py`** — add gitignored `[29] Parametric render → video` (real Manim
  render with ≥1 curve + ≥1 extra produces a video).
- **`npm run build`** clean (`tsc -b`) for panel/types wiring.

---

## 10. Risks / verification items

- **Still-frame verification (the funcgraph lesson).** The "video produced" test missed
  funcgraph's silent missing-curves bug. Render PNG stills (`manim -s -ql … ManimScene`)
  and **view them** to confirm: axes (+ tick numbers when LaTeX on) render; each curve
  shape is correct (circle round, Lissajous lobe count right, astroid cusps, rose petals);
  the tracer dot, velocity arrow, and t-markers land on the curve at the right places.
  For animated extras, also sample a **mid-sweep** frame, not just the final one.
- **`always_redraw` + `ValueTracker` timing.** Confirm the tracer/vector rebuild smoothly
  across the `t_val.animate.set_value` play and that `rate_func=linear` gives even motion;
  verify the arrow doesn't degenerate to zero length where velocity vanishes (e.g. cusp of
  an astroid) — guard `_vel_arrow` against a ~0-length vector (skip/clamp).
- **Preset framing.** Scale factors in §5 are provisional; adjust during still-frame
  verification so each preset fits the default frame (Spiral/Cycloid may still want a wider
  `t_max`, which is acceptable and panel-adjustable).
- **Byte-identical function path.** The `_emit_cartesian_axes` extraction is the one place
  regression can sneak in; lock it with `test_funcgraph.py` before adding parametric. If it
  fights, fall back to a parametric-only inline axes block.
- **Numerical derivative at endpoints.** Central difference at `t_min`/`t_max` samples
  slightly outside `[t0,t1]`; harmless for the smooth presets, and `always_redraw` tolerates
  a non-finite blip (guarded arrow). Note for custom exprs with domain edges.

---

## 11. Future extensions (not this spec)
A `use_latex` toggle for the function (`y=f(x)`) path (the shared axes helper pre-wires it);
3D parametric curves; per-curve `t`-ranges and extras on any curve; arc-length / speed
read-outs tied to the calculus toolkit; an animated trail the tracer leaves behind.
