# v0 "Loop Closes" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the full loop end-to-end — synthetic layouts → from-scratch layout transformer → frozen metric → static artifacts → local Vite/React viewer — on both MPS and CUDA.

**Architecture:** A Python module (`harness/tablelab/`) builds curated synthetic **datasets** (`datasets/<id>/`, local & gitignored — images + samples) and trains models that emit a git-tracked, binary-free experiment ledger under `runs/`; a static Vite/React app (`viewer/`) serves and composes both, overlaying predictions on the page image. Joined only by the artifact contract (schema v2). Data is multimodal (spatial/semantic/visual); the model climbs M0 (spatial) → M3 (fusion). Built in phases, each ending at a human-review gate.

> **Revision note (multimodal):** v0 pivoted to a multimodal data foundation with a `datasets/` vs `runs/` split. The authoritative build order and contract live in the revised spec (§6, §9). The detailed Phase 0–1 steps below are historical — TDD was skipped, and the contract is now schema v2 (per-token `text`, per-sample `image`, `dataset_id` on runs).

**Tech Stack:** Python 3.10+, PyTorch (device-agnostic, no Muon/compile/bf16), `uv`, pytest; Vite + React + TypeScript for the viewer.

**Spec:** [docs/specs/2026-06-13-v0-loop-closes-design.md](../specs/2026-06-13-v0-loop-closes-design.md)

---

## Cadence & gates

Execution **stops at each gate** for human validation before the next phase starts. Phases 0–1 are fully specified below. Phases 2–4 are task-level; each is expanded to full step detail at the gate immediately preceding it, incorporating decisions made at earlier gates.

| Phase | Build | Gate validates | Decisions it locks |
|---|---|---|---|
| 0 | Env foundation | `uv sync` + device report on both machines | device-aware deps |
| 1 | Artifact schema + fixture | schema shape vs. fixture | **the contract** |
| 2 | Viewer reads fixture | review UX in browser | review experience, serving mechanism |
| 3 | Synthetic generator | generated samples in viewer | **task design**, difficulty knobs |
| 4 | Model + train + eval + emitter | first run + H1–H3 in viewer | model/budget/hyperparams |

## File structure (v0)

```
harness/pyproject.toml             device-aware torch + Pillow; LM-only deps shed
harness/tablelab/device.py         get_device() — cuda → mps → cpu
harness/tablelab/artifacts.py      contract v2: dataset manifest + samples + run records
harness/tablelab/generate.py       dataset builder: render PNG + boxes/text/labels → datasets/<id>/
harness/tablelab/model.py          from-scratch M0 spatial model (later rungs: +text, +visual)
harness/tablelab/metric.py         frozen metric + baselines
harness/tablelab/train.py          editable experiment: train on a dataset, emit run artifacts
datasets/<id>/                     curated synthetic data — local & gitignored: manifest + samples + images/
runs/                              git-tracked experiment ledger (JSON only): index.json + <run>/
runs/_fixture/                     tiny committed contract example (incl. a small image)
viewer/                            Vite + React + TS: serves /runs + /datasets, overlays on page image
reference/                         upstream LM files parked (train.py, prepare.py, program.md, …)
```

No TDD — implement and verify by running. Upstream LM files stay in `reference/` until v0 completes.

---

## Phase 0 — Env foundation

### Task 0.1: Device-aware dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Rewrite dependencies and torch source to be device-aware**

Replace the `dependencies`, `[tool.uv.sources]`, and index blocks with:

```toml
[project]
name = "autoresearch"
version = "0.1.0"
description = "From-scratch lab for document table extraction"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "numpy>=2.2",
    "torch>=2.9",
]

[dependency-groups]
dev = ["pytest>=8"]

[tool.uv.sources]
torch = [
    { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]

[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
```

On Apple silicon (`sys_platform == 'darwin'`) no source override applies, so torch resolves from default PyPI (MPS-capable). On Linux/Windows it resolves from the CUDA 12.8 index.

- [ ] **Step 2: Resolve and verify install**

Run: `uv sync`
Expected: completes without error; on macOS pulls a non-CUDA torch wheel.

- [ ] **Step 3: Commit**

```bash
git add harness/pyproject.toml harness/uv.lock
git commit -m "build: device-aware torch deps, shed LM-only packages"
```

### Task 0.2: `get_device()`

**Files:**
- Create: `harness/tablelab/__init__.py` (empty)
- Create: `harness/tablelab/device.py`
- Test: `harness/tests/test_device.py`

- [ ] **Step 1: Write the failing tests**

```python
import torch
from tablelab.device import get_device

def test_prefers_cuda(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert get_device().type == "cuda"

def test_falls_back_to_mps(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert get_device().type == "mps"

def test_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    assert get_device().type == "cpu"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_device.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tablelab.device'`

- [ ] **Step 3: Implement**

`tablelab/__init__.py`: empty file.

`tablelab/device.py`:
```python
import torch


def get_device() -> torch.device:
    """Pick the best available device: CUDA, then Apple MPS, then CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_device.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add harness/tablelab/__init__.py harness/tablelab/device.py harness/tests/test_device.py
git commit -m "feat: device-agnostic get_device()"
```

### 🚦 Gate 0 — validate on both machines

Run on the M4 and on the 3080 Ti:
```bash
cd harness && uv sync
uv run python -c "from tablelab.device import get_device; print(get_device())"
```
Expected: `mps` on the Mac, `cuda` on the 3080 Ti, `uv sync` clean on both. **Stop. Confirm before Phase 1.**

---

## Phase 1 — Artifact schema + fixture (the contract)

### Task 1.1: Schema dataclasses + read/write/validate

**Files:**
- Create: `harness/tablelab/artifacts.py`
- Test: `harness/tests/test_artifacts.py`

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path
from tablelab.artifacts import (
    SCHEMA_VERSION, Token, Sample, RunRecord, IndexEntry,
    write_run, read_run, validate_run_dir, upsert_index,
)

def _record():
    return RunRecord(
        run_id="t-cpu-abc1234", commit="abc1234", branch="exp/v0", device="cpu",
        config={"seed": 1, "generator_version": 1}, metrics={"cell_exact": 0.4},
        curve=[{"step": 1, "train_loss": 2.0, "val_cell_exact": 0.1}],
        wall_seconds=1.0, status="keep", description="t",
    )

def _samples():
    return [Sample(id=0, tokens=[Token(0.0, 0.0, 0.1, 0.1, true_r=0, true_c=0,
                                       pred_r=0, pred_c=1)])]

def test_round_trip(tmp_path):
    write_run(tmp_path, _record(), _samples())
    rec, samples = read_run(tmp_path / "t-cpu-abc1234")
    assert rec.run_id == "t-cpu-abc1234"
    assert samples[0].tokens[0].pred_c == 1
    assert validate_run_dir(tmp_path / "t-cpu-abc1234") == []

def test_validate_flags_bad_schema(tmp_path):
    write_run(tmp_path, _record(), _samples())
    p = tmp_path / "t-cpu-abc1234" / "run.json"
    data = json.loads(p.read_text()); data["schema_version"] = 999
    p.write_text(json.dumps(data))
    errs = validate_run_dir(tmp_path / "t-cpu-abc1234")
    assert any("schema_version" in e for e in errs)

def test_upsert_index_is_idempotent(tmp_path):
    write_run(tmp_path, _record(), _samples())
    upsert_index(tmp_path, IndexEntry.from_record(_record()))
    upsert_index(tmp_path, IndexEntry.from_record(_record()))
    idx = json.loads((tmp_path / "index.json").read_text())
    assert len(idx["runs"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_artifacts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tablelab.artifacts'`

- [ ] **Step 3: Implement**

`tablelab/artifacts.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_artifacts.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add harness/tablelab/artifacts.py harness/tests/test_artifacts.py
git commit -m "feat: artifact schema (the contract) — read/write/validate"
```

### Task 1.2: Hand-authored fixture

**Files:**
- Create: `runs/_fixture/run.json`, `runs/_fixture/samples.json`, `runs/index.json`

- [ ] **Step 1: Generate the fixture from the schema (guarantees conformance)**

Run from `harness/`:
```bash
uv run python -c "
from pathlib import Path
from tablelab.artifacts import RunRecord, Sample, Token, write_run
toks = [Token(0.05,0.10,0.40,0.16,1,0,1,0), Token(0.05,0.10,0.40,0.16,2,0,1,0),
        Token(0.55,0.10,0.70,0.16,1,1,1,1), Token(0.80,0.10,0.95,0.16,1,2,1,3)]
write_run(Path('../runs'), RunRecord(
    run_id='_fixture', commit='0000000', branch='exp/v0', device='cpu',
    config={'seed':1,'generator_version':1,
            'difficulty':{'rows':[2,6],'cols':[2,6],'jitter':0.0,'text':False,'background':False}},
    metrics={'cell_exact':0.5,'row_acc':0.75,'col_acc':0.75,
             'baseline_majority_cell_exact':0.08,'baseline_geosort_cell_exact':0.86},
    curve=[{'step':100,'train_loss':2.3,'val_cell_exact':0.12},
           {'step':200,'train_loss':1.4,'val_cell_exact':0.5}],
    wall_seconds=42.0, status='keep', description='hand-authored fixture'),
  [Sample(0, toks)])
print('fixture written')
"
```
Expected: `fixture written`; files appear under `runs/_fixture/` and `runs/index.json` lists it.

- [ ] **Step 2: Verify it validates**

Run from `harness/`: `uv run python -c "from pathlib import Path; from tablelab.artifacts import validate_run_dir; print(validate_run_dir(Path('../runs/_fixture')))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add runs/_fixture runs/index.json
git commit -m "test: hand-authored artifact fixture for viewer development"
```

### 🚦 Gate 1 — validate the contract

Read `runs/_fixture/run.json` and `runs/_fixture/samples.json`. Confirm the shape carries everything the viewer and future real runs need (metrics, curve, per-token truth+prediction, config/seed). **This is the load-bearing decision — stop and confirm (or adjust the schema) before anything else consumes it.**

---

## Phase 2 — Viewer (task-level; expand at Gate 1)

**Builds:** a static Vite + React + TS app in `viewer/` that reads `runs/index.json` then a selected run.

**Tasks (to expand):**
- 2.1 Scaffold Vite + React + TS; decide and wire how the dev server serves `runs/` (symlink `runs/` → `viewer/public/runs`, or a static mount). *(open question §12)*
- 2.2 `RunList` — table from `index.json` (run id, device, status, metrics, description).
- 2.3 `PredictionOverlay` — SVG render of a sample's boxes on a normalized page; teal where `(pred_r,pred_c)==(true_r,true_c)`, red otherwise, annotated `pred ≠ true`.
- 2.4 `SampleBrowser` — prev/next + "errors only" filter wrapping the overlay.
- 2.5 `MetricCards` + `TrainingCurve` (from `run.json.curve`).

**Gate 2:** open the app on the fixture, poke the review UX. Locks: review experience, serving mechanism, component breakdown.

---

## Phase 3 — Synthetic generator (task-level; expand at Gate 2)

**Builds:** `tablelab/generate.py` — the experiment of section 2 of the spec.

**Tasks (to expand):**
- 3.1 `generate_sample(rng, difficulty)` — sample grid (rows/cols ∈ [2,6]), lay normalized boxes, optional jitter, shuffle token order, attach `(true_r,true_c)`; boxes-only (`text=None`). (`harness/tablelab/generate.py`)
- 3.2 `generate_batch(seed, n, difficulty)` — deterministic by seed; carries `generator_version`.
- 3.3 Tests: determinism by seed; labels consistent with geometry; token count == rows*cols; raising `jitter` changes output. (`harness/tests/test_generate.py`)
- 3.4 Preview script: write N generated samples as a `runs/<id>/samples.json` (truth only, `pred=None`) so the viewer renders generated data.

**Gate 3:** render generated samples in the viewer; validate task realism + difficulty-knob behavior. Locks: task design, formulation, difficulty knobs. *(Decides §12: variable token count → padding/mask; fixed vs relative row/col width.)*

---

## Phase 4 — Model + train + eval + emitter (task-level; expand at Gate 3)

**Builds:** `tablelab/model.py`, `tablelab/metric.py`, `tablelab/train.py` — the first real experiments.

**Tasks (to expand):**
- 4.1 `metric.py`: `row_acc`, `col_acc`, `cell_exact`; baselines `majority` and `geosort`. Tests on hand-constructed inputs. (`harness/tablelab/metric.py`, `harness/tests/test_metric.py`)
- 4.2 `model.py`: linear box embedding `4→d_model` → transformer encoder → row/col heads. Padding + attention mask per Gate 3 decision. Test forward output shapes. (`harness/tablelab/model.py`, `harness/tests/test_model.py`)
- 4.3 `train.py`: wire generator → model → summed CE loss → fixed-step loop → eval → `write_run()` with curve + metrics + a few rendered eval samples (truth + prediction). Smoke test: a few steps emit a schema-valid run. (`harness/tablelab/train.py`)
- 4.4 Run the baseline experiment on `exp/v0`; validate H1 (beats majority), H2 (attention ablation worse), H3 (jitter degrades cell_exact).
- 4.5 Cleanup: remove upstream reference files from `reference/` now that v0 stands on its own.

**Gate 4:** first real run renders in the viewer; H1–H3 confirmed. Locks: model size, budget value, hyperparams (cheap to revisit — append-only ledger).

---

## Self-review notes

- **Spec coverage:** env (§8)→Phase 0; contract (§6)→Phase 1; viewer (§7)→Phase 2; generator + H1–H3 (§2)→Phases 3–4; model/train/eval (§4–5)→Phase 4; workflow (§10)→branch/commit steps; success criteria (§11)→gate checks. Open questions (§12) routed to Gate 2/3.
- **Placeholders:** Phases 0–1 are fully coded. Phases 2–4 are intentionally task-level per the agreed cadence (expand at the preceding gate) — not placeholder TODOs but deferred-by-design to avoid early lock-in.
- **Type consistency:** `Token`/`Sample`/`RunRecord`/`IndexEntry`, `write_run`/`read_run`/`validate_run_dir`/`upsert_index` are used consistently across Phase 1 tasks and reused by Phase 4's emitter.
