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
    """Point one grounded root leaf at a different leaf's word_ids (value/grounding mismatch).
    Only picks from leaves that are genuinely grounded (non-empty value, not the spurious
    sentinel "?") so the swap is the sole broken leaf in the perturbed prediction."""
    keys = [k for k, f in node.fields.items() if f.word_ids and f.value and f.value != "?"]
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
    """Add a root leaf absent from the target (a spurious field). Uses empty word_ids so it
    doesn't pollute the grounding pool or the bad-leaf count in tests; its key being absent
    from the target is what makes the diff mark it spurious."""
    name = f"_spurious_{rng.randrange(1000)}"
    node.fields[name] = Field(value="?", word_ids=[], cell=None)
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
