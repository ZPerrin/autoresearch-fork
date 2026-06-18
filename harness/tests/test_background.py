from __future__ import annotations

import random
from dataclasses import replace

from tablelab import classes as classlib
from tablelab.fields import background_token
from tablelab.specs import DocumentClass, fork
from tablelab.layout import layout
from tablelab.render import render

from _cells import placed, bg_word_ids, cells_where


def _invoice(**structure):
    dc = classlib.get("invoice")
    return fork(dc, structure=replace(dc.structure, **structure))


def _overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def test_background_off_is_default():
    tokens, cells, _regions = placed(classlib.get("invoice"), seed=7)
    # no background: every token is claimed by some cell
    assert bg_word_ids(tokens, cells) == []


def test_background_adds_n_null_label_tokens_below_table():
    dc = _invoice(background=5)
    tokens, cells, _regions = placed(dc, seed=7)
    bg_ids = bg_word_ids(tokens, cells)
    assert len(bg_ids) == 5

    # background sits at or below the bottom of the lowest table row
    claimed_ids = {i for c in cells for i in c.word_ids}
    table_bottom = max(tokens[i].cell[3] for i in claimed_ids)
    assert all(tokens[i].cell[1] >= table_bottom for i in bg_ids)

    # each background token has a unique cell rect
    assert len({tokens[i].cell for i in bg_ids}) == len(bg_ids)

    # every structured (non-background) token is claimed
    assert all(i in claimed_ids for i in range(len(tokens)) if i not in bg_ids)


def test_background_renders_and_round_trips_null_label():
    dc = _invoice(background=4)
    tokens, cells, _regions = placed(dc, seed=7)
    # use layout()+render() for the render check (render takes PlacedWord list)
    p_tokens = layout(dc, random.Random(7))
    _img, boxes = render(p_tokens, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)  # every box set
    # 4 background tokens are present (referenced by no cell)
    assert len(bg_word_ids(tokens, cells)) == 4


def test_background_composes_with_header():
    dc = _invoice(background=3, header=True)
    tokens, cells, _regions = placed(dc, seed=7)
    # 3 background tokens
    assert len(bg_word_ids(tokens, cells)) == 3
    # at least one header cell exists
    assert cells_where(cells, role="header")


def test_reserved_background_slots_do_not_overlap_content_or_each_other():
    dc = _invoice(background=8, header=True)
    tokens, cells, _regions = placed(dc, seed=7)
    bg_ids = bg_word_ids(tokens, cells)
    structured_ids = [i for i in range(len(tokens)) if i not in set(bg_ids)]

    bg_rects = [tokens[i].cell for i in bg_ids]
    str_rects = [tokens[i].cell for i in structured_ids]

    assert not any(
        _overlaps(bg, st)
        for bg in bg_rects
        for st in str_rects
    )
    assert not any(
        _overlaps(bg_rects[i], bg_rects[j])
        for i in range(len(bg_rects))
        for j in range(i + 1, len(bg_rects))
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
