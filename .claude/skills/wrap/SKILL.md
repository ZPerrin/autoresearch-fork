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
