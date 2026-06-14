# Multi-table 4c — Global fields + the EOB class

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Place `DocumentClass.globals` as key-value pairs at the top of the page (label token + value token, `label = {"global": name}`), then upgrade the registered `eob` class to the real EOB shape (member/provider globals + a `claim_line` table with multiple instances). Default-empty globals keep the other built-ins byte-identical. Design: `docs/specs/2026-06-13-multi-table-globals-design.md` (§ 4c).

**Architecture:** `layout()` emits a globals block before the tables when `dc.globals` is non-empty: for each global, a field-name label token (`{"global": name, "header": True}`) and a value token (`{"global": name}`), one per row. `fields.py` gains `name`/`id` samplers. `classes.py` rebuilds `eob` with globals + a multi-instance claim table. `inspect` shows globals.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `pytest`. Run from `harness/` via `uv run`.

**Conventions:** No-TDD. Golden guards byte-identical (invoice/receipt have empty globals). Commit per task.

---

## File structure

| File | Status | Change |
|---|---|---|
| `harness/src/tablelab/fields.py` | modify | `name` + `id` samplers for global fields. |
| `harness/src/tablelab/layout.py` | modify | Emit a globals block (label + value rows) before the tables. |
| `harness/src/tablelab/classes.py` | modify | Rebuild `eob` with globals + `claim_line` instances. |
| `harness/src/tablelab/cli.py` | modify | `inspect` prints globals. |
| `harness/tests/test_globals.py` | create | Globals presence/placement + EOB shape. |
| `harness/README.md` | modify | Note the EOB class shape. |

---

## Task 1: `fields.py` — `name` / `id` samplers

**Files:** Modify `harness/src/tablelab/fields.py`

- [ ] **Step 1: Append after `background_token`**

```python
# Value samplers for global / singleton fields (names, ids).
_NAMES = [
    "John Smith", "Maria Garcia", "Wei Chen", "Aisha Khan", "Robert Jones",
    "Linda Nguyen", "David Patel", "Sarah Johnson",
    "Acme Medical Group", "Lakeside Clinic", "Mercy Hospital", "Summit Health",
]


def _name(rng: random.Random) -> str:
    return rng.choice(_NAMES)


def _id(rng: random.Random) -> str:
    return f"{rng.choice('ABCDEFGHJKMNP')}{rng.randint(100000, 999999)}"


SAMPLERS["name"] = _name
SAMPLERS["id"] = _id
```

- [ ] **Step 2: Verify**

Run (from `harness/`):
```bash
uv run python -c "import random; from tablelab.fields import sample; r=random.Random(3); print(sample('name', r), '|', sample('id', r))"
```
Expected: a name (possibly multi-word) and an ID like `K734512`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/fields.py
git commit -m "feat: name/id value samplers for global fields"
```

---

## Task 2: `layout.py` — emit the globals block

**Files:** Modify `harness/src/tablelab/layout.py`

Replace **only** the `layout()` function (keep `PlacedToken`, `_header_text`, `_emit`, imports).

- [ ] **Step 1: Replace `layout()`**

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Global/singleton fields
    (dc.globals) are laid out first as label:value rows at the top; then each table
    is drawn as randint(instances) stacked instances with table_gap, tagged with a
    region when the class is multi-instance. Header rows (structure.header),
    multi-token split (structure.multi_token) and background tokens
    (structure.background) apply as before. Single table/instance, no-globals output
    is byte-identical to the prior builder."""
    L = dc.layout
    W, H = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    multi_region = len(dc.tables) > 1 or sum(t.instances[1] for t in dc.tables) > 1
    placed: list[PlacedToken] = []
    y = float(my)
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
        if y_hi <= y_lo:  # content fills the page; fall back to the full interior
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

Note: invoice/receipt have `globals=()`, so the globals block is skipped and no extra `sample()` is drawn — byte-identical. The globals block runs before the table loop, so for classes with globals its `sample()` calls precede the table draws (fine; those classes have no golden).

- [ ] **Step 2: Verify golden + globals**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden byte-identical; prior features green).

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat: layout emits global label:value rows above the tables"
```

---

## Task 3: `classes.py` — the real EOB class

**Files:** Modify `harness/src/tablelab/classes.py`

- [ ] **Step 1: Replace the `eob` registration**

Replace the existing `register(DocumentClass(name="eob", ...))` block with:

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
            _f("service_date", "date", "left"),
            _f("code", "code", "left"),
            _f("description", "description", "left"),
            _f("amount_billed", "amount", "right"),
            _f("amount_owed", "amount", "right"),
        ), rows=(2, 5), instances=(1, 2)),
    ),
))
```

(`invoice` and `receipt` are unchanged — single table, no globals.)

- [ ] **Step 2: Verify the EOB shape**

Run (from `harness/`):
```bash
uv run python -c "from tablelab import classes as c; dc=c.get('eob'); print('globals:', [f.name for f in dc.globals]); print('table:', dc.tables[0].name, 'instances', dc.tables[0].instances, 'rows', dc.tables[0].rows)"
```
Expected: `globals: ['member_name', 'member_id', 'provider', 'claim_number']` and `table: claim_line instances (1, 2) rows (2, 5)`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/classes.py
git commit -m "feat: eob class — member/provider globals + multi-instance claim_line table"
```

---

## Task 4: `cli.py` — inspect shows globals

**Files:** Modify `harness/src/tablelab/cli.py`

- [ ] **Step 1: Add a globals line to `_inspect`**

In `_inspect`, after the `fields = [...]` line, add:

```python
    glds = [f["name"] for f in spec.get("globals", [])]
```

and add a print line immediately after the `fields:` print:

```python
    print(f"globals:  {glds}")
```

- [ ] **Step 2: Smoke-test the EOB build**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class eob --n 6 --out ../datasets/smoke-eob --header
uv run python -m tablelab.cli inspect smoke-eob
```
Expected: `inspect` prints `tables: ['claim_line']`, the 5 claim fields, `globals: ['member_name', 'member_id', 'provider', 'claim_number']`, and a tokens/sample count.

- [ ] **Step 3: Confirm globals + region serialized**

Run (from repo root):
```bash
python -c "import json; d=json.load(open('datasets/smoke-eob/samples.json')); toks=[t for s in d['samples'] for t in s['tokens']]; g=[t for t in toks if t['label'] and 'global' in t['label']]; r=[t for t in toks if t['label'] and 'region' in t['label']]; print('global tokens:', len(g), '| region tokens:', len(r))"
```
Expected: both positive (globals present, claim tokens carry region).

- [ ] **Step 4: Clean up**

Run (from repo root):
```bash
rm -rf datasets/smoke-eob
```

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: inspect prints globals"
```

---

## Task 5: Behavioral tests

**Files:** Create `harness/tests/test_globals.py`

- [ ] **Step 1: Write the tests**

```python
from __future__ import annotations

import random
from collections import defaultdict

from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render


def test_no_globals_for_simple_classes():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all(p.label is None or "global" not in p.label for p in placed)


def test_eob_emits_named_globals():
    placed = layout(classlib.get("eob"), random.Random(7))
    gnames = {p.label["global"] for p in placed if p.label and "global" in p.label}
    assert {"member_name", "member_id", "provider", "claim_number"} <= gnames


def test_each_global_has_a_label_and_a_value():
    placed = layout(classlib.get("eob"), random.Random(7))
    by_name = defaultdict(list)
    for p in placed:
        if p.label and "global" in p.label:
            by_name[p.label["global"]].append(p)
    for toks in by_name.values():
        kinds = {bool(t.label.get("header")) for t in toks}
        assert kinds == {True, False}  # a label token (header) and a value token


def test_globals_sit_above_the_claim_table():
    placed = layout(classlib.get("eob"), random.Random(7))
    g = [p for p in placed if p.label and "global" in p.label]
    claim = [p for p in placed if p.label and "record" in p.label]
    assert max(p.cell[3] for p in g) <= min(p.cell[1] for p in claim) + 1


def test_eob_claim_table_is_multi_instance():
    placed = layout(classlib.get("eob"), random.Random(7))
    claim = [p for p in placed if p.label and "record" in p.label]
    assert all("region" in p.label for p in claim)  # multi-instance class always tags region


def test_eob_renders_all_boxes_set():
    dc = classlib.get("eob")
    placed = layout(dc, random.Random(7))
    _img, boxes = render(placed, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)
```

- [ ] **Step 2: Run the full suite**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden + prior features + the six new globals tests).

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_globals.py
git commit -m "test: globals — presence, label+value pairing, placement, EOB multi-instance"
```

---

## Task 6: Docs

**Files:** Modify `harness/README.md`

- [ ] **Step 1: Note the EOB shape**

In the `## CLI (tablelab.cli)` section, after the `build` flags line, add:

```markdown
The `eob` class is the full shape: member/provider **global fields** + a repeated **claim_line** table (multiple instances, `region`-tagged). `invoice` and `receipt` are single tables.
```

- [ ] **Step 2: Commit**

```bash
git add harness/README.md
git commit -m "docs: README note for the EOB class shape"
```

---

## Done criteria

- `uv run pytest -q` passes: golden byte-identical (invoice/receipt have empty globals), six new globals tests pass.
- `build --class eob` produces member/provider globals at the top + a region-tagged claim table; `inspect` shows globals; `samples.json` carries both `global` and `region` labels.
- The EOB document renders in the viewer with key-value globals above the claim lines.

## Implementer notes

- **Byte-identical hinge:** invoice/receipt have `globals=()`, so the globals block is skipped — no extra `sample()`. If `tests/test_golden.py` fails, check that the globals block is guarded by `if dc.globals:`.
- The EOB claim table uses `rows=(2,5)`, `instances=(1,2)` to stay on the default page. Many-instance overflow is the known, deferred limitation.
