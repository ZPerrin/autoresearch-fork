from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCHEMA_VERSION = 1


@dataclass
class Token:
    x0: float; y0: float; x1: float; y1: float
    true_r: int; true_c: int
    pred_r: int | None = None
    pred_c: int | None = None
    text: str | None = None


@dataclass
class Sample:
    id: int
    tokens: list[Token]


@dataclass
class RunRecord:
    run_id: str
    commit: str
    branch: str
    device: str
    config: dict
    metrics: dict
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
    metrics: dict

    @classmethod
    def from_record(cls, r: RunRecord) -> "IndexEntry":
        return cls(r.run_id, r.commit, r.branch, r.device, r.status,
                   r.description, r.metrics)


def _token_from_dict(d: dict) -> Token:
    return Token(**d)


def write_run(runs_dir: Path, record: RunRecord, samples: list[Sample]) -> Path:
    runs_dir = Path(runs_dir)
    run_dir = runs_dir / record.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION, **asdict(record)}, indent=2))
    (run_dir / "samples.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION,
         "samples": [asdict(s) for s in samples]}, indent=2))
    upsert_index(runs_dir, IndexEntry.from_record(record))
    return run_dir


def read_run(run_dir: Path) -> tuple[RunRecord, list[Sample]]:
    run_dir = Path(run_dir)
    rd = json.loads((run_dir / "run.json").read_text())
    rd.pop("schema_version", None)
    record = RunRecord(**rd)
    sd = json.loads((run_dir / "samples.json").read_text())
    samples = [Sample(id=s["id"],
                      tokens=[_token_from_dict(t) for t in s["tokens"]])
               for s in sd["samples"]]
    return record, samples


def validate_run_dir(run_dir: Path) -> list[str]:
    run_dir = Path(run_dir)
    errs: list[str] = []
    for name in ("run.json", "samples.json"):
        p = run_dir / name
        if not p.exists():
            errs.append(f"missing {name}")
            continue
        data = json.loads(p.read_text())
        if data.get("schema_version") != SCHEMA_VERSION:
            errs.append(f"{name}: bad schema_version {data.get('schema_version')}")
    return errs


def upsert_index(runs_dir: Path, entry: IndexEntry) -> None:
    runs_dir = Path(runs_dir)
    idx_path = runs_dir / "index.json"
    if idx_path.exists():
        idx = json.loads(idx_path.read_text())
    else:
        idx = {"schema_version": SCHEMA_VERSION, "runs": []}
    idx["runs"] = [r for r in idx["runs"] if r["run_id"] != entry.run_id]
    idx["runs"].append(asdict(entry))
    idx_path.write_text(json.dumps(idx, indent=2))
