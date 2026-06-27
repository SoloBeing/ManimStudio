# Tables & Matrices Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a combined `table` mode to ManimStudio — a Table/Matrix toggle with rich `Table`/`MathTable` support and a full `Matrix` operations suite (static + scalar multiply + addition + transpose + determinant).

**Architecture:** One new mode `table` registered in `api._BUILDERS`, backed by a single `build_table_source` dispatcher in `builders.py` that branches on `kind` to two internal helpers (`_build_table_kind` / `_build_matrix_kind`) plus per-operation `_emit_*` helpers. One React panel (`TablePanel.tsx`) with the toggle drives the params. No PyQt6 (`panels.py`) work — all Tier-1 modes are React-only.

**Tech Stack:** Python 3.13 (builders emit Manim source strings via `_join`), Manim Community 0.20.1, React + Vite + TypeScript (`tsc -b`), PyWebView bridge (`api.py`).

## Global Constraints

- Manim Community **0.20.1** is the target; generated source must `compile()` and render under it.
- Builders are invoked as `builder(**params)` (see `api._render_impl`); the `build_table_source` signature **is** the param contract.
- Builders return a source string via `_join(lines)`; reuse existing helpers `_text_color`, `_join`, `_validate_expr` where applicable.
- Grid size cap: **≤ 8 rows × 8 columns** (silently truncate beyond).
- The matrix half always emits `Matrix(`/`MathTex`; `MathTable` (use_latex Table) emits `MathTable(`. Both are already in `api._LATEX_TOKENS`, so the LaTeX preflight works with **no** change to `_source_needs_latex`. Plain `Table(` must stay LaTeX-free.
- Failed numeric / shape / square guards `raise ValueError("<human message>")`; `api._render_impl` wraps builder exceptions as `{"ok": False, "error": "Build error: ..."}`.
- Activity-bar icon for the mode is **`⊞`** (NOT `▦` — that is already used by `barchart`). Label **"Table"**, sidebar title **"Tables & Matrices"**.
- **Always smoke test before committing. Never push** — pushing/tagging is a separate, user-confirmed step.
- Verify UI changes with `cd ui && npm run build` (runs `tsc -b`); do **not** rely on `tsc --noEmit`.
- Python builder tests run with `uv run python test_table.py` from `Manim_Project_files/`.
- All commits end with the trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

| File | Responsibility |
|------|----------------|
| `builders.py` | New module-level consts (`_TABLE_ANIMS`, `_BRACKETS`, `_TABLE_SAMPLE`); helpers `_parse_grid`, `_grid_to_floats`, `_matrix_literal`, `_fmt_num`, `_det`; `build_table_source` dispatcher; `_build_table_kind`; `_build_matrix_kind`; matrix-op emitters `_emit_matrix_static`, `_emit_scalar_mul`, `_emit_matrix_add`, `_emit_transpose`, `_emit_determinant`. Append after the polar section (end of file). |
| `api.py` | One line in `_BUILDERS`: `"table": builders.build_table_source`. |
| `test_table.py` (new) | Builder unit tests (both kinds, all ops, all guards). Mirrors `test_polar.py`. |
| `ui/src/types.ts` | Add `'table'` to `Mode` union. |
| `ui/src/components/ActivityBar.tsx` | One entry `{ mode: 'table', icon: '⊞', label: 'Table' }`. |
| `ui/src/components/panels/TablePanel.tsx` (new) | Panel: kind toggle + conditional Table/Matrix controls; `getParams()` returns the contract. |
| `ui/src/components/Sidebar.tsx` | Import + render-switch line + `TITLES.table`. |
| `smoke_test_v2.py` | New `test_table_real_render` added to `SLOW_TESTS`. |

---

### Task 1: Grid parser + builder scaffold + Table basic + registration

**Files:**
- Modify: `builders.py` (append at end of file)
- Modify: `api.py` (`_BUILDERS` dict, ~line 116)
- Test: `test_table.py` (create)

**Interfaces:**
- Produces: `build_table_source(kind="table", data="", title="", anim="Create", cam_zoom=1.0, row_labels="", col_labels="", use_latex=False, include_outer_lines=True, highlights=None, bracket="[]", operation="none", scalar=2.0, data2="", mhighlight=None) -> str`
- Produces: `_parse_grid(s, max_r=8, max_c=8) -> list[list[str]]`
- Produces: `_build_table_kind(grid, row_labels, col_labels, use_latex, include_outer_lines, highlights, title, anim, cam_zoom) -> str`
- Consumes: existing `_join`, `_text_color` from `builders.py`.

- [ ] **Step 1: Write the failing test** — create `test_table.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — `ImportError: cannot import name 'build_table_source'`

- [ ] **Step 3: Implement minimal code** — append to the **end of `builders.py`**:

```python
# ====================================================================
#  Tables & Matrices  (mode "table")  — Table/Matrix toggle via `kind`
# ====================================================================

_TABLE_ANIMS = {
    "Create": ("Create", 1.5),
    "Write":  ("Write",  2.0),
    "FadeIn": ("FadeIn", 1.0),
}
_BRACKETS = {"[]": ("[", "]"), "()": ("(", ")"), "{}": (r"\{", r"\}")}
_TABLE_SAMPLE = [["1", "2"], ["3", "4"]]


def _parse_grid(s, max_r=8, max_c=8):
    """CSV-ish text -> padded list[list[str]], capped max_r x max_c.

    Rows split on newlines; cells split on '|' if the row contains one, else
    on ','. Whitespace stripped. Ragged rows padded with '' to the widest
    (capped) column. Empty input -> []."""
    rows = []
    for line in str(s or "").splitlines():
        line = line.strip()
        if not line:
            continue
        sep = "|" if "|" in line else ","
        cells = [c.strip() for c in line.split(sep)]
        rows.append(cells[:max_c])
        if len(rows) >= max_r:
            break
    if not rows:
        return []
    width = min(max_c, max(len(r) for r in rows))
    return [r[:width] + [""] * (width - len(r)) for r in rows]


def _matrix_literal(grid):
    """2D string grid -> Python list literal source, e.g. [['1', '2'], ...]."""
    return "[" + ", ".join(
        "[" + ", ".join(repr(c) for c in row) + "]" for row in grid
    ) + "]"


def build_table_source(
    kind="table",
    data="", title="", anim="Create", cam_zoom=1.0,
    # ---- table-only ----
    row_labels="", col_labels="", use_latex=False, include_outer_lines=True,
    highlights=None,
    # ---- matrix-only ----
    bracket="[]", operation="none", scalar=2.0, data2="", mhighlight=None,
):
    grid = _parse_grid(data) or [row[:] for row in _TABLE_SAMPLE]
    if str(kind) == "matrix":
        return _build_matrix_kind(grid, bracket, operation, scalar, data2,
                                  mhighlight, title, anim, cam_zoom)
    return _build_table_kind(grid, row_labels, col_labels, use_latex,
                             include_outer_lines, highlights, title, anim, cam_zoom)


def _build_table_kind(grid, row_labels, col_labels, use_latex,
                      include_outer_lines, highlights, title, anim, cam_zoom):
    cls = "MathTable" if use_latex else "Table"
    L = ["from manim import *", "", "", "class ManimScene(Scene):",
         "    def construct(self):"]
    L.append(f"        t = {cls}({_matrix_literal(grid)})")
    if str(title or "").strip():
        ttl = str(title).strip()[:48]
        L.append(f"        _title = Text({ttl!r}, font_size=32, color=WHITE)")
        L.append("        grp = VGroup(_title, t).arrange(DOWN, buff=0.4)")
    else:
        L.append("        grp = VGroup(t)")
    L.append("        grp.scale(min(1.0, 6.5 / grp.width, 7.0 / grp.height))")
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L.append(f"        grp.scale({zoom_f:.3f})")
    intro, rt = _TABLE_ANIMS.get(str(anim), _TABLE_ANIMS["Create"])
    L.append(f"        self.play({intro}(grp), run_time={rt})")
    L.append("        self.wait(1.5)")
    return _join(L)
```

Then register in `api.py` — add to the `_BUILDERS` dict (after the `"polar"` line, ~116):

```python
    "polar":       builders.build_polar_source,
    "table":       builders.build_table_source,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `5/5 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/api.py Manim_Project_files/test_table.py
git commit -m "feat(table): grid parser + Table scaffold + mode registration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Table feature set (labels, MathTable, outer lines, highlights, title)

**Files:**
- Modify: `builders.py` (`_build_table_kind`)
- Test: `test_table.py`

**Interfaces:**
- Consumes: `_build_table_kind`, `_matrix_literal`, `_text_color` from Task 1.
- Produces: extended `_build_table_kind` emitting `row_labels=`/`col_labels=`, `include_outer_lines=True`, `add_highlighted_cell(...)`, and `MathTable` when `use_latex`.

- [ ] **Step 1: Write the failing tests** — append to `test_table.py` (before the `TESTS = ...` collector line):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — the new label/highlight assertions fail (current `_build_table_kind` emits no labels/highlights).

- [ ] **Step 3: Implement** — replace the body of `_build_table_kind` with:

```python
def _build_table_kind(grid, row_labels, col_labels, use_latex,
                      include_outer_lines, highlights, title, anim, cam_zoom):
    cls    = "MathTable" if use_latex else "Table"
    lblcls = "MathTex"   if use_latex else "Text"
    rl = [x.strip() for x in str(row_labels or "").split(",") if x.strip()]
    cl = [x.strip() for x in str(col_labels or "").split(",") if x.strip()]

    args = [_matrix_literal(grid)]
    if rl:
        args.append("row_labels=[" + ", ".join(f"{lblcls}({x!r})" for x in rl) + "]")
    if cl:
        args.append("col_labels=[" + ", ".join(f"{lblcls}({x!r})" for x in cl) + "]")
    if include_outer_lines:
        args.append("include_outer_lines=True")

    L = ["from manim import *", "", "", "class ManimScene(Scene):",
         "    def construct(self):"]
    L.append(f"        t = {cls}(" + ", ".join(args) + ")")

    # highlights — 1-based, label-aware. Skip out-of-range (never crash).
    n_rows = len(grid) + (1 if cl else 0)
    n_cols = len(grid[0]) + (1 if rl else 0)
    for h in (highlights or []):
        h = h or {}
        try:
            r = int(h.get("row")); c = int(h.get("col"))
        except (TypeError, ValueError):
            continue
        if not (1 <= r <= n_rows and 1 <= c <= n_cols):
            continue
        color = _text_color(h.get("color", "yellow"))
        L.append(f"        t.add_highlighted_cell(({r}, {c}), color={color})")

    if str(title or "").strip():
        ttl = str(title).strip()[:48]
        L.append(f"        _title = Text({ttl!r}, font_size=32, color=WHITE)")
        L.append("        grp = VGroup(_title, t).arrange(DOWN, buff=0.4)")
    else:
        L.append("        grp = VGroup(t)")
    L.append("        grp.scale(min(1.0, 6.5 / grp.width, 7.0 / grp.height))")
    zoom_f = float(cam_zoom or 1.0)
    if abs(zoom_f - 1.0) > 0.02:
        L.append(f"        grp.scale({zoom_f:.3f})")
    intro, rt = _TABLE_ANIMS.get(str(anim), _TABLE_ANIMS["Create"])
    L.append(f"        self.play({intro}(grp), run_time={rt})")
    L.append("        self.wait(1.5)")
    return _join(L)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `13/13 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/test_table.py
git commit -m "feat(table): row/col labels, MathTable, outer lines, highlights, title

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Matrix static display + highlight

**Files:**
- Modify: `builders.py` (add `_build_matrix_kind`, `_emit_matrix_static`)
- Test: `test_table.py`

**Interfaces:**
- Consumes: `_matrix_literal`, `_BRACKETS`, `_TABLE_ANIMS`, `_text_color`, `_join`.
- Produces: `_build_matrix_kind(grid, bracket, operation, scalar, data2, mhighlight, title, anim, cam_zoom) -> str`; `_emit_matrix_static(L, grid, lb, rb, mhighlight, intro, rt)`.

- [ ] **Step 1: Write the failing tests** — append to `test_table.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — `_build_matrix_kind` does not exist (raises `NameError` at build).

- [ ] **Step 3: Implement** — append to `builders.py` (after `_build_table_kind`):

```python
def _build_matrix_kind(grid, bracket, operation, scalar, data2, mhighlight,
                       title, anim, cam_zoom):
    lb, rb = _BRACKETS.get(str(bracket), _BRACKETS["[]"])
    op = str(operation or "none")
    zoom_f = float(cam_zoom or 1.0)
    L = ["from manim import *", "import numpy as np", ""]
    if abs(zoom_f - 1.0) > 0.02:
        L += [f"config.frame_width  = {14.222 / zoom_f:.3f}",
              f"config.frame_height = {8.0 / zoom_f:.3f}", ""]
    L += ["", "class ManimScene(Scene):", "    def construct(self):"]
    if str(title or "").strip():
        ttl = str(title).strip()[:48]
        L.append(f"        _title = Text({ttl!r}, font_size=32, color=WHITE).to_edge(UP, buff=0.4)")
        L.append("        self.play(FadeIn(_title), run_time=0.4)")
    intro, rt = _TABLE_ANIMS.get(str(anim), _TABLE_ANIMS["Create"])

    if op == "scalar":
        _emit_scalar_mul(L, grid, lb, rb, scalar, intro, rt)
    elif op == "add":
        _emit_matrix_add(L, grid, data2, lb, rb, intro, rt)
    elif op == "transpose":
        _emit_transpose(L, grid, lb, rb, intro, rt)
    elif op == "determinant":
        _emit_determinant(L, grid, lb, rb, intro, rt)
    else:
        _emit_matrix_static(L, grid, lb, rb, mhighlight, intro, rt)

    L.append("        self.wait(1.5)")
    return _join(L)


def _emit_matrix_static(L, grid, lb, rb, mhighlight, intro, rt):
    L.append(f"        m = Matrix({_matrix_literal(grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        self.play({intro}(m), run_time={rt})")
    H = mhighlight or {}
    if not H.get("on"):
        return
    target = str(H.get("target", "row"))
    try:
        idx = int(H.get("index", 1))
    except (TypeError, ValueError):
        return
    color = _text_color(H.get("color", "yellow"))
    n_rows, n_cols = len(grid), len(grid[0])
    if target == "row" and 1 <= idx <= n_rows:
        sel = f"m.get_rows()[{idx - 1}]"
    elif target == "col" and 1 <= idx <= n_cols:
        sel = f"m.get_columns()[{idx - 1}]"
    elif target == "entry" and 1 <= idx <= n_rows * n_cols:
        sel = f"m.get_entries()[{idx - 1}]"
    else:
        return
    L.append(f"        _sel = {sel}")
    L.append(f"        self.play(Indicate(_sel, color={color}), run_time=0.8)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `20/20 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/test_table.py
git commit -m "feat(table): matrix static display + row/col/entry highlight

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Matrix scalar multiply

**Files:**
- Modify: `builders.py` (add `_grid_to_floats`, `_fmt_num`, `_emit_scalar_mul`)
- Test: `test_table.py`

**Interfaces:**
- Consumes: `_matrix_literal`, `_emit_scalar_mul` slot referenced by `_build_matrix_kind` (Task 3).
- Produces: `_grid_to_floats(grid, label) -> list[list[float]]` (raises `ValueError` on non-numeric); `_fmt_num(v) -> str`; `_emit_scalar_mul(L, grid, lb, rb, scalar, intro, rt)`.

- [ ] **Step 1: Write the failing tests** — append to `test_table.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — `_emit_scalar_mul` / `_fmt_num` not defined.

- [ ] **Step 3: Implement** — append to `builders.py`:

```python
def _fmt_num(v):
    """Float -> compact string: integral values lose the decimal point."""
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:.4g}"


def _grid_to_floats(grid, label):
    """2D string grid -> list[list[float]]; raise ValueError on any non-number."""
    out = []
    for row in grid:
        frow = []
        for c in row:
            try:
                frow.append(float(c))
            except (TypeError, ValueError):
                raise ValueError(
                    f"{label} requires numeric entries; got {c!r}.")
        out.append(frow)
    return out


def _emit_scalar_mul(L, grid, lb, rb, scalar, intro, rt):
    nums = _grid_to_floats(grid, "Scalar multiply")
    k = float(scalar)
    src_grid = [[_fmt_num(v) for v in row] for row in nums]
    res_grid = [[_fmt_num(k * v) for v in row] for row in nums]
    L.append(f"        m = Matrix({_matrix_literal(src_grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        _k = MathTex(r'{_fmt_num(k)} \\cdot')")
    L.append("        _row = VGroup(_k, m).arrange(RIGHT, buff=0.25)")
    L.append(f"        self.play({intro}(_row), run_time={rt})")
    L.append("        self.wait(0.5)")
    L.append(f"        res = Matrix({_matrix_literal(res_grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        res.move_to(m)")
    L.append("        self.play(FadeOut(_k), Transform(m, res), run_time=1.2)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `23/23 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/test_table.py
git commit -m "feat(table): matrix scalar multiply (numeric guard + Transform)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Matrix addition

**Files:**
- Modify: `builders.py` (add `_emit_matrix_add`)
- Test: `test_table.py`

**Interfaces:**
- Consumes: `_parse_grid`, `_grid_to_floats`, `_fmt_num`, `_matrix_literal`.
- Produces: `_emit_matrix_add(L, grid, data2, lb, rb, intro, rt)` (raises `ValueError` on missing/mismatched/non-numeric B).

- [ ] **Step 1: Write the failing tests** — append to `test_table.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — `_emit_matrix_add` not defined.

- [ ] **Step 3: Implement** — append to `builders.py`:

```python
def _emit_matrix_add(L, grid, data2, lb, rb, intro, rt):
    A = _grid_to_floats(grid, "Matrix addition (A)")
    gridB = _parse_grid(data2)
    if not gridB:
        raise ValueError("Matrix addition needs a second matrix (B).")
    B = _grid_to_floats(gridB, "Matrix addition (B)")
    if len(A) != len(B) or any(len(ra) != len(rb_) for ra, rb_ in zip(A, B)):
        raise ValueError(
            "Matrix addition requires both matrices to have the same shape.")
    aS = [[_fmt_num(v) for v in row] for row in A]
    bS = [[_fmt_num(v) for v in row] for row in B]
    C  = [[_fmt_num(a + b) for a, b in zip(ra, rb_)] for ra, rb_ in zip(A, B)]
    L.append(f"        mA = Matrix({_matrix_literal(aS)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        mB = Matrix({_matrix_literal(bS)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _plus = MathTex('+')")
    L.append("        _eq = MathTex('=')")
    L.append(f"        mC = Matrix({_matrix_literal(C)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        _row = VGroup(mA, _plus, mB, _eq, mC).arrange(RIGHT, buff=0.3)")
    L.append("        _row.scale(min(1.0, 12.0 / _row.width))")
    L.append(f"        self.play({intro}(mA), {intro}(mB), FadeIn(_plus), run_time={rt})")
    L.append("        self.play(Write(_eq), FadeIn(mC), run_time=1.0)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `26/26 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/test_table.py
git commit -m "feat(table): matrix addition (shape + numeric guards)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Matrix transpose

**Files:**
- Modify: `builders.py` (add `_emit_transpose`)
- Test: `test_table.py`

**Interfaces:**
- Consumes: `_matrix_literal`.
- Produces: `_emit_transpose(L, grid, lb, rb, intro, rt)` (no numeric requirement — string swap).

- [ ] **Step 1: Write the failing tests** — append to `test_table.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — `_emit_transpose` not defined.

- [ ] **Step 3: Implement** — append to `builders.py`:

```python
def _emit_transpose(L, grid, lb, rb, intro, rt):
    T = [list(col) for col in zip(*grid)]   # grid is rectangular (padded)
    L.append(f"        m = Matrix({_matrix_literal(grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        self.play({intro}(m), run_time={rt})")
    L.append("        self.wait(0.4)")
    L.append(f"        mT = Matrix({_matrix_literal(T)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append("        mT.move_to(m)")
    L.append("        _lbl = MathTex('A^T').next_to(mT, UP, buff=0.3)")
    L.append("        self.play(Transform(m, mT), FadeIn(_lbl), run_time=1.2)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `28/28 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/test_table.py
git commit -m "feat(table): matrix transpose (row/col swap + A^T label)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Matrix determinant

**Files:**
- Modify: `builders.py` (add `_det`, `_emit_determinant`)
- Test: `test_table.py`

**Interfaces:**
- Consumes: `_grid_to_floats`, `_fmt_num`, `_matrix_literal`.
- Produces: `_det(m) -> float` (2x2/3x3); `_emit_determinant(L, grid, lb, rb, intro, rt)` (raises `ValueError` if non-square 2x2/3x3 or non-numeric).

- [ ] **Step 1: Write the failing tests** — append to `test_table.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: FAIL — `_det` / `_emit_determinant` not defined.

- [ ] **Step 3: Implement** — append to `builders.py`:

```python
def _det(m):
    """Determinant of a 2x2 or 3x3 numeric matrix."""
    if len(m) == 2:
        return m[0][0] * m[1][1] - m[0][1] * m[1][0]
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _emit_determinant(L, grid, lb, rb, intro, rt):
    n = len(grid)
    if n not in (2, 3) or any(len(r) != n for r in grid):
        raise ValueError("Determinant requires a square 2x2 or 3x3 matrix.")
    M = _grid_to_floats(grid, "Determinant")
    dstr = _fmt_num(_det(M))
    L.append(f"        m = Matrix({_matrix_literal(grid)}, "
             f"left_bracket={lb!r}, right_bracket={rb!r})")
    L.append(f"        self.play({intro}(m), run_time={rt})")
    L.append(f"        _det = MathTex(r'\\det(A) = {dstr}', font_size=44)")
    L.append("        _det.next_to(m, DOWN, buff=0.5)")
    L.append("        self.play(Write(_det), run_time=1.0)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Manim_Project_files && uv run python test_table.py`
Expected: PASS — `34/34 passed`

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/builders.py Manim_Project_files/test_table.py
git commit -m "feat(table): matrix determinant (2x2/3x3, square+numeric guards)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: React panel + UI wiring

**Files:**
- Modify: `ui/src/types.ts` (`Mode` union)
- Modify: `ui/src/components/ActivityBar.tsx` (`ITEMS`)
- Create: `ui/src/components/panels/TablePanel.tsx`
- Modify: `ui/src/components/Sidebar.tsx` (import + `TITLES` + render switch)

**Interfaces:**
- Consumes: `PanelHandle` from `types.ts`; the `build_table_source` param contract (Tasks 1–7).
- Produces: `TablePanel` React component whose `getParams()` returns `{ mode: 'table', params: {...} }` matching the builder signature.

- [ ] **Step 1: Add `'table'` to the `Mode` union** in `ui/src/types.ts`:

```typescript
export type Mode = 'trig' | 'complex' | 'linear' | 'code' | 'streamlines' | 'playground'
                 | 'geometry' | 'barchart' | 'surface3d' | 'numberline' | 'funcgraph'
                 | 'calculus' | 'polar' | 'table';
```

- [ ] **Step 2: Add the ActivityBar entry** in `ui/src/components/ActivityBar.tsx` — insert after the `polar` line in `ITEMS`:

```typescript
  { mode: 'polar',       icon: '◎',   label: 'Polar' },
  { mode: 'table',       icon: '⊞',   label: 'Table' },
```

- [ ] **Step 3: Create `ui/src/components/panels/TablePanel.tsx`:**

```typescript
import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import type { PanelHandle } from '../../types';

interface Highlight { row: number; col: number; color: string }

const COLORS: [string, string][] = [
  ['Yellow', 'yellow'], ['Red', 'red'], ['Green', 'green'], ['Blue', 'blue'],
  ['Teal', 'teal'], ['Orange', 'orange'], ['Purple', 'purple'], ['Gold', 'gold'],
];
const ANIMS = ['Create', 'Write', 'FadeIn'];
const BRACKETS: [string, string][] = [['[ ]', '[]'], ['( )', '()'], ['{ }', '{}']];
const OPERATIONS: [string, string][] = [
  ['None (static)', 'none'], ['Scalar multiply', 'scalar'], ['Add (A + B)', 'add'],
  ['Transpose', 'transpose'], ['Determinant', 'determinant'],
];
const MTARGETS: [string, string][] = [['Row', 'row'], ['Column', 'col'], ['Entry', 'entry']];

export function TablePanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [kind, setKind]   = useState<'table' | 'matrix'>('table');
  const [data, setData]   = useState('1, 2, 3\n4, 5, 6');
  const [title, setTitle] = useState('');
  const [anim, setAnim]   = useState('Create');
  const [zoom, setZoom]   = useState(1.0);

  // table-only
  const [rowLabels, setRowLabels] = useState('');
  const [colLabels, setColLabels] = useState('');
  const [useLatex, setUseLatex]   = useState(false);
  const [outerLines, setOuterLines] = useState(true);
  const [highlights, setHighlights] = useState<Highlight[]>([]);

  // matrix-only
  const [bracket, setBracket]     = useState('[]');
  const [operation, setOperation] = useState('none');
  const [scalar, setScalar]       = useState(2);
  const [data2, setData2]         = useState('1, 0\n0, 1');
  const [mhOn, setMhOn]           = useState(false);
  const [mhTarget, setMhTarget]   = useState('row');
  const [mhIndex, setMhIndex]     = useState(1);
  const [mhColor, setMhColor]     = useState('yellow');

  function addHighlight() {
    setHighlights(prev => [...prev, { row: 1, col: 1, color: 'yellow' }]);
  }
  function updateHighlight(i: number, field: keyof Highlight, val: string | number) {
    setHighlights(prev => prev.map((h, idx) => idx === i ? { ...h, [field]: val } : h));
  }
  function removeHighlight(i: number) {
    setHighlights(prev => prev.filter((_, idx) => idx !== i));
  }

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'table',
      params: {
        kind, data, title, anim, cam_zoom: zoom,
        row_labels: rowLabels, col_labels: colLabels,
        use_latex: useLatex, include_outer_lines: outerLines,
        highlights: highlights.map(h => ({ row: h.row, col: h.col, color: h.color })),
        bracket, operation, scalar, data2,
        mhighlight: { on: mhOn, target: mhTarget, index: mhIndex, color: mhColor },
      },
    }),
  }));

  return (
    <>
      <div className="mode-toggle" style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        <button className={`mode-toggle__btn${kind === 'table' ? ' active' : ''}`}
          style={{ flex: 1 }} onClick={() => setKind('table')}>Table</button>
        <button className={`mode-toggle__btn${kind === 'matrix' ? ' active' : ''}`}
          style={{ flex: 1 }} onClick={() => setKind('matrix')}>Matrix</button>
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-dim, #9aa)', lineHeight: 1.4, marginBottom: 8 }}>
        One <b>row per line</b>; separate cells with <b>,</b> or <b>|</b>. Max 8×8.
      </div>

      <div className="sec-hdr">Data</div>
      <textarea className="app-input" style={{ width: '100%', boxSizing: 'border-box', minHeight: 70, fontFamily: 'monospace' }}
        value={data} onChange={e => setData(e.target.value)} placeholder="1, 2, 3&#10;4, 5, 6" />

      {kind === 'table' && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Labels</div>
          <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
            value={rowLabels} onChange={e => setRowLabels(e.target.value)} placeholder="Row labels (comma-sep)" />
          <input className="app-input" style={{ width: '100%', boxSizing: 'border-box' }}
            value={colLabels} onChange={e => setColLabels(e.target.value)} placeholder="Column labels (comma-sep)" />

          <div className="sec-sep" />
          <div className="sec-hdr">Highlights (1-based; counts label row/col)</div>
          {highlights.map((h, i) => (
            <div key={i} style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
              <input className="knob__num" style={{ width: 40, textAlign: 'center' }} type="number" value={h.row}
                onChange={e => updateHighlight(i, 'row', Number(e.target.value))} title="row" />
              <input className="knob__num" style={{ width: 40, textAlign: 'center' }} type="number" value={h.col}
                onChange={e => updateHighlight(i, 'col', Number(e.target.value))} title="col" />
              <select className="app-select" style={{ flex: 1 }} value={h.color}
                onChange={e => updateHighlight(i, 'color', e.target.value)}>
                {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button className="mode-toggle__btn" style={{ width: 22, height: 22, padding: 0, fontSize: 12, borderRadius: 4 }}
                onClick={() => removeHighlight(i)} title="Remove">×</button>
            </div>
          ))}
          <button className="mode-toggle__btn" style={{ width: '100%', marginTop: 4 }} onClick={addHighlight}>+ Add Highlight</button>

          <div className="sec-sep" />
          <div className="sec-hdr">Options</div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={useLatex}
              onChange={e => setUseLatex(e.target.checked)} /> Math cells (LaTeX / MathTable)</label>
          </div>
          <div className="check-row">
            <label className="app-check"><input type="checkbox" checked={outerLines}
              onChange={e => setOuterLines(e.target.checked)} /> Outer lines</label>
          </div>
        </>
      )}

      {kind === 'matrix' && (
        <>
          <div className="sec-sep" />
          <div className="sec-hdr">Brackets</div>
          <select className="app-select" style={{ width: '100%' }} value={bracket}
            onChange={e => setBracket(e.target.value)}>
            {BRACKETS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>

          <div className="sec-sep" />
          <div className="sec-hdr">Operation</div>
          <select className="app-select" style={{ width: '100%' }} value={operation}
            onChange={e => setOperation(e.target.value)}>
            {OPERATIONS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
          </select>

          {operation === 'scalar' && (
            <Knob label="Scalar k" min={-10} max={10} value={scalar} onChange={setScalar} decimals={1} step={0.5} />
          )}
          {operation === 'add' && (
            <>
              <div className="sec-hdr" style={{ marginTop: 6 }}>Second matrix (B)</div>
              <textarea className="app-input" style={{ width: '100%', boxSizing: 'border-box', minHeight: 50, fontFamily: 'monospace' }}
                value={data2} onChange={e => setData2(e.target.value)} placeholder="1, 0&#10;0, 1" />
            </>
          )}
          {operation === 'none' && (
            <>
              <div className="check-row" style={{ marginTop: 6 }}>
                <label className="app-check"><input type="checkbox" checked={mhOn}
                  onChange={e => setMhOn(e.target.checked)} /> Highlight</label>
              </div>
              {mhOn && (
                <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  <select className="app-select" style={{ flex: 1 }} value={mhTarget}
                    onChange={e => setMhTarget(e.target.value)}>
                    {MTARGETS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                  <input className="knob__num" style={{ width: 44, textAlign: 'center' }} type="number" value={mhIndex}
                    onChange={e => setMhIndex(Number(e.target.value))} title="index (1-based)" />
                  <select className="app-select" style={{ flex: 1 }} value={mhColor}
                    onChange={e => setMhColor(e.target.value)}>
                    {COLORS.map(([l, v]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
              )}
            </>
          )}
        </>
      )}

      <div className="sec-sep" />
      <div className="sec-hdr">Title & Animation</div>
      <input className="app-input" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 4 }}
        value={title} onChange={e => setTitle(e.target.value.slice(0, 48))} placeholder="Title (optional)" />
      <select className="app-select" style={{ width: '100%', marginBottom: 4 }} value={anim}
        onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(x => <option key={x} value={x}>{x}</option>)}
      </select>
      <Knob label="Zoom" min={0.3} max={3} value={zoom} onChange={setZoom} decimals={2} step={0.05} />
    </>
  );
}
```

- [ ] **Step 4: Wire into `ui/src/components/Sidebar.tsx`** — three edits:

Add the import after the `PolarPlanePanel` import:

```typescript
import { PolarPlanePanel }  from './panels/PolarPlanePanel';
import { TablePanel }       from './panels/TablePanel';
```

Add the `TITLES` entry (after the `polar` line):

```typescript
  polar:       'Polar Plane',
  table:       'Tables & Matrices',
```

Add the render-switch line (after the `polar` line):

```typescript
        {activeMode === 'polar'       && <PolarPlanePanel  ref={panelRef} />}
        {activeMode === 'table'       && <TablePanel       ref={panelRef} />}
```

- [ ] **Step 5: Verify the UI build is clean**

Run: `cd ui && npm run build`
Expected: PASS — `tsc -b` succeeds with no errors and Vite emits the bundle. (A missing `TITLES.table` entry or a `Mode`-union omission would fail the exhaustive `Record<Mode, string>` check here.)

- [ ] **Step 6: Commit**

```bash
git add Manim_Project_files/ui/src/types.ts Manim_Project_files/ui/src/components/ActivityBar.tsx Manim_Project_files/ui/src/components/panels/TablePanel.tsx Manim_Project_files/ui/src/components/Sidebar.tsx
git commit -m "feat(table): React panel + activity-bar/sidebar wiring (Table/Matrix toggle)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Smoke-suite real render + final gate

**Files:**
- Modify: `smoke_test_v2.py` (new `test_table_real_render`, add to `SLOW_TESTS`)

**Interfaces:**
- Consumes: `build_table_source` (Tasks 1–7); `renderer.RenderThread` (existing).
- Produces: `test_table_real_render()` returning `True`/`False` like the other slow tests.

- [ ] **Step 1: Add the failing smoke test** — in `smoke_test_v2.py`, insert after `test_parametric_real_render` (the `[29]` block), before `API_TESTS`:

```python
def test_table_real_render():
    print("\n[30] Tables & Matrices real render (matrix + determinant) → video ... ", end="", flush=True)
    script = textwrap.dedent(f"""\
        import sys, os, threading, tempfile
        sys.path.insert(0, {HERE!r})
        from renderer import RenderThread
        from builders import build_table_source
        src = build_table_source(
            kind="matrix", data="1,2\\n3,4",
            operation="determinant", bracket="[]", title="Determinant",
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

Then add it to the `SLOW_TESTS` list (after the parametric entry):

```python
    ("Parametric real render (curve+tracer+vector+markers)", test_parametric_real_render),
    ("Tables & Matrices real render (matrix+determinant)",   test_table_real_render),
```

- [ ] **Step 2: Run the smoke suite to verify the new test runs (and the others still pass)**

Run: `cd Manim_Project_files && uv run python smoke_test_v2.py`
Expected: PASS — `35/35 passed` (the `[30]` table render produces a video; LaTeX must be installed for the matrix/determinant render).

- [ ] **Step 3: Final regression gate — run all builder suites + UI build**

Run:
```bash
cd Manim_Project_files
uv run python test_table.py        # expect 34/34
uv run python test_polar.py        # expect no regression
uv run python test_calculus.py     # expect no regression
uv run python test_funcgraph.py    # expect no regression
uv run python test_parametric.py   # expect no regression
cd ui && npm run build             # expect clean
```
Expected: every suite green; `npm run build` clean.

- [ ] **Step 4: Manual render-verify (stills)** — render one example per major path and eyeball the PNG (use `-s` for a still frame):

```bash
cd Manim_Project_files
# labelled + highlighted table
uv run python -c "from builders import build_table_source; open('/tmp/t1.py','w').write(build_table_source(kind='table', data='1,2|3,4', row_labels='R1,R2', col_labels='C1,C2', highlights=[{'row':2,'col':2,'color':'yellow'}], title='Demo'))"
# math table, bracketed matrix, scalar-multiply, determinant similarly...
```
Render each with `manim -s -ql /tmp/t1.py ManimScene` and confirm: labels present, cell (2,2) highlighted; MathTable renders fractions; matrix brackets correct; scalar result = k×entries; `det(A) = -2` shown. (This mirrors the still-verification done for polar/calculus/parametric.)

- [ ] **Step 5: Commit**

```bash
git add Manim_Project_files/smoke_test_v2.py
git commit -m "test(table): smoke real-render for Tables & Matrices mode [30]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes for the implementer

- **Do not push or tag.** Release is a separate user-confirmed step (memory: [[feedback_workflow]]).
- The branch already carries 5 unpushed Tier-1 audit fixes + 1 spec-doc commit ahead of `origin/ui/editor-redesign`; this plan adds more on top. That is expected.
- After all tasks pass, the natural follow-ups (separate sessions) are GUI user-verification then release, per the established cadence.
- Out of scope (do not add): matrix multiplication/inverse/eigen/RREF, `MobjectTable`/`MobjectMatrix`, per-cell styling beyond highlights, >8×8 grids, PyQt6 parity.
