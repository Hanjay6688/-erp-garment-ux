// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { capture, installBuildControls } from './f04/history-build-fixture.mjs'

test('P19 history_build with per-root sums equals its predecessor byte for byte, including the reservation refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installBuildControls(db)
    let compared = 0, refused = 0
    for (let seed = 1; seed <= 30; seed++) for (const shape of [{ products: 1, stock: 3, sales: 0 }, { products: 6, stock: 60 }, { products: 9, stock: 120, mismatch: seed % 3 === 0 }]) {
      const c = jsonArg(capture(seed, shape)), q = jsonArg({ from_date: '2026-05-01', through_date: '2026-05-30', group_mode: seed % 2 ? 'AS_SOLD' : 'RESTATED' })
      const row = (await db.query(`select public.hb_state('cp7_planning.history_build_0',${c},${q}) s0,public.hb_state('cp7_planning.history_build',${c},${q}) s1`))[0]
      expect([seed, row.s1]).toEqual([seed, row.s0])
      if (row.s0 === 'NO_ERROR') { expect((await db.query(`select cp7_planning.history_build_0(${c},${q})::text=cp7_planning.history_build(${c},${q})::text same`))[0].same).toBe(true); compared++ } else refused++
    }
    expect(compared).toBeGreaterThan(50); expect(refused).toBeGreaterThan(0)
  } finally { await db.close() }
}, 600_000)
