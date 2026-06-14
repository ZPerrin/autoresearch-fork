from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.fields import background_token
from tablelab.specs import DocumentClass, fork
from tablelab.layout import layout
from tablelab.render import render


def _invoice(**structure):
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, **structure))


def _overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def test_background_off_is_default():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all(p.label is not None for p in placed)


def test_background_adds_n_null_label_tokens_below_table():
    dc = _invoice(background=5)
    placed = layout(dc, random.Random(7))
    bg = [p for p in placed if p.label is None]
    data = [p for p in placed if p.label is not None]
    assert len(bg) == 5
    # background sits at or below the bottom of the lowest table row
    table_bottom = max(p.cell[3] for p in data)
    assert all(p.cell[1] >= table_bottom for p in bg)
    # each background token has a unique cell rect (render groups by cell; null labels must stay singletons)
    assert len({p.cell for p in bg}) == len(bg)
    # table tokens are unaffected and still labeled
    assert all(p.label is not None and "field" in p.label for p in data)


def test_background_renders_and_round_trips_null_label():
    dc = _invoice(background=4)
    placed = layout(dc, random.Random(7))
    img, boxes = render(placed, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)  # every box set, including background
    # the null label is preserved through the placed tokens (what build.py serializes)
    assert sum(1 for p in placed if p.label is None) == 4


def test_background_composes_with_header():
    dc = _invoice(background=3, header=True)
    placed = layout(dc, random.Random(7))
    assert sum(1 for p in placed if p.label is None) == 3
    assert any(p.label and p.label.get("header") for p in placed)


def test_reserved_background_slots_do_not_overlap_content_or_each_other():
    dc = _invoice(background=8, header=True)
    placed = layout(dc, random.Random(7))
    background = [p for p in placed if p.label is None]
    structured = [p for p in placed if p.label is not None]

    assert not any(
        _overlaps(bg.cell, token.cell)
        for bg in background
        for token in structured
    )
    assert not any(
        _overlaps(background[i].cell, background[j].cell)
        for i in range(len(background))
        for j in range(i + 1, len(background))
    )


def test_background_token_uses_document_class_terms():
    eob_terms = classlib.get("eob").background_terms
    rng = random.Random(7)
    values = {background_token(eob_terms, rng) for _ in range(200)}
    words = {value for value in values if not value.isdigit()}

    assert words <= set(eob_terms)
    assert words.isdisjoint({"Invoice", "Receipt"})


def test_builtin_background_vocabularies_match_contract():
    assert classlib.get("invoice").background_terms == (
        "Invoice", "Account", "Customer", "Subtotal", "Total", "Balance",
        "Payment Terms", "Remit To", "Page", "Reference",
    )
    assert classlib.get("eob").background_terms == (
        "Explanation of Benefits", "Patient Responsibility", "Plan Paid",
        "Claim Reference", "Benefit Notice", "This Is Not a Bill",
        "Member Services", "Page", "Reference",
    )
    assert classlib.get("receipt").background_terms == (
        "Receipt", "Paid", "Subtotal", "Total", "Payment", "Thank You",
        "Store Copy", "Page", "Reference",
    )


def test_background_token_uses_neutral_fallback_for_empty_terms():
    neutral = {"Page", "Reference", "Notice", "Confidential", "Original", "Copy"}
    rng = random.Random(7)
    values = {background_token((), rng) for _ in range(200)}
    words = {value for value in values if not value.isdigit()}

    assert all(value.isdigit() or value in neutral for value in values)
    assert words
    assert words <= neutral


def test_background_token_numeric_branch_is_deterministic():
    class NumericRng:
        def random(self):
            return 0.29

        def randint(self, low, high):
            assert (low, high) == (1000, 99999)
            return 4242

    assert background_token(("unused",), NumericRng()) == "4242"


def test_document_class_background_terms_default_to_empty_tuple():
    bare = DocumentClass(name="bare", tables=classlib.get("invoice").tables)

    assert bare.background_terms == ()
