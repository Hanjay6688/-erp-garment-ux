// @vitest-environment jsdom
import {afterEach,it,expect,vi} from 'vitest'
import {BOUNDED_ANALYSIS_REQUEST,persistBoundedAnalysisRequest,readBoundedAnalysisRequest,replaceBoundedAnalysisRequest,type BoundedAnalysisRequest} from './nativeBoundedAnalysis'
import {driveBoundedQuantity,readBoundedQuantity,readBoundedQuantityPage,sameBoundedReference} from './nativeBoundedQuantity'
import {parseStagedJob} from './nativeStagedJob'
import {stagedRun} from '../tests/fixtures/nativeAnalysisPages'

afterEach(()=>{localStorage.clear();vi.restoreAllMocks()})
it('drives the bounded request and existing step facade with one immutable stored UUID/query',async()=>{
 const f=await stagedRun({targets:2000,pageSizes:[500,500,500,500]}),r:BoundedAnalysisRequest={id:f.pageSet.request_id,q:f.query,method:BOUNDED_ANALYSIS_REQUEST}
 persistBoundedAnalysisRequest('quantity',r)
 const rpc=vi.fn(async(name:string,args:{p_request:string;p_query?:unknown})=>{
  expect(args.p_request).toBe(r.id)
  if(name==='erp_cp7_request_bounded_staged_analysis_v1'){expect(args.p_query).toEqual(r.q);expect(readBoundedAnalysisRequest('quantity').pending).toEqual(r);return{data:f.job('RUNNING'),error:null}}
  expect(name).toBe('erp_cp7_step_staged_analysis_v1');return{data:f.job('DONE'),error:null}
 })
 const result=await driveBoundedQuantity({rpc},r,{start:true})
 expect(result?.state).toBe('DONE');expect(result?.targetsTotal).toBe(2000)
 expect(rpc.mock.calls.map(c=>c[0])).toEqual(['erp_cp7_request_bounded_staged_analysis_v1','erp_cp7_step_staged_analysis_v1'])
 expect(readBoundedAnalysisRequest('quantity').pending).toEqual(r)
})
it('uses get rather than relabelling or issuing a new request when resuming a saved result',async()=>{
 const f=await stagedRun({targets:10}),r:BoundedAnalysisRequest={id:f.pageSet.request_id,q:f.query,method:BOUNDED_ANALYSIS_REQUEST}
 const rpc=vi.fn(async()=>({data:f.job('DONE'),error:null}))
 await driveBoundedQuantity({rpc},r,{start:false})
 expect(rpc).toHaveBeenCalledOnce();expect(rpc).toHaveBeenCalledWith('erp_cp7_get_staged_analysis_v1',{p_request:r.id})
})
it('reads the hash-bound full page set and a single page for all2000 targets without the old whole-netting facade',async()=>{
 const f=await stagedRun({targets:2000,pageSizes:[500,500,500,500]}),r:BoundedAnalysisRequest={id:f.pageSet.request_id,q:f.query,method:BOUNDED_ANALYSIS_REQUEST},job=parseStagedJob(f.job('DONE'),r.id,{id:r.id,q:r.q})
 const rpc=vi.fn(async(name:string,args:{p_index:number})=>({data:name==='erp_cp7_read_staged_analysis_pages_v1'?f.pageSet:f.page(args.p_index),error:null}))
 const result=await readBoundedQuantity({rpc},r,job,f.actor),page=await readBoundedQuantityPage({rpc},result,1)
 expect(result.set.targetsTotal).toBe(2000);expect([page.targetLo,page.targetHi]).toEqual([501,1000])
 expect(rpc).toHaveBeenCalledWith('erp_cp7_read_staged_analysis_page_v1',{p_run:f.runId,p_index:1,p_access_epoch:f.pageSet.access_epoch})
 expect(rpc.mock.calls.some(c=>c[0]==='erp_cp7_capture_netting_v1')).toBe(false)
})
it.each(['count','hash','clock'])('rejects a DONE job whose %s disagrees with the page set',async field=>{
 const f=await stagedRun({targets:3}),r:BoundedAnalysisRequest={id:f.pageSet.request_id,q:f.query,method:BOUNDED_ANALYSIS_REQUEST},job=parseStagedJob(f.job('DONE'),r.id,{id:r.id,q:r.q})
 if(field==='count')job.targetsTotal=4
 if(field==='hash')job.reference.sourceHash='f'.repeat(64)
 if(field==='clock')job.reference.capturedAt=job.reference.capturedAt.replace('.000000','.000001')
 const rpc=vi.fn(async()=>({data:f.pageSet,error:null}))
 await expect(readBoundedQuantity({rpc},r,job,f.actor)).rejects.toThrow('Acuan');expect(rpc).toHaveBeenCalledOnce()
})
it('keeps microsecond identity while accepting the Native UTC offset serialization',()=>{
 const a={sourceHash:'a'.repeat(64),capturedAt:'2026-10-24T01:02:03.123456Z'}
 expect(sameBoundedReference(a,{...a,capturedAt:'2026-10-24T01:02:03.123456+00:00'})).toBe(true)
 expect(sameBoundedReference(a,{...a,capturedAt:'2026-10-24T01:02:03.123457Z'})).toBe(false)
})
it('keeps the last request on failed atomic replacement and refuses reusing its UUID for new input',()=>{
 const r:BoundedAnalysisRequest={id:'00000000-0000-4000-8000-000000000001',q:{from_date:'2026-10-01',through_date:'2026-10-23',group_mode:'AS_SOLD'},method:BOUNDED_ANALYSIS_REQUEST}
 persistBoundedAnalysisRequest('quantity',r)
 expect(()=>replaceBoundedAnalysisRequest('quantity',r,{...r,q:{...r.q,group_mode:'RESTATED'}})).toThrow()
 const write=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota')})
 expect(()=>replaceBoundedAnalysisRequest('quantity',r,{...r,id:'00000000-0000-4000-8000-000000000002'})).toThrow('quota')
 write.mockRestore();expect(readBoundedAnalysisRequest('quantity').pending).toEqual(r)
})
