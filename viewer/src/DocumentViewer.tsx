import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Sample, Selection } from './types'
import ViewerHelp from './ViewerHelp'

const MIN_ZOOM = 0.25
const MAX_ZOOM = 4
const ZOOM_STEP = 1.2
const PAN_DRAG_THRESHOLD = 4
const PAN_VISIBLE_MARGIN = 48

// One mode is shown at a time (mutually exclusive lenses), so colors are a small
// reused tier set rather than a unique hue per role: within a mode the first
// category is primary, the next alt, the next tertiary.
const TIER = { primary: '#16A34A', alt: '#2563EB', tertiary: '#9333EA' } as const
const COLOR_SELECTED = '#FF1493'   // neon pink — bespoke selected-word indication

type ViewMode = 'none' | 'words' | 'composed' | 'cells' | 'keyvalue' | 'regions'

const MODES: [ViewMode, string][] = [
  ['none', 'Off'],
  ['words', 'Words'],
  ['composed', 'Composed'],
  ['cells', 'Cells'],
  ['keyvalue', 'Key/Val'],
  ['regions', 'Regions'],
]

// Per-mode legend, also the source of truth for which roles a mode draws.
const LEGEND: Record<ViewMode, [string, string][]> = {
  none: [],
  words: [['word', TIER.primary]],
  composed: [['header', TIER.primary], ['section', TIER.alt], ['summary', TIER.tertiary]],
  cells: [['cell', TIER.primary]],
  keyvalue: [['key', TIER.primary], ['value', TIER.alt]],
  regions: [['region', TIER.primary]],
}

// Tier color for a cell's role in the "composed" lens, or null if not shown there.
function composedColor(role: string): string | null {
  if (role === 'header' || role === 'group_header') return TIER.primary
  if (role === 'section') return TIER.alt
  if (role === 'summary') return TIER.tertiary
  return null
}

// Tier color for a cell's role in the "key/value" lens, or null if not shown there.
function keyValueColor(role: string): string | null {
  if (role === 'key') return TIER.primary
  if (role === 'value') return TIER.alt
  return null
}

// A single thin overlay box from a normalized [x0,y0,x1,y1] bbox. Interactive
// boxes capture clicks via the `ov-hit` class; `fillTint` adds the pink wash used
// for a selected word.
function OverlayBox({ bbox, pw, ph, color, width, dashed = false, fillTint = false, onClick }: {
  bbox: [number, number, number, number]; pw: number; ph: number;
  color: string; width: number; dashed?: boolean; fillTint?: boolean; onClick?: () => void
}) {
  return (
    <rect
      x={bbox[0] * pw}
      y={bbox[1] * ph}
      width={(bbox[2] - bbox[0]) * pw}
      height={(bbox[3] - bbox[1]) * ph}
      fill={fillTint ? 'rgba(255,20,147,0.14)' : 'none'}
      stroke={color}
      strokeWidth={width}
      strokeDasharray={dashed ? '8 6' : undefined}
      rx={2}
      className={onClick ? 'ov-hit' : undefined}
      onClick={onClick}
    />
  )
}

function sameSelection(a: Selection | null, b: Selection | null): boolean {
  return a != null && b != null && a.kind === b.kind && a.index === b.index
}

function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom))
}

function distanceSquared(x: number, y: number): number {
  return x * x + y * y
}

interface Props {
  samples: Sample[]
  task?: string
  selection: Selection | null
  onSelect: (selection: Selection | null) => void
  onSampleChange?: (idx: number) => void
}

export default function DocumentViewer({ samples, task: _task, selection, onSelect, onSampleChange }: Props) {
  const [sampleIdx, setSampleIdx] = useState(0)
  const [imgError, setImgError] = useState(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const hudRef = useRef<HTMLDivElement>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [mode, setMode] = useState<ViewMode>('none')
  const zoomRef = useRef(1)
  const panRef = useRef({ x: 0, y: 0 })
  const dragRef = useRef<{
    pointerId: number
    startX: number
    startY: number
    startPan: { x: number; y: number }
    dragging: boolean
  } | null>(null)
  const suppressClickRef = useRef(false)

  const sample = samples[Math.min(sampleIdx, samples.length - 1)]
  const width = sample?.width ?? 0
  const height = sample?.height ?? 0

  const resetView = useCallback(() => {
    zoomRef.current = 1
    panRef.current = { x: 0, y: 0 }
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }, [])

  const constrainPan = useCallback((requestedPan: { x: number; y: number }, requestedZoom = zoomRef.current) => {
    const viewport = viewportRef.current
    if (viewport == null || width <= 0 || height <= 0) return requestedPan

    const scaledWidth = width * fitScale * requestedZoom
    const scaledHeight = height * fitScale * requestedZoom
    const viewportWidth = viewport.clientWidth
    const viewportHeight = viewport.clientHeight

    const constrainAxis = (panValue: number, viewportSize: number, scaledSize: number) => {
      if (viewportSize <= 0 || scaledSize <= 0 || scaledSize <= viewportSize) return 0
      const maxPan = Math.max(0, (viewportSize + scaledSize) / 2 - PAN_VISIBLE_MARGIN)
      return Math.min(maxPan, Math.max(-maxPan, panValue))
    }

    return {
      x: constrainAxis(requestedPan.x, viewportWidth, scaledWidth),
      y: constrainAxis(requestedPan.y, viewportHeight, scaledHeight),
    }
  }, [fitScale, height, width])

  const applyPan = useCallback((nextPan: { x: number; y: number }) => {
    panRef.current = nextPan
    setPan(nextPan)
  }, [])

  const setZoomAround = useCallback((
    requestedZoom: number,
    clientPoint?: { x: number; y: number },
  ) => {
    const viewport = viewportRef.current
    if (viewport == null) return

    const currentZoom = zoomRef.current
    const nextZoom = clampZoom(requestedZoom)
    if (nextZoom === currentZoom) return

    const rect = viewport.getBoundingClientRect()
    const viewportCenter = {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    }
    const point = clientPoint ?? viewportCenter
    const currentPan = panRef.current
    const ratio = nextZoom / currentZoom
    const nextPan = {
      x: currentPan.x + (point.x - viewportCenter.x - currentPan.x) * (1 - ratio),
      y: currentPan.y + (point.y - viewportCenter.y - currentPan.y) * (1 - ratio),
    }
    const constrainedPan = constrainPan(nextPan, nextZoom)

    zoomRef.current = nextZoom
    panRef.current = constrainedPan
    setZoom(nextZoom)
    setPan(constrainedPan)
  }, [constrainPan])

  const previousSample = useCallback(() => {
    setSampleIdx(index => {
      const next = Math.max(0, index - 1)
      onSampleChange?.(next)
      return next
    })
    onSelect(null)
  }, [onSelect, onSampleChange])

  const nextSample = useCallback(() => {
    setSampleIdx(index => {
      const next = Math.min(samples.length - 1, index + 1)
      onSampleChange?.(next)
      return next
    })
    onSelect(null)
  }, [onSelect, onSampleChange, samples.length])

  useLayoutEffect(() => {
    const viewport = viewportRef.current
    if (viewport == null || width <= 0 || height <= 0) return

    const updateFitScale = () => {
      const availableWidth = viewport.clientWidth
      const availableHeight = viewport.clientHeight
      if (availableWidth <= 0 || availableHeight <= 0) return
      setFitScale(Math.min(availableWidth / width, availableHeight / height))
    }

    updateFitScale()
    const observer = new ResizeObserver(updateFitScale)
    observer.observe(viewport)
    return () => observer.disconnect()
  }, [width, height])

  useLayoutEffect(() => {
    const constrainedPan = constrainPan(panRef.current)
    if (constrainedPan.x === panRef.current.x && constrainedPan.y === panRef.current.y) return
    applyPan(constrainedPan)
  }, [applyPan, constrainPan, fitScale])

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setImgError(false)
      resetView()
    })
    return () => cancelAnimationFrame(frame)
  }, [sample?.id, sample?.image, resetView])

  useEffect(() => {
    const viewport = viewportRef.current
    if (viewport == null) return

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      setZoomAround(
        zoomRef.current * Math.exp(-event.deltaY * 0.0015),
        { x: event.clientX, y: event.clientY },
      )
    }

    viewport.addEventListener('wheel', handleWheel, { passive: false })
    return () => viewport.removeEventListener('wheel', handleWheel)
  }, [setZoomAround])

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

  const handlePointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || !event.isPrimary) return

    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPan: panRef.current,
      dragging: false,
    }
  }, [])

  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current
    if (drag == null || drag.pointerId !== event.pointerId) return

    const dx = event.clientX - drag.startX
    const dy = event.clientY - drag.startY
    if (!drag.dragging) {
      if (distanceSquared(dx, dy) < PAN_DRAG_THRESHOLD * PAN_DRAG_THRESHOLD) return
      drag.dragging = true
      suppressClickRef.current = true
      setIsPanning(true)
      event.currentTarget.setPointerCapture(event.pointerId)
    }

    applyPan({
      x: drag.startPan.x + dx,
      y: drag.startPan.y + dy,
    })
  }, [applyPan])

  const finishPointerDrag = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current
    if (drag == null || drag.pointerId !== event.pointerId) return

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    dragRef.current = null
    setIsPanning(false)

    if (drag.dragging) {
      applyPan(constrainPan(panRef.current))
      window.setTimeout(() => {
        suppressClickRef.current = false
      }, 0)
    }
  }, [applyPan, constrainPan])

  const handlePointerCancel = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    finishPointerDrag(event)
  }, [finishPointerDrag])

  const changeMode = useCallback((next: ViewMode) => {
    setMode(next)
    onSelect(null)   // a selection from one lens doesn't carry to another
  }, [onSelect])

  // Click anything to select it. Re-clicking the same word clears it; cells/regions
  // (which a click may reach via any member word) just stay selected — clear them by
  // switching mode. A drag (pan) sets suppressClickRef so the trailing click is ignored.
  const handleSelect = useCallback((next: Selection) => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false
      return
    }
    const toggleOff = next.kind === 'word' && sameSelection(selection, next)
    onSelect(toggleOff ? null : next)
  }, [onSelect, selection])

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement
    if (['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)) return

    switch (event.key) {
      case '+':
      case '=':
        event.preventDefault()
        setZoomAround(zoomRef.current * ZOOM_STEP)
        break
      case '-':
        event.preventDefault()
        setZoomAround(zoomRef.current / ZOOM_STEP)
        break
      case '0':
        event.preventDefault()
        resetView()
        break
      case '[':
      case 'ArrowLeft':
        event.preventDefault()
        previousSample()
        break
      case ']':
      case 'ArrowRight':
        event.preventDefault()
        nextSample()
        break
    }
  }, [nextSample, previousSample, resetView, setZoomAround])

  if (sample == null) {
    return <p className="empty-note">No samples to display.</p>
  }

  const { words, cells, image } = sample
  const regions = sample.regions ?? []
  const allCells = cells ?? []

  const showImage = image && !imgError

  return (
    <div className="doc-viewer" tabIndex={0} aria-label="Document viewer" onKeyDown={handleKeyDown}>
      <div className="viewer-toolbar">
        <div className="sample-nav">
          <button
            onClick={previousSample}
            disabled={sampleIdx === 0}
          >
            ← Prev
          </button>
          <span className="sample-label">
            Sample {sampleIdx + 1} / {samples.length}
            &nbsp;(id&nbsp;{sample.id})
          </span>
          <button
            onClick={nextSample}
            disabled={sampleIdx === samples.length - 1}
          >
            Next →
          </button>
        </div>
        <div className="overlay-toggles" role="radiogroup" aria-label="Overlay view mode">
          {MODES.map(([m, label]) => (
            <button
              key={m}
              className={mode === m ? 'is-active' : ''}
              role="radio"
              aria-checked={mode === m}
              onClick={() => changeMode(m)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="zoom-controls" aria-label="Document zoom controls">
          <button
            onClick={() => setZoomAround(zoomRef.current / ZOOM_STEP)}
            disabled={zoom <= MIN_ZOOM}
            aria-label="Zoom out"
          >
            -
          </button>
          <button className="zoom-percentage" onClick={resetView} title="Reset to fit">
            {Math.round(zoom * 100)}%
          </button>
          <button
            onClick={() => setZoomAround(zoomRef.current * ZOOM_STEP)}
            disabled={zoom >= MAX_ZOOM}
            aria-label="Zoom in"
          >
            +
          </button>
          <button className="fit-button" onClick={resetView}>Fit</button>
        </div>
        <ViewerHelp />
      </div>

      {/* Document viewport: image + SVG share one fitted surface */}
      <div
        className={`doc-viewport${isPanning ? ' is-panning' : ''}`}
        ref={viewportRef}
        onDoubleClick={resetView}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishPointerDrag}
        onPointerCancel={handlePointerCancel}
      >
        <div
          className="doc-surface"
          style={{
            width,
            height,
            transform: `translate(-50%, -50%) translate(${pan.x}px, ${pan.y}px) scale(${fitScale * zoom})`,
          }}
        >
          {showImage ? (
            <img
              src={image}
              alt={`Sample ${sample.id}`}
              className="doc-image"
              draggable={false}
              onDragStart={event => event.preventDefault()}
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="doc-image-placeholder" />
          )}

          <svg
            className="doc-overlay"
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="xMidYMid meet"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Regions lens — region container outlines (cell-outline style). */}
            {mode === 'regions' && regions.map((rg, i) => {
              const sel = selection?.kind === 'region' && selection.index === i
              return (
                <OverlayBox key={`region-${i}`} bbox={rg.bbox} pw={width} ph={height}
                  color={sel ? COLOR_SELECTED : TIER.primary} width={sel ? 2 : 1.5}
                  dashed onClick={() => handleSelect({ kind: 'region', index: i })} />
              )
            })}
            {/* Cells lens — the only lens that draws full cell outlines. */}
            {mode === 'cells' && allCells.map((cell, i) => {
              const sel = selection?.kind === 'cell' && selection.index === i
              return (
                <OverlayBox key={`cell-${i}`} bbox={cell.bbox} pw={width} ph={height}
                  color={sel ? COLOR_SELECTED : TIER.primary} width={sel ? 2 : 1.25}
                  onClick={() => handleSelect({ kind: 'cell', index: i })} />
              )
            })}
            {/* Composed lens — header/section/summary drawn as their member word
                boxes (tight, word-level), tier-colored; click selects the cell. */}
            {mode === 'composed' && allCells.map((cell, ci) => {
              const color = composedColor(cell.role)
              if (color == null) return null
              const sel = selection?.kind === 'cell' && selection.index === ci
              return cell.word_ids.map(wid => {
                const w = words[wid]
                return w == null ? null : (
                  <OverlayBox key={`composed-${ci}-${wid}`}
                    bbox={[w.x0, w.y0, w.x1, w.y1]} pw={width} ph={height}
                    color={sel ? COLOR_SELECTED : color} width={sel ? 2 : 1.25}
                    onClick={() => handleSelect({ kind: 'cell', index: ci })} />
                )
              })
            })}
            {/* Key/Value lens — key & value drawn as their member word boxes. */}
            {mode === 'keyvalue' && allCells.map((cell, ci) => {
              const color = keyValueColor(cell.role)
              if (color == null) return null
              const sel = selection?.kind === 'cell' && selection.index === ci
              return cell.word_ids.map(wid => {
                const w = words[wid]
                return w == null ? null : (
                  <OverlayBox key={`kv-${ci}-${wid}`}
                    bbox={[w.x0, w.y0, w.x1, w.y1]} pw={width} ph={height}
                    color={sel ? COLOR_SELECTED : color} width={sel ? 2 : 1.25}
                    onClick={() => handleSelect({ kind: 'cell', index: ci })} />
                )
              })
            })}
            {/* Words lens — every word; selected gets the pink fill. */}
            {mode === 'words' && words.map((word, i) => {
              const sel = selection?.kind === 'word' && selection.index === i
              return (
                <OverlayBox
                  key={i}
                  bbox={[word.x0, word.y0, word.x1, word.y1]}
                  pw={width} ph={height}
                  color={sel ? COLOR_SELECTED : TIER.primary}
                  width={sel ? 2 : 1}
                  fillTint={sel}
                  onClick={() => handleSelect({ kind: 'word', index: i })}
                />
              )
            })}
          </svg>
        </div>
        <div ref={hudRef} className="coord-hud hidden" aria-hidden="true" />
      </div>

      {/* Legend — swaps with the active view mode (LEGEND map above) */}
      <div className="legend">
        {mode === 'none' ? (
          <span className="legend-hint">Pick a view mode to overlay structure.</span>
        ) : (
          [...LEGEND[mode], ['selected', COLOR_SELECTED] as [string, string]].map(([label, color]) => (
            <span className="legend-item" key={label}>
              <span className="legend-swatch" style={{ background: color, borderColor: 'rgba(10,14,22,0.55)' }} /> {label}
            </span>
          ))
        )}
      </div>
    </div>
  )
}
