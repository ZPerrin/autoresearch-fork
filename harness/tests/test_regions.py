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


def test_region_bbox_encloses_instance_tokens():
    dc = classlib.get("eob")
    placed, regions = layout_with_regions(dc, random.Random(7))
    assert regions
    by_region: dict[int, list] = {}
    for p in placed:
        if p.label and "region" in p.label:
            by_region.setdefault(p.label["region"], []).append(p)
    assert by_region  # eob is multi-instance
    for reg in regions:
        toks = by_region.get(reg.region, [])
        if not toks:
            continue
        x0 = min(t.cell[0] for t in toks); y0 = min(t.cell[1] for t in toks)
        x1 = max(t.cell[2] for t in toks); y1 = max(t.cell[3] for t in toks)
        bx0, by0, bx1, by1 = reg.bbox
        assert bx0 <= x0 + 1 and by0 <= y0 + 1
        assert bx1 >= x1 - 1 and by1 >= y1 - 1


def test_single_instance_class_has_one_region():
    dc = classlib.get("invoice")
    _placed, regions = layout_with_regions(dc, random.Random(7))
    assert len(regions) == 1
    assert isinstance(regions[0], PlacedRegion)
    assert regions[0].table == "line_item"
    assert regions[0].region == 0
