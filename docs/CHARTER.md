# Charter — what this project is solving for

> **Canonical and stable.** Unlike `docs/specs/` and `docs/plans/` (dated, transient records of
> individual features), this document states the durable *why*. Change it rarely and deliberately.
> Operating mechanics live in `AGENTS.md`; the roadmap lives in
> `docs/specs/2026-06-13-design-and-roadmap.md`.

## The goal

This is a **research harness for exploring multimodal document information extraction**, built from
scratch to learn DL by building it. The synthetic-data toolkit at its center exists to **explore the
document-extraction problem space broadly and cover our bases across modeling approaches** — not to
ship a solution to one task. The driver is graduate ML/DL study; we expect the modeling approach to
stay open for a long time, so the foundation must not quietly commit to one.

**Current focus: repeated-tabular extraction** — that is the unsolved-at-work problem giving the
research its grounding. But it is a focus, not a boundary: global/singleton field extraction (member,
provider, …) and other extraction targets are explicitly **in scope**, not precluded. The
representation is deliberately general (globals are first-class — a `form` region, not an
afterthought) so we can turn to them without re-laying the foundation.

## The real problem (motivation, not the target)

The grounding problem is **repeated-record extraction from documents**: rows that represent a record
(e.g. a claim line — service date / description / cost / …), often rolled up into a table and
associated with document-level globals (member, provider). The pattern varies by document class.

In production this is currently approached as **natural-language query** ("what is the first date of
the first row of the first table?") over **Textract** preprocessing output (token `bbox` + `text`).
It is hard to generalize and scale because the real data is **sparse**: few examples near a table's
max row count, sparsely-populated fields, and limited labels. We *have* real labeled data for this,
plus the Textract output from preprocessing.

We are **not trying to conform to that specific work problem.** It is context that keeps the research
grounded in something real — nothing more.

## The bet: structured truth in, task framings out

Synthetic data is the inverse of the sparse-real-data trap. The generator **knows everything,
densely, for free** — every cell's position, its field meaning, the record rollup, the
global↔table association — because the document class *defines* them. So:

1. **Generate one complete, structured ground truth per document** (regions → cells → words, every
   cell carrying its structural indices and its semantic `field`).
2. **Treat every task framing as a projection of it** — token classification, extractive/NLQ Q&A,
   structure prediction, record extraction are all `derive_*` views over the same source, never baked
   into the data. This is how we cover our bases without choosing a head.
3. **Make sparsity a knob, not a constraint** — `fill`, `rows`, `instances` dial the very scarcity
   that hurts the real data, turning it into a controllable ablation axis.

## Why it stays Textract-shaped

The structural schema mirrors Textract (`Region`/`Cell`/`Token` ≈ `LAYOUT`/`CELL`/`WORD`) on purpose:
the **real labeled + Textract data flows into the same representation** as synthetic. That enables
the research setup we actually want — pretrain/train on dense synthetic, evaluate and transfer on
real — with one schema and one set of projections serving both.

## Non-goals / guardrails

- **Don't overfit to one task framing** (NLQ, token classification, …). Keep the source
  representation task-agnostic; let projections specialize.
- **Don't classify value types** (date/dollar/id). The useful semantic label is the template's
  **field slot** (`copay`, `total`), not the data type.
- **Don't bake derivable facts into observables.** Observables stay `bbox` + `text` (+ image);
  structural and semantic truth live in the annotation layer (cells/regions).
- **Visual realism stays deferred** behind the renderer seam; spatial + semantic come first, vision
  much later.

## End-state

Repeated-record extraction against a **class-defined schema**: global/singleton fields + table
definitions (repeated records) + multiple table instances per document — with the modeling approach
deliberately left open so the research can go where it goes.
