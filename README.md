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

## Layout

- [`harness/`](harness/) — Python module: dataset builder, model, training, artifacts (`src/tablelab/`)
- [`viewer/`](viewer/) — Vite/React review app (overlays document structure on the page image)
- [`runs/`](runs/) — git-tracked experiment ledger (JSON only, no binaries)
- `datasets/` — curated synthetic datasets (images + samples), **local & gitignored**
- [`docs/`](docs/) — [`architecture/`](docs/architecture/) (charter, roadmap, index, conventions), [`design/`](docs/design/) (ideation), [`specs/`](docs/specs/) + [`plans/`](docs/plans/) (scaffolding)
- [`reference/`](reference/) — upstream LM files (karpathy/autoresearch) parked for reference

## What we're building

Durable design lives in [docs/architecture/](docs/architecture/): the
[charter](docs/architecture/charter.md) (why), [roadmap](docs/architecture/roadmap.md) (milestones),
[index](docs/architecture/index.md) (a map of what exists today), and
[conventions](docs/architecture/conventions.md) (how the docs work). Start at the **index** for the
harness — the schema-v4 contract, the synthetic dataset builder, and the viewer.

## How to work in this repo

See **[AGENTS.md](AGENTS.md)** — the operating guide for agents and humans (layout, commands,
branch model, the artifact contract, conventions). In short: git is an append-only lab notebook
(failures kept as `status` labels, never `git reset`); `runs/` is the git-tracked JSON ledger and
`datasets/` is local & gitignored; review is PR-style; no TDD (verify by running); keep it lean.

## Runtimes

Runs on both an Apple-silicon Mac (MPS) and an NVIDIA GPU (CUDA) — device-agnostic from line one
(`cuda` → `mps` → `cpu`). Cross-machine result *comparability* is not a goal yet; both runtimes
just need to train and evaluate.

## License

MIT
