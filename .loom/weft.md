---
kind: loom-config
status: living
updated: 2026-07-01
---

# weft — repo opinion

- Distill landed work from the code (not the spec) into the owning module README's `## Overview`,
  durable decisions into its `## Agentic Guidelines`, and [docs/roadmap.md](../docs/roadmap.md) on
  milestone events.
- Specs and plans are scaffolding: prune once distilled (git retains them). Directional reviews
  (`kind: review`, `YYYY-MM-DD-<subject>-directional-review.md`, model-stamped) are point-in-time
  reads: kept, never rewritten.
- New scaffolding is date-prefixed and mirrors its directory: `docs/specs/YYYY-MM-DD-<topic>-spec.md`,
  `docs/plans/YYYY-MM-DD-<topic>-plan.md`.
- Writing: real repo paths render as plain relative links (the path is the link text); backtick
  code-spans are for concepts (`FieldSpec`) and gitignored paths (`datasets/`). Dates ISO 8601.
- **No meta-documentation.** Never write a sentence whose subject is the doc system, the plugin,
  or where other docs live — if the harness enforces it, don't restate it; if the structure shows
  it, don't narrate it. Links and slices do the routing.
