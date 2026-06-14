import random

import pytest

from tablelab import classes as classlib
from tablelab.fields import _CATEGORIES
from tablelab.specs import (DocumentClass, TableSpec, FieldSpec, StructureSpec,
                            LayoutSpec, SpanCell, SpanRowSpec)
from tablelab.layout import (layout, _group_runs, validate_layout_capacity,
                             LayoutCapacityError)
from tablelab.render import render

F = FieldSpec


def _grouped_class(page=(800, 800), multi_token=False, **over):
    """A small grouped + section + totals table: cols [G1 G1 _ G2], a full-span
    category section row, and a TOTALS label (span 2) + two amount cells."""
    fields = (F("a", "code", "left", group="G1"),
              F("b", "code", "left", group="G1"),
              F("c", "amount", "right"),
              F("d", "amount", "right", group="G2"))
    table = TableSpec(
        name="x", fields=fields, rows=(2, 2), instances=(1, 1),
        section=SpanRowSpec((SpanCell(span=4, type="category"),)),
        totals=SpanRowSpec((SpanCell(span=2, text="TOTALS"),
                            SpanCell(span=1, type="amount", align="right"),
                            SpanCell(span=1, type="amount", align="right"))))
    return DocumentClass(
        name="t", tables=(table,),
        structure=StructureSpec(header=True, multi_token=multi_token),
        layout=LayoutSpec(page=page, margin=(20, 20)), **over)


def _placed(dc, seed=0):
    return layout(dc, random.Random(seed))


# ---- contiguous-run inference ----

def test_group_runs_inclusive_ranges():
    fields = (F("a", "code", "left", group="G1"),
              F("b", "code", "left", group="G1"),
              F("c", "amount", "right"),
              F("d", "amount", "right", group="G2"))
    assert _group_runs(fields) == [("G1", 0, 1), ("G2", 3, 3)]


def test_group_runs_two_non_adjacent_same_name_runs():
    fields = (F("a", "code", "left", group="G"),
              F("b", "code", "left"),            # gap breaks the run
              F("c", "amount", "right", group="G"))
    assert _group_runs(fields) == [("G", 0, 0), ("G", 2, 2)]


# ---- banner geometry ----

def test_banner_sits_above_leaf_header_with_correct_span():
    dc = _grouped_class()
    placed = _placed(dc)
    banners = [p for p in placed if p.label and p.label.get("group")]
    leaf = [p for p in placed
            if p.label and p.label.get("header") and "group" not in p.label
            and "subtotal" not in p.label]
    assert {p.text for p in banners} == {"G1", "G2"}
    assert min(p.cell[1] for p in banners) < min(p.cell[1] for p in leaf)
    g1 = next(p for p in banners if p.text == "G1")
    # G1 spans cols 0..1: its x-range equals the leaf headers' for cols 0 and 1.
    assert g1.label["span"] == [0, 1]
    col0 = next(p for p in leaf if p.label["field"] == 0)
    col1 = next(p for p in leaf if p.label["field"] == 1)
    assert g1.cell[0] == pytest.approx(col0.cell[0])
    assert g1.cell[2] == pytest.approx(col1.cell[2])


def test_row_band_order_top_to_bottom():
    dc = _grouped_class()
    placed = _placed(dc)

    def top(pred):
        return min(p.cell[1] for p in placed if pred(p))

    banner = top(lambda p: p.label and p.label.get("group"))
    leaf = top(lambda p: p.label and p.label.get("header")
               and "group" not in p.label and "subtotal" not in p.label)
    section = top(lambda p: p.label and p.label.get("section"))
    data = top(lambda p: p.label and "record" in p.label)
    totals = top(lambda p: p.label and p.label.get("subtotal"))
    assert banner < leaf < section < data < totals


# ---- spanning data rows ----

def test_section_label_from_category_vocab():
    dc = _grouped_class()
    placed = _placed(dc)
    section = [p for p in placed if p.label and p.label.get("section")]
    assert len(section) == 1
    assert section[0].text in _CATEGORIES
    assert section[0].label["span"] == [0, 3]


def test_totals_label_spans_left_values_under_numeric_columns():
    dc = _grouped_class()
    placed = _placed(dc)
    label = [p for p in placed if p.label
             and p.label.get("subtotal") and p.label.get("header")]
    values = [p for p in placed if p.label
              and p.label.get("subtotal") and not p.label.get("header")]
    assert [p.text for p in label] == ["TOTALS"]
    assert label[0].label["span"] == [0, 1]
    assert sorted(p.label["field"] for p in values) == [2, 3]


# ---- multi_token banner split ----

def test_multi_token_splits_banner_label():
    fields = (F("a", "code", "left", group="Patient Responsibility"),
              F("b", "code", "left", group="Patient Responsibility"))
    dc = DocumentClass(
        name="t",
        tables=(TableSpec(name="x", fields=fields, rows=(1, 1), instances=(1, 1)),),
        structure=StructureSpec(header=True, multi_token=True),
        layout=LayoutSpec(page=(800, 400), margin=(20, 20)))
    placed = _placed(dc)
    words = [p for p in placed if p.label and p.label.get("group")]
    assert [p.text for p in words] == ["Patient", "Responsibility"]
    assert words[0].cell == words[1].cell           # share the banner cell
    assert [p.label["seq"] for p in words] == [0, 1]


# ---- validation ----

def test_group_without_header_raises():
    dc = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(F("a", "code", "left", group="G"),)),))
    with pytest.raises(LayoutCapacityError, match="require a leaf header"):
        validate_layout_capacity(dc)


def test_span_sum_mismatch_raises():
    dc = DocumentClass(
        name="t",
        tables=(TableSpec(name="x", fields=(F("a", "code", "left"),
                                            F("b", "amount", "right")),
                          totals=SpanRowSpec((SpanCell(span=3, text="T"),))),),
        structure=StructureSpec(header=True))
    with pytest.raises(LayoutCapacityError, match="spans sum to 3, expected 2"):
        validate_layout_capacity(dc)


def test_text_and_type_both_set_raises():
    dc = DocumentClass(
        name="t",
        tables=(TableSpec(name="x", fields=(F("a", "code", "left"),),
                          totals=SpanRowSpec(
                              (SpanCell(span=1, text="T", type="amount"),))),),
        structure=StructureSpec(header=True))
    with pytest.raises(LayoutCapacityError, match="both text and type"):
        validate_layout_capacity(dc)


# ---- capacity ----

def test_short_page_that_fits_data_but_not_extra_rows_raises():
    # 4 fixed rows (header+banner+section+totals) + 2 data rows do not fit a short page.
    dc = _grouped_class(page=(800, 360))
    with pytest.raises(LayoutCapacityError):
        validate_layout_capacity(dc)


# ---- off-path inertness ----

def test_plain_table_emits_no_spanning_or_group_tokens():
    dc = classlib.get("invoice")
    placed = _placed(dc)
    assert not any(p.label and (p.label.get("group") or p.label.get("section")
                                or p.label.get("subtotal")) for p in placed)


# ---- end to end: every eob box stays in page ----

def test_eob_boxes_stay_in_page():
    dc = classlib.get("eob")
    W, H = dc.layout.page
    rng = random.Random(7)
    for _ in range(12):
        placed = layout(dc, rng)
        _img, boxes = render(placed, dc)
        for (x0, y0, x1, y1) in boxes:
            assert 0 <= x0 <= x1 <= W
            assert 0 <= y0 <= y1 <= H
