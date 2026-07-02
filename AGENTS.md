---
kind: readme
status: living
updated: 2026-07-01
---

## Agentic Guidelines

- **From scratch, together.** Favor implementing internals over wiring off-the-shelf models; explain the *why* — this is pedagogy as much as delivery.
- **Progressive disclosure.** Gather context the way the docs are layered: root [README.md](README.md) `## Module Map` → module README `## Overview` → deep doc → code. Read only what the task touches. The current focus is the [roadmap](docs/roadmap.md) `## Now`; the *why* (mission + the bet) is the root README `## Overview`.
- **When working in a module, treat its README `## Agentic Guidelines` and `## Agentic Validation` as binding** — they own that module's how-we-build and how-we-validate.
- **Lean.** Small diffs, reviewable changes, tight docs. Brainstorm/design before non-trivial features; complexity must earn its keep at this single-operator scale.
- **PR-style review.** Propose changes as diffs + a one-line rationale; the human accepts/redirects.
- **Append-only lab notebook.** `master` = infra + current-best (deliberate promotions); `exp/<line>` = one line of inquiry, every run a commit; keep failures as a `status` label, never `git reset`. Run ids `{date}-{device}-{shorthash}`.
- **Direct technical judgment.** Give genuine opinions and pushback; name clever-but-hollow patterns plainly; skip sycophancy; keep durable docs ruthlessly concise.

## Agentic Validation

**Verify by running — no TDD.** Exercise a change and show the result; don't claim done without it.
Choose the smallest command that covers the change.

Module-specific commands (`uv` / `tablelab.cli` for the harness, `npm` for the viewer) live in each
module's README `## Agentic Validation` ([harness](harness/README.md), [viewer](viewer/README.md)).
