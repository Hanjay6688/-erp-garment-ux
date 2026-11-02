// One-backend identity-hook model. Native invoice/stock/HPP/ledger engines and
// Auth are not run. Previously accepted storage/allocation/buyer tests stay reused.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const [runtime,output]=process.argv.slice(2);
assert(runtime&&output,'Existing isolated runtime and new output required');
const {PGlite}=await import(pathToFileURL(runtime).href);
const here=fileURLToPath(new URL('.',import.meta.url)),db=new PGlite(),results=[];
const pin=raw=>({bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
const reference=JSON.parse(await readFile(here+'NATIVE_SALES_IDENTITY_REFERENCE.json'));
assert.equal(reference.head,'6e61506c10a18541c104b981bd438e78b175b5d1');
const id=n=>'30000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(9001),mandor=id(1),other=id(2),inactive=id(3),customer=id(101),
 otherCustomer=id(102),inactiveCustomer=id(103),store=id(104);
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
async function tx(body){
 await db.exec('BEGIN');
 try{const value=await body();await db.exec('COMMIT');return value;}
 catch(error){await db.exec('ROLLBACK');throw error;}
}
async function nativeScope(action,body){
 return tx(async()=>{
  await db.query('insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),$1,null,$2)',[actor,action]);
  const value=await body();
  await db.exec('delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()');
  return value;
 });
}
async function refused(label,body,message,code='P0001'){
 let error;try{await body();}catch(caught){error=caught;}
 assert(error,label+': rejection required');assert.equal(error.code,code,label+': SQLSTATE');
 assert(error.message.includes(message),label+': '+error.message);
 results.push({label,result:'REFUSED_AS_REQUIRED',SQLSTATE:error.code,error:message});
}
async function create(sale,cust=customer,status='DRAFT'){
 return scalar(`insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status,notes)
  values($1,$2,$3,'2026-11-02T02:00:00Z',$4,'Original Native header')returning to_jsonb(sales_headers)`,
 [sale,'SALE-'+sale.slice(-5),cust,status]);
}
const draft=sale=>scalar('select to_jsonb(d)from cp7_mandor_shop.draft_buyers d where sale_id=$1',[sale]);
const posted=sale=>scalar('select to_jsonb(s)from cp7_mandor_shop.sales s where sale_id=$1',[sale]);
async function counts(){
 return (await db.query(`select
  (select count(*)::int from erp.sales_headers)headers,
  (select count(*)::int from cp7_mandor_shop.draft_buyers)drafts,
  (select count(*)::int from cp7_mandor_shop.sales)posted,
  (select count(*)::int from cp7_mandor_shop.command_context)own_contexts,
  (select count(*)::int from cp7_sales.command_context)native_contexts,
  (select count(*)::int from erp.journal_entries)journals`)).rows[0];
}
try{
 await db.exec(`
  create role anon;create role authenticated;create role service_role;
  create schema erp;create schema auth;create schema extensions;create schema cp7_sales;
  create function auth.uid()returns uuid language sql stable as $$
   select nullif(current_setting('cp7_model.actor',true),'')::uuid $$;
  create function auth.jwt()returns jsonb language sql stable as $$
   select jsonb_build_object('role',coalesce(nullif(current_setting('cp7_model.jwt_role',true),''),'authenticated')) $$;
  create function extensions.digest(bytea,text)returns bytea language sql immutable as $$
   select case when $2='sha256'then pg_catalog.sha256($1)else null end $$;
  create table erp.app_permissions(id uuid primary key);
  create table erp.app_role_permissions(id uuid primary key);
  create table erp.app_roles(id uuid primary key);
  create table erp.app_users(id uuid primary key);
  create table cp7_sales.command_context(backend_pid integer not null,transaction_id bigint not null,
   actor uuid not null,sale_id uuid,action text not null,primary key(backend_pid,transaction_id));
  -- Explicit Native-scope model, not a replacement in an ERP installation.
  create function erp.require_internal()returns void language plpgsql as $$
  begin
   if not exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
    and c.transaction_id=txid_current_if_assigned()and c.actor=auth.uid()
    and c.action in('CREATE','EDIT','POST','CANCEL','PAYMENT','SALE_REVERSE'))then
    raise exception using errcode='42501',message='MODEL_NATIVE_SALES_SCOPE_REQUIRED';end if;
  end $$;
  create table erp.contractors(id uuid primary key default gen_random_uuid(),
   contractor_code varchar(30)not null unique,contractor_name varchar(120)not null,
   contractor_type varchar(30)not null default 'MANDOR',attendance_required boolean not null default true,
   is_active boolean not null default true,notes text,created_at timestamptz not null default statement_timestamp(),
   updated_at timestamptz not null default statement_timestamp());
  create table erp.customers(id uuid primary key default gen_random_uuid(),
   customer_code varchar(30)not null unique,customer_name varchar(150)not null,phone varchar(50),
   address text,is_active boolean not null default true,created_at timestamptz not null default statement_timestamp(),
   updated_at timestamptz not null default statement_timestamp());
  create table erp.sales_headers(id uuid primary key default gen_random_uuid(),
   sale_number varchar(60)not null unique,customer_id uuid not null references erp.customers(id),
   sale_date timestamptz not null,due_date date,status varchar(20)not null default 'DRAFT',
   payment_terms varchar(100),notes text,created_by uuid,created_at timestamptz not null default statement_timestamp(),
   updated_at timestamptz not null default statement_timestamp(),source_location_id uuid,row_version bigint not null default 1);
  create table erp.payroll_settlements(id uuid primary key,contractor_id uuid,status varchar(20));
  create table erp.payroll_deductions(id uuid primary key);
  create table erp.journal_entries(id uuid primary key);
 `);
 for(const [table,declaration]of Object.entries(reference.columns)){
  const actual=await scalar(`select jsonb_object_agg(a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod))
   from pg_attribute a where a.attrelid=$1::regclass and a.attnum>0 and not a.attisdropped`,[table]);
  assert.deepEqual(actual,Object.fromEntries(Object.values(declaration).map(row=>[row[0],row[2]])));
 }
 const schema=await readFile(here+'schema.sql'),events=await readFile(here+'events.sql'),hook=await readFile(here+'sale_identity.sql');
 await db.exec(schema.toString());await db.exec(events.toString());
 for(const [cid,code,name,active]of[[mandor,'M1','Epi at draft',true],[other,'M2','Other mandor',true],[inactive,'M3','Inactive mandor',false]])
  await db.query('insert into erp.contractors(id,contractor_code,contractor_name,is_active)values($1,$2,$3,$4)',[cid,code,name,active]);
 for(const [cid,code,name]of[[customer,'MD-1','Mandor one'],[otherCustomer,'MD-2','Mandor two'],[inactiveCustomer,'MD-3','Inactive master'],[store,'TOKO','Ordinary store']])
  await db.query('insert into erp.customers(id,customer_code,customer_name)values($1,$2,$3)',[cid,code,name]);
 for(const [cid,cust]of[[mandor,customer],[other,otherCustomer],[inactive,inactiveCustomer]])
  await db.query('insert into cp7_mandor_shop.contractor_accounts(contractor_id,customer_id,created_by)values($1,$2,$3)',[cid,cust,actor]);
 await db.exec(hook.toString());
 results.push({label:'Actual contractor/customer/Native-header column types and new trigger compile unchanged financial engines',result:'PASS'});
 const toko=id(201);
 await create(toko,store);
 await db.query("update erp.sales_headers set status='POSTED'where id=$1",[toko]);
 assert.equal((await counts()).drafts,0);assert.equal((await counts()).posted,0);
 results.push({label:'Ordinary store headers acquire no mandor facts or new actor requirement',result:'PASS'});
 await db.query("select set_config('cp7_model.actor',$1,false)",[actor]);
 const editable=id(202),made=await nativeScope('CREATE',()=>create(editable));
 let d=await draft(editable);
 assert.equal(d.contractor_id,mandor);assert.equal(d.customer_id,customer);assert.equal(d.selected_by,actor);
 assert.equal(made.notes,'Original Native header');assert.equal(made.row_version,1);assert.equal(made.status,'DRAFT');
 assert.equal((await counts()).posted,0);assert.equal((await counts()).own_contexts,0);
 results.push({label:'Native draft records explicit mandor identity without changing Native header values',result:'PASS'});
 await nativeScope('EDIT',()=>db.query('update erp.sales_headers set customer_id=$1,row_version=row_version+1 where id=$2',[otherCustomer,editable]));
 d=await draft(editable);assert.equal(d.contractor_id,other);assert.equal(d.customer_id,otherCustomer);
 results.push({label:'Editing a draft may select another explicit mandor while posted identity is still absent',result:'PASS'});
 await nativeScope('EDIT',()=>db.query('update erp.sales_headers set customer_id=$1 where id=$2',[store,editable]));
 assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.draft_buyers where sale_id=$1',[editable]),0);
 results.push({label:'Switching a Native draft to a store clears only the editable mandor selection',result:'PASS'});
 const cancelled=id(203);await nativeScope('CREATE',()=>create(cancelled));
 await nativeScope('CANCEL',()=>db.query("update erp.sales_headers set status='CANCELLED'where id=$1",[cancelled]));
 assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.draft_buyers where sale_id=$1',[cancelled]),0);
 results.push({label:'Cancelling an unpaid Native draft clears its editable selection',result:'PASS'});
 const invoice=id(204);await nativeScope('CREATE',()=>create(invoice));
 await db.query("update erp.contractors set contractor_name='Epi at actual post'where id=$1",[mandor]);
 await nativeScope('POST',()=>db.query("update erp.sales_headers set status='POSTED',row_version=row_version+1 where id=$1",[invoice]));
 const fact=await posted(invoice);
 assert.equal(fact.contractor_id,mandor);assert.equal(fact.customer_id,customer);assert.equal(fact.contractor_name_at_post,'Epi at actual post');
 assert.equal(fact.posted_by,actor);assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.draft_buyers where sale_id=$1',[invoice]),0);
 assert.equal((await counts()).posted,1);assert.equal((await counts()).own_contexts,0);
 results.push({label:'First Native post stores one immutable explicit buyer snapshot and removes the draft selection',result:'PASS'});
 await nativeScope('POST',()=>db.query("update erp.sales_headers set status='POSTED'where id=$1",[invoice]));
 assert.deepEqual(await posted(invoice),fact);assert.equal((await counts()).posted,1);
 results.push({label:'Repeated posted-header observation never duplicates its buyer fact',result:'PASS'});
 await db.query("update erp.contractors set contractor_name='Later rename',is_active=false where id=$1",[mandor]);
 await nativeScope('PAYMENT',()=>db.query("update erp.sales_headers set status='PAID'where id=$1",[invoice]));
 assert.deepEqual(await posted(invoice),fact);
 await nativeScope('SALE_REVERSE',()=>db.query("update erp.sales_headers set status='REVERSED'where id=$1",[invoice]));
 assert.deepEqual(await posted(invoice),fact);
 results.push({label:'Lawful payment/reversal status observations retain posted names and identities after master changes',result:'PASS'});
 let baseline=await counts();
 await refused('Posted buyer cannot change to another customer',()=>nativeScope('EDIT',()=>db.query('update erp.sales_headers set customer_id=$1 where id=$2',[store,invoice])),'POSTED_BUYER_CHANGED');
 assert.equal(await scalar('select customer_id::text from erp.sales_headers where id=$1',[invoice]),customer);
 await refused('Posted identity cannot be reopened as an editable draft',()=>nativeScope('EDIT',()=>db.query("update erp.sales_headers set status='DRAFT'where id=$1",[invoice])),'POSTED_IDENTITY_CANNOT_RETURN_TO_DRAFT');
 assert.deepEqual(await counts(),baseline);
 await refused('Inactive master cannot acquire a new Native draft',()=>nativeScope('CREATE',()=>create(id(205),inactiveCustomer)),'ACTIVE_POSTING_BUYER_REQUIRED');
 assert.deepEqual(await counts(),baseline);
 await db.query('update erp.customers set is_active=false where id=$1',[otherCustomer]);
 await refused('Inactive linked customer cannot acquire a new Native draft',()=>nativeScope('CREATE',()=>create(id(206),otherCustomer)),'ACTIVE_POSTING_BUYER_REQUIRED');
 await db.query('update erp.customers set is_active=true where id=$1',[otherCustomer]);
 await refused('New mandor identity requires a genuine modeled Native private scope',()=>tx(()=>create(id(207),otherCustomer)),'MODEL_NATIVE_SALES_SCOPE_REQUIRED','42501');
 assert.deepEqual(await counts(),baseline);
 await db.query("select set_config('cp7_model.actor','',false)");
 await refused('New mandor identity cannot use an absent actor',()=>nativeScope('CREATE',()=>create(id(208),otherCustomer)),'NATIVE_SALE_ACTOR_REQUIRED','42501');
 await db.query("select set_config('cp7_model.actor',$1,false)",[actor]);
 await refused('Another private operation context cannot be overwritten',()=>nativeScope('CREATE',async()=>{
  await db.query("insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),$1,$2,'RESERVE',$3)",[actor,id(5001),'a'.repeat(64)]);
  return create(id(209),otherCustomer);
 }),'NATIVE_SALE_CONTEXT_CONFLICT');
 assert.deepEqual(await counts(),baseline);
 const callerOwned=id(210);
 await nativeScope('CREATE',async()=>{
  await db.query("insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),$1,$2,'SAVE_SALE',$3)",[actor,id(5002),'b'.repeat(64)]);
  await create(callerOwned,otherCustomer);
  assert.equal(await scalar('select count(*)::int from cp7_mandor_shop.command_context'),1);
  await db.exec('delete from cp7_mandor_shop.command_context');
 });
 assert.equal((await draft(callerOwned)).contractor_id,other);
 results.push({label:'A matching caller-owned identity context survives the trigger for its owner to clear',result:'PASS'});
 const final=await counts();assert.equal(final.native_contexts,0);assert.equal(final.own_contexts,0);assert.equal(final.journals,0);
 const sourceFiles={};
 for(const name of ['schema.sql','events.sql','sale_identity.sql','sale_identity_model.mjs','NATIVE_SALES_IDENTITY_REFERENCE.json'])sourceFiles[name]=pin(await readFile(here+name));
 const result={status:'FG_MANDOR_NATIVE_HEADER_IDENTITY_MODEL_CONTROLS_PASS_NOT_NATIVE',source_files:sourceFiles,
  results,final_counts:final,model_scope:'One isolated PG/WASM backend; Native-scope gate and Auth modeled; Native invoice/stock/HPP/GL/returns not run',
  retained_storage_15_allocation_15_buyer_20_controls_NOT_rerun:true,Native_financial_functions_changed:0,
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
  public_commands_or_runtime_activated:false,production_go:false,independent_acceptance:false};
 await writeFile(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({status:result.status,controls:results.length,Native_cases:0,output})+'\n');
}finally{await db.close();}
