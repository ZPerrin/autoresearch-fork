from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, cells_where, text_of


def _multi_invoice():
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, multi_token=True))


def test_multiword_cells_split_with_contiguous_seq():
    dc = _multi_invoice()
    tokens, cells, _regions = placed(dc, seed=7)
    data_cells = cells_where(cells, role="data")

    # at least one data cell (a multi-word description) has multiple token_ids
    assert any(len(c.token_ids) > 1 for c in data_cells)

    # for every data cell, the token_ids are in contiguous reading order (seq 0..n-1)
    # PlacedToken.seq is the within-cell word index; tokens within a cell are already
    # ordered by their seq (emit order) so token_ids[k] should correspond to word k.
    for c in data_cells:
        if len(c.token_ids) > 1:
            seqs = [tokens[i].seq for i in c.token_ids]
            assert seqs == list(range(len(seqs)))


def test_multiword_boxes_in_cell_disjoint_and_anchored():
    dc = _multi_invoice()
    rng = random.Random(7)
    tokens, cells, _regions = placed(dc, seed=7)
    # use layout()+render() for pixel box lookup
    p_tokens = layout(dc, rng)
    _img, boxes = render(p_tokens, dc)

    multiword_seen = False
    for c in cells_where(cells, role="data"):
        if len(c.token_ids) < 2:
            continue
        multiword_seen = True
        tids = c.token_ids  # already in reading order (seq 0, 1, ...)
        cx0, cy0, cx1, cy1 = tokens[tids[0]].cell
        align = tokens[tids[0]].align
        bxs = [boxes[i] for i in tids]
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
