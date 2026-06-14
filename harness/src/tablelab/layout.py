from __future__ import annotations
import random
from dataclasses import dataclass

from .specs import DocumentClass
from .fields import sample


@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # cell rect in page pixels (x0, y0, x1, y1)
    label: dict | None                        # {"record": r, "field": c}; null = background (future)
    align: str = "left"
    font_size: int = 22


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Preserves the legacy RNG
    sequence: randint(rows) -> sample() per cell row-major -> shuffle."""
    L = dc.layout
    W = L.page[0]
    mx, my = L.margin
    C = len(dc.fields)
    cell_w = (W - 2 * mx) / C
    rows = rng.randint(L.rows[0], L.rows[1])
    placed: list[PlacedToken] = []
    for r in range(rows):
        for c in range(C):
            f = dc.fields[c]
            s = sample(f.type, rng)
            x0 = mx + c * cell_w
            y0 = my + r * L.row_h
            placed.append(PlacedToken(
                text=s, cell=(x0, y0, x0 + cell_w, y0 + L.row_h),
                label={"record": r, "field": c}, align=f.align,
                font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
