# Multiple tables + global fields — design

- Status: **shipped** (merged to `master` as sub-steps 4a/4b/4c; fourth structural-realism feature — the EOB shape). Plans: `docs/plans/2026-06-13-multi-table-4a-generalize.md`, `…-4b-instances-region.md`, `…-4c-globals-eob.md`.
- Date: 2026-06-13
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md` (§ structural realism). Follows
  `2026-06-13-background-tokens-design.md`.

## Goal

Reach the **EOB shape**: a document with **global/singleton fields** (member, provider) plus **one or
more table instances** of repeated records (claim lines). This is the feature that mirrors the real
extraction problem, so we **generalize the core spec model** rather than bolt on a knob: a
`DocumentClass` becomes a set of **table definitions** + **global fields**, and a data token's label
gains a **`region`** (which table instance).

Because this is the biggest structural change since the backbone, it ships in **three sub-steps**,
each its own plan + branch + review, with the golden test holding byte-identical through the refactor.

## Generalized spec model

```python
@dataclass(frozen=True)
class TableSpec:
    name: str
    fields: tuple[FieldSpec, ...]
    rows: tuple[int, int] = (2, 6)        # record-count range for this table
    instances: tuple[int, int] = (1, 1)   # how many instances of this table appear

@dataclass(frozen=True)
class DocumentClass:
    name: str
    tables: tuple[TableSpec, ...]
    globals: tuple[FieldSpec, ...] = ()
    layout: LayoutSpec = LayoutSpec()
    structure: StructureSpec = StructureSpec()
    render: RenderSpec = RenderSpec()
```

- `rows` **moves** from `LayoutSpec` to `TableSpec` (it is a per-table property). `LayoutSpec` keeps
  `page`, `margin`, `row_h`, `pad`, and gains `table_gap` (vertical space between stacked tables).
- The three built-ins become one-table classes (`tables=(TableSpec(name, fields, rows=(2,6)),)`,
  `globals=()`), so their output is unchanged.

## Label schema (additions)

- **Data token:** `{"region": g, "record": r, "field": c}` — `region` is the 0-based table-instance
  index across the document. To keep the refactor byte-identical, `region` is included **iff the
  class can have more than one table instance** (`sum of max(instances) over tables > 1` or
  `len(tables) > 1`); single-table single-instance classes keep `{"record": r, "field": c}`.
- **Global token:** `{"global": name}` (e.g. `{"global": "member_name"}`), `+ "seq"` when multi-token.
- Header tokens within a table instance also carry `region` under the same rule.

## Sub-steps

### 4a — Generalize to tables (byte-identical refactor)

Introduce `TableSpec`; `DocumentClass.tables` / `globals=()`; move `rows` to `TableSpec`; layout
iterates `dc.tables` (single table, single instance, **no `region`, no globals**). Migrate the three
built-ins. CLI `--rows` overrides every table's `rows`. **Golden unchanged** (label + geometry
identical). No new user-facing behavior — this unlocks 4b/4c.

### 4b — Multiple instances + `region`

`TableSpec.instances`; layout draws `randint(instances)` copies of a table, stacked vertically with
`LayoutSpec.table_gap`; `region` increments per instance across the document and is added to data (and
header) labels when the class is multi-instance. A demo path (e.g. CLI `--instances` to override, or a
multi-instance class variant). Tests: region present and contiguous, instances stacked and disjoint.

### 4c — Global/singleton fields + the EOB class

`DocumentClass.globals`; layout places globals at the top as key-value pairs — a label token
(field-name, header-style) and a value token labeled `{"global": name}`. Then author the real **EOB
`DocumentClass`**: globals (member name/id, provider, claim number) + a `claim_line` table
(`service_date`, `code`, `description`, `amount_billed`, `amount_owed`) with `rows=(2,5)`,
`instances=(1,2)` (chosen to stay on the default page; many-instance overflow is deferred).
Tests: globals present at top with correct labels; EOB class builds with globals + multiple claim
instances.

## Determinism / byte-identical

Each sub-step keeps `sample()` one-call-per-cell and adds RNG only on new paths (extra instances,
globals). 4a is a pure refactor: the single-table/instance path draws the same RNG in the same order
and emits the same labels, so the golden test passes unchanged. 4b/4c add behavior only when the
class declares instances/globals.

## Out of scope (this feature)

- Spanning/merged cells and jitter (later features).
- Per-table distinct page placement beyond vertical stacking; visual realism (deferred `RenderSpec`).
- A general config/YAML for classes (Python registry stays the source of truth).

## Trajectory note

This is the structural payoff: after it, the toolkit can express the real end-state shape (globals +
repeated-record tables against a class-defined schema). Remaining structural realism afterward:
**jitter/irregular** rows & columns, then **spanning cells**.
