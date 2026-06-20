// viewer/src/diff.test.ts
import { expect, test } from 'vitest'
import type { Field, Node } from './types'
import { buildDiff, diffNode, flattenLeaves, pathKey } from './diff'

const f = (value: string, word_ids: number[], cell = 0): Field => ({ value, word_ids, cell })

test('match: same word_ids', () => {
  const t: Node = { fields: { a: f('x', [1, 2]) }, field_groups: {} }
  const p: Node = { fields: { a: f('x', [2, 1]) }, field_groups: {} }   // set-equal
  expect(diffNode(t, p).fields.a.status).toBe('match')
})

test('mismatch: different word_ids', () => {
  const t: Node = { fields: { a: f('x', [1, 2]) }, field_groups: {} }
  const p: Node = { fields: { a: f('y', [3]) }, field_groups: {} }
  const leaf = diffNode(t, p).fields.a
  expect(leaf.status).toBe('mismatch')
  expect(leaf.target?.value).toBe('x')
  expect(leaf.pred?.value).toBe('y')
})

test('missing: leaf in target only', () => {
  const t: Node = { fields: { a: f('x', [1]) }, field_groups: {} }
  const p: Node = { fields: {}, field_groups: {} }
  expect(diffNode(t, p).fields.a.status).toBe('missing')
})

test('spurious: leaf in prediction only', () => {
  const t: Node = { fields: {}, field_groups: {} }
  const p: Node = { fields: { a: f('x', [1]) }, field_groups: {} }
  expect(diffNode(t, p).fields.a.status).toBe('spurious')
})

test('record cardinality delta: pred shorter', () => {
  const rec = (): Node => ({ fields: { a: f('x', [1]) }, field_groups: {} })
  const t: Node = { fields: {}, field_groups: { g: [rec(), rec()] } }
  const p: Node = { fields: {}, field_groups: { g: [rec()] } }
  const d = diffNode(t, p)
  expect(d.field_groups.g.delta).toBe(-1)
  expect(d.field_groups.g.records).toHaveLength(2)        // aligned to the longer side
  expect(d.field_groups.g.records[1].fields.a.status).toBe('missing')  // unmatched target record
})

test('buildDiff: no predictions → showDiff false but tree present', () => {
  const sample = { targets: { extraction: { fields: { a: f('x', [1]) }, field_groups: {} } } } as never
  const { diff, showDiff } = buildDiff(sample)
  expect(showDiff).toBe(false)
  expect(Object.keys(diff.fields)).toEqual(['a'])
})

test('flattenLeaves: paths and grounding field', () => {
  const t: Node = {
    fields: { g0: f('G', [9]) },
    field_groups: { line: [{ fields: { a: f('x', [1]) }, field_groups: {} }] },
  }
  const leaves = flattenLeaves(diffNode(t, undefined))
  const keys = leaves.map(l => pathKey(l.path))
  expect(keys).toContain('fields/g0')
  expect(keys).toContain('field_groups/line/0/fields/a')
  const a = leaves.find(l => pathKey(l.path) === 'field_groups/line/0/fields/a')!
  expect(a.field.word_ids).toEqual([1])   // grounds on target Field
})
