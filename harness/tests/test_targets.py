import random

from tablelab import classes as classlib
from tablelab.artifacts import Field, Node
from tablelab.layout import layout_with_targets, layout_with_regions


def _extraction(dc_name, seed=7):
    dc = classlib.get(dc_name)
    words, cells, regions, targets = layout_with_targets(dc, random.Random(seed))
    return words, cells, targets["extraction"]


def test_layout_with_regions_still_returns_three_tuple():
    dc = classlib.get("invoice")
    out = layout_with_regions(dc, random.Random(7))
    assert len(out) == 3


def test_globals_become_root_fields():
    _w, _c, root = _extraction("eob")
    assert set(root.fields) == {"member_name", "member_id", "provider", "claim_number"}
    for f in root.fields.values():
        assert isinstance(f, Field)


def test_table_becomes_field_group_of_records():
    _w, _c, root = _extraction("eob")
    assert "claim_line" in root.field_groups
    records = root.field_groups["claim_line"]
    assert records and all(isinstance(r, Node) for r in records)
    assert set(records[0].fields) == {
        "service_date", "code", "description", "amount_billed", "allowed",
        "deductible", "copay", "coinsurance", "plan_paid", "amount_owed"}


def test_invoice_records_equal_data_rows():
    words, cells, root = _extraction("invoice")
    data_rows = {(c.region_index, c.row_index) for c in cells if c.role == "data"}
    assert len(root.field_groups["line_item"]) == len(data_rows)


def test_grounding_invariants_eob():
    # `words` are page-px PlacedWord; `cells` are normalized artifacts.Cell — not directly
    # comparable, so grounding is checked via the authored cell membership (word_ids) and
    # the resolved value string, both stronger than a bbox-encloses heuristic.
    words, cells, root = _extraction("eob")

    def leaves(node):
        yield from node.fields.values()
        for recs in node.field_groups.values():
            for r in recs:
                yield from leaves(r)

    for f in leaves(root):
        assert all(0 <= wid < len(words) for wid in f.word_ids)
        assert f.cell is not None and 0 <= f.cell < len(cells)
        assert f.value == " ".join(words[i].text for i in f.word_ids)
        assert set(f.word_ids) == set(cells[f.cell].word_ids)
        if not f.word_ids:
            assert f.value == ""


def test_invoice_completeness_every_word_in_one_leaf():
    # invoice has no header/globals/section/totals/background → every word is a target leaf word.
    words, cells, root = _extraction("invoice")
    seen = []
    for rec in root.field_groups["line_item"]:
        for f in rec.fields.values():
            seen.extend(f.word_ids)
    assert sorted(seen) == list(range(len(words)))
    assert len(seen) == len(set(seen))  # exactly once
