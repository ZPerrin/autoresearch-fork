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
7. Enforce links — run `python3 scripts/doc-lint.py` and fix what it flags (broken or code-styled
   links + nav-list paths that should be links). Stage changes; do not commit.

## Output

Report docs reviewed, files changed with one-line rationales, validation performed, and why nothing
changed where nothing did.
