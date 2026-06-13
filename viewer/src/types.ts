// ---- Artifact schema types (mirrors runs/ and datasets/ JSON contract v2) ----

// ---- Shared ----

export interface Token {
  x0: number
  y0: number
  x1: number
  y1: number
  text: string | null
  label: { record?: number; field?: number; [key: string]: unknown } | null
  pred:  { record?: number; field?: number; confidence?: number; [key: string]: unknown } | null
}

export interface Sample {
  id: number
  image: string        // URL like /datasets/<id>/images/0.png
  width: number        // page pixel width
  height: number       // page pixel height
  tokens: Token[]
}

export interface SamplesFile {
  schema_version: number
  dataset_id?: string
  samples: Sample[]
}

// ---- Runs ----

export interface RunSummary {
  run_id: string
  commit: string
  branch: string
  device: string
  status: string
  description: string
  dataset_id?: string
  metrics: Record<string, number>
}

export interface RunIndex {
  schema_version: number
  runs: RunSummary[]
}

export interface RunDetail {
  schema_version: number
  run_id: string
  commit: string
  branch: string
  device: string
  config: {
    task: string
    seed?: number
    [key: string]: unknown
  }
  metrics: Record<string, number>
  curve: { step: number; train_loss: number; val_exact: number }[]
  wall_seconds: number
  status: string
  description: string
  dataset_id?: string
}

// ---- Datasets ----

export interface DatasetManifest {
  schema_version: number
  dataset_id: string
  generator_version?: number
  task: string
  modalities: string[]
  count: number
  config: {
    schema_name?: string
    fields?: string[]
    page?: [number, number]
    difficulty?: Record<string, unknown>
    [key: string]: unknown
  }
}

export interface DatasetsIndex {
  schema_version: number
  datasets: DatasetManifest[]
}

// ---- Source (what the left pane is currently showing) ----

export type ActiveSource =
  | { kind: 'dataset'; manifest: DatasetManifest; samples: SamplesFile }
  | { kind: 'run';     detail: RunDetail;         samples: SamplesFile }
