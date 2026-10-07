import fixture from './nativeAnalysisStandin.json'
import {sha} from './nativeAnalysisTransport'
// A staged run (P19 §10) built from the one-target stand-in: every target gets
// its own recommendation, action, metric, timeline items, demand model,
// material need and profile assumption (the stand-in's items with the keys
// swapped); every `unreviewed`-th target has an unreviewed production policy
// instead (one warning and one review-policy action). Served as the server
// shapes it: a page set with the inline header body, page reads with
// canonical bodies, and job statuses. Hashes are real SHA-256 values; the
// identity hash is sha256(header_sha256 "\n" page_sha256_0 "\n" …).
// `pageSizes` gives uneven, byte-adaptive-like pages; `perPage` even ones.
const bytes=(text:string)=>new TextEncoder().encode(text)
type Json=Record<string,any>
const FIELDS=['assumptions','generation_warnings','actions','recommendations','demand_models','material_needs','metrics','timeline'] as const
export const STAGED_CAPTURED_AT='2026-10-07T09:00:00.000000Z',STAGED_PROGRESS_AT='2026-10-07T09:05:30.000000Z'
export type StagedJobState='RUNNING'|'DONE'|'FAILED'
// A job status as erp_cp7_request/step/get_staged_analysis_v1 return it.
export function stagedJobFixture(requestId:string,state:StagedJobState,extra:Json={}){
 return{contract_version:'cp7.native-analysis-staged-job.v1',request_id:requestId,state,stage:state==='DONE'?null:'HIST_ROWS',stage_index:state==='DONE'?9:3,stage_count:9,
  units_done:state==='DONE'?55:12,unit_count:55,plan_final:state==='DONE',targets_total:5000,targets_done_in_stage:state==='DONE'?0:1200,
  reference:{captured_at:STAGED_CAPTURED_AT,source_hash:fixture.analysis.snapshot.source_hash},last_progress_at:STAGED_PROGRESS_AT,unit_attempts:0,
  run_id:state==='DONE'?fixture.run_id:null,failure:state==='FAILED'?{unit:12,sqlstate:'42501',code:'CP7_ANALYSIS_ACCESS_CHANGED'}:null,apply_enabled:false,production_go:false,...extra}
}
// itemRanges: a server defect where page p holds the items of other targets
// than the range it claims (hashes, counts and totals all consistent).
export async function stagedRun({targets,perPage,pageSizes,unreviewed=0,requestId=fixture.request_id,itemRanges,capturedAt=STAGED_CAPTURED_AT}:{targets:number;perPage?:number;pageSizes?:number[];unreviewed?:number;requestId?:string;itemRanges?:[number,number][];capturedAt?:string}){
 const base=structuredClone(fixture) as Json,a=base.analysis as Json,key0:string=a.recommendations[0].target.key,[root0,size]=key0.split(':'),profile0:string=a.assumptions[1].id
 const states=['ACTIVE','ACTIVE','PAUSED','STOPPED']
 const per:Record<string,unknown[]>[]=[],labels:Json[]=[]
 for(let i=0;i<targets;i++){
  const root=i===0?root0:`00000000-0000-4000-8000-1${i.toString(16).padStart(11,'0')}`,key=`${root}:${size}`,profile=i===0?profile0:`ce000000-0000-4000-8000-${i.toString(16).padStart(12,'0')}`
  const swap=(v:unknown)=>JSON.parse(JSON.stringify(v).replaceAll(key0,key).replaceAll(root0,root).replaceAll(profile0,profile))
  labels.push({target_key:key,sku:i===0?'TEST':`SKU-${i}`,product_name:i===0?'TEST':`Produk ${i}`})
  if(i>0&&unreviewed>0&&i%unreviewed===unreviewed-1){
   per.push({assumptions:[],generation_warnings:[`PRODUCTION_POLICY_UNREVIEWED:${key}`],recommendations:[],demand_models:[],material_needs:[],metrics:[],timeline:[],
    actions:[{...swap(a.actions[0]),key:`review-policy-${key}`,target_keys:[],primary_reason:'PRODUCTION_POLICY_UNREVIEWED',conditional:false,
     display_priority:{lane:'REVIEW_DATA',rank:null,basis:['Status produksi produk perlu diperiksa'],rule_version:'native-review-1'}}]})
   continue
  }
  per.push({assumptions:[swap(a.assumptions[1])],generation_warnings:[],actions:[swap(a.actions[0])],recommendations:[{...swap(a.recommendations[0]),production_state:states[i%4]}],
   demand_models:[swap(a.demand_models[0])],material_needs:[swap(a.material_needs[0])],metrics:[swap(a.metrics[0])],timeline:a.timeline.slice(0,2).map(swap)})
 }
 // Global items stay in the header: the schedule assumption before the
 // per-target assumptions and the three run warnings before the per-target
 // ones. The header carries no semantic hash (a staged run has none).
 const prefix:Record<string,number>={assumptions:1,generation_warnings:3}
 const header:Json={...a,assumptions:[a.assumptions[0]],generation_warnings:a.generation_warnings,actions:[],recommendations:[],demand_models:[],material_needs:[],metrics:[],timeline:[]}
 delete header.semantic_hash
 const paged:Json={}
 for(const k of FIELDS){const n=per.reduce((s,t)=>s+t[k].length,0);if(n>0)paged[k]={prefix:prefix[k]??0,items:n}}
 const keys=FIELDS.filter(k=>paged[k])
 // The whole analysis the pages reassemble (the single build's shape, with
 // its semantic hash), kept for parity checks only.
 const analysis:Json={...header,semantic_hash:a.semantic_hash};for(const k of keys)analysis[k]=[...header[k].slice(0,paged[k].prefix),...per.flatMap(t=>t[k]),...header[k].slice(paged[k].prefix)]
 labels.sort((x,y)=>x.target_key<y.target_key?-1:1)
 const original={contract_version:'cp7.native-analysis-run.v1',run_id:base.run_id,request_id:requestId,analysis,product_labels:labels,query:base.query,financial_source:null,apply_enabled:false,production_go:false}
 const sizes=pageSizes??Array.from({length:Math.ceil(targets/(perPage??(targets||1)))},(_,p)=>Math.min(perPage??targets,targets-p*(perPage??targets)))
 if(sizes.reduce((s,x)=>s+x,0)!==targets||sizes.some(s=>s<1))throw Error('page sizes must cover the targets')
 const ranges:[number,number][]=[];let at=1;for(const s of sizes){ranges.push([at,at+s-1]);at+=s}
 const pageCount=ranges.length
 const headerDoc={contract_version:'cp7.native-analysis-header.v1',run_id:base.run_id,request_id:requestId,query:base.query,financial_source:null,product_labels:labels,analysis_header:header,
  paged,targets_total:targets,page_count:pageCount,apply_enabled:false,production_go:false}
 const headerBody=JSON.stringify(headerDoc),headerSha=await sha(headerBody)
 const pages:Json[]=[],bodies:string[]=[],running:Record<string,number>={}
 const rec={ACTIVE:0,PAUSED:0,STOPPED:0,OTHER:0} as Record<string,number>;let policy=0
 for(let p=0;p<pageCount;p++){
  const[lo,hi]=ranges[p],slice=itemRanges?per.slice(itemRanges[p][0]-1,itemRanges[p][1]):per.slice(lo-1,hi)
  const items:Json={},counts:Json={},offsets:Json={},totals:Json={}
  for(const k of keys){items[k]=slice.flatMap(t=>t[k]);counts[k]=items[k].length;offsets[k]=running[k]??0;running[k]=(running[k]??0)+counts[k];totals[k]=paged[k].items}
  const summary={recommendations:{ACTIVE:0,PAUSED:0,STOPPED:0,OTHER:0} as Record<string,number>,policy_unreviewed:0}
  for(const r of items.recommendations??[])summary.recommendations[['ACTIVE','PAUSED','STOPPED'].includes(r.production_state)?r.production_state:'OTHER']++
  summary.policy_unreviewed=(items.actions??[]).filter((x:Json)=>x.primary_reason==='PRODUCTION_POLICY_UNREVIEWED').length
  for(const s of Object.keys(rec))rec[s]+=summary.recommendations[s];policy+=summary.policy_unreviewed
  const body=JSON.stringify({contract_version:'cp7.native-analysis-page.v1',run_id:base.run_id,request_id:requestId,index:p,page_count:pageCount,target_lo:lo,target_hi:hi,targets_total:targets,
   header_sha256:headerSha,counts,offsets,totals,summary,items,apply_enabled:false,production_go:false})
  bodies.push(body);pages.push({index:p,target_lo:lo,target_hi:hi,utf8_bytes:bytes(body).byteLength,sha256:await sha(body),counts})
 }
 const identityHash=await sha(headerSha+'\n'+pages.map(p=>p.sha256 as string).join('\n'))
 const reference={captured_at:capturedAt,source_hash:a.snapshot.source_hash as string}
 const pageSet={contract_version:'cp7.native-analysis-pages.v1',run_id:base.run_id,request_id:requestId,reference,access_epoch:'a'.repeat(64),identity_hash:identityHash,
  targets_total:targets,page_count:pageCount,paged,
  totals:{targets,items:Object.fromEntries(keys.map(k=>[k,paged[k].items])),recommendations:rec,policy_unreviewed:policy},
  header:{utf8_bytes:bytes(headerBody).byteLength,sha256:headerSha,body:headerBody},pages,apply_enabled:false,production_go:false}
 const page=(i:number)=>({contract_version:'cp7.native-analysis-page-read.v1',run_id:base.run_id,index:i,page_count:pageCount,target_lo:pages[i].target_lo,target_hi:pages[i].target_hi,
  header_sha256:headerSha,identity_hash:identityHash,utf8_bytes:pages[i].utf8_bytes,sha256:pages[i].sha256,body:bodies[i]})
 const job=(state:StagedJobState,extra:Json={})=>stagedJobFixture(requestId,state,{targets_total:targets,reference,run_id:state==='DONE'?base.run_id:null,...extra})
 return{pageSet,page,headerDoc,bodies,original,query:base.query as {from_date:string;through_date:string;group_mode:'AS_SOLD'|'RESTATED'},actor:a.scope.actor_scope_id as string,runId:base.run_id as string,identityHash,headerSha,reference,job}
}
// Re-serves a changed page body with a consistent envelope hash and size, so
// only the page set or the page's own content can catch the change.
export async function rehash(envelope:Json,body:string){return{...envelope,body,utf8_bytes:bytes(body).byteLength,sha256:await sha(body)}}
