import type {AnalysisResult} from './cp7/contract'
import type {NativeDemandQuery} from './nativeDemandHistory'
import {analysisSchemaMatches,analysisHeaderSchemaMatches,assertAnalysisFacts,assertMaterialNeed,financeSource,pcs,type AnalysisFinanceAccess} from './nativeAnalysis'

// P19 staged run (schema cp7_analysis_stage; P19 plan §10) read BY TARGET
// RANGE. A staged run is NOT a cp7_analysis_native.runs row: it has no
// document, no segments and no semantic hash. Its identity is
//   identity_hash = sha256(header_sha256 || "\n" || page_sha256_0 || "\n" || …)
// over the header and the pages in index order. The client recomputes that
// hash from the listed hashes, verifies the header body against its listed
// size and hash, every page body against the page set, and refuses whatever
// disagrees. Pages are byte-adaptive (≤ 8,000,000 UTF-8 bytes each), so the
// target ranges are uneven; a page is only ever shown as "Target a–b dari N"
// and every whole-run number comes from the server's page set, never from the
// visible page. Source freshness is a separate RPC (no source_state here).
export const ANALYSIS_PAGE_UTF8_BYTES=8000000
export const ANALYSIS_HEADER_UTF8_BYTES=8000000
// The staged job's declared capacity.
export const ANALYSIS_STAGED_TARGETS=5000
export const ANALYSIS_PAGED_FIELDS=['assumptions','generation_warnings','actions','recommendations','demand_models','material_needs','metrics','timeline'] as const
export type PagedField=typeof ANALYSIS_PAGED_FIELDS[number]
type States={ACTIVE:number;PAUSED:number;STOPPED:number;OTHER:number}
export type StagedReference={capturedAt:string;sourceHash:string}
export type AnalysisPageEntry={index:number;targetLo:number;targetHi:number;utf8Bytes:number;sha256:string;counts:Partial<Record<PagedField,number>>;offsets:Partial<Record<PagedField,number>>}
export type AnalysisPageSet={runId:string;requestId:string;reference:StagedReference;accessEpoch:string;identityHash:string
 targetsTotal:number;pageCount:number;paged:Partial<Record<PagedField,{prefix:number;items:number}>>
 totals:{targets:number;items:Partial<Record<PagedField,number>>;recommendations:States;policyUnreviewed:number}
 header:{utf8Bytes:number;sha256:string;body:string};pages:AnalysisPageEntry[]}
// The analysis without its per-target items and without a semantic hash:
// every paged array holds only its global items. It is NOT an analysis of
// the whole run and is never passed to the whole-run views, reports or prompts.
export type AnalysisHeaderResult=Omit<AnalysisResult,'semantic_hash'>
export type AnalysisHeader={runId:string;requestId:string;query:NativeDemandQuery;analysisHeader:AnalysisHeaderResult;labels:{key:string;sku:string;name:string}[]}
export type StagedAnalysis={kind:'STAGED';set:AnalysisPageSet;header:AnalysisHeader}
export type AnalysisPageItems={assumptions:AnalysisResult['assumptions'];generation_warnings:string[];actions:AnalysisResult['actions'];recommendations:AnalysisResult['recommendations']
 demand_models:AnalysisResult['demand_models'];material_needs:AnalysisResult['material_needs'];metrics:AnalysisResult['metrics'];timeline:AnalysisResult['timeline']}
export type AnalysisPage={runId:string;index:number;targetLo:number;targetHi:number;items:AnalysisPageItems;summary:{recommendations:States;policyUnreviewed:number}}
export type StagedSourceCheck={sourceState:'UNCHANGED'|'ARCHIVED_STALE';checkedAt:string}

function fail():never{throw Error('Halaman analisis server belum sesuai sumber dan kontrak CP7.')}
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const uuid=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const exact=(v:Record<string,unknown>,keys:readonly string[])=>{if(Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))fail()}
const hex64=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const count=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max?v:fail()
// A server instant: ISO 8601 with an explicit offset, parseable.
export const stagedInstant=(v:unknown):string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const sha256=async(bytes:Uint8Array<ArrayBuffer>)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('')
const STATES=['ACTIVE','PAUSED','STOPPED','OTHER'] as const
const pagedKeys=(m:AnalysisPageSet)=>ANALYSIS_PAGED_FIELDS.filter(k=>m.paged[k]!==undefined)
const sameKeys=(v:Record<string,unknown>,keys:readonly string[])=>exact(v,keys)
function states(v:unknown):States{const s=object(v);exact(s,STATES);return{ACTIVE:count(s.ACTIVE,0,ANALYSIS_STAGED_TARGETS),PAUSED:count(s.PAUSED,0,ANALYSIS_STAGED_TARGETS),STOPPED:count(s.STOPPED,0,ANALYSIS_STAGED_TARGETS),OTHER:count(s.OTHER,0,ANALYSIS_STAGED_TARGETS)}}
const stateSum=(s:States)=>s.ACTIVE+s.PAUSED+s.STOPPED+s.OTHER
const group=(n:number)=>String(n).replace(/\B(?=(\d{3})+(?!\d))/g,'.')
// "Target 501–1.000 dari 5.000": the visible range and the whole run's count.
export const stagedRangeLabel=(lo:number,hi:number,total:number)=>`Target ${group(lo)}–${group(hi)} dari ${group(total)}`
export const stagedNumber=group
export function parseStagedReference(v:unknown):StagedReference{const r=object(v);exact(r,['captured_at','source_hash']);return{capturedAt:stagedInstant(r.captured_at),sourceHash:hex64(r.source_hash)}}
// The run's identity over its header and pages, in index order (§10).
export const stagedIdentityHash=(headerSha256:string,pageSha256s:readonly string[])=>sha256(new TextEncoder().encode(headerSha256+'\n'+pageSha256s.join('\n')))

export async function parseAnalysisPageSet(v:unknown,runId:string,expectedRequestId:string|null):Promise<AnalysisPageSet>{
 const e=object(v);exact(e,['contract_version','run_id','request_id','reference','access_epoch','identity_hash','targets_total','page_count','paged','totals','header','pages','apply_enabled','production_go'])
 const requestId=uuid(e.request_id)
 if(e.contract_version!=='cp7.native-analysis-pages.v1'||e.apply_enabled!==false||e.production_go!==false||uuid(e.run_id)!==runId||(expectedRequestId!==null&&requestId!==expectedRequestId))fail()
 const reference=parseStagedReference(e.reference),accessEpoch=hex64(e.access_epoch),identityHash=hex64(e.identity_hash)
 const targetsTotal=count(e.targets_total,0,ANALYSIS_STAGED_TARGETS),pageCount=count(e.page_count,0,targetsTotal)
 if((pageCount===0)!==(targetsTotal===0))fail()
 const pagedRaw=object(e.paged),paged:AnalysisPageSet['paged']={}
 for(const[k,raw]of Object.entries(pagedRaw)){if(!(ANALYSIS_PAGED_FIELDS as readonly string[]).includes(k))fail();const p=object(raw);exact(p,['prefix','items']);paged[k as PagedField]={prefix:count(p.prefix,0,Number.MAX_SAFE_INTEGER),items:count(p.items,1,Number.MAX_SAFE_INTEGER)}}
 const keys=ANALYSIS_PAGED_FIELDS.filter(k=>paged[k]!==undefined)
 if(targetsTotal===0?keys.length!==0:paged.actions===undefined)fail()
 // Whole-run totals: every target is one recommendation or one unreviewed
 // production policy; item totals equal the paged counts.
 const t=object(e.totals);exact(t,['targets','items','recommendations','policy_unreviewed'])
 const items=object(t.items);sameKeys(items,keys);const totalItems:Partial<Record<PagedField,number>>={}
 for(const k of keys){if(items[k]!==paged[k]!.items)fail();totalItems[k]=paged[k]!.items}
 const recommendations=states(t.recommendations),policyUnreviewed=count(t.policy_unreviewed,0,targetsTotal)
 if(t.targets!==targetsTotal||stateSum(recommendations)!==(paged.recommendations?.items??0)||stateSum(recommendations)+policyUnreviewed!==targetsTotal||(paged.actions?.items??0)!==targetsTotal)fail()
 // The header is inline: its listed size and hash must be the body's.
 const h=object(e.header);exact(h,['utf8_bytes','sha256','body']);if(typeof h.body!=='string')fail()
 const header={utf8Bytes:count(h.utf8_bytes,1,ANALYSIS_HEADER_UTF8_BYTES),sha256:hex64(h.sha256),body:h.body}
 const headerBytes=new TextEncoder().encode(header.body);if(headerBytes.byteLength!==header.utf8Bytes||await sha256(headerBytes)!==header.sha256)fail()
 // Pages: indexes 0..n-1, target ranges contiguous over 1..total (uneven
 // sizes allowed), counts summing to the whole-run items; offsets follow.
 if(!Array.isArray(e.pages)||e.pages.length!==pageCount)fail()
 let next=1;const running:Partial<Record<PagedField,number>>={}
 const pages=e.pages.map((raw,i):AnalysisPageEntry=>{
  const p=object(raw);exact(p,['index','target_lo','target_hi','utf8_bytes','sha256','counts'])
  if(p.index!==i||p.target_lo!==next)fail()
  const targetHi=count(p.target_hi,next,targetsTotal),c=object(p.counts);sameKeys(c,keys)
  const counts:AnalysisPageEntry['counts']={},offsets:AnalysisPageEntry['offsets']={}
  for(const k of keys){counts[k]=count(c[k],0,Number.MAX_SAFE_INTEGER);offsets[k]=running[k]??0;running[k]=(running[k]??0)+counts[k]!}
  const entry={index:i,targetLo:next,targetHi,utf8Bytes:count(p.utf8_bytes,1,ANALYSIS_PAGE_UTF8_BYTES),sha256:hex64(p.sha256),counts,offsets}
  next=targetHi+1;return entry
 })
 if(next!==targetsTotal+1||keys.some(k=>running[k]!==paged[k]!.items))fail()
 // The identity the server states must be the one the listed hashes give.
 if(await stagedIdentityHash(header.sha256,pages.map(p=>p.sha256))!==identityHash)fail()
 return{runId,requestId,reference,accessEpoch,identityHash,targetsTotal,pageCount,paged,totals:{targets:targetsTotal,items:totalItems,recommendations,policyUnreviewed},header,pages}
}

async function verifiedText(body:unknown,utf8Bytes:number,hash:string){
 if(typeof body!=='string')fail()
 const bytes=new TextEncoder().encode(body);if(bytes.byteLength!==utf8Bytes||await sha256(bytes)!==hash)fail()
 try{return JSON.parse(body) as unknown}catch{return fail()}
}

export async function parseAnalysisHeader(m:AnalysisPageSet,q:NativeDemandQuery,actor:string,access:AnalysisFinanceAccess):Promise<AnalysisHeader>{
 const e=object(await verifiedText(m.header.body,m.header.utf8Bytes,m.header.sha256))
 exact(e,['contract_version','run_id','request_id','query','financial_source','product_labels','analysis_header','paged','targets_total','page_count','apply_enabled','production_go'])
 if(e.contract_version!=='cp7.native-analysis-header.v1'||e.apply_enabled!==false||e.production_go!==false||e.run_id!==m.runId||e.request_id!==m.requestId||e.targets_total!==m.targetsTotal||e.page_count!==m.pageCount)fail()
 const query=object(e.query);exact(query,['from_date','through_date','group_mode']);if(query.from_date!==q.from_date||query.through_date!==q.through_date||query.group_mode!==q.group_mode)fail()
 const p=object(e.paged);exact(p,pagedKeys(m));for(const k of pagedKeys(m)){const x=object(p[k]);exact(x,['prefix','items']);if(x.prefix!==m.paged[k]!.prefix||x.items!==m.paged[k]!.items)fail()}
 // The frozen schema without semantic_hash: a staged header carries none.
 if(!analysisHeaderSchemaMatches(e.analysis_header))fail()
 const a=e.analysis_header as AnalysisHeaderResult
 if(a.run_id!==m.runId||a.scope.actor_scope_id!==actor||a.scope.allocation_scope_id!=='GLOBAL_NATIVE_PLANNING'||a.scope.display_filter!=='ALL'||!/^[0-9a-f]{64}$/.test(a.snapshot.source_hash))fail()
 // Every paged array holds its global items and the place of the per-target ones.
 for(const k of pagedKeys(m)){const arr=(a as unknown as Record<string,unknown>)[k];if(!Array.isArray(arr)||m.paged[k]!.prefix>arr.length)fail()}
 if(!Array.isArray(e.product_labels))fail()
 const labels=e.product_labels.map(raw=>{const l=object(raw);exact(l,['target_key','sku','product_name']);if(typeof l.target_key!=='string'||typeof l.sku!=='string'||!l.sku||typeof l.product_name!=='string'||!l.product_name)fail();return{key:l.target_key,sku:l.sku,name:l.product_name}})
 if(new Set(labels.map(l=>l.key)).size!==labels.length||labels.length<m.totals.recommendations.ACTIVE+m.totals.recommendations.PAUSED+m.totals.recommendations.STOPPED+m.totals.recommendations.OTHER)fail()
 // Checks the header can settle alone: snapshot, uniqueness, fact refs and
 // global assumptions, sources against their allocated edge inputs.
 const unique=(v:string[])=>new Set(v).size===v.length
 if(a.fixture_kind!==undefined||a.snapshot.knowledge_mode!=='CURRENT'||a.stale.is_stale||a.status==='COMPLETE'&&(!a.snapshot.capture_complete||Object.values(a.quality).some(x=>['UNKNOWN','CONFLICT','PARTIAL'].includes(x))))fail()
 if(!unique(a.sources.map(s=>s.source_key))||!unique(a.assumptions.map(x=>x.id))||!unique(a.dependencies.map(d=>d.domain))||a.snapshot.fact_count!==a.dependencies.reduce((n,d)=>n+d.fact_count,0))fail()
 assertAnalysisFacts(a,new Set(a.assumptions.map(x=>x.id)))
 const sources=new Map(a.sources.map(s=>[s.source_key,s])),inputs=new Map<string,{input:bigint;output:bigint}>()
 for(const x of a.allocation_edges){const s=sources.get(x.source_key),i=pcs(x.input_qty),o=pcs(x.projected_output_qty)
  if(!s||s.size_id!==x.size_id||i===null||o===null||o>i||i>0n&&!['CONFIRMED_TARGET','CANDIDATE_MATCH'].includes(x.match))fail()
  const t=inputs.get(x.source_key)??{input:0n,output:0n};inputs.set(x.source_key,{input:t.input+i,output:t.output+o})}
 for(const s of a.sources){const ph=pcs(s.physical_remaining),el=pcs(s.eligible_input),g=pcs(s.eligible_projected),al=pcs(s.allocated),t=inputs.get(s.source_key)??{input:0n,output:0n}
  if(ph!==null&&el!==null&&el>ph||al!==null&&el!==null&&al>el||al!==null&&al!==t.input||g!==null&&t.output>g||al===null&&t.input>0n)fail()}
 // The staged path is operational (financial capture DEFERRED): the header
 // names no financial source and the analysis carries no financial figure.
 if(e.financial_source!==null)fail()
 financeSource(null,a as AnalysisResult,q,access)
 return{runId:m.runId,requestId:m.requestId,query:{...q},analysisHeader:structuredClone(a),labels}
}

export async function parseAnalysisPage(v:unknown,m:AnalysisPageSet,h:AnalysisHeader,index:number):Promise<AnalysisPage>{
 const entry=m.pages[index];if(!entry)fail()
 const e=object(v);exact(e,['contract_version','run_id','index','page_count','target_lo','target_hi','header_sha256','identity_hash','utf8_bytes','sha256','body'])
 if(e.contract_version!=='cp7.native-analysis-page-read.v1'||e.run_id!==m.runId||e.index!==index||e.page_count!==m.pageCount||e.target_lo!==entry.targetLo||e.target_hi!==entry.targetHi
  ||e.header_sha256!==m.header.sha256||e.identity_hash!==m.identityHash||e.utf8_bytes!==entry.utf8Bytes||e.sha256!==entry.sha256)fail()
 const p=object(await verifiedText(e.body,entry.utf8Bytes,entry.sha256))
 exact(p,['contract_version','run_id','request_id','index','page_count','target_lo','target_hi','targets_total','header_sha256','counts','offsets','totals','summary','items','apply_enabled','production_go'])
 if(p.contract_version!=='cp7.native-analysis-page.v1'||p.apply_enabled!==false||p.production_go!==false||p.run_id!==m.runId||p.request_id!==m.requestId||p.index!==index||p.page_count!==m.pageCount
  ||p.target_lo!==entry.targetLo||p.target_hi!==entry.targetHi||p.targets_total!==m.targetsTotal||p.header_sha256!==m.header.sha256)fail()
 const keys=pagedKeys(m),counts=object(p.counts),offsets=object(p.offsets),totals=object(p.totals),raw=object(p.items)
 sameKeys(counts,keys);sameKeys(offsets,keys);sameKeys(totals,keys);sameKeys(raw,keys)
 const items={assumptions:[],generation_warnings:[],actions:[],recommendations:[],demand_models:[],material_needs:[],metrics:[],timeline:[]} as unknown as AnalysisPageItems
 for(const k of keys){
  const list=raw[k];if(!Array.isArray(list)||counts[k]!==entry.counts[k]||list.length!==entry.counts[k]||offsets[k]!==entry.offsets[k]||totals[k]!==m.paged[k]!.items)fail()
  if(list.some(x=>!analysisSchemaMatches(x,k)))fail()
  ;(items as unknown as Record<string,unknown[]>)[k]=structuredClone(list)
 }
 // Per page: each target is one recommendation or one unreviewed policy, and
 // has exactly one action; every per-target item belongs to a target of this
 // page; facts, assumptions, materials and edges are checked as for a whole run.
 const targets=entry.targetHi-entry.targetLo+1,recs=new Map(items.recommendations.map(r=>[r.target.key,r])),labels=new Set(h.labels.map(l=>l.key))
 const unreviewed=items.generation_warnings.filter(w=>typeof w==='string'&&w.startsWith('PRODUCTION_POLICY_UNREVIEWED:'))
 const summary=object(p.summary);exact(summary,['recommendations','policy_unreviewed'])
 const byState=states(summary.recommendations),policyUnreviewed=count(summary.policy_unreviewed,0,targets)
 const actual={ACTIVE:0,PAUSED:0,STOPPED:0,OTHER:0};for(const r of items.recommendations)actual[(['ACTIVE','PAUSED','STOPPED'] as string[]).includes(r.production_state)?r.production_state as 'ACTIVE':'OTHER']++
 if(STATES.some(s=>actual[s]!==byState[s])||policyUnreviewed!==items.actions.filter(a=>a.primary_reason==='PRODUCTION_POLICY_UNREVIEWED').length)fail()
 if(recs.size!==items.recommendations.length||recs.size+policyUnreviewed!==targets||items.actions.length!==targets||unreviewed.length!==policyUnreviewed||unreviewed.length!==items.generation_warnings.length
  ||items.recommendations.some(r=>!labels.has(r.target.key)))fail()
 if(new Set(items.actions.map(a=>a.key)).size!==items.actions.length||new Set(items.material_needs.map(x=>JSON.stringify([x.target_key,x.material_key]))).size!==items.material_needs.length)fail()
 const all=[...h.analysisHeader.assumptions,...items.assumptions],sources=new Set(h.analysisHeader.sources.map(s=>s.source_key))
 if(new Set(all.map(a=>a.id)).size!==all.length)fail()
 assertAnalysisFacts(items,new Set(all.map(a=>a.id)))
 for(const r of items.recommendations){for(const f of[r.actual_fg,r.target_qty,r.q_base,r.q_conditional,r.suggested_new,r.rounding_extra,r.feasible_new,r.unresolved_qty])pcs(f)
  if(r.production_state!=='ACTIVE'&&[r.suggested_new,r.feasible_new].some(f=>'value'in f&&pcs(f)!==0n))fail()}
 for(const x of items.material_needs)assertMaterialNeed(x,recs.get(x.target_key),all)
 for(const a of items.actions){if(a.source_keys.some(k=>!sources.has(k))||a.target_keys.some(k=>!recs.has(k))||a.intent==='START_NEW'&&a.target_keys.some(k=>recs.get(k)?.production_state!=='ACTIVE'))fail()}
 for(const t of items.timeline){if(!recs.has(t.target_key)||t.timing_basis==='DATE_POLICY'&&!t.timing_policy_id||t.timing_basis==='TIMESTAMP_EVIDENCE'&&!t.event_refs.length)fail()}
 for(const x of items.metrics){if(x.scope_kind!=='TARGET'||!recs.has(x.scope_key)||x.period_start>x.period_end||x.value.unit==='IDR')fail()}
 for(const x of h.analysisHeader.allocation_edges){const r=recs.get(x.target_key);if(r&&r.target.size_id!==x.size_id)fail()}
 return{runId:m.runId,index,targetLo:entry.targetLo,targetHi:entry.targetHi,items,summary:{recommendations:byState,policyUnreviewed}}
}

// erp_cp7_check_staged_analysis_source_v1: the current source fingerprint
// against the run's reference, in one statement (§10). Only the two stated
// fields are required; a contract version or the run id may accompany them.
export function parseStagedSourceCheck(v:unknown,runId:string):StagedSourceCheck{
 const e=object(v),keys=Object.keys(e)
 if(keys.some(k=>!['contract_version','run_id','source_state','checked_at'].includes(k))||!Object.hasOwn(e,'source_state')||!Object.hasOwn(e,'checked_at'))fail()
 if(Object.hasOwn(e,'contract_version')&&(typeof e.contract_version!=='string'||!/^cp7\.[a-z0-9.-]+\.v[0-9]+$/.test(e.contract_version)))fail()
 if(Object.hasOwn(e,'run_id')&&e.run_id!==runId)fail()
 if(e.source_state!=='UNCHANGED'&&e.source_state!=='ARCHIVED_STALE')fail()
 return{sourceState:e.source_state,checkedAt:stagedInstant(e.checked_at)}
}
