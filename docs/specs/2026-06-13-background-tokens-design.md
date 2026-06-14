# Background / non-table tokens — design

- Status: **design** (full-agentic build; third structural-realism feature)
- Date: 2026-06-13
- Parent: `docs/specs/2026-06-13-design-and-roadmap.md` (§ structural realism). Follows
  `2026-06-13-header-row-design.md`.

## Goal

Scatter **non-table tokens** (page noise — titles, footer notes, account refs) across the page with
`label = None`: the negative class for "is this token part of the answer?". Gated behind a
`StructureSpec.background` count; **default 0 is byte-identical** to current output (golden guards it).

## Decisions

1. **Knob:** `StructureSpec.background: int = 0` — the number of non-table tokens to scatter per page.

2. **Label:** `label = None`. This is the explicit negative class; it passes straight through the
   contract (`Token.label = None`) and the viewer renders it neutrally. Background tokens are **always
   single tokens** (not split under `multi_token`) — they are noise, not structured answers, so the
   `seq` grouping question never arises and `label` stays cleanly `None`.

3. **Placement:** scattered in the **footer band below the table** — random `x` across the table
   width, random `y` in `[table_bottom, page_h - margin_y - row_h]`, where
   `table_bottom = margin_y + (header? 1 : 0 + rows) * row_h`. Each background token gets its own cell
   rect at its placement, so the cell-keyed renderer treats it as a singleton (legacy single-token
   draw path). The distinct y band keeps them from colliding with table cells. (Top-strip / margin
   placement is a later refinement; footer noise is realistic for invoices/EOBs and always has room
   on the default page.)

4. **Text:** a small page-noise pool in `fields.py` (`_BACKGROUND`: "INVOICE", "STATEMENT",
   "Confidential", "Account", "Balance", "Page", … ) plus an occasional random number, via a
   `background_token(rng)` sampler. Single words only.

5. **Determinism / byte-identical (off path):** the background block runs only when `background > 0`,
   appending tokens after the data rows and before the final shuffle, so with `background = 0` no
   extra RNG is drawn and output is unchanged. The golden test is the guard.

6. **CLI:** `build --background N` (composable with `--header` / `--multi-token`).

## Verification

- **Golden (off):** `tests/test_golden.py` still passes (byte-identical).
- **New tests:** `background=N` yields exactly `N` tokens with `label is None`; every background token
  sits at or below the table's bottom (y not overlapping the data rows); table + header tokens are
  unaffected and still labeled; `background=0` (default) produces no `None`-label tokens; build →
  contract round-trips `label: null`.
- **Smoke:** `build --background 5` then `inspect` shows `+5` tokens/sample; viewer renders the noise
  tokens neutrally below the table.

## Out of scope

- Top-of-page / margin / sidebar noise placement, and noise that overlaps the table (watermarks) —
  later refinements.
- Multi-word background tokens with internal structure — single tokens suffice for the negative class.

## Trajectory note

Third confirmation of the pattern, and the first to exercise `label = null` end-to-end (layout →
render's cell-key grouping → contract → viewer). Next after this: **multiple tables + global fields**
(the EOB shape; adds a `region` to the label).
