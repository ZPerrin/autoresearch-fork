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


def test_sample_regions_round_trip(tmp_path):
    from tablelab.artifacts import (Sample, Token, Region, DatasetManifest,
                                    write_dataset, read_dataset)
    sample = Sample(
        id=0,
        tokens=[Token(x0=0.1, y0=0.1, x1=0.2, y1=0.2, text="x", label={"region": 0})],
        width=100, height=100, image="/datasets/x/images/0.png",
        regions=[Region(region=0, table="claim_line", bbox=[0.05, 0.05, 0.9, 0.5])])
    manifest = DatasetManifest(dataset_id="x", generator_version=2, task="grid_record_field",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got[0].regions is not None
    assert isinstance(got[0].regions[0], Region)
    assert got[0].regions[0].table == "claim_line"
    assert got[0].regions[0].bbox == [0.05, 0.05, 0.9, 0.5]


def test_sample_regions_default_none():
    from tablelab.artifacts import Sample
    assert Sample(id=0, tokens=[]).regions is None


def test_build_dataset_writes_normalized_regions(tmp_path):
    from tablelab.build import build_dataset
    from tablelab.artifacts import read_dataset, Region
    ds = build_dataset(tmp_path, "rg-eob", classlib.get("eob"), seed=7, n=2)
    _m, samples = read_dataset(ds)
    assert all(s.regions for s in samples)
    for s in samples:
        for r in s.regions:
            assert isinstance(r, Region)
            assert r.table == "claim_line"
            assert all(0.0 <= v <= 1.0 for v in r.bbox)
            assert r.bbox[0] < r.bbox[2] and r.bbox[1] < r.bbox[3]
