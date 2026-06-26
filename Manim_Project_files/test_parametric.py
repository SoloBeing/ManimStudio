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


def test_parametric_uses_equal_aspect_axes():
    # default ranges (x -5..5 span 10, y -4..4 span 8) -> scale 0.75 -> x_length 7.5, y_length 6
    src = _param(param_curves=[{"x_expr": "3*cos(t)", "y_expr": "3*sin(t)"}])
    assert "x_length=7.5" in src and "y_length=6" in src
    _compiles(src)


def test_parametric_grid_matches_axis_scale():
    # With Grid on, the NumberPlane must take the same equal-aspect lengths as the
    # axes so its lattice coincides with the axis ticks (radius-3 circle crosses the
    # gridline labeled 3, not ~2.25).
    src = _param(param_curves=[{"x_expr": "3*cos(t)", "y_expr": "3*sin(t)"}],
                 show_grid=True)
    grid = src.split("grid = NumberPlane(", 1)[1]
    assert "x_length=7.5, y_length=6," in grid
    _compiles(src)


def test_function_grid_unchanged():
    # funcgraph never passes grid lengths -> its NumberPlane stays length-free
    # (byte-identical to pre-parametric output).
    src = build_funcgraph_source([{"expr": "x^2"}], show_grid=True)
    grid = src.split("grid = NumberPlane(", 1)[1]
    assert "x_length=" not in grid.split(")", 1)[0]
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
