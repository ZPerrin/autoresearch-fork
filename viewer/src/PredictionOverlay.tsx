import { useState } from 'react'
import type { Sample, Token } from './types'

interface Props {
  task: string
  samples: Sample[]
}

// SVG canvas dimensions (px) — treat as a wide-ish page
const W = 700
const H = 980 // ~A4 aspect (1:1.414 → 700*1.414 ≈ 990)

const COLOR_CORRECT = { fill: 'rgba(29, 158, 117, 0.18)', stroke: '#1D9E75' }
const COLOR_WRONG   = { fill: 'rgba(226, 75,  74, 0.18)', stroke: '#E24B4A' }
const COLOR_GT      = { fill: 'rgba(55, 138, 221, 0.10)', stroke: '#378ADD' }

function isCorrect(task: string, token: Token): boolean {
  if (task === 'grid_record_field') {
    const l = token.label as { record?: unknown; field?: unknown }
    const p = token.pred  as { record?: unknown; field?: unknown }
    return p != null && l != null &&
      p.record === l.record &&
      p.field  === l.field
  }
  // Unknown task — can't evaluate
  return false
}

function fmtDict(d: Record<string, unknown> | null): string {
  if (d == null) return 'null'
  return Object.entries(d)
    .map(([k, v]) => {
      if (typeof v === 'number') {
        return `${k}: ${Number.isInteger(v) ? v : v.toFixed(3)}`
      }
      return `${k}: ${JSON.stringify(v)}`
    })
    .join(', ')
}

export default function PredictionOverlay({ task, samples }: Props) {
  const [sampleIdx, setSampleIdx] = useState(0)

  if (samples.length === 0) {
    return <p className="empty-note">No samples in this run.</p>
  }

  const sample = samples[Math.min(sampleIdx, samples.length - 1)]
  const hasGT      = sample.tokens.some(t => t.pred == null)
  const hasPreds   = sample.tokens.some(t => t.pred != null)

  return (
    <div className="overlay-container">
      {/* Sample navigation */}
      <div className="sample-nav">
        <button
          onClick={() => setSampleIdx(i => Math.max(0, i - 1))}
          disabled={sampleIdx === 0}
        >
          ← Prev
        </button>
        <span className="sample-label">
          Sample {sampleIdx + 1} / {samples.length}
          &nbsp;(id&nbsp;{sample.id})
        </span>
        <button
          onClick={() => setSampleIdx(i => Math.min(samples.length - 1, i + 1))}
          disabled={sampleIdx === samples.length - 1}
        >
          Next →
        </button>
      </div>

      {/* Legend */}
      <div className="legend">
        {hasGT && (
          <>
            <span className="legend-swatch swatch-gt" /> ground truth (no prediction)
          </>
        )}
        {hasPreds && (
          <>
            <span className="legend-swatch swatch-correct" /> correct prediction
            <span className="legend-swatch swatch-wrong" /> mismatch
          </>
        )}
      </div>

      {/* SVG overlay */}
      <div className="svg-wrapper">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          xmlns="http://www.w3.org/2000/svg"
          className="pred-svg"
        >
          {/* faint page background */}
          <rect x={0} y={0} width={W} height={H} fill="#fafafa" stroke="#ddd" strokeWidth={1} />

          {sample.tokens.map((tok, i) => {
            const isGT = tok.pred == null
            const { fill, stroke } = isGT
              ? COLOR_GT
              : isCorrect(task, tok) ? COLOR_CORRECT : COLOR_WRONG
            const x = tok.x0 * W
            const y = tok.y0 * H
            const w = (tok.x1 - tok.x0) * W
            const h = (tok.y1 - tok.y0) * H

            const tooltipLabel = fmtDict(tok.label as Record<string, unknown> | null)
            const tooltipPred  = tok.pred != null ? fmtDict(tok.pred as Record<string, unknown>) : 'null'
            const tooltipText  = tok.text ? `text: "${tok.text}"\n` : ''

            return (
              <rect
                key={i}
                x={x}
                y={y}
                width={w}
                height={h}
                fill={fill}
                stroke={stroke}
                strokeWidth={1.5}
                rx={2}
              >
                <title>{`${tooltipText}label: {${tooltipLabel}}\npred:  {${tooltipPred}}`}</title>
              </rect>
            )
          })}

          {/* Render text inside tokens if present */}
          {sample.tokens.map((tok, i) => {
            if (!tok.text) return null
            const cx = ((tok.x0 + tok.x1) / 2) * W
            const cy = ((tok.y0 + tok.y1) / 2) * H
            return (
              <text
                key={`t${i}`}
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={10}
                fill="#222"
              >
                {tok.text}
              </text>
            )
          })}

          {/* For ground-truth-only tokens: render centered record·field label */}
          {sample.tokens.map((tok, i) => {
            if (tok.pred != null) return null
            const label = tok.label as { record?: number; field?: number } | null
            if (label == null) return null
            const cx = ((tok.x0 + tok.x1) / 2) * W
            const cy = ((tok.y0 + tok.y1) / 2) * H
            return (
              <text
                key={`gt${i}`}
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={9}
                fill="#378ADD"
                fontFamily="monospace"
              >
                {`${label.record}·${label.field}`}
              </text>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
