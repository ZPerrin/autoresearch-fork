// viewer/src/diff.ts
// First-pass, grounding-keyed prediction diff (spec §4). The whole matcher is one pure
// function so the future real metric (spec §7) replaces *it*, not the UI.
import type { Field, Node, Sample, TargetPath } from './types'

const TASK = 'extraction'

export type LeafStatus = 'match' | 'mismatch' | 'missing' | 'spurious'

export interface DiffLeaf {
  status: LeafStatus
  target?: Field
  pred?: Field
}

export interface DiffGroup {
  records: DiffNode[]   // aligned by index to max(target, pred) length
  delta: number         // pred record count − target record count
}

export interface DiffNode {
  fields: Record<string, DiffLeaf>
  field_groups: Record<string, DiffGroup>
}

function sameWordIds(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false
  const set = new Set(a)
  return b.every(x => set.has(x))
}

function diffLeaf(target: Field | undefined, pred: Field | undefined): DiffLeaf {
  if (target && pred) {
    return { status: sameWordIds(target.word_ids, pred.word_ids) ? 'match' : 'mismatch', target, pred }
  }
  if (target) return { status: 'missing', target }
  return { status: 'spurious', pred }
}

export function diffNode(target: Node | undefined, pred: Node | undefined): DiffNode {
  const fields: Record<string, DiffLeaf> = {}
  const fieldKeys = new Set([...Object.keys(target?.fields ?? {}), ...Object.keys(pred?.fields ?? {})])
  for (const k of fieldKeys) {
    fields[k] = diffLeaf(target?.fields[k], pred?.fields[k])
  }

  const field_groups: Record<string, DiffGroup> = {}
  const groupKeys = new Set([
    ...Object.keys(target?.field_groups ?? {}),
    ...Object.keys(pred?.field_groups ?? {}),
  ])
  for (const g of groupKeys) {
    const tRecs = target?.field_groups[g] ?? []
    const pRecs = pred?.field_groups[g] ?? []
    const n = Math.max(tRecs.length, pRecs.length)
    const records: DiffNode[] = []
    for (let i = 0; i < n; i++) records.push(diffNode(tRecs[i], pRecs[i]))
    field_groups[g] = { records, delta: pRecs.length - tRecs.length }
  }

  return { fields, field_groups }
}

export function buildDiff(sample: Sample): { diff: DiffNode; showDiff: boolean } {
  const target = sample.targets?.[TASK]
  const pred = sample.predictions?.[TASK]
  return { diff: diffNode(target, pred), showDiff: pred != null }
}

// ---- Leaf walk (shared by tree + lens) ----

export interface FlatLeaf {
  path: TargetPath
  status: LeafStatus
  field: Field           // the Field to ground on: target for match/mismatch/missing, pred for spurious
  target?: Field
  pred?: Field
}

export function flattenLeaves(diff: DiffNode, base: TargetPath = []): FlatLeaf[] {
  const out: FlatLeaf[] = []
  for (const [k, leaf] of Object.entries(diff.fields)) {
    const field = leaf.status === 'spurious' ? leaf.pred! : leaf.target!
    out.push({ path: [...base, 'fields', k], status: leaf.status, field, target: leaf.target, pred: leaf.pred })
  }
  for (const [g, group] of Object.entries(diff.field_groups)) {
    group.records.forEach((rec, i) => {
      out.push(...flattenLeaves(rec, [...base, 'field_groups', g, i]))
    })
  }
  return out
}

export function pathKey(path: TargetPath): string {
  return path.join('/')
}

export function pathEqual(a: TargetPath, b: TargetPath): boolean {
  return a.length === b.length && a.every((x, i) => x === b[i])
}
