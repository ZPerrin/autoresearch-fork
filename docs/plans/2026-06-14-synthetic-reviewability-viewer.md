# Synthetic Reviewability: Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the complete document easy to review with aligned zoom/pan, discoverable controls, and metadata that understands the resolved synthetic-document structure.

**Architecture:** Keep image and SVG overlay in one transformed document surface inside a clipped viewport. `DocumentViewer` owns navigation and interaction state; a focused `ViewerHelp` component owns the controls popover. Manifest types and `MetaPanel` become schema-aware without coupling rendering to one task label shape.

**Tech Stack:** React 19, TypeScript 6, SVG, CSS transforms, Vite, in-app Browser verification.

**Repo convention:** There is no frontend test framework. Run Tasks 1-5 from `viewer/` and verify
each focused change with `npm run build`, `npm run lint`, and targeted browser interaction. Preserve
and incorporate the existing uncommitted `DocumentViewer.tsx` and `MetaPanel.tsx` edits; do not
revert them.

---

## File structure

| File | Change |
|---|---|
| `viewer/src/types.ts` | Type resolved `manifest.config.spec` and generalized labels. |
| `viewer/src/MetaPanel.tsx` | Present document structure and arbitrary label/prediction keys. |
| `viewer/src/ViewerHelp.tsx` | New IDE-style controls popover. |
| `viewer/src/DocumentViewer.tsx` | Fit-page viewport, zoom, pan, reset, shortcuts, and toolbar. |
| `viewer/src/App.css` | Viewport, canvas, controls, help, and interaction styling. |

---

### Task 1: Resolved manifest and generalized token metadata

**Files:**
- Modify: `viewer/src/types.ts`
- Modify: `viewer/src/MetaPanel.tsx`

- [ ] **Step 1: Add resolved synthetic-spec types**

Add above `DatasetManifest`:

```typescript
export type LabelValue = string | number | boolean | null
export type TokenLabel = Record<string, LabelValue>

export interface FieldSpec {
  name: string
  type: string
  align: string
}

export interface TableSpec {
  name: string
  fields: FieldSpec[]
  rows: [number, number]
  instances: [number, number]
}

export interface ResolvedDocumentSpec {
  name: string
  tables: TableSpec[]
  globals: FieldSpec[]
  background_terms?: string[]
  layout: {
    page: [number, number]
    margin: [number, number]
    row_h: number
    pad: number
    table_gap: number
  }
  structure: {
    multi_token: boolean
    header: boolean
    background: number
    [key: string]: LabelValue
  }
  render: Record<string, unknown>
}
```

Change `Token.label` and `Token.pred` to:

```typescript
label: TokenLabel | null
pred: (TokenLabel & { confidence?: number }) | null
```

Add `spec?: ResolvedDocumentSpec` and `class?: string` under `DatasetManifest.config`. Retain legacy
optional fields for old datasets.

- [ ] **Step 2: Add stable value formatting helpers**

In `MetaPanel.tsx`, add:

```typescript
function formatRange(range: [number, number]): string {
  return range[0] === range[1] ? String(range[0]) : `${range[0]}-${range[1]}`
}

function formatValue(value: unknown): string {
  if (value == null) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (Array.isArray(value)) return value.join(' x ')
  return String(value)
}

function entries(value: Record<string, unknown> | null) {
  return value ? Object.entries(value) : []
}
```

- [ ] **Step 3: Replace legacy dataset metadata with resolved structure**

Inside the dataset section, retain id/task/count/modalities, then render `manifest.config.spec` when
present:

```tsx
{source.manifest.config.spec && (
  <>
    <div className="meta-row">
      <span className="meta-key">class</span>
      <span className="meta-val mono">{source.manifest.config.spec.name}</span>
    </div>
    <div className="meta-row">
      <span className="meta-key">page</span>
      <span className="meta-val mono">
        {source.manifest.config.spec.layout.page.join(' x ')}
      </span>
    </div>
    <div className="meta-row">
      <span className="meta-key">globals</span>
      <span className="meta-val mono">
        {source.manifest.config.spec.globals.map(f => f.name).join(', ') || '-'}
      </span>
    </div>
    {source.manifest.config.spec.tables.map(table => (
      <div className="structure-card" key={table.name}>
        <div className="structure-title">{table.name}</div>
        <div className="structure-detail mono">
          rows {formatRange(table.rows)} · instances {formatRange(table.instances)}
        </div>
        <div className="structure-fields">{table.fields.map(f => f.name).join(', ')}</div>
      </div>
    ))}
    <div className="meta-row">
      <span className="meta-key">structure</span>
      <span className="meta-val mono">
        {Object.entries(source.manifest.config.spec.structure)
          .filter(([, value]) => Boolean(value))
          .map(([key, value]) => `${key}=${formatValue(value)}`)
          .join(', ') || 'default'}
      </span>
    </div>
  </>
)}
```

Keep the legacy `config.fields` row as a fallback only when `spec` is absent.

- [ ] **Step 4: Render arbitrary token label keys**

Keep the in-flight `label = ground truth/null` summary, but replace the hard-coded record/field rows
with:

```tsx
{selectedToken.label != null && entries(selectedToken.label).map(([key, value]) => (
  <div className="meta-row" key={`label-${key}`}>
    <span className="meta-key">{key}</span>
    <span className="meta-val mono">{formatValue(value)}</span>
  </div>
))}
```

Change the null summary to `background / non-answer`. Render prediction entries in the same generic
fashion, excluding `confidence` from the repeated rows because it retains its dedicated formatted
row. Keep the existing `grid_record_field` match comparison for now.

- [ ] **Step 5: Add structure-card CSS**

Add compact card styles in `App.css`:

```css
.structure-card {
  margin: 6px 0;
  padding: 7px 8px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  background: #fafafa;
}

.structure-title { font-size: 0.8rem; font-weight: 650; }
.structure-detail { margin-top: 2px; color: #666; font-size: 0.74rem; }
.structure-fields { margin-top: 3px; color: #444; font-size: 0.76rem; }
```

- [ ] **Step 6: Build, inspect, and commit**

Run:

```powershell
npm run build
npm run lint
```

Open `eob-full`, click a global value, header token, table token, and background token. Expected:

- globals/tables/ranges/features appear in dataset metadata;
- label detail includes whichever of `global`, `region`, `record`, `field`, `header`, and `seq`
  apply;
- background tokens are explicitly described as non-answer;
- no label text is painted over document text.

Commit the current in-flight overlay-removal work together with this metadata completion:

```powershell
git add src/types.ts src/MetaPanel.tsx src/DocumentViewer.tsx src/App.css
git commit -m "feat: show schema-aware viewer metadata"
```

---

### Task 2: Fit-page document viewport

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/App.css`

- [ ] **Step 1: Add viewport and document refs/state**

Update imports:

```typescript
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
```

Add inside `DocumentViewer`:

```typescript
const viewportRef = useRef<HTMLDivElement>(null)
const [fitScale, setFitScale] = useState(1)
const [zoom, setZoom] = useState(1)
const [pan, setPan] = useState({ x: 0, y: 0 })

const resetView = useCallback(() => {
  setZoom(1)
  setPan({ x: 0, y: 0 })
}, [])
```

`zoom` is relative to fit: `1` means Fit page, regardless of pane size.

- [ ] **Step 2: Measure fit scale with `ResizeObserver`**

Add:

```typescript
useLayoutEffect(() => {
  const viewport = viewportRef.current
  if (!viewport || !width || !height) return
  const update = () => {
    const { width: availableW, height: availableH } = viewport.getBoundingClientRect()
    setFitScale(Math.min(availableW / width, availableH / height))
  }
  update()
  const observer = new ResizeObserver(update)
  observer.observe(viewport)
  return () => observer.disconnect()
}, [width, height])

useEffect(() => resetView(), [sample.id, image, resetView])
```

- [ ] **Step 3: Replace the width-driven canvas with a centered transformed surface**

Change the wrapper to:

```tsx
<div className="doc-viewport" ref={viewportRef} onDoubleClick={resetView}>
  <div
    className="doc-surface"
    style={{
      width,
      height,
      transform: `translate(${pan.x}px, ${pan.y}px) scale(${fitScale * zoom})`,
    }}
  >
    {/* existing image and SVG overlay */}
  </div>
</div>
```

The image and SVG retain `width: 100%; height: 100%`; the SVG viewBox remains document pixels.

- [ ] **Step 4: Replace canvas CSS**

Use:

```css
.doc-canvas-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
}

.doc-viewport {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  background: #f6f6f6;
  touch-action: none;
}

.doc-surface {
  position: absolute;
  left: 50%;
  top: 50%;
  transform-origin: center center;
  background: white;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.12);
  will-change: transform;
}
```

Because the surface starts at viewport center, include `translate(-50%, -50%)` before pan in the
transform string:

```typescript
transform: `translate(-50%, -50%) translate(${pan.x}px, ${pan.y}px) scale(${fitScale * zoom})`
```

Remove the old `.doc-canvas`, its `max-height`, and `overflow: hidden` rules.

- [ ] **Step 5: Build and browser-check Fit mode**

Run `npm run build`, reload the viewer, and inspect samples 1, 6, 13, and 25 from legacy
`eob-full`. Expected: the entire 1000x1414 page is visible in the viewport, including blank page
space and any legacy boxes whose coordinates are within the page. Tokens with old `y1 > 1` remain
outside the source image by definition; the viewer does not fabricate page content for them.

- [ ] **Step 6: Commit**

```powershell
git add src/DocumentViewer.tsx src/App.css
git commit -m "feat: fit complete document pages in the viewer"
```

---

### Task 3: Cursor-centered wheel zoom and toolbar controls

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/App.css`

- [ ] **Step 1: Add zoom constants and clamping**

At module scope:

```typescript
const MIN_ZOOM = 0.25
const MAX_ZOOM = 4
const ZOOM_STEP = 1.2

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
```

Add:

```typescript
const setZoomAround = useCallback((nextZoom: number, point?: { x: number; y: number }) => {
  const viewport = viewportRef.current
  if (!viewport) return
  const bounded = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM)
  if (point) {
    const rect = viewport.getBoundingClientRect()
    const px = point.x - rect.left - rect.width / 2
    const py = point.y - rect.top - rect.height / 2
    const ratio = bounded / zoom
    setPan(current => ({
      x: px - (px - current.x) * ratio,
      y: py - (py - current.y) * ratio,
    }))
  }
  setZoom(bounded)
}, [zoom])
```

- [ ] **Step 2: Add non-passive wheel handling**

React wheel events can call `preventDefault`, but browser behavior is most reliable with an explicit
non-passive listener. Add an effect on `viewportRef.current` that:

```typescript
const onWheel = (event: WheelEvent) => {
  event.preventDefault()
  const factor = Math.exp(-event.deltaY * 0.0015)
  setZoomAround(zoom * factor, { x: event.clientX, y: event.clientY })
}
viewport.addEventListener('wheel', onWheel, { passive: false })
return () => viewport.removeEventListener('wheel', onWheel)
```

Ensure the effect dependencies keep the active `zoom` value without accumulating listeners.

- [ ] **Step 3: Add toolbar controls beside sample navigation**

Wrap navigation and controls in `.viewer-toolbar`. Add:

```tsx
<div className="zoom-controls" aria-label="Document zoom controls">
  <button type="button" onClick={() => setZoomAround(zoom / ZOOM_STEP)} aria-label="Zoom out">-</button>
  <button type="button" className="zoom-value" onClick={resetView} title="Reset to Fit">
    {Math.round(zoom * 100)}%
  </button>
  <button type="button" onClick={() => setZoomAround(zoom * ZOOM_STEP)} aria-label="Zoom in">+</button>
  <button type="button" onClick={resetView}>Fit</button>
</div>
```

Disable zoom buttons at their bounds.

- [ ] **Step 4: Style the toolbar compactly**

Add `.viewer-toolbar`, `.zoom-controls`, and `.zoom-value` rules. Reuse the existing sample-nav
button visual language; keep percentage width stable so the toolbar does not shift while zooming.

- [ ] **Step 5: Build and browser-check pointer centering**

Run `npm run build`. In the browser:

1. Place the pointer over a known token and wheel upward.
2. Confirm that token remains near the pointer while the page enlarges.
3. Use `-`, `+`, percentage reset, and `Fit`.
4. Confirm zoom never exceeds 25%-400% relative to Fit.

- [ ] **Step 6: Commit**

```powershell
git add src/DocumentViewer.tsx src/App.css
git commit -m "feat: add cursor-centered document zoom"
```

---

### Task 4: Drag pan without breaking token selection

**Files:**
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/App.css`

- [ ] **Step 1: Add drag refs and threshold**

Add:

```typescript
const dragRef = useRef<{
  pointerId: number
  startX: number
  startY: number
  panX: number
  panY: number
  moved: boolean
} | null>(null)
const suppressClickRef = useRef(false)
const DRAG_THRESHOLD = 4
```

- [ ] **Step 2: Add pointer handlers to the viewport**

Implement pointer down/move/up/cancel. On down, capture the pointer and record start state. On move,
mark `moved` after the threshold and update pan. On up, set `suppressClickRef.current` when moved,
release capture, and clear the drag ref.

Only start pan for the primary button. Permit panning at any zoom so a slightly displaced page can
be recentered, but use grab/grabbing cursors only when `zoom > 1` or pan is non-zero.

- [ ] **Step 3: Suppress token click after drag**

Change token selection to:

```tsx
onClick={(event) => {
  event.stopPropagation()
  if (suppressClickRef.current) {
    suppressClickRef.current = false
    return
  }
  onSelectToken(sel ? null : tok)
}}
```

A normal click still selects the token. A drag beginning over a token pans and does not select it.

- [ ] **Step 4: Constrain pan on pointer-up and zoom changes**

Add a `constrainPan` helper based on viewport size and scaled document size. Keep at least 48 pixels
of the document visible on each axis. If the scaled document is smaller than the viewport on an
axis, center it by forcing that pan coordinate to zero.

Apply constraints after drag, after zoom changes, and after viewport resize. Do not clamp every
pointer-move event; that makes edge dragging feel sticky.

- [ ] **Step 5: Build and browser-check selection versus pan**

Run `npm run build`. Verify:

- clicking a token selects it;
- dragging from the same token pans without selecting;
- the image and every bounding box remain aligned;
- the page cannot be dragged completely out of sight;
- double-click resets to Fit.

- [ ] **Step 6: Commit**

```powershell
git add src/DocumentViewer.tsx src/App.css
git commit -m "feat: add bounded drag pan to document review"
```

---

### Task 5: Hotkeys and IDE-style controls help

**Files:**
- Create: `viewer/src/ViewerHelp.tsx`
- Modify: `viewer/src/DocumentViewer.tsx`
- Modify: `viewer/src/App.css`

- [ ] **Step 1: Create the help popover component**

Create `ViewerHelp.tsx` with local open state, a button labeled `Controls`, and this data:

```typescript
const CONTROLS = [
  ['Wheel', 'Zoom at pointer'],
  ['Drag', 'Pan document'],
  ['Double-click / 0', 'Fit page'],
  ['+ / =', 'Zoom in'],
  ['-', 'Zoom out'],
  ['[ / Left', 'Previous sample'],
  ['] / Right', 'Next sample'],
] as const
```

Use a wrapper ref. While open, listen for `pointerdown` on `document` to close when the event target
is outside the wrapper, and `keydown` to close on `Escape`. Clean up both listeners.

Render semantic `<kbd>` elements for controls and a compact popover anchored below the button.

- [ ] **Step 2: Add keyboard handling scoped to the viewer**

Make `.doc-viewer` focusable with `tabIndex={0}` and an accessible label. Add `onKeyDown` that ignores
events originating from `INPUT`, `TEXTAREA`, `SELECT`, or `BUTTON` and maps:

```typescript
'+', '=' -> zoom in
'-' -> zoom out
'0' -> resetView
'[', 'ArrowLeft' -> previous sample
']', 'ArrowRight' -> next sample
```

Extract `previousSample` and `nextSample` callbacks so buttons and hotkeys share exactly the same
bounds and token-selection reset behavior.

- [ ] **Step 3: Place help in the toolbar**

Render `<ViewerHelp />` after zoom controls. Keep it visible without using scarce document viewport
space.

- [ ] **Step 4: Style popover and keyboard focus**

Add a clear `:focus-visible` ring to `.doc-viewer`, toolbar buttons, and the help trigger. Style the
popover with a modest shadow, 2-column rows, and `<kbd>` chips. Give it a high enough z-index to sit
above the document viewport and metadata divider.

- [ ] **Step 5: Build, lint, and browser-check controls**

Run:

```powershell
npm run build
npm run lint
```

Verify in browser:

- `Controls` opens the list;
- `Escape` and click-outside close it;
- every documented hotkey works after focusing the viewer;
- hotkeys do not fire while a toolbar button has focus;
- previous/next remain bounded.

- [ ] **Step 6: Commit**

```powershell
git add src/ViewerHelp.tsx src/DocumentViewer.tsx src/App.css
git commit -m "feat: add viewer hotkeys and controls help"
```

---

### Task 6: End-to-end browser review and milestone sync

**Files:**
- Modify: `docs/specs/2026-06-14-synthetic-reviewability-design.md`
- Modify: `docs/specs/2026-06-13-design-and-roadmap.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Run all automated checks**

From repo root:

```powershell
$env:UV_CACHE_DIR='harness\.uv-cache'
Push-Location harness
uv run pytest -q
Pop-Location
npm --prefix viewer run build
npm --prefix viewer run lint
git diff --check
```

Expected: harness suite passes, viewer build/lint pass, and no whitespace errors.

- [ ] **Step 2: Review legacy and corrected datasets in the browser**

Use the in-app browser at `http://127.0.0.1:5173/`.

Review at least:

- `eob-full` samples 1, 2, 6, 13, and 25 to confirm legacy overflow is inspectable and its generic
  background tokens are correctly identified as non-answer;
- `eob-reviewable` samples covering one, two, and the maximum feasible instance count;
- a header token, split multi-token value, global value, normal table token, and background token.

Exercise Fit, wheel zoom at pointer, +/- controls, drag pan from empty page and from a token,
double-click reset, hotkeys, help open/close, and source/sample reset.

- [ ] **Step 3: Sync milestone documentation**

Mark the synthetic reviewability design shipped. Update the roadmap and `AGENTS.md` so the next
structural-realism item is jitter/irregular row heights and column widths. Mention page-valid
composition and viewer zoom/pan among completed capabilities.

- [ ] **Step 4: Commit documentation**

```powershell
git add AGENTS.md docs/specs/2026-06-14-synthetic-reviewability-design.md docs/specs/2026-06-13-design-and-roadmap.md
git commit -m "docs: mark synthetic reviewability shipped"
```

- [ ] **Step 5: Record final state**

Run:

```powershell
git status --short --branch
git log -8 --oneline
```

Expected: no implementation files remain unstaged or uncommitted. Local datasets remain ignored.
