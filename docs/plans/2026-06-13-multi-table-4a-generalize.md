# Multi-table 4a — Generalize the spec model (byte-identical)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Generalize `DocumentClass` from one `fields` list to `tables: tuple[TableSpec,...]` + `globals: tuple[FieldSpec,...]`, moving `rows` onto `TableSpec`. Single-table / single-instance output stays **byte-identical** (golden guards it). No new user-facing behavior — this unlocks 4b (instances + region) and 4c (globals + EOB).

**Architecture:** `TableSpec` wraps a table's fields + `rows` + `instances`. `layout()` iterates `dc.tables` with a vertical cursor; for the built-ins (one table, `instances=(1,1)`) it draws the same RNG in the same order and emits the same labels. `LayoutSpec` drops `rows`, gains `table_gap`. CLI `--rows` overrides every table; `inspect` reads fields from tables.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `pytest`. Run from `harness/` via `uv run`.

**Conventions:** No-TDD. The golden test is the byte-identical guard; all existing tests must stay green. Commit per task.

---

## File structure

| File | Status | Change |
|---|---|---|
| `harness/src/tablelab/specs.py` | modify | Add `TableSpec`; `LayoutSpec` drop `rows` + add `table_gap`; `DocumentClass` `fields`→`tables` + `globals`. |
| `harness/src/tablelab/classes.py` | modify | Migrate the 3 built-ins to one-table form. |
| `harness/src/tablelab/layout.py` | modify | Rewrite `layout()` to iterate `dc.tables` (single table/instance, no region). |
| `harness/src/tablelab/cli.py` | modify | `--rows` overrides every table; `inspect` reads fields from tables. |
| `harness/tests/test_header.py` | modify | `len(dc.fields)` → `len(dc.tables[0].fields)`. |

---

## Task 1: `specs.py` — `TableSpec`, `LayoutSpec`, `DocumentClass`

**Files:** Modify `harness/src/tablelab/specs.py`

- [ ] **Step 1: Replace the whole file**

```python
from __future__ import annotations
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str            # key into fields.SAMPLERS (e.g. "amount", "date")
    align: str = "left"  # "left" | "right"


@dataclass(frozen=True)
class TableSpec:
    name: str
    fields: tuple[FieldSpec, ...]
    rows: tuple[int, int] = (2, 6)        # record-count range, inclusive (passed to randint)
    instances: tuple[int, int] = (1, 1)   # number of instances of this table per document


@dataclass(frozen=True)
class LayoutSpec:
    page: tuple[int, int] = (1000, 1414)  # page pixel size (W, H)
    margin: tuple[int, int] = (60, 80)    # (x, y) page margins in px
    row_h: int = 74                       # row height in px
    pad: int = 12                         # in-cell text padding in px
    table_gap: int = 40                   # vertical gap after each table instance in px


@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter, spanning cells). Each follow-on
    spec adds fields here. See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    multi_token: split multi-word cell values into per-word tokens that share one
        record/field and carry a within-cell order index (seq).
    header: emit a top header row of field-name tokens (label {"field": c, "header": True}).
    background: scatter N non-table tokens (label = None) in the footer band below the table."""
    multi_token: bool = False
    header: bool = False
    background: int = 0


@dataclass(frozen=True)
class RenderSpec:
    font_size: int = 22
    renderer: str = "pillow"   # the visual-realism seam; only "pillow" exists today


@dataclass(frozen=True)
class DocumentClass:
    name: str
    tables: tuple[TableSpec, ...]
    globals: tuple[FieldSpec, ...] = ()
    layout: LayoutSpec = LayoutSpec()
    structure: StructureSpec = StructureSpec()
    render: RenderSpec = RenderSpec()


def fork(dc: DocumentClass, name: str | None = None, **overrides) -> DocumentClass:
    """Copy a DocumentClass with top-level fields replaced (e.g. ``tables=...``,
    ``layout=...``). Nested specs are replaced wholesale — build the replacement with
    ``dataclasses.replace(dc.tables[0], rows=...)`` and pass it in."""
    return replace(dc, name=name or dc.name, **overrides)
```

- [ ] **Step 2: Verify**

Run (from `harness/`):
```bash
uv run python -c "from tablelab.specs import TableSpec, DocumentClass, FieldSpec; t=TableSpec('t',(FieldSpec('a','amount','right'),)); dc=DocumentClass('c',(t,)); print(dc.tables[0].name, dc.tables[0].rows, dc.tables[0].instances, dc.globals)"
```
Expected: `t (2, 6) (1, 1) ()`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat: generalize spec model — TableSpec; DocumentClass.tables/globals; rows->TableSpec"
```

---

## Task 2: `classes.py` — migrate built-ins to one-table form

**Files:** Modify `harness/src/tablelab/classes.py`

- [ ] **Step 1: Replace the whole file**

```python
from __future__ import annotations
from .specs import FieldSpec, TableSpec, DocumentClass

REGISTRY: dict[str, DocumentClass] = {}


def register(dc: DocumentClass) -> DocumentClass:
    REGISTRY[dc.name] = dc
    return dc


def get(name: str) -> DocumentClass:
    if name not in REGISTRY:
        raise KeyError(f"unknown document class {name!r}; known: {classes()}")
    return REGISTRY[name]


def classes() -> list[str]:
    return sorted(REGISTRY)


def _f(name: str, type_: str, align: str) -> FieldSpec:
    return FieldSpec(name=name, type=type_, align=align)


register(DocumentClass(name="invoice", tables=(
    TableSpec(name="line_item", fields=(
        _f("description", "description", "left"),
        _f("quantity", "quantity", "right"),
        _f("unit_price", "unit_price", "right"),
        _f("amount", "amount", "right"),
    )),
)))

register(DocumentClass(name="eob", tables=(
    TableSpec(name="claim_line", fields=(
        _f("service_date", "date", "left"),
        _f("code", "code", "left"),
        _f("description", "description", "left"),
        _f("amount_billed", "amount", "right"),
        _f("amount_owed", "amount", "right"),
    )),
)))

register(DocumentClass(name="receipt", tables=(
    TableSpec(name="line_item", fields=(
        _f("description", "description", "left"),
        _f("amount", "amount", "right"),
    )),
)))
```

- [ ] **Step 2: Verify**

Run (from `harness/`):
```bash
uv run python -c "from tablelab import classes as c; print(c.classes()); print([t.name for t in c.get('eob').tables], [f.name for f in c.get('eob').tables[0].fields])"
```
Expected: `['eob', 'invoice', 'receipt']` then `['claim_line'] ['service_date', 'code', 'description', 'amount_billed', 'amount_owed']`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/classes.py
git commit -m "refactor: built-in classes to one-table form (TableSpec)"
```

---

## Task 3: `layout.py` — iterate tables (byte-identical for one table)

**Files:** Modify `harness/src/tablelab/layout.py`

Keep `PlacedToken`, `_header_text`, `_emit`, and the imports unchanged. Replace **only** the `layout()` function.

- [ ] **Step 1: Replace `layout()`**

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Iterates dc.tables with a
    vertical cursor; for one table at instances=(1,1) this draws the same RNG in the
    same order and emits the same labels as the prior single-table builder. A header
    row (structure.header) is emitted atop each table instance; multi-word values split
    into per-word tokens (structure.multi_token); background tokens (structure.background)
    are scattered below everything."""
    L = dc.layout
    W, H = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    placed: list[PlacedToken] = []
    y = float(my)
    for table in dc.tables:
        C = len(table.fields)
        cell_w = (W - 2 * mx) / C
        lo, hi = table.instances
        instances = lo if lo == hi else rng.randint(lo, hi)
        for _inst in range(instances):
            rows = rng.randint(table.rows[0], table.rows[1])
            if header:
                for c in range(C):
                    f = table.fields[c]
                    x0 = mx + c * cell_w
                    cell = (x0, y, x0 + cell_w, y + L.row_h)
                    _emit(placed, _header_text(f.name), cell,
                          {"field": c, "header": True}, f.align, dc.render.font_size, multi)
                y += L.row_h
            for r in range(rows):
                for c in range(C):
                    f = table.fields[c]
                    value = sample(f.type, rng)
                    x0 = mx + c * cell_w
                    cell = (x0, y, x0 + cell_w, y + L.row_h)
                    _emit(placed, value, cell,
                          {"record": r, "field": c}, f.align, dc.render.font_size, multi)
                y += L.row_h
            y += L.table_gap
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

Note: `instances = lo if lo == hi else rng.randint(lo, hi)` draws **no** RNG when `instances=(1,1)`, and `rows = rng.randint(...)` is the first draw — exactly as the prior builder — so the single-table path is byte-identical. The `y += table_gap` after the only instance shifts nothing (no tokens placed after it except background, which is off in the golden).

- [ ] **Step 2: Verify the golden + all existing tests**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden byte-identical; multi-token / header / background still green). If golden FAILS, the RNG order changed — check the `instances` no-draw guard and that `rows` is still an unconditional `randint`. Do NOT edit the golden file.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "refactor: layout iterates dc.tables with a vertical cursor (byte-identical for one table)"
```

---

## Task 4: `cli.py` — `--rows` over tables; `inspect` reads tables

**Files:** Modify `harness/src/tablelab/cli.py`

- [ ] **Step 1: Replace `_build`**

```python
def _build(args):
    dc = classlib.get(args.cls)
    L = dc.layout
    if args.page:
        L = replace(L, page=(args.page[0], args.page[1]))
    tables = dc.tables
    if args.rows:
        tables = tuple(replace(t, rows=(args.rows[0], args.rows[1])) for t in tables)
    S = dc.structure
    if args.multi_token:
        S = replace(S, multi_token=True)
    if args.header:
        S = replace(S, header=True)
    if args.background:
        S = replace(S, background=args.background)
    if L is not dc.layout or tables is not dc.tables or S is not dc.structure:
        dc = fork(dc, layout=L, tables=tables, structure=S)
    out = Path(args.out)
    build_dataset(out.parent, out.name, dc, seed=args.seed, n=args.n)
    print(f"built {args.n} {args.cls} samples -> {out}")
```

- [ ] **Step 2: Replace `_inspect`**

```python
def _inspect(args):
    d = Path(args.datasets_dir) / args.id
    m, samples = read_dataset(d)
    spec = m.config.get("spec", {})
    tables = spec.get("tables", [])
    fields = [f["name"] for t in tables for f in t.get("fields", [])]
    page = spec.get("layout", {}).get("page")
    ntok = sum(len(s.tokens) for s in samples)
    print(f"id:       {m.dataset_id}")
    print(f"class:    {m.config.get('class', '?')}")
    print(f"task:     {m.task}")
    print(f"samples:  {m.count}")
    print(f"tokens:   {ntok} ({ntok / max(m.count, 1):.1f}/sample)")
    print(f"tables:   {[t.get('name') for t in tables]}")
    print(f"fields:   {fields}")
    print(f"page:     {page}")
```

- [ ] **Step 3: Smoke-test build + inspect + an override**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class eob --n 6 --out ../datasets/smoke-4a --rows 3 3
uv run python -m tablelab.cli inspect smoke-4a
```
Expected: `inspect` prints `tables: ['claim_line']`, the 5 EOB field names, `page: [1000, 1414]`, and `tokens: 90 (15.0/sample)` (3 rows × 5 fields × 6 samples).

- [ ] **Step 4: Clean up**

Run (from repo root):
```bash
rm -rf datasets/smoke-4a
```

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: CLI --rows overrides every table; inspect reads fields from tables"
```

---

## Task 5: Fix the one test that read `dc.fields`

**Files:** Modify `harness/tests/test_header.py`

- [ ] **Step 1: Update the field-count read**

In `test_header_row_emits_field_name_tokens_above_data`, change:

```python
    C = len(dc.fields)
```
to:
```python
    C = len(dc.tables[0].fields)
```

- [ ] **Step 2: Run the full suite**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_header.py
git commit -m "test: header test reads fields from tables[0] after spec generalization"
```

---

## Done criteria

- `uv run pytest -q` passes — golden byte-identical; multi-token / header / background green.
- `build`/`list`/`inspect` work; `inspect` shows `tables` + aggregated fields; `--rows` overrides tables.
- `DocumentClass` now exposes `tables` + `globals`; no code reads `dc.fields` or `LayoutSpec.rows`.

## Implementer notes

- **Byte-identical hinge:** `instances=(1,1)` must draw NO RNG (the `lo if lo == hi else randint` guard), and `rows` stays an unconditional `randint`, so the first draw is still the row count. If `tests/test_golden.py` fails, that's the cause — never edit the golden file.
- This is a pure refactor: no `region`, no `globals` placement yet (those are 4b/4c). `dc.globals` exists but is empty for all built-ins.
- Grep the package for any remaining `dc.fields` / `.layout.rows` / `LayoutSpec(rows=` usage and fix it (build.py reads `doc_class.layout.page` only, which is unchanged).
