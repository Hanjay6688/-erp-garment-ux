// One-backend PG/WASM controls of the actual private allocation SQL.
// No ERP installation, Native payment, Auth HTTP, browser, or two-session credit.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const [runtime, output] = process.argv.slice(2);
assert(runtime && output, 'Explicit existing isolated runtime and new output required');
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
  const first=await card(),firstRequest=newRequest(),firstPayload=payload(first.card,300000);
  const made=await command('RESERVE',firstPayload,firstRequest);
  assert.equal(Number(made.net_payable),1700000);assert.equal(made.invoice_settled_by_this_command,false);
  assert.equal(await scalar('select paid::text from erp.model_invoice_amounts where sale_id=$1',[sale]),'0.00');
  results.push({label:'Reserve selected week: 2,000,000 wage less 300,000 purchase = 1,700,000 preview, invoice still unpaid',result:'PASS'});
  const beforeReplay=await counts();
  assert.deepEqual(await command('RESERVE',firstPayload,firstRequest),made);
  assert.deepEqual(await counts(),beforeReplay);
  results.push({label:'Exact repeated request returns its immutable outcome without a second deduction',result:'PASS'});
  await refused('Same request cannot change amount',()=>command('RESERVE',{...firstPayload,amount:'1'},firstRequest),'REQUEST_CHANGED');
  await refused('Stale second-tab review cannot reserve again',()=>command('RESERVE',payload(first.card,100000)),'REVIEW_CHANGED');
  assert.deepEqual(await counts(),beforeReplay);
  let next=await card(nextPayroll);
  await refused('Cross-week reservation cannot exceed unallocated invoice remainder',()=>command('RESERVE',payload(next.card,250000,nextPayroll)),'INVOICE_CAPACITY_CHANGED');
  const second=await command('RESERVE',payload(next.card,200000,nextPayroll));
  assert.equal(Number(second.net_payable),800000);
  assert.equal(Number((await card()).card.available_to_reserve),0);
  results.push({label:'Remaining 200,000 may be reserved manually on a different payroll week',result:'PASS'});
  const small=await card(smallPayroll,secondSale);
  await refused('Payroll capacity limits the purchase deduction',()=>command('RESERVE',payload(small.card,100001,smallPayroll,secondSale)),'PAYROLL_CAPACITY_CHANGED');
  await refused('Fractional cents are rejected before Native numeric rounding',()=>command('RESERVE',payload(small.card,'1.005',smallPayroll,secondSale)),'EXACT_POSITIVE_CENTS_REQUIRED');
  await refused('Wrong mandor cannot use another mandor invoice',()=>command('RESERVE',payload(first.card,1,otherPayroll)),'WRONG_MANDOR');
  const current=await card();
  const releasePayload={contract_version:firstPayload.contract_version,payroll_id:payroll,sale_id:sale,
    review_token:current.card.review_token,allocation_id:made.allocation_id};
  const released=await command('RELEASE',releasePayload);
  assert.equal(Number(released.net_payable),2000000);
  assert.equal(Number((await card()).card.available_to_reserve),300000);
  assert.equal(await scalar('select state from cp7_mandor_shop.allocation_states where allocation_id=$1',[made.allocation_id]),'RELEASED');
  assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.allocations where id=$1',[made.allocation_id]),1);
  results.push({label:'Release removes the draft deduction while preserving immutable allocation and event history',result:'PASS'});
  const beforeBalanceChange=await card();
  await db.query('update erp.model_invoice_amounts set paid=100000 where sale_id=$1',[sale]);
  const baseline=await counts();
  await refused('An external invoice balance change invalidates an old review',()=>command('RESERVE',payload(beforeBalanceChange.card,1)),'REVIEW_CHANGED');
  assert.deepEqual(await counts(),baseline);
  await db.query("update erp.payroll_settlements set status='APPROVED'where id=$1",[nextPayroll]);
  next=await card(nextPayroll);
  await refused('An approved payroll cannot have its purchase deduction silently edited',()=>command('RELEASE',{
    contract_version:firstPayload.contract_version,payroll_id:nextPayroll,sale_id:sale,
    review_token:next.card.review_token,allocation_id:second.allocation_id}),'EDITABLE_PAYROLL_REQUIRED');
  await db.query("select set_config('cp7_model.permissions','deny',false)");
  await refused('Current permissions are required even for an already committed request replay',()=>command('RESERVE',firstPayload,firstRequest),'ACCESS_DENIED','42501');
  await db.query("select set_config('cp7_model.permissions','allow',false)");
  await db.query("update erp.payroll_settlements set status='CALCULATED'where id=$1",[nextPayroll]);
  await db.query("update erp.sales_headers set status='REVERSED'where id=$1",[sale]);
  next=await card(nextPayroll);assert(next.card,'A no-longer-active invoice must retain its releasable current-payroll card');
  await command('RELEASE',{contract_version:firstPayload.contract_version,payroll_id:nextPayroll,sale_id:sale,
    review_token:next.card.review_token,allocation_id:second.allocation_id});
  results.push({label:'A changed/reversed invoice keeps its outstanding reservation card available for lawful release',result:'PASS'});
  assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.command_context'),0);
  assert.equal(await scalar('select count(*)::int from cp7_payroll.settlement_context'),0);
  assert.equal(await scalar('select count(*)::int from erp.journal_entries'),0);
  assert.equal(await scalar('select count(*)::int from erp.payroll_deductions'),0);
  results.push({label:'No journals or fake invoice payments; both private command contexts are empty',result:'PASS'});
  const report={status:'FG_MANDOR_PRIVATE_ALLOCATION_MODEL_CONTROLS_PASS_NOT_NATIVE',
    source_files:{'schema.sql':pin(schema),'events.sql':pin(events),'allocation.sql':pin(allocation),
      'NATIVE_ALLOCATION_REFERENCE.json':pin(rawReference)},
    retained_storage_15_controls_NOT_rerun:true,actual_unchanged_native_definitions_reused:nativeSources,
    modeled_boundaries:['auth.uid/auth.jwt','get_my_access_v1/has_permission','Native invoice net and effective paid',
      'Native require_internal with exact PREPARE context','Native tables reduced to required correctly typed columns'],
    results,final_counts:await counts(),actual_Native_cases:0,actual_Auth_HTTP_cases:0,
    actual_two_session_races:0,actual_browser_cases:0,ERP_installed:false,production_go:false,independent_acceptance:false};
  await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({status:report.status,controls:results.length,actual_Native_cases:0}));
}finally{await db.close();}
