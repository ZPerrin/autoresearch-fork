from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _invoice(**structure):
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, **structure))


def test_header_off_is_default():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all(not (p.label and p.label.get("header")) for p in placed)


def test_header_row_emits_field_name_tokens_above_data():
    dc = _invoice(header=True)
    placed = layout(dc, random.Random(7))
    headers = [p for p in placed if p.label.get("header")]
    data = [p for p in placed if not p.label.get("header")]
    C = len(dc.fields)
    my, row_h = dc.layout.margin[1], dc.layout.row_h
    # one header token per field, carrying the titleized field name
    assert sorted(p.label["field"] for p in headers) == list(range(C))
    assert {p.label["field"]: p.text for p in headers}[0] == "Description"
    # header cells sit at the top margin; every data cell is below the first row
    assert all(p.cell[1] == my for p in headers)
    assert all(p.cell[1] >= my + row_h for p in data)


def test_header_with_multi_token_splits_header_text():
    dc = _invoice(header=True, multi_token=True)
    placed = layout(dc, random.Random(7))
    # "Unit Price" (field 2) -> two header tokens sharing the header cell, ordered by seq
    unit = [p for p in placed if p.label.get("header") and p.label["field"] == 2]
    assert [p.text for p in sorted(unit, key=lambda p: p.label["seq"])] == ["Unit", "Price"]
    assert len({p.cell for p in unit}) == 1


def test_header_renders_boxes_above_data():
    dc = _invoice(header=True)
    placed = layout(dc, random.Random(7))
    _img, boxes = render(placed, dc)
    hb = [b for p, b in zip(placed, boxes) if p.label.get("header")]
    db = [b for p, b in zip(placed, boxes) if not p.label.get("header")]
    assert all(b[2] > b[0] for b in boxes)          # every box set
    assert max(b[3] for b in hb) <= min(b[1] for b in db) + 1  # headers above data
