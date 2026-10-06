// @vitest-environment jsdom
import {beforeEach,expect,it} from 'vitest'
import {parseAnalysisJob,parseAnalysisManifest,parseAnalysisSegment,assembleAnalysisOriginal,readAnalysisJobRequest,persistAnalysisJobRequest,clearAnalysisJobRequest,analysisJobKey,analysisOversized,analysisSinceText,ANALYSIS_DOCUMENT_UTF8_BYTES} from './nativeAnalysisTransport'
import {transport,job,sha} from '../tests/fixtures/nativeAnalysisTransport'
const run='11111111-1111-4111-8111-111111111111',request='22222222-2222-4222-8222-222222222222',other='33333333-3333-4333-8333-333333333333'
const q={from_date:'2026-09-01',through_date:'2026-09-30',group_mode:'AS_SOLD' as const}
// Over two segments; astral characters straddle the 2,000,000-code-point cut.
const big={run_id:run,request_id:request,pad:'x'+'😀é'.repeat(1100000),apply_enabled:false}
beforeEach(()=>localStorage.clear())
type T=Awaited<ReturnType<typeof transport>>
const reader=(t:T,edit:(i:number,s:Record<string,unknown>)=>Record<string,unknown>|Promise<Record<string,unknown>>=(_,s)=>s)=>async(i:number)=>edit(i,structuredClone(t.segment(i)))

it('assembles the exact Original across multibyte segment cuts and adds only the manifest source state',async()=>{
 const t=await transport(big,'ARCHIVED_STALE'),m=parseAnalysisManifest(t.manifest,run,request);expect(m.document.segmentCount).toBe(2)
 const seen:number[][]=[];const out=await assembleAnalysisOriginal(m,reader(t),(d,n)=>seen.push([d,n]))
 expect(out).toEqual({...big,source_state:'ARCHIVED_STALE'});expect(seen).toEqual([[1,2],[2,2]])
 expect(t.parts[0].codePointAt(t.parts[0].length-2)).toBe(0x1f600)
})

it('refuses tampered, reordered, foreign, short and over-bound segments and whole-document drift',async()=>{
 const t=await transport(big),m=parseAnalysisManifest(t.manifest,run,request)
 const refuse=(edit:(i:number,s:Record<string,unknown>)=>Record<string,unknown>|Promise<Record<string,unknown>>)=>expect(assembleAnalysisOriginal(m,reader(t,edit))).rejects.toThrow('belum sesuai')
 await refuse((i,s)=>i===1?{...s,body:String(s.body).replace('é','e')}:s)
 await refuse(async(i,s)=>i===1?{...s,body:String(s.body).replace('é','e'),sha256:await sha(String(s.body).replace('é','e')),utf8_bytes:Number(s.utf8_bytes)-1}:s)
 await refuse((i,s)=>i===0?{...structuredClone(t.segment(1))}:s)
 await refuse((_i,s)=>({...s,run_id:other}))
 await refuse(async(i,s)=>i===1?{...s,body:String(s.body).slice(0,-1),utf8_bytes:Number(s.utf8_bytes)-2,sha256:await sha(String(s.body).slice(0,-1))}:s)
 await refuse((_i,s)=>({...s,extra:true}))
 await refuse((_i,s)=>({...s,document_sha256:'b'.repeat(64)}))
 const drift=parseAnalysisManifest({...t.manifest,document:{...t.manifest.document,sha256:'c'.repeat(64)}},run,request)
 await expect(assembleAnalysisOriginal(drift,async i=>({...t.segment(i),document_sha256:'c'.repeat(64)}))).rejects.toThrow('belum sesuai')
 const withState=await transport({...big,source_state:'UNCHANGED'})
 await expect(assembleAnalysisOriginal(parseAnalysisManifest(withState.manifest,run,request),reader(withState))).rejects.toThrow('belum sesuai')
 await expect(parseAnalysisSegment({...t.segment(0),utf8_bytes:8000001},m,0)).rejects.toThrow('belum sesuai')
})

it('validates manifest identity, counts and the assembled-document bound',async()=>{
 const t=await transport(big),ok=t.manifest
 expect(()=>parseAnalysisManifest(ok,run,other)).toThrow();expect(()=>parseAnalysisManifest(ok,other,request)).toThrow()
 expect(parseAnalysisManifest(ok,run,null).requestId).toBe(request)
 for(const bad of[{...ok,apply_enabled:true},{...ok,source_state:'LIVE'},{...ok,access_epoch:'x'},{...ok,extra:1},
  {...ok,document:{...ok.document,segment_count:3}},{...ok,document:{...ok.document,segment_characters:1000}},
  {...ok,document:{...ok.document,utf8_bytes:ANALYSIS_DOCUMENT_UTF8_BYTES+1}},{...ok,document:{...ok.document,characters:ok.document.utf8_bytes+1}}])
  expect(()=>parseAnalysisManifest(bad,run,request)).toThrow()
})

it('accepts exactly the four job states with consistent run, failure and clock fields',()=>{
 expect(parseAnalysisJob(job(request,q,'DONE',run),request,q)).toMatchObject({state:'DONE',runId:run,failure:null})
 expect(parseAnalysisJob(job(request,q,'FAILED'),request,q).failure).toEqual({sqlstate:'57014',code:'CP7_ANALYSIS_JOB_STOPPED'})
 expect(parseAnalysisJob(job(request,q,'RUNNING'),request,q).finishedAt).toBeNull()
 for(const bad of[job(request,q,'DONE'),job(request,q,'WAITING',null,{run_id:run}),job(request,q,'FAILED',null,{failure:null}),job(request,q,'RUNNING',null,{finished_at:'2026-10-06T12:00:05.000000Z'}),
  job(request,q,'WAITING',null,{started_at:'2026-10-06T11:00:00.000000Z'}),job(request,q,'WAITING',null,{state:'QUEUED'}),job(request,q,'WAITING',null,{attempts:0}),
  job(request,q,'WAITING',null,{production_go:true}),job(request,{...q,group_mode:'RESTATED'},'WAITING'),{...job(request,q,'WAITING'),extra:1},
  job(request,q,'FAILED',null,{failure:{sqlstate:'57014',code:'raw message'}})])expect(()=>parseAnalysisJob(bad,request,q)).toThrow()
 expect(()=>parseAnalysisJob(job(other,q,'WAITING'),request,q)).toThrow()
})

it('keeps the background UUID and query until the same request is cleared, and refuses damaged storage',()=>{
 const scope='analysis:p:a';persistAnalysisJobRequest(scope,{id:request,q});expect(readAnalysisJobRequest(scope).pending).toEqual({id:request,q})
 expect(()=>persistAnalysisJobRequest(scope,{id:other,q})).toThrow();expect(()=>clearAnalysisJobRequest(scope,other)).toThrow()
 clearAnalysisJobRequest(scope,request);expect(readAnalysisJobRequest(scope)).toEqual({pending:null,error:''})
 localStorage.setItem(analysisJobKey(scope),'{"id":"x"}');expect(readAnalysisJobRequest(scope).error).toContain('Jangan hapus')
})

it('measures the single-body bound in UTF8 bytes and states the WIB start clock',()=>{
 expect(analysisOversized({analysis:{pad:'é'.repeat(4000000)}})).toBe(true);expect(analysisOversized({analysis:{pad:'x'.repeat(4000000)}})).toBe(false)
 expect(analysisOversized(null)).toBe(false);expect(analysisSinceText('2026-10-06T12:00:00.000000Z')).toMatch(/^Sedang dihitung sejak jam 19[.:]00[.:]00 WIB \(6 Okt 2026\)\.$/)
})
