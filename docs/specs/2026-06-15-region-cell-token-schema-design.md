# Region / Cell / Token schema — nomenclature + structure cleanup — design

- Status: **shipped** — the v4 contract ([artifacts.py](../../harness/src/tablelab/artifacts.py));
  kept as the contract's design reference (incl. the deferred non-tabular generalization, below).
  Canonical *why*: [charter.md](../architecture/charter.md); map: [index.md](../architecture/index.md).
- Date: 2026-06-15
- Superseded follow-on: the labels layer landed as **materialized targets**, not `derive_*` projections
  — see the [target-schema spec](2026-06-20-target-schema-design.md). This spec fixed the
  *representation* first so that layer had a clean foundation.

## Motivation

The contract grew semantically-loaded names for what are really positional indices, conflating two
layers that the labeling milestone needs kept apart:

- `region: int` is a table-instance ordinal, but the word implies a generic area; the `Region`
  struct already carries the table name and a bbox, so "region" was doing the job of "which
  instance."
- `record`/`field` are row/column **indices** (`r`/`c`), but the names imply semantic identity (a
  logical record; a named attribute). `field: 3` does not say `amount_billed` — you must join
  `TableSpec.fields[3]`.

This matters specifically because **semantic field ≠ column index in general** (a wrapped/composite
cell can host tokens with distinct field labels — see the wrapped-cells design). The moment that is
true you need `column_index` (structural position, 1:1 with layout) and `field` (semantic meaning) to
be *different keys*. The current schema spent the word `field` on the index.

The fix is a clean three-layer split, named honestly, aligned to Textract (the real input):

| layer | unit | keys |
|---|---|---|
| **observables** (locked) | `Token` (word) | `bbox`, `text` |
| **structural truth** (derivable-in-principle; what Textract `TABLES` gives) | `Cell`, `Region` | `region_index`, `row_index`, `column_index`, `span`, `bbox` |
| **semantic truth** (free for synthetic; the extraction target) | `Cell` | `field` (template slot), `role` |

## Model

```
Region { type: "table" | "form" | "footer" | …,  name: str | None,  index: int,  bbox }
Cell   { region_index: int, row_index: int, column_index: int, span: [int, int],
         bbox, role: "header"|"group_header"|"data"|"section"|"summary"|"key"|"value",
         field: str | None, token_ids: list[int] }
Token  { x0, y0, x1, y1, text }
```

Per-sample the document is `regions` + `cells` + `tokens`:

- **`Region`** — a typed area (≈ Textract `LAYOUT_*` / `TABLE`). `type` is the coarse layout class;
  `name` is the specific definition (the table name `"claim_line"`; `"globals"` for the form) so two
  different table *types* sharing `type:"table"` stay distinguishable. `index` is the instance
  ordinal **scoped per (type, name)** — two `claim_line` instances → index 0 and 1; a separate
  `payment_summary` table → its own index 0. Geometry is the explicit `bbox` (no struct is named
  "region" as a stand-in for an area — the area *is* the bbox). A `Cell` joins to its region by
  `region_index`, the **flat position in `Sample.regions`** (unambiguous), while `Region.index` is
  the semantic instance ordinal.
- **`Cell`** — the unit that owns structure and meaning. `row_index`/`column_index` are positional
  (≈ Textract `CELL.RowIndex`/`ColumnIndex`); `span` is `[colspan, rowspan]` (≈ `ColumnSpan`/
  `RowSpan`); `role` is the cell's structural role (≈ Textract `CELL.EntityType`); `field` is the
  template's named extraction slot (e.g. `service_date`, `copay`, `amount_owed`). A cell may be
  **empty** (sparse/`fill < 1`): it still has a `bbox` and a `field`, with `token_ids = []` — a thing
  the word-only model could not express. `token_ids` lists the cell's words in reading order
  (replaces the old per-token `seq`). A **spanning** cell (`group_header` / `section` / `summary`)
  anchors at its top-left covered cell: `row_index`/`column_index` are the first covered row/column
  and `span = [colspan, rowspan]` gives the extent (so a full-width section row is
  `column_index = 0`, `span = [n_columns, 1]`).
- **`Token`** — a pure observable: bbox + text. No `label`, no `region`/`record`/`field`, no `seq`.
  Background/noise words live in `tokens` and are referenced by **no** cell.

### Textract correspondence

| ours | Textract (`TABLES` / `LAYOUT` / `FORMS`) |
|---|---|
| `Region{type:"table"}` | `TABLE` block / `LAYOUT_TABLE` |
| `Region{type:"form"}` | `LAYOUT_KEY_VALUE` / `KEY_VALUE_SET` |
| `Cell.row_index` / `.column_index` | `CELL.RowIndex` / `ColumnIndex` (note: Textract is 1-based; we stay 0-based) |
| `Cell.span` | `CELL.ColumnSpan` / `RowSpan` |
| `Cell.role` | `CELL.EntityType` (`COLUMN_HEADER`, `TABLE_SECTION_TITLE`, `TABLE_SUMMARY`) |
| `Cell.token_ids` | `CELL` → `WORD` child relationships |
| `Token` | `WORD` |

(Enum spellings verified against current Textract docs before any are hardcoded.)

## From → to (current label keys)

| current (token `label`) | new |
|---|---|
| `Region{region, table, bbox}` struct | `Region{type, name, index, bbox}` (table name kept as `name`) |
| `region: int` (token key) | dropped from token → `Cell.region_index` (flat pointer into `Sample.regions`) |
| `record: int` | `Cell.row_index` |
| `field: int` (data/header) | `Cell.column_index` |
| `seq: int` | dropped → order of `Cell.token_ids` |
| `header: True` (leaf) | `Cell.role = "header"` |
| `group` + `header` + `span` (banner) | `Cell.role = "group_header"`, `Cell.span`; group name is the banner cell's token text |
| (implicit data cell) | `Cell.role = "data"` |
| `section: True` | `Cell.role = "section"` |
| `subtotal: True` | `Cell.role = "summary"` |
| `field` name (semantic) | `Cell.field` (populated from `FieldSpec.name`) |
| `global: name` (label/value) | `form` region: `Cell.role ∈ {key, value}`, `Cell.field = name` |
| `null` (background) | `Token` referenced by no cell |

`field`'s **value type** (date/amount/id) is *not* a cell label — it is a property of the
`DocumentClass` field definition, joined via `Cell.field`. We never classify value types.

## Globals and background (coherent-contract consequence)

A half-migrated sample (tables in the new shape, globals/background in the old) is worse than a
complete one, so this pass places **every** token in the new model:

- **Tables** → `table` region + grid cells.
- **Globals** → one `form` region; each global field becomes a key cell (`role:"key"`, the
  `"Member Name:"` label text) and a value cell (`role:"value"`, the value), both carrying
  `field = <slot>`; `row_index` = pair index, `column_index` = 0 (key) / 1 (value). This keeps
  member/provider — central to the end-state — first-class now.
- **Background** → noise `Token`s referenced by no cell. A `footer` *region* (a bbox around them) is
  **deferred**; background needs no cell, so nothing is lost.

So `type` values emitted now are `table` and `form`; `footer` and other `LAYOUT_*` types are
provisioned but unused.

## Contract changes

- `SCHEMA_VERSION` `2 → 3`. The **observables are unchanged** (token bbox + text, sample image) — the
  contract seam held; only the open label layer restructured and `cells`/typed-`regions` were added.
  Worth stating plainly: the lock did its job.
- `artifacts.py`: `Token` loses `label`/`pred`; new `Cell` dataclass; `Region` gains `type`, swaps
  `region`/`table` for `index`; `Sample` gains `cells`. `write`/`read_dataset` + `write`/`read_run`
  round-trip the new shape; `_sample_from_dict` parses `cells`.
- `layout.py`: emit `(tokens, cells, regions)`. The placement math is unchanged; what changes is the
  *bookkeeping* — each placed cell records `region_index/row_index/column_index/span/role/field/bbox`
  and the indices of the tokens it owns. `PlacedToken.label` is removed.
- `build.py`: normalize token + cell + region bboxes to `[0,1]`; assemble the new `Sample`.
- `viewer`: `types.ts` gains `Cell`, updates `Region`; overlay can draw region areas and cell rects
  and tint by `role`; `MetaPanel` reads cells.
- **Golden**: regenerated deliberately (this changes the sample shape — it is a contract change, not
  an additive feature). The new golden asserts the full `regions/cells/tokens` for the invoice seed.

## Out of scope (next spec — labels / task projections)

- `derive_*` projection functions: `derive_token_labels`, `derive_nlq_pairs`, `derive_records`.
- The **record / global rollup** (document-class-specific `field → value` records + member/provider
  association). The schema above makes it near-trivial: cells already carry
  `region_index`/`row_index`/`field`, and globals are a `form` region.
- `pred` / model-output representation (designed with the model loop).
- `footer` region bbox; other `LAYOUT_*` area types; vision-era layout detection.

## Known limitation — `Cell` is the *tabular* element (generalization deferred)

`Cell` carries a tabular bias that we should name now so it doesn't calcify. The **token and region
layers are document-agnostic**; only three `Cell` fields are grid-specific:

```
Cell { region_index, bbox, role, field, token_ids,   ← general (any document)
       row_index, column_index, span }                ← grid-only (tables)
```

A cell-*only* model would force non-grid documents into a grid they don't have. Concretely, for the
**document-class breadth** milestone:

- **key-value form** (W-2, application — on the breadth list): a key and its value are two elements
  sharing a `field` (`role=key`/`role=value`). They need `role` + `field` but **not** row/col — the
  current `form`-as-grid representation (key at `column_index=0`, value at `1`) is a **deliberate
  compromise to revisit when the real form class lands**, not a precedent to extend.
- **letter / contract / narrative**: reading-order text blocks (`role=title`/`paragraph`/`list_item`)
  need an **`order`**, not row/col.
- **figure / logo / signature / stamp**: a typed bbox, possibly with no tokens — no grid at all.

This mirrors Textract, which never forces everything into cells: `WORD` groups into `CELL` (grid)
*or* `KEY_VALUE_SET` (form) *or* `LAYOUT_TEXT`/`LAYOUT_TITLE`/`LAYOUT_LIST`/`LAYOUT_FIGURE` (prose),
keyed by what the content is. Our typed `Region` already provides that seam.

**Generalization path (deferred; let the key-value-form spec drive it):** either (A) add sibling
element types (Textract-style: `Cell` for tables, a key-value element for forms, a block/line for
prose), or (B) — leaner, preferred — keep one annotation unit but make `row_index`/`column_index`/
`span` **optional** (present only for grid roles), add an optional `order` for sequential content,
and rename `Sample.cells` to a neutral container (`elements`/`segments`). Tables fill the grid
fields; forms fill `role`+`field`; prose fills `order`; figures fill neither. The token + region
layers are unchanged either way. We design this with the first concrete non-tabular class in hand
rather than speculatively.

## Verification

- **Round-trip**: `write` then `read_dataset`/`read_run` reproduces `regions`/`cells`/`tokens`
  exactly; `schema_version == 3` enforced.
- **Structural invariants**: every non-background token is referenced by exactly one cell; each
  cell's `bbox` encloses its tokens; an instance's region `bbox` encloses its cells; `row_index`/
  `column_index` are contiguous and within bounds; empty cells have `token_ids == []` and a `field`.
- **Semantic**: every table data/header cell has a `field` matching the originating `FieldSpec.name`;
  globals appear as key/value cell pairs under a `form` region.
- **Golden**: regenerated invoice sample matches the committed fixture byte-for-byte on re-run.
- **Viewer smoke**: build an `eob` set; region areas, cell rects, and role tints render; empty cells
  show; boxes in-page.

## Sources

- AWS Textract — `AnalyzeDocument` block types (`TABLE`/`CELL`/`WORD`, `CELL.EntityType`,
  `LAYOUT_*`, `KEY_VALUE_SET`). Exact enum spellings to be confirmed against current docs at
  implementation time.
