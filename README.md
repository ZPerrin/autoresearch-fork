# autoresearch (fork) — a from-scratch lab for document table extraction

A learning-first research harness for building, training, and evaluating transformer models
that recover **table structure from document layouts** — words plus their bounding boxes, the
modality you get out of OCR/Textract. The aim is twofold: learn the theory by implementing it
from scratch, and make headway on generalizable table extraction from semi-structured documents
(EOBs, invoices, receipts). Real labeled data is scarce, so we prove ideas on unlimited
**synthetic** data first.

Forked from karpathy's [autoresearch](https://github.com/karpathy/autoresearch) (a single-GPU
[nanochat](https://github.com/karpathy/nanochat)). We keep its *machinery* — a single-file
model and a fast train → evaluate → keep/discard loop against a frozen metric — but repoint it
from text language modeling onto 2D structured prediction over positioned tokens.

## What we're building

See the active spec: [docs/specs/2026-06-13-v0-loop-closes-design.md](docs/specs/2026-06-13-v0-loop-closes-design.md).

**v0 — "the loop closes":** synthetic generator → from-scratch layout transformer → frozen
metric → static artifacts → local Vite/React viewer. The synthetic data itself is an experiment.
Specs live in `docs/specs/`; each milestone gets its own.

## How to work in this repo

For agents and humans alike. Read this section and the active spec before starting.

- **Git is an append-only lab notebook.** Failures and crashes are kept and labeled, never
  `git reset` away — they're the lessons.
- **Branches.** `master` holds the harness (generator, model scaffold, viewer, env) plus the
  *current-best* model; only deliberate promotions land there. Each line of inquiry lives on an
  `exp/<line>` branch, where **every run is a commit** — the `train.py` mutation, its emitted
  artifacts, and an appended `runs/index.json` row.
- **Runs are records, not searches.** "Keep" / "discard" / "crash" is a `status` field in the
  artifact, not a git operation.
- **Run ids are globally unique** (`{date}-{device}-{shorthash}`), so artifacts from different
  branches and machines never collide and can be unioned for a cross-branch timeline.
- **Artifacts are the contract.** Each run emits machine-readable JSON under a git-tracked
  `runs/` dir (schema in the active spec). The viewer reads only these — no backend.
- **Data is regenerable from a seed.** Commit the seed + generator version, not datasets.
- **Review is PR-style.** Propose a change as a diff plus a one-line rationale; the human
  accepts, rejects, or redirects.
- **Lean.** Small diffs, reviewable changes, tight docs.

## Runtimes

Runs on both an Apple-silicon Mac (MPS) and an NVIDIA GPU (CUDA) — device-agnostic from line one
(`cuda` → `mps` → `cpu`). Cross-machine result *comparability* is not a goal yet; both runtimes
just need to train and evaluate. (Upstream's `pyproject.toml` pins a CUDA-only torch wheel that
won't install on Apple silicon — making the dependency setup device-aware is part of the env
foundation.)

## Status

Building v0 ([plan](docs/plans/2026-06-13-v0-loop-closes-plan.md)): Phase 0 env ✓ · Phase 1
contract ✓ · Phase 2 viewer (next) · Phases 3–4 (generator, model) pending. Upstream LM files
(`train.py`, `prepare.py`, `program.md`) stay as reference until v0 lands.

## License

MIT
