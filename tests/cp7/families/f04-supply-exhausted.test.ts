// @vitest-environment node
import { afterAll, beforeAll, describe, expect, test } from 'vitest'
import { execFileSync } from 'node:child_process'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { cuttingInput } from './f04/wip-normalize-fixture.mjs'
import { AT, LOADABLE_DEFECTS, MODEL, installSupplyControls, intentPredicate, setBaseline, supplyBase } from './f04/supply-exhausted-fixture.mjs'

// PL-8 part 2: posted cutting groups whose own conserved graph proves every
// piece reached FG or EXIT leave the global production facts and are listed in
// production_scope.exhausted_cutting_groups. Kernel-level, SYNTHETIC erp rows.
let db: any
const one = async (sql: string) => (await db.query(sql))[0]
const parity = async () => (await one(`select public.sx_parity('${AT}') r`)).r
const ids = async (sql: string): Promise<string[]> => (await one(`select coalesce(jsonb_agg(x order by x::uuid),'[]') r from (${sql}) z(x)`)).r
const seed = async (kind: string, n: number, sizes = 1) => (await one(`select to_jsonb(public.sx_seed('${kind}',${n},${sizes})) r`)).r as string[]
const reset = () => db.execute('select public.sx_reset();truncate public.sx_out;')
const load = (facts: unknown) => db.execute(`select public.sx_load(${jsonArg(facts)})`)
const state = async (name: string, sql: string) => (await one(`select public.sx_run('${name}',${`'${sql.replaceAll("'", "''")}'`}) r`)).r as string
const sorted = (a: string[]) => [...a].sort()

beforeAll(async () => { db = await openRuntime({ commandTimeoutMs: 600_000 }); await installSupplyControls(db) }, 600_000)
afterAll(async () => { await db?.close() })

describe('PL-8 exhausted cutting groups leave the global supply source', () => {
  test('below the old caps, data with no exhausted group: same source, WIP and supply build except the declared v2 fields', async () => {
    for (const [i, sizes] of [[1, 1], [2, 2], [3, 3]]) {
      await reset(); await setBaseline(db)
      for (const kind of ['open', 'partial', 'flag', 'failed', 'hold', 'rework_open', 'claim_other', 'unposted']) await seed(kind, 2 + i, sizes)
      await db.execute(`insert into erp.bs_cases(id,product_id,qty_pcs,status,detected_at_stage,physical_at,row_version,untracked_type)
        values(gen_random_uuid(),md5('sx-product-1')::uuid,2,'OPEN','SEWING','2026-09-02T00:00:00Z',1,'LEGACY')`)
      const r = await parity()
      expect(r).toMatchObject({ old_source: 'NO_ERROR', new_source: 'NO_ERROR', exhausted: 0, identical_when_none_pruned: true, same_outcome: true,
        kept_positions_identical: true, kept_totals_identical: true, same_signals: true, new_status: 'COMPLETE' })
      expect(r.scope_keys).toEqual(['cutting_groups', 'exhausted_cutting_groups', 'opening_items', 'unsourced_bs'])
      expect(r.kept).toBe(7 * (2 + i))
      const b = (await one('select public.sx_build_parity() r')).r
      expect(b).toMatchObject({ old_contract: 'cp7.native-supply.v1', new_contract: 'cp7.native-supply.v2', rest_identical: true, wip_identical: true,
        scope_is_old_plus_empty_list: true, hash_changed: true, old_path_absent: true, new_path: [] })
    }
    // The 1000-group edge is unchanged when nothing is exhausted.
    await reset(); await seed('open', 1000)
    expect(await parity()).toMatchObject({ old_source: 'NO_ERROR', new_source: 'NO_ERROR', kept: 1000, exhausted: 0, identical_when_none_pruned: true })
    await seed('open', 1)
    expect(await parity()).toMatchObject({ old_source: 'P0001:CP7_SUPPLY_GLOBAL_SCOPE_LIMIT', new_source: 'P0001:CP7_SUPPLY_GLOBAL_SCOPE_LIMIT' })
  }, 600_000)

  test('generated lifecycles and planted faults: only spent groups leave, every kept position, total and signal is the predecessor\'s, every refusal too', async () => {
    let compared = 0, complete = 0, pruned = 0, prunedPools = 0, untouched = 0, refused = 0, multiBatchPruned = 0
    const outcomes = new Set<string>()
    for (let s = 1; s <= 6; s++) for (const defect of LOADABLE_DEFECTS) {
      // Seeds 5 and 6 span three capture batches: a fault in one batch must
      // leave that batch whole while the others are pruned.
      const c = cuttingInput(s * 977 + LOADABLE_DEFECTS.indexOf(defect), { groups: s < 5 ? 4 + (s * 7) % 23 : 90 + 10 * s, exhaustedGroups: s < 5 ? s % 5 : 25, positionsPerSize: s % 2 ? 2 : 4, defect })
      await reset(); await load(c.facts)
      const r = await parity(); compared++
      expect([s, defect, r.new_source]).toEqual([s, defect, r.old_source])
      if (r.old_source !== 'NO_ERROR') { refused++; continue }
      expect([s, defect, r.disjoint, r.no_pruned_fact, r.exhausted_sorted, r.same_scope_union, r.same_other_scope, r.same_other_facts])
        .toEqual([s, defect, true, true, true, true, true, true])
      expect([s, defect, r.same_outcome]).toEqual([s, defect, true])
      if (s >= 5 && r.exhausted > 0 && (r.old_status !== 'COMPLETE' || r.old_wip !== 'NO_ERROR')) multiBatchPruned++
      outcomes.add(r.old_wip === 'NO_ERROR' ? `${r.old_status}:${r.old_reason ?? ''}` : r.old_wip.split(':').slice(1).join(':'))
      if (r.exhausted === 0) { expect([s, defect, r.identical_when_none_pruned]).toEqual([s, defect, true]); untouched++ }
      if (r.old_status !== 'COMPLETE' || r.old_wip !== 'NO_ERROR') continue
      complete++; pruned += r.exhausted; prunedPools += r.pruned_pools
      expect([s, defect, r.kept_positions_identical, r.kept_totals_identical, r.pruned_all_fg_or_exit, r.every_pruned_has_pools, r.pruned_without_open_signal, r.same_signals])
        .toEqual([s, defect, true, true, true, true, true, true])
    }
    console.log(JSON.stringify({ pl8_lifecycle_parity: { compared, complete, pruned_groups: pruned, pruned_pools: prunedPools, none_pruned: untouched, source_refused: refused, refused_graphs_with_other_batches_pruned: multiBatchPruned, outcomes: [...outcomes].sort() } }))
    expect(compared).toBe(6 * LOADABLE_DEFECTS.length)
    expect(complete).toBeGreaterThan(40); expect(pruned).toBeGreaterThan(200); expect(multiBatchPruned).toBeGreaterThan(20); expect(prunedPools).toBeGreaterThanOrEqual(pruned); expect(untouched).toBeGreaterThan(5)
    // Refused graphs prune nothing from their batch and refuse as before.
    for (const code of ['CONFLICT:NEGATIVE_PREFIX', 'UNKNOWN:CUTTING_YIELDS_MISSING', 'CP7_WIP_TRANSITION_QUANTITY', 'CONFLICT:DELIVERY_SIZE_TOTAL_MISMATCH',
      'CONFLICT:RECEIPT_DELIVERY_LINEAGE_MISMATCH', 'UNKNOWN:LEGACY_RECEIPT_CUSTODY_REQUIRES_RECONCILIATION', 'CONFLICT:BS_SOURCE_LINEAGE_MISMATCH']) expect([...outcomes]).toContain(code)
  }, 600_000)

  test('spent kinds are pruned and listed; open, flagged, failed-attempt, held, open-rework and open-claim groups never are', async () => {
    await reset(); await setBaseline(db)
    const spent: string[] = [], open: string[] = []
    for (const kind of ['direct', 'laundry', 'bs_scrap', 'rework_fg']) spent.push(...await seed(kind, 3, 2))
    for (const kind of ['open', 'partial', 'flag', 'failed', 'hold', 'rework_open', 'claim_other']) open.push(...await seed(kind, 3, 2))
    const draft = await seed('unposted', 2)
    // Status-only open rework (nothing sent yet, so no REWORK piece): its
    // group is physically spent but stays in scope.
    const [quiet] = await seed('bs_scrap', 1, 1)
    await db.execute(`insert into erp.rework_orders select gen_random_uuid(),b.id,0,null,null,'2026-09-02T00:00:00Z',null,'IN_PROGRESS',1,null,false
      from erp.bs_cases b where b.cutting_group_id='${quiet}'`)
    open.push(quiet)
    const r = await parity()
    expect(r).toMatchObject({ exhausted: 12, kept: 22, same_outcome: true, kept_positions_identical: true, pruned_all_fg_or_exit: true, same_signals: true })
    const src = (await one(`select public.sx_get('new_source')->'scope' r`)).r
    expect(src.exhausted_cutting_groups).toEqual(sorted(spent))
    expect(sorted(src.cutting_groups)).toEqual(sorted(open))
    for (const g of draft) expect([...src.cutting_groups, ...src.exhausted_cutting_groups]).not.toContain(g)
    // The listed evidence is fingerprinted: a reversal reopens the group, which
    // re-enters the facts and changes the source; a revision bump of a spent
    // group's posted row changes neither its verdict nor the fingerprint.
    const fp = async () => (await one('select cp7_supply_native.fingerprint(cp7_supply_native.source()) r')).r as string
    const before = await fp()
    await db.execute(`update erp.qc_inspections set row_version=row_version+1 where id in(select inspection_id from erp.qc_inspection_items where cutting_group_id='${spent[0]}')`)
    expect(await fp()).toBe(before)
    await db.execute(`update erp.qc_inspections set status='REVERSED' where id in(select inspection_id from erp.qc_inspection_items where cutting_group_id='${spent[0]}')`)
    expect(await fp()).not.toBe(before)
    const after = await parity()
    expect(after).toMatchObject({ exhausted: 11, kept: 23, kept_positions_identical: true })
  }, 600_000)

  test('more than 1000 SYNTHETIC spent groups plus open work: completes with the per-target numbers of the open work alone; the predecessor refuses', async () => {
    await reset(); await setBaseline(db)
    const c = cuttingInput(4711, { groups: 14, exhaustedGroups: 0 })
    for (const g of c.facts.groups) g.model_id = MODEL
    await load(c.facts)
    const net = 'select cp7_netting_native.build(cp7_netting_native.source(),\'{}\')'
    expect(await state('net_open', net)).toBe('NO_ERROR')
    const alone = (await one(`select jsonb_build_object('status',v->>'status','positions',jsonb_array_length(v->'schedule_run_result'->'wip'->'positions'),
      'rows',jsonb_array_length(v->'rows'),'needs_check',(select count(*) from jsonb_array_elements(v->'match_results')x where x->'result'->>'match' in('NEEDS_CHECK','UNKNOWN')),
      'exhausted',v#>'{schedule_run_result,supply_run_result,production_scope,exhausted_cutting_groups}') r from public.sx_out where name='net_open'`)).r
    expect(alone.positions).toBeGreaterThan(0); expect(alone.rows).toBe(3)
    // Administrative SYNTHETIC clones of historical spent groups (labelled; not Native postings).
    const clones = [...await seed('direct', 700, 2), ...await seed('laundry', 420, 1)]
    expect(clones.length).toBe(1120)
    expect(await state('old_src', `select cp7_supply_native.wip_source_at_0('${AT}')`)).toBe('P0001:CP7_SUPPLY_GLOBAL_SCOPE_LIMIT')
    const t0 = Date.now()
    expect(await state('net_mixed', net)).toBe('NO_ERROR')
    const ms = Date.now() - t0
    // Byte-identical apart from the source hashes and the evidence list.
    const same = (await one(`select public.sx_same_net('net_open','net_mixed') r`)).r
    expect(same).toMatchObject({ identical: true, rows_identical: true, match_results_identical: true, wip_identical: true, hashes_differ: true,
      listed: clones.length + alone.exhausted.length, positions: alone.positions, needs_check: alone.needs_check })
    const listed = (await one(`select v#>'{schedule_run_result,supply_run_result,production_scope,exhausted_cutting_groups}' r from public.sx_out where name='net_mixed'`)).r
    for (const g of clones) expect(listed).toContain(g)
    console.log(JSON.stringify({ pl8_mixed_netting_ms: ms, spent_clones: clones.length, open_positions: alone.positions }))
    // Below 1000 groups the predecessor's zero positions alone hit the netting cap.
    await reset(); await setBaseline(db); await load(c.facts)
    expect(await state('net_open', net)).toBe('NO_ERROR')
    await seed('direct', 600, 1)
    const old = await state('net_old', `select cp7_netting_native.build(cp7_netting_native.source()||jsonb_build_object('production_sources',cp7_supply_native.wip_source_at_0('${AT}')),'{}')`)
    expect(old).toBe('P0001:CP7_NETTING_WORK_LIMIT')
    expect(await state('net_mixed', net)).toBe('NO_ERROR')
    expect((await one(`select public.sx_same_net('net_open','net_mixed') r`)).r).toMatchObject({ identical: true, listed: 600 + alone.exhausted.length })
  }, 600_000)

  test('fail-closed: a batch whose graph is not COMPLETE prunes nothing; capture and scope refusals stay', async () => {
    const batchOf = async (g: string) => {
      const all = await ids("select id::text from erp.cutting_groups where material_issue_posted and cut_at<='" + AT + "'")
      const i = all.indexOf(g); return all.slice(i - (i % 50), i - (i % 50) + 50)
    }
    for (const fault of ['over_qc', 'negative_qc']) {
      await reset()
      const spent = await seed('direct', 140, 1)
      const [bad] = await seed('direct', 1, 1)
      await db.execute(`update erp.qc_inspection_items set qty_good_pcs=${fault === 'over_qc' ? 4 : -1} where cutting_group_id='${bad}'`)
      const r = await parity()
      expect(r).toMatchObject({ old_source: 'NO_ERROR', new_source: 'NO_ERROR', same_outcome: true, disjoint: true })
      if (fault === 'over_qc') expect([r.old_status, r.old_reason, r.new_status, r.new_reason]).toEqual(['CONFLICT', 'NEGATIVE_PREFIX', 'CONFLICT', 'NEGATIVE_PREFIX'])
      else expect([r.old_wip, r.new_wip]).toEqual([expect.stringContaining('CP7_WIP_TRANSITION_QUANTITY'), expect.stringContaining('CP7_WIP_TRANSITION_QUANTITY')])
      const batch = await batchOf(bad)
      const scope = (await one(`select public.sx_get('new_source')->'scope' r`)).r
      expect(sorted(scope.cutting_groups)).toEqual(sorted(batch))
      expect(sorted(scope.exhausted_cutting_groups)).toEqual(sorted(spent.filter(g => !batch.includes(g))))
    }
    // A capture batch over its row limit is refused as before.
    await reset(); await seed('direct', 60, 1)
    const [busy] = await seed('direct', 1, 1)
    await db.execute(`insert into erp.sewing_terminal_events select gen_random_uuid(),'${busy}',1,'COMPLETE',null,'2026-09-02T00:00:00Z',1 from generate_series(1,2001)`)
    expect(await parity()).toMatchObject({ old_source: 'P0001:CP7_SUPPLY_NATIVE_BATCH_INCOMPLETE', new_source: 'P0001:CP7_SUPPLY_NATIVE_BATCH_INCOMPLETE' })
    // The 1000-id scope still holds for groups that are not exhausted.
    await reset(); await seed('direct', 500, 1); await seed('open', 1000, 1)
    expect(await parity()).toMatchObject({ old_source: 'P0001:CP7_SUPPLY_GLOBAL_SCOPE_LIMIT', new_source: 'NO_ERROR', kept: 1000, exhausted: 500 })
    await seed('partial', 1, 1)
    expect(await parity()).toMatchObject({ new_source: 'P0001:CP7_SUPPLY_GLOBAL_SCOPE_LIMIT' })
    // More than 20000 posted groups: refused before any is classified.
    await reset(); await seed('open', 20001, 1)
    const t0 = Date.now()
    expect(await state('ceiling', `select cp7_supply_native.wip_source_at('${AT}')`)).toBe('P0001:CP7_SUPPLY_GLOBAL_SCOPE_LIMIT')
    expect(Date.now() - t0).toBeLessThan(5000)
  }, 600_000)

  test('open intents are never pruned; a spent intent group closes through production_scope.exhausted_cutting_groups', async () => {
    await reset(); await setBaseline(db)
    const [opened] = await seed('open', 1, 1), [partial] = await seed('partial', 1, 1), [spent] = await seed('direct', 1, 1), [draft] = await seed('unposted', 1, 1)
    const [held] = await seed('hold', 1, 1)
    await db.execute(`${intentPredicate()}
      truncate cp7_plan_native.intents;
      insert into cp7_plan_native.intents values('T-open','${opened}'),('T-partial','${partial}'),('T-spent','${spent}'),('T-draft','${draft}'),('T-held','${held}');`)
    expect(await state('scenario', 'select jsonb_build_object(\'netting\',jsonb_build_object(\'schedule_run_result\',cp7_schedule_native.build(cp7_schedule_native.source(),\'{}\')))')).toBe('NO_ERROR')
    const verdict = (await one(`select jsonb_object_agg(t,cp7_plan_native.sx_open_intent(t,(select v from public.sx_out where name='scenario'))) r
      from unnest(array['T-open','T-partial','T-spent','T-draft','T-held']) t`)).r
    expect(verdict).toEqual({ 'T-open': true, 'T-partial': true, 'T-spent': false, 'T-draft': true, 'T-held': true })
    const scope = (await one(`select v#>'{netting,schedule_run_result,supply_run_result,production_scope}' r from public.sx_out where name='scenario'`)).r
    expect(scope.exhausted_cutting_groups).toEqual([spent])
    expect(sorted(scope.cutting_groups)).toEqual(sorted([opened, partial, held]))
    // The predecessor's predicate read a path the supply source never emits:
    // its spent intent would stay open for good.
    const head = execFileSync('git', ['show', `${supplyBase}:scripts/cp7-src/plan-native/preflight.sql`], { encoding: 'utf8' })
    expect(head).toContain("'{netting,schedule_run_result,supply_run_result,exhausted_cutting_groups}'")
    const scenario = (await one(`select v r from public.sx_out where name='scenario'`)).r
    expect(scenario.netting.schedule_run_result.supply_run_result.exhausted_cutting_groups).toBeUndefined()
  }, 600_000)
})
