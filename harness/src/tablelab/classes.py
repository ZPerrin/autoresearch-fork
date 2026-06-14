from __future__ import annotations
from .specs import FieldSpec, TableSpec, DocumentClass

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


def _f(name: str, type_: str, align: str) -> FieldSpec:
    return FieldSpec(name=name, type=type_, align=align)


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
        _f("description", "description", "left"),
        _f("quantity", "quantity", "right"),
        _f("unit_price", "unit_price", "right"),
        _f("amount", "amount", "right"),
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
            _f("description", "description", "left"),
            _f("amount_billed", "amount", "right"),
            _f("amount_owed", "amount", "right"),
        ), rows=(2, 5), instances=(1, 2)),
    ),
    background_terms=_EOB_BACKGROUND,
))

register(DocumentClass(name="receipt", tables=(
    TableSpec(name="line_item", fields=(
        _f("description", "description", "left"),
        _f("amount", "amount", "right"),
    )),
), background_terms=_RECEIPT_BACKGROUND))
