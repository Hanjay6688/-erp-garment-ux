// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { rng } from './f04/demand-history-fixture.mjs'

const refs = [{ kind: 'X', id: 'x', revision: '1' }]
const estimate = (total: number, days: number) => ({ contract_version: 'cp7.demand-estimate-input.v1', snapshot_id: 's', scope_id: 'sc', target_key: 't', size_id: 'z',
  minimum_own_available_days: '1', own: { available_total_pcs: String(total), available_days: String(days), capture_complete: true, refs }, analog: null, manual: null, refs })
const target = (daily: string, l: number, r: number, b: number) => ({ contract_version: 'cp7.target-input.v1', snapshot_id: 's', scope_id: 'sc', mode: 'DAYS', daily_mean: daily,
  lead_days: String(l), review_days: String(r), buffer_days: String(b), quantile: null, horizon_samples: [], refs })

// Self-check planning F1: a rate rounded up at 12 decimals made a whole horizon
// demand one piece too high under ceil(D*(L+R+B)) (20/30 over 30 days gave 21).
test('own-history target equals the exact ceil(total*(L+R+B)/days), never one piece more', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    const run = async (total: number, days: number, l: number, r: number, b: number) => {
      const e = await db.call('cp7_demand.estimate', [jsonArg(estimate(total, days))])
      return (await db.call('cp7_baseline.target', [jsonArg(target(e.daily_pcs, l, r, b))])).target_pcs
    }
    expect([await run(20, 30, 20, 10, 0), await run(2, 3, 2, 1, 0), await run(200, 30, 7, 7, 1)]).toEqual(['20', '2', '100'])
    const random = rng(19)
    for (let i = 0; i < 120; i++) {
      const total = Math.floor(random() * 500), days = 1 + Math.floor(random() * 60), l = Math.floor(random() * 30), r = 1 + Math.floor(random() * 20), b = Math.floor(random() * 10)
      const h = BigInt(l + r + b), exact = (BigInt(total) * h + BigInt(days) - 1n) / BigInt(days)
      expect([total, days, l, r, b, await run(total, days, l, r, b)]).toEqual([total, days, l, r, b, exact.toString()])
    }
  } finally { await db.close() }
}, 600_000)
