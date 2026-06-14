# Multi-table 4b — Multiple instances + region label

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Stack multiple instances of a table and tag each instance's tokens with a `region` index. `region` is added **only when the class is multi-instance**, so the single-instance built-ins stay byte-identical. Design: `docs/specs/2026-06-13-multi-table-globals-design.md` (§ 4b).

**Architecture:** `layout()` already draws `instances` and stacks them with `table_gap` (from 4a). 4b adds a `region` counter incremented per instance and merges `{"region": g}` into data + header labels when `multi_region` (more than one possible table instance, or more than one table). CLI gains `--instances MIN MAX`.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `pytest`. Run from `harness/` via `uv run`.

**Conventions:** No-TDD. Golden test guards byte-identical (built-ins are single-instance → no region). Commit per task.

---

## File structure

| File | Status | Change |
|---|---|---|
| `harness/src/tablelab/layout.py` | modify | Add `multi_region` flag + `region` counter; merge `{"region": g}` into labels. |
| `harness/src/tablelab/cli.py` | modify | Add `--instances MIN MAX`. |
| `harness/tests/test_multi_table.py` | create | Region presence/contiguity, stacking, render. |
| `harness/README.md` | modify | Note `--instances`. |

---

## Task 1: `layout.py` — region label for multi-instance documents

**Files:** Modify `harness/src/tablelab/layout.py`

Replace **only** the `layout()` function (keep `PlacedToken`, `_header_text`, `_emit`, imports).

- [ ] **Step 1: Replace `layout()`**

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Iterates dc.tables with a
    vertical cursor, drawing randint(instances) copies of each table stacked with
    table_gap. When the class is multi-instance (more than one possible table
    instance), data and header labels gain a 0-based ``region`` index. Single
    table/instance output is byte-identical to the prior builder. Header rows
    (structure.header), multi-token split (structure.multi_token) and background
    tokens (structure.background) apply as before."""
    L = dc.layout
    W, H = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    multi_region = len(dc.tables) > 1 or sum(t.instances[1] for t in dc.tables) > 1
    placed: list[PlacedToken] = []
    y = float(my)
    region = 0
    for table in dc.tables:
        C = len(table.fields)
        cell_w = (W - 2 * mx) / C
        lo, hi = table.instances
        instances = lo if lo == hi else rng.randint(lo, hi)
        for _inst in range(instances):
            rows = rng.randint(table.rows[0], table.rows[1])
            reg = {"region": region} if multi_region else {}
            if header:
                for c in range(C):
                    f = table.fields[c]
                    x0 = mx + c * cell_w
                    cell = (x0, y, x0 + cell_w, y + L.row_h)
                    _emit(placed, _header_text(f.name), cell,
                          {**reg, "field": c, "header": True}, f.align, dc.render.font_size, multi)
                y += L.row_h
            for r in range(rows):
                for c in range(C):
                    f = table.fields[c]
                    value = sample(f.type, rng)
                    x0 = mx + c * cell_w
                    cell = (x0, y, x0 + cell_w, y + L.row_h)
                    _emit(placed, value, cell,
                          {**reg, "record": r, "field": c}, f.align, dc.render.font_size, multi)
                y += L.row_h
            y += L.table_gap
            region += 1
    n_bg = dc.structure.background
    if n_bg:
        y_lo, y_hi = y, H - my - L.row_h
        if y_hi <= y_lo:  # tables fill the page; fall back to the full interior
            y_lo, y_hi = float(my), float(H - my - L.row_h)
        for _ in range(n_bg):
            bx = rng.uniform(mx, W - mx - 80)
            by = rng.uniform(y_lo, y_hi)
            cell = (bx, by, bx + 80, by + L.row_h)
            placed.append(PlacedToken(
                text=background_token(rng), cell=cell, label=None,
                align="left", font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
```

Note: for the built-ins (`instances=(1,1)`, one table) `multi_region` is `False`, so `reg = {}` and labels are unchanged `{**{}, "record": r, "field": c}` — byte-identical. The `region` counter draws no RNG.

- [ ] **Step 2: Verify golden + multi-instance behavior**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden byte-identical; prior features green). Do NOT edit the golden file.

Run (from `harness/`):
```bash
uv run python -c "import random; from dataclasses import replace; from tablelab import classes as c; from tablelab.specs import fork; from tablelab.layout import layout; dc=c.get('invoice'); inst=fork(dc, tables=tuple(replace(t, instances=(2,2)) for t in dc.tables)); p=layout(inst, random.Random(7)); regs=sorted({t.label['region'] for t in p}); print('regions:', regs); r0=[t for t in p if t.label['region']==0]; r1=[t for t in p if t.label['region']==1]; print('region 1 below region 0:', max(t.cell[3] for t in r0) <= min(t.cell[1] for t in r1) + 1)"
```
Expected: `regions: [0, 1]` and `region 1 below region 0: True`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat: layout tags multi-instance tables with a region label (single-instance byte-identical)"
```

---

## Task 2: `cli.py` — `--instances` flag

**Files:** Modify `harness/src/tablelab/cli.py`

- [ ] **Step 1: Add the instances override in `_build`**

In `_build`, the tables-building block currently reads:

```python
    tables = dc.tables
    if args.rows:
        tables = tuple(replace(t, rows=(args.rows[0], args.rows[1])) for t in tables)
```

Add an instances clause so it reads:

```python
    tables = dc.tables
    if args.rows:
        tables = tuple(replace(t, rows=(args.rows[0], args.rows[1])) for t in tables)
    if args.instances:
        tables = tuple(replace(t, instances=(args.instances[0], args.instances[1])) for t in tables)
```

- [ ] **Step 2: Add the `--instances` argument**

In `main()`, immediately after the `--rows` argument line for the `build` subparser, add:

```python
    b.add_argument("--instances", type=int, nargs=2, metavar=("MIN", "MAX"),
                   help="number of instances per table (adds a region label)")
```

- [ ] **Step 3: Smoke-test**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class invoice --n 4 --out ../datasets/smoke-inst --instances 2 2 --rows 2 2
uv run python -m tablelab.cli inspect smoke-inst
```
Expected: builds cleanly; `inspect` shows `tokens: 64 (16.0/sample)` (2 instances × 2 rows × 4 fields = 16/sample).

- [ ] **Step 4: Confirm the region label serialized**

Run (from repo root):
```bash
python -c "import json; d=json.load(open('datasets/smoke-inst/samples.json')); regs=sorted({t['label']['region'] for s in d['samples'] for t in s['tokens']}); print('regions in file:', regs)"
```
Expected: `regions in file: [0, 1]`.

- [ ] **Step 5: Clean up**

Run (from repo root):
```bash
rm -rf datasets/smoke-inst
```

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: CLI --instances flag"
```

---

## Task 3: Behavioral tests

**Files:** Create `harness/tests/test_multi_table.py`

- [ ] **Step 1: Write the tests**

```python
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _instanced(n_lo, n_hi, **structure):
    dc = classlib.get("invoice")
    tables = tuple(replace(t, instances=(n_lo, n_hi)) for t in dc.tables)
    return fork(dc, tables=tables, structure=replace(dc.structure, **structure))


def test_single_instance_has_no_region():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all("region" not in p.label for p in placed if p.label)


def test_multiple_instances_label_region_contiguous():
    placed = layout(_instanced(2, 2), random.Random(7))
    regions = sorted({p.label["region"] for p in placed})
    assert regions == [0, 1]
    # records restart per instance (each region is its own table)
    by_region = defaultdict(set)
    for p in placed:
        by_region[p.label["region"]].add(p.label["record"])
    assert by_region[0] and by_region[1]


def test_instances_stacked_vertically():
    placed = layout(_instanced(2, 2), random.Random(7))
    r0 = [p for p in placed if p.label["region"] == 0]
    r1 = [p for p in placed if p.label["region"] == 1]
    assert max(p.cell[3] for p in r0) <= min(p.cell[1] for p in r1) + 1


def test_instances_render_all_boxes_set():
    dc = _instanced(2, 3)
    placed = layout(dc, random.Random(7))
    _img, boxes = render(placed, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)


def test_instances_compose_with_header_and_region():
    placed = layout(_instanced(2, 2, header=True), random.Random(7))
    # each instance's header tokens carry that region
    hdr = [p for p in placed if p.label.get("header")]
    assert sorted({p.label["region"] for p in hdr}) == [0, 1]
```

- [ ] **Step 2: Run the full suite**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden + prior features + the five new instance tests).

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_multi_table.py
git commit -m "test: multiple instances — region presence, contiguity, stacking, render, header"
```

---

## Task 4: Docs

**Files:** Modify `harness/README.md`

- [ ] **Step 1: Note the flag**

In the `## CLI (tablelab.cli)` section, append `--instances` to the `build` flags line:

```markdown
`build` flags: `--seed`, `--rows MIN MAX`, `--page W H`, `--instances MIN MAX` (stacked table instances, adds a region label), `--multi-token` (split multi-word cells into per-word tokens), `--header` (top row of field-name tokens), `--background N` (scatter N non-table tokens). Classes: `invoice`, `eob`, `receipt`.
```

- [ ] **Step 2: Commit**

```bash
git add harness/README.md
git commit -m "docs: README note for --instances"
```

---

## Done criteria

- `uv run pytest -q` passes: golden byte-identical (built-ins single-instance → no region), five new instance tests pass.
- `build --instances 2 2` stacks two grids with `region` 0/1 in the label and in `samples.json`.
- Composes with `--header` (per-instance headers carry region) and the other flags.

## Implementer notes

- **Byte-identical hinge:** `multi_region` is `False` for the single-instance built-ins, so `reg = {}` leaves labels unchanged; `instances=(1,1)` draws no RNG. If `tests/test_golden.py` fails, check those two.
- **Known limitation (acceptable for this slice):** many instances × rows can overflow the page bottom (no multi-page / auto-fit yet) — keep demos small via `--rows` or use a larger `--page`. Deferred.
