# Realistic spacing + jitter - design

- Status: **proposed**
- Date: 2026-06-14
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md`
- Follows: `docs/specs/2026-06-14-synthetic-reviewability-design.md`

## Goal

Make composed documents *look* like real forms by replacing the rigid uniform grid with
configurable, expressive spacing, plus per-axis jitter for modeling research. The output must stay
page-valid through the existing capacity planner; the contract (`schema_version = 2`) is untouched.

This is the **spacing-realism** slice of the jitter/irregular-structure milestone. Spanning/merged
cells and grouped multi-level headers remain a separate, later milestone.

## Findings that motivate the work

Our current `layout.py` is a uniform grid: every row is exactly `row_h` tall, every column is
`(W - 2*margin) / C` (**equal widths**), globals are a single 35%/65% label:value stack, and one
`table_gap` covers every gap. Four openly available EOBs (CMS, Independent Health, Medica, Anthem)
share a different shape:

1. **Non-uniform column widths** - date columns medium, description wide, code narrow, money columns
   narrow and right-aligned hard against the column edge. This is the single biggest "synthetic" tell.
2. **Multi-pair global bands** - member/provider/claim fields are several label:value pairs across a
   row, not one tall stack.
3. **Variable vertical rhythm** - section banners, summary rows, and uneven gaps between blocks.
4. **Sub-grid jitter** - because these are software-generated they *are* on a grid, but with small
   per-row/per-column variation. True pixel jitter is the smallest of the four effects.

So realism is ~80% deterministic structural spacing and ~20% random jitter. The design treats them
as two layers: deterministic knobs that the planner accounts for exactly, and bounded jitter that
rides on top without changing any section's total extent.

## Scope

In scope: non-uniform column widths, configurable vertical spacing, multi-pair globals, and per-axis
jitter. Everything stays a flat grid of single-cell tokens. Out of scope: spanning/merged cells,
grouped multi-level headers, totals/summary rows, visual realism (fonts/rules/scan noise/skew), and
arbitrary free-space packing.

Every knob in this design hangs off the `DocumentClass` (its `LayoutSpec`, its tables' `FieldSpec`
weights, and a class-level `JitterSpec`), so configuration is **per-class**. The intended workflow is
to iterate a class's spacing/jitter profile in the viewer until its output looks right, then keep
that class definition as a repeatable recipe: the deterministic knobs hold the look constant while
jitter plus feasible-shape sampling supply controlled per-document variance.

## Non-uniform column widths (content floor + weighted slack)

Equal `cell_w = usable / C` is content-blind: a narrow column (or a long header) overflows into its
neighbor. Hand-tuned per-field weights only paper over this. The realistic model sizes each column to
its **content** first, then uses weights to share whatever space is left over.

`FieldSpec` gains an optional `width: float | None` weight, and the field **type** registry carries a
default weight (e.g. `date` ~2, `code` ~1, `description` ~4, `amount` ~1.5). Column widths are then
computed as:

1. **Content floor.** For each column, measure the widest of its header label (when headers are on)
   and this document's sampled values, plus padding. That is the column's minimum width — text in
   that column cannot overflow its cell.
2. **Weighted slack.** Give every column its content floor, then distribute the remaining usable
   width across columns in proportion to their weights (so `description` still reads roomy). The
   widths sum to exactly the usable width by construction.
3. **Degenerate case.** If the content floors already exceed the usable width, scale all columns down
   proportionally (a rare last resort).

Because values are random per document, the layout pre-samples a table instance's value grid (in the
existing row-major order, so the RNG stream is unchanged) before sizing columns. Measuring text
requires the render font, so a small `metrics` helper estimates text width from that font and
`layout` calls it — keeping placement logic itself Pillow-light.

**Legacy/explicit path.** When *every* field in a table carries an explicit `width`, the table uses
pure weight-normalized division and skips the content floor. This is the byte-identical golden guard:
the invoice class pins all fields to `width = 1.0`, yielding equal columns exactly as before. Classes
that leave `width` unset (e.g. `eob`) get content-aware sizing for free, with type-default weights
governing only how slack is shared.

## Vertical spacing knobs (`LayoutSpec`)

- `row_h` *(existing)* - row content height.
- `row_gap` *(new)* - vertical gap between consecutive data rows within a table instance.
- `instance_gap` - gap between stacked table instances. This is today's `table_gap` renamed for what
  it does; the old `table_gap` key remains readable for back-compat and existing manifests.
- `section_gap` - gap between major sections (globals -> tables -> background).

Defaults are chosen so the existing golden invoice fixture stays byte-identical: `row_gap = 0`, and
`instance_gap`/`section_gap` resolve to the current single `table_gap` behavior. No new RNG draws on
the legacy path.

## Multi-pair globals

`LayoutSpec.globals_per_row` (default `1` = today's single label:value stack, legacy unchanged).
When `> 1`, that many label:value pairs are packed across one row by splitting the usable width into
equal pair-cells; within each pair-cell the existing label/value split applies. This reproduces the
member/provider/claim bands seen in the reference EOBs. Capacity accounts for the reduced number of
global *rows* this produces.

## Jitter (`JitterSpec`, per-axis)

A small struct on the document class, every axis defaulting to `0` (off). Each axis is independent
so a dataset can isolate one nuisance variable for modeling ablations.

- `row_h` - per-row height variance, **borrowed zero-sum** against the `row_gap`/`section_gap`
  budget so the section's total height never grows. Its magnitude is bounded by the available gap
  budget; with zero gaps there is no vertical room and this axis is effectively a no-op.
- `col_w` - per-column width variance, **zero-sum across the row**: when one column widens, a
  neighbor narrows by the same amount, so the row still spans exactly the usable width. The magnitude
  is a fraction of the **local column width** (not the full page), so `0.2` means roughly ±20% of a
  column; keep it modest so a jittered column does not shrink below its content.
- `offset` - per-token x/y wobble, **bounded inside the cell's interior padding** so the box never
  crosses its cell edge.
- `baseline` - small vertical text-baseline wobble, also bounded inside the cell.

With all axes `0`, no RNG is drawn and the legacy path is byte-identical. Jitter is applied
deterministically from the same per-document RNG stream after deterministic placement, so a dataset
is reproducible from its seed.

## Capacity integration

This is the load-bearing requirement: output must stay inside the page, working cohesively with the
page-valid composition shipped in the synthetic-reviewability milestone.

- Deterministic knobs (vertical gaps, multi-pair globals) become exact terms in the existing planner:
  `_fixed_height`, `_instance_height`, `_shape_height`, and the feasible-shape enumeration in
  `_iter_feasible_shapes` / `_iter_table_shapes`. Capacity math changes; sampling stays the same.
- Jitter is bounded and zero-sum (or in-cell), so it consumes only already-reserved slack and the
  planner does not need a separate headroom reservation.
- `build.py`'s normalized-coordinate `[0, 1]` validator remains the non-negotiable backstop; a
  violation is still a generator error, not a clamp.

The capacity error path is unchanged in spirit: when the minimum structure plus the new gaps cannot
fit, generation fails before writing a partial dataset, and the error reports the contributing terms.

## Component boundaries

- `tablelab.specs` - owns `JitterSpec`, the new `LayoutSpec` fields, and field-type default weights.
- `tablelab.fields` - owns `FieldSpec.width`.
- `tablelab.layout` - owns weight-normalized columns, vertical-gap accounting, multi-pair globals,
  and bounded jitter application. If jitter math would obscure placement, it may live in a small
  helper module (`tablelab.jitter`) with placement calling into it.
- `tablelab.build` - unchanged `[0, 1]` guard.
- Viewer `MetaPanel` - surfaces the resolved spacing and jitter configuration (read-only) so a
  dataset's spacing/jitter knobs are visible during review.

## Verification

- The existing golden invoice fixture remains byte-identical (jitter off, gaps at legacy defaults,
  `globals_per_row = 1`).
- Weight-normalized column widths sum to the usable width; per-field overrides take effect.
- Across a jitter sweep (each axis at its maximum, alone and combined) every cell and serialized box
  stays within `[0, 1]`; the zero-sum/in-cell invariants are checked directly.
- Multi-pair globals place the requested pairs per row without overlap and account correctly for
  capacity.
- Capacity still fails cleanly when minimum structure plus the new gaps cannot fit, with a clear
  error.
- An `eob` dataset regenerated with realistic type-default widths, multi-pair globals, and mild
  jitter renders coherently in the viewer and is visibly less grid-like than the current output.

## Out of scope

- Spanning/merged cells and grouped multi-level headers.
- Totals/summary rows.
- Visual realism: fonts, rules, shading, scan noise, skew.
- Arbitrary free-space packing or semantic page-region generation.

## Roadmap after this milestone

1. Spanning / merged cells and grouped headers.
2. Document-class breadth.
3. M0 spatial model loop, then the modality ladder (M0 -> M3), using per-axis jitter as an
   ablation instrument.
