// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS, MUTANTS, QUERY, baselineCapture, installBaselineControls } from './f04/baseline-build-fixture.mjs'

type Row = { s0: string, s1: string, same: boolean, rows: number, profiled: number, stocked: number, reasons: Record<string, number> }
type Case = { seed: number, defect: string | null, c: unknown }
const MODES = ['auto', 'force_custom_plan', 'force_generic_plan']
// One psql session per batch: plans are reused across the batch, so the
// predecessor and the linear form also meet the plan cache's generic plans.
async function run(db: any, cases: Case[], fn: string, mode: string): Promise<Row[]> {
  const rows = await db.query(`select public.bl_compare(x.value,${jsonArg(QUERY)},'${fn}','${mode}') r from jsonb_array_elements(${jsonArg(cases.map(k => k.c))}) with ordinality x order by x.ordinality`)
  return rows.map((row: { r: Row }) => row.r)
}

test('P19 baseline build equals its predecessor byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installBaselineControls(db, { mutants: Object.keys(MUTANTS) })
    const cases: Case[] = []
    for (let seed = 1; seed <= 20; seed++) for (const defect of DEFECTS)
      cases.push({ seed, defect, c: baselineCapture(seed, { products: 4 + seed % 6, stock: 40 + 5 * seed, sales: 10 + seed, defect }) })
    for (let seed = 101; seed <= 103; seed++) cases.push({ seed, defect: null, c: baselineCapture(seed, { products: 60, stock: 480, sales: 200 }) })
    let compared = 0, profiled = 0, stocked = 0
    const refusals = new Set<string>(), reasons: Record<string, number> = {}, first: Record<string, string[]> = {}
    for (const mode of MODES) for (let i = 0; i < cases.length; i += 25) {
      const batch = cases.slice(i, i + 25), rows = await run(db, batch, 'build', mode)
      rows.forEach((row, k) => {
        const { seed, defect } = batch[k]
        expect([mode, seed, defect, row.s1]).toEqual([mode, seed, defect, row.s0])
        if (mode === MODES[0]) (first[defect ?? 'VALID'] ??= []).push(row.s0)
        if (row.s0 !== 'NO_ERROR') { refusals.add(row.s0); return }
        expect([mode, seed, defect, row.same]).toEqual([mode, seed, defect, true])
        if (mode !== MODES[0]) return
        compared++; profiled += row.profiled; stocked += row.stocked
        for (const [kind, n] of Object.entries(row.reasons)) reasons[kind] = (reasons[kind] ?? 0) + n
      })
    }
    console.log(JSON.stringify({ cases: cases.length, modes: MODES.length, compared, profiled, stocked, reasons, refusals: [...refusals],
      refused_by: Object.fromEntries(Object.entries(first).map(([d, s]) => [d, [...new Set(s.filter(x => x !== 'NO_ERROR'))]]).filter(([, s]) => s.length)) }))
    const all = (d: string, s: string) => expect([d, first[d].every(x => x === s)]).toEqual([d, true])
    // Repeated profile/stock rows refuse only when a history row looks them up.
    all('PROFILE_REPEAT_USED', '21000:more than one row returned by a subquery used as an expression')
    all('STOCK_REPEAT_USED', '21000:more than one row returned by a subquery used as an expression')
    for (const d of ['PROFILE_REPEAT_UNUSED', 'STOCK_REPEAT_UNUSED', 'STOCK_ODD', 'STOCK_MISSING', 'PROFILES_MISSING', 'PROFILES_ODD', 'POLICIES_MISSING',
      'POLICY_MEMBERS_OBJECT', 'POLICY_MEMBERS_STRING', 'POLICY_MEMBERS_ODD', 'POLICY_OVERLAP', 'POLICY_NUMBER_MEMBERS', 'POLICY_ROWS_ODD']) all(d, 'NO_ERROR')
    // A non-array is refused at the row that first read it, and not at all without rows.
    all('PROFILES_OBJECT', '22023:cannot extract elements from an object'); all('PROFILES_SCALAR', '22023:cannot extract elements from a scalar')
    all('POLICIES_OBJECT', '22023:cannot extract elements from an object'); all('STOCK_OBJECT', '22023:cannot extract elements from an object')
    all('NO_ROWS_PROFILES_OBJECT', 'NO_ERROR')
    expect(compared).toBeGreaterThan(300); expect(profiled).toBeGreaterThan(1800); expect(stocked).toBeGreaterThan(1800)
    for (const kind of ['PRODUCTION_DISABLED_EXISTING_STOCK_STILL_SELLABLE', 'PRODUCTION_POLICY_UNREVIEWED_OR_IDENTITY_UNAVAILABLE', 'AUTHORITATIVE_WIP_MATCHING_CALENDAR_CAPACITY_NOT_CAPTURED'])
      expect([kind, (reasons[kind] ?? 0) > 300]).toEqual([kind, true])
    expect(refusals.size).toBeGreaterThan(4)
    // A deliberately wrong shortcut is caught by the same comparison.
    const caughtBy: Record<string, number> = {}
    for (const name of Object.keys(MUTANTS)) {
      let caught = 0
      for (let i = 0; i < cases.length && caught === 0; i += 25)
        caught += (await run(db, cases.slice(i, i + 25), `build_m_${name.toLowerCase()}`, 'auto')).filter(row => row.s1 !== row.s0 || (row.s0 === 'NO_ERROR' && !row.same)).length
      caughtBy[name] = caught
      expect([name, caught > 0]).toEqual([name, true])
    }
    console.log(JSON.stringify({ mutants_caught_in_first_failing_batch: caughtBy }))
  } finally { await db.close() }
}, 600_000)
