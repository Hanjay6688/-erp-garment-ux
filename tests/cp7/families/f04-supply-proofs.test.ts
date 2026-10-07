// @vitest-environment node
import { afterAll, beforeAll, describe, expect, test } from 'vitest'
import { jsonArg, openRuntime } from './f04/runtime.mjs'
import { rng } from './f04/demand-history-fixture.mjs'
import { cuttingInput } from './f04/wip-normalize-fixture.mjs'
import { AT, LOADABLE_DEFECTS, setBaseline } from './f04/supply-exhausted-fixture.mjs'
import { ARRAY_MUTATIONS, MUTATIONS, NORMALIZE, SEED_FOR, installCaptureStubs, installProofControls, kernelDrift, variant } from './f04/supply-proofs-fixture.mjs'

// PL-8 part 3: a stored exhaustion proof replaces normalize_cutting for a group
// whose captured rows (and the kernel) are unchanged. Kernel-level, SYNTHETIC
// erp rows; the predecessor is cb201edf's source (every group classified on
// every request). The source must stay byte-identical with no proof, with every
// proof and with any mix, at the proof clock and at clocks before and after it.
const EARLY = '2026-09-10T00:00:00+00:00', LATE = '2026-11-02T00:00:00+00:00'
let db: any
const one = async (sql: string) => (await db.query(sql))[0]
const cmp = async (at = AT, census = false) => (await one(`select public.sp_cmp('${at}',${census}) r`)).r
const prove = async (at = AT, window = 37, max: number | null = null) => (await one(`select public.sp_prove('${at}',${window},${max ?? 'null'}) r`)).r as number
const seed = async (kind: string, n: number, sizes = 1) => (await one(`select to_jsonb(public.sx_seed('${kind}',${n},${sizes})) r`)).r as string[]
const mutate = async (kind: string, g: string, at = AT) => (await one(`select public.sp_mutate('${kind}','${g}','${at}') r`)).r as boolean
const reset = () => db.execute('select public.sx_reset();truncate cp7_supply_native.exhaustion_proofs;')
const exhausted = async (at = AT) => (await one(`select cp7_supply_native.wip_source_at('${at}')->'scope'->'exhausted_cutting_groups' r`)).r as string[]
const install = (sql: string) => db.execute(sql)
const shipped = async () => install(['cp7_supply_native.proof_kernel', 'cp7_supply_native.batch_reuse', 'cp7_supply_native.batch_verdict'].map(n => variant(n)).join('\n'))
const errorOf = async (sql: string) => (await one(`select public.sx_run('probe',${`'${sql.replaceAll("'", "''")}'`}) r`)).r as string

beforeAll(async () => { db = await openRuntime({ commandTimeoutMs: 600_000 }); await installProofControls(db) }, 600_000)
afterAll(async () => { await db?.close() })

describe('PL-8 stored exhaustion proofs', () => {
  // Generated lifecycles with every loadable planted fault (two shapes taking
  // turns: single-size with direct QC, and up to three sizes through laundry),
  // SYNTHETIC spent clones (one delivery shared by two groups, with a settled
  // claim), proofs stored in windows that are not the source's batches, then
  // corrections, reversals and backdated rows on proven and unproven groups,
  // new groups that shift every later batch, and a partial re-proof (mixed
  // batches). Each state is compared at the proof clock, before it and after it.
  test('generated lifecycles: no proof, every proof, any mix and every later correction, reversal or backdated row give the predecessor\'s source byte for byte', async () => {
    let compared = 0, reused = 0, mixed = 0, refusedWithProofs = 0, mutated = 0, reproven = 0
    const kinds = new Set<string>(), reusedAt: Record<string, number> = { [EARLY]: 0, [LATE]: 0 }
    for (const defect of LOADABLE_DEFECTS) {
      const d = LOADABLE_DEFECTS.indexOf(defect), s = 1 + d % 2, r = rng(s * 7919 + d), tag = [s, defect]
      const c = cuttingInput(s * 977 + d, { groups: 30 + 10 * s, exhaustedGroups: 20, positionsPerSize: s % 2 ? 2 : 4, sizesPerGroup: s === 2 ? 0 : 1, defect })
      await reset(); await setBaseline(db)
      await db.execute(`select public.sx_load(${jsonArg(c.facts)})`)
      const clones = [...await seed('laundry', 4, 2), ...await seed('bs_scrap', 2, 1), ...await seed('rework_fg', 2, 1), ...await seed('direct', 3, 3)]
      // One delivery shared by two spent laundry groups, with a settled claim on it.
      await one(`select public.sp_share('${clones[0]}','${clones[1]}') r`)
      await db.execute(`insert into erp.laundry_claims select gen_random_uuid(),delivery_id,null,'OTHER',1,'SETTLED','2026-09-01T07:00:00Z','2026-09-02T00:00:00Z',1
        from erp.laundry_delivery_lines where cutting_group_id='${clones[0]}' order by id limit 1`)
      const check = async (at: string, census = false) => {
        const x = await cmp(at, census); compared++
        expect([...tag, at, x.new, x.same, x.reader_wrote]).toEqual([...tag, at, x.old, true, false])
        reused += x.reused; mixed += x.mixed_batches; refusedWithProofs += x.refused_batches_with_proofs
        return x
      }
      // No proof stored: the classifier runs for every group.
      await check(AT)
      await prove(AT, 37 + s)
      for (const at of [AT, EARLY, LATE]) { const x = await check(at, true); if (at !== AT) reusedAt[at] += x.reused }
      const round = Array.from({ length: 10 }, (_, i) => MUTATIONS[(d * 10 + i + s) % MUTATIONS.length])
      const applied: string[] = (await one(`select public.sp_mutate_round('{${round.join(',')}}',7,${Math.floor(r() * 1e6)},'${AT}') r`)).r
      mutated += applied.length; for (const k of applied) kinds.add(k)
      if (d % 4 < 2) await db.execute(`update erp.laundry_claims set status='OPEN',row_version=row_version+1 where status='SETTLED'`)
      await seed('direct', 10, 1); await seed('open', 2, 1)
      for (const at of [AT, EARLY, LATE]) await check(at, at === AT)
      // Part of the history proven again (a mixed state), then all of it.
      reproven += await prove(AT, 23, 46)
      await check(AT, true)
      reproven += await prove(AT, 50)
      const last = await check(AT, true)
      expect([...tag, last.reused > 0, (await one(`select public.sp_build_same('${AT}') r`)).r]).toEqual([...tag, true, true])
    }
    console.log(JSON.stringify({ pl8_proof_parity: { compared, reused_groups: reused, reused_at_earlier_clock: reusedAt[EARLY], reused_at_later_clock: reusedAt[LATE],
      mixed_batches: mixed, refused_batches_with_proofs: refusedWithProofs, mutations: mutated, reproven, kinds: [...kinds].sort() } }))
    expect(compared).toBe(LOADABLE_DEFECTS.length * 9)
    expect(reused).toBeGreaterThan(1500); expect(mixed).toBeGreaterThan(100); expect(refusedWithProofs).toBeGreaterThan(20); expect(mutated).toBeGreaterThan(250)
    expect(reusedAt[EARLY]).toBeGreaterThan(100); expect(reusedAt[LATE]).toBeGreaterThan(100)
    expect(kinds.size).toBe(MUTATIONS.length)
  }, 600_000)

  test('a weaker design is caught: every fact array, the group row alone, the kernel, the clock, isolation, batch refusal and graph limits', async () => {
    // Each scenario runs once as shipped (must match) and once with the weaker
    // design installed before its proofs are stored (must not).
    const scenario = async (weak: string | null, run: () => Promise<any>) => {
      await reset(); await shipped(); if (weak) await install(weak)
      try { return await run() } finally { await shipped(); await install(NORMALIZE()) }
    }
    const caught: Record<string, boolean> = {}
    const both = async (name: string, weak: string, run: () => Promise<any>) => {
      const ok = await scenario(null, run), bad = await scenario(weak, run)
      expect([name, ok.same, ok.old]).toEqual([name, true, ok.old])
      caught[name] = bad.same === false
    }
    const hashOmits = (k: string) => variant('cp7_supply_native.batch_reuse', 'from slice s group by s.g', `from slice s where s.k<>'${k}' group by s.g`)
    for (const [k, kind] of Object.entries(ARRAY_MUTATIONS)) {
      await both(`hash_omits_${k}`, hashOmits(k), async () => {
        const gs = await seed(SEED_FOR[k], 6, 1); await seed('open', 2, 1)
        await prove()
        for (const g of gs.slice(0, 3)) expect([k, await mutate(kind, g)]).toEqual([k, true])
        return cmp()
      })
    }
    // A proof bound to the group row's version alone misses a backdated QC.
    await both('group_row_version_only', variant('cp7_supply_native.batch_reuse', 'from slice s group by s.g', `from slice s where s.k='groups' group by s.g`), async () => {
      const gs = await seed('direct', 6, 1); await prove()
      for (const g of gs.slice(0, 2)) await mutate('qc_backdated', g)
      return cmp()
    })
    // Kernel change after the proofs: QC no longer moves pieces.
    const kernelChange = async () => {
      await seed('direct', 6, 1); await seed('laundry', 4, 1); await prove()
      await install(NORMALIZE().replace("for q in select value from jsonb_array_elements(f->'qc') where value->>'status'='POSTED'", "for q in select value from jsonb_array_elements(f->'qc') where value->>'status'='POSTED_ONLY_LATER'"))
      return cmp()
    }
    await both('lookup_ignores_kernel', variant('cp7_supply_native.batch_reuse', 'and x.kernel_version=kernel', ''), kernelChange)
    await both('kernel_names_not_definitions', variant('cp7_supply_native.proof_kernel', 'string_agg(pg_get_functiondef(k.oid),', 'string_agg(k.oid::regprocedure::text,'), kernelChange)
    // As-of read before a rework completed: same rows, different verdict.
    await both('rework_clock_not_hashed', variant('cp7_supply_native.batch_reuse', `case when o.k='reworks'then o.x||jsonb_build_object('completed_by_clock',
   (o.x->>'completed_at')::timestamptz<=clock)else o.x end x`, 'o.x x'), async () => {
      const gs = await seed('rework_fg', 4, 1)
      await db.execute(`update erp.bs_resolutions set physical_at='2026-09-01T05:00:00Z' where bs_case_id in(select id from erp.bs_cases where cutting_group_id=any('${`{${gs.join(',')}}`}'::uuid[]))`)
      await prove(); expect((await exhausted()).length).toBe(4)
      const x = await cmp('2026-09-01T05:30:00Z')
      expect(x.exhausted).toBe(x.same ? 0 : 4)
      return x
    })
    // A zero-quantity QC of group A names group B's receipt line: COMPLETE
    // only while both share a batch.
    const noIsolation = variant('cp7_supply_native.batch_reuse', 'and not exists(select 1 from tangled t where t.g=o.g)', '')
    const A = '00000000-0000-4000-8000-0000000000aa', B = 'ffffffff-ffff-4fff-8fff-ffffffffffbb'
    await both('outgoing_link_not_isolated', noIsolation, async () => {
      const [b] = await seed('laundry', 1, 1), [a] = await seed('direct', 1, 1)
      await db.execute(`select public.sp_rekey('${a}','${A}');select public.sp_rekey('${b}','${B}');
        insert into erp.qc_inspections values('${A.replace('aa', 'a1')}','POSTED','2026-09-01T05:00:00Z',1);
        insert into erp.qc_inspection_items select gen_random_uuid(),'${A}','${A.replace('aa', 'a1')}',r.id,null,md5('sx-product-1')::uuid,0,0
         from erp.laundry_delivery_lines l join erp.laundry_receipt_lines r on r.delivery_line_id=l.id where l.cutting_group_id='${B}'`)
      await seed('direct', 10, 1); await prove()
      const first = await cmp(); expect(first.same).toBe(true)
      await seed('direct', 60, 1)
      return cmp()
    })
    // Group A's FG disposition row names group B's resolution: B refuses only
    // while A shares its batch.
    await both('incoming_link_not_isolated', noIsolation, async () => {
      const [a] = await seed('bs_scrap', 1, 1), [b] = await seed('bs_scrap', 1, 1)
      await db.execute(`select public.sp_rekey('${a}','${A}');select public.sp_rekey('${b}','${B}');
        insert into erp.fg_unsourced_receipts_v1 select gen_random_uuid(),c.id,(select d.id from erp.bs_cases x join erp.bs_resolutions d on d.bs_case_id=x.id where x.cutting_group_id='${B}'),1,'POSTED',null,'B','2026-09-01T06:00:00Z'
         from erp.bs_cases c where c.cutting_group_id='${A}'`)
      const fill = await seed('direct', 60, 1); await prove()
      expect((await exhausted()).length).toBe(62)
      await db.execute(`update erp.cutting_groups set material_issue_posted=false where id=any('{${fill.join(',')}}'::uuid[])`)
      return cmp()
    })
    // A batch whose unproven group refuses proves nothing, proofs or not.
    await both('refused_batch_still_prunes', variant('cp7_supply_native.batch_verdict', `if(cl->>'complete')::boolean and coalesce(`, `if true or coalesce(`), async () => {
      const gs = await seed('direct', 120, 1); await prove()
      const first = [...gs].sort()[0]
      await mutate('qc_backdated', first)
      return cmp()
    })
    // Reconcile's limits hold for the whole batch, reused groups included:
    // 40 proven + 10 classified groups of 21 sizes (mixed), then all 50 proven.
    const limitsOff = variant('cp7_supply_native.batch_verdict', `and coalesce((reuse->>'pools')::bigint,0)+(cl->>'pools')::bigint<=1000`, '')
    const wide = async (allProven: boolean) => {
      const early = (await one(`select to_jsonb(public.sp_seed_wide(40,21,'2026-09-01T00:00:00Z')) r`)).r
      await one(`select to_jsonb(public.sp_seed_wide(10,21,'2026-09-20T00:00:00Z')) r`)
      expect(await prove('2026-09-10T00:00:00Z', 50)).toBe(40)
      if (allProven) {
        await db.execute(`update erp.cutting_groups set material_issue_posted=false where id=any('{${early.join(',')}}'::uuid[])`)
        expect(await prove(AT, 50)).toBe(10)
        await db.execute(`update erp.cutting_groups set material_issue_posted=true where id=any('{${early.join(',')}}'::uuid[])`)
      }
      const x = await cmp(AT, true)
      expect([x.kept, x.reused]).toEqual([x.same ? 50 : 0, allProven ? 50 : 40])
      return x
    }
    await both('graph_limits_ignored_mixed', limitsOff, () => wide(false))
    await both('graph_limits_ignored_all_proven', limitsOff, () => wide(true))
    console.log(JSON.stringify({ pl8_proof_mutants: caught }))
    expect(Object.entries(caught).filter(([, v]) => !v).map(([k]) => k)).toEqual([])
    expect(Object.keys(caught).length).toBe(Object.keys(ARRAY_MUTATIONS).length + 9)
  }, 600_000)

  test('the store: append-only history, readers never write, any batching gives the same proofs, and the guards fail closed', async () => {
    await reset(); await shipped(); await setBaseline(db)
    const spent = [...await seed('direct', 70, 1), ...await seed('laundry', 30, 2)]
    await seed('open', 5, 1)
    // The supply source's own proofs equal those of 37-group windows.
    const fromSource = (await one(`select cp7_supply_native.store_proofs(cp7_supply_native.source_parts()->'proofs','${AT}') r`)).r
    expect(fromSource).toBe(100)
    const rows = async () => (await one(`select jsonb_agg(group_id::text||':'||facts_hash order by group_id,facts_hash) r from cp7_supply_native.exhaustion_proofs`)).r
    const stored = await rows()
    await db.execute('truncate cp7_supply_native.exhaustion_proofs')
    expect(await prove(AT, 37)).toBe(100)
    expect(await rows()).toEqual(stored)
    expect(await prove(AT, 50)).toBe(0)
    // Append-only: superseded proofs stay readable.
    expect(await errorOf('update cp7_supply_native.exhaustion_proofs set verdict=verdict')).toBe('55000:CP7_RUN_IMMUTABLE')
    expect(await errorOf('delete from cp7_supply_native.exhaustion_proofs')).toBe('55000:CP7_RUN_IMMUTABLE')
    await mutate('groups', spent[0]); await mutate('qc', spent[1])
    expect(await prove(AT, 50)).toBe(1)
    const history = (await one(`select jsonb_object_agg(group_id,n) r from(select group_id::text,count(*)n from cp7_supply_native.exhaustion_proofs where group_id=any('{${spent[0]},${spent[1]}}'::uuid[]) group by 1)x`)).r
    expect(history).toEqual({ [spent[0]]: 2, [spent[1]]: 1 })
    const x = await cmp(AT, true)
    expect(x).toMatchObject({ same: true, exhausted: 99, reused: 99, reader_wrote: false })
    // Catalog: CP7-owned, RLS with a no-access policy, nothing granted.
    const cat = (await one(`select jsonb_build_object('owner',pg_get_userbyid(c.relowner),'rls',c.relrowsecurity,
      'policies',(select count(*) from pg_policy p where p.polrelid=c.oid and pg_get_expr(p.polqual,p.polrelid)='false' and pg_get_expr(p.polwithcheck,p.polrelid)='false'),
      'granted',(select count(*) from unnest(array['anon','authenticated','service_role','public']) w where w<>'public' and has_table_privilege(w,c.oid,'SELECT,INSERT,UPDATE,DELETE')),
      'acl',c.relacl::text,'trigger',(select count(*) from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal)) r
      from pg_class c where c.oid='cp7_supply_native.exhaustion_proofs'::regclass`)).r
    expect(cat).toMatchObject({ owner: 'cp7_capture', rls: true, policies: 1, granted: 0, trigger: 1 })
    expect(await errorOf(`insert into cp7_supply_native.exhaustion_proofs(group_id,facts_hash,kernel_version,captured_at,verdict,graph_pools,graph_nodes,graph_events)
      values(gen_random_uuid(),repeat('a',64),repeat('b',64),now(),'OPEN',1,1,1)`)).toMatch(/^23514:/)
    // The kernel version covers what classification reaches; any new clock
    // read in it fails here first (the proof hash covers only the rework one).
    const closure = (await one(`with recursive k(oid)as(select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='cp7_supply_native'and p.proname in('proof_kernel','classify','batch_reuse','batch_verdict')or n.nspname='cp7_wip'and p.proname='capture_cutting_sources'
      union select p.oid from k join pg_proc q on q.oid=k.oid,regexp_matches(q.prosrc,'(cp7_[a-z0-9_]+)\\.([a-z0-9_]+)\\s*\\(','g')m,pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=m[1]and p.proname=m[2])
      select jsonb_object_agg(p.oid::regprocedure::text,(select count(*) from regexp_matches(p.prosrc,'captured_at|scope_at|clock_timestamp|now\\(|current_|statement_timestamp|transaction_timestamp','g'))) r from k join pg_proc p on p.oid=k.oid`)).r
    expect(closure).toEqual({
      'cp7_supply_native.proof_kernel()': 1, 'cp7_supply_native.classify(jsonb)': 0, 'cp7_supply_native.batch_reuse(jsonb,text)': 1, 'cp7_supply_native.batch_verdict(jsonb,text)': 0,
      'cp7_wip.capture_cutting_sources(uuid[],timestamp with time zone)': 1, 'cp7_wip.capture_cutting_sources(uuid[])': 1, 'cp7_wip.normalize_cutting(jsonb)': 4,
      'cp7_wip.settle_bs(jsonb,jsonb,jsonb,timestamp with time zone)': 1, 'cp7_wip.reconcile(jsonb)': 0, 'cp7_wip.transition(jsonb,text,text,text,text,numeric,jsonb)': 0,
      'cp7_wip.ref(text,text,text)': 0, 'cp7_wip.redispatch_valid(jsonb)': 0, 'cp7_wip.fields(jsonb,text[])': 0, 'cp7_wip.key(jsonb)': 0, 'cp7_wip.pcs(jsonb)': 0, 'cp7_wip.refs(jsonb)': 0,
    })
    // The kernel the isolation rules were derived from is the one installed.
    expect(kernelDrift()).toEqual([])
    // Reconcile's limits moved: nothing is reused or proven; the source is unchanged.
    const reconcile = (await one(`select pg_get_functiondef('cp7_wip.reconcile(jsonb)'::regprocedure) r`)).r as string
    await install(reconcile.replace("jsonb_array_length(g->'pools')>1000", "jsonb_array_length(g->'pools')>1001"))
    try {
      expect((await one('select cp7_supply_native.proof_kernel() is null r')).r).toBe(true)
      expect(await cmp(AT, true)).toMatchObject({ same: true, reused: 0, exhausted: 99 })
      expect(await errorOf(`select cp7_supply_native.prove_exhausted('${AT}',null,50)`)).toBe('P0001:CP7_SUPPLY_PROOF_KERNEL')
    } finally { await install(reconcile) }
    expect(await cmp(AT, true)).toMatchObject({ same: true, reused: 99 })
    // The supply run writer stores the proofs its own source found, in the
    // statement that read the facts; the next run reuses them for the same result.
    await installCaptureStubs(db)
    await db.execute('truncate cp7_supply_native.exhaustion_proofs')
    const run = async (req: string) => (await one(`select cp7_supply_native.capture('{}','${req}') r`)).r
    const r1 = await run('5e1f0000-0000-4000-8000-0000000000a1')
    expect(await one('select count(*)::int n,count(distinct captured_at)::int c from cp7_supply_native.exhaustion_proofs')).toEqual({ n: 99, c: 1 })
    const r2 = await run('5e1f0000-0000-4000-8000-0000000000a2')
    expect((await one('select count(*)::int n from cp7_supply_native.exhaustion_proofs')).n).toBe(99)
    expect([r1.source_state, r2.source_state, r2.run_id === r1.run_id]).toEqual(['UNCHANGED', 'UNCHANGED', false])
    const runs = (await one(`select (select result::text from cp7_supply_native.runs order by request_id limit 1)=(select result::text from cp7_supply_native.runs order by request_id desc limit 1) same,
      (select result::text from cp7_supply_native.runs limit 1)=cp7_supply_native.build(cp7_baseline_native.source()||jsonb_build_object('production_sources',cp7_supply_native.wip_source_at_1('${AT}')),'{}')::text predecessor`))
    expect(runs).toEqual({ same: true, predecessor: true })
    // A malformed batch reuses nothing and still classifies as before.
    const part = `cp7_wip.capture_cutting_sources(array(select id from erp.cutting_groups where material_issue_posted order by id limit 50),'${AT}')`
    expect((await one(`select jsonb_array_length(cp7_supply_native.batch_reuse(jsonb_set(${part},'{facts,unknown}','[{"id":"x"}]'),cp7_supply_native.proof_kernel())->'hit') r`)).r).toBe(0)
    expect((await one(`select cp7_supply_native.batch_verdict(jsonb_set(${part},'{facts,unknown}','[{"id":"x"}]'),cp7_supply_native.proof_kernel())->'spent'=cp7_supply_native.batch_verdict(${part},null)->'spent' r`)).r).toBe(true)
    expect((await one(`select cp7_supply_native.exhausted_groups(${part})=cp7_supply_native.exhausted_groups_1(${part}) r`)).r).toBe(true)
  }, 600_000)
})
