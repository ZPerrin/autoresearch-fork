---
kind: index
status: living
updated: 2026-06-20
---

# Project index

README-for-agents: a functional map of what exists and where the deep docs live. Start here; pull
deeper on demand. Why → [charter.md](charter.md). Where we're headed → [roadmap.md](roadmap.md). How
docs work → [conventions.md](conventions.md).

## Contract — schema v4 (Region / Cell / Word)
_updated: 2026-06-19_

The artifact seam between data and runs. Words are atomic, pure observables (`bbox` + `text`, one per
whitespace word, no per-word label). Structure and meaning live on `Cell`s (`row_index`/`column_index`/
`span`/`role`/`field`, grouping words via `word_ids`), grouped under typed `Region`s (`table`/`form`,
`type`/`name`/`index`). Globals → a `form` region; background → cell-less words. Source of truth:
[artifacts.py](../../harness/src/tablelab/artifacts.py).

## Synthetic dataset builder
_updated: 2026-06-19_

A compositional spec API — `FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`JitterSpec`/
`DocumentClass` (modules `specs`/`fields`/`classes`/`layout`/`render`/`build`) — joined by a
Pillow-free placed-cell IR, with a `build`/`list`/`inspect` CLI writing to `datasets/<id>/`. The `eob`
class exercises the full structural-realism surface. Code:
[harness/src/tablelab/](../../harness/src/tablelab/).

## Viewer
_updated: 2026-06-20_

Vite/React split-pane review app (no backend; dev middleware serves `/runs` + `/datasets`). Left: the
page image under a selectable **overlay lens** — raw / words / cells / regions / key-value / composed —
with role-colored clickable words, role-outlined cells, and an Alt-hover normalized-coordinate HUD.
Right: metadata + selected-element detail. Code: [viewer/src/](../../viewer/src/).

## Model loop
_updated: 2026-06-20_

Not started — the spine's M0 (spatial). The training target is now **materialized** per document, not
derived: a grounded `fields` / `field_groups` structure (contract v5, designed in the
[target-schema spec](../specs/2026-06-20-target-schema-spec.md)). M0 is a from-scratch, box-only model
that produces that target and beats the geosort baseline on geometrically-varied data (skew / perspective
/ aspect), proven by prediction invariance under transform. Sequencing → [roadmap.md](roadmap.md).
