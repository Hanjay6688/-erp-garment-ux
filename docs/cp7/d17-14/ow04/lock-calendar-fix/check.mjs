// Exact new owner-bound lock SQL and accepted Native date resolver, isolated.
import fs from'node:fs/promises';import{execFileSync}from'node:child_process';import assert from'node:assert/strict';
import{fileURLToPath}from'node:url';import path from'node:path';
const{PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const root=process.env.ERP_REPO||process.cwd(),out=path.dirname(fileURLToPath(import.meta.url));
const emitted=JSON.parse(execFileSync('python',['-B','-c',`import sys,json,gzip;from pathlib import Path;sys.path.insert(0,'scripts');from cp7_customer_credit.integration import owning_bundle as b;x=json.loads(gzip.decompress(Path('docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz').read_bytes()));print(json.dumps({'lock':b.PAYMENT_LINK_LOCK_SQL,'native':[a['definition']for a in x['functions']if a['schema']=='erp'and a['name']in('_cp3_business_date','resolve_accounting_transaction_date')]}))`],{cwd:root,encoding:'utf8'}));
const db=new PGlite(),cases=[];const pass=name=>cases.push({name,status:'PASS'});
async function denied(name,q){await db.exec('savepoint refusal');let error;try{await db.exec(q)}catch(e){error=e}
 await db.exec('rollback to savepoint refusal;release savepoint refusal');assert(error,name);pass(name);}
try{
await db.exec(`create role isolated_reader nologin noinherit nosuperuser bypassrls;create role cp7_sales_write nologin noinherit;
create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;
create schema cp7_credit authorization isolated_reader;create schema cp7_payment_correction authorization cp7_sales_write;
create table cp7_payment_correction.links(original_id uuid primary key,replacement_id uuid not null);
alter table cp7_payment_correction.links owner to cp7_sales_write;alter table cp7_payment_correction.links enable row level security;
create policy denied on cp7_payment_correction.links for all using(false)with check(false);
insert into cp7_payment_correction.links values('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002');
grant usage on schema cp7_payment_correction to isolated_reader;grant select on cp7_payment_correction.links to isolated_reader;`);
const before=(await db.query("select relacl::text[]acl from pg_class where oid='cp7_payment_correction.links'::regclass")).rows;
await db.exec('begin;set local role isolated_reader');
await denied('FIRST_RED_SELECT_DOES_NOT_AUTHORIZE_FOR_SHARE',"select 1 from cp7_payment_correction.links for share");await db.exec('rollback');
// Only the role name is substituted because PGlite postgres is its immutable
// bootstrap superuser; the actual helper body and owning role stay unchanged.
await db.exec(emitted.lock.replace(/\bpostgres\b/g,'isolated_reader'));
await db.exec('begin;set local role isolated_reader');
await db.exec("select cp7_credit.lock_payment_correction_links(array['00000000-0000-0000-0000-000000000001'::uuid])");pass('ACTUAL_OWNER_HELPER_LOCKS_EXISTING_ROW');
await db.exec('select cp7_credit.lock_payment_correction_links(array[]::uuid[])');pass('EMPTY_SET_IS_VALID');
assert.equal((await db.query("select exists(select 1 from pg_locks where relation='cp7_payment_correction.links'::regclass and mode='RowShareLock'and granted)ok")).rows[0].ok,true);pass('REAL_RELATION_ROW_SHARE_LOCK_HELD');
await denied('CALLER_STILL_CANNOT_UPDATE_HISTORY',"update cp7_payment_correction.links set replacement_id=original_id");await db.exec('rollback');
assert.deepEqual((await db.query("select relacl::text[]acl from pg_class where oid='cp7_payment_correction.links'::regclass")).rows,before);pass('PREDECESSOR_TABLE_ACL_UNCHANGED');
assert.equal((await db.query("select has_schema_privilege('cp7_sales_write','cp7_credit','CREATE')ok")).rows[0].ok,false);pass('TEMPORARY_SCHEMA_CREATE_REVOKED');
await db.exec('create schema erp;create table erp.accounting_period_control(singleton_id int primary key,closed_through date)');
for(const q of emitted.native)await db.exec(q);
const dates=(await db.query("select erp._cp3_business_date(statement_timestamp())::text today,(erp._cp3_business_date(statement_timestamp())-7)::text old_d0,(erp._cp3_business_date(statement_timestamp())-4)::text old_d3")).rows[0];
await db.exec("insert into erp.accounting_period_control values(1,erp._cp3_business_date(statement_timestamp())-5)");
const old=(await db.query('select erp.resolve_accounting_transaction_date($1::date)::text d',[dates.old_d0])).rows[0].d;
assert.equal(old,dates.today);assert.notEqual(old,dates.old_d3);pass('ORIGINAL_MINUS7_FIXTURE_CONTRADICTS_ACCEPTED_NATIVE_RESOLVER');
await db.exec("update erp.accounting_period_control set closed_through=erp._cp3_business_date(statement_timestamp())-1");
assert.equal((await db.query("select erp.resolve_accounting_transaction_date(erp._cp3_business_date(statement_timestamp())-3)::text d")).rows[0].d,dates.today);pass('V2_CLOSED_EXPECTED_D3_EQUALS_LAWFUL_TODAY');
await db.exec("update erp.accounting_period_control set closed_through=erp._cp3_business_date(statement_timestamp())-5");
assert.equal((await db.query("select erp.resolve_accounting_transaction_date(erp._cp3_business_date(statement_timestamp())-1)=erp._cp3_business_date(statement_timestamp())-1 ok")).rows[0].ok,true);pass('REOPENED_RESOLVER_REMAINS_EARLIER_D2');
const result={classification:'ISOLATED_ACTUAL_PRIVATE_LOCK_SQL_AND_ACCEPTED_NATIVE_RESOLVER',status:'PASS',count:cases.length,cases,full_erp_native_settlement:false,role_name_substitution:'postgres->isolated_reader for lock-caller fixture only',financial_expected_changed:false};
await fs.writeFile(out+'/RESULT.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:'PASS',count:cases.length,full_erp_native_settlement:false}));
}catch(e){await fs.writeFile(out+'/FIRST_FAILURE.json',JSON.stringify({error:e.message,cases},null,2)+'\n');console.error(e.message);process.exitCode=1}finally{await db.close()}
