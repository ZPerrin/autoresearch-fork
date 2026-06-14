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
    sequence: randint(rows) -> sample() per cell row-major -> shuffle. When
    structure.multi_token is set, a multi-word value becomes several tokens that
    share the cell's record/field and carry a within-cell order index (seq)."""
    L = dc.layout
    W = L.page[0]
    mx, my = L.margin
    C = len(dc.fields)
    cell_w = (W - 2 * mx) / C
    multi = dc.structure.multi_token
    rows = rng.randint(L.rows[0], L.rows[1])
    placed: list[PlacedToken] = []
    for r in range(rows):
        for c in range(C):
            f = dc.fields[c]
            value = sample(f.type, rng)
            x0 = mx + c * cell_w
            y0 = my + r * L.row_h
            cell = (x0, y0, x0 + cell_w, y0 + L.row_h)
            if multi:
                for k, word in enumerate(value.split()):
                    placed.append(PlacedToken(
                        text=word, cell=cell,
                        label={"record": r, "field": c, "seq": k},
                        align=f.align, font_size=dc.render.font_size))
            else:
                placed.append(PlacedToken(
                    text=value, cell=cell,
                    label={"record": r, "field": c},
                    align=f.align, font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
