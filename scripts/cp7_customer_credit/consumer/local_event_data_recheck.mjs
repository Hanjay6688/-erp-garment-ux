import{readFileSync}from'node:fs';import assert from'node:assert/strict';
const{PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const fragment=(sql,from,to)=>{assert.equal(sql.split(from).length,2);return from+sql.split(from)[1].split(to)[0]};
const ledger=read('../ledger/01_immutable_facts.proposal.sql'),poster=read('../ledger/02_uuid_poster.proposal.sql');
const refund=read('../refund/01_initial_refund.proposal.sql'),source=read('../source/source.sql');
const readers=read('../readers/01_current_reader_capability.proposal.sql');
const strip=sql=>{assert.equal((sql.match(/do \$not_an_installer\$/g)||[]).length,1);return sql.replace(/do \$not_an_installer\$begin[\s\S]*?end \$not_an_installer\$;/,'')};
const db=new PGlite(),checks=[];const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
async function rows(sql,p=[]){return(await db.query(sql,p)).rows}
async function one(sql,p=[]){return(await rows(sql,p))[0]}
async function insert(table,o){const keys=Object.keys(o);await db.query(`insert into ${table}(${keys.join(',')})values(${keys.map((_,n)=>'$'+(n+1)).join(',')})`,Object.values(o))}
async function json(sql,p=[]){return(await one(sql,p)).v}
async function sha(v){return(await one('select cp7_credit.pg_jsonb_sha256($1::jsonb)as h',[JSON.stringify(v)])).h}
async function lineSha(v){return(await one('select cp7_credit.native_lines_sha256($1::jsonb)as h',[JSON.stringify(v)])).h}
async function data(n){return json('select cp7_credit.consumer_event_data_v1($1)as v',[id(n)])}
async function refuse(thunk,re){try{await thunk()}catch(e){assert.match(e.message,re);return}throw Error('Expected refusal '+re)}
// Controlled corruption happens only in a disposable local synthetic database.
// A rollback restores each before-state. Actual immutable trigger bypass is
// explicit here; no claim is made that an app actor can perform these writes.
async function corrupt(sql,p,re,event=20){await db.exec('begin;set local session_replication_role=replica');try{await db.query(sql,p);await db.exec('set local session_replication_role=origin');await refuse(()=>data(event),re)}finally{await db.exec('rollback')}}
try{
await db.exec(`set TimeZone='UTC';create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;create role cp7_credit_write nologin noinherit nobypassrls;
create schema erp;create schema cp7_credit;create schema cp7_note;create schema ow04_source_proposal;
grant usage on schema cp7_credit to cp7_credit_write;
create table erp.customers(id uuid primary key);
create table erp.sales_headers(id uuid primary key,customer_id uuid,status text,sale_date timestamptz);
create table erp.sales_items(id uuid primary key,sale_id uuid,line_total numeric);
create table erp.sales_returns(id uuid primary key);
create table erp.chart_accounts(id uuid primary key,account_type text,normal_balance text);
create table erp.cash_accounts(id uuid primary key,coa_account_id uuid);
create table erp.journal_entries(id uuid primary key,source_type text,source_id uuid,status text,reversal_of_id uuid,economic_date date,transaction_date date,posting_at timestamptz);
create table erp.journal_lines(id uuid primary key,journal_entry_id uuid,account_id uuid,customer_id uuid,description text,debit numeric,credit numeric,vendor_id uuid,contractor_id uuid,po_id uuid,product_id uuid);
create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid,revision bigint);
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid);
create table cp7_credit.recognition_plans(id uuid primary key);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid,source_sale_id uuid,customer_id uuid,credit_account_id uuid,initial_plan_id uuid,initial_net_amount numeric);
create table cp7_credit.financial_materializations(id uuid primary key);
create table cp7_credit.initial_return_materializations(operation_id uuid,refund_operation_id uuid,cohort_id uuid,projection jsonb);`);
await db.exec(fragment(ledger,'create function cp7_credit.pg_jsonb_sha256','-- Register EVERY'));
await db.exec(fragment(ledger,'create table cp7_credit.consumption_events','-- Every snapshot'));
await db.exec(strip(read('02_operation_facts.sql')));
await db.exec(fragment(refund,'create table cp7_credit.initial_refund_operations','-- Separate, closed'));
await db.exec(fragment(poster,'create function cp7_credit.native_cent_lines','-- Private per-part'));
await db.exec(fragment(source,'create function ow04_source_proposal.canonical_json_v1','create function ow04_source_proposal.journal_payload'));
await db.exec(fragment(source,'create function ow04_source_proposal.financial_journal_payload','-- Resolve the real'));
await db.exec(fragment(readers,'create function cp7_credit.current_leaf_assignment','-- REQUIRED integration'));
await db.exec(fragment(refund,'create function cp7_credit.initial_refund_lines','create function cp7_credit.initial_refund_cash_snapshot'));
await db.exec(fragment(refund,'create function cp7_credit.verify_initial_refund_journal','-- Sole writer entry'));
await db.exec(strip(read('05_event_data.sql')));
// The complete coordinator/grants are intentionally absent. Compile the real
// eight bodies, then exercise only the pure payload validator. Never provide
// successful authority/source/closure substitutes for the missing callbacks.
await db.exec(strip(read('06_access_and_requests.sql')).split('do $private$')[0]);
const accessChecks=[];
const payload={action:'APPLY',cohort_id:id(9),target_sale_id:id(2),cash_account_id:null,restores_event_id:null,
 amount:'80.00',physical_at:'2026-10-20T10:00:00+07:00',reason:'Explicit synthetic payload only',reference:null};
const validate=(p,quote)=>db.query('select cp7_credit.validate_consumer_payload_v1($1::jsonb,$2)',[JSON.stringify(p),quote]);
await validate(payload,false);await validate({...payload,quote_sha256:'0'.repeat(64)},true);accessChecks.push('EXPLICIT_APPLY_AND_BOUND_QUOTE_PAYLOAD_ACCEPTED');
await validate({...payload,action:'REFUND',target_sale_id:null,cash_account_id:id(105)},false);accessChecks.push('REFUND_REQUIRES_EXPLICIT_CASH_CHOICE');
const undo={...payload,action:'UNDO',cohort_id:null,target_sale_id:null,amount:null,restores_event_id:id(20)};await validate(undo,false);accessChecks.push('UNDO_NAMES_ONE_ORIGINAL_WITHOUT_DERIVED_AMOUNT_OR_DIMENSIONS');
for(const[name,changes]of[['ZERO',{amount:'0.00'}],['NEGATIVE',{amount:'-1.00'}],['SUBCENT',{amount:'0.001'}],['NONFINITE',{amount:'NaN'}],['NUMBER_INSTEAD_OF_DECIMAL_STRING',{amount:80}],['FREE_BOOK_DATE',{transaction_date:'2026-10-20'}],['BLANK_PHYSICAL',{physical_at:''}],['RELATIVE_PHYSICAL',{physical_at:'now+07:00'}],['ZONELESS_PHYSICAL',{physical_at:'2026-10-20T10:00:00'}],['NONCANONICAL_REASON',{reason:' untrimmed reason '}],['MISSING_TARGET',{target_sale_id:null}],['APPLY_CASH',{cash_account_id:id(105)}],['UNREQUESTED_ORIGINAL',{restores_event_id:id(20)}]]){await refuse(()=>validate({...payload,...changes},false),/CP7_CREDIT_CONSUMER_/);accessChecks.push(name+'_REFUSED')}
await refuse(()=>validate({...undo,amount:'-80.00'},false),/UNDO_NAMES_ORIGINAL_ONLY/);accessChecks.push('UNDO_CANNOT_SUPPLY_ITS_OWN_NEGATIVE_MONEY');
await refuse(()=>validate({...payload,quote_sha256:'bad'},true),/PAYLOAD_FIELDS/);accessChecks.push('INVALID_QUOTE_BINDING_REFUSED');
await refuse(()=>validate({...payload,quote_sha256:'0'.repeat(64)},false),/PAYLOAD_FIELDS/);accessChecks.push('QUOTE_QUERY_CANNOT_SMUGGLE_BOUND_SAVE_FIELDS');
checks.push('EIGHT_COMMAND_CALLBACK_BODIES_COMPILE_WITHOUT_PERMISSION_OR_CLOSURE_STUBS');
checks.push('ACTUAL_CONSUMER_DDL_AND_FIVE_STABLE_PRIVATE_FUNCTIONS_COMPILE');
await insert('erp.customers',{id:id(1)});
for(const n of [1,2,3])await insert('erp.sales_headers',{id:id(n),customer_id:id(1),status:n===1?'PAID':'POSTED',sale_date:'2026-10-19T00:00:00+07:00'});
for(const[n,type,normal]of[[101,'LIABILITY','CREDIT'],[102,'ASSET','DEBIT'],[103,'ASSET','DEBIT'],[104,'REVENUE','CREDIT']])await insert('erp.chart_accounts',{id:id(n),account_type:type,normal_balance:normal});
await insert('erp.cash_accounts',{id:id(105),coa_account_id:id(103)});
await insert('erp.sales_items',{id:id(110),sale_id:id(2),line_total:'500.00'});
await insert('erp.journal_entries',{id:id(111),source_type:'SALE',source_id:id(2),status:'POSTED',economic_date:'2026-10-19',transaction_date:'2026-10-19',posting_at:'2026-10-19T01:00:00Z'});
for(const[n,a,d,c]of[[112,102,'500.00','0.00'],[113,104,'0.00','500.00']])await insert('erp.journal_lines',{id:id(n),journal_entry_id:id(111),account_id:id(a),customer_id:a===102?id(1):null,description:'Synthetic Native-shaped SALE source only',debit:d,credit:c});
await insert('cp7_credit.return_families',{id:id(8),family_root_sale_id:id(1)});
await insert('cp7_credit.cohorts',{id:id(9),family_id:id(8),source_sale_id:id(1),customer_id:id(1),credit_account_id:id(101),initial_plan_id:id(7),initial_net_amount:'200.00'});
const ar=await json('select cp7_credit.consumer_invoice_ar_source_v1($1)as v',[id(2)]);assert.equal(ar.account_id,id(102));checks.push('TARGET_AR_DERIVED_FROM_ACTUAL_SALE_WITHOUT_CURRENT_MAPPING');
const cash={cash:{id:id(105),coa_account_id:id(103)},account:{id:id(103)}};
const opBase={actor:id(200),actor_app_user_id:id(201),cohort_id:id(9),customer_id:id(1),source_sale_id:id(1),source_root_sale_id:id(1),source_current_leaf_id:id(1),credit_account_id:id(101),physical_at:'2026-10-20T10:00:00+07:00',economic_date:'2026-10-20',transaction_date:'2026-10-20',reason:'Synthetic consumer factual validation control',reference:null,quote_sha256:'0'.repeat(64),source_graph:{synthetic:true},locked_sources:{synthetic:true},projection:{synthetic:true},period_snapshot:{synthetic:true},book_manifest:{synthetic:true},authority_snapshot:{synthetic:true},credit_account_snapshot:{account:{id:id(101)}},before_native:{synthetic:true},recorded_at:'2026-10-20T03:00:00Z'};
for(const k of ['source_graph','locked_sources','projection'])opBase[k+'_sha256']=await sha(opBase[k]);
async function event(n,action,kind,amount,original=null,overrides={}){
 const payload={action,amount,original},request=id(1000+n),op={...opBase,id:id(n),request_id:request,action,event_kind:kind,amount,restores_event_id:original===null?null:id(original),payload_sha256:await sha(payload),target_sale_id:kind==='APPLY'?id(2):null,target_root_sale_id:kind==='APPLY'?id(2):null,target_current_leaf_id:kind==='APPLY'?id(2):null,target_ar_account_id:kind==='APPLY'?id(102):null,target_ar_snapshot:kind==='APPLY'?ar:null,cash_account_id:kind==='REFUND'?id(105):null,cash_coa_account_id:kind==='REFUND'?id(103):null,cash_account_snapshot:kind==='REFUND'?cash:null,...overrides};
 await insert('cp7_credit.consumer_requests_v1',{actor:op.actor,request_id:request,action,payload,expected_versions:{synthetic:true}});
 await insert('cp7_credit.consumer_operations_v1',op);
 const lines=await json('select cp7_credit.consumer_operation_lines_v1($1)as v',[id(n)]),journal=id(2000+n);
 await insert('erp.journal_entries',{id:journal,source_type:action==='UNDO'?'CP7_CUSTOMER_CREDIT_EVENT_REVERSE':'CP7_CUSTOMER_CREDIT_'+kind,source_id:id(n),status:'POSTED',economic_date:op.economic_date,transaction_date:op.transaction_date,posting_at:op.recorded_at});
 for(const[k,l]of lines.entries())await insert('erp.journal_lines',{id:id(10000+n*10+k),journal_entry_id:journal,...l});
 const sorted=[...lines].sort((a,b)=>a.account_id.localeCompare(b.account_id));
 await insert('cp7_credit.consumption_events',{id:id(n),cohort_id:op.cohort_id,event_kind:kind,amount,economic_date:op.economic_date,transaction_date:op.transaction_date,target_sale_id:op.target_sale_id,cash_account_id:op.cash_account_id,restores_event_id:op.restores_event_id,journal_id:journal,source_sha256:await sha(op),lines_sha256_pg:await lineSha(sorted),actor:op.actor,request_id:request,reason:op.reason});
 // to_jsonb includes every nullable column and DB timestamp serialization.
 await db.query('update cp7_credit.consumption_events set source_sha256=cp7_credit.pg_jsonb_sha256(to_jsonb(o))from cp7_credit.consumer_operations_v1 o where consumption_events.id=o.id and o.id=$1',[id(n)]);
 try{assert.equal((await data(n)).actual_data_verified,true)}catch(e){
  const diagnostic=await one(`select current_setting('TimeZone')as zone,
   (ce.cohort_id,ce.event_kind,ce.amount,ce.target_sale_id,ce.cash_account_id,ce.restores_event_id,ce.actor,ce.request_id,ce.economic_date,ce.transaction_date,ce.reason)
   is not distinct from(o.cohort_id,o.event_kind,o.amount,o.target_sale_id,o.cash_account_id,o.restores_event_id,o.actor,o.request_id,o.economic_date,o.transaction_date,o.reason)as fields_equal,
   ce.source_sha256=cp7_credit.pg_jsonb_sha256(to_jsonb(o))as operation_hash_equal,
   o.source_graph_sha256=cp7_credit.pg_jsonb_sha256(o.source_graph)as graph_equal,
   o.locked_sources_sha256=cp7_credit.pg_jsonb_sha256(o.locked_sources)as locks_equal,
   o.projection_sha256=cp7_credit.pg_jsonb_sha256(o.projection)as projection_equal,
   o.credit_account_snapshot#>>'{account,id}'as account_snapshot,
   ce.source_sha256,cp7_credit.pg_jsonb_sha256(to_jsonb(o))as actual_operation_hash
   from cp7_credit.consumption_events ce join cp7_credit.consumer_operations_v1 o on o.id=ce.id where ce.id=$1`,[id(n)]);
  e.message+=' SYNTHETIC_DIAGNOSTIC '+JSON.stringify(diagnostic);throw e;
 }return op;
}
await event(20,'APPLY','APPLY','80.00');checks.push('ACTUAL_80_EVENT_AND_EXACT_LIABILITY_AR_LINES_MATCH');
await event(21,'APPLY','APPLY','120.00');checks.push('SECOND_120_IS_ANOTHER_RETAINED_EVENT');
await event(22,'UNDO','APPLY','-80.00',20);checks.push('NAMED_UNDO_VALIDATES_EXACT_POSITIVE_ORIGINAL');
let incoming=await json('select cp7_credit.consumer_incoming_funding_v1($1)as v',[id(2)]);assert.deepEqual(incoming.map(x=>x.amount).sort(),['-80.00','120.00','80.00']);assert.equal(incoming.every(x=>x.kind==='FUNDING'),true);checks.push('INCOMING_FUNDING_RETAINS_BOTH_POSITIVE_AND_NEGATIVE_HISTORY');
assert.deepEqual(await json('select cp7_credit.consumer_incoming_funding_v1($1)as v',[id(3)]),[]);checks.push('UNRELATED_SAME_CUSTOMER_INVOICE_HAS_NO_INCOMING_U');
await event(23,'UNDO','APPLY','-120.00',21);await event(24,'REFUND','REFUND','50.00');await event(25,'UNDO','REFUND','-50.00',24);checks.push('EXACT_CASH_REFUND_AND_NAMED_REFUND_UNDO_DATA_MATCH');
await insert('cp7_credit.return_families',{id:id(30),family_root_sale_id:id(1)});
await insert('cp7_credit.recognition_plans',{id:id(32)});
await insert('cp7_credit.cohorts',{id:id(31),family_id:id(30),source_sale_id:id(1),customer_id:id(1),credit_account_id:id(101),initial_plan_id:id(32),initial_net_amount:'200.00'});
const initial={id:id(34),cohort_id:id(31),initial_plan_id:id(32),actor:id(200),request_id:id(1034),backend_pid:1,transaction_id:1,root_sale_id:id(1),current_leaf_id:id(1),full_amount:'200.00',cash_account_id:id(105),physical_at:opBase.physical_at,reason:opBase.reason,required_book_floor:'2026-10-20',book_floor_manifest:{synthetic:true},materialization_ordinal:2,authority_snapshot:{synthetic:true},cash_account_snapshot:cash};
for(const k of ['payload_sha256','quote_sha256','source_lock_sha256','projection_sha256','recognition_manifest_sha256'])initial[k]='0'.repeat(64);
await insert('cp7_credit.initial_refund_operations',initial);await insert('cp7_credit.initial_return_materializations',{operation_id:id(33),refund_operation_id:id(34),cohort_id:id(31),projection:{refund_book_plan:initial.book_floor_manifest}});
await insert('erp.journal_entries',{id:id(2034),source_type:'CP7_CUSTOMER_CREDIT_REFUND',source_id:id(34),status:'POSTED',economic_date:'2026-10-20',transaction_date:'2026-10-20',posting_at:opBase.recorded_at});
const initialLines=await json('select cp7_credit.initial_refund_lines($1,$2,$3,200)as v',[id(101),id(103),id(1)]);
for(const[k,l]of initialLines.entries())await insert('erp.journal_lines',{id:id(10340+k),journal_entry_id:id(2034),...l});
const initialHash=(await one('select cp7_credit.pg_jsonb_sha256(to_jsonb(o))as h from cp7_credit.initial_refund_operations o where id=$1',[id(34)])).h;
await insert('cp7_credit.consumption_events',{id:id(34),cohort_id:id(31),event_kind:'REFUND',amount:'200.00',economic_date:'2026-10-20',transaction_date:'2026-10-20',cash_account_id:id(105),journal_id:id(2034),source_sha256:initialHash,lines_sha256_pg:await lineSha(initialLines.sort((a,b)=>a.account_id.localeCompare(b.account_id))),actor:id(200),request_id:id(1034),reason:opBase.reason});
assert.equal((await data(34)).operation_origin,'INITIAL_REFUND');checks.push('RETAINED_INITIAL_REFUND_DATA_USES_ORIGINAL_PRIVATE_VERIFIER');
await event(35,'UNDO','REFUND','-200.00',34,{cohort_id:id(31)});assert.equal((await data(34)).actual_data_verified,true);checks.push('NAMED_UNDO_OF_ORIGINAL_INITIAL_REFUND_PRESERVES_ITS_DATA');
assert.deepEqual(await json('select cp7_credit.consumer_active_events_v1($1)as v',[id(9)]),[]);assert.deepEqual(await json('select cp7_credit.consumer_active_events_v1($1)as v',[id(31)]),[]);checks.push('ALL_EXACTLY_UNDONE_USES_HAVE_NO_ACTIVE_BLOCKER_AND_RETAIN_HISTORY');
await event(26,'APPLY','APPLY','80.00');assert.deepEqual((await json('select cp7_credit.consumer_active_events_v1($1)as v',[id(9)])).map(x=>x.id),[id(26)]);checks.push('NEW_UNDONELESS_POSITIVE_REMAINS_AN_ACTIVE_BLOCKER');
for(const[name,sql,p,re]of[
 ['EVENT_ACTOR',"update cp7_credit.consumption_events set actor=$1 where id=$2",[id(999),id(20)],/OPERATION_DATA_CHANGED/],
 ['EVENT_AMOUNT',"update cp7_credit.consumption_events set amount='80.01'where id=$1",[id(20)],/OPERATION_DATA_CHANGED/],
 ['EVENT_SOURCE_HASH',"update cp7_credit.consumption_events set source_sha256=repeat('0',64)where id=$1",[id(20)],/OPERATION_DATA_CHANGED/],
 ['WRONG_CUSTOMER_LINE',"update erp.journal_lines set customer_id=$1 where journal_entry_id=$2",[id(999),id(2020)],/ACTUAL_LINES_CHANGED/],
 ['EXTRA_DIMENSION',"update erp.journal_lines set product_id=$1 where journal_entry_id=$2",[id(999),id(2020)],/ACTUAL_JOURNAL_CHANGED/],
 ['ONE_CENT_LINE',"update erp.journal_lines set debit=debit+0.01 where journal_entry_id=$1",[id(2020)],/ACTUAL_LINES_CHANGED/],
 ['WRONG_SOURCE_TYPE',"update erp.journal_entries set source_type='SALES_PAYMENT'where id=$1",[id(2020)],/ACTUAL_JOURNAL_CHANGED/],
 ['MISSING_LEG',"delete from erp.journal_lines where id=$1",[id(10200)],/ACTUAL_JOURNAL_CHANGED/],
 ['UNLINKED_NATIVE_REVERSE',"insert into erp.journal_entries(id,source_type,source_id,reversal_of_id)values($1,'JOURNAL_REVERSAL',$2,$2)",[id(999),id(2020)],/ACTUAL_JOURNAL_CHANGED/],
 ['SOURCE_CROSS_CUSTOMER',"update erp.sales_headers set customer_id=$1 where id=$2",[id(999),id(1)],/SOURCE_ROOT_CHANGED/],
 ['TARGET_SALE_AR_CHANGED',"update erp.journal_lines set account_id=$1 where id=$2",[id(103),id(112)],/query returned no rows|TARGET_DATA_CHANGED/]
]){await corrupt(sql,p,re);checks.push(name+'_REFUSED')}
await corrupt("update cp7_credit.consumption_events set restores_event_id=$1 where id=$2",[id(26),id(22)],/OPERATION_DATA_CHANGED/,22);checks.push('DIFFERENT_NAMED_ORIGINAL_REFUSED');
await corrupt("update cp7_credit.consumer_operations_v1 set source_graph_sha256=repeat('0',64)where id=$1",[id(20)],/OPERATION_DATA_CHANGED/);checks.push('CHANGED_STORED_SOURCE_VECTOR_REFUSED');
// An old operation remains factual after a later lawful header/leaf status.
await db.exec('begin');try{await db.query("update erp.sales_headers set status='REVERSED'where id=$1",[id(2)]);await db.query('insert into cp7_note.revisions values($1,$1,$2,1)',[id(2),id(3)]);assert.equal((await data(20)).actual_data_verified,true)}finally{await db.exec('rollback')}checks.push('HISTORICAL_OPERATION_DOES_NOT_REQUIRE_OLD_LEAF_TO_STILL_BE_CURRENT');
await refuse(()=>json('select cp7_credit.consumer_active_events_v1($1)as v',[id(999)]),/query returned no rows/);checks.push('UNKNOWN_COHORT_CANNOT_BECOME_ZERO_ACTIVE_USE');
const meta=await rows("select oid::regprocedure::text as signature,provolatile from pg_proc where pronamespace='cp7_credit'::regnamespace and proname in('consumer_invoice_ar_source_v1','consumer_operation_lines_v1','consumer_event_data_v1','consumer_incoming_funding_v1','consumer_active_events_v1')");assert.equal(meta.length,5);assert.ok(meta.every(x=>x.provolatile==='s'));
for(const role of ['anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write'])for(const f of meta)assert.equal((await one('select has_function_privilege($1,$2,\'EXECUTE\')as allowed',[role,f.signature])).allowed,false);checks.push('ALL_FIVE_STABLE_FUNCTIONS_DENY_OUTSIDER_AND_OUTER_EXECUTE');
console.log(JSON.stringify({classification:'LOCAL_PGLITE_EXTRACTED_REAL_CONSUMER_DDL_EVENT_DATA_AND_PURE_REQUEST_SHAPE_WITH_SYNTHETIC_NATIVE_SHAPED_LEDGER_NOT_NATIVE_EXECUTION',status:'PASS',check_count:checks.length,checks,pure_payload_check_count:accessChecks.length,pure_payload_checks:accessChecks,owning_command_executed:false,initial_refund_adapter_executed:true,source_authority_proven:false,complete_financial_operation_proven:false,consumer_command_implemented:false,Native_cases_added:0,production_go:false}));
}catch(e){console.error(JSON.stringify({status:'FAIL_LOCAL_CONTROL',checks_completed:checks,error:e.message,query:e.query?.slice(0,300)}));process.exitCode=1}finally{await db.close()}
