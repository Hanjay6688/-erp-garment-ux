// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { MUTANTS, defects, demandInput, installHistoryControls, installHistoryMutants } from './f04/demand-history-fixture.mjs'

async function compare(db: any, v: unknown) {
  // Immutable calls with constant arguments are folded at plan time, so the
  // byte comparison runs only after both state probes report no refusal.
  const arg = jsonArg(v)
  const row = (await db.query(`select public.dh_state('cp7_demand.history_0',${arg}) s0,public.dh_state('cp7_demand.history',${arg}) s1`))[0]
  if (row.s0 === 'NO_ERROR' && row.s1 === 'NO_ERROR') row.same = (await db.query(`select cp7_demand.history_0(${arg})::text=cp7_demand.history(${arg})::text same`))[0].same
  return row
}

test('P19 linear demand-1 history equals the predecessor byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installHistoryControls(db)
    let compared = 0, refused = 0
    for (let seed = 1; seed <= 40; seed++) {
      for (const shape of [{ targets: 1, days: 1, events: 0 }, { targets: 4, days: 9, events: 30 }, { targets: 7, days: 25, events: 90, availability: 0.9 }]) {
        const row = await compare(db, demandInput(seed, shape))
        expect([seed, shape.events, row.s1]).toEqual([seed, shape.events, row.s0])
        if (row.s0 === 'NO_ERROR') { expect(row.same).toBe(true); compared++ } else refused++
      }
      for (const defect of defects) {
        const row = await compare(db, demandInput(seed * 31 + defects.indexOf(defect), { targets: 5, days: 12, events: 40, defect }))
        expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
        if (row.s0 === 'NO_ERROR') { expect(row.same).toBe(true); compared++ } else refused++
      }
    }
    expect(compared).toBeGreaterThan(100); expect(refused).toBeGreaterThan(200)
    // The comparison sees a real difference.
    const a = demandInput(3, { targets: 3, days: 5, events: 12 }), b = structuredClone(a); b.snapshot_id = 'other'
    expect((await db.query(`select cp7_demand.history_0(${jsonArg(a)})::text=cp7_demand.history(${jsonArg(b)})::text same`))[0].same).toBe(false)
    // A loosened availability fast path is caught by the same defect inputs.
    await installHistoryMutants(db)
    for (const name of Object.keys(MUTANTS)) {
      let caught = 0
      for (let seed = 1; seed <= 40 && caught === 0; seed++) for (const defect of defects) {
        const arg = jsonArg(demandInput(seed * 31 + defects.indexOf(defect), { targets: 5, days: 12, events: 40, defect }))
        const row = (await db.query(`select public.dh_state('cp7_demand.history_0',${arg}) s0,public.dh_state('cp7_demand.history_m_${name.toLowerCase()}',${arg}) s1`))[0]
        if (row.s0 !== row.s1) caught++
      }
      expect([name, caught > 0]).toEqual([name, true])
    }
  } finally { await db.close() }
}, 600_000)
