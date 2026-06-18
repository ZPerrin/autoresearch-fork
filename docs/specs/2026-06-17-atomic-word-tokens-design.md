# Atomic word tokens + `Token` → `Word` rename — design

- Status: **proposed**. Parent: `docs/specs/2026-06-15-region-cell-token-schema-design.md` (the
  Region/Cell/Token contract, merged to `master` as schema v3). Canonical *why*: `docs/CHARTER.md`.
- Date: 2026-06-17
- Self-contained on purpose — written so a fresh session can implement it without the originating
  conversation. Follow-on: an implementation plan in `docs/plans/`.

## Motivation

The observable "token" is currently **inconsistent**: sometimes a single word, sometimes a whole
cell's multi-word text — depending on a class flag and on whether a cell wraps.

- `layout._emit_tokens(..., multi)` splits text into per-word tokens **only when `multi=True`**, where
  `multi = dc.structure.multi_token` (default **`False`**).
- With `multi_token=False` (every current class — `eob`, `invoice`, `receipt`), a cell's text is emitted
  as **one token per cell**. Data values (`$378.48`, `01/03/2026`, codes) are *coincidentally* single
  words, so they look atomic; but headers, group banners, sections, and globals are multi-word and
  become a **phrase crammed into one token** (`Amount Billed`, `Patient Responsibility`, `John Smith`,
  `Plan & Balance`). Measured on one `eob` page: multi-word tokens by role — `header` 8, `group_header`
  4, `key` 3, `value` 2, `section` 2.
- It is also internally inconsistent: the **wrapped-cell path** (`FieldSpec.max_width`) *always* emits
  per-word tokens, so within the same document some cells are per-word and others per-phrase.

This breaks the foundational premise: the token is the **one universal observable**, meant to mirror an
OCR / **Textract `WORD`** (bbox + text per word). A multi-word token (a) breaks the `token ≈ WORD`
correspondence the Textract-shaping rests on, (b) gives a phrase-spanning bbox where data cells get
tight per-word boxes — inconsistent spatial signal for the spatial modality, and (c) is a leftover of
an early incremental build step (`multi_token` was an opt-in split; the default never got revisited).

## Decision

1. **Tokens are always word-level.** Every cell holds one or more **word** tokens, uniformly. Retire
   `StructureSpec.multi_token` (and the `--multi-token` CLI flag) — splitting is no longer optional.
2. **Rename `Token` → `Word`** through the contract and code (and the JSON keys), so the observable atom
   is named for what it is (an OCR/Textract word), distinct from a transformer/sub-word "token". This is
   a breaking on-disk change → **`SCHEMA_VERSION` 3 → 4**.

### Why word is the right atom (durable rationale)

Word is the **lossless floor** of the Token→Cell→Region hierarchy; coarser units are *derived
compositions*, not the observable:

- **It is the real input.** Textract returns `WORD` blocks. A value/cell-level atom would bake in a
  segmentation that does not exist in real input; grouping words into the right value *is* the problem.
- **The composition is the task.** "Which words form this field's value / this record" is exactly what
  extraction learns. Synthetic knows the *perfect* word→cell grouping — the gold to supervise/measure a
  noisy real-data grouping against. Pre-composed atoms assume the task away.
- **Composition is one-way.** You can always group words up (line/value/record — cheap, derivable); you
  cannot recover words from a phrase token. So word is lossless; everything coarser is a view.

Alternatives rejected: *value/cell atom* (assumes segmentation, doesn't transfer to messy real
grouping); *char/sub-word atom* (the LM's internal job, below the spatial unit); *line atom* (itself a
derived grouping). Coarser groupings — Textract-style `Line`, and the `Record` rollup — stay **derived
projections**, added when a model or feature wants them (out of scope here).

## Changes

### `harness/src/tablelab/artifacts.py`
- `SCHEMA_VERSION = 4`.
- Rename dataclass `Token` → `Word`. Fields unchanged (`x0,y0,x1,y1,text`).
- `Sample.tokens: list[Token]` → `Sample.words: list[Word]`.
- `Cell.token_ids: list[int]` → `Cell.word_ids: list[int]`.
- `_token_from_dict` → `_word_from_dict`; `_sample_from_dict` reads `d["words"]` and `c["word_ids"]`.
- Keep `dc_field` aliasing (the `Cell.field` shadow still applies).

### `harness/src/tablelab/layout.py`
- `PlacedToken` → `PlacedWord` (keep the in-memory `seq` field — within-cell word order, used by render
  and now always potentially >1).
- `_emit_tokens` → `_emit_words`: **always** split on whitespace; drop the `multi` parameter. Empty text
  still appends nothing.
- Remove the `multi = dc.structure.multi_token` read and stop threading `multi` to `_emit_words` /
  `_emit_span_row` and the globals/header/data/section/totals emission. The wrapped-cell path already
  splits per-word — it stays; the non-wrapped path now matches it.
- `layout_with_regions` returns `(words, cells, regions)` (build serializable `Cell`s with `word_ids`).
- `Cell` import + the post-shuffle `index_of` id-map resolve `word_ids` (same mechanism, renamed).

### `harness/src/tablelab/render.py`
- `render(placed, dc)` still takes the word list; group by cell rect; order within a rect by
  `placed[i].seq`. Remove the now-obsolete "legacy single-token / multi_token off" comment — the `n == 1`
  branch is simply the single-word case.

### `harness/src/tablelab/build.py`
- Build `Word(...)` (no label), assemble `Sample(words=..., cells=..., regions=...)`; `Cell.word_ids`
  passes through. Normalize bboxes as before.

### `harness/src/tablelab/specs.py`
- Remove `StructureSpec.multi_token`. Update the `StructureSpec` docstring.

### `harness/src/tablelab/cli.py`
- Remove the `--multi-token` flag and its plumbing.

### `harness/src/tablelab/classes.py`
- No class sets `multi_token=True` today, so only remove any `multi_token=...` kwargs if present (none
  expected). Behavior change: all classes now emit word-level tokens.

### Tests (`harness/tests/`)
- `_cells.py`: `text_of` already joins `cell.token_ids` → rename to `word_ids`; `placed()` returns
  `(words, cells, regions)`.
- `test_multi_token.py`: repurpose from "the flag splits cells" to "**splitting is universal**" — assert
  multi-word cell values (header/section/global/data) emit one word token per word with `seq` order, no
  flag involved. (Or fold into another file and delete.)
- Sweep every test for `.tokens`, `token_ids`, `multi_token`, `Token(` → `words`, `word_ids`, removed,
  `Word(`. Many assertions on token *counts* change (multi-word headers/values now split).
- `test_golden.py` + `golden/invoice_seed7_n3.json`: regenerate — token counts rise (e.g. multi-word
  invoice descriptions split), and the fixture keys become `words`/`word_ids`.

### Viewer (`viewer/src/`)
- `types.ts`: `Token` → `Word`; `Sample.tokens` → `words`; `Cell.token_ids` → `word_ids`; header comment
  → `contract v4`.
- `App.tsx`: `selectedTokenIdx` → `selectedWordIdx` (or keep the var name but it indexes words).
- `DocumentViewer.tsx`: `cellByToken` → `cellByWord` keyed over `cell.word_ids`; iterate `sample.words`.
- `MetaPanel.tsx`: read `sample.words`, find cell by `word_ids.includes(idx)`; "Selected token" label →
  "Selected word" (cosmetic).

### Docs
- `AGENTS.md` "Contract is the seam" line: `schema_version = 4`; note tokens are atomic **words**
  (`Word`), and `Cell` groups them via `word_ids`.
- This spec + a `docs/plans/` implementation plan.

## Verification

- `cd harness && uv run pytest -q` green.
- Build `invoice`/`eob`/`receipt`; assert **no word token contains a space** (`' ' not in w.text`) — the
  consistency guarantee. Multi-word headers/sections/globals now emit multiple words; every cell's
  `word_ids` covers its words in reading order.
- `schema_version == 4`; `samples.json` uses `words`/`word_ids`; round-trip test updated and passing.
- Golden regenerated; token geometry still pinned (the locked observable).
- Viewer: `npm --prefix viewer run build` clean; live check — multi-word headers now render as separate
  boxes, click a word → its cell/region detail.

## Out of scope

- `Line` grouping (Textract-style `WORD`→`LINE`) and the `Record` rollup — **derived projections**, added
  when modeling/features need them (the deferred labels/projection milestone).
- Generalizing `Cell` off its tabular bias — tracked separately
  (`docs/specs/2026-06-15-region-cell-token-schema-design.md` §"Known limitation"), driven by the
  key-value form class.
- Any change to `Region`/`Cell` shape beyond the `token_ids`→`word_ids` rename.

## Trajectory note

Subtractive overall: a flag and a render special-case go away; the contract gains a consistent atom and
an honest name. After this, the observable layer is uniform (`Word` = OCR/Textract word), the hierarchy
(`Word` → `Cell` → `Region`) is clean, and `Line`/`Record` are the natural next derived layers.
