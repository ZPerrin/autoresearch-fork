# Synthetic Reviewability: Generator Validity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate class-coherent synthetic documents whose requested structure and background content fit entirely within the fixed page.

**Architecture:** Add class-level background vocabularies to the declarative spec, then make layout choose only feasible instance/row combinations before emitting tokens. Background tokens use reserved grid slots below structured content. Build validates rendered boxes before serialization. The legacy single-table/no-background path remains byte-identical.

**Tech Stack:** Python 3.10+, dataclasses, itertools, Pillow, pytest, uv.

**Repo convention:** This repo explicitly uses implement-then-verify rather than TDD. Add each focused behavior and immediately run its targeted tests. Run commands from `harness/` unless stated otherwise.

---

## File structure

| File | Change |
|---|---|
| `harness/src/tablelab/specs.py` | Add class-level background vocabulary to `DocumentClass`. |
| `harness/src/tablelab/classes.py` | Declare coherent invoice, receipt, and EOB vocabularies. |
| `harness/src/tablelab/fields.py` | Sample background text from the active class vocabulary plus neutral numeric references. |
| `harness/src/tablelab/layout.py` | Add capacity errors, feasible shape selection, and reserved background slots. |
| `harness/src/tablelab/build.py` | Preflight capacity and reject out-of-page rendered boxes. |
| `harness/tests/test_background.py` | Verify class vocabulary and non-overlapping reserved placement. |
| `harness/tests/test_capacity.py` | Verify feasible sampling, clear impossible failures, and page bounds. |
| `harness/tests/test_golden.py` | Continue guarding the byte-identical legacy path unchanged. |

---

### Task 1: Class-aware background vocabulary

**Files:**
- Modify: `harness/src/tablelab/specs.py`
- Modify: `harness/src/tablelab/classes.py`
- Modify: `harness/src/tablelab/fields.py`
- Modify: `harness/tests/test_background.py`

- [ ] **Step 1: Add vocabulary to the document-class contract**

Add a default-empty field after `globals` in `DocumentClass`:

```python
@dataclass(frozen=True)
class DocumentClass:
    name: str
    tables: tuple[TableSpec, ...]
    globals: tuple[FieldSpec, ...] = ()
    background_terms: tuple[str, ...] = ()
    layout: LayoutSpec = LayoutSpec()
    structure: StructureSpec = StructureSpec()
    render: RenderSpec = RenderSpec()
```

Default-empty preserves construction compatibility and records the resolved vocabulary in new
manifests through the existing `asdict(doc_class)` call.

- [ ] **Step 2: Replace the global cross-class background pool**

In `fields.py`, replace `_BACKGROUND` and `background_token` with:

```python
_NEUTRAL_BACKGROUND = (
    "Page", "Reference", "Notice", "Confidential", "Original", "Copy",
)


def background_token(terms: tuple[str, ...], rng: random.Random) -> str:
    """Sample non-answer page furniture from the active document class."""
    if rng.random() < 0.3:
        return str(rng.randint(1000, 99999))
    pool = terms or _NEUTRAL_BACKGROUND
    return rng.choice(pool)
```

Do not merge every class vocabulary with a generic invoice-oriented pool. Classes can repeat
neutral terms explicitly where desired.

- [ ] **Step 3: Declare vocabularies on built-in classes**

Add these tuples near the top of `classes.py`:

```python
_INVOICE_BACKGROUND = (
    "Invoice", "Account", "Customer", "Subtotal", "Total", "Balance",
    "Payment Terms", "Remit To", "Page", "Reference",
)

_EOB_BACKGROUND = (
    "Explanation of Benefits", "Patient Responsibility", "Plan Paid",
    "Claim Reference", "Benefit Notice", "This Is Not a Bill",
    "Member Services", "Page", "Reference",
)

_RECEIPT_BACKGROUND = (
    "Receipt", "Paid", "Subtotal", "Total", "Payment", "Thank You",
    "Store Copy", "Page", "Reference",
)
```

Pass the matching tuple into each `DocumentClass`. Keep table/global definitions unchanged.

- [ ] **Step 4: Update the layout call site temporarily**

Change the existing call in `layout.py` from:

```python
text=background_token(rng)
```

to:

```python
text=background_token(dc.background_terms, rng)
```

Reserved placement replaces the rest of this block in Task 3.

- [ ] **Step 5: Add vocabulary behavior tests**

Append to `test_background.py`:

```python
def test_eob_background_is_class_coherent():
    dc = classlib.get("eob")
    rng = random.Random(7)
    words = {background_token(dc.background_terms, rng) for _ in range(200)}
    words = {word for word in words if not word.isdigit()}
    assert words <= set(dc.background_terms)
    assert not words & {"INVOICE", "Invoice", "RECEIPT", "Receipt"}


def test_background_vocabularies_are_distinct():
    invoice = set(classlib.get("invoice").background_terms)
    eob = set(classlib.get("eob").background_terms)
    receipt = set(classlib.get("receipt").background_terms)
    assert "Explanation of Benefits" in eob
    assert "Invoice" in invoice
    assert "Receipt" in receipt
    assert "Receipt" not in eob
```

Add `from tablelab.fields import background_token` to the test imports. Sampling directly keeps this
test focused on vocabulary; layout composition is covered after capacity planning lands.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_background.py tests/test_golden.py
```

Expected: all selected tests pass and the golden fixture remains unchanged.

Commit:

```powershell
git add src/tablelab/specs.py src/tablelab/classes.py src/tablelab/fields.py src/tablelab/layout.py tests/test_background.py
git commit -m "feat: make background vocabulary document-class aware"
```

---

### Task 2: Capacity model and feasible shape selection

**Files:**
- Modify: `harness/src/tablelab/layout.py`
- Create: `harness/tests/test_capacity.py`

- [ ] **Step 1: Add the capacity error and shape type**

At the top of `layout.py`, import `itertools.product` and add:

```python
from itertools import product


class LayoutCapacityError(ValueError):
    """The minimum requested document structure cannot fit on the page."""


Shape = tuple[tuple[int, ...], ...]
```

`Shape` is parallel to `dc.tables`; each inner tuple contains the row count for each emitted
instance of that table.

- [ ] **Step 2: Add deterministic height helpers**

Add below `_emit`:

```python
_BACKGROUND_COLUMNS = 2


def _background_rows(count: int) -> int:
    return (count + _BACKGROUND_COLUMNS - 1) // _BACKGROUND_COLUMNS


def _fixed_height(dc: DocumentClass) -> int:
    L = dc.layout
    globals_h = len(dc.globals) * L.row_h + (L.table_gap if dc.globals else 0)
    background_h = _background_rows(dc.structure.background) * L.row_h
    return globals_h + background_h


def _shape_height(dc: DocumentClass, shape: Shape) -> int:
    L = dc.layout
    header_rows = 1 if dc.structure.header else 0
    return sum(
        (header_rows + rows) * L.row_h + L.table_gap
        for table_shape in shape
        for rows in table_shape
    )


def _available_height(dc: DocumentClass) -> int:
    return dc.layout.page[1] - 2 * dc.layout.margin[1]
```

The existing layout intentionally includes `table_gap` after every instance. Preserve that
geometry so this milestone does not silently rewrite table spacing.

- [ ] **Step 3: Enumerate feasible shapes only on composed paths**

Add:

```python
def _is_byte_identical_legacy_path(dc: DocumentClass) -> bool:
    if not (
        len(dc.tables) == 1
        and not dc.globals
        and not dc.structure.header
        and dc.structure.background == 0
        and dc.tables[0].instances == (1, 1)
    ):
        return False
    table = dc.tables[0]
    maximum = ((table.rows[1],),)
    return _shape_height(dc, maximum) <= _available_height(dc)


def _all_shapes(dc: DocumentClass):
    instance_choices = [range(t.instances[0], t.instances[1] + 1) for t in dc.tables]
    for counts in product(*instance_choices):
        row_ranges = [
            range(table.rows[0], table.rows[1] + 1)
            for table, count in zip(dc.tables, counts)
            for _ in range(count)
        ]
        for flat_rows in product(*row_ranges):
            offset = 0
            shape = []
            for count in counts:
                shape.append(tuple(flat_rows[offset:offset + count]))
                offset += count
            yield tuple(shape)


def _capacity_message(dc: DocumentClass) -> str:
    tables = ", ".join(
        f"{t.name}: instances>={t.instances[0]}, rows>={t.rows[0]}"
        for t in dc.tables
    )
    return (
        f"minimum structure does not fit page {dc.layout.page}: "
        f"available={_available_height(dc)}px, fixed={_fixed_height(dc)}px, "
        f"globals={len(dc.globals)}, header={dc.structure.header}, "
        f"background={dc.structure.background}, tables=[{tables}]"
    )


def feasible_shapes(dc: DocumentClass) -> list[Shape]:
    available = _available_height(dc)
    fixed = _fixed_height(dc)
    return [shape for shape in _all_shapes(dc) if fixed + _shape_height(dc, shape) <= available]


def validate_layout_capacity(dc: DocumentClass) -> None:
    if _is_byte_identical_legacy_path(dc):
        return
    if not feasible_shapes(dc):
        raise LayoutCapacityError(_capacity_message(dc))


def _choose_shape(dc: DocumentClass, rng: random.Random) -> Shape:
    if _is_byte_identical_legacy_path(dc):
        table = dc.tables[0]
        return ((rng.randint(table.rows[0], table.rows[1]),),)
    shapes = feasible_shapes(dc)
    if not shapes:
        raise LayoutCapacityError(_capacity_message(dc))
    return rng.choice(shapes)
```

The legacy predicate requires the maximum row count to fit, so it can preserve the historical
`randint` without ever selecting an overflowing shape. Other configurations use feasible-shape
selection.

- [ ] **Step 4: Make `layout()` consume the chosen shape**

At the beginning of `layout()`, after local spec aliases, call:

```python
shape = _choose_shape(dc, rng)
```

Replace per-table instance and row sampling with:

```python
for table, table_shape in zip(dc.tables, shape):
    C = len(table.fields)
    cell_w = (W - 2 * mx) / C
    for rows in table_shape:
        reg = {"region": region} if multi_region else {}
        if header:
            for c in range(C):
                f = table.fields[c]
                x0 = mx + c * cell_w
                cell = (x0, y, x0 + cell_w, y + L.row_h)
                _emit(placed, _header_text(f.name), cell,
                      {**reg, "field": c, "header": True},
                      f.align, dc.render.font_size, multi)
            y += L.row_h
        for r in range(rows):
            for c in range(C):
                f = table.fields[c]
                value = sample(f.type, rng)
                x0 = mx + c * cell_w
                cell = (x0, y, x0 + cell_w, y + L.row_h)
                _emit(placed, value, cell,
                      {**reg, "record": r, "field": c},
                      f.align, dc.render.font_size, multi)
            y += L.row_h
        y += L.table_gap
        region += 1
```

Remove `lo`, `hi`, `instances`, and the inner `rng.randint(table.rows...)` calls. Keep cell-value
sampling and final `rng.shuffle(placed)` unchanged.

- [ ] **Step 5: Add capacity tests**

Create `tests/test_capacity.py`:

```python
from __future__ import annotations

import random
from dataclasses import replace

import pytest

from tablelab import classes as classlib
from tablelab.layout import LayoutCapacityError, layout, validate_layout_capacity
from tablelab.specs import fork


def _full_eob(**layout_overrides):
    dc = classlib.get("eob")
    tables = tuple(replace(t, instances=(1, 3)) for t in dc.tables)
    structure = replace(dc.structure, header=True, multi_token=True, background=4)
    layout_spec = replace(dc.layout, **layout_overrides)
    return fork(dc, tables=tables, structure=structure, layout=layout_spec)


def test_full_eob_samples_only_page_valid_shapes():
    dc = _full_eob()
    for seed in range(200):
        placed = layout(dc, random.Random(seed))
        assert placed
        assert all(0 <= p.cell[0] <= p.cell[2] <= dc.layout.page[0] for p in placed)
        assert all(0 <= p.cell[1] <= p.cell[3] <= dc.layout.page[1] for p in placed)


def test_full_eob_keeps_declared_instance_range():
    dc = _full_eob()
    seen = set()
    for seed in range(200):
        placed = layout(dc, random.Random(seed))
        regions = {p.label["region"] for p in placed if p.label and "region" in p.label}
        seen.add(len(regions))
    assert seen <= {1, 2, 3}
    assert seen >= {1, 2}


def test_impossible_minimum_fails_clearly():
    dc = _full_eob(page=(1000, 500))
    with pytest.raises(LayoutCapacityError, match="minimum structure does not fit"):
        validate_layout_capacity(dc)


def test_legacy_invoice_still_fits_without_composed_planning():
    validate_layout_capacity(classlib.get("invoice"))
```

Do not require all feasible instance counts to appear; capacity may legitimately exclude three
instances for some row combinations. The critical assertions are range preservation and page fit.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_capacity.py tests/test_multi_table.py tests/test_globals.py tests/test_golden.py
```

Expected: all selected tests pass; the golden file is unchanged.

Commit:

```powershell
git add src/tablelab/layout.py tests/test_capacity.py
git commit -m "feat: sample only page-feasible document shapes"
```

---

### Task 3: Reserved, non-overlapping background slots

**Files:**
- Modify: `harness/src/tablelab/layout.py`
- Modify: `harness/tests/test_background.py`
- Modify: `harness/tests/test_capacity.py`

- [ ] **Step 1: Replace random scatter with a reserved two-column grid**

Replace the current background block at the end of `layout()` with:

```python
n_bg = dc.structure.background
if n_bg:
    columns = min(_BACKGROUND_COLUMNS, n_bg)
    slot_w = (W - 2 * mx) / columns
    for i in range(n_bg):
        row, col = divmod(i, columns)
        x0 = mx + col * slot_w
        cell = (x0, y + row * L.row_h, x0 + slot_w, y + (row + 1) * L.row_h)
        placed.append(PlacedToken(
            text=background_token(dc.background_terms, rng),
            cell=cell,
            label=None,
            align="left",
            font_size=dc.render.font_size,
        ))
```

Capacity planning already reserves `_background_rows(n_bg) * row_h` after the final table gap.
There is no random coordinate fallback.

- [ ] **Step 2: Strengthen placement tests**

In `test_background.py`, retain the existing below-table assertion and add:

```python
def _overlaps(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def test_background_slots_do_not_overlap_structure_or_each_other():
    dc = _invoice(background=8, header=True)
    placed = layout(dc, random.Random(7))
    bg = [p for p in placed if p.label is None]
    structured = [p for p in placed if p.label is not None]
    assert all(not _overlaps(a.cell, b.cell) for a in bg for b in structured)
    assert all(
        not _overlaps(bg[i].cell, bg[j].cell)
        for i in range(len(bg)) for j in range(i + 1, len(bg))
    )
```

Touching edges are not overlap.

- [ ] **Step 3: Verify full composition across many seeds**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_background.py tests/test_capacity.py
uv run python -c "import random; from dataclasses import replace; from tablelab import classes; from tablelab.specs import fork; from tablelab.layout import layout; dc=classes.get('eob'); dc=fork(dc,tables=tuple(replace(t,instances=(1,3)) for t in dc.tables),structure=replace(dc.structure,header=True,multi_token=True,background=4)); print(max(max(p.cell[3] for p in layout(dc,random.Random(s))) for s in range(1000)), dc.layout.page[1])"
```

Expected: tests pass and printed maximum is `<= 1414`.

- [ ] **Step 4: Commit**

```powershell
git add src/tablelab/layout.py tests/test_background.py tests/test_capacity.py
git commit -m "feat: reserve non-overlapping background slots"
```

---

### Task 4: Preflight and rendered-box invariant

**Files:**
- Modify: `harness/src/tablelab/build.py`
- Modify: `harness/tests/test_capacity.py`

- [ ] **Step 1: Preflight before creating output directories**

Import `validate_layout_capacity` and call it before `ds_dir` or `images/` is created:

```python
from .layout import layout, validate_layout_capacity


def build_dataset(datasets_dir: Path | str, dataset_id: str, doc_class: DocumentClass,
                  seed: int = 7, n: int = 12) -> Path:
    validate_layout_capacity(doc_class)
    rng = random.Random(seed)
    W, H = doc_class.layout.page
    ds_dir = Path(datasets_dir) / dataset_id
    (ds_dir / "images").mkdir(parents=True, exist_ok=True)
    samples: list[Sample] = []
```

- [ ] **Step 2: Validate glyph boxes before saving each image**

Add:

```python
def _validate_boxes(boxes, width: int, height: int) -> None:
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        if not (0 <= x0 <= x1 <= width and 0 <= y0 <= y1 <= height):
            raise ValueError(
                f"rendered token {i} outside page {width}x{height}: "
                f"{(x0, y0, x1, y1)}"
            )
```

Call `_validate_boxes(boxes, W, H)` immediately after `render(...)` and before `img.save(...)`.

- [ ] **Step 3: Test that impossible builds leave no dataset directory**

Append to `test_capacity.py`:

```python
from tablelab.build import build_dataset


def test_impossible_build_fails_before_creating_output(tmp_path):
    dc = _full_eob(page=(1000, 500))
    with pytest.raises(LayoutCapacityError):
        build_dataset(tmp_path, "impossible", dc, n=1)
    assert not (tmp_path / "impossible").exists()
```

The full build smoke test below exercises `_validate_boxes` against every rendered token. Avoid a
font-metric-specific unit fixture because Pillow's default-font metrics vary by supported version.

- [ ] **Step 4: Run the full suite and build a review dataset**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q
uv run python -m tablelab.cli build --class eob --n 30 --out ../datasets/eob-reviewable --header --multi-token --background 4 --instances 1 3
uv run python -m tablelab.cli inspect eob-reviewable
```

Expected:

- all harness tests pass;
- the build completes without coordinates outside `[0, 1]`;
- inspect reports the EOB globals/table and 30 samples.

- [ ] **Step 5: Audit the generated JSON**

From repo root run:

```powershell
$d = Get-Content -Raw datasets\eob-reviewable\samples.json | ConvertFrom-Json
$bad = @($d.samples.tokens | Where-Object { $_.x0 -lt 0 -or $_.y0 -lt 0 -or $_.x1 -gt 1 -or $_.y1 -gt 1 })
$terms = @($d.samples.tokens | Where-Object { $null -eq $_.label } | ForEach-Object text | Sort-Object -Unique)
"out_of_bounds=$($bad.Count)"
$terms
```

Expected: `out_of_bounds=0`; no `INVOICE` or `RECEIPT` terms.

- [ ] **Step 6: Commit**

Do not add the gitignored dataset.

```powershell
git add src/tablelab/build.py tests/test_capacity.py
git commit -m "feat: enforce page-valid dataset output"
```

---

### Task 5: Generator documentation sync

**Files:**
- Modify: `harness/README.md`
- Modify: `docs/specs/2026-06-14-synthetic-reviewability-design.md`

- [ ] **Step 1: Document fit semantics and failure behavior**

Add a concise CLI note explaining that row/instance ranges are sampled only among page-feasible
combinations; impossible minimums fail before output; background content is class-aware and uses
reserved slots.

- [ ] **Step 2: Mark generator sections shipped**

Update only the generator status in the design spec. Leave viewer sections active until the viewer
plan is complete.

- [ ] **Step 3: Final generator verification and commit**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q
git diff --check
```

Expected: all tests pass and no whitespace errors.

Commit:

```powershell
git add README.md ../docs/specs/2026-06-14-synthetic-reviewability-design.md
git commit -m "docs: describe page-valid synthetic composition"
```
