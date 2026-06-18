# Atomic Word Tokens + `Token`→`Word` Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the observable atom uniformly word-level and rename `Token`→`Word` across the contract, code, tests, golden fixture, viewer, and docs — bumping `SCHEMA_VERSION` 3→4.

**Architecture:** The contract's observable was inconsistently a word *or* a whole cell's phrase, gated by `StructureSpec.multi_token` (default off). We retire that flag so every cell always emits one `Word` per whitespace-split word (the wrapped-cell path already did this — the non-wrapped path now matches), and rename the dataclass/JSON keys `Token`→`Word`, `Sample.tokens`→`words`, `Cell.token_ids`→`word_ids`. This is a breaking on-disk change.

**Tech Stack:** Python (`uv` + dataclasses + Pillow) in `harness/src/tablelab/`; pytest in `harness/tests/`; Vite/React/TypeScript in `viewer/src/`.

**Source of truth:** `docs/specs/2026-06-17-atomic-word-tokens-design.md`.

**Convention note (overrides skill default):** AGENTS.md says *"No TDD for now — implement and verify by running."* Tasks below are implement-then-verify, not red/green. This is a rename + flag removal, so several intermediate tasks leave `pytest` red until the test sweep (Task 6) and golden regen (Task 7) land; that's expected. Run the full suite at Task 8.

**In-memory vs. on-disk naming:** We rename the *type* `PlacedToken`→`PlacedWord` (render imports it) but deliberately **keep** the transient field/locals `PlacedCell.tokens` / `toks` — they are never serialized, and keeping them limits churn. Only the serialized contract (`Word`, `Sample.words`, `Cell.word_ids`) and the public `_emit_words` are renamed.

**Out of scope (do not touch):** `runs/_fixture/` is a pre-existing **schema v2** viewer demo (carries old per-token `label`/`pred`, no cells/regions) — it is already stale relative to v3 and is not part of this change. Leave it as-is.

---

## File Structure

Files modified, by responsibility:

- `harness/src/tablelab/artifacts.py` — the contract: dataclasses + (de)serialization + `SCHEMA_VERSION`.
- `harness/src/tablelab/layout.py` — placement: always word-split, drop `multi` threading.
- `harness/src/tablelab/render.py` — rasterization: rename the placed-word type, drop the legacy comment.
- `harness/src/tablelab/build.py` — assembly: construct `Word`/`Sample(words=...)`.
- `harness/src/tablelab/specs.py` — remove `StructureSpec.multi_token`.
- `harness/src/tablelab/cli.py` — remove `--multi-token`; read `s.words` in `inspect`.
- `harness/src/tablelab/classes.py` — verify-only (no `multi_token` kwargs present).
- `harness/tests/**` — rename sweep + repurpose the flag tests.
- `harness/tests/golden/invoice_seed7_n3.json` — regenerate (counts rise, keys rename).
- `viewer/src/{types.ts,App.tsx,DocumentViewer.tsx,MetaPanel.tsx}` — type/prop rename.
- `AGENTS.md`, `docs/CHARTER.md` — contract docs.

---

## Task 1: Contract — rename `Token`→`Word`, bump schema to 4

**Files:**
- Modify: `harness/src/tablelab/artifacts.py`

- [ ] **Step 1: Bump the schema version**

In `harness/src/tablelab/artifacts.py:6`, change:

```python
SCHEMA_VERSION = 3
```
to:
```python
SCHEMA_VERSION = 4
```

- [ ] **Step 2: Rename the `Token` dataclass to `Word`**

Replace (`artifacts.py:9-12`):

```python
@dataclass
class Token:
    x0: float; y0: float; x1: float; y1: float
    text: str | None = None
```
with:
```python
@dataclass
class Word:
    x0: float; y0: float; x1: float; y1: float
    text: str | None = None
```

- [ ] **Step 3: Rename the `Cell.token_ids` field**

In `Cell` (`artifacts.py:24`), change:

```python
    token_ids: list[int] = dc_field(default_factory=list)
```
to:
```python
    word_ids: list[int] = dc_field(default_factory=list)
```

- [ ] **Step 4: Rename `Sample.tokens`**

In `Sample` (`artifacts.py:38`), change:

```python
    tokens: list[Token]
```
to:
```python
    words: list[Word]
```

- [ ] **Step 5: Rename the deserialization helpers**

Replace (`artifacts.py:89-99`):

```python
def _token_from_dict(d: dict) -> Token:
    return Token(**d)


def _sample_from_dict(d: dict) -> Sample:
    raw_regions = d.get("regions")
    regions = [Region(**r) for r in raw_regions] if raw_regions is not None else None
    cells = [Cell(**c) for c in d.get("cells", [])]
    return Sample(id=d["id"], tokens=[_token_from_dict(t) for t in d["tokens"]],
                  image=d.get("image"), width=d.get("width"), height=d.get("height"),
                  cells=cells, regions=regions)
```
with:
```python
def _word_from_dict(d: dict) -> Word:
    return Word(**d)


def _sample_from_dict(d: dict) -> Sample:
    raw_regions = d.get("regions")
    regions = [Region(**r) for r in raw_regions] if raw_regions is not None else None
    cells = [Cell(**c) for c in d.get("cells", [])]
    return Sample(id=d["id"], words=[_word_from_dict(w) for w in d["words"]],
                  image=d.get("image"), width=d.get("width"), height=d.get("height"),
                  cells=cells, regions=regions)
```

- [ ] **Step 6: Verify the module imports and reports v4**

Run: `cd harness && uv run python -c "from tablelab.artifacts import Word, Sample, Cell, SCHEMA_VERSION; print(SCHEMA_VERSION); print([f for f in Cell.__dataclass_fields__])"`
Expected: prints `4` and a field list ending in `word_ids` (no `token_ids`).

---

## Task 2: Layout — always word-split, drop the `multi` flag

**Files:**
- Modify: `harness/src/tablelab/layout.py`

- [ ] **Step 1: Rename the `PlacedToken` dataclass**

Replace (`layout.py:122-130`):

```python
@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # render rect in page px (x0, y0, x1, y1)
    align: str = "left"
    font_size: int = 22
    dx: float = 0.0
    dy: float = 0.0
    seq: int = 0                              # within-rect reading order (render hint; not serialized)
```
with:
```python
@dataclass
class PlacedWord:
    text: str
    cell: tuple[float, float, float, float]   # render rect in page px (x0, y0, x1, y1)
    align: str = "left"
    font_size: int = 22
    dx: float = 0.0
    dy: float = 0.0
    seq: int = 0                              # within-rect reading order (render hint; not serialized)
```

- [ ] **Step 2: Update the `PlacedCell.tokens` type annotation**

In `PlacedCell` (`layout.py:142`), change:

```python
    tokens: list[PlacedToken] = dc_field(default_factory=list)   # transient refs; resolved to ids on return
```
to:
```python
    tokens: list[PlacedWord] = dc_field(default_factory=list)   # transient refs; resolved to ids on return
```

(The field name stays `tokens` — it is transient and never serialized.)

- [ ] **Step 3: Rewrite `_emit_tokens` as `_emit_words` (always split)**

Replace (`layout.py:214-227`):

```python
def _emit_tokens(placed: list[PlacedToken], text: str,
                 rect: tuple[float, float, float, float],
                 align: str, font_size: int, multi: bool) -> list[PlacedToken]:
    """Append one token for `text`, or one per word when `multi`. Empty text appends
    nothing. Returns the appended tokens (in reading order) for cell membership."""
    new: list[PlacedToken] = []
    if not text:
        return new
    words = text.split() if multi else [text]
    for k, word in enumerate(words):
        tok = PlacedToken(text=word, cell=rect, align=align, font_size=font_size, seq=k)
        placed.append(tok)
        new.append(tok)
    return new
```
with:
```python
def _emit_words(placed: list[PlacedWord], text: str,
                rect: tuple[float, float, float, float],
                align: str, font_size: int) -> list[PlacedWord]:
    """Append one PlacedWord per whitespace-split word in `text` (empty text appends
    nothing). Each word carries its within-cell reading order (seq). Returns the
    appended words (in reading order) for cell membership."""
    new: list[PlacedWord] = []
    if not text:
        return new
    for k, word in enumerate(text.split()):
        w = PlacedWord(text=word, cell=rect, align=align, font_size=font_size, seq=k)
        placed.append(w)
        new.append(w)
    return new
```

- [ ] **Step 4: Drop `multi` from `_emit_span_row`**

Replace the signature + body call (`layout.py:230-250`):

```python
def _emit_span_row(placed: list[PlacedToken], cells: list[PlacedCell], spans, edges,
                   y: float, row_h: float, region_index: int, row_index: int, role: str,
                   font: int, multi: bool, rng: random.Random) -> None:
    """Emit one spanning row (section or totals). Each SpanCell covers a contiguous
    column range from the running column index; text cells are literal, type cells are
    sampled left-to-right, empty cells still produce a cell (no tokens)."""
    c = 0
    for sc in spans:
        c0, c1 = c, c + sc.span - 1
        rect = (edges[c0], y, edges[c1 + 1], y + row_h)
        if sc.text is not None:
            value = sc.text
        elif sc.type is not None:
            value = sample(sc.type, rng)
        else:
            value = ""
        toks = _emit_tokens(placed, value, rect, sc.align, font, multi)
        cells.append(PlacedCell(region_index=region_index, row_index=row_index,
                                column_index=c0, span=(c1 - c0 + 1, 1), bbox=rect,
                                role=role, field=None, tokens=toks))
        c = c1 + 1
```
with:
```python
def _emit_span_row(placed: list[PlacedWord], cells: list[PlacedCell], spans, edges,
                   y: float, row_h: float, region_index: int, row_index: int, role: str,
                   font: int, rng: random.Random) -> None:
    """Emit one spanning row (section or totals). Each SpanCell covers a contiguous
    column range from the running column index; text cells are literal, type cells are
    sampled left-to-right, empty cells still produce a cell (no words)."""
    c = 0
    for sc in spans:
        c0, c1 = c, c + sc.span - 1
        rect = (edges[c0], y, edges[c1 + 1], y + row_h)
        if sc.text is not None:
            value = sc.text
        elif sc.type is not None:
            value = sample(sc.type, rng)
        else:
            value = ""
        toks = _emit_words(placed, value, rect, sc.align, font)
        cells.append(PlacedCell(region_index=region_index, row_index=row_index,
                                column_index=c0, span=(c1 - c0 + 1, 1), bbox=rect,
                                role=role, field=None, tokens=toks))
        c = c1 + 1
```

- [ ] **Step 5: Update `layout_with_regions` — signature, docstring, drop `multi`**

In `layout_with_regions`, change the signature return type (`layout.py:538`):

```python
def layout_with_regions(dc: DocumentClass, rng: random.Random) -> tuple[list[PlacedToken], list[Cell], list[PlacedRegion]]:
```
to:
```python
def layout_with_regions(dc: DocumentClass, rng: random.Random) -> tuple[list[PlacedWord], list[Cell], list[PlacedRegion]]:
```

Replace the docstring + opening locals (`layout.py:539-554`):

```python
    """Place one document's tokens, cells, and typed regions (logical, no Pillow).
    Global/singleton fields (dc.globals) are laid out first as key/value cells in a
    'form' region; then each table instance is drawn and tagged with a 'table' region
    (instance-ordinal indexed per table name). Header rows (structure.header),
    multi-token split (structure.multi_token) and background tokens
    (structure.background) apply as before; background tokens belong to no cell.
    Returns (tokens, cells, regions) with cell token_ids resolved after the shuffle."""
    dc = _resolve_row_h(dc)
    L = dc.layout
    W, _ = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    J = dc.jitter
    shape = _choose_shape(dc, rng)
    placed: list[PlacedToken] = []
```
with:
```python
    """Place one document's words, cells, and typed regions (logical, no Pillow).
    Global/singleton fields (dc.globals) are laid out first as key/value cells in a
    'form' region; then each table instance is drawn and tagged with a 'table' region
    (instance-ordinal indexed per table name). Every cell emits one Word per
    whitespace word (uniformly); header rows (structure.header) and background words
    (structure.background) apply as before; background words belong to no cell.
    Returns (words, cells, regions) with cell word_ids resolved after the shuffle."""
    dc = _resolve_row_h(dc)
    L = dc.layout
    W, _ = L.page
    mx, my = L.margin
    header = dc.structure.header
    J = dc.jitter
    shape = _choose_shape(dc, rng)
    placed: list[PlacedWord] = []
```

- [ ] **Step 6: Update the globals emission calls**

Replace the two globals `_emit_tokens` calls (`layout.py:572-579`):

```python
            toks = _emit_tokens(placed, _header_text(f.name) + ":", label_rect,
                                "left", dc.render.font_size, multi)
```
with:
```python
            toks = _emit_words(placed, _header_text(f.name) + ":", label_rect,
                               "left", dc.render.font_size)
```
and:
```python
            toks = _emit_tokens(placed, sample(f.type, rng), value_rect,
                                "left", dc.render.font_size, multi)
```
with:
```python
            toks = _emit_words(placed, sample(f.type, rng), value_rect,
                               "left", dc.render.font_size)
```

- [ ] **Step 7: Update the group-header, header, and section emission calls**

Replace the group-header call (`layout.py:609`):

```python
                    toks = _emit_tokens(placed, name, rect, "left", cell_font, multi)
```
with:
```python
                    toks = _emit_words(placed, name, rect, "left", cell_font)
```

Replace the header call (`layout.py:619-620`):

```python
                    toks = _emit_tokens(placed, _header_text(f.name), rect, f.align,
                                        cell_font, multi)
```
with:
```python
                    toks = _emit_words(placed, _header_text(f.name), rect, f.align,
                                       cell_font)
```

Replace the section span-row call (`layout.py:627-628`):

```python
                _emit_span_row(placed, cells, table.section.cells, edges, y, L.row_h,
                               region_index, row_idx, "section", cell_font, multi, rng)
```
with:
```python
                _emit_span_row(placed, cells, table.section.cells, edges, y, L.row_h,
                               region_index, row_idx, "section", cell_font, rng)
```

- [ ] **Step 8: Update the data-cell paths (wrapped + non-wrapped) and totals**

In the data loop, change the wrapped-cell `PlacedToken` construction (`layout.py:663`):

```python
                                tok = PlacedToken(text=w, cell=line_rect, align=f.align,
                                                  font_size=cell_font, seq=wi)
```
to:
```python
                                tok = PlacedWord(text=w, cell=line_rect, align=f.align,
                                                 font_size=cell_font, seq=wi)
```
and the local `toks` type hint (`layout.py:653`):

```python
                    toks: list[PlacedToken] = []
```
to:
```python
                    toks: list[PlacedWord] = []
```
and the non-wrapped `_emit_tokens` call (`layout.py:668`):

```python
                        toks = _emit_tokens(placed, value, cell_bbox, f.align, cell_font, multi)
```
to:
```python
                        toks = _emit_words(placed, value, cell_bbox, f.align, cell_font)
```

Replace the totals span-row call (`layout.py:677-678`):

```python
                _emit_span_row(placed, cells, table.totals.cells, edges, y, L.row_h,
                               region_index, row_idx, "summary", cell_font, multi, rng)
```
with:
```python
                _emit_span_row(placed, cells, table.totals.cells, edges, y, L.row_h,
                               region_index, row_idx, "summary", cell_font, rng)
```

- [ ] **Step 9: Update the background-word construction and the out-cell builder**

Replace the background `PlacedToken` (`layout.py:695-696`):

```python
            placed.append(PlacedToken(text=background_token(dc.background_terms, rng),
                                      cell=rect, align="left", font_size=dc.render.font_size))
```
with:
```python
            placed.append(PlacedWord(text=background_token(dc.background_terms, rng),
                                     cell=rect, align="left", font_size=dc.render.font_size))
```

Replace the serializable-cell builder (`layout.py:704-710`):

```python
    out_cells = [
        Cell(region_index=c.region_index, row_index=c.row_index,
             column_index=c.column_index, span=list(c.span), bbox=list(c.bbox),
             role=c.role, field=c.field,
             token_ids=[index_of[id(t)] for t in c.tokens])
        for c in cells
    ]
```
with:
```python
    out_cells = [
        Cell(region_index=c.region_index, row_index=c.row_index,
             column_index=c.column_index, span=list(c.span), bbox=list(c.bbox),
             role=c.role, field=c.field,
             word_ids=[index_of[id(t)] for t in c.tokens])
        for c in cells
    ]
```

- [ ] **Step 10: Update the `layout()` back-compat helper return type**

Replace (`layout.py:714-716`):

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Tokens only (back-compat for render/golden helpers)."""
    return layout_with_regions(dc, rng)[0]
```
with:
```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedWord]:
    """Words only (back-compat for render/golden helpers)."""
    return layout_with_regions(dc, rng)[0]
```

- [ ] **Step 11: Confirm no `_emit_tokens` / `multi` / `PlacedToken` references remain**

Run: `cd harness && grep -n "_emit_tokens\|PlacedToken\|\bmulti\b\|multi_token" src/tablelab/layout.py`
Expected: no output (all renamed/removed).

---

## Task 3: Render — rename the placed-word type, drop the legacy comment

**Files:**
- Modify: `harness/src/tablelab/render.py`

- [ ] **Step 1: Update the import and signature**

Replace (`render.py:6`):

```python
from .layout import PlacedToken
```
with:
```python
from .layout import PlacedWord
```

Replace (`render.py:18-22`):

```python
def render(placed: list[PlacedToken], dc: DocumentClass) -> tuple[Image.Image, list[Box]]:
    """Draw placed tokens onto a white page; return the image and per-token
    glyph-extent boxes (page pixels), parallel to ``placed``. Tokens sharing a
    cell rect are laid out left-to-right as one phrase; their boxes are still
    returned in the input order so the caller's 1:1 zip holds."""
```
with:
```python
def render(placed: list[PlacedWord], dc: DocumentClass) -> tuple[Image.Image, list[Box]]:
    """Draw placed words onto a white page; return the image and per-word
    glyph-extent boxes (page pixels), parallel to ``placed``. Words sharing a
    cell rect are laid out left-to-right as one phrase; their boxes are still
    returned in the input order so the caller's 1:1 zip holds."""
```

- [ ] **Step 2: Drop the obsolete legacy comment in the `n == 1` branch**

Replace (`render.py:43-44`):

```python
        if len(idxs) == 1:
            # Legacy single-token path — keeps output byte-identical when multi_token is off.
            p = placed[idxs[0]]
```
with:
```python
        if len(idxs) == 1:
            # Single-word cell: anchor the lone word to its cell edge by alignment.
            p = placed[idxs[0]]
```

- [ ] **Step 3: Verify render imports**

Run: `cd harness && uv run python -c "from tablelab.render import render; from tablelab.layout import PlacedWord; print('ok')"`
Expected: `ok`.

---

## Task 4: Build — construct `Word` / `Sample(words=...)`

**Files:**
- Modify: `harness/src/tablelab/build.py`

- [ ] **Step 1: Update the artifacts import**

Replace (`build.py:16`):

```python
from .artifacts import Sample, Token, Cell, Region, DatasetManifest, write_dataset
```
with:
```python
from .artifacts import Sample, Word, Cell, Region, DatasetManifest, write_dataset
```

- [ ] **Step 2: Construct `Word`s and a `Sample(words=...)` with `word_ids`**

Replace (`build.py:188-204`):

```python
                tokens = [Token(x0=round(b[0] / W, 4), y0=round(b[1] / H, 4),
                                x1=round(b[2] / W, 4), y1=round(b[3] / H, 4),
                                text=p.text)
                          for p, b in zip(placed, boxes)]
                cells = [Cell(region_index=c.region_index, row_index=c.row_index,
                              column_index=c.column_index, span=c.span,
                              bbox=[round(c.bbox[0] / W, 4), round(c.bbox[1] / H, 4),
                                    round(c.bbox[2] / W, 4), round(c.bbox[3] / H, 4)],
                              role=c.role, field=c.field, token_ids=c.token_ids)
                         for c in placed_cells]
                regions = [Region(type=r.type, name=r.name, index=r.index,
                                  bbox=[round(r.bbox[0] / W, 4), round(r.bbox[1] / H, 4),
                                        round(r.bbox[2] / W, 4), round(r.bbox[3] / H, 4)])
                           for r in placed_regions]
                samples.append(Sample(id=i, tokens=tokens, width=W, height=H,
                                      image=f"/datasets/{dataset_id}/images/{i}.png",
                                      cells=cells, regions=regions))
```
with:
```python
                words = [Word(x0=round(b[0] / W, 4), y0=round(b[1] / H, 4),
                              x1=round(b[2] / W, 4), y1=round(b[3] / H, 4),
                              text=p.text)
                         for p, b in zip(placed, boxes)]
                cells = [Cell(region_index=c.region_index, row_index=c.row_index,
                              column_index=c.column_index, span=c.span,
                              bbox=[round(c.bbox[0] / W, 4), round(c.bbox[1] / H, 4),
                                    round(c.bbox[2] / W, 4), round(c.bbox[3] / H, 4)],
                              role=c.role, field=c.field, word_ids=c.word_ids)
                         for c in placed_cells]
                regions = [Region(type=r.type, name=r.name, index=r.index,
                                  bbox=[round(r.bbox[0] / W, 4), round(r.bbox[1] / H, 4),
                                        round(r.bbox[2] / W, 4), round(r.bbox[3] / H, 4)])
                           for r in placed_regions]
                samples.append(Sample(id=i, words=words, width=W, height=H,
                                      image=f"/datasets/{dataset_id}/images/{i}.png",
                                      cells=cells, regions=regions))
```

(The `_validate_boxes` helper's internal "token" wording — `build.py:140-156` — stays untouched; it is an internal diagnostic and `test_capacity` matches its `"at token index"` string.)

- [ ] **Step 3: Verify build imports**

Run: `cd harness && uv run python -c "import tablelab.build; print('ok')"`
Expected: `ok`.

---

## Task 5: Specs + CLI — remove the `multi_token` knob

**Files:**
- Modify: `harness/src/tablelab/specs.py`
- Modify: `harness/src/tablelab/cli.py`
- Verify: `harness/src/tablelab/classes.py`

- [ ] **Step 1: Remove `multi_token` from `StructureSpec` (field + docstring)**

Replace (`specs.py:56-73`):

```python
@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter). Each follow-on spec adds fields here.
    See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    multi_token: split multi-word cell values into per-word tokens that share one
        record/field and carry a within-cell order index (seq).
    header: emit a top header row of field-name tokens (label {"field": c, "header": True}).
        With FieldSpec.group set, a grouped-header banner band is emitted above the leaf
        header row (see docs/specs/2026-06-14-spanning-cells-grouped-headers-design.md).
    background: scatter N non-table tokens (label = None) in the footer band below the table.

    Spanning data rows (section/totals) live on TableSpec; grouped-header membership lives
    on FieldSpec.group."""
    multi_token: bool = False
    header: bool = False
    background: int = 0
```
with:
```python
@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background words,
    multiple tables, jitter). Each follow-on spec adds fields here.
    See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    Cells always emit one Word per whitespace word (the atomic observable); there is
    no opt-in splitting flag — see docs/specs/2026-06-17-atomic-word-tokens-design.md.

    header: emit a top header row of field-name words. With FieldSpec.group set, a
        grouped-header banner band is emitted above the leaf header row
        (see docs/specs/2026-06-14-spanning-cells-grouped-headers-design.md).
    background: scatter N non-table words in the footer band below the table.

    Spanning data rows (section/totals) live on TableSpec; grouped-header membership lives
    on FieldSpec.group."""
    header: bool = False
    background: int = 0
```

- [ ] **Step 2: Remove the CLI `--multi-token` flag and its plumbing**

In `cli.py`, remove the flag-application block (`cli.py:22-24`):

```python
    S = dc.structure
    if args.multi_token:
        S = replace(S, multi_token=True)
    if args.header:
```
becomes:
```python
    S = dc.structure
    if args.header:
```

Remove the argument definition (`cli.py:104-105`):

```python
    b.add_argument("--multi-token", action="store_true",
                   help="split multi-word cells into per-word tokens (shared record/field + seq)")
```
(delete these two lines).

- [ ] **Step 3: Read `s.words` in the `inspect` command**

Replace (`cli.py:76`):

```python
    ntok = sum(len(s.tokens) for s in samples)
```
with:
```python
    ntok = sum(len(s.words) for s in samples)
```
and the print label (`cli.py:81`):

```python
    print(f"tokens:   {ntok} ({ntok / max(m.count, 1):.1f}/sample)")
```
with:
```python
    print(f"words:    {ntok} ({ntok / max(m.count, 1):.1f}/sample)")
```

- [ ] **Step 4: Verify `classes.py` needs no change**

Run: `cd harness && grep -n "multi_token" src/tablelab/classes.py`
Expected: no output (no class sets the flag; nothing to remove).

- [ ] **Step 5: Verify specs + CLI import and the flag is gone**

Run: `cd harness && uv run python -c "from tablelab.specs import StructureSpec; assert not hasattr(StructureSpec(), 'multi_token'); import tablelab.cli; print('ok')"`
Expected: `ok`.

Run: `cd harness && uv run python -m tablelab.cli build --help`
Expected: help text with **no** `--multi-token` option.

---

## Task 6: Tests — rename sweep + repurpose the flag tests

**Files:**
- Modify: `harness/tests/_cells.py`
- Modify: `harness/tests/test_contract_roundtrip.py`
- Modify: `harness/tests/test_regions.py`
- Modify: `harness/tests/test_spanning.py`
- Modify: `harness/tests/test_capacity.py`
- Modify: `harness/tests/test_multi_table.py`
- Modify: `harness/tests/test_header.py`
- Delete: `harness/tests/test_multi_token.py`
- Create: `harness/tests/test_word_split.py`
- (mechanically swept) `test_background.py`, `test_wrap.py`, `test_spacing.py`

- [ ] **Step 1: Mechanical sweep — `token_ids`→`word_ids` and `PlacedToken`→`PlacedWord`**

These two identifiers are unambiguous across the test tree (the `bg_token_ids` helper renames to `bg_word_ids` in `_cells.py` *and* its only importer `test_background.py` in the same pass, staying in sync). Run from `harness/tests/`:

```bash
cd harness/tests
grep -rl 'token_ids' . | xargs sed -i '' 's/token_ids/word_ids/g'
grep -rl 'PlacedToken' . | xargs sed -i '' 's/PlacedToken/PlacedWord/g'
```

- [ ] **Step 2: Fix the `text_of` docstring wording in `_cells.py`**

In `harness/tests/_cells.py`, the `sed` above already changed `cell.token_ids`→`cell.word_ids` and `bg_token_ids`→`bg_word_ids`. Update the `text_of` docstring (`_cells.py:18`) from:

```python
    """The cell's words joined in word_ids order."""
```
(leave as-is — `sed` produced the correct wording). No further edit needed; this step is a visual confirmation that `_cells.py` now reads:

```python
def text_of(tokens, cell):
    """The cell's words joined in word_ids order."""
    return " ".join(tokens[i].text for i in cell.word_ids)


def bg_word_ids(tokens, cells):
    """Token indices that belong to no cell (background words)."""
    claimed = {i for c in cells for i in c.word_ids}
    return [i for i in range(len(tokens)) if i not in claimed]
```

- [ ] **Step 3: Update `test_contract_roundtrip.py` — import, schema assert, `Word`/`words`**

Replace (`test_contract_roundtrip.py:1-7`):

```python
from pathlib import Path
from tablelab.artifacts import (Sample, Token, Cell, Region, DatasetManifest,
                                write_dataset, read_dataset, SCHEMA_VERSION)


def test_schema_version_is_3():
    assert SCHEMA_VERSION == 3
```
with:
```python
from pathlib import Path
from tablelab.artifacts import (Sample, Word, Cell, Region, DatasetManifest,
                                write_dataset, read_dataset, SCHEMA_VERSION)


def test_schema_version_is_4():
    assert SCHEMA_VERSION == 4
```

Replace the sample construction (`test_contract_roundtrip.py:11-13`):

```python
    sample = Sample(
        id=0,
        tokens=[Token(0.1, 0.1, 0.2, 0.15, "Acme"), Token(0.3, 0.1, 0.4, 0.15, "$5.00")],
```
with:
```python
    sample = Sample(
        id=0,
        words=[Word(0.1, 0.1, 0.2, 0.15, "Acme"), Word(0.3, 0.1, 0.4, 0.15, "$5.00")],
```

(The two `Cell(... token_ids=[...])` calls became `word_ids=[...]` via Step 1's `sed`.)

- [ ] **Step 4: Update `test_regions.py` — `Token`→`Word`**

In `harness/tests/test_regions.py`, find the import of `Token` from `tablelab.artifacts` and the `Token(x0=0.1, ...)` usage at line ~62. Replace `Token` with `Word` in both the import line and the construction. Concretely, change:

```python
        tokens=[Token(x0=0.1, y0=0.1, x1=0.2, y1=0.2, text="x")],
```
to:
```python
        words=[Word(x0=0.1, y0=0.1, x1=0.2, y1=0.2, text="x")],
```
and update its `from tablelab.artifacts import ... Token ...` to `... Word ...`. (This is a `Sample(...)` literal, so the keyword `tokens=`→`words=` too.)

Run to find the exact lines first: `cd harness && grep -n "Token\|tokens=" tests/test_regions.py`

- [ ] **Step 5: Repurpose `test_spanning.py` — drop the `multi_token` param/flag**

In `harness/tests/test_spanning.py`, change the helper signature (`test_spanning.py:18`):

```python
def _grouped_class(page=(800, 800), multi_token=False, **over):
```
to:
```python
def _grouped_class(page=(800, 800), **over):
```
and its structure construction (`test_spanning.py:33`):

```python
        structure=StructureSpec(header=True, multi_token=multi_token),
```
to:
```python
        structure=StructureSpec(header=True),
```

Replace the flag-specific banner test (`test_spanning.py:120-141`, the `# ---- multi_token banner split ----` section through `test_multi_token_splits_banner_label`) with a no-flag version. Replace:

```python
# ---- multi_token banner split ----

def test_multi_token_splits_banner_label():
    dc = fork(
        classlib.get("eob"),
        structure=StructureSpec(header=True, multi_token=True),
    )
    tokens, cells, _regions = placed(dc)
    # One banner cell for "Patient Responsibility" with two word_ids
    bc = next(c for c in cells_where(cells, role="group_header")
              if text_of(tokens, c) == "Patient Responsibility")
    words = [tokens[i].text for i in bc.word_ids]
    assert words == ["Patient", "Responsibility"]
    rects = {tokens[i].cell for i in bc.word_ids}
    assert len(rects) == 1
    seqs = [tokens[i].seq for i in bc.word_ids]
    assert seqs == [0, 1]
```

with (note: the exact pre-`sed` text differs; after Step 1 `token_ids` is already `word_ids`. Match whatever the file currently shows and rewrite the function body to drop the flag):

```python
# ---- grouped-header banners always split into words ----

def test_banner_label_splits_into_words():
    # No flag: the eob class emits word-level tokens, so a multi-word banner
    # ("Patient Responsibility") is two words sharing one cell rect, in seq order.
    dc = classlib.get("eob")
    tokens, cells, _regions = placed(dc)
    bc = next(c for c in cells_where(cells, role="group_header")
              if text_of(tokens, c) == "Patient Responsibility")
    words = [tokens[i].text for i in bc.word_ids]
    assert words == ["Patient", "Responsibility"]
    rects = {tokens[i].cell for i in bc.word_ids}
    assert len(rects) == 1
    seqs = [tokens[i].seq for i in bc.word_ids]
    assert seqs == [0, 1]
```

Then drop the now-unused `fork` / `StructureSpec` imports **only if** nothing else in the file uses them. Check first: `cd harness && grep -n "fork\|StructureSpec" tests/test_spanning.py` — `StructureSpec` is still used by `_grouped_class`, so keep it; remove `fork` from the import list only if it has no remaining references.

- [ ] **Step 6: Repurpose `test_capacity.py` — drop `multi_token=True`**

In `harness/tests/test_capacity.py`, change the `_full_eob` structure override (`test_capacity.py:29-31`):

```python
        structure=replace(
            dc.structure, header=True, multi_token=True, background=4
        ),
```
to:
```python
        structure=replace(
            dc.structure, header=True, background=4
        ),
```

(The `PlacedToken(...)` usages at lines ~235/254 became `PlacedWord(...)` via Step 1's `sed`.)

- [ ] **Step 7: Repurpose `test_multi_table.py` — drop the flag, keep the split assertion**

In `harness/tests/test_multi_table.py`, replace the flag test (`test_multi_table.py:86-89`):

```python
def test_instances_compose_with_multi_token():
    _tokens, cells, regions = placed(_instanced(2, 2, multi_token=True), seed=7)

    multi_data_cells = [c for c in cells_where(cells, role="data") if len(c.word_ids) > 1]
```
with:
```python
def test_instances_compose_with_word_split():
    # Word-level tokens are now universal: multi-word data values (invoice
    # descriptions) split across stacked instances without any flag.
    _tokens, cells, regions = placed(_instanced(2, 2), seed=7)

    multi_data_cells = [c for c in cells_where(cells, role="data") if len(c.word_ids) > 1]
```

(Keep the rest of that test body unchanged — the `multi_data_cells` assertions still hold since invoice descriptions are multi-word.)

- [ ] **Step 8: Repurpose `test_header.py` — drop the flag**

In `harness/tests/test_header.py`, replace the flag test (`test_header.py:46-54`):

```python
def test_header_with_multi_token_splits_header_text():
    dc = _invoice(header=True, multi_token=True)
    tokens, cells, _regions = placed(dc, seed=7)
    # "Unit Price" (field 2) → one header cell with two word_ids
```
with:
```python
def test_header_splits_multiword_header_text():
    dc = _invoice(header=True)
    tokens, cells, _regions = placed(dc, seed=7)
    # "Unit Price" (field 2) → one header cell with two word_ids
```

(Keep the rest of the test body unchanged.)

- [ ] **Step 9: Delete `test_multi_token.py` and create `test_word_split.py`**

Delete the old flag test file:

```bash
rm harness/tests/test_multi_token.py
```

Create `harness/tests/test_word_split.py` with:

```python
from __future__ import annotations

import random

from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, cells_where


def test_every_word_is_space_free():
    # The consistency guarantee: every emitted observable is a single OCR-style word.
    for cls in ("invoice", "eob", "receipt"):
        tokens, _cells, _regions = placed(classlib.get(cls), seed=7)
        assert all(" " not in (t.text or "") for t in tokens), cls


def test_multiword_cells_split_with_contiguous_seq():
    # No flag involved: multi-word cells (invoice descriptions) emit one word per
    # word, in contiguous within-cell reading order.
    tokens, cells, _regions = placed(classlib.get("invoice"), seed=7)
    data_cells = cells_where(cells, role="data")
    assert any(len(c.word_ids) > 1 for c in data_cells)
    for c in data_cells:
        if len(c.word_ids) > 1:
            seqs = [tokens[i].seq for i in c.word_ids]
            assert seqs == list(range(len(seqs)))


def test_multiword_boxes_in_cell_disjoint_and_anchored():
    dc = classlib.get("invoice")
    rng = random.Random(7)
    tokens, cells, _regions = placed(dc, seed=7)
    p_tokens = layout(dc, rng)
    _img, boxes = render(p_tokens, dc)

    multiword_seen = False
    for c in cells_where(cells, role="data"):
        if len(c.word_ids) < 2:
            continue
        multiword_seen = True
        tids = c.word_ids
        cx0, cy0, cx1, cy1 = tokens[tids[0]].cell
        align = tokens[tids[0]].align
        bxs = [boxes[i] for i in tids]
        for b in bxs:
            assert cy0 - 1 <= b[1] and b[3] <= cy1 + 1
        for a, b in zip(bxs, bxs[1:]):
            assert b[0] >= a[2] - 1
        if align == "right":
            assert bxs[-1][2] <= cx1 + 1
        else:
            assert bxs[0][0] >= cx0 - 1
    assert multiword_seen
```

- [ ] **Step 10: Confirm no stale identifiers remain in tests**

Run: `cd harness && grep -rn "multi_token\|PlacedToken\|token_ids\|Token(\|\.tokens\b\|tokens=\[Token" tests/`
Expected: no output. (If `tokens` appears as a *local variable name* — e.g. `tokens, cells, _regions = placed(...)` — that is fine and not matched by these patterns.)

---

## Task 7: Regenerate the golden fixture

**Files:**
- Modify: `harness/tests/test_golden.py`
- Regenerate: `harness/tests/golden/invoice_seed7_n3.json`

- [ ] **Step 1: Update `_gen` to emit `words`/`word_ids` keys**

In `harness/tests/test_golden.py`, replace (`test_golden.py:20-30`):

```python
        tokens = [{"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
                   "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4), "text": p.text}
                  for p, b in zip(placed, boxes)]
        out.append({
            "tokens": tokens,
            "cells": [{"region_index": c.region_index, "row_index": c.row_index,
                       "column_index": c.column_index, "span": list(c.span),
                       "role": c.role, "field": c.field, "token_ids": c.token_ids}
                      for c in cells],
            "regions": [{"type": r.type, "name": r.name, "index": r.index} for r in regions],
        })
```
with:
```python
        words = [{"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
                  "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4), "text": p.text}
                 for p, b in zip(placed, boxes)]
        out.append({
            "words": words,
            "cells": [{"region_index": c.region_index, "row_index": c.row_index,
                       "column_index": c.column_index, "span": list(c.span),
                       "role": c.role, "field": c.field, "word_ids": c.word_ids}
                      for c in cells],
            "regions": [{"type": r.type, "name": r.name, "index": r.index} for r in regions],
        })
```

- [ ] **Step 2: Regenerate the golden JSON from the updated generator**

Run:

```bash
cd harness && uv run python -c "
import json, sys
sys.path.insert(0, 'tests')
from pathlib import Path
from test_golden import _gen
Path('tests/golden/invoice_seed7_n3.json').write_text(
    json.dumps(_gen('invoice', 7, 3), indent=2) + '\n')
print('regenerated')
"
```
Expected: `regenerated`.

- [ ] **Step 3: Sanity-check the regenerated fixture (keys + word-split)**

Run:

```bash
cd harness && uv run python -c "
import json
d = json.loads(open('tests/golden/invoice_seed7_n3.json').read())
assert 'words' in d[0] and 'tokens' not in d[0], d[0].keys()
assert all('word_ids' in c for c in d[0]['cells'])
assert all(' ' not in w['text'] for s in d for w in s['words'])
print('words/sample:', [len(s['words']) for s in d])
"
```
Expected: prints per-sample word counts (higher than the old per-cell token counts; e.g. multi-word descriptions split) and no assertion error.

- [ ] **Step 4: Confirm the golden test passes**

Run: `cd harness && uv run pytest tests/test_golden.py -q`
Expected: PASS.

---

## Task 8: Full verification — pytest + build smoke

**Files:** none (verification only).

- [ ] **Step 1: Run the full Python suite**

Run: `cd harness && uv run pytest -q`
Expected: all green, no `multi_token`/`Token`/`token_ids` import or attribute errors.

- [ ] **Step 2: Build all three classes and assert the contract guarantees**

Run:

```bash
cd harness && uv run python -c "
import tempfile, pathlib
from tablelab import classes as classlib
from tablelab.build import build_dataset
from tablelab.artifacts import read_dataset, validate_dataset_dir
for cls in ('invoice', 'eob', 'receipt'):
    with tempfile.TemporaryDirectory() as d:
        build_dataset(d, cls, classlib.get(cls), seed=7, n=3)
        ds = pathlib.Path(d) / cls
        assert validate_dataset_dir(ds) == [], validate_dataset_dir(ds)  # schema_version == 4
        _m, samples = read_dataset(ds)
        for s in samples:
            for w in s.words:
                assert ' ' not in (w.text or ''), (cls, w.text)
            claimed = {i for c in s.cells for i in c.word_ids}
            assert claimed.issubset(range(len(s.words)))
        print(cls, 'ok', sum(len(s.words) for s in samples), 'words')
"
```
Expected: three `... ok N words` lines, no assertion errors. Confirms schema v4 on disk, every word space-free, and `word_ids` index valid words.

- [ ] **Step 3: Confirm `samples.json` uses the new keys on disk**

Run:

```bash
cd harness && uv run python -c "
import tempfile, pathlib, json
from tablelab import classes as classlib
from tablelab.build import build_dataset
with tempfile.TemporaryDirectory() as d:
    build_dataset(d, 'receipt', classlib.get('receipt'), seed=7, n=1)
    j = json.loads((pathlib.Path(d)/'receipt'/'samples.json').read_text())
    assert j['schema_version'] == 4
    s0 = j['samples'][0]
    assert 'words' in s0 and 'tokens' not in s0
    assert all('word_ids' in c and 'token_ids' not in c for c in s0['cells'])
    print('on-disk keys ok')
"
```
Expected: `on-disk keys ok`.

- [ ] **Step 4: Commit the harness change**

```bash
git add harness/ docs/plans/2026-06-18-atomic-word-tokens.md
git commit -m "feat(contract): atomic word tokens; rename Token->Word (schema v4)

Retire StructureSpec.multi_token / --multi-token: every cell now emits one
Word per whitespace word. Rename Token->Word, Sample.tokens->words,
Cell.token_ids->word_ids. SCHEMA_VERSION 3->4. Regenerate golden.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Viewer — `Token`→`Word` types + props

**Files:**
- Modify: `viewer/src/types.ts`
- Modify: `viewer/src/App.tsx`
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/MetaPanel.tsx`

- [ ] **Step 1: Rename the `Token` interface and `Sample.tokens` / `Cell.token_ids` in `types.ts`**

In `viewer/src/types.ts`, change the header comment (`types.ts:1`):

```typescript
// ---- Artifact schema types (mirrors runs/ and datasets/ JSON contract v3) ----
```
to:
```typescript
// ---- Artifact schema types (mirrors runs/ and datasets/ JSON contract v4) ----
```

Rename the interface (`types.ts:7-13`):

```typescript
export interface Token {
  x0: number
  y0: number
  x1: number
  y1: number
  text: string | null
}
```
to:
```typescript
export interface Word {
  x0: number
  y0: number
  x1: number
  y1: number
  text: string | null
}
```

Rename `Cell.token_ids` (`types.ts:26`):

```typescript
  token_ids: number[]
```
to:
```typescript
  word_ids: number[]
```

Rename `Sample.tokens` (`types.ts:41`):

```typescript
  tokens: Token[]
```
to:
```typescript
  words: Word[]
```

- [ ] **Step 2: Rebuild the cell map and iterate words in `DocumentViewer.tsx`**

In `viewer/src/DocumentViewer.tsx`, destructure `words` (`DocumentViewer.tsx:293`):

```typescript
  const { tokens, cells, image } = sample
```
to:
```typescript
  const { words, cells, image } = sample
```

Replace the cell map (`DocumentViewer.tsx:296-302`):

```typescript
  // Build token → owning cell map
  const cellByToken = new Map<number, Cell>()
  for (const cell of (cells ?? [])) {
    for (const tokenId of cell.token_ids) {
      cellByToken.set(tokenId, cell)
    }
  }
```
with:
```typescript
  // Build word → owning cell map
  const cellByWord = new Map<number, Cell>()
  for (const cell of (cells ?? [])) {
    for (const wordId of cell.word_ids) {
      cellByWord.set(wordId, cell)
    }
  }
```

Replace the overlay iteration (`DocumentViewer.tsx:412-419`):

```typescript
            {tokens.map((tok, i) => {
              const sel = i === selectedTokenIdx
              const role = cellByToken.get(i)?.role
              const { fill, stroke } = tokenColors(role, sel)
              const x = tok.x0 * width
              const y = tok.y0 * height
              const w = (tok.x1 - tok.x0) * width
              const h = (tok.y1 - tok.y0) * height
```
with:
```typescript
            {words.map((word, i) => {
              const sel = i === selectedTokenIdx
              const role = cellByWord.get(i)?.role
              const { fill, stroke } = tokenColors(role, sel)
              const x = word.x0 * width
              const y = word.y0 * height
              const w = (word.x1 - word.x0) * width
              const h = (word.y1 - word.y0) * height
```

(The `selectedTokenIdx` / `onSelectToken` prop names are left unchanged — they index words now, but renaming them is cosmetic and would ripple through `App.tsx`/`MetaPanel.tsx` props without behavior change. Keep them.)

- [ ] **Step 3: Read `sample.words` and relabel in `MetaPanel.tsx`**

In `viewer/src/MetaPanel.tsx`, relabel the section title (`MetaPanel.tsx:242`):

```tsx
        <div className="meta-section-title">Selected token</div>
```
to:
```tsx
        <div className="meta-section-title">Selected word</div>
```

Replace the lookup (`MetaPanel.tsx:246-247`):

```tsx
          const token = sample?.tokens[selectedTokenIdx]
          const cell = sample?.cells.find(c => c.token_ids.includes(selectedTokenIdx))
```
with:
```tsx
          const token = sample?.words[selectedTokenIdx]
          const cell = sample?.cells.find(c => c.word_ids.includes(selectedTokenIdx))
```

(The local `token` variable and `selectedTokenIdx` prop are left named as-is — cosmetic only.)

- [ ] **Step 4: Confirm `App.tsx` needs no change**

`App.tsx` references only `selectedTokenIdx` / `setSelectedTokenIdx` (kept) and `samples` (untyped pass-through). No edit required. Verify:

Run: `cd viewer && grep -n "\.tokens\|token_ids\|: Token\b\|<Token" src/App.tsx`
Expected: no output.

- [ ] **Step 5: Build the viewer**

Run: `npm --prefix viewer run build`
Expected: clean TypeScript build, no `Token` / `tokens` / `token_ids` type errors.

- [ ] **Step 6: Commit the viewer change**

```bash
git add viewer/
git commit -m "feat(viewer): read v4 schema (Word/words/word_ids)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Docs — AGENTS.md + CHARTER.md

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/CHARTER.md`

- [ ] **Step 1: Update the "Contract is the seam" line in `AGENTS.md`**

In `AGENTS.md`, replace the seam bullet (`AGENTS.md:51`):

```
- **Contract is the seam** (`schema_version = 3`, defined in `artifacts.py`): observables (per-token
  `bbox` + `text`, per-sample `image`) are locked; the annotation layer is structured as typed
  `Region`s (`type`/`name`/`index`/`bbox`) and `Cell`s (`region_index`/`row_index`/`column_index`/
  `span`/`bbox`/`role`/`field`/`token_ids`); tokens are pure observables with no per-token label.
```
with:
```
- **Contract is the seam** (`schema_version = 4`, defined in `artifacts.py`): observables (per-`Word`
  `bbox` + `text`, per-sample `image`) are locked; words are atomic OCR/Textract-style words (one per
  whitespace word, no opt-in splitting); the annotation layer is structured as typed `Region`s
  (`type`/`name`/`index`/`bbox`) and `Cell`s (`region_index`/`row_index`/`column_index`/`span`/`bbox`/
  `role`/`field`/`word_ids`); words are pure observables with no per-word label.
```

- [ ] **Step 2: Update the `multi_token` line in the "Built" narrative**

In `AGENTS.md`, replace (`AGENTS.md:64`):

```
multi-token cells (`StructureSpec.multi_token` → per-word tokens sharing record/field + `seq`);
```
with:
```
atomic word tokens (every cell emits one `Word` per whitespace word, sharing the cell's record/field
+ `seq`; the old `StructureSpec.multi_token` opt-in was retired in schema v4);
```

- [ ] **Step 3: Update the schema callout block in `AGENTS.md`**

In `AGENTS.md`, the callout currently says the contract is **Region / Cell / Token** at schema v3 (`AGENTS.md:81-86`). Replace the references `Token`→`Word`, `token_ids`→`word_ids`, and note schema v4. Concretely, change the phrase:

```
> `{subtotal}`) are historical: the contract is now **Region / Cell / Token**
> (`docs/specs/2026-06-15-region-cell-token-schema-design.md`). Tokens are pure observables
> (`bbox` + `text`); structure + meaning live on `Cell`s (`row_index`/`column_index`/`span` + `role` ∈
> header/group_header/data/section/summary/key/value + `field`) grouped under typed `Region`s
> (table/form, `type`/`name`/`index`). Globals → a `form` region; background → cell-less tokens.
```
to:
```
> `{subtotal}`) are historical: the contract is now **Region / Cell / Word** (schema v4;
> `docs/specs/2026-06-15-region-cell-token-schema-design.md` +
> `docs/specs/2026-06-17-atomic-word-tokens-design.md`). Words are pure, atomic observables
> (`bbox` + `text`, one per whitespace word); structure + meaning live on `Cell`s
> (`row_index`/`column_index`/`span` + `role` ∈ header/group_header/data/section/summary/key/value +
> `field`, grouping words via `word_ids`) grouped under typed `Region`s (table/form,
> `type`/`name`/`index`). Globals → a `form` region; background → cell-less words.
```

- [ ] **Step 4: Update the Textract-mirror line in `docs/CHARTER.md`**

In `docs/CHARTER.md`, replace (`CHARTER.md:53`):

```
The structural schema mirrors Textract (`Region`/`Cell`/`Token` ≈ `LAYOUT`/`CELL`/`WORD`) on purpose:
```
with:
```
The structural schema mirrors Textract (`Region`/`Cell`/`Word` ≈ `LAYOUT`/`CELL`/`WORD`) on purpose:
```

- [ ] **Step 5: Confirm no stale contract terms remain in the docs**

Run: `cd /Users/zebulonperrin/IdeaProjects/autoresearch-fork && grep -n "schema_version = 3\|token_ids\|Region / Cell / Token\|Cell`/`Token`" AGENTS.md docs/CHARTER.md`
Expected: no output for the seam/contract lines (any remaining historical `Token` mentions in deep-history prose are acceptable, but the contract-defining lines above must be updated).

- [ ] **Step 6: Commit the docs change**

```bash
git add AGENTS.md docs/CHARTER.md
git commit -m "docs: contract is Region/Cell/Word at schema v4 (atomic words)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: Final verification

**Files:** none.

- [ ] **Step 1: Full suite once more**

Run: `cd harness && uv run pytest -q`
Expected: all green.

- [ ] **Step 2: Viewer build once more**

Run: `npm --prefix viewer run build`
Expected: clean.

- [ ] **Step 3: Live viewer check (manual, per spec)**

Build a v4 dataset into `datasets/` and start the dev server:

```bash
cd harness && uv run python -m tablelab.cli build --class eob --n 4 --out ../datasets/wordsplit-eob-v4
npm --prefix ../viewer run dev
```
Then at http://localhost:5173 select `wordsplit-eob-v4` and confirm: multi-word headers/banners (e.g. "Patient Responsibility", "Service Date") render as **separate** word boxes; clicking a word shows its cell/region detail under "Selected word".

- [ ] **Step 4: Confirm the working tree is clean (everything committed)**

Run: `git status`
Expected: clean (the `datasets/wordsplit-eob-v4` from Step 3 is gitignored, so it does not appear).

---

## Self-Review

**Spec coverage** (against `docs/specs/2026-06-17-atomic-word-tokens-design.md` §Changes + §Verification):

- `artifacts.py` (SCHEMA_VERSION=4, `Token`→`Word`, `Sample.words`, `Cell.word_ids`, `_word_from_dict`, `_sample_from_dict` reads `words`/`word_ids`) → **Task 1**.
- `layout.py` (`PlacedToken`→`PlacedWord`, `_emit_tokens`→`_emit_words` always-split, drop `multi` threading, keep wrapped path, return `(words, cells, regions)`, `word_ids` resolution) → **Task 2**.
- `render.py` (takes word list, group by rect, `seq` order, drop legacy comment) → **Task 3**.
- `build.py` (`Word(...)`, `Sample(words=...)`, `Cell.word_ids` pass-through, normalize bboxes) → **Task 4**.
- `specs.py` (remove `StructureSpec.multi_token` + docstring) → **Task 5 Steps 1**.
- `cli.py` (remove `--multi-token` + plumbing; `inspect` reads words) → **Task 5 Steps 2-3**.
- `classes.py` (no `multi_token` kwargs) → **Task 5 Step 4** (verify-only).
- Tests (`_cells.py` rename; repurpose `test_multi_token.py` → universal split; sweep `.tokens`/`token_ids`/`multi_token`/`Token(`; counts change) → **Task 6**.
- Golden (`test_golden.py` keys + regenerate `invoice_seed7_n3.json`) → **Task 7**.
- Viewer (`types.ts`, `App.tsx`, `DocumentViewer.tsx`, `MetaPanel.tsx`) → **Task 9**.
- Docs (`AGENTS.md`; plus `CHARTER.md` which the spec's prose implies via the Textract mirror) → **Task 10**.
- Verification (pytest green; no-space guarantee; schema_version==4; on-disk `words`/`word_ids`; golden pinned; viewer build + live check) → **Tasks 7-8, 11**.

**Placeholder scan:** No `TBD`/`handle edge cases`/"write tests for the above" — every code step shows full code; every run step shows the command + expected output.

**Type consistency:** `Word`/`words`/`word_ids` used uniformly across artifacts, build, tests, golden, viewer; `PlacedWord` used in layout + render; `_emit_words(placed, text, rect, align, font_size)` signature matches all call sites (globals, group-header, header, span-row, data); `_emit_span_row(..., role, font, rng)` (no `multi`) matches both the section and totals calls. Transient `PlacedCell.tokens` / local `toks` intentionally retained (documented in the header), so the out-cell builder reads `c.tokens` while emitting `word_ids` — consistent within Task 2.
