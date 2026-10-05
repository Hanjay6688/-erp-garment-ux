import { describe, expect, it } from 'vitest'
import { parseTransactionDependencies } from './transactionDependencies'

const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const source = { source_type: 'LAUNDRY_RECEIPT', source_id: id(1) }, actor = id(2)
const row = (n: number) => ({ source_type: 'QC_INSPECTION', source_id: id(n), number: `QC-${n}`, status: 'POSTED', revision: '1' })
function fixture(offset = 0, total = 26) {
  return { contract_version: 'cp7.transaction-dependencies.v1', actor_scope_id: actor, source,
    parent: { id: source.source_id, number: 'LR-001', status: 'POSTED', revision: '2' },
    page: { offset, limit: 25, total, has_more: offset + 25 < total },
    dependencies: Array.from({ length: Math.min(25, Math.max(0, total - offset)) }, (_, n) => row(100 + offset + n)),
    read_at: '2026-10-03T00:00:00.000001Z', business_DML: false }
}
describe('Current Native receipt-to-QC dependency contract', () => {
  it('accepts both complete pages and a confirmed empty list for the exact parent', () => {
    expect(parseTransactionDependencies(fixture(), source, actor, 0).dependencies).toHaveLength(25)
    const last = parseTransactionDependencies(fixture(25), source, actor, 25)
    expect(last.page).toEqual({ offset: 25, limit: 25, total: 26, has_more: false }); expect(last.dependencies[0].source_id).toBe(id(125))
    expect(parseTransactionDependencies(fixture(0, 0), source, actor, 0).dependencies).toEqual([])
  })
  it('refuses a different actor, parent, source family, revision or money added to an operational response', () => {
    for (const change of [
      (v: ReturnType<typeof fixture>) => { v.actor_scope_id = id(3) },
      (v: ReturnType<typeof fixture>) => { v.parent.id = id(3) },
      (v: ReturnType<typeof fixture>) => { v.source = { ...source, source_type: 'LAUNDRY_DELIVERY' } },
      (v: ReturnType<typeof fixture>) => { v.parent.revision = '9223372036854775808' },
      (v: ReturnType<typeof fixture>) => { Object.assign(v.dependencies[0], { actual_cost: 100 }) },
      (v: ReturnType<typeof fixture>) => { v.business_DML = true },
    ]) { const value = structuredClone(fixture()); change(value); expect(() => parseTransactionDependencies(value, source, actor, 0)).toThrow() }
  })
  it('refuses hidden truncation, a duplicate QC, a reversed dependency or an incorrect page continuation', () => {
    for (const change of [
      (v: ReturnType<typeof fixture>) => { v.dependencies.pop() },
      (v: ReturnType<typeof fixture>) => { v.dependencies[1] = { ...v.dependencies[0] } },
      (v: ReturnType<typeof fixture>) => { v.dependencies[0].status = 'REVERSED' },
      (v: ReturnType<typeof fixture>) => { v.page.has_more = false },
      (v: ReturnType<typeof fixture>) => { v.page.offset = 25 },
      (v: ReturnType<typeof fixture>) => { v.page.total = -1 },
    ]) { const value = fixture(); change(value); expect(() => parseTransactionDependencies(value, source, actor, 0)).toThrow() }
  })
})
