from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _multi_invoice():
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, multi_token=True))


def _groups(placed):
    g = defaultdict(list)
    for p in placed:
        g[(p.label["record"], p.label["field"])].append(p)
    return g


def test_multiword_cells_split_with_contiguous_seq():
    placed = layout(_multi_invoice(), random.Random(7))
    groups = _groups(placed)
    # at least one cell (a multi-word description) split into >1 token
    assert any(len(v) > 1 for v in groups.values())
    # every cell's tokens carry contiguous seq 0..n-1 (single-word cells get seq 0)
    for toks in groups.values():
        seqs = sorted(p.label["seq"] for p in toks)
        assert seqs == list(range(len(toks)))


def test_multiword_boxes_in_cell_disjoint_and_anchored():
    dc = _multi_invoice()
    rng = random.Random(7)
    placed = layout(dc, rng)
    _img, boxes = render(placed, dc)
    box_of = {id(p): b for p, b in zip(placed, boxes)}

    multiword_seen = False
    for toks in _groups(placed).values():
        if len(toks) < 2:
            continue
        multiword_seen = True
        toks = sorted(toks, key=lambda p: p.label["seq"])
        cx0, cy0, cx1, cy1 = toks[0].cell
        align = toks[0].align
        bxs = [box_of[id(p)] for p in toks]
        # vertically inside the row
        for b in bxs:
            assert cy0 - 1 <= b[1] and b[3] <= cy1 + 1
        # left-to-right, non-overlapping
        for a, b in zip(bxs, bxs[1:]):
            assert b[0] >= a[2] - 1
        # anchored to the correct cell edge by alignment
        if align == "right":
            assert bxs[-1][2] <= cx1 + 1
        else:
            assert bxs[0][0] >= cx0 - 1
    assert multiword_seen  # the fixture actually exercised the multi-word path
