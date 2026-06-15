# Wrapped (multi-line) cells + table bbox metadata — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add (1) wrapped multi-line table cells — a field's value wraps across lines as individual tokens — and (2) per-table-instance bounding-box metadata on the Sample contract.

**Architecture:** Both stay on the established seam (a spec knob + a layout-stage change; renderer untouched). Feature 1 extends the column model: `FieldSpec.max_width` caps a column so its value wraps to the *resolved* column width; layout emits each wrapped line as its own cell sub-rect (so `render.py`'s existing cell-grouping draws it unchanged); row height is content-aware with worst-case capacity reservation. Feature 2 adds a `layout_with_regions()` wrapper that returns per-instance bboxes (the existing `layout()` delegates to it, so its ~40 call sites are untouched); `build.py` normalizes them onto `Sample.regions`.

**Tech Stack:** Python (src-layout `src/tablelab/`), `uv`, pytest, Pillow; Vite/React/TypeScript viewer.

**Spec:** `docs/specs/2026-06-14-wrapped-cells-table-bbox-design.md`

**Commands:** all Python steps run from `harness/`. Run a test: `uv run pytest tests/<file>::<name> -v`. Full suite: `uv run pytest -q`.

**Design invariants to preserve:**
- Off-path byte-identical: when no field sets `max_width`, the invoice golden (`tests/test_golden.py`) stays exact. Wrapping is gated on `max_width is not None`.
- `_line_h(dc)` (default `round(font_size * 1.4)` = 31px at font 22) must stay `< row_h` for default classes (invoice/eob `row_h=74`) so single-line rows keep height `row_h`.
- The eob showcase uses `max_lines=2`; `2 * 31 = 62 < 74`, so eob data rows do **not** grow — zero capacity/geometry change. Existing eob in-page tests (`test_capacity`, `test_globals`, `test_spanning`) guard this.

---

## Part A — Feature 1: Wrapped (multi-line) cells

### Task A1: Spec knobs (`FieldSpec.max_width`/`max_lines`, `LayoutSpec.line_h`)

**Files:**
- Modify: `harness/src/tablelab/specs.py:5-12` (FieldSpec), `:40-50` (LayoutSpec)
- Test: `harness/tests/test_wrap.py` (create)

- [ ] **Step 1: Write the failing test**

Create `harness/tests/test_wrap.py` (header imports only names that already exist; later tasks import their new helpers inline so the module always collects):

```python
import random

import pytest

from tablelab.specs import FieldSpec, LayoutSpec, TableSpec, DocumentClass
from tablelab.layout import layout, validate_layout_capacity, LayoutCapacityError


def test_fieldspec_has_wrap_knobs():
    f = FieldSpec("desc", "description", "left", max_width=200.0, max_lines=2)
    assert f.max_width == 200.0
    assert f.max_lines == 2


def test_fieldspec_wrap_knobs_default_off():
    f = FieldSpec("desc", "description", "left")
    assert f.max_width is None
    assert f.max_lines == 1


def test_layoutspec_line_h_defaults_none():
    assert LayoutSpec().line_h is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'max_width'` (and import errors for `_wrap`/`_line_h`, addressed in A3).

- [ ] **Step 3: Add the fields**

In `specs.py`, `FieldSpec` — add after the `group` field (currently line 12):

```python
    max_width: float | None = None  # cap on content-aware column width (px); wider values wrap. None = grow-to-fit
    max_lines: int = 1              # upper bound on wrapped lines; used for worst-case capacity reservation
```

In `specs.py`, `LayoutSpec` — add after `globals_per_row` (currently line 50):

```python
    line_h: int | None = None             # intra-cell wrapped-line height; None => round(font_size * 1.4)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py -v`
Expected: PASS (the three tests; the module collects cleanly because the header imports only existing names).

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/specs.py harness/tests/test_wrap.py
git commit -m "feat(specs): add FieldSpec.max_width/max_lines and LayoutSpec.line_h"
```

---

### Task A2: Long `service_desc` sampler (so wrapping triggers)

**Files:**
- Modify: `harness/src/tablelab/fields.py:78-104` (samplers + TYPE_WIDTH)
- Test: `harness/tests/test_wrap.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_wrap.py`:

```python
def test_service_desc_sampler_is_multiword():
    from tablelab.fields import sample
    rng = random.Random(0)
    vals = {sample("service_desc", rng) for _ in range(50)}
    assert vals  # non-empty vocab
    assert all(len(v.split()) >= 2 for v in vals)  # always multi-word so it can wrap
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py::test_service_desc_sampler_is_multiword -v`
Expected: FAIL — `KeyError: 'service_desc'`.

- [ ] **Step 3: Add the sampler**

In `fields.py`, after the `_category` block (after line 91, the `SAMPLERS["category"] = _category` line), add:

```python
# Verbose service-line descriptions (multi-word) for wrapped/multi-line cells. Sized to
# wrap to ~2 lines under the eob description column cap; keep individual words short so a
# single word never overflows the column (see wrapped-cells design).
_SERVICE_DESC = (
    "Office visit established patient",
    "Comprehensive metabolic blood panel",
    "Diagnostic chest radiograph series",
    "Physical therapy exercise session",
    "Preventive annual wellness exam",
    "Outpatient specialist consultation visit",
    "Complete blood count laboratory",
    "Influenza immunization administration",
)


def _service_desc(rng: random.Random) -> str:
    return rng.choice(_SERVICE_DESC)


SAMPLERS["service_desc"] = _service_desc
```

In `fields.py`, add a width default to `TYPE_WIDTH` (the dict starting line 95) — add inside it:

```python
    "service_desc": 4.0,
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py::test_service_desc_sampler_is_multiword -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/fields.py harness/tests/test_wrap.py
git commit -m "feat(fields): add multi-word service_desc sampler for wrapped cells"
```

---

### Task A3: `_wrap` + `_line_h` helpers

**Files:**
- Modify: `harness/src/tablelab/layout.py` (add helpers near the top-level helpers, after `_header_text` ~line 119)
- Test: `harness/tests/test_wrap.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_wrap.py` (imports the new helpers inline so the module still collects before A3 lands):

```python
def test_wrap_greedy_packs_words_no_drops():
    from tablelab.layout import _wrap
    words = "alpha beta gamma delta epsilon".split()
    lines = _wrap(words, col_width=70.0, font_size=22)
    assert all(isinstance(line, list) for line in lines)
    assert [w for line in lines for w in line] == words  # order preserved, nothing dropped
    assert len(lines) >= 2                                # narrow width forces wrapping


def test_wrap_single_oversized_word_keeps_own_line():
    from tablelab.layout import _wrap
    lines = _wrap(["supercalifragilisticexpialidocious"], col_width=10.0, font_size=22)
    assert lines == [["supercalifragilisticexpialidocious"]]


def test_line_h_defaults_to_font_scaled():
    from tablelab.layout import _line_h
    dc = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(FieldSpec("a", "amount", "right"),)),))
    assert _line_h(dc) == round(dc.render.font_size * 1.4)


def test_line_h_honors_explicit_override():
    from tablelab.layout import _line_h
    dc = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(FieldSpec("a", "amount", "right"),)),),
        layout=LayoutSpec(line_h=40))
    assert _line_h(dc) == 40
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py -k "wrap_greedy or oversized or line_h" -v`
Expected: FAIL — `ImportError: cannot import name '_wrap'`.

- [ ] **Step 3: Implement the helpers**

In `layout.py`, after `_header_text` (ends ~line 119), add:

```python
def _line_h(dc: DocumentClass) -> int:
    """Intra-cell wrapped-line height: explicit LayoutSpec.line_h, else font-scaled.
    Kept below the default row_h so a single-line row keeps height row_h."""
    L = dc.layout
    return L.line_h if L.line_h is not None else round(dc.render.font_size * 1.4)


def _wrap(words: list[str], col_width: float, font_size: int) -> list[list[str]]:
    """Greedy word-wrap: pack words into lines no wider than col_width px. A single word
    wider than col_width gets its own line (never split mid-word). Order is preserved."""
    lines: list[list[str]] = []
    cur: list[str] = []
    cur_w = 0.0
    space = text_width(" ", font_size)
    for w in words:
        ww = text_width(w, font_size)
        if not cur:
            cur, cur_w = [w], ww
        elif cur_w + space + ww <= col_width:
            cur.append(w)
            cur_w += space + ww
        else:
            lines.append(cur)
            cur, cur_w = [w], ww
    if cur:
        lines.append(cur)
    return lines
```

(`text_width` is already imported at `layout.py:6` via `from .metrics import text_width`.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py -v`
Expected: PASS (all A1/A2/A3 tests, including the three from A1 that previously hit the import error).

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_wrap.py
git commit -m "feat(layout): add _wrap word-wrapping + _line_h helpers"
```

---

### Task A4: Cap-aware column widths + autoscale

**Files:**
- Modify: `harness/src/tablelab/layout.py:44-66` (`_fit_font`), `:68-87` (`_content_column_widths`)
- Test: `harness/tests/test_wrap.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_wrap.py`:

```python
def _capped_class(max_width, page=(600, 400)):
    fields = (FieldSpec("desc", "service_desc", "left", max_width=max_width),
              FieldSpec("amt", "amount", "right"))
    return DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=fields, rows=(2, 2), instances=(1, 1)),),
        layout=LayoutSpec(page=page, margin=(20, 20)))


def test_capped_column_does_not_exceed_max_width():
    dc = _capped_class(max_width=120.0)
    placed = layout(dc, random.Random(0))
    desc_w = {round(p.cell[2] - p.cell[0], 1)
              for p in placed if p.label and p.label.get("field") == 0 and "record" in p.label}
    assert desc_w  # has description tokens
    assert max(desc_w) <= 120.0 + 0.5  # frozen at the cap


def test_uncapped_columns_still_fill_page():
    dc = _capped_class(max_width=120.0)
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    placed = layout(dc, random.Random(0))
    x1s = [p.cell[2] for p in placed if p.label and "field" in p.label]
    assert abs(max(x1s) - (W - mx)) < 1e-6  # table still spans to the right margin
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py -k "capped_column or uncapped_columns" -v`
Expected: FAIL — the description column is currently sized to its full (unwrapped) content width, exceeding 120.

- [ ] **Step 3: Implement cap awareness**

Replace `_content_column_widths` (`layout.py:68-87`) body with:

```python
def _content_column_widths(fields, usable: float, pad: int, header: bool,
                           grid: list[list[str]], font_size: int) -> list[float]:
    """Content floor + weighted slack. Each column is at least wide enough for the
    widest of its header label and sampled values (plus padding); a field with
    max_width is frozen at min(content_floor, max_width) and excluded from slack, so
    its value wraps. Leftover usable width is shared across the remaining columns by
    weight, so the table still fills the page."""
    mins = []
    capped: set[int] = set()
    for c, f in enumerate(fields):
        texts = [row[c] for row in grid]
        if header:
            texts.append(_header_text(f.name))
        longest = max((text_width(t, font_size) for t in texts), default=0.0)
        floor = longest + 2 * pad
        if f.max_width is not None:
            floor = min(floor, float(f.max_width))
            capped.add(c)
        mins.append(floor)
    total_min = sum(mins)
    if total_min >= usable:
        scale = usable / total_min if total_min > 0 else 1.0
        return [m * scale for m in mins]
    slack = usable - total_min
    weights = [0.0 if c in capped else field_weight(f) for c, f in enumerate(fields)]
    wtotal = sum(weights)
    if wtotal <= 0:  # every column capped: fall back to weighting all so the table fills
        weights = [field_weight(f) for f in fields]
        wtotal = sum(weights) or 1.0
    return [mins[c] + slack * weights[c] / wtotal for c in range(len(fields))]
```

In `_fit_font` (`layout.py:44-66`), change the per-column accumulation. Replace the loop body (currently lines 51-55):

```python
    for c, f in enumerate(fields):
        texts = [row[c] for row in grid if row[c]]
        if header:
            texts.append(_header_text(f.name))
        if texts:
            longest = max(text_width(t, base_font) for t in texts)
            if f.max_width is not None:
                longest = min(longest, max(f.max_width - 2 * pad, 0.0))
            text_total += longest
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py -k "capped_column or uncapped_columns" -v`
Expected: PASS

- [ ] **Step 5: Confirm the invoice golden still holds**

Run: `uv run pytest tests/test_golden.py -v`
Expected: PASS (no field sets `max_width`, so `capped` is empty and the slack math is unchanged).

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_wrap.py
git commit -m "feat(layout): cap content-aware column width at FieldSpec.max_width"
```

---

### Task A5: Wrapping emission in the data-row loop

**Files:**
- Modify: `harness/src/tablelab/layout.py:523-542` (the `for r in range(rows)` block inside `layout`)
- Test: `harness/tests/test_wrap.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_wrap.py`:

```python
def test_wrapped_cell_emits_stacked_line_tokens():
    # A capped column whose value wraps emits one token per word, sharing the field label,
    # split across >=2 distinct vertical line positions.
    dc = _capped_class(max_width=110.0)
    found = False
    for seed in range(30):
        placed = layout(dc, random.Random(seed))
        desc = [p for p in placed if p.label and p.label.get("field") == 0 and "record" in p.label]
        ys = sorted({round(p.cell[1], 1) for p in desc})
        if len(ys) >= 2:                                  # this sample wrapped
            found = True
            assert all(p.label["field"] == 0 and "record" in p.label for p in desc)
            assert all("seq" in p.label for p in desc)    # individual word tokens carry order
            # words on the same line share one cell rect
            line0 = [p for p in desc if round(p.cell[1], 1) == ys[0]]
            assert len({p.cell for p in line0}) == 1
            break
    assert found, "expected at least one wrapped sample at max_width=110"


def test_wrapped_words_stay_within_their_column():
    from tablelab.render import render
    dc = _capped_class(max_width=110.0)
    for seed in range(10):
        placed = layout(dc, random.Random(seed))
        _img, boxes = render(placed, dc)
        for p, b in zip(placed, boxes):
            if p.label and p.label.get("field") == 0 and "record" in p.label:
                assert b[0] >= p.cell[0] - 1 and b[2] <= p.cell[2] + 1, (p.text, p.cell, b)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py -k "stacked_line or within_their_column" -v`
Expected: FAIL — wrapping is not emitted yet; the description is a single token per cell (one y position).

- [ ] **Step 3: Implement wrapping emission**

In `layout.py`, replace the entire data-row block (`layout.py:523-542`, the `for r in range(rows):` loop up to and including the `y += cell_h` / gap advance) with:

```python
            line_h = _line_h(dc)
            for r in range(rows):
                row_edges = (jitter_column_edges(edges, J.col_w, rng)
                             if J.col_w > 0 else edges)
                # Content-aware height: a wrappable cell that wraps to N lines grows the row.
                row_lines = 1
                for c in range(C):
                    f = table.fields[c]
                    v = grid[r][c]
                    if f.max_width is not None and v:
                        col_text_w = (row_edges[c + 1] - row_edges[c]) - 2 * L.pad
                        row_lines = max(row_lines, len(_wrap(v.split(), col_text_w, cell_font)))
                base_h = max(L.row_h, row_lines * line_h)
                cell_h = base_h
                gap_after = _row_gap(dc)
                if J.row_h > 0 and _row_gap(dc) > 0:
                    cell_h, delta = jitter_row_height(base_h, J.row_h, _row_gap(dc), rng)
                    gap_after = _row_gap(dc) + delta
                for c in range(C):
                    f = table.fields[c]
                    value = grid[r][c]
                    if not value:
                        continue  # sparse cell: leave it empty, emit no token
                    x0, x1 = row_edges[c], row_edges[c + 1]
                    if f.max_width is not None:
                        col_text_w = (x1 - x0) - 2 * L.pad
                        lines = _wrap(value.split(), col_text_w, cell_font)
                        block_h = len(lines) * line_h
                        top = y + (cell_h - block_h) / 2
                        seq = 0
                        for k, words in enumerate(lines):
                            ly0 = top + k * line_h
                            line_cell = (x0, ly0, x1, ly0 + line_h)
                            for w in words:
                                placed.append(PlacedToken(
                                    text=w, cell=line_cell,
                                    label={**reg, "record": r, "field": c, "seq": seq},
                                    align=f.align, font_size=cell_font))
                                seq += 1
                    else:
                        cell = (x0, y, x1, y + cell_h)
                        _emit(placed, value, cell,
                              {**reg, "record": r, "field": c}, f.align, cell_font, multi)
                y += cell_h
                if r < rows - 1:
                    y += gap_after
```

Note: the non-`max_width` branch is identical to the original (`cell = (x0, y, x1, y + cell_h)` with `cell_h == L.row_h` when nothing wraps), preserving the byte-identical off-path.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py -k "stacked_line or within_their_column" -v`
Expected: PASS

- [ ] **Step 5: Confirm golden still holds**

Run: `uv run pytest tests/test_golden.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_wrap.py
git commit -m "feat(layout): emit wrapped cells as stacked per-line tokens"
```

---

### Task A6: Worst-case capacity reservation

**Files:**
- Modify: `harness/src/tablelab/layout.py:311-321` (`_instance_height`); add `_data_row_h` helper just above it
- Test: `harness/tests/test_wrap.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_wrap.py`:

```python
def _short_page_wrap_class(max_lines):
    # row_h == line_h == 40, so a data row reserves max_lines * 40; a page tall enough for
    # 1-line rows but not max_lines rows must fail capacity validation up front.
    fields = (FieldSpec("desc", "service_desc", "left", max_width=200.0, max_lines=max_lines),)
    return DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=fields, rows=(2, 2), instances=(1, 1)),),
        layout=LayoutSpec(page=(400, 200), margin=(10, 10), row_h=40, line_h=40, table_gap=0))


def test_capacity_reserves_worst_case_lines():
    # 2 rows * (3 * 40) = 240 > available 180 -> capacity error.
    with pytest.raises(LayoutCapacityError):
        validate_layout_capacity(_short_page_wrap_class(max_lines=3))


def test_capacity_ok_for_single_line_reservation():
    # 2 rows * (1 * 40) = 80 < available 180 -> fits.
    validate_layout_capacity(_short_page_wrap_class(max_lines=1))
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py -k "reserves_worst_case or single_line_reservation" -v`
Expected: FAIL — `test_capacity_reserves_worst_case_lines` does not raise (data rows are still reserved at `row_h`, so `2*40=80 < 180`).

- [ ] **Step 3: Implement the reservation**

In `layout.py`, immediately above `_instance_height` (currently line 311), add:

```python
def _data_row_h(dc: DocumentClass, table: TableSpec | None) -> int:
    """Reserved height of one data row: row_h, grown to the worst-case wrapped height
    (max field max_lines * line_h) so capacity planning never underestimates."""
    if table is None:
        return dc.layout.row_h
    max_lines = max((f.max_lines for f in table.fields), default=1)
    return max(dc.layout.row_h, max_lines * _line_h(dc))
```

In `_instance_height` (`layout.py:311-321`), change the data-row term — replace `rows * L.row_h` with `rows * _data_row_h(dc, table)`. The function becomes:

```python
def _instance_height(dc: DocumentClass, rows: int, table: TableSpec | None = None) -> int:
    L = dc.layout
    header = int(dc.structure.header)
    banner = section = totals = 0
    if table is not None:
        banner = header * int(any(f.group for f in table.fields))
        section = int(table.section is not None)
        totals = int(table.totals is not None)
    fixed_rows = header + banner + section + totals
    return (fixed_rows * L.row_h + rows * _data_row_h(dc, table)
            + max(rows - 1, 0) * _row_gap(dc) + _instance_gap(dc))
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py -k "reserves_worst_case or single_line_reservation" -v`
Expected: PASS

- [ ] **Step 5: Confirm golden + full suite still green**

Run: `uv run pytest -q`
Expected: PASS. (Invoice: `max_lines=1`, `_data_row_h = max(74, 31) = 74` → unchanged. eob untouched until A7.)

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_wrap.py
git commit -m "feat(layout): reserve worst-case wrapped row height in capacity planning"
```

---

### Task A7: eob showcase — description wraps

**Files:**
- Modify: `harness/src/tablelab/classes.py:23-27` (`_f` helper), `:65-67` (eob `description` field)
- Test: `harness/tests/test_wrap.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_wrap.py`:

```python
def test_eob_description_wraps_within_max_lines():
    from tablelab import classes as classlib
    from tablelab.render import render
    dc = classlib.get("eob")
    desc_field = next(i for i, f in enumerate(dc.tables[0].fields) if f.name == "description")
    saw_wrap = False
    for seed in range(40):
        placed = layout(dc, random.Random(seed))
        # group description tokens by (region, record); each group's distinct line-tops <= max_lines
        groups: dict[tuple, set] = {}
        for p in placed:
            if p.label and p.label.get("field") == desc_field and "record" in p.label:
                key = (p.label.get("region"), p.label["record"])
                groups.setdefault(key, set()).add(round(p.cell[1], 1))
        for tops in groups.values():
            assert len(tops) <= dc.tables[0].fields[desc_field].max_lines
            if len(tops) >= 2:
                saw_wrap = True
        # every box stays in page
        _img, boxes = render(placed, dc)
        W, H = dc.layout.page
        for (x0, y0, x1, y1) in boxes:
            assert 0 <= x0 <= x1 <= W and 0 <= y0 <= y1 <= H
    assert saw_wrap, "expected the eob description to wrap on at least one seed"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wrap.py::test_eob_description_wraps_within_max_lines -v`
Expected: FAIL — eob `description` uses the short `description` sampler and no `max_width`, so it never wraps (`saw_wrap` stays False).

- [ ] **Step 3: Implement the eob recipe change**

In `classes.py`, extend the `_f` helper (lines 23-26) to pass the wrap knobs:

```python
def _f(name: str, type_: str, align: str, width: float | None = None,
       fill: float = 1.0, group: str | None = None,
       max_width: float | None = None, max_lines: int = 1) -> FieldSpec:
    return FieldSpec(name=name, type=type_, align=align, width=width, fill=fill,
                     group=group, max_width=max_width, max_lines=max_lines)
```

In `classes.py`, the eob `description` field (line 67) becomes:

```python
            _f("description", "service_desc", "left", max_width=260.0, max_lines=2),
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wrap.py::test_eob_description_wraps_within_max_lines -v`
Expected: PASS.

If `saw_wrap` is False: the longest phrase fits one line — lower `max_width` (e.g. 220). If an assertion `len(tops) <= max_lines` fails or a box leaves the page: a phrase wraps to 3 lines — raise `max_width` (e.g. 300) or shorten the offending `_SERVICE_DESC` entry in `fields.py`. Re-run.

- [ ] **Step 5: Run the eob-sensitive suites**

Run: `uv run pytest tests/test_spacing.py tests/test_capacity.py tests/test_globals.py tests/test_spanning.py -q`
Expected: PASS. (eob `max_lines=2`: `2*31=62 < 74`, so data-row height stays 74 — no capacity/geometry change. `_fit_font` cap keeps `test_autoscale_noop_when_content_already_fits` green; frozen-column slack keeps `test_eob_columns_are_non_uniform_but_fill_page` green; wrapping fits the column so the overflow tests stay green.)

If `test_autoscale_noop_when_content_already_fits` fails: the capped description still pushes total content over the wide-page budget — confirm the `_fit_font` cap from A4 is applied. If an eob overflow test fails: a wrapped word exceeds its column — shorten that `_SERVICE_DESC` entry.

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/classes.py harness/tests/test_wrap.py
git commit -m "feat(eob): description column wraps to two lines (service_desc + max_width)"
```

---

### Task A8: Full Feature-1 verification + smoke dataset

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS (all suites).

- [ ] **Step 2: Build a smoke dataset and eyeball wrapping**

Run:
```bash
uv run python -m tablelab.cli build --class eob --n 6 --out ../datasets/eob-wrapped --seed 3
uv run python -m tablelab.cli inspect eob-wrapped --datasets-dir ../datasets
```
Expected: build succeeds; `inspect` reports `class: eob` and a token count higher than a non-wrapped eob (descriptions now split into per-word tokens). Open `viewer` (after Part B) to confirm visually; for now confirm the build did not raise and images exist under `datasets/eob-wrapped/images/`.

- [ ] **Step 3: Remove the smoke dataset (gitignored, keep tree clean)**

```bash
rm -rf ../datasets/eob-wrapped
```

(No commit — datasets are gitignored.)

---

## Part B — Feature 2: Table bbox metadata

### Task B1: `PlacedRegion` + `layout_with_regions` wrapper

**Files:**
- Modify: `harness/src/tablelab/layout.py` (add `PlacedRegion` near `PlacedToken` ~line 106; rename `layout` body to `layout_with_regions`, add delegating `layout`)
- Test: `harness/tests/test_regions.py` (create)

- [ ] **Step 1: Write the failing test**

Create `harness/tests/test_regions.py`:

```python
import random

from tablelab import classes as classlib
from tablelab.layout import layout, layout_with_regions, PlacedRegion


def test_layout_with_regions_returns_tokens_and_region_list():
    dc = classlib.get("invoice")
    placed, regions = layout_with_regions(dc, random.Random(7))
    assert isinstance(placed, list) and placed
    assert isinstance(regions, list)                       # may be empty until B2 captures bboxes


def test_layout_delegates_and_matches_tokens():
    dc = classlib.get("eob")
    a = layout(dc, random.Random(7))
    b, _regions = layout_with_regions(dc, random.Random(7))
    assert [(p.text, p.cell, p.label) for p in a] == [(p.text, p.cell, p.label) for p in b]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_regions.py -v`
Expected: FAIL — `ImportError: cannot import name 'layout_with_regions'`.

- [ ] **Step 3: Add `PlacedRegion` and the wrapper**

In `layout.py`, after the `PlacedToken` dataclass (ends ~line 115), add:

```python
@dataclass
class PlacedRegion:
    region: int                                # matches the {"region": k} token label
    table: str                                 # table name (e.g. "claim_line")
    bbox: tuple[float, float, float, float]    # page px (x0, y0, x1, y1)
```

In `layout.py`, rename the existing `def layout(dc, rng) -> list[PlacedToken]:` (line 450) to:

```python
def layout_with_regions(dc: DocumentClass, rng: random.Random) -> tuple[list[PlacedToken], list[PlacedRegion]]:
```

Keep the existing docstring/body. At the very start of the body add a regions accumulator next to `placed`:

```python
    placed: list[PlacedToken] = []
    regions: list[PlacedRegion] = []
```

Change the final `return placed` (line 566) to:

```python
    return placed, regions
```

Then add the thin delegate immediately after the function:

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Tokens only (back-compat). Use layout_with_regions when per-instance bboxes are needed."""
    return layout_with_regions(dc, rng)[0]
```

(Region capture itself is Task B2 — for now `regions` is returned empty; B1's tests only assert `regions` is a list and that delegation preserves tokens.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_regions.py -v`
Expected: PASS (both B1 tests: an empty region list and identical tokens through the delegate).

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_regions.py
git commit -m "feat(layout): add layout_with_regions wrapper (layout delegates)"
```

---

### Task B2: Capture per-instance bbox

**Files:**
- Modify: `harness/src/tablelab/layout.py` (inside `layout_with_regions`, the `for rows in table_shape:` loop)
- Test: `harness/tests/test_regions.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_regions.py`:

```python
def test_region_bbox_encloses_instance_tokens():
    dc = classlib.get("eob")
    placed, regions = layout_with_regions(dc, random.Random(7))
    assert regions
    by_region: dict[int, list] = {}
    for p in placed:
        if p.label and "region" in p.label:
            by_region.setdefault(p.label["region"], []).append(p)
    assert by_region  # eob is multi-instance
    for reg in regions:
        toks = by_region.get(reg.region, [])
        if not toks:
            continue
        x0 = min(t.cell[0] for t in toks); y0 = min(t.cell[1] for t in toks)
        x1 = max(t.cell[2] for t in toks); y1 = max(t.cell[3] for t in toks)
        bx0, by0, bx1, by1 = reg.bbox
        assert bx0 <= x0 + 1 and by0 <= y0 + 1
        assert bx1 >= x1 - 1 and by1 >= y1 - 1


def test_single_instance_class_has_one_region():
    dc = classlib.get("invoice")
    _placed, regions = layout_with_regions(dc, random.Random(7))
    assert len(regions) == 1
    assert isinstance(regions[0], PlacedRegion)
    assert regions[0].table == "line_item"
    assert regions[0].region == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_regions.py -k "encloses_instance or single_instance" -v`
Expected: FAIL — `regions` is still empty (assert `regions` / `len(regions) == 1`).

- [ ] **Step 3: Capture the bbox**

In `layout_with_regions`, inside `for rows in table_shape:` (begins ~line 493), record the instance top before any emission and append the region after the totals row. Add `y_start = y` as the first statement inside the loop:

```python
        for rows in table_shape:
            y_start = y
            reg = {"region": region} if multi_region else {}
```

Then, after the totals block and before `y += _instance_gap(dc)` (currently lines 543-548), insert the region append. The tail of the loop becomes:

```python
            if table.totals is not None:
                _emit_span_row(placed, table.totals.cells, edges, y, L.row_h,
                               {**reg, "subtotal": True}, cell_font, multi, rng,
                               header_on_text=True)
                y += L.row_h
            regions.append(PlacedRegion(
                region=region, table=table.name,
                bbox=(edges[0], y_start, edges[-1], y)))
            y += _instance_gap(dc)
            region += 1
```

(`edges` is in scope — computed per `rows` earlier in the loop. `edges[0]` is the left margin, `edges[-1]` the right table edge.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_regions.py -v`
Expected: PASS (all B1 + B2 tests, including `_returns_tokens_and_regions`).

- [ ] **Step 5: Confirm golden + full suite green**

Run: `uv run pytest -q`
Expected: PASS (region capture does not touch tokens).

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_regions.py
git commit -m "feat(layout): capture per-instance table bbox as PlacedRegion"
```

---

### Task B3: `Region` contract + `Sample.regions` round-trip

**Files:**
- Modify: `harness/src/tablelab/artifacts.py:9-24` (Region + Sample), `:69-75` (`_sample_from_dict`)
- Test: `harness/tests/test_regions.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_regions.py`:

```python
def test_sample_regions_round_trip(tmp_path):
    from tablelab.artifacts import (Sample, Token, Region, DatasetManifest,
                                    write_dataset, read_dataset)
    sample = Sample(
        id=0,
        tokens=[Token(x0=0.1, y0=0.1, x1=0.2, y1=0.2, text="x", label={"region": 0})],
        width=100, height=100, image="/datasets/x/images/0.png",
        regions=[Region(region=0, table="claim_line", bbox=[0.05, 0.05, 0.9, 0.5])])
    manifest = DatasetManifest(dataset_id="x", generator_version=2, task="grid_record_field",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got[0].regions is not None
    assert isinstance(got[0].regions[0], Region)
    assert got[0].regions[0].table == "claim_line"
    assert got[0].regions[0].bbox == [0.05, 0.05, 0.9, 0.5]


def test_sample_regions_default_none():
    from tablelab.artifacts import Sample
    assert Sample(id=0, tokens=[]).regions is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_regions.py -k "round_trip or regions_default_none" -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'regions'`.

- [ ] **Step 3: Add the contract**

In `artifacts.py`, after the `Token` dataclass (ends line 14) add:

```python
@dataclass
class Region:
    region: int                         # matches the {"region": k} token label
    table: str                          # table name (e.g. "claim_line")
    bbox: list[float]                   # normalized [0,1] (x0, y0, x1, y1)
```

In `artifacts.py`, `Sample` (lines 17-24) — add the optional field after `height`:

```python
    regions: list[Region] | None = None   # per table-instance bbox; additive structural metadata
```

In `_sample_from_dict` (lines 73-75), parse regions:

```python
def _sample_from_dict(d: dict) -> Sample:
    raw = d.get("regions")
    regions = [Region(**r) for r in raw] if raw is not None else None
    return Sample(id=d["id"], tokens=[_token_from_dict(t) for t in d["tokens"]],
                  image=d.get("image"), width=d.get("width"), height=d.get("height"),
                  regions=regions)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_regions.py -k "round_trip or regions_default_none" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/artifacts.py harness/tests/test_regions.py
git commit -m "feat(contract): add Region + optional Sample.regions (round-trips)"
```

---

### Task B4: Wire regions through `build_dataset`

**Files:**
- Modify: `harness/src/tablelab/build.py:15-18` (imports), `:184-193` (per-sample loop)
- Test: `harness/tests/test_regions.py`

- [ ] **Step 1: Write the failing test**

Append to `harness/tests/test_regions.py`:

```python
def test_build_dataset_writes_normalized_regions(tmp_path):
    from tablelab.build import build_dataset
    from tablelab.artifacts import read_dataset, Region
    ds = build_dataset(tmp_path, "rg-eob", classlib.get("eob"), seed=7, n=2)
    _m, samples = read_dataset(ds)
    assert all(s.regions for s in samples)
    for s in samples:
        for r in s.regions:
            assert isinstance(r, Region)
            assert r.table == "claim_line"
            assert all(0.0 <= v <= 1.0 for v in r.bbox)
            assert r.bbox[0] < r.bbox[2] and r.bbox[1] < r.bbox[3]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_regions.py::test_build_dataset_writes_normalized_regions -v`
Expected: FAIL — samples have `regions is None` (build does not populate them yet).

- [ ] **Step 3: Wire it through**

In `build.py`, update the imports (lines 16-17):

```python
from .artifacts import Sample, Token, Region, DatasetManifest, write_dataset
from .layout import layout_with_regions, validate_layout_capacity
```

In `build.py`, the per-sample loop (lines 184-193) — call the wrapper and attach normalized regions:

```python
            for i in tqdm(range(n), desc=dataset_id):
                placed, placed_regions = layout_with_regions(doc_class, rng)
                img, boxes = render(placed, doc_class)
                _validate_boxes(boxes, placed, dataset_id, i, W, H)
                img.save(staging_dir / "images" / f"{i}.png")
                tokens = [Token(x0=round(b[0] / W, 4), y0=round(b[1] / H, 4),
                                x1=round(b[2] / W, 4), y1=round(b[3] / H, 4),
                                text=p.text, label=p.label)
                          for p, b in zip(placed, boxes)]
                regions = [Region(region=r.region, table=r.table,
                                  bbox=[round(r.bbox[0] / W, 4), round(r.bbox[1] / H, 4),
                                        round(r.bbox[2] / W, 4), round(r.bbox[3] / H, 4)])
                           for r in placed_regions]
                samples.append(Sample(id=i, tokens=tokens, width=W, height=H,
                                      image=f"/datasets/{dataset_id}/images/{i}.png",
                                      regions=regions))
```

(`layout` is no longer imported in build.py — confirm no other reference to bare `layout(` remains in the file.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_regions.py::test_build_dataset_writes_normalized_regions -v`
Expected: PASS

- [ ] **Step 5: Confirm the full suite (incl. build-path tests in test_capacity/test_globals)**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/build.py harness/tests/test_regions.py
git commit -m "feat(build): write normalized per-instance regions onto samples"
```

---

### Task B5: Viewer — region type + overlay

**Files:**
- Modify: `viewer/src/types.ts:19-25` (Sample) — add `Region` + `regions?`
- Modify: `viewer/src/DocumentViewer.tsx:281` (destructure), `:372-373` (SVG overlay)
- Verify: `npm --prefix viewer run build`

- [ ] **Step 1: Add the Region type**

In `viewer/src/types.ts`, after the `Token` interface (line 17) add:

```typescript
export interface Region {
  region: number
  table: string
  bbox: [number, number, number, number]   // normalized [0,1] (x0, y0, x1, y1)
}
```

In `viewer/src/types.ts`, the `Sample` interface (lines 19-25) — add:

```typescript
  regions?: Region[]
```

- [ ] **Step 2: Draw region outlines in the overlay**

In `viewer/src/DocumentViewer.tsx`, where the sample is destructured (line 281):

```typescript
  const { tokens, image } = sample
  const regions = sample.regions ?? []
```

In the SVG (`<svg className="doc-overlay" …>`), immediately before `{tokens.map(...)}` (line 373), add the region rects (non-interactive, dashed, drawn behind tokens):

```tsx
            {regions.map((rg, i) => (
              <rect
                key={`region-${i}`}
                x={rg.bbox[0] * width}
                y={rg.bbox[1] * height}
                width={(rg.bbox[2] - rg.bbox[0]) * width}
                height={(rg.bbox[3] - rg.bbox[1]) * height}
                fill="none"
                stroke="#9333EA"
                strokeWidth={2}
                strokeDasharray="8 6"
                rx={4}
                pointerEvents="none"
              />
            ))}
```

- [ ] **Step 3: Typecheck + build the viewer**

Run: `npm --prefix viewer run build`
Expected: build succeeds (TypeScript compiles; `regions` is optional so existing data without it is fine).

- [ ] **Step 4: Commit**

```bash
git add viewer/src/types.ts viewer/src/DocumentViewer.tsx
git commit -m "feat(viewer): draw per-instance table region outlines from sample.regions"
```

---

### Task B6: End-to-end verification + viewer eyeball

**Files:** none (verification only)

- [ ] **Step 1: Full Python suite**

Run (from `harness/`): `uv run pytest -q`
Expected: PASS (all suites, including `test_golden`, `test_wrap`, `test_regions`).

- [ ] **Step 2: Build a combined showcase dataset**

Run:
```bash
uv run python -m tablelab.cli build --class eob --n 8 --out ../datasets/eob-wrapped-regions --seed 5
uv run python -m tablelab.cli inspect eob-wrapped-regions --datasets-dir ../datasets
```
Expected: build succeeds; `inspect` shows `class: eob`.

- [ ] **Step 3: Eyeball in the viewer**

Run: `npm --prefix viewer install` (if needed) then `npm --prefix viewer run dev` → open http://localhost:5173, select `eob-wrapped-regions`.
Expected: each claim instance is enclosed by a dashed purple region outline; some description cells render across two lines; clicking a wrapped word shows `{region, record, field, seq}` in the token detail panel; every box sits inside the page.

- [ ] **Step 4: Clean up the showcase dataset (gitignored)**

```bash
rm -rf ../datasets/eob-wrapped-regions
```

(Stop the dev server.)

---

## Part C — Docs

### Task C1: Mark the spec shipped + roadmap note

**Files:**
- Modify: `docs/specs/2026-06-14-wrapped-cells-table-bbox-design.md:3` (status), `docs/specs/2026-06-13-design-and-roadmap.md` (current-state note)

- [ ] **Step 1: Flip the spec status**

In `docs/specs/2026-06-14-wrapped-cells-table-bbox-design.md`, change the Status line from `**proposed**` to `**shipped** (merged to master). Plan: docs/plans/2026-06-14-wrapped-cells-table-bbox.md`.

- [ ] **Step 2: Add a current-state line to the roadmap**

In `docs/specs/2026-06-13-design-and-roadmap.md`, under "Current state (done)", add a bullet:

```markdown
- **Wrapped cells + table bbox**: `FieldSpec.max_width`/`max_lines` wrap a cell's value to
  multiple per-word line-tokens (renderer untouched; content-aware row height with worst-case
  capacity reservation); `Sample.regions` records each table-instance bbox (additive to contract
  v2). The eob `description` column wraps to two lines. See
  `2026-06-14-wrapped-cells-table-bbox-design.md`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/specs/2026-06-14-wrapped-cells-table-bbox-design.md docs/specs/2026-06-13-design-and-roadmap.md
git commit -m "docs: mark wrapped cells + table bbox shipped"
```

---

## Self-review notes (for the executor)

- **Off-path byte-identical** is guarded at three points: A4 step 5, A5 step 5, A6 step 5 all re-run `test_golden.py`. If any fails, the most recent change leaked into the no-`max_width` path.
- **eob stability** rests on `max_lines=2` keeping `2*line_h (62) < row_h (74)`. If you change `line_h` or the eob `row_h`, re-check `test_capacity.py` / `test_globals.py`.
- **Tuning knobs** if A7 wrapping misbehaves: `max_width` (260) and the `_SERVICE_DESC` phrase lengths. Existing 200/1000-seed in-page tests in `test_capacity.py`/`test_globals.py` are the safety net for vertical overflow.
- **No new CLI knobs** (per spec): wrapping is class-defined content, regions are always-on metadata.
