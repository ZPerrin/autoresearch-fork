// ---- Artifact schema types (mirrors runs/ JSON contract) ----

export interface RunSummary {
  run_id: string
  commit: string
  branch: string
  device: string
  status: string
  description: string
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
    seed: number
    [key: string]: unknown
  }
  metrics: Record<string, number>
  curve: { step: number; train_loss: number; val_exact: number }[]
  wall_seconds: number
  status: string
  description: string
}

export interface Token {
  x0: number
  y0: number
  x1: number
  y1: number
  text: string | null
  label: Record<string, unknown>
  pred: Record<string, unknown>
}

export interface Sample {
  id: number
  tokens: Token[]
}

export interface SamplesFile {
  schema_version: number
  samples: Sample[]
}
