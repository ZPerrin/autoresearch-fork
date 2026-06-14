# Synthetic data toolkit — compositional API + CLI backbone

- Status: **design** (approved in brainstorming; first slice of the active "synthetic data toolkit" milestone)
- Date: 2026-06-13
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md` (§ "Active milestone: the synthetic data toolkit")

## Scope

This is the **backbone only**: decompose the monolithic `generate.py` into a compositional spec
API (`FieldSpec` / `LayoutSpec` / `StructureSpec` / `RenderSpec` / `DocumentClass`) plus a CLI
(`build` / `list` / `inspect`), **reproducing today's output exactly** (one token per cell, the three
existing schemas as registered document classes). No new structural realism in this slice.

The point of building the abstraction first: each of the six structural-realism features (see
**Enhancement trajectory** below) then lands as a small additive change — a `StructureSpec` /
`LayoutSpec` knob plus a layout-stage change — rather than a rewrite. The trajectory is recorded
here so we don't lose sight of it; each feature gets its own bite-sized spec when started.

Out of scope: any structural-realism feature, visual realism (the `RenderSpec` seam is provisioned
but only a Pillow renderer exists), the model loop, annotation schema.

## Architecture

Generation is split into a **layout stage** (produces placed tokens) and a **render stage** (draws
them), joined by an explicit intermediate representation (`PlacedToken`). Every future feature
changes *what tokens exist and where they sit* (layout); deferred visual realism changes *how they
are drawn* (render). The IR is the seam that keeps the two independent.

```
get(class) → fork(overrides) → resolved DocumentClass
   for i in range(n):
     LayoutEngine(spec, rng) → [PlacedToken]      # sample values, compute pixel boxes (no Pillow)
     PillowRenderer.render(placed, page) → PNG     # draw, tighten boxes to glyph extents
     → contract Tokens (normalize [0,1], shuffle) → Sample(image=…)
   write_dataset(manifest{resolved spec + seed}, samples)
```

### Module layout

Decompose the single `generate.py` into focused, single-purpose modules under
`harness/src/tablelab/`:

| Module | Responsibility | Holds |
|---|---|---|
| `specs.py` | Pure data — the compositional spec | `FieldSpec`, `LayoutSpec`, `StructureSpec`, `RenderSpec`, `DocumentClass`, `fork()` |
| `fields.py` | Value samplers | semantic-type registry: `"amount"→_money`, `"date"→_date`, … (today's `FIELD_TYPES`) |
| `classes.py` | DocumentClass registry | `register` / `get` / `classes` + built-in `invoice` / `eob` / `receipt` |
| `layout.py` | Logical placement | `PlacedToken` + `LayoutEngine`: spec + rng → `list[PlacedToken]` |
| `render.py` | Pixels | `Renderer` protocol + `PillowRenderer`: PlacedTokens → PNG, tighten boxes |
| `build.py` | Orchestrator | `build_dataset()`: compose → per sample layout→render→convert→`Sample` → `write_dataset` |
| `cli.py` | Entry point | `argparse` + `tqdm`: `build` / `list` / `inspect` |

`generate.py` is retired (no consumers yet); its `build_dataset` moves to `build.py`.

## Data types

```python
# specs.py — frozen dataclasses, pure data
FieldSpec(name="amount", type="amount", align="right")    # type → key into fields.py samplers
LayoutSpec(rows=(2,6), page=(1000,1414), margin=(60,80), row_h=74, pad=12)
StructureSpec()         # named seam for the six follow-ons; minimal today, documented
RenderSpec(font_size=22, renderer="pillow")               # the visual-realism seam
DocumentClass(name, fields=(FieldSpec,...), layout=LayoutSpec(),
              structure=StructureSpec(), render=RenderSpec())

# fork(): copy a DocumentClass with top-level / nested overrides → new named class
#   (dataclasses.replace under the hood; CLI overrides apply to LayoutSpec)
```

```python
# layout.py — the IR
@dataclass
class PlacedToken:
    text: str
    box: tuple[float, float, float, float]   # pixel x0,y0,x1,y1
    label: dict | None                       # {"record": r, "field": c}
    align: str = "left"
    font_size: int = 22
```

`PlacedToken` is a generation-time object, distinct from the contract `Token`. It carries pixel
boxes and draw metadata (alignment, font size); it is converted to a contract `Token` (boxes
normalized to `[0,1]`, stripped to `text` + box + `label`) only at the final step. `label` is an
open dict mirroring the contract: `null` = background (follow-on 3), a repeated label = multi-token
cell (follow-on 1), an added `region` key = multi-table (follow-on 4).

### Built-in classes

The three existing `SCHEMAS` become registered `DocumentClass`es; each column maps to a `FieldSpec`
(`type` + `align` from today's `FIELD_TYPES`). Field **names** are cosmetic (manifest only — the
`label` keys on `record`/`field` by index), so they may be made more descriptive (e.g. EOB's two
`amount` columns → `amount_billed` / `amount_owed`) without changing rendered pixels.

- `invoice`: description, quantity, unit_price, amount
- `eob`: date, code, description, amount, amount
- `receipt`: description, amount

## CLI

`python -m tablelab.cli`, run from `harness/`:

- `build --class <name> --n <count> --out ../datasets/<id> [--seed 7] [--rows MIN MAX] [--page W H]`
  — compose class, apply overrides onto `LayoutSpec`, `tqdm` over samples, write under `datasets/`.
  `dataset_id` = basename of `--out`.
- `list [--datasets-dir ../datasets]` — scan local datasets, print `id · class · count · created`.
- `inspect <id> [--datasets-dir ../datasets]` — print resolved manifest + quick stats (token count,
  fields, page).

## Manifest / reproducibility

`build_dataset` records the **resolved** `DocumentClass` (after overrides) plus `seed` in the
dataset manifest `config`, so a dataset is reproducible and forkable. Existing manifest fields
(`task = "grid_record_field"`, `modalities`, `count`) are unchanged.

## Determinism & verification

The refactor **preserves the RNG call order** of today's `generate_sample` (per sample:
`randint` for row count → `sampler(rng)` per cell in row-major order → `shuffle` of the tokens), so
for a given seed it produces **byte-identical** `samples.json` and images. This is the primary
correctness anchor:

- **Golden snapshot**: build a small dataset on `master` before the refactor; assert the refactored
  builder reproduces identical `samples.json` + image bytes for the same seed. (Manifest is exempt —
  it intentionally changes to record the resolved spec.)
- **Smoke**: `build` / `list` / `inspect` run without error; `inspect` stats match the manifest.
- **Eyeball**: build a fresh dataset and view it in the viewer (boxes + labels look right).

No TDD (per repo conventions) — implement and verify by running.

## Enhancement trajectory (follow-on specs, not this slice)

Recorded so the abstraction is designed to absorb them; all land as `StructureSpec` / `LayoutSpec`
knobs + a layout-stage change, renderer untouched:

1. **multi-token cells** — one cell emits N `PlacedToken`s sharing a `label` (biggest realism jump).
2. **header row** — emit a header row of field-name tokens.
3. **background / non-table tokens** — emit `PlacedToken`s with `label = null`.
4. **multiple tables + global fields** — `label` gains a `region` key; layout places multiple grids
   + singleton fields (the EOB shape).
5. **jitter / irregular** — `LayoutSpec` row-height / column-width randomization.
6. **spanning / merged cells** — merged-cell placement.

Then **document-class breadth** (EOB prioritized — it mirrors the real multi-table + globals
problem).

## Open questions

- `fork()` ergonomics for nested specs (flat kwargs vs. nested replace) — settle during implementation.
- Default `--datasets-dir` discovery (relative `../datasets` vs. walk up to repo root) — start with
  relative, revisit if it bites.
