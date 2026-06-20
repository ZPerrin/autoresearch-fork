# v0 — "the loop closes"

> ⚠️ **Superseded in part — read for the M0 *shape*, not its contract.** Predates both the v4
> Region/Cell/Word schema *and* the materialized-target reframe: the target is now **materialized**,
> not derived (per-token `label = {record, field}` is gone), and the M0 proof now requires geometric
> variation + invariance, not "beat majority on clean." Live direction:
> [roadmap.md](../architecture/roadmap.md), [index.md](../architecture/index.md), and the
> [target-schema spec](2026-06-20-target-schema-design.md). Kept for its still-useful model sketch,
> geosort baselines, and H1/H2/H3 hypotheses.

- Status: **deferred milestone — the model loop.** Current direction lives in
  [architecture/](../architecture/) (see [roadmap.md](../architecture/roadmap.md) and
  [index.md](../architecture/index.md)). This spec covers the *model-loop* milestone, to resume once
  the toolkit matures.
- Date: 2026-06-13 (revised: multimodal data foundation + dataset/run split)
- Scope: the model-loop milestone — train a from-scratch model on a dataset and close the loop

## 1. Goal

Prove the full loop closes end-to-end on the smallest honest task:

> **build a synthetic dataset → train a from-scratch model → evaluate against a frozen metric
> → emit static run artifacts → see predictions overlaid on the page in a local web app.**

v0 succeeds when we can run an experiment on either machine (MPS or CUDA) and review its
prediction overlay and metrics in the Vite/React viewer. **Accuracy is not the goal** — the
*loop* is. The first model uses one modality (spatial); a model that decisively beats the
trivial baseline on clean grids is enough.

### End-state context (what we're teeing up for, not building in v0)

The real target is **repeated-record extraction against a class-defined schema**: for a document
class (e.g. medical EOB), recover the tokens — bbox, text, confidence — that answer, per line
item, fields like `service_date`, `amount_owed`, `description`, `copay`. Records are variable in
count; fields are semantic and class-defined; a document may hold global/singleton fields
(`member`, `provider`) *and* multiple table instances. The modeling approach is open. v0 commits
to none of this — it just must not corner the contract. See §3.

### Modalities & the model ladder

The data is **multimodal from the start** — the LayoutLMv3 stack:

- **spatial** — token bounding boxes (geometry)
- **semantic** — token text (the OCR strings)
- **visual** — the rendered page image (pixels)

The synthetic generator emits all three, perfectly aligned and labeled (synthetic = free,
exact ground truth). We are multimodal at the **data layer** and walk unimodal→multimodal at the
**model layer** — modality is a `config` knob, so the autoresearch loop becomes a clean
**modality-ablation** rig:

| Model | Modalities | What it teaches |
|---|---|---|
| M0 (v0) | spatial | from-scratch transformer over box geometry |
| M1 | spatial + semantic | fusing learned text embeddings with layout |
| M2 | spatial + visual | per-token visual features (ROI crop) / ViT patches |
| M3 | full fusion | LayoutLMv3-style tri-modal model |

## 2. The synthetic dataset builder

The generator is **not assumed correct** — designing it is itself an experiment. v0 validates
three hypotheses (spatial modality):

- **H1 (learnable):** a small transformer can group tokens into **records** and type each into a
  **field** from box geometry alone, decisively beating a majority-class baseline.
- **H2 (relational):** structure comes from *comparing* boxes — attention matters; an
  attention-ablation (per-token MLP only) should do markedly worse.
- **H3 (meaningful metric):** the exact-match metric moves sensibly as we perturb difficulty.

### Datasets are curated local assets

Synthetic data lives in **`datasets/<dataset-id>/`** — **local, gitignored**, not seed-ephemeral.
A dataset is a curated, reusable asset you build, browse, **cull** bad samples from, and **fork**
into variants ("same but jitter +0.1"). Each holds a `manifest.json` (id, generator version, the
difficulty/config it was built with, count, modalities), `samples.json` (ground truth), and
`images/*.png`. Experiments reference a dataset by `dataset_id`; the data itself is never
committed. (Proper dataset versioning/registry is a deferred "later store correctly" concern.)

### Generator design (v0, easiest setting)

- Sample a grid: records (rows) ∈ `[2,6]`, fields (cols) ∈ `[2,6]`, uniform. v0's "table" is
  "the tokens inside one table."
- Lay cells on a regular grid; **render the page to a PNG** (Pillow), capturing each word's pixel
  bbox (normalized to `[0,1]`) and its text string. So every sample carries **image + text + box
  + label** even though the first model uses only boxes.
- Emit tokens in **shuffled order**, each with `(x0,y0,x1,y1)`, `text`, and `label={record,field}`.
- Difficulty knobs present but pinned to easiest; the dial (alignment/jitter → multi-token cells →
  background tokens → multiple tables → spans → semantic text; plus visual axes: fonts/noise/skew)
  is post-v0.

## 3. Task formulation — three layers

The contract separates three things so we stay flexible across modeling approaches:

| Layer | What it is | v0 stance |
|---|---|---|
| **Observables** | per-token `bbox + text`, per-sample `image` (spatial/semantic/visual) | locked: always present |
| **Task labels** | the target for *one* experiment's approach | open: `label`/`pred` dicts, keyed by a `task` tag in `config` |
| **Annotation schema** | document-class → global fields + table defs + instances | deferred entirely |

v0's experiment is `task = "grid_record_field"`: per-token classification into a **record** and a
**field**, `label = {record, field}`, `pred = {record, field, confidence}`. Loss = sum of CE on
record and field. A different approach later (e.g. `task = "extractive_qa"`, or form `kv`) reuses
the same artifact/viewer plumbing with its own `label` convention.

## 4. Model (from scratch)

Deliberately small and hand-built — the learning artifact, and one rung (M0, `grid_record_field`),
not a final architecture.

- **Input embedding:** linear `4 → d_model` over box coords. This *is* the positional encoding —
  here position is the input, not a sinusoid bolted on.
- **Encoder:** a few transformer encoder layers; self-attention is the point (a token learns its
  record/field by comparing its box to the others).
- **Heads:** two linear heads → record logits, field logits.
- Defaults: `d_model=128`, `n_layers=4`, `n_heads=4`, `max_records=max_fields=16`.
- Device-agnostic PyTorch — no Muon, no `torch.compile`, no forced bf16.

Climbing the ladder (M1+) adds a text-embedding branch and a visual branch fused into the same
encoder — future specs.

## 5. Training & evaluation

- **Budget:** a fixed number of **training steps** for v0.
- **Frozen metric** (higher is better): `record_acc`, `field_acc`, `exact` (both correct).
- **Baselines:** majority-class and a geometric-sort heuristic (sort by y → record, x → field).
- A run records which dataset it used (`config.dataset_id`).

## 6. The artifact contract

Two layers, deliberately separated:

- **`datasets/`** — the data. **Local, gitignored.** Curatable.
- **`runs/`** — the experiment ledger. **Git-tracked, binary-free.** References a dataset by id.

Every file carries `schema_version` (now **2**). Coordinates normalized to `[0,1]`. The viewer
serves both `/runs` and `/datasets` locally and composes them (prediction boxes from a run over
the page image from its dataset); with no local dataset it still renders boxes/metrics, just no
image backdrop.

### `datasets/<id>/manifest.json`

```json
{
  "schema_version": 2,
  "dataset_id": "grid-v1-a",
  "created": "2026-06-13T15:00:00Z",
  "generator_version": 1,
  "task": "grid_record_field",
  "modalities": ["spatial", "semantic", "visual"],
  "count": 512,
  "config": { "difficulty": { "rows": [2,6], "cols": [2,6], "jitter": 0.0 } }
}
```

### `datasets/<id>/samples.json` — ground truth (no predictions)

```json
{
  "schema_version": 2,
  "samples": [
    {
      "id": 0,
      "image": "/datasets/grid-v1-a/images/0.png",
      "width": 1000, "height": 1414,
      "tokens": [
        { "x0": 0.05, "y0": 0.10, "x1": 0.40, "y1": 0.16, "text": "Office chair",
          "label": { "record": 1, "field": 0 } }
      ]
    }
  ]
}
```

### `runs/index.json` — run list + experiment log

```json
{
  "schema_version": 2,
  "runs": [
    { "run_id": "jun13-mps-b2c3d4e", "commit": "b2c3d4e", "branch": "exp/v0",
      "device": "mps", "status": "keep", "description": "M0 baseline",
      "dataset_id": "grid-v1-a",
      "metrics": { "exact": 0.41, "record_acc": 0.62, "field_acc": 0.55 } }
  ]
}
```

### `runs/<id>/run.json` — full per-run record

```json
{
  "schema_version": 2,
  "run_id": "jun13-mps-b2c3d4e", "commit": "b2c3d4e", "branch": "exp/v0", "device": "mps",
  "config": {
    "task": "grid_record_field", "dataset_id": "grid-v1-a", "modalities": ["spatial"],
    "model": { "d_model": 128, "n_layers": 4, "n_heads": 4, "max_records": 16, "max_fields": 16 },
    "budget": { "kind": "steps", "value": 2000 }, "batch_size": 32, "lr": 0.0003
  },
  "metrics": { "exact": 0.41, "record_acc": 0.62, "field_acc": 0.55,
               "baseline_majority_exact": 0.08, "baseline_geosort_exact": 0.86 },
  "curve": [ { "step": 100, "train_loss": 2.31, "val_exact": 0.12 } ],
  "wall_seconds": 123.4, "status": "keep"
}
```

### `runs/<id>/samples.json` — prediction samples for rendering

Same token shape as a dataset sample, plus `pred`, and an `image` ref into the dataset:

```json
{
  "schema_version": 2,
  "dataset_id": "grid-v1-a",
  "samples": [
    {
      "id": 0,
      "image": "/datasets/grid-v1-a/images/0.png",
      "width": 1000, "height": 1414,
      "tokens": [
        { "x0": 0.05, "y0": 0.10, "x1": 0.40, "y1": 0.16, "text": "Office chair",
          "label": { "record": 1, "field": 0 },
          "pred":  { "record": 1, "field": 0, "confidence": 0.98 } }
      ]
    }
  ]
}
```

## 7. The viewer (Vite/React)

Local web app, **no backend** — a dev-server middleware serves both `/runs` and `/datasets` from
disk (PNG served with correct content-type).

v0 views:

- **Run selector / experiment log** — table from `runs/index.json`.
- **Prediction overlay** — render the sample's **page image** as the backdrop, draw token boxes
  on top: teal where `pred` matches `label`, red on mismatch, neutral + `record·field` label when
  `pred` is absent (dataset/ground-truth browsing). Interpreted per `config.task`. Sample browser
  + "errors only" filter. Degrades gracefully if the image is missing locally.
- **Metric cards** — `record_acc`, `field_acc`, `exact`, Δ vs previous run.
- **Training curve** — from `run.json.curve`.
- (Reuses the same overlay to **browse a dataset** truth-only.)

## 8. Env foundation

- `uv`, device-aware torch (MPS + CUDA), `get_device()` (cuda→mps→cpu).
- Add **Pillow** (rendering). Other LM-only deps stay shed.

## 9. Component boundaries & build order

Each unit testable alone, joined by the artifact contract (datasets/ ↔ runs/).

1. **Contract v2 + fixture** — schema (dataset manifest/samples + run records), tiny committed
   `_fixture` (with a small image) to unblock the viewer.
2. **Env** — device-aware deps + Pillow.
3. **Dataset-builder generator** — renders PNG + emits image/text/box/label into `datasets/<id>/`
   (local, gitignored).
4. **Model + train + eval + emitter** — trains on a dataset, emits run artifacts (M0, spatial).
5. **Viewer** — image-overlay over `/datasets`, against the fixture first, then real runs.

## 10. Repo workflow

Append-only git lab notebook; `master` = infra + current best; `exp/<line>` branches commit every
run (failures kept; "discard" is a status label). `runs/` git-tracked (JSON only); `datasets/`
local & gitignored. Review is PR-style.

## 11. Success criteria

- One command builds a dataset and runs an experiment on MPS and CUDA, producing schema-valid run
  artifacts.
- M0 decisively beats the majority baseline (H1); attention-ablation worse (H2); `exact` degrades
  with jitter (H3).
- The viewer overlays predictions on the page image and renders metrics/curve/log from artifacts.

## 12. Open questions (resolve during planning)

- Variable token count per sample → padding + attention mask vs. bucketing.
- `max_records`/`max_fields` fixed width vs. relative (start fixed at 16).
- Synthetic text content for v0 (random tokens vs. field-appropriate strings — the latter
  pre-stages semantic typing).
- Page render size / DPI and how small the committed `_fixture` image should be.
