---
kind: spec
status: scaffolding
updated: 2026-06-20
---

# Target schema — materialized, grounded extraction targets — design

- Builds on the **v4** Region/Cell/Word contract ([artifacts.py](../../harness/src/tablelab/artifacts.py)).
  Canonical *why*: [charter.md](../architecture/charter.md); functional map: [index.md](../architecture/index.md).
- **Fulfills and revises** the "labels / task projections" follow-on the v4 schema spec teed up
  ([2026-06-15-region-cell-token-schema-spec.md](2026-06-15-region-cell-token-schema-spec.md), §"Out of scope").
  That plan was `derive_*` projection functions; this spec replaces *derivation* with **materialized
  targets** — §1 says why.

## 1. Why materialize, not derive

The generator *places* every value into a known field of a known record — it **authors** the answer.
A `derive_*` that reconstructs records after the fact (filter `role=="data"`, re-rank `row_index`,
group by region) is a **hand-coded solution to the structure problem the model is meant to learn** —
the geosort baseline trap, one level up. Worse, it makes the *label* a function of that heuristic, so
the benchmark scores the heuristic as much as the model. We know the truth at build time; we store it.

(Reading a *word's* `(record, field)` off the stored target for a token-classification head is still
fine — that is indexing the authored answer, not reconstructing structure from geometry.)

## 2. Three layers (only the third is new)

| layer | unit(s) | role | state |
|---|---|---|---|
| **observables** | `words` (bbox + text; `image` later) | what the page shows | unchanged |
| **structure** | `cells`, `regions` (`role`, `span`, instance) | how it's drawn | unchanged |
| **targets** | `targets[task]` (materialized, grounded) | what it means | **new (v5)** |

Targets are *additive* — words/cells/regions are untouched. Structure stays: it feeds
structure-prediction and the viewer, and it is what target leaves point at.

## 3. The target model

A **target** is a grounded instance of a class-declared **target schema**, materialized at build time.
It is symmetric with model output: a dataset sample carries `targets`, a run sample carries
`predictions`, same shape.

- **field** — one grounded value. A filled field *is* `{ value, word_ids, cell }`. `value` is the
  rendered string (join the cell's words in order); we keep the string, not a normalized date/amount —
  the value *type* lives on the class `FieldSpec`, never on the label. `word_ids` ground it to tokens,
  `cell` to its rect. An **absent** field is explicit: `{ value: "", word_ids: [], cell: <the empty
  cell> }` — sparsity is signal and mirrors the real data.
- **field_group** — a set of fields that repeats → a list of **records**.
- **record** — one entry of a field_group: its own fields, *and optionally nested field_groups* (§5).

Keyed by **task**, so a sample can carry several; `extraction` is the only task this spec defines,
the rest are reserved:

```
sample.targets := { <task>: Node }            # e.g. { "extraction": …, "sentiment": …, "qc": … }
Node           := { fields?: { <name>: Field }, field_groups?: { <name>: [ Node, … ] } }
Field          := { value: str, word_ids: [int], cell: int | null }
```

A target is the document-root `Node`; every record is also a `Node` — uniform recursion.

## 4. The layering rule

> If it is **what you'd store in a database**, it's a **target** (fields / field_groups).
> If it is **how it's drawn** — one table or two, section banners, a TOTALS row, the header — it's
> **structure** (cells / regions).

So multiple rendered tables of one type, "Office Visits" section bands, and totals rows are
*structure*; the target is the semantic fields + (possibly nested) field_groups. A printed total is
just a `field` grounded to the TOTALS-row words; the `summary` cell role marks it structurally.

## 5. Worked example — eob (recursion + variable cardinality)

Real EOBs nest: a document holds 1..N **claims**, each with singleton fields *and* a list of
**service lines**. The recursive `Node` captures it directly. Every count is a list length — nothing
is capped, which retires v0's artificial `max_records = 16` and makes cardinality part of the learning
problem (set / variable-length prediction). `sample.targets` for one eob:

```json
{ "extraction": {
  "fields": {
    "member_name": { "value": "John Smith",        "word_ids": [41, 12], "cell": 0 },
    "provider":    { "value": "Acme Medical Group", "word_ids": [8, 30, 5], "cell": 4 }
  },
  "field_groups": {
    "claims": [
      {
        "fields": {
          "claim_number": { "value": "A100293", "word_ids": [2],  "cell": 7 },
          "claim_total":  { "value": "$25.00",  "word_ids": [15], "cell": 40 }
        },
        "field_groups": {
          "service_lines": [
            { "fields": {
                "service_date": { "value": "03/14/2025", "word_ids": [19], "cell": 22 },
                "code":         { "value": "99213",      "word_ids": [3],  "cell": 23 },
                "copay":        { "value": "",           "word_ids": [],   "cell": 28 },
                "amount_owed":  { "value": "$25.00",     "word_ids": [15], "cell": 31 }
            } }
          ]
        }
      }
    ]
  }
}}
```

A document with no claims carries `"claims": []` (explicit-empty, same rule as an absent field).
Whether the synthetic eob models "2 claim tables" as two `claims` records (nested, true to real EOBs)
or a visual split of one flat field_group is a **class-modeling** call (§9), not a schema constraint.

## 6. The schema (the type) is the DocumentClass

The class already declares it: `globals` → singleton **fields**; each `TableSpec` → a **field_group**
of records over its `FieldSpec`s. We formalize that mapping and emit instances. The `TableSpec` becomes
"the *layout* of a field_group" (how) — distinct from the field_group (what). No new declaration
surface for the flat case; nested classes (claims → service_lines) are authored when first needed.

## 7. Real-label parity

`fields` / `field_groups` is the production labeling vocabulary (singleton fields; field_groups =
repeated records). Matching it is the point of being Textract-shaped: **structure** mirrors Textract
blocks (CELL / KEY_VALUE / LAYOUT — see the v4 spec's correspondence table), **targets** mirror the
*real labels*. Real labeled data and synthetic then land in one representation — pretrain on dense
synthetic, transfer on real.

## 8. Contract changes — v4 → v5 (additive)

- `SCHEMA_VERSION` `4 → 5`. **Observables and structure unchanged**; only `targets` is added — the
  seam holds again.
- `artifacts.py`: `Sample` gains `targets: dict[str, Node]`; run samples gain `predictions`;
  dataclasses + `read`/`write` round-trip them; `_sample_from_dict` parses targets.
- `layout.py` / `build.py`: emit the target **as records are placed** (the authored path — the layout
  loop already knows record `r`, field `c`, and the words it emits), not by post-hoc reconstruction.
- `manifest.task`: today the literal `"grid_record_field"`; becomes the task set / schema id.
- `viewer`: render a target / prediction tree; overlay `predictions[task]` against `targets[task]`.
- **Golden**: regenerated (sample shape changes — a contract change). Asserts full
  `words / cells / regions / targets` for the invoice seed.

## 9. Out of scope

- **The model + metric** that produce and score targets (the "prove the idea" loop): structured
  field / record / exact metrics, geosort as the bar. Designed with the loop.
- **prediction** internals (confidence, partial trees) — symmetric to `target`, detailed with the model.
- **Non-extraction targets** (sentiment, qc) beyond reserving the `task` key.
- The **eob nesting** class-modeling decision (flat vs. nested `claims`).
- Normalized values / value-type classification — out by charter.

## 10. Verification

- **Round-trip**: `write` then `read` reproduces `targets` / `predictions`; `schema_version == 5`.
- **Grounding invariants**: every target `word_id` references a real `Word`; every non-empty leaf's
  `cell` bbox encloses its words; absent leaves have `word_ids == []` and a `cell`.
- **Completeness**: every non-background word appears in exactly one target leaf (extraction covers the
  document); leaf↔cell `field` agree.
- **Golden**: regenerated invoice sample matches its committed fixture byte-for-byte.
- **Viewer smoke**: build an `eob` set; the target tree renders, grounded boxes land in-page, empty
  fields show.
