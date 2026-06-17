from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, cells_where, text_of


def _invoice(**structure):
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, **structure))


def test_header_off_is_default():
    _tokens, cells, _regions = placed(classlib.get("invoice"), seed=7)
    # no header cells when structure.header is off
    assert cells_where(cells, role="header") == []


def test_header_row_emits_field_name_tokens_above_data():
    dc = _invoice(header=True)
    tokens, cells, _regions = placed(dc, seed=7)
    header_cells = cells_where(cells, role="header")
    data_cells = cells_where(cells, role="data")
    C = len(dc.tables[0].fields)
    my, row_h = dc.layout.margin[1], dc.layout.row_h

    # one header cell per field
    assert len(header_cells) == C
    # column indices cover 0..C-1
    assert sorted(c.column_index for c in header_cells) == list(range(C))
    # field 0 → "Description"
    hdr0 = next(c for c in header_cells if c.column_index == 0)
    assert text_of(tokens, hdr0) == "Description"
    # header cell tops sit at the top margin
    assert all(c.bbox[1] == my for c in header_cells)
    # every data cell is below the first row
    assert all(c.bbox[1] >= my + row_h for c in data_cells)


def test_header_with_multi_token_splits_header_text():
    dc = _invoice(header=True, multi_token=True)
    tokens, cells, _regions = placed(dc, seed=7)
    # "Unit Price" (field 2) → one header cell with two token_ids
    unit_hdr = next(c for c in cells_where(cells, role="header") if c.column_index == 2)
    words = [tokens[i].text for i in unit_hdr.token_ids]
    assert words == ["Unit", "Price"]
    # all tokens share the same cell rect
    rects = {tokens[i].cell for i in unit_hdr.token_ids}
    assert len(rects) == 1


def test_header_renders_boxes_above_data():
    dc = _invoice(header=True)
    tokens, cells, _regions = placed(dc, seed=7)
    # use layout()+render() for render geometry check
    p_tokens = layout(dc, random.Random(7))
    _img, boxes = render(p_tokens, dc)
    header_cells = cells_where(cells, role="header")
    data_cells = cells_where(cells, role="data")
    hb = [boxes[i] for c in header_cells for i in c.token_ids]
    db = [boxes[i] for c in data_cells for i in c.token_ids]
    assert all(b[2] > b[0] for b in boxes)          # every box set
    assert max(b[3] for b in hb) <= min(b[1] for b in db) + 1  # headers above data
