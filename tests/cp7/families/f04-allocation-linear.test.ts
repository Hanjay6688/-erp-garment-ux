// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS, MUTANTS, allocationInput, installAllocationControls, memoProbe } from './f04/allocation-fixture.mjs'

type Row = { s0: string, s1: string, same: boolean, status: string | null, rows: number, edges: Record<string, number>, reviews: Record<string, number> }
type Case = { seed: number, defect: string | null, v: unknown }
const MODES = ['auto', 'force_custom_plan', 'force_generic_plan']
// One psql session per batch: plans are reused across the batch, so the
// predecessor and the linear form also meet the plan cache's generic plans.
async function run(db: any, cases: Case[], fn: string, mode: string): Promise<Row[]> {
  const rows = await db.query(`select public.al_compare(x.value,'${fn}','${mode}') r from jsonb_array_elements(${jsonArg(cases.map(k => k.v))}) with ordinality x order by x.ordinality`)
  return rows.map((row: { r: Row }) => row.r)
}

test('P19 allocation equals its predecessor byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installAllocationControls(db, { mutants: Object.keys(MUTANTS) })
    const cases: Case[] = [null, 'BAD_SOURCE', 'BAD_TARGET'].map(variant => ({ seed: 0, defect: `MEMO_PROBE_${variant ?? 'VALID'}`, v: memoProbe(variant) }))
    for (let seed = 1; seed <= 20; seed++) for (const defect of DEFECTS)
      cases.push({ seed, defect, v: allocationInput(seed, { positions: 6 + seed % 17, targets: 3 + seed % 13, pools: 2 + seed % 4, ties: seed % 5 === 0, defect }) })
    for (let seed = 101; seed <= 104; seed++) cases.push({ seed, defect: null, v: allocationInput(seed, { positions: 60, targets: 80, pools: 12, ties: seed === 104 }) })
    let compared = 0, scenarios = 0
    const refusals = new Set<string>(), edges: Record<string, number> = {}, reviews: Record<string, number> = {}, first: Row[] = []
    // Every case under each plan cache mode.
    for (const mode of MODES) for (let i = 0; i < cases.length; i += 40) {
      const batch = cases.slice(i, i + 40), rows = await run(db, batch, 'allocate', mode)
      rows.forEach((row, k) => {
        const { seed, defect } = batch[k]
        if (mode === MODES[0]) first.push(row)
        expect([mode, seed, defect, row.s1]).toEqual([mode, seed, defect, row.s0])
        if (row.s0 !== 'NO_ERROR') { refusals.add(row.s0); return }
        expect([mode, seed, defect, row.same]).toEqual([mode, seed, defect, true])
        if (mode !== MODES[0]) return
        compared++; if (row.status === 'SCENARIO') scenarios++
        for (const [kind, n] of Object.entries(row.edges)) edges[kind] = (edges[kind] ?? 0) + n
        for (const [kind, n] of Object.entries(row.reviews)) reviews[kind] = (reviews[kind] ?? 0) + n
      })
    }
    console.log(JSON.stringify({ cases: cases.length, modes: MODES.length, compared, scenarios, edges, reviews, refusals: [...refusals] }))
    // The probes: a source or target with an earlier pair's facts but invalid
    // refs refuses at its own first pair instead of reusing that verdict.
    expect(first.slice(0, 3).map(row => row.s0)).toEqual(['NO_ERROR', '22023:CP7_WIP_DUPLICATE_REF', '22023:CP7_WIP_DUPLICATE_REF'])
    expect(compared).toBeGreaterThan(350); expect(scenarios).toBeGreaterThan(280)
    expect(edges.CANDIDATE_MATCH ?? 0).toBeGreaterThan(150); expect(edges.CONFIRMED_TARGET ?? 0).toBeGreaterThan(60)
    for (const kind of ['TIME_UNKNOWN', 'ETA_OR_YIELD_UNKNOWN', 'UNKNOWN', 'INCOMPATIBLE', 'NEEDS_CHECK']) expect(reviews[kind] ?? 0).toBeGreaterThan(300)
    for (const code of ['P0001:CP7_BASELINE_SCOPE', '22023:CP7_WIP_PCS', 'P0001:CP7_F04_CONTRACT', '22023:CP7_WIP_FIELDS', 'P0001:CP7_BASELINE_MATCH_SNAPSHOT',
      'P0001:CP7_WIP_MATCH_DUPLICATE', '22023:CP7_WIP_KEY', 'P0001:CP7_F04_ARRAY_LIMIT', 'P0001:CP7_BASELINE_ALLOCATION_LIMIT', 'P0001:CP7_BASELINE_DUPLICATE_POOL',
      'P0001:CP7_BASELINE_POSITION', 'P0001:CP7_BASELINE_YIELD', '22023:CP7_WIP_REFS', '22023:CP7_WIP_DUPLICATE_REF', 'P0001:CP7_BASELINE_ETA_BINDING',
      'P0001:CP7_F04_INSTANT_UTC', '22008:date/time field value out of range: "2026-13-01"', 'P0001:CP7_BASELINE_TARGET', 'P0001:CP7_BASELINE_TARGET_MATCH_BINDING',
      'P0001:CP7_BASELINE_SOURCE_MATCH_BINDING', 'P0001:CP7_WIP_QUALITY', 'P0001:CP7_WIP_CONSTRAINT', 'P0001:CP7_WIP_MATCH_BINDING',
      '22023:cannot extract elements from a scalar']) expect(refusals).toContain(code)
    // A deliberately wrong shortcut is caught by the same comparison.
    const caughtBy: Record<string, number> = {}
    for (const name of Object.keys(MUTANTS)) {
      let caught = 0
      for (let i = 0; i < cases.length && caught === 0; i += 40)
        caught += (await run(db, cases.slice(i, i + 40), `allocate_m_${name.toLowerCase()}`, 'auto')).filter(row => row.s1 !== row.s0 || (row.s0 === 'NO_ERROR' && !row.same)).length
      caughtBy[name] = caught
      expect([name, caught > 0]).toEqual([name, true])
    }
    console.log(JSON.stringify({ mutants_caught_in_first_failing_batch: caughtBy }))
  } finally { await db.close() }
}, 600_000)
