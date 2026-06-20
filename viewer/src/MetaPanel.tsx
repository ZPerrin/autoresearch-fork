import { useCallback, useEffect, useRef, type ReactNode } from 'react'
import type { ActiveSource, Cell, LabelValue, Region, Sample, Selection, TargetPath } from './types'
import { buildDiff, pathEqual, pathKey, type DiffLeaf, type DiffNode, type LeafStatus } from './diff'

interface Props {
  source: ActiveSource | null
  task?: string
  selection: Selection | null
  sample: Sample | null
  onSelectTarget: (path: TargetPath) => void
}

function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="meta-row">
      <span className="meta-key">{k}</span>
      <span className="meta-val mono">{v}</span>
    </div>
  )
}

function formatBox(b: [number, number, number, number]): string {
  return `(${b[0].toFixed(3)}, ${b[1].toFixed(3)}) → (${b[2].toFixed(3)}, ${b[3].toFixed(3)})`
}

function RegionBody({ region }: { region: Region }) {
  return (
    <>
      <div className="meta-subsection-title">Region</div>
      <Row k="type" v={region.type} />
      {region.name != null && <Row k="name" v={region.name} />}
      <Row k="index" v={region.index} />
      <Row k="bbox" v={<span style={{ fontSize: '0.78rem' }}>{formatBox(region.bbox)}</span>} />
    </>
  )
}

function CellBody({ cell, sample }: { cell: Cell; sample: Sample }) {
  const region = sample.regions?.[cell.region_index]
  const texts = cell.word_ids
    .map(id => sample.words[id]?.text)
    .filter((t): t is string => t != null && t !== '')
  return (
    <>
      <div className="meta-subsection-title">Cell</div>
      <Row k="role" v={cell.role} />
      {cell.field != null && <Row k="field" v={cell.field} />}
      <Row k="row" v={cell.row_index} />
      <Row k="col" v={cell.column_index} />
      <Row k="span" v={`${cell.span[0]}×${cell.span[1]}`} />
      <Row k="bbox" v={<span style={{ fontSize: '0.78rem' }}>{formatBox(cell.bbox)}</span>} />
      {texts.length > 0 && <Row k="words" v={`"${texts.join(' ')}"`} />}
      {region != null && <RegionBody region={region} />}
    </>
  )
}

const KEY_METRICS = ['exact', 'record_acc', 'field_acc', 'baseline_majority_exact', 'baseline_geosort_exact']

function formatRange([minimum, maximum]: [number, number]): string {
  return minimum === maximum ? String(minimum) : `${minimum}-${maximum}`
}

function formatValue(value: LabelValue): string {
  return value === null ? 'null' : String(value)
}

function entries(obj: Record<string, LabelValue>): [string, LabelValue][] {
  return Object.entries(obj)
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

// Diff status → swatch color. Mirrors DocumentViewer's lens palette: green match, red
// missing/mismatch, amber spurious. (Kept in sync by eye; both are first-pass.)
const STATUS_COLOR: Record<LeafStatus, string> = {
  match: '#16A34A',
  mismatch: '#DC2626',
  missing: '#DC2626',
  spurious: '#D97706',
}

function LeafRow({ name, leaf, path, showDiff, selected, onSelect, rowRef }: {
  name: string; leaf: DiffLeaf; path: TargetPath; showDiff: boolean
  selected: boolean; onSelect: (p: TargetPath) => void
  rowRef: (el: HTMLDivElement | null) => void
}) {
  const value = (leaf.target ?? leaf.pred)?.value ?? ''
  const mismatch = showDiff && leaf.status === 'mismatch'
  return (
    <div
      ref={rowRef}
      className={`target-leaf${selected ? ' is-selected' : ''}`}
      onClick={() => onSelect(path)}
    >
      {showDiff && <span className="target-dot" style={{ background: STATUS_COLOR[leaf.status] }} />}
      <span className="target-leaf-name mono">{name}</span>
      <span className="target-leaf-value mono">
        {mismatch
          ? `${leaf.target?.value ?? '∅'} → ${leaf.pred?.value ?? '∅'}`
          : (value === '' ? '∅' : value)}
      </span>
    </div>
  )
}

function TargetsTree({ node, base, showDiff, selection, onSelect, registerRow }: {
  node: DiffNode; base: TargetPath; showDiff: boolean
  selection: Selection | null
  onSelect: (p: TargetPath) => void
  registerRow: (key: string, el: HTMLDivElement | null) => void
}) {
  return (
    <div className="targets-tree">
      {Object.entries(node.fields).map(([name, leaf]) => {
        const path: TargetPath = [...base, 'fields', name]
        const selected = selection?.kind === 'target' && pathEqual(selection.path, path)
        return (
          <LeafRow key={pathKey(path)} name={name} leaf={leaf} path={path} showDiff={showDiff}
            selected={selected} onSelect={onSelect}
            rowRef={el => registerRow(pathKey(path), el)} />
        )
      })}
      {Object.entries(node.field_groups).map(([g, group]) => (
        <div className="target-group" key={g}>
          <div className="target-group-header mono">
            {g} <span className="target-group-count">[{group.records.length}]</span>
            {showDiff && group.delta !== 0 && (
              <span className="target-group-delta" style={{ color: STATUS_COLOR[group.delta > 0 ? 'spurious' : 'missing'] }}>
                {group.delta > 0 ? `+${group.delta}` : group.delta}
              </span>
            )}
          </div>
          {group.records.map((rec, i) => (
            <div className="target-record" key={i}>
              <div className="target-record-label mono">#{i}</div>
              <TargetsTree node={rec} base={[...base, 'field_groups', g, i]} showDiff={showDiff}
                selection={selection} onSelect={onSelect} registerRow={registerRow} />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

export default function MetaPanel({ source, task: _task, selection, sample, onSelectTarget }: Props) {

  const rowRefs = useRef(new Map<string, HTMLDivElement | null>())
  // Stable identity so leaf rows don't re-run their ref callbacks on every parent render.
  const registerRow = useCallback((key: string, el: HTMLDivElement | null) => {
    rowRefs.current.set(key, el)
  }, [])

  useEffect(() => {
    if (selection?.kind !== 'target') return
    const el = rowRefs.current.get(pathKey(selection.path))
    el?.scrollIntoView({ block: 'nearest' })
  }, [selection])

  const targetRoot = sample?.targets?.extraction
  const diffResult = sample ? buildDiff(sample) : null

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
                {(() => {
                  const tables = source.manifest.config.spec.tables
                  const features: string[] = []
                  if (tables.some(t => t.fields.some(f => f.group != null)))
                    features.push('grouped headers')
                  if (tables.some(t => t.section != null)) features.push('section rows')
                  if (tables.some(t => t.totals != null)) features.push('totals rows')
                  return features.map(name => (
                    <span className="structure-flag mono" key={name}>{name}</span>
                  ))
                })()}
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

      {/* Selection detail — word / cell / region */}
      <section className="meta-section token-detail">
        {(() => {
          if (selection == null || sample == null) {
            return (
              <>
                <div className="meta-section-title">Selection</div>
                <p className="empty-note">Click a box in the document to inspect it.</p>
              </>
            )
          }

          if (selection.kind === 'word') {
            const token = sample.words[selection.index]
            const cell = sample.cells.find(c => c.word_ids.includes(selection.index))
            return (
              <>
                <div className="meta-section-title">Selected word</div>
                {token?.text != null && <Row k="text" v={`"${token.text}"`} />}
                {token && (
                  <Row k="coords" v={
                    <span style={{ fontSize: '0.78rem' }}>
                      {formatBox([token.x0, token.y0, token.x1, token.y1])}
                    </span>
                  } />
                )}
                {cell == null
                  ? <Row k="cell" v="background / non-answer" />
                  : <CellBody cell={cell} sample={sample} />}
              </>
            )
          }

          if (selection.kind === 'cell') {
            const cell = sample.cells[selection.index]
            return (
              <>
                <div className="meta-section-title">Selected cell</div>
                {cell == null
                  ? <p className="empty-note">Cell not found.</p>
                  : <CellBody cell={cell} sample={sample} />}
              </>
            )
          }

          if (selection.kind === 'target') {
            return (
              <>
                <div className="meta-section-title">Selected target</div>
                <p className="empty-note mono" style={{ fontSize: '0.78rem' }}>{selection.path.join(' / ')}</p>
              </>
            )
          }

          const region = sample.regions?.[selection.index]
          const cellCount = sample.cells.filter(c => c.region_index === selection.index).length
          return (
            <>
              <div className="meta-section-title">Selected region</div>
              {region == null ? (
                <p className="empty-note">Region not found.</p>
              ) : (
                <>
                  <RegionBody region={region} />
                  <Row k="cells" v={cellCount} />
                </>
              )}
            </>
          )
        })()}
      </section>

      {targetRoot && diffResult && (
        <section className="meta-section targets-section">
          <div className="meta-section-title">Targets{diffResult.showDiff ? ' · diff' : ''}</div>
          <TargetsTree
            node={diffResult.diff}
            base={[]}
            showDiff={diffResult.showDiff}
            selection={selection}
            onSelect={onSelectTarget}
            registerRow={registerRow}
          />
        </section>
      )}

    </div>
  )
}
