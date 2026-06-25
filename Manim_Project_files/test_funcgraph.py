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
