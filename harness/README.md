---
kind: readme
status: living
updated: 2026-07-01
---
# harness

The Python side of the autoresearch document-extraction harness — the synthetic **dataset builder**,
the model, the training loop, and the **artifact contract**. Package: `src/tablelab/` (src-layout),
managed with `uv`.

## Overview

The dataset builder and the artifact contract are built; the model + training loop are next. A
compositional spec API — `FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`JitterSpec`/
`DocumentClass` (modules `specs`/`fields`/`classes`/`layout`/`render`/`build`) — joins through a
Pillow-free placed-cell IR, with a `build`/`list`/`inspect` CLI writing `datasets/<id>/`. The layout
pass (`layout_with_targets`) authors the grounded extraction target alongside words/cells/regions,
emitted per sample (`manifest.task = "extraction"`); the `eob` class exercises the full
structural-realism surface.

The **contract** (`artifacts.py`, `schema_version = 5`) is the seam between data and runs, in three
additive layers. **Observables**: `Word`s are atomic (`bbox` + `text`, one per whitespace word, no
per-word label). **Structure**: meaning-of-drawing lives on `Cell`s (`row_index`/`column_index`/`span`/
`role`/`field`, grouping words via `word_ids`) under typed `Region`s (`table`/`form`); globals → a
`form` region, background → cell-less words. **Targets** (v5, additive — observables/structure
serialization unchanged): a `Sample` carries `targets` (and symmetric `predictions`) keyed by task,
each a `Node` tree of singleton `fields` and repeating `field_groups` (lists of record `Node`s — root
and record share one type). A `Field` is one grounded value `{value, word_ids, cell}`; an absent field
is explicit-empty (`value:""`, `word_ids:[]`, the empty cell). Targets are *authored in the placement
loop* (globals → root fields, each table → a field_group of per-row records flattened across
instances), never reconstructed from geometry.

The **model loop** has not started — it is the spine's M0 (spatial): a from-scratch, box-only model
that produces the materialized target and beats the geosort baseline on geometrically-varied data
(skew / perspective / aspect), proven by prediction invariance under transform. Sequencing →
[roadmap.md](../docs/roadmap.md).

## Setup

```bash
cd harness
uv sync
```

Device-aware torch — MPS on Apple silicon, CUDA on NVIDIA, CPU fallback:

```bash
uv run python -c "from tablelab.device import get_device; print(get_device())"
```

## CLI (`tablelab.cli`)

```bash
uv run python -m tablelab.cli build --class eob --n 100 --out ../datasets/eob-demo
uv run python -m tablelab.cli list
uv run python -m tablelab.cli inspect eob-demo
```

`build` flags:
- structure: `--rows MIN MAX`, `--instances MIN MAX` (stacked instances, `region`-tagged), `--header` (field-name header row), `--background N` (class-aware non-table words in reserved slots). Every cell emits one `Word` per whitespace word (atomic, always — no flag).
- spanning cells / grouped headers are **class-defined** (no CLI flag): `FieldSpec.group` (contiguous fields → a header banner band) and `TableSpec.section`/`totals` (`SpanRowSpec` of colspan `SpanCell`s → a section heading / TOTALS row per instance). The `eob` class showcases all three.
- spacing: `--page W H`, `--row-gap PX`, `--instance-gap PX`, `--section-gap PX`, `--globals-per-row N` (pack label:value pairs across a global row).
- jitter: `--jitter ROW_H COL_W OFFSET BASELINE` (per-axis magnitudes, 0 = off; bounded/zero-sum).
- rendering: `--autoscale-font` (shrink an overflowing table's font to fit the page).
- other: `--seed`. Classes: `invoice`, `eob`, `receipt`.

Column widths are content-aware (each column sized to its content, leftover width shared by weight);
`FieldSpec.fill < 1.0` leaves some cells empty. Row/instance ranges are sampled only among
page-feasible combinations; impossible minimums fail before output. Builds stage atomically and
refuse existing dataset IDs.

The `eob` class is a representative explanation-of-benefits form: member/provider **global fields**
(2-up) + a repeated ten-column **claim_line** table (service date, code, description, billed,
allowed, deductible, copay, coinsurance, plan paid, owed — financial columns sparse) on a wide
`1500x1414` page, with **Charges / Patient Responsibility / Plan & Balance header banners**, a sampled
**service-category section row**, and a **TOTALS row** per instance. `invoice` (golden-pinned, uniform
columns) and `receipt` are single tables.

## Structure (`src/tablelab/`)

- `device.py` — `get_device()` (cuda → mps → cpu).
- `artifacts.py` — the schema-v5 contract (`Region`/`Cell`/`Word` + `targets`/`predictions`): datasets + runs (`read`/`write`/`validate`, manifests).
- `specs.py` — compositional spec types: `FieldSpec`/`LayoutSpec`/`StructureSpec`/`JitterSpec`/`RenderSpec`/`SpanCell`/`SpanRowSpec`/`DocumentClass` + `fork()`.
- `fields.py` — value-sampler registry keyed by semantic type + per-type default column weights.
- `classes.py` — `DocumentClass` registry + built-in `invoice`/`eob`/`receipt`.
- `layout.py` — `PlacedWord` IR + `layout()`: capacity planner, content-aware columns, gaps, jitter.
- `jitter.py` — bounded/zero-sum jitter helpers (column edges, row height, word offset).
- `metrics.py` — `text_width()`: estimate rendered text width from the render font (for column sizing).
- `render.py` — `render()`: draw placed words (per-word font size) → PNG + glyph boxes.
- `build.py` — `build_dataset()` orchestrator (compose → layout → render → contract).
- `cli.py` — `argparse` + `tqdm`: `build` / `list` / `inspect`.
- _(planned)_ `model.py`, `metric.py`, `train.py`.

Datasets are written to the repo-root `datasets/` (local, gitignored); run artifacts to `runs/`
(git-tracked).

## Agentic Guidelines

**How & why we build (durable decisions):**
- **From scratch.** Favor implementing internals over wiring off-the-shelf models; explain the *why* — this is pedagogy as much as delivery.
- **The contract is the seam.** `schema_version = 5` in `artifacts.py`; observables stay `bbox` + `text` (+ image), structural/semantic truth lives in the cell/region annotation layer, and targets are additive over both.
- **Targets are authored, never reconstructed** — the placement loop emits the grounded `fields` / `field_groups` target; do not rebuild it from geometry.
- **Keep the source representation task-agnostic** — task framings (token classification, NLQ, structure, record extraction) are `derive_*` projections, not baked into the data.
- **Don't classify value types** (date/dollar/id) — the useful semantic label is the template's **field slot** (`copay`, `total`), not the data type.

**Working guidance:**
- Use `uv` as the default Python runner (`uv sync`, then `uv run ...`) for commands in this module.
- Device-agnostic from line one (`cuda` → `mps` → `cpu`); never hardcode a device.

## Agentic Validation

**Verify by running — no TDD.** Exercise a change and show the result; don't claim done without it.

- `uv sync` — install (device-aware torch: MPS / CUDA / CPU).
- `uv run python -c "from tablelab.device import get_device; print(get_device())"` — device check.
- `uv run python -m tablelab.cli build --class <name> --n <count> --out ../datasets/<id>` — build a dataset (smoke-tests the generator).
- `uv run python -m tablelab.cli list` / `inspect <id>` — list / inspect local datasets.
