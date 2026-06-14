import random
from dataclasses import replace
from tablelab.fields import field_weight
from tablelab.specs import FieldSpec, fork
from tablelab import classes as classlib
from tablelab.layout import layout, validate_layout_capacity, LayoutCapacityError


def test_field_weight_uses_explicit_override():
    assert field_weight(FieldSpec("amount", "amount", "right", width=3.0)) == 3.0


def test_field_weight_falls_back_to_type_default():
    assert field_weight(FieldSpec("desc", "description")) == 4.0


def test_field_weight_unknown_type_is_one():
    assert field_weight(FieldSpec("x", "totally_unknown_type")) == 1.0


def test_eob_columns_are_non_uniform_but_fill_page():
    dc = classlib.get("eob")
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    placed = layout(dc, random.Random(0))
    widths = sorted({round(t.cell[2] - t.cell[0], 3)
                     for t in placed if t.label and "field" in t.label})
    assert len(widths) >= 2  # not all equal
    xs = [t.cell[0] for t in placed if t.label and "field" in t.label]
    x1s = [t.cell[2] for t in placed if t.label and "field" in t.label]
    assert abs(min(xs) - mx) < 1e-6
    assert abs(max(x1s) - (W - mx)) < 1e-6


def test_row_gap_increases_row_pitch():
    dc = classlib.get("eob")
    base = layout(dc, random.Random(1))
    spaced = layout(fork(dc, layout=replace(dc.layout, row_gap=30)), random.Random(1))
    ys = lambda p: sorted({t.cell[1] for t in p if t.label and t.label.get("record") is not None})
    assert ys(spaced)[1] - ys(spaced)[0] > ys(base)[1] - ys(base)[0]


def test_oversized_gaps_fail_capacity_cleanly():
    dc = classlib.get("eob")
    huge = fork(dc, layout=replace(dc.layout, section_gap=5000, instance_gap=5000))
    try:
        validate_layout_capacity(huge)
        raised = False
    except LayoutCapacityError:
        raised = True
    assert raised
