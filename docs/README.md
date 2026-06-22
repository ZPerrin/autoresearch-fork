---
kind: readme
status: living
updated: 2026-06-21
---

## Overview

The canonical description of this repo's documentation system: the taxonomy, the lifecycle, the
nomenclature, and the writing ethos — the negotiated source of truth every harness artifact derives
from. The skills that maintain it reference this file rather than redefining it: `/wrap` (session
delta, and closes out work branches: gate + explicit merge) and `/refine-docs` (whole-tree) keep doc
*content* honest; `/init-docs` scaffolds the structure;
`/refine-context` tunes the session-context slice ([source-doc-context.py](../.claude/hooks/source-doc-context.py));
`/refine-linter` reconciles the linter ([doc-lint.py](../.claude/skills/refine-docs/doc-lint.py),
bundled in `/refine-docs`) back to this file.

## Module Map

- [config/](config/) - durable control docs: [charter](config/charter.md) (the why) + [roadmap](config/roadmap.md) (where headed).
- [specs/](specs/) - design specs + directional reviews (`kind: review`, kept); implementation specs are scaffolding, pruned once distilled.
- [plans/](plans/) - implementation plans (scaffolding, pruned once distilled).
- [design/](design/) - ideation, not yet actionable (holds [visual-realism/](design/visual-realism/)).

## Taxonomy — one home per fact, split by volatility

- **The functional map ("what exists") is distributed**, not central: the root [README.md](../README.md)
  `## Module Map` lists the modules; each module `README.md` opens with a stamped `## Overview` that is
  that module's slice. There is no `index.md`.
- **Durable build decisions live with their module**: each module README's `## Agentic Guidelines`
  merges the hardened how/why-we-build with how-to-work-here. There is no central `decisions.md`.
- `docs/config/` — the small set of durable control docs:
  - [config/charter.md](config/charter.md) — the WHY (mission, the bet, non-goals, end-state). Rarely changes.
  - [config/roadmap.md](config/roadmap.md) — long-horizon milestones + `## Now` / `## Next`. Changes on milestone events.
- `docs/specs/`, `docs/plans/` — superpowers-flow scaffolding (design specs + implementation plans).
  Pruned once implemented and distilled. **Directional reviews** live here too as a spec *kind*
  (`kind: review`): point-in-time strategic reads that sit above specs, model-stamped, never
  rewritten, and **kept** (not pruned).
- `docs/design/` — ideation, not yet actionable. Pruned once it graduates to a spec or ships.
- `AGENTS.md` — the **router**: how we work (global agentic guidelines + validation) plus pointers into
  the durable layer; no mission, install, or module map. Auto-loaded, portable. `CLAUDE.md` is a symlink to it.
- Module `README.md` (harness / viewer / docs) — the front door for that scope: a stamped `## Overview`,
  setup / structure, and `## Agentic Guidelines` / `## Agentic Validation`.
- Git history — the activity log. We do not hand-maintain a running log anywhere.

## Canonical headers (sliceable)

Stable header names let a context-slice hook target sections without parsing prose:

- Module READMEs: `## Overview` (stamped), `## Setup`, `## Structure`, `## Agentic Guidelines`, `## Agentic Validation`.
- Root `README.md`: `## Overview`, `## Module Map`, `## Getting Started`.
- This file (`docs/README.md`): `## Overview` and `## Module Map` (the documentation index) — both
  sliced into the session context by [source-doc-context.py](../.claude/hooks/source-doc-context.py).

## Lifecycle

`docs/design/<topic>-design.md` (ideation) and directional reviews → `docs/specs/…-spec.md` +
`docs/plans/…-plan.md` → implemented + verified → the durable essence is distilled (from the code, not
the spec) into the relevant module README's `## Overview` (and `## Agentic Guidelines` when a durable
decision was made), plus a hardened doc or diagram if it earns one — and, on milestone events,
[config/roadmap.md](config/roadmap.md). The spec / plan is then pruned (git retains it). Directional
reviews are point-in-time and kept, not pruned. Deferred-but-unimplemented specs are kept (optionally
banner-marked) until actioned.

## Nomenclature

- **Two-tier stamping** (enforced by [doc-lint.py](../.claude/skills/refine-docs/doc-lint.py)):
  - **Frontmatter** on the `docs/` tree (config + specs / plans / design, and this file) plus `AGENTS.md`:
    ```yaml
    ---
    kind: charter | roadmap | readme | guide | reference | spec | plan | design | review
    status: living | hardened | superseded | scaffolding | ideation
    updated: YYYY-MM-DD
    ---
    ```
    Retirement tombstones add `superseded_by: <relative-path>`; successors may add `supersedes:`.
  - **No frontmatter** on the root + module READMEs (keeps the GitHub landing clean); each instead
    carries a `## Overview` with an `_updated: YYYY-MM-DD_` stamp directly under the heading.
- [config/roadmap.md](config/roadmap.md) uses stable headings `## Now`, `## Next`, `## Milestones`.
- Directional reviews: `docs/specs/YYYY-MM-DD-<subject>-directional-review.md` with `kind: review`, model-stamped.
- **Scaffolding filenames** name the stage and mirror the directory: `docs/specs/YYYY-MM-DD-<topic>-spec.md`,
  `docs/plans/YYYY-MM-DD-<topic>-plan.md` — date-prefixed, the suffix matching the `kind:` frontmatter.
- Dates ISO 8601 (`YYYY-MM-DD`). Links relative + wiki-style (resolve in IDEs and GitHub).
- **Links vs. code-spans.** A reference to a real repo path renders as a **plain relative link** (the
  path is the link text, no surrounding backticks); wrapping link text in a code-span makes it render
  as code, not a link. Reserve backtick code-spans for concepts / classes (`FieldSpec`) and for
  gitignored paths absent on GitHub (`datasets/`). In navigation / structure lists, a resolving path is a link.

## Writing ethos

Docs are routing + decision context, not a running log. Editorial before additive: prune, move, and
link before you append. Put each fact in its smallest stable home. Apply a brevity gate over ornamental
prose. If no durable update is justified, make no edit.

And a craft standard for what survives — **compression as craft**: dense, concrete, decision-useful
prose where every sentence earns its place by changing a reader's next action; the precise noun and
verb over hedging and ornament. A doc is done not when nothing more can be added, but when nothing more
can be removed without losing signal.
