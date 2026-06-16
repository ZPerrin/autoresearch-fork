// ---- Artifact schema types (mirrors runs/ and datasets/ JSON contract v3) ----

// ---- Shared ----

export type LabelValue = string | number | boolean | null

export interface Token {
  x0: number
  y0: number
  x1: number
  y1: number
  text: string | null
}

export type CellRole =
  | 'header' | 'group_header' | 'data' | 'section' | 'summary' | 'key' | 'value'

export interface Cell {
  region_index: number
  row_index: number
  column_index: number
  span: [number, number]                    // [colspan, rowspan]
  bbox: [number, number, number, number]    // normalized [0,1]
  role: CellRole
  field: string | null
  token_ids: number[]
}

export interface Region {
  type: string                              // "table" | "form" | "footer" | …
  name: string | null
  index: number
  bbox: [number, number, number, number]    // normalized [0,1]
}

export interface Sample {
  id: number
  image: string        // URL like /datasets/<id>/images/0.png
  width: number        // page pixel width
  height: number       // page pixel height
  tokens: Token[]
  cells: Cell[]
  regions?: Region[]
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

export interface FieldSpec {
  name: string
  type: string
  align: string
  group?: string | null
}

export interface SpanCell {
  span: number
  text?: string | null
  type?: string | null
  align: string
}

export interface SpanRowSpec {
  cells: SpanCell[]
}

export interface TableSpec {
  name: string
  fields: FieldSpec[]
  rows: [number, number]
  instances: [number, number]
  section?: SpanRowSpec | null
  totals?: SpanRowSpec | null
}

export interface JitterSpec {
  row_h: number
  col_w: number
  offset: number
  baseline: number
}

export interface ResolvedDocumentSpec {
  name: string
  tables: TableSpec[]
  globals: FieldSpec[]
  background_terms: string[]
  layout: {
    page: [number, number]
    margin: [number, number]
    row_h: number
    pad: number
    table_gap: number
    row_gap?: number
    instance_gap?: number | null
    section_gap?: number | null
    globals_per_row?: number
  }
  jitter?: JitterSpec
  structure: Record<string, LabelValue>
  render: Record<string, LabelValue>
}

export interface DatasetManifest {
  schema_version: number
  dataset_id: string
  generator_version?: number
  task: string
  modalities: string[]
  count: number
  config: {
    class?: string
    spec?: ResolvedDocumentSpec
    seed?: number
    // Legacy manifest fields, used only when resolved spec is absent.
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
