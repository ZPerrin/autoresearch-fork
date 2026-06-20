---
kind: plan
status: implemented
updated: 2026-06-20
---

# Target schema v5 (harness) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add materialized, grounded extraction targets to the contract (v4 → v5): the generator authors `targets["extraction"]` per document and the harness round-trips it.

**Architecture:** Targets are *additive* — words/cells/regions are untouched (the contract seam holds). The target tree (`Node` of `fields` / `field_groups` of records) is emitted **structurally inside the placement loop** in `layout.py` — never reconstructed from the `cells` list (grouping by `row_index`/region is the geosort anti-pattern the spec forbids, §1). `globals` → root `fields`; each `TableSpec` → a `field_groups[name]` of one record per data row, flattened across instances (the flat class-modeling rule for current classes). Leaves carry `word_ids` + a `cell` index, resolved after the word shuffle exactly like cells already are.

**Tech Stack:** Python 3.10+, dataclasses, `uv`, pytest. Run all commands from `harness/`.

**Scope:** Harness only — contract, emission, build wiring, golden. The **viewer** (render the target tree, §8/§10 of the spec) is a separate follow-on plan, authored against the real emitted JSON this plan produces.

**Source spec:** [docs/specs/2026-06-20-target-schema-spec.md](../specs/2026-06-20-target-schema-spec.md).

---

## File Structure

- `harness/src/tablelab/artifacts.py` — add `Field`, `Node` dataclasses; `Sample` gains `targets` + `predictions`; `SCHEMA_VERSION` 4→5; recursive parse/round-trip.
- `harness/src/tablelab/layout.py` — placement-phase `_TargetField` / `_TargetNode`; build the root during the layout loop; resolve to `artifacts.Node` on return; new `layout_with_targets` (4-tuple) with `layout_with_regions` / `layout` re-expressed as slices (all existing 3-tuple callers stay green).
- `harness/src/tablelab/build.py` — consume `layout_with_targets`; set `Sample.targets`; manifest `task` → `"extraction"`.
- `harness/tests/test_contract_roundtrip.py` — version bump + targets/predictions round-trip.
- `harness/tests/test_targets.py` — **new** — structure + grounding invariants (spec §10).
- `harness/tests/test_golden.py` + `harness/tests/golden/invoice_seed7_n3.json` — extend `_gen` to emit targets; regenerate fixture.

---

## Task 1: Contract types — `Field`, `Node`, `Sample.targets`, schema v5

**Files:**
- Modify: `harness/src/tablelab/artifacts.py`
- Test: `harness/tests/test_contract_roundtrip.py`

- [ ] **Step 1: Update the round-trip test (version + targets)**

Replace the whole body of `harness/tests/test_contract_roundtrip.py` with:

```python
from pathlib import Path
from tablelab.artifacts import (Sample, Word, Cell, Region, Field, Node,
                                DatasetManifest, write_dataset, read_dataset,
                                SCHEMA_VERSION)


def test_schema_version_is_5():
    assert SCHEMA_VERSION == 5


def test_sample_with_cells_regions_and_targets_roundtrips(tmp_path: Path):
    sample = Sample(
        id=0,
        words=[Word(0.1, 0.1, 0.2, 0.15, "Acme"), Word(0.3, 0.1, 0.4, 0.15, "$5.00")],
        width=1000, height=1400, image="/datasets/x/images/0.png",
        cells=[
            Cell(region_index=0, row_index=0, column_index=0, span=[1, 1],
                 bbox=[0.1, 0.1, 0.2, 0.15], role="data", field="description", word_ids=[0]),
            Cell(region_index=0, row_index=0, column_index=1, span=[1, 1],
                 bbox=[0.3, 0.1, 0.4, 0.15], role="data", field="amount", word_ids=[1]),
        ],
        regions=[Region(type="table", name="line_item", index=0, bbox=[0.1, 0.1, 0.4, 0.15])],
        targets={"extraction": Node(field_groups={"line_item": [
            Node(fields={
                "description": Field(value="Acme", word_ids=[0], cell=0),
                "amount": Field(value="$5.00", word_ids=[1], cell=1),
            })
        ]})},
    )
    manifest = DatasetManifest(dataset_id="x", generator_version=1, task="extraction",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got == [sample]


def test_empty_targets_default_and_roundtrip(tmp_path: Path):
    sample = Sample(id=0, words=[Word(0.1, 0.1, 0.2, 0.15, "x")])
    assert sample.targets == {} and sample.predictions == {}
    manifest = DatasetManifest(dataset_id="y", generator_version=1, task="extraction",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "y")
    assert got == [sample]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_contract_roundtrip.py -q`
Expected: FAIL — `ImportError: cannot import name 'Field'` (and `test_schema_version_is_5` would fail on the old `4`).

- [ ] **Step 3: Add the dataclasses and bump the version**

In `harness/src/tablelab/artifacts.py`, change line 6:

```python
SCHEMA_VERSION = 5
```

Add, immediately after the `Region` dataclass (after line 33):

```python
@dataclass
class Field:
    value: str                             # rendered string (cell's words joined in order); "" if absent
    word_ids: list[int] = dc_field(default_factory=list)  # grounding tokens; [] if absent
    cell: int | None = None                # index into Sample.cells; the empty cell if absent


@dataclass
class Node:
    """A target/prediction subtree: singleton ``fields`` and repeating ``field_groups``
    (each a list of record Nodes). The document root and every record are both Nodes."""
    fields: dict[str, Field] = dc_field(default_factory=dict)
    field_groups: dict[str, list["Node"]] = dc_field(default_factory=dict)
```

In the `Sample` dataclass, add two fields after `regions` (after line 43):

```python
    targets: dict[str, Node] = dc_field(default_factory=dict)
    predictions: dict[str, Node] = dc_field(default_factory=dict)
```

- [ ] **Step 4: Add the recursive parsers and wire `_sample_from_dict`**

In `harness/src/tablelab/artifacts.py`, add after `_word_from_dict` (after line 90):

```python
def _field_from_dict(d: dict) -> Field:
    return Field(value=d["value"], word_ids=d.get("word_ids", []), cell=d.get("cell"))


def _node_from_dict(d: dict) -> Node:
    return Node(
        fields={k: _field_from_dict(v) for k, v in d.get("fields", {}).items()},
        field_groups={k: [_node_from_dict(n) for n in v]
                      for k, v in d.get("field_groups", {}).items()},
    )
```

Then, in `_sample_from_dict`, add the targets/predictions kwargs to the `Sample(...)` call:

```python
def _sample_from_dict(d: dict) -> Sample:
    raw_regions = d.get("regions")
    regions = [Region(**r) for r in raw_regions] if raw_regions is not None else None
    cells = [Cell(**c) for c in d.get("cells", [])]
    targets = {k: _node_from_dict(v) for k, v in d.get("targets", {}).items()}
    predictions = {k: _node_from_dict(v) for k, v in d.get("predictions", {}).items()}
    return Sample(id=d["id"], words=[_word_from_dict(w) for w in d["words"]],
                  image=d.get("image"), width=d.get("width"), height=d.get("height"),
                  cells=cells, regions=regions, targets=targets, predictions=predictions)
```

(`asdict` already serializes `targets`/`predictions` recursively — dicts of dataclasses and lists of dataclasses are handled. No change needed to `_write_samples`.)

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/test_contract_roundtrip.py -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/artifacts.py harness/tests/test_contract_roundtrip.py
git commit -m "feat(contract): v5 — additive grounded targets (Field/Node)"
```

---

## Task 2: Emit targets during placement (`layout.py`)

**Files:**
- Modify: `harness/src/tablelab/layout.py`
- Test: `harness/tests/test_targets.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `harness/tests/test_targets.py`:

```python
import random

from tablelab import classes as classlib
from tablelab.artifacts import Field, Node
from tablelab.layout import layout_with_targets, layout_with_regions


def _extraction(dc_name, seed=7):
    dc = classlib.get(dc_name)
    words, cells, regions, targets = layout_with_targets(dc, random.Random(seed))
    return words, cells, targets["extraction"]


def test_layout_with_regions_still_returns_three_tuple():
    dc = classlib.get("invoice")
    out = layout_with_regions(dc, random.Random(7))
    assert len(out) == 3


def test_globals_become_root_fields():
    _w, _c, root = _extraction("eob")
    assert set(root.fields) == {"member_name", "member_id", "provider", "claim_number"}
    for f in root.fields.values():
        assert isinstance(f, Field)


def test_table_becomes_field_group_of_records():
    _w, _c, root = _extraction("eob")
    assert "claim_line" in root.field_groups
    records = root.field_groups["claim_line"]
    assert records and all(isinstance(r, Node) for r in records)
    # each record carries exactly the table's leaf fields
    assert set(records[0].fields) == {
        "service_date", "code", "description", "amount_billed", "allowed",
        "deductible", "copay", "coinsurance", "plan_paid", "amount_owed"}


def test_invoice_records_equal_data_rows():
    words, cells, root = _extraction("invoice")
    data_rows = {(c.region_index, c.row_index) for c in cells if c.role == "data"}
    assert len(root.field_groups["line_item"]) == len(data_rows)


def test_grounding_invariants_eob():
    # `words` are page-px PlacedWord; `cells` are normalized artifacts.Cell — not directly
    # comparable, so grounding is checked via the authored cell membership (word_ids) and
    # the resolved value string, both stronger than a bbox-encloses heuristic.
    words, cells, root = _extraction("eob")

    def leaves(node):
        yield from node.fields.values()
        for recs in node.field_groups.values():
            for r in recs:
                yield from leaves(r)

    for f in leaves(root):
        # every word_id references a real word; cell references a real cell
        assert all(0 <= wid < len(words) for wid in f.word_ids)
        assert f.cell is not None and 0 <= f.cell < len(cells)
        # value is the words joined in reading order
        assert f.value == " ".join(words[i].text for i in f.word_ids)
        # the leaf points at exactly its cell's authored token membership
        assert set(f.word_ids) == set(cells[f.cell].word_ids)
        if not f.word_ids:                      # absent leaf: explicit-empty + a cell
            assert f.value == ""


def test_invoice_completeness_every_word_in_one_leaf():
    # invoice has no header/globals/section/totals/background → every word is a target leaf word.
    words, cells, root = _extraction("invoice")
    seen = []
    for rec in root.field_groups["line_item"]:
        for f in rec.fields.values():
            seen.extend(f.word_ids)
    assert sorted(seen) == list(range(len(words)))
    assert len(seen) == len(set(seen))  # exactly once
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_targets.py -q`
Expected: FAIL — `ImportError: cannot import name 'layout_with_targets'`.

- [ ] **Step 3: Import the new contract types in `layout.py`**

In `harness/src/tablelab/layout.py`, change line 5:

```python
from .artifacts import Cell, Field, Node
```

- [ ] **Step 4: Add placement-phase target dataclasses**

In `harness/src/tablelab/layout.py`, add after the `PlacedRegion` dataclass (after line 151):

```python
@dataclass
class _TargetField:
    value: str
    tokens: list[PlacedWord]                    # transient refs; resolved to word_ids on return
    cell: PlacedCell                            # transient ref; resolved to a cell index on return


@dataclass
class _TargetNode:
    fields: dict[str, _TargetField] = dc_field(default_factory=dict)
    field_groups: dict[str, list["_TargetNode"]] = dc_field(default_factory=dict)


def _resolve_node(tn: "_TargetNode", index_of: dict, cell_index: dict) -> Node:
    return Node(
        fields={k: Field(value=f.value,
                         word_ids=[index_of[id(t)] for t in f.tokens],
                         cell=cell_index[id(f.cell)])
                for k, f in tn.fields.items()},
        field_groups={k: [_resolve_node(r, index_of, cell_index) for r in recs]
                      for k, recs in tn.field_groups.items()},
    )
```

- [ ] **Step 5: Rename the layout body to `layout_with_targets` and build the root**

Rename the function signature at line 538 from `def layout_with_regions(...)` to:

```python
def layout_with_targets(dc: DocumentClass, rng: random.Random) -> tuple[list[PlacedWord], list[Cell], list[PlacedRegion], dict[str, Node]]:
```

Keep its existing docstring; append this sentence to it:

```
    Also authors the extraction target as records are placed: dc.globals -> root
    fields; each table -> a field_group of one record per data row (flattened across
    instances). Returns (words, cells, regions, {"extraction": root}).
```

Initialize the root immediately after `y = float(my)` (after line 556):

```python
    root = _TargetNode()
    for t in dc.tables:                          # explicit-empty groups for tables with 0 instances
        root.field_groups[t.name] = []
```

In the globals loop, capture the sampled value and the value cell so the field can be authored. Replace the value-cell block (lines 576–581) with:

```python
            value_rect = (px0 + gw, y, px0 + pair_w, y + L.row_h)
            gval = sample(f.type, rng)
            toks = _emit_words(placed, gval, value_rect, "left", dc.render.font_size)
            vcell = PlacedCell(region_index=form_index, row_index=i // gpr,
                               column_index=2 * col + 1, span=(1, 1), bbox=value_rect,
                               role="value", field=f.name, tokens=toks)
            cells.append(vcell)
            root.fields[f.name] = _TargetField(value=gval, tokens=toks, cell=vcell)
```

(Splitting the inline `sample(...)` into `gval` is RNG-neutral — one call, same order — and eob is not the byte-identical golden; invoice has no globals.)

In the data-row loop, author a record per row. Inside `for r in range(rows):`, add `record = _TargetNode()` as the first line of the loop body (immediately after `for r in range(rows):` on line 631, before `row_edges = ...`):

```python
            for r in range(rows):
                record = _TargetNode()
                row_edges = (jitter_column_edges(edges, J.col_w, rng)
```

Then, in the inner `for c in range(C):` that emits the data cells (lines 647–670), replace the cell-append block (the final `cells.append(PlacedCell(... role="data" ...))`) so the cell is captured and the field authored. The block from line 668–670 becomes:

```python
                    dcell = PlacedCell(region_index=region_index, row_index=row_idx,
                                       column_index=c, span=(1, 1), bbox=cell_bbox,
                                       role="data", field=f.name, tokens=toks)
                    cells.append(dcell)
                    record.fields[f.name] = _TargetField(value=value, tokens=toks, cell=dcell)
```

After that inner column loop closes (after `y += cell_h` / the `if r < rows - 1:` gap block, i.e. right before `row_idx += 1` at line 674), append the finished record:

```python
                root.field_groups[table.name].append(record)
                row_idx += 1
```

- [ ] **Step 6: Resolve the root and return the 4-tuple**

At the end of the function, replace the return block (lines 701–710) with:

```python
    rng.shuffle(placed)
    index_of = {id(t): i for i, t in enumerate(placed)}
    cell_index = {id(c): i for i, c in enumerate(cells)}
    out_cells = [
        Cell(region_index=c.region_index, row_index=c.row_index,
             column_index=c.column_index, span=list(c.span), bbox=list(c.bbox),
             role=c.role, field=c.field,
             word_ids=[index_of[id(t)] for t in c.tokens])
        for c in cells
    ]
    targets = {"extraction": _resolve_node(root, index_of, cell_index)}
    return placed, out_cells, regions, targets
```

- [ ] **Step 7: Re-express the back-compat wrappers**

Replace the old `layout` wrapper (lines 713–715) with both wrappers:

```python
def layout_with_regions(dc: DocumentClass, rng: random.Random) -> tuple[list[PlacedWord], list[Cell], list[PlacedRegion]]:
    """Words, cells, regions (back-compat; drops targets). See layout_with_targets."""
    return layout_with_targets(dc, rng)[:3]


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedWord]:
    """Words only (back-compat for render/golden helpers)."""
    return layout_with_targets(dc, rng)[0]
```

- [ ] **Step 8: Run the new tests, then the full layout/contract suite**

Run: `uv run pytest tests/test_targets.py -q`
Expected: PASS (7 tests).

Run: `uv run pytest tests/test_regions.py tests/test_capacity.py tests/test_jitter.py -q`
Expected: PASS (3-tuple callers unaffected).

- [ ] **Step 9: Commit**

```bash
git add harness/src/tablelab/layout.py harness/tests/test_targets.py
git commit -m "feat(layout): author grounded extraction targets in the placement loop"
```

---

## Task 3: Wire `build.py` to emit targets end-to-end

**Files:**
- Modify: `harness/src/tablelab/build.py`
- Test: `harness/tests/test_targets.py` (append)

- [ ] **Step 1: Append the end-to-end build test**

Add to `harness/tests/test_targets.py`:

```python
def test_build_dataset_writes_grounded_targets(tmp_path):
    from tablelab.build import build_dataset
    from tablelab.artifacts import read_dataset
    ds = build_dataset(tmp_path, "tg-eob", classlib.get("eob"), seed=7, n=2)
    manifest, samples = read_dataset(ds)
    assert manifest.task == "extraction"
    for s in samples:
        root = s.targets["extraction"]
        assert set(root.fields) == {"member_name", "member_id", "provider", "claim_number"}
        assert root.field_groups["claim_line"]
        # grounding survives normalize + round-trip
        for rec in root.field_groups["claim_line"]:
            for f in rec.fields.values():
                assert all(0 <= wid < len(s.words) for wid in f.word_ids)
                assert f.cell is not None and 0 <= f.cell < len(s.cells)
                assert f.value == " ".join(s.words[i].text for i in f.word_ids)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_targets.py::test_build_dataset_writes_grounded_targets -q`
Expected: FAIL — `KeyError: 'extraction'` (build does not emit targets yet; `manifest.task` is `"grid_record_field"`).

- [ ] **Step 3: Consume `layout_with_targets` and set `Sample.targets`**

In `harness/src/tablelab/build.py`, change the import on line 17:

```python
from .layout import layout_with_targets, validate_layout_capacity
```

Change line 184 to capture targets:

```python
                placed, placed_cells, placed_regions, targets = layout_with_targets(doc_class, rng)
```

Change the `samples.append(Sample(...))` call (lines 202–204) to pass targets:

```python
                samples.append(Sample(id=i, words=words, width=W, height=H,
                                      image=f"/datasets/{dataset_id}/images/{i}.png",
                                      cells=cells, regions=regions, targets=targets))
```

Change the manifest `task` (line 207):

```python
                task="extraction", modalities=["spatial", "semantic", "visual"],
```

- [ ] **Step 4: Run the end-to-end test**

Run: `uv run pytest tests/test_targets.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/build.py harness/tests/test_targets.py
git commit -m "feat(build): emit extraction targets into v5 dataset samples"
```

---

## Task 4: Regenerate the golden fixture with targets

**Files:**
- Modify: `harness/tests/test_golden.py`
- Modify: `harness/tests/golden/invoice_seed7_n3.json`

- [ ] **Step 1: Extend `_gen` to consume the 4-tuple and serialize targets**

In `harness/tests/test_golden.py`, change the import (line 6):

```python
from tablelab.layout import layout_with_targets
```

Change the unpack in `_gen` (line 18):

```python
        placed, cells, regions, targets = layout_with_targets(dc, rng)
```

Add a `"targets"` key to the appended dict. Replace the `out.append({...})` block (lines 23–30) with:

```python
        def _node(n):
            return {
                "fields": {k: {"value": f.value, "word_ids": f.word_ids, "cell": f.cell}
                           for k, f in n.fields.items()},
                "field_groups": {k: [_node(r) for r in recs]
                                 for k, recs in n.field_groups.items()},
            }
        out.append({
            "words": words,
            "cells": [{"region_index": c.region_index, "row_index": c.row_index,
                       "column_index": c.column_index, "span": list(c.span),
                       "role": c.role, "field": c.field, "word_ids": c.word_ids}
                      for c in cells],
            "regions": [{"type": r.type, "name": r.name, "index": r.index} for r in regions],
            "targets": {k: _node(v) for k, v in targets.items()},
        })
```

- [ ] **Step 2: Run to verify it fails (fixture now stale)**

Run: `uv run pytest tests/test_golden.py -q`
Expected: FAIL — `assert got == want` (the committed fixture has no `targets` key).

- [ ] **Step 3: Inspect the diff before regenerating (sanity, not blind overwrite)**

Run:

```bash
uv run python -c "import json, random; from tablelab import classes; from tablelab.layout import layout_with_targets; dc=classes.get('invoice'); rng=random.Random(7); w,c,r,t=layout_with_targets(dc,rng); root=t['extraction']; print('groups:', list(root.field_groups)); print('records:', len(root.field_groups['line_item'])); print('rec0 fields:', list(root.field_groups['line_item'][0].fields))"
```

Expected: `groups: ['line_item']`, a positive record count, and `rec0 fields: ['description', 'quantity', 'unit_price', 'amount']`. Confirms the target shape is sane before it becomes the frozen fixture.

- [ ] **Step 4: Regenerate the fixture**

Run:

```bash
uv run python -c "import json; from pathlib import Path; import tests.test_golden as g; Path('tests/golden/invoice_seed7_n3.json').write_text(json.dumps(g._gen('invoice', 7, 3), indent=2))"
```

If `tests` is not importable as a package, regenerate inline instead:

```bash
uv run python -c "
import json, sys; sys.path.insert(0, 'tests')
import test_golden as g
from pathlib import Path
Path('tests/golden/invoice_seed7_n3.json').write_text(json.dumps(g._gen('invoice', 7, 3), indent=2))
"
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/test_golden.py -q`
Expected: PASS.

- [ ] **Step 6: Full suite green**

Run: `uv run pytest -q`
Expected: PASS (all suites; no 3-tuple caller regressions).

- [ ] **Step 7: Commit**

```bash
git add harness/tests/test_golden.py harness/tests/golden/invoice_seed7_n3.json
git commit -m "test(golden): regenerate invoice fixture with v5 targets"
```

---

## Task 5: Doc hygiene + follow-on note

**Files:**
- Modify: `docs/specs/2026-06-20-target-schema-spec.md` (status)
- Modify: `docs/plans/2026-06-20-target-schema-v5-plan.md` (this file, status)

- [ ] **Step 1: Flip statuses to implemented**

Set `status: implemented` in both front-matters once Tasks 1–4 are green. (Pruning is `/wrap`'s job; leave the files for the wrap pass to retire.)

- [ ] **Step 2: Run doc-lint**

Run (from repo root): `python3 scripts/doc-lint.py`
Expected: no broken-link / unlinked-nav errors.

- [ ] **Step 3: Commit**

```bash
git add docs/specs/2026-06-20-target-schema-spec.md docs/plans/2026-06-20-target-schema-v5-plan.md
git commit -m "docs: mark target-schema v5 (harness) implemented"
```

---

## Out of scope (follow-on)

- **Viewer** — render the target/prediction tree, overlay grounded boxes (spec §8/§10 "Viewer smoke"). Author a separate plan against the real v5 JSON this plan emits.
- **Model + metric**, **prediction internals**, **eob nesting**, **normalized values** — out by the spec (§9).
