# Viewer overlay toggles + cell bounds + Alt coordinate HUD — design

- Status: **proposed**. Scope: **viewer only** (`viewer/src/`); no contract / dataset / runs change.
  Canonical *why*: `docs/CHARTER.md`. Contract reference: `docs/specs/2026-06-15-region-cell-token-schema-design.md`
  + `docs/specs/2026-06-17-atomic-word-tokens-design.md` (schema v4: Region / Cell / Word).
- Date: 2026-06-18
- Self-contained on purpose — written so a fresh session can implement it without the originating
  conversation. Follow-on: an implementation plan in `docs/plans/`.

## Motivation

The viewer currently draws a fixed overlay over the page image: **regions** (table/form bounds, purple
dashed rects + label) and **words** (clickable rects filled + role-colored via their owning cell). Two
gaps:

- **Cells are invisible.** `Cell` is the structural unit carrying `row_index`/`column_index`/`span`/
  `role`/`field` and grouping words via `word_ids`, but nothing draws `cell.bbox`. Words only *borrow*
  the cell's role color (`cellByWord` in `DocumentViewer.tsx`). We can't visually inspect cell extents,
  spans, or how words group into cells.
- **The overlay is all-or-nothing.** Every layer is always on; you can't isolate one, and you can't see
  the **raw rendered page** by itself to judge visual realism.

We want a **rich, explorable overlay**: turn each element class (words / cells / tables) on or off
independently, starting from the raw image, plus a quick way to read off a coordinate while pointing at
the page (for cross-referencing the normalized `[0,1]` bboxes in the contract).

## Decisions

1. **Three independent overlay toggles** — `Words`, `Cells`, `Tables` — surfaced as toggle buttons in
   the top toolbar (`.viewer-toolbar`). State is **session-only** (React state, no persistence), and
   **all default off** so a freshly loaded sample shows only the raw page image.
2. **New cell-bounds layer.** Each `cell.bbox` draws as an **outline-only** rect (no fill), stroked in
   the cell's `role` color (reusing the existing `ROLE_COLOR` map). Outline-only keeps it legible over
   the filled word rects; role-coloring is correct because `role` is a cell attribute (words merely
   inherit it today). Non-interactive (`pointerEvents: none`) for now.
3. **Words layer stays as-is** — the colored, clickable word rects, including the role-derived coloring
   for header / group_header / section / summary / key / value. These are "word-derived" views and keep
   their current colors. Word click-selection only works while `Words` is on.
4. **Alt coordinate HUD.** Holding **Alt** while hovering the document shows the pointer's **normalized
   `[0,1]`** coordinates in a small fixed badge in a corner of the viewport. Implemented efficiently:
   the `pointermove` listener is attached **only while Alt is held** and the readout is written directly
   to the badge via a DOM ref (no React re-render per move).
5. **Controls legend** gains one row documenting the Alt gesture.

Out of scope: persistence across reloads; cell click/selection; pixel-coordinate readout; changes to the
bottom role legend; any contract/dataset/runs change.

## Changes

All changes are in `viewer/src/`.

### `DocumentViewer.tsx`

**Overlay visibility state.** Three booleans, all default `false`:

```ts
const [showWords, setShowWords]     = useState(false)
const [showCells, setShowCells]     = useState(false)
const [showRegions, setShowRegions] = useState(false)
```

- Gate each SVG layer: render the regions `<g>` only when `showRegions`, the cells `<g>` only when
  `showCells`, the words `<g>` only when `showWords`.
- When `Words` is toggled **off**, clear any current selection: `onSelectToken(null)` (a selected word
  whose rect is no longer drawn would otherwise be a dangling highlight). Do this in the toggle handler.
- Cells and regions render with `pointerEvents: none` (regions already do) so they never intercept
  pan/click; only word rects remain interactive, and only when `showWords` is on.

**New cells layer.** Between the regions layer and the words layer, draw cell outlines:

```tsx
{showCells && cells?.map((cell, i) => {
  const stroke = (ROLE_COLOR[cell.role] ?? COLOR_BACKGROUND).stroke
  const x = cell.bbox[0] * width
  const y = cell.bbox[1] * height
  const w = (cell.bbox[2] - cell.bbox[0]) * width
  const h = (cell.bbox[3] - cell.bbox[1]) * height
  return (
    <rect key={`cell-${i}`}
      x={x} y={y} width={w} height={h}
      fill="none" stroke={stroke} strokeWidth={1.5} rx={2}
      pointerEvents="none" />
  )
})}
```

(`cell.bbox` is `[x0,y0,x1,y1]` normalized, same convention as `word`/`region` already use.)

**Toolbar toggle group.** A new `.overlay-toggles` group placed between `.sample-nav` and
`.zoom-controls`. Three buttons, each with `aria-pressed` and an `is-active` class when on:

```tsx
<div className="overlay-toggles" aria-label="Overlay visibility">
  <button className={showWords ? 'is-active' : ''} aria-pressed={showWords}
    onClick={() => setShowWords(v => !v)}>Words</button>
  <button className={showCells ? 'is-active' : ''} aria-pressed={showCells}
    onClick={() => setShowCells(v => !v)}>Cells</button>
  <button className={showRegions ? 'is-active' : ''} aria-pressed={showRegions}
    onClick={() => setShowRegions(v => !v)}>Tables</button>
</div>
```

(The `Words` handler also clears selection when turning off, as noted above.)

**Alt coordinate HUD.**

- A `hudRef` to a `<div className="coord-hud">` rendered inside `.doc-viewport` (sibling of
  `.doc-surface`), hidden by default via a `hidden` class.
- A `window` keydown/keyup effect tracks Alt. On Alt **down**: attach a `pointermove` listener to the
  viewport and reveal the HUD. On Alt **up** (or `blur`): remove the listener and hide the HUD. This
  guarantees no per-move work unless Alt is held.
- The move handler computes normalized coords from `.doc-surface`'s `getBoundingClientRect()`:
  `nx = (e.clientX - rect.left) / rect.width`, `ny = (e.clientY - rect.top) / rect.height`. If outside
  `[0,1]` on either axis, hide the HUD (pointer is off the page); otherwise write
  `` `${nx.toFixed(3)}, ${ny.toFixed(3)}` `` to `hudRef.current.textContent` directly — **no React
  state**, so hovering does not re-render the overlay.
- Use the `.doc-surface` rect (not the viewport) so coordinates are relative to the page image and stay
  correct under zoom/pan (the surface is the transformed element).

### `ViewerHelp.tsx`

Add one row to `CONTROLS`:

```ts
['Alt + hover', 'Show normalized coords'],
```

### `App.css`

- `.overlay-toggles` — a flex group mirroring `.zoom-controls` spacing; `.is-active` buttons get a filled
  accent background (e.g. the existing blue `#378ADD` family) with light text so active layers read at a
  glance. Reuse `.viewer-toolbar button` base styling.
- `.coord-hud` — `position: absolute`, pinned bottom-left of `.doc-viewport`, small monospace badge with
  a semi-opaque dark background + light text, `pointer-events: none`, `z-index` above the surface. A
  `.coord-hud.hidden { display: none }` variant.

## Data flow

```
sample.cells[]  ──(showCells)──▶  cell outline rects   (role-colored stroke, no fill)
sample.words[]  ──(showWords)──▶  word rects           (role fill, clickable → onSelectToken)
sample.regions[]──(showRegions)─▶  region rects + label (dashed)

Alt held → pointermove on viewport → normalized coords from .doc-surface rect
        → hudRef.textContent  (direct DOM write, no re-render)
```

No new props on `DocumentViewer`; all state is internal. `cellByWord` (word→cell role lookup) is
unchanged and still drives word coloring.

## Edge cases

- **Word selected, then `Words` toggled off** → selection cleared in the toggle handler; re-enabling
  starts unselected.
- **Sample with no cells/regions** (`cells: []`, `regions` undefined) → layers render nothing; toggles
  still operate harmlessly. Existing `?? []` guards cover this.
- **Alt released while pointer off-window** → `keyup` may not fire; the `window` `blur` handler also
  tears down the listener and hides the HUD.
- **Zoom/pan during Alt hover** → coords derive from the live `.doc-surface` rect each move, so they stay
  correct without recomputing transforms.
- **Alt is also a browser/OS modifier** → the handlers are read-only (we never `preventDefault`), so
  holding Alt must not steal focus or trigger native menus; we only observe the held state.

## Testing / verification

No automated tests (repo convention: implement + verify by running). Verify in the viewer
(`npm --prefix viewer run dev`) against an `eob` dataset:

1. Fresh load shows the **raw image only** (no overlays).
2. Each toggle independently shows/hides its layer; combinations compose correctly.
3. Cell outlines are role-colored, outline-only, and align with word groupings.
4. Word selection works with `Words` on; toggling `Words` off clears the highlight.
5. Holding Alt shows the normalized-coord badge tracking the pointer; releasing Alt hides it; corner
   bboxes read ≈ `0.000, 0.000` / `1.000, 1.000`; coords stay correct after zoom/pan.
6. Hovering without Alt does no work (no badge, no re-render).
```
