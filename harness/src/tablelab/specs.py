from __future__ import annotations
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str            # key into fields.SAMPLERS (e.g. "amount", "date")
    align: str = "left"  # "left" | "right"
    width: float | None = None  # column weight; None => fields.TYPE_WIDTH default
    fill: float = 1.0    # probability a data cell is populated; < 1.0 leaves some cells empty (no token)


@dataclass(frozen=True)
class TableSpec:
    name: str
    fields: tuple[FieldSpec, ...]
    rows: tuple[int, int] = (2, 6)        # record-count range, inclusive (passed to randint)
    instances: tuple[int, int] = (1, 1)   # number of instances of this table per document


@dataclass(frozen=True)
class LayoutSpec:
    page: tuple[int, int] = (1000, 1414)
    margin: tuple[int, int] = (60, 80)
    row_h: int = 74
    pad: int = 12
    table_gap: int = 40                   # back-compat base gap; instance_gap/section_gap fall back to this
    row_gap: int = 0                      # extra gap between consecutive data rows within a table
    instance_gap: int | None = None       # gap between stacked instances (None => table_gap)
    section_gap: int | None = None        # gap between sections globals->tables->background (None => table_gap)
    globals_per_row: int = 1              # label:value pairs packed across one global row


@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter, spanning cells). Each follow-on
    spec adds fields here. See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    multi_token: split multi-word cell values into per-word tokens that share one
        record/field and carry a within-cell order index (seq).
    header: emit a top header row of field-name tokens (label {"field": c, "header": True}).
    background: scatter N non-table tokens (label = None) in the footer band below the table."""
    multi_token: bool = False
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
    out of its cell (see docs/specs/2026-06-14-realistic-spacing-jitter-design.md)."""
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
