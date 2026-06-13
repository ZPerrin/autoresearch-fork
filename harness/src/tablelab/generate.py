from __future__ import annotations
import random
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .artifacts import Sample, Token, DatasetManifest, write_dataset

GENERATOR_VERSION = 2

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


# name -> (sampler, alignment within the cell)
FIELD_TYPES = {
    "description": (_desc, "left"),
    "quantity":   (_qty, "right"),
    "unit_price": (_money, "right"),
    "amount":     (_money, "right"),
    "date":       (_date, "left"),
    "code":       (_code, "left"),
}

# Document-class-like column schemas (a dataset uses ONE schema for all its samples).
SCHEMAS = {
    "invoice": ["description", "quantity", "unit_price", "amount"],
    "eob":     ["date", "code", "description", "amount", "amount"],
    "receipt": ["description", "amount"],
}


def _font(size: int = 22):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def generate_sample(rng: random.Random, sample_id: int, schema: list[str],
                    page: tuple[int, int] = (1000, 1414)):
    """Render one document image; return (PIL image, Sample with one token per cell)."""
    W, H = page
    R = rng.randint(2, 6)
    C = len(schema)
    margin_x, margin_y, pad, row_h = 60, 80, 12, 74
    cell_w = (W - 2 * margin_x) / C
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _font(22)
    tokens: list[Token] = []
    for r in range(R):
        for c in range(C):
            sampler, align = FIELD_TYPES[schema[c]]
            s = sampler(rng)
            cell_x0 = margin_x + c * cell_w
            cell_y0 = margin_y + r * row_h
            tb = draw.textbbox((0, 0), s, font=font)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            ty = cell_y0 + (row_h - th) / 2 - tb[1]
            tx = (cell_x0 + cell_w - pad - tw) if align == "right" else (cell_x0 + pad)
            draw.text((tx, ty), s, fill="black", font=font)
            rb = draw.textbbox((tx, ty), s, font=font)  # actual rendered extent
            tokens.append(Token(
                x0=round(rb[0] / W, 4), y0=round(rb[1] / H, 4),
                x1=round(rb[2] / W, 4), y1=round(rb[3] / H, 4),
                text=s, label={"record": r, "field": c}))
    rng.shuffle(tokens)
    return img, Sample(id=sample_id, tokens=tokens, width=W, height=H)


def build_dataset(datasets_dir, dataset_id: str, schema_name: str = "invoice",
                  seed: int = 7, n: int = 12, page: tuple[int, int] = (1000, 1414)) -> Path:
    rng = random.Random(seed)
    schema = SCHEMAS[schema_name]
    ds_dir = Path(datasets_dir) / dataset_id
    (ds_dir / "images").mkdir(parents=True, exist_ok=True)
    samples: list[Sample] = []
    for i in range(n):
        img, s = generate_sample(rng, i, schema, page)
        img.save(ds_dir / "images" / f"{i}.png")
        s.image = f"/datasets/{dataset_id}/images/{i}.png"
        samples.append(s)
    manifest = DatasetManifest(
        dataset_id=dataset_id, generator_version=GENERATOR_VERSION,
        task="grid_record_field", modalities=["spatial", "semantic", "visual"],
        count=n,
        config={"schema_name": schema_name, "fields": schema, "page": list(page),
                "difficulty": {"rows": [2, 6], "jitter": 0.0}})
    write_dataset(datasets_dir, manifest, samples)
    return ds_dir
