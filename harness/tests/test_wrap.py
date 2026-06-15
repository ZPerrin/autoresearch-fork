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
