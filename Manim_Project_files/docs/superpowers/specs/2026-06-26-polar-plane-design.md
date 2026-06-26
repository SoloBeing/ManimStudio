# Polar Plane — Design Spec

**Mode key:** `polar`  ·  **Date:** 2026-06-26  ·  **Tier:** 1 #3 (after funcgraph, calculus)
**Builds on / mirrors:** [`2026-06-25-function-grapher-design.md`](./2026-06-25-function-grapher-design.md), [`2026-06-25-calculus-toolkit-design.md`](./2026-06-25-calculus-toolkit-design.md)

A dedicated point-and-click polar visualizer: render a configurable `PolarPlane`
grid and plot one or more polar curves `r = f(θ)` (rose, cardioid, spiral, limaçon,
circle), with optional point-marker / angular-sector / radial-line overlays.
Generates a LaTeX-free Manim `Scene` by default, with an opt-in LaTeX mode for the
canonical π-radian coordinate labels.

---

## 1. Goal & Scope

### In scope (v1)
A new **dedicated mode** (Approach A — its own builder + panel, NOT an extension of
funcgraph) covering:

1. **Polar grid** — a `PolarPlane` with configurable radius max / radius step,
   azimuth divisions (number of radial spokes), size, and zoom.
2. **Polar curves** — 1–3 simultaneous `r = f(θ)` curves, each with its own
   color/label, plus a preset menu of classics (rose, cardioid, spiral, limaçon,
   circle). Friendly syntax; `θ` entered as `theta`. Animated draw.
3. **Three independently-toggleable overlays:**
   - **Points** — labeled `Dot`s at user-given `(r, θ°)` polar coordinates.
   - **Angular sector** — a shaded wedge from `start°` to `end°` out to `radius_max`.
   - **Radial reference line** — a ray from the origin to the rim at a given angle.
4. A **`use_latex` toggle** (default off): off → `Text` degree labels placed manually
   (no LaTeX); on → `plane.add_coordinates()` for π-radian/MathTex labels.

### Out of scope (explicit — future specs)
- Parametric curves `(x(t), y(t))` — that is its own Tier-1 mode (next after polar).
- Polar-area / arc-length calculus on polar curves (belongs with the calculus toolkit).
- 3D / spherical / cylindrical coordinates.
- Animating a point sweeping along a curve, or tracing `r(θ)` against a θ-dial.
- Symbolic anything (sympy stays unused here, as in calculus).

---

## 2. Key decisions (brainstorming log)

- **Approach A — dedicated `polar` mode with its own builder.** Rejected B (extend
  `build_funcgraph_source`): polar geometry differs enough (`PolarPlane` vs `Axes`,
  `polar_to_point`, angular extras, no Cartesian x/y axes) that sharing would tangle
  both code paths and both panels. Polar reuses funcgraph's **module-level** helpers
  where they fit (`_validate_expr`, color helpers, the friendly-math numpy namespace,
  the segment-plot break-on-non-finite pattern) without sharing the builder body.
- **Full scope: grid + curves + all three extras** (user chose the richest option).
- **Up to 3 curves + preset menu** (user choice). 3, not funcgraph's 4 — polar curves
  are visually busier, and 3 keeps the plot readable.
- **LaTeX-free default + optional LaTeX.** Default emits only `Text` degree labels
  (no install, never trips the preflight dialog). `use_latex` opts into
  `plane.add_coordinates()` for canonical π-radian labels. Because `add_coordinates`
  is already in `api._LATEX_TOKENS`, the existing `_source_needs_latex` preflight +
  warning dialog fire automatically on the LaTeX path — **no new preflight wiring.**
- **Angle-unit split (confirmed with user):** curve formulas use **radians** (`theta`,
  math-standard — `cos(3*theta)` gives a 3-petal rose); the three extras' angles are
  entered in **degrees** (humans say "shade 0–90°", "ray at 30°"). The panel shows an
  inline heads-up making this explicit so it never surprises the user.
- **Custom `_polar_plot` helper, not `plane.plot_polar_graph`.** We sample θ and build
  the curve with `plane.polar_to_point(r, θ)` + `set_points_as_corners`, **breaking the
  path on non-finite `r`** — the exact robustness pattern as funcgraph's `_fg_plot`, so
  divergent `r` (e.g. `r = 1/θ` near 0) renders as a gap, not a crash. Negative `r` is
  fine (`polar_to_point` reflects it naturally).

---

## 3. Architecture — the 6 seams (mirrors funcgraph/calculus)

| # | Seam | File | Change |
|---|------|------|--------|
| 1 | Mode button | `ui/src/components/ActivityBar.tsx` | add `{ mode:'polar', icon:'◎', label:'Polar' }` |
| 2 | Mode type | `ui/src/types.ts` | add `'polar'` to the `Mode` union |
| 3 | Panel switch | `ui/src/components/Sidebar.tsx` | add `PolarPlanePanel` to the `TITLES` `Record<Mode>` + the mode switch (App.tsx unchanged) |
| 4 | Builder registry | `api.py` | `_BUILDERS["polar"] = builders.build_polar_source` |
| 5 | Generator | `builders.py` | new `build_polar_source(...)` + `_polar_plot` / `_polar_expr` helpers |
| 6 | Generated scene | (string output) | `PolarPlane` + labels + curve(s) + extras |

New frontend file: `ui/src/components/panels/PolarPlanePanel.tsx`.
New test file: `Manim_Project_files/test_polar.py` (tracked).

---

## 4. Data model (`params` payload → builder signature)

`PolarPlanePanel.getParams()` returns `{ mode: 'polar', params: {...} }`:

```jsonc
{
  "curves": [
    { "expr": "cos(3*theta)", "color": "blue", "label": "rose" }
    // up to 3; expr is r = f(theta), theta in RADIANS, friendly syntax
  ],

  "radius_max": 4.0,          // outer radius of the grid
  "radius_step": 1.0,         // spacing of concentric circles
  "azimuth_divisions": 12,    // number of radial spokes (12 → every 30°)
  "size": 6.0,                // diameter of the plane (Manim units)

  "theta_min": 0.0,           // curve sampling range, in RADIANS
  "theta_max": 6.2832,        // default 2π
  "show_curve_labels": true,

  "points":      { "on": false, "coords": "2,45; 3,135", "color": "yellow" },
  "sector":      { "on": false, "start_deg": 0,  "end_deg": 90,  "color": "teal" },
  "radial_line": { "on": false, "angle_deg": 30, "color": "red" },

  "cam_zoom": 1.0,
  "title": "",

  "use_latex": false,
  "anim": "Create"
}
```

**Builder signature:**
```python
def build_polar_source(
    curves,
    radius_max=4.0, radius_step=1.0, azimuth_divisions=12, size=6.0,
    theta_min=0.0, theta_max=6.2832, show_curve_labels=True,
    points=None, sector=None, radial_line=None,     # dicts (defaults applied)
    cam_zoom=1.0, title="",
    use_latex=False, anim="Create",
): -> str
```

- Defaults applied via `{**DEFAULT, **(points or {})}` so partial dicts are safe.
- `points.coords` is a free-text string of `r,θ°` pairs separated by `;` (or newline),
  parsed defensively by the builder; malformed pairs are skipped.
- Empty/blank `curves` → fall back to one default curve `1 + cos(theta)` (cardioid),
  so a bare render is never empty (mirrors funcgraph's `x**2` fallback).

---

## 5. Expression pipeline (reused from funcgraph)

`curve.expr` → `_polar_expr(expr)` — a thin wrapper that translates `^`→`**` and runs
the existing `_validate_expr(body, label, default="1 + cos(theta)")` against the shared
blocklists — then emitted as `def _r0(theta): return <body>` inside the scene, with the
friendly-math numpy namespace (`from numpy import (...)`, `_FG_NAMESPACE`). No new
validation surface. A blocked token raises and `api.render` returns a clean error,
exactly as funcgraph/calculus.

`theta` is the only free variable; `t` is **not** accepted (avoids ambiguity with a
future parametric mode whose variable is `t`). Presets emit canonical `theta` formulas:

| Preset    | Emitted `r = f(theta)`        |
|-----------|-------------------------------|
| Rose      | `cos(3*theta)`                |
| Cardioid  | `1 + cos(theta)`              |
| Spiral    | `0.5*theta`                   |
| Limaçon   | `1 + 2*cos(theta)`            |
| Circle    | `2`                           |

---

## 6. Generated scene shape (LaTeX-free by default)

```python
from manim import *
import numpy as np
from numpy import (<_FG_NAMESPACE>)

def _polar_plot(plane, r_func, t0, t1, dt, color, width):
    # Sample theta over [t0, t1]; split into continuous, finite runs so a divergent
    # r renders as a break (a nan/inf voids the path). Mirrors funcgraph's _fg_plot.
    grp = VGroup(); pts = []
    n = int(round((t1 - t0) / dt)) + 1
    for k in range(n):
        th = t0 + k * dt
        try:
            with np.errstate(all='ignore'):
                rr = float(r_func(th))
        except Exception:
            rr = float('nan')
        if not np.isfinite(rr):
            if len(pts) >= 2:
                m = VMobject(color=color, stroke_width=width)
                m.set_points_as_corners(pts); grp.add(m)
            pts = []
        else:
            pts.append(plane.polar_to_point(rr, th))
    if len(pts) >= 2:
        m = VMobject(color=color, stroke_width=width)
        m.set_points_as_corners(pts); grp.add(m)
    return grp

# (optional config.frame_width/height block for cam_zoom, exactly like funcgraph)

class ManimScene(Scene):
    def construct(self):
        plane = PolarPlane(
            size=<size>, radius_max=<radius_max>,
            radius_config={"stroke_color": GREY},
            azimuth_units=<"PI radians" if use_latex else None>,
            azimuth_step=<azimuth_divisions>,
        )
        self.play(Create(plane), run_time=0.9)   # animation per `anim`

        # --- labels ---
        # use_latex False (default): Text("0°","45°",...) for the cardinal/inter-cardinal
        #   subset (see §10 — NOT every spoke, to avoid clutter), placed via
        #   plane.polar_to_point(radius_max, angle); FadeIn together. NO LaTeX token.
        # use_latex True: plane.add_coordinates()  → π-radian + radius MathTex labels.

        # title via Text().to_edge(UP) if provided

        # --- curves (1..3) ---
        def _r0(theta): return <validated body>
        g0 = _polar_plot(plane, _r0, <theta_min>, <theta_max>, <dt>, BLUE, 3.0)
        self.play(Create(g0), run_time=1.0)       # + FadeIn(Text(label)) stacked UR
        # ... _r1/_r2 likewise

        # --- extras (each emitted only when its .on is true) ---
        # Points:      Dot(plane.polar_to_point(r, radians(deg))) + small Text label
        # Sector:      AnnularSector / Sector at origin, start/end via radians(deg),
        #              outer_radius scaled to radius_max in plane units; faded in
        # Radial line: Line(plane.polar_to_point(0, a), plane.polar_to_point(radius_max, a))

        self.wait(1.5)
```

**`dt` (sampling step)** = `max(0.005, (theta_max − theta_min) / 400.0)` — same density
as funcgraph, smooth enough for tight roses/spirals.

**LaTeX branch (the only place `use_latex` matters):** chooses between manually-placed
`Text("…°")` spoke labels and `plane.add_coordinates()`. When `use_latex` is false the
source contains **no** `add_coordinates` (nor any other LaTeX token), so
`_source_needs_latex` returns false and the preflight dialog never fires. When true,
`add_coordinates` is present → preflight fires if LaTeX is missing. Curve/point/title
labels are always `Text` (never LaTeX) regardless of the toggle.

---

## 7. Panel UI (`PolarPlanePanel.tsx`)

Mirrors funcgraph/calculus idioms (`sec-hdr`/`sec-sep`, `Knob`, `app-select`,
`app-input`, `check-row`); reuses funcgraph's `COLORS`/`ANIMS` constants. Sections:

- **Heads-up note** (top, small muted text): *"Curve formulas use θ in **radians** (e.g.
  `cos(3*theta)`). Overlay angles below are in **degrees**."* — the explicit user-requested
  heads-up.
- **Curves (up to 3)** — per curve: preset `select` (Rose/Cardioid/Spiral/Limaçon/Circle),
  `r = ` expr `app-input`, color `select`, label input, remove `×`; **+ Add Curve** (≤3).
- **Grid** — `Knob` radius max, `Knob` radius step, `Knob` azimuth divisions (spokes),
  `Knob` size, `Knob` zoom.
- **Curve range** — `Knob` θ min, `Knob` θ max (radians; default 0…2π), ☐ show curve labels.
- **Overlays** (each a lead checkbox; options apply when on):
  - ☐ Points → coords `app-input` (`r,θ°` pairs, e.g. `2,45; 3,135`), color `select`.
  - ☐ Angular sector → `Knob` start° , `Knob` end° , color `select`.
  - ☐ Radial line → `Knob` angle° , color `select`.
- **Labels** — Title `app-input`.
- **Options** — ☐ Use LaTeX labels (π-radian; default off), Animation `select`.

Sensible defaults: a bare render (one cardioid `1 + cos(theta)`, grid, no extras,
no LaTeX) produces a visible result immediately.

---

## 8. Error handling & robustness

- **Expr safety:** `_polar_expr`/`_validate_expr` (shared); blocked tokens raise → clean api error.
- **Builder guards:** `theta_min < theta_max` else default `[0, 2π]`; clamp
  `azimuth_divisions` to a sane range (e.g. 2–48); `radius_step > 0`; `radius_max > 0`;
  `dt = max(0.005, span/400)`; up to 3 curves, blanks skipped, empty → cardioid fallback.
- **Points parsing:** split on `;`/newline then `,`; each `r,θ` parsed as floats inside
  try/except; malformed entries skipped; cap the count (e.g. ≤ 12) to avoid clutter.
- **Independent overlays:** any subset enabled (or none → just grid + curves).
- **Divergent r:** `_polar_plot` breaks the path on non-finite `r` (no crash, renders gaps).
- **LaTeX isolation:** `add_coordinates` emitted only under `use_latex`; everything else `Text`.

---

## 9. Testing

- **`test_polar.py`** (tracked unit tests, pure-Python `compile()` + substring asserts):
  - Default render → source `compile`s, contains `PolarPlane(`, `_polar_plot(`,
    `polar_to_point`, and a `Text(` degree label; contains **no** `add_coordinates`.
  - `use_latex=True` → source contains `add_coordinates`; `_source_needs_latex` agrees
    with the flag both ways (false when off, true when on).
  - Friendly syntax: `expr="cos(3*theta)"` → `return cos(3*theta)`; `^`→`**` translated.
  - Each preset emits its canonical formula.
  - Up to 3 curves emit `_r0/_r1/_r2`; blank curves skipped; empty list → cardioid fallback.
  - Each extra appears only when toggled: points → `Dot(`; sector → sector mobject;
    radial line → `Line(`. Malformed point coords are skipped without raising.
  - Blocked expr (`__import__`, `open`, `eval`) rejected with `ValueError`.
  - All animation styles compile.
- **`smoke_test_v2.py`** — add gitignored `[28] Polar render → video` (real Manim render
  with ≥1 curve + ≥1 extra produces a video).
- **Regression:** re-run `test_funcgraph.py` (9/9) and `test_calculus.py` (20/20) unchanged.
- **`npm run build`** clean (`tsc -b`) for panel/types/Sidebar wiring.

---

## 10. Risks / verification items

- **Still-frame verification (the funcgraph lesson).** The automated "video produced"
  test missed funcgraph's silent missing-curves bug. Render PNG stills
  (`manim -s -ql … ManimScene`) and **view them** to confirm: the grid + spokes render;
  each curve shape is correct (rose has the right petal count, cardioid/spiral/limaçon
  look right); degree labels are placed at the right spokes (LaTeX-off) and π-radian
  labels appear (LaTeX-on); each extra (points, sector, radial line) lands at the right
  angle.
- **`PolarPlane` API drift.** Verify the Manim 0.20.1 `PolarPlane` kwargs against the
  installed version during implementation: `size`, `radius_max`, `radius_step`,
  `azimuth_units`, `azimuth_step`/`azimuth_divisions`, and `radius_config`. The root
  example uses `azimuth_units`, `size`, `azimuth_label_font_size`, `radius_config`;
  confirm the spoke-count kwarg name and adjust.
- **`polar_to_point` signature.** Confirm it is `polar_to_point(radius, azimuth)` (radians)
  on the installed `PolarPlane`; that drives both curve points and the extras' geometry.
- **Sector mobject choice.** `Sector`/`AnnularSector` sizing is in scene units, not plane
  units — scale `outer_radius` so the wedge matches `radius_max` on the grid. If sizing
  is fiddly, fall back to an `ArcPolygon`/filled `VMobject` built from `polar_to_point`
  samples along the arc.
- **Degree-label placement (LaTeX-off).** Manually placing `Text("0°"…"330°")` at every
  spoke can clutter; default to the cardinal/inter-cardinal set (e.g. every 45° or every
  90°) regardless of `azimuth_divisions`, to keep the LaTeX-free grid clean.
- **Negative / very large r.** `polar_to_point` reflects negative r (correct); very large
  r is clipped only by the frame — acceptable for v1 (user controls radius_max/zoom).

---

## 11. Future extensions (not this spec)
Parametric mode `(x(t), y(t))` (next Tier-1), polar-area/arc-length integration tied to
the calculus toolkit, an animated θ-sweep tracer, and extracting the shared
grid/label/expression scaffolding once parametric confirms the common surface.
