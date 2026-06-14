from __future__ import annotations
import random
from dataclasses import dataclass

from .specs import DocumentClass
from .fields import sample


@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # cell rect in page pixels (x0, y0, x1, y1)
    label: dict | None                        # data {"record": r, "field": c} | header {"field": c, "header": True} (+ "seq": k when multi_token); null = background (future)
    align: str = "left"
    font_size: int = 22


def _header_text(name: str) -> str:
    """Field name → display header, e.g. 'unit_price' -> 'Unit Price'."""
    return name.replace("_", " ").title()


def _emit(placed: list[PlacedToken], text: str, cell: tuple[float, float, float, float],
          base_label: dict, align: str, font_size: int, multi: bool) -> None:
    """Append one token for `text`, or one per word (sharing cell + label, with seq) when multi."""
    if multi:
        for k, word in enumerate(text.split()):
            placed.append(PlacedToken(text=word, cell=cell,
                label={**base_label, "seq": k}, align=align, font_size=font_size))
    else:
        placed.append(PlacedToken(text=text, cell=cell,
            label=base_label, align=align, font_size=font_size))


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Preserves the legacy RNG
    sequence: randint(rows) -> sample() per data cell row-major -> shuffle. A header
    row (structure.header) is emitted above the data rows; multi-word values split
    into per-word tokens (structure.multi_token) sharing the cell's label + a seq."""
    L = dc.layout
    W = L.page[0]
    mx, my = L.margin
    C = len(dc.fields)
    cell_w = (W - 2 * mx) / C
    multi = dc.structure.multi_token
    header = dc.structure.header
    row_offset = 1 if header else 0
    rows = rng.randint(L.rows[0], L.rows[1])
    placed: list[PlacedToken] = []
    if header:
        for c in range(C):
            f = dc.fields[c]
            x0 = mx + c * cell_w
            cell = (x0, my, x0 + cell_w, my + L.row_h)
            _emit(placed, _header_text(f.name), cell,
                  {"field": c, "header": True}, f.align, dc.render.font_size, multi)
    for r in range(rows):
        for c in range(C):
            f = dc.fields[c]
            value = sample(f.type, rng)
            x0 = mx + c * cell_w
            y0 = my + (r + row_offset) * L.row_h
            cell = (x0, y0, x0 + cell_w, y0 + L.row_h)
            _emit(placed, value, cell,
                  {"record": r, "field": c}, f.align, dc.render.font_size, multi)
    rng.shuffle(placed)
    return placed
