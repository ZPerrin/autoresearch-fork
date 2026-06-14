from __future__ import annotations
from .specs import FieldSpec, DocumentClass

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


register(DocumentClass(name="invoice", fields=(
    _f("description", "description", "left"),
    _f("quantity", "quantity", "right"),
    _f("unit_price", "unit_price", "right"),
    _f("amount", "amount", "right"),
)))

register(DocumentClass(name="eob", fields=(
    _f("service_date", "date", "left"),
    _f("code", "code", "left"),
    _f("description", "description", "left"),
    _f("amount_billed", "amount", "right"),
    _f("amount_owed", "amount", "right"),
)))

register(DocumentClass(name="receipt", fields=(
    _f("description", "description", "left"),
    _f("amount", "amount", "right"),
)))
