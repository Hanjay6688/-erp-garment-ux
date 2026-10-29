/** Real PGlite Postgres DDL semantics on declared role/function stand-ins.
 * Python helper control double supplies the exact emitted owner-DDL trace;
 * no actual Native parent, financial command, source admission, or restore is claimed.
 */
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('./',import.meta.url),db=new PGlite(),checks=[]
const trace=JSON.parse(execFileSync('python3',[new URL('local_owner_check.py',here).pathname],{encoding:'utf8',env:{...process.env,PYTHONPATH:new URL('../',here).pathname}}))
async function one(sql,args=[]){return(await db.query(sql,args)).rows[0]}
async function meta(sig){return one(`select pg_get_userbyid(proowner) owner,proacl::text acl,prosecdef,provolatile,proconfig from pg_proc where oid=$1::regprocedure`,[sig])}
try{
 await db.exec(`create role cp7_sales_read;create role cp7_sales_write;create role native_business_executor nosuperuser;
 revoke create on schema public from public;
 create function public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)returns jsonb language sql volatile security definer set search_path=''as $$select $1$$;
 alter function public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)owner to cp7_sales_write;
 create function public.erp_cp7_get_sales_return_correction_v1(jsonb)returns jsonb language sql volatile security definer set search_path=''as $$select $1$$;
 alter function public.erp_cp7_get_sales_return_correction_v1(jsonb)owner to cp7_sales_read;
 grant create on schema public to native_business_executor;
 grant create on schema public to cp7_sales_read,cp7_sales_write;
 revoke create on schema public from cp7_sales_read,cp7_sales_write;`)
 for(const owner of['cp7_sales_write','cp7_sales_read']){
  const name=owner==='cp7_sales_write'?'erp_cp7_correct_sales_return_v1':'erp_cp7_get_sales_return_correction_v1',args=owner==='cp7_sales_write'?'jsonb,uuid,text':'jsonb',sig=`public.${name}(${args})`
  const original=`create or replace function ${sig}returns jsonb language sql volatile security definer set search_path=''as $$select $1$$;`
  const changed=original.replace('select $1',"select $1||'{\"owner_control\":true}'::jsonb")
  const before=await meta(sig),schema=await one("select nspacl::text acl from pg_namespace where nspname='public'")
  assert.equal(before.acl,null)
  await db.exec('begin;set local role native_business_executor')
  try{await db.exec(changed);assert.fail('NONOWNER_REPLACEMENT_SUCCEEDED')}catch(e){assert.match(e.message,/must be owner/)}finally{await db.exec('rollback')}
  checks.push(owner+'_OLD_NONOWNER_DDL_REFUSED')
  async function replace(definition){
   await db.exec('begin')
   try{
    for(const step of trace.traces[owner+':False']){
     if(step.sql.includes('join pg_namespace')||step.sql==='show role'||step.sql.includes('select nspacl::text'))continue
     if(step.sql==='DECLARED_REPLACEMENT')await db.exec(definition)
     else if(step.params)await db.query(step.sql.replaceAll('%s','$1'),step.params)
     else await db.exec(step.sql)
    }
    assert.deepEqual(await meta(sig),before)
    assert.deepEqual(await one("select nspacl::text acl from pg_namespace where nspname='public'"),schema)
    assert.equal((await one('show role')).role,'none')
    await db.exec('commit')
   }catch(e){await db.exec('rollback');throw e}
  }
  await replace(changed);checks.push(owner+'_INSTALL_PRESERVES_OWNER_NULL_FUNCTION_ACL_ROLE_SCHEMA')
  await replace(original);checks.push(owner+'_PREUSE_RESTORE_PRESERVES_OWNER_NULL_FUNCTION_ACL_ROLE_SCHEMA')
  await assert.rejects(()=>replace('INVALID DECLARED DDL'),/syntax error/)
  assert.deepEqual(await meta(sig),before)
  assert.deepEqual(await one("select nspacl::text acl from pg_namespace where nspname='public'"),schema)
  assert.equal((await one('show role')).role,'none')
  checks.push(owner+'_LATE_DDL_ERROR_ATOMIC_ROLLBACK_RESTORES_ROLE_SCHEMA_FUNCTION')
  // Explicit empty function ACL is also distinct from NULL and remains exact.
  await db.exec(`revoke all on function ${sig} from public;revoke all on function ${sig} from ${owner}`)
  const empty=await meta(sig);assert.equal(empty.acl,'{}')
  await assert.rejects(()=>replace(changed),/permission denied for function/)
  assert.deepEqual(await meta(sig),empty)
  assert.deepEqual(await one("select nspacl::text acl from pg_namespace where nspname='public'"),schema)
  assert.equal((await one('show role')).role,'none')
  checks.push(owner+'_EMPTY_FUNCTION_ACL_REMAINS_EMPTY_AFTER_REFUSED_DDL')
 }
 console.log(JSON.stringify({status:'PASS',scope:'REAL_LOCAL_POSTGRES_DDL_ON_ROLE_AND_FUNCTION_STANDINS',helper_controls:trace.checks,checks,Native_execution:false,full_parent_restore:false},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL',message:error.message,sqlstate:error.code,checks,Native_execution:false},null,2));process.exitCode=1}finally{await db.close()}
