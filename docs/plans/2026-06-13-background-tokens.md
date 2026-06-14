# Background / Non-table Tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a `StructureSpec.background` count that scatters non-table tokens (`label = None`) in the footer band below the table. Default 0 stays byte-identical.

**Architecture:** `fields.py` gains a noise-word pool + `background_token(rng)`. `layout.py` appends `background` single tokens with `label = None` at random footer positions (after the data rows, before the shuffle). `render.py` already groups by cell rect and draws singletons via the legacy path — no change needed. `build.py` already round-trips `label = None`. CLI gains `--background N`.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `pytest`. Run from `harness/` via `uv run`.

**Conventions:** No-TDD (implement + verify by running). The off-path golden test guards byte-identical output; new behavioral tests cover the on path. Commit per task.

---

## File structure

| File | Status | Change |
|---|---|---|
| `harness/src/tablelab/specs.py` | modify | Add `background: int = 0` to `StructureSpec`. |
| `harness/src/tablelab/fields.py` | modify | `_BACKGROUND` pool + `background_token(rng)`. |
| `harness/src/tablelab/layout.py` | modify | Append `background` non-table tokens (`label = None`) in the footer band. |
| `harness/src/tablelab/cli.py` | modify | Add `--background N`; fork `dc.structure`. |
| `harness/tests/test_background.py` | create | Behavioral tests for the background path. |
| `harness/README.md` | modify | Note the `--background` flag. |

`render.py` and `build.py` are intentionally untouched (the cell-key grouping already handles `label = None` singletons; the contract already serializes `None`).

---

## Task 1: `specs.py` — add the `background` knob

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
    header: emit a top header row of field-name tokens (label {"field": c, "header": True}).
    background: scatter N non-table tokens (label = None) in the footer band below the table."""
    multi_token: bool = False
    header: bool = False
    background: int = 0
```

- [ ] **Step 2: Verify**

Run (from `harness/`):
```bash
uv run python -c "from tablelab.specs import StructureSpec; s=StructureSpec(); print(s.multi_token, s.header, s.background)"
```
Expected: `False False 0`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat: StructureSpec.background knob (default 0)"
```

---

## Task 2: `fields.py` — noise-word pool + sampler

**Files:** Modify `harness/src/tablelab/fields.py`

- [ ] **Step 1: Add the pool and sampler**

After the existing `SAMPLERS` dict and `sample()` function, append:

```python
# Page-noise vocabulary for non-table (background) tokens — titles, footer notes, refs.
_BACKGROUND = [
    "INVOICE", "STATEMENT", "RECEIPT", "Confidential", "Original", "Duplicate",
    "Page", "Total", "Subtotal", "Balance", "Account", "Customer", "Provider",
    "Ref", "Paid", "Due", "Remit", "Terms", "Copy", "Notice",
]


def background_token(rng: random.Random) -> str:
    """A single non-table noise token: a page-furniture word, or sometimes a number."""
    if rng.random() < 0.3:
        return str(rng.randint(1000, 99999))
    return rng.choice(_BACKGROUND)
```

- [ ] **Step 2: Verify**

Run (from `harness/`):
```bash
uv run python -c "import random; from tablelab.fields import background_token; r=random.Random(1); print([background_token(r) for _ in range(6)])"
```
Expected: a list of 6 strings — a mix of words from the pool and numeric strings.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/fields.py
git commit -m "feat: background_token sampler + page-noise pool"
```

---

## Task 3: `layout.py` — scatter background tokens

**Files:** Modify `harness/src/tablelab/layout.py`

- [ ] **Step 1: Import the sampler**

Update the import line:

```python
from .fields import sample
```
to:
```python
from .fields import sample, background_token
```

- [ ] **Step 2: Append the background block before the shuffle**

In `layout()`, find the end of the data-rows loop and the final shuffle:

```python
            _emit(placed, value, cell,
                  {"record": r, "field": c}, f.align, dc.render.font_size, multi)
    rng.shuffle(placed)
    return placed
```

Insert the background block between the data loop and `rng.shuffle(placed)` so it reads:

```python
            _emit(placed, value, cell,
                  {"record": r, "field": c}, f.align, dc.render.font_size, multi)
    n_bg = dc.structure.background
    if n_bg:
        H = L.page[1]
        table_bottom = my + (row_offset + rows) * L.row_h
        y_lo, y_hi = table_bottom, H - my - L.row_h
        for _ in range(n_bg):
            bx = rng.uniform(mx, W - mx - 80)
            by = rng.uniform(y_lo, y_hi)
            cell = (bx, by, bx + 80, by + L.row_h)
            placed.append(PlacedToken(
                text=background_token(rng), cell=cell, label=None,
                align="left", font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
```

Note: the block runs only when `n_bg > 0`, so with `background = 0` no extra RNG is drawn — the off path is byte-identical. (`W` and `mx`/`my` are already bound earlier in `layout()`.)

- [ ] **Step 3: Verify both paths**

Run (from `harness/`):
```bash
uv run python -c "import random; from dataclasses import replace; from tablelab import classes as c; from tablelab.specs import fork; from tablelab.layout import layout; dc=fork(c.get('invoice'), structure=replace(c.get('invoice').structure, background=5)); p=layout(dc, random.Random(7)); bg=[t for t in p if t.label is None]; data=[t for t in p if t.label is not None]; print('bg tokens:', len(bg), '| texts:', [t.text for t in bg]); tb=max(t.cell[3] for t in data); print('all bg below table:', all(t.cell[1] >= tb - 1 for t in bg))"
```
Expected: `bg tokens: 5`, a list of 5 noise strings, and `all bg below table: True`.

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat: layout scatters background (label=None) tokens in the footer band"
```

---

## Task 4: `cli.py` — `--background` flag

**Files:** Modify `harness/src/tablelab/cli.py`

- [ ] **Step 1: Update `_build` to fork structure for the background count**

In `_build`, the structure-building block currently reads:

```python
    S = dc.structure
    if args.multi_token:
        S = replace(S, multi_token=True)
    if args.header:
        S = replace(S, header=True)
```

Add a background clause so it reads:

```python
    S = dc.structure
    if args.multi_token:
        S = replace(S, multi_token=True)
    if args.header:
        S = replace(S, header=True)
    if args.background:
        S = replace(S, background=args.background)
```

- [ ] **Step 2: Add the `--background` argument**

In `main()`, immediately after the `--header` argument line for the `build` subparser, add:

```python
    b.add_argument("--background", type=int, default=0, metavar="N",
                   help="scatter N non-table tokens (label null) below the table")
```

- [ ] **Step 3: Smoke-test**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class invoice --n 6 --out ../datasets/smoke-bg --background 5
uv run python -m tablelab.cli inspect smoke-bg
uv run python -m tablelab.cli build --class invoice --n 6 --out ../datasets/smoke-nobg
uv run python -m tablelab.cli inspect smoke-nobg
```
Expected: `smoke-bg` shows a higher `tokens (…/sample)` than `smoke-nobg` (≈ +5/sample). Both build cleanly.

- [ ] **Step 4: Verify the contract serialized `label: null`**

Run (from repo root):
```bash
python -c "import json; d=json.load(open('datasets/smoke-bg/samples.json')); nulls=[t for s in d['samples'] for t in s['tokens'] if t['label'] is None]; print('null-label tokens in file:', len(nulls))"
```
Expected: a positive number (≈ 30 for 6 samples × 5).

- [ ] **Step 5: Clean up smoke datasets**

Run (from repo root):
```bash
rm -rf datasets/smoke-bg datasets/smoke-nobg
```

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: CLI --background flag"
```

---

## Task 5: Behavioral tests

**Files:** Create `harness/tests/test_background.py`

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


def test_background_off_is_default():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all(p.label is not None for p in placed)


def test_background_adds_n_null_label_tokens_below_table():
    dc = _invoice(background=5)
    placed = layout(dc, random.Random(7))
    bg = [p for p in placed if p.label is None]
    data = [p for p in placed if p.label is not None]
    assert len(bg) == 5
    # background sits at or below the bottom of the lowest table row
    table_bottom = max(p.cell[3] for p in data)
    assert all(p.cell[1] >= table_bottom - 1 for p in bg)
    # table tokens are unaffected and still labeled
    assert all(p.label is not None and "field" in p.label for p in data)


def test_background_renders_and_round_trips_null_label():
    dc = _invoice(background=4)
    placed = layout(dc, random.Random(7))
    img, boxes = render(placed, dc)
    assert all(b[2] > b[0] for b in boxes)  # every box set, including background
    # the null label is preserved through the placed tokens (what build.py serializes)
    assert sum(1 for p in placed if p.label is None) == 4


def test_background_composes_with_header():
    dc = _invoice(background=3, header=True)
    placed = layout(dc, random.Random(7))
    assert sum(1 for p in placed if p.label is None) == 3
    assert any(p.label and p.label.get("header") for p in placed)
```

- [ ] **Step 2: Run the full suite**

Run (from `harness/`):
```bash
uv run pytest -q
```
Expected: all pass (golden + multi-token + header + the four background tests).

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_background.py
git commit -m "test: background tokens — count, null label, footer placement, render, compose"
```

---

## Task 6: Docs

**Files:** Modify `harness/README.md`

- [ ] **Step 1: Note the flag**

In the `## CLI (tablelab.cli)` section, update the `build` flags line to add `--background`:

```markdown
`build` flags: `--seed`, `--rows MIN MAX`, `--page W H`, `--multi-token` (split multi-word cells into per-word tokens), `--header` (top row of field-name tokens), `--background N` (scatter N non-table tokens). Classes: `invoice`, `eob`, `receipt`.
```

- [ ] **Step 2: Commit**

```bash
git add harness/README.md
git commit -m "docs: README note for --background"
```

---

## Done criteria

- `uv run pytest -q` passes: golden unchanged (byte-identical), prior features green, four new background tests pass.
- `build --background N` adds ≈N `label: null` tokens/sample; `samples.json` serializes `label: null`; composes with `--header`/`--multi-token`.
- A background dataset renders in the viewer with neutral (unlabeled) tokens below the table.

## Implementer notes

- **Byte-identical hinge:** the background block is guarded by `if n_bg:` and appends after the data loop, so `background = 0` draws no extra RNG. If `tests/test_golden.py` fails, that guard or its placement is the issue — never edit the golden file.
- **No render/build change:** the cell-key grouping already draws `label = None` singletons via the legacy path, and the contract already serializes `None`. Do not modify `render.py` or `build.py`.
