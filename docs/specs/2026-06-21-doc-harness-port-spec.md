---
kind: spec
status: scaffolding
updated: 2026-06-21
---

# Port the updated doc harness from the Jack project

Adopt the matured documentation-harness skill family from the sibling **Jack** project
(`C:/Users/Zebulon/Software Projects/jack`, `master`) onto this repo, migrating this project's
doc tree to the canonical layout the family is designed against.

## 1. Why / scope

The harness skills here (`wrap`, `refine-docs`) are an earlier generation. In Jack they have grown
into a five-skill family — `init-docs`, `refine-context`, `refine-docs`, `refine-linter`, `wrap` —
that interlock against a newer doc **topology**. Porting verbatim breaks every path reference, so a
full port requires migrating this project's topology to match. The user chose **full migration**.

A second, deliberate goal: exercise the branch → commits → explicit-merge workflow the new `wrap`
encodes, so the working pattern itself becomes consistent and visible on the git tree.

## 2. The topology gap

| Concern | This repo (before) | Jack / canonical (after) |
|---|---|---|
| Doc source-of-truth | `docs/architecture/conventions.md` | `docs/README.md` |
| The map | one `docs/architecture/index.md` | distributed module `README.md`s with canonical headers |
| roadmap / charter | `docs/architecture/` | `docs/config/` |
| Linter | `scripts/doc-lint.py` | `.claude/skills/refine-docs/doc-lint.py` (bundled) |
| Bearings hook | `session-bearings.sh` (bash) | `source-doc-context.py` (python, sliced) |
| Skills | `wrap`, `refine-docs` | + `init-docs`, `refine-context`, `refine-linter` |

Canonical module `README.md` headers: `## Overview` (stamped with `_updated:`), `## Setup`,
`## Structure`, `## Agentic Guidelines`, `## Agentic Validation`.

## 3. Strategy — port the machinery, then run it on ourselves

The ported skills are themselves the migration tools, so execution is two stages:

1. **Port the machinery** — copy the 5 skill directories + their templates into `.claude/skills/`
   verbatim from Jack. No doc changes yet; pure tooling. This is a self-contained, reviewable commit.
2. **Dogfood `/init-docs`** (existing-repo detect-and-adapt path) to migrate the doc tree:
   - author `docs/README.md`, folding the durable ethos from today's `conventions.md`;
   - distribute `docs/architecture/index.md` content into per-module `README.md`s;
   - relocate `roadmap.md` + `charter.md` → `docs/config/`;
   - seed the new linter + `source-doc-context.py` from `init-docs` templates, configured for this
     repo's module set; rewire `settings.json`'s `SessionStart` hook;
   - slim `AGENTS.md` to router + GLOBAL `## Agentic Guidelines` / `## Agentic Validation`.
   Then `/refine-linter` and `/refine-context` finalize the two generated artifacts.

## 4. Module set

Modules (own canonical `README.md`): **`harness/`**, **`viewer/`** — both already have a README.
`runs/` is a git-tracked ledger documented as a dir, not a code module. `datasets/` (gitignored,
local) and `reference/` (parked upstream LM files) are not modules. `init-docs` confirms the final
call conversationally.

## 5. Process / workflow convention (the dogfood)

- **Branch:** `harness/doc-harness-port`, cut from `master`; all work lands here.
- **Commits:** conventional-commit style already used in this repo (`feat(...)`, `docs(...)`,
  `chore(...)`), each a reviewable step.
- **Merge convention — enforced behaviorally via the ported `wrap`:** close out with
  `git merge --no-ff harness/doc-harness-port` into `master`; subject
  `Merge harness/doc-harness-port: <summary>`; descriptive body; `Co-Authored-By` trailer.
  `--no-ff` guarantees an explicit merge commit so the pattern is always visible on the tree.
- **Gate:** no merge without explicit user confirmation; close-out only after lint is clean and the
  tree has no stray/untracked files.

## 6. Out of scope

- Mechanical (git-hook) enforcement of the merge convention — behavioral enforcement via `wrap` is
  the chosen lean path; a `commit-msg` hook is a possible later addition.
- Porting any non-doc-harness Jack content (seed tooling, app code).

## 7. Done when

The 5 skills are present and their internal links resolve; the doc tree is in canonical layout;
the new linter runs clean; the `source-doc-context.py` bearings hook runs clean and is wired in
`settings.json`; and the branch is merged into `master` with the explicit-merge convention.
