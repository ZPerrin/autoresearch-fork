# Wrapped (multi-line) cells + table bbox metadata — design

- Status: **proposed**. Two structural additions requested before document-class breadth. Parent:
  `docs/specs/2026-06-13-design-and-roadmap.md`.
- Date: 2026-06-14
- Follows: `docs/specs/2026-06-14-spanning-cells-grouped-headers-design.md` (completed the ordered
  structural-realism list; this doc is a small pre-breadth pair, not a new ordered item).

## Goal

Two independent structural capabilities, both staying on the established seam (a spec knob + a
layout-stage change; renderer and observables contract stable):

1. **Wrapped (multi-line) cells.** A cell's value can wrap across several lines within its column,
   each word an individual token. Real documents do this constantly — a verbose description, or a
   human "doubling up" information in one cell (`"laboratory services with blood on 12-31-26"`).
2. **Table bbox metadata.** Record each table-instance's bounding box as per-sample structural
   metadata, joinable to the tokens it contains, so spatial features *relative to the table* can be
   derived later (or not).

Both default-off / additive-only: the invoice golden (per-token list) stays byte-identical.

## Framing: structure is not labeling

We are building a **structural** generator. A cell is a structural unit that holds (possibly
wrapped) tokens. **What is extractable from a cell, and how those tokens are labeled, is the
separate, deferred layer** — the contract's open "task labels" / deferred "annotation schema"
(`design-and-roadmap.md` § Task framing). A wrapped cell sits under one column header, yet a learned
extractor might later pull *two* values from it (a description and a service date), and we would
label it accordingly **only if** we choose to model that case.

Design consequence: the wrapped-cell primitive is **label-agnostic**. Today a cell's tokens inherit
the field they were generated from (`{record, field, seq}` — that is simply how generation works),
but nothing bakes in "one cell ⇒ exactly one field label." A future composite cell could host tokens
carrying distinct labels without re-architecting. **We build wrapping now; multi-field labeling of a
cell is allowed-for and deferred.**

---

## Feature 1 — Wrapped (multi-line) cells

Extends the existing `multi_token` path (per-word tokens sharing a cell + `seq`): when a value is too
wide for its column, it wraps onto additional lines instead of overflowing. Columns stay 1:1 with
fields, so grouped headers, span rows, and globals are untouched.

### Spec API (`FieldSpec`)

```python
@dataclass(frozen=True)
class FieldSpec:
    ...
    max_width: float | None = None   # cap on content-aware column width (px); wider values wrap. None = grow-to-fit (today)
    max_lines: int = 1               # upper bound on wrapped lines; used for capacity reservation
```

- `max_width` is the **config suggestion / ceiling** mirroring the column-width philosophy: the
  content-aware sizer still floors a column to its content, but no longer grows it past `max_width`;
  values exceeding the cap wrap. `None` (every existing field) = today's grow-to-fit, no wrap →
  byte-identical.
- `max_lines` bounds wrapping for capacity math (below). A value that would exceed `max_lines` is
  clamped (the last line is allowed to run; we never silently drop tokens — see Out of scope).
- A **verbose value sampler** (e.g. a longer `description`) is added to `tablelab.fields` so wrapping
  actually triggers in the `eob` showcase. Literal/short samplers are unchanged.

### Geometry — all in `tablelab.layout`, renderer untouched

Layout already measures text (`metrics.text_width`) for column sizing. For a wrappable cell it
greedily packs words to the capped column width and emits **each line as its own sub-rect**: the
column x-range, the line's y-slot. Tokens on a line share that rect with a within-line `seq`.

Because each line is just a left-to-right phrase in its own cell rect, `render.py`'s existing
cell-grouping draws it with **zero changes** (same trajectory as the previous six features).

- New layout knob `line_h: int` (font-derived default, e.g. `round(font_size * 1.3)`) sets intra-cell
  line spacing.
- Cell / row height = `row_h + (n_lines − 1) · line_h`, where `n_lines` is the max wrapped-line count
  across the row's cells.

### Per-row variable height + capacity

Data rows advance `y` by their **actual** wrapped height (variable, content-justified — the
row-height analog of content-aware column widths). Fixed rows (banner / leaf header / section /
totals) stay single-line.

Capacity planning must stay sound despite variable heights. **Decision to confirm at review:**

- **(A) Worst-case-reserve — recommended v1.** `_instance_height` reserves the worst case
  (`max_lines`) for every data row; actual rendering uses the real height (≤ reserved), so a document
  never overflows its planned budget. Contained change: only `_instance_height`'s per-data-row term
  changes (`row_h → row_h + (max_data_lines − 1)·line_h`, where `max_data_lines` is the largest
  `max_lines` among the table's fields). The intricate `_choose_shape` / `_iter_feasible_shapes`
  enumerator and the legacy fast path are otherwise untouched. Cost: conservative trailing whitespace
  when rows wrap less than worst case.
- **(B) Measure-then-pack — deferred.** Sample all candidate rows, measure real heights, then fit as
  many as the height budget allows. Truly content-driven row counts and tighter packing, but it
  inverts the sample/plan order and rewrites the capacity machinery. Documented as the future
  upgrade if (A)'s whitespace becomes a problem.

### Labels

Unchanged: `{record, field, seq}` (plus `region` when multi-instance). No per-line key — labeling is
independent of line structure (see Framing). The label dict stays open, so distinct per-token labels
within a cell remain expressible later without a schema change.

### `eob` recipe (showcase)

`claim_line.description` gains `max_width` (a cap narrow enough that the verbose sampler wraps) and
`max_lines = 2`. Other columns keep grow-to-fit. Result: a claim table whose description column wraps
to two lines on longer values, with variable data-row heights — visibly the Highmark stacked-cell
shape, while every token still carries the `description` field label.

---

## Feature 2 — Table bbox metadata

Store each table-instance's bounding box as per-sample structural metadata, joinable to tokens via
the `region` index they already carry, so "position relative to my table" can later feed token
embeddings (or be ignored).

### Contract (`tablelab.artifacts`)

```python
@dataclass
class Region:
    region: int                 # matches the {"region": k} label on the instance's tokens
    table: str                  # table name (e.g. "claim_line")
    bbox: tuple[float, float, float, float]   # normalized [0,1], (x0, y0, x1, y1)

@dataclass
class Sample:
    ...
    regions: list[Region] | None = None   # optional, additive
```

- **Geometry source = layout cell-rect extent**, not glyph union:
  `bbox = (left_edge, y_at_instance_start, right_edge, y_at_instance_end)`. Layout knows these
  exactly, so the bbox captures the table's *true* bounds — header/section/totals bands and
  sparse/empty cells the glyph union would miss.
- **Always-on**: pure metadata, no RNG, no change to tokens or images → the golden token-list is
  unaffected and every class gets regions for free.
- Additive + optional → **schema stays v2**; `write_dataset`/`read_dataset` round-trip it; readers
  (viewer `_sample_from_dict`) tolerate its absence.
- **Granularity: per table-instance only** for now. The `region` index is the join key (single-table
  single-instance classes get one region `0`). Globals / background regions are a trivial later
  extension, deferred.

### Plumbing

- `layout()` returns `(placed, regions)` instead of just `placed`. The two internal call sites
  (`build.build_dataset`, `tests/test_golden`) and any direct callers update to unpack; `render`
  still takes `placed`.
- Each instance's `(left_edge, y_start, right_edge, y_end)` is recorded in page px as layout advances
  through that instance; `build.py` normalizes to `[0,1]` (like tokens) and attaches to the `Sample`.

### Viewer

- Optional region-rect overlay (toggleable), drawn from `sample.regions`.
- `MetaPanel`: a small per-sample "regions" readout (table name + region index); `types.ts` gains the
  optional `regions` field on `Sample`.

---

## Verification

- **Golden (off):** invoice per-token list byte-identical (`tests/test_golden.py`) — no field sets
  `max_width`, so no wrap path runs; `regions` is Sample-level and outside the token list the golden
  compares.
- **Feature 1 unit tests:** a long value at a capped `max_width` wraps to the expected line count;
  each wrapped line is its own left-to-right group with correct `seq`; row height grows by
  `(n_lines − 1)·line_h`; capacity reserves worst-case (a page that fits 1-line rows but not
  `max_lines` rows fails up front with a clear `LayoutCapacityError`); tokens stay in-page
  (`build._validate_boxes`).
- **Feature 2 unit tests:** an instance's `regions` bbox encloses every token tagged with that
  `region`; bbox is normalized and in-page; `write`/`read_dataset` round-trips `regions`; a
  single-instance class yields exactly one region.
- **Smoke / viewer:** build an `eob-wrapped` dataset; `inspect` shows the wrapping fields; viewer
  eyeball — description wraps to two lines with variable row heights, region overlay encloses each
  claim instance, boxes in-page.

## Out of scope

- **Multi-field composite cells / per-line labels** — allowed-for by the open label dict, not built
  now.
- **Measure-then-pack** row packing (Feature 1 ships with worst-case-reserve).
- **Wrapping header / section / totals rows** — single-line for now.
- **Globals / background region bboxes** — table instances only.
- **Visual styling** (cell ruling, shading) — deferred `RenderSpec` seam.

## Trajectory note

Two more confirmations of the pattern: a spec knob (`FieldSpec.max_width`/`max_lines`) + a
layout-stage change with the renderer stable (Feature 1), and the first deliberate, additive
extension of the Sample contract for derived-feature provisioning (Feature 2). Both keep the
observables (`bbox + text`) locked and the label layer open. Next: **document-class breadth**.

## Sources

- Highmark — How to Read Your EOB (stacked Provider/Date/Type/Code cell):
  `https://www.pointpark.edu/studentlife/healthandstudentservices/studenthealthinsurance/media/highmark-how-to-read-your-eob.pdf`
