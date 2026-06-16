import json
import random
from pathlib import Path

from tablelab import classes as classlib
from tablelab.layout import layout_with_regions
from tablelab.render import render

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _gen(cls_name: str, seed: int, n: int) -> list[dict]:
    dc = classlib.get(cls_name)
    rng = random.Random(seed)
    W, H = dc.layout.page
    out: list[dict] = []
    for _ in range(n):
        placed, cells, regions = layout_with_regions(dc, rng)
        _img, boxes = render(placed, dc)
        tokens = [{"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
                   "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4), "text": p.text}
                  for p, b in zip(placed, boxes)]
        out.append({
            "tokens": tokens,
            "cells": [{"region_index": c.region_index, "row_index": c.row_index,
                       "column_index": c.column_index, "span": list(c.span),
                       "role": c.role, "field": c.field, "token_ids": c.token_ids}
                      for c in cells],
            "regions": [{"type": r.type, "name": r.name, "index": r.index} for r in regions],
        })
    return out


def test_invoice_matches_golden():
    got = _gen("invoice", seed=7, n=3)
    want = json.loads(GOLDEN.read_text())
    assert got == want
