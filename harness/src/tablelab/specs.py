from __future__ import annotations
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str            # key into fields.SAMPLERS (e.g. "amount", "date")
    align: str = "left"  # "left" | "right"


@dataclass(frozen=True)
class LayoutSpec:
    rows: tuple[int, int] = (2, 6)        # record-count range, inclusive (passed to randint)
    page: tuple[int, int] = (1000, 1414)  # page pixel size (W, H)
    margin: tuple[int, int] = (60, 80)    # (x, y) page margins in px
    row_h: int = 74                       # row height in px
    pad: int = 12                         # in-cell text padding in px


@dataclass(frozen=True)
class StructureSpec:
    """Named home for structural-realism knobs (header row, background tokens,
    multi-token cells, multiple tables, jitter, spanning cells). Each follow-on
    spec adds fields here. See docs/specs/2026-06-13-synth-toolkit-backbone-design.md.

    multi_token: split multi-word cell values into per-word tokens that share one
    record/field and carry a within-cell order index (seq)."""
    multi_token: bool = False


@dataclass(frozen=True)
class RenderSpec:
    font_size: int = 22
    renderer: str = "pillow"   # the visual-realism seam; only "pillow" exists today


@dataclass(frozen=True)
class DocumentClass:
    name: str
    fields: tuple[FieldSpec, ...]
    layout: LayoutSpec = LayoutSpec()
    structure: StructureSpec = StructureSpec()
    render: RenderSpec = RenderSpec()


def fork(dc: DocumentClass, name: str | None = None, **overrides) -> DocumentClass:
    """Copy a DocumentClass with top-level fields replaced (e.g. ``layout=...``).
    Nested specs are replaced wholesale — build the replacement with
    ``dataclasses.replace(dc.layout, rows=...)`` and pass it in."""
    return replace(dc, name=name or dc.name, **overrides)
