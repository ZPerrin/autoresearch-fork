---
name: refine-docs
description: Holistically reconcile the whole documentation tree against the current code and realign it to docs/README.md. Use periodically when docs have drifted after many sessions, milestones, or reviews.
---

Reconcile the entire documentation tree, re-derived from the current code, into a small durable navigation layer aligned to [docs/README.md](../../../docs/README.md). Same ethos as `/wrap`, but whole-tree in scope rather than the session delta. Treat docs as routing and decision context, not a running log: keep guidance that changes the next good action; prune or relocate text that is stale, duplicated, task-local, or merely ornamental. Stage changes; never commit.

## Workflow

1. Inspect by progressive disclosure: start at `AGENTS.md`, follow the root [README.md](../../../README.md) `## Module Map` to the module READMEs; scan headings before bodies; read only the docs and code the reconciliation touches. Cover backend / frontend / cdk in turn.
2. Identify stale, duplicated, misplaced, or low-leverage text. Preserve durable guidance; remove ordinary status, history, and task-local state (git holds it).
3. Move each fact to its smallest stable home and collapse duplication to one home plus links. Module `README.md` files own their `## Overview`, setup, and commands; the root README `## Module Map` links to them rather than restating them.
4. Normalize product, module, workflow, command, heading, and concept names unless a local term is intentionally different.
5. Rewrite survivors as compressed, durable prose (the conventions' craft standard): signal per sentence, no ornament. Apply the brevity gate; verify every surviving line helps a future agent choose a better next action. If no durable update is justified, make none.
6. Run the bundled linter `python3 .claude/skills/refine-docs/doc-lint.py` (in this skill's directory) and fix what it flags (links + the frontmatter/stamp two-tier). Stage; do not commit.

## Output

Report docs reviewed, files changed with one-line rationales, validation performed, and why nothing changed where nothing did.
