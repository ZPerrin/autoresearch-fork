---
kind: spec
status: scaffolding
updated: 2026-06-20
---

# Viewer — target tree + prediction diff — design

- Builds on **contract v5** (the materialized `targets` / `predictions` layer): see the Contract entry
  in [harness/README.md](../../harness/README.md), source [artifacts.py](../../harness/src/tablelab/artifacts.py).
- Extends the **viewer** (split-pane review app): overview in [viewer/README.md](../../viewer/README.md),
  code [viewer/src/](../../viewer/src/).
- Roadmap home: the [## Now](../config/roadmap.md) — "Targets in the viewer".

## 1. Why / scope

The harness now emits a grounded `fields` / `field_groups` target per document, but nothing renders it.
This makes the target **legible** — render the tree, ground each leaf on the page — and stands up a
**first-pass prediction diff** so a model's output can be eyeballed against truth. Predictions don't
exist yet (no model), so a **mock-predictions generator** feeds the diff with controllable cases. The
diff here is a *proof*, not the metric: it shows match / missing / spurious / mismatch, keyed on
grounding. The formal scoring (§7) is designed later with the model.

## 2. Data model (`types.ts` → v5)

Mirror the contract's target types (and drop the stale "v4" header):

```ts
export interface Field { value: string; word_ids: number[]; cell: number | null }
export interface Node  { fields: Record<string, Field>; field_groups: Record<string, Node[]> }
```

`Sample` gains `targets?: Record<string, Node>` and `predictions?: Record<string, Node>` — optional, so
pre-v5 fixtures still load. Everything keys off the `"extraction"` task.

## 3. Mock-predictions generator (harness)

A new CLI subcommand `tablelab.cli mock-run --dataset <id> --out ../runs/<run-id> [--seed N]`. It reads a
built dataset, and for each sample copies the sample (keeping `targets`) and writes a sibling **run**
whose samples carry injected `predictions` — a copy of `targets` with a few seeded perturbations:

- a **value/grounding swap** on one leaf (point it at the wrong `word_ids`),
- a **dropped record** in a `field_group`,
- a **spurious field** (a leaf present in prediction, absent in target),
- a leaf left **missing** (in target, dropped from prediction).

Writes `run.json` (a synthetic `RunRecord`, `status="mock"`, `dataset_id` set) + `samples.json`; images
resolve through the referenced dataset (runs stay binary-free). This matches the eventual real flow
(runs carry model output) and doubles as a test fixture.

## 4. Diff — first-pass, grounding-keyed, swappable

A single **pure function** is the whole matcher — isolated so the future metric work (§7) replaces *it*,
not the UI:

```ts
type LeafStatus = 'match' | 'mismatch' | 'missing' | 'spurious'
function diffNode(target: Node | undefined, pred: Node | undefined): DiffNode
```

`DiffNode` mirrors `Node` but each leaf carries a `LeafStatus` and both sides' values, and each
`field_groups` entry carries a **record-count delta** (pred vs target). First-pass rules:

- **match** — leaf in both, same `word_ids` (set-equal).
- **mismatch** — leaf in both, different `word_ids`.
- **missing** — leaf in target, not in prediction.
- **spurious** — leaf in prediction, not in target.
- **record cardinality** — surfaced per `field_group` (extra/short records align by index for now).

Value-string equality is *shown*, not the key. Colors: existing TIER palette for `match`, plus red
(missing/mismatch) and amber (spurious), added to the legend. With no predictions (plain dataset), the
diff layer is inert — only the target tree shows.

## 5. Right pane: target/diff tree (in `MetaPanel`)

A new collapsible **Targets** section renders the `Node` tree: root `fields` (globals) first, then each
`field_groups` name → an ordered list of **records**, each showing its `fields` (`name: value`),
recursing for nested groups. Each leaf row shows `field: value` and, when predictions exist, a
diff-status dot and `target → pred` on a mismatch. Group headers show the record-count delta when
nonzero. Clicking a leaf selects it (§6). Tree-building reads the `DiffNode` so the dataset case (no
diff) and run case (diff) share one renderer.

## 6. Left pane: Targets lens + cross-highlight

A new `targets` entry in the overlay-lens toolbar highlights each leaf's grounded box (the leaf's `cell`
bbox, or its member-word boxes), diff-colored when predictions exist. Selection becomes bidirectional —
extend the `Selection` union:

```ts
| { kind: 'target'; path: TargetPath }   // e.g. ['field_groups','claim_line',2,'fields','amount_owed']
```

Clicking a tree leaf highlights its box on the page; clicking a box in the lens selects the tree leaf and
scrolls it into view. Absent leaves (empty `word_ids`) appear in the tree but draw no box (or a faint
placeholder at their empty `cell`). A selection from another lens doesn't carry to `targets` (existing
behavior: mode change clears selection).

## 7. Out of scope (designed later, with the model)

- **The metric.** Formal TP / FP / TN / FN, IoU-based box matching, normalized-semantic value matching,
  and **per-run validation strategies** (a run declares how it's scored). The §4 matcher is a deliberate
  placeholder behind a pure-function seam so these replace it without UI churn.
- **Real predictions** (the M0 model) and record-alignment beyond index order (e.g. optimal matching).
- **Run-level diff aggregation / summary metrics** in the panel.

## 8. Verification

Build an `eob` dataset → `mock-run` → load the run in the viewer: the target tree renders; the Targets
lens grounds leaves on the page; the seeded perturbations show as match / missing / spurious / mismatch
in both panes; clicking a leaf cross-highlights its box and vice-versa; a plain dataset shows the tree
with no diff. Unit tests: `diffNode` over hand-built target×prediction pairs (each status + cardinality
delta), and the mock generator's perturbation output (each seeded error present, grounding still valid).
