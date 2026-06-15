import random

import pytest

from tablelab.specs import FieldSpec, LayoutSpec, TableSpec, DocumentClass
from tablelab.layout import layout, validate_layout_capacity, LayoutCapacityError


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
    placed = layout(dc, random.Random(0))
    desc_w = {round(p.cell[2] - p.cell[0], 1)
              for p in placed if p.label and p.label.get("field") == 0 and "record" in p.label}
    assert desc_w  # has description tokens
    assert max(desc_w) <= 120.0 + 0.5  # frozen at the cap


def test_uncapped_columns_still_fill_page():
    dc = _capped_class(max_width=120.0)
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    placed = layout(dc, random.Random(0))
    x1s = [p.cell[2] for p in placed if p.label and "field" in p.label]
    assert abs(max(x1s) - (W - mx)) < 1e-6  # table still spans to the right margin


def test_wrapped_cell_emits_stacked_line_tokens():
    # A capped column whose value wraps emits one token per word, sharing the field label,
    # split across >=2 distinct vertical line positions.
    dc = _capped_class(max_width=110.0)
    found = False
    for seed in range(30):
        placed = layout(dc, random.Random(seed))
        desc = [p for p in placed if p.label and p.label.get("field") == 0 and "record" in p.label]
        ys = sorted({round(p.cell[1], 1) for p in desc})
        if len(ys) >= 2:                                  # this sample wrapped
            found = True
            assert all(p.label["field"] == 0 and "record" in p.label for p in desc)
            assert all("seq" in p.label for p in desc)    # individual word tokens carry order
            # words on the same line share one cell rect
            line0 = [p for p in desc if round(p.cell[1], 1) == ys[0]]
            assert len({p.cell for p in line0}) == 1
            break
    assert found, "expected at least one wrapped sample at max_width=110"


def test_wrapped_words_stay_within_their_column():
    # max_width wide enough that every individual service_desc word fits the column (so a
    # phrase wraps across lines but no single word overflows — a word cannot be split).
    from tablelab.render import render
    dc = _capped_class(max_width=240.0)
    for seed in range(10):
        placed = layout(dc, random.Random(seed))
        _img, boxes = render(placed, dc)
        for p, b in zip(placed, boxes):
            if p.label and p.label.get("field") == 0 and "record" in p.label:
                assert b[0] >= p.cell[0] - 1 and b[2] <= p.cell[2] + 1, (p.text, p.cell, b)
