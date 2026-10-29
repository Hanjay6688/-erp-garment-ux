// @vitest-environment node
// Source-derived Native routines on declared table/Auth/calendar/HPP doubles.
// This is zero actual Native/Auth/browser qualification credit.
import {beforeAll,afterAll,beforeEach,afterEach,expect,test} from 'vitest'
import {readFileSync,writeFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'
import {execFileSync} from 'node:child_process'
import {randomUUID} from 'node:crypto'

const HERE=resolve('scripts/cp7_attendance_period_choice')
const abi=JSON.parse(readFileSync(resolve(HERE,'SOURCE_DERIVED_NATIVE_ABI.json'),'utf8'))
const derived=JSON.parse(execFileSync('python',['-B',resolve(HERE,'render_local.py')],{encoding:'utf8'}))
const owner='00000000-0000-4000-8000-000000000001'
const catalogQueries=JSON.parse(execFileSync('python',['-B',resolve(HERE,'local_catalog.py')],{encoding:'utf8'}))
let db:any,today:string,catalogBefore:any,catalogInstalled:any,installedDefinitions:Record<string,string>
const lit=(s:string)=>"'"+s.replaceAll("'","''")+"'"
const js=(value:unknown)=>lit(JSON.stringify(value))+'::jsonb'
async function one(sql:string){const result=await db.query(sql);return Object.values(result.rows[0])[0] as any}
async function run(sql:string){return db.exec(sql)}
async function catalog(){
 const path=await one('show search_path'),zone=await one('show timezone');await run("set search_path='';set timezone='UTC'")
 try{
  const result:Record<string,unknown>={}
  for(const[group,query]of Object.entries(catalogQueries)){
   const rows=await db.query(query as string),objects=rows.rows.map((row:any)=>Object.values(row));result[group]=Object.fromEntries(objects as any)
   expect(Object.keys(result[group]as object)).toHaveLength(rows.rows.length)
  }
  return result
 }finally{await run(`select set_config('search_path',${lit(path)},false),set_config('timezone',${lit(zone)},false)`)}
}
async function day(offset:number){return one(`select(erp.bb_business_today_v1()+${offset})::text`)}
async function census(){
 const names=await db.query("select format('%I.%I',n.nspname,c.relname) name from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname<>all(array['pg_catalog','information_schema','cron'])and n.nspname!~'^pg_'and c.relkind in('r','p','m','S')order by 1")
 const out:Record<string,unknown>={}
 for(const{name}of names.rows){
  const kind=await one(`select relkind from pg_class where oid=${lit(name)}::regclass`)
  out[name]=kind==='S'?await one(`select jsonb_build_array(last_value::text,is_called)from ${name}`):await one(`select coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),'[]'::jsonb)from ${name} r`)
 }
 return out
}
async function refused(sql:string,pattern:RegExp){
 const before=await census();await run('savepoint rejected')
 try{await expect(one(sql)).rejects.toThrow(pattern)}finally{await run('rollback to savepoint rejected;release savepoint rejected')}
 const after=await census()
 if(JSON.stringify(after)!==JSON.stringify(before))writeFileSync('/tmp/s03-refusal-census-diff.json',JSON.stringify({classification:'LOCAL_MODEL_ALL_USER_SCHEMA_CENSUS_NOT_ACTUAL_NATIVE',refusal:pattern.source,
  changed:Object.fromEntries(Object.keys(before).filter(key=>JSON.stringify(before[key])!==JSON.stringify(after[key])).map(key=>[key,{before:before[key],after:after[key]}]))},null,2))
 expect(after).toEqual(before)
}
function payload(f:string,choice:string|null=null,output:string|null=null,reason='Pilihan biaya absensi telah diperiksa Owner'){
 return {period_start:f,period_end:f,choice,output_start:output,output_end:output,reason}
}
async function preview(action:string,p:unknown){return one(`select public.erp_cp7_preview_attendance_choice_v1(${lit(action)},${js(p)})`)}
async function save(action:string,p:unknown,key=randomUUID()){
 const review=await preview(action,p)
 return one(`select public.erp_cp7_save_attendance_choice_v1(${lit(action)},${js({...p as any,review_token:review.review_token})},'${key}')`)
}
async function policy(contractor:string,f:string,special=false,attendanceRequired=true){
 return one(`select erp.set_contractor_hpp_policy_v1(${js({contractor_id:contractor,effective_from:f,is_special:special,attendance_required:attendanceRequired,reason:'Kebijakan fixture lokal eksplisit'})},'${randomUUID()}',null)`)
}
async function contractor(f:string,special=false,attendanceRequired=true){
 const id=randomUUID();await run(`insert into erp.contractors(id,contractor_code,contractor_name,attendance_required)values('${id}',${lit('S03-'+id.slice(0,8))},'Mandor fixture lokal',${attendanceRequired})`)
 await policy(id,f,special,attendanceRequired);return id
}
async function payroll(contractor:string,f:string,amount='1000.03',approve=true){
 const id=randomUUID();await run(`insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,attendance_total,payment_date,status)
  values('${id}',${lit('S03-'+id.slice(0,8))},'${contractor}','${f}','${f}',${amount},'${today}','REVIEW');
  insert into erp.payroll_attendance_items(payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot,attendance_date_snapshot)
  values('${id}','${randomUUID()}','${randomUUID()}',1,${amount},'${f}')`)
 await one(`select erp.${approve?'approve_payroll':'recalculate_payroll'}('${id}')`);return id
}
async function sewn(contractor:string,f:string,qty=3,hour=2){
 const po=randomUUID(),group=randomUUID(),work=randomUUID(),event=randomUUID()
 await run(`insert into erp.production_orders(id,po_number,model_id,contractor_id,status)values('${po}',${lit('PO-'+po.slice(0,8))},'${randomUUID()}','${contractor}','IN_PROGRESS');
 insert into erp.cutting_groups(id,po_id,group_number,cut_at)values('${group}','${po}',${lit('CG-'+group.slice(0,8))},'${f} 01:00+07');
 insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status)
 values('${work}',${lit('WC-'+work.slice(0,8))},'${po}','${contractor}','${group}','${f} ${hour.toString().padStart(2,'0')}:00+07','POSTED');
 insert into erp.sewing_terminal_events(id,event_number,event_kind,source_work_completion_id,contractor_id,po_id,cutting_group_id,physical_at,qty_signed,reason)
 values('${event}',${lit('SEW-'+event.slice(0,8))},'SELESAI_DIJAHIT','${work}','${contractor}','${po}','${group}','${f} ${hour.toString().padStart(2,'0')}:00+07',${qty},'Native-shaped output fixture, not screen creation')`)
 return {po,group,work,event}
}
async function fixture(offset=-3,amount='1000.03'){
 const f=await day(offset),m=await contractor(f),p=await payroll(m,f,amount)
 return {f,m,p}
}

beforeAll(async()=>{
 const module=process.env.CP7_S03_PGLITE_MODULE??resolve('../test-runtime/node_modules/@electric-sql/pglite/dist/index.js')
 const {PGlite}=await import(/* @vite-ignore */pathToFileURL(module).href);db=new PGlite()
 await run(readFileSync(resolve(HERE,'local_fixture.sql'),'utf8'))
 for(const[name,cols]of Object.entries(abi.local_table_columns)as any){
  const columns=cols.map((c:any)=>{
   const generated=c.default&&cols.some((other:any)=>other.name!==c.name&&new RegExp('\\b'+other.name+'\\b').test(c.default))
   return `"${c.name}" ${c.type}`+(generated?` generated always as(${c.default})stored`:c.default?` default ${c.default}`:'')+(!c.nullable?' not null':'')
  })
  if(cols.some((c:any)=>c.name==='id'))columns.push('primary key(id)')
  if(name==='idempotency_requests')columns.push('primary key(actor_key,operation_name,client_request_id)')
  if(name==='account_daily_balances')columns.push('primary key(balance_date,account_id)')
  if(name==='accounting_account_mappings')columns.push('primary key(mapping_key)')
  if(name==='accounting_period_control')columns.push('primary key(singleton_id)')
  await run(`create table erp.${name}(${columns.join(',')})`)
 }
 await run(`create unique index local_one_active_pool_period on erp.attendance_hpp_pools(period_start,period_end)where status='ACTIVE';
 create unique index local_one_posted_journal_source on erp.journal_entries(source_type,source_id)where status='POSTED';
 insert into local_s03.identity(actor,role_code)values('${owner}','OWNER');select set_config('local_s03.actor','${owner}',false);
 insert into erp.accounting_period_control(singleton_id,closed_through)values(1,null);
 create function erp.account_id(p text)returns uuid language sql stable as $$select account_id from erp.accounting_account_mappings where mapping_key=p$$;
 create function erp.resolve_accounting_transaction_date(p date)returns date language sql stable as $$select case when closed_through is not null and p<=closed_through then closed_through+1 else p end from erp.accounting_period_control where singleton_id=1$$;
 create function erp.check_opening_cash_advance_payroll_v1(p uuid)returns void language plpgsql as $$begin return;end$$;
 create function erp.bb_check_opening_payable_payroll_v1(p uuid)returns void language plpgsql as $$begin return;end$$;
 create function erp.bb_assert_opening_balance_floor_v1(p uuid,d date)returns void language plpgsql as $$begin return;end$$;
 create function erp.refresh_contractor_issue_payroll_status(p uuid)returns void language plpgsql as $$begin return;end$$;
 create function erp.rebuild_bs_component_counters(p uuid)returns void language plpgsql as $$begin return;end$$;
 create function erp.rebuild_po_hpp(p uuid,why text)returns void language plpgsql as $$begin
  if(select fail_hpp from local_s03.controls)then raise exception 'LOCAL_EXPLICIT_HPP_DEPENDENCY_FAILURE';end if;
  insert into local_s03.hpp_calls values('REBUILD',p,null);end$$;
 create function erp.propagate_conversion_hpp_for_po(p uuid)returns void language sql as $$insert into local_s03.hpp_calls values('PROPAGATE',p,null)$$;
 create function erp.sync_po_hpp_to_gl(p uuid,d date)returns void language sql as $$insert into local_s03.hpp_calls values('GL',p,d)$$;
 create function erp.sync_finished_po_wip_residual(p uuid,d date,why text)returns void language sql as $$insert into local_s03.hpp_calls values('FINISHED_RESIDUAL',p,d)$$;`)
 for(const key of ['WIP','OTHER_EXPENSE','CONTRACTOR_PAYABLE','AP_VENDOR','CASH','CAPITAL']){
  const id=randomUUID(),expense=key==='OTHER_EXPENSE',liability=key==='CONTRACTOR_PAYABLE'||key==='AP_VENDOR'||key==='CAPITAL'
  await run(`insert into erp.chart_accounts(id,account_code,account_name,account_type,report_group,normal_balance)
   values('${id}','${key}','${key}','${expense?'EXPENSE':liability?'LIABILITY':'ASSET'}','LOCAL','${liability?'CREDIT':'DEBIT'}');
   insert into erp.accounting_account_mappings(mapping_key,account_id)values('${key}','${id}')`)
 }
 const refs=abi.local_reference_definitions
 const helperOrder=['erp._cp3_canonical_date(date)','erp._cp3_epoch_microseconds(timestamp with time zone)',
  'erp._cp3_business_date(timestamp with time zone)','erp._cp3_parse_canonical_date(text,text)',
  'erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)','erp._cp3_manifest_sha256(jsonb)',
  'erp._request_hash(jsonb)','erp._idempotency_actor_key()','erp._idempotency_begin(text,uuid,text)',
  'erp._idempotency_complete(text,uuid,jsonb)','erp._cp3_lock_business_date(date)','erp._cp3_lock_business_period(date,date)',
  'erp._cp3_lock_manifest_contractors(date,date)','erp.pocket_period_lock_v1()',
  'erp.bump_row_version()','erp.audit_row_change()','erp.recalculate_payroll(uuid)',
  'erp._build_attendance_hpp_manifest_v1(date,date)','erp._assert_attendance_hpp_manifest_v1(jsonb)',
  'erp.preview_attendance_hpp_pool_v1(date,date)','erp.post_journal(text,uuid,date,text,jsonb)',
  'erp._cp3_r4_reverse_journal_internal(uuid,text)','erp.post_payroll_payment(uuid)',
  'erp.reverse_sewing_terminal_v1(uuid,text,uuid,bigint)',
  'cp7_hpp_pool.iso(timestamp with time zone)','cp7_hpp_pool.pool_token(erp.attendance_hpp_pools)',
  'cp7_hpp_pool.preview_token(date,date,text,text,bigint,text)','cp7_hpp_pool.access_now(boolean)',
  'cp7_hpp_pool.preview(date,date,date)','cp7_hpp_pool.pool_json(erp.attendance_hpp_pools,date)',
  'cp7_hpp_pool.workspace(integer,integer,date,date)']
 for(const key of helperOrder)await run(refs[key].definition)
 for(const definition of abi.local_payroll_audit_triggers)await run(definition)
 // The facade source is exact. Access/context/token/document and nonwork
 // eligibility dependencies remain declared local doubles. Rebuild is audited
 // through actual retained Native recalculate+bump/audit, never a no-op.
 await run(`create function cp7_payroll.settlement_access(p text)returns jsonb language plpgsql as $$begin
 perform erp.require_owner_admin();return erp.get_my_access_v1();end$$;
 create function cp7_payroll.require_settlement_context(p uuid)returns void language plpgsql as $$begin
 if not exists(select 1 from cp7_payroll.settlement_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()and c.actor=auth.uid()and c.payroll_id=p)then raise exception 'LOCAL_SETTLEMENT_CONTEXT';end if;end$$;
 create function cp7_payroll.settlement_token(p uuid)returns text language sql stable as $$select md5(to_jsonb(h)::text)from erp.payroll_settlements h where id=p$$;
 create function cp7_payroll.settlement_document(p uuid)returns jsonb language sql stable as $$select to_jsonb(h)||jsonb_build_object('review_token',cp7_payroll.settlement_token(h.id))from erp.payroll_settlements h where id=p$$;
 create function cp7_payroll.rebuild_nonwork(p uuid)returns void language sql as $$select erp.recalculate_payroll(p)$$;`)
 for(const key of ['cp7_payroll.settlement_meaning(uuid)','cp7_payroll.apply_settlement(text,jsonb,text)','cp7_payroll.settlement_command(text,jsonb,uuid)'])
  if(!Object.hasOwn(derived.originals,key))await run(refs[key].definition)
 await run(`create function public.erp_cp7_save_payroll_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text)returns jsonb
 language sql volatile security definer set search_path=''as $$select cp7_payroll.settlement_command(p_action,p_payload,p_request,p_expected)$$;`)
 for(const definition of Object.values(derived.originals)as string[])await run(definition)
 // Explicit local-only old-reader references compare unaffected JSON exactly.
 // They exist before the catalog baseline, never as installed product clones.
 await run(refs['cp7_hpp_pool.pool_json(erp.attendance_hpp_pools,date)'].definition.replace('FUNCTION cp7_hpp_pool.pool_json(', 'FUNCTION local_s03.reference_pool_json_v1('))
 await run(refs['cp7_hpp_pool.preview(date,date,date)'].definition.replace('FUNCTION cp7_hpp_pool.preview(', 'FUNCTION local_s03.reference_preview_v1('))
 // Explicit old-policy reader double: no pocket/other Native close proof.
 await run(`create function cp7_hpp_close.blockers_v1(p_through date)returns table(family text,code text,severity text,scope text,impact_date date,reference jsonb,reason text)
 language plpgsql stable as $$declare r record;m jsonb;begin
 return query select 'OTHER'::text,'LOCAL_RETAINED_SENTINEL'::text,'INFO'::text,'AS_OF'::text,p_through,'{}'::jsonb,'unchanged local fixture family'::text;
 for r in select distinct period_start,period_end from erp.payroll_settlements where status in('APPROVED','PAID')and period_end<=p_through loop
  m:=erp._build_attendance_hpp_manifest_v1(r.period_start,r.period_end);
  if(m->>'numerator_cents')::bigint>0 and(m->>'denominator_qty')::bigint=0 then
   return query select 'HPP_POOL'::text,'ATTENDANCE_POOL_ZERO_OUTPUT'::text,'INFO'::text,'AS_OF'::text,r.period_end,
    jsonb_build_object('period_start',r.period_start,'period_end',r.period_end,'amount',((m->>'numerator_cents')::numeric/100)::text),'historical INFO double, not Native Original'::text;
  end if;
 end loop;end$$;`)
 catalogBefore=await catalog()
 await run(readFileSync(resolve(HERE,'choice.sql'),'utf8'))
 await run(readFileSync(resolve(HERE,'readers.sql'),'utf8'))
 for(const definition of Object.values(derived.clones)as string[])await run(definition)
 await run('revoke all on all functions in schema cp7_attendance_choice from public,anon,authenticated,service_role')
 for(const definition of Object.values(derived.patched)as string[])await run(definition)
 catalogInstalled=await catalog();installedDefinitions={}
 for(const sig of Object.keys(derived.patched))installedDefinitions[sig]=catalogInstalled.functions[sig][0]
 writeFileSync('/tmp/s03-local-catalog.json',JSON.stringify({classification:'LOCAL_MODEL_NOT_NATIVE_CAPTURE',before:catalogBefore,after:catalogInstalled,definitions:installedDefinitions}))
 today=await one('select erp.bb_business_today_v1()::text')
},30_000)
afterAll(async()=>{await db?.close()},30_000)
beforeEach(async()=>{await run('begin');await run(`select set_config('local_s03.actor','${owner}',false)`)} )
afterEach(async()=>{await run('rollback')})

test('APPROVED cost moves only its exact WIP to expense; PAID remains settlement and the source binding stays current',async()=>{
 const f=await fixture(),capture=await one(`select cp7_attendance_choice.capture_v1('${f.f}','${f.f}',true)`)
 const result=await save('CHOOSE',payload(f.f,'EXPENSE'))
 expect(result.status).toBe('COMMITTED');expect(result.amount_cents).toBe('100003')
 expect(await one("select sum(l.debit-l.credit)::text from erp.journal_lines l where l.account_id=erp.account_id('WIP')")).toBe('0.00')
 expect(await one("select sum(l.debit-l.credit)::text from erp.journal_lines l where l.account_id=erp.account_id('OTHER_EXPENSE')")).toBe('1000.03')
 const cash=randomUUID();await run(`insert into erp.cash_accounts(id,cash_account_code,cash_account_name,coa_account_id,account_kind)
  values('${cash}','LOCAL','Local bank',erp.account_id('CASH'),'BANK')`)
 await one(`select erp.post_journal('LOCAL_CAPITAL','${randomUUID()}','${today}','Only required cash for local settlement',
  jsonb_build_array(jsonb_build_object('mapping_key','CASH','debit',1000.03,'credit',0),jsonb_build_object('mapping_key','CAPITAL','debit',0,'credit',1000.03)))`)
 await run(`update erp.payroll_settlements set payment_cash_account_id='${cash}'where id='${f.p}'`)
 await one(`select erp.post_payroll_payment('${f.p}')`)
 expect(await one(`select status from erp.payroll_settlements where id='${f.p}'`)).toBe('PAID')
 const after=await one(`select cp7_attendance_choice.capture_v1('${f.f}','${f.f}',true)`)
 expect(after.source_binding).toBe(capture.source_binding)
 expect(await one(`select count(*)::text from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id='${f.p}'`)).toBe('1')
 await refused(`select erp.reverse_paid_payroll('${f.p}','Must refuse source reversal while expense active')`,/CP7_S03_PAYROLL_CLAIMED/)
})

test('CARRY uses old exact sources and later Native sewing with exact cents, explicit dates and unchanged old-period basis',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'))
 // Distinct physical facts fix the intended 3-then-7 chronology. The retained
 // failed attempt used equal times and incorrectly assumed creation order
 // won over Native's UUID tie-break; it is not an allocation product repair.
 const x=await sewn(f.m,today,3,2),y=await sewn(f.m,today,7,3)
 const reviewed=await preview('ALLOCATE',payload(f.f,null,today));expect(reviewed.economic_date).toBe(today);expect(reviewed.book_date).toBe(today)
 const result=await save('ALLOCATE',payload(f.f,null,today))
 const pool=await one(`select to_jsonb(p)from erp.attendance_hpp_pools p where id='${result.pool_id}'`)
 expect(pool.period_start).toBe(f.f);expect(pool.period_end).toBe(f.f);expect(pool.denominator_qty).toBe(10)
 const rows=await db.query(`select a.sewing_terminal_event_id::text id,a.allocated_amount::text amount from erp.attendance_hpp_pool_allocations a where pool_id='${result.pool_id}'order by a.allocated_amount`)
 expect(rows.rows.map((r:any)=>r.amount)).toEqual(['300.00','700.03'])
 expect(new Set(rows.rows.map((r:any)=>r.id))).toEqual(new Set([x.event,y.event]))
 expect(await one(`select validation from jsonb_to_record(erp.validate_attendance_hpp_pool_v1('${result.pool_id}'))as x(validation text)`)).toBe('PASS')
 expect(await one(`select economic_date::text from erp.journal_entries where id='${pool.post_journal_entry_id}'`)).toBe(today)
 expect(await one("select count(*)::text from local_s03.hpp_calls where kind='GL'and book_date="+lit(today))).toBe('2')
})

test('source ordinary output remains zero; later payroll approval and a disjoint ordinary later pool coexist without false stale',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,today,10)
 const result=await save('ALLOCATE',payload(f.f,null,today))
 const original=await one(`select source_manifest_sha256 from erp.attendance_hpp_pools where id='${result.pool_id}'`)
 await payroll(f.m,today,'20.02')
 const normal=await one(`select erp.create_attendance_hpp_pool_v1(${js({period_start:today,period_end:today,reason:'Disjoint later normal attendance pool'})},'${randomUUID()}')`)
 await one(`select erp.activate_attendance_hpp_pool_v1('${normal.pool_id}','Activate disjoint later cost','${randomUUID()}',${normal.row_version})`)
 expect(await one(`select erp.validate_attendance_hpp_pool_v1('${result.pool_id}')->>'validation'`)).toBe('PASS')
 expect(await one(`select source_manifest_sha256 from erp.attendance_hpp_pools where id='${result.pool_id}'`)).toBe(original)
 expect(await one(`select count(*)::text from erp.attendance_hpp_pools where status='ACTIVE'`)).toBe('2')
})

test('a direct carried-pool cancel and late new output refuse before writes; owning cancellation closes metadata then permits current-date reallocation',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,today,10)
 const result=await save('ALLOCATE',payload(f.f,null,today))
 await refused(`select erp.cancel_attendance_hpp_pool_v1('${result.pool_id}','Direct old facade must not detach metadata','${randomUUID()}',2)`,/OWNING_CARRY_CANCEL_REQUIRED/)
 const late=await sewn(f.m,today,1);await run(`delete from erp.sewing_terminal_events where id='${late.event}'`)
 await refused(`select erp.record_sewing_terminal_v1(${js({work_completion_id:late.work,qty_pcs:1,reason:'Must not shift carried output intervals'})},'${randomUUID()}')`,/ACTIVE_CARRY_OUTPUT_LOCKED/)
 await save('CANCEL_ALLOCATION',payload(f.f));expect(await one('select count(*)::text from cp7_attendance_choice.allocation_reversals_v1')).toBe('1')
 expect(await one(`select cp7_attendance_choice.current_allocation_v1('${result.decision_id}')`)).toBeNull()
 const again=await save('ALLOCATE',payload(f.f,null,today));expect(again.pool_id).not.toBe(result.pool_id)
})

test('fresh preview, owner authority, immutable request recovery and source-bound policy guards refuse without row/sequence changes',async()=>{
 const f=await fixture(),p=payload(f.f,'CARRY'),r=await preview('CHOOSE',p),key=randomUUID()
 const command=`select public.erp_cp7_save_attendance_choice_v1('CHOOSE',${js({...p,review_token:r.review_token})},'${key}')`
 const saved=await one(command),before=await census();expect(await one(command)).toEqual(saved);expect(await census()).toEqual(before)
 await refused(`select public.erp_cp7_save_attendance_choice_v1('CHOOSE',${js({...p,reason:'Changed request payload is forbidden',review_token:r.review_token})},'${key}')`,/REQUEST_CHANGED/)
 await run("update local_s03.identity set role_code='ADMIN'where actor="+lit(owner));await refused(command,/OWNER_REQUIRED/)
 await run("update local_s03.identity set role_code='OWNER'where actor="+lit(owner))
 const current=await one(`select id::text from erp.contractor_hpp_policy_versions where contractor_id='${f.m}'order by effective_from desc limit 1`)
 await refused(`select erp.set_contractor_hpp_policy_v1(${js({contractor_id:f.m,effective_from:today,is_special:false,attendance_required:true,reason:'Future version would truncate a held source policy'})},'${randomUUID()}','${current}')`,/HELD_POLICY_CHANGED/)
 await refused(`select erp.cancel_unpaid_payroll('${f.p}','Source must be released through its owning choice')`,/PAYROLL_CLAIMED/)
})

test('restored WIP cannot be expensed or allocated before either source-recognition axis; lawful restoration-forward path works',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'EXPENSE'));await save('CORRECT',payload(f.f,'CARRY'))
 const past=await day(-1);await sewn(f.m,past,10)
 await refused(`select public.erp_cp7_preview_attendance_choice_v1('ALLOCATE',${js(payload(f.f,null,past))})`,/ALLOCATION_BEFORE_WIP_AVAILABLE/)
 await refused(`select public.erp_cp7_preview_attendance_choice_v1('CORRECT',${js(payload(f.f,'EXPENSE'))})`,/EXPENSE_BEFORE_WIP_AVAILABLE|WIP_NEGATIVE_DATED/)
 await sewn(f.m,today,10);expect((await save('ALLOCATE',payload(f.f,null,today))).status).toBe('COMMITTED')
})

test('unresolved zero output is the successor POLICY blocker, while the historical INFO reader and unrelated families remain unchanged',async()=>{
 const f=await fixture();const query=(name:string)=>one(`select jsonb_agg(to_jsonb(r)order by code)from ${name}('${today}')r`)
 expect((await query('cp7_hpp_close.blockers_v1')).find((r:any)=>r.code==='ATTENDANCE_POOL_ZERO_OUTPUT').severity).toBe('INFO')
 expect((await query('cp7_attendance_choice.blockers_v1')).find((r:any)=>r.code==='ATTENDANCE_ZERO_CHOICE_REQUIRED').severity).toBe('POLICY')
 await save('CHOOSE',payload(f.f,'CARRY'))
 const rows=await query('cp7_attendance_choice.blockers_v1');expect(rows.find((r:any)=>r.code==='ATTENDANCE_ZERO_CARRY_WAITING').severity).toBe('INFO')
 expect(rows.find((r:any)=>r.code==='LOCAL_RETAINED_SENTINEL')).toEqual((await query('cp7_hpp_close.blockers_v1')).find((r:any)=>r.code==='LOCAL_RETAINED_SENTINEL'))
})

test('closed payloads, stale source previews and revoked current access refuse with the entire row/sequence census unchanged',async()=>{
 const f=await fixture(),p=payload(f.f,'CARRY')
 for(const action of ['null',lit(''),lit('CHOOSE '),lit('UNKNOWN')])await refused(`select public.erp_cp7_preview_attendance_choice_v1(${action},${js(p)})`,/CP7_S03_ACTION/)
 for(const bad of [{...p,unexpected:'extra'}, {...p,choice:null},{...p,output_start:today},{...p,reason:'x'}])
  await refused(`select public.erp_cp7_preview_attendance_choice_v1('CHOOSE',${js(bad)})`,/S03|Unexpected.*field|Unknown.*field/i)
 const r=await preview('CHOOSE',p),key=randomUUID(),sql=`select public.erp_cp7_save_attendance_choice_v1('CHOOSE',${js({...p,review_token:r.review_token})},'${key}')`
 const other=await contractor(f.f);await payroll(other,f.f,'11.01')
 await refused(sql,/CP7_S03_STALE_REVIEW/)
 await run(`update local_s03.identity set can_manage=false where actor='${owner}'`)
 await refused(sql,/CP7_S03_OWNER_REQUIRED/)
})

test('a changed expense account mapping invalidates the exact preview before posting rather than silently spending through a new account',async()=>{
 const f=await fixture(),p=payload(f.f,'EXPENSE'),r=await preview('CHOOSE',p),id=randomUUID()
 await run(`insert into erp.chart_accounts(id,account_code,account_name,account_type,report_group,normal_balance)
 values('${id}','LOCAL_EXPENSE_NEW','Replacement local expense','EXPENSE','LOCAL','DEBIT');
 update erp.accounting_account_mappings set account_id='${id}'where mapping_key='OTHER_EXPENSE'`)
 await refused(`select public.erp_cp7_save_attendance_choice_v1('CHOOSE',${js({...p,review_token:r.review_token})},'${randomUUID()}')`,/CP7_S03_STALE_REVIEW/)
 expect((await save('CHOOSE',p)).status).toBe('COMMITTED')
 expect(await one(`select sum(l.debit)::text from erp.journal_lines l where account_id='${id}'`)).toBe('1000.03')
})

test('caller timezone alone cannot invalidate a source review or carry manifest',async()=>{
 const f=await fixture(),p=payload(f.f,'CARRY');await run("set timezone='Asia/Jakarta'")
 const reviewed=await preview('CHOOSE',p);await run("set timezone='America/New_York'")
 expect((await one(`select public.erp_cp7_save_attendance_choice_v1('CHOOSE',${js({...p,review_token:reviewed.review_token})},'${randomUUID()}')`)).status).toBe('COMMITTED')
 await sewn(f.m,today,10);const a=await preview('ALLOCATE',payload(f.f,null,today));await run("set timezone='UTC'")
 expect((await preview('ALLOCATE',payload(f.f,null,today))).review_token).toBe(a.review_token)
})

test('old accrual booked after closed books keeps its recognition floor after reopening, and can carry forward lawfully',async()=>{
 const f=await day(-3),m=await contractor(f),yesterday=await day(-1)
 await run(`update erp.accounting_period_control set closed_through='${yesterday}'`)
 const p=await payroll(m,f)
 expect(await one(`select transaction_date::text from erp.journal_entries where source_id='${p}'and source_type='PAYROLL_ATTENDANCE_ACCRUAL'`)).toBe(today)
 await run('update erp.accounting_period_control set closed_through=null')
 await refused(`select public.erp_cp7_preview_attendance_choice_v1('CHOOSE',${js(payload(f,'EXPENSE'))})`,/CP7_S03_EXPENSE_BEFORE_WIP_AVAILABLE/)
 await save('CHOOSE',payload(f,'CARRY'));await sewn(m,yesterday,10)
 await refused(`select public.erp_cp7_preview_attendance_choice_v1('ALLOCATE',${js(payload(f,null,yesterday))})`,/CP7_S03_ALLOCATION_BEFORE_WIP_AVAILABLE/)
 await sewn(m,today,10);expect((await save('ALLOCATE',payload(f,null,today))).status).toBe('COMMITTED')
})

test('special and historically attendance-exempt sources remain outside the chosen normal Mandor cents',async()=>{
 const f=await fixture(),special=await contractor(f.f,true),before=await day(-4),exempt=await contractor(before)
 await payroll(special,f.f,'22.02');await payroll(exempt,f.f,'33.03')
 // The old cost was legitimately APPROVED while attendance was required.
 // Explicit administrative master fixture + retained Native policy writer
 // make that historical source exempt before S03 use. No posted cost is seeded.
 const current=await one(`select id::text from erp.contractor_hpp_policy_versions where contractor_id='${exempt}'`)
 await run(`update erp.contractors set attendance_required=false where id='${exempt}'`)
 await one(`select erp.set_contractor_hpp_policy_v1(${js({contractor_id:exempt,effective_from:f.f,is_special:false,attendance_required:false,reason:'Historical source current exemption before any S03 choice'})},'${randomUUID()}','${current}')`)
 const r=await preview('CHOOSE',payload(f.f,'EXPENSE'));expect(r.amount_cents).toBe('100003');expect(r.source_count).toBe('1')
 await save('CHOOSE',payload(f.f,'EXPENSE'))
 expect(await one("select sum(debit-credit)::text from erp.journal_lines where account_id=erp.account_id('WIP')")).toBe('55.05')
})

test('same-day corrections append both directions; only an owning inverse releases the original payroll source',async()=>{
 const f=await fixture(0);const first=await save('CHOOSE',payload(f.f,'EXPENSE'))
 const journal=await one(`select journal_id::text from cp7_attendance_choice.decisions_v1 where id='${first.decision_id}'`)
 await refused(`select erp.reverse_journal('${journal}','Generic reversal must not detach its owning choice')`,/CP7_S03_OWNING_INVERSE_REQUIRED/)
 await save('CORRECT',payload(f.f,'CARRY'));const third=await save('CORRECT',payload(f.f,'EXPENSE'))
 expect(await one('select count(*)::text from cp7_attendance_choice.decisions_v1')).toBe('3')
 expect(await one('select count(*)::text from cp7_attendance_choice.reversals_v1')).toBe('2')
 expect(await one(`select correction_of is not null from cp7_attendance_choice.decisions_v1 where id='${third.decision_id}'`)).toBe(true)
 await save('REVERSE',payload(f.f));await one(`select erp.cancel_unpaid_payroll('${f.p}','Legitimate whole source cancellation after owning release')`)
 expect(await one(`select status from erp.payroll_settlements where id='${f.p}'`)).toBe('REVERSED')
 expect(await one("select sum(debit-credit)::text from erp.journal_lines where account_id=erp.account_id('WIP')")).toBe('0.00')
})

test('closed source permits a distinct open carry destination, but owning corrections respect the affected closed period',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await run(`update erp.accounting_period_control set closed_through='${f.f}'`)
 await refused(`select public.erp_cp7_preview_attendance_choice_v1('REVERSE',${js(payload(f.f))})`,/CP7_S03_PERIOD_CLOSED/)
 await sewn(f.m,today,10);await save('ALLOCATE',payload(f.f,null,today))
 await run(`update erp.accounting_period_control set closed_through='${today}'`)
 await refused(`select public.erp_cp7_preview_attendance_choice_v1('CANCEL_ALLOCATION',${js(payload(f.f))})`,/CP7_S03_PERIOD_CLOSED/)
 await run(`update erp.accounting_period_control set closed_through='${f.f}'`)
 expect((await save('CANCEL_ALLOCATION',payload(f.f))).status).toBe('COMMITTED')
})

test('private history is append-only and public wrappers never expose private DML authority',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'))
 for(const sql of ['update cp7_attendance_choice.decisions_v1 set reason=reason','delete from cp7_attendance_choice.decisions_v1','truncate cp7_attendance_choice.decisions_v1 cascade'])
  await refused(sql,/CP7_S03_APPEND_ONLY/)
 for(const role of ['anon','authenticated','service_role']){
  expect(await one(`select has_table_privilege('${role}','cp7_attendance_choice.decisions_v1','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')`)).toBe(false)
  expect(await one(`select has_function_privilege('${role}','cp7_attendance_choice.choose_v1(date,date,text,text,uuid,jsonb,uuid)','EXECUTE')`)).toBe(false)
  expect(await one(`select has_function_privilege('${role}','public.erp_cp7_save_attendance_choice_v1(text,jsonb,uuid)','EXECUTE')`)).toBe(role==='authenticated')
 }
 expect(await one(`select cp7_attendance_choice.inner_uuid_v1('${owner}','00000000-0000-4000-8000-000000000002','NATIVE_CREATE')<>cp7_attendance_choice.inner_uuid_v1('00000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000002','NATIVE_CREATE')`)).toBe(true)
})

test('all22 installed catalog matches exact additive identities; preuse removal restores every old object and reinstall stays exact',async()=>{
 const check=execFileSync('python',['-B',resolve(HERE,'local_catalog.py'),'--check','/tmp/s03-local-catalog.json'],{encoding:'utf8'})
 expect(check).toContain('LOCAL_ALL22_ADDITIVE_TRANSITION_PASS')
 const data=await census()
 for(const definition of Object.values(derived.originals)as string[])await run(definition)
 await run(`drop function public.erp_cp7_get_attendance_choice_v1(date,date,integer,integer);
 drop function public.erp_cp7_preview_attendance_choice_v1(text,jsonb);
 drop function public.erp_cp7_save_attendance_choice_v1(text,jsonb,uuid);
 drop schema cp7_attendance_choice cascade`)
 expect(await catalog()).toEqual(catalogBefore)
 const old=Object.fromEntries(Object.entries(data).filter(([key])=>!key.startsWith('cp7_attendance_choice.')))
 expect(await census()).toEqual(old)
 await run(readFileSync(resolve(HERE,'choice.sql'),'utf8'))
 await run(readFileSync(resolve(HERE,'readers.sql'),'utf8'))
 for(const definition of Object.values(derived.clones)as string[])await run(definition)
 await run('revoke all on all functions in schema cp7_attendance_choice from public,anon,authenticated,service_role')
 for(const definition of Object.values(derived.patched)as string[])await run(definition)
 expect(await catalog()).toEqual(catalogInstalled);expect(await census()).toEqual(data)
})

test('bounded history includes each allocation and inverse once and every read/preview remains row-and-sequence unchanged',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,today,10)
 await save('ALLOCATE',payload(f.f,null,today));await save('CANCEL_ALLOCATION',payload(f.f));await save('REVERSE',payload(f.f))
 const before=await census(),events:any[]=[]
 for(let offset=0;offset<4;offset++){
  const page=await one(`select public.erp_cp7_get_attendance_choice_v1('${f.f}','${f.f}',${offset},1)`)
  expect(page.history_total).toBe('4');expect(page.history).toHaveLength(1);expect(page.next_offset).toBe(offset<3?offset+1:null)
  events.push(page.history[0]);expect(page.current_choice).toBeNull();expect(page.current_allocation).toBeNull()
 }
 expect(events.map(e=>e.event)).toEqual(['REVERSE','CANCEL_ALLOCATION','ALLOCATE','CHOOSE'])
 expect(new Set(events.map(e=>e.event_id)).size).toBe(4)
 await preview('CHOOSE',payload(f.f,'CARRY'));expect(await census()).toEqual(before)
 await refused(`select public.erp_cp7_get_attendance_choice_v1('${f.f}','${f.f}',0,51)`,/CP7_S03_PAGE/)
})

test('owning REVERSE receipt event_id names its exact immutable reversal row',async()=>{
 const f=await fixture();const first=await save('CHOOSE',payload(f.f,'CARRY')),result=await save('REVERSE',payload(f.f))
 expect(await one(`select id::text from cp7_attendance_choice.reversals_v1 where decision_id='${first.decision_id}'`)).toBe(result.event_id)
})

test('newly eligible later output refuses before audit; a harmless future destination-only policy version keeps carry current',async()=>{
 const f=await fixture(),excluded=randomUUID(),later=await contractor(today)
 await run(`insert into erp.contractors(id,contractor_code,contractor_name)values('${excluded}','NEW-ELIGIBILITY','Existing output without policy')`)
 await sewn(f.m,today,10);await sewn(excluded,today,5);await sewn(later,today,5)
 await save('CHOOSE',payload(f.f,'CARRY'));const result=await save('ALLOCATE',payload(f.f,null,today))
 await refused(`select erp.set_contractor_hpp_policy_v1(${js({contractor_id:excluded,effective_from:today,is_special:false,attendance_required:true,reason:'Previously excluded output would change active carried denominator'})},'${randomUUID()}',null)`,/CP7_S03_ACTIVE_CARRY_POLICY_CHANGED/)
 const current=await one(`select id::text from erp.contractor_hpp_policy_versions where contractor_id='${later}'`),tomorrow=await day(1)
 const original=await one(`select source_manifest_sha256 from erp.attendance_hpp_pools where id='${result.pool_id}'`)
 // Unlike source_json, exact Native destination_json does not bind effective_to.
 // The retained failed expectation over-restricted a legitimate future policy.
 // This checks unchanged current eligibility/IDs/quantity plus Native validation.
 const future=await one(`select erp.set_contractor_hpp_policy_v1(${js({contractor_id:later,effective_from:tomorrow,is_special:false,attendance_required:true,reason:'Future version leaves current destination identity and eligibility unchanged'})},'${randomUUID()}','${current}')`)
 expect(future.policy_version_id).not.toBe(current)
 expect(await one(`select erp._cp3_manifest_sha256(cp7_attendance_choice.pool_manifest_v1('${result.pool_id}'))`)).toBe(original)
 expect(await one(`select erp.validate_attendance_hpp_pool_v1('${result.pool_id}')->>'validation'`)).toBe('PASS')
})

test('whole-payroll E05 context refuses its first Native cash inverse while cost is held; individual payment inverse preserves held cost',async()=>{
 const f=await fixture(),capture=await one(`select cp7_attendance_choice.capture_v1('${f.f}','${f.f}',true)`)
 await save('CHOOSE',payload(f.f,'EXPENSE'))
 const payment=randomUUID(),cash=randomUUID(),key=randomUUID()
 await one(`select erp.post_journal('LOCAL_CAPITAL','${randomUUID()}','${today}','Explicit cash for isolated context control',
 jsonb_build_array(jsonb_build_object('mapping_key','CASH','debit',600,'credit',0),jsonb_build_object('mapping_key','CAPITAL','debit',0,'credit',600)))`)
 const j=await one(`select erp.post_journal('PAYROLL_INSTALLMENT','${payment}','${today}','Actual retained Native cash journal for local E05 context model',
 jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',600,'credit',0,'contractor_id','${f.m}'),
 jsonb_build_object('mapping_key','CASH','debit',0,'credit',600,'contractor_id','${f.m}')))`)
 // Declared administrative E05 metadata/context fixture, not actual E05 writer.
 await run(`insert into cp7_installment.payments(id,payroll_id,amount,payment_date,cash_account_id,cash_coa_id,journal_id,created_by,request_id)
 values('${payment}','${f.p}',600,'${today}','${cash}',erp.account_id('CASH'),'${j}','${owner}','${key}');
 insert into cp7_installment.command_context values(pg_backend_pid(),txid_current(),'${owner}','${key}','REVERSE_PAYROLL',${js({payroll_id:f.p})},'1',null)`)
 await refused(`select erp.reverse_journal('${j}','Whole E05 inverse cannot spend cash before its claimed cost guard')`,/CP7_S03_PAYROLL_CLAIMED/)
 await run("update cp7_installment.command_context set action='REVERSE_PAYMENT'")
 await one(`select erp.reverse_journal('${j}','Individual payment correction must remain lawful settlement')`)
 expect((await one(`select cp7_attendance_choice.capture_v1('${f.f}','${f.f}',true)`)).source_binding).toBe(capture.source_binding)
 expect(await one(`select count(*)::text from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id='${f.p}'`)).toBe('1')
})

test('late HPP dependency failure rolls all business rows back and records the exact nontransactional Native audit allocation honestly',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,today,10)
 await run('update local_s03.controls set fail_hpp=true')
 const p=payload(f.f,null,today),r=await preview('ALLOCATE',p),before=await census()
 await run('savepoint failed_native_dependency')
 try{
  await expect(one(`select public.erp_cp7_save_attendance_choice_v1('ALLOCATE',${js({...p,review_token:r.review_token})},'${randomUUID()}')`)).rejects.toThrow(/LOCAL_EXPLICIT_HPP_DEPENDENCY_FAILURE/)
 }finally{await run('rollback to savepoint failed_native_dependency;release savepoint failed_native_dependency')}
 const after=await census(),priorAudit=before['erp.audit_logs_id_seq']as [string,boolean]
 expect(after['erp.audit_logs_id_seq']).toEqual([String(BigInt(priorAudit[0])+1n),true])
 const withoutAudit=(v:Record<string,unknown>)=>Object.fromEntries(Object.entries(v).filter(([key])=>key!=='erp.audit_logs_id_seq'))
 expect(withoutAudit(after)).toEqual(withoutAudit(before))
 // Native CREATE inserts its audit before ACTIVATE reaches this injected
 // dependency failure. PostgreSQL nextval is not rolled back. This is exact
 // row atomicity plus one named audit allocation, not absolute full no-DML.
 expect(await one('select count(*)::text from cp7_attendance_choice.allocations_v1')).toBe('0')
 expect(await one('select count(*)::text from erp.attendance_hpp_pools')).toBe('0')
})

test('additional CALCULATED payroll existing before choice refuses public and direct APPROVE before audited rebuild or recalculate',async()=>{
 const f=await fixture(),other=await contractor(f.f),pending=await payroll(other,f.f,'11.01',false)
 expect(await one(`select status from erp.payroll_settlements where id='${pending}'`)).toBe('CALCULATED')
 const p=await one(`select cp7_payroll.settlement_document('${pending}')`),intent={id:pending,review_token:p.review_token,change_reason:'An existing unapproved payroll must wait for owning choice release'}
 const key=randomUUID(),command=`select public.erp_cp7_save_payroll_v1('APPROVE',${js(intent)},'${key}','${p.row_version}')`
 await save('CHOOSE',payload(f.f,'CARRY'))
 await refused(command,/CP7_S03_PERIOD_CLAIMED/)
 await refused(`select erp.approve_payroll('${pending}')`,/CP7_S03_PERIOD_CLAIMED/)
 await save('REVERSE',payload(f.f))
 const approved=await one(command);expect(approved.status).toBe('APPROVED')
 expect(await one(`select count(*)::text from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id='${pending}'`)).toBe('1')
})

async function poolRead(id:string,closed:string|null=null){
 return one(`select cp7_hpp_pool.pool_json(p,${closed?lit(closed):'null'}::date)from erp.attendance_hpp_pools p where id='${id}'`)
}
async function ordinaryPool(f:{f:string},activate=true){
 const p=await one(`select erp.create_attendance_hpp_pool_v1(${js({period_start:f.f,period_end:f.f,reason:'Ordinary Native pool for independent reader controls'})},'${randomUUID()}')`)
 if(activate)await one(`select erp.activate_attendance_hpp_pool_v1('${p.pool_id}','Ordinary Native activation for reader controls','${randomUUID()}',${p.row_version})`)
 return p.pool_id as string
}
async function ordinaryCancelledThenHeld(){
 const f=await fixture(),e=await sewn(f.m,f.f,3),id=await ordinaryPool(f)
 const version=await one(`select row_version from erp.attendance_hpp_pools where id='${id}'`)
 await one(`select erp.cancel_attendance_hpp_pool_v1('${id}','Ordinary inverse before zero-output choice','${randomUUID()}',${version})`)
 const eventVersion=await one(`select row_version from erp.sewing_terminal_events where id='${e.event}'`)
 await one(`select erp.reverse_sewing_terminal_v1('${e.event}','Lawful terminal inverse after ordinary pool cancellation','${randomUUID()}',${eventVersion})`)
 const choice=await save('CHOOSE',payload(f.f,'CARRY'))
 return {...f,id,choice}
}

test('reader leaves disjoint ordinary P2 pool and preview JSON byte-exact while P1 is carried to P2',async()=>{
 const f=await fixture(),out=await day(-1)
 await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,out,10)
 await save('ALLOCATE',payload(f.f,null,out));await payroll(f.m,out,'20.02')
 const ordinary=await ordinaryPool({f:out})
 const before=await census()
 const pair=await one(`select jsonb_build_array(cp7_hpp_pool.pool_json(p,null),local_s03.reference_pool_json_v1(p,null))from erp.attendance_hpp_pools p where id='${ordinary}'`)
 expect(pair[0]).toEqual(pair[1]);expect(pair[0].actions).toEqual(['CANCEL'])
 expect(pair[0]).not.toHaveProperty('attendance_choice');expect(pair[0]).not.toHaveProperty('period_hold')
 const previews=await one(`select jsonb_build_array(cp7_hpp_pool.preview('${out}','${out}',null),local_s03.reference_preview_v1('${out}','${out}',null))`)
 expect(previews[0]).toEqual(previews[1]);expect(await census()).toEqual(before)
})

test('owned ACTIVE reader exposes exact P1 source and P2 output, closes legacy actions, and respects output rather than source closure',async()=>{
 const f=await fixture(),out=await day(-1),choice=await save('CHOOSE',payload(f.f,'CARRY'))
 await sewn(f.m,out,10);const made=await save('ALLOCATE',payload(f.f,null,out))
 const before=await census(),open=await poolRead(made.pool_id)
 expect(open.actions).toEqual([])
 expect(open.attendance_choice).toEqual({domain:'ATTENDANCE_PERIOD_CHOICE',decision_id:choice.decision_id,
  allocation_id:made.event_id,source_period_start:f.f,source_period_end:f.f,output_period_start:out,output_period_end:out,output_period_closed:false})
 expect(open).not.toHaveProperty('period_hold');expect(await census()).toEqual(before)
 await run(`update erp.accounting_period_control set closed_through='${f.f}'`)
 const closed=await poolRead(made.pool_id,f.f)
 expect(closed.period_start).toBe(f.f);expect(closed.period_end).toBe(f.f);expect(closed.period_closed).toBe(true)
 expect(closed.attendance_choice.output_period_closed).toBe(false);expect(closed.actions).toEqual([])
 await run(`update erp.accounting_period_control set closed_through='${out}'`)
 expect((await poolRead(made.pool_id,out)).attendance_choice.output_period_closed).toBe(true)
})

test('owned CANCELLED pool retains permanent S03 identity after inverse and decision correction then reversal',async()=>{
 const f=await fixture(),choice=await save('CHOOSE',payload(f.f,'CARRY'))
 await sewn(f.m,today,10);const made=await save('ALLOCATE',payload(f.f,null,today))
 await save('CANCEL_ALLOCATION',payload(f.f))
 const first=await poolRead(made.pool_id)
 expect(first.status).toBe('CANCELLED');expect(first.actions).toEqual([])
 expect(first.attendance_choice.decision_id).toBe(choice.decision_id)
 const next=await save('CORRECT',payload(f.f,'CARRY'));expect(next.decision_id).not.toBe(choice.decision_id)
 expect((await poolRead(made.pool_id)).attendance_choice).toEqual(first.attendance_choice)
 await save('REVERSE',payload(f.f));const before=await census(),historical=await poolRead(made.pool_id)
 expect(historical.attendance_choice).toEqual(first.attendance_choice);expect(historical.actions).toEqual([])
 expect(historical).not.toHaveProperty('period_hold');expect(await census()).toEqual(before)
})

test('stale owned Native composite refuses with READ_CHANGED after an owning inverse and changes no rows or sequences',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,today,10)
 const made=await save('ALLOCATE',payload(f.f,null,today))
 const old=await one(`select to_jsonb(p)from erp.attendance_hpp_pools p where id='${made.pool_id}'`)
 await save('CANCEL_ALLOCATION',payload(f.f))
 await refused(`select cp7_hpp_pool.pool_json(jsonb_populate_record(null::erp.attendance_hpp_pools,${js(old)}),null)`,/CP7_S03_HPP_READ_CHANGED/)
})

test('ordinary historical pool in an exactly held P1 has period_hold with no false S03 ownership or replacement action',async()=>{
 const f=await ordinaryCancelledThenHeld(),before=await census(),row=await poolRead(f.id)
 expect(row.actions).toEqual([]);expect(row).not.toHaveProperty('attendance_choice')
 expect(row.period_hold).toEqual({domain:'ATTENDANCE_PERIOD_CHOICE',decision_id:f.choice.decision_id,source_period_start:f.f,source_period_end:f.f})
 const adjacent=await day(-2)
 const pair=await one(`select jsonb_build_array(cp7_hpp_pool.preview('${adjacent}','${adjacent}',null),local_s03.reference_preview_v1('${adjacent}','${adjacent}',null))`)
 expect(pair[0]).toEqual(pair[1]);expect(pair[0]).not.toHaveProperty('period_hold')
 expect(await census()).toEqual(before)
})

test('late P1 output leaves Native preview READY but held legacy preview BLOCKED without figures or a usable create token',async()=>{
 const f=await ordinaryCancelledThenHeld();await sewn(f.m,f.f,4,3)
 const before=await census(),native=await one(`select erp.preview_attendance_hpp_pool_v1('${f.f}','${f.f}')`)
 expect(native.status).toBe('READY');expect(native.denominator_qty).toBe(4)
 const result=await one(`select cp7_hpp_pool.preview('${f.f}','${f.f}',null)`)
 expect(result.status).toBe('BLOCKED');expect(result.can_create).toBe(false)
 expect(result.blocker.code).toBe('CP7_S03_PERIOD_HELD')
 expect(result.period_hold.decision_id).toBe(f.choice.decision_id)
 for(const key of ['numerator_amount','denominator_qty','unit_cost_per_sewn_pcs','source_count','destination_count','po_count','manifest_sha256','review_token'])expect(result[key]).toBeNull()
 expect(result.pos).toEqual([]);expect(await census()).toEqual(before)
 await refused(`select erp.create_attendance_hpp_pool_v1(${js({period_start:f.f,period_end:f.f,reason:'Direct Native route still honors exact current S03 period claim'})},'${randomUUID()}')`,/CP7_S03_PERIOD_CLAIMED/)
})

test('ordinary reader JSON is unaffected by caller DateStyle while its exact Native composite stays current',async()=>{
 const f=await fixture();await sewn(f.m,f.f,3);const id=await ordinaryPool(f)
 const previous=await one('show DateStyle')
 await run('savepoint reader_datestyle')
 try{
  await run("set DateStyle='German, DMY'")
  const before=await census()
  const pair=await one(`select jsonb_build_array(cp7_hpp_pool.pool_json(p,null),local_s03.reference_pool_json_v1(p,null))from erp.attendance_hpp_pools p where id='${id}'`)
  expect(pair[0]).toEqual(pair[1]);expect(await census()).toEqual(before)
 }catch(error){await run('rollback to savepoint reader_datestyle');throw error}
 finally{await run(`select set_config('DateStyle',${lit(previous)},false);release savepoint reader_datestyle`)}
})

test('existing Admin HPP view can read owned metadata but gains no Owner-only S03 action',async()=>{
 const f=await fixture();await save('CHOOSE',payload(f.f,'CARRY'));await sewn(f.m,today,10)
 const made=await save('ALLOCATE',payload(f.f,null,today)),adminActor=randomUUID()
 await run(`insert into local_s03.identity(actor,role_code,can_view,can_manage)values('${adminActor}','ADMIN',true,false)`)
 await run(`select set_config('local_s03.actor','${adminActor}',false)`)
 try{
  const before=await census(),workspace=await one(`select cp7_hpp_pool.workspace(0,25,'${f.f}','${f.f}')`)
  const row=workspace.pools.find((p:any)=>p.id===made.pool_id)
  expect(row.attendance_choice.domain).toBe('ATTENDANCE_PERIOD_CHOICE');expect(row.actions).toEqual([])
  expect(workspace.can_manage).toBe(false);expect(workspace.preview.blocker.code).toBe('CP7_S03_PERIOD_HELD')
  expect(await census()).toEqual(before)
  await refused(`select public.erp_cp7_preview_attendance_choice_v1('CANCEL_ALLOCATION',${js(payload(f.f))})`,/CP7_S03_OWNER_REQUIRED/)
 }finally{await run(`select set_config('local_s03.actor','${owner}',false)`)}
})
