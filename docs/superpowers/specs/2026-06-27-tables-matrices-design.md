# Tables & Matrices mode — design

**Date:** 2026-06-27
**Branch:** `ui/editor-redesign`
**Tier:** Tier 2, feature #1 of the post-Tier-1 roadmap (`[[feature_coverage_audit]]`)
**Status:** Design approved — proceeding to implementation plan.

## Summary

Add a single new mode `table` to ManimStudio: a **combined Tables & Matrices**
mode with an in-panel **Table / Matrix** toggle (`kind` param), in the spirit of
how parametric extended funcgraph via a `plot_kind` switch. One ActivityBar
button; two substantial code paths behind it.

- **Table half** — `Table` / `MathTable` with row/column labels, cell
  highlighting, outer lines, an optional title, and a LaTeX (math-cells) toggle.
- **Matrix half** — bracketed `Matrix` plus a **full operations suite**: static
  display with row/col/entry highlight, scalar multiply, matrix addition (second
  grid), transpose, and 2×2/3×3 determinant readout.

Manim's `Table` and `Matrix` are **distinct primitives with no shared
substrate** (a Table has grid lines + headers; a Matrix has brackets and is
built to be transformed). The combined mode is therefore "two builders behind
one button," not a shared base with variants.

## Scope decisions (locked during brainstorming)

| Decision | Choice |
|----------|--------|
| Mode structure | One combined `table` mode, in-panel Table/Matrix toggle |
| Code structure | **Approach B** — one mode / one panel / one `_BUILDERS` entry, but two internal builder helpers (`_build_table_kind` / `_build_matrix_kind`) + per-operation `_emit_*` helpers |
| Data input | CSV-style textarea (rows = lines, cells = `,` or `\|`), parsed safely (no `eval`) |
| Table features | Row & column labels, cell highlighting, math cells (LaTeX → `MathTable`), outer lines + title |
| Matrix depth | Full operations suite (static + scalar + add + transpose + determinant) |
| Size cap | ≤ 8 rows × 8 cols (silently truncate beyond) |
| PyQt6 (`panels.py`) | **No work** — all Tier-1 modes are React-only; `panels.py` has zero references to them |

## Architecture & file map

| File | Change |
|------|--------|
| `builders.py` | New `build_table_source(...)` dispatcher → `_build_table_kind` / `_build_matrix_kind`; shared CSV parser `_parse_grid`; matrix-op helpers `_emit_scalar_mul` / `_emit_matrix_add` / `_emit_transpose` / `_emit_determinant` |
| `api.py` | One line: `"table": builders.build_table_source` in `_BUILDERS` |
| `ui/src/types.ts` | Add `'table'` to the mode union + a `TableParams` interface |
| `ui/src/components/ActivityBar.tsx` | One entry: `{ mode: 'table', icon: '▦', label: 'Table' }` |
| `ui/src/components/panels/TablePanel.tsx` | New panel: kind toggle + conditional Table/Matrix controls |
| `ui/src/App.tsx` | `'table'` case in render switch + default-params block |
| `test_table.py` (new) | Builder unit tests (both kinds, all matrix ops, all guards) |
| `smoke_test_v2.py` | Add `table` to the mode roster (target ~35/35) |

Builders are invoked as `builder(**params)` (see `api._render_impl`), so the
`build_table_source` signature **is** the param contract.

## Param schema (`build_table_source`)

```python
def build_table_source(
    kind="table",            # "table" | "matrix"
    data="",                 # CSV grid: rows = lines, cells = "," or "|"
    title="", anim="Create", # intro anim: Create | Write | FadeIn
    cam_zoom=1.0,
    # ---- table-only ----
    row_labels="", col_labels="",      # comma-separated; "" = none
    use_latex=False,                   # True -> MathTable (LaTeX cells)
    include_outer_lines=True,
    highlights=None,                   # [{row, col, color}, ...] cell highlights
    # ---- matrix-only ----
    bracket="[]",                      # "[]" | "()" | "{}"
    operation="none",                  # none | scalar | add | transpose | determinant
    scalar=2.0,                        # used when operation == "scalar"
    data2="",                          # second grid, when operation == "add"
    mhighlight=None,                   # static row/col/entry highlight {target, index, color}
):
```

`data`/`data2` parse via shared `_parse_grid()` → `list[list[str]]`: split rows
on newlines, cells on `,`/`|`, strip whitespace, pad ragged rows to the widest
column, truncate to ≤ 8×8. Table cells stay strings; matrix cells are
numeric-validated per operation.

## Table half — `_build_table_kind`

1. `_parse_grid(data)` → string grid (empty → built-in 2×2 sample).
2. `MathTable(grid, ...)` if `use_latex` else `Table(grid, ...)`.
   `row_labels` / `col_labels` (when non-empty, comma-split) → `[Text(l) ...]`
   (or `[MathTex(l) ...]` in LaTeX mode); `include_outer_lines` passed through.
3. **Highlights:** each `{row, col, color}` → `t.add_highlighted_cell((row, col), color=...)`.
4. **Title:** if set, `Text(title).next_to(table, UP)`, grouped with the table.
5. **Fit:** `VGroup(...).scale(...)` clamped so an 8×8 table still fits frame,
   then apply `cam_zoom`.
6. **Intro:** `anim` → `Create` / `Write` / `FadeIn` on the group.

**Indexing note (pinned by a test):** Manim `Table` cell coordinates are
**1-based and label-aware** — adding `row_labels`/`col_labels` makes the label
row/column occupy index 1, so data-cell (1,1) becomes (2,2). The panel states
"coordinates are 1-based, counting the label row/column."

## Matrix half — `_build_matrix_kind`

Build `Matrix(grid, left_bracket, right_bracket)` — bracket map: `[]`→`[ ]`,
`()`→`( )`, `{}`→`\{ \}`. Then dispatch on `operation`:

| `operation` | Helper | Behavior | Guard |
|-------------|--------|----------|-------|
| `none` | — | Display; optional `mhighlight` of a row/col/entry via `get_rows()[i]` / `get_columns()[j]` / `get_entries()[k]` → `Indicate` / `SurroundingRectangle` | — |
| `scalar` | `_emit_scalar_mul` | Show `k·A`, build result (each entry ×`k`), `Transform(A → result)` | entries numeric |
| `add` | `_emit_matrix_add` | Parse `data2`→B, show `A + B`, animate → `C = A+B` | numeric **and** same shape |
| `transpose` | `_emit_transpose` | Build `Aᵀ` (swap rows/cols), `Transform(A → Aᵀ)` | none (string swap) |
| `determinant` | `_emit_determinant` | Compute det in Python, show `\det(A) = value` below | numeric **and** square 2×2/3×3 |

The matrix half always emits LaTeX (`Matrix` renders entries as `MathTex`), so it
is gated automatically by the existing `_source_needs_latex` preflight in
`api.py`.

## Error handling & guards

- **Empty `data` → built-in 2×2 sample grid** so a freshly-opened mode renders
  immediately (mirrors polar's `if not clean: clean = [default]`).
- ≤ 8×8 size cap (silently truncate).
- Out-of-range highlight coords → skip, never crash.
- Failed numeric / same-shape / square guards `raise ValueError("<human-readable>")`;
  `api._render_impl` already wraps builder exceptions as
  `{"ok": False, "error": "Build error: ..."}` → shown in the UI error banner.
- Matrix LaTeX dependency handled by the existing preflight (no new code).

## React panel — `TablePanel.tsx`

Reuses shared `Dropdown` / `NumInput` / `Knob` / `TextControls`; conditional
rendering keyed on `kind` and `operation`:

- **Top:** segmented **Table | Matrix** toggle (`kind`).
- **Shared:** `data` textarea (CSV, format placeholder), `title`, `anim`
  dropdown, `cam_zoom` knob.
- **Table-only:** `row_labels` / `col_labels` inputs, `use_latex` toggle,
  `include_outer_lines` toggle, **highlights editor** (add/remove rows of
  `{row, col, color}`, modeled on polar's points editor).
- **Matrix-only:** `bracket` dropdown, `operation` dropdown, then conditional —
  `scalar` `NumInput` (op=scalar), `data2` textarea (op=add), `mhighlight`
  target/index/color (op=none).

`App.tsx`: add a `'table'` case to the render switch and a default-params block.

## Testing plan

- **`test_table.py`** (mirrors `test_polar.py` / `test_calculus.py` — assert on
  generated source + `compile()` validity):
  - *Table:* emits `Table(` / `MathTable(` per `use_latex`; row/col labels;
    `include_outer_lines`; `add_highlighted_cell` with label-shifted coords;
    title present.
  - *Matrix:* `Matrix(` with correct brackets; scalar → result + `Transform`;
    add matching dims; **add dim-mismatch raises**; transpose swaps dims;
    **determinant 2×2 & 3×3 values correct**, **non-square raises**,
    **non-numeric raises**.
  - *Guards:* empty-data fallback; 8×8 cap.
- **`smoke_test_v2.py`:** add `table` to the mode roster (target ~35/35).
- **Manual render-verify** (as prior sessions did): labelled + highlighted
  table, a `MathTable`, a bracketed matrix, scalar-multiply, determinant readout.

## Out of scope (YAGNI / future)

- Matrix–matrix multiplication, inverse, eigen-decomposition, RREF.
- `MobjectTable` / `MobjectMatrix` (image/mobject cells).
- Per-cell font/color styling beyond highlights.
- Tables larger than 8×8.
- PyQt6 (`master`) parity.
