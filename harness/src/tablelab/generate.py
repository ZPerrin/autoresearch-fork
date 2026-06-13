from __future__ import annotations
import random
from pathlib import Path
from .artifacts import Sample, Token, RunRecord, write_run

GENERATOR_VERSION = 1
DEFAULT_DIFFICULTY = {"rows": [2, 6], "cols": [2, 6], "jitter": 0.0, "text": False, "background": False}


def generate_sample(rng: random.Random, sample_id: int, difficulty: dict = DEFAULT_DIFFICULTY) -> Sample:
    rmin, rmax = difficulty["rows"]
    cmin, cmax = difficulty["cols"]
    R = rng.randint(rmin, rmax)
    C = rng.randint(cmin, cmax)
    jitter = float(difficulty.get("jitter", 0.0))
    margin = 0.05
    cell_w = (1.0 - 2 * margin) / C
    cell_h = (1.0 - 2 * margin) / R
    pad_x = cell_w * 0.12
    pad_y = cell_h * 0.18
    tokens: list[Token] = []
    for r in range(R):
        for c in range(C):
            x0 = margin + c * cell_w + pad_x
            x1 = margin + (c + 1) * cell_w - pad_x
            y0 = margin + r * cell_h + pad_y
            y1 = margin + (r + 1) * cell_h - pad_y
            if jitter:
                jx = (rng.random() * 2 - 1) * jitter * cell_w
                jy = (rng.random() * 2 - 1) * jitter * cell_h
                x0 += jx; x1 += jx; y0 += jy; y1 += jy
            tokens.append(Token(
                x0=round(x0, 4), y0=round(y0, 4), x1=round(x1, 4), y1=round(y1, 4),
                text=None, label={"record": r, "field": c}, pred=None))
    rng.shuffle(tokens)
    return Sample(id=sample_id, tokens=tokens)


def generate_batch(seed: int, n: int, difficulty: dict = DEFAULT_DIFFICULTY) -> list[Sample]:
    rng = random.Random(seed)
    return [generate_sample(rng, i, difficulty) for i in range(n)]


def write_preview(runs_dir, seed: int = 7, n: int = 6, difficulty: dict = DEFAULT_DIFFICULTY,
                  run_id: str = "_genpreview") -> None:
    samples = generate_batch(seed, n, difficulty)
    write_run(Path(runs_dir), RunRecord(
        run_id=run_id, commit="0000000", branch="exp/v0", device="cpu",
        config={"task": "grid_record_field", "seed": seed,
                "generator_version": GENERATOR_VERSION, "difficulty": difficulty},
        metrics={}, curve=[], status="keep",
        description="generator preview (ground truth only)"), samples)
