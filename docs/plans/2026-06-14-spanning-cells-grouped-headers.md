# Spanning cells + grouped headers — implementation plan

> **For agentic workers:** implement task-by-task. This repo is **no-TDD** (AGENTS.md: "implement
> and verify by running"); tests are added alongside the code, not test-first. Steps use checkbox
> (`- [ ]`) syntax for tracking. Run all Python commands from `harness/` via `uv run`.

**Goal:** Add a colspan primitive expressed as grouped-header banners and spanning data rows
(section + totals), gated so default-off output stays byte-identical, and showcase it on the `eob`
class.

**Architecture:** Spec knobs (`FieldSpec.group`, `SpanCell`/`SpanRowSpec`, `TableSpec.section/totals`)
+ layout-stage emission. The renderer is untouched (it groups tokens by cell rect; a spanning cell is
one wider rect). New label keys ride the open observables contract. See
`docs/specs/2026-06-14-spanning-cells-grouped-headers-design.md`.

**Tech Stack:** Python (`uv`, dataclasses, Pillow), pytest; React/Vite viewer (one small `MetaPanel`
touch).

**Branch:** `feat/spanning-cells-grouped-headers` off `master`. Merge to `master` after the golden
test passes and a smoke dataset renders cleanly.

---

### Task 1: Spec API additions

**Files:**
- Modify: `harness/src/tablelab/specs.py`

- [ ] **Step 1: Add `group` to `FieldSpec`**

Add field after `fill`:
```python
    group: str | None = None  # contiguous fields sharing a group name form one banner cell
```

- [ ] **Step 2: Add `SpanCell` and `SpanRowSpec` dataclasses** (above `TableSpec`)

```python
@dataclass(frozen=True)
class SpanCell:
    span: int = 1              # columns this cell covers
    text: str | None = None    # literal label (e.g. "TOTALS")
    type: str | None = None    # value sampler key (e.g. "amount", "category"); xor with text
    align: str = "left"


@dataclass(frozen=True)
class SpanRowSpec:
    """A row whose cells each cover a contiguous column range. Spans must sum to the
    table's field count. Used as a section row (before records) or totals row (after)."""
    cells: tuple[SpanCell, ...]
```

- [ ] **Step 3: Add `section`/`totals` slots to `TableSpec`**

```python
    section: SpanRowSpec | None = None   # emitted once before each instance's records
    totals:  SpanRowSpec | None = None   # emitted once after each instance's records
```

- [ ] **Step 4: Update `StructureSpec` docstring** to mention spanning cells/grouped headers are now
implemented (replace the parenthetical "spanning cells" note).

- [ ] **Step 5: Verify import + golden unaffected**

Run: `cd harness && uv run python -c "from tablelab.specs import SpanCell, SpanRowSpec, FieldSpec, TableSpec; print('ok')"`
Run: `cd harness && uv run pytest tests/test_golden.py -q`
Expected: `ok`; golden PASS (new optional fields default off → byte-identical).

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/specs.py
git commit -m "feat(specs): group + SpanCell/SpanRowSpec + section/totals slots (data only)"
```

---

### Task 2: `category` sampler

**Files:**
- Modify: `harness/src/tablelab/fields.py`

- [ ] **Step 1: Inspect the sampler registry** to match the existing pattern (how `SAMPLERS` and a
sampler function are defined; how `sample(type, rng)` dispatches).

Run: `cd harness && uv run python -c "import tablelab.fields as f; print([k for k in f.SAMPLERS])"`

- [ ] **Step 2: Add a `category` vocabulary + sampler** following the existing style, e.g.

```python
_CATEGORY = ("Office Visits", "Lab Services", "Radiology", "Pharmacy",
             "Preventive Care", "Emergency Services", "Physical Therapy")

def _category(rng):
    return rng.choice(_CATEGORY)
```
Register it under key `"category"` in `SAMPLERS` (mirror the registration of the other samplers).

- [ ] **Step 3: Verify**

Run: `cd harness && uv run python -c "import random, tablelab.fields as f; print(f.sample('category', random.Random(0)))"`
Expected: one of the category strings.
Run: `cd harness && uv run pytest tests/test_golden.py -q`  → PASS (no existing class uses it).

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/fields.py
git commit -m "feat(fields): category sampler for section-row labels"
```

---

### Task 3: Validation

**Files:**
- Modify: `harness/src/tablelab/layout.py` (extend `_validate_layout`)

- [ ] **Step 1: Add a span-row + group validator** invoked from `_validate_layout` for each table.

```python
def _validate_span_rows(dc, table):
    C = len(table.fields)
    if any(f.group for f in table.fields) and not dc.structure.header:
        raise LayoutCapacityError(
            f"table {table.name!r} sets field group(s) but structure.header is off; "
            "grouped-header banners require a leaf header row"
        )
    for slot, srow in (("section", table.section), ("totals", table.totals)):
        if srow is None:
            continue
        total = sum(cell.span for cell in srow.cells)
        if total != C:
            raise LayoutCapacityError(
                f"table {table.name!r} {slot} spans sum to {total}, expected {C}"
            )
        for cell in srow.cells:
            if cell.span < 1:
                raise LayoutCapacityError(
                    f"table {table.name!r} {slot} has a cell span {cell.span} < 1"
                )
            if cell.text is not None and cell.type is not None:
                raise LayoutCapacityError(
                    f"table {table.name!r} {slot} cell sets both text and type"
                )
```

Call `_validate_span_rows(dc, table)` inside the existing `for table in dc.tables:` loop in
`_validate_layout`.

- [ ] **Step 2: Verify validation fires**

Run a quick inline check that a bad span sum raises `LayoutCapacityError`, and that a `group` without
`header` raises. (Construct a throwaway `DocumentClass` in a `uv run python -c` snippet.)

- [ ] **Step 3: Golden still passes**

Run: `cd harness && uv run pytest tests/test_golden.py -q` → PASS

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat(layout): validate span-row spans + group requires header"
```

---

### Task 4: Capacity terms for the new fixed rows

**Files:**
- Modify: `harness/src/tablelab/layout.py` (`_instance_height`)

- [ ] **Step 1: Add per-instance constant rows** to `_instance_height`. The banner band exists when
any field is grouped (and header is on, already required by validation); section/totals each add a
row.

```python
def _instance_height(dc, rows, table=None):
    L = dc.layout
    header = int(dc.structure.header)
    if table is not None:
        banner  = int(any(f.group for f in table.fields)) and header
        section = int(table.section is not None)
        totals  = int(table.totals is not None)
    else:
        banner = section = totals = 0
    fixed_rows = header + banner + section + totals
    return (fixed_rows * L.row_h + rows * L.row_h
            + max(rows - 1, 0) * _row_gap(dc) + _instance_gap(dc))
```

- [ ] **Step 2: Thread `table` through callers.** Pass the current `table` at every `_instance_height`
call site that has one: `_shape_height` (iterate tables alongside shape), `_minimum_shape_height`,
`_iter_table_shapes`, `_iter_feasible_shapes` (`table_options`), and `_is_safe_legacy`'s `maximum`
computation. The single-table legacy path passes `dc.tables[0]`. Keep the default `table=None` so any
call without a table (none expected after threading) is still valid.

- [ ] **Step 3: Verify capacity math** — a page tall enough for data but not the extra rows fails with
`LayoutCapacityError`; a comfortably tall page succeeds. Quick inline `uv run python -c` check using a
small grouped/totals class on a deliberately short page.

- [ ] **Step 4: Golden still passes** (invoice has no table-driven extras; `table` arg is benign).

Run: `cd harness && uv run pytest tests/test_golden.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat(layout): account for banner/section/totals rows in capacity"
```

---

### Task 5: Emit the grouped-header banner band

**Files:**
- Modify: `harness/src/tablelab/layout.py` (`layout()`)

- [ ] **Step 1: Add a contiguous-run helper**

```python
def _group_runs(fields):
    """Yield (group_name, c0, c1) inclusive ranges for each maximal run of equal
    non-None group. None columns are skipped (blank banner slot)."""
    runs, i, n = [], 0, len(fields)
    while i < n:
        g = fields[i].group
        j = i
        while j + 1 < n and fields[j + 1].group == g:
            j += 1
        if g is not None:
            runs.append((g, i, j))
        i = j + 1
    return runs
```

- [ ] **Step 2: Emit the banner row** in `layout()`, immediately before the existing `if header:`
block, inside the per-instance loop. Use the resolved `edges` (already computed for the instance).

```python
            grouped = any(f.group for f in table.fields)
            if grouped:
                for name, c0, c1 in _group_runs(table.fields):
                    cell = (edges[c0], y, edges[c1 + 1], y + L.row_h)
                    _emit(placed, name, cell,
                          {**reg, "field": c0, "header": True,
                           "group": name, "span": [c0, c1]},
                          "left", cell_font, multi)
                y += L.row_h
```

(`reg` and `edges`/`cell_font` are already in scope at that point; confirm ordering — `edges` is
resolved just above the `if header:` block.)

- [ ] **Step 3: Verify geometry** — build a tiny grouped class inline; assert banner tokens sit one
`row_h` above the leaf header tokens, and each banner's x-range equals `edges[c0]..edges[c1+1]`.

- [ ] **Step 4: Golden still passes** (no field grouped → block skipped, no RNG/tokens).

Run: `cd harness && uv run pytest tests/test_golden.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat(layout): grouped-header banner band over contiguous field runs"
```

---

### Task 6: Emit section + totals spanning rows

**Files:**
- Modify: `harness/src/tablelab/layout.py` (`layout()`)

- [ ] **Step 1: Add a span-row emitter helper**

```python
def _emit_span_row(placed, cells, edges, y, row_h, base_label, font, multi, rng):
    """Emit one spanning row. Each cell covers a contiguous column range starting at
    the running column index; text cells are literal, type cells are sampled, empty
    cells emit nothing. Label gets field=c0 and span=[c0,c1] (+ base_label)."""
    c = 0
    for cell in cells:
        c0, c1 = c, c + cell.span - 1
        rect = (edges[c0], y, edges[c1 + 1], y + row_h)
        if cell.text is not None:
            value = cell.text
        elif cell.type is not None:
            value = sample(cell.type, rng)
        else:
            value = ""
        if value:
            _emit(placed, value, rect,
                  {**base_label, "field": c0, "span": [c0, c1]},
                  cell.align, font, multi)
        c = c1 + 1
```

- [ ] **Step 2: Emit the section row** right after the leaf-header block and before the data-row loop,
inside the per-instance loop:

```python
            if table.section is not None:
                _emit_span_row(placed, table.section.cells, edges, y, L.row_h,
                               {**reg, "section": True}, cell_font, multi, rng)
                y += L.row_h
```

- [ ] **Step 3: Emit the totals row** right after the data-row loop, before `y += _instance_gap(dc)`:

```python
            if table.totals is not None:
                # header=True on the spanning label cell(s); value cells carry subtotal only.
                base = {**reg, "subtotal": True}
                _emit_span_row(placed, table.totals.cells, edges, y, L.row_h,
                               base, cell_font, multi, rng)
                y += L.row_h
```

Note on totals label vs value: per the spec, label cells (text) should also carry `header: True`. Set
that on the literal-label cells inside `_emit_span_row` by adding `"header": True` when
`cell.text is not None`. Adjust the helper to merge `{"header": True}` for text cells.

- [ ] **Step 4: Verify** — build the inline class with section + totals; assert section row is above
data, totals below; totals value cells land under their numeric columns (`field` matches column);
section label is one of the `category` vocab.

- [ ] **Step 5: Golden still passes** (no section/totals → skipped, no RNG/tokens).

Run: `cd harness && uv run pytest tests/test_golden.py -q` → PASS

- [ ] **Step 6: Commit**

```bash
git add harness/src/tablelab/layout.py
git commit -m "feat(layout): section + totals spanning data rows"
```

---

### Task 7: `eob` recipe showcase

**Files:**
- Modify: `harness/src/tablelab/classes.py`

- [ ] **Step 1: Add groups + structure.header + section + totals to the `eob` `claim_line`.**
Enable `structure.header=True` on the class (banners require it). Set `group=` on the `_f(...)`
columns:
- `amount_billed`, `allowed` → `group="Charges"`
- `deductible`, `copay`, `coinsurance` → `group="Patient Responsibility"`
- `plan_paid`, `amount_owed` → `group="Plan & Balance"`
- `service_date`, `code`, `description` → no group.

Extend `_f` with a `group` passthrough if needed.

Add to the `TableSpec`:
```python
        section=SpanRowSpec((SpanCell(span=10, type="category"),)),
        totals=SpanRowSpec((
            SpanCell(span=3, text="TOTALS"),
            SpanCell(span=1, type="amount", align="right"),  # amount_billed
            SpanCell(span=1, type="amount", align="right"),  # allowed
            SpanCell(span=1, type="amount", align="right"),  # deductible
            SpanCell(span=1, type="amount", align="right"),  # copay
            SpanCell(span=1, type="amount", align="right"),  # coinsurance
            SpanCell(span=1, type="amount", align="right"),  # plan_paid
            SpanCell(span=1, type="amount", align="right"),  # amount_owed
        )),
```
Import `SpanCell`, `SpanRowSpec`, and `StructureSpec` in `classes.py`.

- [ ] **Step 2: Validate the class composes + fits**

Run: `cd harness && uv run python -c "from tablelab.classes import get; from tablelab.layout import validate_layout_capacity; validate_layout_capacity(get('eob')); print('eob ok')"`
Expected: `eob ok` (the wide 1500x1414 page must still fit globals + banner + leaf header + section +
data + totals; if it fails, the error reports the shortfall — reduce `rows`/`instances` range or
raise the page height as a recipe fix).

- [ ] **Step 3: Golden still passes** (invoice unchanged).

Run: `cd harness && uv run pytest tests/test_golden.py -q` → PASS

- [ ] **Step 4: Commit**

```bash
git add harness/src/tablelab/classes.py
git commit -m "feat(classes): eob grouped headers + section + totals showcase"
```

---

### Task 8: Tests

**Files:**
- Create: `harness/tests/test_spanning.py`

- [ ] **Step 1: Write unit tests** covering (use `random.Random(0)` and small inline classes):
  - `_group_runs` returns correct inclusive ranges; two non-adjacent same-name runs → two banners.
  - banner tokens sit one row above leaf headers; banner x-range == `edges[c0]..edges[c1+1]`.
  - geometry order top→bottom: banner, leaf header, section, data, totals.
  - validation: span sum ≠ field count raises; `text`+`type` both set raises; `group` without
    `header` raises.
  - capacity: a short page that fits data but not the extra rows raises `LayoutCapacityError`.
  - `multi_token` splits a multi-word banner label ("Patient Responsibility" → 2 tokens, shared cell,
    `seq` 0/1).
  - totals value cells populate under each numeric column (`field` indices 3..9 present).
  - section label ∈ the `category` vocab.

- [ ] **Step 2: Run the new tests + full suite**

Run: `cd harness && uv run pytest -q`
Expected: all PASS (including `test_golden`, `test_jitter`, `test_spacing`).

- [ ] **Step 3: Commit**

```bash
git add harness/tests/test_spanning.py
git commit -m "test: spanning cells + grouped headers"
```

---

### Task 9: Viewer — features readout

**Files:**
- Modify: `viewer/src/MetaPanel.tsx`

- [ ] **Step 1: Inspect how MetaPanel derives "enabled structural features"** from the resolved spec
(`manifest.config.spec`). Find where header/background/multi_token/jitter flags are listed.

- [ ] **Step 2: Add grouped-headers / section-rows / totals-rows flags** derived from the resolved
spec: grouped headers when any table field has `group`; section rows when any table has `section`;
totals rows when any table has `totals`. Match the existing label/style of the features list.

- [ ] **Step 3: Build the viewer**

Run: `npm --prefix viewer run build`
Expected: clean TypeScript/Vite production build.

- [ ] **Step 4: Commit**

```bash
git add viewer/src/MetaPanel.tsx
git commit -m "feat(viewer): surface grouped-header/section/totals features in metadata"
```

---

### Task 10: Smoke build + final verification

**Files:** none (verification only).

- [ ] **Step 1: Build a showcase dataset**

Run: `cd harness && uv run python -m tablelab.cli build --class eob --n 8 --out ../datasets/eob-grouped`
Expected: succeeds; writes images + samples.

- [ ] **Step 2: Inspect it**

Run: `cd harness && uv run python -m tablelab.cli inspect ../datasets/eob-grouped`
Expected: token counts reflect the extra banner/section/totals tokens; resolved spec shows the new
features.

- [ ] **Step 3: Eyeball in the viewer** (manual): `npm --prefix viewer run dev`, open the dataset,
confirm the banner band, section heading, and `TOTALS` row render with boxes in-page, and token
detail shows `group`/`section`/`subtotal`/`span` keys. (Surface as a blocker if anything renders
out-of-page or misaligned.)

- [ ] **Step 4: Update docs.** Flip the design-doc status to **shipped**; update `AGENTS.md`
"Current state" + the roadmap (`docs/specs/2026-06-13-design-and-roadmap.md` item 6 → ✅) and
`harness/README.md` if it enumerates structural knobs.

- [ ] **Step 5: Commit docs, then merge to `master`**

```bash
git add -A && git commit -m "docs: mark spanning cells + grouped headers shipped"
git checkout master && git merge --no-ff feat/spanning-cells-grouped-headers
```

(`datasets/` is gitignored — the `eob-grouped` dataset is local only.)

---

## Self-review

- **Spec coverage:** spec API (T1/T2), validation (T3), capacity (T4), banner emission (T5), span rows
  (T6), label schema (T5/T6 — group/section/subtotal/span keys), eob recipe (T7), byte-identical
  off-path (golden run in every task), viewer features readout (T9), verification incl. smoke (T8/T10).
  Out-of-scope items (row-span, nested banners, banner-driven widths, consistent totals, visual
  styling, CLI toggles) are intentionally untouched.
- **Type consistency:** `_instance_height(dc, rows, table=None)` signature is introduced in T4 and used
  consistently; `_emit_span_row(..., rng)` defined in T6 and used for section + totals;
  `_group_runs` defined T5 used T5/T8; label keys (`group`/`section`/`subtotal`/`span`/`field`) match
  the design table.
- **Placeholders:** none — each step has concrete code or an exact command. Test bodies in T8 are
  enumerated as concrete assertions to write (the only deliberately list-form step, per repo no-TDD).
</content>
