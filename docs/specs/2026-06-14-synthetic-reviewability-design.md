# Synthetic reviewability - design

- Status: **design approved; awaiting written-spec review** (implementation plan not started)
- Date: 2026-06-14
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md`
- Follows: `docs/specs/2026-06-13-multi-table-globals-design.md`

## Goal

Pause before adding jitter and make generated documents trustworthy and easy to inspect. The
generator must emit page-valid, class-coherent documents, and the viewer must show the complete
page with practical zoom/pan controls and schema-aware metadata.

This milestone consolidates the structural features already shipped - multi-token cells, headers,
background tokens, tables/instances/regions, and globals - into a reliable review surface. Jitter,
irregular sizing, and spanning cells remain the next structural-realism work after this milestone.

## Findings that motivate the work

Reviewing `datasets/eob-full` exposed three distinct problems:

1. Generic background vocabulary includes terms such as `RECEIPT`, `INVOICE`, and `Total`, making
   an EOB appear to contain data from another document class even though its labeled table fields
   are correct.
2. Background tokens fall back to random placement across the full page when no footer band
   remains, so they can overlap structured content.
3. `--instances 1 3` can produce more rows than fit on the fixed page. The generator serializes
   normalized coordinates greater than `1.0`, while the viewer's width-driven, clipped canvas hides
   the bottom of the document.

The in-flight viewer change that removes `record.field` text from the SVG overlay is part of this
milestone. Labels belong in token detail, not on top of source text.

## Generator validity

### Fit before sampling

Layout computes vertical capacity before choosing table-instance and row counts. Capacity includes:

- top and bottom margins;
- global-field rows and their following gap;
- optional header rows per table instance;
- table row heights;
- gaps between table instances; and
- space reserved for background content.

The layout samples only combinations inside the class/CLI ranges that fit the page. Randomness is
preserved among feasible choices; the generator must not silently shrink below a requested minimum.

If the minimum requested structure cannot fit, generation fails before writing a partial dataset.
The error reports the page capacity and the minimum requested globals, instances, rows, headers,
gaps, and background reservation so the user can adjust the class, page, or overrides.

Every emitted cell and rendered token box must stay inside the page. Dataset construction validates
that normalized coordinates remain in `[0, 1]` and treats a violation as a generator error.

### Class-aware background content

Background/non-answer text remains `label = null`, but its content is selected from the active
document class rather than one global invoice/receipt-heavy pool. Each registered class defines a
small vocabulary of plausible surrounding text. The EOB pool includes items such as patient
responsibility, plan-paid, claim/reference, page, notice, and explanatory boilerplate; it excludes
receipt/invoice titles.

Document classes may share a neutral fallback pool for generic page markers, but cross-class terms
must be explicit rather than accidental.

### Reserved background regions

Background tokens are placed only in free regions reserved during capacity calculation. The first
implementation uses a simple block below the structured content; it does not attempt arbitrary
packing around tables. Tokens receive non-overlapping rows or slots within that block and never
overlap globals, headers, table cells, or one another.

When the requested background count cannot fit alongside the minimum structured content,
generation fails through the same capacity error. There is no full-page scatter fallback.

### Compatibility

The no-background, single-table default path remains byte-identical so the existing invoice golden
fixture continues to guard historical output. New capacity logic must not consume additional RNG
draws on that path. Existing manifests remain readable; resolved new background configuration is
recorded in newly built manifests.

## Viewer review surface

### Complete-page rendering

The viewer defaults to **Fit page**: the entire page is visible inside the available left pane with
its aspect ratio preserved. It must never crop the document merely because the pane is shorter than
the width-derived page height.

Image and token SVG remain in one document canvas and share exactly one viewport transform. Token
coordinates stay in document space, so bounding boxes cannot drift relative to the image during
zoom or pan.

### Zoom and pan

The document canvas supports lightweight infinite-canvas-style navigation:

- wheel over the document zooms directly, centered on the cursor;
- click-drag pans when the document is larger than its fitted viewport;
- double-click returns to Fit page;
- compact `-`, percentage, `+`, and `Fit` controls provide visible alternatives;
- zoom is bounded to `25%-400%`; and
- changing samples or sources resets to Fit page.

Panning is constrained enough that the page cannot be lost completely outside the viewport. Token
selection remains a click; drag movement beyond a small threshold is treated as pan rather than a
token click.

### Controls help

An IDE-style help control near the viewer toolbar opens a compact popover listing mouse controls and
hotkeys. At minimum it documents wheel zoom, drag pan, double-click/Fit reset, zoom in/out, previous
sample, and next sample. The popover is dismissible with `Escape` or a click outside it.

Initial shortcuts:

- `+` / `=`: zoom in;
- `-`: zoom out;
- `0`: Fit page;
- `[` / `ArrowLeft`: previous sample; and
- `]` / `ArrowRight`: next sample.

Shortcuts apply while the viewer has focus and do not intercept typing in form controls.

### Schema-aware metadata

Dataset metadata reads the resolved `manifest.config.spec` rather than relying on legacy flat
`config.fields`. It shows the document class, global fields, table names and fields, instance/row
ranges, page dimensions, and enabled structural features.

Selected-token detail renders arbitrary label keys rather than assuming only `record` and `field`.
Current keys include `global`, `region`, `record`, `field`, `header`, and `seq`. A null label is shown
as background/non-answer. Prediction comparison remains task-aware; until generalized prediction
tasks exist, `grid_record_field` compares record and field while retaining all raw prediction keys
for inspection.

No label identifiers are drawn over the document text. The overlay contains selectable bounding
boxes only.

## Component boundaries

- `tablelab.specs` owns class-level background vocabulary/configuration.
- `tablelab.fields` samples values from the selected class-aware pool.
- `tablelab.layout` owns capacity planning, feasible structure sampling, and reserved placement.
- `tablelab.build` enforces the final normalized-coordinate invariant before serialization.
- `DocumentViewer` owns document viewport state and interactions.
- A small viewer helper/component may own transform math and the controls popover if keeping those
  concerns in `DocumentViewer.tsx` would obscure token rendering.
- `MetaPanel` owns resolved-spec and arbitrary-label presentation.

## Verification

Generator checks cover:

- feasible instance/row sampling stays within the declared ranges;
- minimum-impossible configurations fail before dataset output is completed;
- all cells and serialized boxes remain within page bounds;
- EOB background vocabulary contains no receipt/invoice-specific terms;
- background tokens do not overlap structured cells or one another;
- composed EOB generation with headers, multi-token cells, background, and up to three requested
  instances either fits by feasible sampling or fails clearly; and
- the existing golden fixture remains byte-identical.

Viewer verification covers:

- TypeScript/Vite production build;
- the complete page is visible in Fit mode at representative pane sizes;
- wheel zoom remains centered near the pointer and image/boxes stay aligned;
- drag pan, double-click reset, toolbar controls, shortcuts, and help popover work;
- sample/source changes reset the viewport;
- generalized labels and resolved document structure are visible in metadata; and
- no record/field text is rendered over document tokens.

Browser verification uses `eob-full` plus a freshly generated valid EOB dataset after the generator
changes. The old dataset remains useful as a regression fixture for viewing out-of-bounds legacy
data, but it is not regenerated in place.

## Out of scope

- Jitter or irregular row heights/column widths.
- Spanning/merged cells.
- Arbitrary free-space packing or semantic page-region generation.
- Visual realism such as fonts, rules, scan noise, or skew.
- Dynamic page growth or clipping as a difficulty mode.
- A general annotation-schema editor.

## Roadmap after this milestone

1. Jitter / irregular row heights and column widths.
2. Spanning / merged cells.
3. Document-class breadth.
4. M0 spatial model loop, followed by the modality ladder.
