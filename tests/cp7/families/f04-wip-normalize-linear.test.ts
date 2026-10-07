// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS, GRAPH_DEFECTS, PRODUCTION_DEFECTS, cuttingInput, graphInput, installWipControls, productionInput } from './f04/wip-normalize-fixture.mjs'

const outcome = (row: any) => (row.s0 === 'NO_ERROR' ? `${row.status}:${row.reason ?? ''}` : row.s0.split(':').slice(1).join(':'))

test('PL-8 linear cutting normalization, settle_bs, reconcile and production merge equal their predecessors byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installWipControls(db)
    const cmp = async (fn: string, v: unknown) => (await db.query(`select public.wn_cmp('${fn}_0','${fn}',${jsonArg(v)}) r`))[0].r
    let compared = 0, complete = 0, zero = 0
    const seen = new Set<string>()
    for (let seed = 1; seed <= 10; seed++) for (const defect of DEFECTS) {
      const c = cuttingInput(seed * 101 + DEFECTS.indexOf(defect), { groups: 4 + seed % 13, defect, ties: seed % 3 === 0, exhaustedGroups: seed % 4 })
      const row = await cmp('cp7_wip.normalize_cutting', c)
      expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
      expect([seed, defect, row.same]).toEqual([seed, defect, true])
      seen.add(outcome(row)); compared++
      if (row.status === 'COMPLETE') { complete++; zero += row.zero }
    }
    expect(compared).toBe(10 * DEFECTS.length); expect(complete).toBeGreaterThan(100); expect(zero).toBeGreaterThan(300)
    for (const code of ['UNKNOWN:CUTTING_NOT_POSTED', 'UNKNOWN:CUTTING_YIELDS_MISSING', 'CONFLICT:DELIVERY_SIZE_TOTAL_MISMATCH', 'CONFLICT:DELIVERY_BATCH_LINEAGE_UNPROVEN',
      'UNKNOWN:DELIVERY_EXACT_SIZE_UNPROVEN', 'CONFLICT:RECEIPT_SIZE_TOTAL_MISMATCH', 'CONFLICT:RECEIPT_DELIVERY_LINEAGE_MISMATCH', 'UNKNOWN:LEGACY_RECEIPT_CUSTODY_REQUIRES_RECONCILIATION',
      'CONFLICT:MISSING_STUCK_CLAIM_REQUIRES_DELIVERY_SOURCE', 'UNKNOWN:CLAIM_EXACT_SIZE_OR_SOURCE_UNPROVEN', 'CONFLICT:QC_RECEIPT_LINEAGE_MISMATCH', 'CONFLICT:QC_RECEIPT_PARENT_MISSING',
      'UNKNOWN:CANCELLED_BS_SOURCE_UNPROVEN', 'CONFLICT:BS_SOURCE_LINEAGE_MISMATCH', 'UNKNOWN:BS_EXACT_SIZE_UNPROVEN', 'UNKNOWN:REWORK_BS_SOURCE_UNPROVEN',
      'UNKNOWN:REWORK_COMPLETION_NOT_POSTED', 'CONFLICT:DISPOSITION_BS_SOURCE_UNPROVEN', 'UNKNOWN:DISPOSITION_TYPE_UNPROVEN', 'CONFLICT:DUPLICATE_BS_FG_DISPOSITION',
      'CONFLICT:BS_FG_DISPOSITION_MISMATCH', 'UNKNOWN:BS_HOLD_STATE_UNPROVEN', 'CONFLICT:BS_HOLD_QUANTITY_UNPROVEN', 'CONFLICT:REDISPATCH_RANGE_LINEAGE_CONFLICT',
      'CONFLICT:NEGATIVE_PREFIX', 'UNKNOWN:SOURCE_CAPTURE_INCOMPLETE', 'CP7_WIP_TRANSITION_QUANTITY', 'CP7_WIP_TRANSITION_NODE', 'CP7_WIP_KEY',
      'UNKNOWN:RECEIPT_EXACT_SIZE_UNPROVEN', 'CONFLICT:FAILED_ATTEMPT_IS_NOT_PHYSICAL_RECEIPT', 'CONFLICT:REWORK_COMPLETION_MISMATCH', 'CONFLICT:REWORK_RESOLUTION_LINEAGE_MISMATCH',
      'CONFLICT:CANCELLED_BS_SOURCE_UNPROVEN', 'cannot call jsonb_to_recordset on a non-array', 'invalid input syntax for type timestamp with time zone: "not-a-time"',
      'invalid input syntax for type numeric: "x1"', 'cannot extract elements from an object']) expect([...seen]).toContain(code)
    // reconcile on its own, with reversal events normalization never emits.
    const graphSeen = new Set<string>()
    let graphs = 0
    for (let seed = 1; seed <= 12; seed++) for (const defect of GRAPH_DEFECTS) {
      const row = await cmp('cp7_wip.reconcile', graphInput(seed * 37 + GRAPH_DEFECTS.indexOf(defect), { pools: 2 + seed % 7, defect }))
      expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
      expect([seed, defect, row.same]).toEqual([seed, defect, true])
      graphSeen.add(outcome(row)); if (row.status === 'COMPLETE') graphs++
    }
    expect(graphs).toBeGreaterThan(30)
    for (const code of ['CP7_WIP_POOL', 'CP7_WIP_NODE', 'CP7_WIP_EVENT', 'CP7_WIP_LINEAGE', 'CP7_WIP_REVERSAL', 'CP7_WIP_LIMIT', 'CP7_WIP_SHAPE', 'CP7_WIP_PCS', 'CP7_WIP_KEY',
      'CONFLICT:INPUT_EXCEEDS_ORIGIN', 'CONFLICT:NEGATIVE_PREFIX', 'UNKNOWN:ORIGIN_NOT_FULLY_ACCOUNTED', 'UNKNOWN:SOURCE_CAPTURE_INCOMPLETE']) expect([...graphSeen]).toContain(code)
    // The supply entry: cutting and opening/unsourced graphs merged and reconciled once.
    let merged = 0
    for (let seed = 1; seed <= 8; seed++) for (const defect of PRODUCTION_DEFECTS) {
      const row = await cmp('cp7_wip.normalize_production', productionInput(seed * 53 + PRODUCTION_DEFECTS.indexOf(defect), { groups: 3 + seed % 7, defect, exhaustedGroups: seed % 3 }))
      expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
      expect([seed, defect, row.same]).toEqual([seed, defect, true])
      if (row.status === 'COMPLETE') merged++
    }
    expect(merged).toBeGreaterThan(8)
    // One larger capture: many lifecycles plus spent groups on both laundry shapes.
    const big = await cmp('cp7_wip.normalize_production', productionInput(4242, { groups: 80, exhaustedGroups: 60, positionsPerSize: 4 }))
    expect([big.s0, big.s1, big.same, big.status]).toEqual(['NO_ERROR', 'NO_ERROR', true, 'COMPLETE'])
    expect(big.positions).toBeGreaterThan(400)
    // The comparison sees a real difference.
    const a = cuttingInput(3, { groups: 5 }), b = structuredClone(a); b.captured_at = '2026-10-07T03:00:01+00:00'
    expect((await db.query(`select cp7_wip.normalize_cutting_0(${jsonArg(a)})::text=cp7_wip.normalize_cutting(${jsonArg(b)})::text same`))[0].same).toBe(false)
  } finally { await db.close() }
}, 600_000)
