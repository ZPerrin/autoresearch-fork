import random

import pytest

from tablelab import classes as classlib
from tablelab.fields import _CATEGORIES
from tablelab.specs import (DocumentClass, TableSpec, FieldSpec, StructureSpec,
                            LayoutSpec, SpanCell, SpanRowSpec)
from tablelab.layout import (layout, _group_runs, validate_layout_capacity,
                             LayoutCapacityError)
from tablelab.render import render

from _cells import placed, cells_where, text_of

F = FieldSpec


def _grouped_class(page=(800, 800), **over):
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
        structure=StructureSpec(header=True),
        layout=LayoutSpec(page=page, margin=(20, 20)), **over)


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
    tokens, cells, _regions = placed(dc)
    banners = cells_where(cells, role="group_header")
    leaf_hdrs = cells_where(cells, role="header")

    banner_names = {text_of(tokens, c) for c in banners}
    assert banner_names == {"G1", "G2"}

    # banners sit above leaf headers
    assert min(c.bbox[1] for c in banners) < min(c.bbox[1] for c in leaf_hdrs)

    # G1 spans cols 0..1 (colspan=2), G2 spans col 3 (colspan=1)
    g1 = next(c for c in banners if text_of(tokens, c) == "G1")
    assert g1.column_index == 0
    assert g1.span[0] == 2  # colspan = 2

    # G1's x-range should match the combined range of leaf headers for cols 0 and 1
    col0_hdr = next(c for c in leaf_hdrs if c.column_index == 0)
    col1_hdr = next(c for c in leaf_hdrs if c.column_index == 1)
    assert g1.bbox[0] == pytest.approx(col0_hdr.bbox[0])
    assert g1.bbox[2] == pytest.approx(col1_hdr.bbox[2])


def test_row_band_order_top_to_bottom():
    dc = _grouped_class()
    tokens, cells, _regions = placed(dc)

    def top_of_role(role):
        return min(c.bbox[1] for c in cells_where(cells, role=role))

    banner_top = top_of_role("group_header")
    leaf_top = top_of_role("header")
    section_top = top_of_role("section")
    data_top = top_of_role("data")
    summary_top = top_of_role("summary")
    assert banner_top < leaf_top < section_top < data_top < summary_top


# ---- spanning data rows ----

def test_section_label_from_category_vocab():
    dc = _grouped_class()
    tokens, cells, _regions = placed(dc)
    section_cells = cells_where(cells, role="section")
    assert len(section_cells) == 1
    sc = section_cells[0]
    assert text_of(tokens, sc) in _CATEGORIES
    assert sc.span[0] == 4  # colspan = 4 (full-width span)
    assert sc.column_index == 0  # starts at the first column


def test_totals_label_spans_left_values_under_numeric_columns():
    dc = _grouped_class()
    tokens, cells, _regions = placed(dc)
    summary_cells = cells_where(cells, role="summary")
    # TOTALS label cell: span=2, column_index=0
    label_cell = next(c for c in summary_cells if text_of(tokens, c) == "TOTALS")
    assert label_cell.span[0] == 2
    # value cells: column_index 2 and 3
    value_cells = [c for c in summary_cells if c != label_cell and c.word_ids]
    assert sorted(c.column_index for c in value_cells) == [2, 3]


# ---- grouped-header banners always split into words ----

def test_banner_label_splits_into_words():
    # No flag: the eob class emits word-level tokens, so a multi-word banner
    # ("Patient Responsibility") is two words sharing one cell rect, in seq order.
    dc = classlib.get("eob")
    tokens, cells, _regions = placed(dc)
    bc = next(c for c in cells_where(cells, role="group_header")
              if text_of(tokens, c) == "Patient Responsibility")
    words = [tokens[i].text for i in bc.word_ids]
    assert words == ["Patient", "Responsibility"]
    rects = {tokens[i].cell for i in bc.word_ids}
    assert len(rects) == 1
    seqs = [tokens[i].seq for i in bc.word_ids]
    assert seqs == [0, 1]


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
    dc = _grouped_class(page=(800, 280))
    with pytest.raises(LayoutCapacityError):
        validate_layout_capacity(dc)


# ---- off-path inertness ----

def test_plain_table_emits_no_spanning_or_group_tokens():
    dc = classlib.get("invoice")
    _tokens, cells, _regions = placed(dc)
    # plain invoice has no group_header, section, or summary cells
    assert cells_where(cells, role="group_header") == []
    assert cells_where(cells, role="section") == []
    assert cells_where(cells, role="summary") == []


# ---- end to end: every eob box stays in page ----

def test_eob_boxes_stay_in_page():
    dc = classlib.get("eob")
    W, H = dc.layout.page
    rng = random.Random(7)
    for _ in range(12):
        placed_toks = layout(dc, rng)
        _img, boxes = render(placed_toks, dc)
        for (x0, y0, x1, y1) in boxes:
            assert 0 <= x0 <= x1 <= W
            assert 0 <= y0 <= y1 <= H
