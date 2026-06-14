from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .specs import DocumentClass
from .layout import PlacedToken

Box = tuple[float, float, float, float]


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def render(placed: list[PlacedToken], dc: DocumentClass) -> tuple[Image.Image, list[Box]]:
    """Draw placed tokens onto a white page; return the image and per-token
    glyph-extent boxes (page pixels), parallel to ``placed``."""
    W, H = dc.layout.page
    pad = dc.layout.pad
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _font(dc.render.font_size)
    boxes: list[Box] = []
    for p in placed:
        cx0, cy0, cx1, cy1 = p.cell
        row_h = cy1 - cy0  # honor this cell's height (supports variable rows later)
        tb = draw.textbbox((0, 0), p.text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ty = cy0 + (row_h - th) / 2 - tb[1]
        tx = (cx1 - pad - tw) if p.align == "right" else (cx0 + pad)
        draw.text((tx, ty), p.text, fill="black", font=font)
        boxes.append(draw.textbbox((tx, ty), p.text, font=font))  # actual rendered extent
    return img, boxes
