// New settings facade controls in a small PostgreSQL model. Auth functions
// below are explicit session stubs; no actual Auth HTTP or ERP journey credit.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {execFileSync} from 'node:child_process'
import {createHash,randomUUID} from 'node:crypto'

const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..')
assert(process.env.PGLITE_MODULE)
const {PGlite}=await import(pathToFileURL(resolve(process.env.PGLITE_MODULE)).href)
const db=new PGlite(),q=(sql,args=[])=>db.query(sql,args)
let inTransaction=false
const val=async(sql,args=[])=>Object.values((await q(sql,args)).rows[0])[0]
const id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const owner=id(1),admin=id(2),operator=id(3),authUser=id(900),category=id(4),specialPolicy=id(5),contractor=id(6)
const permissions=['settings.erp.view','warehouse.accessory.view','settings.erp.manage']
const access=(actor=owner,role='OWNER',perms=permissions)=>({allowed:true,profile:{id:actor,auth_user_id:authUser,
  role_code:role,row_version:1,role_row_version:1,is_active:true},permissions:perms})
const setAccess=async(value,subject=authUser,jwtRole='authenticated')=>{
  await q("select set_config('model.access',$1,false),set_config('request.jwt.claim.sub',$2,false),set_config('request.jwt.claim.role',$3,false)",[JSON.stringify(value),subject??'',jwtRole??''])
}
const as=async(role,fn)=>{
  if(inTransaction)await db.exec('savepoint model_rpc_role')
  await db.exec('set role '+role)
  try{return await fn()}
  catch(error){if(inTransaction)await db.exec('rollback to savepoint model_rpc_role');throw error}
  finally{await db.exec('reset role');if(inTransaction)await db.exec('release savepoint model_rpc_role')}
}
const read=(p={before_version:null,before_date:null})=>as('authenticated',()=>val('select public.erp_cp7_get_good_policy_dates_v1($1::jsonb)',[JSON.stringify(p)]))
const save=(payload,request=randomUUID(),cancel=false)=>as('authenticated',()=>val('select public.erp_cp7_save_good_policy_date_v1($1::jsonb,$2::uuid,$3::boolean)',[JSON.stringify(payload),request,cancel]))
const command=(w,day='2026-10-01',event=w.current_source)=>({contract_version:'cp7.good-policy-date-command.v1',actor:w.actor,
  access_epoch:w.access_epoch,effective_from:day,source_event_id:event.id,expected_current_version:w.current_source.version,
  expected_timeline:w.timeline_token,reason:'SYNTHETIC EXPLICIT GOOD DATE',reviewed:true})
const counts=()=>val(`select jsonb_build_object('versions',(select count(*)from cp7_accessory_nonpayable.category_versions_v1),
  'requests',(select count(*)from cp7_accessory_nonpayable.date_requests_v1))`)
const checks=[],test=async(name,fn)=>{await fn();checks.push({name,status:'PASS'})}
const queries=JSON.parse(execFileSync('python',['-B','-c',`
import ast,json,pathlib
p=pathlib.Path('scripts/cp7_ow04_restore_bundle.py');nodes=[]
for n in ast.parse(p.read_bytes()).body:
 if isinstance(n,ast.FunctionDef) and n.name=='_acl':nodes.append(n)
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('NAMESPACE','QUERIES') for t in n.targets):nodes.append(n)
space={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':pure-query-strings','exec'),space)
assert len(space['QUERIES'])==22
print(json.dumps(space['QUERIES']))
`],{cwd:root,encoding:'utf8'}))
const capture=async()=>{
  const result={}
  for(const [group,sql]of Object.entries(queries)){
    const rows=(await q(sql)).rows.map(row=>Object.values(row))
    assert.equal(new Set(rows.map(row=>row[0])).size,rows.length)
    result[group]=Object.fromEntries(rows)
  }
  return result
}
let report
try{
  await db.exec(`create role anon nologin;create role authenticated nologin;create role service_role nologin;
    create schema erp;create schema auth;
    create table erp.app_users(id uuid primary key);
    create table erp.bc_policy_settings_v1(policy_key text primary key,status text,value jsonb,version bigint);
    create table erp.bc_policy_setting_events_v1(id uuid primary key,policy_key text,version bigint,status text,value jsonb,set_at timestamptz default statement_timestamp(),reason text,unique(policy_key,version));
    create table erp.accessory_categories(id uuid primary key,category_name text,is_active boolean);
    create table erp.contractors(id uuid primary key,contractor_type text);
    create table erp.contractor_hpp_policy_versions(id uuid primary key,contractor_id uuid,effective_from date,effective_to date,is_special boolean,row_version bigint);
    create table erp.fg_lots(id uuid primary key,lot_origin text);
    create table erp.fg_accessory_cost_snapshots(id uuid primary key,lot_id uuid,po_id uuid,product_id uuid,
      bom_version_id uuid,bom_item_id uuid,category_id uuid,good_qty_pcs integer,qty_per_good_fg_base numeric,
      hpp_method text,reimbursement_unit_rate_base_snapshot numeric,costing_basis_at timestamptz,costing_basis_source text);
    create function auth.uid()returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
    create function auth.jwt()returns jsonb language sql stable as $$select jsonb_build_object('role',current_setting('request.jwt.claim.role',true))$$;
    create function erp.get_my_access_v1()returns jsonb language sql stable as $$select current_setting('model.access')::jsonb$$;
    create function erp.current_app_user_id()returns uuid language sql stable as $$select(current_setting('model.access')::jsonb->'profile'->>'id')::uuid$$;
    create function erp.has_permission(text)returns boolean language sql stable as $$select(current_setting('model.access')::jsonb->'permissions')?$1$$;
    create function erp.require_internal()returns void language plpgsql as $$begin
      if auth.uid() is null or current_setting('model.access')::jsonb->'allowed' is distinct from 'true'::jsonb then raise exception 'MODEL_INTERNAL_REQUIRED';end if;end;$$;
    create function erp.require_owner_admin()returns void language plpgsql as $$begin
      if current_setting('model.access')::jsonb->'profile'->>'role_code' not in('OWNER','ADMIN')then raise exception 'MODEL_OWNER_ADMIN_REQUIRED';end if;end;$$;`)
  await q('insert into erp.app_users values($1),($2),($3)',[owner,admin,operator])
  await q("insert into erp.accessory_categories values($1,'SYNTHETIC CATEGORY',true)",[category])
  await q("insert into erp.contractors values($1,'MANDOR')",[contractor])
  await q("insert into erp.contractor_hpp_policy_versions values($1,$2,'2026-01-01',null,true,1)",[specialPolicy,contractor])
  const value={special_free_category_ids:[category]}
  for(let version=1;version<=35;version++)await q("insert into erp.bc_policy_setting_events_v1(id,policy_key,version,status,value,reason)values($1,'ERP_DEC02',$2,$3,$4::jsonb,'SYNTHETIC SOURCE')",[id(100+version),version,version===1?'PENDING_POLICY_VALUE':'SET',version===1?null:JSON.stringify(value)])
  await q("insert into erp.bc_policy_settings_v1 values('ERP_DEC02','SET',$1::jsonb,35)",[JSON.stringify(value)])
  for(const file of ['policy.sql','basis.sql'])await db.exec(readFileSync(resolve(here,file),'utf8'))
  await setAccess(access())
  await db.exec("set search_path='';set timezone='UTC'")
  const before=await capture(),schemaAcl=await val("select nspacl::text from pg_namespace where nspname='public'")
  assert.notEqual(schemaAcl,null,'EXPLICIT_PUBLIC_SCHEMA_ACL_REQUIRED')
  await db.exec(readFileSync(resolve(here,'settings.sql'),'utf8'))
  await test('PUBLIC_SCHEMA_RAW_ACL_RESTORED_AFTER_OWNERSHIP_GRANT',async()=>assert.equal(await val("select nspacl::text from pg_namespace where nspname='public'"),schemaAcl))
  await test('OWNER_WORKSPACE_HAS_CURRENT_SOURCE_AND_BOUNDED_HISTORY',async()=>{
    const w=await read();assert.equal(w.actor,owner);assert.equal(w.can_write,true);assert.equal(w.current_source.version,'35')
    assert.equal(w.source_events.length,30);assert.equal(w.source_has_more,true);assert.equal(w.next_source_before,'6')
    assert.equal(w.current_source_registered,false);assert.deepEqual(w.versions,[])
    const page=await read({before_version:w.next_source_before,before_date:null})
    assert.equal(page.source_events.length,5);assert.equal(page.source_has_more,false);assert.equal(page.next_source_before,null)
    assert.equal(page.source_events.at(-1).status,'PENDING_POLICY_VALUE')
  })
  await test('ADMIN_CAN_READ_BUT_CANNOT_CONFIRM_DATE',async()=>{
    await setAccess(access(admin,'ADMIN'));assert.equal((await read()).can_write,false)
    const w=await read();await assert.rejects(()=>save(command(w)),/NONPAYABLE_OWNER_DATE_REQUIRED/)
    assert.deepEqual(await counts(),{versions:0,requests:0})
  })
  await test('ORDINARY_INTERNAL_USER_CANNOT_READ_POLICY_VALUES',async()=>{
    await setAccess(access(operator,'OPERATOR'));await assert.rejects(()=>read(),/NONPAYABLE_SETTINGS_DENIED/)
  })
  for(const missing of ['settings.erp.view','warehouse.accessory.view','settings.erp.manage'])await test('EXISTING_PERMISSION_REQUIRED:'+missing,async()=>{
    await setAccess(access(owner,'OWNER',permissions.filter(p=>p!==missing)))
    if(missing==='settings.erp.manage'){
      const w=await read();assert.equal(w.can_write,false);await assert.rejects(()=>save(command(w)),/NONPAYABLE_OWNER_DATE_REQUIRED/)
    }else await assert.rejects(()=>read(),/NONPAYABLE_SETTINGS_DENIED/)
  })
  await test('MISSING_JWT_AND_WRONG_JWT_ROLE_REFUSE',async()=>{
    await setAccess(access(),null);await assert.rejects(()=>read(),/NONPAYABLE_SETTINGS_DENIED/)
    await setAccess(access(),authUser,'service_role');await assert.rejects(()=>read(),/NONPAYABLE_SETTINGS_DENIED/)
  })
  await test('DISABLED_ACCESS_REFUSES',async()=>{
    await setAccess({...access(),allowed:false});await assert.rejects(()=>read(),/NONPAYABLE_SETTINGS_DENIED/)
  })
  await setAccess(access())
  for(const role of ['anon','service_role'])await test('PUBLIC_EXECUTE_DENIED:'+role,async()=>{
    await assert.rejects(()=>as(role,()=>val("select public.erp_cp7_get_good_policy_dates_v1('{\"before_version\":null,\"before_date\":null}'::jsonb)")),/permission denied/)
  })
  await test('FACADE_ROLE_HAS_ONLY_TWO_PRIVATE_ENTRYPOINTS_NO_TABLE_OR_FINANCIAL_ACCESS',async()=>{
    assert.equal(await val("select has_schema_privilege('cp7_good_policy_date','cp7_accessory_nonpayable','USAGE')"),true)
    assert.equal(await val("select has_schema_privilege('cp7_good_policy_date','cp7_accessory_nonpayable','CREATE')"),false)
    const functions=(await q("select p.oid::regprocedure::text as signature,has_function_privilege('cp7_good_policy_date',p.oid,'EXECUTE') as allowed from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_accessory_nonpayable'")).rows
    assert.deepEqual(functions.filter(f=>f.allowed).map(f=>f.signature).sort(),[
      'cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean)','cp7_accessory_nonpayable.settings_workspace_v1(jsonb)'])
    for(const table of ['category_versions_v1','good_bases_v1','date_requests_v1'])assert.equal(await val("select has_table_privilege('cp7_good_policy_date',$1,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",['cp7_accessory_nonpayable.'+table]),false)
    const role=(await q("select rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls from pg_roles where rolname='cp7_good_policy_date'")).rows[0]
    assert(Object.values(role).every(value=>value===false))
  })
  await db.exec('begin isolation level repeatable read');inTransaction=true
  await test('REPEATABLE_READ_IS_REFUSED_FOR_FRESH_ACCESS',async()=>await assert.rejects(()=>read(),/NONPAYABLE_FRESH_ACCESS_REQUIRED/))
  await db.exec('rollback');inTransaction=false
  await db.exec('begin');inTransaction=true
  const initial=await read(),payload=command(initial),request=randomUUID()
  const nativeBefore=await val("select jsonb_build_object('settings',(select jsonb_agg(to_jsonb(s))from erp.bc_policy_settings_v1 s),'events',(select jsonb_agg(to_jsonb(e)order by e.id)from erp.bc_policy_setting_events_v1 e))")
  let outcome
  await test('EXPLICIT_OWNER_SOURCE_AND_DATE_SAVED_WITH_SAME_REQUEST',async()=>{
    outcome=await save(payload,request);assert.equal(outcome.status,'SAVED');assert.equal(outcome.request_id,request)
    assert.equal(outcome.actor,owner);assert.equal(outcome.effective_from,'2026-10-01');assert.equal(outcome.source_version,'35')
    assert.deepEqual(await counts(),{versions:1,requests:1});assert.equal((await read()).current_source_registered,true)
    assert.deepEqual(await val("select jsonb_build_object('settings',(select jsonb_agg(to_jsonb(s))from erp.bc_policy_settings_v1 s),'events',(select jsonb_agg(to_jsonb(e)order by e.id)from erp.bc_policy_setting_events_v1 e))"),nativeBefore)
  })
  await test('EXACT_REPLAY_RETURNS_STORED_REPLY_WITHOUT_NEW_ROWS',async()=>{
    const before=await counts();assert.deepEqual(await save(payload,request),outcome);assert.deepEqual(await counts(),before)
  })
  await test('CHANGED_INTENT_WITH_SAME_REQUEST_REFUSES',async()=>{
    const before=await counts();await assert.rejects(()=>save({...payload,reason:'SYNTHETIC CHANGED INTENT'},request),/NONPAYABLE_DATE_REQUEST_INTENT_CHANGED/)
    assert.deepEqual(await counts(),before)
  })
  await test('ANOTHER_OWNER_CANNOT_REUSE_THE_REQUEST',async()=>{
    await setAccess(access(admin,'OWNER'));const w=await read()
    await assert.rejects(()=>save({...payload,actor:admin,access_epoch:w.access_epoch},request),/NONPAYABLE_DATE_REQUEST_INTENT_CHANGED/)
    await setAccess(access())
  })
  await test('SOURCE_CHANGE_REFUSES_STALE_NEW_COMMAND_BUT_EXACT_REPLAY_SURVIVES',async()=>{
    await q("insert into erp.bc_policy_setting_events_v1(id,policy_key,version,status,value,reason)values($1,'ERP_DEC02',36,'SET',$2::jsonb,'SYNTHETIC SOURCE CHANGE')",[id(136),JSON.stringify(value)])
    await q("update erp.bc_policy_settings_v1 set version=36 where policy_key='ERP_DEC02'")
    const before=await counts()
    await assert.rejects(()=>save({...payload,effective_from:'2026-10-02'}),/NONPAYABLE_CURRENT_SOURCE_STALE/)
    assert.deepEqual(await save(payload,request),outcome);assert.deepEqual(await counts(),before)
  })
  await test('ACCESS_EPOCH_CHANGE_REFUSES_NEW_COMMAND_AND_STILL_ALLOWS_AUTHORIZED_EXACT_REPLAY',async()=>{
    const w=await read(),old=command(w,'2026-10-03'),changed=access();changed.profile.row_version=2
    await setAccess(changed);await assert.rejects(()=>save(old),/NONPAYABLE_SETTINGS_ACCESS_CHANGED/)
    assert.deepEqual(await save(payload,request),outcome);await setAccess(access())
  })
  await test('REVOKED_PERMISSION_CANNOT_REPLAY_CACHED_SUCCESS',async()=>{
    await setAccess(access(owner,'OWNER',permissions.filter(p=>p!=='settings.erp.manage')))
    await assert.rejects(()=>save(payload,request),/NONPAYABLE_OWNER_DATE_REQUIRED/);await setAccess(access())
  })
  await test('TWO_OBSERVATIONS_STALE_TIMELINE_REFUSES_SECOND_NEW_DATE',async()=>{
    const w=await read(),a=command(w,'2026-11-01'),b=command(w,'2026-11-02')
    await save(a);const before=await counts();await assert.rejects(()=>save(b),/NONPAYABLE_TIMELINE_STALE/)
    assert.deepEqual(await counts(),before)
  })
  await test('CANCEL_ABSENT_STALE_REQUEST_WRITES_ONLY_A_TOMBSTONE',async()=>{
    const w=await read(),p=command(w,'2026-11-03'),cancelledRequest=randomUUID(),before=await counts()
    p.expected_current_version='1';p.expected_timeline='0'.repeat(64);p.access_epoch='0'.repeat(64)
    const cancelled=await save(p,cancelledRequest,true)
    assert.equal(cancelled.status,'CANCELLED');assert.equal(cancelled.id,null);assert.equal(cancelled.source_version,null)
    assert.equal(cancelled.request_id,cancelledRequest);assert.equal(cancelled.source_event_id,p.source_event_id)
    assert.deepEqual(await counts(),{versions:before.versions,requests:before.requests+1})
    assert.deepEqual(await save(p,cancelledRequest),cancelled)
    assert.deepEqual(await save(p,cancelledRequest,true),cancelled)
    assert.deepEqual(await counts(),{versions:before.versions,requests:before.requests+1})
  })
  await test('CANCEL_ALREADY_SAVED_RETURNS_SUCCESS_AND_PRESERVES_POLICY_HISTORY',async()=>{
    const before=await counts();assert.deepEqual(await save(payload,request,true),outcome);assert.deepEqual(await counts(),before)
  })
  await test('CANCEL_SAME_UUID_CHANGED_INTENT_IS_REFUSED',async()=>{
    const before=await counts();await assert.rejects(()=>save({...payload,effective_from:'2026-12-01'},request,true),/NONPAYABLE_DATE_REQUEST_INTENT_CHANGED/)
    assert.deepEqual(await counts(),before)
  })
  await test('INVALID_CLOSED_FIELDS_DATE_REVIEW_AND_REASON_HAVE_NO_EFFECT',async()=>{
    const p=command(await read(),'2026-10-04'),before=await counts()
    for(const bad of [{...p,extra:true},{...p,reviewed:false},{...p,reason:''},{...p,effective_from:'2026-02-30'},
      {...p,expected_current_version:true},{...p,actor:admin}])await assert.rejects(()=>save(bad))
    await assert.rejects(()=>save(p,null));assert.deepEqual(await counts(),before)
  })
  await test('EXPLICIT_PENDING_SOURCE_DATE_IS_RECORDED_AS_PENDING_NOT_FREE',async()=>{
    const w=await read(),first=(await read({before_version:'2',before_date:null})).source_events[0]
    assert.equal(first.status,'PENDING_POLICY_VALUE');await save(command(w,'2026-09-01',first))
    assert.equal((await read()).versions.find(v=>v.effective_from==='2026-09-01').source_event.status,'PENDING_POLICY_VALUE')
  })
  await test('TIMELINE_KEYSET_PAGES_ARE_BOUNDED_WITH_NO_DUPLICATES_OR_OMISSIONS',async()=>{
    for(let day=1;day<=31;day++)await q('select cp7_accessory_nonpayable.record_version_v1($1::date,$2,$3,cp7_accessory_nonpayable.timeline_token_v1(),$4)',
      ['2025-01-'+String(day).padStart(2,'0'),id(136),randomUUID(),'SYNTHETIC PAGINATION'])
    const w=await read();assert.equal(w.versions.length,30);assert.equal(w.version_has_more,true)
    const next=await read({before_version:null,before_date:w.next_version_before})
    assert.equal(next.version_has_more,false);assert.equal(next.next_version_before,null)
    const ids=[...w.versions,...next.versions].map(v=>v.id)
    assert.equal(new Set(ids).size,ids.length);assert.equal(ids.length,(await counts()).versions)
  })
  await test('ACTIVE_POSTED_GOOD_REFUSES_POLICY_BACKDATE_AND_LEAVES_REQUEST_UNRECORDED',async()=>{
    const lot=randomUUID(),snapshot=randomUUID(),basis=await val("select id from cp7_accessory_nonpayable.category_versions_v1 where effective_from='2026-10-01'")
    await q("insert into erp.fg_lots values($1,'PRODUCTION')",[lot])
    await q('insert into erp.fg_accessory_cost_snapshots(id,lot_id)values($1,$2)',[snapshot,lot])
    await q("insert into cp7_accessory_nonpayable.good_bases_v1(snapshot_id,lot_id,contractor_id,category_policy_id,special_policy_id,good_date,nonpayable,original_reimbursement_rate,fixed_snapshot,basis)values($1,$2,$3,$4,$5,'2026-10-15',true,3,'{}','{}')",[snapshot,lot,contractor,basis,specialPolicy])
    const p=command(await read(),'2026-10-10'),before=await counts()
    await assert.rejects(()=>save(p),/NONPAYABLE_POSTED_GOOD_POLICY_REVIEW_REQUIRED/);assert.deepEqual(await counts(),before)
  })
  await test('REQUEST_HISTORY_IS_IMMUTABLE',async()=>{
    for(const statement of ["update cp7_accessory_nonpayable.date_requests_v1 set response='{}'",
      'delete from cp7_accessory_nonpayable.date_requests_v1','truncate cp7_accessory_nonpayable.date_requests_v1']){
      await db.exec('savepoint model_immutable')
      try{await assert.rejects(()=>db.exec(statement),/NONPAYABLE_POLICY_HISTORY_IMMUTABLE/)}
      finally{await db.exec('rollback to savepoint model_immutable');await db.exec('release savepoint model_immutable')}
    }
  })
  await db.exec('rollback');inTransaction=false
  // The transaction above was the disposable model's restore boundary. The
  // settings stage remains unused, so its exact DDL inverse is now lawful.
  await db.exec(`drop function public.erp_cp7_get_good_policy_dates_v1(jsonb);
    drop function public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean);
    drop table cp7_accessory_nonpayable.date_requests_v1;
    drop function cp7_accessory_nonpayable.settings_access_v1(boolean);
    drop function cp7_accessory_nonpayable.settings_event_v1(uuid);
    drop function cp7_accessory_nonpayable.settings_workspace_v1(jsonb);
    drop function cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean);
    revoke usage on schema cp7_accessory_nonpayable from cp7_good_policy_date;
    drop role cp7_good_policy_date;`)
  await test('MODEL_TRANSACTION_RESTORE_AND_SETTINGS_DDL_INVERSE_RESTORE_ALL22',async()=>assert.deepEqual(await capture(),before))
  report={status:'ISOLATED_POSTGRES_GOOD_DATE_SETTINGS_FACADE_MODEL_PASS',engine:await val('select version()'),checks,
    contract_samples:{workspace:initial,command:{requestId:request,actor:owner,payload},outcome},
    source_sha256:Object.fromEntries(['policy.sql','basis.sql','settings.sql'].map(f=>[f,createHash('sha256').update(readFileSync(resolve(here,f))).digest('hex')])),
    actual_ERP_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,actual_two_session_races:0,
    full_real_settings_installer_lifecycle_qualified:false,installed_on_candidate:false,production_go:false,independent_acceptance:false}
}catch(error){report={status:'ISOLATED_POSTGRES_GOOD_DATE_SETTINGS_FIRST_FAILURE',checks,error:String(error),actual_Auth_HTTP_cases:0,actual_ERP_Native_cases:0,production_go:false};throw error}
finally{if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(report,null,2)+'\n');await db.close()}
process.stdout.write(JSON.stringify({status:report.status,checks:checks.length,actual_Auth_HTTP_cases:0})+'\n')
