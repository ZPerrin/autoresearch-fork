---
kind: plan
status: scaffolding
updated: 2026-06-20
---

# Viewer targets + prediction diff — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Render contract-v5 grounded `targets` in the viewer (right-pane tree + left-pane grounding
lens), and stand up a first-pass, grounding-keyed prediction diff fed by a new `mock-run` CLI generator.

**Architecture:** Two halves behind one seam. (1) Harness: a `mock-run` subcommand copies a built
dataset's samples, injects four seeded perturbations into `predictions`, and writes a binary-free
`RunRecord` to `runs/`. (2) Viewer: a single pure `diffNode(target, pred)` matcher produces a `DiffNode`
that both panes render — the `MetaPanel` tree and a new `targets` overlay lens — with bidirectional
leaf↔box cross-highlight. The matcher is isolated so the future real metric replaces *it*, not the UI.

**Tech Stack:** Python (`tablelab`, `uv`, pytest) for the generator; React 19 + TypeScript + Vite for the
viewer; **vitest** (added in Task 4) for the `diffNode` unit tests.

**Source spec:** [docs/specs/2026-06-20-viewer-targets-diff-spec.md](../specs/2026-06-20-viewer-targets-diff-spec.md).

---

## Orientation (read before starting)

Contract v5 target types already exist and are emitted into datasets. The shapes you will mirror:

```python
# harness/src/tablelab/artifacts.py
@dataclass
class Field:   value: str; word_ids: list[int] = []; cell: int | None = None
@dataclass
class Node:    fields: dict[str, Field] = {}; field_groups: dict[str, list[Node]] = {}
@dataclass
class Sample:  ...; targets: dict[str, Node] = {}; predictions: dict[str, Node] = {}
```

Everything keys off the `"extraction"` task: `sample.targets["extraction"]` is the document-root `Node`.
A real sample's root has `fields` = `{member_name, member_id, provider, claim_number}` and
`field_groups` = `{claim_line: [Node, …]}`; each record's `fields` are the 10 line columns.

Key facts you will rely on:
- `sample.image` is a URL like `/datasets/<id>/images/0.png` (absolute, points at the dataset). A run that
  copies samples keeps this path, so images resolve through the dataset and `runs/` stays binary-free.
- `artifacts.read_dataset(ds_dir) -> (DatasetManifest, list[Sample])` and
  `artifacts.write_run(runs_dir, RunRecord, list[Sample])` are the existing I/O seams. `write_run` writes
  `run.json` + `samples.json` and upserts `runs/index.json`.
- The viewer dev server (`viewer/vite.config.ts`) serves `/runs/*` and `/datasets/*` straight from the repo
  dirs; `App.tsx` `loadRun(id)` fetches `/runs/<id>/run.json` + `/runs/<id>/samples.json`.
- Leaf `Field.value == " ".join(words[i].text for i in word_ids)`; an absent leaf has `word_ids == []`,
  `value == ""`, and a non-null `cell` (the empty cell). These invariants are asserted in
  `harness/tests/test_targets.py` and must survive perturbation (except the deliberately-broken leaf).

---

## File Structure

**Harness (create / modify):**
- Create `harness/src/tablelab/mock_run.py` — pure perturbation functions over `Node` + a `mock_run`
  orchestrator that reads a dataset and returns `(RunRecord, list[Sample])`.
- Modify `harness/src/tablelab/cli.py` — add the `mock-run` subcommand.
- Create `harness/tests/test_mock_run.py` — perturbation + grounding-validity tests.

**Viewer (create / modify):**
- Modify `viewer/src/types.ts` — add `Field`, `Node`, `TargetPath`; extend `Sample`, `Selection`; drop the
  stale "v4" header comment.
- Create `viewer/src/diff.ts` — `LeafStatus`, `DiffLeaf`, `DiffGroup`, `DiffNode`, the pure `diffNode`, the
  `buildDiff` helper, and `flattenLeaves` (leaf-walk used by both panes). Plus `pathEqual` / `pathKey`.
- Create `viewer/src/diff.test.ts` — vitest unit tests for `diffNode`.
- Modify `viewer/package.json` + `viewer/vite.config.ts` — add vitest, a `test` script, and the test config.
- Modify `viewer/src/MetaPanel.tsx` — a collapsible **Targets** section rendering the `DiffNode` tree, with
  per-leaf status dots and scroll-into-view on `target` selection.
- Modify `viewer/src/DocumentViewer.tsx` — `targets` lens (grounded, diff-colored boxes), `mode` lifted to a
  prop, diff legend entries.
- Modify `viewer/src/App.tsx` — own `mode`, compute nothing (panes derive diff from `sample`), add a
  `selectTarget` handler that switches to the `targets` lens and selects.

---

## Task 1: Harness — perturbation functions over `Node`

**Files:**
- Create: `harness/src/tablelab/mock_run.py`
- Test: `harness/tests/test_mock_run.py`

Pure functions that take a deep-copied target `Node` and return a perturbed `Node` representing a
prediction. Each models one error class from spec §3. We operate on `copy.deepcopy` so targets are never
mutated. "Grounding still valid" means: for every surviving (non-deliberately-broken) leaf,
`value == " ".join(words[i].text for i in word_ids)` and indices are in range.

- [ ] **Step 1: Write the failing test**

```python
# harness/tests/test_mock_run.py
import copy
import random

from tablelab import classes as classlib
from tablelab.artifacts import Field, Node
from tablelab.layout import layout_with_targets
from tablelab import mock_run as mr


def _eob_root(seed=7):
    dc = classlib.get("eob")
    _w, _c, _r, targets = layout_with_targets(dc, random.Random(seed))
    return targets["extraction"]


def test_swap_grounding_points_leaf_at_other_word_ids():
    root = _eob_root()
    pred = mr.swap_grounding(copy.deepcopy(root), random.Random(0))
    # some leaf's word_ids differ from the target's
    tgt_leaves = list(mr._leaves(root))
    pred_leaves = list(mr._leaves(pred))
    changed = [i for i, (a, b) in enumerate(zip(tgt_leaves, pred_leaves))
               if a.word_ids != b.word_ids]
    assert len(changed) == 1


def test_drop_record_shortens_one_group():
    root = _eob_root()
    pred = mr.drop_record(copy.deepcopy(root), random.Random(0))
    assert len(pred.field_groups["claim_line"]) == len(root.field_groups["claim_line"]) - 1


def test_spurious_field_adds_a_leaf_absent_in_target():
    root = _eob_root()
    pred = mr.add_spurious_field(copy.deepcopy(root), random.Random(0))
    extra = set(pred.fields) - set(root.fields)
    assert len(extra) == 1


def test_drop_field_removes_a_leaf_present_in_target():
    root = _eob_root()
    pred = mr.drop_field(copy.deepcopy(root), random.Random(0))
    # a record leaf that existed in target is gone from prediction
    t_rec = root.field_groups["claim_line"][0].fields
    p_rec = pred.field_groups["claim_line"][0].fields
    assert set(p_rec).issubset(set(t_rec)) and len(p_rec) == len(t_rec) - 1


def test_perturb_applies_all_four_and_keeps_grounding(tmp_path):
    root = _eob_root()
    words = [w for w in _words_for("eob")]
    pred = mr.perturb(root, random.Random(0))
    # exactly one leaf is the deliberately-broken (swapped) one; every *other*
    # grounded leaf still satisfies value == join(words[word_ids]).
    bad = 0
    for leaf in mr._leaves(pred):
        if not leaf.word_ids:
            continue
        if leaf.value != " ".join(words[i].text for i in leaf.word_ids):
            bad += 1
    assert bad == 1


def _words_for(dc_name, seed=7):
    dc = classlib.get(dc_name)
    words, _c, _r, _t = layout_with_targets(dc, random.Random(seed))
    return words
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd harness && uv run pytest tests/test_mock_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tablelab.mock_run'`.

- [ ] **Step 3: Write the implementation**

```python
# harness/src/tablelab/mock_run.py
"""Mock-predictions generator: copy a built dataset's targets and inject a few seeded
perturbations so the viewer's first-pass diff has controllable match / missing / spurious /
mismatch cases. This is a placeholder for real model output — runs carry predictions the same
way. See docs/specs/2026-06-20-viewer-targets-diff-spec.md §3."""
from __future__ import annotations
import copy
import random
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .artifacts import Field, Node, RunRecord, Sample, read_dataset, write_run

TASK = "extraction"


def _leaves(node: Node) -> Iterator[Field]:
    """Depth-first over every Field in the tree (root fields, then each record's, recursing)."""
    yield from node.fields.values()
    for recs in node.field_groups.values():
        for r in recs:
            yield from _leaves(r)


def _all_word_ids(node: Node) -> set[int]:
    ids: set[int] = set()
    for leaf in _leaves(node):
        ids.update(leaf.word_ids)
    return ids


def swap_grounding(node: Node, rng: random.Random) -> Node:
    """Point one grounded root leaf at a different leaf's word_ids (value/grounding mismatch)."""
    keys = [k for k, f in node.fields.items() if f.word_ids]
    others = [list(_all_word_ids(node) - set(node.fields[k].word_ids)) for k in keys]
    candidates = [(k, o) for k, o in zip(keys, others) if o]
    if not candidates:
        return node
    k, pool = candidates[rng.randrange(len(candidates))]
    f = node.fields[k]
    node.fields[k] = replace(f, word_ids=[pool[rng.randrange(len(pool))]])
    return node


def drop_record(node: Node, rng: random.Random) -> Node:
    """Remove one record from a non-empty field_group (a missing-record cardinality case)."""
    groups = [g for g, recs in node.field_groups.items() if recs]
    if not groups:
        return node
    g = groups[rng.randrange(len(groups))]
    recs = node.field_groups[g]
    del recs[rng.randrange(len(recs))]
    return node


def add_spurious_field(node: Node, rng: random.Random) -> Node:
    """Add a root leaf absent from the target (a spurious field). Borrows a real word for grounding
    so it still has a plausible box, but its key is new so the diff marks it spurious."""
    name = f"_spurious_{rng.randrange(1000)}"
    pool = sorted(_all_word_ids(node))
    wid = [pool[rng.randrange(len(pool))]] if pool else []
    node.fields[name] = Field(value="?", word_ids=wid, cell=None)
    return node


def drop_field(node: Node, rng: random.Random) -> Node:
    """Drop one leaf from the first record of a field_group (a missing field)."""
    groups = [g for g, recs in node.field_groups.items() if recs and recs[0].fields]
    if not groups:
        return node
    g = groups[rng.randrange(len(groups))]
    rec = node.field_groups[g][0]
    k = list(rec.fields)[rng.randrange(len(rec.fields))]
    del rec.fields[k]
    return node


def perturb(node: Node, rng: random.Random) -> Node:
    """Apply all four perturbations to a deep copy and return it as a prediction Node."""
    pred = copy.deepcopy(node)
    drop_field(pred, rng)        # missing leaf
    add_spurious_field(pred, rng)  # spurious leaf
    drop_record(pred, rng)       # short record list
    swap_grounding(pred, rng)    # value/grounding mismatch (do last; leaves a verifiable single break)
    return pred


def mock_run(dataset_dir: Path, run_id: str, seed: int) -> tuple[RunRecord, list[Sample]]:
    """Read a dataset, inject predictions per sample, and return a synthetic RunRecord + samples.
    Samples keep their `targets` and `image`; only `predictions` is added (runs stay binary-free)."""
    manifest, samples = read_dataset(dataset_dir)
    rng = random.Random(seed)
    out: list[Sample] = []
    for s in samples:
        root = s.targets.get(TASK)
        preds = {TASK: perturb(root, rng)} if root is not None else {}
        out.append(replace(s, predictions=preds))
    record = RunRecord(
        run_id=run_id,
        commit="0000000",
        branch="",
        device="cpu",
        config={"task": TASK, "seed": seed, "generator": "mock-run"},
        metrics={},
        dataset_id=manifest.dataset_id,
        status="mock",
        description=f"mock predictions over {manifest.dataset_id} (seed {seed})",
    )
    return record, out
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd harness && uv run pytest tests/test_mock_run.py -q`
Expected: PASS (5 passed). If `swap_grounding` ever overlaps a dropped/spurious key and the count is off,
re-read the test's `changed`/`bad` accounting — the swap must land on a *root* leaf that survives.

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/mock_run.py harness/tests/test_mock_run.py
git commit -m "feat(mock-run): seeded target perturbations for the prediction diff"
```

---

## Task 2: Harness — `mock-run` CLI subcommand

**Files:**
- Modify: `harness/src/tablelab/cli.py`
- Test: `harness/tests/test_mock_run.py` (add one end-to-end test)

- [ ] **Step 1: Write the failing test (append to `test_mock_run.py`)**

```python
def test_mock_run_writes_a_loadable_run(tmp_path):
    from tablelab.build import build_dataset
    from tablelab.artifacts import read_run
    ds = build_dataset(tmp_path, "mr-eob", classlib.get("eob"), seed=7, n=2)
    record, samples = mr.mock_run(ds, run_id="t-run", seed=1)
    runs_dir = tmp_path / "runs"
    from tablelab.artifacts import write_run
    write_run(runs_dir, record, samples)
    rec2, samples2 = read_run(runs_dir / "t-run")
    assert rec2.status == "mock" and rec2.dataset_id == "mr-eob"
    for s in samples2:
        assert "extraction" in s.predictions          # predictions present
        assert "extraction" in s.targets              # targets preserved
        assert s.image and s.image.startswith("/datasets/")  # binary-free, points at dataset
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd harness && uv run pytest tests/test_mock_run.py::test_mock_run_writes_a_loadable_run -q`
Expected: PASS already (uses only Task 1 + existing I/O) — this asserts the orchestrator before the CLI
wiring. If it fails, fix `mock_run` before wiring the CLI.

- [ ] **Step 3: Add the CLI subcommand**

In `harness/src/tablelab/cli.py`, add the import near the top:

```python
from .mock_run import mock_run as run_mock
from .artifacts import write_run
```

Add a handler above `def main`:

```python
def _mock_run(args):
    ds = Path(args.dataset_dir) / args.dataset
    if args.run_id:
        run_id = args.run_id
    else:
        run_id = f"{ds.name}-mock-{args.seed}"
    record, samples = run_mock(ds, run_id=run_id, seed=args.seed)
    out = write_run(Path(args.runs_dir), record, samples)
    print(f"wrote mock run {run_id} ({len(samples)} samples) -> {out}")
```

Register it inside `main`, after the `inspect` parser block:

```python
    mk = sub.add_parser("mock-run", help="inject mock predictions over a dataset into a run")
    mk.add_argument("--dataset", required=True, help="dataset id under --dataset-dir")
    mk.add_argument("--dataset-dir", default="../datasets")
    mk.add_argument("--runs-dir", default="../runs")
    mk.add_argument("--run-id", default=None, help="run id (default: <dataset>-mock-<seed>)")
    mk.add_argument("--seed", type=int, default=1)
    mk.set_defaults(fn=_mock_run)
```

- [ ] **Step 4: Exercise it end-to-end (verify by running)**

```bash
cd harness
uv run python -m tablelab.cli build --class eob --n 4 --out ../datasets/eob-diff
uv run python -m tablelab.cli mock-run --dataset eob-diff --seed 1
cat ../runs/eob-diff-mock-1/run.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d['dataset_id'])"
```

Expected: `built 4 eob samples -> ../datasets/eob-diff`, then `wrote mock run eob-diff-mock-1 (4 samples) -> …`,
then `mock eob-diff`. Confirm `runs/index.json` gained the entry and `runs/eob-diff-mock-1/` holds no `.png`.

- [ ] **Step 5: Run the full harness suite, then commit**

```bash
cd harness && uv run pytest -q
git add harness/src/tablelab/cli.py harness/tests/test_mock_run.py
git commit -m "feat(cli): mock-run subcommand writes a prediction run"
```

Note: `datasets/eob-diff/` is gitignored (local). The `runs/eob-diff-mock-1/` dir is git-tracked and
binary-free — leave it staged-but-uncommitted for now; it is the viewer verification fixture (Task 9). Do
not commit dataset images.

---

## Task 3: Viewer — v5 contract types

**Files:**
- Modify: `viewer/src/types.ts`

- [ ] **Step 1: Replace the stale header + add target types**

Change the top comment line 1 from the v4 wording to:

```ts
// ---- Artifact schema types (mirrors runs/ and datasets/ JSON contract v5) ----
```

Add, after the `Cell` interface block (keep near the other artifact types):

```ts
// ---- Targets / predictions (contract v5) ----

export interface Field {
  value: string
  word_ids: number[]
  cell: number | null
}

export interface Node {
  fields: Record<string, Field>
  field_groups: Record<string, Node[]>
}

// A path from the document root to one leaf, e.g.
// ['field_groups','claim_line',2,'fields','amount_owed'].
export type TargetPath = (string | number)[]
```

- [ ] **Step 2: Extend `Sample` and `Selection`**

In `Sample`, add after `regions?: Region[]`:

```ts
  targets?: Record<string, Node>
  predictions?: Record<string, Node>
```

Replace the `Selection` union with:

```ts
export type Selection =
  | { kind: 'word'; index: number }
  | { kind: 'cell'; index: number }
  | { kind: 'region'; index: number }
  | { kind: 'target'; path: TargetPath }
```

- [ ] **Step 3: Typecheck**

Run: `npm --prefix viewer run build`
Expected: PASS (no type errors). `DocumentViewer.tsx`'s `sameSelection` compares `a.index === b.index`;
adding the `target` variant won't break compilation because `index` access is guarded by `kind` checks at
call sites — but if `tsc` flags `sameSelection`, leave it; Task 7 rewrites it. If the build is clean, proceed.

- [ ] **Step 4: Commit**

```bash
git add viewer/src/types.ts
git commit -m "feat(viewer-types): contract v5 Field/Node/TargetPath + target selection"
```

---

## Task 4: Viewer — add vitest

**Files:**
- Modify: `viewer/package.json`, `viewer/vite.config.ts`

- [ ] **Step 1: Install vitest**

```bash
npm --prefix viewer install -D vitest@^3
```

- [ ] **Step 2: Add a `test` script**

In `viewer/package.json` `"scripts"`, add:

```json
    "test": "vitest run",
```

- [ ] **Step 3: Add the test config to `vite.config.ts`**

At the top, add the triple-slash reference as the **first line** of the file:

```ts
/// <reference types="vitest/config" />
```

In the `defineConfig({ … })` object, add a `test` key (sibling of `plugins`):

```ts
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
```

- [ ] **Step 4: Sanity-check the runner with a throwaway test**

```bash
printf "import { expect, test } from 'vitest'\ntest('sanity', () => expect(1 + 1).toBe(2))\n" > viewer/src/_sanity.test.ts
npm --prefix viewer test
rm viewer/src/_sanity.test.ts
```

Expected: `1 passed`. Then the file is removed.

- [ ] **Step 5: Commit**

```bash
git add viewer/package.json viewer/package-lock.json viewer/vite.config.ts
git commit -m "chore(viewer): add vitest for pure-function unit tests"
```

---

## Task 5: Viewer — `diffNode` matcher + helpers (TDD)

**Files:**
- Create: `viewer/src/diff.ts`
- Test: `viewer/src/diff.test.ts`

This is the pure-function seam (spec §4). `diffNode(target?, pred?)` returns a `DiffNode` mirroring `Node`
where each leaf carries a `LeafStatus` plus both sides' `Field`, and each group carries a record-count
`delta` (pred − target). Records align by index. `buildDiff(sample)` wraps it for the `"extraction"` task
and reports whether predictions exist. `flattenLeaves` is the shared leaf-walk both panes use.

- [ ] **Step 1: Write the failing tests**

```ts
// viewer/src/diff.test.ts
import { describe, expect, test } from 'vitest'
import type { Field, Node } from './types'
import { buildDiff, diffNode, flattenLeaves, pathKey } from './diff'

const f = (value: string, word_ids: number[], cell = 0): Field => ({ value, word_ids, cell })

test('match: same word_ids', () => {
  const t: Node = { fields: { a: f('x', [1, 2]) }, field_groups: {} }
  const p: Node = { fields: { a: f('x', [2, 1]) }, field_groups: {} }   // set-equal
  expect(diffNode(t, p).fields.a.status).toBe('match')
})

test('mismatch: different word_ids', () => {
  const t: Node = { fields: { a: f('x', [1, 2]) }, field_groups: {} }
  const p: Node = { fields: { a: f('y', [3]) }, field_groups: {} }
  const leaf = diffNode(t, p).fields.a
  expect(leaf.status).toBe('mismatch')
  expect(leaf.target?.value).toBe('x')
  expect(leaf.pred?.value).toBe('y')
})

test('missing: leaf in target only', () => {
  const t: Node = { fields: { a: f('x', [1]) }, field_groups: {} }
  const p: Node = { fields: {}, field_groups: {} }
  expect(diffNode(t, p).fields.a.status).toBe('missing')
})

test('spurious: leaf in prediction only', () => {
  const t: Node = { fields: {}, field_groups: {} }
  const p: Node = { fields: { a: f('x', [1]) }, field_groups: {} }
  expect(diffNode(t, p).fields.a.status).toBe('spurious')
})

test('record cardinality delta: pred shorter', () => {
  const rec = (): Node => ({ fields: { a: f('x', [1]) }, field_groups: {} })
  const t: Node = { fields: {}, field_groups: { g: [rec(), rec()] } }
  const p: Node = { fields: {}, field_groups: { g: [rec()] } }
  const d = diffNode(t, p)
  expect(d.field_groups.g.delta).toBe(-1)
  expect(d.field_groups.g.records).toHaveLength(2)        // aligned to the longer side
  expect(d.field_groups.g.records[1].fields.a.status).toBe('missing')  // unmatched target record
})

test('buildDiff: no predictions → showDiff false but tree present', () => {
  const sample = { targets: { extraction: { fields: { a: f('x', [1]) }, field_groups: {} } } } as never
  const { diff, showDiff } = buildDiff(sample)
  expect(showDiff).toBe(false)
  expect(Object.keys(diff.fields)).toEqual(['a'])
})

test('flattenLeaves: paths and grounding field', () => {
  const t: Node = {
    fields: { g0: f('G', [9]) },
    field_groups: { line: [{ fields: { a: f('x', [1]) }, field_groups: {} }] },
  }
  const leaves = flattenLeaves(diffNode(t, undefined))
  const keys = leaves.map(l => pathKey(l.path))
  expect(keys).toContain('fields/g0')
  expect(keys).toContain('field_groups/line/0/fields/a')
  const a = leaves.find(l => pathKey(l.path) === 'field_groups/line/0/fields/a')!
  expect(a.field.word_ids).toEqual([1])   // grounds on target Field
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm --prefix viewer test`
Expected: FAIL — cannot resolve `./diff`.

- [ ] **Step 3: Implement `diff.ts`**

```ts
// viewer/src/diff.ts
// First-pass, grounding-keyed prediction diff (spec §4). The whole matcher is one pure
// function so the future real metric (spec §7) replaces *it*, not the UI.
import type { Field, Node, Sample, TargetPath } from './types'

const TASK = 'extraction'

export type LeafStatus = 'match' | 'mismatch' | 'missing' | 'spurious'

export interface DiffLeaf {
  status: LeafStatus
  target?: Field
  pred?: Field
}

export interface DiffGroup {
  records: DiffNode[]   // aligned by index to max(target, pred) length
  delta: number         // pred record count − target record count
}

export interface DiffNode {
  fields: Record<string, DiffLeaf>
  field_groups: Record<string, DiffGroup>
}

function sameWordIds(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false
  const set = new Set(a)
  return b.every(x => set.has(x))
}

function diffLeaf(target: Field | undefined, pred: Field | undefined): DiffLeaf {
  if (target && pred) {
    return { status: sameWordIds(target.word_ids, pred.word_ids) ? 'match' : 'mismatch', target, pred }
  }
  if (target) return { status: 'missing', target }
  return { status: 'spurious', pred }
}

export function diffNode(target: Node | undefined, pred: Node | undefined): DiffNode {
  const fields: Record<string, DiffLeaf> = {}
  const fieldKeys = new Set([...Object.keys(target?.fields ?? {}), ...Object.keys(pred?.fields ?? {})])
  for (const k of fieldKeys) {
    fields[k] = diffLeaf(target?.fields[k], pred?.fields[k])
  }

  const field_groups: Record<string, DiffGroup> = {}
  const groupKeys = new Set([
    ...Object.keys(target?.field_groups ?? {}),
    ...Object.keys(pred?.field_groups ?? {}),
  ])
  for (const g of groupKeys) {
    const tRecs = target?.field_groups[g] ?? []
    const pRecs = pred?.field_groups[g] ?? []
    const n = Math.max(tRecs.length, pRecs.length)
    const records: DiffNode[] = []
    for (let i = 0; i < n; i++) records.push(diffNode(tRecs[i], pRecs[i]))
    field_groups[g] = { records, delta: pRecs.length - tRecs.length }
  }

  return { fields, field_groups }
}

export function buildDiff(sample: Sample): { diff: DiffNode; showDiff: boolean } {
  const target = sample.targets?.[TASK]
  const pred = sample.predictions?.[TASK]
  return { diff: diffNode(target, pred), showDiff: pred != null }
}

// ---- Leaf walk (shared by tree + lens) ----

export interface FlatLeaf {
  path: TargetPath
  status: LeafStatus
  field: Field           // the Field to ground on: target for match/mismatch/missing, pred for spurious
  target?: Field
  pred?: Field
}

export function flattenLeaves(diff: DiffNode, base: TargetPath = []): FlatLeaf[] {
  const out: FlatLeaf[] = []
  for (const [k, leaf] of Object.entries(diff.fields)) {
    const field = leaf.status === 'spurious' ? leaf.pred! : leaf.target!
    out.push({ path: [...base, 'fields', k], status: leaf.status, field, target: leaf.target, pred: leaf.pred })
  }
  for (const [g, group] of Object.entries(diff.field_groups)) {
    group.records.forEach((rec, i) => {
      out.push(...flattenLeaves(rec, [...base, 'field_groups', g, i]))
    })
  }
  return out
}

export function pathKey(path: TargetPath): string {
  return path.join('/')
}

export function pathEqual(a: TargetPath, b: TargetPath): boolean {
  return a.length === b.length && a.every((x, i) => x === b[i])
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm --prefix viewer test`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add viewer/src/diff.ts viewer/src/diff.test.ts
git commit -m "feat(viewer-diff): pure grounding-keyed diffNode + leaf-walk helpers"
```

---

## Task 6: Viewer — Targets tree in `MetaPanel`

**Files:**
- Modify: `viewer/src/MetaPanel.tsx`
- Modify: `viewer/src/App.css` (status-dot styles)

Render the `DiffNode` as a collapsible tree: root `fields` first, then each `field_groups` name → an ordered
list of records (each its own `fields`, recursing). Each leaf row shows `field: value`; when predictions
exist, a status dot and `target → pred` on a mismatch. Group headers show the record-count delta when
nonzero. Clicking a leaf selects it; the selected row scrolls into view.

- [ ] **Step 1: Add props to `MetaPanel` and import the diff helpers**

Replace the import line and `Props`:

```tsx
import { useEffect, useRef, type ReactNode } from 'react'
import type { ActiveSource, Cell, LabelValue, Region, Sample, Selection, TargetPath } from './types'
import { buildDiff, pathEqual, pathKey, type DiffLeaf, type DiffNode, type LeafStatus } from './diff'

interface Props {
  source: ActiveSource | null
  task?: string
  selection: Selection | null
  sample: Sample | null
  onSelectTarget: (path: TargetPath) => void
}
```

Update the default export signature:

```tsx
export default function MetaPanel({ source, task: _task, selection, sample, onSelectTarget }: Props) {
```

- [ ] **Step 2: Add the status-color helper + a TargetsTree component (above `MetaPanel`)**

```tsx
// Diff status → swatch color. Mirrors DocumentViewer's lens palette: green match, red
// missing/mismatch, amber spurious. (Kept in sync by eye; both are first-pass.)
const STATUS_COLOR: Record<LeafStatus, string> = {
  match: '#16A34A',
  mismatch: '#DC2626',
  missing: '#DC2626',
  spurious: '#D97706',
}

function LeafRow({ name, leaf, path, showDiff, selected, onSelect, rowRef }: {
  name: string; leaf: DiffLeaf; path: TargetPath; showDiff: boolean
  selected: boolean; onSelect: (p: TargetPath) => void
  rowRef: (el: HTMLDivElement | null) => void
}) {
  const value = (leaf.target ?? leaf.pred)?.value ?? ''
  const mismatch = showDiff && leaf.status === 'mismatch'
  return (
    <div
      ref={rowRef}
      className={`target-leaf${selected ? ' is-selected' : ''}`}
      onClick={() => onSelect(path)}
    >
      {showDiff && <span className="target-dot" style={{ background: STATUS_COLOR[leaf.status] }} />}
      <span className="target-leaf-name mono">{name}</span>
      <span className="target-leaf-value mono">
        {mismatch
          ? `${leaf.target?.value ?? '∅'} → ${leaf.pred?.value ?? '∅'}`
          : (value === '' ? '∅' : value)}
      </span>
    </div>
  )
}

function TargetsTree({ node, base, showDiff, selection, onSelect, registerRow }: {
  node: DiffNode; base: TargetPath; showDiff: boolean
  selection: Selection | null
  onSelect: (p: TargetPath) => void
  registerRow: (key: string, el: HTMLDivElement | null) => void
}) {
  return (
    <div className="targets-tree">
      {Object.entries(node.fields).map(([name, leaf]) => {
        const path: TargetPath = [...base, 'fields', name]
        const selected = selection?.kind === 'target' && pathEqual(selection.path, path)
        return (
          <LeafRow key={pathKey(path)} name={name} leaf={leaf} path={path} showDiff={showDiff}
            selected={selected} onSelect={onSelect}
            rowRef={el => registerRow(pathKey(path), el)} />
        )
      })}
      {Object.entries(node.field_groups).map(([g, group]) => (
        <div className="target-group" key={g}>
          <div className="target-group-header mono">
            {g} <span className="target-group-count">[{group.records.length}]</span>
            {showDiff && group.delta !== 0 && (
              <span className="target-group-delta" style={{ color: STATUS_COLOR[group.delta > 0 ? 'spurious' : 'missing'] }}>
                {group.delta > 0 ? `+${group.delta}` : group.delta}
              </span>
            )}
          </div>
          {group.records.map((rec, i) => (
            <div className="target-record" key={i}>
              <div className="target-record-label mono">#{i}</div>
              <TargetsTree node={rec} base={[...base, 'field_groups', g, i]} showDiff={showDiff}
                selection={selection} onSelect={onSelect} registerRow={registerRow} />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Render the Targets section + scroll-into-view (inside `MetaPanel`, before the closing `</div>`)**

Add this hook + row-registry at the top of the `MetaPanel` body (just after the function opens):

```tsx
  const rowRefs = useRef(new Map<string, HTMLDivElement | null>())
  const registerRow = (key: string, el: HTMLDivElement | null) => { rowRefs.current.set(key, el) }

  useEffect(() => {
    if (selection?.kind !== 'target') return
    const el = rowRefs.current.get(pathKey(selection.path))
    el?.scrollIntoView({ block: 'nearest' })
  }, [selection])

  const targetRoot = sample?.targets?.extraction
  const diffResult = sample ? buildDiff(sample) : null
```

Add the section just before the final `</div>` that closes `.meta-panel` (after the Selection section):

```tsx
      {targetRoot && diffResult && (
        <section className="meta-section targets-section">
          <div className="meta-section-title">Targets{diffResult.showDiff ? ' · diff' : ''}</div>
          <TargetsTree
            node={diffResult.diff}
            base={[]}
            showDiff={diffResult.showDiff}
            selection={selection}
            onSelect={onSelectTarget}
            registerRow={registerRow}
          />
        </section>
      )}
```

- [ ] **Step 4: Add styles to `App.css`**

Append:

```css
/* ---- Targets tree (right pane) ---- */
.targets-tree { display: flex; flex-direction: column; gap: 2px; }
.target-leaf {
  display: flex; align-items: center; gap: 6px; padding: 2px 4px;
  border-radius: 4px; cursor: pointer; font-size: 0.8rem;
}
.target-leaf:hover { background: rgba(10, 14, 22, 0.05); }
.target-leaf.is-selected { background: rgba(255, 20, 147, 0.14); }
.target-dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }
.target-leaf-name { color: #555; flex: 0 0 auto; }
.target-leaf-value { color: #111; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.target-group { margin: 6px 0 2px; }
.target-group-header { font-size: 0.78rem; color: #333; display: flex; gap: 6px; align-items: baseline; }
.target-group-count { color: #999; }
.target-group-delta { font-weight: 600; }
.target-record { border-left: 2px solid rgba(10, 14, 22, 0.12); margin-left: 4px; padding-left: 8px; margin-top: 4px; }
.target-record-label { font-size: 0.72rem; color: #aaa; }
```

- [ ] **Step 5: Typecheck (App.tsx will error until Task 8 — verify MetaPanel compiles in isolation)**

Run: `npm --prefix viewer run build`
Expected: ONE expected error — `App.tsx` does not yet pass `onSelectTarget` to `MetaPanel`. That is wired in
Task 8. If MetaPanel itself has type errors (anything in `MetaPanel.tsx` or `diff.ts`), fix them now.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/MetaPanel.tsx viewer/src/App.css
git commit -m "feat(viewer-meta): render target/diff tree with status dots"
```

---

## Task 7: Viewer — Targets lens + cross-highlight in `DocumentViewer`

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`

Add a `targets` overlay lens that grounds each leaf (member-word boxes, or a faint placeholder at the empty
`cell`), diff-colored when predictions exist. Lift `mode` to a prop so the parent can switch to the lens
when a tree leaf is clicked. Make `sameSelection` path-aware. Clicking a lens box selects the tree leaf.

- [ ] **Step 1: Update imports, palette, modes, and `Props`**

Replace the type import + add diff imports:

```tsx
import type { Sample, Selection, TargetPath } from './types'
import { buildDiff, flattenLeaves, pathEqual, type FlatLeaf, type LeafStatus } from './diff'
```

Extend the palette (after `COLOR_SELECTED`):

```tsx
// Diff palette for the targets lens — mirrors MetaPanel's STATUS_COLOR.
const DIFF_COLOR: Record<LeafStatus, string> = {
  match: TIER.primary, mismatch: '#DC2626', missing: '#DC2626', spurious: '#D97706',
}
```

Add `'targets'` to the `ViewMode` union and the `MODES` list (append after `'regions'`):

```tsx
type ViewMode = 'none' | 'words' | 'composed' | 'cells' | 'keyvalue' | 'regions' | 'targets'
```
```tsx
  ['regions', 'Regions'],
  ['targets', 'Targets'],
```

Add a `targets` entry to `LEGEND` (the default, no-diff form):

```tsx
  regions: [['region', TIER.primary]],
  targets: [['target', TIER.primary]],
```

Replace `Props` and the component signature to make `mode` controlled:

```tsx
interface Props {
  samples: Sample[]
  task?: string
  selection: Selection | null
  onSelect: (selection: Selection | null) => void
  onSampleChange?: (idx: number) => void
  mode: ViewMode
  onModeChange: (mode: ViewMode) => void
}

export default function DocumentViewer({
  samples, task: _task, selection, onSelect, onSampleChange, mode, onModeChange,
}: Props) {
```

Delete the local `const [mode, setMode] = useState<ViewMode>('none')` line.

- [ ] **Step 2: Make `sameSelection` path-aware and rewrite `changeMode`**

Replace `sameSelection`:

```tsx
function sameSelection(a: Selection | null, b: Selection | null): boolean {
  if (a == null || b == null || a.kind !== b.kind) return false
  if (a.kind === 'target' && b.kind === 'target') return pathEqual(a.path, b.path)
  return 'index' in a && 'index' in b && a.index === b.index
}
```

Replace `changeMode` (it now defers to the parent, which clears selection):

```tsx
  const changeMode = useCallback((next: ViewMode) => {
    onModeChange(next)   // parent owns mode + clears selection on a toolbar switch
  }, [onModeChange])
```

- [ ] **Step 3: Compute the diff for the active sample**

After `const allCells = cells ?? []` (near line 405), add:

```tsx
  const { diff, showDiff } = buildDiff(sample)
  const targetLeaves: FlatLeaf[] = mode === 'targets' ? flattenLeaves(diff) : []
```

- [ ] **Step 4: Render the targets lens (add inside `<svg>`, after the words-lens block)**

```tsx
            {/* Targets lens — each leaf grounded by its member-word boxes (or a faint
                placeholder at its empty cell), diff-colored when predictions exist. */}
            {mode === 'targets' && targetLeaves.map(leaf => {
              const sel = selection?.kind === 'target' && pathEqual(selection.path, leaf.path)
              const color = sel ? COLOR_SELECTED : (showDiff ? DIFF_COLOR[leaf.status] : TIER.primary)
              const key = leaf.path.join('-')
              const onClick = () => handleSelect({ kind: 'target', path: leaf.path })
              if (leaf.field.word_ids.length > 0) {
                return leaf.field.word_ids.map(wid => {
                  const w = words[wid]
                  return w == null ? null : (
                    <OverlayBox key={`tgt-${key}-${wid}`} bbox={[w.x0, w.y0, w.x1, w.y1]}
                      pw={width} ph={height} color={color} width={sel ? 2 : 1.25} onClick={onClick} />
                  )
                })
              }
              // absent leaf: faint dashed placeholder at the empty cell, if any
              const c = leaf.field.cell != null ? allCells[leaf.field.cell] : undefined
              return c == null ? null : (
                <OverlayBox key={`tgt-${key}-empty`} bbox={c.bbox} pw={width} ph={height}
                  color={sel ? COLOR_SELECTED : '#bbb'} width={1} dashed onClick={onClick} />
              )
            })}
```

- [ ] **Step 5: Make the legend diff-aware for the targets lens**

Replace the legend body (the `mode === 'none' ? … : …` block) with:

```tsx
        {mode === 'none' ? (
          <span className="legend-hint">Pick a view mode to overlay structure.</span>
        ) : (
          (mode === 'targets' && showDiff
            ? [['match', DIFF_COLOR.match], ['missing/mismatch', DIFF_COLOR.missing], ['spurious', DIFF_COLOR.spurious]] as [string, string][]
            : [...LEGEND[mode], ['selected', COLOR_SELECTED] as [string, string]]
          ).map(([label, color]) => (
            <span className="legend-item" key={label}>
              <span className="legend-swatch" style={{ background: color, borderColor: 'rgba(10,14,22,0.55)' }} /> {label}
            </span>
          ))
        )}
```

- [ ] **Step 6: Typecheck (App.tsx still expects the old props — error expected)**

Run: `npm --prefix viewer run build`
Expected: errors only in `App.tsx` (missing `mode`/`onModeChange` props, missing `onSelectTarget` for
MetaPanel). `DocumentViewer.tsx` itself must be clean. Fix any DocumentViewer-local errors now.

- [ ] **Step 7: Commit**

```bash
git add viewer/src/DocumentViewer.tsx
git commit -m "feat(viewer-lens): grounded targets lens with diff coloring"
```

---

## Task 8: Viewer — wire `App` (controlled mode + cross-pane select)

**Files:**
- Modify: `viewer/src/App.tsx`

`App` owns `mode`. A toolbar switch clears selection; clicking a tree leaf switches to the `targets` lens and
selects (without the clear). Pass `onSelectTarget` to `MetaPanel`, `mode`/`onModeChange` to `DocumentViewer`.

- [ ] **Step 1: Add the `ViewMode` type + `mode`/selectTarget state**

`DocumentViewer` does not export `ViewMode`; declare a matching alias in `App.tsx` near the top:

```tsx
type ViewMode = 'none' | 'words' | 'composed' | 'cells' | 'keyvalue' | 'regions' | 'targets'
```

Add to the imports from `./types`: `TargetPath`. Inside the component, add state next to `selection`:

```tsx
  const [mode, setMode] = useState<ViewMode>('none')
```

Add handlers after the `loadRun` function:

```tsx
  function handleModeChange(next: ViewMode) {
    setMode(next)
    setSelection(null)   // a selection from one lens doesn't carry to another
  }

  function selectTarget(path: TargetPath) {
    setMode('targets')                       // ensure the leaf's box is visible
    setSelection({ kind: 'target', path })   // (no clear — this is a cross-pane focus)
  }
```

Reset `mode` is not needed on source change (selection already clears); leave existing `loadDataset`/
`loadRun` as-is.

- [ ] **Step 2: Pass the new props through**

Update the `DocumentViewer` element:

```tsx
            <DocumentViewer
              samples={samples}
              task={task}
              selection={selection}
              onSelect={setSelection}
              onSampleChange={setSampleIdx}
              mode={mode}
              onModeChange={handleModeChange}
            />
```

Update the `MetaPanel` element:

```tsx
          <MetaPanel
            source={activeSource}
            task={task}
            selection={selection}
            sample={activeSample}
            onSelectTarget={selectTarget}
          />
```

- [ ] **Step 3: Full typecheck/build**

Run: `npm --prefix viewer run build`
Expected: PASS (clean build, no errors).

- [ ] **Step 4: Commit**

```bash
git add viewer/src/App.tsx
git commit -m "feat(viewer-app): own overlay mode; cross-pane target focus"
```

---

## Task 9: End-to-end verification (spec §8)

**Files:** none (verification only). Uses the `datasets/eob-diff` + `runs/eob-diff-mock-1` from Task 2.

- [ ] **Step 1: Ensure the fixture exists**

```bash
cd harness
uv run python -m tablelab.cli build --class eob --n 4 --out ../datasets/eob-diff
uv run python -m tablelab.cli mock-run --dataset eob-diff --seed 1
```

- [ ] **Step 2: Run the full suites**

```bash
cd harness && uv run pytest -q          # all green, incl. test_mock_run.py
npm --prefix viewer test                # diff.test.ts green
npm --prefix viewer run build           # clean tsc + vite build
```

- [ ] **Step 3: Verify in the running viewer (preview tools)**

Start the dev server (`npm --prefix viewer run dev`, or preview_start) and confirm against spec §8:
1. Select **dataset `eob-diff`** → Targets section renders the tree (globals, then `claim_line` records);
   switch the left lens to **Targets** → leaves ground on the page; **no** status dots (plain dataset).
2. Select **run `eob-diff-mock-1`** → the same tree now shows status dots; the seeded perturbations appear
   as **missing** (dropped field), **spurious** (`_spurious_*`), a **record-count delta** on `claim_line`,
   and a **mismatch** (`target → pred`) on one global.
3. With the Targets lens active, **click a tree leaf** → its box highlights pink on the page; **click a box**
   → the matching tree row highlights and scrolls into view.

Capture a screenshot of the run view (tree + diff-colored lens) as proof.

- [ ] **Step 4: Commit the viewer fixture run**

The dataset (`datasets/eob-diff`) is gitignored; the run is tracked and binary-free:

```bash
git add runs/eob-diff-mock-1 runs/index.json
git commit -m "test(fixture): mock-run over eob for the viewer diff demo"
```

---

## Self-Review — spec coverage

| Spec section | Task(s) |
|---|---|
| §2 Data model (`types.ts` → v5, optional `targets`/`predictions`) | Task 3 |
| §3 Mock-predictions generator (4 perturbations, `mock-run`, binary-free run) | Tasks 1, 2 |
| §4 Diff — pure `diffNode`, 4 statuses, record-count delta, swappable seam | Task 5 |
| §4 Colors (TIER match, red missing/mismatch, amber spurious) + legend | Tasks 6, 7 |
| §5 Right pane target/diff tree (globals first, records, `name: value`, deltas, click-select) | Task 6 |
| §6 Left pane Targets lens, grounded boxes, empty-leaf placeholder, bidirectional select + scroll | Tasks 7, 8, 6 |
| §7 Out of scope (real metric / predictions / alignment) | n/a — deliberately not built |
| §8 Verification (build → mock-run → load; unit tests for `diffNode` + generator) | Tasks 1, 5, 9 |
