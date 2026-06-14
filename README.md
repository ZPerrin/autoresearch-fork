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

- `harness/` — Python module: dataset builder, model, training, artifacts (`src/tablelab/`)
- `viewer/` — Vite/React review app (overlays predictions on the page image)
- `runs/` — git-tracked experiment ledger (JSON only, no binaries)
- `datasets/` — curated synthetic datasets (images + samples), **local & gitignored**
- `docs/` — specs and plans
- `reference/` — upstream LM files (karpathy/autoresearch) parked for reference

## What we're building

Authoritative design & roadmap:
[docs/specs/2026-06-13-design-and-roadmap.md](docs/specs/2026-06-13-design-and-roadmap.md).

The harness is in place — env, contract v2, multimodal dataset builder, split-pane viewer. The
**active milestone is the synthetic data toolkit**: its backbone is built — a compositional API
(`FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`DocumentClass`) and a `build`/`list`/
`inspect` CLI to declare document classes and curate/fork datasets. Next we climb **structural
realism** (multi-token cells first), then document-class breadth, before the model loop. Specs
live in `docs/specs/`; each milestone gets its own.

## How to work in this repo

See **[AGENTS.md](AGENTS.md)** — the operating guide for agents and humans (layout, commands,
branch model, the artifact contract, conventions). In short: git is an append-only lab notebook
(failures kept as `status` labels, never `git reset`); `runs/` is the git-tracked JSON ledger and
`datasets/` is local & gitignored; review is PR-style; no TDD (verify by running); keep it lean.

## Runtimes

Runs on both an Apple-silicon Mac (MPS) and an NVIDIA GPU (CUDA) — device-agnostic from line one
(`cuda` → `mps` → `cpu`). Cross-machine result *comparability* is not a goal yet; both runtimes
just need to train and evaluate.

## Status

Harness built: env ✓, contract v2 ✓, multimodal dataset builder ✓, split-pane viewer ✓,
synth-toolkit backbone ✓ (compositional API + `build`/`list`/`inspect` CLI). **Active: the
synthetic data toolkit** — next is structural realism (multi-token cells → … → spanning cells) →
document-class breadth; visual realism deferred. The model loop comes after. Upstream LM files
(`train.py`, `prepare.py`, `program.md`) are parked in `reference/`.

## License

MIT
