---
kind: index
status: living
updated: 2026-06-20
---

# Project index

README-for-agents: a functional map of what exists and where the deep docs live. Start here; pull
deeper on demand. Why → [charter.md](charter.md). Where we're headed → [roadmap.md](roadmap.md). How
docs work → [conventions.md](conventions.md).

## Contract — schema v5 (Region / Cell / Word + Targets)
_updated: 2026-06-20_

The artifact seam between data and runs, in three additive layers. **Observables**: `Word`s are atomic
(`bbox` + `text`, one per whitespace word, no per-word label). **Structure**: the meaning-of-drawing lives
on `Cell`s (`row_index`/`column_index`/`span`/`role`/`field`, grouping words via `word_ids`) under typed
`Region`s (`table`/`form`, `type`/`name`/`index`); globals → a `form` region, background → cell-less words.
**Targets** (v5, additive — observables/structure serialization unchanged): a `Sample` carries `targets`
(and symmetric `predictions`) keyed by task, each a `Node` tree of singleton `fields` and repeating
`field_groups` (lists of record `Node`s — root and record share one type). A `Field` is one grounded value
`{value, word_ids, cell}`; an absent field is explicit-empty (`value:""`, `word_ids:[]`, the empty cell).
Targets are *authored in the placement loop* (globals → root fields, each table → a field_group of per-row
records flattened across instances), never reconstructed from geometry. Source of truth:
[artifacts.py](../../harness/src/tablelab/artifacts.py).

## Synthetic dataset builder
_updated: 2026-06-20_

A compositional spec API — `FieldSpec`/`LayoutSpec`/`StructureSpec`/`RenderSpec`/`JitterSpec`/
`DocumentClass` (modules `specs`/`fields`/`classes`/`layout`/`render`/`build`) — joined by a
Pillow-free placed-cell IR, with a `build`/`list`/`inspect` CLI writing to `datasets/<id>/`. The layout
pass (`layout_with_targets`) authors the grounded extraction target alongside words/cells/regions, which
`build` emits per sample (`manifest.task = "extraction"`). The `eob` class exercises the full
structural-realism surface. Code: [harness/src/tablelab/](../../harness/src/tablelab/).

## Viewer
_updated: 2026-06-20_

Vite/React split-pane review app (no backend; dev middleware serves `/runs` + `/datasets`). Left: the
page image under a selectable **overlay lens** — raw / words / cells / regions / key-value / composed —
with role-colored clickable words, role-outlined cells, and an Alt-hover normalized-coordinate HUD.
Right: metadata + selected-element detail. Code: [viewer/src/](../../viewer/src/).

## Model loop
_updated: 2026-06-20_

Not started — the spine's M0 (spatial). The training target is **materialized** per document, not
derived: the grounded `fields` / `field_groups` structure of contract v5 (see the Contract entry above).
M0 is a from-scratch, box-only model that produces that target and beats the geosort baseline on
geometrically-varied data (skew / perspective / aspect), proven by prediction invariance under transform.
Sequencing → [roadmap.md](roadmap.md).
