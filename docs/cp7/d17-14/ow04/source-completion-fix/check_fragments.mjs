// Actual Native header UPDATE and unchanged final guard fragments only.
import fs from'node:fs';import path from'node:path';import assert from'node:assert/strict';
const{PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const dir=path.dirname(new URL(import.meta.url).pathname),f=JSON.parse(fs.readFileSync(dir+'/FRAGMENTS.json','utf8'));
fs.writeFileSync(dir+'/DECLARATION.json',JSON.stringify({classification:'ACTUAL_NATIVE_HEADER_UPDATE_AND_UNCHANGED_GUARD_FRAGMENTS_NOT_NATIVE_RUNTIME',expected:'Old midpoint rejects lawful stale header; after Native header update final predicate accepts exact monetary/status state; net-negative, paid-negative, paid-over-net still reject. No permission/poster/source-complete function stub.'},null,2)+'\n');
const db=new PGlite(),out=[];
try{
 await db.exec("create schema erp;create table erp.sales_headers(id uuid,status text);insert into erp.sales_headers values('00000000-0000-0000-0000-000000000001','POSTED')");
 for(const part of f.updates){
 const [oldStatus,net,paid]=part.function==='post_sales_payment'?['POSTED',60,60]:part.function==='reverse_sales_payment'?['PARTIAL_PAID',60,0]:['PAID',80,60];
 for(const version of['OLD_MIDPOINT','FINAL_TAIL']){
  await db.exec('begin');let error;
  const before=`select *into h from erp.sales_headers;select *into s from erp.sales_headers;`;
  const guard=`select *into h from erp.sales_headers;${f.unchanged_final_predicate}`;
  try{await db.exec(`update erp.sales_headers set status='${oldStatus}';do $$declare h record;s record;v_paid numeric:=${paid};v_total numeric:=${net};paid numeric:=${paid};net numeric:=${net};begin ${before}${version==='OLD_MIDPOINT'?guard+part.update:part.update+guard}end $$;`);}catch(e){error=e;}
  await db.exec('rollback');
  if(version==='OLD_MIDPOINT'){assert(error);assert(error.message.includes('CP7_NATIVE_EMPTY_FINAL_AR_OR_STATUS'));}else if(error)throw error;
  out.push({function:part.function,position:version,status:'PASS',observed_refusal:error?.message??null});
 }
 }
 for(const [net,paid]of[[-1,0],[60,-1],[60,61]]){
  await db.exec('begin');let e;
  try{await db.exec(`do $$declare h record;net numeric:=${net};paid numeric:=${paid};begin select *into h from erp.sales_headers;${f.unchanged_final_predicate}end $$;`);}catch(x){e=x;}
  await db.exec('rollback');assert(e);assert(e.message.includes('CP7_NATIVE_EMPTY_FINAL_AR_OR_STATUS'));out.push({negative:{net,paid},status:'PASS',observed_refusal:e.message});
 }
 const r={classification:'ISOLATED_ACTUAL_SQL_FRAGMENTS_NOT_NATIVE_POSTING_OR_AUTHORITY',status:'PASS',count:out.length,cases:out};fs.writeFileSync(dir+'/FRAGMENT_RESULT.json',JSON.stringify(r,null,2)+'\n');console.log(JSON.stringify({status:'PASS',count:out.length}));
}catch(e){fs.writeFileSync(dir+'/FIRST_FRAGMENT_FAILURE.json',JSON.stringify({error:e.message,code:e.code,cases:out},null,2)+'\n');console.error(e);process.exitCode=1;}finally{await db.close();}
