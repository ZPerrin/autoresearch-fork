from __future__ import annotations
import random
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from .specs import DocumentClass
from .artifacts import Sample, Token, DatasetManifest, write_dataset
from .layout import layout, validate_layout_capacity
from .render import render

GENERATOR_VERSION = 2


def _validate_boxes(boxes, placed, sample_id: int, width: int, height: int) -> None:
    for index, box in enumerate(boxes):
        x0, y0, x1, y1 = box
        if not (0 <= x0 <= x1 <= width and 0 <= y0 <= y1 <= height):
            raise ValueError(
                f"invalid rendered box in sample {sample_id} at token index {index} "
                f"with text {placed[index].text!r}: "
                f"page=({width}, {height}), box={box}"
            )


def build_dataset(datasets_dir: Path | str, dataset_id: str, doc_class: DocumentClass,
                  seed: int = 7, n: int = 12) -> Path:
    """Compose a DocumentClass into a dataset: per sample layout->render->convert,
    write images + contract samples + a reproducible manifest (resolved spec + seed)."""
    validate_layout_capacity(doc_class)
    datasets_dir = Path(datasets_dir)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    ds_dir = datasets_dir / dataset_id
    if ds_dir.exists():
        raise FileExistsError(f"dataset already exists: {ds_dir}")

    rng = random.Random(seed)
    W, H = doc_class.layout.page
    with tempfile.TemporaryDirectory(
        prefix=f".{dataset_id}.staging-", dir=datasets_dir
    ) as staging_parent:
        staging_dir = Path(staging_parent) / dataset_id
        (staging_dir / "images").mkdir(parents=True)
        samples: list[Sample] = []
        for i in tqdm(range(n), desc=dataset_id):
            placed = layout(doc_class, rng)
            img, boxes = render(placed, doc_class)
            _validate_boxes(boxes, placed, i, W, H)
            img.save(staging_dir / "images" / f"{i}.png")
            tokens = [Token(x0=round(b[0] / W, 4), y0=round(b[1] / H, 4),
                            x1=round(b[2] / W, 4), y1=round(b[3] / H, 4),
                            text=p.text, label=p.label)
                      for p, b in zip(placed, boxes)]
            samples.append(Sample(id=i, tokens=tokens, width=W, height=H,
                                  image=f"/datasets/{dataset_id}/images/{i}.png"))
        manifest = DatasetManifest(
            dataset_id=dataset_id, generator_version=GENERATOR_VERSION,
            task="grid_record_field", modalities=["spatial", "semantic", "visual"],
            count=n,
            config={"class": doc_class.name, "seed": seed, "spec": asdict(doc_class)},
            created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        write_dataset(staging_parent, manifest, samples)
        if ds_dir.exists():
            raise FileExistsError(f"dataset already exists: {ds_dir}")
        staging_dir.rename(ds_dir)
    return ds_dir
