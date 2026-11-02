// Isolated SQL controls for the NEW private payment owner. Prior95 retained.
// Actual Native definition bodies are exercised on reduced model tables.
// Native constraints/triggers, Auth, credit materialization, stock/HPP and
// two PostgreSQL backends are not installed or qualified by this model.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const [runtime,output,mode]=process.argv.slice(2);assert(runtime&&output);
assert(mode==='--guards-only','Only new Native-table boundary controls execute');
const runtimePackage=JSON.parse(await readFile(new URL('../package.json',pathToFileURL(runtime))));
assert.equal(runtimePackage.version,'0.5.14');
const {PGlite}=await import(pathToFileURL(runtime).href),db=new PGlite();
const here=fileURLToPath(new URL('.',import.meta.url));
const reference=JSON.parse(await readFile(here+'NATIVE_PAYMENT_OWNER_REFERENCE.json'));
assert.equal(reference.head,'6e61506c10a18541c104b981bd438e78b175b5d1');
assert.equal(reference.functions_unchanged_in_actual_after_committed_E_use,true);
const guardReference=JSON.parse(await readFile(here+'NATIVE_PAYMENT_GUARD_REFERENCE.json'));
assert.equal(guardReference.head,reference.head);
const retained=JSON.parse(await readFile(here+'PAYMENT_RETAINED19_MODEL_CONTROLS.json'));
assert.equal(retained.completed_controls_retained,19);assert.equal(retained.original_failure_relabelled_PASS,false);
for(const[name,expected]of Object.entries(retained.source_files)){const raw=await readFile(here+name);
 assert.deepEqual({bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')},expected);}
const derived=JSON.parse(execFileSync('python',['-B','-c',
 "import importlib.util,json;from pathlib import Path;p=Path('native_payment_routes.py');s=importlib.util.spec_from_file_location('model_exact_payment_routes',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);r=json.loads(Path('NATIVE_PAYMENT_OWNER_REFERENCE.json').read_bytes());v,p=m.derive(r['functions']);print(json.dumps(v))"],
 {cwd:here,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
assert.equal(Object.keys(derived).length,8);
const results=[],pin=raw=>({bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
const id=n=>'50000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(1),mandor=id(2),customer=id(3),shop=id(4),payable=id(10),ar=id(11),
 income=id(12),bank=id(13),cashAccount=id(14),ap=id(15);
let serial=1000;const next=()=>id(++serial),sha='a'.repeat(64);
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
const check=label=>results.push({label,result:'PASS'});
async function tx(body){await db.exec('BEGIN');try{const v=await body();await db.exec('COMMIT');return v;}
 catch(error){await db.exec('ROLLBACK');throw error;}}
async function scope(action,body){return tx(async()=>{
 const request=next();await db.query(`insert into cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response)
  values($1,$2,$3,'{}',$4,'{}')`,[actor,request,action,sha]);
 await db.query('insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),$1,$2,$3,$4)',[actor,request,action,sha]);
 const v=await body(request);await db.exec('delete from cp7_mandor_shop.command_context');return v;
});}
async function refused(label,body,message,code='P0001'){
 let error;try{await body();}catch(e){error=e;}assert(error,label+': rejection required');
 assert.equal(error.code,code,label+': SQLSTATE');assert(error.message.includes(message),label+': '+error.message);
 results.push({label,result:'REFUSED_AS_REQUIRED',SQLSTATE:error.code,error:message});
}
const cents=async(sql,args=[])=>BigInt(await scalar('select round(100*('+sql+'))::text',args));
const paid=sale=>cents('cp7_credit.current_effective_paid($1)',[sale]);
async function snapshot(){return(await db.query(`select
 (select count(*)from erp.journal_entries)::int journals,(select count(*)from erp.journal_lines)::int legs,
 (select count(*)from cp7_mandor_shop.settlements)::int settlements,
 (select count(*)from cp7_mandor_shop.allocation_events)::int events,
 (select count(*)from cp7_mandor_shop.requests)::int requests,
 (select count(*)from cp7_mandor_shop.payment_work)::int work,
 (select count(*)from cp7_mandor_shop.command_context)::int context`)).rows[0];}
async function event(allocation,kind,request){
 const st=await scalar('select(select to_jsonb(s)from cp7_mandor_shop.allocation_states s where allocation_id=$1)',[allocation]);
 await db.query(`insert into cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,predecessor_id,kind,actor,request_id)
 values($1,$2,$3,$4,$5,$6,$7)`,[next(),allocation,(st?.last_ordinal||0)+1,st?.last_event_id||null,kind,actor,request]);
}
async function sale(amount='300000'){
 const sale=next();await scope('POST_SALE',async()=>{
  await db.query(`insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status)
   values($1,$2,$3,'2026-10-05T02:00:00Z','POSTED')`,[sale,'INV-'+sale,customer]);
  await db.query('insert into cp7_model.invoice_amounts values($1,$2,0)',[sale,amount]);
  await db.query(`insert into cp7_mandor_shop.sales(sale_id,contractor_id,customer_id,contractor_name_at_post,posted_by)
   values($1,$2,$3,'Epi',$4)`,[sale,mandor,customer,actor]);
 });return sale;
}
async function payroll(date='2026-10-12',gross='2000000'){
 const payroll=next();await scope('RESERVE',async()=>{
  await db.query(`insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,
   status,labor_total,attendance_total,reimburse_total,deduction_total,manual_adjustment,net_payable,row_version)
   values($1,$2,$3,$4::date,$4::date+6,'DRAFT',$5,0,0,0,0,$5,1)`,[payroll,'PAY-'+payroll,mandor,date,gross]);
  await db.query('insert into erp.payroll_work_items(id,payroll_id,amount)values($1,$2,$3)',[next(),payroll,gross]);
  await db.query('insert into cp7_mandor_shop.payroll_identities(payroll_id,contractor_id,created_by)values($1,$2,$3)',[payroll,mandor,actor]);
 });return payroll;
}
async function reserve(sale,payroll,amount){return scope('RESERVE',async request=>{
 const allocation=next(),deduction=next();
 await db.query(`insert into cp7_mandor_shop.allocations(id,sale_id,payroll_id,contractor_id,amount,actor,request_id)
  values($1,$2,$3,$4,$5,$6,$7)`,[allocation,sale,payroll,mandor,amount,actor,request]);
 await db.query(`insert into erp.payroll_deductions(id,payroll_id,deduction_type,amount)values($1,$2,'OTHER',$3)`,[deduction,payroll,amount]);
 await db.query('insert into cp7_mandor_shop.deduction_links values($1,$2,$3,$4,$5,$6)',[allocation,sale,payroll,mandor,amount,deduction]);
 await event(allocation,'RESERVE',request);return{allocation,sale,payroll,amount,deduction};
});}
async function approve(payroll){await db.query(`update erp.payroll_settlements p set status='APPROVED',
 deduction_total=(select coalesce(sum(amount),0)from erp.payroll_deductions where payroll_id=p.id),
 net_payable=p.labor_total-(select coalesce(sum(amount),0)from erp.payroll_deductions where payroll_id=p.id)where p.id=$1`,[payroll]);}
async function enter(payroll,source='PAYROLL',action='PAY',request=next(),date='2026-10-19'){
 const before=await scalar('select status from erp.payroll_settlements where id=$1',[payroll]);
 const payload={...(source==='PAYROLL'?{id:payroll}:{payroll_id:payroll}),payment_date:date,
  cash_account_id:cashAccount,review_token:'0'.repeat(32),change_reason:'Model explicit request'};
 const native=source==='PAYROLL'?action:action==='REVERSE_PAYROLL'?(before==='PAID'?'REVERSE':'CANCEL'):'PAY';
 await db.query('insert into cp7_payroll.settlement_context values(pg_backend_pid(),txid_current(),$1,$2,$3)',[actor,payroll,native]);
 if(source==='PAYROLL')await db.query('insert into cp7_payroll.settlement_requests values($1,$2,$3,$4::jsonb,$5,null)',[actor,request,action,JSON.stringify(payload),'1']);
 else await db.query('insert into cp7_installment.command_context values(pg_backend_pid(),txid_current(),$1,$2,$3,$4::jsonb,$5,$6)',[actor,request,action,JSON.stringify(payload),'1',next()]);
 await db.query('select cp7_mandor_shop.payment_begin($1,$2,$3::jsonb,$4,$5)',[source,action,JSON.stringify(payload),request,'1']);
 return{payroll,source,action,request,payload};
}
async function leave(value){await db.query('select cp7_mandor_shop.payment_finish($1)',[value.payroll]);
 await db.exec('delete from cp7_payroll.settlement_context;delete from cp7_installment.command_context');
 if(value.source==='PAYROLL')await db.query(`update cp7_payroll.settlement_requests set response='{}'where actor=$1 and request_id=$2`,[actor,value.request]);
}
async function pay(payroll,{source='PAYROLL',amount=null,date='2026-10-19',skipOwner=false,revokeAfter=false}={}){return tx(async()=>{
 const value=await enter(payroll,source,'PAY',next(),date);
 await db.query('update erp.payroll_settlements set payment_date=$2::date,payment_cash_account_id=$3 where id=$1',[payroll,date,cashAccount]);
 if(source==='PAYROLL')await db.query('select erp.post_payroll_payment($1)',[payroll]);
 else{
  const payment=await scalar('select native_payment_id from cp7_installment.command_context');
  const remaining=await scalar(`select p.net_payable-coalesce((select sum(amount)from cp7_installment.payments
   where payroll_id=p.id and reversal_journal_id is null),0)from erp.payroll_settlements p where p.id=$1`,[payroll]);
  let journal;
  if(BigInt(String(amount))===BigInt(String(remaining).split('.')[0])){
   await db.query('select cp7_installment.final_payment($1,$2)',[payroll,amount]);
   journal=await scalar(`select id from erp.journal_entries where source_type='PAYROLL_INSTALLMENT'and source_id=$1 and status='POSTED'`,[payment]);
  }else journal=await scalar(`select erp.post_journal('PAYROLL_INSTALLMENT',$1,'2026-10-19','Model partial Native caller',
    jsonb_build_array(jsonb_build_object('account_id',$2::uuid,'debit',$3::numeric,'credit',0,'contractor_id',$4::uuid),
    jsonb_build_object('account_id',$5::uuid,'debit',0,'credit',$3::numeric,'contractor_id',$4::uuid)))`,[payment,payable,amount,mandor,bank]);
  await db.query(`insert into cp7_installment.payments(id,payroll_id,amount,payment_date,cash_account_id,cash_coa_id,journal_id,created_by,request_id)
   values($1,$2,$3,'2026-10-19',$4,$5,$6,$7,$8)`,[payment,payroll,amount,cashAccount,bank,journal,actor,value.request]);
  value.payment=payment;value.journal=journal;
 }
 if(revokeAfter)await db.exec("select set_config('cp7_model.permissions','deny',true)");
 if(!skipOwner)await leave(value);return value;
});}
async function reverse(payroll,source='PAYROLL',action='REVERSE'){return tx(async()=>{
 const value=await enter(payroll,source,action);
 if(action==='REVERSE_PAYMENT')await db.query('select cp7_installment.reopen_settlement($1,$2)',[payroll,'Model reverse final installment']);
 else if(action==='CANCEL')await db.query('select erp.cancel_unpaid_payroll($1,$2)',[payroll,'Model cancel selected week']);
 else await db.query('select erp.reverse_paid_payroll($1,$2)',[payroll,'Model lawful full reversal']);
 await leave(value);return value;
});}

try{
 await db.exec(`create role anon;create role authenticated;create role service_role;create role cp7_payroll_write nologin;
  create schema erp;create schema auth;create schema extensions;create schema cp7_payroll;
  create schema cp7_installment;create schema cp7_credit;create schema cp7_attendance_choice;create schema cp7_model;
  create function auth.uid()returns uuid language sql stable as $$select nullif(current_setting('cp7_model.actor',true),'')::uuid$$;
  create function auth.jwt()returns jsonb language sql stable as $$select '{"role":"authenticated"}'::jsonb$$;
  create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select case when $2='sha256'then pg_catalog.sha256($1)end$$;
  create function erp.get_my_access_v1()returns jsonb language sql stable as $$select jsonb_build_object('allowed',true,'actor',auth.uid(),'permissions',current_setting('cp7_model.permissions',true))$$;
  create function erp.has_permission(text)returns boolean language sql stable as $$select coalesce(nullif(current_setting('cp7_model.permissions',true),''),'allow')='allow'$$;
  create function erp.require_internal()returns void language plpgsql as $$begin return;end$$;
  create function erp.require_owner_admin()returns void language plpgsql as $$begin return;end$$;
  create function erp.current_app_user_id()returns uuid language sql stable as $$select auth.uid()$$;
  create function erp._cp3_lock_business_period(date,date)returns void language plpgsql as $$begin return;end$$;
  create function erp._cp3_business_date(timestamptz)returns date language sql stable as $$select($1 at time zone'Asia/Jakarta')::date$$;
  create function erp.resolve_accounting_transaction_date(date)returns date language sql stable as $$select $1$$;
  create function erp.check_opening_cash_advance_payroll_v1(uuid)returns void language plpgsql as $$begin return;end$$;
  create function erp.bb_check_opening_payable_payroll_v1(uuid)returns void language plpgsql as $$begin return;end$$;
  create function cp7_attendance_choice.assert_payroll_unclaimed_v1(uuid)returns void language plpgsql as $$begin return;end$$;
  create function erp.refresh_contractor_issue_payroll_status(uuid)returns void language plpgsql as $$begin return;end$$;
  create function erp.rebuild_bs_component_counters(uuid)returns void language plpgsql as $$begin return;end$$;
  create function erp.bb_assert_opening_balance_floor_v1(uuid,date)returns void language plpgsql as $$begin return;end$$;`);
 for(const [table,columns]of Object.entries({...reference.columns,...guardReference.columns})){
  const cols=Object.values(columns).sort((a,b)=>a[1]-b[1]);
  let pk=cols.some(c=>c[0]==='id')?['id']:table==='erp.accounting_account_mappings'?['mapping_key']:[];
  if(table==='erp.account_daily_balances')pk=['balance_date','account_id'];
  if(table.endsWith('.settlement_requests'))pk=['actor','request_id'];
  if(table.endsWith('.settlement_context')||table.endsWith('.command_context'))pk=['backend_pid','transaction_id'];
  const fields=cols.map(c=>'"'+c[0]+'" '+c[2]+(c[0]==='id'&&c[2]==='uuid'?' default gen_random_uuid()':c[0]==='id'&&c[2]==='bigint'?' generated by default as identity':''));
  if(pk.length)fields.push('primary key('+pk.map(n=>'"'+n+'"').join(',')+')');
  await db.exec('create table '+table+'('+fields.join(',')+')');
  const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(actual,Object.fromEntries(cols.map(c=>[c[0],c[2]])));
 }
 await db.exec(`create table cp7_model.invoice_amounts(sale_id uuid primary key,net numeric(20,2),ordinary_paid numeric(20,2));
  create function erp.account_id(text)returns uuid language sql stable as $$select account_id from erp.accounting_account_mappings where mapping_key=$1$$;
  create function erp.sale_net_total(uuid)returns numeric language sql stable as $$select net from cp7_model.invoice_amounts where sale_id=$1$$;
  create function cp7_installment.require_context(uuid)returns void language plpgsql as $$begin
   if not exists(select 1 from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current_if_assigned()and actor=auth.uid()and payload->>'payroll_id'=$1::text)then raise exception 'MODEL_NATIVE_INSTALLMENT_CONTEXT_REQUIRED';end if;end$$;
  create function cp7_installment.assert_payment_amount(uuid,numeric,boolean)returns void language plpgsql as $$declare remaining_ numeric;begin
   select p.net_payable-coalesce((select sum(amount)from cp7_installment.payments where payroll_id=p.id and reversal_journal_id is null),0)into remaining_ from erp.payroll_settlements p where p.id=$1;
   if $2<=0 or $2<>remaining_ then raise exception 'MODEL_EXACT_FINAL_CASH_REMAINDER_REQUIRED';end if;end$$;`);
 for(const name of ['schema.sql','events.sql','allocation.sql','offset_projection.sql','payment_owner.sql','payment_guards.sql'])await db.exec((await readFile(here+name)).toString());
 await db.exec(`create function cp7_credit.current_effective_paid(uuid)returns numeric language sql stable as $$
  select ordinary_paid+case when coalesce(current_setting('cp7_model.offset_integrated',true),'yes')='yes'
   then cp7_mandor_shop.invoice_offset_paid($1)else 0 end from cp7_model.invoice_amounts where sale_id=$1$$;`);
 for(const n of ['cp7_payroll.access_now(text)','cp7_payroll.settlement_access(text)','cp7_installment.access_now(text)',
  'cp7_installment.meaning(uuid)','erp.post_journal(text,uuid,date,text,jsonb)','erp._cp3_r4_reverse_journal_internal(uuid,text)'])await db.exec(reference.functions[n][0]);
 for(const sql of Object.values(derived))await db.exec(sql);
 // Rebuilding these model tables is setup, not fresh credit for retained compile control.
 assert.equal(Object.keys(reference.columns).length,32);
 await db.query("select set_config('cp7_model.actor',$1,false)",[actor]);
 await db.query(`insert into erp.contractors(id,contractor_name,is_active,attendance_required)values($1,'Epi',true,false)`,[mandor]);
 await db.query(`insert into erp.customers(id,customer_name,is_active)values($1,'Epi',true),($2,'Ordinary shop',true)`,[customer,shop]);
 await db.query('insert into cp7_mandor_shop.contractor_accounts(contractor_id,customer_id,created_by)values($1,$2,$3)',[mandor,customer,actor]);
 for(const [value,code]of[[payable,'PAYABLE'],[ar,'AR'],[income,'INCOME'],[bank,'BANK'],[ap,'AP']])await db.query('insert into erp.chart_accounts(id,account_code,is_active,is_postable)values($1,$2,true,true)',[value,code]);
 for(const [key,value]of[['CONTRACTOR_PAYABLE',payable],['AR_CUSTOMER',ar],['OTHER_INCOME',income],['AP_VENDOR',ap]])await db.query('insert into erp.accounting_account_mappings(mapping_key,account_id)values($1,$2)',[key,value]);
 await db.query('insert into erp.cash_accounts(id,coa_account_id,is_active)values($1,$2,true)',[cashAccount,bank]);
 await db.exec('insert into erp.accounting_period_control(singleton_id)values(1)');
 check('33 actual Native column-type maps, six new boundary functions and six Native-table triggers compile on the isolated model');
 const invoice=await sale(),week=await payroll();await reserve(invoice,week,'300000');await approve(week);
 const empty=await snapshot();
 await refused('An internal journal primitive cannot invent an FG source without the explicit payroll owner',()=>tx(async()=>{
  await db.query(`select erp.post_journal('FG_MANDOR_PAYROLL_OFFSET',$1,'2026-10-19','Unowned model source',
   jsonb_build_array(jsonb_build_object('account_id',$2::uuid,'debit',300000,'credit',0,'contractor_id',$3::uuid),
   jsonb_build_object('account_id',$4::uuid,'debit',0,'credit',300000,'customer_id',$5::uuid)))`,[next(),payable,mandor,ar,customer]);
 }),'OWNING_COMMAND_REQUIRED','42501');assert.deepEqual(await snapshot(),empty);
 await refused('Even a valid owning context cannot COMMIT a protected FG journal without exact settlement, account and event facts',()=>tx(async()=>{
  await enter(week);await db.query(`update erp.payroll_settlements set status='PAID',payment_date='2026-10-19'where id=$1`,[week]);
  await db.query(`select erp.post_journal('FG_MANDOR_PAYROLL_OFFSET',$1,'2026-10-19','Missing model facts',
   jsonb_build_array(jsonb_build_object('account_id',$2::uuid,'debit',300000,'credit',0,'contractor_id',$3::uuid),
   jsonb_build_object('account_id',$4::uuid,'debit',0,'credit',300000,'customer_id',$5::uuid)))`,[next(),payable,mandor,ar,customer]);
 }),'PROTECTED_JOURNAL_EXACT_FACTS_REQUIRED_AT_COMMIT');assert.deepEqual(await snapshot(),empty);
 await pay(week);assert.equal(await paid(invoice),30000000n);
 const original=await scalar('select journal_id from cp7_mandor_shop.settlements where payroll_id=$1',[week]);
 check('A lawful actual derived Native payroll payment satisfies all new deferred facts and settles the same invoice once');
 await refused('Posted FG journal legs cannot be edited through the Native table',()=>tx(()=>db.query('update erp.journal_lines set credit=credit+1 where journal_entry_id=$1 and credit>0',[original])),'PROTECTED_JOURNAL_LEGS_IMMUTABLE');
 await refused('Changing protected journal source type cannot disguise the offset',()=>tx(()=>db.query("update erp.journal_entries set source_type='MANUAL'where id=$1",[original])),'PROTECTED_JOURNAL_IDENTITY_IMMUTABLE');
 await refused('Generic Native journal reversal cannot bypass the owning payroll reversal',()=>tx(()=>db.query('select erp._cp3_r4_reverse_journal_internal($1,$2)',[original,'Model wrong owner'])),'OWNING_COMMAND_REQUIRED','42501');
 await refused('Invoice correction with active FG settlement requires lawful payroll reversal first',()=>tx(()=>db.query("update erp.sales_headers set status='REVERSED'where id=$1",[invoice])),'ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_INVOICE_CORRECTION');
 const returned=next();await db.query(`insert into erp.sales_returns(id,return_number,sale_id,customer_id,status)
  values($1,$2,$3,$4,'DRAFT')`,[returned,'RET-'+returned,invoice,customer]);
 await refused('A draft sales return can be reviewed, but cannot post against an active FG settlement',()=>tx(()=>db.query("update erp.sales_returns set status='POSTED'where id=$1",[returned])),'ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_SALES_RETURN');
 assert.equal(await paid(invoice),30000000n);
 await reverse(week);assert.equal(await paid(invoice),0n);
 const inverse=await scalar('select reversal_journal_id from cp7_mandor_shop.settlement_reversals where settlement_id=(select id from cp7_mandor_shop.settlements where payroll_id=$1)',[week]);
 check('Lawful Native payroll reversal alone creates the exact protected inverse and immutable reversal history');
 await db.query("update erp.sales_returns set status='POSTED'where id=$1",[returned]);
 check('After lawful offset reversal, the invoice-return boundary is released for the existing Native return engine');
 await refused('Protected inverse history cannot be reversed again through a generic journal call',()=>tx(()=>db.query('select erp._cp3_r4_reverse_journal_internal($1,$2)',[inverse,'Model reverse inverse'])),'OWNING_COMMAND_REQUIRED','42501');
 const ordinary=await payroll();await approve(ordinary);await pay(ordinary);
 check('Ordinary Native payroll cash journals still pass without any FG context or protected settlement');
 const state=await snapshot();assert.equal(state.work,0);assert.equal(state.context,0);
 const files={};for(const name of ['schema.sql','events.sql','allocation.sql','offset_projection.sql','payment_owner.sql','native_payment_routes.py',
  'NATIVE_PAYMENT_OWNER_REFERENCE.json','NATIVE_PAYMENT_GUARD_REFERENCE.json','payment_guards.sql','payment_guard_model.mjs','PAYMENT_GUARD_MODEL_ORIGIN.json'])files[name]=pin(await readFile(here+name));
 const report={status:'FG_MANDOR_PROTECTED_NATIVE_JOURNAL_AND_INVOICE_BOUNDARY_MODEL_CONTROLS_PASS_NOT_NATIVE',results,source_files:files,
  new_guard_functions_compiled:6,new_Native_table_triggers_compiled:6,Native_column_type_maps:33,
  retained_95_and_payment23_controls_NOT_rerun:true,Native_function_or_payment_owner_sources_changed:false,
  modeled_boundaries:['Native base-table constraints/triggers and generated defaults','Auth, permissions, internal/owner admission and Native review/caller contexts',
   'invoice net/paid provider and credit materialization','Native approval, period, HPP/stock and sales-return engine'],
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
  real_sales_return_engine_executed:false,production_go:false,independent_acceptance:false};
 await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({status:report.status,new_controls:results.length,actual_Native_cases:0})+'\n');
}catch(error){process.stderr.write(JSON.stringify({status:'FG_MANDOR_PAYMENT_GUARD_MODEL_FIRST_FAILURE',completed_new_controls:results,actual_Native_cases:0,error:String(error),SQLSTATE:error.code})+'\n');throw error;}
finally{await db.close();}

