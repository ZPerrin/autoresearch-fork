---
kind: spec
status: scaffolding
updated: 2026-06-19
---

# Doc system + session ritual — design

A clean-slate redesign of the project's **documentation harness**: a lean, progressive-disclosure
doc system plus self-maintaining doc skills, so durable direction has exactly one home and stops
going stale. The trigger was discovering duplicated, contradictory "current state" narration spread
across `CHARTER.md`, `AGENTS.md`, `README.md`, and a dated roadmap doc claiming to be "authoritative."

**Scope boundary.** This is the *project harness* — how we organize and navigate the work. It is
distinct from karpathy's *autoresearch* append-only lab-notebook ethos ("every run a commit,
failures are lessons, never `git reset`"), which governs the **experiment/run loop** and stays
deferred until we build that loop. Pruning a spec here is ordinary tree hygiene, not a violation of
that ethos.

**Prior art.** The editorial ethos is adapted from the `refine-docs` skill in the `jack` project
(`docs as routing + decision context, not a running log`); this design extends it with a concrete
`architecture/` structure, a funnel lifecycle, and a self-describing `conventions.md`.

## 1. Goal

- One home per fact, split by volatility: mutable "where we are" never lives in more than one place.
- A fresh agent gets its bearings cheaply: `AGENTS.md` (auto-loaded, portable to Codex) carries the
  bearings *protocol* — read `index.md`/`roadmap.md`, check `git log` recency — and the agent pulls
  deeper context on demand. Progressive disclosure, not force-loading.
- **No hand-maintained running log.** Durable milestones live in the roadmap; granular activity lives
  in git; the bootstrap reads recency from `git log`. Nothing accretes fluff that dies after the next
  session.
- Repeatable doc rituals — `/wrap` (incremental, per-session) and `/refine-docs` (holistic,
  periodic) — compress landed work into rich, durable prose, prune transient scaffolding, and stage
  the result for human review.
- The system documents itself in one stable place (`conventions.md`), referenced (not redefined) by
  the skills and hook.

## 2. Document architecture

### Folder map

```
docs/
  architecture/         durable core — the progressive-disclosure hub
    charter.md          the WHY (moved from docs/CHARTER.md; rarely changes)
    roadmap.md          long-horizon milestones + Now / Next (low-churn)
    index.md            README-for-agents — the HUB; links to everything below
    conventions.md      how this doc system works + the nomenclature standard (stable)
    <feature docs>      hardened md / diagrams / feature-folders, added only when
                        warranted, grouped however is logical — index.md links to them
  design/               ideation, not yet actionable — pruned once specced/implemented
  specs/  plans/        superpowers-flow scaffolding — pruned on /wrap
```

`architecture/` is an **open-ended space**, not a fixed file set. Hardened docs are added only when a
result rises to the level of deserving its own documentation; most features are fully captured by
their `index.md` paragraph. The index is the hub that links *to* whatever exists.

### The living docs

- **charter.md** — canonical *why* (mission, the bet, non-goals, end-state). Already in good shape;
  it only relocates. Low volatility.
- **roadmap.md** — **long-horizon milestones defined ahead of time**, plus `## Now`/`## Next`
  pointers into them. Updated only when a milestone is *reached or refined* — **not every wrap**. No
  running work-log; recent activity is read from git history (§2 ladder), so the roadmap stays
  durable and low-churn.
- **index.md** — the bearings read. Functional sections by subsystem (Contract · Dataset builder ·
  Viewer · Model loop · …). Each: one paragraph of *what it does + how*, a `_updated: <date>_` stamp,
  and links to the hardened doc / source / `git show <ref>` where useful. **Lean** — a launchpad to
  deeper context, not the context itself. Decisions/dead-ends captured inline per section (a
  one-liner "why X over Y"), not as a separate ledger.
- **conventions.md** — the self-describing doc (§5). Declares the taxonomy, lifecycle, nomenclature,
  and editorial ethos. Stable.

### Progressive-disclosure ladder (what loads when)

1. **Always (cheap, every session, portable):** `CLAUDE.md` → `AGENTS.md` (Codex loads `AGENTS.md`
   natively), slimmed to *how we work* — layout, commands, conventions, doc-taxonomy summary — plus
   the **bearings protocol**: read `index.md`/`roadmap.md` and check `git log` recency before
   starting. No mission paragraph, no current-state narration.
2. **Pushed by a thin SessionStart hook (Claude Code only, not load-bearing):** the **last ~15
   commits** (`git log --oneline -15`) — the one bit of live state a static file can't hold —
   optionally with the sliced `## Now`. A *convenience* (push vs. pull): it saves a tool call and
   guarantees fresh recency in context. The portable grounding lives in `AGENTS.md` (tier 1), so a
   Codex session loses nothing without the hook.
3. **Pulled on demand:** `index.md` → and from its links, the specific hardened doc / diagram /
   feature-folder the task touches; `charter.md`; `artifacts.py`.
4. **Active scaffolding (only while a feature is in flight):** `specs/` + `plans/` + `design/`.

So `index.md` and `roadmap.md` are the two things the hook points at; the agent reads them as needed —
index to locate the subsystem and its deep docs, roadmap to know the current milestone focus.

## 3. Lifecycle (the funnel)

```
design/<idea>.md  ──graduates──►  specs/ + plans/  ──implemented + verified──►  /wrap distills into:
                                                                                  index.md section
   pruned once specced            deleted on /wrap                                (+ hardened doc if
                                                                                   warranted); roadmap
                                                                                   only on milestones
```

- Index entries are written **from the code, not the spec** — so they record what *is*, not what was
  *intended*, and are drift-corrected by construction.
- A spec/plan is pruned only **after** its durable essence is captured in `architecture/`.
- Deferred-but-not-yet-implemented specs (e.g. a north-star design) are **not** pruned; they stay,
  optionally banner-marked, until actioned.

## 4. Nomenclature standard

Defined here, declared canonically in `conventions.md`, enforced by `/wrap` and `/refine-docs`.

- **Doc-level frontmatter** on every managed doc — architecture docs and scaffolding alike (this
  spec dogfoods it):
  ```yaml
  ---
  kind: charter | roadmap | index | conventions | reference | spec | plan | design
  status: living | hardened | superseded | scaffolding | ideation
  updated: 2026-06-19                            # ISO 8601, last meaningful edit
  ---
  ```
  Architecture docs are `living` (charter/roadmap/index/conventions) or `hardened` (feature docs);
  `specs`/`plans` are `scaffolding`; `design/` is `ideation`. Retirement tombstones add
  `superseded_by: <relative-path>`; the successor may carry `supersedes:`.
- **Section stamps** in `index.md` — a greppable, human-visible token directly under each heading:
  `_updated: 2026-06-19_`. (Sections accrete independently, so each carries its own.)
- **Stable anchor headings** in `roadmap.md` — `## Now`, `## Next`, `## Milestones` (no session log)
  — so the hook can deterministically slice `## Now`.
- **Dates** ISO 8601 `YYYY-MM-DD` everywhere.
- **Links** relative, wiki-style (`[contract](contract.md)`, `[artifacts.py](../../harness/src/tablelab/artifacts.py)`)
  so they resolve in both IDEs and GitHub.

## 5. conventions.md — the self-describing doc

The single source of truth for *how the docs work*: the folder taxonomy (§2), the funnel lifecycle
(§3), and the nomenclature standard (§4), stated concisely. Rationale for a doc (not skill/hook-only):

- Keeps the system **referenceable** by humans and agents declaratively, not buried in procedure.
- **DRY** — `/wrap` and `/refine-docs` and the hook reference it instead of each re-encoding the rules.
- Keeps `AGENTS.md` lean: AGENTS carries a 2-3 line taxonomy summary + a pointer here.
- Low volatility — like the charter, it changes rarely, so it won't restale.

It also states the **editorial ethos** both skills inherit (carrying the `refine-docs` prior art's
DNA): docs are routing + decision context, **not a running log**; editorial before additive (prune /
move / link before append); every fact in its smallest stable home; a brevity gate over ornamental
prose; and **if no durable update is justified, make no edit**.

And — the nuance worth preserving — a positive craft standard for the prose that *does* survive:
**compression as craft.** Write it to last. Dense, concrete, decision-useful prose where every
sentence earns its place by changing a future reader's next action; reach for the precise noun and
verb over hedging and ornament. A doc is done not when nothing more can be added, but when nothing
more can be removed without losing signal. This marries the `refine-docs` instinct to this repo's
own lean, structured, Textract-grounded voice.

Axis separation: `index.md` = *what the project is*; `conventions.md` = *how the docs work*.

## 6. Session ritual & doc skills

### SessionStart hook (thin, Claude Code only)

The static bearings protocol lives in `AGENTS.md` (auto-loaded, portable to Codex), **not** the hook.
The hook does only the one thing auto-load can't: a committed `.claude/settings.json` script pushes
the **last ~15 commits** (`git log --oneline -15`), optionally with the sliced `## Now` from
`roadmap.md`, so live recency is in context without a tool call. It is a convenience, **not
load-bearing** — a Codex session (no hook) still grounds fully via `AGENTS.md`. Git history — not a
maintained log — supplies "what just happened."

### `/wrap` — incremental, per-session (order of operations)

The deliberate end-of-session ritual (invoked, not hooked — a Stop hook fires every turn and has no
reliable "session ending" signal). Scope = the **session delta**. Editorial before additive (§5):

1. **Scope** the diff/commits since the last wrap.
2. **Distill from the code** (drift-corrected): update the relevant `index.md` section (refresh
   `_updated:` stamp, add links/refs), writing the distillate as compressed, durable prose (§5) —
   signal per sentence, no fluff. *If* the result rises to it, add/update a hardened doc/diagram/
   feature-folder under `architecture/` and link it from the index. Most features stop at the index
   paragraph; if no durable update is justified, make none.
3. **Roadmap — milestone-gated:** touch `roadmap.md` *only* when a milestone was actually reached or
   the plan genuinely shifted (update `## Now`/`## Next`, check off `## Milestones`). No per-session
   log entry — git history is the activity record.
4. **Prune:** delete the implemented spec/plan and any graduated `design/` ideation — only after
   capture.
5. **Sync** charter / AGENTS / README *only* if a durable fact changed.
6. **Stage + review:** enforce relative wiki-style links and verify they resolve; **stage** the doc
   changes (`git add`) and present the diff. **Do not commit** — the human reviews the staged diff and
   commits (at least until the ritual has earned trust).

### `/refine-docs` — holistic, periodic

Same ethos and target state as `/wrap`, but scope = the **whole tree**, re-derived from the ground up.
Kicked off occasionally (after many wraps/milestones, or when docs have drifted) to take a full pass
and realign everything to this design. Editorial-first: inspect by progressive disclosure from
`AGENTS.md` → `index.md`; prune/relocate stale, duplicated, task-local, or ornamental text; put each
fact in its smallest stable home; normalize names; apply the brevity gate; rewrite what survives as
compressed, durable prose (§5); make no edit where no durable update is justified. Stages its changes and reports files changed with one-line rationales
(and why nothing changed, when nothing did). `/wrap` is routine maintenance; `/refine-docs` is the
periodic reconciliation/GC — and is the skill we'd use to realign the whole project to this ethos
after it has been running a while.

## 7. Clean-house (migration performed by the implementation)

- **Move** `docs/CHARTER.md` → `docs/architecture/charter.md`; update inbound pointers (CLAUDE.md,
  AGENTS.md, README.md).
- **Create** `docs/architecture/{roadmap.md, index.md, conventions.md}`; migrate the durable bits out
  of `docs/specs/2026-06-13-design-and-roadmap.md`, then **delete** that dated doc.
- **Slim `AGENTS.md`** to layout / commands / conventions / doc-taxonomy summary + the **bearings
  protocol** (read index/roadmap, check `git log` recency) + pointers — strip the mission paragraph
  and the "Current state & active milestone" narration.
- **Slim `README.md`** — replace "What we're building" current-state narration with a pointer to
  `docs/architecture/`; keep the external elevator pitch + layout.
- **Banner** `docs/specs/2026-06-13-v0-loop-closes-design.md` as "predates schema v4 — refresh when
  M0 is scheduled" (kept, not pruned — not yet implemented).
- **Add** the thin SessionStart hook (`.claude/settings.json` + a small `git log` script) and the
  `/wrap` + `/refine-docs` skills (project skills under `.claude/skills/`).
- **Seed** `index.md` from the actual code: Contract (schema v4), Dataset builder + synth toolkit,
  Viewer, and a "Model loop — not started" placeholder. **Seed `roadmap.md`'s `## Milestones`** from
  the known long-horizon arc (toolkit → model loop → modality ladder → difficulty dial + real data);
  `## Now`/`## Next` left for the *next* conversation (the M0-vs-breadth decision we deferred).

## 8. Out of scope

- The research/experiment loop and its append-only `runs/` ledger ethos (a later milestone).
- The model loop itself (M0) and the M0-vs-document-breadth milestone choice — deferred to the
  immediately-following conversation, on this fresh footing.
- Visual realism (stays deferred behind the renderer seam).
- Any Stop-hook nudge or auto-commit for `/wrap` — add later only if warranted.

## 9. Success criteria

- No mutable "current state" lives in more than one place; `grep` for the old duplicated phrasing
  finds a single home.
- **No hand-maintained running work-log exists** — recent activity is read from `git log`, and
  `roadmap.md` changes only on milestone events.
- A fresh agent, given only the SessionStart hook output, can reach the right deep doc via
  `index.md`/`roadmap.md` without reading any stale spec.
- `/wrap` reproducibly distills → prunes → updates, ending in a **staged, reviewable diff** (never an
  auto-commit); `/refine-docs` can realign the whole tree to `conventions.md` from the ground up.
- All cross-doc links are relative and resolve in-tree.
- `conventions.md` fully describes the system; both skills and the hook only *reference* it.
- Grounding is portable: a Codex session (no hook) still reaches the right docs via `AGENTS.md`'s
  bearings protocol; the hook only *adds* live `git log` recency for Claude Code.
