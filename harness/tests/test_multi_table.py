from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _instanced(n_lo, n_hi, **structure):
    dc = classlib.get("invoice")
    tables = tuple(replace(t, instances=(n_lo, n_hi)) for t in dc.tables)
    return fork(dc, tables=tables, structure=replace(dc.structure, **structure))


def test_single_instance_has_no_region():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all("region" not in p.label for p in placed if p.label)


def test_multiple_instances_label_region_contiguous():
    placed = layout(_instanced(2, 2), random.Random(7))
    regions = sorted({p.label["region"] for p in placed if p.label})
    assert regions == [0, 1]
    # records restart per instance (each region is its own table)
    by_region = defaultdict(set)
    for p in placed:
        if p.label:
            by_region[p.label["region"]].add(p.label.get("record"))
    assert all(0 in records for records in by_region.values())


def test_instances_stacked_vertically():
    placed = layout(_instanced(2, 2), random.Random(7))
    r0 = [p for p in placed if p.label and p.label.get("region") == 0]
    r1 = [p for p in placed if p.label and p.label.get("region") == 1]
    assert max(p.cell[3] for p in r0) <= min(p.cell[1] for p in r1) + 1


def test_instances_render_all_boxes_set():
    dc = _instanced(2, 3)
    placed = layout(dc, random.Random(7))
    _img, boxes = render(placed, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)
    region_count = len({p.label["region"] for p in placed if p.label})
    assert 2 <= region_count <= 3


def test_instances_compose_with_header_and_region():
    placed = layout(_instanced(2, 2, header=True), random.Random(7))
    # each instance's header tokens carry that region
    hdr = [p for p in placed if p.label and p.label.get("header")]
    assert sorted({p.label["region"] for p in hdr}) == [0, 1]


def test_instances_compose_with_multi_token():
    placed = layout(_instanced(2, 2, multi_token=True), random.Random(7))
    # a split data word carries region + record + field + seq together
    words = [p for p in placed if p.label and "seq" in p.label and "record" in p.label]
    assert words
    assert {"region", "record", "field", "seq"}.issubset(words[0].label.keys())
