// Actual captured Native guard SQL on a narrow isolated PostgreSQL model.
// This is not an installed ERP, Auth, browser or Native business qualification.
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const here=fileURLToPath(new URL('.',import.meta.url));
const {PGlite}=await import(process.env.JOIN_OWNER_PGLITE_MODULE);
const origin=JSON.parse(readFileSync(here+'ACTUAL_NATIVE_SOURCE_ORIGIN.json'));
const sql=JSON.parse(readFileSync(here+'FIXTURE_SQL.json'));
const native={};
for(const [name,pin]of Object.entries(origin.files)){
  const raw=readFileSync(here+name);assert.equal(raw.length,pin.bytes);
  assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);native[name]=raw.toString();
}
const db=new PGlite();const engine=(await db.query('select version()v')).rows[0].v;
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const ownerRole=id(900),adminRole=id(901);const results=[];
const params=text=>{let i=0;return text.replaceAll('%s',()=>'$'+(++i));};
const snapshot=async()=>(await db.query('select id::text,auth_user_id::text,full_name,role,role_id::text,is_active from erp.app_users order by id')).rows;
await db.exec(`create schema erp;
create table erp.app_roles(id uuid primary key,role_code text,is_active boolean);
create table erp.app_users(id uuid primary key,auth_user_id uuid unique,full_name text,role text,role_id uuid references erp.app_roles,is_active boolean);
insert into erp.app_roles values('${ownerRole}','OWNER',true),('${adminRole}','ADMIN',true);`);
await db.exec(native['captured_guard_last_active_owner.sql']);
await db.exec(native['captured_guard_protected_role.sql']);
await db.exec(`create trigger model_last_owner before update or delete on erp.app_users for each row execute function erp.guard_last_active_owner();
create trigger model_protected_role before update or delete on erp.app_roles for each row execute function erp.guard_protected_role();`);
async function refused(operation,message){
  const before=await snapshot();await db.exec('savepoint expected_refusal');let failure;
  try{await operation();}catch(e){failure=e;}
  await db.exec('rollback to savepoint expected_refusal;release savepoint expected_refusal');
  assert.ok(failure,'Native guard must actually refuse');assert.equal(failure.code,'42501');assert.equal(failure.message,message);
  assert.deepEqual(await snapshot(),before);
}
for(const number of[1,2,4]){
  await db.exec("begin;set local erp.cp45_allow_synthetic_cleanup='off'");
  for(let n=1;n<=number;n++)await db.query('insert into erp.app_users values($1,$2,$3,$4,$5,true)',[id(n),id(100+n),'MODEL OWNER '+n,'OWNER',ownerRole]);
  await db.query('insert into erp.app_users values($1,$2,$3,$4,$5,true)',[id(50),id(150),'MODEL ADMIN','ADMIN',adminRole]);
  const before=await snapshot();const rows=(await db.query(sql.ROSTER)).rows;
  assert.equal(rows.length,number);
  for(let n=2;n<=number;n++){
    const changed=(await db.query(params(sql.DEACTIVATE),[id(n),id(100+n)])).rows;
    assert.deepEqual(changed,[{id:id(n)}]);
  }
  const isolated=await snapshot();
  assert.deepEqual(isolated,before.map(row=>({...row,is_active:row.role==='OWNER'&&row.id!==id(1)?false:row.is_active})));
  assert.equal((await db.query(sql.ROSTER)).rows.length,1);
  await refused(()=>db.query(params(sql.DEACTIVATE),[id(1),id(101)]),'LAST_ACTIVE_OWNER_PROTECTED');
  await refused(()=>db.query("update erp.app_roles set is_active=true where role_code='OWNER'"),'PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED');
  await db.query('insert into erp.app_users values(gen_random_uuid(),$1,$2,$3,$4,true)',[id(200),'MODEL backup OWNER','OWNER',ownerRole]);
  assert.equal((await db.query(sql.ROSTER)).rows.length,2);
  assert.deepEqual((await db.query(params(sql.DEACTIVATE),[id(1),id(101)])).rows,[{id:id(1)}]);
  assert.equal((await db.query(sql.ROSTER)).rows.length,1);
  await db.exec('rollback');assert.deepEqual(await snapshot(),[]);
  results.push({initial_active_owners:number,only_other_active_flags_changed:true,last_owner_refused:'42501',protected_role_refused:'42501',backup_then_original_deactivation_allowed:true,whole_model_rollback_equal:true});
}
await db.close();const value={classification:'ISOLATED_POSTGRESQL_NATIVE_GUARD_SQL_MODEL_NOT_ERP',engine,results,
  actual_Native_cases:0,actual_Auth_or_browser_cases:0,financial_SQL_executed:0,Native_guard_changes:0,production_go:false,independent_acceptance:false};
writeFileSync(here+'ACTUAL_SQL_MODEL_CONTROLS.json',JSON.stringify(value,null,2)+'\n');
console.log(JSON.stringify(value));
