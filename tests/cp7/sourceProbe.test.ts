import { expect, it } from 'vitest'
import { parseSourceProbe } from './sourceProbeContract'

const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const at = '2026-09-29T03:00:00.123456+07:00'
const earlier = '2026-09-28T10:00:00+07:00'

// Owner oracle O15/X07 prerequisites: one root, two physical child yields and
// a pending cost. These are facts only; no production gap/stock formula here.
const example = () => ({
  contract_version: 'cp7.source-probe.v1', status: 'COMPLETE',
  scope: { root_id: id(1), exact_size_id: id(2), commercial_status: 'LEGACY_UNMAPPED' },
  snapshot: { effective_as_of: at, known_as_of: at, generated_at: at,
    knowledge_mode: 'CURRENT', time_zone: 'Asia/Jakarta',
    completeness_proven_only_for: 'SOURCE_PROBE_SIX_DOMAINS' },
  counts: { physical: 1, commercial: 0, cutting_candidates: 2,
    stock_movements: 1, sales_lines: 1, lot_cost: 1 },
  sources: {
    physical: [{ product_id: id(1), root_id: id(1), size_id: id(2), model_id: id(3),
      brand_id: id(4), effective_from: earlier }],
    commercial: [],
    cutting_candidates: [5, 6].map((n) => ({ source_key: `CUTTING_YIELD:${id(n)}`,
      yield_id: id(n), cutting_group_id: id(n + 10), po_id: id(n + 20),
      slot_id: id(n + 30), size_id: id(2), pattern_id: null, pattern_revision: null,
      group_revision: '1', cut_at: earlier, cut_qty_pcs: n === 5 ? '7' : '3',
      match: 'UNBOUND_CANDIDATE' })),
    stock_movements: [{ source_key: `FG_MOVEMENT:${id(7)}`, product_id: id(1),
      lot_id: id(8), location_id: id(9), quality_grade: 'GRADE_A',
      qty_signed_pcs: '9', physical_at: earlier, system_created_at: earlier,
      reversal_of_id: null }],
    sales_lines: [{ source_key: `SALE_LINE:${id(10)}`, sale_id: id(11),
      product_id: id(1), status: 'DRAFT', header_revision: '1',
      sale_date: earlier, created_at: earlier, qty_pcs: '2' }],
    lot_cost: [{ source_key: `LOT_COST:${id(8)}`, lot_id: id(8), product_id: id(1),
      produced_at: earlier, hpp_version_id: null, hpp_revision: null,
      calculated_at: null, cost_state: null,
      valuation: { state: 'UNKNOWN', reason: 'PENDING_COST_OR_NO_HPP' } }],
  },
  snapshot_hash: 'a'.repeat(64),
})

it('accepts only complete, separate physical facts with explicitly unknown cost', () => {
  const input = example()
  const result = parseSourceProbe(input)
  expect(result.sources.cutting_candidates.map(row => row.cut_qty_pcs)).toEqual(['7', '3'])
  expect(result.sources.cutting_candidates.every(row => row.match === 'UNBOUND_CANDIDATE')).toBe(true)
  expect(result.sources.lot_cost[0].valuation).toEqual({ state: 'UNKNOWN', reason: 'PENDING_COST_OR_NO_HPP' })
  expect(result).not.toBe(input)
  expect(input.sources.stock_movements[0].qty_signed_pcs).toBe('9')
})

it.each(['0.5', '-1', 'NaN', '9007199254740993.01'])(
  'rejects invalid physical PCS %s without rounding or substituting zero', quantity => {
    const input = example()
    input.sources.cutting_candidates[0].cut_qty_pcs = quantity
    expect(() => parseSourceProbe(input)).toThrow('COUNT')
  },
)

it('allows signed movement and exact money from a recorded HPP version', () => {
  const input = example()
  input.sources.stock_movements[0].qty_signed_pcs = '-3'
  input.sources.lot_cost[0].hpp_version_id = id(15)
  input.sources.lot_cost[0].hpp_revision = '2'
  input.sources.lot_cost[0].cost_state = 'FINAL'
  const cost = input.sources.lot_cost[0] as typeof input.sources.lot_cost[number] & { valuation: unknown }
  cost.valuation = { state: 'KNOWN', value: '-42.123456', unit: 'IDR' }
  expect(parseSourceProbe(input).sources.lot_cost[0].valuation).toEqual(cost.valuation)
  cost.valuation = { state: 'KNOWN', value: '42.1234567', unit: 'IDR' }
  expect(() => parseSourceProbe(input)).toThrow('MONEY')
})

it('never converts a missing or partial source page into an empty success', () => {
  const partial = example(); partial.counts.sales_lines = 2
  expect(() => parseSourceProbe(partial)).toThrow('PARTIAL_PAGE')
  const incomplete = example(); incomplete.status = 'INCOMPLETE'
  expect(() => parseSourceProbe(incomplete)).toThrow('INCOMPLETE')
  const noPhysical = example(); noPhysical.sources.physical = []; noPhysical.counts.physical = 0
  expect(() => parseSourceProbe(noPhysical)).toThrow('SCOPE_COUNT')
})

it('blocks cross-size candidate, duplicate source and invented SKU membership', () => {
  const cross = example(); cross.sources.cutting_candidates[1].size_id = id(30)
  expect(() => parseSourceProbe(cross)).toThrow('CANDIDATE_LINEAGE')
  const duplicate = example()
  duplicate.sources.cutting_candidates[1].source_key = duplicate.sources.cutting_candidates[0].source_key
  duplicate.sources.cutting_candidates[1].yield_id = duplicate.sources.cutting_candidates[0].yield_id
  expect(() => parseSourceProbe(duplicate)).toThrow('DUPLICATE_SOURCE')
  const fake = example(); fake.scope.commercial_status = 'BOUND'
  expect(() => parseSourceProbe(fake)).toThrow('SCOPE_COUNT')
})

it('rejects future knowledge, including a microsecond after the snapshot', () => {
  const input = example()
  input.sources.stock_movements[0].system_created_at = '2026-09-29T03:00:00.123457+07:00'
  expect(() => parseSourceProbe(input)).toThrow('FUTURE_KNOWLEDGE')
  const future = example(); future.sources.cutting_candidates[0].cut_at = '2026-09-29T03:00:00.123457+07:00'
  expect(() => parseSourceProbe(future)).toThrow('FUTURE_EFFECTIVE_FACT')
})

it('rejects hidden extra financial fields and fabricated Rp0 on pending cost', () => {
  const extra = example()
  Object.assign(extra.sources.sales_lines[0], { private_margin: '9000000.00' })
  expect(() => parseSourceProbe(extra)).toThrow('FIELDS')
  const fakeZero = example()
  Object.assign(fakeZero.sources.lot_cost[0].valuation, { value: '0' })
  expect(() => parseSourceProbe(fakeZero)).toThrow('FIELDS')
})
