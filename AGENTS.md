# AGENTS.md — operating guide for autoresearch (fork)

How to work in this repo, for agents and humans. (Claude Code loads this via `@AGENTS.md` in
`CLAUDE.md`; Codex loads it natively.) Keep it lean and current. What this project *is* and *why*:
[docs/architecture/charter.md](docs/architecture/charter.md). Where it's headed:
[docs/architecture/roadmap.md](docs/architecture/roadmap.md).

## Bearings (start here each session)

Before starting a task, get oriented: read [docs/architecture/index.md](docs/architecture/index.md)
(the map of what exists) and [docs/architecture/roadmap.md](docs/architecture/roadmap.md) (current
focus), and skim `git log --oneline -15` for recent activity. Pull deeper docs on demand from the index.

## Layout

- `harness/` — Python package `src/tablelab/`: dataset builder, model, training, artifact contract.
  `uv` + device-aware torch + Pillow.
- `datasets/` — curated synthetic data `<id>/{manifest.json, samples.json, images/}`. **Local & gitignored.**
- `runs/` — experiment ledger: `index.json` + `<run>/…`. **Git-tracked, binary-free**; references a
  dataset by `dataset_id`.
- `viewer/` — Vite/React split-pane review app (page image + interactive structure overlay). No backend.
- `docs/` — `architecture/` (durable core: charter, roadmap, index, conventions), `design/` (ideation),
  `specs/` + `plans/` (transient scaffolding). `reference/` — upstream LM files (parked).

## Commands

Python (run from `harness/`):
- `cd harness && uv sync` — install (device-aware torch: MPS on Apple silicon, CUDA on NVIDIA, CPU).
- `uv run python -c "from tablelab.device import get_device; print(get_device())"` — device check.
- `uv run python -m tablelab.cli build --class <name> --n <count> --out ../datasets/<id>` — build a dataset.
- `uv run python -m tablelab.cli list` / `inspect <id>` — list local datasets / inspect one.

Viewer:
- `npm --prefix viewer install`, then `npm --prefix viewer run dev` → http://localhost:5173. Build:
  `npm --prefix viewer run build`.

## How we work

- **Docs.** One home per fact, split by volatility. The taxonomy, the design→spec→plan→distill funnel,
  nomenclature, and the writing ethos live in
  [docs/architecture/conventions.md](docs/architecture/conventions.md). Git is the activity log — we
  don't hand-maintain a running log. `/wrap` (per-session) and `/refine-docs` (holistic) keep the
  durable docs sharp; both stage changes for review, never auto-commit.
- **Branches & git.** `master` = infra + current-best (deliberate promotions only). `exp/<line>` = one
  line of inquiry; **every run is a commit** — git is an append-only lab notebook, failures kept as a
  `status` label, never `git reset` to discard. Run ids: `{date}-{device}-{shorthash}`.
- **Contract is the seam** (`schema_version = 4`, in `artifacts.py`) — see the Contract entry in
  [docs/architecture/index.md](docs/architecture/index.md).
- **No TDD** — implement and verify by running. **PR-style review** — propose changes as diffs + a
  one-line rationale; the human accepts/redirects. **Lean** — small diffs, reviewable changes, tight docs.

## Collaborator

Zeb: ~15y SAS, 7y applied ML, finishing a UMN CS grad program; going deeper into DL theory/PyTorch.
Real problem = generalizable table/record extraction from OCR/Textract output (bbox + text). Works
across an M4 MacBook (MPS) and a Windows 3080 Ti (CUDA). Prefers building from scratch together; values
clean structure and lean docs.
