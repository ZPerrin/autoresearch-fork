# autoresearch — design & roadmap

- Status: **authoritative** (current state + direction; supersedes the original v0 framing as we've iterated)
- Date: 2026-06-13

## What this is

A from-scratch, learning-first research harness for **multimodal document information
extraction**. Forked from karpathy's `autoresearch` (single-GPU nanochat); we keep its machinery
(single-file model, fast build→train→eval→keep/discard loop, frozen metric) but repoint it at
documents. Two goals, pursued together: **learn multimodal DL by implementing it from scratch**
(grad-school / work focus), and **make headway on generalizable repeated-record extraction** from
semi-structured documents (EOBs, invoices, receipts). Real labeled data is scarce, so we curate
**synthetic** data ourselves.

## Architecture (as built)

- **`harness/`** — Python module (src-layout package `src/tablelab/`): dataset builder, model,
  training, artifacts/contract. `uv` + device-aware torch (MPS + CUDA), Pillow.
- **`datasets/`** — curated synthetic data: `<id>/{manifest.json, samples.json, images/}`.
  **Local & gitignored** — built to be reused, culled, and forked into variants.
- **`runs/`** — the experiment ledger: `index.json` + `<run>/…`. **Git-tracked, binary-free**;
  references a dataset by `dataset_id`.
- **`viewer/`** — Vite/React split-pane review app: **left** = document image + token overlay,
  **right** = metadata / selected-token detail / source picker. No backend (dev-server middleware
  serves `/runs` + `/datasets`).
- Joined only by the **artifact contract** (schema v2). Two data layers: `datasets/` (the data)
  vs `runs/` (the ledger).

## The research spine: modalities & the model ladder

Data is multimodal from the start (LayoutLMv3 stack): **spatial** (token boxes), **semantic**
(token text), **visual** (page image). We're multimodal at the *data* layer and climb at the
*model* layer — modality is a config knob, so the loop becomes a clean **modality-ablation** rig:
**M0** spatial → **M1** + semantic → **M2** + visual → **M3** fusion.

## Task framing (three layers)

- **Observables** (locked): per-token `bbox + text`, per-sample `image`.
- **Task labels** (open): `label`/`pred` dicts keyed by `config.task`. Current task
  `grid_record_field` → `label = {record, field}`.
- **Annotation schema** (deferred): document-class → global fields + table definitions +
  instances. End-state = **repeated-record extraction against a class-defined schema** (e.g. EOB:
  global `member`/`provider` + claim tables of `service_date`/`amount_owed`/…). Modeling approach
  stays open (token classification, extractive QA, structure+QA).

## Current state (done)

- **Env**: device-aware `uv`/torch (MPS + CUDA), `get_device()`, Pillow.
- **Contract v2**: datasets + runs, per-token `text`, per-sample `image`/`width`/`height`,
  `dataset_id`; round-trips + validation.
- **Dataset builder**: renders field-appropriate grids to PNG (invoice/eob/receipt schemas), one
  token per cell, captures word boxes + text → `datasets/<id>/`.
- **Viewer**: split-pane, image overlay (ground-truth + prediction modes), source picker, token
  detail, dataset metadata.
- **Synth-toolkit backbone**: compositional spec API (`FieldSpec`/`LayoutSpec`/`StructureSpec`/
  `RenderSpec`/`DocumentClass` + `fork`; modules `specs`/`fields`/`classes`/`layout`/`render`/
  `build`) joined by a Pillow-free `PlacedToken` IR, plus a `build`/`list`/`inspect` CLI.
  Byte-identical to the prior builder (golden regression test). See
  `2026-06-13-synth-toolkit-backbone-design.md`.
- **Multi-token cells** (first structural-realism feature): `StructureSpec.multi_token` splits
  multi-word cell values into per-word tokens sharing `record/field` + a within-cell `seq`; off is
  byte-identical. See `2026-06-13-multi-token-cells-design.md`.
- **Header row** (second structural-realism feature): `StructureSpec.header` emits a top row of
  field-name tokens (label `{"field": c, "header": True}`); renderer grouping keyed on the cell
  rect (schema-agnostic); off is byte-identical. See `2026-06-13-header-row-design.md`.
- **Background / non-table tokens** (third structural-realism feature): `StructureSpec.background`
  scatters N tokens with `label = null` in the footer band — the negative class; off is
  byte-identical. See `2026-06-13-background-tokens-design.md`.
- **Multiple tables + global fields** (fourth structural-realism feature — the EOB shape):
  `DocumentClass.tables`/`globals`; `TableSpec.instances` stacks instances with a `region` label;
  globals are label:value rows at the top (`label = {"global": name}`); the `eob` class is now the
  full shape. Single-table/instance, no-globals classes stay byte-identical. See
  `2026-06-13-multi-table-globals-design.md`.

## Roadmap (milestones — each gets its own plan when started)

1. **Synthetic data toolkit — ACTIVE** (this doc, below): backbone + **multi-token cells** +
   **header row** + **background tokens** + **multiple tables / globals** shipped. Remaining
   **structural realism** in order — jitter/irregular → spanning cells — then document-class breadth.
   Visual realism architecturally provisioned but deferred.
2. **The loop closes**: M0 spatial model trains on a dataset → emits run artifacts → predictions
   overlaid in the viewer; validate it learns. (Detail in the prior
   `2026-06-13-v0-loop-closes-design.md`, now the *model-loop* milestone — deferred until the
   toolkit matures.)
3. **Modality ladder**: M1 (+text), M2 (+visual), M3 (fusion); modality-ablation experiments.
4. **Full difficulty dial incl. visual realism; real Textract data; autonomous overnight loop.**

---

## Active milestone: the synthetic data toolkit

**Goal:** a powerful, compositional, **CLI-driven** generator — declare document classes, compose
structural features, build / curate / fork datasets — so we can play with and *review* data
options before any model touches them.

### CLI (standard Python: `argparse`, `tqdm`)

- `python -m tablelab.cli build --class <name> --n <count> --out datasets/<id> [overrides…]`
  (progress via `tqdm`).
- `python -m tablelab.cli list` — local datasets + summaries.
- `python -m tablelab.cli inspect <id>` — manifest + quick stats.
- Always writes under `datasets/` (local, gitignored).

### Compositional API (the backbone)

A declarative spec composed from small, testable pieces; the resolved spec is recorded in the
dataset `manifest` (so a dataset is reproducible and forkable):

- **`FieldSpec`** — name, semantic type (value sampler), alignment. Extensible type registry
  (`description`, `quantity`, `unit_price`, `amount`, `date`, `code`, …).
- **`LayoutSpec`** — records range, row/column sizing, jitter / irregularity.
- **`StructureSpec`** — header row; background / non-table tokens; multiple tables + global
  fields; spanning cells; multi-token cells.
- **`RenderSpec`** — page size; **visual-realism extension point** (fonts, ruling, noise, skew) —
  interface defined now, implementations deferred.
- **`DocumentClass`** — ordered fields + layout + structure + render; named, registered,
  **forkable** (copy + override). Datasets = compose a class + difficulty overrides.

### Structural realism to implement (ordered)

All become `StructureSpec`/`LayoutSpec` knobs; all are wanted:

1. **multi-token cells** — multi-word values → several tokens sharing one `record/field`
   (grouping; the biggest realism jump).
2. **header row** — field-name headers.
3. **background / non-table tokens** — `label = null` ("is this part of the answer?").
4. **multiple tables + global / singleton fields** — the EOB shape; adds a table/region index.
5. **jitter / irregular** row heights & column widths.
6. **spanning / merged cells.**

### Document-class breadth

Invoice, **EOB (prioritized — it mirrors the real work problem: multi-table + globals)**,
receipt, with room for purchase order / bank statement / a key-value **form** class.

### Visual realism — deferred (but provisioned)

Not built until the ML/multimodal grasp matures. `RenderSpec` is the seam: a pluggable renderer
interface so fonts / ruling lines / scan noise / skew slot in later without disturbing the rest.

---

## Contract (v2, summary)

`datasets/<id>/{manifest.json, samples.json, images/}`; `runs/{index.json, <run>/run.json,
samples.json}`. `Token = bbox + text + label + pred`; `Sample = tokens + image + width/height`.
Coordinates normalized `[0,1]`; every file carries `schema_version = 2`. Full field-by-field
examples live in `artifacts.py` and the model-loop spec.

## Conventions

Append-only git lab notebook; `master` = infra + current best; `exp/<line>` branches commit every
run (failures kept; "discard" is a status label). `runs/` tracked, `datasets/` local. PR-style
review. **No TDD** — implement and verify by running. (See README "How to work in this repo".)

## Open questions

- `DocumentClass` definition: lean Python registry first; optional YAML/JSON config later.
- Multi-token grouping target representation (shared `record/field` only, or + within-cell order).
- Train/val split representation within a dataset.
