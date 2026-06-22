---
name: init-docs
description: Scaffold the canonical doc harness on a blank or existing repo — negotiate the root README identity and doc location first, then generate the coherent structure (module READMEs, docs/README.md, config, scaffolding dirs) and prove it lint-clean. Use when standing up docs on a new project or adopting the harness on an existing one.
---

Stand up the doc harness conversationally — explaining each artifact as it lands and letting the operator pivot — so the result is a *coherent* harness, not just files. The endstate definition of what docs mean lives in [docs/README.md](../../../docs/README.md) (here, jack's tree is the worked example); everything else implements it. Stage; never commit.

## Foundation first (invest the conversation here)

Everything derives from two decisions — settle them before generating anything:

1. **Project identity** — the root `README.md` `## Overview` (what it is) and `## Module Map` (what exists), derived from the actual top-level code dirs.
2. **Doc location & organization** — where `docs/` lives and how it is structured, captured as `docs/README.md`. This *is* the source of truth; lock it, then generate downstream from it.

## Detect-and-adapt

- **Blank repo:** write the full canonical template with guiding placeholder prose under each canonical header; prompt for the identity one-liner, module list, charter-or-not.
- **Existing repo:** inventory what exists and **map content into canonical homes** rather than overwrite — fold an existing README intro into `## Overview`, derive `## Module Map` from real top-level dirs, fill module `## Overview`s cheaply from code where obvious, and **flag gaps** ("backend has no Setup section — fill via /wrap") instead of inventing detail. Never clobber existing prose silently.

## Canonical layout to produce

- `README.md` — `## Overview` (stamped) · `## Module Map` · `## Getting Started`; frontmatter-free.
- `AGENTS.md` (with `CLAUDE.md` symlink) — router + GLOBAL `## Agentic Guidelines` / `## Agentic Validation` only.
- `<module>/README.md` — `## Overview` (stamped) · `## Setup` · `## Structure` · `## Agentic Guidelines` · `## Agentic Validation`.
- `docs/README.md` — how docs work (taxonomy / lifecycle / nomenclature / ethos): the source of truth.
- `docs/config/` — `roadmap.md` (required) · `charter.md` (optional).
- `docs/{specs,plans,design,diagrams}/` — scaffolding + assets.
- Seed the linter + bearings from [templates/doc-lint.py](templates/doc-lint.py) and [templates/source-doc-context.py](templates/source-doc-context.py): copy each into place, fill the `init-docs:`-marked lists from the chosen structure (module set, docs/ dirs), and wire the SessionStart hook — so `/refine-linter` and `/refine-context` inherit working artifacts to refine, not blank stubs.

## Cohesion (the binding invariant)

Generate every dependent artifact *from* `docs/README.md` so a pivot propagates: module READMEs, the linter's path lists/enums, the slice list. Offer pivots (charter in/out, which dirs are modules, keep/drop `docs/design` + `docs/diagrams`, the `docs/` location) and recommend a core — but never leave a reference pointing at the old shape. Hand off to `/refine-linter` and `/refine-context` to finalize those two artifacts against the chosen structure.

## Self-check

End by running `python3 .claude/skills/refine-docs/doc-lint.py` — the scaffold is born lint-clean, which also proves the cross-reference web is coherent.

## Output

Report what was scaffolded vs. mapped from existing content, the pivots chosen, gaps flagged for `/wrap`, and the clean lint run.
