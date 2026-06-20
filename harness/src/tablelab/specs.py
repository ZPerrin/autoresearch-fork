from __future__ import annotations
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str            # key into fields.SAMPLERS (e.g. "amount", "date")
    align: str = "left"  # "left" | "right"
    width: float | None = None  # column weight; None => fields.TYPE_WIDTH default
    fill: float = 1.0    # probability a data cell is populated; < 1.0 leaves some cells empty (no token)
    group: str | None = None  # contiguous fields sharing a group name form one header banner cell
    max_width: float | None = None  # cap on content-aware column width (px); wider values wrap. None = grow-to-fit
    max_lines: int = 1              # upper bound on wrapped lines; used for worst-case capacity reservation


@dataclass(frozen=True)
class SpanCell:
    span: int = 1              # columns this cell covers
    text: str | None = None    # literal label (e.g. "TOTALS")
    type: str | None = None    # value sampler key (e.g. "amount", "category"); xor with text
    align: str = "left"


@dataclass(frozen=True)
class SpanRowSpec:
    """A row whose cells each cover a contiguous column range. Spans must sum to the
    table's field count. Used as a section row (before records) or totals row (after)."""
    cells: tuple[SpanCell, ...]


@dataclass(frozen=True)
class TableSpec:
    name: str
    fields: tuple[FieldSpec, ...]
    rows: tuple[int, int] = (2, 6)        # record-count range, inclusive (passed to randint)
    instances: tuple[int, int] = (1, 1)   # number of instances of this table per document
    section: SpanRowSpec | None = None    # spanning row emitted once before each instance's records
    totals: SpanRowSpec | None = None     # spanning row emitted once after each instance's records


@dataclass(frozen=True)
class LayoutSpec:
    page: tuple[int, int] = (1000, 1414)
    margin: tuple[int, int] = (60, 80)
    row_h: int | None = None              # row band height (px); None => font-derived (round(font_size * 1.7))
    pad: int = 12
    table_gap: int = 40                   # back-compat base gap; instance_gap/section_gap fall back to this
    row_gap: int = 0                      # extra gap between consecutive data rows within a table
    instance_gap: int | None = None       # gap between stacked instances (None => table_gap)
    section_gap: int | None = None        # gap between sections globals->tables->background (None => table_gap)
    globals_per_row: int = 1              # label:value pairs packed across one global row
    line_h: int | None = None             # intra-cell wrapped-line height; None => round(font_size * 1.4)


@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background words,
    multiple tables, jitter). Each follow-on spec adds fields here.

    Cells always emit one Word per whitespace word (the atomic observable); there is
    no opt-in splitting flag.

    header: emit a top header row of field-name words. With FieldSpec.group set, a
        grouped-header banner band is emitted above the leaf header row.
    background: scatter N non-table words in the footer band below the table.

    Spanning data rows (section/totals) live on TableSpec; grouped-header membership lives
    on FieldSpec.group."""
    header: bool = False
    background: int = 0


@dataclass(frozen=True)
class RenderSpec:
    font_size: int = 22
    renderer: str = "pillow"   # the visual-realism seam; only "pillow" exists today
    autoscale_font: bool = False  # shrink a table's font so wide column sets fit instead of overflowing


@dataclass(frozen=True)
class JitterSpec:
    """Per-axis random perturbation magnitudes (fractions, 0 = off). Each axis is
    independent so a dataset can isolate one nuisance variable for modeling ablations.
    All bounded/zero-sum: jitter never grows a section's total extent or pushes a token
    out of its cell."""
    row_h: float = 0.0    # per-row height variance, borrowed zero-sum from row_gap budget
    col_w: float = 0.0    # per-column width variance, zero-sum across the row
    offset: float = 0.0   # per-token x/y wobble, bounded inside the cell pad
    baseline: float = 0.0 # per-token vertical baseline wobble, bounded inside the cell pad


@dataclass(frozen=True)
class DocumentClass:
    name: str
    tables: tuple[TableSpec, ...]
    globals: tuple[FieldSpec, ...] = ()
    background_terms: tuple[str, ...] = ()
    layout: LayoutSpec = LayoutSpec()
    structure: StructureSpec = StructureSpec()
    render: RenderSpec = RenderSpec()
    jitter: JitterSpec = JitterSpec()


def fork(dc: DocumentClass, name: str | None = None, **overrides) -> DocumentClass:
    """Copy a DocumentClass with top-level fields replaced (e.g. ``tables=...``,
    ``layout=...``). Nested specs are replaced wholesale — build the replacement with
    ``dataclasses.replace(dc.tables[0], rows=...)`` and pass it in."""
    return replace(dc, name=name or dc.name, **overrides)
