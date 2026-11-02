// One-backend PG/WASM controls of the actual private allocation SQL.
// No ERP installation, Native payment, Auth HTTP, browser, or two-session credit.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const [runtime, output] = process.argv.slice(2);
assert(runtime && output, 'Explicit existing isolated runtime and new output required');
assert.equal(process.argv[4],'--facade-only','Only the new browser facade controls execute');
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
  const publicNames=['public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer)',
    'public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid)',
    'public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)',
    'public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)'];
  const entry=['cp7_mandor_shop.buyer_options(text,text,uuid,integer)',
    'cp7_mandor_shop.buyer_command(jsonb,uuid)','cp7_mandor_shop.workspace(uuid,uuid)',
    'cp7_mandor_shop.allocation_command(text,jsonb,uuid)'];
  for(const signature of publicNames){
    const row=(await db.query("select pg_get_userbyid(proowner)owner,prosecdef,proconfig from pg_proc where oid=$1::regprocedure",[signature])).rows[0];
    assert.deepEqual(row,{owner:'cp7_mandor_shop_api',prosecdef:true,proconfig:['search_path=""']});
    for(const role of ['anon','authenticated','service_role'])assert.equal(await scalar("select has_function_privilege($1,$2,'EXECUTE')",[role,signature]),role==='authenticated');
  }
  const role=(await db.query("select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolconnlimit from pg_roles where rolname='cp7_mandor_shop_api'")).rows[0];
  assert.deepEqual(role,{rolcanlogin:false,rolinherit:false,rolsuper:false,rolcreatedb:false,rolcreaterole:false,rolreplication:false,rolbypassrls:false,rolconnlimit:0});
  results.push({label:'Four exact public definer functions compile under one NOLOGIN nonprivileged role; only authenticated can execute',result:'PASS'});
  const privateFns=(await db.query("select p.oid::regprocedure::text name from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_mandor_shop'")).rows.map(r=>r.name);
  for(const signature of privateFns){
    assert.equal(await scalar("select has_function_privilege('cp7_mandor_shop_api',$1,'EXECUTE')",[signature]),entry.includes(signature));
    for(const browser of ['anon','authenticated','service_role'])assert.equal(await scalar("select has_function_privilege($1,$2,'EXECUTE')",[browser,signature]),false);
  }
  for(const role of ['cp7_mandor_shop_api','anon','authenticated','service_role']){
    for(const row of (await db.query("select oid::regclass::text name from pg_class where relnamespace='cp7_mandor_shop'::regnamespace and relkind='r'")).rows)
      assert.equal(await scalar("select has_table_privilege($1,$2,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",[role,row.name]),false);
    assert.equal(await scalar("select has_schema_privilege($1,'cp7_mandor_shop','CREATE')",[role]),false);
  }
  assert.equal(await scalar("select has_schema_privilege('cp7_mandor_shop_api','public','CREATE')"),false);
  results.push({label:'Facade role has exactly four private entrypoints and no private table privileges; browsers have no direct private access',result:'PASS'});
  const asBrowser=body=>tx(async()=>{await db.exec('set local role authenticated');return body();});
  const read=payrollID=>asBrowser(()=>scalar('select public.erp_cp7_get_mandor_shop_payroll_v1($1)',[payrollID]));
  const options=await asBrowser(()=>scalar("select public.erp_cp7_get_mandor_shop_buyers_v1('CREATE','Epi')"));
  assert.equal(options.rows.length,2);assert.notEqual(options.rows[0].contractor_id,options.rows[1].contractor_id);
  const chosen=options.rows.find(x=>x.contractor_id===mandor),requestBuyer=newRequest();
  const buyerPayload={contract_version:'cp7.mandor-shop-buyer-command.v1',sales_action:'CREATE',contractor_id:mandor,review_token:chosen.review_token};
  const buyer=await asBrowser(()=>scalar('select public.erp_cp7_prepare_mandor_shop_buyer_v1($1::jsonb,$2)',[JSON.stringify(buyerPayload),requestBuyer]));
  assert.equal(buyer.contractor_id,mandor);assert.equal(buyer.customer_id,customer);
  assert.deepEqual(await asBrowser(()=>scalar('select public.erp_cp7_prepare_mandor_shop_buyer_v1($1::jsonb,$2)',[JSON.stringify(buyerPayload),requestBuyer])),buyer);
  results.push({label:'Public buyer picker keeps same-name mandors distinct and preparing/replaying the chosen buyer retains the same explicit customer identity',result:'PASS'});
  const first=await read(nextPayroll);assert.equal(first.period_start,'2026-11-09');assert(first.cards.some(c=>c.sale_id===sale));assert(!first.cards.some(c=>c.sale_id===otherSale));
  const card=first.cards.find(c=>c.sale_id===sale),rq=newRequest();
  const doc={contract_version:'cp7.mandor-shop-allocation-command.v1',payroll_id:nextPayroll,sale_id:sale,review_token:card.review_token,amount:'300000.00'};
  const save=(action,document,requestID=newRequest())=>asBrowser(()=>scalar('select public.erp_cp7_save_mandor_shop_allocation_v1($1,$2::jsonb,$3)',[action,JSON.stringify(document),requestID]));
  const outcome=await save('RESERVE',doc,rq);assert.equal(outcome.payroll_id,nextPayroll);assert.equal(outcome.invoice_settled_by_this_command,false);assert.equal(outcome.net_payable,'700000.00');
  const countsBefore=await counts();assert.deepEqual(await save('RESERVE',doc,rq),outcome);assert.deepEqual(await counts(),countsBefore);
  assert.equal(await scalar('select count(*)::int from erp.journal_entries'),0);assert.equal(await scalar('select paid::text from erp.model_invoice_amounts where sale_id=$1',[sale]),'0.00');
  results.push({label:'Public command installs one chosen-next-week draft allocation and exact request replay adds no duplicate deduction, settlement or journal',result:'PASS'});
  const reread=await read(nextPayroll),shown=reread.cards.find(c=>c.sale_id===sale);assert.equal(shown.allocations[0].payroll_number,'PAY-W2');assert.equal(shown.allocations[0].period_start,'2026-11-09');assert.equal(shown.available_to_reserve,'200000.00');
  results.push({label:'Public card exposes the actual allocated payroll/week, outstanding amount and remaining unallocated amount after authoritative reread',result:'PASS'});
  await refused('Public replay refuses changed request payload before any second allocation',()=>save('RESERVE',{...doc,amount:'1.00'},rq),'CP7_MANDOR_SHOP_REQUEST_CHANGED');assert.deepEqual(await counts(),countsBefore);
  await db.exec("select set_config('cp7_model.permissions','deny',false)");
  await refused('A revoked permission blocks a public workspace read',()=>read(nextPayroll),'CP7_MANDOR_SHOP_ACCESS_DENIED','42501');
  await refused('A revoked permission blocks replay of a previously committed public allocation',()=>save('RESERVE',doc,rq),'CP7_MANDOR_SHOP_ACCESS_DENIED','42501');
  await db.exec("select set_config('cp7_model.permissions','allow',false)");
  const current=await read(nextPayroll),currentCard=current.cards.find(c=>c.sale_id===sale);
  const release=await save('RELEASE',{contract_version:doc.contract_version,payroll_id:nextPayroll,sale_id:sale,review_token:currentCard.review_token,allocation_id:outcome.allocation_id});
  assert.equal(release.net_payable,'1000000.00');assert.equal((await counts()).deductions,0);
  assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.command_context'),0);
  assert.equal(await scalar('select count(*)::int from cp7_payroll.settlement_context'),0);
  results.push({label:'Public card release removes only the selected draft deduction, preserves release history and restores payroll capacity without settling the invoice',result:'PASS'});
  const files={};for(const n of ['schema.sql','events.sql','allocation.sql','buyers.sql','facade.sql','NATIVE_BUYER_REFERENCE.json','NATIVE_ALLOCATION_REFERENCE.json','facade_model.mjs','FACADE_MODEL_ORIGIN.json'])files[n]=pin(await readFile(here+n));
  const report={status:'FG_MANDOR_NARROW_PUBLIC_FACADE_MODEL_CONTROLS_PASS_NOT_NATIVE',results,source_files:files,
    public_functions_compiled:4,private_entrypoint_grants:4,facade_role:'cp7_mandor_shop_api',Native_master_context_column_type_maps:3,
    unchanged_actual_Native_functions:['erp.recalculate_payroll(uuid)','cp7_installment.meaning(uuid)','cp7_sales.command_access(text)'],
    retained_131_controls_NOT_rerun:true,actual_native_function_or_private_owner_source_changes:0,
    modeled_boundaries:['Reduced Native tables and constraints; generated payroll net uses the prior documented actual formula',
      'Auth/JWT and permissions providers, customer defaults/audit and private Native internal context admission',
      'Invoice paid/net projection; no full Native sales, payroll payment, stock, HPP, Auth HTTP, browser or two backends'],
    actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
    Native_runtime_or_public_facade_activated:false,production_go:false,independent_acceptance:false};
  await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,new_controls:results.length,actual_Native_cases:0}));
}catch(error){process.stderr.write(JSON.stringify({status:'FG_MANDOR_FACADE_MODEL_FIRST_FAILURE',completed_new_controls:results,actual_Native_cases:0,error:String(error),SQLSTATE:error.code})+'\n');throw error;}
finally{await db.close();}
