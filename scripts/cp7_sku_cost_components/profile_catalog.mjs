// Exact empty PostgreSQL 17 DDL, metadata/ACL and explicit unused inverse.
// Minimal dependency tables are not an ERP database; no financial function runs.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const input=JSON.parse(await readFile(process.env.CP7_COST_CATALOG_INPUT,'utf8'));
assert.equal(input.classification,'ISOLATED_DDL_PROFILE_INPUT_NOT_ERP');
assert.equal(Object.keys(input.queries).length,22);
const db=new PGlite(),quote=s=>'"'+s.replaceAll('"','""')+'"';
const pin=s=>({bytes:Buffer.byteLength(s),sha256:createHash('sha256').update(s).digest('hex')});
const ownTables=[...input.product.ddl.matchAll(/^create table ([\w.]+)\(/gm)].map(m=>m[1]);
const oldTables=[...input.parent_valuation_sql.matchAll(/^create table ([\w.]+)\(/gm)].map(m=>m[1]);
const dependencies=new Map();
for(const match of(input.parent_valuation_sql+'\n'+input.product.ddl).matchAll(/references\s+([\w.]+)\((\w+)\)/gi)){
 if(ownTables.includes(match[1])||oldTables.includes(match[1]))continue;
 const old=dependencies.get(match[1]);assert(!old||old===match[2]);dependencies.set(match[1],match[2]);
}
let stage='SETUP';
try{
 const engine=(await db.query('select version()version')).rows[0].version;assert.match(engine,/^PostgreSQL 17\./);
 await db.exec("create schema erp;create schema cp7_sku_conversion;create schema cp7_credit;create role anon;create role authenticated;create role service_role;create role cp7_fg_read;set search_path='';set timezone='UTC';set check_function_bodies=off;");
 for(const[table,column]of dependencies){
  const status=['erp.sales_headers','erp.sales_returns'].includes(table)?',status text':'';
  await db.exec('create table '+table+'('+quote(column)+' uuid primary key'+status+')');
 }
 await db.exec("create function cp7_sku_conversion.immutable_v1()returns trigger language plpgsql as $$begin raise exception 'DDL_PROFILE_ONLY';end$$;");
 await db.exec(input.parent_valuation_sql);
 for(const[sig,row]of Object.entries(input.baseline_functions)){
  assert.equal(row[1],'postgres');
  await db.exec(row[0]);
  await db.exec('revoke all on function '+sig+' from public,anon,authenticated,service_role,cp7_fg_read');
  for(const[role,grantor,permission,grantable]of row[18]){
   assert.equal(grantor,'postgres');assert.equal(permission,'EXECUTE');assert.equal(grantable,false);
   if(role==='postgres')continue;
   await db.exec('grant execute on function '+sig+' to '+(role==='PUBLIC'?'public':quote(role)));
  }
 }
 await db.exec('grant usage on schema cp7_sku_conversion to cp7_fg_read');
 const capture=async()=>{
  const out={};for(const[group,sql]of Object.entries(input.queries)){
   const rows=(await db.query(sql)).rows;out[group]=Object.fromEntries(rows.map(r=>Object.values(r)));
   assert.equal(Object.keys(out[group]).length,rows.length,'Every catalogue identity must be unique: '+group);
  }return out;
 };
 const before=await capture();
 for(const[sig,row]of Object.entries(input.baseline_functions))assert.deepEqual(before.functions[sig],row,'Exact parent function and all18 metadata attributes: '+sig);
 stage='INSTALL_PREPARED_DDL';await db.exec(input.product.ddl);
 for(const definition of Object.values(input.product.definitions))await db.exec(definition);
 const after=await capture(),groups={},changed={};
 for(const group of Object.keys(before)){
  groups[group]={};changed[group]={};
  for(const[key,row]of Object.entries(after[group])){
   if(!Object.hasOwn(before[group],key))groups[group][key]=row;
   else if(JSON.stringify(before[group][key])!==JSON.stringify(row)){
    assert.equal(group,'functions','Existing non-function metadata cannot change: '+key);
    assert(Object.hasOwn(input.product.definitions,key),'Only an exact declared replacement may change: '+key);
    assert.deepEqual(row.slice(1),before[group][key].slice(1),'All18 original function attributes must remain: '+key);
    changed[group][key]={before:before[group][key],after:row};
   }
  }
  assert(Object.keys(before[group]).every(k=>Object.hasOwn(after[group],k)),'No original catalogue object removed: '+group);
 }
 const additions=Object.keys(groups.functions);
 assert.deepEqual(Object.keys(groups.relations).filter(k=>groups.relations[k][1]==='r').sort(),[...ownTables].sort());
 for(const sig of additions){
  const row=groups.functions[sig];assert.equal(row[1],'postgres');assert.equal(row[4],true);
  assert(row[12].includes('search_path=""'));assert.deepEqual(row[18],[['postgres','postgres','EXECUTE',false]]);
 }
 for(const table of ownTables){const row=after.relations[table];assert.equal(row[0],'postgres');assert.equal(row[3],true);}
 for(const role of['anon','authenticated','service_role','cp7_fg_read']){
  for(const sig of additions)assert.equal((await db.query("select has_function_privilege($1,$2,'EXECUTE')access",[role,sig])).rows[0].access,false);
  for(const table of ownTables)assert.equal((await db.query("select has_table_privilege($1,$2,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')access",[role,table])).rows[0].access,false);
 }
 const replacementFunctions=Object.fromEntries(Object.keys(input.product.definitions).map(sig=>[sig,after.functions[sig]]));
 const baselineReplacements=Object.fromEntries(Object.keys(input.product.definitions).map(sig=>[sig,before.functions[sig]]));
 const profile={contract:'cp7.sku-cost-money-catalogue-additions.v1',classification:'EXPECTED_POSTGRES17_DDL_ONLY_NOT_ERP_QUALIFICATION',
  engine,catalog_source_sha256:input.catalog_source_sha256,original_sha256:input.original_sha256,
  source_files:input.product.source_files,derived_ddl:pin(input.product.ddl),derived_replacements:Object.fromEntries(Object.entries(input.product.definitions).map(([s,d])=>[s,pin(d)])),
  groups,replacement_functions:replacementFunctions,replacement_before:baselineReplacements,
  actual_ERP_cases:0,financial_functions_executed:0,production_go:false,independent_acceptance:false};
 stage='EXPLICIT_UNUSED_INVERSE';
 for(const[sig,row]of Object.entries(baselineReplacements))await db.exec(row[0]);
 for(const sig of [...additions].reverse())await db.exec('drop function '+sig);
 for(const table of [...ownTables].reverse())await db.exec('drop table '+table);
 const restored=await capture();assert.deepEqual(restored,before,'Explicit inverse restores every original all22 row');
 profile.explicit_unused_inverse_all22_exact=true;
 await writeFile(process.env.CP7_COST_CATALOG_PROFILE,JSON.stringify(profile,null,2)+'\n');
 const report={status:'POSTGRES17_COST_MONEY_DDL_ALL22_ACL_UNUSED_INVERSE_PASS_NOT_NATIVE',engine,
  dependencies:Object.fromEntries(dependencies),source_files:input.product.source_files,before,after,restored,changed,
  additions:Object.fromEntries(Object.entries(groups).map(([g,r])=>[g,Object.keys(r).length])),
  existing_function_all18_attributes_preserved:true,explicit_unused_inverse_all22_exact:true,
  financial_functions_executed:0,actual_ERP_cases:0,production_go:false,independent_acceptance:false};
 await writeFile(process.env.CP7_COST_CATALOG_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,additions:report.additions,changed_functions:Object.keys(changed.functions),actual_ERP_cases:0}));
}catch(error){
 const report={status:'FAILED',stage,error:{message:error.message,code:error.code,context:error.where,detail:error.detail,actual:error.actual,expected:error.expected},actual_ERP_cases:0};
 await writeFile(process.env.CP7_COST_CATALOG_REPORT,JSON.stringify(report,null,2)+'\n');console.error(JSON.stringify(report));process.exitCode=1;
}finally{await db.close();}
