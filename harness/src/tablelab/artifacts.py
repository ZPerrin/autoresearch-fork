from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCHEMA_VERSION = 2


@dataclass
class Token:
    x0: float; y0: float; x1: float; y1: float
    text: str | None = None
    label: dict | None = None
    pred: dict | None = None


@dataclass
class Sample:
    id: int
    tokens: list[Token]
    image: str | None = None      # path/URL the viewer can fetch (e.g. /datasets/<id>/images/0.png)
    width: int | None = None      # page pixel dims; token boxes stay normalized to [0,1]
    height: int | None = None


@dataclass
class DatasetManifest:
    dataset_id: str
    generator_version: int
    task: str
    modalities: list[str]
    count: int
    config: dict = field(default_factory=dict)
    created: str = ""


@dataclass
class RunRecord:
    run_id: str
    commit: str
    branch: str
    device: str
    config: dict
    metrics: dict
    dataset_id: str = ""
    curve: list[dict] = field(default_factory=list)
    wall_seconds: float = 0.0
    status: str = "keep"
    description: str = ""


@dataclass
class IndexEntry:
    run_id: str
    commit: str
    branch: str
    device: str
    status: str
    description: str
    dataset_id: str
    metrics: dict

    @classmethod
    def from_record(cls, r: RunRecord) -> "IndexEntry":
        return cls(r.run_id, r.commit, r.branch, r.device, r.status,
                   r.description, r.dataset_id, r.metrics)


def _token_from_dict(d: dict) -> Token:
    return Token(**d)


def _sample_from_dict(d: dict) -> Sample:
    return Sample(id=d["id"], tokens=[_token_from_dict(t) for t in d["tokens"]],
                  image=d.get("image"), width=d.get("width"), height=d.get("height"))


def _write_samples(path: Path, samples: list[Sample], extra: dict | None = None) -> None:
    payload: dict = {"schema_version": SCHEMA_VERSION}
    if extra:
        payload.update(extra)
    payload["samples"] = [asdict(s) for s in samples]
    path.write_text(json.dumps(payload, indent=2))


def _validate(d: Path, names: tuple[str, ...]) -> list[str]:
    errs: list[str] = []
    for name in names:
        p = d / name
        if not p.exists():
            errs.append(f"missing {name}")
            continue
        data = json.loads(p.read_text())
        if data.get("schema_version") != SCHEMA_VERSION:
            errs.append(f"{name}: bad schema_version {data.get('schema_version')}")
    return errs


# ---- runs: git-tracked experiment ledger ----

def write_run(runs_dir: Path, record: RunRecord, samples: list[Sample]) -> Path:
    runs_dir = Path(runs_dir)
    run_dir = runs_dir / record.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION, **asdict(record)}, indent=2))
    _write_samples(run_dir / "samples.json", samples, {"dataset_id": record.dataset_id})
    upsert_index(runs_dir, IndexEntry.from_record(record))
    return run_dir


def read_run(run_dir: Path) -> tuple[RunRecord, list[Sample]]:
    run_dir = Path(run_dir)
    rd = json.loads((run_dir / "run.json").read_text())
    rd.pop("schema_version", None)
    record = RunRecord(**rd)
    sd = json.loads((run_dir / "samples.json").read_text())
    return record, [_sample_from_dict(s) for s in sd["samples"]]


def upsert_index(runs_dir: Path, entry: IndexEntry) -> None:
    runs_dir = Path(runs_dir)
    idx_path = runs_dir / "index.json"
    idx = (json.loads(idx_path.read_text()) if idx_path.exists()
           else {"schema_version": SCHEMA_VERSION, "runs": []})
    idx["runs"] = [r for r in idx["runs"] if r["run_id"] != entry.run_id]
    idx["runs"].append(asdict(entry))
    idx_path.write_text(json.dumps(idx, indent=2))


def validate_run_dir(run_dir: Path) -> list[str]:
    return _validate(Path(run_dir), ("run.json", "samples.json"))


# ---- datasets: local, gitignored curated data ----

def write_dataset(datasets_dir: Path, manifest: DatasetManifest, samples: list[Sample]) -> Path:
    ds_dir = Path(datasets_dir) / manifest.dataset_id
    (ds_dir / "images").mkdir(parents=True, exist_ok=True)
    (ds_dir / "manifest.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION, **asdict(manifest)}, indent=2))
    _write_samples(ds_dir / "samples.json", samples, {"dataset_id": manifest.dataset_id})
    return ds_dir


def read_dataset(ds_dir: Path) -> tuple[DatasetManifest, list[Sample]]:
    ds_dir = Path(ds_dir)
    md = json.loads((ds_dir / "manifest.json").read_text())
    md.pop("schema_version", None)
    manifest = DatasetManifest(**md)
    sd = json.loads((ds_dir / "samples.json").read_text())
    return manifest, [_sample_from_dict(s) for s in sd["samples"]]


def validate_dataset_dir(ds_dir: Path) -> list[str]:
    return _validate(Path(ds_dir), ("manifest.json", "samples.json"))
