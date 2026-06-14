import json
import random
from pathlib import Path

from tablelab import classes as classlib
from tablelab.layout import layout
from tablelab.render import render

GOLDEN = Path(__file__).parent / "golden" / "invoice_seed7_n3.json"


def _gen_tokens(cls_name: str, seed: int, n: int) -> list[list[dict]]:
    dc = classlib.get(cls_name)
    rng = random.Random(seed)
    W, H = dc.layout.page
    out: list[list[dict]] = []
    for _ in range(n):
        placed = layout(dc, rng)
        _img, boxes = render(placed, dc)
        out.append([
            {"x0": round(b[0] / W, 4), "y0": round(b[1] / H, 4),
             "x1": round(b[2] / W, 4), "y1": round(b[3] / H, 4),
             "text": p.text, "label": p.label}
            for p, b in zip(placed, boxes)
        ])
    return out


def test_invoice_matches_legacy_golden():
    got = _gen_tokens("invoice", seed=7, n=3)
    want = json.loads(GOLDEN.read_text())
    assert got == want
