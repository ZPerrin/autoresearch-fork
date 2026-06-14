# Multi-token cells — design

- Status: **design** (full-agentic build; first structural-realism follow-on on the synth-toolkit backbone)
- Date: 2026-06-13
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md` (§ structural realism, item 1) and the backbone
  spec `2026-06-13-synth-toolkit-backbone-design.md`.

## Goal

A cell whose value is multiple words becomes several tokens that **share one `record/field`** and
carry a within-cell order index (`seq`). This is the biggest realism jump toward real OCR/Textract
output (where "Physical therapy" is two word-boxes, not one) and the first real stress test of the
backbone's layout/render/IR seam. Gated behind a `StructureSpec` knob; **default off is
byte-identical to the backbone** (the golden test still passes).

## Decisions

1. **Knob:** `StructureSpec.multi_token: bool = False`. When `True`, each cell value is split on
   whitespace into per-word tokens. Fields whose values contain no spaces (amount/date/code/quantity)
   are naturally unaffected; descriptions ("Office chair", "Physical therapy") split. Realism emerges
   from the data — no per-field configuration needed for this slice.

2. **Target representation:** `label = {"record": r, "field": c, "seq": k}` when on, where `k` is the
   0-based word order within the cell. Off keeps `{"record": r, "field": c}`. This resolves the
   backbone spec's open question ("shared record/field only, or + within-cell order") **in favor of
   including order** — reading order is signal for any grouping/sequence model target.

3. **Seam (where the work lands):**
   - `layout.py` (Pillow-free) splits a multi-word value into N `PlacedToken`s that **share the same
     cell rect** and differ only in `text` + `seq`. The `PlacedToken` IR is unchanged.
   - `render.py` gains **sequence-in-cell** layout: it groups tokens by `(record, field)`, orders by
     `seq`, lays the words out as a contiguous phrase within the shared cell (anchored left or right
     per alignment), and records each word's glyph-extent box. It returns boxes **in the original
     input order**, so `build.py`'s 1:1 `zip(placed, boxes)` is untouched.
   - `build.py` is unchanged.

4. **Determinism / byte-identical (off path):** `sample()` is called exactly once per cell regardless
   of the knob, so the off-path RNG stream is identical to the backbone. Off, every cell is a
   one-token group; the renderer routes one-token groups through the **exact legacy positioning code**,
   so single-word cells keep their tight boxes and the image is identical. The golden regression test
   is the guard.

5. **Rendering detail (on path, multi-word group):** positions use `draw.textlength` (advance width)
   for phrase width and per-word advance; boxes use `draw.textbbox` (ink extent). Right-aligned
   phrases end at `cx1 - pad`; left-aligned start at `cx0 + pad`; each word is vertically centered in
   the row by its own glyph height (same formula as the backbone). Words are drawn contiguously so the
   cell reads like normal text, but each emits its own box.

6. **CLI:** `build --multi-token` (forks `dc.structure` with `multi_token=True`).

## Verification

- **Golden (off):** existing `tests/test_golden.py` still passes — off path is byte-identical.
- **New behavioral test (on):** for `invoice` seed 7 with `multi_token=True`: at least one cell splits
  into >1 token; every `(record, field)` group has contiguous `seq` `0..n-1`; per-word boxes are
  vertically within their cell, left-to-right disjoint, and anchored to the correct cell edge by
  alignment.
- **Smoke:** `build --multi-token` then `inspect` shows a higher tokens/sample; viewer eyeball.

## Out of scope (deliberately, to keep this a manageable chunk)

- Enriching the description sampler with longer phrases (would change the RNG draw and break the
  golden test) — defer.
- Per-field / per-type multi-token control — a global bool is enough now (YAGNI).
- The other five structural-realism features (header row, background tokens, multi-table + globals,
  jitter, spanning) — each its own follow-on.

## Trajectory note

This validates the pattern every follow-on uses: a `StructureSpec` knob + a layout-stage change, with
the renderer evolving and the IR/contract stable. Next after this: **header row**.
