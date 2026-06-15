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
