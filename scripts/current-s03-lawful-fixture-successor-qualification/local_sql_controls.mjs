// Actual retained function text on declared tables/authority/idempotency doubles.
// This is PGlite-only local qualification preparation: actual Native/Auth=0.
import {readFileSync,writeFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'
import {createHash,randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'

const here=resolve('scripts/current-s03-lawful-fixture-successor-qualification')
const abi=JSON.parse(readFileSync(resolve(here,'ACTUAL9AC_ABI.json'),'utf8'))
const definition=sig=>{
 const row=abi.definitions[sig]
 assert.equal(createHash('sha256').update(row.definition).digest('hex'),row.definition_sha256)
 return row.definition
}
const modulePath=process.env.CP7_S03_PGLITE_MODULE??resolve('../test-runtime/node_modules/@electric-sql/pglite/dist/index.js')
const {PGlite}=await import(pathToFileURL(modulePath).href)
const db=new PGlite(),checks=[]
const lit=x=>"'"+String(x).replaceAll("'","''")+"'"
const run=sql=>db.exec(sql)
const one=async sql=>Object.values((await db.query(sql)).rows[0])[0]
const rows=async sql=>(await db.query(sql)).rows
async function check(name,fn){await fn();checks.push({id:name,status:'PASS'})}
async function rejects(sql,pattern){await run('savepoint refusal');try{await assert.rejects(()=>one(sql),pattern)}finally{await run('rollback to savepoint refusal;release savepoint refusal')}}
const worker=randomUUID(),other=randomUUID(),contractor=randomUUID(),actor=randomUUID(),p1='2026-10-01',p2='2026-10-02'
try{
 await run(`create schema erp;
  create table erp.contractors(id uuid primary key,attendance_required boolean not null);
  create table erp.contractor_workers(id uuid primary key,contractor_id uuid,pay_scheme text,joined_at date,daily_rate numeric,row_version bigint default 1,updated_by uuid);
  create table erp.worker_daily_rate_versions(id uuid primary key default gen_random_uuid(),worker_id uuid,daily_rate numeric,effective_from date,effective_to date,change_reason text,created_by uuid,created_at timestamptz default clock_timestamp());
  create table erp.worker_employment_periods(id uuid primary key default gen_random_uuid(),worker_id uuid,started_on date,ended_on date);
  create table erp.attendance_periods(id uuid primary key,contractor_id uuid,period_start date,period_end date);
  create table erp.attendance_records(id uuid primary key default gen_random_uuid(),attendance_period_id uuid,worker_id uuid,attendance_date date,record_lifecycle text,status text);
  create table erp.accounting_period_control(singleton_id integer primary key,closed_through date,updated_at timestamptz,updated_by uuid,change_reason text);
  create table erp.audit_logs(id bigserial primary key,entity_type text,entity_id uuid,action text,old_data jsonb,new_data jsonb,changed_by uuid,change_reason text);
  create function erp.require_owner_admin()returns void language plpgsql as $$begin if current_setting('local.owner',true)is distinct from'on'then raise exception 'LOCAL_OWNER_REQUIRED';end if;end$$;
  create function erp.current_app_user_id()returns uuid language sql as $$select '${actor}'::uuid$$;
  create function erp._request_hash(jsonb)returns text language sql as $$select md5($1::text)$$;
  create function erp._idempotency_begin(text,uuid,text)returns jsonb language sql as $$select null::jsonb$$;
  create function erp._idempotency_complete(text,uuid,jsonb)returns jsonb language sql as $$select $3$$;
  create function erp.local_bump()returns trigger language plpgsql as $$begin new.row_version:=old.row_version+1;return new;end$$;
  create trigger local_bump before update on erp.contractor_workers for each row execute function erp.local_bump();
  select set_config('local.owner','on',false);
  insert into erp.contractors values('${contractor}',true);
  insert into erp.contractor_workers values('${worker}','${contractor}','DAILY','${p1}',1000.03,1,null);
  insert into erp.worker_employment_periods(worker_id,started_on)values('${worker}','${p1}');
  insert into erp.worker_daily_rate_versions(worker_id,daily_rate,effective_from,change_reason,created_by)values('${worker}',1000.03,'${p1}','LOCAL_P1_RATE','${actor}');
  insert into erp.accounting_period_control values(1,'2026-10-10',null,null,null);`)
 for(const sig of ['erp.worker_is_employed_on(uuid,date)','erp.worker_daily_rate_at(uuid,date)','erp.guard_worker_daily_rate_version()',
  'erp.set_worker_daily_rate_v1(uuid,numeric,date,text,uuid,bigint)','erp.reopen_accounting_through(date,text)'])await run(definition(sig))
 await run('create trigger local_guard_rate before insert or update or delete on erp.worker_daily_rate_versions for each row execute function erp.guard_worker_daily_rate_version()')
 const post=definition('erp.post_attendance_period_v1(uuid,text,uuid,bigint)')
 const start=post.indexOf('  if (select attendance_required from erp.contractors where id = v_period.contractor_id) then')
 assert(start>=0);const end=post.indexOf('\n  end if;',start)+10;assert(end>start)
 const block=post.slice(start,end)
 assert(block.includes('blanks are not ABSENT or OFF'))
 await run(`create function erp.local_exact_native_completeness(p_period uuid)returns boolean language plpgsql as $$
  declare v_period erp.attendance_periods%rowtype;v_missing_count integer;v_uncovered_rate_count integer;begin
  select *into v_period from erp.attendance_periods where id=p_period;
  ${block}
  return true;end$$;begin;`)
 await check('OLD_EARNED_NEW_WORKER_LEAVES_REAL_UNKNOWN_CELL',async()=>{
  const period=randomUUID();await run(`savepoint old_fixture;
   insert into erp.contractor_workers values('${other}','${contractor}','DAILY','${p2}',20.02,1,null);
   insert into erp.worker_employment_periods(worker_id,started_on)values('${other}','${p2}');
   insert into erp.attendance_periods values('${period}','${contractor}','${p2}','${p2}');
   insert into erp.attendance_records(attendance_period_id,worker_id,attendance_date,record_lifecycle,status)values('${period}','${other}','${p2}','DRAFT','PRESENT');`)
  await rejects(`select erp.local_exact_native_completeness('${period}')`,/1 unrecorded eligible worker\/day cells; blanks are not ABSENT or OFF/)
  await run('rollback to savepoint old_fixture;release savepoint old_fixture')
 })
 const rateBefore=[await one(`select to_jsonb(r)from erp.worker_daily_rate_versions r where worker_id='${worker}'`)]
 let rate
 await check('ACTUAL_NATIVE_RATE_FRESH_VERSION_P2_PRESERVES_P1_RATE',async()=>{
  const version=await one(`select row_version from erp.contractor_workers where id='${worker}'`)
  rate=await one(`select erp.set_worker_daily_rate_v1('${worker}',20.02,'${p2}','Owner reviewed later rate','${randomUUID()}',${version})`)
  assert.equal(rate.worker_id,worker);assert.equal(rate.row_version,2)
  assert.equal(Number(await one(`select erp.worker_daily_rate_at('${worker}','${p1}')`)),1000.03)
  assert.equal(Number(await one(`select erp.worker_daily_rate_at('${worker}','${p2}')`)),20.02)
  const old=await one(`select to_jsonb(r)from erp.worker_daily_rate_versions r where id='${rateBefore[0].id}'`)
  assert.deepEqual({...old,effective_to:null},rateBefore[0]);assert.equal(old.effective_to,p1)
 })
 await check('SAME_KNOWN_P1_WORKER_P2_PRESENT_IS_COMPLETE',async()=>{
  const period=randomUUID();await run(`insert into erp.attendance_periods values('${period}','${contractor}','${p2}','${p2}');
   insert into erp.attendance_records(attendance_period_id,worker_id,attendance_date,record_lifecycle,status)values('${period}','${worker}','${p2}','DRAFT','PRESENT')`)
  assert.equal(await one(`select erp.local_exact_native_completeness('${period}')`),true)
  const eligible=await rows(`select id from erp.contractor_workers where contractor_id='${contractor}'and pay_scheme in('DAILY','HYBRID')and erp.worker_is_employed_on(id,'${p2}')order by id`)
  assert.deepEqual(eligible,[{id:worker}])
 })
 await check('ACTUAL_NATIVE_RATE_STALE_AND_HISTORY_FACT_EDIT_REFUSE',async()=>{
  await rejects(`select erp.set_worker_daily_rate_v1('${worker}',30,'2026-10-03','stale','${randomUUID()}',1)`,/STALE_VERSION/)
  await rejects(`update erp.worker_daily_rate_versions set daily_rate=0 where id='${rateBefore[0].id}'returning id`,/Existing worker rate facts are immutable/)
 })
 await check('ACTUAL_NATIVE_OWNER_REOPEN_BACKWARD_REASON_AND_AUDIT',async()=>{
  await rejects(`select erp.reopen_accounting_through('2026-10-10','reviewed')`,/Tanggal reopen harus lebih awal/)
  await rejects(`select erp.reopen_accounting_through('2026-09-30','')`,/Alasan membuka kembali/)
  await one(`select erp.reopen_accounting_through('2026-09-30','Owner reviewed original source before inverse')`)
  assert.equal(await one('select closed_through::text from erp.accounting_period_control'),'2026-09-30')
  const audit=await one("select to_jsonb(a)from erp.audit_logs a where entity_type='accounting_period_control'")
  assert.deepEqual(audit.old_data,{closed_through:'2026-10-10'});assert.deepEqual(audit.new_data,{closed_through:'2026-09-30'})
  assert.equal(audit.changed_by,actor)
 })
 // This exact valuation statement is not presented as a whole rebuild run.
 const rebuild=definition('erp.rebuild_po_hpp(uuid,text)')
 const valuation="    update erp.fg_stock_movements set unit_hpp_snapshot=(select hpp_per_pcs from erp.hpp_versions where id=v_new_id)\n    where lot_id=r.id and movement_type in ('QC_GOOD','REWORK_IN');"
 assert.equal(rebuild.split(valuation).length-1,1)
 await run(`create table erp.hpp_versions(id uuid primary key,hpp_per_pcs numeric);
  create table erp.fg_stock_movements(id uuid primary key,product_id uuid,lot_id uuid,location_id uuid,quality_grade text,movement_type text,qty_signed integer,unit_hpp_snapshot numeric,customer_id uuid,source_type text,source_id uuid,physical_at timestamptz,system_created_at timestamptz,created_by uuid,reversal_of_id uuid,notes text,book_order bigint);`)
 const lot=randomUUID(),hpp=randomUUID(),cache=randomUUID(),sale=randomUUID()
 await run(`insert into erp.hpp_versions values('${hpp}',10);
  insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,unit_hpp_snapshot,physical_at,system_created_at,notes,book_order)
  values('${cache}','${lot}','QC_GOOD',10,10,'${p2} 03:00+07','${p2} 03:01+07','Native cache row',1),('${sale}','${lot}','SALE',-4,10,'${p2} 05:00+07','${p2} 05:01+07','SALE history',2);`)
 const original=await rows('select *from erp.fg_stock_movements order by id')
 const refresh=()=>run(`do $$declare r record;v_new_id uuid:='${hpp}';begin select '${lot}'::uuid id into r;${valuation}end$$`)
 await check('EXACT_NATIVE_QC_CACHE_CHANGES_ALL16_OTHER_FIELDS_AND_ENTIRE_SALE_EXACT',async()=>{
  await run(`update erp.hpp_versions set hpp_per_pcs=110.003 where id='${hpp}'`);await refresh()
  const after=await rows('select *from erp.fg_stock_movements order by id');assert.notDeepEqual(after,original)
  for(let i=0;i<original.length;i++){
   assert.equal(Object.keys(after[i]).length,17)
   if(original[i].movement_type==='SALE')assert.deepEqual(after[i],original[i])
   else{assert.equal(Number(after[i].unit_hpp_snapshot),110.003);assert.deepEqual({...after[i],unit_hpp_snapshot:original[i].unit_hpp_snapshot},original[i])}
  }
 })
 await check('EXACT_NATIVE_CACHE_CANCEL_VALUATION_FULL_FG_ROWS_RETURN',async()=>{
  await run(`update erp.hpp_versions set hpp_per_pcs=10 where id='${hpp}'`);await refresh()
  assert.deepEqual(await rows('select *from erp.fg_stock_movements order by id'),original)
 })
 await run('rollback')
 const result={classification:'LOCAL_PGLITE_ACTUAL_RETAINED_FUNCTION_TEXT_ON_DECLARED_TABLE_AUTHORITY_IDEMPOTENCY_DOUBLES',
  status:'PASS',checks,actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,
  actual_whole_rebuild_executed:false,actual_completeness_guard_block_only:true,
  full_S03_financial_qualification:false,production_go:false}
 console.log(JSON.stringify(result,null,2))
}catch(error){
 console.error(JSON.stringify({classification:'LOCAL_PGLITE_PREPARATION_FAILURE_NOT_ACTUAL_NATIVE',status:'FAIL',completed:checks,error:String(error),stack:error.stack,actual_Native_cases:0},null,2));process.exitCode=1
}finally{await db.close()}
