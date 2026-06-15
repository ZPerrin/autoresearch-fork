import random

from tablelab import classes as classlib
from tablelab.layout import layout, layout_with_regions, PlacedRegion


def test_layout_with_regions_returns_tokens_and_region_list():
    dc = classlib.get("invoice")
    placed, regions = layout_with_regions(dc, random.Random(7))
    assert isinstance(placed, list) and placed
    assert isinstance(regions, list)                       # may be empty until a later task captures bboxes


def test_layout_delegates_and_matches_tokens():
    dc = classlib.get("eob")
    a = layout(dc, random.Random(7))
    b, _regions = layout_with_regions(dc, random.Random(7))
    assert [(p.text, p.cell, p.label) for p in a] == [(p.text, p.cell, p.label) for p in b]
