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
    _compiles(src)
    _compiles(src2)


def test_area_off_emits_nothing():
    src = build_calculus_source("x^2", area={"on": False})
    assert "get_area(" not in src
    _compiles(src)


def test_tangent_draws_line_and_slope():
    src = build_calculus_source("x^2", x0=1, tangent={"on": True, "animate_secant": False})
    assert "axes.plot(lambda x:" in src    # tangent line through (x0, f(x0))
    assert "_slope" in src
    _compiles(src)


def test_tangent_animate_secant_uses_valuetracker():
    src = build_calculus_source("x^2", x0=1, tangent={"on": True, "animate_secant": True})
    assert "ValueTracker(" in src
    assert "get_secant_slope_group(" in src
    # after the secant converges, the exact tangent line is drawn and persists
    assert "axes.plot(lambda x: _f(_x0) + _slope * (x - _x0)" in src
    assert "_sec.clear_updaters()" in src
    _compiles(src)


def test_tangent_off_emits_nothing():
    src = build_calculus_source("x^2", tangent={"on": False})
    assert "TangentLine(" not in src and "get_secant_slope_group(" not in src


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


def test_curve_drawn_with_segmented_plot():
    # C2: the visible f-curve is drawn with the segmented _fg_plot sampler (so it
    # gaps at asymptotes), while the raw axes.plot graph_f is kept as the analysis
    # object the overlays read from.
    src = build_calculus_source("x^2", a=-1, b=2)
    assert "def _fg_plot(" in src           # segmented sampler emitted into the scene
    assert "_fg_plot(axes, _f" in src       # visible curve drawn via it
    assert "graph_f = axes.plot(_f" in src  # analysis graph still created (not shown)
    _compiles(src)


def test_overlays_gated_on_validity_flag():
    # C2: a runtime _ok flag (finite + in-band over [a, b]) gates the DISPLAY of the
    # area-style overlays, so a divergent f (1/x has a pole at 0) suppresses the
    # spiking Riemann/derivative overlays instead of rendering garbage.
    src = build_calculus_source("1/x", a=-1, b=1,
                                riemann={"on": True, "method": "left"},
                                derivative={"on": True})
    assert "_ok = " in src    # validity flag defined in the finiteness pre-check
    assert "if _ok:" in src   # overlay display gated on it
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
