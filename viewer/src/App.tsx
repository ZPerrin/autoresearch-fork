import { useEffect, useState } from 'react'
import type {
  DatasetsIndex,
  DatasetManifest,
  RunIndex,
  RunSummary,
  SamplesFile,
  RunDetail,
  ActiveSource,
  Token,
} from './types'
import SourceSelector from './SourceSelector'
import DocumentViewer from './DocumentViewer'
import MetaPanel from './MetaPanel'
import './App.css'

const DEFAULT_DATASET = 'grid-invoice-v1'

export default function App() {
  // Index state
  const [datasets, setDatasets]           = useState<DatasetManifest[]>([])
  const [runs, setRuns]                   = useState<RunSummary[]>([])
  const [indexLoading, setIndexLoading]   = useState(true)
  const [indexError, setIndexError]       = useState<string | null>(null)

  // Active source
  const [activeSource, setActiveSource]   = useState<ActiveSource | null>(null)
  const [sourceLoading, setSourceLoading] = useState(false)
  const [sourceError, setSourceError]     = useState<string | null>(null)
  const [activeKind, setActiveKind]       = useState<'dataset' | 'run' | null>(null)
  const [activeId, setActiveId]           = useState<string | null>(null)

  // Selected token
  const [selectedToken, setSelectedToken] = useState<Token | null>(null)

  // Load both indices on mount
  useEffect(() => {
    Promise.all([
      fetch('/datasets/index.json').then(r => {
        if (!r.ok) throw new Error(`datasets/index.json HTTP ${r.status}`)
        return r.json() as Promise<DatasetsIndex>
      }),
      fetch('/runs/index.json').then(r => {
        if (!r.ok) throw new Error(`runs/index.json HTTP ${r.status}`)
        return r.json() as Promise<RunIndex>
      }),
    ])
      .then(([dsIdx, runsIdx]) => {
        setDatasets(dsIdx.datasets ?? [])
        setRuns(runsIdx.runs ?? [])
        setIndexLoading(false)
        // Auto-load default dataset if present
        const defaultDs = dsIdx.datasets?.find(d => d.dataset_id === DEFAULT_DATASET)
          ?? dsIdx.datasets?.[0]
        if (defaultDs) {
          loadDataset(defaultDs.dataset_id)
        }
      })
      .catch(err => {
        setIndexError(String(err))
        setIndexLoading(false)
      })
  }, [])

  function loadDataset(id: string) {
    setActiveKind('dataset')
    setActiveId(id)
    setSourceLoading(true)
    setSourceError(null)
    setSelectedToken(null)
    setActiveSource(null)

    Promise.all([
      fetch(`/datasets/${id}/manifest.json`).then(r => {
        if (!r.ok) throw new Error(`manifest HTTP ${r.status}`)
        return r.json() as Promise<DatasetManifest>
      }),
      fetch(`/datasets/${id}/samples.json`).then(r => {
        if (!r.ok) throw new Error(`samples HTTP ${r.status}`)
        return r.json() as Promise<SamplesFile>
      }),
    ])
      .then(([manifest, samples]) => {
        setActiveSource({ kind: 'dataset', manifest, samples })
        setSourceLoading(false)
      })
      .catch(err => {
        setSourceError(String(err))
        setSourceLoading(false)
      })
  }

  function loadRun(id: string) {
    setActiveKind('run')
    setActiveId(id)
    setSourceLoading(true)
    setSourceError(null)
    setSelectedToken(null)
    setActiveSource(null)

    Promise.all([
      fetch(`/runs/${id}/run.json`).then(r => {
        if (!r.ok) throw new Error(`run.json HTTP ${r.status}`)
        return r.json() as Promise<RunDetail>
      }),
      fetch(`/runs/${id}/samples.json`).then(r => {
        if (!r.ok) throw new Error(`samples.json HTTP ${r.status}`)
        return r.json() as Promise<SamplesFile>
      }),
    ])
      .then(([detail, samples]) => {
        setActiveSource({ kind: 'run', detail, samples })
        setSourceLoading(false)
      })
      .catch(err => {
        setSourceError(String(err))
        setSourceLoading(false)
      })
  }

  const samples = activeSource?.samples.samples ?? []
  const task = activeSource?.kind === 'run'
    ? activeSource.detail.config.task
    : activeSource?.kind === 'dataset'
    ? activeSource.manifest.task
    : undefined

  return (
    <div className="app">
      <header className="app-header">
        <h1>autoresearch · viewer</h1>
      </header>

      <div className="split-layout">
        {/* LEFT: document viewer */}
        <div className="pane pane-left">
          {sourceLoading && <p className="loading-note">Loading source…</p>}
          {sourceError  && <p className="error-note">{sourceError}</p>}
          {!sourceLoading && !sourceError && samples.length === 0 && activeSource == null && (
            <p className="empty-note" style={{ padding: 24 }}>Select a dataset or run →</p>
          )}
          {samples.length > 0 && (
            <DocumentViewer
              samples={samples}
              task={task}
              selectedToken={selectedToken}
              onSelectToken={setSelectedToken}
            />
          )}
        </div>

        {/* RIGHT: metadata panel */}
        <div className="pane pane-right">
          {indexError && <p className="error-note" style={{ marginBottom: 12 }}>{indexError}</p>}

          <SourceSelector
            datasets={datasets}
            runs={runs}
            activeKind={activeKind}
            activeId={activeId}
            onSelectDataset={loadDataset}
            onSelectRun={loadRun}
            loading={indexLoading}
          />

          <MetaPanel
            source={activeSource}
            task={task}
            selectedToken={selectedToken}
          />
        </div>
      </div>
    </div>
  )
}
