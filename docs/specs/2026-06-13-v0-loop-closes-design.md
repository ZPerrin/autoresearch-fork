# v0 — "the loop closes"

- Status: draft for review
- Date: 2026-06-13
- Scope: the first end-to-end milestone for the from-scratch table-extraction harness

## 1. Goal

Prove the full loop closes end-to-end on the smallest honest task:

> **generate synthetic layouts → train a from-scratch layout transformer → evaluate against a
> frozen metric → emit static artifacts → see the result rendered in a local web app.**

v0 succeeds when we can run an experiment on either machine (MPS or CUDA) and review its
prediction overlay and metrics in the Vite/React viewer. **Accuracy is not the goal** — the
*loop* is. A model that decisively beats the trivial baseline on clean grids is enough.

### Non-goals (deferred, each its own later spec)

- The difficulty dial beyond the easiest setting (text content, background/non-table tokens,
  noise/skew, spanning cells, multiple tables).
- Real Textract data.
- The autonomous overnight keep/discard loop (upstream `program.md` flow).
- Docker (CUDA box only when it comes — MPS can't be containerized on macOS).
- Muon and other H100-era performance tricks.
- Cross-machine result *comparability*. Both runtimes must run; comparing their numbers is not
  a v0 concern.

## 2. The synthetic data experiment

The generator is **not assumed correct** — designing it is itself an experiment. v0 validates
three hypotheses:

- **H1 (learnable):** a small transformer can recover `(row, col)` for each token from box
  geometry alone, decisively beating a majority-class baseline.
- **H2 (relational):** structure comes from *comparing* boxes — so attention matters; an
  ablation with attention removed (per-token MLP only) should do markedly worse.
- **H3 (meaningful metric):** cell-exact accuracy moves sensibly as we perturb difficulty
  (e.g. adding jitter degrades it), confirming the metric tracks what we care about.

### Generator design (v0, easiest setting)

- Sample a grid: `rows ∈ [2,6]`, `cols ∈ [2,6]`, uniform.
- Lay cells on a regular grid in a normalized page (coords in `[0,1]`), one token per cell,
  with small optional jitter (default `0.0` for v0).
- **Boxes only — no text content** in v0 (`text: null`). The structure lives in geometry.
- Emit tokens in **shuffled order**, each with `(x0,y0,x1,y1)` and labels `(true_r, true_c)`.
- Fully **regenerable from a seed**. We commit the seed + `generator_version`, never datasets.
- Difficulty knobs exist in the config but are pinned to easiest; turning them up is post-v0.

## 3. Task formulation

Per-token classification. Input: an unordered set of token boxes. Output, for each token: a
row-index logit vector and a column-index logit vector (classification over `[0, max_rows)` and
`[0, max_cols)`). Loss = sum of cross-entropy on row and column. This keeps the metric clean and
automatable; richer formulations (edge prediction, set prediction) are deferred.

## 4. Model (from scratch)

Deliberately small and hand-built — this is the learning artifact.

- **Input embedding:** linear `4 → d_model` over the box coords. This *is* the positional
  encoding — a first "click": here position is the input, not a sinusoid bolted on.
- **Encoder:** a few transformer encoder layers (self-attention + MLP). Self-attention is the
  point — a token only knows it's "row 2, col 3" by comparing its box to the others.
- **Heads:** two linear heads → row logits, column logits.
- Default starting size: `d_model=128`, `n_layers=4`, `n_heads=4`, `max_rows=max_cols=16`. These
  are starting points an experiment may change.

Written in plain, device-agnostic PyTorch — no Muon, no `torch.compile`, no forced bf16.

## 5. Training & evaluation

- **Budget:** a fixed number of **training steps** for v0 (deterministic, device-independent,
  good for a reproducible learning record). Wall-clock budgets are a later option.
- **Frozen metric** (the ground truth, higher is better), computed on freshly generated held-out
  samples: `row_acc`, `col_acc`, and `cell_exact` (both row and column correct).
- **Baselines** recorded alongside, for sanity: majority-class (everything `r=0,c=0`) and a
  geometric-sort heuristic (sort by y → row band, by x → col band). Beating majority decisively
  ⇒ loop works; approaching the geometric heuristic ⇒ attention learned the structure.

## 6. The artifact contract

The seam between Python (produces) and React (consumes). Defined first so the model and viewer
build independently. **May evolve** — every file carries `schema_version`. All committed under a
git-tracked `runs/` directory; coordinates are normalized to `[0,1]`.

### `runs/index.json` — the run list + experiment log

```json
{
  "schema_version": 1,
  "runs": [
    {
      "run_id": "jun13-mps-b2c3d4e",
      "commit": "b2c3d4e",
      "branch": "exp/v0",
      "device": "mps",
      "created": "2026-06-13T14:21:00Z",
      "status": "keep",
      "description": "baseline: 2-layer, box-coords only",
      "metrics": { "cell_exact": 0.41, "row_acc": 0.62, "col_acc": 0.55 }
    }
  ]
}
```

### `runs/<run-id>/run.json` — full per-run record

```json
{
  "schema_version": 1,
  "run_id": "jun13-mps-b2c3d4e",
  "commit": "b2c3d4e",
  "branch": "exp/v0",
  "device": "mps",
  "config": {
    "seed": 1234,
    "generator_version": 1,
    "difficulty": { "rows": [2, 6], "cols": [2, 6], "jitter": 0.0, "text": false, "background": false },
    "model": { "d_model": 128, "n_layers": 4, "n_heads": 4, "max_rows": 16, "max_cols": 16 },
    "budget": { "kind": "steps", "value": 2000 },
    "batch_size": 32,
    "lr": 0.0003
  },
  "metrics": {
    "cell_exact": 0.41, "row_acc": 0.62, "col_acc": 0.55,
    "baseline_majority_cell_exact": 0.08,
    "baseline_geosort_cell_exact": 0.86
  },
  "curve": [ { "step": 100, "train_loss": 2.31, "val_cell_exact": 0.12 } ],
  "wall_seconds": 123.4,
  "status": "keep"
}
```

### `runs/<run-id>/samples.json` — a handful of eval samples for rendering

```json
{
  "schema_version": 1,
  "samples": [
    {
      "id": 0,
      "tokens": [
        { "x0": 0.05, "y0": 0.10, "x1": 0.40, "y1": 0.16, "text": null, "true_r": 1, "true_c": 0, "pred_r": 1, "pred_c": 0 }
      ]
    }
  ]
}
```

## 7. The viewer (Vite/React)

A local web app that reads the artifacts and nothing else — **no backend, pure static fetch**.
It reads `runs/index.json`, then a selected run's `run.json` and `samples.json`.

v0 views:

- **Run selector / experiment log** — table from `index.json` (run id, device, status, metrics,
  description).
- **Prediction overlay** — render a sample's boxes on a normalized page; color teal where
  `(pred_r, pred_c) == (true_r, true_c)`, red otherwise, annotated `pred ≠ true`. Sample browser
  (prev/next) with an "errors only" filter. This is the primary debugging surface.
- **Metric cards** — `row_acc`, `col_acc`, `cell_exact`, and Δ vs the previous run.
- **Training curve** — loss and `val_cell_exact` over steps from `run.json.curve`.

Because `runs/` is git-tracked, checking out a branch swaps what the viewer shows (per-branch
view). A global cross-branch timeline is post-v0 (a `collate` read over branches). The exact
mechanism for the dev server to serve `runs/` (symlink into `public/` vs. a static mount) is an
implementation detail for the plan; no backend either way.

## 8. Env foundation

Built first; everything sits on it.

- Keep `uv`. Make the torch dependency **device-aware** so Apple silicon pulls the default
  (MPS-capable) wheel and the 3080 Ti pulls the CUDA wheel. Upstream's CUDA-only pin must be
  fixed — it does not install on the Mac.
- A single `get_device()` (`cuda` → `mps` → `cpu`); never hard-code device.
- Shed LM-only deps not needed for boxes-only (`tiktoken`, `rustbpe`, `kernels`).

## 9. Component boundaries & build order

Designed so each unit is testable alone, joined only by the artifact contract.

1. **Artifact schema + a hand-authored fixture** (`runs/_fixture/`) — define the contract; the
   fixture unblocks the viewer immediately.
2. **Env foundation** — device-aware deps, `get_device()`.
3. **Synthetic generator** — testable in isolation: emits valid samples; round-trips the schema.
4. **Model + train + eval + emitter** — consumes generator output, emits artifacts conforming to
   the schema; validates H1–H3.
5. **Viewer** — built against the fixture first, then pointed at real `runs/`.

## 10. Repo workflow (assumed by this spec)

Conventions live in the README (the operating guide). In brief: append-only git lab notebook;
`master` = infra + current best; `exp/<line>` branches commit every run (failures kept, "discard"
is a status label, never `git reset`); globally-unique run ids; artifacts committed under `runs/`;
review is PR-style (diff + one-line rationale).

## 11. Success criteria

- One command runs an experiment on MPS and on CUDA, producing schema-valid artifacts.
- The model decisively beats the majority baseline on clean grids (H1).
- The attention-ablation does markedly worse (H2).
- `cell_exact` degrades when jitter is raised (H3).
- The viewer renders the run's overlay, metrics, curve, and the experiment log from artifacts
  alone.

## 12. Open questions (resolve during planning)

- Variable token count per sample → padding + attention mask vs. bucketing.
- `max_rows`/`max_cols` as fixed classification width vs. relative indexing (start fixed at 16).
- Dev-server mechanism for serving `runs/` (symlink vs. static mount).
