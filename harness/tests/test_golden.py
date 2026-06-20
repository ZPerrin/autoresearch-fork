import json
import random
from pathlib import Path

from tablelab import classes as classlib
from tablelab.layout import layout_with_targets
from tablelab.render import render

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _gen(cls_name: str, seed: int, n: int) -> list[dict]:
    dc = classlib.get(cls_name)
    rng = random.Random(seed)
    W, H = dc.layout.page
    out: list[dict] = []
    for _ in range(n):
        placed, cells, regions, targets = layout_with_targets(dc, rng)
        _img, boxes = render(placed, dc)
        words = [{"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
                  "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4), "text": p.text}
                 for p, b in zip(placed, boxes)]
        def _node(n):
            return {
                "fields": {k: {"value": f.value, "word_ids": f.word_ids, "cell": f.cell}
                           for k, f in n.fields.items()},
                "field_groups": {k: [_node(r) for r in recs]
                                 for k, recs in n.field_groups.items()},
            }
        out.append({
            "words": words,
            "cells": [{"region_index": c.region_index, "row_index": c.row_index,
                       "column_index": c.column_index, "span": list(c.span),
                       "role": c.role, "field": c.field, "word_ids": c.word_ids}
                      for c in cells],
            "regions": [{"type": r.type, "name": r.name, "index": r.index} for r in regions],
            "targets": {k: _node(v) for k, v in targets.items()},
        })
    return out


def test_invoice_matches_golden():
    got = _gen("invoice", seed=7, n=3)
    want = json.loads(GOLDEN.read_text())
    assert got == want
