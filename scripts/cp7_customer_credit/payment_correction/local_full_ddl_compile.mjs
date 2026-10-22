// Reuse the unchanged full aligned-schema compiler, adding this exact owning
// stage with check_function_bodies enabled. Compilation, never Native finance.
import{readFileSync}from'node:fs';
import{pathToFileURL}from'node:url';
if(process.env.OW04_PGLITE_MODULE?.startsWith('/'))process.env.OW04_PGLITE_MODULE=pathToFileURL(process.env.OW04_PGLITE_MODULE).href;
const previous=new URL('../consumer/local_full_ddl_compile.mjs',import.meta.url);
let source=readFileSync(previous,'utf8');
const replace=(before,after)=>{
 if(source.split(before).length!==2)throw Error('Exact predecessor compiler anchor changed');
 source=source.replace(before,after);
};
replace("const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');",
 `const read=p=>readFileSync(new URL(p,${JSON.stringify(previous.href)}),'utf8');`);
const anchor="await exec('REMOVE_TEMPORARY_CREATE',";
replace(anchor,`
const paymentFragments=JSON.parse(readFileSync(process.env.OW04_LOCAL_PAYMENT_FRAGMENTS,'utf8'));
const paymentDerived=JSON.parse(readFileSync(process.env.OW04_LOCAL_PAYMENT_DERIVED,'utf8'));
await exec('ACCEPTED_TERMINAL_HEADER_DEPENDENCY',accepted.catalog.functions['cp7_credit.source_native_terminal_header_v1(jsonb,jsonb,uuid)'][0]);
await exec('ACTUAL_APPROVED_NATIVE_HEADER_CLOCK',accepted.catalog.functions['erp.touch_updated_at()'][0]);
const catalogInput=process.env.OW04_LOCAL_PAYMENT_CATALOG_INPUT?JSON.parse(readFileSync(process.env.OW04_LOCAL_PAYMENT_CATALOG_INPUT,'utf8')):null;
async function catalogRows(){
 const result={};
 for(const[group,query]of Object.entries(catalogInput.queries)){
  const rows=(await db.query(query)).rows;
  result[group]=Object.fromEntries(rows.map(row=>Object.values(row)));
 }
 return result;
}
let catalogBefore;
if(catalogInput){
 for(const[name,sql]of Object.entries(catalogInput.predecessor_definitions))await exec('ACTUAL_CURRENT_PREDECESSOR_'+name,sql);
 await exec('CATALOG_SEARCH_PATH',"set search_path=''");
 catalogBefore=await catalogRows();
}
for(const[name,sql]of paymentFragments)await exec('PAYMENT_SOURCE_'+name,sql);
for(const[name,sql]of Object.entries(paymentDerived))await exec('PAYMENT_SOURCE_DERIVED_'+name,sql);
assert.equal(Object.keys(paymentDerived).length,25);
if(catalogInput){
 const rows=(await db.query("select p.oid::regprocedure::text as signature,n.nspname||'.'||p.proname as name from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname||'.'||p.proname=any($1::text[])",[catalogInput.new_function_names])).rows;
 assert.equal(rows.length,catalogInput.new_function_names.length);
 for(const row of rows){
  await exec('PRIVATE_OWNER_'+row.signature,'alter function '+row.signature+' owner to postgres');
  await exec('PRIVATE_ACL_'+row.signature,'revoke all on function '+row.signature+' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write');
 }
 const catalogAfter=await catalogRows();
 const{writeFileSync}=await import('node:fs');
 writeFileSync(process.env.OW04_LOCAL_PAYMENT_CATALOG_OUTPUT,JSON.stringify({classification:'LOCAL_POSTGRES_DDL_CATALOG_TRANSITION_NOT_NATIVE_FINANCE',before:catalogBefore,after:catalogAfter,new_signatures:rows.map(row=>row.signature)}));
 console.log(JSON.stringify({classification:'LOCAL_ACTUAL_DDL_CATALOG_CAPTURE',groups:Object.keys(catalogAfter).length,new_functions:rows.length,financial_execution:false}));
}
if(process.env.OW04_LOCAL_BINDING_EQUIVALENCE_SQL){
 const checks=await db.exec(readFileSync(process.env.OW04_LOCAL_BINDING_EQUIVALENCE_SQL,'utf8'));
 console.log(JSON.stringify({classification:'LOCAL_BINDING_PROJECTION_EQUIVALENCE_NOT_NATIVE_FINANCE',result:checks.at(-1).rows}));
}
console.log(JSON.stringify({classification:'LOCAL_PAYMENT_SOURCE_DDL_ONLY_NOT_NATIVE_EXECUTION',compiled_fragments:paymentFragments.length,compiled_derivations:Object.keys(paymentDerived).length,check_function_bodies_enabled:true}));
`+anchor);
await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
