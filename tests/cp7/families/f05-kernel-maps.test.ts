// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime } from './f04/runtime.mjs'
import { assemblyArgs, assemblyInput, compareAssembly, installAssemblyControls, uid } from './f04/analysis-assembly-fixture.mjs'

// P19 replaced per-row lookups into the whole netting result with maps built
// once (edges and match results per target, ETA per position, allocated input
// per source, directed sources). The shared assembly fixture has one position
// and at most two edges, so this control feeds the same ab4 predecessor and the
// current compiler many positions, repeated edges per (key, target) with JSON
// null or absent match, match results, multi-row matching sources, missing or
// result-less ETAs and null inputs. Pure SQL kernels only; no Native/Auth credit.
type Json = Record<string, unknown>

function enrich(count: number, seed: number) {
 const c = assemblyInput(count, seed)
 let state = (seed * 7919) >>> 0
 const pick = <T,>(choices: T[]): T => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return choices[state % choices.length] }
 const n = c.test_netting
 n.allocation.status = 'SCENARIO'
 n.rows.forEach((r: Json, i: number) => { (r.production_policy as Json).policy = { state: i % 4 === 3 ? null : 'ACTIVE' } })
 const known = n.rows.filter((r: Json) => ((r.production_policy as Json).policy as Json).state).map((r: Json) => r.target_key as string)
 const keys = ['p0', 'p1', 'p2', 'p3', 'p4']
 const refs = [{ kind: 'EXPLICIT_SYNTHETIC_KERNEL_ONLY', id: uid(9), revision: '1' }]
 n.schedule_run_result.wip.positions = keys.map((key, i) => ({ key, size_id: uid(100000), stage: 'SEWING', eligible_company_wip: pick([true, true, false]),
  remaining_pcs: pick(['8', '0', '3']), projection: { eligible_input_pcs: '8', projected_good_pcs: String(i) }, refs }))
 n.schedule_run_result.etas = keys.flatMap(key => pick([0, 1, 1, 1]) ? [pick<Json>([{ position_key: key, result: { eta: '2026-10-07T00:00:00Z', status: 'KNOWN' } },
  { position_key: key, result: { eta: null, status: 'CONDITIONAL' } }, { position_key: key }])] : [])
 n.matching.sources = keys.flatMap(key => Array.from({ length: pick([0, 1, 2]) }, () => {
  const target = pick([null, known[0], undefined])
  return target === undefined ? { key } : { key, confirmed_target: target }
 }))
 n.allocation.allocation.edges = []
 for (const target of [...known, null]) {
  for (let j = pick([0, 1, 2, 3]); j > 0; j--) {
   const edge: Json = { key: pick(keys), position_key: pick(keys), target_key: target, size_id: uid(100000),
    input_pcs: pick(['4', '0.01', null, '9007199254740993.01']), projected_good_pcs: '3', refs }
   const match = pick(['CONFIRMED_TARGET', 'CANDIDATE_MATCH', 'REJECTED', null, undefined])
   if (match !== undefined) edge.match = match
   n.allocation.allocation.edges.push(edge)
  }
 }
 n.match_results = Array.from({ length: pick([0, 2, 5]) }, () => ({ position_key: pick(keys), target_key: pick([...known, 'OTHER:1']),
  result: { match: pick(['CONFIRMED_TARGET', 'CANDIDATE_MATCH', 'UNKNOWN']) } }))
 n.rows.forEach((r: Json) => {
  (r.timeline as Json).events = Array.from({ length: pick([0, 2, 4]) }, (_, j) => ({ event: { kind: pick(['SUPPLY', 'SUPPLY', 'DEMAND', 'UNKNOWN']),
   at: j % 2 ? '2026-10-05T17:00:00.000001Z' : '2026-10-05T16:59:59.999999Z', key: `supply-${pick([...keys, 'none'])}`, qty_pcs: '7', refs },
   balance_pcs: j % 2 ? '-1.5' : null, new_unmet_pcs: '0.01' }))
 })
 return c
}

async function states(db: { query: (sql: string) => Promise<Json[]> }, c: Json) {
 const args = assemblyArgs(c)
 return (await db.query(`select public.p19_state_0(${args}) old,public.p19_state_1(${args}) candidate`))[0] as { old: string, candidate: string }
}

test('P19 kernel maps equal the predecessor for rich edges, match results, ETAs, sources and inputs', async () => {
 const db = await openRuntime({ commandTimeoutMs: 600_000 })
 try {
  await installAssemblyControls(db)
  const coverage = { same: 0, refused: 0 }
  const seen = new Set<string>()
  for (let seed = 1; seed <= 30; seed++) {
   for (const count of [4, 9]) {
    const c = enrich(count, seed)
    const state = await states(db, c)
    expect(state.candidate).toBe(state.old)
    if (state.old !== 'NO_ERROR') { coverage.refused++; continue }
    const result = await compareAssembly(db, c)
    expect(result.same).toBe(true)
    coverage.same++
    const marks = (await db.query(`with v as materialized(select public.p19_assembly_1(${assemblyArgs(c)}) v)
     select distinct m from v,lateral(
      select 'kind:'||(x->>'supply_kind') m from jsonb_array_elements(v.v->'sources')x
      union all select 'directed:'||(x->'directed_supply'->>'state') from jsonb_array_elements(v.v->'timeline')x
      union all select 'candidate:'||(x->'candidate_supply'->>'state') from jsonb_array_elements(v.v->'timeline')x
      union all select 'allocated:'||(x->'allocated'->>'state') from jsonb_array_elements(v.v->'sources')x
      union all select 'eta:'||coalesce(x->>'eta_basis','none') from jsonb_array_elements(v.v->'sources')x)s`)) as { m: string }[]
    marks.forEach(row => seen.add(row.m))
   }
  }
  // Every branch the maps feed is reached on the compared outputs.
  expect(coverage.same).toBeGreaterThan(40)
  for (const mark of ['kind:DIRECTED', 'kind:CANDIDATE', 'directed:KNOWN', 'directed:ASSUMED', 'directed:UNKNOWN', 'candidate:KNOWN',
   'candidate:ASSUMED', 'candidate:UNKNOWN', 'allocated:KNOWN', 'eta:CONFIRMED_PLAN', 'eta:ASSUMED', 'eta:UNKNOWN']) {
   expect([...seen].some(m => m === mark), mark).toBe(true)
  }
  // An ambiguous ETA for a visited position still refuses identically.
  const twin = enrich(4, 2)
  const edge = twin.test_netting.allocation.allocation.edges.find((e: Json) => e.target_key)
  twin.test_netting.schedule_run_result.etas.push({ position_key: edge.position_key, result: { eta: null, status: 'KNOWN' } },
   { position_key: edge.position_key, result: { eta: null, status: 'KNOWN' } })
  expect(await states(db, twin)).toEqual({ old: '21000', candidate: '21000' })
  // The same when only the source loop visits that position (no edge does).
  const source = enrich(4, 2)
  source.test_netting.allocation.allocation.edges = []
  source.test_netting.schedule_run_result.wip.positions[0] = { ...source.test_netting.schedule_run_result.wip.positions[0], eligible_company_wip: true, remaining_pcs: '8' }
  source.test_netting.schedule_run_result.etas.push({ position_key: 'p0', result: { eta: null, status: 'KNOWN' } },
   { position_key: 'p0', result: { eta: null, status: 'KNOWN' } })
  expect(await states(db, source)).toEqual({ old: '21000', candidate: '21000' })
  // An edge for a target that was never compiled still refuses identically.
  const stray = enrich(4, 3)
  stray.test_netting.allocation.allocation.edges.push({ key: 'p0', position_key: 'p0', target_key: 'MISSING:1', match: 'CONFIRMED_TARGET', refs: [] })
  expect(await states(db, stray)).toEqual({ old: 'P0001', candidate: 'P0001' })
  // The compared output depends on the mapped facts: changing the first edge's
  // match of a visited supply event changes both compilers the same way.
  const base = enrich(4, 5)
  const before = await compareAssembly(db, base)
  const target = base.test_netting.rows.find((r: Json) => ((r.production_policy as Json).policy as Json).state &&
   (r.timeline as Json & { events: Json[] }).events.some(e => (e.event as Json).kind === 'SUPPLY'))
  const supplyKey = ((target.timeline.events as Json[]).find(e => (e.event as Json).kind === 'SUPPLY')!.event as Json).key as string
  base.test_netting.allocation.allocation.edges.unshift({ key: supplyKey.slice('supply-'.length), position_key: 'p0', target_key: target.target_key,
   input_pcs: '1', projected_good_pcs: '1', match: 'CANDIDATE_MATCH', refs: [] })
  const after = await compareAssembly(db, base)
  expect(after.same).toBe(true)
  expect(after.sha256).not.toBe(before.sha256)
 } finally { await db.close() }
}, 600_000)
