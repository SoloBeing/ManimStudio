# Polar Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `polar` mode — render a configurable `PolarPlane` grid, plot 1–3 polar curves `r = f(θ)` (rose/cardioid/spiral/limaçon/circle), and layer three independently-toggleable overlays (labeled points, a shaded angular sector, a radial reference line).

**Architecture:** Approach A from the spec — a self-contained `build_polar_source(...)` generator in `builders.py` (reusing funcgraph's module-level helpers `_validate_expr`, `_text_color`, `_FG_NAMESPACE`, `_FG_ANIMS`, `_join`) plus a new `PolarPlanePanel.tsx`. The builder emits a `Scene` that builds a `PolarPlane`, draws each curve with a robust `_polar_plot` helper (samples θ, `plane.polar_to_point(r, θ)` + `set_points_as_corners`, breaking on non-finite `r`), and appends the extras. Labels are LaTeX-free `Text` degree labels by default; a `use_latex` flag emits `plane.add_coordinates()` for π-radian MathTex labels.

**Tech Stack:** Python (string-emitting builder), Manim CE 0.20.1, React + TypeScript (Vite), plain-Python test harness (no pytest).

**Spec:** `docs/superpowers/specs/2026-06-26-polar-plane-design.md`

## Global Constraints

- **LaTeX-free by default.** Emit `plane.add_coordinates()` **only** when `use_latex=True`. With `use_latex=False`, `api._source_needs_latex(src)` MUST return `False`. (`add_coordinates` is already in `api._LATEX_TOKENS`, so the existing preflight fires automatically on the LaTeX path — do NOT add new preflight wiring.)
- **Curve formulas are in RADIANS**, variable name `theta` only (NOT `t` — reserved for a future parametric mode). The three extras' angles are in **DEGREES**, converted at build time via the module constant `_DEG2RAD`.
- **Reuse existing module-level helpers** in `builders.py`: `_validate_expr(expr, label, default)`, `_text_color(name) -> str`, `_FG_NAMESPACE: str`, `_FG_ANIMS: dict[str,(tmpl,rt)]`, `_join(list[str]) -> str`. Do NOT duplicate or refactor funcgraph/calculus.
- **No `math` import in `builders.py`** (it currently imports only `ast`). Use the new module-level `_DEG2RAD = 3.141592653589793 / 180.0` for degree→radian at build time.
- **Curve drawing seam:** the custom `_polar_plot` helper (break-on-non-finite). Do NOT use `plane.plot_polar_graph` (a single non-finite `r` voids the whole path).
- **Sector seam:** a filled `Polygon` wedge built from `plane.polar_to_point` samples (center + arc). Do NOT use `Sector`/`AnnularSector` (their radius is in scene units, not plane data units — sizing mismatch).
- **Builder dispatch** is `source = builder(**params)` (api.py) — nested `params` keys become kwargs, so `points`/`sector`/`radial_line` arrive as dicts.
- **Tests:** plain-Python harness like `test_funcgraph.py` (substring asserts + `compile()` + `_source_needs_latex`). Run with `uv run python test_polar.py`. `test_polar.py` is **tracked**.
- **Frontend** verified with `cd ui && npm run build` (`tsc -b`) — never `tsc --noEmit`.
- Adding `'polar'` to `Mode` **forces** a `Sidebar.tsx` `TITLES` entry (it's `Record<Mode, string>`) or tsc fails.
- **Smoke test before committing; never push** (CLAUDE.md).
- Verified Manim 0.20.1 API (do not re-guess): `PolarPlane(radius_max=4.0, size=None, radius_step=1, azimuth_step=None, azimuth_units='PI radians', radius_config=None, ...)`; `plane.polar_to_point(radius, azimuth)` (azimuth in radians); `plane.add_coordinates()`.

---

## File Structure

- **Create** `Manim_Project_files/test_polar.py` — tracked unit tests (Tasks 1–5).
- **Modify** `Manim_Project_files/builders.py` — append `build_polar_source` + helpers + extra-default dicts + extra emitters (Tasks 1–4).
- **Modify** `Manim_Project_files/api.py` — register `"polar"` in `_BUILDERS` (Task 5).
- **Create** `Manim_Project_files/ui/src/components/panels/PolarPlanePanel.tsx` (Task 6).
- **Modify** `Manim_Project_files/ui/src/types.ts` — add `'polar'` to `Mode` (Task 6).
- **Modify** `Manim_Project_files/ui/src/components/ActivityBar.tsx` — add `◎ Polar` entry (Task 6).
- **Modify** `Manim_Project_files/ui/src/components/Sidebar.tsx` — `TITLES` + import + panel switch (Task 6).
- **Modify** `Manim_Project_files/smoke_test_v2.py` — add `[28]` render test (Task 7; gitignored).

All commands run from `Manim_Project_files/` unless noted.

---

### Task 1: Builder scaffold — grid, labels, `_polar_plot`, curves (no extras)

Builds the full `build_polar_source` signature and a runnable scene: a `PolarPlane`, its labels (Text degrees by default / `add_coordinates` under `use_latex`), an optional title, and 1–3 animated curves drawn via `_polar_plot`. Applies all numeric guards. The three extras are wired as no-op stub emitters filled by Tasks 2–4.

**Files:**
- Create: `test_polar.py`
- Modify: `builders.py` (append at end of file)

**Interfaces:**
- Consumes (existing in `builders.py`): `_validate_expr(expr, label, default) -> str`, `_text_color(name) -> str`, `_FG_NAMESPACE: str`, `_FG_ANIMS: dict[str,(tmpl,rt)]`, `_join(list[str]) -> str`.
- Produces:
  ```python
  _DEG2RAD = 3.141592653589793 / 180.0
  def _polar_expr(expr, label) -> str          # "^"->"**" then _validate_expr, default "1 + cos(theta)"
  def _parse_polar_points(s) -> list[tuple[float,float]]   # "r,deg; r,deg" -> [(r,deg)], capped at 12
  def build_polar_source(
      curves,
      radius_max=4.0, radius_step=1.0, azimuth_divisions=12, size=6.0,
      theta_min=0.0, theta_max=6.2832, show_curve_labels=True,
      points=None, sector=None, radial_line=None,      # dicts
      cam_zoom=1.0, title="",
      use_latex=False, anim="Create",
  ) -> str
  # stub emitters (filled Tasks 2-4):
  def _emit_polar_points(L, P) -> None
  def _emit_polar_sector(L, S, rmax) -> None
  def _emit_polar_radial(L, RL, rmax) -> None
  ```

- [ ] **Step 1: Write the failing test**

Create `test_polar.py`:
```python
"""Unit tests for the Polar Plane builder (build_polar_source).

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_polar.py
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_polar_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<polar>", "exec")


def test_scaffold_compiles_and_builds_grid():
    src = build_polar_source([{"expr": "cos(3*theta)", "color": "blue"}])
    _compiles(src)
    assert "class ManimScene(Scene):" in src
    assert "PolarPlane(" in src
    assert "def _polar_plot(" in src and "polar_to_point" in src
    assert "def _r0(theta):" in src and "return cos(3*theta)" in src


def test_default_cardioid_fallback():
    # empty / blank curves -> one default cardioid
    src = build_polar_source([])
    assert "return 1 + cos(theta)" in src
    _compiles(src)
    src2 = build_polar_source([{"expr": "   "}])
    assert "return 1 + cos(theta)" in src2
    _compiles(src2)


def test_friendly_syntax_and_namespace():
    src = build_polar_source([{"expr": "theta^2"}])
    assert "return theta**2" in src            # ^ -> **
    assert "from numpy import (" in src
    _compiles(src)


def test_curves_capped_at_3():
    src = build_polar_source([{"expr": "1"}, {"expr": "2"}, {"expr": "3"}, {"expr": "4"}])
    assert "def _r0(theta):" in src and "def _r2(theta):" in src
    assert "def _r3(theta):" not in src        # 4th curve dropped
    _compiles(src)


def test_latex_free_by_default():
    from api import _source_needs_latex
    src = build_polar_source([{"expr": "2"}], title="Polar Demo")
    assert "add_coordinates" not in src
    assert "0°" in src                         # manual Text degree labels
    assert not _source_needs_latex(src), "default scene must be LaTeX-free"
    _compiles(src)


def test_blocked_expr_rejected():
    for bad in ("__import__('os')", "open('x')", "eval('1')"):
        try:
            build_polar_source([{"expr": bad}])
        except ValueError:
            continue
        raise AssertionError(f"blocked expr was not rejected: {bad}")


def test_all_animation_styles_compile():
    for a in ("Create", "FadeIn", "Write", "GrowFromEdge", "DrawBorderThenFill"):
        _compiles(build_polar_source([{"expr": "2"}], anim=a))


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

Run: `uv run python test_polar.py`
Expected: FAIL — `ImportError: cannot import name 'build_polar_source'`.

- [ ] **Step 3: Write minimal implementation**

Append to the **end of `builders.py`**:
```python
# ── Polar Plane ────────────────────────────────────────────────────────────
_DEG2RAD = 3.141592653589793 / 180.0
_POLAR_LABEL_DEGS = (0, 45, 90, 135, 180, 225, 270, 315)
_POLAR_POINTS_DEFAULT = {"on": False, "coords": "",  "color": "yellow"}
_POLAR_SECTOR_DEFAULT = {"on": False, "start_deg": 0.0, "end_deg": 90.0, "color": "teal"}
_POLAR_RADIAL_DEFAULT = {"on": False, "angle_deg": 30.0, "color": "red"}


def _polar_expr(expr, label):
    """Friendly-syntax translate (^ -> **) then validate; default cardioid."""
    return _validate_expr(str(expr or "").replace("^", "**"), label, default="1 + cos(theta)")


def _parse_polar_points(s):
    """Parse 'r,deg; r,deg' text into a capped list of (r, deg) float pairs."""
    out = []
    for chunk in str(s or "").replace("\n", ";").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split(",")
        if len(parts) != 2:
            continue
        try:
            out.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
        if len(out) >= 12:
            break
    return out


def build_polar_source(
    curves,
    radius_max=4.0, radius_step=1.0, azimuth_divisions=12, size=6.0,
    theta_min=0.0, theta_max=6.2832, show_curve_labels=True,
    points=None, sector=None, radial_line=None,
    cam_zoom=1.0, title="",
    use_latex=False, anim="Create",
):
    P  = {**_POLAR_POINTS_DEFAULT, **(points or {})}
    S  = {**_POLAR_SECTOR_DEFAULT, **(sector or {})}
    RL = {**_POLAR_RADIAL_DEFAULT, **(radial_line or {})}

    # --- numeric guards --------------------------------------------------
    rmax  = float(radius_max)  if float(radius_max)  > 0 else 4.0
    rstep = float(radius_step) if float(radius_step) > 0 else 1.0
    adiv  = max(2, min(48, int(azimuth_divisions or 12)))
    sz    = float(size) if float(size) > 0 else 6.0
    t0, t1 = float(theta_min), float(theta_max)
    if t0 >= t1:
        t0, t1 = 0.0, 6.2832
    dt = max(0.005, (t1 - t0) / 400.0)
    zoom_f = float(cam_zoom or 1.0)

    # --- curves (validate, fill defaults, cap at 3) ----------------------
    clean = []
    for i, c in enumerate(curves or []):
        c = c or {}
        raw = str(c.get("expr", "")).strip()
        if not raw:
            continue
        body  = _polar_expr(raw, f"Curve {i + 1} r(theta)")
        color = _text_color(c.get("color", "blue"))
        label = str(c.get("label", "")).strip()[:24]
        clean.append((body, color, label))
        if len(clean) >= 3:
            break
    if not clean:
        clean = [("1 + cos(theta)", "BLUE", "")]

    # --- header + namespace + robust polar-plot helper -------------------
    L = [
        "from manim import *",
        "import numpy as np",
        f"from numpy import ({_FG_NAMESPACE})",
        "",
        "",
        "def _polar_plot(plane, r_func, t0, t1, dt, color, width):",
        "    # Sample theta over [t0, t1]; break the path on non-finite r so a",
        "    # divergent r renders as a gap (mirrors funcgraph's _fg_plot).",
        "    grp = VGroup()",
        "    pts = []",
        "    n = int(round((t1 - t0) / dt)) + 1",
        "    for k in range(n):",
        "        th = t0 + k * dt",
        "        try:",
        "            with np.errstate(all='ignore'):",
        "                rr = float(r_func(th))",
        "        except Exception:",
        "            rr = float('nan')",
        "        if not np.isfinite(rr):",
        "            if len(pts) >= 2:",
        "                m = VMobject(color=color, stroke_width=width)",
        "                m.set_points_as_corners(pts)",
        "                grp.add(m)",
        "            pts = []",
        "        else:",
        "            pts.append(plane.polar_to_point(rr, th))",
        "    if len(pts) >= 2:",
        "        m = VMobject(color=color, stroke_width=width)",
        "        m.set_points_as_corners(pts)",
        "        grp.add(m)",
        "    return grp",
        "",
    ]
    if abs(zoom_f - 1.0) > 0.02:
        L += [
            f"config.frame_width  = {14.222 / zoom_f:.3f}",
            f"config.frame_height = {8.0 / zoom_f:.3f}",
            "",
        ]

    # --- scene: PolarPlane ----------------------------------------------
    L += [
        "class ManimScene(Scene):",
        "    def construct(self):",
        "        plane = PolarPlane(",
        f"            size={sz:.4f}, radius_max={rmax:.4f}, radius_step={rstep:.4f},",
        f"            azimuth_step={adiv}, azimuth_units='PI radians',",
        "            radius_config={'stroke_color': GREY, 'font_size': 28},",
        "        )",
    ]
    # labels: add_coordinates (MathTex) under use_latex, else manual Text degrees
    if use_latex:
        L.append("        plane.add_coordinates()")
    L.append("        self.play(Create(plane), run_time=0.9)")
    if not use_latex:
        L.append("        _lbls = VGroup()")
        for d in _POLAR_LABEL_DEGS:
            rad = d * _DEG2RAD
            L.append(
                f"        _lbls.add(Text('{d}°', font_size=20, color=GREY_B)"
                f".move_to(plane.polar_to_point({rmax * 1.08:.4f}, {rad:.4f})))"
            )
        L.append("        self.play(FadeIn(_lbls), run_time=0.5)")

    # optional title (Text — LaTeX-free)
    ttl = str(title or "").strip()[:48]
    if ttl:
        L.append(f"        _title = Text({ttl!r}, font_size=30, color=WHITE).to_edge(UP, buff=0.3)")
        L.append("        self.play(FadeIn(_title), run_time=0.4)")

    # --- curves (1..3) ---------------------------------------------------
    wrap_tmpl, rt = _FG_ANIMS.get(str(anim or "Create"), _FG_ANIMS["Create"])
    for i, (body, color, label) in enumerate(clean):
        g, fn = f"g{i}", f"_r{i}"
        L += [
            f"        def {fn}(theta):",
            f"            return {body}",
            f"        {g} = _polar_plot(plane, {fn}, {t0:.4f}, {t1:.4f}, {dt:.4f}, {color}, 3.0)",
        ]
        play = wrap_tmpl.format(g=g)
        if show_curve_labels and label:
            lv = f"lbl{i}"
            L.append(f"        {lv} = Text({label!r}, font_size=22, color={color})")
            if i == 0:
                L.append(f"        {lv}.to_corner(UR, buff=0.4)")
            else:
                L.append(f"        {lv}.next_to(lbl{i - 1}, DOWN, buff=0.15, aligned_edge=LEFT)")
            L.append(f"        self.play({play}, FadeIn({lv}), run_time={rt:.1f})")
        else:
            L.append(f"        self.play({play}, run_time={rt:.1f})")

    # --- extras (Tasks 2-4) ----------------------------------------------
    _emit_polar_points(L, P)          # Task 2
    _emit_polar_sector(L, S, rmax)    # Task 3
    _emit_polar_radial(L, RL, rmax)   # Task 4

    L.append("        self.wait(1.5)")
    return _join(L)


# Extra emitters — filled in by Tasks 2-4; no-ops until then.
def _emit_polar_points(L, P):        pass
def _emit_polar_sector(L, S, rmax):  pass
def _emit_polar_radial(L, RL, rmax): pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python test_polar.py`
Expected: PASS — `7/7 passed`.

- [ ] **Step 5: Commit**

```bash
git add test_polar.py builders.py
git commit -m "feat(polar): build_polar_source scaffold + grid/labels/curves"
```

---

### Task 2: Points overlay (labeled dots at (r, θ°))

**Files:**
- Modify: `builders.py` (`_emit_polar_points`)
- Modify: `test_polar.py` (add tests)

**Interfaces:**
- Consumes: `L: list[str]`, `P: dict` (`on/coords/color`); module helpers `_parse_polar_points`, `_text_color`, `_DEG2RAD`.
- Produces: appends a `VGroup` of `Dot`s + small coordinate `Text` labels to `L`.

- [ ] **Step 1: Write the failing test** — add to `test_polar.py`:
```python
def test_points_overlay_emits_dots():
    src = build_polar_source([{"expr": "2"}],
                             points={"on": True, "coords": "2,45; 3,135", "color": "yellow"})
    assert "Dot(plane.polar_to_point(" in src
    assert src.count("Dot(") == 2          # two points parsed
    _compiles(src)

def test_points_malformed_skipped():
    src = build_polar_source([{"expr": "2"}],
                             points={"on": True, "coords": "2,45; garbage; 3"})
    assert src.count("Dot(") == 1          # only the valid "2,45" pair survives
    _compiles(src)

def test_points_off_emits_nothing():
    src = build_polar_source([{"expr": "2"}], points={"on": False, "coords": "2,45"})
    assert "Dot(" not in src
    _compiles(src)
```

- [ ] **Step 2: Run** `uv run python test_polar.py` → FAIL (`Dot(` not in src).

- [ ] **Step 3: Implement** — replace the stub `def _emit_polar_points(L, P): pass` with:
```python
def _emit_polar_points(L, P):
    if not P.get("on"):
        return
    pts = _parse_polar_points(P.get("coords", ""))
    if not pts:
        return
    color = _text_color(P.get("color", "yellow"))
    L.append("        _pts = VGroup()")
    for (r, d) in pts:
        rad = d * _DEG2RAD
        L.append(
            f"        _pts.add(Dot(plane.polar_to_point({r:.4f}, {rad:.5f}), "
            f"radius=0.07, color={color}))"
        )
        L.append(
            f"        _pts.add(Text('({r:g}, {d:g}°)', font_size=16, color={color})"
            f".next_to(plane.polar_to_point({r:.4f}, {rad:.5f}), UR, buff=0.05))"
        )
    L.append("        self.play(FadeIn(_pts), run_time=0.6)")
```

- [ ] **Step 4: Run** `uv run python test_polar.py` → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_polar.py
git commit -m "feat(polar): labeled-points overlay at (r, theta) coordinates"
```

---

### Task 3: Angular sector overlay (shaded Polygon wedge)

**Files:** Modify `builders.py` (`_emit_polar_sector`), `test_polar.py`.

**Interfaces:**
- Consumes: `L`, `S` (`on/start_deg/end_deg/color`), `rmax: float`; `_text_color`, `_DEG2RAD`.
- Produces: a filled `Polygon` wedge (center + arc samples) faded in.

- [ ] **Step 1: Write the failing test:**
```python
def test_sector_overlay_emits_polygon_wedge():
    src = build_polar_source([{"expr": "2"}],
                             sector={"on": True, "start_deg": 0, "end_deg": 90, "color": "teal"})
    assert "Polygon(" in src
    assert "np.linspace(" in src
    assert "plane.polar_to_point(0" in src     # wedge apex at the origin
    _compiles(src)

def test_sector_off_emits_nothing():
    src = build_polar_source([{"expr": "2"}], sector={"on": False})
    assert "Polygon(" not in src
    _compiles(src)
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `_emit_polar_sector`:
```python
def _emit_polar_sector(L, S, rmax):
    if not S.get("on"):
        return
    color = _text_color(S.get("color", "teal"))
    a0 = float(S.get("start_deg", 0.0)) * _DEG2RAD
    a1 = float(S.get("end_deg", 90.0)) * _DEG2RAD
    if a1 < a0:
        a0, a1 = a1, a0
    L += [
        f"        _arc_ts = np.linspace({a0:.5f}, {a1:.5f}, 60)",
        f"        _wedge_pts = [plane.polar_to_point(0, {a0:.5f})] + "
        f"[plane.polar_to_point({rmax:.4f}, _a) for _a in _arc_ts]",
        f"        _wedge = Polygon(*_wedge_pts, stroke_width=2, stroke_color={color}, "
        f"fill_color={color}, fill_opacity=0.35)",
        "        self.play(FadeIn(_wedge), run_time=0.8)",
    ]
```

> **Why a `Polygon` wedge, not `Sector`:** `Sector`/`AnnularSector` size their radius in scene units, which won't match the plane's data-unit radius after `size`/`radius_max` scaling. Sampling `plane.polar_to_point(rmax, θ)` along the arc and closing back to `plane.polar_to_point(0, …)` (the center) guarantees the wedge lines up with the grid exactly.

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_polar.py
git commit -m "feat(polar): shaded angular-sector overlay (Polygon wedge)"
```

---

### Task 4: Radial reference line overlay

**Files:** Modify `builders.py` (`_emit_polar_radial`), `test_polar.py`.

**Interfaces:**
- Consumes: `L`, `RL` (`on/angle_deg/color`), `rmax: float`; `_text_color`, `_DEG2RAD`.
- Produces: a `Line` from the origin to the rim at the given angle, drawn with `Create`.

- [ ] **Step 1: Write the failing test:**
```python
def test_radial_line_overlay_emits_line():
    src = build_polar_source([{"expr": "2"}],
                             radial_line={"on": True, "angle_deg": 30, "color": "red"})
    assert "Line(plane.polar_to_point(0" in src
    assert "Create(_radial)" in src
    _compiles(src)

def test_radial_off_emits_nothing():
    src = build_polar_source([{"expr": "2"}], radial_line={"on": False})
    assert "_radial" not in src
    _compiles(src)
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `_emit_polar_radial`:
```python
def _emit_polar_radial(L, RL, rmax):
    if not RL.get("on"):
        return
    color = _text_color(RL.get("color", "red"))
    rad = float(RL.get("angle_deg", 30.0)) * _DEG2RAD
    L += [
        f"        _radial = Line(plane.polar_to_point(0, {rad:.5f}), "
        f"plane.polar_to_point({rmax:.4f}, {rad:.5f}), color={color}, stroke_width=4)",
        "        self.play(Create(_radial), run_time=0.6)",
    ]
```

- [ ] **Step 4: Run** `uv run python test_polar.py` → PASS.

- [ ] **Step 5: Commit**
```bash
git add builders.py test_polar.py
git commit -m "feat(polar): radial reference-line overlay"
```

---

### Task 5: Register mode + holistic LaTeX test

**Files:** Modify `api.py`, `test_polar.py`.

**Interfaces:**
- Consumes: `api._BUILDERS`, `api._source_needs_latex`.
- Produces: `"polar"` dispatchable; `use_latex` on/off behavior pinned.

- [ ] **Step 1: Write the failing test** — add to `test_polar.py`:
```python
def test_registered_in_builders():
    from api import _BUILDERS
    assert "polar" in _BUILDERS

def test_use_latex_toggles_add_coordinates_and_preflight():
    from api import _source_needs_latex
    params = dict(curves=[{"expr": "cos(3*theta)"}],
                  points={"on": True, "coords": "2,45"},
                  sector={"on": True, "start_deg": 0, "end_deg": 90},
                  radial_line={"on": True, "angle_deg": 30})
    off = build_polar_source(use_latex=False, **params)
    assert "add_coordinates" not in off
    assert not _source_needs_latex(off)
    _compiles(off)
    on = build_polar_source(use_latex=True, **params)
    assert "plane.add_coordinates()" in on
    assert _source_needs_latex(on)
    _compiles(on)
```

- [ ] **Step 2: Run** `uv run python test_polar.py` → FAIL (`'polar' not in _BUILDERS`).

- [ ] **Step 3: Implement** — in `api.py`, add to the `_BUILDERS` dict (after the `"calculus"` line):
```python
    "funcgraph":   builders.build_funcgraph_source,
    "calculus":    builders.build_calculus_source,
    "polar":       builders.build_polar_source,
}
```

- [ ] **Step 4: Run** `uv run python test_polar.py` → PASS (all tests, ~16). Then confirm no regression in the sibling suites:
```bash
uv run python test_funcgraph.py   # expect 9/9 passed
uv run python test_calculus.py    # expect 20/20 passed
```

- [ ] **Step 5: Commit**
```bash
git add api.py test_polar.py
git commit -m "feat(polar): register polar mode + holistic use_latex/preflight test"
```

---

### Task 6: Frontend — mode wiring + PolarPlanePanel

**Files:**
- Modify: `ui/src/types.ts`, `ui/src/components/ActivityBar.tsx`, `ui/src/components/Sidebar.tsx`
- Create: `ui/src/components/panels/PolarPlanePanel.tsx`

**Interfaces:**
- Produces: `PolarPlanePanel.getParams()` returning `{ mode: 'polar', params: {...} }` matching the builder signature (Task 1 Produces block).

- [ ] **Step 1: Add the mode type** — `ui/src/types.ts`, extend the union:
```typescript
export type Mode = 'trig' | 'complex' | 'linear' | 'code' | 'streamlines' | 'playground'
                 | 'geometry' | 'barchart' | 'surface3d' | 'numberline' | 'funcgraph'
                 | 'calculus' | 'polar';
```

- [ ] **Step 2: Add the ActivityBar entry** — `ui/src/components/ActivityBar.tsx`, in the `ITEMS` array after the `calculus` entry:
```typescript
  { mode: 'polar',       icon: '◎',   label: 'Polar' },
```

- [ ] **Step 3: Wire Sidebar** — `ui/src/components/Sidebar.tsx`: import, title, switch.
```typescript
import { PolarPlanePanel }  from './panels/PolarPlanePanel';
```
Add to `TITLES` (required — `Record<Mode>`):
```typescript
  polar:       'Polar Plane',
```
Add to the switch (after the calculus line):
```tsx
        {activeMode === 'polar'       && <PolarPlanePanel  ref={panelRef} />}
```

- [ ] **Step 4: Create the panel** — `ui/src/components/panels/PolarPlanePanel.tsx`:
```tsx
import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface PCurve { expr: string; color: string; label: string }

const COLORS: [string, string][] = [
  ['Blue', 'blue'], ['Red', 'red'], ['Green', 'green'], ['Yellow', 'yellow'],
  ['Purple', 'purple'], ['Orange', 'orange'], ['Teal', 'teal'], ['Pink', 'pink'], ['Gold', 'gold'],
];
const PRESETS: [string, string][] = [
  ['Preset…', ''],
  ['Rose', 'cos(3*theta)'], ['Cardioid', '1 + cos(theta)'], ['Spiral', '0.5*theta'],
  ['Limaçon', '1 + 2*cos(theta)'], ['Circle', '2'],
];
const ANIMS = ['Create', 'FadeIn', 'Write', 'GrowFromEdge', 'DrawBorderThenFill'];
const DEFAULT_CURVES: PCurve[] = [{ expr: '1 + cos(theta)', color: 'blue', label: 'cardioid' }];

export function PolarPlanePanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [curves, setCurves]       = useState<PCurve[]>(DEFAULT_CURVES);
  const [radiusMax, setRadiusMax] = useState(4);
  const [radiusStep, setRadiusStep] = useState(1);
  const [azDiv, setAzDiv]         = useState(12);
  const [size, setSize]           = useState(6);
  const [zoom, setZoom]           = useState(1.0);
  const [thetaMin, setThetaMin]   = useState(0);
  const [thetaMax, setThetaMax]   = useState(6.2832);
  const [showLabels, setShowLabels] = useState(true);

  const [ptOn, setPtOn]       = useState(false);
  const [ptCoords, setPtCoords] = useState('2,45; 3,135');
  const [ptColor, setPtColor] = useState('yellow');

  const [seOn, setSeOn]       = useState(false);
  const [seStart, setSeStart] = useState(0);
  const [seEnd, setSeEnd]     = useState(90);
  const [seColor, setSeColor] = useState('teal');

  const [rlOn, setRlOn]       = useState(false);
  const [rlAngle, setRlAngle] = useState(30);
  const [rlColor, setRlColor] = useState('red');

  const [title, setTitle]     = useState('');
  const [useLatex, setUseLatex] = useState(false);
  const [anim, setAnim]       = useState('Create');

  function updateCurve(i: number, field: keyof PCurve, val: string) {
    setCurves(prev => prev.map((c, idx) => idx === i ? { ...c, [field]: val } : c));
  }
  function addCurve() {
    if (curves.length >= 3) return;
    const defaults = ['blue', 'red', 'green'];
    setCurves(prev => [...prev, { expr: '', color: defaults[prev.length % 3], label: '' }]);
  }
  function removeCurve(i: number) {
    if (curves.length <= 1) return;
    setCurves(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'polar',
      params: {
        curves: curves.map(c => ({ expr: c.expr, color: c.color, label: c.label })),
        radius_max: radiusMax, radius_step: radiusStep,
        azimuth_divisions: azDiv, size,
        theta_min: thetaMin, theta_max: thetaMax, show_curve_labels: showLabels,
        points:      { on: ptOn, coords: ptCoords, color: ptColor },
        sector:      { on: seOn, start_deg: seStart, end_deg: seEnd, color: seColor },
        radial_line: { on: rlOn, angle_deg: rlAngle, color: rlColor },
        cam_zoom: zoom, title,
        use_latex: useLatex, anim,
      },
    }),
  }));

  return (
    <>
      <div style={{ fontSize: 11, color: 'var(--text-dim, #9aa)', lineHeight: 1.4, marginBottom: 8 }}>
        Curve formulas use <b>θ in radians</b> (e.g. <code>cos(3*theta)</code>).
        Overlay angles below are in <b>degrees</b>.
      </div>

      <div className="sec-hdr">Curves (up to 3)</div>
      {curves.map((c, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
            <select className="app-select" style={{ width: 70 }} value=""
              onChange={e => { if (e.target.value) updateCurve(i, 'expr', e.target.value); }}>
              {PRESETS.map(([l, v]) => <option key={l} value={v}>{l}</option>)}
            </select>
            <input className="app-input" style={{ flex: 1 }} value={c.expr}
              onChange={e => updateCurve(i, 'expr', e.target.value.slice(0, 120))}
              placeholder="r = f(theta), e.g. cos(3*theta)" />
            <button className="mode-toggle__btn"
              style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
              onClick={() => removeCurve(i)} title="Remove curve">×</button>
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <select className="app-select" style={{ flex: 1 }} value={c.color}
              onChange={e => updateCurve(i, 'color', e.target.value)}>
              {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input className="knob__num" style={{ width: 60, textAlign: 'center' }} value={c.label}
              onChange={e => updateCurve(i, 'label', e.target.value.slice(0, 12))} placeholder="lbl" />
          </div>
        </div>
      ))}
      {curves.length < 3 && (
        <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addCurve}>
          + Add Curve
        </button>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Grid</div>
      <Knob label="Radius Max"  min={1}   max={20} value={radiusMax}  onChange={v => setRadiusMax(Math.round(v))} decimals={0} step={1} />
      <Knob label="Radius Step" min={0.5} max={5}  value={radiusStep} onChange={setRadiusStep} decimals={1} step={0.5} />
      <Knob label="Spokes"      min={2}   max={48} value={azDiv}      onChange={v => setAzDiv(Math.round(v))}     decimals={0} step={1} />
      <Knob label="Size"        min={3}   max={10} value={size}       onChange={setSize} decimals={1} step={0.5} />
      <Knob label="Zoom"        min={0.3} max={3}  value={zoom}       onChange={setZoom} decimals={2} step={0.05} />

      <div className="sec-sep" />
      <div className="sec-hdr">Curve Range (radians)</div>
      <Knob label="θ Min" min={0}    max={6.2832}  value={thetaMin} onChange={setThetaMin} decimals={2} step={0.1} />
      <Knob label="θ Max" min={0.1}  max={25.133}  value={thetaMax} onChange={setThetaMax} decimals={2} step={0.1} />
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={showLabels}
          onChange={e => setShowLabels(e.target.checked)} /> Show curve labels</label>
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Overlays</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={ptOn}
          onChange={e => setPtOn(e.target.checked)} /> Points</label>
      </div>
      {ptOn && (
        <>
          <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
            value={ptCoords} onChange={e => setPtCoords(e.target.value.slice(0, 120))}
            placeholder="r,θ° pairs — e.g. 2,45; 3,135" />
          <select className="app-select" style={{ width: '100%' }} value={ptColor}
            onChange={e => setPtColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={seOn}
          onChange={e => setSeOn(e.target.checked)} /> Angular sector</label>
      </div>
      {seOn && (
        <>
          <Knob label="Start°" min={0} max={360} value={seStart} onChange={v => setSeStart(Math.round(v))} decimals={0} step={5} />
          <Knob label="End°"   min={0} max={360} value={seEnd}   onChange={v => setSeEnd(Math.round(v))}   decimals={0} step={5} />
          <select className="app-select" style={{ width: '100%' }} value={seColor}
            onChange={e => setSeColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </>
      )}
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={rlOn}
          onChange={e => setRlOn(e.target.checked)} /> Radial line</label>
      </div>
      {rlOn && (
        <>
          <Knob label="Angle°" min={0} max={360} value={rlAngle} onChange={v => setRlAngle(Math.round(v))} decimals={0} step={5} />
          <select className="app-select" style={{ width: '100%' }} value={rlColor}
            onChange={e => setRlColor(e.target.value)}>
            {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Labels</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />

      <div className="sec-sep" />
      <div className="sec-hdr">Options</div>
      <div className="check-row">
        <label className="app-check"><input type="checkbox" checked={useLatex}
          onChange={e => setUseLatex(e.target.checked)} /> Use LaTeX labels (π-radian)</label>
      </div>
      <select className="app-select" style={{ width: '100%', marginTop: 4 }} value={anim}
        onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(x => <option key={x} value={x}>{x}</option>)}
      </select>
    </>
  );
}
```

- [ ] **Step 5: Build to verify TS** — Run: `cd ui && npm run build`
Expected: `tsc -b` clean, `✓ built in …`. (If `TITLES` is missing the `polar` key, tsc errors — add it.)

- [ ] **Step 6: Commit**
```bash
git add ui/src/types.ts ui/src/components/ActivityBar.tsx ui/src/components/Sidebar.tsx ui/src/components/panels/PolarPlanePanel.tsx
git commit -m "feat(polar): add Polar mode button + PolarPlanePanel + wiring"
```

---

### Task 7: Smoke render test + still-frame verification

**Files:** Modify `smoke_test_v2.py` (gitignored).

**Interfaces:** Consumes `build_polar_source`, `RenderThread`, and the existing `_run`/`_show_err`/`PASS`/`FAIL`/`HERE` harness in `smoke_test_v2.py`.

- [ ] **Step 1: Add the render test** — in `smoke_test_v2.py`, after `test_calculus_real_render` (~line 1373):
```python
def test_polar_real_render():
    print("\n[28] Polar real render (grid+curve+sector+radial) → video ... ", end="", flush=True)
    script = textwrap.dedent(f"""\
        import sys, os, threading, tempfile
        sys.path.insert(0, {HERE!r})
        from renderer import RenderThread
        from builders import build_polar_source
        src = build_polar_source(
            [{{"expr": "cos(3*theta)", "color": "blue", "label": "rose"}}],
            radius_max=4, sector={{"on": True, "start_deg": 0, "end_deg": 90}},
            radial_line={{"on": True, "angle_deg": 30}},
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
And register it in `SLOW_TESTS` after the calculus entry:
```python
    ("Calculus real render (4 overlays)",                  test_calculus_real_render),
    ("Polar real render (grid+curve+extras)",              test_polar_real_render),
```

- [ ] **Step 2: Run the full smoke suite** — Run: `uv run python smoke_test_v2.py`
Expected: `Result: 33/33 passed` (32 prior + new `[28]`).

- [ ] **Step 3: Still-frame self-verification (the funcgraph lesson).** Render PNG stills and view them — "a video was produced" is not enough.
```bash
python - <<'PY'
import sys, os, tempfile
sys.path.insert(0, os.getcwd())
from builders import build_polar_source
cases = {
  "rose":       dict(curves=[{"expr":"cos(3*theta)","color":"blue","label":"rose"}]),
  "cardioid":   dict(curves=[{"expr":"1 + cos(theta)","color":"red","label":"cardioid"}]),
  "spiral":     dict(curves=[{"expr":"0.5*theta","color":"green","label":"spiral"}], theta_max=18.85),
  "extras":     dict(curves=[{"expr":"2","color":"teal"}],
                     points={"on":True,"coords":"2,45; 3,135"},
                     sector={"on":True,"start_deg":0,"end_deg":90},
                     radial_line={"on":True,"angle_deg":30}),
  "latex_on":   dict(curves=[{"expr":"1 + cos(theta)","color":"blue"}], use_latex=True),
}
out = tempfile.mkdtemp()
for name, kw in cases.items():
    src = build_polar_source(**kw)
    p = os.path.join(out, name + ".py")
    open(p, "w").write(src)
    print(name, "->", p)
print("OUT", out)
PY
# Then for each .py: manim -s -ql -o <name> <name>.py ManimScene  (latex_on needs texlive)
```
Open each PNG and confirm: the polar grid + spokes render; **rose has exactly 3 petals**; cardioid/spiral look right; degree labels sit just outside the rim at 0/45/…/315° (LaTeX-off); the `extras` case shows two labeled dots at 45°/135°, a shaded 0–90° wedge, and a red ray at 30°; the `latex_on` case shows π-radian labels (`π/2`, `π`, …). Fix any overlay that renders empty or wrong, then re-run Step 2.

- [ ] **Step 4: Commit** (smoke file is gitignored — `git status` to confirm; the assertion-free commit records the verification in history).
```bash
git add -A && git status --porcelain   # smoke_test_v2.py is gitignored; likely nothing to add
git commit -m "test(polar): add [28] real-render smoke test" --allow-empty
```

---

## Self-Review

**1. Spec coverage:**
- §1.1 polar grid (radius max/step, spokes, size) → Task 1 (`PolarPlane(...)` + guards) + Task 6 Grid knobs. ✓
- §1.2 1–3 curves + presets + friendly `theta` syntax + animated draw → Task 1 (curve loop, `_polar_plot`, `_polar_expr`, cap-at-3, cardioid fallback) + Task 6 (`PRESETS`, up-to-3 UI). ✓
- §1.3 three overlays (points / sector / radial) → Tasks 2, 3, 4 + Task 6 toggles. ✓
- §1.4 `use_latex` toggle (Text degrees vs `add_coordinates`) → Task 1 (label branch) + pinned in Task 5. ✓
- §3 six seams → builder (Tasks 1–4), api registry (Task 5), types/ActivityBar/Sidebar/panel (Task 6). ✓
- §4 payload + signature → Task 1 Produces + Task 6 `getParams`. ✓
- §5 expr pipeline + `theta`-only + presets table → Task 1 (`_polar_expr`) + Task 6 `PRESETS`. ✓
- §6 scene shape + `_polar_plot` break-on-non-finite → Task 1. ✓
- §7 panel (incl. **radians/degrees heads-up note**) → Task 6 (top muted-text block). ✓
- §8 guards/parsing/fallback → Task 1 (numeric guards, cardioid fallback) + `_parse_polar_points` (malformed skipped). ✓
- §9 testing → `test_polar.py` (Tasks 1–5), smoke `[28]` (Task 7), `npm run build` (Task 6), funcgraph/calculus regression (Task 5 Step 4). ✓
- §10 still-frame verification + Polygon-wedge sector decision → Task 7 Step 3 + Task 3 note. ✓

**2. Placeholder scan:** No "TBD/TODO/handle edge cases". Every code step shows complete code; the sector-vs-`Sector` choice carries an explicit rationale note, not a vague instruction.

**3. Type consistency:** Builder kwargs (`curves, radius_max, radius_step, azimuth_divisions, size, theta_min, theta_max, show_curve_labels, points, sector, radial_line, cam_zoom, title, use_latex, anim`) match the panel `getParams` payload and the smoke/still-frame calls exactly. Extra dict keys are identical across builder defaults, emitters, panel, and tests: points `on/coords/color`; sector `on/start_deg/end_deg/color`; radial `on/angle_deg/color`. Emitter signatures `_emit_polar_points(L, P)`, `_emit_polar_sector(L, S, rmax)`, `_emit_polar_radial(L, RL, rmax)` are consistent between the Task 1 stubs/call-sites and the Task 2–4 implementations. Helper names `_polar_plot`, `_polar_expr`, `_parse_polar_points`, `_DEG2RAD` are used consistently.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-26-polar-plane.md`.**
