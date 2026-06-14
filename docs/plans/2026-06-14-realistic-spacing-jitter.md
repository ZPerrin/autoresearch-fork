# Realistic Spacing + Jitter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the uniform layout grid with per-class, configurable spacing — non-uniform column widths, vertical gap knobs, multi-pair globals, and per-axis jitter — while keeping output page-valid and the golden fixture byte-identical.

**Architecture:** All knobs hang off `DocumentClass` (`FieldSpec.width`, new `LayoutSpec` fields, a new `JitterSpec`). Deterministic knobs fold into the existing capacity planner exactly; jitter is bounded/zero-sum so it consumes only reserved slack. `build.py`'s normalized `[0,1]` validator stays the backstop. Defaults are chosen so every existing class's default output is unchanged.

**Tech Stack:** Python 3 (`harness/src/tablelab`, frozen dataclasses, `random.Random`), pytest, Pillow; React/TS viewer for the read-only metadata surface.

**Spec:** `docs/specs/2026-06-14-realistic-spacing-jitter-design.md`

**Conventions for this plan:** Per `AGENTS.md`, no strict TDD — implement, add a test, verify by running. Run tests from `harness/` with `uv run pytest`. Commit after each task. The invariant that guards us at every step: **`uv run pytest` stays green**, and in particular `tests/test_golden.py` (byte-identical invoice) never breaks.

---

## File map

- `harness/src/tablelab/specs.py` — add `FieldSpec.width`; add `LayoutSpec.row_gap/instance_gap/section_gap/globals_per_row`; add `JitterSpec`; add `DocumentClass.jitter`. *(data only)*
- `harness/src/tablelab/fields.py` — add `TYPE_WIDTH` default-weight map + `field_weight(field)`.
- `harness/src/tablelab/jitter.py` — **new**: bounded/zero-sum jitter helpers.
- `harness/src/tablelab/layout.py` — weighted column edges; resolved vertical gaps; multi-pair globals; jitter integration; capacity-helper updates.
- `harness/src/tablelab/render.py` — apply per-token `dx/dy` offset.
- `harness/src/tablelab/classes.py` — author the `eob` width profile; pin `invoice` field widths to `1.0` (golden guard).
- `harness/src/tablelab/cli.py` — flags for gaps / `globals_per_row` / jitter.
- `harness/tests/test_spacing.py` — **new**: width-sum, gap-capacity, multi-pair globals.
- `harness/tests/test_jitter.py` — **new**: jitter-off byte-identity + page-valid jitter sweep.
- `viewer/src/MetaPanel.tsx`, `viewer/src/types.ts` — surface resolved spacing/jitter config (read-only).

---

## Task 1: Spec fields (data only, no behavior change)

**Files:**
- Modify: `harness/src/tablelab/specs.py`

- [ ] **Step 1: Add `width` to `FieldSpec`**

```python
@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str            # key into fields.SAMPLERS (e.g. "amount", "date")
    align: str = "left"  # "left" | "right"
    width: float | None = None  # column weight; None => fields.TYPE_WIDTH default
```

- [ ] **Step 2: Extend `LayoutSpec`**

```python
@dataclass(frozen=True)
class LayoutSpec:
    page: tuple[int, int] = (1000, 1414)
    margin: tuple[int, int] = (60, 80)
    row_h: int = 74
    pad: int = 12
    table_gap: int = 40                   # back-compat base gap; instance_gap/section_gap fall back to this
    row_gap: int = 0                      # extra gap between consecutive data rows within a table
    instance_gap: int | None = None       # gap between stacked instances (None => table_gap)
    section_gap: int | None = None        # gap between sections globals->tables->background (None => table_gap)
    globals_per_row: int = 1              # label:value pairs packed across one global row
```

- [ ] **Step 3: Add `JitterSpec` and wire it onto `DocumentClass`**

```python
@dataclass(frozen=True)
class JitterSpec:
    """Per-axis random perturbation magnitudes (fractions, 0 = off). Each axis is
    independent so a dataset can isolate one nuisance variable for modeling ablations.
    All bounded/zero-sum: jitter never grows a section's total extent or pushes a token
    out of its cell (see docs/specs/2026-06-14-realistic-spacing-jitter-design.md)."""
    row_h: float = 0.0    # per-row height variance, borrowed zero-sum from row_gap budget
    col_w: float = 0.0    # per-column width variance, zero-sum across the row
    offset: float = 0.0   # per-token x/y wobble, bounded inside the cell pad
    baseline: float = 0.0 # per-token vertical baseline wobble, bounded inside the cell pad
```

Add to `DocumentClass` (after `render`):

```python
    jitter: JitterSpec = JitterSpec()
```

- [ ] **Step 4: Verify nothing changed**

Run: `cd harness && uv run pytest -q`
Expected: PASS (all existing tests; defaults make this a pure data addition).

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat(specs): add width/gap/globals/jitter knobs (data only)"
```

---

## Task 2: Field width weights

**Files:**
- Modify: `harness/src/tablelab/fields.py`
- Test: `harness/tests/test_spacing.py` (new)

- [ ] **Step 1: Add the default-weight map and resolver** (append near `SAMPLERS` in `fields.py`)

```python
# Default column width weights by field type. A column's pixel width is
# usable_width * weight / sum(weights). Explicit FieldSpec.width overrides this.
TYPE_WIDTH = {
    "description": 4.0,
    "date": 2.0,
    "name": 3.0,
    "id": 2.0,
    "code": 1.0,
    "quantity": 1.0,
    "unit_price": 1.5,
    "amount": 1.5,
}


def field_weight(field) -> float:
    """Resolve a field's column weight: explicit override, else type default, else 1.0."""
    if field.width is not None:
        return field.width
    return TYPE_WIDTH.get(field.type, 1.0)
```

- [ ] **Step 2: Write the test** (`harness/tests/test_spacing.py`)

```python
from tablelab.fields import field_weight
from tablelab.specs import FieldSpec


def test_field_weight_uses_explicit_override():
    assert field_weight(FieldSpec("amount", "amount", "right", width=3.0)) == 3.0


def test_field_weight_falls_back_to_type_default():
    assert field_weight(FieldSpec("desc", "description")) == 4.0


def test_field_weight_unknown_type_is_one():
    assert field_weight(FieldSpec("x", "totally_unknown_type")) == 1.0
```

- [ ] **Step 3: Run**

Run: `cd harness && uv run pytest tests/test_spacing.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/fields.py harness/tests/test_spacing.py
git commit -m "feat(fields): type-default column width weights + resolver"
```

---

## Task 3: Weighted column edges in layout (+ pin invoice for golden)

**Why pin invoice:** `TYPE_WIDTH` makes `description`/`amount` non-uniform, which would change the invoice golden. The invoice class is the frozen regression guard, so we pin each of its fields to `width=1.0` (uniform) and document it. `eob`/`receipt` get non-uniform columns for free.

**Files:**
- Modify: `harness/src/tablelab/layout.py` (table-loop column math in `layout()`)
- Modify: `harness/src/tablelab/classes.py` (invoice fields)
- Test: `harness/tests/test_spacing.py`

- [ ] **Step 1: Add a column-edges helper** (in `layout.py`, after `_BACKGROUND_COLUMNS`)

```python
from .fields import sample, background_token, field_weight  # extend existing import

def _column_edges(fields, usable: float, mx: float) -> list[float]:
    """Left/right pixel edges for each column from normalized field weights.
    Returns len(fields)+1 edges; columns sum to exactly `usable` by construction."""
    weights = [field_weight(f) for f in fields]
    total = sum(weights)
    edges = [mx]
    acc = 0.0
    for w in weights:
        acc += w
        edges.append(mx + usable * (acc / total))
    return edges
```

- [ ] **Step 2: Use it in the table loop of `layout()`**

Replace:

```python
        C = len(table.fields)
        cell_w = (W - 2 * mx) / C
```

with:

```python
        C = len(table.fields)
        edges = _column_edges(table.fields, W - 2 * mx, mx)
```

Replace the two `x0 = mx + c * cell_w` / `cell = (x0, y, x0 + cell_w, ...)` blocks (header and data) with edge lookups:

```python
                    x0, x1 = edges[c], edges[c + 1]
                    cell = (x0, y, x1, y + L.row_h)
```

- [ ] **Step 3: Pin invoice fields** (`classes.py`) — keep the golden uniform:

```python
register(DocumentClass(name="invoice", tables=(
    TableSpec(name="line_item", fields=(
        # width=1.0 pins uniform columns: invoice is the byte-identical golden guard.
        _f("description", "description", "left", 1.0),
        _f("quantity", "quantity", "right", 1.0),
        _f("unit_price", "unit_price", "right", 1.0),
        _f("amount", "amount", "right", 1.0),
    )),
), background_terms=_INVOICE_BACKGROUND))
```

And extend the `_f` helper to pass width:

```python
def _f(name: str, type_: str, align: str, width: float | None = None) -> FieldSpec:
    return FieldSpec(name=name, type=type_, align=align, width=width)
```

- [ ] **Step 4: Add a width-sum test** (`test_spacing.py`)

```python
import random
from tablelab import classes as classlib
from tablelab.layout import layout


def test_eob_columns_are_non_uniform_but_fill_page():
    dc = classlib.get("eob")
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    placed = layout(dc, random.Random(0))
    # collect distinct cell x-spans for the claim_line columns
    widths = sorted({round(t.cell[2] - t.cell[0], 3)
                     for t in placed if t.label and "field" in t.label})
    assert len(widths) >= 2  # not all equal
    # leftmost edge at margin, rightmost at W-mx
    xs = [t.cell[0] for t in placed if t.label and "field" in t.label]
    x1s = [t.cell[2] for t in placed if t.label and "field" in t.label]
    assert abs(min(xs) - mx) < 1e-6
    assert abs(max(x1s) - (W - mx)) < 1e-6
```

- [ ] **Step 5: Run — golden must still pass**

Run: `cd harness && uv run pytest -q`
Expected: PASS, including `test_golden.py::test_invoice_matches_legacy_golden`.
If the golden fails: the equal-weight column arithmetic drifted; compute uniform columns with the legacy `mx + c * (usable / C)` formula when all weights are equal. Re-run.

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/layout.py harness/src/tablelab/classes.py harness/tests/test_spacing.py
git commit -m "feat(layout): weighted column widths; pin invoice golden uniform"
```

---

## Task 4: Deterministic vertical gaps

**Files:**
- Modify: `harness/src/tablelab/layout.py` (capacity helpers + `layout()` vertical advance)
- Test: `harness/tests/test_spacing.py`

- [ ] **Step 1: Add gap resolvers** (top of `layout.py`, module-level)

```python
def _row_gap(dc) -> int:
    return dc.layout.row_gap

def _instance_gap(dc) -> int:
    L = dc.layout
    return L.instance_gap if L.instance_gap is not None else L.table_gap

def _section_gap(dc) -> int:
    L = dc.layout
    return L.section_gap if L.section_gap is not None else L.table_gap
```

- [ ] **Step 2: Update `_instance_height`** to include row gaps + instance gap

```python
def _instance_height(dc: DocumentClass, rows: int) -> int:
    L = dc.layout
    header = int(dc.structure.header)
    return (header * L.row_h + rows * L.row_h
            + max(rows - 1, 0) * _row_gap(dc) + _instance_gap(dc))
```

- [ ] **Step 3: Update `_shape_height` and `_fixed_height`** to match

```python
def _shape_height(dc: DocumentClass, shape: Shape) -> int:
    return sum(_instance_height(dc, rows)
               for table_shape in shape for rows in table_shape)


def _fixed_height(dc: DocumentClass) -> int:
    L = dc.layout
    gpr = max(L.globals_per_row, 1)
    n_global_rows = (len(dc.globals) + gpr - 1) // gpr
    globals_height = n_global_rows * L.row_h
    if dc.globals:
        globals_height += _section_gap(dc)
    return globals_height + _background_rows(dc.structure.background) * L.row_h
```

(Note: `_shape_height` previously inlined `(header_rows + rows) * row_h + table_gap`; it now delegates to `_instance_height` so the gap model lives in one place.)

- [ ] **Step 4: Update the vertical advance in `layout()`**

Globals trailer: replace `y += L.table_gap` (after the globals loop) with `y += _section_gap(dc)`.

Data-row loop: replace

```python
            for r in range(rows):
                for c in range(C):
                    ...
                y += L.row_h
            y += L.table_gap
            region += 1
```

with

```python
            for r in range(rows):
                for c in range(C):
                    ...
                y += L.row_h
                if r < rows - 1:
                    y += _row_gap(dc)
            y += _instance_gap(dc)
            region += 1
```

- [ ] **Step 5: Add gap tests** (`test_spacing.py`)

```python
from dataclasses import replace
from tablelab.specs import fork
from tablelab.layout import validate_layout_capacity, LayoutCapacityError


def test_row_gap_increases_row_pitch():
    dc = classlib.get("eob")
    base = layout(dc, random.Random(1))
    spaced = layout(fork(dc, layout=replace(dc.layout, row_gap=30)), random.Random(1))
    ys = lambda p: sorted({t.cell[1] for t in p if t.label and t.label.get("record") is not None})
    # with extra row_gap, the second data row starts lower than without
    assert ys(spaced)[1] - ys(spaced)[0] > ys(base)[1] - ys(base)[0]


def test_oversized_gaps_fail_capacity_cleanly():
    dc = classlib.get("eob")
    huge = fork(dc, layout=replace(dc.layout, section_gap=5000, instance_gap=5000))
    try:
        validate_layout_capacity(huge)
        raised = False
    except LayoutCapacityError:
        raised = True
    assert raised
```

- [ ] **Step 6: Run**

Run: `cd harness && uv run pytest -q`
Expected: PASS. Defaults (`row_gap=0`, gaps -> `table_gap`) keep golden + capacity tests green.

- [ ] **Step 7: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_spacing.py
git commit -m "feat(layout): configurable row/instance/section gaps in planner + placement"
```

---

## Task 5: Multi-pair globals

**Files:**
- Modify: `harness/src/tablelab/layout.py` (globals block of `layout()`)
- Test: `harness/tests/test_spacing.py`

- [ ] **Step 1: Rewrite the globals block** in `layout()`

Replace:

```python
    if dc.globals:
        gw = (W - 2 * mx) * 0.35
        for f in dc.globals:
            label_cell = (mx, y, mx + gw, y + L.row_h)
            _emit(placed, _header_text(f.name) + ":", label_cell,
                  {"global": f.name, "header": True}, "left", dc.render.font_size, multi)
            value_cell = (mx + gw, y, W - mx, y + L.row_h)
            _emit(placed, sample(f.type, rng), value_cell,
                  {"global": f.name}, "left", dc.render.font_size, multi)
            y += L.row_h
        y += L.table_gap
```

with:

```python
    if dc.globals:
        gpr = max(L.globals_per_row, 1)
        usable = W - 2 * mx
        pair_w = usable / gpr
        for i, f in enumerate(dc.globals):
            col = i % gpr
            if i and col == 0:
                y += L.row_h
            px0 = mx + col * pair_w
            gw = pair_w * 0.35
            label_cell = (px0, y, px0 + gw, y + L.row_h)
            _emit(placed, _header_text(f.name) + ":", label_cell,
                  {"global": f.name, "header": True}, "left", dc.render.font_size, multi)
            value_cell = (px0 + gw, y, px0 + pair_w, y + L.row_h)
            _emit(placed, sample(f.type, rng), value_cell,
                  {"global": f.name}, "left", dc.render.font_size, multi)
        y += L.row_h
        y += _section_gap(dc)
```

(For `gpr=1` this is byte-identical to the old stack: same per-token cells and same total advance.)

- [ ] **Step 2: Test** (`test_spacing.py`)

```python
def test_globals_per_row_packs_pairs_and_stays_in_page():
    dc = classlib.get("eob")
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    paired = fork(dc, layout=replace(dc.layout, globals_per_row=2))
    placed = layout(paired, random.Random(0))
    gl = [t for t in placed if t.label and "global" in t.label]
    # two distinct label x-starts => two columns of pairs
    starts = sorted({round(t.cell[0], 3) for t in gl if t.label.get("header")})
    assert len(starts) == 2
    assert all(t.cell[2] <= W - mx + 1e-6 for t in gl)
```

- [ ] **Step 3: Run**

Run: `cd harness && uv run pytest -q`
Expected: PASS (golden untouched: invoice has no globals; eob default `globals_per_row=1` unchanged).

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_spacing.py
git commit -m "feat(layout): multi-pair globals via globals_per_row"
```

---

## Task 6: Jitter (bounded / zero-sum)

**Files:**
- Create: `harness/src/tablelab/jitter.py`
- Modify: `harness/src/tablelab/layout.py` (PlacedToken `dx/dy`; apply jitter)
- Modify: `harness/src/tablelab/render.py` (apply `dx/dy`)
- Test: `harness/tests/test_jitter.py` (new)

- [ ] **Step 1: Jitter helpers** (`jitter.py`)

```python
from __future__ import annotations
import random


def jitter_column_edges(edges: list[float], mag: float, usable: float,
                        rng: random.Random, min_w: float = 8.0) -> list[float]:
    """Perturb interior column edges; first/last stay fixed so the row still spans
    exactly `usable` (zero-sum). Each edge stays >= min_w from its neighbors."""
    out = list(edges)
    span = mag * usable
    for i in range(1, len(edges) - 1):
        lo = out[i - 1] + min_w
        hi = edges[i + 1] - min_w
        if hi <= lo:
            continue
        out[i] = min(max(edges[i] + rng.uniform(-span, span), lo), hi)
    return out


def jitter_row_height(row_h: int, mag: float, gap_budget: int,
                      rng: random.Random) -> tuple[float, float]:
    """Return (cell_height, trailing_gap_delta). Height grows/shrinks within the gap
    budget; the trailing gap absorbs the opposite, so the section total is unchanged."""
    span = min(mag * row_h, gap_budget)
    delta = rng.uniform(-span, span)
    return row_h + delta, -delta


def jitter_offset(mag: float, baseline: float, pad: int,
                  rng: random.Random) -> tuple[float, float]:
    """Per-token (dx, dy) wobble bounded inside the cell pad so the box stays in-cell."""
    sx = mag * pad
    sy = (mag + baseline) * pad
    return rng.uniform(-sx, sx), rng.uniform(-sy, sy)
```

- [ ] **Step 2: Add `dx/dy` to `PlacedToken`** (`layout.py`)

```python
@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]
    label: dict | None
    align: str = "left"
    font_size: int = 22
    dx: float = 0.0
    dy: float = 0.0
```

- [ ] **Step 3: Apply jitter in `layout()`**

At the top of `layout()` add:

```python
    J = dc.jitter
    jx = J.col_w > 0 or J.row_h > 0 or J.offset > 0 or J.baseline > 0
```

Column edges per data row — when `J.col_w > 0`, recompute jittered edges inside the row loop (otherwise reuse the base `edges` with no RNG draw):

```python
            for r in range(rows):
                row_edges = (jitter_column_edges(edges, J.col_w, W - 2 * mx, rng)
                             if J.col_w > 0 else edges)
                cell_h = L.row_h
                gap_after = _row_gap(dc)
                if J.row_h > 0 and _row_gap(dc) > 0:
                    cell_h, delta = jitter_row_height(L.row_h, J.row_h, _row_gap(dc), rng)
                    gap_after = _row_gap(dc) + delta
                for c in range(C):
                    f = table.fields[c]
                    value = sample(f.type, rng)
                    x0, x1 = row_edges[c], row_edges[c + 1]
                    cell = (x0, y, x1, y + cell_h)
                    _emit(placed, value, cell,
                          {**reg, "record": r, "field": c}, f.align, dc.render.font_size, multi)
                y += cell_h
                if r < rows - 1:
                    y += gap_after
            y += _instance_gap(dc)
```

Per-token offset — apply after `rng.shuffle(placed)` is **not** safe (offset uses rng); instead apply offset just before shuffle, iterating placed tokens, only when enabled:

```python
    if J.offset > 0 or J.baseline > 0:
        for p in placed:
            p.dx, p.dy = jitter_offset(J.offset, J.baseline, L.pad, rng)
    rng.shuffle(placed)
    return placed
```

Add the import at the top of `layout.py`:

```python
from .jitter import jitter_column_edges, jitter_row_height, jitter_offset
```

**Critical:** when every jitter axis is `0`, none of these branches run, so no RNG is drawn and the shuffle order — hence the output — is byte-identical.

- [ ] **Step 4: Apply `dx/dy` in `render.py`**

In the single-token path, after computing `tx, ty`:

```python
            tx += p.dx
            ty += p.dy
```

In the multi-word path, add `placed[idxs[0]].dx` / `.dy` to the phrase origin `x` and each `ty`. (Bounded by pad, so glyphs stay in-cell; `build._validate_boxes` remains the page-bounds backstop.)

- [ ] **Step 5: Tests** (`test_jitter.py`)

```python
import json, random
from dataclasses import replace
from pathlib import Path

from tablelab import classes as classlib
from tablelab.specs import fork, JitterSpec
from tablelab.layout import layout
from tablelab.render import render

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _tokens(dc, seed, n):
    rng = random.Random(seed)
    W, H = dc.layout.page
    out = []
    for _ in range(n):
        placed = layout(dc, rng)
        _img, boxes = render(placed, dc)
        out.append([
            {"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
             "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4),
             "text": p.text, "label": p.label}
            for p, b in zip(placed, boxes)])
    return out


def test_jitter_off_is_byte_identical_to_golden():
    # invoice with an explicit all-zero JitterSpec must still match the golden.
    dc = fork(classlib.get("invoice"), jitter=JitterSpec())
    assert _tokens(dc, 7, 3) == json.loads(GOLDEN.read_text())


def test_jitter_keeps_every_box_in_page():
    base = classlib.get("eob")
    dc = fork(base, layout=replace(base.layout, row_gap=24),
              jitter=JitterSpec(row_h=0.4, col_w=0.4, offset=0.8, baseline=0.5))
    W, H = dc.layout.page
    for seed in range(100):
        placed = layout(dc, random.Random(seed))
        _img, boxes = render(placed, dc)
        for (x0, y0, x1, y1) in boxes:
            assert 0 <= x0 <= x1 <= W
            assert 0 <= y0 <= y1 <= H


def test_columns_stay_zero_sum_under_col_jitter():
    base = classlib.get("eob")
    W, mx = base.layout.page[0], base.layout.margin[0]
    dc = fork(base, jitter=JitterSpec(col_w=0.5))
    placed = layout(dc, random.Random(3))
    xs = [t.cell[0] for t in placed if t.label and "field" in t.label]
    x1s = [t.cell[2] for t in placed if t.label and "field" in t.label]
    assert abs(min(xs) - mx) < 1e-6 and abs(max(x1s) - (W - mx)) < 1e-6
```

- [ ] **Step 6: Run**

Run: `cd harness && uv run pytest -q`
Expected: PASS, including both golden tests and the 100-seed jitter sweep.

- [ ] **Step 7: Commit**

```bash
git add harness/src/tablelab/jitter.py harness/src/tablelab/layout.py harness/src/tablelab/render.py harness/tests/test_jitter.py
git commit -m "feat(jitter): bounded zero-sum per-axis jitter (col_w/row_h/offset/baseline)"
```

---

## Task 7: CLI knobs

**Files:**
- Modify: `harness/src/tablelab/cli.py`

- [ ] **Step 1: Add arguments** to the `build` subparser (after `--background`)

```python
    b.add_argument("--row-gap", type=int, metavar="PX", help="gap between data rows")
    b.add_argument("--instance-gap", type=int, metavar="PX", help="gap between table instances")
    b.add_argument("--section-gap", type=int, metavar="PX", help="gap between sections")
    b.add_argument("--globals-per-row", type=int, metavar="N",
                   help="label:value pairs packed across one global row")
    b.add_argument("--jitter", type=float, nargs=4, metavar=("ROW_H", "COL_W", "OFFSET", "BASELINE"),
                   help="per-axis jitter magnitudes (0 = off)")
```

- [ ] **Step 2: Apply them in `_build`** (extend the existing `replace`/`fork` block)

```python
    layout_kw = {}
    if args.row_gap is not None: layout_kw["row_gap"] = args.row_gap
    if args.instance_gap is not None: layout_kw["instance_gap"] = args.instance_gap
    if args.section_gap is not None: layout_kw["section_gap"] = args.section_gap
    if args.globals_per_row is not None: layout_kw["globals_per_row"] = args.globals_per_row
    if layout_kw:
        L = replace(L, **layout_kw)
    jitter = dc.jitter
    if args.jitter:
        from .specs import JitterSpec
        jitter = JitterSpec(*args.jitter)
    if L is not dc.layout or tables is not dc.tables or S is not dc.structure or jitter is not dc.jitter:
        dc = fork(dc, layout=L, tables=tables, structure=S, jitter=jitter)
```

(Remove the now-duplicated final `fork` call so there is exactly one.)

- [ ] **Step 3: Smoke test the CLI** end-to-end into a temp dir

Run:
```bash
cd harness && uv run python -m tablelab.cli build --class eob --n 2 \
  --globals-per-row 2 --row-gap 20 --section-gap 60 --jitter 0.3 0.3 0.6 0.4 \
  --out ../datasets/_cli_smoke && rm -rf ../datasets/_cli_smoke
```
Expected: prints `built 2 eob samples -> ../datasets/_cli_smoke`, no `LayoutCapacityError`, no box-validation error.

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat(cli): build flags for gaps, globals-per-row, and jitter"
```

---

## Task 8: Author the `eob` recipe + regenerate a review dataset

**Files:**
- Modify: `harness/src/tablelab/classes.py` (eob field widths + `globals_per_row`)

- [ ] **Step 1: Give eob explicit column widths and 2-up globals**

```python
register(DocumentClass(
    name="eob",
    globals=(
        _f("member_name", "name", "left"),
        _f("member_id", "id", "left"),
        _f("provider", "name", "left"),
        _f("claim_number", "id", "left"),
    ),
    tables=(
        TableSpec(name="claim_line", fields=(
            _f("service_date", "date", "left", 2.0),
            _f("code", "code", "left", 1.0),
            _f("description", "description", "left", 4.0),
            _f("amount_billed", "amount", "right", 1.5),
            _f("amount_owed", "amount", "right", 1.5),
        ), rows=(2, 5), instances=(1, 2)),
    ),
    background_terms=_EOB_BACKGROUND,
    layout=LayoutSpec(globals_per_row=2),
))
```

Add `LayoutSpec` to the `classes.py` import line:

```python
from .specs import FieldSpec, TableSpec, DocumentClass, LayoutSpec
```

- [ ] **Step 2: Run the suite** — eob column/global changes are horizontal/row-count only; verify nothing regressed

Run: `cd harness && uv run pytest -q`
Expected: PASS. If a structural test in `test_globals.py`/`test_capacity.py` asserted an exact position that moved, update that assertion to the new resolved geometry (the structural contract — labels/regions/counts — is unchanged).

- [ ] **Step 3: Build a review dataset with mild jitter**

Run:
```bash
cd harness && uv run python -m tablelab.cli build --class eob --n 12 \
  --instances 1 3 --header --multi-token --background 4 \
  --row-gap 18 --section-gap 64 --jitter 0.25 0.25 0.6 0.4 \
  --out ../datasets/eob-spaced
```
Expected: builds without capacity/box errors.

- [ ] **Step 4: Eyeball in the viewer** (the dev server honors `PORT`; use the preview tooling or `npm --prefix viewer run dev`). Confirm: non-uniform columns, 2-up member/provider/claim globals, visible row breathing, and slight per-row irregularity — visibly less grid-like than `eob-full`.

- [ ] **Step 5: Commit** (dataset is gitignored; only the class change is tracked)

```bash
git add harness/src/tablelab/classes.py
git commit -m "feat(classes): eob spacing recipe (weighted columns + 2-up globals)"
```

---

## Task 9: Surface spacing/jitter config in the viewer (read-only)

**Files:**
- Modify: `viewer/src/types.ts` (extend the resolved-spec types)
- Modify: `viewer/src/MetaPanel.tsx` (render the knobs)

- [ ] **Step 1: Extend types** — add the new `LayoutSpec` fields and a `jitter` block to whatever interface models `manifest.config.spec` (mirror the Python dataclasses: `row_gap`, `instance_gap`, `section_gap`, `globals_per_row`, and `jitter: {row_h, col_w, offset, baseline}`). Make them optional for back-compat with old manifests.

- [ ] **Step 2: Render them** in `MetaPanel`'s STRUCTURE area — a compact "Spacing" line (`row_gap`/`instance_gap`/`section_gap`/`globals_per_row`) and a "Jitter" line showing only non-zero axes (or "off"). Read-only chips/text consistent with the existing metadata styling.

- [ ] **Step 3: Build the viewer**

Run: `npm --prefix viewer run build`
Expected: type-checks and builds clean.

- [ ] **Step 4: Verify in-app** — load `eob-spaced` and confirm the spacing/jitter values display.

- [ ] **Step 5: Commit**

```bash
git add viewer/src/types.ts viewer/src/MetaPanel.tsx
git commit -m "feat(viewer): surface resolved spacing/jitter config in metadata"
```

---

## Self-review notes (coverage check)

- Non-uniform widths (spec §Non-uniform column widths) → Tasks 2, 3, 8.
- Vertical gaps (spec §Vertical spacing knobs) → Tasks 1, 4.
- Multi-pair globals (spec §Multi-pair globals) → Tasks 1, 5, 8.
- Per-axis jitter, bounded/zero-sum (spec §Jitter) → Tasks 1, 6.
- Capacity integration + `[0,1]` backstop (spec §Capacity integration) → Tasks 4, 5 (planner terms), 6 (zero-sum invariants), verified by existing `_validate_boxes` and the jitter sweep.
- Golden byte-identity (spec §Verification) → guarded every task; explicit jitter-off test in Task 6.
- Per-class configurability (spec §Scope) → all knobs on `DocumentClass`; eob recipe in Task 8; CLI overrides in Task 7.
- Viewer surface (spec §Component boundaries) → Task 9.
- Out of scope (spanning cells, totals rows, visual realism) → untouched.

**Method-name consistency:** `field_weight` (Task 2) used in Task 3; `_row_gap`/`_instance_gap`/`_section_gap` (Task 4) used in Tasks 4–6; `jitter_column_edges`/`jitter_row_height`/`jitter_offset` (Task 6) match their call sites; `PlacedToken.dx/dy` (Task 6) consumed in `render.py` (Task 6 Step 4).
