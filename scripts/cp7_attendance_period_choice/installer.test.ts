// @vitest-environment node
// Local PostgreSQL role/DDL causality only; zero actual Native/Auth/hosted credit.
import {beforeAll,afterAll,beforeEach,afterEach,expect,test} from 'vitest'
import {readFileSync,writeFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'
import {execFileSync} from 'node:child_process'

const HERE=resolve('scripts/cp7_attendance_period_choice')
const OUTER='s03_local_qualified_outer'
const schemas=['cp7_hpp_pool','cp7_payroll']
const signatures=['cp7_payroll.apply_settlement(text,jsonb,text)','cp7_hpp_pool.preview(date,date,date)','cp7_hpp_pool.pool_json(erp.attendance_hpp_pools,date)']
const heads=['cp7_payroll.apply_settlement(p_action text,p_payload jsonb,p_expected text)','cp7_hpp_pool.preview(p_start date,p_end date,p_closed date)','cp7_hpp_pool.pool_json(p_pool erp.attendance_hpp_pools,p_closed date)']
const definition=(head:string,value='original')=>`create or replace function ${head}returns jsonb language sql security definer set search_path=''as $$select jsonb_build_object('LOCAL_ROLE_DDL_DOUBLE','${value}')$$`
const python=String.raw`import json,sys
sys.dont_write_bytecode=True;sys.path.insert(0,'scripts')
from cp7_attendance_period_choice import installer_ddl as d
if sys.argv[1]=='inventory':print(d.INVENTORY_SQL)
else:print(json.dumps(d.plan_inventory(json.load(sys.stdin))))`
const inventorySql=execFileSync('python',['-B','-c',python,'inventory'],{encoding:'utf8'}).trim()
const queries=JSON.parse(execFileSync('python',['-B',resolve(HERE,'local_catalog.py')],{encoding:'utf8'}))
let db:any
const observations:any[]=[]
const q=(sql:string,args:unknown[]=[])=>db.query(sql,args)
const exec=(sql:string)=>db.exec(sql)
const first=async(sql:string,args:unknown[]=[])=>Object.values((await q(sql,args)).rows[0])[0] as any
function placeholders(statement:string){let n=0;return statement.replaceAll('%s',()=>'$'+(++n))}
async function inventory(){return(await q(placeholders(inventorySql),[schemas])).rows}
function plan(rows:any[]){return JSON.parse(execFileSync('python',['-B','-c',python,'plan'],{input:JSON.stringify(rows),encoding:'utf8'}))}
async function steps(list:[string,unknown[]][]){for(const[statement,args]of list)await q(placeholders(statement),args)}
async function catalog(){
 const role=await first('show role'),path=await first('show search_path'),zone=await first('show TimeZone')
 await exec(`set local role ${OUTER}`);await q("select set_config('search_path','',true),set_config('TimeZone','UTC',true)")
 try{
  const result:Record<string,unknown>={}
  for(const[group,query]of Object.entries(queries)){
   const rows=(await q(query as string)).rows.map((row:any)=>Object.values(row));result[group]=Object.fromEntries(rows as any)
   expect(Object.keys(result[group]as object)).toHaveLength(rows.length)
  }
  return result
 }finally{await q("select set_config('search_path',$1,true),set_config('TimeZone',$2,true),set_config('role',$3,true)",[path,zone,role])}
}
async function data(){
 const role=await first('show role');await exec(`set local role ${OUTER}`)
 try{
  return{rows:(await q('select id::text,note from erp.s03_local_ddl_rows order by id')).rows,
   sequence:await first('select jsonb_build_array(last_value::text,is_called)from erp.s03_local_ddl_seq')}
 }finally{await q("select set_config('role',$1,true)",[role])}
}
async function snapshot(){return{catalog:await catalog(),inventory:await inventory(),data:await data()}}

beforeAll(async()=>{
 const module=process.env.CP7_S03_PGLITE_MODULE??resolve('../test-runtime/node_modules/@electric-sql/pglite/dist/index.js')
 const{PGlite}=await import(/* @vite-ignore */pathToFileURL(module).href);db=new PGlite()
 // Explicit local administrative role fixture. Rename the immutable bootstrap
 // role to create a literal non-SU postgres, with the qualified outer SU as
 // session_user. This is not a claim about actual9a0's unrecorded role catalog.
 await exec(`create role ${OUTER} superuser login;set session authorization ${OUTER};
 alter role postgres rename to s03_local_original_bootstrap;
 create role postgres nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
 create role cp7_payroll_read nologin noinherit nosuperuser nocreatedb nocreaterole;
 create role cp7_hpp_pool_read nologin noinherit nosuperuser nocreatedb nocreaterole;
 create schema erp;grant usage on schema erp to postgres;
 create table erp.attendance_hpp_pools(id uuid primary key);
 create table erp.s03_local_ddl_rows(id uuid primary key,note text);
 grant insert on erp.s03_local_ddl_rows to postgres;
 insert into erp.s03_local_ddl_rows values('00000000-0000-0000-0000-000000000001','preexisting exact row');
 create sequence erp.s03_local_ddl_seq;
 create schema cp7_payroll authorization cp7_payroll_read;create schema cp7_hpp_pool authorization cp7_hpp_pool_read;
 revoke all on schema cp7_payroll,cp7_hpp_pool from public;grant usage on schema cp7_payroll,cp7_hpp_pool to postgres;`)
 for(let i=0;i<heads.length;i++){
  await exec(definition(heads[i]));await exec(`alter function ${signatures[i]}owner to postgres;revoke all on function ${signatures[i]}from public;`)
 }
},30_000)
afterAll(async()=>{
 if(observations.length)writeFileSync('/tmp/s03-installer-role-observations.json',JSON.stringify({classification:'LOCAL_LITERAL_NON_SU_POSTGRES_AND_SESSION_SU_DDL_MODEL_NOT_ACTUAL_NATIVE_AUTH',
  actual_Native_financial_cases:0,external_DB_calls:0,source_generated_plan:true,observations},null,2))
 await db?.close()
},30_000)
beforeEach(async()=>{await exec('begin;set local role postgres;')})
afterEach(async()=>{await exec('rollback;')})

test('literal function owner postgres with USAGE but no CREATE reproduces42501 on BOTH real private schemas',async()=>{
 const before=await snapshot()
 expect(before.inventory).toHaveLength(2)
 for(const row of before.inventory){
  expect(row.actor).toBe('postgres');expect(row.actor_superuser).toBe(false);expect(row.session_superuser).toBe(true)
  expect(row.usage).toBe(true);expect(row.create).toBe(false);expect(row.actor_can_set_owner).toBe(false);expect(row.session_can_set_owner).toBe(true)
 }
 const failures=[]
 for(let i=0;i<heads.length;i++){
  await exec('savepoint missing_schema_create')
  let error:any
  try{await exec(definition(heads[i],'refused_without_create'))}catch(e){error=e}
  await exec('rollback to savepoint missing_schema_create;release savepoint missing_schema_create;')
  expect(error?.code).toBe('42501');expect(error?.message).toBe('permission denied for schema '+signatures[i].split('.')[0])
  failures.push({signature:signatures[i],sqlstate:error.code,message:error.message})
 }
 expect(await snapshot()).toEqual(before)
 observations.push({id:'LITERAL_NS_POSTGRES_FIRST_REPRO_BOTH_SCHEMAS',failures,inventory:before.inventory,full22_rawACL_rows_sequences_equal:true})
})

test('actual source-generated temporary CREATE plan permits replacement then restores exact all22/rawACL/rows/sequences',async()=>{
 const before=await snapshot(),p=plan(before.inventory)
 expect(p.temporary_CREATE_schemas).toEqual(schemas)
 await steps(p.enter)
 for(const row of await inventory()){expect(row.actor).toBe('postgres');expect(row.create).toBe(true);expect(row.usage).toBe(true)}
 // Replacing identical definitions proves permission without introducing an
 // unrelated expected catalog delta in this authority-conservation control.
 for(const head of heads)await exec(definition(head))
 await steps(p.leave)
 expect(await snapshot()).toEqual(before)
 observations.push({id:'SOURCE_PLAN_SUCCESS_RESTORES_FULL22_RAW_ACL_AND_DATA',temporary_CREATE_schemas:p.temporary_CREATE_schemas,full22_equal:true,all_rows_sequences_equal:true})
})

test('late SQL error under owning atomic savepoint restores grants/bodies/role/all22 and data without cleanup SQL in aborted state',async()=>{
 const before=await snapshot(),p=plan(before.inventory)
 await exec('savepoint owning_atomic')
 let error:any
 try{
  await steps(p.enter);await exec(definition(heads[0],'would_change_but_rolls_back'))
  await exec("insert into erp.s03_local_ddl_rows values('00000000-0000-0000-0000-000000000002','must rollback')")
  await exec('select 1/0')
 }catch(e){error=e;await exec('rollback to savepoint owning_atomic;release savepoint owning_atomic;')}
 expect(error?.code).toBe('22012');expect(await snapshot()).toEqual(before)
 observations.push({id:'SQL_ERROR_OUTER_ATOMIC_RESTORES_EVERYTHING',sqlstate:error.code,full22_equal:true,rawACL_equal:true,rows_sequences_equal:true,no_manual_catalog_write:true})
})

test('preexisting CREATE is neither revoked nor normalized',async()=>{
 await exec('set local role cp7_payroll_read;grant create on schema cp7_payroll to postgres;set local role cp7_hpp_pool_read;grant create on schema cp7_hpp_pool to postgres;set local role postgres;')
 const before=await snapshot(),p=plan(before.inventory)
 expect(p.enter).toEqual([]);expect(p.leave).toEqual([])
 for(const head of heads)await exec(definition(head))
 expect(await snapshot()).toEqual(before)
 observations.push({id:'PREEXISTING_CREATE_NO_OP',full22_equal:true,rawACL_equal:true})
})

test('raw NULL schema ACL is preserved on no-op path and a NULL grant attempt is rejected before DDL',async()=>{
 await exec(`set local role ${OUTER};drop schema cp7_payroll,cp7_hpp_pool cascade;
 create schema cp7_payroll authorization cp7_payroll_read;create schema cp7_hpp_pool authorization cp7_hpp_pool_read;
 alter role postgres superuser;set local role postgres;`)
 const before=await snapshot();expect(before.inventory.every((row:any)=>row.raw_acl===null&&row.create&&row.usage)).toBe(true)
 const p=plan(before.inventory);expect(p.enter).toEqual([]);expect(p.leave).toEqual([]);expect(await snapshot()).toEqual(before)
 // This impossible-in-the-source permission combination is an explicit local
 // malformed-inventory control; it must never normalize raw NULL via GRANT.
 const malformed=before.inventory.map((row:any)=>({...row,create:false,actor_superuser:false}))
 expect(()=>plan(malformed)).toThrow(/RAW_NULL_GRANT_NOT_ADMITTED/)
 observations.push({id:'RAW_NULL_NO_OP_AND_UNADMITTED_NULL_GRANT',actual_raw_null_preserved:true,malformed_profile_refused:true})
})
