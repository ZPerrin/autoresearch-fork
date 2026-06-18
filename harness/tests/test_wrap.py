import random

import pytest

from tablelab.specs import FieldSpec, LayoutSpec, TableSpec, DocumentClass
from tablelab.layout import layout, validate_layout_capacity, LayoutCapacityError

from _cells import placed, cells_where, text_of


def test_fieldspec_has_wrap_knobs():
    f = FieldSpec("desc", "description", "left", max_width=200.0, max_lines=2)
    assert f.max_width == 200.0
    assert f.max_lines == 2


def test_fieldspec_wrap_knobs_default_off():
    f = FieldSpec("desc", "description", "left")
    assert f.max_width is None
    assert f.max_lines == 1


def test_layoutspec_line_h_defaults_none():
    assert LayoutSpec().line_h is None


def test_service_desc_sampler_is_multiword():
    from tablelab.fields import sample
    rng = random.Random(0)
    vals = {sample("service_desc", rng) for _ in range(50)}
    assert vals  # non-empty vocab
    assert all(len(v.split()) >= 2 for v in vals)  # always multi-word so it can wrap


def test_wrap_greedy_packs_words_no_drops():
    from tablelab.layout import _wrap
    words = "alpha beta gamma delta epsilon".split()
    lines = _wrap(words, col_width=70.0, font_size=22)
    assert all(isinstance(line, list) for line in lines)
    assert [w for line in lines for w in line] == words  # order preserved, nothing dropped
    assert len(lines) >= 2                                # narrow width forces wrapping


def test_wrap_single_oversized_word_keeps_own_line():
    from tablelab.layout import _wrap
    lines = _wrap(["supercalifragilisticexpialidocious"], col_width=10.0, font_size=22)
    assert lines == [["supercalifragilisticexpialidocious"]]


def test_line_h_defaults_to_font_scaled():
    from tablelab.layout import _line_h
    dc = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(FieldSpec("a", "amount", "right"),)),))
    assert _line_h(dc) == round(dc.render.font_size * 1.4)


def test_line_h_honors_explicit_override():
    from tablelab.layout import _line_h
    dc = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(FieldSpec("a", "amount", "right"),)),),
        layout=LayoutSpec(line_h=40))
    assert _line_h(dc) == 40


def _capped_class(max_width, page=(600, 400)):
    fields = (FieldSpec("desc", "service_desc", "left", max_width=max_width),
              FieldSpec("amt", "amount", "right"))
    return DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=fields, rows=(2, 2), instances=(1, 1)),),
        layout=LayoutSpec(page=page, margin=(20, 20)))


def test_capped_column_does_not_exceed_max_width():
    dc = _capped_class(max_width=120.0)
    _tokens, cells, _regions = placed(dc, seed=0)
    # desc is field "desc" (column_index=0), data cells only
    desc_cells = cells_where(cells, role="data", field="desc")
    assert desc_cells  # has description cells
    desc_widths = {round(c.bbox[2] - c.bbox[0], 1) for c in desc_cells}
    assert max(desc_widths) <= 120.0 + 0.5  # frozen at the cap


def test_uncapped_columns_still_fill_page():
    dc = _capped_class(max_width=120.0)
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    _tokens, cells, _regions = placed(dc, seed=0)
    # all data/header cells: rightmost bbox edge should reach right margin
    content_cells = [c for c in cells if c.role in ("data", "header")]
    x1s = [c.bbox[2] for c in content_cells]
    assert abs(max(x1s) - (W - mx)) < 1e-4  # table still spans to the right margin


def test_wrapped_cell_emits_stacked_line_tokens():
    # A capped column whose value wraps emits multiple tokens in the data cell,
    # spanning >=2 distinct vertical line positions.
    from collections import defaultdict
    dc = _capped_class(max_width=110.0)
    found = False
    for seed in range(30):
        tokens, cells, _regions = placed(dc, seed=seed)
        desc_cells = cells_where(cells, role="data", field="desc")
        # check if any desc cell has tokens at >= 2 distinct vertical positions
        for c in desc_cells:
            if len(c.word_ids) < 2:
                continue
            ys = sorted({round(tokens[i].cell[1], 1) for i in c.word_ids})
            if len(ys) >= 2:
                found = True
                # the wrapped cell is a role="data" cell with field="desc" with >1 word_ids
                assert c.role == "data" and c.field == "desc" and len(c.word_ids) > 1
                # group tokens by per-line render rect; assert >= 2 distinct rects (actually wrapped)
                by_rect = defaultdict(list)
                for i in c.word_ids:
                    by_rect[tokens[i].cell].append(i)
                assert len(by_rect) >= 2  # wrapped onto >= 2 lines
                # each line group references exactly one rect, and within a line the
                # tokens carry seq 0,1,2,... in reading order (seq resets per line)
                for line_ids in by_rect.values():
                    assert len({tokens[i].cell for i in line_ids}) == 1
                    assert [tokens[i].seq for i in line_ids] == list(range(len(line_ids)))
                break
        if found:
            break
    assert found, "expected at least one wrapped sample at max_width=110"


def test_wrapped_words_stay_within_their_column():
    # max_width wide enough that every individual service_desc word fits the column
    from tablelab.render import render
    dc = _capped_class(max_width=240.0)
    for seed in range(10):
        p_tokens = layout(dc, random.Random(seed))
        _img, boxes = render(p_tokens, dc)
        tokens, cells, _regions = placed(dc, seed=seed)
        desc_cells = cells_where(cells, role="data", field="desc")
        for c in desc_cells:
            cx0, _cy0, cx1, _cy1 = c.bbox
            for i in c.word_ids:
                b = boxes[i]
                assert b[0] >= cx0 - 1 and b[2] <= cx1 + 1, (p_tokens[i].text, c.bbox, b)


def _short_page_wrap_class(max_lines):
    # row_h == line_h == 40, so a data row reserves max_lines * 40; a page tall enough for
    # 1-line rows but not max_lines rows must fail capacity validation up front.
    fields = (FieldSpec("desc", "service_desc", "left", max_width=200.0, max_lines=max_lines),)
    return DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=fields, rows=(2, 2), instances=(1, 1)),),
        layout=LayoutSpec(page=(400, 200), margin=(10, 10), row_h=40, line_h=40, table_gap=0))


def test_capacity_reserves_worst_case_lines():
    # 2 rows * (3 * 40) = 240 > available 180 -> capacity error.
    with pytest.raises(LayoutCapacityError):
        validate_layout_capacity(_short_page_wrap_class(max_lines=3))


def test_capacity_ok_for_single_line_reservation():
    # 2 rows * (1 * 40) = 80 < available 180 -> fits.
    validate_layout_capacity(_short_page_wrap_class(max_lines=1))


def test_eob_description_wraps_within_max_lines():
    from tablelab import classes as classlib
    from tablelab.render import render
    dc = classlib.get("eob")
    desc_field_name = next(f.name for f in dc.tables[0].fields if f.name == "description")
    max_lines = next(f.max_lines for f in dc.tables[0].fields if f.name == "description")
    saw_wrap = False
    for seed in range(40):
        tokens, cells, _regions = placed(dc, seed=seed)
        # group description data cells by (region_index, row_index)
        desc_cells = cells_where(cells, role="data", field=desc_field_name)
        for c in desc_cells:
            if len(c.word_ids) > 1:
                ys = {round(tokens[i].cell[1], 1) for i in c.word_ids}
                assert len(ys) <= max_lines
                if len(ys) >= 2:
                    saw_wrap = True
        # every box stays in page
        p_tokens = layout(dc, random.Random(seed))
        _img, boxes = render(p_tokens, dc)
        W, H = dc.layout.page
        for (x0, y0, x1, y1) in boxes:
            assert 0 <= x0 <= x1 <= W and 0 <= y0 <= y1 <= H
    assert saw_wrap, "expected the eob description to wrap on at least one seed"
