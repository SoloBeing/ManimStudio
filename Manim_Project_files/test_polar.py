"""Unit tests for the Polar Plane builder (build_polar_source).

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_polar.py
"""
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_polar_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<polar>", "exec")


def _assert_no_undefined_labels(src):
    """Every next_to(lblN, ...) target must have a matching `lblN = ...` def,
    else the generated scene raises NameError at render time (audit C1)."""
    defined = set(re.findall(r"^\s*(lbl\d+)\s*=", src, re.M))
    referenced = set(re.findall(r"next_to\((lbl\d+)", src))
    missing = referenced - defined
    assert not missing, f"references undefined label vars: {sorted(missing)}"


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


def test_label_gap_does_not_reference_undefined_var():
    # C1: curve 0 unlabeled, curve 1 labeled -> must NOT next_to(lbl0) (undefined).
    src = build_polar_source([
        {"expr": "cos(3*theta)", "color": "blue"},                 # no label
        {"expr": "2*theta", "color": "red", "label": "spiral"},    # labeled
    ], show_curve_labels=True)
    _compiles(src)
    _assert_no_undefined_labels(src)


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


def test_sector_degenerate_when_start_equals_end():
    # C8: start_deg == end_deg is a zero-area wedge -> draw nothing (was a degenerate
    # Polygon because the guard only handled a1 < a0, not a1 == a0).
    src = build_polar_source([{"expr": "1 + cos(theta)"}],
                             sector={"on": True, "start_deg": 45, "end_deg": 45})
    assert "_wedge" not in src
    # a real sector (start != end) still emits the wedge
    ok = build_polar_source([{"expr": "1 + cos(theta)"}],
                            sector={"on": True, "start_deg": 0, "end_deg": 90})
    assert "_wedge = Polygon(" in ok
    _compiles(src)
    _compiles(ok)


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
