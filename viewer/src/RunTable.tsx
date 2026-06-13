import type { RunSummary } from './types'

interface Props {
  runs: RunSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
}

const KEY_METRICS = ['exact', 'record_acc', 'field_acc', 'baseline_geosort_exact']

export default function RunTable({ runs, selectedId, onSelect }: Props) {
  if (runs.length === 0) {
    return <p className="empty-note">No runs found in index.json.</p>
  }

  // Collect all metric keys present across all runs
  const metricKeys = Array.from(
    new Set(runs.flatMap(r => Object.keys(r.metrics)))
  ).sort((a, b) => {
    // Put KEY_METRICS first
    const ai = KEY_METRICS.indexOf(a)
    const bi = KEY_METRICS.indexOf(b)
    if (ai !== -1 && bi !== -1) return ai - bi
    if (ai !== -1) return -1
    if (bi !== -1) return 1
    return a.localeCompare(b)
  })

  return (
    <table className="run-table">
      <thead>
        <tr>
          <th>Run ID</th>
          <th>Branch</th>
          <th>Device</th>
          <th>Status</th>
          <th>Description</th>
          {metricKeys.map(k => (
            <th key={k}>{k}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {runs.map(run => (
          <tr
            key={run.run_id}
            className={run.run_id === selectedId ? 'selected' : ''}
            onClick={() => onSelect(run.run_id)}
            title="Click to inspect this run"
          >
            <td className="mono">{run.run_id}</td>
            <td className="mono">{run.branch}</td>
            <td>{run.device}</td>
            <td>
              <span className={`status-badge status-${run.status}`}>{run.status}</span>
            </td>
            <td>{run.description}</td>
            {metricKeys.map(k => (
              <td key={k} className="metric-cell">
                {run.metrics[k] != null ? run.metrics[k].toFixed(3) : '—'}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
