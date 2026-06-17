import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Cell, Sample } from './types'
import ViewerHelp from './ViewerHelp'

const COLOR_SELECTED = { fill: 'rgba(255,180,0,0.28)',   stroke: '#F59E0B' }
const MIN_ZOOM = 0.25
const MAX_ZOOM = 4
const ZOOM_STEP = 1.2
const PAN_DRAG_THRESHOLD = 4
const PAN_VISIBLE_MARGIN = 48

const ROLE_COLOR: Record<string, { fill: string; stroke: string }> = {
  data:         { fill: 'rgba(55,138,221,0.10)',  stroke: '#378ADD' },
  header:       { fill: 'rgba(124,92,196,0.16)',  stroke: '#7C5CC4' },
  group_header: { fill: 'rgba(124,92,196,0.22)',  stroke: '#5B3FA0' },
  section:      { fill: 'rgba(217,119,6,0.16)',   stroke: '#D97706' },
  summary:      { fill: 'rgba(29,158,117,0.16)',  stroke: '#1D9E75' },
  key:          { fill: 'rgba(100,116,139,0.14)', stroke: '#64748B' },
  value:        { fill: 'rgba(55,138,221,0.10)',  stroke: '#378ADD' },
}
const COLOR_BACKGROUND = { fill: 'rgba(148,163,184,0.08)', stroke: '#94A3B8' }

function tokenColors(role: string | undefined, selected: boolean) {
  if (selected) return COLOR_SELECTED
  return role ? (ROLE_COLOR[role] ?? COLOR_BACKGROUND) : COLOR_BACKGROUND
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
  selectedTokenIdx: number | null
  onSelectToken: (idx: number | null) => void
  onSampleChange?: (idx: number) => void
}

export default function DocumentViewer({ samples, task: _task, selectedTokenIdx, onSelectToken, onSampleChange }: Props) {
  const [sampleIdx, setSampleIdx] = useState(0)
  const [imgError, setImgError] = useState(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
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
    onSelectToken(null)
  }, [onSelectToken, onSampleChange])

  const nextSample = useCallback(() => {
    setSampleIdx(index => {
      const next = Math.min(samples.length - 1, index + 1)
      onSampleChange?.(next)
      return next
    })
    onSelectToken(null)
  }, [onSelectToken, onSampleChange, samples.length])

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

  const handleTokenClick = useCallback((idx: number, selected: boolean) => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false
      return
    }
    onSelectToken(selected ? null : idx)
  }, [onSelectToken])

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

  const { tokens, cells, image } = sample
  const regions = sample.regions ?? []

  // Build token → owning cell map
  const cellByToken = new Map<number, Cell>()
  for (const cell of (cells ?? [])) {
    for (const tokenId of cell.token_ids) {
      cellByToken.set(tokenId, cell)
    }
  }

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
            {regions.map((rg, i) => (
              <g key={`region-${i}`}>
                <rect
                  x={rg.bbox[0] * width}
                  y={rg.bbox[1] * height}
                  width={(rg.bbox[2] - rg.bbox[0]) * width}
                  height={(rg.bbox[3] - rg.bbox[1]) * height}
                  fill="none"
                  stroke="#9333EA"
                  strokeWidth={2}
                  strokeDasharray="8 6"
                  rx={4}
                  pointerEvents="none"
                />
                <text
                  x={rg.bbox[0] * width + 4}
                  y={rg.bbox[1] * height - 3}
                  fontSize={10}
                  fill="#9333EA"
                  pointerEvents="none"
                >
                  {`${rg.type}:${rg.name ?? ''}#${rg.index}`}
                </text>
              </g>
            ))}
            {tokens.map((tok, i) => {
              const sel = i === selectedTokenIdx
              const role = cellByToken.get(i)?.role
              const { fill, stroke } = tokenColors(role, sel)
              const x = tok.x0 * width
              const y = tok.y0 * height
              const w = (tok.x1 - tok.x0) * width
              const h = (tok.y1 - tok.y0) * height

              return (
                <g key={i}>
                  <rect
                    x={x} y={y} width={w} height={h}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={sel ? 2.5 : 1.5}
                    rx={3}
                    onClick={() => handleTokenClick(i, sel)}
                  />
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      {/* Legend — derived from ROLE_COLOR + COLOR_BACKGROUND constants above */}
      <div className="legend">
        {([
          ['data',         ROLE_COLOR.data],
          ['header',       ROLE_COLOR.header],
          ['group header', ROLE_COLOR.group_header],
          ['section',      ROLE_COLOR.section],
          ['summary',      ROLE_COLOR.summary],
          ['key / value',  ROLE_COLOR.key],
          ['background',   COLOR_BACKGROUND],
        ] as [string, { fill: string; stroke: string }][]).map(([label, c]) => (
          <span className="legend-item" key={label}>
            <span className="legend-swatch" style={{ background: c.fill, border: `1.5px solid ${c.stroke}` }} /> {label}
          </span>
        ))}
        <span className="legend-item">
          <span className="legend-swatch swatch-selected" /> selected
        </span>
      </div>
    </div>
  )
}
