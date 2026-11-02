// Actual new private buyer SQL on one isolated PostgreSQL/WASM backend.
// Native sales command_access is byte-exact; Auth/permission providers, audit,
// and the remaining Native schema are explicit models. No ERP qualification.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const [runtime,output]=process.argv.slice(2);
assert(runtime&&output,'Explicit existing isolated runtime and new result path required');
const {PGlite}=await import(pathToFileURL(runtime).href);
const here=fileURLToPath(new URL('.',import.meta.url));
const pin=raw=>({bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
const rawReference=await readFile(here+'NATIVE_BUYER_REFERENCE.json');
const reference=JSON.parse(rawReference),signature='cp7_sales.command_access(text)';
assert.equal(reference.head,'6e61506c10a18541c104b981bd438e78b175b5d1');
assert.equal(reference.raw_original.sha256,'7607987b5a8a9100dddbfef5b39135b330eda329bf89b072b3839467cf7c7b86');
const db=new PGlite(),results=[];
const id=n=>'20000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(9001),first=id(1),sameName=id(2),renamed=id(3),disabled=id(4),
 nonMandor=id(5),collision=id(6),nested=id(7),last=id(8),store=id(8001);
let sequence=10000;
const request=()=>id(++sequence);
const permissions=['sales.invoice.view','finance.ar.view','sales.invoice.create','sales.invoice.edit_draft'];
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
async function tx(body){
 await db.exec('BEGIN');
 try{const value=await body();await db.exec('COMMIT');return value;}
 catch(error){await db.exec('ROLLBACK');throw error;}
}
async function refused(label,body,message,code='P0001'){
 let error;try{await body();}catch(caught){error=caught;}
 assert(error,label+': rejection required');assert.equal(error.code,code,label+': SQLSTATE');
 assert(error.message.includes(message),label+': '+error.message);
 results.push({label,result:'REFUSED_AS_REQUIRED',SQLSTATE:error.code,error:message});
}
const options=async(q='',after=null,limit=25,action='CREATE')=>scalar(
 'select cp7_mandor_shop.buyer_options($1,$2,$3,$4)',[action,q,after,limit]);
const option=async(cid,action='CREATE')=>(await options('',null,25,action)).rows.find(x=>x.contractor_id===cid);
const payload=(row,action='CREATE')=>({contract_version:'cp7.mandor-shop-buyer-command.v1',
 sales_action:action,contractor_id:row.contractor_id,review_token:row.review_token});
const command=(p,key=request())=>tx(()=>scalar('select cp7_mandor_shop.buyer_command($1::jsonb,$2)',[JSON.stringify(p),key]));
const counts=async()=>(await db.query(`select
 (select count(*)::int from erp.customers)customers,
 (select count(*)::int from cp7_mandor_shop.contractor_accounts)accounts,
 (select count(*)::int from cp7_mandor_shop.requests)requests,
 (select count(*)::int from cp7_sales.command_context)native_contexts,
 (select count(*)::int from cp7_mandor_shop.command_context)own_contexts,
 (select count(*)::int from erp.sales_headers)sales,
 (select count(*)::int from erp.journal_entries)journals`)).rows[0];
try{
 await db.exec(`
  create role anon;create role authenticated;create role service_role;create role cp7_sales_read;
  create schema erp;create schema auth;create schema extensions;create schema cp7_sales;
  create function auth.uid()returns uuid language sql stable as $$
   select nullif(current_setting('cp7_model.actor',true),'')::uuid $$;
  create function auth.jwt()returns jsonb language sql stable as $$
   select jsonb_build_object('role',coalesce(nullif(current_setting('cp7_model.jwt_role',true),''),'authenticated')) $$;
  create function erp.get_my_access_v1()returns jsonb language sql stable as $$
   select jsonb_build_object('allowed',true,'profile',jsonb_build_object('role_code','STAFF'),
    'actor',auth.uid(),'permissions',coalesce(nullif(current_setting('cp7_model.permissions',true),''),'[]')::jsonb) $$;
  create function erp.has_permission(text)returns boolean language sql stable as $$
   select coalesce(nullif(current_setting('cp7_model.permissions',true),''),'[]')::jsonb?$1 $$;
  create function extensions.digest(bytea,text)returns bytea language sql immutable as $$
   select case when $2='sha256'then pg_catalog.sha256($1)else null end $$;
  create table erp.app_permissions(id uuid primary key);
  create table erp.app_role_permissions(id uuid primary key);
  create table erp.app_roles(id uuid primary key);
  create table erp.app_users(id uuid primary key);
  create table erp.contractors(id uuid primary key default gen_random_uuid(),
   contractor_code varchar(30)not null unique,contractor_name varchar(120)not null,
   contractor_type varchar(30)not null default 'MANDOR',attendance_required boolean not null default true,
   is_active boolean not null default true,notes text,created_at timestamptz not null default statement_timestamp(),
   updated_at timestamptz not null default statement_timestamp());
  create table erp.customers(id uuid primary key default gen_random_uuid(),
   customer_code varchar(30)not null unique,customer_name varchar(150)not null,phone varchar(50),
   address text,is_active boolean not null default true,created_at timestamptz not null default statement_timestamp(),
   updated_at timestamptz not null default statement_timestamp());
  create table cp7_sales.command_context(backend_pid integer not null,transaction_id bigint not null,
   actor uuid not null,sale_id uuid,action text not null,primary key(backend_pid,transaction_id));
  -- Remaining Native tables supply only the existing private schema's FK/type
  -- targets. Their business machinery and audit implementation are not run.
  create table erp.sales_headers(id uuid primary key,customer_id uuid,status varchar(20));
  create table erp.payroll_settlements(id uuid primary key,contractor_id uuid,status varchar(20));
  create table erp.payroll_deductions(id uuid primary key);
  create table erp.journal_entries(id uuid primary key);
  grant usage on schema erp,auth,cp7_sales to cp7_sales_read;
 `);
 await db.exec(reference.functions[signature][0]);
 assert.equal(reference.functions[signature][1],'cp7_sales_read');
 await db.exec('alter function cp7_sales.command_access(text)owner to cp7_sales_read');
 const schema=await readFile(here+'schema.sql'),events=await readFile(here+'events.sql'),buyers=await readFile(here+'buyers.sql');
 await db.exec(schema.toString());await db.exec(events.toString());await db.exec(buyers.toString());
 await db.query("select set_config('cp7_model.actor',$1,false),set_config('cp7_model.permissions',$2,false)",[actor,JSON.stringify(permissions)]);
 for(const [cid,code,name,type,active]of[
  [first,'M1','Epi','MANDOR',true],[sameName,'M2','Epi','MANDOR',true],
  [renamed,'M3','Before rename','MANDOR',true],[disabled,'M4','Inactive','MANDOR',false],
  [nonMandor,'X5','Other contractor','LAUNDRY',true],[collision,'M6','Collision','MANDOR',true],
  [nested,'M7','Nested','MANDOR',true],[last,'M8','Last','MANDOR',true]])
  await db.query('insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,is_active)values($1,$2,$3,$4,$5)',[cid,code,name,type,active]);
 await db.query("insert into erp.customers(id,customer_code,customer_name)values($1,'STORE-1','Epi')",[store]);

 const expectedColumns={};
 for(const [table,declaration]of Object.entries(reference.columns)){
  const actual=await scalar(`select jsonb_object_agg(a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod))
   from pg_attribute a where a.attrelid=$1::regclass and a.attnum>0 and not a.attisdropped`,[table]);
  expectedColumns[table]=Object.fromEntries(Object.values(declaration).map(row=>[row[0],row[2]]));
  assert.deepEqual(actual,expectedColumns[table]);
 }
 results.push({label:'All Native contractor/customer/context column names and types match accepted DE6e615',result:'PASS'});
 const samples=['00000000-0000-0000-0000-000000000000','ffffffff-ffff-ffff-ffff-ffffffffffff',...Array.from({length:100},(_,i)=>id(i+1))];
 const codes=[];
 for(const uuid of samples){
  const code=await scalar('select cp7_mandor_shop.customer_code($1)',[uuid]);
  assert.equal(code,'MD-'+BigInt('0x'+uuid.replaceAll('-','')).toString(36).toUpperCase().padStart(25,'0'));
  assert.equal(code.length,28);codes.push(code);
 }
 assert.equal(new Set(codes).size,samples.length);
 results.push({label:'UUID zero/max and 100 identities preserve all 128 bits in 28-character Native codes',result:'PASS'});
 const beforeOptions=await counts(),all=await options('Epi');
 assert.equal(all.rows.length,2);assert(all.rows.every(x=>x.customer_id===null&&x.can_select===true));
 assert.deepEqual(await counts(),beforeOptions);
 const page1=await options('',null,2),page2=await options('',page1.next_after,2);
 assert.equal(page1.has_more,true);assert.equal(new Set([...page1.rows,...page2.rows].map(x=>x.contractor_id)).size,4);
 assert(!(await options()).rows.some(x=>[disabled,nonMandor].includes(x.contractor_id)));
 results.push({label:'Buyer search/paging is read-only and uses active MANDOR UUIDs even when names match',result:'PASS'});
 await db.exec(`
  create function erp.model_customer_insert_context()returns trigger language plpgsql as $$
  begin
   if not exists(select 1 from cp7_sales.command_context n join cp7_mandor_shop.command_context s
    on n.backend_pid=s.backend_pid and n.transaction_id=s.transaction_id and n.actor=s.actor
    where n.backend_pid=pg_backend_pid()and n.transaction_id=txid_current()
     and n.actor=auth.uid()and n.action in('CREATE','EDIT')and s.action='PREPARE_BUYER')then
    raise exception 'MODEL_EXACT_PRIVATE_CUSTOMER_PREPARATION_CONTEXT_REQUIRED';end if;
   return new;
  end $$;
  create trigger model_customer_context before insert on erp.customers
   for each row execute function erp.model_customer_insert_context();
 `);
 const firstOption=await option(first),firstPayload=payload(firstOption),key=request();
 const made=await command(firstPayload,key);
 assert.equal(made.contractor_id,first);assert.equal(made.name,'Epi');assert.notEqual(made.customer_id,store);
 assert.equal(made.customer_code,await scalar('select cp7_mandor_shop.customer_code($1)',[first]));
 let current=await counts();assert.equal(current.accounts,1);assert.equal(current.customers,beforeOptions.customers+1);
 assert.equal(current.native_contexts,0);assert.equal(current.own_contexts,0);assert.equal(current.sales,0);assert.equal(current.journals,0);
 results.push({label:'Preparing mandor buyer creates one explicit customer/account and cleans both private contexts',result:'PASS'});
 assert.deepEqual(await command(firstPayload,key),made);assert.deepEqual(await counts(),current);
 results.push({label:'Exact request replay returns its immutable result without a second customer or account',result:'PASS'});
 await refused('Changed buyer intent cannot reuse a completed request',()=>command({...firstPayload,contractor_id:sameName},key),'REQUEST_CHANGED');
 assert.deepEqual(await counts(),current);
 await refused('A stale review from before account creation cannot create a second customer',()=>command(firstPayload),'REVIEW_CHANGED');
 assert.deepEqual(await counts(),current);
 const reused=await command(payload(await option(first,'EDIT'),'EDIT'));
 assert.equal(reused.customer_id,made.customer_id);assert.equal((await counts()).accounts,1);
 results.push({label:'Another permitted draft action reuses the same immutable mandor/customer identity',result:'PASS'});
 const second=await command(payload(await option(sameName)));
 assert.notEqual(second.customer_id,made.customer_id);assert.notEqual(second.customer_id,store);
 results.push({label:'Same mandor name and same ordinary store-customer name never merge identities',result:'PASS'});
 const oldReview=payload(await option(renamed));current=await counts();
 await db.query("update erp.contractors set contractor_name='Renamed'where id=$1",[renamed]);
 await refused('Changed master mandor invalidates the earlier buyer review',()=>command(oldReview),'REVIEW_CHANGED');
 assert.deepEqual(await counts(),current);
 const disabledBasis=await scalar('select cp7_mandor_shop.buyer_basis($1)',[disabled]);
 const access=await scalar("select cp7_mandor_shop.buyer_access('CREATE')");
 for(const cid of [disabled,nonMandor]){
  const basis=cid===disabled?disabledBasis:await scalar('select cp7_mandor_shop.buyer_basis($1)',[cid]);
  const review=await scalar("select cp7_mandor_shop.buyer_review('CREATE',$1::jsonb,$2::jsonb)",[JSON.stringify(access),JSON.stringify(basis)]);
  await refused(cid===disabled?'Inactive mandor cannot prepare a buyer':'Non-MANDOR master cannot prepare a buyer',
   ()=>command(payload({contractor_id:cid,review_token:review})),'ACTIVE_MANDOR_REQUIRED');
 }
 await db.query('update erp.customers set is_active=false where id=$1',[second.customer_id]);
 const inactive=await option(sameName);assert.equal(inactive.can_select,false);
 await refused('An inactive linked customer is not silently reactivated',()=>command(payload(inactive)),'CUSTOMER_INACTIVE');
 assert.equal(await scalar('select is_active from erp.customers where id=$1',[second.customer_id]),false);
 await db.exec('alter table erp.customers disable trigger model_customer_context');
 const blockedCode=await scalar('select cp7_mandor_shop.customer_code($1)',[collision]);
 await db.query("insert into erp.customers(customer_code,customer_name)values($1,'Unrelated customer')",[blockedCode]);
 await db.exec('alter table erp.customers enable trigger model_customer_context');
 current=await counts();
 await refused('An ordinary customer with the generated code requires review instead of being linked',async()=>command(payload(await option(collision))),'ACCOUNT_CODE_COLLISION_REVIEW_REQUIRED');
 assert.deepEqual(await counts(),current);
 const nestedPayload=payload(await option(nested));
 await refused('An existing Native command context cannot be overwritten',()=>tx(async()=>{
  await db.query("insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),$1,null,'CREATE')",[actor]);
  return scalar('select cp7_mandor_shop.buyer_command($1::jsonb,$2)',[JSON.stringify(nestedPayload),request()]);
 }),'BUYER_NESTED_CONTEXT_REFUSED');
 assert.deepEqual(await counts(),current);
 await db.query("select set_config('cp7_model.permissions',$1,false)",[JSON.stringify(permissions.filter(x=>x!=='finance.ar.view'))]);
 await refused('Current Native sales permission is required even for an exact replay',()=>command(firstPayload,key),'CP7_SALES_WRITE_DENIED','42501');
 assert.deepEqual(await counts(),current);
 await db.query("select set_config('cp7_model.permissions',$1,false)",[JSON.stringify(permissions)]);
 await refused('Unsupported action cannot reuse Native sales authority',async()=>command({...payload(await option(last)),sales_action:'POST'}),'BUYER_ACTION_DENIED','42501');
 await refused('Unexpected buyer fields are refused',async()=>command({...payload(await option(last)),customer_id:store}),'BUYER_COMMAND_FIELDS');
 await refused('Read committed is required before mutation',()=>tx(async()=>{
  await db.exec('set transaction isolation level repeatable read');
  return scalar('select cp7_mandor_shop.buyer_command($1::jsonb,$2)',[JSON.stringify(payload(await option(last))),request()]);
 }),'CP7_FRESH_ACCESS_REQUIRED');
 await refused('Private buyer functions are not exposed directly to the browser role',()=>tx(async()=>{
  await db.exec('set local role authenticated');return scalar("select cp7_mandor_shop.buyer_options('CREATE')");
 }),'permission denied','42501');
 assert.deepEqual(await counts(),current);
 const sourceFiles={};
 for(const name of ['schema.sql','events.sql','buyers.sql','NATIVE_BUYER_REFERENCE.json','buyer_model.mjs'])sourceFiles[name]=pin(await readFile(here+name));
 const result={status:'FG_MANDOR_PRIVATE_BUYER_MODEL_CONTROLS_PASS_NOT_NATIVE',source_files:sourceFiles,
  exact_Native_command_access_definition:pin(Buffer.from(reference.functions[signature][0])),
  exact_Native_schema_column_types:expectedColumns,results,
  model_scope:'One isolated PG/WASM backend; Auth/permission providers, private-context audit guard and partial Native schema are explicit models',
  retained_storage_15_and_allocation_15_controls_NOT_rerun:true,Native_invoice_or_stock_or_payroll_ran:false,
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
  public_commands_or_runtime_activated:false,production_go:false,independent_acceptance:false};
 await writeFile(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({status:result.status,controls:results.length,Native_cases:0,output})+'\n');
}finally{await db.close();}
