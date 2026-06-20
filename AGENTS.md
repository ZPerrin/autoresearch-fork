---
kind: guide
status: living
updated: 2026-06-19
---

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

## Getting Oriented

What this project *is* and *why* →
[charter](docs/architecture/charter.md). Where it's headed → [roadmap](docs/architecture/roadmap.md).

Before starting a task:

- **Read** [index](docs/architecture/index.md) — the map of what exists; pull deeper docs from it on demand.
- **Check** [roadmap](docs/architecture/roadmap.md) `## Now` — the current focus.
- **Skim** `git log --oneline -15` — recent activity (git is the activity log; we keep no written one).

### Repository Map

- [harness/](harness/) — Python package `src/tablelab/`: dataset builder, model, training, contract. `uv` + device-aware torch + Pillow.
- `datasets/` — curated synthetic data `<id>/{manifest, samples, images}`. **Local & gitignored.**
- [runs/](runs/) — experiment ledger: `index.json` + `<run>/…`. **Git-tracked, binary-free.**
- [viewer/](viewer/) — Vite/React split-pane review app (page image + structure overlay). No backend.
- [docs/](docs/) — [architecture/](docs/architecture/) (durable: charter/roadmap/index/conventions), [design/](docs/design/) (ideation), [specs/](docs/specs/) + [plans/](docs/plans/) (scaffolding). [reference/](reference/) — parked upstream LM files.
- [scripts/](scripts/) — repo tooling (e.g. [doc-lint.py](scripts/doc-lint.py)).

## Agentic Guidelines

- **From scratch, together.** Favor implementing internals over wiring off-the-shelf models; explain the *why* — this is pedagogy as much as delivery.
- **Lean.** Small diffs, reviewable changes, tight docs. Brainstorm/design before non-trivial features.
- **PR-style review.** Propose changes as diffs + a one-line rationale; the human accepts/redirects.
- **Docs are routing, not a log.** One home per fact; maintain the durable layer with `/wrap` (per-session) and `/refine-docs` (holistic). The system is defined in [conventions](docs/architecture/conventions.md).
- **Append-only lab notebook.** `master` = infra + current-best (deliberate promotions); `exp/<line>` = one line of inquiry, every run a commit; keep failures as a `status` label, never `git reset`. Run ids `{date}-{device}-{shorthash}`.
- **Contract is the seam.** `schema_version = 5` in `artifacts.py`; see the Contract entry in [index](docs/architecture/index.md).

## Agentic Validation

**Verify by running — no TDD.** Exercise a change and show the result; don't claim done without it.

Python — from [harness/](harness/):
- `uv sync` — install (device-aware torch: MPS / CUDA / CPU).
- `uv run python -c "from tablelab.device import get_device; print(get_device())"` — device check.
- `uv run python -m tablelab.cli build --class <name> --n <count> --out ../datasets/<id>` — build a dataset (smoke-tests the generator).
- `uv run python -m tablelab.cli list` / `inspect <id>` — list / inspect local datasets.

Viewer:
- `npm --prefix viewer install`, then `npm --prefix viewer run dev` → http://localhost:5173. Build: `npm --prefix viewer run build`.

Docs:
- `python3 scripts/doc-lint.py` — link hygiene (broken links + unlinked nav paths). Run before staging doc changes.
