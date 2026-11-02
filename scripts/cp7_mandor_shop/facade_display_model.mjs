// One-backend PG/WASM controls of the actual private allocation SQL.
// No ERP installation, Native payment, Auth HTTP, browser, or two-session credit.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const [runtime, output] = process.argv.slice(2);
assert(runtime && output, 'Explicit existing isolated runtime and new output required');
assert.equal(process.argv[4],'--display-only','Only new exact browser amount projection controls execute');
const { PGlite } = await import(pathToFileURL(runtime).href);
const here = fileURLToPath(new URL('.', import.meta.url));
const pin = raw => ({ bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex') });
const rawReference = await readFile(here+'NATIVE_ALLOCATION_REFERENCE.json');
const reference = JSON.parse(rawReference);
assert.equal(reference.head,'15a2170cea88cd03a4d1bcaa0873a969d495b9fa');
const id = n => '10000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(9001), mandor=id(1), otherMandor=id(2), customer=id(101), otherCustomer=id(102);
const sale=id(201), secondSale=id(202), otherSale=id(203);
const payroll=id(301), nextPayroll=id(302), smallPayroll=id(303), otherPayroll=id(304);
const db = new PGlite();
const results=[];
let request=10000;
const newRequest=()=>id(++request);
async function tx(body) {
  await db.exec('BEGIN');
  try { const value=await body();await db.exec('COMMIT');return value; }
  catch(error) { await db.exec('ROLLBACK');throw error; }
}
async function scalar(sql,args=[]) { return Object.values((await db.query(sql,args)).rows[0])[0]; }
async function card(payrollID=payroll,saleID=sale) {
  const w=await scalar('select cp7_mandor_shop.workspace($1)',[payrollID]);
  return { workspace:w,card:w.cards.find(x=>x.sale_id===saleID) };
}
function payload(c,amount,payrollID=payroll,saleID=sale) {
  assert(c,'Reviewed card required');
  return { contract_version:'cp7.mandor-shop-allocation-command.v1',payroll_id:payrollID,
    sale_id:saleID,review_token:c.review_token,amount:String(amount) };
}
async function command(action,p,req=newRequest()) {
  return tx(()=>scalar('select cp7_mandor_shop.allocation_command($1,$2::jsonb,$3)',[action,JSON.stringify(p),req]));
}
async function refused(label,body,message,code='P0001') {
  let error;
  try { await body(); }catch(caught) { error=caught; }
  assert(error,label+': rejection required');
  assert.equal(error.code,code,label+': SQLSTATE');
  assert(error.message.includes(message),label+': '+error.message);
  results.push({label,result:'REFUSED_AS_REQUIRED',SQLSTATE:error.code,error:message});
}
async function counts() {
  return (await db.query(`select
    (select count(*)::int from cp7_mandor_shop.allocations) allocations,
    (select count(*)::int from cp7_mandor_shop.allocation_events) events,
    (select count(*)::int from erp.payroll_deductions) deductions,
    (select count(*)::int from cp7_mandor_shop.requests) requests`)).rows[0];
}
try {
  await db.exec(`
    CREATE ROLE anon;CREATE ROLE authenticated;CREATE ROLE service_role;
    CREATE SCHEMA erp;CREATE SCHEMA auth;CREATE SCHEMA extensions;
    CREATE SCHEMA cp7_installment;CREATE SCHEMA cp7_credit;CREATE SCHEMA cp7_payroll;
    CREATE FUNCTION auth.uid()returns uuid language sql stable as $$
      select nullif(current_setting('cp7_model.actor',true),'')::uuid $$;
    CREATE FUNCTION auth.jwt()returns jsonb language sql stable as $$
      select '{"role":"authenticated"}'::jsonb $$;
    -- Exact SHA-256 implemented by PostgreSQL itself. This wrapper models the
    -- extension namespace, not an alternative production hashing algorithm.
    CREATE FUNCTION extensions.digest(bytea,text)returns bytea language sql immutable as $$
      select case when $2='sha256'then pg_catalog.sha256($1)else null end $$;
    CREATE FUNCTION erp.get_my_access_v1()returns jsonb language sql stable as $$
      select jsonb_build_object('allowed',true,'actor',auth.uid(),'permissions',
        jsonb_build_array('finance.payroll.view','finance.ar.view','finance.payroll.approve')) $$;
    CREATE FUNCTION erp.has_permission(text)returns boolean language sql stable as $$
      select coalesce(current_setting('cp7_model.permissions',true),'allow')='allow' $$;
    CREATE TABLE erp.app_permissions(id uuid primary key);
    CREATE TABLE erp.app_role_permissions(id uuid primary key);
    CREATE TABLE erp.app_roles(id uuid primary key);
    CREATE TABLE erp.app_users(id uuid primary key);
    CREATE TABLE erp.contractors(id uuid primary key,is_active boolean not null,attendance_required boolean not null);
    CREATE TABLE erp.customers(id uuid primary key,is_active boolean not null);
    CREATE TABLE erp.sales_headers(id uuid primary key,customer_id uuid not null,status varchar(30)not null,
      sale_number varchar(60)not null,sale_date timestamptz not null);
    CREATE TABLE erp.model_invoice_amounts(sale_id uuid primary key,net numeric(20,2)not null,paid numeric(20,2)not null);
    CREATE FUNCTION erp.sale_net_total(uuid)returns numeric language sql stable as $$
      select net from erp.model_invoice_amounts where sale_id=$1 $$;
    CREATE FUNCTION cp7_credit.current_effective_paid(uuid)returns numeric language sql stable as $$
      select paid from erp.model_invoice_amounts where sale_id=$1 $$;
    CREATE TABLE erp.payroll_settlements(
      id uuid primary key,payroll_number varchar(60)not null,contractor_id uuid not null,
      period_start date not null,period_end date not null,status varchar(20)not null,
      labor_total numeric(20,2)not null default 0,attendance_total numeric(20,2)not null default 0,
      reimburse_total numeric(20,2)not null default 0,deduction_total numeric(20,2)not null default 0,
      manual_adjustment numeric(20,2)not null default 0,
      net_payable numeric(20,2)generated always as(labor_total+attendance_total+reimburse_total-deduction_total+manual_adjustment)stored,
      settled_at timestamptz,notes text,created_at timestamptz not null default statement_timestamp(),
      updated_at timestamptz not null default statement_timestamp(),payment_cash_account_id uuid,
      payment_date date not null default '2026-11-02',row_version bigint not null default 1);
    CREATE TABLE erp.payroll_work_items(id uuid primary key,payroll_id uuid not null references erp.payroll_settlements(id),amount numeric(20,2)not null);
    CREATE TABLE erp.payroll_attendance_items(id uuid primary key,payroll_id uuid not null references erp.payroll_settlements(id),amount numeric(20,2)not null);
    CREATE TABLE erp.payroll_reimbursements(id uuid primary key,payroll_id uuid not null references erp.payroll_settlements(id),amount numeric(20,2)not null);
    CREATE TABLE erp.payroll_deductions(id uuid primary key,payroll_id uuid not null references erp.payroll_settlements(id),
      deduction_type varchar(30)not null,contractor_issue_item_id uuid,bs_resolution_id uuid,
      amount numeric(20,2)not null,notes text,opening_cash_advance_balance_id uuid);
    CREATE TABLE erp.journal_entries(id uuid primary key,source_type varchar(100),source_id uuid,status varchar(30),
      economic_date date,transaction_date date,reversal_of_id uuid);
    CREATE TABLE cp7_payroll.settlement_context(backend_pid int,transaction_id bigint,actor uuid,payroll_id uuid,action text,
      primary key(backend_pid,transaction_id));
    CREATE FUNCTION erp.require_internal()returns void language plpgsql as $$
    begin if not exists(select 1 from cp7_payroll.settlement_context
      where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and action='PREPARE')
      then raise exception 'MODEL_EXACT_NATIVE_PREPARE_CONTEXT_REQUIRED';end if;end $$;
  `);
  const schema=await readFile(here+'schema.sql'),events=await readFile(here+'events.sql');
  const allocation=await readFile(here+'allocation.sql');
  await db.exec(schema.toString());await db.exec(events.toString());
  const nativeSources={};
  for(const signature of ['erp.recalculate_payroll(uuid)','cp7_installment.meaning(uuid)']) {
    const definition=reference.functions[signature][0];nativeSources[signature]=pin(Buffer.from(definition));
    await db.exec(definition);
  }
  await db.exec(allocation.toString());
  await db.query("select set_config('cp7_model.actor',$1,false)",[actor]);
  await db.query('insert into erp.contractors values($1,true,false),($2,true,false)',[mandor,otherMandor]);
  await db.query('insert into erp.customers values($1,true),($2,true)',[customer,otherCustomer]);
  for(const [saleID,cust,n]of[[sale,customer,'SALE-A'],[secondSale,customer,'SALE-B'],[otherSale,otherCustomer,'SALE-C']]) {
    await db.query("insert into erp.sales_headers values($1,$2,'POSTED',$3,'2026-11-01T00:00:00Z')",[saleID,cust,n]);
    await db.query('insert into erp.model_invoice_amounts values($1,500000,0)',[saleID]);
  }
  for(const [payrollID,cid,start,end,amount,n]of[[payroll,mandor,'2026-11-02','2026-11-08',2000000,'PAY-W1'],
    [nextPayroll,mandor,'2026-11-09','2026-11-15',1000000,'PAY-W2'],
    [smallPayroll,mandor,'2026-11-16','2026-11-22',100000,'PAY-W3'],
    [otherPayroll,otherMandor,'2026-11-02','2026-11-08',1000000,'PAY-OTHER']]) {
    await db.query("insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,labor_total)values($1,$2,$3,$4,$5,'DRAFT',$6)",[payrollID,n,cid,start,end,amount]);
    await db.query('insert into erp.payroll_work_items values($1,$2,$3)',[id(Number(payrollID.slice(-3))+5000),payrollID,amount]);
  }
  await db.query('insert into cp7_mandor_shop.contractor_accounts(contractor_id,customer_id,created_by)values($1,$2,$5),($3,$4,$5)',[mandor,customer,otherMandor,otherCustomer,actor]);
  await tx(async()=>{
    await db.query("insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),$1,$2,'POST_SALE',$3)",[actor,newRequest(),'a'.repeat(64)]);
    for(const [saleID,cid,cust]of[[sale,mandor,customer],[secondSale,mandor,customer],[otherSale,otherMandor,otherCustomer]])
      await db.query("insert into cp7_mandor_shop.sales(sale_id,contractor_id,customer_id,contractor_name_at_post,posted_by)values($1,$2,$3,'model master',$4)",[saleID,cid,cust,actor]);
    await db.exec('delete from cp7_mandor_shop.command_context');
  });

  // Extend only the modeled master/context tables with the exact actual Native
  // column types required by the unchanged buyer owners. No old case is rerun.
  const buyerReference=JSON.parse(await readFile(here+'NATIVE_BUYER_REFERENCE.json'));
  await db.exec('create schema cp7_sales;create role cp7_sales_read nologin;grant usage on schema erp,auth,cp7_sales to cp7_sales_read');
  for(const [table,cols]of Object.entries(buyerReference.columns)){
    const seen=await scalar("select coalesce(jsonb_agg(attname),'[]')from pg_attribute where attrelid=to_regclass($1)and attnum>0 and not attisdropped",[table]);
    if(!seen.length){await db.exec('create table '+table+'('+Object.values(cols).sort((a,b)=>a[1]-b[1]).map(c=>'"'+c[0]+'" '+c[2]).join(',')+',primary key(backend_pid,transaction_id))');}
    else for(const c of Object.values(cols))if(!seen.includes(c[0]))await db.exec('alter table '+table+' add column "'+c[0]+'" '+c[2]);
    const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
    assert.deepEqual(actual,Object.fromEntries(Object.values(cols).map(c=>[c[0],c[2]])));
  }
  await db.exec(buyerReference.functions['cp7_sales.command_access(text)'][0]);
  await db.exec('alter function cp7_sales.command_access(text)owner to cp7_sales_read');
  await db.exec((await readFile(here+'buyers.sql')).toString());
  await db.exec((await readFile(here+'facade.sql')).toString());
  await db.query("update erp.contractors set contractor_code=case when id=$1 then 'M1'else'M2'end,contractor_name='Epi',contractor_type='MANDOR'",[mandor]);
  await db.query("update erp.customers set customer_code=case when id=$1 then 'MD-1'else'MD-2'end,customer_name='Epi'",[customer]);

  await db.exec((await readFile(here+'facade_display.sql')).toString());
  // The original private commands create the fixture. No previous model cases
  // or payroll payment tests are replayed by these new display-only controls.
  const before=await scalar('select cp7_mandor_shop.workspace($1)',[nextPayroll]);
  const reviewed=before.cards.find(c=>c.sale_id===sale);
  await command('RESERVE',payload(reviewed,'300000.19',nextPayroll));
  const shown=await scalar('select public.erp_cp7_get_mandor_shop_payroll_v1($1)',[nextPayroll]);
  const a=shown.cards.find(c=>c.sale_id===sale).allocations[0].allocation;
  assert.equal(a.amount,'300000.19');assert.equal(typeof a.amount,'string');
  assert.equal(shown.cards.find(c=>c.sale_id===sale).allocations[0].payroll_number,'PAY-W2');
  results.push({label:'Actual public read emits exact decimal strings for nested allocation amounts and retains the chosen payroll/week',result:'PASS'});
  const raw=await scalar('select cp7_mandor_shop.workspace($1)',[nextPayroll]);
  for(const c of raw.cards)for(const row of c.allocations)row.allocation.amount=String(row.allocation.amount);
  assert.deepEqual(shown,raw);
  results.push({label:'The complete workspace, card order, allocation order, source review tokens and every other field remain unchanged',result:'PASS'});
  // Cross the JavaScript safe-integer boundary with exact PostgreSQL numerics.
  const huge='9007199254740993.99';
  await db.query('update erp.model_invoice_amounts set net=$2 where sale_id=$1',[secondSale,huge]);
  await db.query('update erp.payroll_work_items set amount=$2 where payroll_id=$1',[payroll,huge]);
  await db.query('update erp.payroll_settlements set labor_total=$2 where id=$1',[payroll,huge]);
  const hugeCard=(await card(payroll,secondSale)).card;
  await command('RESERVE',payload(hugeCard,huge,payroll,secondSale));
  const large=await scalar('select public.erp_cp7_get_mandor_shop_payroll_v1($1)',[payroll]);
  assert.equal(large.cards.find(c=>c.sale_id===secondSale).allocations[0].allocation.amount,huge);
  assert.equal(large.net_payable_preview,'0.00');
  const exact=await scalar(`with original as materialized(select cp7_mandor_shop.workspace($1) d),
   displayed as materialized(select public.erp_cp7_get_mandor_shop_payroll_v1($1) d)
   select ((select c#>>'{allocations,0,allocation,amount}'from original,jsonb_array_elements(d->'cards')c where c->>'sale_id'=$2)::numeric
    =(select c#>>'{allocations,0,allocation,amount}'from displayed,jsonb_array_elements(d->'cards')c where c->>'sale_id'=$2)::numeric)`,[payroll,secondSale]);
  assert.equal(exact,true);assert.equal(await scalar('select count(*)::int from erp.journal_entries'),0);
  results.push({label:'An allocation beyond JavaScript safe integer range keeps every cent through the public JSON response; display performs no journal posting',result:'PASS'});
  const functionRow=(await db.query("select pg_get_userbyid(proowner)owner,prosecdef,proconfig from pg_proc where oid='public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)'::regprocedure")).rows[0];
  assert.deepEqual(functionRow,{owner:'cp7_mandor_shop_api',prosecdef:true,proconfig:['search_path=""']});
  for(const role of ['anon','authenticated','service_role'])assert.equal(await scalar("select has_function_privilege($1,'public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)','EXECUTE')",[role]),role==='authenticated');
  results.push({label:'Read replacement preserves the exact narrow owner and browser execution privileges',result:'PASS'});
  const files={};for(const n of ['schema.sql','events.sql','allocation.sql','buyers.sql','facade.sql','facade_display.sql','NATIVE_BUYER_REFERENCE.json','NATIVE_ALLOCATION_REFERENCE.json','facade_display_model.mjs','FACADE_DISPLAY_MODEL_ORIGIN.json'])files[n]=pin(await readFile(here+n));
  const report={status:'FG_MANDOR_EXACT_PUBLIC_DISPLAY_CENTS_MODEL_CONTROLS_PASS_NOT_NATIVE',results,source_files:files,
    new_public_functions:0,new_roles:0,new_grants:0,public_read_projection_only:true,prior_140_controls_NOT_rerun:true,
    actual_native_function_or_private_owner_source_changes:0,Native_runtime_or_public_facade_activated:false,
    modeled_boundaries:['Unchanged reduced Native table/Auth/permission/invoice/internal-context setup inherited from the facade model',
      'No complete ERP installation, sales, payroll payment, stock/HPP, Auth HTTP, browser or two PostgreSQL sessions'],
    actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
    production_go:false,independent_acceptance:false};
  await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,new_controls:results.length,actual_Native_cases:0}));
}catch(error){process.stderr.write(JSON.stringify({status:'FG_MANDOR_DISPLAY_MODEL_FIRST_FAILURE',completed_new_controls:results,actual_Native_cases:0,error:String(error),SQLSTATE:error.code})+'\n');throw error;}
finally{await db.close();}
