from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.fields import background_token
from tablelab.specs import fork
from tablelab.layout import layout
from tablelab.render import render


def _invoice(**structure):
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, **structure))


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


def test_background_token_uses_document_class_terms():
    eob_terms = classlib.get("eob").background_terms
    rng = random.Random(7)
    values = {background_token(eob_terms, rng) for _ in range(200)}
    words = {value for value in values if not value.isdigit()}

    assert words <= set(eob_terms)
    assert words.isdisjoint({"Invoice", "Receipt"})


def test_builtin_background_vocabularies_are_distinct():
    invoice = classlib.get("invoice").background_terms
    eob = classlib.get("eob").background_terms
    receipt = classlib.get("receipt").background_terms

    assert len({invoice, eob, receipt}) == 3
    assert {"Invoice", "Account", "Remit To"} <= set(invoice)
    assert {"Explanation of Benefits", "Patient Responsibility", "This Is Not a Bill"} <= set(eob)
    assert {"Receipt", "Thank You", "Store Copy"} <= set(receipt)
