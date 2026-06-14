import random
from tablelab.fields import field_weight
from tablelab.specs import FieldSpec
from tablelab import classes as classlib
from tablelab.layout import layout


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
