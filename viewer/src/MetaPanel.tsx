import type { ActiveSource, LabelValue, Token, TokenLabel } from './types'
import { predictionMatchStatus } from './tokenMatch'

interface Props {
  source: ActiveSource | null
  task?: string
  selectedToken: Token | null
}

const KEY_METRICS = ['exact', 'record_acc', 'field_acc', 'baseline_majority_exact', 'baseline_geosort_exact']

function formatRange([minimum, maximum]: [number, number]): string {
  return minimum === maximum ? String(minimum) : `${minimum}-${maximum}`
}

function formatValue(value: LabelValue): string {
  return value === null ? 'null' : String(value)
}

function entries(label: TokenLabel): [string, LabelValue][] {
  return Object.entries(label)
}

function MetricRow({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="meta-row">
      <span className="meta-key">{label}</span>
      <span className="meta-val mono">{value != null ? value.toFixed(3) : '—'}</span>
    </div>
  )
}

/** Tiny inline sparkline for the training curve (val_exact vs steps) */
function Sparkline({ curve }: { curve: { step: number; val_exact: number }[] }) {
  if (curve.length === 0) return null
  const W = 120, H = 32, PAD = 2
  const steps   = curve.map(p => p.step)
  const vals    = curve.map(p => p.val_exact)
  const minX = Math.min(...steps),  maxX = Math.max(...steps)
  const minY = Math.min(...vals),   maxY = Math.max(...vals)
  const rangeX = maxX - minX || 1
  const rangeY = maxY - minY || 0.001

  const pts = curve.map(p => {
    const x = PAD + ((p.step - minX) / rangeX) * (W - 2 * PAD)
    const y = PAD + (1 - (p.val_exact - minY) / rangeY) * (H - 2 * PAD)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  return (
    <svg width={W} height={H} style={{ display: 'block', margin: '4px 0' }}>
      <rect x={0} y={0} width={W} height={H} fill="#f5f5f5" rx={3} />
      <polyline points={pts} fill="none" stroke="#1D9E75" strokeWidth={1.5} />
    </svg>
  )
}

export default function MetaPanel({ source, task, selectedToken }: Props) {
  const matchStatus = selectedToken == null
    ? 'not-applicable'
    : predictionMatchStatus(task, selectedToken.label, selectedToken.pred)

  return (
    <div className="meta-panel">
      {/* Source metadata */}
      {source == null && (
        <p className="empty-note" style={{ marginBottom: 12 }}>Select a dataset or run from above.</p>
      )}

      {source?.kind === 'dataset' && (
        <section className="meta-section">
          <div className="meta-section-title">Dataset</div>
          <div className="meta-row">
            <span className="meta-key">id</span>
            <span className="meta-val mono">{source.manifest.dataset_id}</span>
          </div>
          <div className="meta-row">
            <span className="meta-key">task</span>
            <span className="meta-val mono">{source.manifest.task}</span>
          </div>
          <div className="meta-row">
            <span className="meta-key">count</span>
            <span className="meta-val">{source.manifest.count}</span>
          </div>
          <div className="meta-row">
            <span className="meta-key">modalities</span>
            <span className="meta-val">{source.manifest.modalities.join(', ')}</span>
          </div>
          {source.manifest.config.spec ? (
            <>
              <div className="meta-row">
                <span className="meta-key">class</span>
                <span className="meta-val mono">
                  {source.manifest.config.class ?? source.manifest.config.spec.name}
                </span>
              </div>
              <div className="meta-row">
                <span className="meta-key">page</span>
                <span className="meta-val mono">
                  {source.manifest.config.spec.layout.page.join(' x ')}
                </span>
              </div>
              <div className="meta-subsection-title">Globals</div>
              <div className="meta-val mono spec-field-list">
                {source.manifest.config.spec.globals.length > 0
                  ? source.manifest.config.spec.globals.map(field => field.name).join(', ')
                  : 'none'}
              </div>
              <div className="meta-subsection-title">Tables</div>
              <div className="structure-list">
                {source.manifest.config.spec.tables.map(table => (
                  <div className="structure-card" key={table.name}>
                    <div className="structure-card-title mono">{table.name}</div>
                    <div className="structure-card-range">
                      rows {formatRange(table.rows)} · instances {formatRange(table.instances)}
                    </div>
                    <div className="structure-card-fields mono">
                      {table.fields.map(field => field.name).join(', ')}
                    </div>
                  </div>
                ))}
              </div>
              <div className="meta-subsection-title">Structure</div>
              <div className="structure-flags">
                {entries(source.manifest.config.spec.structure)
                  .filter(([, value]) => value === true || (typeof value === 'number' && value > 0))
                  .map(([key, value]) => (
                    <span className="structure-flag mono" key={key}>
                      {value === true ? key : `${key}=${formatValue(value)}`}
                    </span>
                  ))}
              </div>
              {(() => {
                const layout = source.manifest.config.spec.layout
                const spacingParts: string[] = []
                if (layout.row_gap != null) spacingParts.push(`row_gap ${layout.row_gap}`)
                if (layout.instance_gap != null) spacingParts.push(`instance_gap ${layout.instance_gap}`)
                if (layout.section_gap != null) spacingParts.push(`section_gap ${layout.section_gap}`)
                if (layout.globals_per_row != null) spacingParts.push(`globals_per_row ${layout.globals_per_row}`)
                if (spacingParts.length === 0) return null
                return (
                  <div className="meta-row">
                    <span className="meta-key">spacing</span>
                    <span className="meta-val mono">{spacingParts.join(' · ')}</span>
                  </div>
                )
              })()}
              {(() => {
                const jitter = source.manifest.config.spec.jitter
                const axes = jitter
                  ? ([
                      ['row_h', jitter.row_h],
                      ['col_w', jitter.col_w],
                      ['offset', jitter.offset],
                      ['baseline', jitter.baseline],
                    ] as [string, number][]).filter(([, v]) => v !== 0)
                  : []
                return (
                  <div className="meta-row">
                    <span className="meta-key">jitter</span>
                    <span className="meta-val mono">
                      {axes.length > 0
                        ? axes.map(([k, v]) => `${k} ${v}`).join(' · ')
                        : 'off'}
                    </span>
                  </div>
                )
              })()}
            </>
          ) : (
            <>
              {source.manifest.config.schema_name && (
                <div className="meta-row">
                  <span className="meta-key">schema</span>
                  <span className="meta-val mono">{source.manifest.config.schema_name}</span>
                </div>
              )}
              {source.manifest.config.page && (
                <div className="meta-row">
                  <span className="meta-key">page</span>
                  <span className="meta-val mono">{source.manifest.config.page.join(' x ')}</span>
                </div>
              )}
              {source.manifest.config.fields && (
                <div className="meta-row">
                  <span className="meta-key">fields</span>
                  <span className="meta-val mono">{source.manifest.config.fields.join(', ')}</span>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {source?.kind === 'run' && (
        <section className="meta-section">
          <div className="meta-section-title">Run</div>
          <div className="meta-row">
            <span className="meta-key">id</span>
            <span className="meta-val mono">{source.detail.run_id}</span>
          </div>
          <div className="meta-row">
            <span className="meta-key">status</span>
            <span className={`status-badge status-${source.detail.status}`}>{source.detail.status}</span>
          </div>
          <div className="meta-row">
            <span className="meta-key">dataset</span>
            <span className="meta-val mono">{source.detail.dataset_id ?? '—'}</span>
          </div>
          <div className="meta-row">
            <span className="meta-key">branch</span>
            <span className="meta-val mono">{source.detail.branch}</span>
          </div>
          <div className="meta-subsection-title">Metrics</div>
          {KEY_METRICS.map(k => (
            <MetricRow key={k} label={k} value={source.detail.metrics[k]} />
          ))}
          {source.detail.curve?.length > 0 && (
            <>
              <div className="meta-subsection-title" style={{ marginTop: 10 }}>
                val_exact curve
              </div>
              <Sparkline curve={source.detail.curve} />
              <div style={{ fontSize: '0.75rem', color: '#888' }}>
                final: {source.detail.curve.at(-1)?.val_exact.toFixed(3)}
              </div>
            </>
          )}
        </section>
      )}

      {/* Token detail */}
      <section className="meta-section token-detail">
        <div className="meta-section-title">Selected token</div>
        {selectedToken == null ? (
          <p className="empty-note">Click a box in the document to inspect it.</p>
        ) : (
          <>
            {selectedToken.text != null && (
              <div className="meta-row">
                <span className="meta-key">text</span>
                <span className="meta-val mono">"{selectedToken.text}"</span>
              </div>
            )}
            <div className="meta-row">
              <span className="meta-key">label</span>
              <span className="meta-val mono">
                {selectedToken.label != null ? 'ground truth' : 'background / non-answer'}
              </span>
            </div>
            {selectedToken.label != null && (
              entries(selectedToken.label).map(([key, value]) => (
                <div className="meta-row" key={key}>
                  <span className="meta-key">{key}</span>
                  <span className="meta-val mono">{formatValue(value)}</span>
                </div>
              ))
            )}
            {selectedToken.pred != null && (
              <>
                <div className="meta-row">
                  <span className="meta-key">pred</span>
                  <span className="meta-val mono">prediction</span>
                </div>
                {entries(selectedToken.pred)
                  .filter(([key]) => key !== 'confidence')
                  .map(([key, value]) => (
                    <div className="meta-row" key={key}>
                      <span className="meta-key">{key}</span>
                      <span className="meta-val mono">{formatValue(value)}</span>
                    </div>
                  ))}
                {selectedToken.pred.confidence != null && (
                  <div className="meta-row">
                    <span className="meta-key">confidence</span>
                    <span className="meta-val mono">{Number(selectedToken.pred.confidence).toFixed(3)}</span>
                  </div>
                )}
                <div className="meta-row">
                  <span className="meta-key">match</span>
                  <span className={`meta-val ${
                    matchStatus === 'correct'
                      ? 'correct-tag'
                      : matchStatus === 'mismatch' ? 'wrong-tag' : ''
                  }`}>
                    {matchStatus === 'not-applicable' ? 'not evaluated' : matchStatus}
                  </span>
                </div>
              </>
            )}
            <div className="meta-row coords-row">
              <span className="meta-key">coords</span>
              <span className="meta-val mono" style={{ fontSize: '0.78rem' }}>
                ({selectedToken.x0.toFixed(3)}, {selectedToken.y0.toFixed(3)}) →
                ({selectedToken.x1.toFixed(3)}, {selectedToken.y1.toFixed(3)})
              </span>
            </div>
          </>
        )}
      </section>

      {/* Legend */}
      <section className="meta-section">
        <div className="meta-section-title">Legend</div>
        <div className="legend-list">
          <span className="legend-item"><span className="legend-swatch swatch-gt" /> ground truth (no pred)</span>
          <span className="legend-item"><span className="legend-swatch swatch-correct" /> correct prediction</span>
          <span className="legend-item"><span className="legend-swatch swatch-wrong" /> mismatch</span>
          <span className="legend-item"><span className="legend-swatch swatch-selected" /> selected</span>
        </div>
      </section>
    </div>
  )
}
