from __future__ import annotations
from functools import lru_cache

from PIL import ImageFont


@lru_cache(maxsize=8)
def _font(size: int):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def text_width(text: str, font_size: int) -> float:
    """Estimated rendered width (px) of `text` in the default render font.
    Used by layout to set content-aware column minimums without a full draw pass."""
    font = _font(font_size)
    try:
        return float(font.getlength(text))
    except (AttributeError, OSError):
        bbox = font.getbbox(text)
        return float(bbox[2] - bbox[0])
