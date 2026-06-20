---
kind: roadmap
status: living
updated: 2026-06-20
---

# Roadmap

Long-horizon milestones over a fixed contract; recent activity is in git (`git log`), not here. What
exists today → [index.md](index.md); the *why* → [charter.md](charter.md).

The invariant: one **target** per document — materialized, grounded `fields` / `field_groups`
([target-schema spec](../specs/2026-06-20-target-schema-design.md)); every experiment reproduces or
projects it. Progress is movement along two axes — **modality** (spatial → +semantic → +visual →
fusion) and **difficulty** (clean → realistic → geometric → visual → real) — and the toolkit's realism
is the model's **adversary**: it exists to defeat the geosort baseline (sort y→record, x→field), which
survives clean grids and local jitter, so the rung that truly breaks it is **geometric**. The bar is
beating geosort there, not majority on clean.

## Now

_Parked — set when we move from contract to model._

## Next

_See `## Milestones`._

## Milestones

The spine — the modality × difficulty progression:

- [x] **Structured-truth generator** — compositional class specs → words + cells / regions; the realism
  dial (jitter, spans, sparse cells, multi-instance, wrapping) is largely built — the adversary is ready.
- [ ] **Materialized targets — contract v5** — emit the grounded `fields` / `field_groups` target per
  document; the viewer renders the target tree. *Done when: targets round-trip, every non-background
  word lands in exactly one target leaf, and the eob target reconstructs its claims.*
- [ ] **The loop closes — spatial (M0)** — a from-scratch, box-only model produces the structured
  target; static run artifacts; predictions overlaid on the page. *Done when: it beats geosort on
  geometrically-varied data (skew / perspective / aspect, so absolute position is not a sufficient cue),
  and its prediction is invariant — the same target whether the page is straight or transformed.*
- [ ] **Modality ladder** — M1 (+text), M2 (+visual), M3 (fusion); modality is a config knob, so the
  loop is a clean ablation rig. *Done when: each added modality earns a measurable lift on a regime
  where the prior one plateaus.*
- [ ] **Difficulty → real** — the remaining hard axes:
  [visual realism](../design/visual-realism/physicalized-document-capture-design-spec.md) (the renderer
  seam — fonts, scan noise, capture artifacts), then real Textract data, then transfer. *Done when: a
  synthetic-trained model holds up on real Textract output.*

Cross-cutting — pulled in as a regime needs them, not gating the spine:

- **Document-class breadth** — invoice / receipt / purchase-order / bank-statement / key-value form.
- **Autonomous research loop** — unattended train → evaluate → keep / discard against the frozen metric
  (the autoresearch machinery, repointed).
