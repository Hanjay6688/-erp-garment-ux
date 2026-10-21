import{readFileSync}from'node:fs';import assert from'node:assert/strict';
const{PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const ledger=readFileSync(new URL('../ledger/01_immutable_facts.proposal.sql',import.meta.url),'utf8');
const facts=readFileSync(new URL('02_operation_facts.sql',import.meta.url),'utf8');
assert.equal((facts.match(/do \$not_an_installer\$/g)||[]).length,1);
const input={
 domain:'create domain cp7_credit.cent_amount'+ledger.split('create domain cp7_credit.cent_amount')[1].split('create function cp7_credit.cent_text')[0],
 immutable:'create function cp7_credit.immutable_fact()'+ledger.split('create function cp7_credit.immutable_fact()')[1].split('-- Register EVERY')[0],
 facts:facts.replace(/do \$not_an_installer\$begin[\s\S]*?end \$not_an_installer\$;/,'')
};
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');const db=new PGlite(),checks=[];
async function refuse(sql,params,reason){try{await db.query(sql,params)}catch(e){assert.match(e.message,reason);return}throw Error('Expected refusal '+sql)}
try{
await db.exec('create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;create role cp7_credit_write nologin noinherit nobypassrls;create schema erp;create schema cp7_credit;grant usage on schema cp7_credit to cp7_credit_write;');
for(const t of ['customers','sales_headers','cash_accounts','chart_accounts','journal_entries'])await db.exec(`create table erp.${t}(id uuid primary key)`);
for(const t of ['cohorts','consumption_events','financial_materializations'])await db.exec(`create table cp7_credit.${t}(id uuid primary key)`);
await db.exec(input.domain);await db.exec(input.immutable);await db.exec(input.facts);
const tables=['consumer_requests_v1','consumer_command_context_v1','consumer_operations_v1','consumer_posting_scope_v1','consumer_completions_v1'];
const metadata=(await db.query("select relname,relrowsecurity from pg_class where oid in(select c.oid from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_credit'and c.relname=any($1::text[]))",[tables])).rows;assert.equal(metadata.length,5);assert.ok(metadata.every(x=>x.relrowsecurity));checks.push('ALL_FIVE_TABLES_HAVE_RLS');
for(const role of ['anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'])for(const t of tables)assert.equal((await db.query("select has_table_privilege($1,$2,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')as permitted",[role,'cp7_credit.'+t])).rows[0].permitted,false);checks.push('ALL_OUTSIDER_TABLE_RIGHTS_DENIED');
for(const t of ['consumer_operations_v1','consumer_posting_scope_v1','consumer_completions_v1'])assert.equal((await db.query("select has_table_privilege('cp7_credit_write',$1,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')as permitted",['cp7_credit.'+t])).rows[0].permitted,false);checks.push('OUTER_WRITER_HAS_NO_FINANCIAL_FACT_DML');
for(const t of ['customers','sales_headers','cash_accounts','chart_accounts','journal_entries'])for(const n of [1,2,3])await db.query(`insert into erp.${t} values($1)`,[id(n)]);
for(const t of ['cohorts','consumption_events','financial_materializations'])await db.query(`insert into cp7_credit.${t} values($1)`,[id(1)]);
await db.query("insert into cp7_credit.consumer_requests_v1 values($1,$2,'APPLY','{}','{}',null),($1,$3,'APPLY','{}','{}',null)",[id(10),id(11),id(12)]);
const op={id:id(20),actor:id(10),actor_app_user_id:id(10),request_id:id(11),action:'APPLY',event_kind:'APPLY',cohort_id:id(1),customer_id:id(1),source_sale_id:id(1),source_root_sale_id:id(1),source_current_leaf_id:id(1),target_sale_id:id(2),target_root_sale_id:id(2),target_current_leaf_id:id(2),cash_account_id:null,credit_account_id:id(1),target_ar_account_id:id(2),cash_coa_account_id:null,amount:'80.00',restores_event_id:null,physical_at:'2026-10-21T10:00:00+07:00',economic_date:'2026-10-21',transaction_date:'2026-10-21',reason:'Synthetic table constraint control only',reference:null,recorded_at:'2026-10-21T03:00:00Z'};
for(const k of ['payload_sha256','quote_sha256','source_graph_sha256','locked_sources_sha256','projection_sha256'])op[k]='0'.repeat(64);
for(const k of ['source_graph','locked_sources','projection','period_snapshot','book_manifest','authority_snapshot','credit_account_snapshot','target_ar_snapshot','before_native'])op[k]={};op.cash_account_snapshot=null;
const insert='insert into cp7_credit.consumer_operations_v1 select(jsonb_populate_record(null::cp7_credit.consumer_operations_v1,$1::jsonb)).*';await db.query(insert,[JSON.stringify(op)]);checks.push('SYNTHETIC_COMPLETE_SHAPE_ACCEPTED_NOT_SOURCE_AUTHORITY');
for(const[name,changes]of[['ZERO_AMOUNT',{amount:'0.00'}],['SUBCENT_AMOUNT',{amount:'0.001'}],['NONFINITE_AMOUNT',{amount:'NaN'}],['WRONG_NEGATIVE_ACTION',{amount:'-80.00',restores_event_id:id(1)}],['UNDO_WITHOUT_ORIGINAL',{action:'UNDO',amount:'-80.00'}],['UNDO_WITH_POSITIVE_AMOUNT',{action:'UNDO',restores_event_id:id(1)}],['MISSING_TARGET',{target_sale_id:null}],['APPLY_WITH_CASH',{cash_account_id:id(1)}],['LIABILITY_AR_COLLISION',{target_ar_account_id:id(1)}],['BOOK_BEFORE_ECONOMIC',{transaction_date:'2026-10-20'}],['PHYSICAL_WIB_PAIR_MISMATCH',{economic_date:'2026-10-20'}]]){
 await refuse(insert,[JSON.stringify({...op,id:id(21),request_id:id(12),...changes})],/violates check constraint|violates check constraint for domain/);checks.push(name+'_REFUSED');
}
for(const statement of ["update cp7_credit.consumer_operations_v1 set reason='changed immutable record'","delete from cp7_credit.consumer_operations_v1","truncate cp7_credit.consumer_operations_v1 cascade"]){await refuse(statement,[],/CP7_CREDIT_HISTORY_IMMUTABLE/);}checks.push('POSTGRES_UPDATE_DELETE_TRUNCATE_OF_OPERATIONS_REFUSED');
await refuse(insert,[JSON.stringify({...op,id:id(22)})],/duplicate key/);checks.push('SECOND_OPERATION_FOR_SAME_ACTOR_UUID_REFUSED');
const result={classification:'LOCAL_PGLITE_PRIVATE_DDL_AND_SYNTHETIC_CONSTRAINTS_WITH_DUMMY_PROVENANCE_NOT_NATIVE_OR_SOURCE_PROOF',status:'PASS',check_count:checks.length,checks,financial_command_implemented:false,complete_deferred_closure_implemented:false,installer_loads_fragment:false,Native_cases_added:0,production_go:false};
assert.equal(checks.length,17);console.log(JSON.stringify(result));
}catch(e){console.error(JSON.stringify({status:"FAIL_LOCAL_CONTROL",error:e.message,query:e.query?.slice(0,200)}));process.exitCode=1;}finally{await db.close()}
