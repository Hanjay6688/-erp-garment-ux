import{readFileSync}from'node:fs';import assert from'node:assert/strict';
const{PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const source=readFileSync(new URL('cp7_ow04_consumer_fixture.py',import.meta.url),'utf8');
const section=source.split('def _document_ar(')[1].split('def profiles(')[0];
const matches=[...section.matchAll(/return cur\.execute\("""([\s\S]*?)""",/g)];
assert.equal(matches.length,1);let parameters=0;
const query=matches[0][1].replace(/%s/g,()=>'$'+(++parameters));
assert.equal(parameters,7);
const db=new PGlite();const checks=[];
try{
await db.exec(`create schema erp;create schema cp7_credit;
create table erp.journal_entries(id text,source_type text,source_id text,reversal_of_id text,status text default 'POSTED');
create table erp.journal_lines(journal_entry_id text,customer_id text,account_id text,debit numeric,credit numeric);
create table erp.sales_payments(id text,sale_id text);create table erp.sales_returns(id text,sale_id text);
create table cp7_credit.component_journals(part_id text,journal_id text);create table cp7_credit.component_parts(id text,component_id text);
create table cp7_credit.recognition_components(id text,plan_id text);create table cp7_credit.recognition_plans(id text,cohort_id text);
create table cp7_credit.cohorts(id text,family_id text);create table cp7_credit.return_families(id text,family_root_sale_id text);
create table cp7_credit.consumption_events(journal_id text,event_kind text,target_sale_id text);`);
async function j(id,type,source,amount,parent=null){await db.query('insert into erp.journal_entries(id,source_type,source_id,reversal_of_id)values($1,$2,$3,$4)',[id,type,source,parent]);await db.query("insert into erp.journal_lines values($1,'same-customer','actual-AR',$2,$3)",[id,Math.max(amount,0),Math.max(-amount,0)]);}
async function ar(sale){return(await db.query(query,[sale,sale,sale,sale,sale,'same-customer','actual-AR'])).rows[0].coalesce;}
async function recognition(id,amount){await j('j'+id,'CP7_CUSTOMER_CREDIT_RECOGNITION',id,amount);await db.query('insert into cp7_credit.component_parts values($1,$2)',[id,'component']);await db.query('insert into cp7_credit.component_journals values($1,$2)',[id,'j'+id]);}
await db.exec("insert into erp.sales_payments values('payment','A');insert into erp.sales_returns values('return','A');insert into cp7_credit.return_families values('family','A');insert into cp7_credit.cohorts values('cohort','family');insert into cp7_credit.recognition_plans values('plan','cohort');insert into cp7_credit.recognition_components values('component','plan');");
await j('sale-A','SALE','A',1000);await j('payment-J','SALES_PAYMENT','payment',-1000);await j('return-J','SALES_RETURN','return',-200);await recognition('recognition',200);await j('sale-B','SALE','B',500);
assert.equal(await ar('A'),'0');assert.equal(await ar('B'),'500');checks.push('SEPARATE_SOURCE_ZERO_AND_TARGET500_SAME_CUSTOMER');
async function apply(id,amount){await j(id,amount>0?'CP7_CUSTOMER_CREDIT_APPLY':'CP7_CUSTOMER_CREDIT_EVENT_REVERSE',id,-amount);await db.query("insert into cp7_credit.consumption_events values($1,'APPLY','B')",[id]);}
await apply('apply80',80);assert.equal(await ar('A'),'0');assert.equal(await ar('B'),'420');checks.push('APPLY80_AFFECTS_ONLY_NAMED_TARGET_AR');
await apply('apply120',120);assert.equal(await ar('A'),'0');assert.equal(await ar('B'),'300');checks.push('SECOND_APPLY120_RETAINS_FIRST80');
await apply('undo80',-80);assert.equal(await ar('B'),'380');checks.push('LINKED_EVENT_REVERSE_NEGATIVE_USE_RESTORES_TARGET_AR');
await j('unrelated-sale','SALE','C',123);assert.equal(await ar('A'),'0');assert.equal(await ar('B'),'380');checks.push('UNRELATED_SAME_CUSTOMER_INVOICE_EXCLUDED');
await apply('undo120',-120);await db.exec("update erp.journal_entries set status='REVERSED'where id='return-J'");await j('return-inverse','JOURNAL_REVERSAL','return-J',200,'return-J');await recognition('negative-recognition',-200);
assert.equal(await ar('A'),'0');assert.equal(await ar('B'),'500');checks.push('NATIVE_RETURN_INVERSE_AND_SIGNED_RECOGNITION_RETAINED_ONCE');
const result={classification:'LOCAL_PGLITE_SYNTHETIC_LEDGER_FOR_EXACT_FIXTURE_QUERY_ONLY_NOT_NATIVE_BUSINESS_EXECUTION',status:'PASS',check_count:checks.length,checks,consumer_prepare_executed:false,consumer_command_implemented:false,Native_cases_added:0,production_go:false};
assert.equal(checks.length,6);console.log(JSON.stringify(result));
}finally{await db.close()}
