import {readFileSync}from'node:fs';
import assert from'node:assert/strict';
// Local synthetic graph controls only. No connection or financial writer.
const{PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const leafSource=readFileSync(new URL('../readers/01_current_reader_capability.proposal.sql',import.meta.url),'utf8');
const ledgerSource=readFileSync(new URL('../ledger/01_immutable_facts.proposal.sql',import.meta.url),'utf8');
const graphSource=readFileSync(new URL('01_dependency_graph.sql',import.meta.url),'utf8');
const input={
 leaf:'create function cp7_credit.current_leaf_assignment'+leafSource.split('create function cp7_credit.current_leaf_assignment')[1].split('-- REQUIRED integration interface')[0],
 sha:'create function cp7_credit.pg_jsonb_sha256'+ledgerSource.split('create function cp7_credit.pg_jsonb_sha256')[1].split('-- Same PG jsonb')[0],
 graph:graphSource.replace(/do \$not_an_installer\$begin[\s\S]*?end \$not_an_installer\$;/,'')
};
const db=new PGlite();const uuid=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const A=uuid(1),A2=uuid(2),B=uuid(3),C=uuid(4),D=uuid(5),E=uuid(6),B2=uuid(7),customer=uuid(90),other=uuid(91);
const checks=[];
async function graph(id){return(await db.query('select cp7_credit.consumer_dependency_graph_v1($1::uuid) as result',[id])).rows[0].result}
async function refuse(sql,args,expected){try{await db.query(sql,args)}catch(e){assert.match(e.message,expected);return}throw Error('Expected refusal '+sql)}
try{
await db.exec(`create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;
create schema erp;create schema cp7_note;create schema cp7_credit;
create table erp.sales_headers(id uuid primary key,customer_id uuid not null,status text not null,row_version bigint default 1);
create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid,revision bigint);
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid,family_ordinal bigint);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid,source_sale_id uuid,customer_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,cohort_id uuid,event_kind text,amount numeric,target_sale_id uuid,restores_event_id uuid);`);
await db.exec(input.sha);await db.exec(input.leaf);await db.exec(input.graph);
for(const[id,cust,status]of[[A,customer,'REVERSED'],[A2,customer,'POSTED'],[B,customer,'POSTED'],[C,customer,'POSTED'],[D,customer,'POSTED'],[E,other,'POSTED']])await db.query('insert into erp.sales_headers(id,customer_id,status)values($1,$2,$3)',[id,cust,status]);
await db.query('insert into cp7_note.revisions values($1,$1,$2,1)',[A,A2]);
for(const[n,root]of[[1,A],[2,B],[3,C],[4,D]]){
 await db.query('insert into cp7_credit.return_families values($1,$2,1)',[uuid(10+n),root]);
 await db.query('insert into cp7_credit.cohorts values($1,$2,$3,$4)',[uuid(20+n),uuid(10+n),root,customer]);
}
for(const[n,cohort,kind,amount,target,restores]of[[1,21,'APPLY','80.00',B,null],[2,22,'APPLY','40.00',C,null],[3,23,'APPLY','20.00',A2,null],[4,21,'APPLY','-80.00',B,uuid(31)],[5,21,'REFUND','10.00',null,null]])await db.query('insert into cp7_credit.consumption_events values($1,$2,$3,$4,$5,$6)',[uuid(30+n),uuid(cohort),kind,amount,target,restores]);
let a=await graph(A2),b=await graph(B);
assert.deepEqual(a.sale_ids,[A,A2,B,C]);assert.deepEqual(a.root_sale_ids,[A,B,C]);assert.equal(a.facts.consumptions.length,5);assert.equal(a.source_authority_proven,false);checks.push('BIDIRECTIONAL_CYCLE_TERMINATES_WITH_ALL_MEMBERS');
assert.equal(a.facts_sha256,b.facts_sha256);checks.push('CONNECTED_START_NODES_HAVE_IDENTICAL_FACT_CAPTURE');
assert.ok(a.facts.consumptions.some(x=>x.amount<0));assert.ok(a.facts.consumptions.some(x=>x.event_kind==='REFUND'));checks.push('SIGNED_UNDO_AND_REFUND_HISTORY_RETAINED');
await db.query('delete from cp7_credit.consumption_events where id in($1,$2)',[uuid(32),uuid(33)]);
a=await graph(A2);assert.deepEqual(a.root_sale_ids,[A,B]);assert.equal(a.facts.consumptions.length,3);checks.push('FULLY_UNDONE_APPLICATION_REMAINS_A_DEPENDENCY');
await db.query("update erp.sales_headers set status='REVERSED'where id=$1",[B]);await db.query("insert into erp.sales_headers(id,customer_id,status)values($1,$2,'POSTED')",[B2,customer]);await db.query('insert into cp7_note.revisions values($1,$1,$2,1)',[B,B2]);
a=await graph(A2);assert.deepEqual(a.current_leaf_ids,[A2,B2]);assert.ok(a.sale_ids.includes(B));assert.ok(a.sale_ids.includes(B2));checks.push('HISTORICAL_TARGET_AND_CORRECTED_LEAF_BOTH_INCLUDED');
const isolated=await graph(D);assert.deepEqual(isolated.sale_ids,[D]);assert.equal(isolated.cohort_ids.length,1);assert.equal(isolated.facts.consumptions.length,0);checks.push('ISOLATED_INVOICE_HAS_ONLY_ITS_ACTUAL_COHORT');
await db.query("insert into cp7_credit.consumption_events values($1,$2,'APPLY',1,$3,null)",[uuid(36),uuid(21),E]);await refuse('select cp7_credit.consumer_dependency_graph_v1($1)',[A2],/CONSUMER_GRAPH_CUSTOMER_CHANGED/);await db.query('delete from cp7_credit.consumption_events where id=$1',[uuid(36)]);checks.push('CROSS_CUSTOMER_EDGE_REFUSED');
await db.query('update cp7_credit.cohorts set source_sale_id=$1 where id=$2',[D,uuid(21)]);await refuse('select cp7_credit.consumer_dependency_graph_v1($1)',[A2],/CONSUMER_GRAPH_COHORT_ROOT_CHANGED/);await db.query('update cp7_credit.cohorts set source_sale_id=$1 where id=$2',[A,uuid(21)]);checks.push('WRONG_COHORT_SOURCE_ROOT_REFUSED');
await refuse('select cp7_credit.consumer_dependency_graph_v1($1)',[uuid(999)],/no rows|no data/i);checks.push('UNKNOWN_DOCUMENT_REFUSED');
await db.exec('set role authenticated');await refuse('select cp7_credit.consumer_dependency_graph_v1($1)',[A2],/permission denied/);await db.exec('reset role');checks.push('AUTHENTICATED_CANNOT_EXECUTE_PRIVATE_GRAPH');
assert.equal(checks.length,10);
const result={classification:'LOCAL_PGLITE_SYNTHETIC_GRAPH_ONLY_NOT_NATIVE_OR_FINANCIAL_COMMAND',status:'PASS',check_count:checks.length,checks,full_owning_command_implemented:false,Native_cases_added:0,production_go:false};
console.log(JSON.stringify(result));
}finally{await db.close()}
