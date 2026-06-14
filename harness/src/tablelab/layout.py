from __future__ import annotations
import random
from dataclasses import dataclass

from .fields import sample, background_token
from .specs import DocumentClass, TableSpec


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


def _validate_layout(dc: DocumentClass) -> None:
    L = dc.layout
    width, height = L.page
    mx, my = L.margin
    if width <= 0 or height <= 0:
        raise LayoutCapacityError(
            f"invalid page dimensions: page={L.page}; width and height must be positive"
        )
    if mx < 0 or my < 0:
        raise LayoutCapacityError(
            f"invalid margins: margin={L.margin}; margins must be nonnegative"
        )
    if L.row_h <= 0:
        raise LayoutCapacityError(
            f"invalid row height: row_h={L.row_h}; row_h must be positive"
        )
    if L.table_gap < 0:
        raise LayoutCapacityError(
            f"invalid table gap: table_gap={L.table_gap}; table_gap must be nonnegative"
        )
    usable_width = width - 2 * mx
    if usable_width <= 0:
        raise LayoutCapacityError(
            f"invalid usable page width: page={L.page}, margin={L.margin}, "
            f"usable_width={usable_width}px"
        )
    available = height - 2 * my
    if available <= 0:
        raise LayoutCapacityError(
            f"invalid available page height: page={L.page}, margin={L.margin}, "
            f"available={available}px"
        )
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
        if table.instances[1] > 0 and not table.fields:
            raise LayoutCapacityError(
                f"table {table.name!r} allows up to {table.instances[1]} instances "
                "but has no fields"
            )
        if (
            table.instances[1] > 0
            and not dc.structure.header
            and table.rows[0] == 0
            and L.table_gap == 0
        ):
            raise LayoutCapacityError(
                f"table {table.name!r} can emit zero-height instances: "
                f"instances={table.instances}, rows={table.rows}, "
                f"header={dc.structure.header}, table_gap={L.table_gap}"
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


def _instance_height(dc: DocumentClass, rows: int) -> int:
    return (int(dc.structure.header) + rows) * dc.layout.row_h + dc.layout.table_gap


def _minimum_shape_height(dc: DocumentClass) -> int:
    return sum(
        table.instances[0] * _instance_height(dc, table.rows[0])
        for table in dc.tables
    )


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


def _iter_table_shapes(
    dc: DocumentClass,
    table: TableSpec,
    instances: int,
    budget: int,
):
    minimum_instance = _instance_height(dc, table.rows[0])
    stack = [((), 0)]
    while stack:
        rows, used = stack.pop()
        remaining = instances - len(rows)
        if used + remaining * minimum_instance > budget:
            continue
        if not remaining:
            yield rows, used
            continue
        for row_count in range(table.rows[1], table.rows[0] - 1, -1):
            height = _instance_height(dc, row_count)
            if used + height > budget:
                continue
            stack.append(((*rows, row_count), used + height))


def _iter_feasible_shapes(dc: DocumentClass):
    budget = _available_height(dc) - _fixed_height(dc)
    minimum_by_table = [
        table.instances[0] * _instance_height(dc, table.rows[0])
        for table in dc.tables
    ]
    minimum_suffix = [0] * (len(dc.tables) + 1)
    for index in range(len(dc.tables) - 1, -1, -1):
        minimum_suffix[index] = minimum_by_table[index] + minimum_suffix[index + 1]

    def table_options(table_index: int, used: int):
        table = dc.tables[table_index]
        remaining_budget = budget - used - minimum_suffix[table_index + 1]
        for instances in range(table.instances[0], table.instances[1] + 1):
            minimum = instances * _instance_height(dc, table.rows[0])
            if minimum > remaining_budget:
                break
            for table_shape, table_height in _iter_table_shapes(
                dc, table, instances, remaining_budget
            ):
                yield table_shape, table_height

    stack = [(0, (), 0, None)]
    while stack:
        table_index, shape, used, options = stack[-1]
        if used + minimum_suffix[table_index] > budget:
            stack.pop()
            continue
        if table_index == len(dc.tables):
            stack.pop()
            yield shape
            continue
        if options is None:
            options = iter(table_options(table_index, used))
            stack[-1] = (table_index, shape, used, options)
        try:
            table_shape, table_height = next(options)
        except StopIteration:
            stack.pop()
            continue
        stack.append((
            table_index + 1,
            (*shape, table_shape),
            used + table_height,
            None,
        ))


def _ensure_minimum_fits(dc: DocumentClass) -> None:
    available = _available_height(dc)
    fixed = _fixed_height(dc)
    if fixed + _minimum_shape_height(dc) > available:
        raise _capacity_error(dc, available, fixed)


def _choose_shape(dc: DocumentClass, rng: random.Random) -> Shape:
    _validate_layout(dc)
    if _is_safe_legacy(dc):
        table = dc.tables[0]
        return ((rng.randint(table.rows[0], table.rows[1]),),)

    _ensure_minimum_fits(dc)
    chosen = None
    count = 0
    for shape in _iter_feasible_shapes(dc):
        count += 1
        if rng.randrange(count) == 0:
            chosen = shape
    if chosen is None:
        raise _capacity_error(dc, _available_height(dc), _fixed_height(dc))
    return chosen


def validate_layout_capacity(dc: DocumentClass) -> None:
    """Raise when no declared document shape can fit within the page height."""
    _validate_layout(dc)
    if _is_safe_legacy(dc):
        return
    _ensure_minimum_fits(dc)
    if next(_iter_feasible_shapes(dc), None) is None:
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
    W, _ = L.page
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
        columns = min(_BACKGROUND_COLUMNS, n_bg)
        slot_w = (W - 2 * mx) / columns
        for i in range(n_bg):
            row, col = divmod(i, columns)
            x0 = mx + col * slot_w
            cell = (x0, y + row * L.row_h,
                    x0 + slot_w, y + (row + 1) * L.row_h)
            placed.append(PlacedToken(
                text=background_token(dc.background_terms, rng), cell=cell, label=None,
                align="left", font_size=dc.render.font_size))
    rng.shuffle(placed)
    return placed
