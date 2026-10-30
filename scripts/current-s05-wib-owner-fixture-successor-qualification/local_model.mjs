/** Actual captured Native3 on typed source-derived LOCAL doubles. Native credit0. */
import fs from 'node:fs';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';

const here=path.dirname(fileURLToPath(import.meta.url));
if(!process.env.S05_PGLITE_MODULE)throw new Error('Explicit local PGlite module path required; no install/network');
const {PGlite}=await import(pathToFileURL(process.env.S05_PGLITE_MODULE).href);
const db=new PGlite();
const inputs=JSON.parse(fs.readFileSync(path.join(here,'evidence/LOCAL_TYPED_INPUTS.json')));
const captured=JSON.parse(fs.readFileSync(path.join(here,'evidence/ACTUAL_602_NATIVE_INPUTS.json')));
const quote=s=>'"'+s.replaceAll('"','""')+'"';
const checks=[];
const result={status:'INCOMPLETE',classification:'SOURCE_DERIVED_LOCAL_SQL_DOUBLES_NOT_ACTUAL_ERP',actual_Native:0,
  captured_source_head_class:'ACTUAL602_NOT52EED',full_native_definitions_unchanged:true,
  declared_doubles:['permission/internal/closed-JSON prelude','request actor/hash','typed tables without fullRLS/ACL/FKs','post-validation contractors empty','AFTER-user audit sequence'],checks};
try{
 await db.exec('create schema erp;create schema s05_model;');
 const tables=new Map();
 for(const [key,row]of Object.entries(inputs.columns)){
  const [table]=key.split(':');if(!tables.has(table))tables.set(table,[]);tables.get(table).push(row);
 }
 for(const [table,rows]of tables){
  const fields=rows.sort((a,b)=>a[1]-b[1]).map(row=>quote(row[0])+' '+row[2]+(row[13]?' default '+row[13]:'')+(row[3]?' not null':''));
  await db.exec('create table '+table+'('+fields.join(',')+');');
 }
 for(const [key,row]of Object.entries(inputs.idempotency_constraints))await db.exec('alter table erp.idempotency_requests add constraint '+quote(key.split(':')[1])+' '+row.at(-1)+';');
 await db.exec(`
 create function erp.require_permission(text)returns void language sql as $$select$$;
 create function erp.require_internal()returns void language sql as $$select$$;
 create function erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)returns void language sql as $$select$$;
 create function erp._request_hash(jsonb)returns text language sql as $$select md5($1::text)$$;
 create function erp._idempotency_actor_key()returns text language sql as $$select 'DECLARED_MODEL_OWNER'::text$$;
 create function erp._cp3_business_date(timestamptz)returns date language sql as $$select($1 at time zone 'Asia/Jakarta')::date$$;
 create sequence s05_model.audit_seq;
 create function s05_model.audit_user()returns trigger language plpgsql as $$begin perform nextval('s05_model.audit_seq');if TG_OP='DELETE'then return old;else return new;end if;end$$;
 create trigger model_after_user after insert or update or delete on erp.app_users for each row execute function s05_model.audit_user();
 `);
 for(const row of Object.values(captured.functions))await db.exec(row[0]);
 await db.exec('create trigger trg_02_guard_last_active_owner before update or delete on erp.app_users for each row execute function erp.guard_last_active_owner();');
 const ownerRole='10000000-0000-4000-8000-000000000001',staffRole='10000000-0000-4000-8000-000000000002';
 const first='20000000-0000-4000-8000-000000000001',second='20000000-0000-4000-8000-000000000002';
 await db.query("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active)values($1,'OWNER','ModelOwner',true,true,true),($2,'STAFF','ModelStaff',true,true,true)",[ownerRole,staffRole]);
 await db.query("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values($1,$1,'Original','OWNER',$2,true)",[first,ownerRole]);
 async function snapshot(){
  const rows={};for(const table of [...tables.keys()].sort())rows[table]=(await db.query('select to_jsonb(t)as row from '+table+' t order by to_jsonb(t)::text')).rows;
  const sequences=(await db.query('select last_value,is_called from s05_model.audit_seq')).rows;
  const definitions=(await db.query("select oid::regprocedure::text as signature,pg_get_functiondef(oid)as ddl from pg_proc where pronamespace='erp'::regnamespace order by oid::regprocedure::text")).rows;
  return JSON.stringify({rows,sequences,definitions});
 }
 async function denied(name,operation,message,code='P0001'){
  const before=await snapshot();await db.exec('begin;savepoint guarded;');let error;
  try{await operation();}catch(e){error=e;}
  await db.exec('rollback to savepoint guarded;release savepoint guarded;commit;');
  assert(error,'Expected real captured Native refusal: '+name);assert.equal(error.message,message);assert.equal(error.code,code);assert.equal(await snapshot(),before);
  checks.push({name,status:'PASS_EXPECTED_CAPTURED_NATIVE_REFUSAL',error:message,sqlstate:code,typed_rows_all_model_sequences_and_definitions_equal:true,Native_credit:0});
 }
 const request=(time)=>({number:'MODEL_TIME',physical_at:time,reason:'Declared local parser diagnostic',items:[]});
 const call=async(time)=>db.query('select erp.save_accessory_issue_action_v1($1,$2::jsonb,gen_random_uuid())',['POST',JSON.stringify(request(time))]);
 for(const value of ['2026-01-15T00:00:00.000000+07:00','2026-01-15T23:59:59.999999+07:00','2026-01-15T00:00:00+00:00'])await denied('WIB_FORMAT_'+value,()=>call(value),'Waktu pengambilan wajib memakai tanggal dan jam WIB');
 for(const value of ['2026-01-15T00:00:00+07:00','2026-01-15T23:59:59+07:00'])await denied('SUPPORTED_SECONDS_REACH_NEXT_NATIVE_GUARD_'+value,()=>call(value),'Pilih mandor aktif');
 await denied('SOLE_OWNER_DEACTIVATE',()=>db.query('update erp.app_users set is_active=false where id=$1',[first]),'LAST_ACTIVE_OWNER_PROTECTED','42501');
 await denied('SOLE_OWNER_DELETE',()=>db.query('delete from erp.app_users where id=$1',[first]),'LAST_ACTIVE_OWNER_PROTECTED','42501');
 await denied('SOLE_OWNER_DEMOTE',()=>db.query("update erp.app_users set role='STAFF',role_id=$2 where id=$1",[first,staffRole]),'LAST_ACTIVE_OWNER_PROTECTED','42501');
 await denied('SOLE_OWNER_CLEAR_AUTH',()=>db.query('update erp.app_users set auth_user_id=null where id=$1',[first]),'LAST_ACTIVE_OWNER_PROTECTED','42501');
 await db.query("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values($1,$1,'Backup','OWNER',$2,true)",[second,ownerRole]);
 await db.query('update erp.app_users set is_active=false where id=$1',[first]);
 assert.deepEqual((await db.query('select auth_user_id::text,is_active from erp.app_users order by id')).rows,[{auth_user_id:first,is_active:false},{auth_user_id:second,is_active:true}]);
 checks.push({name:'DISTINCT_BACKUP_OWNER_ALLOWS_ORIGINAL_DEACTIVATION',status:'PASS_CAPTURED_NATIVE_GUARD_LIFECYCLE_MODEL',Native_credit:0});
 await denied('REMAINING_BACKUP_STILL_PROTECTED',()=>db.query('update erp.app_users set is_active=false where id=$1',[second]),'LAST_ACTIVE_OWNER_PROTECTED','42501');
 result.status='PASS_LOCAL_NATIVE_PARSER_AND_OWNER_GUARD_MODELS_ONLY';
}catch(error){result.error=String(error.stack??error);process.exitCode=1;}
finally{await db.close();}
process.stdout.write(JSON.stringify(result,null,2)+'\n');
