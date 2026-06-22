---
name: refine-context
description: Stand up and re-tune the SessionStart context slice — the bash hook that stitches targeted doc sections into each session's opening context. Use to set up, trim, or extend what loads at session start (the bearings/slice). Sibling to refine-docs.
---

Own the SessionStart context slice: the script whose stdout is injected as each session's opening context (the bearings). Its job is to materialize the *next ring of progressive disclosure* — the context [AGENTS.md](../../../AGENTS.md) only points at — so a session boots already holding it. AGENTS.md/CLAUDE.md are free (always-on) and never re-pushed. Start maximal, refine *down*: the always-on slice is paid every session, so cut to what changes the next action. The durable artifact is [source-doc-context.py](../../hooks/source-doc-context.py); its slice list (the `section(...)` / `module(...)` calls at the bottom of `main()`) is the thing you tune. Follow [docs/README.md](../../../docs/README.md). Stage; never commit.

## Workflow (the facilitator loop)

1. Discover structure: read the root [README.md](../../../README.md) `## Module Map` for the live module set. On first setup, assemble the maximal slice list (git recency; roadmap `## Now` + `## Milestones`; root `## Module Map`; each module README `## Overview`). On a re-tune, read the *current* slice list in the script instead.
2. Run the script (`python3 .claude/hooks/source-doc-context.py`) and show the operator the **actual rendered context**, with a rough per-slice line/token cost so the always-on tax is visible.
3. Tune with the operator: drop, add, or reorder `section(...)` / `module(...)` calls. Each slice targets a canonical header (`## Overview`, `## Agentic Validation`, roadmap `## Now`/`## Milestones`, root `## Module Map`, docs `## Module Map`) — the same sliceable headers the layout defines. Re-run, re-show. Loop until it lands.
4. Land it: write the final script, syntax-check it (`python3 -m py_compile`) and run once clean, and confirm the SessionStart hook is wired in [settings.json](../../settings.json).

## Boundaries

Owns only the slice script + hook wiring. Does not edit doc content (that is `/wrap` and `/refine-docs`) and never re-pushes AGENTS.md. If a sliced header is missing, the helper emits nothing — fix the doc with `/wrap`, not by working around it here.

## Output

Report the final slice list, what it renders (and rough cost), what changed and why, and confirm the hook runs clean. If nothing wanted tuning, say so and change nothing.
