# AGENTS.md — operating guide for autoresearch (fork)

Single source of truth for working in this repo, for agents and humans. (Claude Code loads this
via `@AGENTS.md` in `CLAUDE.md`.) Keep it concise and current.

## What this is

A from-scratch, learning-first research harness for **multimodal document information extraction** —
**spatial** (token bounding boxes), **semantic** (token text), **visual** (page image). Forked from
karpathy's `autoresearch` (single-GPU nanochat); we keep its machinery (single-file model, a fast
build → train → evaluate → keep/discard loop, a frozen metric) but repoint it at documents. Two
goals pursued together: **learn multimodal DL by building it from scratch**, and **make headway on
generalizable repeated-record extraction** (EOBs, invoices, receipts). Real labeled data is scarce,
so we curate **synthetic** data ourselves.

Authoritative design + roadmap: `docs/specs/2026-06-13-design-and-roadmap.md`.

## Layout

- `harness/` — Python module (src-layout package `src/tablelab/`): dataset builder, model, training,
  artifact contract. `uv` + device-aware torch + Pillow.
- `datasets/` — curated synthetic data: `<id>/{manifest.json, samples.json, images/}`.
  **Local & gitignored** — built to be reused, culled, forked into variants.
- `runs/` — the experiment ledger: `index.json` + `<run>/…`. **Git-tracked, binary-free**; references
  a dataset by `dataset_id`.
- `viewer/` — Vite/React split-pane review app (document image + overlay | metadata). No backend.
- `docs/specs/`, `docs/plans/` — design + plans. `reference/` — upstream LM files (parked).

## Commands

Python (run from `harness/`):
- `cd harness && uv sync` — install (device-aware torch: MPS on Apple silicon, CUDA on NVIDIA, CPU).
- `uv run python -c "from tablelab.device import get_device; print(get_device())"` — device check.
- (once built) `uv run python -m tablelab.cli build --class invoice --n 100 --out ../datasets/<id>`.

Viewer:
- `npm --prefix viewer install`, then `npm --prefix viewer run dev` → http://localhost:5173
  (dev middleware serves repo-root `/runs` + `/datasets`). Build: `npm --prefix viewer run build`.

## How we work (conventions)

- **Git is an append-only lab notebook.** Keep failures/crashes as a `status` label; never
  `git reset` to discard — they're the lessons.
- **Branches.** `master` = infra + current-best (deliberate promotions only). `exp/<line>` = one
  line of inquiry; **every run is a commit** (model mutation + run artifacts + an `index.json` row).
  Run ids are globally unique: `{date}-{device}-{shorthash}`.
- **Two data layers.** `runs/` = git-tracked JSON ledger; `datasets/` = local & gitignored curated
  data. The viewer composes both locally; on a machine without the dataset it still renders
  boxes/metrics, just no page image.
- **Contract is the seam** (`schema_version = 2`, defined in `artifacts.py`): observables (per-token
  `bbox` + `text`, per-sample `image`) are locked; task labels are open (`label`/`pred` dicts keyed
  by `config.task`); the annotation schema is deferred.
- **No TDD** for now — implement and verify by running.
- **PR-style review.** Propose changes as diffs + a one-line rationale; the human accepts/redirects.
- **Lean.** Small diffs, reviewable changes, tight docs. Specs in `docs/specs/`; each milestone gets
  its own. Brainstorm/design before building non-trivial features.

## Current state & active milestone

Built: env (MPS + CUDA), contract v2, multimodal dataset builder (field-appropriate grids → PNG,
one token per cell), split-pane viewer; synth-toolkit backbone (compositional spec API
specs/fields/classes/layout/render/build + build/list/inspect CLI).

**Active milestone — the synthetic data toolkit:** backbone is done. Next step: **structural
realism**, starting with multi-token cells. Full order — multi-token cells → header row →
background/non-table tokens → multiple tables + global fields → jitter/irregular → spanning cells
— then **document-class breadth** (EOB prioritized; it mirrors the real problem). **Visual realism
is deferred** but provisioned via the `RenderSpec` renderer seam.

Deferred next: the **model loop** (M0 spatial → run artifacts → predictions overlaid), see
`docs/specs/2026-06-13-v0-loop-closes-design.md`. Then the **modality ladder** M0→M3 (spatial → +text
→ +visual → fusion) as modality-ablation experiments.

## End-state (don't overfit early)

Repeated-record extraction against a **class-defined schema**: global/singleton fields (member,
provider) + table definitions (repeated records like `claim_line`: `service_date`, `amount_owed`, …)
+ multiple table instances per document. Modeling approach stays open (token classification,
extractive QA, structure+QA).

## Collaborator

Zeb: ~15y SAS, 7y applied ML, finishing a UMN CS grad program; going deeper into DL theory/PyTorch.
Real problem = generalizable table/record extraction from OCR/Textract output (bbox + text). Works
across an M4 MacBook (MPS) and a Windows 3080 Ti (CUDA). Prefers building from scratch together and
learning by doing; values clean structure and lean docs.
