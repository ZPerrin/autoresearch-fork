# Region / Cell / Token Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the artifact contract from per-token semantic labels into a three-layer `Region` / `Cell` / `Token` model (`schema_version 2 → 3`), so structural indices and semantic field labels live on cells/regions and tokens are pure observables — the foundation the labels milestone needs.

**Architecture:** `layout` emits three lists — pure-observable `PlacedToken`s, `PlacedCell`s carrying structural+semantic truth plus the token refs they own, and typed `PlacedRegion`s. `build` normalizes and serializes them onto `Sample`. The renderer is unaffected (it never read labels). Tokens are shuffled to mimic unordered OCR, so cell→token references are resolved to final indices *after* the shuffle.

**Tech Stack:** Python 3.10+, `uv`, dataclasses, Pillow (render), pytest. Spec: `docs/specs/2026-06-15-region-cell-token-schema-design.md`. Project rule (AGENTS.md): **no strict TDD — implement, then verify by running**; the existing 133-test suite is the regression net.

---

## Project conventions (read before starting)

- Run everything from `harness/`: `cd harness && uv run pytest -q`.
- Commit style: conventional commits; this is `master`-direct infra work (project convention). End commit messages with the `Co-Authored-By` trailer.
- "Verify by running" means: after each task, run the named command and read the output before moving on. Do not claim a task done without the command output.

## File structure (what changes and why)

- `harness/src/tablelab/artifacts.py` — **contract**: `Token` slims to observables; new `Cell`; `Region` gains `type`/`name`/`index`; `Sample` gains `cells`; `SCHEMA_VERSION = 3`; read/write round-trip the new shape.
- `harness/src/tablelab/layout.py` — **placement**: `PlacedToken` drops `label`; new `PlacedCell`; `PlacedRegion` gains `type`/`name`/`index`; emission sites build cells; `layout_with_regions` returns `(tokens, cells, regions)`; cell token refs resolved to indices post-shuffle.
- `harness/src/tablelab/build.py` — **assembly**: unpack three lists, normalize bboxes to `[0,1]`, assemble `Sample(tokens, cells, regions)`.
- `harness/src/tablelab/render.py` — **unaffected** (verify only): it groups by `PlacedToken.cell`, never reads `.label`.
- `harness/tests/*` — migrate label-shape assertions to cell-shape via a new shared helper; regenerate the golden fixture.
- Viewer (`viewer/src/*`) — separate follow-on plan (see end). The Python side ships and tests green on its own.

---

### Task 1: Contract dataclasses (`artifacts.py`)

**Files:**
- Modify: `harness/src/tablelab/artifacts.py` (`SCHEMA_VERSION`, `Token`, new `Cell`, `Region`, `Sample`, `_sample_from_dict`)
- Test: `harness/tests/test_contract_roundtrip.py` (new)

- [ ] **Step 1: Update the contract types**

In `harness/src/tablelab/artifacts.py`, set `SCHEMA_VERSION = 3` and replace the `Token`, `Region`, `Sample` definitions (currently lines 6–31) with:

```python
SCHEMA_VERSION = 3


@dataclass
class Token:
    x0: float; y0: float; x1: float; y1: float
    text: str | None = None


@dataclass
class Cell:
    region_index: int                      # flat index into Sample.regions
    row_index: int                         # 0-based visual row within the region
    column_index: int                      # 0-based visual column (leftmost for spanning cells)
    span: list[int]                        # [colspan, rowspan]
    bbox: list[float]                      # normalized [0,1] (x0, y0, x1, y1)
    role: str                              # header|group_header|data|section|summary|key|value
    field: str | None = None               # template slot name (FieldSpec.name); None for span/group rows
    token_ids: list[int] = field(default_factory=list)


@dataclass
class Region:
    type: str                              # "table" | "form" | "footer" | …
    name: str | None                       # table name ("claim_line"); "globals" for the form
    index: int                             # instance ordinal, scoped per (type, name)
    bbox: list[float]                      # normalized [0,1] (x0, y0, x1, y1)


@dataclass
class Sample:
    id: int
    tokens: list[Token]
    image: str | None = None
    width: int | None = None
    height: int | None = None
    cells: list[Cell] = field(default_factory=list)
    regions: list[Region] | None = None
```

- [ ] **Step 2: Update the deserializer**

Replace `_sample_from_dict` (currently lines 81–86) with:

```python
def _sample_from_dict(d: dict) -> Sample:
    raw_regions = d.get("regions")
    regions = [Region(**r) for r in raw_regions] if raw_regions is not None else None
    cells = [Cell(**c) for c in d.get("cells", [])]
    return Sample(id=d["id"], tokens=[_token_from_dict(t) for t in d["tokens"]],
                  image=d.get("image"), width=d.get("width"), height=d.get("height"),
                  cells=cells, regions=regions)
```

(`_token_from_dict` stays `Token(**d)` — the slimmer `Token` ignores nothing extra because we control the writer.)

- [ ] **Step 3: Add a round-trip test**

Create `harness/tests/test_contract_roundtrip.py`:

```python
from pathlib import Path
from tablelab.artifacts import (Sample, Token, Cell, Region, DatasetManifest,
                                write_dataset, read_dataset, SCHEMA_VERSION)


def test_schema_version_is_3():
    assert SCHEMA_VERSION == 3


def test_sample_with_cells_and_regions_roundtrips(tmp_path: Path):
    sample = Sample(
        id=0,
        tokens=[Token(0.1, 0.1, 0.2, 0.15, "Acme"), Token(0.3, 0.1, 0.4, 0.15, "$5.00")],
        width=1000, height=1400, image="/datasets/x/images/0.png",
        cells=[
            Cell(region_index=0, row_index=0, column_index=0, span=[1, 1],
                 bbox=[0.1, 0.1, 0.2, 0.15], role="data", field="description", token_ids=[0]),
            Cell(region_index=0, row_index=0, column_index=1, span=[1, 1],
                 bbox=[0.3, 0.1, 0.4, 0.15], role="data", field="amount", token_ids=[1]),
        ],
        regions=[Region(type="table", name="line_item", index=0, bbox=[0.1, 0.1, 0.4, 0.15])],
    )
    manifest = DatasetManifest(dataset_id="x", generator_version=1, task="grid_record_field",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got == [sample]
```

- [ ] **Step 4: Run it**

Run: `cd harness && uv run pytest tests/test_contract_roundtrip.py -q`
Expected: PASS (3 assertions across 2 tests). The rest of the suite will fail until later tasks — that is expected.

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/artifacts.py harness/tests/test_contract_roundtrip.py
git commit -m "feat(contract): Region/Cell/Token schema v3 (round-trips)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Layout placement types + helpers (`layout.py`)

**Files:**
- Modify: `harness/src/tablelab/layout.py` (`PlacedToken` lines 121–129, `PlacedRegion` lines 132–136, `_emit`/`_emit_span_row` lines 189–234)

- [ ] **Step 1: Replace the placement dataclasses**

Replace `PlacedToken` (lines 121–129) and `PlacedRegion` (lines 132–136) with:

```python
@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # render rect in page px (x0, y0, x1, y1)
    align: str = "left"
    font_size: int = 22
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class PlacedCell:
    region_index: int
    row_index: int
    column_index: int
    span: tuple[int, int]                      # (colspan, rowspan)
    bbox: tuple[float, float, float, float]    # cell rect in page px
    role: str
    field: str | None
    tokens: list[PlacedToken] = field(default_factory=list)   # transient refs; resolved to ids on return


@dataclass
class PlacedRegion:
    type: str
    name: str | None
    index: int
    bbox: tuple[float, float, float, float]    # page px
```

Add `field` to the dataclasses import at the top: change `from dataclasses import dataclass, replace` to `from dataclasses import dataclass, field, replace`.

- [ ] **Step 2: Replace `_emit` with a token-returning helper**

Replace `_emit` (lines 189–209; note both the docstring-only fragment at 189 and the body) with a helper that returns the tokens it appended so a caller can attach them to a cell:

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
    for word in words:
        tok = PlacedToken(text=word, cell=rect, align=align, font_size=font_size)
        placed.append(tok)
        new.append(tok)
    return new
```

- [ ] **Step 3: Replace `_emit_span_row` to build cells**

`_emit_span_row` now also appends `PlacedCell`s. Replace it (lines 212–234) with:

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

(Note: the `header_on_text` flag is gone — `role` now distinguishes the totals row, so the old "header=True on the TOTALS literal" is replaced by `role="summary"` on every totals cell.)

- [ ] **Step 4: Run import smoke**

Run: `cd harness && uv run python -c "import tablelab.layout"`
Expected: a `NameError`/usage error is still possible because callers below aren't updated yet — but the module-level dataclass/helper definitions must import cleanly. If it errors inside `layout_with_regions` references, that's fixed in Task 3. To isolate: `uv run python -c "from tablelab.layout import PlacedCell, PlacedRegion, _emit_tokens, _emit_span_row; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat(layout): PlacedCell + cell-aware emission helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Layout emission refactor + new return signature (`layout.py`)

**Files:**
- Modify: `harness/src/tablelab/layout.py` (`layout_with_regions` body lines 522–673, `layout` wrapper lines 676–678)

This rewrites the body to build `cells` and `regions`, drop the per-token `label`, and resolve token refs to indices after the shuffle.

- [ ] **Step 1: Rewrite `layout_with_regions`**

Replace the body from `placed: list[PlacedToken] = []` (line 540) through `return placed, regions` (line 673) with:

```python
    placed: list[PlacedToken] = []
    cells: list[PlacedCell] = []
    regions: list[PlacedRegion] = []
    y = float(my)

    if dc.globals:
        form_index = len(regions)
        g_y0 = y
        gpr = max(L.globals_per_row, 1)
        usable = W - 2 * mx
        pair_w = usable / gpr
        for i, f in enumerate(dc.globals):
            col = i % gpr
            if i and col == 0:
                y += L.row_h
            px0 = mx + col * pair_w
            gw = pair_w * 0.35
            label_rect = (px0, y, px0 + gw, y + L.row_h)
            toks = _emit_tokens(placed, _header_text(f.name) + ":", label_rect,
                                "left", dc.render.font_size, multi)
            cells.append(PlacedCell(region_index=form_index, row_index=i // gpr,
                                    column_index=2 * col, span=(1, 1), bbox=label_rect,
                                    role="key", field=f.name, tokens=toks))
            value_rect = (px0 + gw, y, px0 + pair_w, y + L.row_h)
            toks = _emit_tokens(placed, sample(f.type, rng), value_rect,
                                "left", dc.render.font_size, multi)
            cells.append(PlacedCell(region_index=form_index, row_index=i // gpr,
                                    column_index=2 * col + 1, span=(1, 1), bbox=value_rect,
                                    role="value", field=f.name, tokens=toks))
        y += L.row_h
        regions.append(PlacedRegion(type="form", name="globals", index=0,
                                    bbox=(mx, g_y0, W - mx, y)))
        y += _section_gap(dc)

    name_counts: dict[str, int] = {}
    for table, table_shape in zip(dc.tables, shape):
        if not table_shape:
            continue
        C = len(table.fields)
        explicit_widths = all(f.width is not None for f in table.fields)
        for rows in table_shape:
            y_start = y
            region_index = len(regions)
            row_idx = 0
            grid = [[_sample_cell(table.fields[c], rng) for c in range(C)]
                    for _ in range(rows)]
            cell_font = dc.render.font_size
            if dc.render.autoscale_font and not explicit_widths:
                cell_font = _fit_font(table.fields, W - 2 * mx, L.pad, header,
                                      grid, dc.render.font_size)
            edges = _resolve_column_edges(table.fields, W - 2 * mx, mx, L.pad,
                                          header, grid, cell_font)
            if header and any(f.group for f in table.fields):
                for name, c0, c1 in _group_runs(table.fields):
                    rect = (edges[c0], y, edges[c1 + 1], y + L.row_h)
                    toks = _emit_tokens(placed, name, rect, "left", cell_font, multi)
                    cells.append(PlacedCell(region_index=region_index, row_index=row_idx,
                                            column_index=c0, span=(c1 - c0 + 1, 1), bbox=rect,
                                            role="group_header", field=None, tokens=toks))
                y += L.row_h
                row_idx += 1
            if header:
                for c in range(C):
                    f = table.fields[c]
                    rect = (edges[c], y, edges[c + 1], y + L.row_h)
                    toks = _emit_tokens(placed, _header_text(f.name), rect, f.align,
                                        cell_font, multi)
                    cells.append(PlacedCell(region_index=region_index, row_index=row_idx,
                                            column_index=c, span=(1, 1), bbox=rect,
                                            role="header", field=f.name, tokens=toks))
                y += L.row_h
                row_idx += 1
            if table.section is not None:
                _emit_span_row(placed, cells, table.section.cells, edges, y, L.row_h,
                               region_index, row_idx, "section", cell_font, multi, rng)
                y += L.row_h
                row_idx += 1
            line_h = _line_h(dc)
            for r in range(rows):
                row_edges = (jitter_column_edges(edges, J.col_w, rng)
                             if J.col_w > 0 else edges)
                row_lines = 1
                for c in range(C):
                    f = table.fields[c]
                    v = grid[r][c]
                    if f.max_width is not None and v:
                        col_text_w = (row_edges[c + 1] - row_edges[c]) - 2 * L.pad
                        row_lines = max(row_lines, len(_wrap(v.split(), col_text_w, cell_font)))
                base_h = max(L.row_h, row_lines * line_h)
                cell_h = base_h
                gap_after = _row_gap(dc)
                if J.row_h > 0 and _row_gap(dc) > 0 and r < rows - 1:
                    cell_h, delta = jitter_row_height(base_h, J.row_h, _row_gap(dc), rng)
                    gap_after = _row_gap(dc) + delta
                for c in range(C):
                    f = table.fields[c]
                    value = grid[r][c]
                    x0, x1 = row_edges[c], row_edges[c + 1]
                    cell_bbox = (x0, y, x1, y + cell_h)
                    toks: list[PlacedToken] = []
                    if value and f.max_width is not None:
                        col_text_w = (x1 - x0) - 2 * L.pad
                        lines = _wrap(value.split(), col_text_w, cell_font)
                        block_h = len(lines) * line_h
                        top = y + (cell_h - block_h) / 2
                        for k, words in enumerate(lines):
                            ly0 = top + k * line_h
                            line_rect = (x0, ly0, x1, ly0 + line_h)
                            for w in words:
                                tok = PlacedToken(text=w, cell=line_rect, align=f.align,
                                                  font_size=cell_font)
                                placed.append(tok)
                                toks.append(tok)
                    elif value:
                        toks = _emit_tokens(placed, value, cell_bbox, f.align, cell_font, multi)
                    cells.append(PlacedCell(region_index=region_index, row_index=row_idx,
                                            column_index=c, span=(1, 1), bbox=cell_bbox,
                                            role="data", field=f.name, tokens=toks))
                y += cell_h
                if r < rows - 1:
                    y += gap_after
                row_idx += 1
            if table.totals is not None:
                _emit_span_row(placed, cells, table.totals.cells, edges, y, L.row_h,
                               region_index, row_idx, "summary", cell_font, multi, rng)
                y += L.row_h
                row_idx += 1
            idx = name_counts.get(table.name, 0)
            name_counts[table.name] = idx + 1
            regions.append(PlacedRegion(type="table", name=table.name, index=idx,
                                        bbox=(edges[0], y_start, edges[-1], y)))
            y += _instance_gap(dc)

    n_bg = dc.structure.background
    if n_bg:
        columns = min(_BACKGROUND_COLUMNS, n_bg)
        slot_w = (W - 2 * mx) / columns
        for i in range(n_bg):
            row, col = divmod(i, columns)
            x0 = mx + col * slot_w
            rect = (x0, y + row * L.row_h, x0 + slot_w, y + (row + 1) * L.row_h)
            placed.append(PlacedToken(text=background_token(dc.background_terms, rng),
                                      cell=rect, align="left", font_size=dc.render.font_size))

    if J.offset > 0 or J.baseline > 0:
        for p in placed:
            p.dx, p.dy = jitter_offset(J.offset, J.baseline, L.pad, rng)

    rng.shuffle(placed)
    index_of = {id(t): i for i, t in enumerate(placed)}
    out_cells = [
        Cell(region_index=c.region_index, row_index=c.row_index,
             column_index=c.column_index, span=list(c.span), bbox=list(c.bbox),
             role=c.role, field=c.field,
             token_ids=[index_of[id(t)] for t in c.tokens])
        for c in cells
    ]
    return placed, out_cells, regions
```

Add to the top-of-file imports: `from .artifacts import Cell` (so the function can build serializable `Cell`s). Keep `PlacedCell`/`PlacedRegion` for the in-process build.

Notes captured here (do not skip): the `multi_region` conditional is gone (every table cell always references its region); the old wrapped-cell `seq` is gone (order is `token_ids` order); empty/sparse data cells now still emit a `PlacedCell` with `tokens=[]`; token ids are resolved **after** `rng.shuffle`.

- [ ] **Step 2: Update the return type + `layout` wrapper**

Update the `layout_with_regions` signature return annotation to `tuple[list[PlacedToken], list[Cell], list[PlacedRegion]]` and import `Cell` (above). Replace `layout` (lines 676–678):

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Tokens only (back-compat for render/golden helpers)."""
    return layout_with_regions(dc, rng)[0]
```

- [ ] **Step 3: Smoke the three classes**

Run:
```bash
cd harness && uv run python -c "
import random
from tablelab import classes as classlib
from tablelab.layout import layout_with_regions
for name in ('invoice','eob','receipt'):
    toks, cells, regions = layout_with_regions(classlib.get(name), random.Random(7))
    bg = sum(1 for c in cells)
    in_cells = {i for c in cells for i in c.token_ids}
    assert all(0 <= i < len(toks) for i in in_cells), name
    print(name, 'tokens', len(toks), 'cells', len(cells), 'regions',
          [(r.type, r.name, r.index) for r in regions])
"
```
Expected: prints counts for all three with no assertion error; `eob` shows a `('form','globals',0)` region plus one or two `('table','claim_line',k)` regions.

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat(layout): emit cells + typed regions; tokens lose labels

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Build assembly (`build.py`)

**Files:**
- Modify: `harness/src/tablelab/build.py` (imports line 16–17, build loop lines 184–198, `_validate_boxes` if it reads labels)

- [ ] **Step 1: Update imports and the build loop**

Change the import (line 16) to include `Cell`:
`from .artifacts import Sample, Token, Cell, Region, DatasetManifest, write_dataset`
Change the layout import (line 17) to: `from .layout import layout_with_regions, validate_layout_capacity`

Replace the per-sample assembly (lines 184–198) with:

```python
                placed, placed_cells, placed_regions = layout_with_regions(doc_class, rng)
                img, boxes = render(placed, doc_class)
                _validate_boxes(boxes, placed, dataset_id, i, W, H)
                img.save(staging_dir / "images" / f"{i}.png")
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

(`layout_with_regions` already returns serializable `Cell`s with resolved `token_ids`; here we only normalize the cell `bbox` to `[0,1]`. `c.span` is already a list from Task 3 Step 1.)

- [ ] **Step 2: Check `_validate_boxes` does not read `.label`**

Run: `cd harness && grep -n "label" src/tablelab/build.py`
Expected: no matches. If any remain (e.g. in `_validate_boxes`), remove the `.label` reference — it validated box bounds, not labels.

- [ ] **Step 3: Build smoke**

Run: `cd harness && uv run python -m tablelab.cli build --class eob --n 2 --seed 1 --out ../datasets/_v3smoke && uv run python -m tablelab.cli inspect ../datasets/_v3smoke`
Expected: builds 2 samples; `inspect` prints class/task/fields without error. Then:
```bash
cd harness && uv run python -c "
import json; d=json.load(open('../datasets/_v3smoke/samples.json'))
assert d['schema_version']==3
s=d['samples'][0]
print('tokens',len(s['tokens']),'cells',len(s['cells']),'regions',len(s['regions']))
assert all(set(t)<= {'x0','y0','x1','y1','text'} for t in s['tokens']), 'token has stray keys'
"
rm -rf ../datasets/_v3smoke
```
Expected: prints counts; no stray-key assertion. (Remove the smoke dataset — it is gitignored anyway.)

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/build.py
git commit -m "feat(build): assemble v3 Sample(tokens, cells, regions)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Migrate the test suite

The existing tests assert on the old token `label` shape (`record`/`field`/`region`/`header`/`section`/`subtotal`/`global`). They move to asserting on `cells`. Add one shared helper, then migrate file by file, running until green.

**Files:**
- Create: `harness/tests/_cells.py` (shared helper)
- Modify: `harness/tests/test_multi_token.py`, `test_header.py`, `test_background.py`, `test_globals.py`, `test_multi_table.py`, `test_spanning.py`, `test_regions.py`, `test_wrap.py`, `test_capacity.py`, `test_jitter.py`, `test_spacing.py`

- [ ] **Step 1: Add the shared cell helper**

Create `harness/tests/_cells.py`:

```python
"""Test helpers: run layout and query the emitted cells/regions by role/field."""
import random
from tablelab.layout import layout_with_regions


def placed(dc, seed=0):
    """Return (tokens, cells, regions)."""
    return layout_with_regions(dc, random.Random(seed))


def cells_where(cells, **kw):
    """Cells matching all given attributes, e.g. cells_where(cells, role='data', field='amount')."""
    return [c for c in cells if all(getattr(c, k) == v for k, v in kw.items())]


def text_of(tokens, cell):
    """The cell's words joined in token_ids order."""
    return " ".join(tokens[i].text for i in cell.token_ids)
```

- [ ] **Step 2: Migrate one file and establish the pattern**

Open `harness/tests/test_header.py`. Wherever a test asserted a token had `label == {"field": c, "header": True}`, rewrite it to assert a cell exists. Example transformation — replace an assertion like:

```python
# OLD
assert any(p.label == {"field": 0, "header": True} for p in placed)
```

with:

```python
# NEW
from tests._cells import placed as run, cells_where
_toks, cells, _regions = run(dc)
assert cells_where(cells, role="header", column_index=0)
```

Run: `cd harness && uv run pytest tests/test_header.py -q` and fix until green.

- [ ] **Step 3: Migrate the remaining files**

Apply the same mechanical mapping in each file, using `_cells.py`. The role/field mapping table (old label → new cell query):

| old label assertion | new cell query |
|---|---|
| `label["record"]==r, label["field"]==c` | `cells_where(cells, role="data", row_index=r, column_index=c)` |
| `label["header"]` (leaf) | `cells_where(cells, role="header", column_index=c)` |
| `label["group"]==g` / `span` | `cells_where(cells, role="group_header")` ; check `.span`, and `text_of` for the group name |
| `label["section"]` | `cells_where(cells, role="section")` |
| `label["subtotal"]` | `cells_where(cells, role="summary")` |
| `label["global"]==name` | `cells_where(cells, role="value", field=name)` (or `role="key"` for the label) |
| `label is None` (background) | token referenced by no cell: `all(i not in {j for c in cells for j in c.token_ids} for i in bg_ids)` |
| `label["region"]==k` | `cells_where(cells, region_index=k)` ; region metadata via the `regions` list |

For `test_regions.py`: assert each `region.type`, `region.name`, `region.index`, and that a region's `bbox` encloses every cell with that `region_index`. For `test_spacing.py`/`test_capacity.py`/`test_jitter.py`: these mostly assert geometry (positions, in-page, capacity errors) and need only the `layout_with_regions` unpacking change `placed = layout(...)` → keep using `layout(dc, rng)` (still returns tokens) where they only inspect token boxes; switch to `placed`/`cells` only where they inspected labels.

Run after each file: `cd harness && uv run pytest tests/<file> -q`

- [ ] **Step 4: Full suite (golden still expected to fail)**

Run: `cd harness && uv run pytest -q`
Expected: everything green **except** `test_golden.py` (fixture regenerated in Task 6). Note which tests fail; only `test_golden` should remain.

- [ ] **Step 5: Commit**

```bash
git add harness/tests/_cells.py harness/tests/test_*.py
git commit -m "test: migrate label assertions to cell/region shape

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Regenerate the golden fixture

The golden compared per-token `bbox`+`text`+`label`. Tokens no longer carry labels, so the fixture shape changes. Regenerate it deliberately (this is a contract change) and have the golden assert the full `tokens`/`cells`/`regions`.

**Files:**
- Modify: `harness/tests/test_golden.py`
- Regenerate: `harness/tests/golden/invoice_seed7_n3.json`

- [ ] **Step 1: Rewrite the golden generator + test**

Replace `harness/tests/test_golden.py` `_gen_tokens` and the test with a version that captures all three lists:

```python
import json
import random
from pathlib import Path

from tablelab import classes as classlib
from tablelab.layout import layout_with_regions
from tablelab.render import render

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _gen(cls_name: str, seed: int, n: int) -> list[dict]:
    dc = classlib.get(cls_name)
    rng = random.Random(seed)
    W, H = dc.layout.page
    out: list[dict] = []
    for _ in range(n):
        placed, cells, regions = layout_with_regions(dc, rng)
        _img, boxes = render(placed, dc)
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
    return out


def test_invoice_matches_golden():
    got = _gen("invoice", seed=7, n=3)
    want = json.loads(GOLDEN.read_text())
    assert got == want
```

(Cell/region bboxes are page-px in `layout`; the golden omits them to stay stable under the px→normalized rounding, asserting structure + token geometry. Token boxes — the locked observable — are still pinned exactly.)

- [ ] **Step 2: Generate the fixture**

Run:
```bash
cd harness && uv run python -c "
import json, random
from tests.test_golden import _gen
json.dump(_gen('invoice', 7, 3), open('tests/golden/invoice_seed7_n3.json','w'), indent=2)
print('regenerated')
"
```
Expected: `regenerated`.

- [ ] **Step 3: Verify the golden passes**

Run: `cd harness && uv run pytest tests/test_golden.py -q`
Expected: PASS.

- [ ] **Step 4: Eyeball the fixture**

Run: `cd harness && uv run python -c "import json; d=json.load(open('tests/golden/invoice_seed7_n3.json')); print('samples',len(d)); print('cell roles', sorted({c['role'] for c in d[0]['cells']})); print('regions', d[0]['regions'])"`
Expected: 3 samples; roles `['data']` (invoice has no header/section/totals); regions `[{'type':'table','name':'line_item','index':0}]`.

- [ ] **Step 5: Commit**

```bash
git add harness/tests/test_golden.py harness/tests/golden/invoice_seed7_n3.json
git commit -m "test(golden): regenerate for v3 tokens/cells/regions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Full verification

- [ ] **Step 1: Whole suite green**

Run: `cd harness && uv run pytest -q`
Expected: all tests pass (count ≥ 134 with the new round-trip file).

- [ ] **Step 2: Build + inspect each class**

Run:
```bash
cd harness && for c in invoice eob receipt; do
  uv run python -m tablelab.cli build --class $c --n 3 --seed 5 --out ../datasets/_v3_$c >/dev/null
  uv run python -m tablelab.cli inspect ../datasets/_v3_$c
done
```
Expected: three builds succeed; `inspect` prints for each. Spot-check one samples.json has `schema_version: 3`, non-empty `cells`, and `regions` with `type`/`name`/`index`.

- [ ] **Step 3: Structural invariant check**

Run:
```bash
cd harness && uv run python -c "
import json
for c in ('invoice','eob','receipt'):
    d=json.load(open(f'../datasets/_v3_{c}/samples.json'))
    for s in d['samples']:
        ncells=len(s['cells']); ntok=len(s['tokens'])
        in_cells={i for cell in s['cells'] for i in cell['token_ids']}
        # every cell token id is valid
        assert all(0<=i<ntok for i in in_cells), c
        # each data cell has a field
        assert all(cell['field'] for cell in s['cells'] if cell['role']=='data'), c
    print(c,'ok')
"
rm -rf ../datasets/_v3_invoice ../datasets/_v3_eob ../datasets/_v3_receipt
```
Expected: `invoice ok` / `eob ok` / `receipt ok`; cleanup leaves no smoke datasets.

- [ ] **Step 4: Update AGENTS.md contract note**

In `AGENTS.md`, the "Contract is the seam" line says `schema_version = 2`. Update it to `schema_version = 3` and adjust the description to note observables are per-token `bbox`+`text` and the label layer is now `Region`/`Cell`. Keep it to the existing one-paragraph style.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): contract is now schema v3 (Region/Cell/Token)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Out of scope (separate follow-on plans)

- **Viewer** (`viewer/src/types.ts`, `DocumentViewer.tsx`, `MetaPanel`): read v3, draw region areas + cell rects, tint by `role`. Mechanical, independent, and the Python side is green without it. Write as its own short plan.
- **`derive_*` projections** + the document-class record/global rollup — the next milestone (the spec's deferred section).

## Self-review notes (already reconciled)

- Spec coverage: contract types (Task 1), layout cells/regions incl. globals→form + background as cell-less tokens + spanning roles (Tasks 2–3), build assembly (Task 4), tests + golden regenerated (Tasks 5–6), schema-version bump + observables-locked statement (Tasks 1, 7). Viewer deferred per spec note.
- Type consistency: `Cell`/`Region` field names identical across `artifacts.py`, `layout.py` output, `build.py`, and tests (`region_index`, `row_index`, `column_index`, `span`, `role`, `field`, `token_ids`; `type`/`name`/`index`). `PlacedCell.tokens` (refs) is resolved to `Cell.token_ids` (ints) exactly once, post-shuffle.
- Token-order hazard: `rng.shuffle(placed)` runs before id resolution — handled explicitly in Task 3 Step 1.
