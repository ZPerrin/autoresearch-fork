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

Build a dataset: `uv run python -m tablelab.cli build --class eob --n 100 --out ../datasets/<id>`

## Modules (`src/tablelab/`)

- `device.py` — `get_device()` (cuda → mps → cpu).
- `artifacts.py` — the schema-v2 contract: datasets + runs (`read`/`write`/`validate`, manifests).
- `specs.py` — compositional spec types: `FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`DocumentClass` + `fork()`.
- `fields.py` — value-sampler registry keyed by semantic type.
- `classes.py` — `DocumentClass` registry + built-in `invoice`/`eob`/`receipt`.
- `layout.py` — `PlacedToken` IR + `layout()` (Pillow-free placement).
- `render.py` — `render()`: draw placed tokens → PNG + glyph boxes.
- `build.py` — `build_dataset()` orchestrator (compose → layout → render → contract).
- `cli.py` — `argparse` + `tqdm`: `build` / `list` / `inspect`.
- _(planned)_ `model.py`, `metric.py`, `train.py`.

Datasets are written to the repo-root `datasets/` (local, gitignored); run artifacts to `runs/`
(git-tracked). See `../AGENTS.md` and `../docs/specs/` for the design and conventions.
