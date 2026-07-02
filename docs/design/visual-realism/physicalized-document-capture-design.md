---
kind: design
status: ideation
updated: 2026-07-01
---
# Physicalized document capture — design spec

- **Status:** Deferred / north-star. Captures a direction we agreed on; nothing here is scheduled
  to build yet. Visual realism does not bite until the **M2 (+visual)** rung of the modality ladder,
  and tier 1 (below) comes before any of the 3D work.
- **Date:** 2026-06-18
- **Idea space:** `visual-realism`
- **Relates to:** the **Difficulty → real** milestone in `docs/roadmap.md` (the
  `RenderSpec` visual-realism seam), the v4 Region/Cell/Word contract (`harness/src/tablelab/artifacts.py`),
  `JitterSpec` (`harness/src/tablelab/specs.py`).

## Problem

Our synthetic documents are **structurally** rich (regions, cells, spans, headers, sparse fills,
realistic spacing/jitter) but **visually** pristine: flat black text on a white page, drawn by
Pillow. Real-world inputs are not — they're phone photos and scans with camera perspective, uneven
lighting, paper folds/curl/crumple, and ink/substrate degradation (fading, bleed-through, stains,
broken glyphs). We will eventually fine-tune on real labeled data captured under these conditions,
but that data is scarce; the goal here is to see **how far synthetic alone can close the visual
reality gap** before we spend real-label budget.

This doc records the direction, not an implementation. The point is to lock the *architecture and
seams* now so the structure work isn't built in a way that boxes out visual realism later.

## The constraint that drives the whole design

`render()` (`harness/src/tablelab/render.py`) returns the page image **and** the per-word ground-truth
boxes together, both in flat page-space. Every nuisance we want to add — perspective, folds, lighting,
degradation — is a **transform of an already-solved flat document**. So the flat renderer stays the
**source of truth** for both pixels and labels, and distortion is a *downstream* concern.

**Design rule:** distortion is a pure, post-render stage — a new seam *parallel* to `renderer`, never
entangled with it:

```
(flat_image, page_space_boxes)  →  (distorted_image, distorted_boxes [+ transform params])
```

Consequences:
- **The modality ladder stays clean.** M0 (spatial) and M1 (+text) keep consuming flat page-space
  boxes, untouched. Only M2 (+visual) opts into the distorted view.
- **Paired flat ↔ distorted is a free lunch.** Because the flat twin and the exact transform are
  always available, we can train *either* a distortion-robust extractor *or* a dewarp-then-extract
  front-end — or both — from one generator. Real data never gives this pairing without huge labeling
  cost. The distortion stage must therefore **emit the transform params** (homography / mesh + camera),
  not just warped pixels — those are expensive to recover later and free to store now.

## Tier ladder (cheapest first)

1. **2D post-process augmentation** — homography warp (perspective/skew), lighting gradients, blur,
   JPEG artifacts, sensor noise, paper-texture multiply, mild crumple via displacement maps. Runs in
   the existing Python builder (OpenCV); labels stay **exact** by pushing the same homography through
   the box corners. ~80% of "someone photographed a document." **This is the first thing to build,
   when M2 lands.**
2. **2.5D / 3D mesh-projection capture** *(the long-term target of this doc)* — texture the flat page
   onto a deformation mesh (fold / curl / roll / crumple), light it, shoot it with a virtual camera,
   read the framebuffer. The "folds and paper geometry" tier.
3. **Full PBR 3D** (Blender/Unreal, real materials + lens) — maximum fidelity, heaviest. **Rejected
   as overkill**: for a spatial+text extraction task, broad *domain randomization* generalizes better
   than a few photoreal frames, and the residual gap over tier 2 is cheap 2D post-process (see below).

## Chosen long-term direction: tier 2, mesh-projection capture

Why this tier is categorically different from tier 1, not just "more realism":

- **Label projection is free and exact.** A word's box corners are UV coordinates on the page texture.
  They ride the *same* vertex → camera projection the pixels do. We don't "also compute labels" — they
  fall out of the render. (`vector.project(camera)` in WebGL, or the MVP matrix by hand.)
- **Occlusion becomes an emergent, correctly-labeled signal.** A crease can curve part of a word away
  from the camera or tuck it behind a fold — the label exists but the pixels don't (the real
  folded-EOB-through-a-digit failure). Recover it from the depth buffer (z-test: is this surface point
  frontmost at its pixel?) and emit a per-word **visibility fraction**. This is impossible to
  manufacture with correct labels from 2D augmentation, and it's the strongest reason to go 3D.
- **Lighting and geometry are physically consistent.** Fold self-shadows, baseline foreshortening over
  a curl, a phone-flash specular hotspot — emergent from the 3D setup, exactly the "messy photo" cues.
  A 2D homography cannot fake them.

### Engine: WebGL capture engine, not Blender-as-engine

Separate two jobs we'd been bundling under "Blender":

- **Job A — capturing a frame** (texture → mesh → camera → light → read pixels → project labels).
  **WebGL/three.js does all of this well:** offscreen render-to-framebuffer; `MeshStandardMaterial` +
  an HDRI env map for real-ish PBR (diffuse paper, slight specular, soft shadow maps); depth textures
  for the occlusion z-test; MVP matrices in hand for exact label projection.
- **Job B — manufacturing the deformation geometry.** The *only* place a real solver beats WebGL, and
  only for one case. **Key insight: paper is nearly inextensible, so its deformations are developable
  surfaces** — folds, curls, rolls, single creases are all **closed-form vertex displacements** with
  **zero physics** (a fold is a piecewise bend; a curl is a cylindrical/sine displacement; a tri-fold
  is two creases). The *only* geometry that truly wants a cloth solver is full **crumple**
  (non-developable). Bake a handful of crumples **once** (Blender, or a JS mass-spring), export as
  static glTF, reuse.

So: **WebGL is the per-sample capture engine; mesh source is mostly parametric (free), occasionally
baked-once.** Blender drops to an occasional offline tool ("I baked five crumples last month"), not a
per-sample dependency. **Unreal is rejected** — it's built for real-time interactive rendering; we
want offline, seed-reproducible batch.

The residual reality gap after WebGL (real lens chromatic aberration, vignetting, bokeh; sensor noise)
is cheap **2D post-process stacked on top** of the captured frame (i.e. reuse tier-1 ops). WebGL
capture + tier-1 post = genuinely close for documents specifically.

## Label-contract implications

- **Page-space axis-aligned `bbox` stays the canonical observable.** The distorted view is *additive*:
  it does not mutate the v4 contract.
- Under perspective/fold a tight box becomes a **quadrilateral**. The distorted view should carry a
  **Textract-shaped polygon** (4 corners — aligns with our "stay Textract-compatible" principle and
  Textract's `Geometry.Polygon`), the **transform params**, and a **visibility fraction**.
- **Curved-within-word precision knob:** if a crease runs *through* a word, the straight quad between
  projected corners under-describes the warped glyph. Gentle folds: fine. Sharp creases: sample points
  *along* the box edges and emit a finer polyline. A dial, not a blocker.
- **Open question — degradation vs the atomic-word assumption.** Geometry is the easy axis (a clean
  coordinate transform; labels follow exactly). Ink/substrate degradation is the hard one: faded
  strokes, bleed-through, broken glyphs can make a word **no longer cleanly segmentable into a word** —
  precisely the real OCR failure. Decide later whether degraded data is "same labels, uglier pixels"
  (easy) or "the segmentation itself degrades" (more real, and it changes what the model is asked).

## Config shape

A `DistortSpec` that **mirrors `JitterSpec`**: per-axis, independent, zeroable magnitudes
(perspective / curl / fold / lighting / blur / noise / ink-erosion), so a dataset can turn **one**
nuisance on at a time and watch the model break — same modeling-ablation DNA as the existing jitter
knobs. This is the natural home for the difficulty dial.

## Architectural wrinkle to resolve before building tier 2

Data-gen must be **headless, seed-reproducible, and write artifacts to disk** — and the builder is
**Python**. A WebGL path means a JS renderer stage (headless node + three.js, driven as a subprocess
from the Python builder), which **splits the builder across two languages**. The competing pull: the
viewer is **already** Vite/React, so the *same* three.js renderer could preview distortions live in
the viewer (a real, attractive coupling). The Python-GL alternative (moderngl / pyrender) keeps one
language and gives us the camera math from scratch, but loses the shared-renderer synergy.

Decision deferred. It's a **placement** question (share with the viewer vs unify with the builder),
not a capability one — both stacks can do the capture.

## What we deliberately deferred / did not decide

- Build order beyond "tier 1 first, at M2." No APIs, no transform math worked out, no manifest fields
  finalized — this is a direction, not a buildable spec.
- The JS-vs-Python renderer placement (above).
- The degradation-vs-segmentation question (above).
- The specific catalog of canonical deformation meshes worth baking.

## Next step when this is picked up

Promote to a dated, buildable spec in `docs/specs/` for the **tier-1 2D augmentation stage** first
(smallest seam, exact labels, no new render engine), and only schedule tier-2 mesh capture once a
model demonstrably plateaus on flat-but-noisy input.
