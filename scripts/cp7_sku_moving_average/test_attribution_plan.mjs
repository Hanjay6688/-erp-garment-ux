// Exact candidate attribution INSERT on PostgreSQL17, synthetic source rows.
// This is an early planner/SQL check, not five Native ERP transactions.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const here=dirname(fileURLToPath(import.meta.url));
const ddl=await readFile(join(here,'valuation.sql'),'utf8');
const failed=" joined as(select coalesce(e.po_id,l.po_id)po_id,coalesce(e.effective,0)effective,coalesce(l.legacy,0)legacy from effective e full join legacy l on l.po_id is not distinct from e.po_id),\n";
const fixed=" keys as(select po_id from effective union select po_id from legacy),\n joined as(select k.po_id,coalesce(e.effective,0)effective,coalesce(l.legacy,0)legacy from keys k\n  left join effective e on e.po_id is not distinct from k.po_id\n  left join legacy l on l.po_id is not distinct from k.po_id),\n";
assert.equal(ddl.split(fixed).length,2);assert(!ddl.includes(failed));
const old=ddl.replace(fixed,failed);
assert.equal(createHash('sha256').update(old).digest('hex'),'ddbe7c1632ebe2f09b5df66229c1d71d96ca5a10eed091e9ef836c261dd40679');
const extract=sql=>{
 const fn=sql.split('create function cp7_sku_conversion.finalize_valuation_v2(p_group uuid) returns void');assert.equal(fn.length,2);
 const start=fn[1].indexOf(' with effective as('),end=fn[1].indexOf('\n for r in select *from cp7_sku_conversion.valuation_attributions_v2',start);
 assert(start>=0&&end>start);return fn[1].slice(start,end);
};
const statement=extract(ddl),oldStatement=extract(old);
const db=new PGlite(),results=[];
const id=n=>'72000000-0000-4000-8000-'+String(n).padStart(12,'0');
const group=id(1),source=id(2),target=id(3),poA=id(10),poB=id(11),poC=id(12),zero='00000000-0000-0000-0000-000000000000';
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
const wrapper=(name,sql)=>'create function public.'+name+'(p_group uuid,p_source uuid,p_target uuid)returns void language plpgsql as $body$declare q record;begin select p_source source_product_id,p_target target_product_id into q;'+sql+'end $body$;';
const cases=[
 {name:'NULL non-PO appears once and preserves its complete source/target values',effective:[[null,2000]],legacy:[[null,1000]]},
 {name:'Mixed PO and NULL scopes keep zero UUID distinct and include both one-sided scopes',effective:[[null,750],[poA,1250],[zero,25],[poB,0]],legacy:[[null,1000],[poA,1100],[poC,200],[zero,75]]},
 {name:'Effective-only scope retains zero legacy instead of disappearing',effective:[[poA,275]],legacy:[]},
 {name:'Legacy-only NULL scope retains zero effective instead of disappearing',effective:[],legacy:[[null,3599]]},
 {name:'Multiple contributors and allocations aggregate by identity before numbering',effective:[[null,1],[null,2],[poA,7],[poA,9]],legacy:[[null,3],[null,4],[poA,8],[poA,6]]},
 {name:'Both inputs empty produce no attribution rows',effective:[],legacy:[]},
 {name:'Zero-valued scopes are retained with stable NULL-last line numbers',effective:[[poA,0],[null,0]],legacy:[[zero,0],[null,0]]},
];
let engine;
try{
 engine=await scalar('select version()');assert.match(engine,/^PostgreSQL 17\./);
 await db.exec(`create schema erp;create schema cp7_sku_conversion;
 create table cp7_sku_conversion.valuation_contributors_v2(group_id uuid,po_id uuid,transfer_value numeric);
 create table cp7_sku_conversion.members_v1(group_id uuid,conversion_id uuid);
 create table erp.product_conversion_allocations(conversion_id uuid,source_lot_id uuid,qty_pcs integer,original_hpp_per_pcs numeric);
 create table erp.fg_lots(id uuid,po_id uuid);
 create table cp7_sku_conversion.valuation_attributions_v2(group_id uuid,phase text,side text,line_no integer,po_id uuid,product_id uuid,effective_value_delta numeric,legacy_value_delta numeric,adjustment_delta numeric);
 `+wrapper('candidate_attribution_sql',statement)+wrapper('failed_attribution_sql',oldStatement));
 await assert.rejects(()=>db.query('select public.failed_attribution_sql($1,$2,$3)',[group,source,target]),
  error=>error.code==='0A000'&&error.message==='FULL JOIN is only supported with merge-joinable or hash-joinable join conditions');
 results.push({label:'Exact retained first-failure INSERT reproduces PostgreSQL planner refusal',result:'EXPECTED_REFUSAL'});
 for(const test of cases){
  await db.exec('begin');try{
   for(const[po,cents]of test.effective)await db.query('insert into cp7_sku_conversion.valuation_contributors_v2 values($1,$2,$3::numeric/100)',[group,po,cents]);
   let count=100;for(const[po,cents]of test.legacy){const conversion=id(count++),lot=id(count++);
    await db.query('insert into cp7_sku_conversion.members_v1 values($1,$2)',[group,conversion]);
    await db.query('insert into erp.fg_lots values($1,$2)',[lot,po]);
    await db.query('insert into erp.product_conversion_allocations values($1,$2,1,$3::numeric/100)',[conversion,lot,cents]);
   }
   await db.query('select public.candidate_attribution_sql($1,$2,$3)',[group,source,target]);
   const observed=(await db.query("select phase,side,line_no,po_id,product_id,(effective_value_delta*100)::bigint::text effective,(legacy_value_delta*100)::bigint::text legacy,(adjustment_delta*100)::bigint::text adjustment from cp7_sku_conversion.valuation_attributions_v2 order by side,line_no")).rows;
   const values=new Map();for(const[key,rows]of[['effective',test.effective],['legacy',test.legacy]])for(const[po,cents]of rows){
    if(!values.has(po))values.set(po,{effective:0n,legacy:0n});values.get(po)[key]+=BigInt(cents);
   }
   const ids=[...values.keys()].sort((a,b)=>a===null?1:b===null?-1:a.localeCompare(b)),expected=[];
   for(const side of['SOURCE','TARGET'])for(const[rank,po]of ids.entries()){
    const v=values.get(po),sign=side==='SOURCE'?-1n:1n;
    expected.push({phase:'POST',side,line_no:rank+1,po_id:po,product_id:side==='SOURCE'?source:target,
     effective:String(sign*v.effective),legacy:String(sign*v.legacy),adjustment:String(sign*(v.effective-v.legacy))});
   }
   assert.deepEqual(observed,expected,test.name);
   assert.equal(await scalar('select count(*)from(select po_id from cp7_sku_conversion.valuation_attributions_v2 group by po_id having sum(effective_value_delta)<>0 or sum(legacy_value_delta)<>0 or sum(adjustment_delta)<>0)x'),0);
   results.push({label:test.name,result:'PASS'});
  }finally{await db.exec('rollback');}
 }
 const report={status:'POSTGRES17_EXACT_ATTRIBUTION_INSERT_PLANNER_AND_CENTS_PASS_NOT_NATIVE',engine,results,
  valuation_source:{bytes:Buffer.byteLength(ddl),sha256:createHash('sha256').update(ddl).digest('hex')},
  statement_sha256:createHash('sha256').update(statement).digest('hex'),modeled_dependencies:'Five synthetic input/output tables; wrapper supplies existing typed PL variables only',
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false};
 if(process.env.CP7_ATTRIBUTION_REPORT)await writeFile(process.env.CP7_ATTRIBUTION_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:results.length,actual_Native_cases:0}));
}catch(error){
 if(process.env.CP7_ATTRIBUTION_REPORT)await writeFile(process.env.CP7_ATTRIBUTION_REPORT,JSON.stringify({status:'FAILED',engine,results,error:{message:error.message,SQLSTATE:error.code??null},actual_Native_cases:0},null,2)+'\n');
 throw error;
}finally{await db.close();}
