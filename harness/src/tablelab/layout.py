from __future__ import annotations
import random
from dataclasses import dataclass

from .specs import DocumentClass
from .fields import sample, background_token


@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # cell rect in page pixels (x0, y0, x1, y1)
    label: dict | None                        # data {"record": r, "field": c} | header {"field": c, "header": True}; + "region": g when multi-instance, + "seq": k when multi_token; null = background
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
    """Place one document's tokens (logical, no Pillow). Iterates dc.tables with a
    vertical cursor, drawing randint(instances) copies of each table stacked with
    table_gap. When the class is multi-instance (more than one possible table
    instance), data and header labels gain a 0-based ``region`` index. Single
    table/instance output is byte-identical to the prior builder. Header rows
    (structure.header), multi-token split (structure.multi_token) and background
    tokens (structure.background) apply as before."""
    L = dc.layout
    W, H = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    multi_region = len(dc.tables) > 1 or sum(t.instances[1] for t in dc.tables) > 1
    placed: list[PlacedToken] = []
    y = float(my)
    region = 0
    for table in dc.tables:
        C = len(table.fields)
        cell_w = (W - 2 * mx) / C
        lo, hi = table.instances
        instances = lo if lo == hi else rng.randint(lo, hi)
        for _inst in range(instances):
            rows = rng.randint(table.rows[0], table.rows[1])
            reg = {"region": region} if multi_region else {}
            if header:
                for c in range(C):
                    f = table.fields[c]
                    x0 = mx + c * cell_w
                    cell = (x0, y, x0 + cell_w, y + L.row_h)
                    _emit(placed, _header_text(f.name), cell,
                          {**reg, "field": c, "header": True}, f.align, dc.render.font_size, multi)
                y += L.row_h
            for r in range(rows):
                for c in range(C):
                    f = table.fields[c]
                    value = sample(f.type, rng)
                    x0 = mx + c * cell_w
                    cell = (x0, y, x0 + cell_w, y + L.row_h)
                    _emit(placed, value, cell,
                          {**reg, "record": r, "field": c}, f.align, dc.render.font_size, multi)
                y += L.row_h
            y += L.table_gap
            region += 1
    n_bg = dc.structure.background
    if n_bg:
        y_lo, y_hi = y, H - my - L.row_h
        if y_hi <= y_lo:  # tables fill the page; fall back to the full interior
            y_lo, y_hi = float(my), float(H - my - L.row_h)
        for _ in range(n_bg):
            bx = rng.uniform(mx, W - mx - 80)
            by = rng.uniform(y_lo, y_hi)
            cell = (bx, by, bx + 80, by + L.row_h)
            placed.append(PlacedToken(
                text=background_token(rng), cell=cell, label=None,
                align="left", font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
