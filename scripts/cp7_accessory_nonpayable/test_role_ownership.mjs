// Only the new settings-stage catalogue/body/authority transition. The 30
// settings API cases and prior financial suites are not repeated here.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..')
assert(process.env.PGLITE_MODULE)
const {PGlite}=await import(pathToFileURL(resolve(process.env.PGLITE_MODULE)).href)
const db=new PGlite(),q=(sql,args=[])=>db.query(sql,args)
const python=(code,input)=>execFileSync('python',['-B','-c',code],{cwd:root,input,encoding:'utf8',maxBuffer:4*1024*1024})
const queries=JSON.parse(python(`
import ast,json,pathlib
p=pathlib.Path('scripts/cp7_ow04_restore_bundle.py');nodes=[]
for n in ast.parse(p.read_bytes()).body:
 if isinstance(n,ast.FunctionDef) and n.name=='_acl':nodes.append(n)
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('NAMESPACE','QUERIES') for t in n.targets):nodes.append(n)
space={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':pure-query-strings','exec'),space)
assert len(space['QUERIES'])==22
print(json.dumps(space['QUERIES']))
`))
const capture=async()=>{
  const result={}
  for(const [group,sql]of Object.entries(queries)){
    const rows=(await q(sql)).rows.map(row=>Object.values(row))
    assert.equal(new Set(rows.map(row=>row[0])).size,rows.length)
    result[group]=Object.fromEntries(rows)
  }
  return result
}
const checks=[],test=async(name,fn)=>{await fn();checks.push({name,status:'PASS'})}
let report
try{
  // Synthetic Supabase creator profile; no ERP business case runs.
  await db.exec(`create role role_probe_session login superuser;
    set session authorization role_probe_session;
    alter role postgres rename to supabase_admin;
    create role postgres login inherit nosuperuser createrole nocreatedb noreplication nobypassrls;`)
  const database=(await q('select current_database() as name')).rows[0].name
  assert(/^[a-z_0-9]+$/.test(database))
  await db.exec('alter database '+database+' owner to postgres;grant all on schema public to postgres;set role postgres')
  const model=readFileSync(resolve(here,'test_settings.mjs'),'utf8')
  const setup=model.match(/await db\.exec\(`(create role anon[\s\S]*?)`\)/)?.[1]
  assert(setup&&!setup.includes('${')&&!setup.includes('\\'),'EXACT_LITERAL_EXISTING_MODEL_SETUP_REQUIRED')
  await db.exec(setup)
  for(const file of ['policy.sql','basis.sql'])await db.exec(readFileSync(resolve(here,file),'utf8'))
  await db.exec("set search_path='';set timezone='UTC'")
  const profile=(await q("select current_user as creator,(select rolsuper from pg_roles where rolname=current_user) as superuser,(select rolcreaterole from pg_roles where rolname=current_user)as createrole,pg_get_userbyid(10)as bootstrap,current_setting('server_version')as version")).rows[0]
  assert.equal(profile.creator,'postgres');assert.equal(profile.superuser,false);assert.equal(profile.createrole,true);assert.equal(profile.bootstrap,'supabase_admin')
  const before=await capture()
  const rawAcl=(await q("select nspacl::text as acl from pg_namespace where nspname='public'")).rows[0].acl
  await db.exec(readFileSync(resolve(here,'settings.sql'),'utf8'))
  const after=await capture()
  await test('EXACT_SETTINGS_SQL_TRANSFERS_TWO_PUBLIC_OWNERS_UNDER_NON_SUPERUSER_POSTGRES',async()=>{
    for(const signature of ['public.erp_cp7_get_good_policy_dates_v1(jsonb)','public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean)'])
      assert.equal((await q('select pg_get_userbyid(proowner)as owner from pg_proc where oid=$1::regprocedure',[signature])).rows[0].owner,'cp7_good_policy_date')
    assert.equal((await q("select nspacl::text as acl from pg_namespace where nspname='public'")).rows[0].acl,rawAcl)
    assert.equal(await q("select 1 from pg_auth_members m where m.roleid='cp7_good_policy_date'::regrole and(m.inherit_option or m.set_option)").then(r=>r.rows.length),0)
  })
  await test('ALL22_ADMITS_ONLY_BOOTSTRAP_ADMIN_ONLY_MEMBERSHIP_AND_EXISTING_DECLARED_STAGE_DELTA',async()=>{
    const proof=JSON.parse(python(`
import json,sys
sys.path.insert(0,'scripts')
from cp7_accessory_nonpayable import settings_stage as s
v=json.load(sys.stdin);s.transition(v['before'],v['after'])
print(json.dumps(dict(status='NON_SUPERUSER_EXACT_SETTINGS_STAGE_CATALOGUE_PASS')))
`,JSON.stringify({before,after})))
    assert.equal(proof.status,'NON_SUPERUSER_EXACT_SETTINGS_STAGE_CATALOGUE_PASS')
    assert.deepEqual(after.memberships['cp7_good_policy_date:postgres:supabase_admin'],[true,false,false])
    assert(!after.memberships['cp7_good_policy_date:postgres:postgres'])
  })
  await test('ADDITIONAL_SET_INHERIT_OR_OTHER_MEMBER_REFUSED_WITHOUT_CHANGING_ORACLES',async()=>{
    const proof=JSON.parse(python(`
import json,sys,copy
sys.path.insert(0,'scripts')
from cp7_accessory_nonpayable import settings_stage as s
v=json.load(sys.stdin);key='cp7_good_policy_date:postgres:supabase_admin'
for target,row in [(key,[True,False,True]),(key,[True,True,False]),('cp7_good_policy_date:authenticated:postgres',[False,False,True])]:
 changed=copy.deepcopy(v['after']);changed['memberships'][target]=row
 try:s.transition(v['before'],changed)
 except ValueError:pass
 else:raise AssertionError('UNDECLARED_ROLE_PRIVILEGE_ACCEPTED')
print(json.dumps(dict(rejected=3)))
`,JSON.stringify({before,after})))
    assert.equal(proof.rejected,3)
  })
  await db.exec(python("import sys;sys.path.insert(0,'scripts');from cp7_accessory_nonpayable import settings_stage as s;print(s.inverse_sql())"))
  await test('NON_SUPERUSER_PREUSE_INVERSE_RESTORES_EXACT_ALL22_WITH_NO_ROLE_MEMBERSHIP_LEFT',async()=>assert.deepEqual(await capture(),before))
  report={status:'ISOLATED_POSTGRES_NON_SUPERUSER_ROLE_OWNERSHIP_FOCUSED4_PASS_NOT_ERP',checks,creator_profile:profile,
    source_sha256:Object.fromEntries(['policy.sql','basis.sql','settings.sql','settings_stage.py','test_role_ownership.mjs'].map(file=>[file,createHash('sha256').update(readFileSync(resolve(here,file))).digest('hex')])),
    schema_auth_and_permissions_are_models:true,old_settings_API_or_financial_cases_rerun:0,
    actual_ERP_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,full_real_installer_lifecycle_qualified:false,
    production_go:false,independent_acceptance:false}
}catch(error){report={status:'ISOLATED_NON_SUPERUSER_ROLE_OWNERSHIP_FIRST_FAILURE',checks,error:String(error),SQLSTATE:error.code,actual_ERP_Native_cases:0,production_go:false};throw error}
finally{if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(report,null,2)+'\n');await db.close()}
process.stdout.write(JSON.stringify({status:report.status,checks:checks.length,actual_ERP_Native_cases:0})+'\n')
