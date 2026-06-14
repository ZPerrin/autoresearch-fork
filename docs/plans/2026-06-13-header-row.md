# Header Row Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a `StructureSpec.header` knob that emits a top row of field-name tokens (`{"field": c, "header": True}`), shifting data rows down one. Default off stays byte-identical.

**Architecture:** `layout.py` emits a header row (text derived from `FieldSpec.name`) above the data rows, factoring the multi-word split into an `_emit()` helper shared by header and data. `render.py` switches cell grouping to key on the cell rect (so header tokens, which lack `record`, group correctly). `build.py` unchanged. CLI gains `--header`.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `pytest`. Run from `harness/` via `uv run`.

**Conventions:** No-TDD (implement + verify by running). The off-path golden test guards byte-identical output; new behavioral tests cover the on path. Commit per task.

---

## File structure

| File | Status | Change |
|---|---|---|
| `harness/src/tablelab/specs.py` | modify | Add `header: bool = False` to `StructureSpec`. |
| `harness/src/tablelab/layout.py` | modify | `_emit()` helper + header row; `_header_text()`. |
| `harness/src/tablelab/render.py` | modify | Group by `PlacedToken.cell` instead of `(record, field)`. |
| `harness/src/tablelab/cli.py` | modify | Add `--header` flag; fork `dc.structure`. |
| `harness/tests/test_header.py` | create | Behavioral tests for the header path. |
| `harness/README.md` | modify | Note the `--header` flag. |

---

## Task 1: `specs.py` — add the `header` knob

**Files:** Modify `harness/src/tablelab/specs.py`

- [ ] **Step 1: Replace the `StructureSpec` class**

```python
@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter, spanning cells). Each follow-on
    spec adds fields here. See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    multi_token: split multi-word cell values into per-word tokens that share one
        record/field and carry a within-cell order index (seq).
    header: emit a top header row of field-name tokens (label {"field": c, "header": True})."""
    multi_token: bool = False
    header: bool = False
```

- [ ] **Step 2: Verify**

Run (from `harness/`):
```bash
uv run python -c "from tablelab.specs import StructureSpec; s=StructureSpec(); print(s.multi_token, s.header)"
```
Expected: `False False`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat: StructureSpec.header knob (default off)"
```

---

## Task 2: `layout.py` — header row + `_emit()` helper

**Files:** Modify `harness/src/tablelab/layout.py`

- [ ] **Step 1: Add helpers and rewrite `layout()`**

Keep the `PlacedToken` dataclass as-is. Add the two module-level helpers and replace `layout()`:

```python
def _header_text(name: str) -> str:
    """Field name → display header, e.g. 'unit_price' -> 'Unit Price'."""
    return name.replace("_", " ").title()


def _emit(placed: list[PlacedToken], text: str, cell, base_label: dict,
          align: str, font_size: int, multi: bool) -> None:
    """Append one token for `text`, or one per word (sharing cell + label, with seq) when multi."""
    if multi:
        for k, word in enumerate(text.split()):
            placed.append(PlacedToken(text=word, cell=cell,
                label={**base_label, "seq": k}, align=align, font_size=font_size))
    else:
        placed.append(PlacedToken(text=text, cell=cell,
            label=base_label, align=align, font_size=font_size))


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Preserves the legacy RNG
    sequence: randint(rows) -> sample() per data cell row-major -> shuffle. A header
    row (structure.header) is emitted above the data rows; multi-word values split
    into per-word tokens (structure.multi_token) sharing the cell's label + a seq."""
    L = dc.layout
    W = L.page[0]
    mx, my = L.margin
    C = len(dc.fields)
    cell_w = (W - 2 * mx) / C
    multi = dc.structure.multi_token
    header = dc.structure.header
    row_offset = 1 if header else 0
    rows = rng.randint(L.rows[0], L.rows[1])
    placed: list[PlacedToken] = []
    if header:
        for c in range(C):
            f = dc.fields[c]
            x0 = mx + c * cell_w
            cell = (x0, my, x0 + cell_w, my + L.row_h)
            _emit(placed, _header_text(f.name), cell,
                  {"field": c, "header": True}, f.align, dc.render.font_size, multi)
    for r in range(rows):
        for c in range(C):
            f = dc.fields[c]
            value = sample(f.type, rng)
            x0 = mx + c * cell_w
            y0 = my + (r + row_offset) * L.row_h
            cell = (x0, y0, x0 + cell_w, y0 + L.row_h)
            _emit(placed, value, cell,
                  {"record": r, "field": c}, f.align, dc.render.font_size, multi)
    rng.shuffle(placed)
    return placed
```

Note: with `header` off the header block is skipped and `sample()` is still called once per data cell in row-major order — the off path is byte-identical.

- [ ] **Step 2: Verify both paths**

Run (from `harness/`):
```bash
uv run python -c "import random; from dataclasses import replace; from tablelab import classes as c; from tablelab.specs import fork; from tablelab.layout import layout; dc=c.get('invoice'); hd=fork(dc, structure=replace(dc.structure, header=True)); p=layout(hd, random.Random(7)); hdrs=[t for t in p if t.label.get('header')]; print('header tokens:', len(hdrs), '| texts:', sorted({t.text for t in hdrs})); print('header y == margin_y:', all(t.cell[1]==hd.layout.margin[1] for t in hdrs))"
```
Expected: 4 header tokens with texts like `['Amount', 'Description', 'Quantity', 'Unit Price']`; `header y == margin_y: True`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat: layout emits a field-name header row; _emit helper shared with data rows"
```

---

## Task 3: `render.py` — group by cell rect

**Files:** Modify `harness/src/tablelab/render.py`

Header tokens carry no `record` key, so the cell-grouping key must not read `record`. Switch the key to the `PlacedToken.cell` tuple (identical for tokens in a cell, distinct across cells).

- [ ] **Step 1: Replace the grouping loop**

Find this block in `render()`:

```python
    # Group token indices by their cell (record, field); order within a cell by seq.
    groups: dict[tuple, list[int]] = {}
    for i, p in enumerate(placed):
        key = (p.label["record"], p.label["field"])
        groups.setdefault(key, []).append(i)
```

Replace it with:

```python
    # Group token indices by their cell rect; order within a cell by seq.
    groups: dict[tuple, list[int]] = {}
    for i, p in enumerate(placed):
        groups.setdefault(p.cell, []).append(i)
```

Leave the rest of `render()` unchanged (the `if len(idxs) > 1: idxs.sort(key=lambda i: placed[i].label["seq"])` and both draw paths stay as they are).

- [ ] **Step 2: Verify off path is byte-identical, header path renders**

Run (from `harness/`):
```bash
uv run pytest tests/test_golden.py tests/test_multi_token.py -q
```
Expected: all pass (golden byte-identical + multi-token still works with the new key).

Run (from `harness/`):
```bash
uv run python -c "import random; from dataclasses import replace; from tablelab import classes as c; from tablelab.specs import fork; from tablelab.layout import layout; from tablelab.render import render; dc=fork(c.get('invoice'), structure=replace(c.get('invoice').structure, header=True)); p=layout(dc, random.Random(7)); img,b=render(p,dc); hb=[bb for t,bb in zip(p,b) if t.label.get('header')]; db=[bb for t,bb in zip(p,b) if not t.label.get('header')]; print('all boxes set:', all(x[2]>x[0] for x in b), '| headers above data:', max(x[3] for x in hb) <= min(x[1] for x in db)+1)"
```
Expected: `all boxes set: True | headers above data: True`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/render.py
git commit -m "refactor: group render tokens by cell rect (schema-agnostic; enables header tokens)"
```

---

## Task 4: `cli.py` — `--header` flag

**Files:** Modify `harness/src/tablelab/cli.py`

- [ ] **Step 1: Update `_build` to fork structure for both knobs**

Replace the `_build` function with:

```python
def _build(args):
    dc = classlib.get(args.cls)
    L = dc.layout
    if args.rows:
        L = replace(L, rows=(args.rows[0], args.rows[1]))
    if args.page:
        L = replace(L, page=(args.page[0], args.page[1]))
    S = dc.structure
    if args.multi_token:
        S = replace(S, multi_token=True)
    if args.header:
        S = replace(S, header=True)
    if L is not dc.layout or S is not dc.structure:
        dc = fork(dc, layout=L, structure=S)
    out = Path(args.out)
    build_dataset(out.parent, out.name, dc, seed=args.seed, n=args.n)
    print(f"built {args.n} {args.cls} samples -> {out}")
```

- [ ] **Step 2: Add the `--header` argument**

In `main()`, immediately after the `--multi-token` argument line for the `build` subparser, add:

```python
    b.add_argument("--header", action="store_true",
                   help="emit a top header row of field-name tokens")
```

- [ ] **Step 3: Smoke-test**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class invoice --n 6 --out ../datasets/smoke-hdr --header
uv run python -m tablelab.cli inspect smoke-hdr
uv run python -m tablelab.cli build --class invoice --n 6 --out ../datasets/smoke-plain
uv run python -m tablelab.cli inspect smoke-plain
```
Expected: `smoke-hdr` shows a higher `tokens (…/sample)` than `smoke-plain` (each sample has +4 header tokens). Both build cleanly.

- [ ] **Step 4: Clean up smoke datasets**

Run (from repo root):
```bash
rm -rf datasets/smoke-hdr datasets/smoke-plain
```

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: CLI --header flag"
```

---

## Task 5: Behavioral tests

**Files:** Create `harness/tests/test_header.py`

- [ ] **Step 1: Write the tests**

```python
from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _invoice(**structure):
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, **structure))


def test_header_off_is_default():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all(not (p.label and p.label.get("header")) for p in placed)


def test_header_row_emits_field_name_tokens_above_data():
    dc = _invoice(header=True)
    placed = layout(dc, random.Random(7))
    headers = [p for p in placed if p.label.get("header")]
    data = [p for p in placed if not p.label.get("header")]
    C = len(dc.fields)
    my, row_h = dc.layout.margin[1], dc.layout.row_h
    # one header token per field, carrying the titleized field name
    assert sorted(p.label["field"] for p in headers) == list(range(C))
    assert {p.label["field"]: p.text for p in headers}[0] == "Description"
    # header cells sit at the top margin; every data cell is below the first row
    assert all(p.cell[1] == my for p in headers)
    assert all(p.cell[1] >= my + row_h for p in data)


def test_header_with_multi_token_splits_header_text():
    dc = _invoice(header=True, multi_token=True)
    placed = layout(dc, random.Random(7))
    # "Unit Price" (field 2) -> two header tokens sharing the header cell, ordered by seq
    unit = [p for p in placed if p.label.get("header") and p.label["field"] == 2]
    assert [p.text for p in sorted(unit, key=lambda p: p.label["seq"])] == ["Unit", "Price"]
    assert len({p.cell for p in unit}) == 1


def test_header_renders_boxes_above_data():
    dc = _invoice(header=True)
    placed = layout(dc, random.Random(7))
    _img, boxes = render(placed, dc)
    hb = [b for p, b in zip(placed, boxes) if p.label.get("header")]
    db = [b for p, b in zip(placed, boxes) if not p.label.get("header")]
    assert all(b[2] > b[0] for b in boxes)          # every box set
    assert max(b[3] for b in hb) <= min(b[1] for b in db) + 1  # headers above data
```

- [ ] **Step 2: Run the full suite**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden + multi-token + the four header tests).

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_header.py
git commit -m "test: header row — field-name tokens, placement, multi-token split, render order"
```

---

## Task 6: Docs

**Files:** Modify `harness/README.md`

- [ ] **Step 1: Note the flag**

In the `## CLI (tablelab.cli)` section, update the `build` flags line to add `--header`:

```markdown
`build` flags: `--seed`, `--rows MIN MAX`, `--page W H`, `--multi-token` (split multi-word cells into per-word tokens), `--header` (top row of field-name tokens). Classes: `invoice`, `eob`, `receipt`.
```

- [ ] **Step 2: Commit**

```bash
git add harness/README.md
git commit -m "docs: README note for --header"
```

---

## Done criteria

- `uv run pytest -q` passes: golden unchanged (byte-identical), multi-token still green, four new header tests pass.
- `build --header` adds `C` header tokens/sample; composes with `--multi-token`.
- A header dataset renders correctly in the viewer (a top row of column names above the records).

## Implementer notes

- **Byte-identical hinge:** off-path skips the header block and keeps `sample()` one-call-per-data-cell. If `tests/test_golden.py` fails, that's the place to look — never edit the golden file.
- **Render grouping** now keys on `PlacedToken.cell`; do not reintroduce a `label["record"]` read there (header tokens have no `record`).
