// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS, MUTANTS, TIMELINE_DEFECTS, installNettingControls, nettingInput, orderProbe, timelineInput } from './f04/netting-fixture.mjs'

type Row = { s0: string, s1: string, same: boolean, allocation: string | null, matches: Record<string, number>, edges: number, supplies: number, supply_events: number }
type Case = { seed: number, defect: string | null, c: unknown }
const MODES = ['auto', 'force_custom_plan', 'force_generic_plan']
// One psql session per batch: plans are reused across the batch, so the
// predecessor and the linear form also meet the plan cache's generic plans.
async function run(db: any, cases: Case[], fn: string, mode: string): Promise<Row[]> {
  const rows = await db.query(`select public.nt_compare(x.value,'${fn}','${mode}') r from jsonb_array_elements(${jsonArg(cases.map(k => k.c))}) with ordinality x order by x.ordinality`)
  return rows.map((row: { r: Row }) => row.r)
}

test('P19 netting build equals its predecessor byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installNettingControls(db, { mutants: Object.keys(MUTANTS) })
    const cases: Case[] = [{ seed: 0, defect: 'ORDER', c: orderProbe(false) }, { seed: 0, defect: 'ORDER_SWAPPED', c: orderProbe(true) }]
    for (let seed = 1; seed <= 20; seed++) for (const defect of DEFECTS) {
      // The predecessor spends seconds on 3660 forecast days; three suffice.
      if (defect === 'BIG_HORIZON' && seed % 8 !== 1) continue
      cases.push({ seed, defect, c: nettingInput(seed, { positions: 6 + seed % 13, targets: 3 + seed % 9, roots: 2 + seed % 5, models: 2 + seed % 3, complete: seed % 3 !== 1, defect }) })
    }
    let compared = 0, scenarios = 0, edges = 0, supplies = 0, events = 0
    const refusals = new Set<string>(), kinds: Record<string, number> = {}, seen: Row[] = []
    for (let i = 0; i < cases.length; i += 15) {
      const batch = cases.slice(i, i + 15), rows = await run(db, batch, 'build', MODES[(i / 15) % MODES.length])
      rows.forEach((row, k) => {
        const { seed, defect } = batch[k]
        seen.push(row)
        expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
        if (row.s0 !== 'NO_ERROR') { refusals.add(row.s0.split(':').slice(1).join(':')); return }
        expect([seed, defect, row.same]).toEqual([seed, defect, true])
        compared++; if (row.allocation === 'SCENARIO') scenarios++
        edges += row.edges; supplies += row.supplies; events += row.supply_events
        for (const [kind, n] of Object.entries(row.matches)) kinds[kind] = (kinds[kind] ?? 0) + n
      })
    }
    // The order probes: positions outer, targets inner, as the predecessor.
    expect([seen[0].s0, seen[1].s0]).toEqual(['22023:CP7_WIP_DUPLICATE_REF', '22023:CP7_WIP_KEY'])
    expect(compared).toBeGreaterThan(350); expect(scenarios).toBeGreaterThan(120)
    expect(edges).toBeGreaterThan(60); expect(supplies).toBeGreaterThan(450); expect(events).toBeGreaterThan(250)
    for (const kind of ['CONFIRMED_TARGET', 'CANDIDATE_MATCH', 'NEEDS_CHECK', 'INCOMPATIBLE', 'UNKNOWN']) expect(kinds[kind] ?? 0).toBeGreaterThan(20)
    for (const code of ['more than one row returned by a subquery used as an expression', 'CP7_NETTING_WORK_LIMIT', 'CP7_NETTING_MATCH_SOURCE_LIMIT',
      'CP7_NETTING_NATIVE_PRODUCT_MISSING', 'CP7_NETTING_NATIVE_SOURCE_SIZE', 'CP7_NETTING_TIMELINE_HORIZON_LIMIT', 'CP7_WIP_PCS', 'CP7_WIP_KEY',
      'CP7_WIP_REFS', 'CP7_WIP_DUPLICATE_REF', 'CP7_F04_DECIMAL', 'CP7_BASELINE_TARGET', 'CP7_BASELINE_ETA_BINDING', 'cannot extract elements from a scalar',
      'cannot extract elements from an object', 'invalid input syntax for type timestamp with time zone: "not-a-time"']) expect(refusals).toContain(code)
    // timeline() on its own, as any caller could use it, including ETA arrays
    // that build never passes (not an array, null, a repeated position).
    const lines: { seed: number, defect: string | null, v: unknown }[] = []
    for (let seed = 1; seed <= 25; seed++) for (const defect of TIMELINE_DEFECTS) lines.push({ seed, defect, v: timelineInput(seed, defect) })
    const timelines = await db.query(`select public.nt_timeline(x.value,'${MODES[1]}') r from jsonb_array_elements(${jsonArg(lines.map(k => k.v))}) with ordinality x order by x.ordinality`)
    const lineRefusals = new Set<string>()
    let lineSupplies = 0
    timelines.forEach(({ r: row }: { r: Row }, k: number) => {
      const { seed, defect } = lines[k]
      expect([seed, defect, row.s1]).toEqual([seed, defect, row.s0])
      if (row.s0 !== 'NO_ERROR') lineRefusals.add(row.s0.split(':').slice(1).join(':'))
      else { expect([seed, defect, row.same]).toEqual([seed, defect, true]); lineSupplies += row.supply_events }
    })
    expect(lineSupplies).toBeGreaterThan(50)
    for (const code of ['more than one row returned by a subquery used as an expression', 'CP7_F04_INSTANT_UTC', 'cannot extract elements from a scalar',
      'cannot extract elements from an object']) expect(lineRefusals).toContain(code)
    // A deliberately wrong lookup is caught by the same comparison.
    for (const name of Object.keys(MUTANTS)) {
      let caught = 0
      for (let i = 0; i < cases.length && caught === 0; i += 15)
        caught += (await run(db, cases.slice(i, i + 15), `build_m_${name.toLowerCase()}`, 'auto')).filter(row => row.s1 !== row.s0 || (row.s0 === 'NO_ERROR' && !row.same)).length
      expect([name, caught > 0]).toEqual([name, true])
    }
  } finally { await db.close() }
}, 600_000)
