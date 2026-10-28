// @vitest-environment jsdom
import {expect,it} from 'vitest'
import {driveStagedJob,persistStagedRequest,readStagedRequest,STAGED_NO_PROGRESS_MS,STAGED_STALL_MESSAGE,type StagedReply,type StagedJob,type StagedRequest} from './nativeStagedJob'
import {stagedJobFixture} from '../tests/fixtures/nativeAnalysisPages'
const id='00000000-0000-4000-8000-000000000095'
const request={id,q:{from_date:'2026-09-01',through_date:'2026-09-30',group_mode:'AS_SOLD' as const}}
const ok=(data:unknown):StagedReply=>({data,error:null})
const initial=(extra:Record<string,unknown>={})=>ok(stagedJobFixture(id,'RUNNING',{units_done:0,targets_total:null,targets_done_in_stage:0,...extra}))
const refused={data:null,error:{code:'55000',message:'CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED'}}
const done=()=>ok(stagedJobFixture(id,'DONE'))
function server(script:Partial<Record<'request'|'get'|'step',StagedReply[]>>){
 const calls:{method:string;id:string}[]=[]
 const call=async(method:'request'|'get'|'step',requestId:string)=>{calls.push({method,id:requestId});const next=script[method]?.shift();if(!next)throw Error('unexpected '+method);return next}
 return{calls,rpc:{request:(r:StagedRequest)=>call('request',r.id),get:(i:string)=>call('get',i),step:(i:string)=>call('step',i)}}
}
it('polls the same UUID after the exact initial refusal, even without worker/runner flags and with an unknown total',async()=>{
 const s=server({request:[initial()],step:[refused,done()],get:[initial(),initial({units_done:1})]}),seen:StagedJob[]=[],waits:number[]=[]
 expect((await driveStagedJob({rpc:s.rpc,request,start:true,onStatus:j=>seen.push(j),sleep:async ms=>{waits.push(ms)}}))?.state).toBe('DONE')
 expect(s.calls.map(c=>c.method)).toEqual(['request','step','get','get','step']);expect(s.calls.every(c=>c.id===id)).toBe(true)
 expect(waits).toEqual([2000,2000]);expect(seen.slice(0,3).every(j=>j.targetsTotal===null&&j.planFinal===false)).toBe(true)
 expect(seen[1].workerActive).toBe(false);expect(seen[1].unitAttempts).toBe(0)
})
it.each([
 {code:'55000',message:'CP7_OTHER_REFUSAL'},
 {code:'42501',message:'CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED'},
 {code:'42501',message:'CP7_ANALYSIS_ACCESS_CHANGED'},
 {code:'55000',message:'CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED extra'},
 {message:'CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED'}
])('preserves other errors exactly: %j',async error=>{
 const s=server({request:[initial()],step:[{data:null,error}]})
 await expect(driveStagedJob({rpc:s.rpc,request,start:true})).rejects.toBe(error)
 expect(s.calls.map(c=>c.method)).toEqual(['request','step'])
})
it('does not reinterpret the initial refusal from request/get or after the initial unit',async()=>{
 for(const script of [{request:[refused]},{get:[refused]},{request:[initial({units_done:1})],step:[refused]}]){
  const s=server(script)
  await expect(driveStagedJob({rpc:s.rpc,request,start:!('get'in script)})).rejects.toBe(refused.error)
 }
})
it('stops unchanged heartbeat/lock observations at the existing two-minute bound and preserves the request for same-UUID reopen',async()=>{
 localStorage.clear();persistStagedRequest('initial-recovery',request)
 let time=0
 const heartbeat=(seconds:number)=>initial({worker_active:seconds%2===0,server_runner:{active:true,last_tick_at:`2026-10-07T09:0${seconds}:00.000000Z`},last_progress_at:`2026-10-07T09:0${seconds}:00.000000Z`})
 const s=server({request:[initial()],step:[refused],get:[heartbeat(1),heartbeat(2)]})
 await expect(driveStagedJob({rpc:s.rpc,request,start:true,now:()=>time,sleep:async()=>{time+=STAGED_NO_PROGRESS_MS/2}})).rejects.toThrow(STAGED_STALL_MESSAGE)
 expect(s.calls.map(c=>c.method)).toEqual(['request','step','get','get']);expect(readStagedRequest('initial-recovery').pending).toEqual(request)
 const reopened=server({get:[done()]})
 expect((await driveStagedJob({rpc:reopened.rpc,request:readStagedRequest('initial-recovery').pending!,start:false}))?.state).toBe('DONE')
 expect(reopened.calls).toEqual([{method:'get',id}])
})
it('resets observation only on real progress and returns a terminal status even after a long elapsed interval',async()=>{
 let time=0
 const s=server({request:[initial()],step:[refused],get:[initial({units_done:1,worker_active:true}),initial({units_done:2,worker_active:true}),done()]})
 expect((await driveStagedJob({rpc:s.rpc,request,start:true,now:()=>time,sleep:async()=>{time+=STAGED_NO_PROGRESS_MS}}))?.state).toBe('DONE')
 expect(time).toBe(STAGED_NO_PROGRESS_MS*3)
})
it('backs off an unchanged ordinary step without delaying real work and bounds an ordinary lock stall',async()=>{
 let time=0
 const s=server({request:[initial({units_done:12})],step:[initial({units_done:12})],get:[initial({units_done:12,worker_active:true}),initial({units_done:12,worker_active:true})]})
 await expect(driveStagedJob({rpc:s.rpc,request,start:true,now:()=>time,sleep:async()=>{time+=STAGED_NO_PROGRESS_MS/2}})).rejects.toThrow(STAGED_STALL_MESSAGE)
 expect(s.calls.map(c=>c.method)).toEqual(['request','step','get','get'])
})
it('preserves access revocation or transport loss while observing the server initial unit',async()=>{
 const access={code:'42501',message:'CP7_ANALYSIS_ACCESS_CHANGED'}
 const s=server({request:[initial()],step:[refused],get:[{data:null,error:access}]})
 await expect(driveStagedJob({rpc:s.rpc,request,start:true,sleep:async()=>{}})).rejects.toBe(access)
 const t=server({request:[initial()],step:[refused]});const lost=new TypeError('Failed to fetch')
 await expect(driveStagedJob({rpc:{...t.rpc,get:async()=>{throw lost}},request,start:true,sleep:async()=>{}})).rejects.toBe(lost)
})
it('retires the observer during backoff without another RPC or a fabricated terminal result',async()=>{
 let aborted=false
 const s=server({request:[initial()],step:[refused]})
 expect(await driveStagedJob({rpc:s.rpc,request,start:true,aborted:()=>aborted,sleep:async()=>{aborted=true}})).toBeNull()
 expect(s.calls.map(c=>c.method)).toEqual(['request','step'])
})
