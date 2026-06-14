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

## Modules (`src/tablelab/`)

- `device.py` — `get_device()` (cuda → mps → cpu).
- `artifacts.py` — the schema-v2 contract: datasets + runs (`read`/`write`/`validate`, manifests).
- `generate.py` — synthetic dataset builder: renders grids to PNG with field-appropriate text,
  captures word boxes + labels, writes a `datasets/<id>/`.
- _(planned)_ `cli.py` (argparse + tqdm), `model.py`, `metric.py`, `train.py`.

Datasets are written to the repo-root `datasets/` (local, gitignored); run artifacts to `runs/`
(git-tracked). See `../AGENTS.md` and `../docs/specs/` for the design and conventions.
