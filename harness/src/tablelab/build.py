from __future__ import annotations
import json
import os
import random
import re
import secrets
import shutil
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
_DATASET_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def _validate_dataset_id(dataset_id: str) -> None:
    basename = dataset_id.split(".", 1)[0].upper()
    if not _DATASET_ID_RE.fullmatch(dataset_id) or dataset_id.endswith("."):
        raise ValueError(
            f"invalid dataset_id {dataset_id!r}: expected 1-100 ASCII characters, "
            "starting alphanumeric and containing only alphanumeric, dot, underscore, "
            "or hyphen characters"
        )
    if basename in _WINDOWS_RESERVED:
        raise ValueError(f"invalid dataset_id {dataset_id!r}: reserved Windows basename")


def _pid_is_alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _lock_metadata(pid: int, staging: Path | None = None) -> bytes:
    return json.dumps({
        "pid": pid,
        "staging": str(staging) if staging is not None else None,
    }).encode("utf-8")


def _update_lock(lock_path: Path, staging: Path) -> None:
    temp_path = lock_path.with_name(f"{lock_path.name}.tmp-{os.getpid()}")
    try:
        temp_path.write_bytes(_lock_metadata(os.getpid(), staging))
        os.replace(temp_path, lock_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _safe_staging_path(
    datasets_dir: Path, dataset_id: str, recorded: object
) -> Path | None:
    if not isinstance(recorded, str):
        return None
    parent = datasets_dir.resolve()
    staging = Path(recorded).resolve()
    expected_prefix = f".{dataset_id}.staging-"
    if staging.parent != parent or not staging.name.startswith(expected_prefix):
        return None
    return staging


def _recover_stale_lock(
    lock_path: Path, datasets_dir: Path, dataset_id: str
) -> None:
    metadata = None
    try:
        metadata = json.loads(lock_path.read_text(encoding="utf-8"))
        pid = metadata["pid"]
        if type(pid) is not int or pid <= 0:
            raise ValueError("invalid pid")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        pid = None

    if pid is not None and _pid_is_alive(pid):
        raise FileExistsError(
            f"dataset build already in progress: {dataset_id!r}, owner pid={pid}"
        )

    recovery_path = lock_path.with_name(
        f"{lock_path.name}.stale-{os.getpid()}-{secrets.token_hex(4)}"
    )
    try:
        lock_path.rename(recovery_path)
    except FileNotFoundError:
        return
    try:
        staging = _safe_staging_path(
            datasets_dir,
            dataset_id,
            metadata.get("staging") if isinstance(metadata, dict) else None,
        )
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
    finally:
        recovery_path.unlink(missing_ok=True)


def _acquire_build_lock(lock_path: Path, datasets_dir: Path, dataset_id: str) -> None:
    # This lock coordinates tablelab builders; unrelated filesystem writers do not
    # participate in the no-replace contract.
    for attempt in range(2):
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if attempt:
                raise FileExistsError(
                    f"dataset build already in progress: {dataset_id!r} ({lock_path})"
                ) from None
            _recover_stale_lock(lock_path, datasets_dir, dataset_id)
            continue
        try:
            os.write(lock_fd, _lock_metadata(os.getpid()))
        finally:
            os.close(lock_fd)
        return


def _validate_boxes(
    boxes, placed, dataset_id: str, sample_id: int, width: int, height: int
) -> None:
    if len(boxes) != len(placed):
        raise ValueError(
            f"dataset {dataset_id!r} sample {sample_id}: rendered token cardinality "
            f"mismatch: placed={len(placed)}, boxes={len(boxes)}"
        )
    for index, box in enumerate(boxes):
        x0, y0, x1, y1 = box
        if not (0 <= x0 <= x1 <= width and 0 <= y0 <= y1 <= height):
            raise ValueError(
                f"invalid rendered box in dataset {dataset_id!r} sample {sample_id} "
                f"at token index {index} "
                f"with text {placed[index].text!r}: "
                f"page=({width}, {height}), box={box}"
            )


def build_dataset(datasets_dir: Path | str, dataset_id: str, doc_class: DocumentClass,
                  seed: int = 7, n: int = 12) -> Path:
    """Compose a DocumentClass into a dataset: per sample layout->render->convert,
    write images + contract samples + a reproducible manifest (resolved spec + seed)."""
    validate_layout_capacity(doc_class)
    _validate_dataset_id(dataset_id)
    datasets_dir = Path(datasets_dir)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    ds_dir = datasets_dir / dataset_id
    lock_path = datasets_dir / f".{dataset_id}.build.lock"
    _acquire_build_lock(lock_path, datasets_dir, dataset_id)

    try:
        if ds_dir.exists():
            raise FileExistsError(f"dataset already exists: {ds_dir}")
        rng = random.Random(seed)
        W, H = doc_class.layout.page
        with tempfile.TemporaryDirectory(
            prefix=f".{dataset_id}.staging-", dir=datasets_dir
        ) as staging_parent:
            _update_lock(lock_path, Path(staging_parent))
            staging_dir = Path(staging_parent) / dataset_id
            (staging_dir / "images").mkdir(parents=True)
            samples: list[Sample] = []
            for i in tqdm(range(n), desc=dataset_id):
                placed = layout(doc_class, rng)
                img, boxes = render(placed, doc_class)
                _validate_boxes(boxes, placed, dataset_id, i, W, H)
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
            # Under the cooperative lock, rename publishes without replacing another
            # tablelab builder's dataset. External racing writers remain out of scope.
            staging_dir.rename(ds_dir)
    finally:
        lock_path.unlink(missing_ok=True)
    return ds_dir
