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

See the active spec: [docs/specs/2026-06-13-v0-loop-closes-design.md](docs/specs/2026-06-13-v0-loop-closes-design.md).

**v0 — "the loop closes":** synthetic dataset builder → from-scratch model → frozen metric →
static run artifacts → local viewer overlaying predictions on the page. The data is multimodal
from the start; the first model is spatial-only. Specs live in `docs/specs/`; each milestone gets
its own.

## How to work in this repo

For agents and humans alike. Read this section and the active spec before starting.

- **Git is an append-only lab notebook.** Failures and crashes are kept and labeled, never
  `git reset` away — they're the lessons.
- **Branches.** `master` holds the harness plus the *current-best* model; only deliberate
  promotions land there. Each line of inquiry lives on an `exp/<line>` branch, where **every run
  is a commit** — the model mutation, its emitted run artifacts, and an appended `runs/index.json`
  row.
- **Runs are records, not searches.** "Keep" / "discard" / "crash" is a `status` field in the
  artifact, not a git operation.
- **Run ids are globally unique** (`{date}-{device}-{shorthash}`), so artifacts from different
  branches and machines never collide and can be unioned for a cross-branch timeline.
- **Two data layers.** `runs/` is the git-tracked, binary-free ledger (metrics, config, prediction
  samples), and references a dataset by `dataset_id`. `datasets/` holds the curated synthetic data
  (images + samples) — **local and gitignored**, built to be reused, culled, and forked into
  variants. The viewer serves and composes both locally; proper dataset storage is a later concern.
- **The contract is the seam.** Schema in the active spec (`schema_version`); the viewer reads
  artifacts only — no backend.
- **Review is PR-style.** Propose a change as a diff plus a one-line rationale; the human accepts,
  rejects, or redirects.
- **Lean.** Small diffs, reviewable changes, tight docs.

## Runtimes

Runs on both an Apple-silicon Mac (MPS) and an NVIDIA GPU (CUDA) — device-agnostic from line one
(`cuda` → `mps` → `cpu`). Cross-machine result *comparability* is not a goal yet; both runtimes
just need to train and evaluate.

## Status

Building v0 — **multimodal data foundation** (spatial / semantic / visual). Env ✓. Revising the
contract → dataset-builder → image-overlay viewer (schema v2), then the spatial (M0) model.
Upstream LM files (`train.py`, `prepare.py`, `program.md`) are parked in `reference/`.

## License

MIT
