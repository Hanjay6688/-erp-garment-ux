// Isolated DDL/scalar-only proposal check. NO ERP Native definitions/writers,
// no grant/permission stubs, no source collector, no journal posting calls.
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const directory=dirname(fileURLToPath(import.meta.url));
const {PGlite}=await import(process.env.OW04_PGLITE_MODULE??'@electric-sql/pglite');
const sha=value=>createHash('sha256').update(value).digest('hex');
const expectedText=await readFile(resolve(directory,'HELPER_EXPECTED.json'),'utf8');
const expected=JSON.parse(expectedText);
const sourceNames=['01_immutable_facts.proposal.sql','02_uuid_poster.proposal.sql'];
const sources=await Promise.all(sourceNames.map(name=>readFile(resolve(directory,name),'utf8')));
const receipts=Object.fromEntries(sourceNames.map((name,i)=>[name,sha(sources[i])]));
const barrier=/do \$not_an_installer\$ begin\s*raise exception 'OW04_PROPOSAL_NOT_INSTALLABLE_WITHOUT_COMPLETE_FEATURE';\s*end \$not_an_installer\$;/g;
const result={scope:expected.scope,native_execution_proven:false,expected_sha256:sha(expectedText),source_sha256:receipts,cases:[]};
const db=new PGlite();
let step='synthetic_types';
try {
 // FK/composite type scaffolding ONLY. These deliberately have no ERP data,
 // Native writers, authorization functions, source locks or financial behavior.
 await db.exec(`
 create role anon;create role authenticated;create role service_role;
 create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;
 create schema erp;create schema auth;
 create table erp.sales_headers(id uuid primary key);
 create table erp.sales_returns(id uuid primary key,sale_id uuid,physical_at timestamptz);
 create table erp.customers(id uuid primary key);
 create table erp.chart_accounts(id uuid primary key);
 create table erp.cash_accounts(id uuid primary key);
 create table erp.journal_entries(id uuid primary key,source_type text,source_id uuid,
  economic_date date,transaction_date date,status text,reversal_of_id uuid);
 create table erp.journal_lines(id uuid primary key,journal_entry_id uuid,
  account_id uuid,customer_id uuid,debit numeric,credit numeric);
 `);
 for(let i=0;i<sources.length;i++){
  step=sourceNames[i];
  assert.equal([...sources[i].matchAll(barrier)].length,1,'install barrier absent or duplicated');
  await db.exec(sources[i].replace(barrier,'-- Isolated scalar/DDL check ONLY; barrier removed from this in-memory copy.'));
  result.cases.push({name:step,status:'DDL_CREATED_WITHOUT_AUTHORITY_STUBS'});
 }
 const scalar=async(q,args=[])=>(await db.query(q,args)).rows[0].value;
 for(const [input,want]of expected.accepted_cents){
  step=`accept_cent_${input}`;
  const got=await scalar('select cp7_credit.cent_text($1::cp7_credit.cent_amount)as value',[input]);
  assert.equal(got,want);result.cases.push({name:step,status:'PASS',observed:got});
 }
 for(const input of expected.refused_cents){
  step=`refuse_cent_${input}`;let caught;
  try{await scalar('select $1::cp7_credit.cent_amount as value',[input]);}catch(error){caught=error;}
  assert(caught,'fractional/nonfinite amount accepted');assert.equal(caught.code,'23514');
  result.cases.push({name:step,status:'EXPECTED_REFUSAL',sqlstate:caught.code});
 }
 step='native_typmod_counter';
 const rounded=await scalar("select '0.001'::numeric(20,2)::text as value");
 assert.equal(rounded,expected.native_typmod_counter);result.cases.push({name:step,status:'COUNTER_CONFIRMED',observed:rounded});
 step='native_cent_hash_idempotence';
 const lines=JSON.stringify([{account_id:'00000000-0000-0000-0000-000000000001',debit:200,credit:0},{account_id:'00000000-0000-0000-0000-000000000002',debit:0,credit:200}]);
 const idempotent=await scalar('select cp7_credit.native_lines_sha256($1::jsonb)=cp7_credit.native_lines_sha256(cp7_credit.native_cent_lines($1::jsonb))as value',[lines]);
 assert.equal(idempotent,expected.native_cent_hash_is_idempotent);result.cases.push({name:step,status:'PASS'});
 for(const sign of[1,-1]){
  step=sign>0?'positive_split':'negative_split';
  const parts=(await db.query(`select cp7_credit.cent_text((($1::numeric)*least(cp7_credit.native_journal_cent_max(),
   1999999999999999999.98::numeric-(n-1)*cp7_credit.native_journal_cent_max()))::cp7_credit.cent_amount)as amount
   from generate_series(1,2)n order by n`,[sign])).rows.map(x=>x.amount);
  assert.deepEqual(parts,expected[step]);result.cases.push({name:step,status:'PASS',observed:parts});
 }
 step='component_uuid_only_signature';
 const signatures=(await db.query("select oid::regprocedure::text as signature from pg_proc where pronamespace='cp7_credit'::regnamespace and proname='post_component'")).rows.map(x=>x.signature);
 assert.deepEqual(signatures,['cp7_credit.post_component(uuid)']);result.cases.push({name:step,status:'PASS',signatures});
 step='synthetic_ancestry_rows';
 const jid=n=>`00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
 const journals=[
  [1,'CP7_CUSTOMER_CREDIT_RECOGNITION',null,null],
  [2,'JOURNAL_REVERSAL',1,1],[3,'JOURNAL_REVERSAL',2,2],
  [4,'MISC',null,null],[5,'MISC',null,6],[6,'MISC',null,5],
  [7,'JOURNAL_REVERSAL',1,null],[8,'MISC',null,1],
 ];
 for(const[id,type,source,inverse]of journals)await db.query(
  'insert into erp.journal_entries(id,source_type,source_id,reversal_of_id)values($1,$2,$3,$4)',
  [jid(id),type,source===null?null:jid(source),inverse===null?null:jid(inverse)]);
 for(const[id,want]of expected.journal_protection){
  step=`journal_protection_${id}`;
  const got=await scalar('select cp7_credit.is_protected_journal($1::uuid)as value',[jid(id)]);
  assert.equal(got,want);result.cases.push({name:step,status:'PASS',observed:got});
 }
 step='no_native_or_authority_writers';
 const erpFunctions=await scalar("select count(*)::integer as value from pg_proc where pronamespace='erp'::regnamespace or pronamespace='auth'::regnamespace");
 assert.equal(erpFunctions,0);result.cases.push({name:step,status:'PASS'});
 result.status='PASS';
 await writeFile(resolve(directory,'HELPER_RESULT.json'),JSON.stringify(result,null,2)+'\n');
 process.stdout.write(JSON.stringify({scope:result.scope,status:result.status,cases:result.cases.length,native_execution_proven:false})+'\n');
}catch(error){
 const failure={...result,status:'FAIL',step,message:error.message,code:error.code};
 try{await writeFile(resolve(directory,'FIRST_HELPER_FAILURE.json'),JSON.stringify(failure,null,2)+'\n',{flag:'wx'});}catch(writeError){if(writeError.code!=='EEXIST')throw writeError;}
 process.stderr.write(JSON.stringify({scope:result.scope,step,message:error.message,code:error.code})+'\n');
 process.exitCode=1;
}finally{await db.close();}
