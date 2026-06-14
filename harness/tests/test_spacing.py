from tablelab.fields import field_weight
from tablelab.specs import FieldSpec


def test_field_weight_uses_explicit_override():
    assert field_weight(FieldSpec("amount", "amount", "right", width=3.0)) == 3.0


def test_field_weight_falls_back_to_type_default():
    assert field_weight(FieldSpec("desc", "description")) == 4.0


def test_field_weight_unknown_type_is_one():
    assert field_weight(FieldSpec("x", "totally_unknown_type")) == 1.0
