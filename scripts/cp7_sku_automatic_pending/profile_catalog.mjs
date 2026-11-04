// Real PG17 DDL/ACL/all22/inverse checks in an empty isolated model.
// Only minimal dependency identities exist; no ERP financial command executes.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const input=JSON.parse(await readFile(process.env.CP7_AUTO_CATALOG_INPUT,'utf8'));
assert.equal(input.classification,'ISOLATED_AUTOMATIC_DDL_PROFILE_INPUT_NOT_ERP');
assert.equal(Object.keys(input.queries).length,22);
const db=new PGlite(),quote=s=>'"'+s.replaceAll('"','""')+'"';
const pin=s=>({bytes:Buffer.byteLength(s),sha256:createHash('sha256').update(s).digest('hex')});
const ownTables=[...input.product.ddl.matchAll(/^create table ([\w.]+)\(/gm)].map(m=>m[1]);
const baseline=input.product.replacement_before,dependencies=new Set();
for(const m of input.product.ddl.matchAll(/references\s+([\w.]+)\(id\)/gi))dependencies.add(m[1]);
for(const body of[input.product.ddl,...Object.values(input.product.definitions),...Object.values(baseline).map(r=>r[0])]){
 for(const m of body.matchAll(/([\w.]+)%rowtype/gi))dependencies.add(m[1]);
}
for(const name of ownTables)dependencies.delete(name);
let stage='SETUP';
try{
 const engine=(await db.query('select version()version')).rows[0].version;assert.match(engine,/^PostgreSQL 17\./);
 const roles=new Set(['anon','authenticated','service_role','cp7_fg_read']);
 for(const row of Object.values(baseline))for(const[role]of row[18])if(!['postgres','PUBLIC'].includes(role))roles.add(role);
 // PostgreSQL requires its bootstrap role to remain superuser. Keep that
 // identity intact and create a distinct ordinary owning role named postgres.
 // These two bootstrap identities exist only in the disposable model.
 for(const statement of[
  'create role model_profile_admin superuser',
  'set session authorization model_profile_admin',
  'alter role postgres rename to model_profile_bootstrap',
  'create role postgres nosuperuser'
 ]){stage='BOOTSTRAP_IDENTITY:'+statement.split(' ').slice(0,4).join(' ');await db.exec(statement);await db.query('select current_user,session_user');}
 stage='DEPENDENCY_ROLES';for(const role of roles)await db.exec('create role '+quote(role));
 // These schemas belong to the already-installed parent. The incremental
 // installer creates no schema and needs no database CREATE grant. A direct
 // template1 ACL edit failed in this fixture, so bootstrap only those existing
 // namespace identities, then do all dependency/new object DDL as their owner.
 stage='EXISTING_PARENT_SCHEMAS';await db.exec('create schema erp authorization postgres;create schema cp7_sku_conversion authorization postgres');
 stage='ORDINARY_OWNER';await db.exec('set role postgres');
 await db.exec("set search_path='';set timezone='UTC';set check_function_bodies=off;");
 stage='DEPENDENCY_TABLES';for(const table of dependencies)await db.exec('create table '+table+'(id uuid primary key)');
 stage='BASELINE_IMMUTABILITY';
 await db.exec("create function cp7_sku_conversion.immutable_v1()returns trigger language plpgsql as $$begin raise exception 'DDL_PROFILE_ONLY';end$$;");
 for(const[sig,row]of Object.entries(baseline)){
  stage='BASELINE_FUNCTION:'+sig;
  assert.equal(row[1],'postgres');await db.exec(row[0]);
  await db.exec('revoke all on function '+sig+' from public,'+[...roles].map(quote).join(','));
  for(const[role,grantor,permission,grantable]of row[18]){
   assert.equal(grantor,'postgres');assert.equal(permission,'EXECUTE');assert.equal(grantable,false);
   if(role!=='postgres')await db.exec('grant execute on function '+sig+' to '+(role==='PUBLIC'?'public':quote(role)));
  }
 }
 const installer=(await db.query("select current_user name,rolsuper from pg_roles where rolname=current_user")).rows[0];
 assert.equal(installer.name,'postgres');assert.equal(installer.rolsuper,false);
 const capture=async()=>{
  // The owning composition observes outside as_owner(postgres), then switches
  // only the DDL section. Keep the same separation: a privileged observer may
  // read all system metadata, while every new object is installed by postgres.
  await db.exec('set role model_profile_admin');
  try{
   const out={};for(const[group,sql]of Object.entries(input.queries)){
    const rows=(await db.query(sql)).rows;out[group]=Object.fromEntries(rows.map(r=>Object.values(r)));
    assert.equal(Object.keys(out[group]).length,rows.length,'Every catalogue identity must be unique: '+group);
   }return out;
  }finally{await db.exec('set role postgres');}
 };
 const before=await capture();
 for(const[sig,row]of Object.entries(baseline))assert.deepEqual(before.functions[sig],row,'Exact frozen money/Native row: '+sig);
 stage='INSTALL_INCREMENTAL_DDL';await db.exec(input.product.ddl);
 for(const definition of Object.values(input.product.definitions))await db.exec(definition);
 const after=await capture(),groups={},changed={};
 for(const group of Object.keys(before)){
  groups[group]={};changed[group]={};
  for(const[key,row]of Object.entries(after[group])){
   if(!Object.hasOwn(before[group],key))groups[group][key]=row;
   else if(JSON.stringify(before[group][key])!==JSON.stringify(row)){
    assert.equal(group,'functions','Existing non-function metadata remains exact: '+key);
    assert(Object.hasOwn(input.product.definitions,key),'Every changed function is predeclared: '+key);
    assert.deepEqual(row.slice(1),before[group][key].slice(1),'All original function metadata/ACL remain: '+key);
    changed[group][key]={before:before[group][key],after:row};
   }
  }
  assert(Object.keys(before[group]).every(k=>Object.hasOwn(after[group],k)),'No old object removed: '+group);
 }
 const additions=Object.keys(groups.functions);
 assert.equal(additions.length,10);assert.equal(Object.keys(changed.functions).length,9);
 assert.deepEqual(Object.keys(groups.relations).filter(k=>groups.relations[k][1]==='r').sort(),[...ownTables].sort());
 for(const sig of additions){const row=groups.functions[sig];assert.equal(row[1],'postgres');assert.equal(row[4],true);
  assert(row[12].includes('search_path=""'));assert.deepEqual(row[18],[['postgres','postgres','EXECUTE',false]]);}
 for(const table of ownTables){assert.equal(after.relations[table][0],'postgres');assert.equal(after.relations[table][3],true);}
 for(const role of roles){
  for(const sig of additions)assert.equal((await db.query("select has_function_privilege($1,$2,'EXECUTE')access",[role,sig])).rows[0].access,false);
  for(const table of ownTables)assert.equal((await db.query("select has_table_privilege($1,$2,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')access",[role,table])).rows[0].access,false);
 }
 const profile={contract:'cp7.sku-automatic-pending-catalogue-additions.v1',classification:'EXPECTED_POSTGRES17_DDL_ONLY_NOT_ERP_QUALIFICATION',
  engine,catalog_source_sha256:input.catalog_source_sha256,original_sha256:input.original_sha256,
  source_files:input.product.source_files,derived_ddl:pin(input.product.ddl),
  derived_replacements:Object.fromEntries(Object.entries(input.product.definitions).map(([sig,body])=>[sig,pin(body)])),
  groups,replacement_functions:Object.fromEntries(Object.keys(baseline).map(sig=>[sig,after.functions[sig]])),replacement_before:baseline,
  installer,catalogue_observer:'model_profile_admin',actual_ERP_cases:0,financial_functions_executed:0,production_go:false,independent_acceptance:false};
 stage='EXPLICIT_UNUSED_INVERSE';
 for(const row of Object.values(baseline))await db.exec(row[0]);
 for(const sig of [...additions].reverse())await db.exec('drop function '+sig);
 for(const table of [...ownTables].reverse())await db.exec('drop table '+table);
 const restored=await capture();assert.deepEqual(restored,before,'Explicit inverse restores every row in all22 groups');
 profile.explicit_unused_inverse_all22_exact=true;
 await writeFile(process.env.CP7_AUTO_CATALOG_PROFILE,JSON.stringify(profile,null,2)+'\n');
 const report={status:'POSTGRES17_AUTOMATIC_DDL_ALL22_ACL_UNUSED_INVERSE_PASS_NOT_ERP',engine,installer,catalogue_observer:'model_profile_admin',
  dependencies:[...dependencies],before,after,restored,changed,
  additions:Object.fromEntries(Object.entries(groups).map(([g,rows])=>[g,Object.keys(rows).length])),
  existing_function_attributes_and_ACL_exact:true,explicit_unused_inverse_all22_exact:true,
  financial_functions_executed:0,actual_ERP_cases:0,production_go:false,independent_acceptance:false};
 await writeFile(process.env.CP7_AUTO_CATALOG_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,additions:report.additions,changed_functions:Object.keys(changed.functions),actual_ERP_cases:0}));
}catch(error){
 const report={status:'FAILED',stage,error:{message:error.message,code:error.code,context:error.where,detail:error.detail,actual:error.actual,expected:error.expected},actual_ERP_cases:0};
 await writeFile(process.env.CP7_AUTO_CATALOG_REPORT,JSON.stringify(report,null,2)+'\n');console.error(JSON.stringify(report));process.exitCode=1;
}finally{await db.close();}
