# Multi-token Cells Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a `StructureSpec.multi_token` knob that splits multi-word cell values into per-word tokens sharing `record/field` and carrying a within-cell `seq`. Default off stays byte-identical to the backbone.

**Architecture:** `layout.py` splits values into per-word `PlacedToken`s sharing the cell rect (Pillow-free). `render.py` groups a cell's tokens by `(record, field)`, lays them out as a contiguous phrase, and returns per-word glyph boxes in input order. `build.py` unchanged. CLI gains `--multi-token`.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `pytest`. Run from `harness/` via `uv run`.

**Conventions:** No-TDD (implement + verify by running). The off-path golden test (`tests/test_golden.py`) is the regression guard; a new behavioral test covers the on path. Commit per task.

---

## File structure

| File | Status | Change |
|---|---|---|
| `harness/src/tablelab/specs.py` | modify | Add `multi_token: bool = False` to `StructureSpec`. |
| `harness/src/tablelab/layout.py` | modify | When `multi_token`, split value → per-word `PlacedToken`s sharing the cell, with `seq`. |
| `harness/src/tablelab/render.py` | modify | Group by `(record, field)`; sequence-in-cell phrase layout; boxes in input order. |
| `harness/src/tablelab/cli.py` | modify | Add `--multi-token` flag; fork `dc.structure`. |
| `harness/tests/test_multi_token.py` | create | Behavioral tests for the on path. |
| `harness/README.md` | modify | Note the `--multi-token` flag. |

---

## Task 1: `specs.py` — add the `multi_token` knob

**Files:** Modify `harness/src/tablelab/specs.py`

- [ ] **Step 1: Add the field to `StructureSpec`**

Replace the `StructureSpec` class with:

```python
@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter, spanning cells). Each follow-on
    spec adds fields here. See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    multi_token: split multi-word cell values into per-word tokens that share one
    record/field and carry a within-cell order index (seq)."""
    multi_token: bool = False
```

- [ ] **Step 2: Verify it imports with the default**

Run (from `harness/`):
```bash
uv run python -c "from tablelab.specs import StructureSpec; from dataclasses import replace; s=StructureSpec(); print(s.multi_token, replace(s, multi_token=True).multi_token)"
```
Expected: `False True`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat: StructureSpec.multi_token knob (default off)"
```

---

## Task 2: `layout.py` — split multi-word values into per-word tokens

**Files:** Modify `harness/src/tablelab/layout.py`

- [ ] **Step 1: Replace the body of `layout()`**

The current `layout()` appends one `PlacedToken` per cell. Replace the per-cell append so it splits when `multi_token` is on. The full new function:

```python
def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Preserves the legacy RNG
    sequence: randint(rows) -> sample() per cell row-major -> shuffle. When
    structure.multi_token is set, a multi-word value becomes several tokens that
    share the cell's record/field and carry a within-cell order index (seq)."""
    L = dc.layout
    W = L.page[0]
    mx, my = L.margin
    C = len(dc.fields)
    cell_w = (W - 2 * mx) / C
    multi = dc.structure.multi_token
    rows = rng.randint(L.rows[0], L.rows[1])
    placed: list[PlacedToken] = []
    for r in range(rows):
        for c in range(C):
            f = dc.fields[c]
            value = sample(f.type, rng)
            x0 = mx + c * cell_w
            y0 = my + r * L.row_h
            cell = (x0, y0, x0 + cell_w, y0 + L.row_h)
            if multi:
                for k, word in enumerate(value.split()):
                    placed.append(PlacedToken(
                        text=word, cell=cell,
                        label={"record": r, "field": c, "seq": k},
                        align=f.align, font_size=dc.render.font_size))
            else:
                placed.append(PlacedToken(
                    text=value, cell=cell,
                    label={"record": r, "field": c},
                    align=f.align, font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
```

Note: `sample()` is still called exactly once per cell, so the off path's RNG stream and tokens are unchanged.

- [ ] **Step 2: Verify both paths**

Run (from `harness/`):
```bash
uv run python -c "import random; from dataclasses import replace; from tablelab import classes as c; from tablelab.specs import fork; from tablelab.layout import layout; dc=c.get('invoice'); off=layout(dc, random.Random(7)); on=layout(fork(dc, structure=replace(dc.structure, multi_token=True)), random.Random(7)); print('off tokens:', len(off), '| has seq:', 'seq' in (off[0].label)); print('on tokens:', len(on), '| has seq:', 'seq' in on[0].label, '| >= off:', len(on) >= len(off))"
```
Expected: off has no `seq` and fewer-or-equal tokens; on has `seq` and `>= off` token count (multi-word descriptions split). Example: `off tokens: 40 | has seq: False` / `on tokens: 5x | has seq: True | >= off: True`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat: layout splits multi-word cells into per-word tokens (seq) when multi_token"
```

---

## Task 3: `render.py` — sequence-in-cell phrase layout

**Files:** Modify `harness/src/tablelab/render.py`

The renderer must now handle several tokens sharing a cell. Group by `(record, field)`, order by `seq`, lay the words out as a contiguous phrase, and return boxes in the original input order. One-token groups go through the exact legacy path so output stays byte-identical when `multi_token` is off.

- [ ] **Step 1: Replace the `render()` function**

```python
def render(placed: list[PlacedToken], dc: DocumentClass) -> tuple[Image.Image, list[Box]]:
    """Draw placed tokens onto a white page; return the image and per-token
    glyph-extent boxes (page pixels), parallel to ``placed``. Tokens sharing a
    cell (same record/field) are laid out left-to-right as one phrase; their boxes
    are still returned in the input order so the caller's 1:1 zip holds."""
    W, H = dc.layout.page
    pad = dc.layout.pad
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _font(dc.render.font_size)
    boxes: list[Box] = [(0.0, 0.0, 0.0, 0.0)] * len(placed)

    # Group token indices by their cell (record, field); order within a cell by seq.
    groups: dict[tuple, list[int]] = {}
    for i, p in enumerate(placed):
        key = (p.label["record"], p.label["field"])
        groups.setdefault(key, []).append(i)

    for idxs in groups.values():
        idxs.sort(key=lambda i: placed[i].label.get("seq", 0))
        cx0, cy0, cx1, cy1 = placed[idxs[0]].cell
        row_h = cy1 - cy0
        align = placed[idxs[0]].align

        if len(idxs) == 1:
            # Legacy single-token path — keeps output byte-identical when multi_token is off.
            p = placed[idxs[0]]
            tb = draw.textbbox((0, 0), p.text, font=font)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            ty = cy0 + (row_h - th) / 2 - tb[1]
            tx = (cx1 - pad - tw) if align == "right" else (cx0 + pad)
            draw.text((tx, ty), p.text, fill="black", font=font)
            boxes[idxs[0]] = draw.textbbox((tx, ty), p.text, font=font)
            continue

        # Multi-word: lay the words out as a contiguous phrase within the cell.
        words = [placed[i].text for i in idxs]
        phrase_w = draw.textlength(" ".join(words), font=font)
        x = (cx1 - pad - phrase_w) if align == "right" else (cx0 + pad)
        for i, word in zip(idxs, words):
            tb = draw.textbbox((0, 0), word, font=font)
            th = tb[3] - tb[1]
            ty = cy0 + (row_h - th) / 2 - tb[1]
            draw.text((x, ty), word, fill="black", font=font)
            boxes[i] = draw.textbbox((x, ty), word, font=font)
            x += draw.textlength(word + " ", font=font)

    return img, boxes
```

- [ ] **Step 2: Verify the off path is byte-identical (golden) and on path renders**

Run (from `harness/`):
```bash
uv run pytest tests/test_golden.py -q
```
Expected: `1 passed`. (If this fails, the one-token path diverged from legacy — compare to the backbone `render()`; do NOT edit the golden file.)

Run (from `harness/`):
```bash
uv run python -c "import random; from dataclasses import replace; from tablelab import classes as c; from tablelab.specs import fork; from tablelab.layout import layout; from tablelab.render import render; dc=fork(c.get('invoice'), structure=replace(c.get('invoice').structure, multi_token=True)); p=layout(dc, random.Random(7)); img, b=render(p, dc); print('tokens:', len(p), '| boxes:', len(b), '| all boxes set:', all(x[2] > x[0] for x in b))"
```
Expected: `boxes == tokens`, and `all boxes set: True` (every box has positive width).

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/render.py
git commit -m "feat: renderer lays out multi-token cells as a phrase, boxes in input order"
```

---

## Task 4: `cli.py` — `--multi-token` flag

**Files:** Modify `harness/src/tablelab/cli.py`

- [ ] **Step 1: Update `_build` to fork structure**

Replace the `_build` function with:

```python
def _build(args):
    dc = classlib.get(args.cls)
    L = dc.layout
    if args.rows:
        L = replace(L, rows=(args.rows[0], args.rows[1]))
    if args.page:
        L = replace(L, page=(args.page[0], args.page[1]))
    S = replace(dc.structure, multi_token=True) if args.multi_token else dc.structure
    if L is not dc.layout or S is not dc.structure:
        dc = fork(dc, layout=L, structure=S)
    out = Path(args.out)
    build_dataset(out.parent, out.name, dc, seed=args.seed, n=args.n)
    print(f"built {args.n} {args.cls} samples -> {out}")
```

- [ ] **Step 2: Add the argument to the `build` subparser**

In `main()`, immediately after the `--page` argument line for the `build` subparser, add:

```python
    b.add_argument("--multi-token", action="store_true",
                   help="split multi-word cells into per-word tokens (shared record/field + seq)")
```

(`argparse` exposes `--multi-token` as `args.multi_token`.)

- [ ] **Step 3: Smoke-test the flag**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class invoice --n 6 --out ../datasets/smoke-mt --multi-token
uv run python -m tablelab.cli inspect smoke-mt
uv run python -m tablelab.cli build --class invoice --n 6 --out ../datasets/smoke-single
uv run python -m tablelab.cli inspect smoke-single
```
Expected: `smoke-mt` shows a **higher** `tokens (…/sample)` than `smoke-single` (descriptions split). Both build without error.

- [ ] **Step 4: Clean up smoke datasets**

Run (from repo root):
```bash
rm -rf datasets/smoke-mt datasets/smoke-single
```

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: CLI --multi-token flag"
```

---

## Task 5: Behavioral tests for the on path

**Files:** Create `harness/tests/test_multi_token.py`

- [ ] **Step 1: Write the tests**

```python
import random
from collections import defaultdict
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _multi_invoice():
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, multi_token=True))


def _groups(placed):
    g = defaultdict(list)
    for p in placed:
        g[(p.label["record"], p.label["field"])].append(p)
    return g


def test_multiword_cells_split_with_contiguous_seq():
    placed = layout(_multi_invoice(), random.Random(7))
    groups = _groups(placed)
    # at least one cell (a multi-word description) split into >1 token
    assert any(len(v) > 1 for v in groups.values())
    # every cell's tokens carry contiguous seq 0..n-1
    for toks in groups.values():
        seqs = sorted(p.label["seq"] for p in toks)
        assert seqs == list(range(len(toks)))


def test_multiword_boxes_in_cell_disjoint_and_anchored():
    dc = _multi_invoice()
    rng = random.Random(7)
    placed = layout(dc, rng)
    _img, boxes = render(placed, dc)
    box_of = {id(p): b for p, b in zip(placed, boxes)}

    multiword_seen = False
    for toks in _groups(placed).values():
        if len(toks) < 2:
            continue
        multiword_seen = True
        toks = sorted(toks, key=lambda p: p.label["seq"])
        cx0, cy0, cx1, cy1 = toks[0].cell
        align = toks[0].align
        bxs = [box_of[id(p)] for p in toks]
        # vertically inside the row
        for b in bxs:
            assert cy0 - 1 <= b[1] and b[3] <= cy1 + 1
        # left-to-right, non-overlapping
        for a, b in zip(bxs, bxs[1:]):
            assert b[0] >= a[2] - 1
        # anchored to the correct cell edge by alignment
        if align == "right":
            assert bxs[-1][2] <= cx1 + 1
        else:
            assert bxs[0][0] >= cx0 - 1
    assert multiword_seen  # the fixture actually exercised the multi-word path
```

- [ ] **Step 2: Run the new tests + the full suite**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all tests pass (the golden test + the two new tests).

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_multi_token.py
git commit -m "test: multi-token cells — split, contiguous seq, in-cell disjoint boxes"
```

---

## Task 6: Docs

**Files:** Modify `harness/README.md`

- [ ] **Step 1: Note the flag in the CLI section**

In the `## CLI (tablelab.cli)` section, update the `build` overrides line to mention the flag:

```markdown
`build` flags: `--seed`, `--rows MIN MAX`, `--page W H`, `--multi-token` (split multi-word cells into per-word tokens). Classes: `invoice`, `eob`, `receipt`.
```

- [ ] **Step 2: Commit**

```bash
git add harness/README.md
git commit -m "docs: README note for --multi-token"
```

---

## Done criteria

- `uv run pytest -q` passes: the off-path golden test is unchanged (byte-identical) and the two new on-path behavioral tests pass.
- `build --multi-token` produces more tokens/sample than the single-token build; `inspect` reflects it.
- A multi-token dataset renders correctly in the viewer (words boxed individually, sharing record/field).

## Implementer notes

- **Byte-identical hinge:** `sample()` stays one-call-per-cell (Task 2) and one-token groups use the legacy positioning (Task 3). If `tests/test_golden.py` fails, look there first — never edit the golden file.
- **Box order:** `render()` must return `boxes` aligned to the **input** `placed` order (it writes into a pre-sized list by index), even though it processes tokens grouped by cell. `build.py` depends on this.
