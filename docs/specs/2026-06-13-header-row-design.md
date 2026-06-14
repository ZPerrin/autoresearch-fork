# Header row — design

- Status: **shipped** (merged to `master`; second structural-realism feature). Plan: `docs/plans/2026-06-13-header-row.md`.
- Date: 2026-06-13
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md` (§ structural realism). Follows
  `2026-06-13-multi-token-cells-design.md`.

## Goal

A table gains a top **header row** of field-name tokens (e.g. "Description", "Quantity", "Unit
Price", "Amount"); the data rows shift down by one. Gated behind a `StructureSpec.header` knob;
**default off is byte-identical** to the current output (golden test guards it).

## Decisions

1. **Knob:** `StructureSpec.header: bool = False`. When `True`, emit one header row above the data
   rows; data records keep their `record` indices but shift down one pixel row.

2. **Header label:** `{"field": c, "header": True}` — marks the token as the header for column `c`,
   with no `record` key (headers are not data records). With `multi_token` on, a multi-word header
   ("Unit Price") splits into per-word tokens sharing the header cell, each gaining `seq`
   (`{"field": c, "header": True, "seq": k}`).

3. **Header text:** derived from `FieldSpec.name` via `name.replace("_", " ").title()`
   (`unit_price → "Unit Price"`, `amount_billed → "Amount Billed"`). No new `FieldSpec` field
   needed now (YAGNI); custom header text can be added later if a class needs it. Header alignment
   matches the column's `FieldSpec.align`.

4. **Enabling render refactor:** the renderer currently groups a cell's tokens by
   `(record, field)`. Header tokens have no `record`, so grouping switches to key on the **cell rect**
   (`PlacedToken.cell`) — the tuple is identical for all tokens in a cell and distinct across cells.
   This decouples the renderer from the label schema (also smoothing future features like background
   tokens with `label = null`) and stays byte-identical off-path (every cell is a one-token group in
   insertion order).

5. **Layout factoring:** the multi-word split (used by both header and data emission) moves into a
   small `_emit()` helper so header and data rows share one code path.

6. **Determinism / byte-identical (off path):** with `header` off the header block is skipped
   entirely and `sample()` is still called once per data cell in row-major order, so the RNG stream
   and all data boxes are unchanged. The golden test is the guard.

7. **CLI:** `build --header` (composable with `--multi-token`).

## Verification

- **Golden (off):** `tests/test_golden.py` still passes (byte-identical).
- **New tests:** header on → one header token per field with the titleized name, header cells sit at
  the top margin and all data cells below the first row; header off is the default (no header
  tokens); header + multi_token splits "Unit Price" into two header tokens sharing the header cell;
  rendered header boxes sit above all data boxes (exercises the cell-key grouping).
- **Smoke:** `build --header` then `inspect` shows `+C` tokens/sample; viewer eyeball.

## Out of scope

- Custom/configurable header text or styling (bold) — derivation is enough; styling is the deferred
  `RenderSpec` visual-realism seam.
- Per-table headers for the multi-table feature (feature 4) — that builds on this.

## Trajectory note

Second confirmation of the pattern: a `StructureSpec` knob + a layout-stage change, renderer evolving
but IR/contract stable. The cell-key grouping refactor makes the renderer schema-agnostic for the
remaining features. Next after this: **background / non-table tokens**.
