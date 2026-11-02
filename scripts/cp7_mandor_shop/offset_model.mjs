// New offset proof controls only. Existing 67 models are retained, not rerun.
// Native tables copy accepted-DE column types; Native constraints, Auth,
// journal/payroll/invoice engines, stock, HPP and two backends are NOT run.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const [runtime,output]=process.argv.slice(2);
assert(runtime&&output,'Pinned PG/WASM runtime and new output required');
const runtimePackage=JSON.parse(await readFile(new URL('../package.json',pathToFileURL(runtime))));
assert.equal(runtimePackage.version,'0.5.14','Exact pinned model runtime');
const {PGlite}=await import(pathToFileURL(runtime).href),db=new PGlite();
const here=fileURLToPath(new URL('.',import.meta.url)),results=[];
const pin=raw=>({bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
const reference=JSON.parse(await readFile(here+'NATIVE_OFFSET_REFERENCE.json'));
assert.equal(reference.head,'6e61506c10a18541c104b981bd438e78b175b5d1');
assert.equal(reference.functions_unchanged_in_actual_after_committed_E_use,true);
const id=n=>'40000000-0000-4000-8000-'+String(n).padStart(12,'0');
const actor=id(1),mandor=id(2),customer=id(3),store=id(4),payable=id(10),ar=id(11),
 income=id(12),cash=id(13),newAR=id(14);
let serial=1000;
const next=()=>id(++serial),sha='a'.repeat(64);
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
const check=(label)=>results.push({label,result:'PASS'});
async function plain(body){
 await db.exec('BEGIN');
 try{const result=await body();await db.exec('COMMIT');return result;}
 catch(error){await db.exec('ROLLBACK');throw error;}
}
async function scope(action,body){
 return plain(async()=>{
  const request=next();
  await db.query(`insert into cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response)
   values($1,$2,$3,'{}',$4,'{}')`,[actor,request,action,sha]);
  await db.query(`insert into cp7_mandor_shop.command_context
   values(pg_backend_pid(),txid_current(),$1,$2,$3,$4)`,[actor,request,action,sha]);
  const result=await body(request);
  await db.exec('delete from cp7_mandor_shop.command_context');
  return result;
 });
}
async function refused(label,body,expected,code='P0001'){
 let error;try{await body();}catch(caught){error=caught;}
 assert(error,label+': rejection required');assert.equal(error.code,code,label+': SQLSTATE');
 assert(error.message.includes(expected),label+': '+error.message);
 results.push({label,result:'REFUSED_AS_REQUIRED',SQLSTATE:error.code,error:expected});
}
const paid=sale=>scalar('select cp7_mandor_shop.invoice_offset_paid($1)::text',[sale]);
async function counts(){
 return (await db.query(`select (select count(*)::int from cp7_mandor_shop.settlements)settlements,
  (select count(*)::int from cp7_mandor_shop.settlement_reversals)reversals,
  (select count(*)::int from cp7_mandor_shop.offset_accounts)accounts,
  (select count(*)::int from cp7_mandor_shop.allocation_events)events,
  (select count(*)::int from erp.journal_entries)journals,
  (select count(*)::int from erp.journal_lines)legs`)).rows[0];
}
async function event(allocation,kind,request,settlement=null,reversal=null){
 const s=await scalar('select(select to_jsonb(s)from cp7_mandor_shop.allocation_states s where allocation_id=$1)',[allocation]);
 return db.query(`insert into cp7_mandor_shop.allocation_events
  (id,allocation_id,ordinal,predecessor_id,kind,settlement_id,reversal_id,actor,request_id)
  values($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
 [next(),allocation,(s?.last_ordinal||0)+1,s?.last_event_id||null,kind,settlement,reversal,actor,request]);
}
async function sale(){
 const sale=next();
 await scope('POST_SALE',async()=>{
  await db.query(`insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status)
   values($1,$2,$3,'2026-10-05T02:00:00Z','POSTED')`,[sale,'MODEL-'+sale,customer]);
  await db.query(`insert into cp7_mandor_shop.sales
   (sale_id,contractor_id,customer_id,contractor_name_at_post,posted_by)
   values($1,$2,$3,'Epi',$4)`,[sale,mandor,customer,actor]);
 });
 return sale;
}
async function payroll(date){
 const payroll=next();
 await scope('RESERVE',async()=>{
  await db.query(`insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status)
   values($1,$2,$3,$4::date,$4::date+6,'DRAFT')`,[payroll,'PAY-'+payroll,mandor,date]);
  await db.query(`insert into cp7_mandor_shop.payroll_identities(payroll_id,contractor_id,created_by)
   values($1,$2,$3)`,[payroll,mandor,actor]);
 });
 return payroll;
}
async function reserve(sale,payroll,amount){
 return scope('RESERVE',async request=>{
  const allocation=next(),deduction=next();
  await db.query(`insert into cp7_mandor_shop.allocations
   (id,sale_id,payroll_id,contractor_id,amount,actor,request_id)values($1,$2,$3,$4,$5,$6,$7)`,
  [allocation,sale,payroll,mandor,amount,actor,request]);
  await db.query(`insert into erp.payroll_deductions(id,payroll_id,deduction_type,amount)
   values($1,$2,'OTHER',$3)`,[deduction,payroll,amount]);
  await db.query(`insert into cp7_mandor_shop.deduction_links
   (allocation_id,sale_id,payroll_id,contractor_id,amount,deduction_id)values($1,$2,$3,$4,$5,$6)`,
  [allocation,sale,payroll,mandor,amount,deduction]);
  await event(allocation,'RESERVE',request);
  return {allocation,sale,payroll,amount,deduction};
 });
}
async function legs(journal,total,receivable,inverse=false){
 await db.query(`insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,contractor_id)
  values($1,$2,$3,$4,$5,$6)`,[next(),journal,payable,inverse?'0':total,inverse?total:'0',mandor]);
 await db.query(`insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,customer_id)
  values($1,$2,$3,$4,$5,$6)`,[next(),journal,receivable,inverse?total:'0',inverse?'0':total,customer]);
}
async function settle(items,options={}){
 return scope('SETTLE',async request=>{
  const settlement=next(),journal=next(),payroll=items[0].payroll;
  const total=String(items.reduce((n,l)=>n+Number(l.amount),0));
  const receivable=await scalar("select account_id::text from erp.accounting_account_mappings where mapping_key='AR_CUSTOMER'");
  await db.query("update erp.payroll_settlements set status='PAID'where id=$1",[payroll]);
  await db.query(`insert into erp.journal_entries
   (id,journal_number,transaction_date,economic_date,source_type,source_id,status)
   values($1,$2,'2026-10-19','2026-10-12','FG_MANDOR_PAYROLL_OFFSET',$3,'POSTED')`,
  [journal,'J-'+journal,settlement]);
  await legs(journal,total,receivable);
  if(options.badCustomer)await db.query('update erp.journal_lines set customer_id=null where journal_entry_id=$1 and account_id=$2',[journal,receivable]);
  await db.query(`insert into cp7_mandor_shop.settlements
   (id,payroll_id,contractor_id,journal_id,total_amount,economic_date,book_date,actor,request_id)
   values($1,$2,$3,$4,$5,'2026-10-12','2026-10-19',$6,$7)`,
  [settlement,payroll,mandor,journal,total,actor,request]);
  await db.query(`insert into cp7_mandor_shop.offset_accounts
   values($1,$2,$3,$4,$5,$6)`,[settlement,payable,receivable,customer,options.wrongActor?store:actor,request]);
  for(const l of items){
   await db.query(`insert into cp7_mandor_shop.settlement_lines
    values($1,$2,$3,$4,$5,$6)`,[settlement,l.allocation,l.sale,payroll,mandor,l.amount]);
   if(!options.noEvents)await event(l.allocation,'SETTLE',request,settlement);
  }
  return {settlement,journal,payroll,total,receivable,items};
 });
}
async function reverse(value,kind='REOPEN',options={}){
 return scope(kind,async request=>{
  const journal=next(),reversal=next();
  await db.query("update erp.journal_entries set status='REVERSED'where id=$1",[value.journal]);
  await db.query("update erp.payroll_settlements set status='APPROVED'where id=$1",[value.payroll]);
  await db.query(`insert into erp.journal_entries
   (id,journal_number,transaction_date,economic_date,source_type,source_id,status,reversal_of_id)
   values($1,$2,'2026-11-02','2026-11-02',$3,$4,'POSTED',$4)`,
  [journal,'REV-'+journal,options.badSource?'FG_MANDOR_OFFSET_REVERSE':'JOURNAL_REVERSAL',value.journal]);
  await legs(journal,value.total,options.badAccount?cash:value.receivable,true);
  await db.query(`insert into cp7_mandor_shop.settlement_reversals
   (id,settlement_id,reversal_journal_id,reason,actor,request_id)values($1,$2,$3,'Model legal correction',$4,$5)`,
  [reversal,value.settlement,journal,actor,request]);
  for(const l of value.items){
   await event(l.allocation,kind,request,value.settlement,reversal);
   if(kind==='REVERSE'){
    await db.query('delete from cp7_mandor_shop.deduction_links where allocation_id=$1',[l.allocation]);
    await db.query('delete from erp.payroll_deductions where id=$1',[l.deduction]);
   }
  }
  return reversal;
 });
}

try{
 await db.exec(`create role anon;create role authenticated;create role service_role;
  create schema erp;create schema auth;
  create function auth.uid()returns uuid language sql stable as $$
   select nullif(current_setting('cp7_model.actor',true),'')::uuid $$;`);
 for(const [table,columns]of Object.entries(reference.columns)){
  const names=Object.values(columns).sort((a,b)=>a[1]-b[1]);
  const key=table==='erp.accounting_account_mappings'?'mapping_key':'id';
  await db.exec('create table '+table+'('+names.map(c=>'"'+c[0]+'" '+c[2]+(c[0]===key?' primary key':'')).join(',')+')');
  const actual=await scalar(`select jsonb_object_agg(attname,format_type(atttypid,atttypmod))
   from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped`,[table]);
  assert.deepEqual(actual,Object.fromEntries(names.map(c=>[c[0],c[2]])));
 }
 for(const name of ['schema.sql','events.sql','offset_projection.sql'])await db.exec((await readFile(here+name)).toString());
 const postgres=await scalar('select version()');
 check('Ten Native table column-type maps match actual accepted DE30 and all three new private functions compile');
 await db.query("select set_config('cp7_model.actor',$1,false)",[actor]);
 await db.query("insert into erp.contractors(id,contractor_name,is_active)values($1,'Epi',true)",[mandor]);
 for(const [value,name]of[[customer,'Epi'],[store,'Ordinary shop']])
  await db.query('insert into erp.customers(id,customer_name,is_active)values($1,$2,true)',[value,name]);
 await db.query('insert into cp7_mandor_shop.contractor_accounts(contractor_id,customer_id,created_by)values($1,$2,$3)',[mandor,customer,actor]);
 for(const [value,code]of[[payable,'PAYABLE'],[ar,'AR'],[income,'INCOME'],[cash,'BANK'],[newAR,'NEW_AR']])
  await db.query('insert into erp.chart_accounts(id,account_code,is_active,is_postable)values($1,$2,true,true)',[value,code]);
 for(const [key,value]of[['CONTRACTOR_PAYABLE',payable],['AR_CUSTOMER',ar],['OTHER_INCOME',income]])
  await db.query('insert into erp.accounting_account_mappings(mapping_key,account_id)values($1,$2)',[key,value]);
 await db.query('insert into erp.cash_accounts(id,coa_account_id,is_active)values($1,$2,true)',[next(),cash]);
 const invoice=await sale(),week1=await payroll('2026-10-12'),week2=await payroll('2026-10-19');
 const first=await reserve(invoice,week1,'200000'),remaining=await reserve(invoice,week2,'100000');
 assert.equal(await paid(invoice),'0');assert.equal((await counts()).journals,0);
 check('Two manually chosen weeks reserve the same invoice without paid projection or journal');
 const original=await settle([first]);
 assert.equal(await paid(invoice),'200000');
 check('A settled chosen-week part pays the same invoice exactly once through two noncash GL legs');
 const second=await settle([remaining]);assert.equal(await paid(invoice),'300000');
 assert.equal(await paid(invoice),'300000');assert.equal((await counts()).journals,2);
 check('Following-week remainder and repeated read sum to 300000 without a duplicated journal');
 const b=await sale(),c=await sale(),week3=await payroll('2026-10-26');
 await settle([await reserve(b,week3,'75000'),await reserve(c,week3,'25000')]);
 assert.equal(await paid(b),'75000');assert.equal(await paid(c),'25000');
 check('One payroll journal serves two explicit invoices while each paid projection keeps its own amount');
 const toko=next();
 await db.query(`insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status)
  values($1,'TOKO',$2,'2026-10-05T02:00:00Z','POSTED')`,[toko,store]);
 assert.equal(await paid(toko),'0');assert.equal(await paid(store),'0');
 check('A posted ordinary shop invoice and an unknown invoice have no mandor offset');
 const badSale=await sale(),badWeek=await payroll('2026-11-02'),badAllocation=await reserve(badSale,badWeek,'10');
 let baseline=await counts();
 await refused('Deferred commit rejects missing SETTLE event before any financial fact survives',()=>settle([badAllocation],{noEvents:true}),'EXACT_SETTLED_PREFIX_AND_NATIVE_DEDUCTION_REQUIRED');
 assert.deepEqual(await counts(),baseline);
 await refused('Deferred commit rejects NULL customer leg and rolls back the whole settlement',()=>settle([badAllocation],{badCustomer:true}),'EXACT_NONCASH_OFFSET_LEGS_REQUIRED');
 assert.deepEqual(await counts(),baseline);
 await refused('Posted snapshot actor must be the same owning command actor',()=>settle([badAllocation],{wrongActor:true}),'EXACT_OFFSET_ACCOUNT_COMMAND_REQUIRED');
 assert.deepEqual(await counts(),baseline);
 // Mapping cases need the same command transaction; use a temporary committed
 // modeled configuration and restore it in finally. No Native settings API ran.
 for(const [label,key,value]of[
  ['Native cash account cannot be captured as an offset receivable','AR_CUSTOMER',cash],
  ['OTHER_INCOME cannot share an offset account','OTHER_INCOME',ar]]){
  const old=await scalar('select account_id::text from erp.accounting_account_mappings where mapping_key=$1',[key]);
  await db.query('update erp.accounting_account_mappings set account_id=$1 where mapping_key=$2',[value,key]);
  try{await refused(label,()=>settle([badAllocation]),'ACTIVE_NONCASH_NATIVE_OFFSET_ACCOUNTS_REQUIRED');}
  finally{await db.query('update erp.accounting_account_mappings set account_id=$1 where mapping_key=$2',[old,key]);}
 }
 const mutations=[
  ['NULL customer dimension is not skipped by an aggregate','update erp.journal_lines set customer_id=null where journal_entry_id=$1 and credit>0',[original.journal],'EXACT_NONCASH_OFFSET_LEGS_REQUIRED'],
  ['NULL contractor dimension cannot pass the payable leg','update erp.journal_lines set contractor_id=null where journal_entry_id=$1 and debit>0',[original.journal],'EXACT_NONCASH_OFFSET_LEGS_REQUIRED'],
  ['Wrong cash account cannot pass a posted offset proof','update erp.journal_lines set account_id=$1 where journal_entry_id=$2 and credit>0',[cash,original.journal],'EXACT_NONCASH_OFFSET_LEGS_REQUIRED'],
  ['A third zero-value GL leg is still an invalid offset',`insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit)values($1,$2,$3,0,0)`,[next(),original.journal,ar],'EXACT_NONCASH_OFFSET_LEGS_REQUIRED'],
  ['Changed Native deduction amount requires review','update erp.payroll_deductions set amount=1 where id=$1',[first.deduction],'EXACT_SETTLED_PREFIX_AND_NATIVE_DEDUCTION_REQUIRED'],
  ['Cash-advance linkage cannot masquerade as an FG deduction','update erp.payroll_deductions set opening_cash_advance_balance_id=$1 where id=$2',[next(),first.deduction],'EXACT_SETTLED_PREFIX_AND_NATIVE_DEDUCTION_REQUIRED'],
  ['Inactive invoice with an active offset requires lawful correction',"update erp.sales_headers set status='REVERSED'where id=$1",[invoice],'INACTIVE_INVOICE_ACTIVE_OFFSET_REVIEW_REQUIRED']
 ];
 for(const [label,sql,args,message]of mutations)
  await refused(label,()=>plain(async()=>{await db.query(sql,args);await paid(invoice);}),message);
 await refused('Unclaimed Native offset journal cannot mint an invoice payment',()=>plain(async()=>{
  await db.query(`insert into erp.journal_entries(id,status,source_type,source_id)
   values($1,'POSTED','FG_MANDOR_PAYROLL_OFFSET',$2)`,[next(),next()]);await paid(invoice);
 }),'UNCLAIMED_NATIVE_OFFSET_JOURNAL');
 await db.query("update erp.accounting_account_mappings set account_id=$1 where mapping_key='AR_CUSTOMER'",[newAR]);
 await db.query('update erp.chart_accounts set is_active=false where id=$1',[ar]);
 assert.equal(await paid(invoice),'300000');check('Later mapping and account activation changes do not rewrite historical posted account snapshots');
 baseline=await counts();
 await refused('Wrong reversal source type is rejected at commit atomically',()=>reverse(original,'REOPEN',{badSource:true}),'EXACT_NATIVE_OFFSET_REVERSAL_REQUIRED');
 assert.deepEqual(await counts(),baseline);
 await refused('A cash leg cannot replace the exact historical inverse',()=>reverse(original,'REOPEN',{badAccount:true}),'EXACT_INVERSE_OFFSET_LEGS_REQUIRED');
 assert.deepEqual(await counts(),baseline);
 await reverse(original);assert.equal(await paid(invoice),'100000');
 assert.equal(await scalar('select state from cp7_mandor_shop.allocation_states where allocation_id=$1',[first.allocation]),'RESERVED');
 check('Lawful Native-shaped reversal removes only the settled part and restores its reservation');
 await settle([first]);assert.equal(await paid(invoice),'300000');
 check('A new settlement after reopening remains valid while old inverse proof survives the payroll becoming PAID again');
 await reverse(second,'REVERSE');assert.equal(await paid(invoice),'200000');
 assert.equal(await scalar('select state from cp7_mandor_shop.allocation_states where allocation_id=$1',[remaining.allocation]),'RELEASED');
 check('Full reversal releases the allocation and keeps the remaining posted invoice payment exactly');
 await refused('Historical posted account snapshot cannot be edited',()=>plain(()=>db.query('update cp7_mandor_shop.offset_accounts set customer_id=$1 where settlement_id=$2',[store,original.settlement])),'IMMUTABLE');
 baseline=await counts();await db.exec('BEGIN READ ONLY');assert.equal(await paid(invoice),'200000');await db.exec('COMMIT');
 assert.deepEqual(await counts(),baseline);check('Paid projection executes in a read-only transaction and creates no event or journal');
 assert.equal(await scalar("select has_table_privilege('authenticated','cp7_mandor_shop.offset_accounts','SELECT')"),false);
 assert.equal(await scalar("select has_function_privilege('authenticated','cp7_mandor_shop.invoice_offset_paid(uuid)','EXECUTE')"),false);
 check('New table and functions expose no direct authenticated-role access');
 const sourceFiles={};
 for(const name of ['schema.sql','events.sql','offset_projection.sql','offset_model.mjs','NATIVE_OFFSET_REFERENCE.json'])sourceFiles[name]=pin(await readFile(here+name));
 const value={status:'FG_MANDOR_PRIVATE_OFFSET_PROJECTION_MODEL_CONTROLS_PASS_NOT_NATIVE',
  source_files:sourceFiles,postgres_version:postgres,PGlite_version:runtimePackage.version,
  Node_version:process.version,new_private_functions:3,results,
  Native_model_tables:Object.keys(reference.columns),Native_model_column_types_match_accepted_DE30:true,
  Native_constraints_Auth_and_posting_engines_modeled_or_not_run:true,
  retained_67_storage_allocation_buyer_identity_controls_NOT_rerun:true,
  previous_unpublished_19_offset_controls_NOT_reused_on_rebuilt_source:true,
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
  Native_payment_hooks_implemented:false,authoritative_Native_paid_projection_integrated:false,
  public_commands_or_runtime_activated:false,production_go:false,independent_acceptance:false};
 await writeFile(output,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({status:value.status,controls:results.length,Native_cases:0,output}));
}catch(error){
 const sourceFiles={};
 for(const name of ['schema.sql','events.sql','offset_projection.sql','offset_model.mjs','NATIVE_OFFSET_REFERENCE.json'])sourceFiles[name]=pin(await readFile(here+name));
 await writeFile(output,JSON.stringify({status:'INCOMPLETE',source_files:sourceFiles,results,
  first_error:{name:error.name,code:error.code||null,message:error.message,stack:error.stack},
  actual_Native_cases:0,production_go:false,independent_acceptance:false},null,2)+'\n',{flag:'wx'});
 throw error;
}finally{await db.close();}
