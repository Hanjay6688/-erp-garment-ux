// @vitest-environment node
import { execFileSync } from 'node:child_process'
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS as NETTING_DEFECTS } from './f04/netting-fixture.mjs'
import { DEFECTS as ALLOCATION_DEFECTS, allocationInput, memoProbe } from './f04/allocation-fixture.mjs'
import { functionBlocks } from './f04/schedule-scenario-fixture.mjs'
import { STAGED_DEFECTS, installStagedControls, runJob, stagedInput } from './f04/staged-analysis-fixture.mjs'

// P19 staged analysis PROTOTYPE: the staged job's Original equals the single
// compiler's byte for byte, and every refusal is the single path's refusal,
// at sizes both can run. Tiny chunk bounds put chunk edges everywhere.
// Kernel stand-ins only (schedule build, fabric, accessories); LOCAL proof.
const SMALL = { targets_per_chunk: 7, pairs_per_chunk: 45, visits_per_allocation_step: 100000, allocation_targets_per_step: 4, targets_per_segment_unit: 10,
  job_targets: 5000, job_pairs: 1000000, job_matching_products: 10000 }
const uuid = (n: number) => `03000000-0000-4000-8000-${n.toString(16).padStart(12, '0')}`
type Case = { seed: number, defect: string | null, shape: Record<string, unknown>, c: unknown }
type Row = Record<string, any>

test('P19 staged allocation equals allocate byte for byte, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installStagedControls(db)
    const cases: { seed: number, defect: string | null, v: unknown }[] = [null, 'BAD_SOURCE', 'BAD_TARGET'].map(variant => ({ seed: 0, defect: `MEMO_PROBE_${variant ?? 'VALID'}`, v: memoProbe(variant) }))
    for (let seed = 1; seed <= 12; seed++) for (const defect of ALLOCATION_DEFECTS)
      cases.push({ seed, defect, v: allocationInput(seed, { positions: 6 + seed % 17, targets: 3 + seed % 13, pools: 2 + seed % 4, ties: seed % 5 === 0, defect }) })
    for (let seed = 101; seed <= 103; seed++) cases.push({ seed, defect: null, v: allocationInput(seed, { positions: 60, targets: 80, pools: 12, ties: seed === 103 }) })
    let compared = 0, scenarios = 0, multiStep = 0, edges = 0
    const refusals = new Set<string>()
    for (const step of [1, 3, 1000]) for (let i = 0; i < cases.length; i += 40) {
      const batch = cases.slice(i, i + 40)
      const rows = (await db.query(`select public.st_alloc(x.value,${step}) r from jsonb_array_elements(${jsonArg(batch.map(k => k.v))}) with ordinality x order by x.ordinality`)).map((r: Row) => r.r)
      rows.forEach((row: Row, k: number) => {
        const { seed, defect } = batch[k]
        expect([step, seed, defect, row.s1]).toEqual([step, seed, defect, row.s0])
        if (row.s0 !== 'NO_ERROR') { refusals.add(row.s0); return }
        expect([step, seed, defect, row.same]).toEqual([step, seed, defect, true])
        compared++; if (row.status === 'SCENARIO') scenarios++; if (row.steps > 1) multiStep++; edges += row.edges
      })
    }
    console.log(JSON.stringify({ cases: cases.length, compared, scenarios, multi_step: multiStep, edges, refusals: [...refusals].length }))
    expect(scenarios).toBeGreaterThan(500); expect(multiStep).toBeGreaterThan(300); expect(edges).toBeGreaterThan(400)
    for (const code of ['P0001:CP7_BASELINE_ALLOCATION_LIMIT', 'P0001:CP7_F04_ARRAY_LIMIT', 'P0001:CP7_WIP_MATCH_DUPLICATE', '22023:CP7_WIP_KEY',
      'P0001:CP7_BASELINE_TARGET_MATCH_BINDING', 'P0001:CP7_BASELINE_SOURCE_MATCH_BINDING', '22023:CP7_WIP_DUPLICATE_REF']) expect(refusals).toContain(code)
  } finally { await db.close() }
}, 900_000)

test('P19 linear check_allocations equals its predecessor, including the first refusal', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    // The predecessor is this file at the commit before the linear form.
    const base = execFileSync('git', ['log', '-1', '--format=%H', 'a68abf1e'], { encoding: 'utf8' }).trim()
    const old = functionBlocks(execFileSync('git', ['show', `${base}:scripts/cp7-src/wip/matching.sql`], { encoding: 'utf8' })).get('cp7_wip.check_allocations')
    if (!old || old.includes('i=repeated')) throw new Error('predecessor check_allocations not found')
    await db.execute(old.replace('create function cp7_wip.check_allocations(', 'create function cp7_wip.check_allocations_0(') + `
     create function public.ca_compare(v jsonb,with_edges boolean)returns jsonb language plpgsql as $s$
     declare a jsonb;r0 jsonb;r1 jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';e jsonb:='[]';
     begin
      if with_edges then begin e:=coalesce(cp7_baseline.allocate(v)->'allocation'->'edges','[]');exception when others then e:='[]';end;end if;
      a:=jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges',e);
      begin r0:=cp7_wip.check_allocations_0(v->'positions',a);exception when others then s0:=sqlstate||':'||sqlerrm;end;
      begin r1:=cp7_wip.check_allocations(v->'positions',a);exception when others then s1:=sqlstate||':'||sqlerrm;end;
      return jsonb_build_object('s0',s0,'s1',s1,'same',r0::text is not distinct from r1::text,'status',r0->>'status','edges',jsonb_array_length(e));
     end $s$;`)
    const cases: unknown[] = []
    for (let seed = 1; seed <= 15; seed++) for (const defect of ALLOCATION_DEFECTS) cases.push(allocationInput(seed, { positions: 6 + seed % 17, targets: 3 + seed % 13, pools: 2 + seed % 4, defect }))
    // Matching facts whose keys repeat or are not strings at several positions.
    for (let seed = 200; seed < 260; seed++) {
      const v = allocationInput(seed, { positions: 10, targets: 12, pools: 3 }) as any
      const side = seed % 2 ? v.matching.sources : v.matching.targets
      if (seed % 3 === 0) side.splice(seed % side.length, 0, { ...side[(seed * 7) % side.length] })
      if (seed % 4 === 0) side[(seed * 3) % side.length].key = seed % 8 === 0 ? 5 : { k: 1 }
      if (seed % 5 === 0) side.push({ ...side[0], key: String(side[0].key) + ' ' })
      if (seed % 7 === 0) side.splice(1, 0, { key: null })
      cases.push(v)
    }
    const seen = new Set<string>(); let same = 0
    for (const withEdges of [false, true]) for (let i = 0; i < cases.length; i += 50) {
      const rows = (await db.query(`select public.ca_compare(x.value,${withEdges}) r from jsonb_array_elements(${jsonArg(cases.slice(i, i + 50))}) with ordinality x order by x.ordinality`)).map((r: Row) => r.r)
      for (const row of rows) { expect(row.s1).toBe(row.s0); if (row.s0 === 'NO_ERROR') { expect(row.same).toBe(true); same++ } else seen.add(row.s0) }
    }
    console.log(JSON.stringify({ cases: cases.length * 2, same, refusals: [...seen] }))
    expect(same).toBeGreaterThan(600)
    for (const code of ['P0001:CP7_WIP_MATCH_DUPLICATE', '22023:CP7_WIP_KEY', 'P0001:CP7_WIP_MATCH_SNAPSHOT']) expect(seen).toContain(code)
  } finally { await db.close() }
}, 900_000)

test('P19 staged job Original equals the single build byte for byte; refusals are the same refusals', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installStagedControls(db, { bounds: SMALL })
    const cases: Case[] = []
    const shapes = [{ targets: 40, positions: 16, roots: 14, models: 3, complete: true }, { targets: 30, positions: 24, roots: 9, models: 2, complete: false },
      { targets: 9, positions: 3, roots: 4, models: 2, complete: true }]
    for (let seed = 1; seed <= 3; seed++) for (const defect of [...NETTING_DEFECTS, ...STAGED_DEFECTS])
      cases.push({ seed, defect, shape: shapes[seed - 1], c: stagedInput(4000 + seed * 100 + cases.length, shapes[seed - 1], defect) })
    for (let seed = 10; seed < 22; seed++) cases.push({ seed, defect: null, shape: shapes[seed % 3], c: stagedInput(5000 + seed, shapes[seed % 3]) })
    let done = 0, allocated = 0, edges = 0, confirmed = 0, multiPair = 0, multiAlloc = 0
    const refusals = new Set<string>(), divergences: string[] = []
    for (let i = 0; i < cases.length; i += 10) {
      const batch = cases.slice(i, i + 10)
      const rows = (await db.query(`select public.st_case(x.value,('03000000-0000-4000-8000-'||lpad(to_hex(${i}+x.ordinality::integer),12,'0'))::uuid) r
        from jsonb_array_elements(${jsonArg(batch.map(k => k.c))}) with ordinality x order by x.ordinality`)).map((r: Row) => r.r)
      rows.forEach((row: Row, k: number) => {
        const { seed, defect } = batch[k], id = [seed, defect]
        if (defect === 'MATCH_LIMIT') {
          // The one intended difference at these sizes: 5001 matching products
          // exceed the single call's 5000 but not the job's declared 10000.
          expect([...id, row.single, row.single_code, row.job]).toEqual([...id, 'REFUSED', 'CP7_NETTING_MATCH_SOURCE_LIMIT', 'DONE'])
          divergences.push(`${seed}:${defect}`); return
        }
        if (row.single === 'REFUSED') {
          const code = /^CP7_[A-Z0-9_]+$/.test(row.single_code) ? row.single_code : 'CP7_ANALYSIS_STAGE_ERROR'
          expect([...id, row.job, row.failure?.sqlstate, row.failure?.code]).toEqual([...id, 'FAILED', row.single_sqlstate, code])
          refusals.add(`${row.single_sqlstate}:${row.single_code}`); return
        }
        expect([...id, row.job, row.same, row.text_same, row.document_same, row.netting_rows_same, row.match_results_same, row.allocation_same])
          .toEqual([...id, 'DONE', true, true, true, true, true, true])
        done++; if (row.allocation === 'SCENARIO') allocated++; edges += row.edges; confirmed += row.confirmed
        if ((row.units.NET_PAIRS ?? 0) > 1) multiPair++; if ((row.units.ALLOC_STEP ?? 0) > 1) multiAlloc++
      })
    }
    console.log(JSON.stringify({ cases: cases.length, done, allocated, edges, confirmed, multi_pair_chunks: multiPair, multi_alloc_steps: multiAlloc, divergences, refusals: [...refusals] }))
    expect(done).toBeGreaterThanOrEqual(75); expect(allocated).toBeGreaterThanOrEqual(30); expect(edges).toBeGreaterThanOrEqual(30); expect(confirmed).toBeGreaterThan(300)
    expect(multiPair).toBeGreaterThanOrEqual(40); expect(multiAlloc).toBeGreaterThanOrEqual(25); expect(divergences.length).toBe(3)
    for (const code of ['P0001:CP7_NETTING_WORK_LIMIT', 'P0001:CP7_NETTING_NATIVE_PRODUCT_MISSING', '21000:more than one row returned by a subquery used as an expression'])
      expect(refusals).toContain(code)
  } finally { await db.close() }
}, 1_800_000)

test('P19 staged job: progress from stored rows, retry after the statement limit, refusal, no double worker, immutable outputs', async () => {
  const db = await openRuntime({ commandTimeoutMs: 600_000 })
  try {
    await installStagedControls(db, { bounds: SMALL })
    const c = stagedInput(7001, { targets: 40, positions: 16, roots: 14, models: 3, complete: true })
    // Every unit in its own session; progress only grows and is read back.
    const seen: Row[] = []
    const r = await runJob(db, c, { request: uuid(0x701), oneCallPerUnit: true, onStep: (s: Row) => { seen.push(s) } })
    expect(r.status.state).toBe('DONE')
    expect(seen.map(s => s.units_done)).toEqual(seen.map((_, i) => i + 1))
    expect(seen.at(-1)).toMatchObject({ state: 'DONE', plan_final: true, units_done: seen.at(-1)!.unit_count, apply_enabled: false, production_go: false })
    expect(seen.some(s => s.stage === 'NET_TARGETS' && s.targets_done_in_stage > 0 && s.targets_done_in_stage < s.targets_total)).toBe(true)
    const [{ ok }] = await db.query(`select (select result from cp7_analysis_native.runs where id='${r.run_id}')::text=(public.st_single(${jsonArg(c)},'${JSON.stringify({ from_date: '2026-05-01', through_date: '2026-05-30', group_mode: 'AS_SOLD' })}'::jsonb,'${r.run_id}','{"actor":"03000000-0000-4000-8000-000000000001","profile":{"role_code":"OWNER"}}'::jsonb)->'body')::text ok`)
    expect(ok).toBe(true)
    // The document of a staged run is cut by the unchanged job store.
    const [doc] = await db.query(`select segment_count,utf8_bytes from cp7_analysis_jobs.documents where run_id='${r.run_id}'`)
    expect(doc.segment_count).toBeGreaterThan(0)
    // A second session (dblink) holds what a unit needs. A unit stopped by the
    // statement limit is retried by the next call from the same stored inputs;
    // three stops fail the job with the stop code. A caller finding the job
    // held by a worker neither waits nor runs a unit.
    const [{ dir }] = await db.query(`select setting dir from pg_settings where name='unix_socket_directories'`)
    await db.execute('create extension if not exists dblink;')
    const second = (sql: string) => `select dblink_connect('w2','host=${dir} dbname=postgres user=cp7_f04_test');select dblink_exec('w2','${sql.replaceAll("'", "''")}');`
    const last = (out: unknown) => JSON.parse(String(out).trim().split('\n').at(-1)!)
    const [{ job }] = await db.query(`select cp7_analysis_stage.create_job('03000000-0000-4000-8000-000000000001','${uuid(0x702)}','{}'::jsonb,'{}'::jsonb,${jsonArg(c)}) job`)
    const stopped = async () => last(await db.execute(`${second('begin;lock table cp7_analysis_stage.outputs in exclusive mode')}
      set statement_timeout='400ms';select cp7_analysis_stage.step('${job}')::text;`))
    let s = await stopped()
    expect(s).toMatchObject({ state: 'RUNNING', units_done: 0, unit_attempts: 1 })
    s = last(await db.execute(`set statement_timeout='8s';select cp7_analysis_stage.step('${job}')::text;`))
    expect(s).toMatchObject({ state: 'RUNNING', units_done: 1, unit_attempts: 0 })
    await stopped(); await stopped(); s = await stopped()
    expect(s).toMatchObject({ state: 'FAILED', units_done: 1, failure: { unit: 1, sqlstate: '57014', code: 'CP7_ANALYSIS_STAGE_STOPPED' } })
    const [{ job: j3 }] = await db.query(`select cp7_analysis_stage.create_job('03000000-0000-4000-8000-000000000001','${uuid(0x703)}','{}'::jsonb,'{}'::jsonb,${jsonArg(c)}) job`)
    s = last(await db.execute(`${second(`begin;update cp7_analysis_stage.jobs set updated_at=updated_at where id='${j3}'`)}
      set statement_timeout='8s';select cp7_analysis_stage.step('${j3}')::text;`))
    expect(s).toMatchObject({ state: 'RUNNING', units_done: 0, worker_active: true })
    // A refusal fails the job at its unit with the single path's code.
    const bad = stagedInput(7002, { targets: 12, positions: 6, roots: 4, models: 2, complete: true }, 'MISSING_PRODUCT')
    const refused = await runJob(db, bad, { request: uuid(0x704), oneCallPerUnit: true })
    expect(refused.status).toMatchObject({ state: 'FAILED', failure: { code: 'CP7_NETTING_NATIVE_PRODUCT_MISSING' } })
    // The document cut equals store()'s cut (substr per segment) on a
    // multibyte document whose segment boundaries split no character, in two
    // units with the second starting mid-document.
    const run2 = '03000000-0000-4000-8000-00000000d0c0'
    await db.execute(`insert into cp7_analysis_native.runs select '${run2}'::uuid,actor,'${uuid(0xd0c)}'::uuid,query,captured_at,access_at_capture,facts,result,dependency_hash
       from cp7_analysis_native.runs where id='${r.run_id}';
      create table public.doc as select repeat('a😀é',1500000)||'✓x' body;
      select cp7_analysis_stage.document_row('${run2}',body) from public.doc;
      select cp7_analysis_stage.document_segments('${run2}',body,0,0) from public.doc;
      select cp7_analysis_stage.document_segments('${run2}',body,1,2) from public.doc;`)
    const [same] = await db.query(`select d.segment_count,d.characters,d.utf8_bytes=octet_length(doc.body) bytes_ok,
       d.sha256=encode(sha256(convert_to(doc.body,'UTF8')),'hex') hash_ok,
       bool_and(s.body=substr(doc.body,s.idx*2000000+1,2000000) and s.utf8_bytes=octet_length(s.body)
        and s.sha256=encode(sha256(convert_to(s.body,'UTF8')),'hex')) segments_ok,count(s.*) n
      from public.doc doc cross join cp7_analysis_jobs.documents d join cp7_analysis_jobs.segments s on s.run_id=d.run_id
      where d.run_id='${run2}' group by 1,2,3,4`)
    expect(same).toMatchObject({ segment_count: 3, characters: 4500002, bytes_ok: true, hash_ok: true, segments_ok: true, n: 3 })
    // Outputs and per-target rows never change once written.
    for (const t of ['outputs', 'target_rows', 'snapshots'])
      await expect(db.execute(`update cp7_analysis_stage.${t} set job_id=job_id where job_id='${r.job}';`)).rejects.toThrow(/CP7_RUN_IMMUTABLE/)
  } finally { await db.close() }
}, 900_000)
