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


# Page-noise vocabulary for non-table (background) tokens — titles, footer notes, refs.
_NEUTRAL_BACKGROUND = (
    "Page", "Reference", "Notice", "Confidential", "Original", "Copy",
)


def background_token(terms: tuple[str, ...], rng: random.Random) -> str:
    """A single non-table noise token: a page-furniture word, or sometimes a number."""
    if rng.random() < 0.3:
        return str(rng.randint(1000, 99999))
    return rng.choice(terms or _NEUTRAL_BACKGROUND)


# Value samplers for global / singleton fields (names, ids).
_NAMES = [
    "John Smith", "Maria Garcia", "Wei Chen", "Aisha Khan", "Robert Jones",
    "Linda Nguyen", "David Patel", "Sarah Johnson",
    "Acme Medical Group", "Lakeside Clinic", "Mercy Hospital", "Summit Health",
]


def _name(rng: random.Random) -> str:
    return rng.choice(_NAMES)


def _id(rng: random.Random) -> str:
    return f"{rng.choice('ABCDEFGHJKMNP')}{rng.randint(100000, 999999)}"


SAMPLERS["name"] = _name
SAMPLERS["id"] = _id
