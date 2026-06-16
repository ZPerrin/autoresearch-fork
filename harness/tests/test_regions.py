import random

from tablelab import classes as classlib
from tablelab.layout import layout, layout_with_regions, PlacedRegion

from _cells import placed, cells_where


def test_layout_with_regions_returns_tokens_and_region_list():
    dc = classlib.get("invoice")
    tokens, cells, regions = layout_with_regions(dc, random.Random(7))
    assert isinstance(tokens, list) and tokens
    assert isinstance(cells, list)
    assert isinstance(regions, list)


def test_layout_delegates_and_matches_tokens():
    dc = classlib.get("eob")
    a = layout(dc, random.Random(7))
    b, _cells, _regions = layout_with_regions(dc, random.Random(7))
    assert [(p.text, p.cell) for p in a] == [(p.text, p.cell) for p in b]


def test_region_bbox_encloses_instance_tokens():
    dc = classlib.get("eob")
    tokens, cells, regions = layout_with_regions(dc, random.Random(7))
    assert regions
    # gather cells per region_index
    by_region: dict[int, list] = {}
    for c in cells:
        by_region.setdefault(c.region_index, []).append(c)
    assert by_region  # eob is multi-instance
    for idx, reg in enumerate(regions):
        reg_cells = by_region.get(idx, [])
        if not reg_cells:
            continue
        x0 = min(c.bbox[0] for c in reg_cells)
        y0 = min(c.bbox[1] for c in reg_cells)
        x1 = max(c.bbox[2] for c in reg_cells)
        y1 = max(c.bbox[3] for c in reg_cells)
        bx0, by0, bx1, by1 = reg.bbox
        assert bx0 <= x0 + 1 and by0 <= y0 + 1
        assert bx1 >= x1 - 1 and by1 >= y1 - 1


def test_single_instance_class_has_one_region():
    dc = classlib.get("invoice")
    _tokens, _cells, regions = layout_with_regions(dc, random.Random(7))
    # invoice has no globals, one table → one region
    assert len(regions) == 1
    assert isinstance(regions[0], PlacedRegion)
    assert regions[0].type == "table"
    assert regions[0].name == "line_item"
    assert regions[0].index == 0


def test_sample_regions_round_trip(tmp_path):
    from tablelab.artifacts import (Sample, Token, Region, DatasetManifest,
                                    write_dataset, read_dataset)
    sample = Sample(
        id=0,
        tokens=[Token(x0=0.1, y0=0.1, x1=0.2, y1=0.2, text="x")],
        width=100, height=100, image="/datasets/x/images/0.png",
        regions=[Region(type="table", name="claim_line", index=0,
                        bbox=[0.05, 0.05, 0.9, 0.5])])
    manifest = DatasetManifest(dataset_id="x", generator_version=2, task="grid_record_field",
                               modalities=["spatial"], count=1)
    write_dataset(tmp_path, manifest, [sample])
    _m, got = read_dataset(tmp_path / "x")
    assert got[0].regions is not None
    assert isinstance(got[0].regions[0], Region)
    assert got[0].regions[0].type == "table"
    assert got[0].regions[0].name == "claim_line"
    assert got[0].regions[0].index == 0
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
        table_regions = [r for r in s.regions if r.type == "table"]
        assert table_regions and all(r.name == "claim_line" for r in table_regions)
        for r in s.regions:
            assert isinstance(r, Region)
            assert r.type in ("table", "form")
            assert all(0.0 <= v <= 1.0 for v in r.bbox)
            assert r.bbox[0] < r.bbox[2] and r.bbox[1] < r.bbox[3]
