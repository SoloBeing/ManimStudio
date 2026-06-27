"""Unit tests for the Tables & Matrices builder (build_table_source).

Pure Python: imports builders directly (no Qt, no manim render needed).
Run:  uv run python test_table.py
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from builders import build_table_source

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def _compiles(src):
    compile(src, "<table>", "exec")


def test_registered_in_builders():
    from api import _BUILDERS
    assert "table" in _BUILDERS


def test_basic_table_compiles():
    src = build_table_source(kind="table", data="a,b\nc,d")
    _compiles(src)
    assert "class ManimScene(Scene):" in src
    assert "Table(" in src
    assert "MathTable(" not in src          # plain Table by default
    assert "['a', 'b']" in src and "['c', 'd']" in src


def test_empty_data_falls_back_to_sample():
    src = build_table_source(kind="table", data="   ")
    _compiles(src)
    assert "['1', '2']" in src and "['3', '4']" in src   # built-in 2x2 sample


def test_grid_capped_at_8x8():
    rows = "\n".join(",".join(str(c) for c in range(12)) for _ in range(12))
    src = build_table_source(kind="table", data=rows)
    _compiles(src)
    # 8 rows max -> the 9th value "8" never appears as a row of 12 cells;
    # 8 cols max -> cell "8".."11" dropped from each row.
    assert "'0', '1', '2', '3', '4', '5', '6', '7'" in src
    assert "'0', '1', '2', '3', '4', '5', '6', '7', '8'" not in src


def test_pipe_separator():
    src = build_table_source(kind="table", data="a|b|c")
    _compiles(src)
    assert "['a', 'b', 'c']" in src


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
