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
    glyph-extent boxes (page pixels), parallel to ``placed``. Tokens sharing a
    cell rect are laid out left-to-right as one phrase; their boxes are still
    returned in the input order so the caller's 1:1 zip holds."""
    W, H = dc.layout.page
    pad = dc.layout.pad
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    boxes: list[Box] = [(0.0, 0.0, 0.0, 0.0)] * len(placed)

    # Group token indices by their cell rect; order within a cell by seq.
    groups: dict[tuple, list[int]] = {}
    for i, p in enumerate(placed):
        groups.setdefault(p.cell, []).append(i)

    for idxs in groups.values():
        if len(idxs) > 1:
            idxs.sort(key=lambda i: placed[i].label["seq"])
        cx0, cy0, cx1, cy1 = placed[idxs[0]].cell
        row_h = cy1 - cy0
        align = placed[idxs[0]].align
        font = _font(placed[idxs[0]].font_size)  # per-token size (autoscale shrinks table cells)

        if len(idxs) == 1:
            # Legacy single-token path — keeps output byte-identical when multi_token is off.
            p = placed[idxs[0]]
            tb = draw.textbbox((0, 0), p.text, font=font)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            ty = cy0 + (row_h - th) / 2 - tb[1]
            tx = (cx1 - pad - tw) if align == "right" else (cx0 + pad)
            tx += p.dx
            ty += p.dy
            draw.text((tx, ty), p.text, fill="black", font=font)
            raw = draw.textbbox((tx, ty), p.text, font=font)
            # Clamp reported box to cell horizontal bounds so callers can rely on
            # box ⊆ cell; needed when an oversized word exceeds the column cap.
            boxes[idxs[0]] = (raw[0], raw[1], min(raw[2], cx1), raw[3])
            continue

        # Multi-word: lay the words out as a contiguous phrase within the cell.
        leader = placed[idxs[0]]
        words = [placed[i].text for i in idxs]
        widths = [draw.textlength(w, font=font) for w in words]
        space_w = draw.textlength(" ", font=font)
        phrase_w = sum(widths) + space_w * (len(words) - 1)
        x = (cx1 - pad - phrase_w) if align == "right" else (cx0 + pad)
        x += leader.dx
        for k, (i, word, w) in enumerate(zip(idxs, words, widths)):
            tb = draw.textbbox((0, 0), word, font=font)
            th = tb[3] - tb[1]
            ty = cy0 + (row_h - th) / 2 - tb[1] + leader.dy
            draw.text((x, ty), word, fill="black", font=font)
            boxes[i] = draw.textbbox((x, ty), word, font=font)
            x += w + (space_w if k < len(words) - 1 else 0)

    return img, boxes
