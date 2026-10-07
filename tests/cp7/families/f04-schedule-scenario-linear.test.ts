// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS, YIELD_DEFECTS, installScheduleControls, scheduleInput, yieldInput } from './f04/schedule-scenario-fixture.mjs'

test('P19 schedule scenario and project_yield equal their predecessors byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installScheduleControls(db)
    let compared = 0, scenarios = 0, known = 0
    const refusals = new Set<string>()
    for (let seed = 1; seed <= 30; seed++) for (const defect of DEFECTS) {
      const c = jsonArg(scheduleInput(seed, { positions: 6 + seed % 9, windows: 3 + seed % 7, defect, maxMinutes: seed % 2 ? 90 : 2 }))
      const row = (await db.query(`select public.sc_state('cp7_schedule_native.build_0',${c}) s0,public.sc_state('cp7_schedule_native.build',${c}) s1`))[0]
      expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
      if (row.s0 !== 'NO_ERROR') { refusals.add(row.s0.split(':')[1]); continue }
      // Separate statement: an immutable call on constants is folded even inside CASE.
      const out = (await db.query(`select cp7_schedule_native.build_0(${c},'{}')::text=cp7_schedule_native.build(${c},'{}')::text same,
        cp7_schedule_native.build(${c},'{}')->>'status' status,jsonb_array_length(jsonb_path_query_array(cp7_schedule_native.build(${c},'{}'),'$.etas[*] ? (@.result.status != "UNKNOWN")')) known`))[0]
      expect([seed, defect, out.same]).toEqual([seed, defect, true])
      compared++; if (out.status === 'SCENARIO') scenarios++; known += out.known
    }
    expect(compared).toBeGreaterThan(300); expect(scenarios).toBeGreaterThan(200); expect(known).toBeGreaterThan(500)
    for (const code of ['CP7_WIP_PCS', 'CP7_WIP_YIELD_POLICY', 'more than one row returned by a subquery used as an expression', 'CP7_WIP_TIMING_WINDOWS']) expect(refusals).toContain(code)
    let yielded = 0
    const yieldRefusals = new Set<string>()
    for (let seed = 1; seed <= 40; seed++) for (const defect of YIELD_DEFECTS) {
      const { positions, policies } = yieldInput(seed, { positions: 4 + seed % 12, defect }), p = jsonArg(positions), q = jsonArg(policies)
      const row = (await db.query(`select public.yd_state('cp7_wip.project_yield_0',${p},${q}) s0,public.yd_state('cp7_wip.project_yield',${p},${q}) s1`))[0]
      expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
      if (row.s0 !== 'NO_ERROR') { yieldRefusals.add(row.s0.split(':')[1]); continue }
      expect((await db.query(`select cp7_wip.project_yield_0(${p},${q})::text=cp7_wip.project_yield(${p},${q})::text same`))[0].same).toBe(true); yielded++
    }
    expect(yielded).toBeGreaterThan(40)
    for (const code of ['CP7_WIP_YIELD_DUPLICATE', 'CP7_WIP_YIELD_POLICY', 'CP7_WIP_KEY', 'cannot extract elements from an object']) expect(yieldRefusals).toContain(code)
  } finally { await db.close() }
}, 600_000)
