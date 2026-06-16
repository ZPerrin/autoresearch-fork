import json, random
from dataclasses import replace
from pathlib import Path

from tablelab import classes as classlib
from tablelab.specs import fork, JitterSpec
from tablelab.layout import layout, layout_with_regions
from tablelab.render import render

from _cells import cells_where

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _tokens(dc, seed, n):
    rng = random.Random(seed)
    W, H = dc.layout.page
    out = []
    for _ in range(n):
        placed = layout(dc, rng)
        _img, boxes = render(placed, dc)
        out.append([
            {"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
             "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4),
             "text": p.text}
            for p, b in zip(placed, boxes)])
    return out


def test_jitter_off_is_byte_identical_to_golden():
    dc = fork(classlib.get("invoice"), jitter=JitterSpec())
    golden = json.loads(GOLDEN.read_text())
    assert _tokens(dc, 7, 3) == [s["tokens"] for s in golden]


def test_jitter_keeps_every_box_in_page():
    base = classlib.get("eob")
    dc = fork(base, layout=replace(base.layout, row_gap=24),
              jitter=JitterSpec(row_h=0.4, col_w=0.4, offset=0.8, baseline=0.5))
    W, H = dc.layout.page
    for seed in range(100):
        placed = layout(dc, random.Random(seed))
        _img, boxes = render(placed, dc)
        for (x0, y0, x1, y1) in boxes:
            assert 0 <= x0 <= x1 <= W
            assert 0 <= y0 <= y1 <= H


def test_columns_stay_zero_sum_under_col_jitter():
    base = classlib.get("eob")
    W, mx = base.layout.page[0], base.layout.margin[0]
    dc = fork(base, jitter=JitterSpec(col_w=0.5))
    tokens, cells, _regions = layout_with_regions(dc, random.Random(3))
    # data and header cells: column-content-sized tokens; filter to those roles
    col_cells = [c for c in cells if c.role in ("data", "header")]
    xs = [c.bbox[0] for c in col_cells]
    x1s = [c.bbox[2] for c in col_cells]
    assert abs(min(xs) - mx) < 1e-6 and abs(max(x1s) - (W - mx)) < 1e-6
