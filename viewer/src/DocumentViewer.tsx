import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Sample, Token } from './types'
import { predictionMatchStatus } from './tokenMatch'

const COLOR_CORRECT  = { fill: 'rgba(29,158,117,0.18)',  stroke: '#1D9E75' }
const COLOR_WRONG    = { fill: 'rgba(226,75,74,0.18)',   stroke: '#E24B4A' }
const COLOR_GT       = { fill: 'rgba(55,138,221,0.10)',  stroke: '#378ADD' }
const COLOR_SELECTED = { fill: 'rgba(255,180,0,0.28)',   stroke: '#F59E0B' }

function tokenColors(tok: Token, task: string | undefined, selected: boolean) {
  if (selected) return COLOR_SELECTED
  if (tok.pred == null) return COLOR_GT
  const status = predictionMatchStatus(task, tok.label, tok.pred)
  if (status === 'correct') return COLOR_CORRECT
  if (status === 'mismatch') return COLOR_WRONG
  return COLOR_GT
}

interface Props {
  samples: Sample[]
  task?: string
  selectedToken: Token | null
  onSelectToken: (tok: Token | null) => void
}

export default function DocumentViewer({ samples, task, selectedToken, onSelectToken }: Props) {
  const [sampleIdx, setSampleIdx] = useState(0)
  const [imgError, setImgError] = useState(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })

  const sample = samples[Math.min(sampleIdx, samples.length - 1)]
  const width = sample?.width ?? 0
  const height = sample?.height ?? 0

  const resetView = useCallback(() => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }, [])

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

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setImgError(false)
      resetView()
    })
    return () => cancelAnimationFrame(frame)
  }, [sample?.id, sample?.image, resetView])

  if (sample == null) {
    return <p className="empty-note">No samples to display.</p>
  }

  const { tokens, image } = sample

  const statuses = tokens.map(token => predictionMatchStatus(task, token.label, token.pred))
  const hasGT = tokens.some(token => token.pred == null)
  const hasCorrect = statuses.includes('correct')
  const hasMismatch = statuses.includes('mismatch')
  const hasNotEvaluatedPreds = tokens.some((token, index) =>
    token.pred != null && statuses[index] === 'not-applicable')

  const showImage = image && !imgError

  return (
    <div className="doc-viewer">
      {/* Navigation */}
      <div className="sample-nav">
        <button
          onClick={() => { setSampleIdx(i => Math.max(0, i - 1)); onSelectToken(null) }}
          disabled={sampleIdx === 0}
        >
          ← Prev
        </button>
        <span className="sample-label">
          Sample {sampleIdx + 1} / {samples.length}
          &nbsp;(id&nbsp;{sample.id})
        </span>
        <button
          onClick={() => { setSampleIdx(i => Math.min(samples.length - 1, i + 1)); onSelectToken(null) }}
          disabled={sampleIdx === samples.length - 1}
        >
          Next →
        </button>
      </div>

      {/* Document viewport: image + SVG share one fitted surface */}
      <div className="doc-viewport" ref={viewportRef} onDoubleClick={resetView}>
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
            {tokens.map((tok, i) => {
              const sel = tok === selectedToken
              const { fill, stroke } = tokenColors(tok, task, sel)
              const x = tok.x0 * width
              const y = tok.y0 * height
              const w = (tok.x1 - tok.x0) * width
              const h = (tok.y1 - tok.y0) * height

              return (
                <g key={i} style={{ cursor: 'pointer' }} onClick={() => onSelectToken(sel ? null : tok)}>
                  <rect
                    x={x} y={y} width={w} height={h}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={sel ? 2.5 : 1.5}
                    rx={3}
                  />
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      {/* Legend */}
      <div className="legend">
        {(hasGT || hasNotEvaluatedPreds) && (
          <span className="legend-item">
            <span className="legend-swatch swatch-gt" />
            {hasNotEvaluatedPreds ? 'ground truth / not evaluated' : 'ground truth'}
          </span>
        )}
        {hasCorrect && (
          <span className="legend-item">
            <span className="legend-swatch swatch-correct" /> correct
          </span>
        )}
        {hasMismatch && (
          <span className="legend-item">
            <span className="legend-swatch swatch-wrong" /> mismatch
          </span>
        )}
        <span className="legend-item">
          <span className="legend-swatch swatch-selected" /> selected
        </span>
      </div>
    </div>
  )
}
