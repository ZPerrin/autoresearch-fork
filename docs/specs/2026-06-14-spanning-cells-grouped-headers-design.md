# Spanning cells + grouped headers — design

- Status: **designed** (not yet implemented). Sixth structural-realism feature.
- Date: 2026-06-14
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md` (§ structural realism, item 6).
- Follows: `docs/specs/2026-06-14-realistic-spacing-jitter-design.md` (item 5).

## Goal

Add the last structural-realism knob before document-class breadth: a **cell that spans a
contiguous range of columns** (colspan). One primitive, two surfaces:

1. **Grouped headers** — a banner band of column-group labels above the existing leaf header row
   (e.g. on the EOB `claim_line`, "Patient Responsibility" over deductible/copay/coinsurance).
2. **Spanning data rows** — a row template whose cells can each cover several columns, covering both
   **section header rows** (a full-span label introducing a block of records) and **subtotal/total
   rows** (a label spanning the left columns + values under the right columns).

Both reduce to the same mechanism. Real EOBs confirm both shapes: the Highmark sample EOB shows a
"Member Responsibility" banner spanning the claim table and a `TOTALS` row (label on the left, values
aligned under the numeric columns); multi-claim/Medicare EOBs additionally group claim lines under a
provider/category section heading.

Gated so that **default off is byte-identical** to current output (the invoice golden guards it).

## Decisions

### Spec API (data model) — Approach A

All additions live in `tablelab.specs`; no new top-level container types beyond two small
dataclasses. Grouped-header membership rides on `FieldSpec`; span rows are declarative data attached
to `TableSpec`.

```python
@dataclass(frozen=True)
class FieldSpec:
    ...
    group: str | None = None   # contiguous fields sharing a group name form one banner cell

@dataclass(frozen=True)
class SpanCell:
    span: int = 1              # columns this cell covers
    text: str | None = None    # literal label (e.g. "TOTALS")
    type: str | None = None    # value sampler key (e.g. "amount", "category"); xor with text
    align: str = "left"

@dataclass(frozen=True)
class SpanRowSpec:
    cells: tuple[SpanCell, ...]   # spans must sum to len(table.fields)

@dataclass(frozen=True)
class TableSpec:
    ...
    section: SpanRowSpec | None = None   # emitted once before each instance's records
    totals:  SpanRowSpec | None = None   # emitted once after each instance's records
```

1. **Grouped headers are inferred from contiguous runs.** Consecutive fields with the same non-`None`
   `group` collapse into one banner cell spanning that column range. `group=None` columns get a blank
   banner slot (their leaf header sits directly beneath). A group is therefore always contiguous; a
   gap in the middle is simply two banners. This matches real banners and needs no new container.

2. **A span row is a sequence of colspan cells.** A `SpanCell` is a literal label (`text`), a sampled
   value (`type`, e.g. `amount`/`category`), or empty (neither). Position is implicit in the slot:
   `section` renders before an instance's records, `totals` after. No ordering field now — generalize
   to an interleaved list only if a class needs it (YAGNI).

3. **A new `category` sampler** in `tablelab.fields` (small vocab: "Office Visits", "Lab Services",
   "Radiology", "Pharmacy", …) backs section labels. Literal labels (`text=…`) draw no RNG.

### Layout emission + label schema

All emission is in `tablelab.layout.layout()`, reusing the existing `_emit()` helper (so
`structure.multi_token` splitting of multi-word labels comes for free). Per-instance vertical order:

```
[group banner band]      # if any field.group  (requires structure.header)
[leaf header row]        # existing structure.header
[section row]            # if table.section
 data rows …             # existing
[totals row]             # if table.totals
```

4. **Column edges already give spans.** A cell over fields `c0..c1` has rect
   `(edges[c0], y, edges[c1+1], y + row_h)` from the column edges layout already computes. A spanning
   cell is just one wider rect; the renderer (which groups tokens by cell rect) is **untouched**.

5. **Label keys** (open contract — new keys; the viewer's arbitrary-label detail panel from the
   reviewability milestone absorbs them). `reg` is the existing `{"region": k}` tag on multi-instance
   tables; `field: c0` anchors a spanning token to its first column; `span` records the inclusive
   column range so a model and the viewer can recover the grouping.

   | Token        | label |
   |--------------|-------|
   | group banner | `{"field": c0, "header": True, "group": name, "span": [c0, c1]}` |
   | section cell | `{**reg, "section": True, "field": c0, "span": [c0, c1]}` |
   | totals label | `{**reg, "subtotal": True, "header": True, "field": c0, "span": [c0, c1]}` |
   | totals value | `{**reg, "subtotal": True, "field": c}` |

   Data rows keep `{"record": r, "field": c}` unchanged. `header: True` on the banner / totals-label
   reuses the path the viewer already renders as a header.

6. **Byte-identical off-path (golden guard).** Every new block is gated on its spec being present: no
   field has `group`, `table.section is None`, `table.totals is None`. When all are absent, no
   banner/section/totals code runs, **no extra `sample()` calls happen**, and emission order is
   unchanged → invoice stays byte-identical. When present, RNG draw order is fixed and documented:
   section cells (top-to-bottom, left-to-right) → existing data grid → totals values left-to-right.
   Sampled spanning values honor `multi_token` via `_emit`.

### Capacity / fit planning

7. **New rows are fixed per instance** (independent of the sampled row count), so feasibility math
   stays simple. `_instance_height()` gains constant terms:

   ```python
   banner  = int(any(f.group for f in table.fields) and header)
   section = int(table.section is not None)
   totals  = int(table.totals is not None)
   # (header + banner + section + totals) * row_h + rows * row_h + gaps + instance_gap
   ```

   These flow through every use of `_instance_height` (minimum-shape, feasible-shape enumeration, the
   capacity error), so a page too short for the banner/section/totals rows fails up front with the
   existing `LayoutCapacityError` — no partial dataset. `_is_safe_legacy` already excludes anything
   with headers/globals/multi-instance, so the new path never touches the byte-identical fast path.

8. **Banners and span rows do not drive column widths.** `_content_column_widths` keeps sizing
   columns from leaf headers + data cells only; a banner sits over columns already sized for their
   data, and letting a wide banner label stretch columns would distort the table. If a banner label
   exceeds its span it is handled like any overflow (and `autoscale_font`, which measures leaf
   content, is unaffected). Accepted known limitation.

### Component touchpoints

9. **`tablelab.specs`** owns `FieldSpec.group`, `SpanCell`, `SpanRowSpec`, and the `TableSpec` slots.
10. **`tablelab.fields`** gains the `category` sampler.
11. **`tablelab.layout`** owns banner/section/totals emission, the capacity terms, and validation
    (in `_validate_layout`): each `SpanRowSpec`'s spans sum to exactly `len(fields)`; each `SpanCell`
    has `text` xor `type` (or neither); `group` set on any field requires `structure.header=True`.
12. **`tablelab.render`** — unchanged (wider rects via existing cell-rect grouping;
    `build._validate_boxes` already checks boxes stay in-page).
13. **Viewer** — overlay unchanged (wider boxes are data-driven; token detail already renders
    arbitrary label keys). One small `MetaPanel` addition: the "enabled structural features" readout
    gains *grouped headers* / *section rows* / *totals rows*, derived from the resolved spec.
14. **CLI — no new knobs.** Unlike `--header`/`--jitter` (generic bools), grouping and span rows are
    *content* (which columns group, what the totals row holds), so they live in the class definition
    alongside field widths/fill. `build --class eob` picks them up; `inspect` surfaces them via the
    resolved spec.

### `eob` recipe (the showcase)

Applied to `claim_line`'s ten columns (exact banner names/columns finalized in the plan):

- **Grouped headers** (current column order kept): `service_date`/`code`/`description` ungrouped →
  `amount_billed`/`allowed` = **"Charges"** → `deductible`/`copay`/`coinsurance` =
  **"Patient Responsibility"** → `plan_paid`/`amount_owed` = **"Plan & Balance"**.
- **Section row**: `section = SpanRowSpec((SpanCell(span=10, type="category"),))` — a sampled
  service-category heading before each instance's lines.
- **Totals row**: `totals = SpanRowSpec((SpanCell(span=3, text="TOTALS"),
  *seven SpanCell(span=1, type="amount", align="right")))` — `TOTALS` over the three service columns,
  an amount under each of the seven numeric columns (spans sum to 10). Totals values always populate
  (no sparsity).

## Verification

- **Golden (off):** `tests/test_golden.py` invoice byte-identical. Plus an RNG-identity check that a
  class with no `group`/`section`/`totals` produces tokens identical to before.
- **New unit tests:** banner spans the right column ranges; two non-adjacent same-name runs → two
  banners; geometry (banner › leaf header › section › data › totals, top to bottom); validation
  errors (spans ≠ `len(fields)`; `text` and `type` both set; `group` without `header`); capacity
  failure when a page fits data but not the added fixed rows (clear `LayoutCapacityError`);
  `multi_token` splits a multi-word banner label; totals value cells populate under each numeric
  column; section label drawn from the `category` vocab.
- **Smoke / viewer:** build an `eob-grouped` dataset; `inspect` shows the new features; viewer eyeball
  — banner band, section heading, and `TOTALS` row render with boxes in-page; token detail shows
  `group`/`section`/`subtotal`/`span` keys; `MetaPanel` features readout lists them.

## Out of scope

- True vertical row-span / stacked multi-line cells (the Highmark "Provider/Date/Type/Code" cell).
- Nested banners (>1 group level) — one band only.
- Banner labels driving column widths.
- *Consistent* totals — values are sampled, not real column sums.
- Visual styling (shading banner/total rows) — deferred `RenderSpec` seam.
- CLI toggles for grouping content — class-defined.

## Trajectory note

Sixth confirmation of the pattern: a spec knob (here on `FieldSpec`/`TableSpec`) + a layout-stage
change, with the renderer and the observables contract stable. Completes the ordered structural-
realism list (items 1–6); next is **document-class breadth**, then the deferred **M0 spatial model
loop** and the modality ladder.

## Sources

- Highmark — How to Read Your EOB:
  `https://www.pointpark.edu/studentlife/healthandstudentservices/studenthealthinsurance/media/highmark-how-to-read-your-eob.pdf`
- CMS sample EOB: `https://www.cms.gov/files/document/11819-sample-explanation-benefits-508.pdf`
- Patient Advocate Foundation — What an EOB looks like:
  `https://www.patientadvocate.org/explore-our-resources/interacting-with-your-insurer/what-does-an-eob-look-like/`
</content>
</invoke>
