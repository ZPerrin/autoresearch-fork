---
kind: readme
status: living
updated: 2026-07-01
---
# autoresearch (fork) — a from-scratch lab for multimodal document extraction

This lab is my answer to two problems that turned out to share a solution.

The first is from work: pulling repeated records out of semi-structured documents. Claim lines off
an EOB, line items off an invoice, all from what OCR hands you: words, boxes, and the page image.
Production treats this as natural-language queries over Textract output, and it generalizes about
as well as you'd expect. The real data is sparse exactly where it hurts (few examples near the hard
cases, thin labels, half the fields empty), and no amount of prompting fixes a data problem.

The second is mine. I keep *pointing* deep learning at problems without having built any of it. So
the rule here is from scratch, every layer: the data generator, the models, the training loop.
Implementing a thing is the only way I actually learn it.

Synthetic data is where the two meet. I can't get more real documents, but I can define the whole
distribution: the generator knows every cell's position, meaning, and record rollup for free,
because the document class *defines* them. Models then climb a modality ladder (boxes first, then
text, then the page image itself), each rung earning its keep before the next. The skeleton is
forked from karpathy's [autoresearch](https://github.com/karpathy/autoresearch), a single-GPU
[nanochat](https://github.com/karpathy/nanochat). I kept the machinery, a small model on a fast
train → evaluate → keep/discard loop against a frozen metric, and repointed it from language
modeling at documents.

## Overview

The synthetic dataset builder and the materialized v5 contract (grounded `fields` / `field_groups`
targets per document) are built; the viewer renders the structure and is gaining the target tree +
prediction diff; the from-scratch model loop is next (spatial M0). Runs device-agnostic on Apple
silicon (MPS), NVIDIA (CUDA), or CPU. Where it's headed is the [roadmap](docs/roadmap.md).

## The bet

**Structured truth in, task framings out.** Synthetic data is the inverse of the
sparse-real-data trap: the generator knows everything, densely, for free — every cell's position,
its field meaning, the record rollup, the global↔table association — because the document class
*defines* them. So generate one complete, structured ground truth per document; treat every task
framing (token classification, extractive/NLQ Q&A, structure prediction, record extraction) as a
`derive_*` projection over it, never baked into the data; and make sparsity a knob, not a
constraint. The schema stays **Textract-shaped** (`Region`/`Cell`/`Word` ≈ `LAYOUT`/`CELL`/`WORD`)
on purpose: real labeled + Textract data flows into the same representation, so we can pretrain on
dense synthetic and evaluate/transfer on real. The grounding problem is repeated-record extraction
(claim lines rolled into tables, plus document-level globals) from work — context that keeps the
research real, not a boundary — and the modeling approach stays deliberately open.

## Module Map

- [harness](harness/) - Python package `src/tablelab/`: dataset builder, model, training, the artifact contract. `uv` + device-aware torch.
- [viewer](viewer/) - Vite/React split-pane review app (page image + structure overlay). No backend.
- [runs](runs/) - git-tracked experiment ledger (`index.json` + per-run JSON, no binaries).
- [docs](docs/) - the roadmap + durable design docs ([docs/README.md](docs/README.md)).
- `datasets/` - curated synthetic data `<id>/{manifest, samples, images}`. **Local & gitignored.**
- [reference](reference/) - parked upstream LM files (karpathy/autoresearch).

## Getting Started

Each module sets up independently:

```bash
# harness (Python) — see harness/README.md
cd harness && uv sync

# viewer (Node) — see viewer/README.md
cd viewer && npm install && npm run dev   # http://localhost:5173
```

`uv` installs device-aware torch (MPS / CUDA / CPU). Build a first dataset with
`uv run python -m tablelab.cli build --class eob --n 100 --out ../datasets/eob-demo`, then review it
in the viewer.

## Documentation

- [docs/README.md](docs/README.md) - the docs tree: what lives where
- [docs/roadmap.md](docs/roadmap.md) - milestones and current focus
- [AGENTS.md](AGENTS.md) - how we work; repo context for coding agents (`CLAUDE.md` symlinks to it)
