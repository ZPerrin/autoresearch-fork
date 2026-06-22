# autoresearch (fork) — a from-scratch lab for multimodal document extraction

A learning-first research harness for building, training, and evaluating models that extract
structured information from documents — words, their bounding boxes, and the page image, the
modalities you get out of OCR/Textract. The aim is twofold: learn the theory by implementing it
from scratch, and make headway on generalizable extraction from semi-structured documents
(EOBs, invoices, receipts). Real labeled data is scarce, so we prove ideas on **synthetic** data
we curate ourselves.

Forked from karpathy's [autoresearch](https://github.com/karpathy/autoresearch) (a single-GPU
[nanochat](https://github.com/karpathy/nanochat)). We keep its *machinery* — a single-file model
and a fast train → evaluate → keep/discard loop against a frozen metric — but repoint it from
text language modeling onto **multimodal document extraction**: spatial (boxes), semantic (text),
and visual (page image). The data carries all three; models climb a modality ladder from
spatial-only upward.

## Overview
_updated: 2026-06-21_

The synthetic dataset builder and the materialized v5 contract (grounded `fields` / `field_groups`
targets per document) are built; the viewer renders the structure and is gaining the target tree +
prediction diff; the from-scratch model loop is next (spatial M0). Runs device-agnostic on Apple
silicon (MPS), NVIDIA (CUDA), or CPU. The durable *why* is the [charter](docs/config/charter.md);
where it's headed is the [roadmap](docs/config/roadmap.md).

## Module Map

- [harness](harness/) - Python package `src/tablelab/`: dataset builder, model, training, the artifact contract. `uv` + device-aware torch.
- [viewer](viewer/) - Vite/React split-pane review app (page image + structure overlay). No backend.
- [runs](runs/) - git-tracked experiment ledger (`index.json` + per-run JSON, no binaries).
- [docs](docs/) - durable design docs + how docs work ([docs/README.md](docs/README.md)).
- `datasets/` - curated synthetic data `<id>/{manifest, samples, images}`. **Local & gitignored.**
- [reference](reference/) - parked upstream LM files (karpathy/autoresearch).

## Getting Started

Each module sets up independently:

```bash
# harness (Python) — see harness/README.md
cd harness && uv sync

# viewer (Node) — see viewer/README.md
cd viewer && npm install && npm run dev   # http://localhost:5173
```

`uv` installs device-aware torch (MPS / CUDA / CPU). Build a first dataset with
`uv run python -m tablelab.cli build --class eob --n 100 --out ../datasets/eob-demo`, then review it
in the viewer.

## Documentation

- [docs/README.md](docs/README.md) - how docs work in this repo (taxonomy, lifecycle, conventions)
- [docs/config/charter.md](docs/config/charter.md) - why this project exists and the bet it makes
- [docs/config/roadmap.md](docs/config/roadmap.md) - milestones and current focus
- [AGENTS.md](AGENTS.md) - how we work; repo context for coding agents (`CLAUDE.md` symlinks to it)
