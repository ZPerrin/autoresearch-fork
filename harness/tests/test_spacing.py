import random
from dataclasses import replace
from tablelab.fields import field_weight
from tablelab.specs import FieldSpec, TableSpec, DocumentClass, fork
from tablelab import classes as classlib
from tablelab.layout import layout, validate_layout_capacity, LayoutCapacityError
from tablelab.render import render

from _cells import placed, cells_where


def _content_sized_cells(cells):
    """Cells whose bbox is governed by content-aware column sizing: data or leaf-header
    cells. Banners (group_header), section, and summary (totals) rows are intentionally
    excluded (see the spanning-cells design)."""
    return [c for c in cells if c.role in ("data", "header")]


def test_field_weight_uses_explicit_override():
    assert field_weight(FieldSpec("amount", "amount", "right", width=3.0)) == 3.0


def test_field_weight_falls_back_to_type_default():
    assert field_weight(FieldSpec("desc", "description")) == 4.0


def test_field_weight_unknown_type_is_one():
    assert field_weight(FieldSpec("x", "totally_unknown_type")) == 1.0


def test_eob_columns_are_non_uniform_but_fill_page():
    dc = classlib.get("eob")
    W, mx = dc.layout.page[0], dc.layout.margin[0]
    _tokens, cells, _regions = placed(dc, seed=0)
    col_cells = _content_sized_cells(cells)
    widths = sorted({round(c.bbox[2] - c.bbox[0], 3) for c in col_cells})
    assert len(widths) >= 2  # not all equal
    xs = [c.bbox[0] for c in col_cells]
    x1s = [c.bbox[2] for c in col_cells]
    assert abs(min(xs) - mx) < 1e-6
    assert abs(max(x1s) - (W - mx)) < 1e-6


def test_row_gap_increases_row_pitch():
    dc = classlib.get("eob")
    _tokens_base, cells_base, _regions = placed(dc, seed=1)
    _tokens_spaced, cells_spaced, _regions2 = placed(
        fork(dc, layout=replace(dc.layout, row_gap=30)), seed=1)

    # Only data cells with a single token line (not wrapped multi-token rows) for
    # a clean inter-row pitch comparison.
    def row_ys(cells):
        data = cells_where(cells, role="data")
        # exclude wrapped cells (multiple vertical positions among token_ids)
        # for simplicity use cell bbox[1] (top of data row) deduped
        return sorted({round(c.bbox[1], 1) for c in data})

    assert row_ys(cells_spaced)[1] - row_ys(cells_spaced)[0] > \
           row_ys(cells_base)[1] - row_ys(cells_base)[0]


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
    _tokens, cells, _regions = placed(paired, seed=0)
    # key cells (global labels) should start at 2 distinct x positions when globals_per_row=2
    key_cells = cells_where(cells, role="key")
    starts = sorted({round(c.bbox[0], 3) for c in key_cells})
    assert len(starts) == 2
    # all global cells stay within the page
    all_global = key_cells + cells_where(cells, role="value")
    assert all(c.bbox[2] <= W - mx + 1e-6 for c in all_global)


def test_content_aware_columns_prevent_overflow():
    dc = classlib.get("eob")
    p_tokens = layout(dc, random.Random(0))
    _img, boxes = render(p_tokens, dc)
    _tokens, cells, _regions = placed(dc, seed=0)
    col_cells = _content_sized_cells(cells)
    for c in col_cells:
        cx0, _cy0, cx1, _cy1 = c.bbox
        for i in c.token_ids:
            b = boxes[i]
            assert b[0] >= cx0 - 1 and b[2] <= cx1 + 1, (p_tokens[i].text, c.bbox, b)


def test_eob_rich_columns_fit_at_template_width_with_header():
    # The eob class declares a wide page so its ten claim-line columns fit; verify
    # no data/header token overflows its cell when headers are on (the realistic build).
    dc = classlib.get("eob")  # header is on by default in the eob recipe
    for seed in range(10):
        p_tokens = layout(dc, random.Random(seed))
        _img, boxes = render(p_tokens, dc)
        _tokens, cells, _regions = placed(dc, seed=seed)
        col_cells = _content_sized_cells(cells)
        for c in col_cells:
            cx0, _cy0, cx1, _cy1 = c.bbox
            for i in c.token_ids:
                b = boxes[i]
                assert b[0] >= cx0 - 1 and b[2] <= cx1 + 1, (p_tokens[i].text, c.bbox, b)


def test_fill_below_one_leaves_cells_empty():
    # A field with fill=0.0 is never populated, so it emits data cells with no token_ids.
    sparse = DocumentClass(name="t", tables=(
        TableSpec(name="x", fields=(
            FieldSpec("a", "amount", "right", fill=0.0),
            FieldSpec("b", "amount", "right"),
        ), rows=(3, 3), instances=(1, 1)),
    ))
    _tokens, cells, _regions = placed(sparse, seed=0)
    a_cells = cells_where(cells, role="data", field="a")
    b_cells = cells_where(cells, role="data", field="b")
    # fill=0.0 column: all cells are empty (no token_ids)
    assert a_cells  # cells exist but are empty (sparse)
    assert all(len(c.token_ids) == 0 for c in a_cells)
    # fill=1.0 column: all cells are populated
    assert len(b_cells) == 3
    assert all(len(c.token_ids) > 0 for c in b_cells)


def _field_overflow_count(dc, seeds):
    n = 0
    for s in seeds:
        p_tokens = layout(dc, random.Random(s))
        _img, boxes = render(p_tokens, dc)
        _tokens, cells, _regions = placed(dc, seed=s)
        col_cells = _content_sized_cells(cells)
        for c in col_cells:
            cx0, _cy0, cx1, _cy1 = c.bbox
            for i in c.token_ids:
                b = boxes[i]
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
