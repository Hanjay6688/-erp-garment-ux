// New catalogue/authority controls only. No old financial cases are rerun.
// Minimal native table shapes support parsing, not ERP business execution.
import assert from 'node:assert/strict'
import {readFileSync, writeFileSync} from 'node:fs'
import {dirname, resolve} from 'node:path'
import {fileURLToPath, pathToFileURL} from 'node:url'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'

const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..')
assert(process.env.PGLITE_MODULE)
const {PGlite}=await import(pathToFileURL(resolve(process.env.PGLITE_MODULE)).href)
const db=new PGlite(),q=(sql,args=[])=>db.query(sql,args)
const origin=JSON.parse(readFileSync(resolve(here,'NATIVE_ORIGIN.json')))
const checks=[],test=async(name,fn)=>{await fn();checks.push({name,status:'PASS'})}
const sha=raw=>createHash('sha256').update(raw).digest('hex')
const queriesSource='scripts/cp7_ow04_restore_bundle.py'
// Compile only the existing pure query strings/ACL renderer. No psycopg,
// ERP installer, connection or runtime module is imported by this extraction.
const queries=JSON.parse(execFileSync('python',['-B','-c',`
import ast,json,pathlib
p=pathlib.Path('${queriesSource}');nodes=[]
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
    assert.equal(new Set(rows.map(row=>row[0])).size,rows.length,'CATALOGUE_IDENTITY_COLLISION:'+group)
    result[group]=Object.fromEntries(rows)
  }
  return result
}
const authority=async()=>Object.fromEntries(await Promise.all(Object.keys(origin.functions).map(async name=>
  [name,(await q('select p.oid::text as oid,pg_get_userbyid(p.proowner) as owner,p.proacl::text as acl from pg_proc p where p.oid=$1::regprocedure',[name])).rows[0]])))
let report
try{
  await db.exec(`create role anon nologin;create role authenticated nologin;create role service_role nologin;
    create role cp7_nonpayable_test nologin;create schema erp;
    create table erp.bc_policy_setting_events_v1(id uuid primary key);
    create table erp.contractors(id uuid primary key);
    create table erp.contractor_hpp_policy_versions(id uuid primary key);
    create table erp.fg_lots(id uuid primary key);
    create table erp.fg_accessory_cost_snapshots(id uuid primary key,lot_id uuid,po_id uuid,product_id uuid,
      bom_version_id uuid,bom_item_id uuid,category_id uuid,good_qty_pcs integer,qty_per_good_fg_base numeric,
      hpp_method text,reimbursement_unit_rate_base_snapshot numeric,costing_basis_at timestamptz,costing_basis_source text);`)
  const originals=Object.fromEntries(Object.entries(origin.functions).map(([name,row])=>[name,readFileSync(resolve(here,row.file),'utf8')]))
  const rowtypes=new Set(Object.values(originals).flatMap(text=>[...text.matchAll(/\b(erp\.[a-z_0-9]+)%rowtype/gi)].map(m=>m[1])))
  for(const table of rowtypes)await db.exec('create table if not exists '+table+'(id uuid primary key)')
  for(const [name,body]of Object.entries(originals)){
    await db.exec(body)
    await db.exec('revoke all on function '+name+' from public')
    for(const [role,,privilege]of origin.functions[name].metadata.at(-1)){
      assert.equal(privilege,'EXECUTE');assert(['postgres','service_role'].includes(role))
      await db.exec('grant execute on function '+name+' to '+role)
    }
  }
  await db.exec("set search_path='';set timezone='UTC'")
  const before=await capture(),beforeAuthority=await authority()
  for(const [name,row]of Object.entries(origin.functions)){
    assert.equal(sha(before.functions[name][0]),row.sha256)
    assert.deepEqual(before.functions[name].slice(1),row.metadata)
  }
  await db.exec(readFileSync(resolve(here,'policy.sql'),'utf8'))
  await db.exec(readFileSync(resolve(here,'basis.sql'),'utf8'))
  const derived=execFileSync('python',['-B',resolve(here,'native_derivation.py'),'--sql'],{cwd:root,encoding:'utf8'})
  await db.exec(derived)
  const after=await capture()
  const fixture={before,after}
  const result=JSON.parse(execFileSync('python',['-B','-c',`
import sys,json
sys.path.insert(0,'scripts')
from cp7_accessory_nonpayable import composition as c
value=json.load(sys.stdin);definitions,_=c.native_derivation.derive(c.native_derivation.originals())
c.transition(value['before'],value['after'],definitions)
print(json.dumps(dict(status='ACTUAL_POSTGRES_CATALOGUE_TRANSITION_PASS',new_functions=len(c.FUNCTIONS),external_triggers=11)))
`],{cwd:root,input:JSON.stringify(fixture),encoding:'utf8',maxBuffer:1024*1024}))
  await test('ACTUAL_ALL22_ONLY_DECLARED_NATIVE_PRIVATE_AND_EXACT_RI_DELTA',async()=>assert.equal(result.status,'ACTUAL_POSTGRES_CATALOGUE_TRANSITION_PASS'))
  await test('SIX_NATIVE_RAW_OIDS_OWNERS_NULL_OR_EXPLICIT_ACLS_PRESERVED',async()=>assert.deepEqual(await authority(),beforeAuthority))
  await test('NO_SEEDED_POLICY_OR_GOOD_ROWS',async()=>{
    for(const table of ['category_versions_v1','good_bases_v1'])assert.equal((await q('select count(*)::int as n from cp7_accessory_nonpayable.'+table)).rows[0].n,0)
  })
  await test('PRIVATE_FUNCTION_OWNERS_SEARCH_PATH_AND_SECURITY',async()=>{
    for(const [name,row]of Object.entries(after.functions).filter(([name])=>name.startsWith('cp7_accessory_nonpayable.'))){
      assert.equal(row[1],'postgres');assert.deepEqual(row[12],['search_path=""'])
      const invoker=name.includes('.immutable_v1(')||name.includes('.timeline_token_v1(')||name.includes('.snapshot_identity_v1(')
      assert.equal(row[4],!invoker)
    }
  })
  for(const role of ['anon','authenticated','service_role','cp7_nonpayable_test'])await test('NO_PRIVATE_EXPOSURE:'+role,async()=>{
    assert.equal((await q("select has_schema_privilege($1,'cp7_accessory_nonpayable','USAGE,CREATE') as p",[role])).rows[0].p,false)
    for(const name of Object.keys(after.functions).filter(name=>name.startsWith('cp7_accessory_nonpayable.')))
      assert.equal((await q("select has_function_privilege($1,$2,'EXECUTE') as p",[role,name])).rows[0].p,false)
    for(const table of ['category_versions_v1','good_bases_v1'])assert.equal((await q("select has_table_privilege($1,$2,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') as p",[role,'cp7_accessory_nonpayable.'+table])).rows[0].p,false)
  })
  await test('BOTH_PRIVATE_TABLES_HAVE_RLS',async()=>{
    for(const table of ['category_versions_v1','good_bases_v1'])assert.equal((await q('select relrowsecurity as rls from pg_class where oid=$1::regclass',['cp7_accessory_nonpayable.'+table])).rows[0].rls,true)
  })
  // No data has been used. Execute the exact delta inverse and compare all22.
  for(const [name,body]of Object.entries(originals))if(name in before.functions && after.functions[name][0]!==before.functions[name][0])await db.exec(body)
  await db.exec('drop schema cp7_accessory_nonpayable cascade')
  await test('ACTUAL_PREUSE_DDL_INVERSE_RESTORES_ALL22_AND_NATIVE_RAW_AUTHORITY',async()=>{
    assert.deepEqual(await capture(),before);assert.deepEqual(await authority(),beforeAuthority)
  })
  report={status:'ISOLATED_POSTGRES_NONPAYABLE_CATALOGUE_AND_AUTHORITY_PASS',engine:(await q('select version() as v')).rows[0].v,
    checks,source_sha256:Object.fromEntries(['policy.sql','basis.sql','native_derivation.py','composition.py','ri_catalog.py',
      ...Object.values(origin.functions).map(row=>row.file)].map(f=>[f,sha(readFileSync(resolve(here,f)))])),
    unchanged_all22_query_source:{path:queriesSource,sha256:sha(readFileSync(resolve(root,queriesSource)))},
    actual_ERP_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,installed_on_candidate:false,
    full_installer_lifecycle_qualified:false,production_go:false,independent_acceptance:false}
}catch(error){report={status:'ISOLATED_POSTGRES_NONPAYABLE_CATALOGUE_FIRST_FAILURE',checks,error:String(error),
  actual_ERP_Native_cases:0,production_go:false,independent_acceptance:false};throw error}
finally{if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(report,null,2)+'\n');await db.close()}
process.stdout.write(JSON.stringify({status:report.status,checks:checks.length,actual_ERP_Native_cases:0})+'\n')
