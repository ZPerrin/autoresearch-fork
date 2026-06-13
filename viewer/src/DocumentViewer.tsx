import { useState } from 'react'
import type { Sample, Token } from './types'

const COLOR_CORRECT  = { fill: 'rgba(29,158,117,0.18)',  stroke: '#1D9E75' }
const COLOR_WRONG    = { fill: 'rgba(226,75,74,0.18)',   stroke: '#E24B4A' }
const COLOR_GT       = { fill: 'rgba(55,138,221,0.10)',  stroke: '#378ADD' }
const COLOR_SELECTED = { fill: 'rgba(255,180,0,0.28)',   stroke: '#F59E0B' }

function isCorrect(tok: Token): boolean {
  const l = tok.label
  const p = tok.pred
  if (p == null || l == null) return false
  return p.record === l.record && p.field === l.field
}

function tokenColors(tok: Token, selected: boolean) {
  if (selected) return COLOR_SELECTED
  if (tok.pred == null) return COLOR_GT
  return isCorrect(tok) ? COLOR_CORRECT : COLOR_WRONG
}

interface Props {
  samples: Sample[]
  task?: string
  selectedToken: Token | null
  onSelectToken: (tok: Token | null) => void
}

export default function DocumentViewer({ samples, selectedToken, onSelectToken }: Props) {
  const [sampleIdx, setSampleIdx] = useState(0)
  const [imgError, setImgError] = useState(false)

  if (samples.length === 0) {
    return <p className="empty-note">No samples to display.</p>
  }

  const sample = samples[Math.min(sampleIdx, samples.length - 1)]
  const { width, height, tokens, image } = sample

  const hasGT    = tokens.some(t => t.pred == null)
  const hasPreds = tokens.some(t => t.pred != null)

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

      {/* Document canvas: image + SVG overlay */}
      <div className="doc-canvas-wrapper">
        <div
          className="doc-canvas"
          style={{ aspectRatio: `${width} / ${height}` }}
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
              const { fill, stroke } = tokenColors(tok, sel)
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
                  {/* Ground-truth label text */}
                  {tok.pred == null && tok.label != null && (
                    <text
                      x={x + w / 2}
                      y={y + h / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={Math.max(8, Math.min(h * 0.55, 14))}
                      fill={sel ? '#B45309' : '#378ADD'}
                      fontFamily="monospace"
                      pointerEvents="none"
                    >
                      {`${tok.label.record}·${tok.label.field}`}
                    </text>
                  )}
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      {/* Legend */}
      <div className="legend">
        {hasGT && (
          <span className="legend-item">
            <span className="legend-swatch swatch-gt" /> ground truth
          </span>
        )}
        {hasPreds && (
          <>
            <span className="legend-item">
              <span className="legend-swatch swatch-correct" /> correct
            </span>
            <span className="legend-item">
              <span className="legend-swatch swatch-wrong" /> mismatch
            </span>
          </>
        )}
        <span className="legend-item">
          <span className="legend-swatch swatch-selected" /> selected
        </span>
      </div>
    </div>
  )
}
