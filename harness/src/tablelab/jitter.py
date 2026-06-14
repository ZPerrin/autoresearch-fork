from __future__ import annotations
import random


def jitter_column_edges(edges: list[float], mag: float,
                        rng: random.Random, min_w: float = 8.0) -> list[float]:
    """Perturb interior column edges; first/last stay fixed so the row still spans
    exactly the same total width (zero-sum). Each edge moves by up to `mag` of the
    smaller adjacent column, and stays >= min_w from its neighbors."""
    out = list(edges)
    for i in range(1, len(edges) - 1):
        local = min(edges[i] - edges[i - 1], edges[i + 1] - edges[i])
        span = mag * local
        lo = out[i - 1] + min_w
        hi = edges[i + 1] - min_w
        if hi <= lo:
            continue
        out[i] = min(max(edges[i] + rng.uniform(-span, span), lo), hi)
    return out


def jitter_row_height(row_h: int, mag: float, gap_budget: int,
                      rng: random.Random) -> tuple[float, float]:
    """Return (cell_height, trailing_gap_delta). Height grows/shrinks within the gap
    budget; the trailing gap absorbs the opposite, so the section total is unchanged."""
    span = min(mag * row_h, gap_budget)
    delta = rng.uniform(-span, span)
    return row_h + delta, -delta


def jitter_offset(mag: float, baseline: float, pad: int,
                  rng: random.Random) -> tuple[float, float]:
    """Per-token (dx, dy) wobble bounded inside the cell pad so the box stays in-cell."""
    sx = mag * pad
    sy = (mag + baseline) * pad
    return rng.uniform(-sx, sx), rng.uniform(-sy, sy)
