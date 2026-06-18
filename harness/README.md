# harness

The Python side of the autoresearch document-extraction harness — the synthetic **dataset builder**,
the model, the training loop, and the **artifact contract**. Package: `src/tablelab/` (src-layout),
managed with `uv`.

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

## Modules (`src/tablelab/`)

- `device.py` — `get_device()` (cuda → mps → cpu).
- `artifacts.py` — the schema-v4 contract (`Region`/`Cell`/`Word`): datasets + runs (`read`/`write`/`validate`, manifests).
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
(git-tracked). See `../AGENTS.md` and `../docs/specs/` for the design and conventions.
