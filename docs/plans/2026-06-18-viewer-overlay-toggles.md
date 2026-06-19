# Viewer Overlay Toggles + Cell Bounds + Alt Coord HUD — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`)
> syntax for tracking.

**Goal:** Add independent show/hide toggles for the viewer's Words / Cells / Tables overlay layers
(default all off → raw image), a new outline-only role-colored cell-bounds layer, and an Alt-gated
normalized-coordinate HUD.

**Architecture:** Viewer-only change in `viewer/src/`. Three session-only `useState` booleans gate the
SVG overlay layers in `DocumentViewer.tsx`; a new cells `<g>` mirrors the existing word/region layers; an
Alt keydown/keyup effect attaches a `pointermove` listener only while Alt is held and writes normalized
coords straight to a DOM ref (no per-move re-render). No contract / dataset / runs change.

**Tech Stack:** React + TypeScript (Vite), inline SVG overlay, CSS in `App.css`.

**Spec:** `docs/specs/2026-06-18-viewer-overlay-toggles-design.md`.

**Project conventions:** No TDD — implement and verify by **running the viewer**
(`npm --prefix viewer run dev` → http://localhost:5173, open an `eob` dataset). Keep commits small and
append-only. Run `npm --prefix viewer run build` before the final commit to catch TS/type errors.

---

### Task 1: Overlay visibility state + gate existing layers + toolbar toggle group

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/App.css`

- [ ] **Step 1: Add the three session-only visibility booleans**

In `DocumentViewer.tsx`, alongside the other `useState` calls near the top of the component (after the
`const [zoom, setZoom] = useState(1)` block, around line 49), add:

```tsx
  const [showWords, setShowWords]     = useState(false)
  const [showCells, setShowCells]     = useState(false)
  const [showRegions, setShowRegions] = useState(false)
```

- [ ] **Step 2: Add the Words toggle handler that also clears selection**

Add this callback near the other `useCallback` handlers (e.g. just before `handleTokenClick`, ~line 250).
Turning Words off must clear any dangling selection:

```tsx
  const toggleWords = useCallback(() => {
    setShowWords(prev => {
      if (prev) onSelectToken(null)   // hiding words: drop any selection highlight
      return !prev
    })
  }, [onSelectToken])
```

- [ ] **Step 3: Gate the existing regions layer**

In the JSX, the regions layer currently starts with `{regions.map((rg, i) => (`. Wrap it so it only
renders when `showRegions` is on. Change:

```tsx
            {regions.map((rg, i) => (
```

to:

```tsx
            {showRegions && regions.map((rg, i) => (
```

(The `regions.map(...)` block already ends with `))}` — leave that as-is; the leading `{showRegions &&`
pairs with the existing closing `}`.)

- [ ] **Step 4: Gate the existing words layer**

The words layer currently starts with `{words.map((word, i) => {`. Change it to:

```tsx
            {showWords && words.map((word, i) => {
```

(Existing closing `})}` is unchanged.)

- [ ] **Step 5: Add the toolbar toggle group**

In the `.viewer-toolbar`, insert a new group between the `.sample-nav` div (which ends at `</div>` after
the Next button, ~line 326) and the `.zoom-controls` div (~line 327). Add:

```tsx
        <div className="overlay-toggles" aria-label="Overlay visibility">
          <button
            className={showWords ? 'is-active' : ''}
            aria-pressed={showWords}
            onClick={toggleWords}
          >
            Words
          </button>
          <button
            className={showCells ? 'is-active' : ''}
            aria-pressed={showCells}
            onClick={() => setShowCells(v => !v)}
          >
            Cells
          </button>
          <button
            className={showRegions ? 'is-active' : ''}
            aria-pressed={showRegions}
            onClick={() => setShowRegions(v => !v)}
          >
            Tables
          </button>
        </div>
```

- [ ] **Step 6: Add toolbar toggle styling**

In `App.css`, after the `.zoom-controls .fit-button { … }` rule (~line 422), add:

```css
.overlay-toggles {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.overlay-toggles button {
  min-width: 52px;
  padding-inline: 9px;
}

.overlay-toggles button.is-active {
  background: #378ADD;
  border-color: #2f78c2;
  color: #fff;
}

.overlay-toggles button.is-active:hover:not(:disabled) {
  background: #2f78c2;
}
```

- [ ] **Step 7: Verify by running**

Run: `npm --prefix viewer install` (first time only), then `npm --prefix viewer run dev`
Open http://localhost:5173, select an `eob` dataset.
Expected: fresh load shows the **raw image only** (no overlays). The toolbar shows `Words` `Cells`
`Tables` buttons between sample-nav and zoom-controls. Clicking `Words` shows/hides the colored word
rects and highlights the button; clicking `Tables` shows/hides the dashed region bounds. (`Cells` does
nothing yet — added in Task 2.) Selecting a word then clicking `Words` off clears the highlight.

- [ ] **Step 8: Commit**

```bash
git add viewer/src/DocumentViewer.tsx viewer/src/App.css
git commit -m "feat(viewer): session toggles for words/tables overlays (default off)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Cell-bounds overlay layer

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`

- [ ] **Step 1: Add the cells layer to the SVG**

In `DocumentViewer.tsx`, the SVG layers render in order: regions, then words. Insert a cells layer
**between** them — i.e. after the regions block's closing `))}` and before
`{showWords && words.map((word, i) => {`. Add:

```tsx
            {showCells && (cells ?? []).map((cell, i) => {
              const stroke = (ROLE_COLOR[cell.role] ?? COLOR_BACKGROUND).stroke
              const x = cell.bbox[0] * width
              const y = cell.bbox[1] * height
              const w = (cell.bbox[2] - cell.bbox[0]) * width
              const h = (cell.bbox[3] - cell.bbox[1]) * height
              return (
                <rect
                  key={`cell-${i}`}
                  x={x} y={y} width={w} height={h}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={1.5}
                  rx={2}
                  pointerEvents="none"
                />
              )
            })}
```

Note: `ROLE_COLOR` and `COLOR_BACKGROUND` are already defined at the top of the file (lines 12–21);
`cells` is already destructured from `sample` (line 293). `cell.bbox` is normalized `[x0,y0,x1,y1]`,
the same convention regions/words use.

- [ ] **Step 2: Verify by running**

With the dev server running, reload and open an `eob` dataset.
Expected: clicking `Cells` draws **outline-only** rects (no fill) stroked in each cell's role color
(blue data, purple headers, orange sections, green summaries, etc.), aligning with where words group into
cells. Cell outlines never intercept clicks or panning. Words + Cells together compose (word fills inside
cell outlines).

- [ ] **Step 3: Commit**

```bash
git add viewer/src/DocumentViewer.tsx
git commit -m "feat(viewer): role-colored cell-bounds overlay layer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Alt-gated normalized coordinate HUD

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/App.css`

- [ ] **Step 1: Add the HUD ref**

In `DocumentViewer.tsx`, alongside the other refs (e.g. after `const viewportRef = useRef<HTMLDivElement>(null)`,
~line 47), add:

```tsx
  const hudRef = useRef<HTMLDivElement>(null)
```

- [ ] **Step 2: Add the Alt keydown/keyup effect that attaches pointermove only while Alt is held**

Add this effect after the existing wheel-listener `useEffect` (the one ending ~line 194). It attaches the
`pointermove` listener **only while Alt is held**, writes coords straight to the HUD via the ref (no
React state → no re-render per move), and tears everything down on Alt release or window blur:

```tsx
  useEffect(() => {
    const viewport = viewportRef.current
    if (viewport == null) return

    const surfaceRect = () =>
      viewport.querySelector('.doc-surface')?.getBoundingClientRect()

    const handlePointerMove = (event: PointerEvent) => {
      const hud = hudRef.current
      const rect = surfaceRect()
      if (hud == null || rect == null || rect.width <= 0 || rect.height <= 0) return
      const nx = (event.clientX - rect.left) / rect.width
      const ny = (event.clientY - rect.top) / rect.height
      if (nx < 0 || nx > 1 || ny < 0 || ny > 1) {
        hud.classList.add('hidden')   // pointer off the page
        return
      }
      hud.classList.remove('hidden')
      hud.textContent = `${nx.toFixed(3)}, ${ny.toFixed(3)}`
    }

    const stopTracking = () => {
      viewport.removeEventListener('pointermove', handlePointerMove)
      hudRef.current?.classList.add('hidden')
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Alt') return
      viewport.addEventListener('pointermove', handlePointerMove)
    }
    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.key !== 'Alt') return
      stopTracking()
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    window.addEventListener('blur', stopTracking)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      window.removeEventListener('blur', stopTracking)
      stopTracking()
    }
  }, [])
```

- [ ] **Step 3: Render the HUD element inside the viewport**

In the JSX, inside `.doc-viewport` and as a **sibling of** `.doc-surface` (i.e. right after the
`.doc-surface` closing `</div>`, ~line 435, still inside the `.doc-viewport` div), add:

```tsx
        <div ref={hudRef} className="coord-hud hidden" aria-hidden="true" />
```

- [ ] **Step 4: Add the HUD styling**

In `App.css`, after the `.doc-overlay` rules (~line 362), add:

```css
.coord-hud {
  position: absolute;
  left: 8px;
  bottom: 8px;
  z-index: 6;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(20, 24, 28, 0.82);
  color: #f1f5f9;
  font: 0.78rem ui-monospace, SFMono-Regular, Menlo, monospace;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}

.coord-hud.hidden {
  display: none;
}
```

- [ ] **Step 5: Verify by running**

With the dev server running, reload the viewer.
Expected: holding **Alt** and moving over the page shows a dark badge in the bottom-left reading e.g.
`0.495, 0.225`, tracking the pointer. Near the top-left corner it reads ≈ `0.000, 0.000`; bottom-right ≈
`1.000, 1.000`. Moving off the page (or releasing Alt) hides the badge. Hovering **without** Alt shows no
badge. Zoom in/pan, then hold Alt — coords still correct relative to the page.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/DocumentViewer.tsx viewer/src/App.css
git commit -m "feat(viewer): Alt-gated normalized coordinate HUD

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Document the Alt gesture in the controls legend

**Files:**
- Modify: `viewer/src/ViewerHelp.tsx`

- [ ] **Step 1: Add the legend row**

In `ViewerHelp.tsx`, the `CONTROLS` array (lines 3–11) lists keyboard/mouse controls. Add a row for the
Alt gesture — insert before the closing `] as const`:

```tsx
  ['Alt + hover', 'Show normalized coords'],
```

- [ ] **Step 2: Verify by running**

With the dev server running, reload and click the `Controls` button in the toolbar.
Expected: the popover now includes a row `Alt + hover  Show normalized coords`.

- [ ] **Step 3: Build to catch type errors, then commit**

Run: `npm --prefix viewer run build`
Expected: build succeeds with no TypeScript errors.

```bash
git add viewer/src/ViewerHelp.tsx
git commit -m "docs(viewer): document Alt coord readout in controls legend

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification checklist (run after all tasks)

With `npm --prefix viewer run dev` and an `eob` dataset loaded, confirm the full spec:

1. Fresh load shows the **raw image only** — no overlays.
2. `Words`, `Cells`, `Tables` each toggle their layer independently; all combinations compose.
3. Cell outlines are role-colored, outline-only, and align with word groupings.
4. Word selection works with `Words` on; toggling `Words` off clears the highlight.
5. Alt+hover shows the normalized-coord badge tracking the pointer; release hides it; corners read
   ≈ `0,0` / `1,1`; coords stay correct after zoom/pan.
6. Hovering without Alt does nothing (no badge).
7. `npm --prefix viewer run build` passes.
