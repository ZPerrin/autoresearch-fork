from __future__ import annotations
import random
from datetime import date, timedelta

# Field-appropriate value samplers, modeled on real invoice / EOB / receipt line items.
_DESCRIPTIONS = [
    "Office chair", "Desk lamp", "USB-C cable", "Notebook", "Stapler",
    "Monitor stand", "Printer paper", "Ballpoint pens", "Whiteboard", "Headset",
    "Office visit", "Lab panel", "X-ray exam", "Consultation", "Physical therapy",
    "Vaccination", "Blood test", "MRI scan", "Follow-up", "Screening",
]


def _money(rng: random.Random) -> str:
    return f"${rng.uniform(2, 950):,.2f}"


def _qty(rng: random.Random) -> str:
    return str(rng.randint(1, 24))


def _date(rng: random.Random) -> str:
    return (date(2025, 1, 1) + timedelta(days=rng.randint(0, 480))).strftime("%m/%d/%Y")


def _code(rng: random.Random) -> str:
    return f"{rng.randint(10000, 99999)}"  # CPT-like


def _desc(rng: random.Random) -> str:
    return rng.choice(_DESCRIPTIONS)


# semantic type name -> sampler. Alignment lives on FieldSpec, not here.
SAMPLERS = {
    "description": _desc,
    "quantity": _qty,
    "unit_price": _money,
    "amount": _money,
    "date": _date,
    "code": _code,
}


def sample(type_name: str, rng: random.Random) -> str:
    return SAMPLERS[type_name](rng)
