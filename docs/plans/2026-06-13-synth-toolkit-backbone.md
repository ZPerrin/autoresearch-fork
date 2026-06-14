# Synth Toolkit Backbone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose the monolithic `generate.py` into a compositional spec API (`FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`DocumentClass`) + a `build`/`list`/`inspect` CLI, reproducing today's dataset output byte-for-byte.

**Architecture:** Split generation into a Pillow-free **layout stage** (`layout()` → `list[PlacedToken]`, the IR) and a **render stage** (`render()` → PNG + glyph boxes), joined by the `PlacedToken` IR. An orchestrator (`build_dataset`) composes a registered `DocumentClass`, runs layout→render per sample, converts to the contract `Token`/`Sample`, and writes the dataset. The legacy RNG call order is preserved so output is identical; a golden-snapshot test is the correctness anchor.

**Tech Stack:** Python 3.10+, `uv`, Pillow, `argparse` + `tqdm`, `pytest` (dev). Run everything from `harness/` via `uv run`.

**Conventions:** This repo is **No-TDD** (AGENTS.md: "implement and verify by running"). Verification here is the spec's anchors — a golden regression test for the refactor, plus smoke runs and a viewer eyeball — not red-green-per-step. Commit after each task.

---

## File structure

All paths under `harness/src/tablelab/` unless noted. One responsibility each:

| File | Status | Responsibility |
|---|---|---|
| `specs.py` | create | Frozen dataclasses (`FieldSpec`, `LayoutSpec`, `StructureSpec`, `RenderSpec`, `DocumentClass`) + `fork()`. Pure data. |
| `fields.py` | create | Value-sampler registry keyed by semantic type (`SAMPLERS`, `sample()`). |
| `classes.py` | create | `DocumentClass` registry (`register`/`get`/`classes`) + built-in `invoice`/`eob`/`receipt`. |
| `layout.py` | create | `PlacedToken` IR + `layout()`: spec + rng → placed tokens (pixel cell rects, no Pillow). |
| `render.py` | create | `render()`: placed tokens + class → PIL image + glyph-extent boxes. |
| `build.py` | create | `build_dataset()` orchestrator; `GENERATOR_VERSION`. Replaces `generate.py`. |
| `cli.py` | create | `argparse` + `tqdm`: `build` / `list` / `inspect`. |
| `generate.py` | delete | Retired; logic split across the modules above. |
| `tests/golden/invoice_seed7_n3.json` | create | Golden token snapshot captured from legacy `generate.py`. |
| `tests/test_golden.py` | create | Regression: refactored layout+render reproduces the golden tokens. |
| `README.md`, `../AGENTS.md` | modify | Update module list + current-state note. |

---

## Task 1: Prep — add `tqdm`, capture the golden baseline

Do this **before** any refactor, while `generate.py` still exists, so the golden snapshot reflects legacy output.

**Files:**
- Modify: `harness/pyproject.toml` (via `uv add`)
- Create: `harness/tests/golden/invoice_seed7_n3.json`

- [ ] **Step 1: Add the tqdm dependency**

Run (from `harness/`):
```bash
uv add tqdm
```
Expected: `pyproject.toml` gains `tqdm>=…` under `dependencies`; `uv.lock` updates; install succeeds.

- [ ] **Step 2: Capture the golden token snapshot from legacy generate.py**

Run (from `harness/`):
```bash
uv run python -c "import json, pathlib, tempfile; from tablelab.generate import build_dataset; d=tempfile.mkdtemp(); build_dataset(d,'inv','invoice',seed=7,n=3); sd=json.loads((pathlib.Path(d)/'inv'/'samples.json').read_text()); toks=[[{k:t[k] for k in ('x0','y0','x1','y1','text','label')} for t in s['tokens']] for s in sd['samples']]; out=pathlib.Path('tests/golden'); out.mkdir(parents=True, exist_ok=True); (out/'invoice_seed7_n3.json').write_text(json.dumps(toks, indent=2)); print('captured', sum(len(t) for t in toks), 'tokens across', len(toks), 'samples')"
```
Expected: prints `captured N tokens across 3 samples`; `tests/golden/invoice_seed7_n3.json` exists (a list of 3 lists of token dicts).

- [ ] **Step 3: Commit**

```bash
git add harness/pyproject.toml harness/uv.lock harness/tests/golden/invoice_seed7_n3.json
git commit -m "chore: add tqdm; capture legacy golden token snapshot for refactor"
```

---

## Task 2: `specs.py` — the compositional spec types

**Files:**
- Create: `harness/src/tablelab/specs.py`

- [ ] **Step 1: Write the module**

```python
from __future__ import annotations
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str            # key into fields.SAMPLERS (e.g. "amount", "date")
    align: str = "left"  # "left" | "right"


@dataclass(frozen=True)
class LayoutSpec:
    rows: tuple[int, int] = (2, 6)        # record-count range, inclusive (passed to randint)
    page: tuple[int, int] = (1000, 1414)  # page pixel size (W, H)
    margin: tuple[int, int] = (60, 80)    # (x, y) page margins in px
    row_h: int = 74                       # row height in px
    pad: int = 12                         # in-cell text padding in px


@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter, spanning cells). Minimal today;
    each follow-on spec adds fields here. See the enhancement trajectory in
    docs/specs/2026-06-13-synth-toolkit-backbone-design.md."""


@dataclass(frozen=True)
class RenderSpec:
    font_size: int = 22
    renderer: str = "pillow"   # the visual-realism seam; only "pillow" exists today


@dataclass(frozen=True)
class DocumentClass:
    name: str
    fields: tuple[FieldSpec, ...]
    layout: LayoutSpec = LayoutSpec()
    structure: StructureSpec = StructureSpec()
    render: RenderSpec = RenderSpec()


def fork(dc: DocumentClass, name: str | None = None, **overrides) -> DocumentClass:
    """Copy a DocumentClass with top-level fields replaced (e.g. ``layout=...``).
    Nested specs are replaced wholesale — build the replacement with
    ``dataclasses.replace(dc.layout, rows=...)`` and pass it in."""
    return replace(dc, name=name or dc.name, **overrides)
```

- [ ] **Step 2: Verify it imports and forks**

Run (from `harness/`):
```bash
uv run python -c "from dataclasses import replace; from tablelab.specs import DocumentClass, FieldSpec, LayoutSpec, fork; dc=DocumentClass('t',(FieldSpec('a','amount','right'),)); dc2=fork(dc, name='t2', layout=replace(dc.layout, rows=(1,1))); print(dc2.name, dc2.layout.rows, dc.layout.rows)"
```
Expected: `t2 (1, 1) (2, 6)` — fork is non-mutating; nested replace works.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat: compositional spec types (Field/Layout/Structure/Render/DocumentClass) + fork"
```

---

## Task 3: `fields.py` — value-sampler registry

Move the legacy samplers verbatim (identical bodies → identical RNG draws → identical output).

**Files:**
- Create: `harness/src/tablelab/fields.py`

- [ ] **Step 1: Write the module**

```python
from __future__ import annotations
import random
from datetime import date, timedelta

# Field-appropriate value samplers, modeled on real invoice / EOB / receipt line items.
_DESCRIPTIONS = [
    "Office chair", "Desk lamp", "USB-C cable", "Notebook", "Stapler",
    "Monitor stand", "Printer paper", "Ballpoint pens", "Whiteboard", "Headset",
    "Office visit", "Lab panel", "X-ray exam", "Consultation", "Physical therapy",
    "Vaccination", "Blood test", "MRI scan", "Follow-up", "Screening",
]


def _money(rng: random.Random) -> str:
    return f"${rng.uniform(2, 950):,.2f}"


def _qty(rng: random.Random) -> str:
    return str(rng.randint(1, 24))


def _date(rng: random.Random) -> str:
    return (date(2025, 1, 1) + timedelta(days=rng.randint(0, 480))).strftime("%m/%d/%Y")


def _code(rng: random.Random) -> str:
    return f"{rng.randint(10000, 99999)}"  # CPT-like


def _desc(rng: random.Random) -> str:
    return rng.choice(_DESCRIPTIONS)


# semantic type name -> sampler. Alignment lives on FieldSpec, not here.
SAMPLERS = {
    "description": _desc,
    "quantity": _qty,
    "unit_price": _money,
    "amount": _money,
    "date": _date,
    "code": _code,
}


def sample(type_name: str, rng: random.Random) -> str:
    return SAMPLERS[type_name](rng)
```

- [ ] **Step 2: Verify it imports and samples**

Run (from `harness/`):
```bash
uv run python -c "import random; from tablelab.fields import sample, SAMPLERS; r=random.Random(7); print(sorted(SAMPLERS)); print({t: sample(t, r) for t in ('amount','date','code','quantity')})"
```
Expected: prints the 6 type names sorted, and one sampled value per type (e.g. an `$x.xx` string, an `MM/DD/YYYY` date, a 5-digit code, an int string).

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/fields.py
git commit -m "feat: value-sampler registry keyed by semantic type"
```

---

## Task 4: `classes.py` — DocumentClass registry + built-ins

**Files:**
- Create: `harness/src/tablelab/classes.py`

Alignments must match the legacy `FIELD_TYPES` (description/date/code = left; quantity/unit_price/amount = right) so output stays identical. EOB field **names** are made descriptive (`service_date`/`amount_billed`/`amount_owed`) — names appear only in the manifest, never in tokens (labels key on index), so this does not change rendered output.

- [ ] **Step 1: Write the module**

```python
from __future__ import annotations
from .specs import FieldSpec, DocumentClass

REGISTRY: dict[str, DocumentClass] = {}


def register(dc: DocumentClass) -> DocumentClass:
    REGISTRY[dc.name] = dc
    return dc


def get(name: str) -> DocumentClass:
    if name not in REGISTRY:
        raise KeyError(f"unknown document class {name!r}; known: {classes()}")
    return REGISTRY[name]


def classes() -> list[str]:
    return sorted(REGISTRY)


def _f(name: str, type_: str, align: str) -> FieldSpec:
    return FieldSpec(name=name, type=type_, align=align)


register(DocumentClass(name="invoice", fields=(
    _f("description", "description", "left"),
    _f("quantity", "quantity", "right"),
    _f("unit_price", "unit_price", "right"),
    _f("amount", "amount", "right"),
)))

register(DocumentClass(name="eob", fields=(
    _f("service_date", "date", "left"),
    _f("code", "code", "left"),
    _f("description", "description", "left"),
    _f("amount_billed", "amount", "right"),
    _f("amount_owed", "amount", "right"),
)))

register(DocumentClass(name="receipt", fields=(
    _f("description", "description", "left"),
    _f("amount", "amount", "right"),
)))
```

- [ ] **Step 2: Verify the registry**

Run (from `harness/`):
```bash
uv run python -c "from tablelab import classes as c; print(c.classes()); print([f.name for f in c.get('eob').fields]); print([f.align for f in c.get('invoice').fields])"
```
Expected: `['eob', 'invoice', 'receipt']`, then `['service_date', 'code', 'description', 'amount_billed', 'amount_owed']`, then `['left', 'right', 'right', 'right']`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/classes.py
git commit -m "feat: DocumentClass registry + built-in invoice/eob/receipt classes"
```

---

## Task 5: `layout.py` — `PlacedToken` IR + `layout()`

Pillow-free placement. Preserves the legacy RNG order exactly: `randint(rows)` → `sample()` per cell row-major → `shuffle(tokens)`.

**Files:**
- Create: `harness/src/tablelab/layout.py`

- [ ] **Step 1: Write the module**

```python
from __future__ import annotations
import random
from dataclasses import dataclass

from .specs import DocumentClass
from .fields import sample


@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # cell rect in page pixels (x0, y0, x1, y1)
    label: dict | None                        # {"record": r, "field": c}; null = background (future)
    align: str = "left"
    font_size: int = 22


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Preserves the legacy RNG
    sequence: randint(rows) -> sample() per cell row-major -> shuffle."""
    L = dc.layout
    W, H = L.page
    mx, my = L.margin
    C = len(dc.fields)
    cell_w = (W - 2 * mx) / C
    rows = rng.randint(L.rows[0], L.rows[1])
    placed: list[PlacedToken] = []
    for r in range(rows):
        for c in range(C):
            f = dc.fields[c]
            s = sample(f.type, rng)
            x0 = mx + c * cell_w
            y0 = my + r * L.row_h
            placed.append(PlacedToken(
                text=s, cell=(x0, y0, x0 + cell_w, y0 + L.row_h),
                label={"record": r, "field": c}, align=f.align,
                font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
```

- [ ] **Step 2: Verify placement**

Run (from `harness/`):
```bash
uv run python -c "import random; from tablelab import classes as c; from tablelab.layout import layout; p=layout(c.get('invoice'), random.Random(7)); print(len(p), 'tokens'); print(p[0])"
```
Expected: a token count that is a multiple of 4 (invoice has 4 fields), and a `PlacedToken(...)` repr with a 4-tuple `cell`, a `{'record':…, 'field':…}` label, and an `align`.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat: PlacedToken IR + Pillow-free layout() preserving legacy RNG order"
```

---

## Task 6: `render.py` — draw tokens, return glyph boxes

The box math is copied from legacy `generate_sample` so glyph extents are identical.

**Files:**
- Create: `harness/src/tablelab/render.py`

- [ ] **Step 1: Write the module**

```python
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .specs import DocumentClass
from .layout import PlacedToken

Box = tuple[float, float, float, float]


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def render(placed: list[PlacedToken], dc: DocumentClass) -> tuple[Image.Image, list[Box]]:
    """Draw placed tokens onto a white page; return the image and per-token
    glyph-extent boxes (page pixels), parallel to ``placed``."""
    W, H = dc.layout.page
    pad = dc.layout.pad
    row_h = dc.layout.row_h
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _font(dc.render.font_size)
    boxes: list[Box] = []
    for p in placed:
        cx0, cy0, cx1, cy1 = p.cell
        tb = draw.textbbox((0, 0), p.text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ty = cy0 + (row_h - th) / 2 - tb[1]
        tx = (cx1 - pad - tw) if p.align == "right" else (cx0 + pad)
        draw.text((tx, ty), p.text, fill="black", font=font)
        boxes.append(draw.textbbox((tx, ty), p.text, font=font))  # actual rendered extent
    return img, boxes
```

- [ ] **Step 2: Verify render**

Run (from `harness/`):
```bash
uv run python -c "import random; from tablelab import classes as c; from tablelab.layout import layout; from tablelab.render import render; dc=c.get('invoice'); p=layout(dc, random.Random(7)); img, boxes=render(p, dc); print(img.size, len(boxes), 'boxes', boxes[0])"
```
Expected: `(1000, 1414) N boxes (…)` where N == number of placed tokens; box is a 4-tuple of pixel coords.

- [ ] **Step 3: Commit**

```bash
git add harness/src/tablelab/render.py
git commit -m "feat: Pillow renderer — draw placed tokens, return glyph-extent boxes"
```

---

## Task 7: `build.py` — orchestrator; retire `generate.py`

**Files:**
- Create: `harness/src/tablelab/build.py`
- Delete: `harness/src/tablelab/generate.py`

- [ ] **Step 1: Write the orchestrator**

```python
from __future__ import annotations
import random
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from .specs import DocumentClass
from .artifacts import Sample, Token, DatasetManifest, write_dataset
from .layout import layout
from .render import render

GENERATOR_VERSION = 2


def build_dataset(datasets_dir, dataset_id: str, doc_class: DocumentClass,
                  seed: int = 7, n: int = 12) -> Path:
    """Compose a DocumentClass into a dataset: per sample layout->render->convert,
    write images + contract samples + a reproducible manifest (resolved spec + seed)."""
    rng = random.Random(seed)
    W, H = doc_class.layout.page
    ds_dir = Path(datasets_dir) / dataset_id
    (ds_dir / "images").mkdir(parents=True, exist_ok=True)
    samples: list[Sample] = []
    for i in tqdm(range(n), desc=dataset_id):
        placed = layout(doc_class, rng)
        img, boxes = render(placed, doc_class)
        img.save(ds_dir / "images" / f"{i}.png")
        tokens = [Token(x0=round(b[0] / W, 4), y0=round(b[1] / H, 4),
                        x1=round(b[2] / W, 4), y1=round(b[3] / H, 4),
                        text=p.text, label=p.label)
                  for p, b in zip(placed, boxes)]
        samples.append(Sample(id=i, tokens=tokens, width=W, height=H,
                              image=f"/datasets/{dataset_id}/images/{i}.png"))
    manifest = DatasetManifest(
        dataset_id=dataset_id, generator_version=GENERATOR_VERSION,
        task="grid_record_field", modalities=["spatial", "semantic", "visual"],
        count=n,
        config={"class": doc_class.name, "seed": seed, "spec": asdict(doc_class)},
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    write_dataset(datasets_dir, manifest, samples)
    return ds_dir
```

- [ ] **Step 2: Delete the legacy builder**

```bash
git rm harness/src/tablelab/generate.py
```

- [ ] **Step 3: Verify a full build works end to end**

Run (from `harness/`):
```bash
uv run python -c "import tempfile, json, pathlib; from tablelab import classes as c; from tablelab.build import build_dataset; d=tempfile.mkdtemp(); build_dataset(d,'inv',c.get('invoice'),seed=7,n=3); m=json.loads((pathlib.Path(d)/'inv'/'manifest.json').read_text()); print('class', m['config']['class'], '| fields', [f['name'] for f in m['config']['spec']['fields']], '| images', len(list((pathlib.Path(d)/'inv'/'images').glob('*.png'))))"
```
Expected: `class invoice | fields ['description', 'quantity', 'unit_price', 'amount'] | images 3`.

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/build.py
git commit -m "feat: build_dataset orchestrator (compose->layout->render->contract); retire generate.py"
```

---

## Task 8: Golden regression — prove output is unchanged

This is the correctness anchor. The refactored layout+render must reproduce the legacy token snapshot from Task 1.

**Files:**
- Create: `harness/tests/test_golden.py`

- [ ] **Step 1: Write the test**

```python
import json
import random
from pathlib import Path

from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _gen_tokens(cls_name: str, seed: int, n: int) -> list[list[dict]]:
    dc = classlib.get(cls_name)
    rng = random.Random(seed)
    W, H = dc.layout.page
    out: list[list[dict]] = []
    for _ in range(n):
        placed = layout(dc, rng)
        _img, boxes = render(placed, dc)
        out.append([
            {"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
             "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4),
             "text": p.text, "label": p.label}
            for p, b in zip(placed, boxes)
        ])
    return out


def test_invoice_matches_legacy_golden():
    got = _gen_tokens("invoice", seed=7, n=3)
    want = json.loads(GOLDEN.read_text())
    assert got == want
```

- [ ] **Step 2: Run the golden test**

Run (from `harness/`):
```bash
uv run pytest tests/test_golden.py -v
```
Expected: `test_invoice_matches_legacy_golden PASSED`. If it FAILS, the refactor changed output — diff `got` vs `want` to find which token/box/RNG-order diverged; do not adjust the golden file to match new output.

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_golden.py
git commit -m "test: golden regression — refactored layout+render reproduces legacy tokens"
```

---

## Task 9: `cli.py` — `build` / `list` / `inspect`

**Files:**
- Create: `harness/src/tablelab/cli.py`

- [ ] **Step 1: Write the CLI**

```python
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path

from . import classes as classlib
from .specs import fork
from .build import build_dataset
from .artifacts import read_dataset


def _build(args):
    dc = classlib.get(args.cls)
    L = dc.layout
    if args.rows:
        L = replace(L, rows=(args.rows[0], args.rows[1]))
    if args.page:
        L = replace(L, page=(args.page[0], args.page[1]))
    if (L is not dc.layout):
        dc = fork(dc, layout=L)
    out = Path(args.out)
    build_dataset(out.parent, out.name, dc, seed=args.seed, n=args.n)
    print(f"built {args.n} {args.cls} samples -> {out}")


def _list(args):
    root = Path(args.datasets_dir)
    if not root.exists():
        print(f"no datasets dir at {root}")
        return
    found = False
    for d in sorted(p for p in root.iterdir() if (p / "manifest.json").exists()):
        m, _ = read_dataset(d)
        found = True
        print(f"{m.dataset_id:24} {m.config.get('class', '?'):10} n={m.count:<5} {m.created}")
    if not found:
        print(f"no datasets under {root}")


def _inspect(args):
    d = Path(args.datasets_dir) / args.id
    m, samples = read_dataset(d)
    spec = m.config.get("spec", {})
    fields = [f["name"] for f in spec.get("fields", [])]
    page = spec.get("layout", {}).get("page")
    ntok = sum(len(s.tokens) for s in samples)
    print(f"id:       {m.dataset_id}")
    print(f"class:    {m.config.get('class', '?')}")
    print(f"task:     {m.task}")
    print(f"samples:  {m.count}")
    print(f"tokens:   {ntok} ({ntok / max(m.count, 1):.1f}/sample)")
    print(f"fields:   {fields}")
    print(f"page:     {page}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="tablelab.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a synthetic dataset")
    b.add_argument("--class", dest="cls", required=True,
                   help=f"document class {classlib.classes()}")
    b.add_argument("--n", type=int, default=12, help="number of samples")
    b.add_argument("--out", required=True, help="dataset dir, e.g. ../datasets/<id>")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--rows", type=int, nargs=2, metavar=("MIN", "MAX"),
                   help="override record-count range")
    b.add_argument("--page", type=int, nargs=2, metavar=("W", "H"),
                   help="override page size")
    b.set_defaults(fn=_build)

    ls = sub.add_parser("list", help="list local datasets")
    ls.add_argument("--datasets-dir", default="../datasets")
    ls.set_defaults(fn=_list)

    ins = sub.add_parser("inspect", help="inspect a dataset")
    ins.add_argument("id")
    ins.add_argument("--datasets-dir", default="../datasets")
    ins.set_defaults(fn=_inspect)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test all three subcommands (writes to the real `datasets/`)**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class eob --n 8 --out ../datasets/smoke-eob --seed 7
uv run python -m tablelab.cli list
uv run python -m tablelab.cli inspect smoke-eob
```
Expected: `build` shows a tqdm bar then `built 8 eob samples -> ../datasets/smoke-eob`; `list` includes a `smoke-eob  eob  n=8  <timestamp>` row; `inspect` prints class `eob`, `samples: 8`, a `tokens: …/sample` line, the 5 EOB field names, and `page: [1000, 1414]`.

- [ ] **Step 3: Verify an override works**

Run (from `harness/`):
```bash
uv run python -m tablelab.cli build --class invoice --n 4 --out ../datasets/smoke-inv --rows 3 3 --page 800 1000
uv run python -m tablelab.cli inspect smoke-inv
```
Expected: `inspect` shows `page: [800, 1000]`; every sample has exactly `3 records × 4 fields = 12` tokens (so `tokens: 48 (12.0/sample)`).

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/cli.py
git commit -m "feat: CLI (argparse + tqdm) — build/list/inspect over the compositional API"
```

---

## Task 10: Viewer eyeball + docs; clean up smoke datasets

**Files:**
- Modify: `harness/README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Eyeball a built dataset in the viewer**

Run (from repo root, in a separate terminal):
```bash
npm --prefix viewer install
npm --prefix viewer run dev
```
Open http://localhost:5173, pick `smoke-eob` (or `smoke-inv`) as the source. Confirm: the page image renders, token boxes align to the rendered text, and ground-truth `record·field` labels look right. Stop the dev server when done.

- [ ] **Step 2: Update `harness/README.md` module list**

Replace the `generate.py` bullet and the `_(planned)_ cli.py` bullet in the "Modules" section with:
```markdown
- `specs.py` — compositional spec types: `FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`DocumentClass` + `fork()`.
- `fields.py` — value-sampler registry keyed by semantic type.
- `classes.py` — `DocumentClass` registry + built-in `invoice`/`eob`/`receipt`.
- `layout.py` — `PlacedToken` IR + `layout()` (Pillow-free placement).
- `render.py` — `render()`: draw placed tokens → PNG + glyph boxes.
- `build.py` — `build_dataset()` orchestrator (compose → layout → render → contract).
- `cli.py` — `argparse` + `tqdm`: `build` / `list` / `inspect`.
```
Also add a usage line under Setup:
```markdown
Build a dataset: `uv run python -m tablelab.cli build --class eob --n 100 --out ../datasets/<id>`
```

- [ ] **Step 3: Update `AGENTS.md` current-state note**

In the "Current state & active milestone" section, update the **Built** line to include the toolkit backbone, e.g. append:
```
; synth-toolkit backbone (compositional spec API specs/fields/classes/layout/render/build + build/list/inspect CLI)
```
and adjust the "Active milestone" prose to note the backbone is done and the next step is the first structural-realism follow-on (multi-token cells).

- [ ] **Step 4: Remove the smoke datasets (they're gitignored, just local cleanup)**

Run (from repo root):
```bash
rm -rf datasets/smoke-eob datasets/smoke-inv
```

- [ ] **Step 5: Commit the docs**

```bash
git add harness/README.md AGENTS.md
git commit -m "docs: synth-toolkit backbone — module list, CLI usage, current-state"
```

---

## Done criteria

- `uv run pytest tests/test_golden.py -v` passes (output identical to legacy).
- `python -m tablelab.cli build|list|inspect` all work, including `--rows`/`--page` overrides.
- A built dataset renders correctly in the viewer.
- `generate.py` is gone; its responsibilities live in the focused modules.
- `docs/specs/2026-06-13-synth-toolkit-backbone-design.md` requirements are all covered.

## Self-review notes (for the implementer)

- **Byte-identical hinge:** the RNG stream is shared across samples and drawn in the order `randint → per-cell sample (row-major) → shuffle`. Tasks 3/5 must not reorder or add/remove draws. If the golden test fails, that ordering is the first place to look.
- **`label` is an open dict** on both `PlacedToken` and contract `Token` — that's deliberate: follow-ons set `null` (background), repeat a label (multi-token), or add `region` (multi-table) without schema changes.
- **`StructureSpec` is intentionally empty today** — it's the named seam for the six structural-realism follow-ons, not dead code.
