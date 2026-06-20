# Doc System + Session Ritual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `docs/architecture/` durable core, slim the duplicated/stale docs into it, and add the session ritual (thin SessionStart hook + `/wrap` + `/refine-docs` skills).

**Architecture:** A progressive-disclosure doc layer: `architecture/` holds the living core (charter, roadmap, index, conventions) and feature docs; `design/` and `specs/`+`plans/` are transient scaffolding pruned via `/wrap`. Portable grounding lives in `AGENTS.md`; a Claude-only hook pushes live `git log`. Git is the activity log — nothing hand-maintains a running log.

**Tech Stack:** Markdown + YAML frontmatter; bash (hook script); Claude Code skills (`SKILL.md`) and `.claude/settings.json` hooks.

**Spec:** [../specs/2026-06-19-doc-system-and-session-ritual-design.md](../specs/2026-06-19-doc-system-and-session-ritual-design.md)

**Conventions for this plan:** No TDD — implement, then **verify by running** (link-checks, grep, dry-runs). Frequent commits (one per task). Already on branch `infra/doc-system`. Paste file content **exactly** — these docs are the deliverable.

---

## Phase 1 — The durable core (`docs/architecture/`)

### Task 1: conventions.md — the self-describing system

**Files:**
- Create: `docs/architecture/conventions.md`

- [ ] **Step 1: Create the file with this exact content**

```markdown
---
kind: conventions
status: living
updated: 2026-06-19
---

# Documentation conventions

How docs work in this repo: the taxonomy, the lifecycle, the nomenclature, and the writing ethos. The
skills (`/wrap`, `/refine-docs`) and the SessionStart hook reference this file; they do not redefine it.

## Taxonomy — one home per fact, split by volatility

- `docs/architecture/` — the durable core, the progressive-disclosure hub.
  - `charter.md` — the WHY (mission, the bet, non-goals, end-state). Rarely changes.
  - `roadmap.md` — long-horizon milestones + `## Now`/`## Next`. Changes on milestone events.
  - `index.md` — README-for-agents: a functional map of what exists, linking to the deep docs.
  - `conventions.md` — this file.
  - feature docs / diagrams / folders — added only when a result earns its own documentation.
- `docs/design/` — ideation, not yet actionable. Pruned once it graduates to a spec or ships.
- `docs/specs/`, `docs/plans/` — superpowers-flow scaffolding. Pruned on `/wrap` once implemented.
- `AGENTS.md` — how we work (layout, commands, conventions, bearings protocol). Auto-loaded, portable.
- Git history — the activity log. We do not hand-maintain a running log anywhere.

## Lifecycle — the funnel

`design/<idea>.md` → `specs/` + `plans/` → implemented + verified → `/wrap` distills the durable
essence (written from the code, not the spec) into an `index.md` section (plus a hardened doc if it
earns one) and, on milestone events, `roadmap.md`. The spec/plan is then pruned; git retains it.
Deferred-but-unimplemented specs are kept (optionally banner-marked) until actioned.

## Nomenclature

- Frontmatter on every managed doc:
  ```yaml
  ---
  kind: charter | roadmap | index | conventions | reference | spec | plan | design
  status: living | hardened | superseded | scaffolding | ideation
  updated: YYYY-MM-DD
  ---
  ```
  Retirement tombstones add `superseded_by: <relative-path>`; successors may add `supersedes:`.
- `index.md` sections carry a `_updated: YYYY-MM-DD_` stamp directly under each heading.
- `roadmap.md` uses stable headings `## Now`, `## Next`, `## Milestones`.
- Dates ISO 8601 (`YYYY-MM-DD`). Links relative + wiki-style (resolve in IDEs and GitHub).

## Writing ethos

Docs are routing + decision context, not a running log. Editorial before additive: prune, move, and
link before you append. Put each fact in its smallest stable home. Apply a brevity gate over
ornamental prose. If no durable update is justified, make no edit.

And a craft standard for what survives — **compression as craft**: dense, concrete, decision-useful
prose where every sentence earns its place by changing a reader's next action; the precise noun and
verb over hedging and ornament. A doc is done not when nothing more can be added, but when nothing
more can be removed without losing signal.
```

- [ ] **Step 2: Verify frontmatter + structure**

Run: `head -5 docs/architecture/conventions.md && grep -c '^## ' docs/architecture/conventions.md`
Expected: frontmatter block printed; `4` (four `##` sections).

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/conventions.md
git commit -m 'docs(architecture): conventions — the self-describing doc system

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 2: roadmap.md — milestones (Now/Next deferred)

**Files:**
- Create: `docs/architecture/roadmap.md`

- [ ] **Step 1: Create the file with this exact content**

```markdown
---
kind: roadmap
status: living
updated: 2026-06-19
---

# Roadmap

Long-horizon milestones, defined ahead and updated when reached or refined. Recent activity is in git
(`git log`), not here. For what exists today, see [index.md](index.md).

## Now

_To be set next session — the active milestone (M0 model loop vs. document-class breadth) is an open
decision deferred from the doc-system redesign._

## Next

_See `## Milestones` below until `## Now` is set._

## Milestones

- [x] **Synthetic data toolkit** — compositional spec API + `build`/`list`/`inspect` CLI; structural
  realism complete (atomic words, headers, multi-table/globals, spacing/jitter, sparse cells, spanning
  cells + grouped headers). The `eob` class exercises the full shape.
- [ ] **The loop closes (M0, spatial)** — train a from-scratch model on a dataset → emit run artifacts
  → predictions overlaid in the viewer. The v0 design predates schema v4 and needs a refresh (derive
  labels from cells, not per-word labels) before starting.
- [ ] **Document-class breadth** — invoice/receipt variants, purchase order, bank statement, key-value
  form.
- [ ] **Modality ladder** — M1 (+text), M2 (+visual), M3 (fusion); modality-ablation experiments.
- [ ] **Full difficulty dial** — visual realism, real Textract data, autonomous overnight loop.
```

- [ ] **Step 2: Verify anchor headings exist (the hook depends on `## Now`)**

Run: `grep -E '^## (Now|Next|Milestones)$' docs/architecture/roadmap.md`
Expected: all three headings printed.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/roadmap.md
git commit -m 'docs(architecture): roadmap — milestones (now/next deferred)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 3: index.md — README-for-agents, seeded from the code

**Files:**
- Create: `docs/architecture/index.md`

- [ ] **Step 1: Create the file with this exact content**

```markdown
---
kind: index
status: living
updated: 2026-06-19
---

# Project index

README-for-agents: a functional map of what exists and where the deep docs live. Start here; pull
deeper on demand. Why → [charter.md](charter.md). Where we're headed → [roadmap.md](roadmap.md). How
docs work → [conventions.md](conventions.md).

## Contract — schema v4 (Region / Cell / Word)
_updated: 2026-06-19_

The artifact seam between data and runs. Words are atomic, pure observables (`bbox` + `text`, one per
whitespace word, no per-word label). Structure and meaning live on `Cell`s (`row_index`/`column_index`/
`span`/`role`/`field`, grouping words via `word_ids`), grouped under typed `Region`s (`table`/`form`,
`type`/`name`/`index`). Globals → a `form` region; background → cell-less words. Source of truth:
[artifacts.py](../../harness/src/tablelab/artifacts.py).

## Synthetic dataset builder
_updated: 2026-06-19_

A compositional spec API — `FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`JitterSpec`/
`DocumentClass` (modules `specs`/`fields`/`classes`/`layout`/`render`/`build`) — joined by a
Pillow-free placed-cell IR, with a `build`/`list`/`inspect` CLI writing to `datasets/<id>/`. The `eob`
class exercises the full structural-realism surface. Code:
[harness/src/tablelab/](../../harness/src/tablelab/).

## Viewer
_updated: 2026-06-19_

Vite/React split-pane review app (no backend; dev middleware serves `/runs` + `/datasets`): page image
+ interactive structure-overlay lenses on the left, metadata + selected-element detail on the right.
Code: [viewer/src/](../../viewer/src/).

## Model loop
_updated: 2026-06-19_

Not started. The v0 design ([specs/2026-06-13-v0-loop-closes-design.md](../specs/2026-06-13-v0-loop-closes-design.md))
predates schema v4 and needs a refresh — derive `(record, field)` targets from cells rather than
per-word labels — before M0.
```

- [ ] **Step 2: Verify section stamps**

Run: `grep -c '^_updated: 2026-06-19_$' docs/architecture/index.md`
Expected: `4`.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/index.md
git commit -m 'docs(architecture): index — functional map seeded from the code

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 4: Move the charter into `architecture/` + fix inbound links

**Files:**
- Move: `docs/CHARTER.md` → `docs/architecture/charter.md`
- Modify: `docs/architecture/charter.md` (add frontmatter; fix roadmap pointer)

- [ ] **Step 1: Move the file with git**

Run: `git mv docs/CHARTER.md docs/architecture/charter.md`

- [ ] **Step 2: Add frontmatter to the top of `docs/architecture/charter.md`**

Insert these 5 lines as the very first lines of the file (above the existing `# Charter` heading):

```markdown
---
kind: charter
status: living
updated: 2026-06-19
---
```

- [ ] **Step 3: Fix the roadmap pointer inside the charter**

In `docs/architecture/charter.md`, find:

```markdown
> Operating mechanics live in `AGENTS.md`; the roadmap lives in
> `docs/specs/2026-06-13-design-and-roadmap.md`.
```

Replace with:

```markdown
> Operating mechanics live in `AGENTS.md`; the roadmap lives in [roadmap.md](roadmap.md).
```

- [ ] **Step 4: Find every other reference to the old charter path**

Run: `grep -rn 'CHARTER.md\|docs/CHARTER' --include='*.md' . ; grep -rn 'CHARTER' AGENTS.md README.md`
Expected: matches in `AGENTS.md` and `README.md` (handled in Tasks 6 & 8) and possibly the spec/plan (leave those — scaffolding). Note them; do not edit AGENTS.md/README.md here.

- [ ] **Step 5: Verify the move**

Run: `test -f docs/architecture/charter.md && test ! -f docs/CHARTER.md && head -5 docs/architecture/charter.md`
Expected: frontmatter printed, no error.

- [ ] **Step 6: Commit**

```bash
git add -A docs/CHARTER.md docs/architecture/charter.md
git commit -m 'docs(architecture): move charter into architecture/; add frontmatter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

## Phase 2 — Migrate the stale roadmap + slim the duplicators

### Task 5: Retire the dated roadmap doc; banner the v0-loop spec

**Files:**
- Delete: `docs/specs/2026-06-13-design-and-roadmap.md`
- Modify: `docs/specs/2026-06-13-v0-loop-closes-design.md`

- [ ] **Step 1: Confirm durable content is already captured**

The durable bits of `design-and-roadmap.md` now live in: milestones → `roadmap.md` (Task 2); current
state → `index.md` (Task 3); why/end-state → `charter.md` (Task 4); conventions → `conventions.md`
(Task 1) + `AGENTS.md` (Task 6). Skim `docs/specs/2026-06-13-design-and-roadmap.md` once and confirm
nothing durable is unaccounted for. If something is, add it to the relevant architecture doc first.

- [ ] **Step 2: Delete the dated roadmap doc**

Run: `git rm docs/specs/2026-06-13-design-and-roadmap.md`

- [ ] **Step 3: Add a "predates schema v4" banner to the v0-loop spec**

In `docs/specs/2026-06-13-v0-loop-closes-design.md`, insert this block immediately **after** the line
`# v0 — "the loop closes"`:

```markdown

> ⚠️ **Predates schema v4.** This spec assumes per-token `label = {record, field}`; the contract has
> since moved to atomic, label-free words with structure on `Cell`s. Refresh it (derive labels from
> cells) when the M0 model loop is scheduled. Current state: [../architecture/index.md](../architecture/index.md).
```

- [ ] **Step 4: Verify**

Run: `test ! -f docs/specs/2026-06-13-design-and-roadmap.md && grep -q 'Predates schema v4' docs/specs/2026-06-13-v0-loop-closes-design.md && echo OK`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add -A docs/specs/
git commit -m 'docs(specs): retire dated roadmap (migrated to architecture/); banner v0-loop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 6: Slim `AGENTS.md` to how-we-work + bearings protocol

**Files:**
- Modify: `AGENTS.md` (full rewrite)

- [ ] **Step 1: Replace the entire contents of `AGENTS.md` with this**

```markdown
# AGENTS.md — operating guide for autoresearch (fork)

How to work in this repo, for agents and humans. (Claude Code loads this via `@AGENTS.md` in
`CLAUDE.md`; Codex loads it natively.) Keep it lean and current. What this project *is* and *why*:
[docs/architecture/charter.md](docs/architecture/charter.md). Where it's headed:
[docs/architecture/roadmap.md](docs/architecture/roadmap.md).

## Bearings (start here each session)

Before starting a task, get oriented: read [docs/architecture/index.md](docs/architecture/index.md)
(the map of what exists) and [docs/architecture/roadmap.md](docs/architecture/roadmap.md) (current
focus), and skim `git log --oneline -15` for recent activity. Pull deeper docs on demand from the
index.

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
- **Branches.** `master` = infra + current-best (deliberate promotions only). `exp/<line>` = one line
  of inquiry; **every run is a commit** (model mutation + run artifacts + an `index.json` row). Run ids
  are globally unique: `{date}-{device}-{shorthash}`.
- **Contract is the seam** (`schema_version = 4`, in `artifacts.py`) — see the Contract entry in
  [docs/architecture/index.md](docs/architecture/index.md).
- **No TDD** — implement and verify by running. **PR-style review** — propose changes as diffs + a
  one-line rationale; the human accepts/redirects. **Lean** — small diffs, reviewable changes, tight docs.

## Collaborator

Zeb: ~15y SAS, 7y applied ML, finishing a UMN CS grad program; going deeper into DL theory/PyTorch.
Real problem = generalizable table/record extraction from OCR/Textract output (bbox + text). Works
across an M4 MacBook (MPS) and a Windows 3080 Ti (CUDA). Prefers building from scratch together; values
clean structure and lean docs.
```

- [ ] **Step 2: Verify the stale narration is gone and pointers resolve**

Run: `grep -c 'active milestone\|Current state\|Structural realism is complete' AGENTS.md`
Expected: `0`.
Run: `grep -q 'architecture/conventions.md' AGENTS.md && grep -q 'Bearings' AGENTS.md && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m 'docs(agents): slim to how-we-work + bearings protocol; point at architecture/

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 7: Update the `CLAUDE.md` pointer

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the stale roadmap bullet**

In `CLAUDE.md`, find:

```markdown
- Authoritative design + roadmap: `docs/specs/2026-06-13-design-and-roadmap.md`. The **active
  milestone is the synthetic data toolkit**; the ML model loop is deferred.
```

Replace with:

```markdown
- Durable direction lives in `docs/architecture/`: the charter (why), roadmap (milestones + now/next),
  index (what exists today), conventions (how docs work). Get bearings there plus `git log`.
```

- [ ] **Step 2: Verify**

Run: `grep -q 'docs/architecture/' CLAUDE.md && ! grep -q '2026-06-13-design-and-roadmap' CLAUDE.md && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m 'docs(claude): point at docs/architecture/ instead of the retired roadmap spec

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 8: Slim `README.md` (drop duplicated current-state)

**Files:**
- Modify: `README.md`

The README has **two** stale current-state pockets (`## What we're building` and `## Status`) plus a
stale `docs/` layout bullet. Fix all three.

- [ ] **Step 1: Replace the "What we're building" section**

In `README.md`, replace everything from the `## What we're building` heading up to (but **not**
including) the `## How to work in this repo` heading with:

```markdown
## What we're building

Durable design lives in [docs/architecture/](docs/architecture/): the
[charter](docs/architecture/charter.md) (why), [roadmap](docs/architecture/roadmap.md) (milestones),
[index](docs/architecture/index.md) (a map of what exists today), and
[conventions](docs/architecture/conventions.md) (how the docs work). Start at the **index** for the
harness — the schema-v4 contract, the synthetic dataset builder, and the viewer.

```

- [ ] **Step 2: Fix the Layout `docs/` bullet**

Find:

```markdown
- `docs/` — specs, plans, exploratory design specs, and the charter
```

Replace with:

```markdown
- `docs/` — `architecture/` (charter, roadmap, index, conventions), `design/` (ideation), `specs/` + `plans/` (scaffolding)
```

- [ ] **Step 3: Remove the stale `## Status` section**

`index.md` + `roadmap.md` are now the status. In `README.md`, delete everything from the `## Status`
heading up to (but **not** including) the `## License` heading.

- [ ] **Step 4: Verify pointers in, stale state out**

Run: `grep -q 'docs/architecture/index.md' README.md && ! grep -qiE 'active milestone|active: the synthetic|structural realism ✓' README.md && ! grep -q '2026-06-13-design-and-roadmap' README.md && echo OK`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m 'docs(readme): replace current-state narration with pointers to architecture/

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

## Phase 3 — The session ritual (hook + skills)

### Task 9: Thin SessionStart hook (live `git log` push)

**Files:**
- Create: `.claude/hooks/session-bearings.sh`
- Create: `.claude/settings.json`

- [ ] **Step 1: Create the hook script**

Create `.claude/hooks/session-bearings.sh` with this exact content:

```bash
#!/usr/bin/env bash
# Thin bearings push (Claude Code only): live git recency + the roadmap's current focus.
# Portable grounding (read index/roadmap) lives in AGENTS.md — this hook is not load-bearing.
set -euo pipefail
root="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
cd "$root"

echo "## Bearings — recent activity (from git)"
echo
git log --oneline -15 2>/dev/null || echo "(no git history)"

roadmap="docs/architecture/roadmap.md"
if [ -f "$roadmap" ]; then
  echo
  echo "## Roadmap — Now"
  awk '/^## Now/{f=1; next} /^## /{f=0} f' "$roadmap"
fi
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x .claude/hooks/session-bearings.sh`

- [ ] **Step 3: Create `.claude/settings.json`**

Note: `.claude/settings.local.json` (permissions) already exists and is separate. Create the shared,
committed `.claude/settings.json` with this exact content:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/session-bearings.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Verify the script runs and produces bearings**

Run: `bash .claude/hooks/session-bearings.sh`
Expected: a `## Bearings — recent activity (from git)` block listing the last ≤15 commits, then a
`## Roadmap — Now` block echoing the deferred-Now note from `roadmap.md`.

- [ ] **Step 5: Verify settings.json is valid JSON**

Run: `python3 -c "import json; json.load(open('.claude/settings.json')); print('valid')"`
Expected: `valid`.

- [ ] **Step 6: Commit**

```bash
git add .claude/hooks/session-bearings.sh .claude/settings.json
git commit -m 'feat(hook): thin SessionStart bearings push (git log + roadmap Now)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 10: `/wrap` skill

**Files:**
- Create: `.claude/skills/wrap/SKILL.md`

- [ ] **Step 1: Create the skill with this exact content**

```markdown
---
name: wrap
description: End-of-session ritual — distill the session's landed work from the code into docs/architecture (index, plus roadmap on milestones), prune implemented specs/plans, and stage the diff for review. Use when wrapping up a work session.
---

# /wrap — incremental documentation distillation

Distill this session's landed work into the durable doc layer, then prune the scaffolding. Scope is
the **session delta**. Follow the ethos in
[docs/architecture/conventions.md](../../../docs/architecture/conventions.md): editorial before
additive, compression as craft, no edit without durable signal. **Stage** changes; never commit.

## Steps

1. **Scope.** Find what landed since the last wrap — `git log --oneline` and `git diff` against the
   last doc-sync commit (or the branch base). Identify completed features and any abandoned direction.
2. **Distill from the code (not the spec).** For each landed feature, update its section in
   [index.md](../../../docs/architecture/index.md): refresh the `_updated:` stamp and write a
   compressed, durable paragraph describing what *is*, with source links. If a result earns its own
   documentation (a schema, a complex subsystem, a diagram), add or update a doc/folder under
   `docs/architecture/` and link it from the index. Most features stop at the index paragraph; if no
   durable update is justified, make none.
3. **Roadmap — milestone-gated.** Touch [roadmap.md](../../../docs/architecture/roadmap.md) only when a
   milestone was actually reached or the plan shifted: update `## Now`/`## Next`, check off
   `## Milestones`. No per-session log entry — git is the activity record.
4. **Prune.** Delete implemented `docs/specs/` + `docs/plans/` files and any graduated `docs/design/`
   ideation — only after their durable essence is captured above.
5. **Sync sparingly.** Update `charter.md` / `AGENTS.md` / `README.md` only if a durable fact changed.
6. **Stage + review.** Enforce relative wiki-style links and verify they resolve; `git add` the doc
   changes and present the diff. Do not commit — the human reviews and commits.

## Output

Report files touched with one-line rationales, what was pruned, whether the roadmap moved (and why),
and — when nothing durable changed — say so and make no edit.
```

- [ ] **Step 2: Verify frontmatter + relative link depth**

Run: `head -3 .claude/skills/wrap/SKILL.md && test -f .claude/skills/wrap/../../../docs/architecture/conventions.md && echo 'link OK'`
Expected: frontmatter printed; `link OK` (confirms `../../../` resolves to repo root).

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/wrap/SKILL.md
git commit -m 'feat(skill): /wrap — incremental per-session doc distillation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

### Task 11: `/refine-docs` skill

**Files:**
- Create: `.claude/skills/refine-docs/SKILL.md`

- [ ] **Step 1: Create the skill with this exact content**

```markdown
---
name: refine-docs
description: Holistic documentation reconciliation — re-derive the whole doc tree from the current code and realign it to docs/architecture/conventions.md. Use periodically when docs have drifted, after many sessions or milestones.
---

# /refine-docs — holistic documentation reconciliation

Same ethos and target as `/wrap`, but scope is the **whole tree**, re-derived from the ground up. Use
periodically to realign every doc to
[conventions.md](../../../docs/architecture/conventions.md). **Stage** changes; never commit.

## Workflow

1. Inspect by progressive disclosure: start at `AGENTS.md`, follow to
   [index.md](../../../docs/architecture/index.md); scan headings before bodies; read only docs and
   code the reconciliation touches.
2. Find stale, duplicated, misplaced, task-local, or ornamental text. Preserve durable guidance;
   remove ordinary status, history, and task-local state (git holds it).
3. Move each fact to its smallest stable home; collapse duplication to one home plus links.
4. Normalize product / module / workflow / heading / concept names unless a local term is intentional.
5. Rewrite what survives as compressed, durable prose (the conventions' craft standard): signal per
   sentence, no fluff.
6. Apply the brevity gate; verify every surviving line helps a future agent choose a better next
   action. If no durable update is justified, make no edit.
7. Enforce relative wiki-style links and verify they resolve. Stage changes; do not commit.

## Output

Report docs reviewed, files changed with one-line rationales, validation performed, and why nothing
changed where nothing did.
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -3 .claude/skills/refine-docs/SKILL.md`
Expected: the `name: refine-docs` frontmatter block.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/refine-docs/SKILL.md
git commit -m 'feat(skill): /refine-docs — holistic doc reconciliation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

---

## Phase 4 — End-to-end verification

### Task 12: Verify the system holds together

**Files:**
- None (verification only; final commit if any link fixes are needed)

- [ ] **Step 1: Link-check every relative link under `docs/architecture/`**

Run:
```bash
python3 - <<'PY'
import re, pathlib
bad = []
for md in pathlib.Path("docs/architecture").rglob("*.md"):
    text = md.read_text()
    for m in re.finditer(r"\]\(([^)]+)\)", text):
        link = m.group(1).split("#")[0].strip()
        if not link or link.startswith(("http://", "https://", "mailto:")):
            continue
        if not (md.parent / link).resolve().exists():
            bad.append(f"{md}: {link}")
print("BROKEN:", *bad, sep="\n  ") if bad else print("all links resolve")
PY
```
Expected: `all links resolve`. If any are broken, fix the link in the offending file and re-run.

- [ ] **Step 2: Confirm "one home per fact" — no duplicated current-state phrasing**

Run: `grep -rniE 'active milestone is the synthetic|active: the synthetic data toolkit|structural realism (is complete|✓)' --include='*.md' . | grep -vE 'docs/(specs|plans)/'`
Expected: no output (any survivors are in pruned-later scaffolding under specs/plans).

- [ ] **Step 3: Confirm the retired roadmap doc is gone and its replacements exist**

Run: `test ! -f docs/specs/2026-06-13-design-and-roadmap.md && ls docs/architecture/`
Expected: lists `charter.md  conventions.md  index.md  roadmap.md`.

- [ ] **Step 4: Re-run the hook end-to-end**

Run: `bash .claude/hooks/session-bearings.sh | head -20`
Expected: the bearings block (recent commits) followed by the `## Roadmap — Now` block.

- [ ] **Step 5: Confirm both skills are discoverable**

Skills load at session start. In a **fresh** Claude Code session in this repo, confirm `/wrap` and
`/refine-docs` appear in the available skills. (If running inline, note that they will be available
next session; the `SKILL.md` files are in place.)

- [ ] **Step 6: Final commit (only if Step 1 required link fixes)**

```bash
git add -A docs/architecture/
git commit -m 'docs(architecture): fix relative links flagged by link-check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
```

- [ ] **Step 7: Review the branch diff before promotion**

Run: `git log --oneline master..infra/doc-system && git diff --stat master..infra/doc-system`
Expected: ~12 commits; changes confined to `docs/`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `.claude/`.
Hand off to the human for PR-style review and a deliberate merge to `master`.

---

## Notes for the executor

- **Don't dogfood `/wrap` to write these docs.** The architecture docs here are authored directly by
  the plan; `/wrap` runs at the end of a *future* feature session, against landed code.
- **`## Now`/`## Next` are intentionally deferred** (Task 2) — the M0-vs-breadth milestone decision is
  the very next conversation. Leave the italic placeholder notes; they are not plan gaps.
- **The branch already exists** (`infra/doc-system`). Stay on it; the final step hands off for review.
