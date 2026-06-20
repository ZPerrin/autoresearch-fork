---
kind: conventions
status: living
updated: 2026-06-19
---

# Documentation conventions

How docs work in this repo: the taxonomy, the lifecycle, the nomenclature, and the writing ethos.
This is the canonical description; the tooling that maintains the docs references it rather than
redefining it.

## Taxonomy — one home per fact, split by volatility

- `docs/architecture/` — the durable core, the progressive-disclosure hub.
  - `charter.md` — the WHY (mission, the bet, non-goals, end-state). Rarely changes.
  - `roadmap.md` — long-horizon milestones + `## Now`/`## Next`. Changes on milestone events.
  - `index.md` — README-for-agents: a functional map of what exists, linking to the deep docs.
  - `conventions.md` — this file.
  - feature docs / diagrams / folders — added only when a result earns its own documentation.
- `docs/design/` — ideation, not yet actionable. Pruned once it graduates to a spec or ships.
- `docs/specs/`, `docs/plans/` — superpowers-flow scaffolding. Pruned once implemented and distilled.
- `AGENTS.md` — how we work (layout, commands, conventions, bearings protocol). Auto-loaded, portable.
- Git history — the activity log. We do not hand-maintain a running log anywhere.

## Lifecycle — the funnel

`design/<idea>.md` → `specs/` + `plans/` → implemented + verified → the durable essence is distilled
(from the code, not the spec) into an `index.md` section (plus a hardened doc if it earns one) and, on
milestone events, `roadmap.md`; the spec/plan is then pruned (git retains it).
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
