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
