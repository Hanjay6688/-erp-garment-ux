// Structural in-memory SQL/trigger controls only. No Native, Auth or ERP claim.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '../..')
const output = resolve(process.argv[2] ?? resolve(here, 'evidence/LOCAL_TRIGGER_FIRST.json'))
const modulePath = process.env.F04_PGLITE_MODULE
if (!modulePath) throw new Error('Set F04_PGLITE_MODULE to the existing pinned local PGlite module.')
const { PGlite } = await import(pathToFileURL(modulePath).href)
const sql = execFileSync('python3', ['-B', '-c', `
import ast,json
from pathlib import Path
p=Path('scripts/cp7_credit_correction_de/e_cases.py');s=p.read_text()
node=next(n for n in ast.walk(ast.parse(s))if isinstance(n,ast.FunctionDef)and n.name=='late_failure')
found=[n.args[0].value for n in ast.walk(node)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='execute'and n.args and isinstance(n.args[0],ast.Constant)and isinstance(n.args[0].value,str)and 'create function cp7_credit_note_carry_de.test_post_failure' in n.args[0].value]
assert len(found)==1
print(json.dumps(found[0]))
`], { cwd: root, encoding: 'utf8' })
const triggerSQL = JSON.parse(sql)
const hash = value => createHash('sha256').update(value).digest('hex')
const report = {
  status: 'INCOMPLETE', scope: 'LOCAL_STRUCTURAL_SQL_TRIGGER_DOUBLES_NOT_NATIVE',
  trigger_source: 'EXACT_LITERAL_EXTRACTED_FROM_SUCCESSOR_LATE_FAILURE_ONLY',
  trigger_sha256: hash(triggerSQL), controls: [],
  declared_doubles: ['minimal ERP/work/request/revision/event/journal tables', 'fixed local auth.uid',
    'materialized journal JSON/hash helper signatures', 'three Native/historical/profile guard stand-ins'],
  Native_execution: false, actual_E_cases: 0, actual_Auth: false, remote_calls: 0,
  production_go: false, independent_acceptance: false,
}
const db = new PGlite()
const actor = '00000000-0000-0000-0000-000000000001'
const original = '00000000-0000-0000-0000-000000000002'
const replacement = '00000000-0000-0000-0000-000000000003'
const operation = '00000000-0000-0000-0000-000000000004'
const request = '00000000-0000-0000-0000-000000000005'
const revision = '00000000-0000-0000-0000-000000000006'
const event = '00000000-0000-0000-0000-000000000007'
const journal = '00000000-0000-0000-0000-000000000008'
const saleJournal = '00000000-0000-0000-0000-000000000009'
const contextTables = ['erp.journal_entries','erp.journal_lines','erp.sales_headers','erp.sales_items',
  'cp7_note.requests','cp7_note.context','cp7_note.revisions','cp7_sales.command_context',
  'cp7_credit.consumption_events','cp7_credit_note_carry_de.work_v1',
  'cp7_credit_note_carry_de.assignments_v1','cp7_credit_note_carry_de.operations_v1']
const census = async () => {
  const result = {}
  for (const table of contextTables) {
    result[table] = (await db.query(`select coalesce(jsonb_agg(j order by j::text),'[]'::jsonb) document from(select to_jsonb(t)j from ${table} t)x`)).rows[0].document
  }
  result.sequences = (await db.query('select * from pg_catalog.pg_sequences order by schemaname,sequencename')).rows
  return result
}
const ERPTriggers = async () => (await db.query(`select coalesce(jsonb_agg(to_jsonb(t)order by t.oid),'[]'::jsonb) document
  from pg_catalog.pg_trigger t join pg_catalog.pg_class c on c.oid=t.tgrelid
  join pg_catalog.pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'`)).rows[0].document
const setup = `
create schema erp;create schema cp7_note;create schema cp7_sales;create schema cp7_credit;create schema cp7_credit_note_carry_de;create schema auth;
create function auth.uid()returns uuid language sql stable as $$select '${actor}'::uuid$$;
create table erp.journal_entries(id uuid primary key,status text,source_type text,source_id uuid);
create table erp.journal_lines(id uuid primary key,journal_entry_id uuid,account_id text,debit numeric,credit numeric);
create table erp.sales_headers(id uuid primary key,status text);
create table erp.sales_items(id uuid primary key,sale_id uuid,line_total numeric);
create table cp7_note.requests(actor uuid,request_id uuid,payload jsonb,expected_version text,response jsonb);
create table cp7_note.context(backend_pid integer,transaction_id bigint);
create table cp7_sales.command_context(backend_pid integer,transaction_id bigint);
create table cp7_note.revisions(id uuid,root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid,revision integer,actor uuid,request_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,event_kind text,target_sale_id uuid,amount numeric,journal_id uuid,cohort_id uuid);
create table cp7_credit_note_carry_de.work_v1(operation_id uuid primary key,backend_pid integer,transaction_id bigint,actor uuid,request_id uuid,
 source_sale_id uuid,replacement_sale_id uuid,revision_id uuid,payload jsonb,expected_version text,phase text,basis jsonb,actual_proof jsonb);
create table cp7_credit_note_carry_de.assignments_v1(operation_id uuid,event_id uuid,event_kind text,historical_target_id uuid,root_sale_id uuid,
 replacement_sale_id uuid,event_snapshot jsonb,journal_snapshot jsonb,event_sha256 text,journal_sha256 text);
create table cp7_credit_note_carry_de.operations_v1(operation_id uuid primary key,actor uuid,request_id uuid,source_sale_id uuid,replacement_sale_id uuid,
 revision_id uuid,payload jsonb,expected_version text,proof jsonb,response jsonb);
create function cp7_credit.materialized_journal_payload(p_id uuid)returns jsonb language sql stable as $$
 select jsonb_build_object('journal',to_jsonb(j)-'status','lines',coalesce((select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id),'[]'))
 from erp.journal_entries j where j.id=p_id$$;
create function cp7_credit.pg_jsonb_sha256(p jsonb)returns text language sql immutable as $$select encode(sha256(convert_to(p::text,'UTF8')),'hex')$$;
create function cp7_credit.assert_source_native_trigger_census_v1()returns void language plpgsql as $$begin return;end$$;
create function cp7_credit_note_carry_de.assert_historical_v1(p uuid)returns void language plpgsql as $$begin return;end$$;
create function cp7_credit.assert_current_materialized_profile(p uuid,r uuid,l uuid)returns void language plpgsql as $$begin return;end$$;
`
const seed = `
insert into erp.journal_entries values('${journal}','POSTED','LOCAL_DOUBLE_APPLY','${event}'),('${saleJournal}','POSTED','SALE','${replacement}');
insert into erp.journal_lines values('10000000-0000-0000-0000-000000000001','${journal}','LOCAL_DOUBLE_AR',0,80),
 ('10000000-0000-0000-0000-000000000002','${saleJournal}','LOCAL_DOUBLE_AR',550,0);
insert into erp.sales_headers values('${original}','REVERSED'),('${replacement}','PARTIAL_PAID');
insert into erp.sales_items values('20000000-0000-0000-0000-000000000001','${replacement}',550);
insert into cp7_credit.consumption_events values('${event}','APPLY','${original}',80,'${journal}','30000000-0000-0000-0000-000000000001');
insert into cp7_note.requests values('${actor}','${request}','{"LOCAL_STRUCTURAL_DOUBLE":true}','1','{"kind":"COMMITTED_OUTCOME","LOCAL_STRUCTURAL_DOUBLE":true}');
insert into cp7_note.revisions values('${revision}','${original}','${original}','${replacement}',1,'${actor}','${request}');
insert into cp7_credit_note_carry_de.work_v1
 select '${operation}',pg_backend_pid(),txid_current(),'${actor}','${request}','${original}','${replacement}','${revision}',
 '{"LOCAL_STRUCTURAL_DOUBLE":true}'::jsonb,'1','MATERIALIZED',
 jsonb_build_object('incoming_facts',jsonb_build_array(jsonb_build_object('event',to_jsonb(e),'journal',cp7_credit.materialized_journal_payload(e.journal_id)))),
 jsonb_build_object('replacement_journal',cp7_credit.materialized_journal_payload('${saleJournal}'),'no_consumer_money_created',true,'same_physical_and_HPP',true)
 from cp7_credit.consumption_events e where id='${event}';
insert into cp7_credit_note_carry_de.assignments_v1
 select '${operation}',e.id,'APPLY','${original}','${original}','${replacement}',to_jsonb(e),cp7_credit.materialized_journal_payload(e.journal_id),
 cp7_credit.pg_jsonb_sha256(to_jsonb(e)),cp7_credit.pg_jsonb_sha256(cp7_credit.materialized_journal_payload(e.journal_id))from cp7_credit.consumption_events e where id='${event}';
`
const insert = `insert into cp7_credit_note_carry_de.operations_v1
 select w.operation_id,w.actor,w.request_id,w.source_sale_id,w.replacement_sale_id,w.revision_id,w.payload,w.expected_version,to_jsonb(w),
 '{"kind":"COMMITTED_OUTCOME","LOCAL_STRUCTURAL_DOUBLE":true}'::jsonb from cp7_credit_note_carry_de.work_v1 w`
const expectedGuardNames = ['assert_source_native_trigger_census_v1','assert_historical_v1','assert_current_materialized_profile']

async function vector(name, mutation = '', expected = 'E_TEST_LATE_POINT_SETUP_FAILED', detailCheck) {
  await db.exec('begin')
  try {
    await db.exec(seed)
    if (mutation) await db.exec(mutation)
    const before = await census()
    const triggers = await ERPTriggers()
    await db.exec('savepoint actual_test_call')
    let error
    try { await db.exec(insert) } catch (observed) { error = observed }
    assert.ok(error, `${name}: trigger failed to refuse`)
    assert.equal(error.message, expected, `${name}: wrong refusal`)
    assert.equal(error.code, 'P0001')
    if (detailCheck) detailCheck(JSON.parse(error.detail))
    await db.exec('rollback to savepoint actual_test_call')
    assert.deepEqual(await census(), before, `${name}: structural rows/sequences changed`)
    assert.deepEqual(await ERPTriggers(), triggers, `${name}: ERP trigger catalog changed`)
    report.controls.push({name,status:'PASS',message:error.message,detail:error.detail ?? null,
      local_rows_sequences_equal_after_refusal:true,ERP_trigger_rows_equal:true})
  } catch (error) {
    report.controls.push({name,status:'FAIL',message:error.message,code:error.code,detail:error.detail})
    try { await db.exec('rollback to savepoint actual_test_call') } catch {}
  } finally { await db.exec('rollback') }
}

try {
  await db.exec(setup)
  const before = await ERPTriggers()
  await db.exec(triggerSQL)
  assert.deepEqual(await ERPTriggers(), before)
  const targets = (await db.query(`select n.nspname,c.relname,t.tgtype::int from pg_trigger t join pg_class c on c.oid=t.tgrelid
    join pg_namespace n on n.oid=c.relnamespace where not t.tgisinternal order by n.nspname,c.relname,t.tgname`)).rows
  assert.deepEqual(targets,[{nspname:'cp7_credit_note_carry_de',relname:'operations_v1',tgtype:5}])
  report.controls.push({name:'exact_literal_compiles_and_attaches_only_private_AFTER_INSERT',status:'PASS',targets,ERP_trigger_rows_equal:true})
  await vector('structural_late_facts_reach_old_token_with_observed_DETAIL','', 'E_TEST_ACTUAL_NATIVE_POST_FAILURE', detail => {
    assert.equal(detail.failure_point,'AFTER_NATIVE_POST_DURING_E_FINISH')
    assert.equal(detail.operation_id,operation); assert.equal(detail.request_id,request); assert.equal(detail.revision_id,revision)
    assert.equal(detail.source_sale_id,original); assert.equal(detail.replacement_sale_id,replacement)
    assert.equal(detail.replacement_sale_journal_id,saleJournal); assert.equal(detail.replacement_sale_journal_status,'POSTED')
    assert.equal(detail.original_APPLY_event_id,event); assert.equal(detail.original_APPLY_journal_id,journal)
    assert.equal(detail.original_APPLY_target_id,original); assert.equal(Number(detail.replacement_native_net),550)
    assert.equal(Number(detail.carried_amount),80); assert.equal(detail.assignment_count,1); assert.equal(detail.work_phase,'MATERIALIZED')
    assert.equal(detail.owning_contexts_remaining,0); assert.deepEqual(detail.actual_guards_returned,expectedGuardNames)
  })
  await vector('missing_posted_replacement_journal_cannot_fake_late_point',`delete from erp.journal_entries where id='${saleJournal}'`)
  await vector('unposted_replacement_journal_cannot_fake_late_point',`update erp.journal_entries set status='DRAFT' where id='${saleJournal}'`)
  await vector('wrong_phase_cannot_fake_late_point',"update cp7_credit_note_carry_de.work_v1 set phase='REVERSED'")
  await vector('owning_context_not_cleared_cannot_fake_late_point','insert into cp7_note.context select pg_backend_pid(),txid_current()')
  await vector('missing_assignment_cannot_fake_carried80','delete from cp7_credit_note_carry_de.assignments_v1')
  await vector('changed_original_APPLY_cannot_fake_immutability',`update cp7_credit.consumption_events set amount=81 where id='${event}'`)
  await vector('changed_original_APPLY_journal_cannot_fake_immutability',`update erp.journal_lines set credit=81 where journal_entry_id='${journal}'`)
  await vector('changed_actual_revision_cannot_fake_link','update cp7_note.revisions set revision=2')
  await vector('changed_final_response_cannot_fake_finish',"update cp7_note.requests set response='{}'::jsonb")
  await vector('actual_native_census_call_is_not_a_literal_success_marker',`create or replace function cp7_credit.assert_source_native_trigger_census_v1()returns void language plpgsql as $$begin raise exception 'LOCAL_STRUCTURAL_NATIVE_CENSUS_REFUSAL';end$$;`, 'LOCAL_STRUCTURAL_NATIVE_CENSUS_REFUSAL')
  await vector('actual_historical_guard_call_is_not_a_literal_success_marker',`create or replace function cp7_credit_note_carry_de.assert_historical_v1(p uuid)returns void language plpgsql as $$begin raise exception 'LOCAL_STRUCTURAL_HISTORICAL_REFUSAL';end$$;`, 'LOCAL_STRUCTURAL_HISTORICAL_REFUSAL')
  await vector('actual_current_profile_guard_call_is_not_a_literal_success_marker',`create or replace function cp7_credit.assert_current_materialized_profile(p uuid,r uuid,l uuid)returns void language plpgsql as $$begin raise exception 'LOCAL_STRUCTURAL_CURRENT_PROFILE_REFUSAL';end$$;`, 'LOCAL_STRUCTURAL_CURRENT_PROFILE_REFUSAL')
  report.counts = report.controls.reduce((out,row) => ({...out,[row.status]:(out[row.status] ?? 0)+1}), {})
  report.status = report.controls.every(row=>row.status==='PASS') ? 'PASS_LOCAL_DOUBLES_ONLY' : 'FAIL_LOCAL_DOUBLES_ONLY'
} catch (error) {
  report.error = {message:error.message,code:error.code,detail:error.detail}
  report.status = 'FAIL_LOCAL_DOUBLES_ONLY'
} finally {
  await db.close()
  mkdirSync(dirname(output),{recursive:true}); writeFileSync(output,JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify({status:report.status,counts:report.counts,error:report.error,output,Native_execution:false}))
  if (report.status!=='PASS_LOCAL_DOUBLES_ONLY') process.exitCode=1
}
