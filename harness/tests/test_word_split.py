from __future__ import annotations

import random

from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, cells_where


def test_every_word_is_space_free():
    # The consistency guarantee: every emitted observable is a single OCR-style word.
    for cls in ("invoice", "eob", "receipt"):
        tokens, _cells, _regions = placed(classlib.get(cls), seed=7)
        assert all(" " not in (t.text or "") for t in tokens), cls


def test_multiword_cells_split_with_contiguous_seq():
    # No flag involved: multi-word cells (invoice descriptions) emit one word per
    # word, in contiguous within-cell reading order.
    tokens, cells, _regions = placed(classlib.get("invoice"), seed=7)
    data_cells = cells_where(cells, role="data")
    assert any(len(c.word_ids) > 1 for c in data_cells)
    for c in data_cells:
        if len(c.word_ids) > 1:
            seqs = [tokens[i].seq for i in c.word_ids]
            assert seqs == list(range(len(seqs)))


def test_multiword_boxes_in_cell_disjoint_and_anchored():
    dc = classlib.get("invoice")
    rng = random.Random(7)
    tokens, cells, _regions = placed(dc, seed=7)
    p_tokens = layout(dc, rng)
    _img, boxes = render(p_tokens, dc)

    multiword_seen = False
    for c in cells_where(cells, role="data"):
        if len(c.word_ids) < 2:
            continue
        multiword_seen = True
        tids = c.word_ids
        cx0, cy0, cx1, cy1 = tokens[tids[0]].cell
        align = tokens[tids[0]].align
        bxs = [boxes[i] for i in tids]
        for b in bxs:
            assert cy0 - 1 <= b[1] and b[3] <= cy1 + 1
        for a, b in zip(bxs, bxs[1:]):
            assert b[0] >= a[2] - 1
        if align == "right":
            assert bxs[-1][2] <= cx1 + 1
        else:
            assert bxs[0][0] >= cx0 - 1
    assert multiword_seen
