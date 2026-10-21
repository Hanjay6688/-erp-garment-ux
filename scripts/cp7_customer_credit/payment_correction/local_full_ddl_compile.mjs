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
for(const[name,sql]of paymentFragments)await exec('PAYMENT_SOURCE_'+name,sql);
for(const[name,sql]of Object.entries(paymentDerived))await exec('PAYMENT_SOURCE_DERIVED_'+name,sql);
assert.equal(Object.keys(paymentDerived).length,20);
console.log(JSON.stringify({classification:'LOCAL_PAYMENT_SOURCE_DDL_ONLY_NOT_NATIVE_EXECUTION',compiled_fragments:paymentFragments.length,compiled_derivations:Object.keys(paymentDerived).length,check_function_bodies_enabled:true}));
`+anchor);
await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
