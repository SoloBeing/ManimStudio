"""Unit tests for the Function Grapher builder (build_funcgraph_source).

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_funcgraph.py
"""
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_funcgraph_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<funcgraph>", "exec")


def _assert_no_undefined_labels(src):
    """Every next_to(lblN, ...) target must have a matching `lblN = ...` def,
    else the generated scene raises NameError at render time (audit C1)."""
    defined = set(re.findall(r"^\s*(lbl\d+)\s*=", src, re.M))
    referenced = set(re.findall(r"next_to\((lbl\d+)", src))
    missing = referenced - defined
    assert not missing, f"references undefined label vars: {sorted(missing)}"


def test_single_curve_compiles():
    src = build_funcgraph_source([{"expr": "x^2", "color": "blue"}])
    _compiles(src)
    assert "_fg_plot(axes, _f0" in src
    assert "return x**2" in src            # friendly ^ translated to **
    assert "set_points_as_corners" in src  # robust segment-plot helper


def test_namespace_injected():
    src = build_funcgraph_source([{"expr": "sin(x)"}])
    assert "from numpy import (" in src
    assert "return sin(x)" in src
    _compiles(src)


def test_strict_numpy_still_works():
    src = build_funcgraph_source([{"expr": "np.exp(-x**2)"}])
    assert "return np.exp(-x**2)" in src
    _compiles(src)


def test_multiple_curves_and_dashed():
    src = build_funcgraph_source([
        {"expr": "x^2",    "color": "blue", "label": "f", "style": "solid"},
        {"expr": "sin(x)", "color": "red",  "label": "g", "style": "dashed"},
    ])
    assert "_fg_plot(axes, _f0" in src and "_fg_plot(axes, _f1" in src
    assert "dashed=True" in src                # 2nd curve dashed
    assert "dashed=False" in src               # 1st curve solid
    assert "Text('f'" in src and "Text('g'" in src
    _compiles(src)


def test_empty_or_blank_curves_fallback():
    src = build_funcgraph_source([])
    assert "return x**2" in src                # fallback to one x**2 curve
    _compiles(src)
    src2 = build_funcgraph_source([{"expr": "   "}])  # blank expr skipped
    assert "return x**2" in src2
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


def test_label_gap_does_not_reference_undefined_var():
    # C1: curve 0 unlabeled, curve 1 labeled -> stacking must NOT next_to(lbl0)
    # because lbl0 is never created (label-emit is gated on `if label:`).
    src = build_funcgraph_source([
        {"expr": "x^2", "color": "blue"},                  # no label
        {"expr": "sin(x)", "color": "red", "label": "g"},  # labeled
    ])
    _compiles(src)
    _assert_no_undefined_labels(src)


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
