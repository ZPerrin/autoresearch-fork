from __future__ import annotations

import random
from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, cells_where


def test_no_globals_for_simple_classes():
    _tokens, cells, regions = placed(classlib.get("invoice"), seed=7)
    # invoice has no globals → no form region and no key/value cells
    assert cells_where(cells, role="key") == []
    assert cells_where(cells, role="value") == []
    assert not any(r.type == "form" for r in regions)


def test_eob_emits_named_globals():
    _tokens, cells, _regions = placed(classlib.get("eob"), seed=7)
    value_cells = cells_where(cells, role="value")
    global_names = {c.field for c in value_cells}
    assert {"member_name", "member_id", "provider", "claim_number"} <= global_names


def test_each_global_has_a_label_and_a_value():
    _tokens, cells, _regions = placed(classlib.get("eob"), seed=7)
    # for each named global field there must be exactly one key cell and one value cell
    key_fields = {c.field for c in cells_where(cells, role="key")}
    value_fields = {c.field for c in cells_where(cells, role="value")}
    assert key_fields == value_fields  # every global has both a label and a value cell


def test_globals_sit_above_the_claim_table():
    tokens, cells, _regions = placed(classlib.get("eob"), seed=7)
    # globals are in the form region; claim_line data is in the table region
    key_cells = cells_where(cells, role="key") + cells_where(cells, role="value")
    data_cells = cells_where(cells, role="data")
    assert key_cells and data_cells
    global_bottom = max(c.bbox[3] for c in key_cells)
    table_top = min(c.bbox[1] for c in data_cells)
    assert global_bottom <= table_top + 1


def test_eob_claim_table_is_multi_instance():
    _tokens, cells, regions = placed(classlib.get("eob"), seed=7)
    # eob has multiple table instances → multiple table regions, all named "claim_line"
    table_regions = [r for r in regions if r.type == "table"]
    assert table_regions and all(r.name == "claim_line" for r in table_regions)
    # every data cell belongs to a claim_line table region (none slip outside the region system)
    data_cells = cells_where(cells, role="data")
    assert all(regions[c.region_index].name == "claim_line" for c in data_cells)


def test_eob_renders_all_boxes_set():
    dc = classlib.get("eob")
    p_tokens = layout(dc, random.Random(7))
    _img, boxes = render(p_tokens, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)
