from __future__ import annotations
import random
from dataclasses import dataclass
from itertools import product

from .specs import DocumentClass
from .fields import sample, background_token


class LayoutCapacityError(ValueError):
    pass


Shape = tuple[tuple[int, ...], ...]
_BACKGROUND_COLUMNS = 2


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


def _background_rows(count: int) -> int:
    return (count + _BACKGROUND_COLUMNS - 1) // _BACKGROUND_COLUMNS


def _validate_ranges(dc: DocumentClass) -> None:
    if dc.structure.background < 0:
        raise LayoutCapacityError(
            f"invalid background count: {dc.structure.background}"
        )
    for table in dc.tables:
        for name, bounds in (("instances", table.instances), ("rows", table.rows)):
            lo, hi = bounds
            if lo < 0 or hi < lo:
                raise LayoutCapacityError(
                    f"invalid {name} range for table {table.name!r}: {bounds!r}"
                )


def _fixed_height(dc: DocumentClass) -> int:
    L = dc.layout
    globals_height = len(dc.globals) * L.row_h
    if dc.globals:
        globals_height += L.table_gap
    return globals_height + _background_rows(dc.structure.background) * L.row_h


def _shape_height(dc: DocumentClass, shape: Shape) -> int:
    L = dc.layout
    header_rows = int(dc.structure.header)
    return sum(
        (header_rows + rows) * L.row_h + L.table_gap
        for table_shape in shape
        for rows in table_shape
    )


def _available_height(dc: DocumentClass) -> int:
    return dc.layout.page[1] - 2 * dc.layout.margin[1]


def _is_safe_legacy(dc: DocumentClass) -> bool:
    if not (
        len(dc.tables) == 1
        and not dc.globals
        and not dc.structure.header
        and dc.structure.background == 0
        and dc.tables[0].instances == (1, 1)
    ):
        return False
    maximum = ((dc.tables[0].rows[1],),)
    return _fixed_height(dc) + _shape_height(dc, maximum) <= _available_height(dc)


def _table_shapes(table) -> list[tuple[int, ...]]:
    row_counts = range(table.rows[0], table.rows[1] + 1)
    return [
        rows
        for instances in range(table.instances[0], table.instances[1] + 1)
        for rows in product(row_counts, repeat=instances)
    ]


def _capacity_error(dc: DocumentClass, available: int, fixed: int) -> LayoutCapacityError:
    table_minimums = ", ".join(
        f"{table.name}: minimum instances={table.instances[0]}, rows={table.rows[0]}"
        for table in dc.tables
    ) or "none"
    return LayoutCapacityError(
        "no page-feasible document shape: "
        f"page={dc.layout.page}, available={available}px, fixed={fixed}px, "
        f"globals={len(dc.globals)}, header={dc.structure.header}, "
        f"background={dc.structure.background}, tables=[{table_minimums}]"
    )


def _feasible_shapes(dc: DocumentClass) -> list[Shape]:
    _validate_ranges(dc)
    available = _available_height(dc)
    fixed = _fixed_height(dc)
    table_shapes = [_table_shapes(table) for table in dc.tables]
    return [
        shape
        for shape in product(*table_shapes)
        if fixed + _shape_height(dc, shape) <= available
    ]


def _choose_shape(dc: DocumentClass, rng: random.Random) -> Shape:
    _validate_ranges(dc)
    if _is_safe_legacy(dc):
        table = dc.tables[0]
        return ((rng.randint(table.rows[0], table.rows[1]),),)

    feasible = _feasible_shapes(dc)
    if not feasible:
        raise _capacity_error(dc, _available_height(dc), _fixed_height(dc))
    return rng.choice(feasible)


def validate_layout_capacity(dc: DocumentClass) -> None:
    """Raise when no declared document shape can fit within the page height."""
    _validate_ranges(dc)
    if _is_safe_legacy(dc):
        return
    if not _feasible_shapes(dc):
        raise _capacity_error(dc, _available_height(dc), _fixed_height(dc))


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Place one document's tokens (logical, no Pillow). Global/singleton fields
    (dc.globals) are laid out first as label:value rows at the top; then each table
    is drawn as stacked instances with table_gap, tagged with a
    region when the class is multi-instance. Header rows (structure.header),
    multi-token split (structure.multi_token) and background tokens
    (structure.background) apply as before. The single-table, single-instance path
    without globals, headers, or background remains byte-identical when its maximum
    row count fits the page."""
    L = dc.layout
    W, H = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    shape = _choose_shape(dc, rng)
    multi_region = len(dc.tables) > 1 or sum(t.instances[1] for t in dc.tables) > 1
    placed: list[PlacedToken] = []
    y = float(my)
    if dc.globals:
        gw = (W - 2 * mx) * 0.35
        for f in dc.globals:
            label_cell = (mx, y, mx + gw, y + L.row_h)
            _emit(placed, _header_text(f.name) + ":", label_cell,
                  {"global": f.name, "header": True}, "left", dc.render.font_size, multi)
            value_cell = (mx + gw, y, W - mx, y + L.row_h)
            _emit(placed, sample(f.type, rng), value_cell,
                  {"global": f.name}, "left", dc.render.font_size, multi)
            y += L.row_h
        y += L.table_gap
    region = 0
    for table, table_shape in zip(dc.tables, shape):
        if not table_shape:
            continue
        C = len(table.fields)
        cell_w = (W - 2 * mx) / C
        for rows in table_shape:
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
        if y_hi <= y_lo:  # content fills the page; fall back to the full interior
            y_lo, y_hi = float(my), float(H - my - L.row_h)
        for _ in range(n_bg):
            bx = rng.uniform(mx, W - mx - 80)
            by = rng.uniform(y_lo, y_hi)
            cell = (bx, by, bx + 80, by + L.row_h)
            placed.append(PlacedToken(
                text=background_token(dc.background_terms, rng), cell=cell, label=None,
                align="left", font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
