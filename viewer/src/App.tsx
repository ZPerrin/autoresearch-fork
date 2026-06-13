import { useEffect, useState } from 'react'
import type { RunIndex, RunDetail, SamplesFile } from './types'
import RunTable from './RunTable'
import PredictionOverlay from './PredictionOverlay'
import './App.css'

type LoadState = 'idle' | 'loading' | 'error'

export default function App() {
  const [index, setIndex] = useState<RunIndex | null>(null)
  const [indexState, setIndexState] = useState<LoadState>('idle')

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null)
  const [samples, setSamples] = useState<SamplesFile | null>(null)
  const [detailState, setDetailState] = useState<LoadState>('idle')

  // Fetch index on mount
  useEffect(() => {
    setIndexState('loading')
    fetch('/runs/index.json')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<RunIndex>
      })
      .then(data => {
        setIndex(data)
        setIndexState('idle')
      })
      .catch(() => setIndexState('error'))
  }, [])

  // Fetch run detail + samples when selection changes
  useEffect(() => {
    if (!selectedId) return
    setDetailState('loading')
    setRunDetail(null)
    setSamples(null)

    Promise.all([
      fetch(`/runs/${selectedId}/run.json`).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<RunDetail>
      }),
      fetch(`/runs/${selectedId}/samples.json`).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<SamplesFile>
      }),
    ])
      .then(([detail, samp]) => {
        setRunDetail(detail)
        setSamples(samp)
        setDetailState('idle')
      })
      .catch(() => setDetailState('error'))
  }, [selectedId])

  return (
    <div className="app">
      <header className="app-header">
        <h1>autoresearch · run viewer</h1>
      </header>

      <main>
        {/* Run list */}
        <section className="section">
          <h2>Runs</h2>
          {indexState === 'loading' && <p className="loading-note">Loading index…</p>}
          {indexState === 'error'   && <p className="error-note">Failed to load /runs/index.json. Is the dev server running?</p>}
          {index && (
            <RunTable
              runs={index.runs}
              selectedId={selectedId}
              onSelect={id => {
                setSelectedId(id)
                setRunDetail(null)
                setSamples(null)
              }}
            />
          )}
        </section>

        {/* Run detail */}
        {selectedId && (
          <section className="section detail-section">
            <h2>
              Run: <span className="mono">{selectedId}</span>
            </h2>

            {detailState === 'loading' && <p className="loading-note">Loading run data…</p>}
            {detailState === 'error'   && <p className="error-note">Failed to load run data.</p>}

            {runDetail && samples && (
              <>
                <div className="run-meta">
                  <dl>
                    <dt>Branch</dt><dd className="mono">{runDetail.branch}</dd>
                    <dt>Commit</dt><dd className="mono">{runDetail.commit}</dd>
                    <dt>Device</dt><dd>{runDetail.device}</dd>
                    <dt>Task</dt>  <dd className="mono">{runDetail.config.task}</dd>
                    <dt>Status</dt><dd><span className={`status-badge status-${runDetail.status}`}>{runDetail.status}</span></dd>
                    <dt>Wall time</dt><dd>{runDetail.wall_seconds.toFixed(1)} s</dd>
                  </dl>
                </div>

                <h3>Prediction overlay</h3>
                <PredictionOverlay
                  task={runDetail.config.task}
                  samples={samples.samples}
                />
              </>
            )}
          </section>
        )}
      </main>
    </div>
  )
}
