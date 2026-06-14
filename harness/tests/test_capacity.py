from __future__ import annotations

import random
from dataclasses import replace

import pytest

from tablelab import classes as classlib
from tablelab import layout as layout_module
from tablelab.layout import LayoutCapacityError, layout, validate_layout_capacity
from tablelab.specs import fork


def _full_eob(**layout_overrides):
    dc = classlib.get("eob")
    tables = tuple(replace(table, instances=(1, 3)) for table in dc.tables)
    return fork(
        dc,
        tables=tables,
        layout=replace(dc.layout, **layout_overrides),
        structure=replace(
            dc.structure, header=True, multi_token=True, background=4
        ),
    )


def test_full_eob_cells_stay_within_page_across_seeds():
    dc = _full_eob()
    width, height = dc.layout.page

    for seed in range(200):
        for token in layout(dc, random.Random(seed)):
            x0, y0, x1, y1 = token.cell
            assert 0 <= x0 <= x1 <= width
            assert 0 <= y0 <= y1 <= height


def test_full_eob_samples_feasible_region_counts():
    dc = _full_eob()
    observed = set()

    for seed in range(200):
        placed = layout(dc, random.Random(seed))
        observed.add(len({
            token.label["region"]
            for token in placed
            if token.label and "region" in token.label
        }))

    assert observed <= {1, 2, 3}
    assert {1, 2} <= observed


def test_too_short_page_fails_capacity_validation():
    with pytest.raises(LayoutCapacityError, match="no page-feasible document shape"):
        validate_layout_capacity(_full_eob(page=(1000, 500)))


def test_default_invoice_validates():
    validate_layout_capacity(classlib.get("invoice"))


@pytest.mark.parametrize(
    ("attribute", "bounds"),
    [
        ("instances", (-1, 2)),
        ("instances", (2, 1)),
        ("rows", (-1, 2)),
        ("rows", (3, 2)),
    ],
)
def test_invalid_table_ranges_fail_clearly(attribute, bounds):
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], **{attribute: bounds})

    with pytest.raises(LayoutCapacityError, match=f"invalid {attribute} range"):
        validate_layout_capacity(fork(dc, tables=(table,)))


def test_negative_background_count_fails_clearly():
    dc = classlib.get("invoice")

    with pytest.raises(LayoutCapacityError, match="invalid background count"):
        validate_layout_capacity(
            fork(dc, structure=replace(dc.structure, background=-1))
        )


def test_empty_field_table_with_possible_instance_fails_clearly():
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], fields=(), instances=(0, 1))

    with pytest.raises(LayoutCapacityError, match="table 'line_item'.*no fields"):
        validate_layout_capacity(fork(dc, tables=(table,)))


@pytest.mark.parametrize(
    ("layout_overrides", "message"),
    [
        ({"page": (0, 1414)}, "invalid page dimensions"),
        ({"page": (1000, 0)}, "invalid page dimensions"),
        ({"margin": (-1, 80)}, "invalid margins"),
        ({"margin": (60, -1)}, "invalid margins"),
        ({"page": (100, 1414), "margin": (50, 80)}, "invalid usable page width"),
        ({"page": (1000, 100), "margin": (60, 50)}, "invalid available page height"),
        ({"row_h": 0}, "invalid row height"),
        ({"row_h": -1}, "invalid row height"),
        ({"table_gap": -1}, "invalid table gap"),
    ],
)
def test_invalid_layout_dimensions_fail_clearly(layout_overrides, message):
    dc = classlib.get("invoice")

    with pytest.raises(LayoutCapacityError, match=message):
        validate_layout_capacity(
            fork(dc, layout=replace(dc.layout, **layout_overrides))
        )


def test_enormous_impossible_range_fails_before_shape_enumeration(monkeypatch):
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], rows=(1, 1_000_000), instances=(1, 1_000_000))
    impossible = fork(
        dc,
        tables=(table,),
        layout=replace(dc.layout, page=(1000, 200)),
    )

    def fail_if_enumerated(_dc):
        raise AssertionError("minimum-height precheck did not stop enumeration")

    monkeypatch.setattr(layout_module, "_iter_feasible_shapes", fail_if_enumerated)
    with pytest.raises(LayoutCapacityError, match="no page-feasible document shape"):
        validate_layout_capacity(impossible)


def test_large_zero_height_instance_range_fails_clearly():
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], rows=(0, 0), instances=(1, 1_000_000))
    degenerate = fork(
        dc,
        tables=(table,),
        layout=replace(dc.layout, table_gap=0),
    )

    with pytest.raises(LayoutCapacityError, match="zero-height instances"):
        validate_layout_capacity(degenerate)


def test_background_requires_current_fixed_cell_width():
    dc = classlib.get("invoice")
    narrow = fork(
        dc,
        layout=replace(dc.layout, page=(199, 1414), margin=(60, 80)),
        structure=replace(dc.structure, background=1),
    )

    with pytest.raises(LayoutCapacityError, match="background placement requires at least 80px"):
        validate_layout_capacity(narrow)


def test_large_valid_instance_depth_uses_iterative_traversal():
    dc = classlib.get("invoice")
    table = replace(dc.tables[0], rows=(0, 0), instances=(1200, 1200))
    deep = fork(
        dc,
        tables=(table,),
        layout=replace(dc.layout, page=(1000, 1361), table_gap=1),
    )

    validate_layout_capacity(deep)
    shape = layout_module._choose_shape(deep, random.Random(7))
    assert len(shape[0]) == 1200
    assert set(shape[0]) == {0}


def test_many_zero_instance_tables_use_iterative_traversal():
    dc = classlib.get("invoice")
    tables = tuple(
        replace(dc.tables[0], name=f"table_{index}", rows=(0, 0), instances=(0, 0))
        for index in range(1200)
    )
    deep = fork(dc, tables=tables)

    validate_layout_capacity(deep)
    shape = layout_module._choose_shape(deep, random.Random(7))
    assert len(shape) == 1200
    assert all(table_shape == () for table_shape in shape)


def test_iterative_traversal_preserves_depth_first_yield_order():
    dc = classlib.get("invoice")
    tables = tuple(
        replace(dc.tables[0], name=f"table_{index}", rows=(0, 1), instances=(0, 1))
        for index in range(2)
    )
    ordered = fork(dc, tables=tables)

    assert list(layout_module._iter_feasible_shapes(ordered)) == [
        ((), ()),
        ((), (0,)),
        ((), (1,)),
        ((0,), ()),
        ((0,), (0,)),
        ((0,), (1,)),
        ((1,), ()),
        ((1,), (0,)),
        ((1,), (1,)),
    ]
