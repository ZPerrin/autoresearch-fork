from __future__ import annotations
from .specs import (FieldSpec, TableSpec, DocumentClass, LayoutSpec,
                    StructureSpec, SpanCell, SpanRowSpec)

REGISTRY: dict[str, DocumentClass] = {}


def register(dc: DocumentClass) -> DocumentClass:
    REGISTRY[dc.name] = dc
    return dc


def get(name: str) -> DocumentClass:
    if name not in REGISTRY:
        raise KeyError(f"unknown document class {name!r}; known: {classes()}")
    return REGISTRY[name]


def classes() -> list[str]:
    return sorted(REGISTRY)


def _f(name: str, type_: str, align: str, width: float | None = None,
       fill: float = 1.0, group: str | None = None,
       max_width: float | None = None, max_lines: int = 1) -> FieldSpec:
    return FieldSpec(name=name, type=type_, align=align, width=width, fill=fill,
                     group=group, max_width=max_width, max_lines=max_lines)


_INVOICE_BACKGROUND = (
    "Invoice", "Account", "Customer", "Subtotal", "Total", "Balance",
    "Payment Terms", "Remit To", "Page", "Reference",
)

_EOB_BACKGROUND = (
    "Explanation of Benefits", "Patient Responsibility", "Plan Paid",
    "Claim Reference", "Benefit Notice", "This Is Not a Bill",
    "Member Services", "Page", "Reference",
)

_RECEIPT_BACKGROUND = (
    "Receipt", "Paid", "Subtotal", "Total", "Payment", "Thank You",
    "Store Copy", "Page", "Reference",
)


register(DocumentClass(name="invoice", tables=(
    TableSpec(name="line_item", fields=(
        # width=1.0 pins uniform columns: invoice is the byte-identical golden guard.
        _f("description", "description", "left", 1.0),
        _f("quantity", "quantity", "right", 1.0),
        _f("unit_price", "unit_price", "right", 1.0),
        _f("amount", "amount", "right", 1.0),
    )),
), background_terms=_INVOICE_BACKGROUND))

register(DocumentClass(
    name="eob",
    globals=(
        _f("member_name", "name", "left"),
        _f("member_id", "id", "left"),
        _f("provider", "name", "left"),
        _f("claim_number", "id", "left"),
    ),
    tables=(
        TableSpec(name="claim_line", fields=(
            _f("service_date", "date", "left"),
            _f("code", "code", "left"),
            _f("description", "service_desc", "left", max_width=178.0, max_lines=2),
            _f("amount_billed", "amount", "right", group="Charges"),
            _f("allowed", "amount", "right", group="Charges"),
            _f("deductible", "amount", "right", fill=0.3, group="Patient Responsibility"),
            _f("copay", "amount", "right", fill=0.4, group="Patient Responsibility"),
            _f("coinsurance", "amount", "right", fill=0.3, group="Patient Responsibility"),
            _f("plan_paid", "amount", "right", group="Plan & Balance"),
            _f("amount_owed", "amount", "right", group="Plan & Balance"),
        ), rows=(2, 5), instances=(1, 2),
            # Section heading introduces each claim block; TOTALS row closes it.
            section=SpanRowSpec((SpanCell(span=10, type="category"),)),
            totals=SpanRowSpec((
                SpanCell(span=3, text="TOTALS"),
                *(SpanCell(span=1, type="amount", align="right") for _ in range(7)),
            )),
        ),
    ),
    background_terms=_EOB_BACKGROUND,
    # Grouped-header banners require the leaf header row.
    structure=StructureSpec(header=True),
    # Wide page is the class-level template size: ten claim-line columns need the room.
    layout=LayoutSpec(page=(1500, 1414), globals_per_row=2),
))

register(DocumentClass(name="receipt", tables=(
    TableSpec(name="line_item", fields=(
        _f("description", "description", "left"),
        _f("amount", "amount", "right"),
    )),
), background_terms=_RECEIPT_BACKGROUND))
