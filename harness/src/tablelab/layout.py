from __future__ import annotations
import random
from dataclasses import dataclass, replace

from .fields import sample, background_token, field_weight
from .jitter import jitter_column_edges, jitter_row_height, jitter_offset
from .metrics import text_width
from .specs import DocumentClass, TableSpec


class LayoutCapacityError(ValueError):
    pass


Shape = tuple[tuple[int, ...], ...]
_BACKGROUND_COLUMNS = 2


def _row_gap(dc) -> int:
    return dc.layout.row_gap

def _instance_gap(dc) -> int:
    L = dc.layout
    return L.instance_gap if L.instance_gap is not None else L.table_gap

def _section_gap(dc) -> int:
    L = dc.layout
    return L.section_gap if L.section_gap is not None else L.table_gap


def _column_edges(fields, usable: float, mx: float) -> list[float]:
    """Left/right pixel edges for each column from normalized field weights.
    Returns len(fields)+1 edges; columns sum to exactly `usable` by construction."""
    weights = [field_weight(f) for f in fields]
    total = sum(weights)
    edges = [mx]
    acc = 0.0
    for w in weights:
        acc += w
        edges.append(mx + usable * (acc / total))
    return edges


def _fit_font(fields, usable: float, pad: int, header: bool, grid: list[list[str]],
              base_font: int, min_font: int = 6, safety: float = 0.95) -> int:
    """Largest font (<= base) at which the columns' content fits the usable width.
    Sums each column's widest content (header + populated cells); leaves the fixed
    padding out of the scale and keeps a safety margin so the re-measured widths fit
    without tripping the degenerate column-scale. Returns base_font when it already fits.
    A field with max_width set has its contribution capped at max_width - 2*pad so that
    a column that will wrap does not needlessly trigger a font shrink."""
    text_total = 0.0
    for c, f in enumerate(fields):
        texts = [row[c] for row in grid if row[c]]
        if header:
            texts.append(_header_text(f.name))
        if texts:
            longest = max(text_width(t, base_font) for t in texts)
            if f.max_width is not None:
                longest = min(longest, max(f.max_width - 2 * pad, 0.0))
            text_total += longest
    avail = usable - len(fields) * 2 * pad
    if text_total <= 0:
        return base_font
    if avail <= 0:
        return min_font
    if text_total <= avail:
        return base_font  # already fits at base font; autoscale is a no-op
    k = safety * avail / text_total  # overflow: shrink with a margin so it fits
    return max(min_font, round(base_font * k))


def _content_column_widths(fields, usable: float, pad: int, header: bool,
                           grid: list[list[str]], font_size: int) -> list[float]:
    """Content floor + weighted slack. Each column is at least wide enough for the
    widest of its header label and sampled values (plus padding); a field with
    max_width is frozen at min(content_floor, max_width) and excluded from slack, so
    its value wraps. Leftover usable width is shared across the remaining columns by
    weight, so the table still fills the page."""
    mins = []
    capped: set[int] = set()
    for c, f in enumerate(fields):
        texts = [row[c] for row in grid]
        if header:
            texts.append(_header_text(f.name))
        longest = max((text_width(t, font_size) for t in texts), default=0.0)
        floor = longest + 2 * pad
        if f.max_width is not None:
            floor = min(floor, float(f.max_width))
            capped.add(c)
        mins.append(floor)
    total_min = sum(mins)
    if total_min >= usable:
        scale = usable / total_min if total_min > 0 else 1.0
        return [m * scale for m in mins]
    slack = usable - total_min
    weights = [0.0 if c in capped else field_weight(f) for c, f in enumerate(fields)]
    wtotal = sum(weights)
    if wtotal <= 0:  # every column capped: fall back to weighting all so the table fills
        weights = [field_weight(f) for f in fields]
        wtotal = sum(weights) or 1.0
    return [mins[c] + slack * weights[c] / wtotal for c in range(len(fields))]


def _resolve_column_edges(fields, usable: float, mx: float, pad: int, header: bool,
                          grid: list[list[str]], font_size: int) -> list[float]:
    """Pixel edges (len(fields)+1). Tables whose fields all carry an explicit width
    use pure weighted division (byte-identical legacy path, e.g. invoice); otherwise
    columns are content-aware sized."""
    if all(f.width is not None for f in fields):
        return _column_edges(fields, usable, mx)
    widths = _content_column_widths(fields, usable, pad, header, grid, font_size)
    edges = [mx]
    acc = 0.0
    for w in widths:
        acc += w
        edges.append(mx + acc)
    return edges


@dataclass
class PlacedToken:
    text: str
    cell: tuple[float, float, float, float]   # cell rect in page pixels (x0, y0, x1, y1)
    label: dict | None                        # data {"record": r, "field": c} | header {"field": c, "header": True}; + "region": g when multi-instance, + "seq": k when multi_token; null = background
    align: str = "left"
    font_size: int = 22
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class PlacedRegion:
    region: int                                # matches the {"region": k} token label
    table: str                                 # table name (e.g. "claim_line")
    bbox: tuple[float, float, float, float]    # page px (x0, y0, x1, y1)


def _header_text(name: str) -> str:
    """Field name → display header, e.g. 'unit_price' -> 'Unit Price'."""
    return name.replace("_", " ").title()


def _line_h(dc: DocumentClass) -> int:
    """Intra-cell wrapped-line height: explicit LayoutSpec.line_h, else font-scaled.
    Kept below the default row_h so a single-line row keeps height row_h."""
    L = dc.layout
    return L.line_h if L.line_h is not None else round(dc.render.font_size * 1.4)


def _resolve_row_h(dc: DocumentClass) -> DocumentClass:
    """Materialize a font-derived row_h when LayoutSpec.row_h is None (the default),
    so all downstream reads of dc.layout.row_h see a concrete px height. Explicit
    values (including invalid 0/-1, caught by _validate_layout) pass through untouched.
    Font-derived default keeps rows dense relative to the glyph (~1.7x font height)
    instead of carrying a magic absolute height that strands wide-font classes."""
    if dc.layout.row_h is not None:
        return dc
    return replace(dc, layout=replace(dc.layout, row_h=round(dc.render.font_size * 1.7)))


def _wrap(words: list[str], col_width: float, font_size: int) -> list[list[str]]:
    """Greedy word-wrap: pack words into lines no wider than col_width px. A single word
    wider than col_width gets its own line (never split mid-word). Order is preserved."""
    lines: list[list[str]] = []
    cur: list[str] = []
    cur_w = 0.0
    space = text_width(" ", font_size)
    for w in words:
        ww = text_width(w, font_size)
        if not cur:
            cur, cur_w = [w], ww
        elif cur_w + space + ww <= col_width:
            cur.append(w)
            cur_w += space + ww
        else:
            lines.append(cur)
            cur, cur_w = [w], ww
    if cur:
        lines.append(cur)
    return lines


def _group_runs(fields) -> list[tuple[str, int, int]]:
    """Maximal runs of equal non-None FieldSpec.group → (name, c0, c1) inclusive ranges.
    Ungrouped (group=None) columns are skipped (they get no banner cell)."""
    runs: list[tuple[str, int, int]] = []
    i, n = 0, len(fields)
    while i < n:
        g = fields[i].group
        j = i
        while j + 1 < n and fields[j + 1].group == g:
            j += 1
        if g is not None:
            runs.append((g, i, j))
        i = j + 1
    return runs


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


def _emit_span_row(placed: list[PlacedToken], cells, edges, y: float, row_h: float,
                   base_label: dict, font: int, multi: bool, rng: random.Random,
                   header_on_text: bool = False) -> None:
    """Emit one spanning row: each cell covers a contiguous column range starting at the
    running column index. text cells are literal, type cells are sampled (RNG drawn left to
    right), empty cells emit nothing. Each token gets field=c0 and span=[c0, c1]; a literal
    label additionally gets header=True when ``header_on_text`` (the totals label cell)."""
    c = 0
    for cell in cells:
        c0, c1 = c, c + cell.span - 1
        rect = (edges[c0], y, edges[c1 + 1], y + row_h)
        if cell.text is not None:
            value, is_text = cell.text, True
        elif cell.type is not None:
            value, is_text = sample(cell.type, rng), False
        else:
            value, is_text = "", False
        if value:
            label = {**base_label, "field": c0, "span": [c0, c1]}
            if is_text and header_on_text:
                label["header"] = True
            _emit(placed, value, rect, label, cell.align, font, multi)
        c = c1 + 1


def _sample_cell(field, rng: random.Random) -> str:
    """Sample a data cell's value, honoring sparsity: a field with fill < 1.0 leaves
    some cells empty. fill >= 1.0 samples directly (no extra RNG draw), so existing
    classes are byte-identical."""
    if field.fill >= 1.0:
        return sample(field.type, rng)
    return sample(field.type, rng) if rng.random() < field.fill else ""


def _background_rows(count: int) -> int:
    return (count + _BACKGROUND_COLUMNS - 1) // _BACKGROUND_COLUMNS


def _validate_span_rows(dc: DocumentClass, table: TableSpec) -> None:
    """Grouped-header banners need a leaf header row; each span row's cells must tile the
    columns exactly and each cell is text-xor-type (or empty)."""
    C = len(table.fields)
    if any(f.group for f in table.fields) and not dc.structure.header:
        raise LayoutCapacityError(
            f"table {table.name!r} sets field group(s) but structure.header is off; "
            "grouped-header banners require a leaf header row"
        )
    for slot, srow in (("section", table.section), ("totals", table.totals)):
        if srow is None:
            continue
        total = 0
        for cell in srow.cells:
            if cell.span < 1:
                raise LayoutCapacityError(
                    f"table {table.name!r} {slot} cell span {cell.span} < 1"
                )
            if cell.text is not None and cell.type is not None:
                raise LayoutCapacityError(
                    f"table {table.name!r} {slot} cell sets both text and type"
                )
            total += cell.span
        if total != C:
            raise LayoutCapacityError(
                f"table {table.name!r} {slot} spans sum to {total}, expected {C}"
            )


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
        _validate_span_rows(dc, table)
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
    gpr = max(L.globals_per_row, 1)
    n_global_rows = (len(dc.globals) + gpr - 1) // gpr
    globals_height = n_global_rows * L.row_h
    if dc.globals:
        globals_height += _section_gap(dc)
    return globals_height + _background_rows(dc.structure.background) * L.row_h


def _shape_height(dc: DocumentClass, shape: Shape) -> int:
    return sum(_instance_height(dc, rows, table)
               for table, table_shape in zip(dc.tables, shape) for rows in table_shape)


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


def _data_row_h(dc: DocumentClass, table: TableSpec | None) -> int:
    """Reserved height of one data row: row_h, grown to the worst-case wrapped height
    (max field max_lines * line_h) so capacity planning never underestimates."""
    if table is None:
        return dc.layout.row_h
    max_lines = max((f.max_lines for f in table.fields), default=1)
    return max(dc.layout.row_h, max_lines * _line_h(dc))


def _instance_height(dc: DocumentClass, rows: int, table: TableSpec | None = None) -> int:
    L = dc.layout
    header = int(dc.structure.header)
    banner = section = totals = 0
    if table is not None:
        banner = header * int(any(f.group for f in table.fields))
        section = int(table.section is not None)
        totals = int(table.totals is not None)
    fixed_rows = header + banner + section + totals
    return (fixed_rows * L.row_h + rows * _data_row_h(dc, table)
            + max(rows - 1, 0) * _row_gap(dc) + _instance_gap(dc))


def _minimum_shape_height(dc: DocumentClass) -> int:
    return sum(
        table.instances[0] * _instance_height(dc, table.rows[0], table)
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
    minimum_instance = _instance_height(dc, table.rows[0], table)
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
            height = _instance_height(dc, row_count, table)
            if used + height > budget:
                continue
            stack.append(((*rows, row_count), used + height))


def _iter_feasible_shapes(dc: DocumentClass):
    budget = _available_height(dc) - _fixed_height(dc)
    minimum_by_table = [
        table.instances[0] * _instance_height(dc, table.rows[0], table)
        for table in dc.tables
    ]
    minimum_suffix = [0] * (len(dc.tables) + 1)
    for index in range(len(dc.tables) - 1, -1, -1):
        minimum_suffix[index] = minimum_by_table[index] + minimum_suffix[index + 1]

    def table_options(table_index: int, used: int):
        table = dc.tables[table_index]
        remaining_budget = budget - used - minimum_suffix[table_index + 1]
        for instances in range(table.instances[0], table.instances[1] + 1):
            minimum = instances * _instance_height(dc, table.rows[0], table)
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
    dc = _resolve_row_h(dc)
    _validate_layout(dc)
    if _is_safe_legacy(dc):
        return
    _ensure_minimum_fits(dc)
    if next(_iter_feasible_shapes(dc), None) is None:
        raise _capacity_error(dc, _available_height(dc), _fixed_height(dc))


def layout_with_regions(dc: DocumentClass, rng: random.Random) -> tuple[list[PlacedToken], list[PlacedRegion]]:
    """Place one document's tokens (logical, no Pillow). Global/singleton fields
    (dc.globals) are laid out first as label:value rows at the top; then each table
    is drawn as stacked instances with table_gap, tagged with a
    region when the class is multi-instance. Header rows (structure.header),
    multi-token split (structure.multi_token) and background tokens
    (structure.background) apply as before. The single-table, single-instance path
    without globals, headers, or background remains byte-identical when its maximum
    row count fits the page."""
    dc = _resolve_row_h(dc)
    L = dc.layout
    W, _ = L.page
    mx, my = L.margin
    multi = dc.structure.multi_token
    header = dc.structure.header
    J = dc.jitter
    shape = _choose_shape(dc, rng)
    multi_region = len(dc.tables) > 1 or sum(t.instances[1] for t in dc.tables) > 1
    placed: list[PlacedToken] = []
    regions: list[PlacedRegion] = []
    y = float(my)
    if dc.globals:
        gpr = max(L.globals_per_row, 1)
        usable = W - 2 * mx
        pair_w = usable / gpr
        for i, f in enumerate(dc.globals):
            col = i % gpr
            if i and col == 0:
                y += L.row_h
            px0 = mx + col * pair_w
            gw = pair_w * 0.35
            label_cell = (px0, y, px0 + gw, y + L.row_h)
            _emit(placed, _header_text(f.name) + ":", label_cell,
                  {"global": f.name, "header": True}, "left", dc.render.font_size, multi)
            value_cell = (px0 + gw, y, px0 + pair_w, y + L.row_h)
            _emit(placed, sample(f.type, rng), value_cell,
                  {"global": f.name}, "left", dc.render.font_size, multi)
        y += L.row_h
        y += _section_gap(dc)
    region = 0
    for table, table_shape in zip(dc.tables, shape):
        if not table_shape:
            continue
        C = len(table.fields)
        explicit_widths = all(f.width is not None for f in table.fields)
        for rows in table_shape:
            y_start = y
            reg = {"region": region} if multi_region else {}
            grid = [[_sample_cell(table.fields[c], rng) for c in range(C)]
                    for _ in range(rows)]
            cell_font = dc.render.font_size
            if dc.render.autoscale_font and not explicit_widths:
                cell_font = _fit_font(table.fields, W - 2 * mx, L.pad, header,
                                      grid, dc.render.font_size)
            edges = _resolve_column_edges(table.fields, W - 2 * mx, mx, L.pad,
                                          header, grid, cell_font)
            if header and any(f.group for f in table.fields):
                for name, c0, c1 in _group_runs(table.fields):
                    cell = (edges[c0], y, edges[c1 + 1], y + L.row_h)
                    _emit(placed, name, cell,
                          {**reg, "field": c0, "header": True,
                           "group": name, "span": [c0, c1]},
                          "left", cell_font, multi)
                y += L.row_h
            if header:
                for c in range(C):
                    f = table.fields[c]
                    x0, x1 = edges[c], edges[c + 1]
                    cell = (x0, y, x1, y + L.row_h)
                    _emit(placed, _header_text(f.name), cell,
                          {**reg, "field": c, "header": True}, f.align, cell_font, multi)
                y += L.row_h
            if table.section is not None:
                _emit_span_row(placed, table.section.cells, edges, y, L.row_h,
                               {**reg, "section": True}, cell_font, multi, rng)
                y += L.row_h
            line_h = _line_h(dc)
            for r in range(rows):
                row_edges = (jitter_column_edges(edges, J.col_w, rng)
                             if J.col_w > 0 else edges)
                # Content-aware height: a wrappable cell that wraps to N lines grows the row.
                row_lines = 1
                for c in range(C):
                    f = table.fields[c]
                    v = grid[r][c]
                    if f.max_width is not None and v:
                        col_text_w = (row_edges[c + 1] - row_edges[c]) - 2 * L.pad
                        row_lines = max(row_lines, len(_wrap(v.split(), col_text_w, cell_font)))
                base_h = max(L.row_h, row_lines * line_h)
                cell_h = base_h
                gap_after = _row_gap(dc)
                # Height jitter is zero-sum against the trailing gap, so it must skip the
                # last row (which has no trailing gap) or the instance grows past its
                # reserved budget and can overrun the page.
                if J.row_h > 0 and _row_gap(dc) > 0 and r < rows - 1:
                    cell_h, delta = jitter_row_height(base_h, J.row_h, _row_gap(dc), rng)
                    gap_after = _row_gap(dc) + delta
                for c in range(C):
                    f = table.fields[c]
                    value = grid[r][c]
                    if not value:
                        continue  # sparse cell: leave it empty, emit no token
                    x0, x1 = row_edges[c], row_edges[c + 1]
                    if f.max_width is not None:
                        col_text_w = (x1 - x0) - 2 * L.pad
                        lines = _wrap(value.split(), col_text_w, cell_font)
                        block_h = len(lines) * line_h
                        top = y + (cell_h - block_h) / 2
                        seq = 0
                        for k, words in enumerate(lines):
                            ly0 = top + k * line_h
                            line_cell = (x0, ly0, x1, ly0 + line_h)
                            for w in words:
                                placed.append(PlacedToken(
                                    text=w, cell=line_cell,
                                    label={**reg, "record": r, "field": c, "seq": seq},
                                    align=f.align, font_size=cell_font))
                                seq += 1
                    else:
                        cell = (x0, y, x1, y + cell_h)
                        _emit(placed, value, cell,
                              {**reg, "record": r, "field": c}, f.align, cell_font, multi)
                y += cell_h
                if r < rows - 1:
                    y += gap_after
            if table.totals is not None:
                _emit_span_row(placed, table.totals.cells, edges, y, L.row_h,
                               {**reg, "subtotal": True}, cell_font, multi, rng,
                               header_on_text=True)
                y += L.row_h
            regions.append(PlacedRegion(
                region=region, table=table.name,
                bbox=(edges[0], y_start, edges[-1], y)))
            y += _instance_gap(dc)
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
    if J.offset > 0 or J.baseline > 0:
        for p in placed:
            p.dx, p.dy = jitter_offset(J.offset, J.baseline, L.pad, rng)
    rng.shuffle(placed)
    return placed, regions


def layout(dc: DocumentClass, rng: random.Random) -> list[PlacedToken]:
    """Tokens only (back-compat). Use layout_with_regions when per-instance bboxes are needed."""
    return layout_with_regions(dc, rng)[0]
