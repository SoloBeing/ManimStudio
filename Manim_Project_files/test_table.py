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


def test_mathtable_when_use_latex():
    from api import _source_needs_latex
    plain = build_table_source(kind="table", data="1,2\n3,4")
    assert not _source_needs_latex(plain), "plain Table must be LaTeX-free"
    math = build_table_source(kind="table", data=r"\frac{1}{2},x^2", use_latex=True)
    _compiles(math)
    assert "MathTable(" in math
    assert _source_needs_latex(math)


def test_row_and_col_labels():
    src = build_table_source(kind="table", data="1,2\n3,4",
                             row_labels="R1, R2", col_labels="C1, C2")
    _compiles(src)
    assert "row_labels=[Text('R1'), Text('R2')]" in src
    assert "col_labels=[Text('C1'), Text('C2')]" in src


def test_labels_are_mathtex_in_latex_mode():
    src = build_table_source(kind="table", data="1,2\n3,4",
                             row_labels="a", use_latex=True)
    _compiles(src)
    assert "row_labels=[MathTex('a')]" in src


def test_outer_lines_toggle():
    on = build_table_source(kind="table", data="1,2\n3,4", include_outer_lines=True)
    off = build_table_source(kind="table", data="1,2\n3,4", include_outer_lines=False)
    assert "include_outer_lines=True" in on
    assert "include_outer_lines=True" not in off
    _compiles(on); _compiles(off)


def test_highlight_emits_add_highlighted_cell():
    src = build_table_source(kind="table", data="1,2\n3,4",
                             highlights=[{"row": 2, "col": 2, "color": "yellow"}])
    _compiles(src)
    assert "t.add_highlighted_cell((2, 2), color=YELLOW)" in src


def test_out_of_range_highlight_skipped():
    # 2x2 grid, no labels -> valid coords are 1..2; (5,5) is out of range.
    src = build_table_source(kind="table", data="1,2\n3,4",
                             highlights=[{"row": 5, "col": 5, "color": "red"}])
    _compiles(src)
    assert "add_highlighted_cell" not in src


def test_highlight_range_accounts_for_labels():
    # With col_labels present, the label row is index 1, so (3,2) is valid
    # for a 2-data-row table (rows 1=labels, 2..3=data).
    src = build_table_source(kind="table", data="1,2\n3,4",
                             col_labels="C1,C2",
                             highlights=[{"row": 3, "col": 2, "color": "teal"}])
    _compiles(src)
    assert "t.add_highlighted_cell((3, 2), color=TEAL)" in src


def test_title_grouped_above_table():
    src = build_table_source(kind="table", data="1,2\n3,4", title="My Table")
    _compiles(src)
    assert "_title = Text('My Table'" in src
    assert "VGroup(_title, t).arrange(DOWN" in src


def test_matrix_static_emits_matrix_with_brackets():
    src = build_table_source(kind="matrix", data="1,2\n3,4", bracket="()")
    _compiles(src)
    assert "Matrix([['1', '2'], ['3', '4']]" in src
    assert "left_bracket='('" in src and "right_bracket=')'" in src


def test_matrix_brace_brackets():
    src = build_table_source(kind="matrix", data="1\n2", bracket="{}")
    _compiles(src)
    assert r"left_bracket='\\{'" in src and r"right_bracket='\\}'" in src


def test_matrix_needs_latex():
    from api import _source_needs_latex
    src = build_table_source(kind="matrix", data="1,2\n3,4")
    assert _source_needs_latex(src), "matrix must trigger the LaTeX preflight"


def test_matrix_row_highlight_indicates():
    src = build_table_source(kind="matrix", data="1,2\n3,4",
                             mhighlight={"on": True, "target": "row", "index": 1, "color": "yellow"})
    _compiles(src)
    assert "m.get_rows()[0]" in src
    assert "Indicate(" in src


def test_matrix_col_highlight():
    src = build_table_source(kind="matrix", data="1,2\n3,4",
                             mhighlight={"on": True, "target": "col", "index": 2, "color": "red"})
    _compiles(src)
    assert "m.get_columns()[1]" in src


def test_matrix_highlight_off_emits_nothing():
    src = build_table_source(kind="matrix", data="1,2\n3,4",
                             mhighlight={"on": False, "target": "row", "index": 1})
    _compiles(src)
    assert "Indicate(" not in src


def test_matrix_highlight_out_of_range_skipped():
    src = build_table_source(kind="matrix", data="1,2\n3,4",
                             mhighlight={"on": True, "target": "row", "index": 9})
    _compiles(src)
    assert "Indicate(" not in src


def test_scalar_multiply_builds_result_and_transform():
    src = build_table_source(kind="matrix", data="1,2\n3,4",
                             operation="scalar", scalar=3)
    _compiles(src)
    # source matrix and the x3 result both present
    assert "Matrix([['1', '2'], ['3', '4']]" in src
    assert "Matrix([['3', '6'], ['9', '12']]" in src
    assert "Transform(m, res" in src
    assert r"3 \cdot" in src


def test_scalar_multiply_non_numeric_raises():
    try:
        build_table_source(kind="matrix", data="a,b\nc,d", operation="scalar", scalar=2)
    except ValueError:
        return
    raise AssertionError("non-numeric scalar multiply must raise ValueError")


def test_fmt_num_integers_have_no_decimal():
    from builders import _fmt_num
    assert _fmt_num(6.0) == "6"
    assert _fmt_num(-2.0) == "-2"
    assert _fmt_num(1.5) == "1.5"


def test_matrix_add_builds_sum():
    src = build_table_source(kind="matrix", data="1,2\n3,4",
                             operation="add", data2="5,6\n7,8")
    _compiles(src)
    assert "mA = Matrix([['1', '2'], ['3', '4']]" in src
    assert "mB = Matrix([['5', '6'], ['7', '8']]" in src
    assert "mC = Matrix([['6', '8'], ['10', '12']]" in src
    assert "MathTex('+')" in src and "MathTex('=')" in src


def test_matrix_add_shape_mismatch_raises():
    try:
        build_table_source(kind="matrix", data="1,2\n3,4",
                           operation="add", data2="5,6,7")
    except ValueError:
        return
    raise AssertionError("shape mismatch in addition must raise ValueError")


def test_matrix_add_missing_second_raises():
    try:
        build_table_source(kind="matrix", data="1,2\n3,4",
                           operation="add", data2="")
    except ValueError:
        return
    raise AssertionError("missing second matrix must raise ValueError")


def test_transpose_swaps_rows_and_cols():
    src = build_table_source(kind="matrix", data="1,2,3\n4,5,6", operation="transpose")
    _compiles(src)
    assert "m = Matrix([['1', '2', '3'], ['4', '5', '6']]" in src
    assert "mT = Matrix([['1', '4'], ['2', '5'], ['3', '6']]" in src
    assert "Transform(m, mT" in src
    assert "MathTex('A^T')" in src


def test_transpose_allows_non_numeric():
    # transpose is a pure layout swap; symbolic entries are fine (no ValueError).
    src = build_table_source(kind="matrix", data="a,b\nc,d", operation="transpose")
    _compiles(src)
    assert "mT = Matrix([['a', 'c'], ['b', 'd']]" in src


def test_determinant_2x2_value():
    src = build_table_source(kind="matrix", data="1,2\n3,4", operation="determinant")
    _compiles(src)
    assert r"\det(A) = -2" in src          # 1*4 - 2*3 = -2


def test_determinant_3x3_value():
    src = build_table_source(kind="matrix", data="1,2,3\n4,5,6\n7,8,10",
                             operation="determinant")
    _compiles(src)
    assert r"\det(A) = -3" in src          # rule-of-Sarrus = -3


def test_determinant_non_square_raises():
    try:
        build_table_source(kind="matrix", data="1,2,3\n4,5,6", operation="determinant")
    except ValueError:
        return
    raise AssertionError("non-square determinant must raise ValueError")


def test_determinant_too_big_raises():
    big = "\n".join("1,2,3,4" for _ in range(4))   # 4x4
    try:
        build_table_source(kind="matrix", data=big, operation="determinant")
    except ValueError:
        return
    raise AssertionError("4x4 determinant must raise ValueError")


def test_determinant_non_numeric_raises():
    try:
        build_table_source(kind="matrix", data="a,b\nc,d", operation="determinant")
    except ValueError:
        return
    raise AssertionError("non-numeric determinant must raise ValueError")


def test_det_helper_values():
    from builders import _det
    assert _det([[1, 2], [3, 4]]) == -2
    assert _det([[1, 2, 3], [4, 5, 6], [7, 8, 10]]) == -3


def test_matrix_static_fits_frame():
    src = build_table_source(kind="matrix", data="1,2\n3,4")
    _compiles(src)
    assert "11.5 / m.width" in src and "m.scale(_sf)" in src


def test_large_matrix_compiles_with_fit():
    big = "\n".join(",".join(str(c) for c in range(8)) for _ in range(8))  # 8x8
    src = build_table_source(kind="matrix", data=big)
    _compiles(src)
    assert ".scale(_sf)" in src


def test_scalar_result_scaled_to_match_source():
    src = build_table_source(kind="matrix", data="1,2\n3,4", operation="scalar", scalar=3)
    _compiles(src)
    assert "res.scale(_sf)" in src      # Transform target matches source size


def test_matrix_no_dead_numpy_import():
    src = build_table_source(kind="matrix", data="1,2\n3,4")
    assert "import numpy as np" not in src


def test_nan_inf_cells_rejected():
    for bad in ("1,nan\n3,4", "1,inf\n3,4"):
        try:
            build_table_source(kind="matrix", data=bad, operation="scalar", scalar=2)
        except ValueError:
            continue
        raise AssertionError(f"non-finite cell not rejected: {bad!r}")


def test_table_scale_guarded_against_zero():
    src = build_table_source(kind="table", data="1,2\n3,4")
    assert "max(grp.width, 1e-6)" in src and "max(grp.height, 1e-6)" in src


def test_transpose_target_scaled_to_match():
    src = build_table_source(kind="matrix", data="1,2,3\n4,5,6", operation="transpose")
    _compiles(src)
    assert "mT.scale(_sf)" in src               # transpose target scaled
    assert "/ mT.width" in src and "/ mT.height" in src   # joint fit includes mT shape


def test_nonsquare_transpose_compiles():
    src = build_table_source(kind="matrix", data="1,2,3,4,5,6,7,8", operation="transpose")  # 1x8 -> 8x1
    _compiles(src)
    assert "mT.scale(_sf)" in src


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
