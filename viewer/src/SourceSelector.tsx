import type { DatasetManifest, RunSummary } from './types'

interface Props {
  datasets: DatasetManifest[]
  runs: RunSummary[]
  activeKind: 'dataset' | 'run' | null
  activeId: string | null
  onSelectDataset: (id: string) => void
  onSelectRun: (id: string) => void
  loading: boolean
}

export default function SourceSelector({
  datasets,
  runs,
  activeKind,
  activeId,
  onSelectDataset,
  onSelectRun,
  loading,
}: Props) {
  return (
    <div className="source-selector">
      {loading && <p className="loading-note" style={{ marginBottom: 8 }}>Loading…</p>}

      <div className="source-columns">
        {/* Datasets column */}
        <div className="source-col">
          <div className="source-col-header">Datasets</div>
          {datasets.length === 0 && <p className="empty-note">None found.</p>}
          {datasets.map(ds => (
            <button
              key={ds.dataset_id}
              className={`source-item ${activeKind === 'dataset' && activeId === ds.dataset_id ? 'active' : ''}`}
              onClick={() => onSelectDataset(ds.dataset_id)}
            >
              <span className="source-item-id">{ds.dataset_id}</span>
              <span className="source-item-meta">{ds.count} samples · {ds.task}</span>
            </button>
          ))}
        </div>

        {/* Runs column */}
        <div className="source-col">
          <div className="source-col-header">Runs</div>
          {runs.length === 0 && <p className="empty-note">None found.</p>}
          {runs.map(run => (
            <button
              key={run.run_id}
              className={`source-item ${activeKind === 'run' && activeId === run.run_id ? 'active' : ''}`}
              onClick={() => onSelectRun(run.run_id)}
            >
              <span className="source-item-id">{run.run_id}</span>
              <span className="source-item-meta">
                <span className={`status-dot status-${run.status}`} />
                {run.status} · {run.metrics.exact != null ? `exact=${run.metrics.exact.toFixed(2)}` : run.description}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
