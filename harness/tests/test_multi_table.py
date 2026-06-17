from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, cells_where


def _instanced(n_lo, n_hi, **structure):
    dc = classlib.get("invoice")
    tables = tuple(replace(t, instances=(n_lo, n_hi)) for t in dc.tables)
    return fork(dc, tables=tables, structure=replace(dc.structure, **structure))


def test_single_instance_has_no_region():
    _tokens, cells, regions = placed(classlib.get("invoice"), seed=7)
    # single-instance: exactly one table region; data cells all share region_index 0
    # (for a multi-table class there could be multiple, but invoice has one table)
    table_regions = [r for r in regions if r.type == "table"]
    assert len(table_regions) == 1
    data_cells = cells_where(cells, role="data")
    assert all(c.region_index == regions.index(table_regions[0]) for c in data_cells)
    # all data cells share a single region_index (one table region)
    region_indices = {c.region_index for c in data_cells}
    assert len(region_indices) == 1


def test_multiple_instances_label_region_contiguous():
    _tokens, cells, regions = placed(_instanced(2, 2), seed=7)
    table_regions = [r for r in regions if r.type == "table"]
    # Two instances → two table regions with index 0 and 1
    assert len(table_regions) == 2
    assert sorted(r.index for r in table_regions) == [0, 1]

    # Data cells must map to two distinct region_indices
    data_cells = cells_where(cells, role="data")
    region_indices = sorted({c.region_index for c in data_cells})
    assert len(region_indices) == 2

    # Row_index restarts per instance (both instances start at row_index 0)
    by_region_index: dict[int, set] = defaultdict(set)
    for c in data_cells:
        by_region_index[c.region_index].add(c.row_index)
    assert all(0 in rows for rows in by_region_index.values())


def test_instances_stacked_vertically():
    _tokens, cells, regions = placed(_instanced(2, 2), seed=7)
    table_regions = sorted([r for r in regions if r.type == "table"], key=lambda r: r.index)
    r0_idx = regions.index(table_regions[0])
    r1_idx = regions.index(table_regions[1])
    r0_cells = [c for c in cells if c.region_index == r0_idx]
    r1_cells = [c for c in cells if c.region_index == r1_idx]
    r0_bottom = max(c.bbox[3] for c in r0_cells)
    r1_top = min(c.bbox[1] for c in r1_cells)
    assert r0_bottom <= r1_top + 1


def test_instances_render_all_boxes_set():
    dc = _instanced(2, 3)
    p_tokens = layout(dc, random.Random(7))
    _img, boxes = render(p_tokens, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)
    _tokens, cells, regions = placed(dc, seed=7)
    table_region_count = sum(1 for r in regions if r.type == "table")
    assert 2 <= table_region_count <= 3


def test_instances_compose_with_header_and_region():
    _tokens, cells, regions = placed(_instanced(2, 2, header=True), seed=7)
    # header cells exist in both table regions
    header_cells = cells_where(cells, role="header")
    table_regions = [r for r in regions if r.type == "table"]
    assert len(table_regions) == 2
    hdr_region_indices = {c.region_index for c in header_cells}
    table_region_indices = {regions.index(r) for r in table_regions}
    assert hdr_region_indices == table_region_indices


def test_instances_compose_with_multi_token():
    _tokens, cells, regions = placed(_instanced(2, 2, multi_token=True), seed=7)
    # multi-word data cells exist; each belongs to a table region
    multi_data_cells = [c for c in cells_where(cells, role="data") if len(c.token_ids) > 1]
    table_region_indices = {i for i, r in enumerate(regions) if r.type == "table"}
    # at least some multi-token data cells have a region_index in a table region
    # (split header words are in group_header/header cells, not data)
    assert multi_data_cells
    assert all(c.region_index in table_region_indices for c in multi_data_cells)
