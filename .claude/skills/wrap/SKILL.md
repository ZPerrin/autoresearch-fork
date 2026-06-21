---
name: wrap
description: Wrap up a work session — distill its landed changes from the code into the durable doc layer (module README `## Overview` sections, decisions into module `## Agentic Guidelines`, roadmap on milestones), prune implemented specs/plans, and stage the diff. Invoke as `/wrap into <branch>` to also close out the work branch: gate, commit the sync, and merge into <branch> with an explicit merge commit.
---

Distill this session's landed work into the durable docs, then prune the scaffolding it leaves behind. Scope is the session delta, not the whole tree. Follow [docs/README.md](../../../docs/README.md): editorial before additive, compression as craft, no edit without durable signal.

After distilling, **wrap always asks whether to close out the branch** — sync the docs, then offer to finish the work by merging per the close-out flow. Two invocations:

- **`/wrap`** — distill + stage the doc diff, then ask "close out this branch by merging? into which branch?". If no, stop with the diff staged and **never commit** — the operator reviews and commits. If yes, run the close-out flow into the chosen branch.
- **`/wrap into <branch>`** — the same distill, but the target is already named: skip the question and run the close-out flow straight into `<branch>`.

Close-out finishes a feature/work branch: docs synced, tree clean, merged with an explicit commit, optionally cleaned up. Committing happens only on close-out — the operator opted in (by answering yes, or by naming a target).

## Distill (both modes)

1. Scope the delta: `git log --oneline` and `git diff` against the last doc-sync commit or the branch base. Name what landed and any direction abandoned.
2. Distill from the code, not the spec. For each landed feature, refresh the touched module README's `## Overview` (its `_updated:` stamp + paragraph), and record any durable build or infrastructure decision in that module README's `## Agentic Guidelines`. If a result earns its own doc — a schema, a subsystem, a diagram — add it under `docs/` and link it from the module README. Most features stop at an Overview paragraph; if nothing durable changed, write nothing.
3. Move the roadmap only on milestone events: update `## Now`/`## Next`, check off `## Milestones` in [roadmap.md](../../../docs/config/roadmap.md). No per-session entry — git is the activity log.
4. Prune implemented `docs/specs/` and `docs/plans/` files and graduated `docs/design/` ideation, only once their essence is captured above. Leave directional reviews (kept as `kind: review` specs in `docs/specs/`) in place.
5. Sync `docs/config/charter.md`, `AGENTS.md`, or the root `README.md` `## Overview` only if a durable fact changed.
6. Run the bundled linter `python3 .claude/skills/refine-docs/doc-lint.py` and fix what it flags (links + the frontmatter/stamp two-tier); `git add` the doc changes.

Then **ask whether to close out**: "Close out this branch by merging? Into which branch?" (skip the question when invoked as `/wrap into <branch>` — the target is given). If the operator declines, stop here: report and leave the diff staged. If they choose a target, continue with close-out.

## Close out (on operator opt-in)

7. **Gate before merging** — the work does not merge until both pass:
   - **Lint clean:** `python3 .claude/skills/refine-docs/doc-lint.py` exits 0.
   - **Untracked / missing check:** `git status --porcelain`. Surface every untracked (`??`) and deleted/missing (` D`) path; stage what belongs in the sync and remove or explain what doesn't. Do not merge a tree with stray or orphaned files.
   If either fails, stop and report — never merge through a failing gate.
8. **Commit the sync** on the work branch: `git commit -m "docs(wrap): <what was distilled>"` (project trailer per the repo's commit convention).
9. **Merge with an explicit commit, as the last step:** `git checkout <branch>` then `git merge --no-ff <work-branch>` with a written merge-commit message naming the work. `--no-ff` is required — always an explicit merge commit, never a fast-forward. Re-run the linter on the merged result.
10. **Optionally clean up** — on operator confirmation, delete the merged branch (`git branch -d <work-branch>`) and `git worktree prune` if applicable. Skip if they want it kept.

## Output

Report files touched with one-line rationales, what was pruned, and whether the roadmap moved and why; when nothing durable changed, say so and make no edit. In close-out mode, also report the gate result, the sync commit, the merge commit, and whether the branch was cleaned up.
