---
kind: roadmap
status: living
updated: 2026-06-19
---

# Roadmap

Long-horizon milestones, defined ahead and updated when reached or refined. Recent activity is in git
(`git log`), not here. For what exists today, see [index.md](index.md).

## Now

_To be set next session — the active milestone (M0 model loop vs. document-class breadth) is an open
decision deferred from the doc-system redesign._

## Next

_See `## Milestones` below until `## Now` is set._

## Milestones

- [x] **Synthetic data toolkit** — compositional spec API + `build`/`list`/`inspect` CLI; structural
  realism complete (atomic words, headers, multi-table/globals, spacing/jitter, sparse cells, spanning
  cells + grouped headers). The `eob` class exercises the full shape.
- [ ] **The loop closes (M0, spatial)** — train a from-scratch model on a dataset → emit run artifacts
  → predictions overlaid in the viewer. The v0 design predates schema v4 and needs a refresh (derive
  labels from cells, not per-word labels) before starting.
- [ ] **Document-class breadth** — invoice/receipt variants, purchase order, bank statement, key-value
  form.
- [ ] **Modality ladder** — M1 (+text), M2 (+visual), M3 (fusion); modality-ablation experiments.
- [ ] **Full difficulty dial** — visual realism, real Textract data, autonomous overnight loop.
