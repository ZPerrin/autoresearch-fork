import random
from dataclasses import replace
from tablelab.fields import field_weight
from tablelab.specs import FieldSpec, TableSpec, DocumentClass, fork
from tablelab import classes as classlib
from tablelab.layout import layout, validate_layout_capacity, LayoutCapacityError
from tablelab.render import render


def _content_sized(p) -> bool:
    """A token whose cell width is governed by content-aware column sizing: a data or
    leaf-header column token. Banners and span rows (section/totals) are intentionally
    not column-content-sized (see the spanning-cells design), so they are excluded."""
    lab = p.label
    return bool(lab and "field" in lab
                and not (lab.get("group") or lab.get("section") or lab.get("subtotal")))


def test_field_weight_uses_explicit_override():
    assert field_weight(FieldSpec("amount", "amount", "right", width=3.0)) == 3.0


def test_field_weight_falls_back_to_type_default():
    assert field_weight(FieldSpec("desc", "description")) == 4.0


def test_field_weight_unknown_type_is_one():
    assert field_weight(FieldSpec("x", "totally_unknown_type")) == 1.0


def test_eob_columns_are_non_uniform_but_fill_page():
    dc = classlib.get("eob")
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    placed = layout(dc, random.Random(0))
    widths = sorted({round(t.cell[2] - t.cell[0], 3)
                     for t in placed if t.label and "field" in t.label})
    assert len(widths) >= 2  # not all equal
    xs = [t.cell[0] for t in placed if t.label and "field" in t.label]
    x1s = [t.cell[2] for t in placed if t.label and "field" in t.label]
    assert abs(min(xs) - mx) < 1e-6
    assert abs(max(x1s) - (W - mx)) < 1e-6


def test_row_gap_increases_row_pitch():
    dc = classlib.get("eob")
    base = layout(dc, random.Random(1))
    spaced = layout(fork(dc, layout=replace(dc.layout, row_gap=30)), random.Random(1))
    # Exclude wrapped-line tokens (they carry "seq" and span intra-row lines; those
    # would pollute the set with positions that reflect centering within a row rather
    # than the row's top, confusing the inter-row pitch comparison).
    def row_ys(p):
        return sorted({t.cell[1] for t in p
                       if t.label and t.label.get("record") is not None
                       and "seq" not in t.label})
    assert row_ys(spaced)[1] - row_ys(spaced)[0] > row_ys(base)[1] - row_ys(base)[0]


def test_oversized_gaps_fail_capacity_cleanly():
    dc = classlib.get("eob")
    huge = fork(dc, layout=replace(dc.layout, section_gap=5000, instance_gap=5000))
    try:
        validate_layout_capacity(huge)
        raised = False
    except LayoutCapacityError:
        raised = True
    assert raised


def test_globals_per_row_packs_pairs_and_stays_in_page():
    dc = classlib.get("eob")
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    paired = fork(dc, layout=replace(dc.layout, globals_per_row=2))
    placed = layout(paired, random.Random(0))
    gl = [t for t in placed if t.label and "global" in t.label]
    starts = sorted({round(t.cell[0], 3) for t in gl if t.label.get("header")})
    assert len(starts) == 2
    assert all(t.cell[2] <= W - mx + 1e-6 for t in gl)


def test_content_aware_columns_prevent_overflow():
    dc = classlib.get("eob")  # content-aware, jitter off by default
    placed = layout(dc, random.Random(0))
    _img, boxes = render(placed, dc)
    for p, b in zip(placed, boxes):
        if not _content_sized(p):
            continue  # only column-content-sized tokens; globals/span rows are separate
        cx0, _cy0, cx1, _cy1 = p.cell
        assert b[0] >= cx0 - 1 and b[2] <= cx1 + 1, (p.text, p.cell, b)


def test_eob_rich_columns_fit_at_template_width_with_header():
    # The eob class declares a wide page so its ten claim-line columns fit; verify
    # no data/header token overflows its cell when headers are on (the realistic build).
    # Banners and span rows (section/totals) are intentionally not column-content-sized
    # (see docs/specs/2026-06-14-spanning-cells-grouped-headers-design.md), so they are
    # excluded — only data + leaf-header containment is guaranteed.
    dc = classlib.get("eob")  # header is on by default in the eob recipe
    for seed in range(10):
        placed = layout(dc, random.Random(seed))
        _img, boxes = render(placed, dc)
        for p, b in zip(placed, boxes):
            if not _content_sized(p):
                continue
            cx0, _cy0, cx1, _cy1 = p.cell
            assert b[0] >= cx0 - 1 and b[2] <= cx1 + 1, (p.text, p.cell, b)


def test_fill_below_one_leaves_cells_empty():
    # A field with fill=0.0 is never populated, so it emits no data tokens.
    sparse = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(
            FieldSpec("a", "amount", "right", fill=0.0),
            FieldSpec("b", "amount", "right"),
        ), rows=(3, 3), instances=(1, 1)),
    ))
    placed = layout(sparse, random.Random(0))
    a_tokens = [p for p in placed if p.label and p.label.get("field") == 0
                and "record" in p.label]
    b_tokens = [p for p in placed if p.label and p.label.get("field") == 1
                and "record" in p.label]
    assert a_tokens == []      # fill=0.0 column is always empty
    assert len(b_tokens) == 3  # fill=1.0 column is always populated


def _field_overflow_count(dc, seeds):
    n = 0
    for s in seeds:
        placed = layout(dc, random.Random(s))
        _img, boxes = render(placed, dc)
        for p, b in zip(placed, boxes):
            if p.label and "field" in p.label:
                cx0, _cy0, cx1, _cy1 = p.cell
                if b[0] < cx0 - 1 or b[2] > cx1 + 1:
                    n += 1
    return n


def test_autoscale_font_fits_a_narrow_page():
    # eob's ten columns overflow a 1000px page at base font; autoscale shrinks the
    # font to fit, while the wide-page default is unaffected (font unchanged).
    base = classlib.get("eob")
    narrow = replace(base.layout, page=(1000, 1414))
    hdr = replace(base.structure, header=True)
    off = fork(base, layout=narrow, structure=hdr)
    on = fork(base, layout=narrow, structure=hdr,
              render=replace(base.render, autoscale_font=True))
    seeds = range(5)
    assert _field_overflow_count(off, seeds) > 0   # overflows without autoscale
    assert _field_overflow_count(on, seeds) == 0   # autoscale makes every column fit


def test_autoscale_noop_when_content_already_fits():
    # On the wide template page the content fits, so autoscale keeps the base font
    # and produces the same placement as without it.
    base = classlib.get("eob")
    hdr = replace(base.structure, header=True)
    off = layout(fork(base, structure=hdr), random.Random(1))
    on = layout(fork(base, structure=hdr, render=replace(base.render, autoscale_font=True)),
                random.Random(1))
    assert [p.font_size for p in on] == [p.font_size for p in off]
