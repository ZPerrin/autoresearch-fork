from __future__ import annotations

import random
from dataclasses import replace

import pytest

from tablelab import classes as classlib
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
    [("instances", (2, 1)), ("rows", (3, 2)), ("rows", (-1, 2))],
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
