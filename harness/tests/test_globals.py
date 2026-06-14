from __future__ import annotations

import random
from collections import defaultdict

from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render


def test_no_globals_for_simple_classes():
    placed = layout(classlib.get("invoice"), random.Random(7))
    assert all(p.label is None or "global" not in p.label for p in placed)


def test_eob_emits_named_globals():
    placed = layout(classlib.get("eob"), random.Random(7))
    gnames = {p.label["global"] for p in placed if p.label and "global" in p.label}
    assert {"member_name", "member_id", "provider", "claim_number"} <= gnames


def test_each_global_has_a_label_and_a_value():
    placed = layout(classlib.get("eob"), random.Random(7))
    by_name = defaultdict(list)
    for p in placed:
        if p.label and "global" in p.label:
            by_name[p.label["global"]].append(p)
    for toks in by_name.values():
        kinds = {bool(t.label.get("header")) for t in toks}
        assert kinds == {True, False}  # a label token (header) and a value token


def test_globals_sit_above_the_claim_table():
    placed = layout(classlib.get("eob"), random.Random(7))
    g = [p for p in placed if p.label and "global" in p.label]
    claim = [p for p in placed if p.label and "record" in p.label]
    assert max(p.cell[3] for p in g) <= min(p.cell[1] for p in claim) + 1


def test_eob_claim_table_is_multi_instance():
    placed = layout(classlib.get("eob"), random.Random(7))
    claim = [p for p in placed if p.label and "record" in p.label]
    assert all("region" in p.label for p in claim)  # multi-instance class always tags region


def test_eob_renders_all_boxes_set():
    dc = classlib.get("eob")
    placed = layout(dc, random.Random(7))
    _img, boxes = render(placed, dc)
    assert all(b[2] > b[0] and b[3] > b[1] for b in boxes)
