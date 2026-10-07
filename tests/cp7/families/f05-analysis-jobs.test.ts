// @vitest-environment node
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { openRuntime } from './f04/runtime.mjs'

// Pure SQL control of the P19 job/segment layer over explicit stand-ins for the
// analysis source, compiler and access reader. It proves the state machine,
// exact segmentation/hashes, refusals and privileges of analysis-jobs.sql only;
// Native/Auth/HTTP/browser qualification is the separate CP7 P19 transport suite.
const A = '00000000-0000-4000-8000-0000000000a1'
const B = '00000000-0000-4000-8000-0000000000b2'
const STANDINS = `
 create schema cp7_private;
 create function cp7_private.immutable_run()returns trigger language plpgsql set search_path='' as $$
  begin raise exception using errcode='55000',message='CP7_RUN_IMMUTABLE';end $$;
 create schema cp7_analysis_native authorization cp7_capture;
 create table cp7_analysis_native.runs(id uuid primary key,actor uuid not null,request_id uuid not null,query jsonb not null,
  captured_at timestamptz not null,access_at_capture jsonb not null,facts jsonb not null,result jsonb not null,
  dependency_hash text not null,unique(actor,request_id));
 alter table cp7_analysis_native.runs owner to cp7_capture;
 create trigger immutable_analysis_run before update or delete on cp7_analysis_native.runs for each row execute function cp7_private.immutable_run();
 create schema cp7_schedule_native;create schema cp7_planning;
 grant usage on schema cp7_private,cp7_schedule_native,cp7_planning to cp7_capture;
 create function cp7_schedule_native.access_now(writing boolean)returns jsonb language plpgsql stable set search_path='' as $$
  begin
   if coalesce(current_setting('test.actor',true),'')='' then raise exception using errcode='42501',message='CP7_ACCESS_DENIED';end if;
   return jsonb_build_object('actor',current_setting('test.actor'),'permissions',coalesce(current_setting('test.perm',true),'view'));
  end $$;
 create function cp7_planning.history_query(q jsonb)returns jsonb language sql immutable set search_path='' as $$select q$$;
 create function cp7_analysis_native.source(q jsonb)returns jsonb language plpgsql volatile set search_path='' as $$
  begin
   perform pg_sleep(coalesce(nullif(current_setting('test.sleep',true),'')::numeric,0));
   if current_setting('test.fail',true)<>'' then raise exception '%',current_setting('test.fail');end if;
   return jsonb_build_object('captured_at','2026-10-06T00:00:00Z','version',coalesce(nullif(current_setting('test.version',true),''),'1'),
    'facts',jsonb_build_object('products',jsonb_build_array(jsonb_build_object('root_id','r1','size_id','s1','sku','SKU-1','product_name','Kaos ✓',
     'commercial',jsonb_build_array(jsonb_build_object('sku','SKU-1C'))))),'financial_source',null);
  end $$;
 create function cp7_analysis_native.build(c jsonb,q jsonb,p_run uuid,a jsonb)returns jsonb language sql stable set search_path='' as $$
  select jsonb_build_object('run_id',p_run,'scope',a->>'actor','body',
   repeat(coalesce(nullif(current_setting('test.unit',true),''),'x'),coalesce(nullif(current_setting('test.repeat',true),'')::integer,10)))$$;
 create function cp7_analysis_native.fingerprint(c jsonb)returns text language sql immutable set search_path='' as $$select md5(c::text)$$;
 -- The finance-mode pair as in analysis.sql / analysis-finance.sql: DEFERRED
 -- adds no financial source and marks the facts; only two modes exist.
 create function cp7_analysis_native.finance_mode(facts jsonb)returns text language sql immutable set search_path='' as $$
  select case when facts->>'financial_capture'='DEFERRED'then 'DEFERRED'else 'INCLUDED'end$$;
 create function cp7_analysis_native.source_for(q jsonb,p_finance text)returns jsonb language plpgsql volatile set search_path='' as $$
  begin
   if p_finance='INCLUDED'then return cp7_analysis_native.source(q);end if;
   if p_finance is distinct from 'DEFERRED'then raise exception 'CP7_ANALYSIS_FINANCE_MODE';end if;
   return cp7_analysis_native.source(q)||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
  end $$;
 alter function cp7_analysis_native.finance_mode(jsonb)owner to cp7_capture;
 alter function cp7_analysis_native.source_for(jsonb,text)owner to cp7_capture;
 alter function cp7_analysis_native.source(jsonb)owner to cp7_capture;
 alter function cp7_analysis_native.build(jsonb,jsonb,uuid,jsonb)owner to cp7_capture;
 alter function cp7_analysis_native.fingerprint(jsonb)owner to cp7_capture;`

type Db = Awaited<ReturnType<typeof openRuntime>>
const as = (actor: string, extra = '') => `set role authenticated;set test.actor='${actor}';${extra}`
const q = (mode = 'AS_SOLD') => `'{"from_date":"2026-10-01","through_date":"2026-10-06","group_mode":"${mode}"}'::jsonb`
async function call(db: Db, actor: string, sql: string, extra = '') {
 const out = String(await db.execute(`${as(actor, extra)}select (${sql})::text;`)).trim().split('\n').at(-1) as string
 return JSON.parse(out)
}
async function refused(db: Db, actor: string, sql: string, code: string, extra = '') {
 let message = ''
 try { await db.execute(`${as(actor, extra)}select (${sql})::text;`) } catch (error) { message = String((error as { stderr?: string }).stderr ?? error) }
 expect(message).toContain(code)
}
const sha = (text: string) => createHash('sha256').update(Buffer.from(text, 'utf8')).digest('hex')

test('P19 analysis job states, exact segmented Original, refusals and privileges', async () => {
 const db = await openRuntime({ commandTimeoutMs: 300_000 })
 try {
  await db.execute(`begin;${STANDINS}\n${readFileSync('scripts/cp7-src/planning/analysis-jobs.sql', 'utf8')}\ncommit;`)
  const r1 = '00000000-0000-4000-8000-000000000101'
  const requested = await call(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${r1}')`)
  expect(requested).toMatchObject({ contract_version: 'cp7.native-analysis-job.v1', state: 'WAITING', attempts: 1, run_id: null, failure: null, apply_enabled: false, production_go: false })
  expect((await call(db, A, `public.erp_cp7_get_analysis_job_v1('${r1}')`)).state).toBe('WAITING')
  // A held compute lock is the running worker; status reads never take it.
  const running = String(await db.execute(`${as(A)}begin;select pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS:${A}:${r1}',0));
   select (public.erp_cp7_get_analysis_job_v1('${r1}')->>'state');rollback;`)).trim().split('\n').at(-1)
  expect(running).toBe('RUNNING')
  await refused(db, A, `public.erp_cp7_request_analysis_job_v1(${q('RESTATED')},'${r1}')`, 'CP7_ANALYSIS_REQUEST_CHANGED')
  // Multibyte characters across segment boundaries: 3 code points per unit.
  const done = await call(db, A, `public.erp_cp7_run_analysis_job_v1('${r1}')`, `set test.unit='a😀é';set test.repeat='1500000';`)
  expect(done).toMatchObject({ state: 'DONE', attempts: 1, failure: null })
  expect(await call(db, A, `public.erp_cp7_run_analysis_job_v1('${r1}')`)).toEqual({ ...done, state: 'DONE' })
  expect((await call(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${r1}')`)).run_id).toBe(done.run_id)
  const manifest = await call(db, A, `public.erp_cp7_read_analysis_manifest_v1('${done.run_id}')`)
  expect(manifest).toMatchObject({ contract_version: 'cp7.native-analysis-manifest.v1', run_id: done.run_id, request_id: r1, source_state: 'UNCHANGED', apply_enabled: false, production_go: false })
  expect(manifest.document.segment_characters).toBe(2000000)
  expect(manifest.document.segment_count).toBe(Math.ceil(manifest.document.characters / 2000000))
  expect(manifest.document.segment_count).toBeGreaterThanOrEqual(3)
  const parts: string[] = []
  for (let i = 0; i < manifest.document.segment_count; i++) {
   const s = await call(db, A, `public.erp_cp7_read_analysis_segment_v1('${done.run_id}',${i},'${manifest.access_epoch}')`)
   expect(s).toMatchObject({ contract_version: 'cp7.native-analysis-segment.v1', run_id: done.run_id, index: i, segment_count: manifest.document.segment_count,
    document_sha256: manifest.document.sha256, document_utf8_bytes: manifest.document.utf8_bytes })
   expect(Buffer.byteLength(s.body, 'utf8')).toBe(s.utf8_bytes)
   expect(s.utf8_bytes).toBeLessThanOrEqual(8000000)
   expect(sha(s.body)).toBe(s.sha256)
   // substr(body,i*n+1,n): every segment but the last holds exactly n code points.
   if (i < manifest.document.segment_count - 1) expect([...s.body].length).toBe(2000000)
   parts.push(s.body)
  }
  const whole = parts.join('')
  expect(Buffer.byteLength(whole, 'utf8')).toBe(manifest.document.utf8_bytes)
  expect(sha(whole)).toBe(manifest.document.sha256)
  const original = JSON.parse(whole)
  expect(original).toMatchObject({ contract_version: 'cp7.native-analysis-run.v1', run_id: done.run_id, request_id: r1, apply_enabled: false, production_go: false, financial_source: null,
   product_labels: [{ target_key: 'r1:s1', sku: 'SKU-1C', product_name: 'Kaos ✓' }] })
  expect(original.analysis.body).toBe('a😀é'.repeat(1500000))
  expect(original).not.toHaveProperty('source_state')
  // Refusals: changed access epoch, another actor, missing index, stale source.
  await refused(db, A, `public.erp_cp7_read_analysis_segment_v1('${done.run_id}',0,'${manifest.access_epoch}')`, 'CP7_ANALYSIS_ACCESS_CHANGED', `set test.perm='view,revoked-one';`)
  await refused(db, B, `public.erp_cp7_read_analysis_segment_v1('${done.run_id}',0,'${manifest.access_epoch}')`, 'CP7_ANALYSIS_ACCESS_CHANGED')
  const epochB = String(await db.execute(`set test.actor='${B}';select encode(sha256(convert_to(cp7_schedule_native.access_now(false)::text,'UTF8')),'hex');`)).trim()
  await refused(db, B, `public.erp_cp7_read_analysis_segment_v1('${done.run_id}',0,'${epochB}')`, 'CP7_ANALYSIS_RUN_UNAVAILABLE')
  await refused(db, B, `public.erp_cp7_read_analysis_manifest_v1('${done.run_id}')`, 'CP7_ANALYSIS_RUN_UNAVAILABLE')
  await refused(db, A, `public.erp_cp7_read_analysis_segment_v1('${done.run_id}',${manifest.document.segment_count},'${manifest.access_epoch}')`, 'CP7_ANALYSIS_SEGMENT_UNAVAILABLE')
  await refused(db, '', `public.erp_cp7_get_analysis_job_v1('${r1}')`, 'CP7_ACCESS_DENIED')
  expect((await call(db, A, `public.erp_cp7_read_analysis_manifest_v1('${done.run_id}')`, `set test.version='2';`)).source_state).toBe('ARCHIVED_STALE')
  // The existing statement limit stops a worker: FAILED is committed, nothing else.
  const r2 = '00000000-0000-4000-8000-000000000102'
  await call(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${r2}')`)
  const stopped = await call(db, A, `public.erp_cp7_run_analysis_job_v1('${r2}')`, `set test.sleep='2';set statement_timeout='300ms';`)
  expect(stopped).toMatchObject({ state: 'FAILED', run_id: null, failure: { sqlstate: '57014', code: 'CP7_ANALYSIS_JOB_STOPPED' } })
  expect(stopped.finished_at).toBeTruthy()
  expect((await db.query(`select count(*)::int n from cp7_analysis_native.runs where request_id='${r2}'`))[0].n).toBe(0)
  expect((await call(db, A, `public.erp_cp7_run_analysis_job_v1('${r2}')`)).state).toBe('FAILED')
  const again = await call(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${r2}')`)
  expect(again).toMatchObject({ state: 'WAITING', attempts: 2, failure: null, finished_at: null })
  expect(new Date(again.started_at).getTime()).toBeGreaterThan(new Date(stopped.started_at).getTime())
  expect((await call(db, A, `public.erp_cp7_run_analysis_job_v1('${r2}')`)).state).toBe('DONE')
  // A refusal keeps its own CP7 code; any other error is not echoed.
  for (const [id, failure, code] of [['00000000-0000-4000-8000-000000000104', 'CP7_ANALYSIS_EDGE_TARGET_UNPROVEN', 'CP7_ANALYSIS_EDGE_TARGET_UNPROVEN'],
   ['00000000-0000-4000-8000-000000000105', 'division by zero (internal)', 'CP7_ANALYSIS_JOB_ERROR']]) {
   await call(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${id}')`)
   expect((await call(db, A, `public.erp_cp7_run_analysis_job_v1('${id}')`, `set test.fail='${failure}';`)).failure).toEqual({ sqlstate: 'P0001', code })
  }
  // An ordinary capture already owning the UUID is the job's result.
  const r3 = '00000000-0000-4000-8000-000000000103', run3 = '00000000-0000-4000-8000-000000000903'
  await db.execute(`insert into cp7_analysis_native.runs values('${run3}','${A}','${r3}',${q()},now(),'{}','{"facts":{"products":[]}}','{"run_id":"${run3}"}','h')`)
  expect(await call(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${r3}')`)).toMatchObject({ state: 'DONE', run_id: run3 })
  await refused(db, A, `public.erp_cp7_request_analysis_job_v1(${q('RESTATED')},'${r3}')`, 'CP7_ANALYSIS_REQUEST_CHANGED')
  await refused(db, A, `public.erp_cp7_run_analysis_job_v1('00000000-0000-4000-8000-000000000199')`, 'CP7_ANALYSIS_JOB_UNAVAILABLE')
  // Finance on demand: an operational job stores the DEFERRED mark; one UUID is one mode.
  const r4 = '00000000-0000-4000-8000-000000000106'
  expect((await call(db, A, `public.erp_cp7_request_operational_analysis_job_v1(${q()},'${r4}')`)).state).toBe('WAITING')
  await refused(db, A, `public.erp_cp7_request_analysis_job_v1(${q()},'${r4}')`, 'CP7_ANALYSIS_REQUEST_CHANGED')
  const ops = await call(db, A, `public.erp_cp7_run_analysis_job_v1('${r4}')`)
  expect(ops.state).toBe('DONE')
  expect((await db.query(`select facts->>'financial_capture' mode,(select finance from cp7_analysis_jobs.jobs where request_id='${r4}') job from cp7_analysis_native.runs where id='${ops.run_id}'`))[0]).toEqual({ mode: 'DEFERRED', job: 'DEFERRED' })
  expect((await call(db, A, `public.erp_cp7_read_analysis_manifest_v1('${ops.run_id}')`)).source_state).toBe('UNCHANGED')
  expect((await call(db, A, `public.erp_cp7_request_operational_analysis_job_v1(${q()},'${r4}')`)).run_id).toBe(ops.run_id)
  await refused(db, A, `public.erp_cp7_request_operational_analysis_job_v1(${q()},'${r1}')`, 'CP7_ANALYSIS_REQUEST_CHANGED')
  await refused(db, A, `public.erp_cp7_request_operational_analysis_job_v1(${q()},'${r3}')`, 'CP7_ANALYSIS_REQUEST_CHANGED')
  // Privileges and immutability.
  const privileges = (await db.query(`select bool_or(has_table_privilege(r,t,'SELECT,INSERT,UPDATE,DELETE'))tables,
   bool_or(has_schema_privilege(r,'cp7_analysis_jobs','USAGE'))schema,
   bool_or(has_function_privilege(r,'cp7_analysis_jobs.run(uuid)','EXECUTE'))private_run
   from unnest(array['anon','authenticated','service_role'])r,unnest(array['cp7_analysis_jobs.jobs','cp7_analysis_jobs.documents','cp7_analysis_jobs.segments'])t`))[0]
  expect(privileges).toEqual({ tables: false, schema: false, private_run: false })
  const execute = (await db.query(`select p.proname,has_function_privilege('authenticated',p.oid,'EXECUTE')a,has_function_privilege('anon',p.oid,'EXECUTE')n,
   pg_get_userbyid(p.proowner)o,p.prosecdef d from pg_proc p where p.pronamespace='public'::regnamespace and p.proname like 'erp_cp7_%analysis_%' order by 1`))
  expect(execute).toEqual(['erp_cp7_get_analysis_job_v1', 'erp_cp7_read_analysis_manifest_v1', 'erp_cp7_read_analysis_segment_v1', 'erp_cp7_request_analysis_job_v1', 'erp_cp7_request_operational_analysis_job_v1', 'erp_cp7_run_analysis_job_v1']
   .map(proname => ({ proname, a: true, n: false, o: 'cp7_capture', d: true })))
  for (const table of ['segments', 'documents']) {
   let message = ''
   try { await db.execute(`update cp7_analysis_jobs.${table} set run_id=run_id`) } catch (error) { message = String((error as { stderr?: string }).stderr) }
   expect(message).toContain('CP7_RUN_IMMUTABLE')
  }
 } finally { await db.close() }
}, 300_000)
