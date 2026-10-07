// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { ACCESS, SCENARIO_DEFECTS, applyMutant, installScenarioControls, query, scenarioCapture } from './f04/staged-scenario-fixture.mjs'

// P19 phase B: the staged job's SCENARIO is the real chain, in units
// (HIST_PREP, HIST_EVENTS, HIST_VALIDATE, HIST_ROWS, HIST_STOCK, BASE_ROWS,
// SUPPLY, SCENARIO), and the whole job equals the single analysis build byte
// for byte; the assembled scenario equals cp7_schedule_native.build; every
// refusal is the single path's first refusal (SQLSTATE and message). Tiny
// bounds put chunk edges everywhere. Generated captures, LOCAL kernel proof.
const SMALL = { targets_per_chunk: 7, pairs_per_chunk: 45, visits_per_allocation_step: 100000, allocation_targets_per_step: 4, targets_per_segment_unit: 10,
  job_targets: 5000, job_pairs: 1000000, job_matching_products: 10000, history_cells_per_unit: 37, sales_per_events_unit: 7, targets_per_stock_unit: 5, job_history_cells: 500000 }
const SHAPES = [{ targets: 14, days: 6, groups: 4, reviewed: false }, { targets: 20, days: 3, groups: 5, reviewed: true },
  { targets: 9, days: 1, groups: 3, reviewed: true }, { targets: 30, days: 9, groups: 6, reviewed: false }]
type Row = Record<string, any>
type Case = { seed: number, defect: string | null, c: unknown, q: unknown }
const uuid = (n: number) => `03000000-0000-4000-8000-${n.toString(16).padStart(12, '0')}`
const ALL = Object.values(SCENARIO_DEFECTS).flat() as string[]

// The job and the single chain on each case, server side, in batches.
async function compare(db: any, cases: Case[], base: number) {
  const out: Row[] = []
  for (let i = 0; i < cases.length; i += 8) {
    const batch = cases.slice(i, i + 8)
    const rows = await db.query(`select public.ss_case(public.ss_complete(x.value->'c',(x.value->>'seed')::integer,x.value->>'defect'),x.value->'q',
      ('03000000-0000-4000-8000-'||lpad(to_hex(${base + i}+x.ordinality::integer),12,'0'))::uuid,${jsonArg(ACCESS)}) r
      from jsonb_array_elements(${jsonArg(batch)}) with ordinality x order by x.ordinality`)
    rows.forEach((r: Row, k: number) => out.push({ ...r.r, seed: batch[k].seed, defect: batch[k].defect }))
  }
  return out
}
const identical = (r: Row) => r.single === 'DONE' && r.job === 'DONE' && r.bad?.length===0 && r.same && r.text_same && r.document_same && r.scenario_same && r.netting_rows_same
  && r.match_results_same && r.allocation_same && r.fabric_plan_same !== false
const sameRefusal = (r: Row) => r.single === 'REFUSED' && r.job === 'FAILED' && r.failure?.sqlstate === r.single_sqlstate && r.failure?.message === r.single_message
  && (r.scenario_state === 'DONE' ? true : r.scenario_sqlstate === r.single_sqlstate && r.scenario_message === r.single_message)

test('P19 staged scenario units equal the single chain byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installScenarioControls(db, { bounds: SMALL })
    const cases: Case[] = []
    for (let seed = 1; seed <= 3; seed++) for (const defect of ALL) {
      const shape = SHAPES[(seed + cases.length) % SHAPES.length], { c, q } = scenarioCapture(seed * 31 + cases.length, shape, defect)
      cases.push({ seed: seed * 31 + cases.length, defect, c, q })
    }
    for (let seed = 400; seed < 448; seed++) { const { c, q } = scenarioCapture(seed, SHAPES[seed % SHAPES.length]); cases.push({ seed, defect: null, c, q }) }
    const rows = await compare(db, cases, 0)
    const refusals = new Map<string, Set<string>>(), stats = { cases: rows.length, done: 0, refused: 0, allocated: 0, edges: 0, confirmed: 0, candidates: 0,
      fabric_numbers: 0, accessory_rows: 0, events_unclean_done: 0, availability_unclean_done: 0, multi: {} as Record<string, number> }
    for (const r of rows) {
      const id = [r.seed, r.defect]
      if (r.single === 'DONE') {
        expect([...id, r.job, r.same, r.text_same, r.document_same, r.scenario_same, r.netting_rows_same, r.match_results_same, r.allocation_same, r.fabric_plan_same])
          .toEqual([...id, 'DONE', true, true, true, true, true, true, true, true])
        expect([...id,r.bad]).toEqual([...id,[]])
        stats.done++; if (r.allocation === 'SCENARIO') stats.allocated++
        stats.edges += r.edges; stats.confirmed += r.confirmed; stats.candidates += r.candidates; stats.fabric_numbers += r.fabric_numbers; stats.accessory_rows += r.accessory_rows
        if (r.events_clean === false) stats.events_unclean_done++
        if (r.availability_clean === false) stats.availability_unclean_done++
        for (const [k, n] of Object.entries(r.units as Record<string, number>)) if (n > 1) stats.multi[k] = (stats.multi[k] ?? 0) + 1
      } else {
        // The single path's first refusal, at the unit that runs its statement.
        expect([...id, r.job, r.failure?.sqlstate, r.failure?.message]).toEqual([...id, 'FAILED', r.single_sqlstate, r.single_message])
        if (r.scenario_state === 'REFUSED') expect([...id, r.scenario_sqlstate, r.scenario_message]).toEqual([...id, r.single_sqlstate, r.single_message])
        stats.refused++
        const unit = r.failed_kind as string
        if (!refusals.has(unit)) refusals.set(unit, new Set())
        refusals.get(unit)!.add(`${r.single_sqlstate}:${r.single_message}`)
      }
    }
    const byUnit = Object.fromEntries([...refusals].map(([k, v]) => [k, [...v]]))
    console.log(JSON.stringify({ ...stats, refusals_by_unit: byUnit, distinct_refusals: [...refusals.values()].reduce((n, s) => n + s.size, 0) }))
    // Every scenario family refuses somewhere, and so do the later stages.
    for (const unit of ['HIST_PREP', 'HIST_VALIDATE', 'HIST_STOCK', 'BASE_ROWS', 'SUPPLY', 'SCENARIO', 'NET_PREP', 'ANA_TARGETS']) expect(refusals.has(unit), unit).toBe(true)
    for (const code of ['P0001:CP7_PLANNING_CAPTURE_INCOMPLETE', 'P0001:CP7_F04_INSTANT_UTC', 'P0001:CP7_DEMAND_COMPLETE_DAYS_REQUIRED', 'P0001:CP7_DEMAND_POLICY',
      '22007:invalid input syntax for type timestamp with time zone: "not-a-time"', '22P02:invalid input syntax for type numeric: "1x"'])
      expect(refusals.get('HIST_PREP')).toContain(code)
    for (const code of ['P0001:CP7_DEMAND_DUPLICATE_TARGET', '22023:CP7_WIP_KEY', 'P0001:CP7_DEMAND_REVISION_CONFLICT', 'P0001:CP7_DEMAND_TARGET_SIZE', 'P0001:CP7_DEMAND_LIFECYCLE'])
      expect(refusals.get('HIST_VALIDATE')).toContain(code)
    for (const code of ['P0001:CP7_PLANNING_NATIVE_RESERVATION_MISMATCH', '22023:CP7_WIP_PCS']) expect(refusals.get('HIST_STOCK')).toContain(code)
    for (const code of ['21000:more than one row returned by a subquery used as an expression', '22023:cannot extract elements from a scalar', 'P0001:CP7_DEMAND_MINIMUM_DAYS', '22023:CP7_F04_DECIMAL'])
      expect(refusals.get('BASE_ROWS')).toContain(code)
    expect(refusals.get('SCENARIO')).toContain('P0001:CP7_WIP_YIELD_POLICY')
    expect(refusals.get('SCENARIO')).toContain('21000:more than one row returned by a subquery used as an expression')
    expect(stats.done).toBeGreaterThanOrEqual(95); expect(stats.allocated).toBeGreaterThanOrEqual(20); expect(stats.edges).toBeGreaterThan(10)
    expect(stats.confirmed).toBeGreaterThan(50); expect(stats.candidates).toBeGreaterThan(20); expect(stats.fabric_numbers).toBeGreaterThan(20); expect(stats.accessory_rows).toBeGreaterThan(500)
    expect(stats.events_unclean_done).toBeGreaterThanOrEqual(2); expect(stats.availability_unclean_done).toBeGreaterThanOrEqual(2)
    for (const k of ['HIST_EVENTS', 'HIST_ROWS', 'HIST_STOCK', 'BASE_ROWS', 'NET_TARGETS', 'NET_PAIRS', 'ALLOC_STEP', 'ANA_TARGETS']) expect(stats.multi[k] ?? 0, k).toBeGreaterThanOrEqual(20)
  } finally { await db.close() }
}, 3_600_000)

test('P19 staged scenario: single-call caps are job bounds that refuse loudly; the two intended differences', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installScenarioControls(db, { bounds: { ...SMALL, targets_per_chunk: 250, history_cells_per_unit: 12500, sales_per_events_unit: 2500, targets_per_stock_unit: 1000,
      pairs_per_chunk: 100000, allocation_targets_per_step: 1000, targets_per_segment_unit: 1000 } })
    const long = (days: number) => ({ ...query(days) })
    const cases: Case[] = []
    // 1001 targets x 1 day: the single call's DEMAND_ARRAYS cap (targets 1000).
    { const { c, q } = scenarioCapture(901, { targets: 1001, days: 1, sales: 1, stock: 1, groups: 3, reviewed: true }); cases.push({ seed: 901, defect: 'CAP_TARGETS_1001', c, q }) }
    // 40 targets x 2600 days = 104000 cells: the single call's grid cap 100000.
    { const { c } = scenarioCapture(902, { targets: 40, days: 30, groups: 3, reviewed: true }); cases.push({ seed: 902, defect: 'CAP_GRID_104000', c, q: long(2600) }) }
    // Job bounds: 5001 targets; 200 x 2600 = 520000 cells > 500000.
    { const { c, q } = scenarioCapture(903, { targets: 5001, days: 1, sales: 0, stock: 0, groups: 1 }); cases.push({ seed: 903, defect: 'JOB_TARGETS_5001', c, q }) }
    { const { c } = scenarioCapture(904, { targets: 200, days: 30, sales: 1, stock: 1, groups: 1 }); cases.push({ seed: 904, defect: 'JOB_CELLS_520000', c, q: long(2600) }) }
    const rows = await compare(db, cases, 0x900)
    const by = Object.fromEntries(rows.map(r => [r.defect, r]))
    console.log(JSON.stringify(rows.map(r => ({ defect: r.defect, job: r.job, failure: r.failure, single: r.single, single_message: r.single_message, scenario_state: r.scenario_state, units: r.units }))))
    // Intended differences: the single call refuses at its cap, the job (bounds 5000 targets, 500000 cells) completes.
    expect([by.CAP_TARGETS_1001.single, by.CAP_TARGETS_1001.single_message, by.CAP_TARGETS_1001.job]).toEqual(['REFUSED', 'CP7_F04_ARRAY_LIMIT', 'DONE'])
    expect([by.CAP_GRID_104000.single, by.CAP_GRID_104000.single_message, by.CAP_GRID_104000.job]).toEqual(['REFUSED', 'CP7_PLANNING_HISTORY_GRID_LIMIT', 'DONE'])
    // Complete: every target has its history row and its netting row.
    for (const [k, n] of [['CAP_TARGETS_1001', 1001], ['CAP_GRID_104000', 40]] as const) expect([k, by[k].history_rows, by[k].rows]).toEqual([k, n, n])
    // Above the job bounds the job refuses loudly in its first unit.
    expect([by.JOB_TARGETS_5001.job, by.JOB_TARGETS_5001.failed_kind, by.JOB_TARGETS_5001.failure?.code]).toEqual(['FAILED', 'HIST_PREP', 'CP7_ANALYSIS_STAGED_TARGET_LIMIT'])
    expect([by.JOB_CELLS_520000.job, by.JOB_CELLS_520000.failed_kind, by.JOB_CELLS_520000.failure?.code]).toEqual(['FAILED', 'HIST_PREP', 'CP7_PLANNING_HISTORY_GRID_LIMIT'])
  } finally { await db.close() }
}, 3_600_000)

// Deliberately wrong staged units. Each must apply to the product once and
// must make the comparison above fail on at least one case of a small corpus.
const MUTANTS: [string, string, string, string][] = [
  // A sale's inverse journal without its header is dropped from the chunk.
  ['EVENTS_NO_INVERSE', 'cp7_analysis_stage.event_facts', "where headers?(x->>'sale_id')or sj_ids?(x->>'reversal_of_id');", "where headers?(x->>'sale_id');"],
  // The first sale of every chunk is lost at the cut.
  ['EVENTS_CUT_EDGE', 'cp7_analysis_stage.event_facts', "where x->>'id'between lo and hi;", "where x->>'id'>lo and x->>'id'<=hi;"],
  // An uncastable stock quantity no longer forces the single path's whole call.
  ['AVAILABILITY_NOT_CHECKED', 'cp7_analysis_stage.availability_clean', "and cp7_analysis_stage.castable(m->>'qty_signed','numeric')", ''],
  // Invalid sale dates no longer force the single path's whole call.
  ['EVENTS_NOT_CHECKED', 'cp7_analysis_stage.events_clean', "bool_and(cp7_analysis_stage.castable(x->>'sale_date','timestamptz')and", 'bool_and(true and'],
  // The last history row of every chunk is lost.
  ['ROWS_EDGE', 'cp7_analysis_stage.run_scenario_unit', 'where k.pos between u.lo and u.hi;', 'where k.pos between u.lo and u.hi-1;'],
  // Draft reservations are read as cancelled ones.
  ['ROWS_DRAFTS', 'cp7_analysis_stage.history_rows', "from ev where ev.ev_row->>'status'='DRAFT' group by 1", "from ev where ev.ev_row->>'status'='CANCELLED' group by 1"],
  // The last policy containing a root wins.
  ['BASE_POLICY_LAST', 'cp7_analysis_stage.baseline_rows', "(array_agg(x order by o))[1] v from jsonb_array_elements(c->'production_policies'->'rows')", "(array_agg(x order by o desc))[1] v from jsonb_array_elements(c->'production_policies'->'rows')"],
  // A repeated revision no longer refuses.
  ['VALIDATE_NO_CONFLICT', 'cp7_analysis_stage.events_validate', "  if event_conflict[i] then raise exception 'CP7_DEMAND_REVISION_CONFLICT';end if;\n", ''],
  // A chunk's events refusal is raised before the targets check.
  ['VALIDATE_EVENTS_FIRST', 'cp7_analysis_stage.history_validate', " for t,i in select x.value,x.n from jsonb_array_elements(v->'targets')with ordinality x(value,n) order by x.n loop",
    " for e in select x.value from jsonb_array_elements(v->'errors')with ordinality x(value,o)order by x.o loop raise exception using errcode=e->>'sqlstate',message=e->>'message';end loop;\n for t,i in select x.value,x.n from jsonb_array_elements(v->'targets')with ordinality x(value,n) order by x.n loop"],
  // The schedule skips the selected yield projection.
  ['SCHEDULE_NO_YIELD', 'cp7_analysis_stage.schedule', 'wip:=cp7_wip.project_yield(wip,to_jsonb(yield_inputs));remaining_load:=load;', 'remaining_load:=load;'],
  // The fabric plan reads no conditional gap.
  ['FABRIC_NO_GAP', 'cp7_analysis_stage.run_unit', "   'conditional_gap_pcs',x.v->'conditional_gap_pcs','net'", "   'conditional_gap_pcs',null,'net'"],
]
test('P19 staged scenario: the comparison catches every deliberately wrong unit', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installScenarioControls(db, { bounds: SMALL })
    const cases: Case[] = []
    const add = (seed: number, shape: Record<string, unknown>, defect: string | null) => { const { c, q } = scenarioCapture(seed, shape, defect); cases.push({ seed, defect, c, q }) }
    for (let seed = 600; seed < 606; seed++) add(seed, SHAPES[seed % SHAPES.length], null)
    for (let seed = 610; seed < 614; seed++) add(seed, SHAPES[1], null)
    for (const defect of ['BAD_STOCK_QTY', 'BAD_SALE_DATE', 'POLICY_OVERLAP', 'DRAFT_TWIN', 'TWO_ORIGINAL_JOURNALS', 'DUP_PRODUCT_RETURN_OVER']) for (const seed of [620, 621]) add(seed, SHAPES[seed % 2], defect)
    const baseline = await compare(db, cases, 0x600)
    expect(baseline.filter(r => !(identical(r) || sameRefusal(r))).map(r => [r.seed, r.defect])).toEqual([])
    const caught: Record<string, number> = {}
    let base = 0x700
    for (const [name, fn, from, to] of MUTANTS) {
      const restore = await applyMutant(db, [fn, from, to])
      try {
        const rows = await compare(db, cases, (base += 0x40))
        caught[name] = rows.filter(r => !(identical(r) || sameRefusal(r))).length
      } finally { await restore() }
    }
    console.log(JSON.stringify({ cases: cases.length, caught }))
    for (const [name] of MUTANTS) expect([name, caught[name] > 0]).toEqual([name, true])
    // Restored: the same corpus agrees again.
    const again = await compare(db, cases, (base += 0x40))
    expect(again.filter(r => !(identical(r) || sameRefusal(r))).map(r => [r.seed, r.defect])).toEqual([])
  } finally { await db.close() }
}, 3_600_000)
