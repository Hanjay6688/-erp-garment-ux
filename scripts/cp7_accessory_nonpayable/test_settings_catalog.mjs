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
  const model=readFileSync(resolve(here,'test_settings.mjs'),'utf8')
  const setup=model.match(/await db\.exec\(`(create role anon[\s\S]*?)`\)/)?.[1]
  assert(setup&&!setup.includes('${')&&!setup.includes('\\'),'EXACT_LITERAL_EXISTING_MODEL_SETUP_REQUIRED')
  await db.exec(setup)
  for(const file of ['policy.sql','basis.sql'])await db.exec(readFileSync(resolve(here,file),'utf8'))
  await db.exec("set search_path='';set timezone='UTC'")
  const before=await capture()
  await db.exec(readFileSync(resolve(here,'settings.sql'),'utf8'))
  const after=await capture()
  await test('ACTUAL_ALL22_ACCEPTS_ONLY_EXACT_SETTINGS_ROLE_SCHEMA_GRANT_SIX_FUNCTIONS_TABLE_AND_RI',async()=>{
    const proof=JSON.parse(python(`
import json,sys
sys.path.insert(0,'scripts')
from cp7_accessory_nonpayable import settings_stage as s
v=json.load(sys.stdin);s.transition(v['before'],v['after'])
print(json.dumps(dict(status='EXACT_SETTINGS_STAGE_ACTUAL_CATALOGUE_TRANSITION_PASS')))
`,JSON.stringify({before,after})))
    assert.equal(proof.status,'EXACT_SETTINGS_STAGE_ACTUAL_CATALOGUE_TRANSITION_PASS')
  })
  const bodies=JSON.parse(python("import sys,json;sys.path.insert(0,'scripts');from cp7_accessory_nonpayable import settings_stage as s;print(json.dumps(s.function_bodies()))"))
  await test('ALL_SIX_ACTUAL_PROSRC_OWNERS_LANGUAGES_VOLATILITY_SEARCH_PATHS_MATCH_SOURCE',async()=>{
    for(const [signature,expected]of Object.entries(bodies)){
      const row=(await q('select pg_get_userbyid(p.proowner) as owner,p.prosecdef as definer,p.provolatile as vol,l.lanname as language,p.proconfig as config,p.prosrc as body from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=$1::regprocedure',[signature])).rows[0]
      assert.deepEqual(row,{owner:signature.startsWith('public.')?'cp7_good_policy_date':'postgres',definer:true,vol:expected.volatility,language:expected.language,config:['search_path=""'],body:expected.body})
    }
  })
  await test('UNDECLARED_OLD_GRANT_EXTRA_FUNCTION_AND_EXTRA_PARENT_TRIGGER_ARE_REFUSED',async()=>{
    const proof=JSON.parse(python(`
import json,sys,copy
sys.path.insert(0,'scripts')
from cp7_accessory_nonpayable import settings_stage as s
v=json.load(sys.stdin)
for group,key,row in [('functions','public.unreviewed()',['EXTRA']),('triggers','erp.app_users:unreviewed',['EXTRA']),('schemas','public',['OTHER_OWNER',[]])]:
 changed=copy.deepcopy(v['after']);changed[group][key]=row
 try:s.transition(v['before'],changed)
 except ValueError:pass
 else:raise AssertionError('UNDECLARED_SETTINGS_DELTA_ACCEPTED')
print(json.dumps(dict(rejected=3)))
`,JSON.stringify({before,after})))
    assert.equal(proof.rejected,3)
  })
  await db.exec(python("import sys;sys.path.insert(0,'scripts');from cp7_accessory_nonpayable import settings_stage as s;print(s.inverse_sql())"))
  await test('EXACT_STAGE_INVERSE_SOURCE_RESTORES_ALL22',async()=>assert.deepEqual(await capture(),before))
  report={status:'ISOLATED_POSTGRES_SETTINGS_STAGE_CATALOGUE_AND_BODY_PASS',checks,
    source_sha256:Object.fromEntries(['policy.sql','basis.sql','settings.sql','settings_stage.py','test_settings_catalog.mjs'].map(file=>[file,createHash('sha256').update(readFileSync(resolve(here,file))).digest('hex')])),
    model_setup_source:'scripts/cp7_accessory_nonpayable/test_settings.mjs:literal-schema-only',old_API_or_financial_cases_rerun:0,
    actual_ERP_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,full_real_installer_lifecycle_qualified:false,
    production_go:false,independent_acceptance:false}
}catch(error){report={status:'ISOLATED_POSTGRES_SETTINGS_STAGE_CATALOGUE_FIRST_FAILURE',checks,error:String(error),actual_ERP_Native_cases:0,production_go:false};throw error}
finally{if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(report,null,2)+'\n');await db.close()}
process.stdout.write(JSON.stringify({status:report.status,checks:checks.length,actual_ERP_Native_cases:0})+'\n')
