import {afterEach,it,expect,vi} from 'vitest'
import {boundedFrozenReply,frozenProgressGuard,frozenProgressView,FROZEN_NO_PROGRESS_MS,FROZEN_RPC_WAIT_MS,FROZEN_STALL_MESSAGE,FROZEN_WAIT_MESSAGE} from './nativeFrozenProgress'
import type {StagedJob} from '../../../src/nativeStagedJob'

const job=(extra:Partial<StagedJob>={}):StagedJob=>({requestId:'job',state:'RUNNING',stage:'HIST_ROWS',stageIndex:3,stageCount:9,unitsDone:12,unitCount:55,planFinal:false,targetsTotal:3600,targetsDoneInStage:1200,reference:{capturedAt:'2026-10-26T01:00:00Z',sourceHash:'a'.repeat(64)},lastProgressAt:'2026-10-26T01:00:09Z',unitAttempts:0,runId:null,failure:null,workerActive:false,serverRunner:null,retention:null,...extra})
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks()})

it('never gives a percentage while the plan grows, or uses target completion as whole-job completion',()=>{
 expect(frozenProgressView(job({targetsDoneInStage:3600})).percent).toBeNull()
 expect(frozenProgressView(job({planFinal:true,targetsDoneInStage:3600})).percent).toBe(21)
 expect(frozenProgressView(job({planFinal:true,unitsDone:55,state:'DONE'})).percent).toBe(100)
})
it('allows arbitrarily long total work when real completed units continue advancing',()=>{
 let time=0;const check=frozenProgressGuard(()=>time)
 for(let done=0;done<55;done++){time+=FROZEN_NO_PROGRESS_MS-1;expect(()=>check(job({unitsDone:done}))).not.toThrow()}
 expect(time).toBeGreaterThan(8_000)
})
it('does not treat heartbeat timestamps or worker-active flags as completed work',()=>{
 let time=0;const check=frozenProgressGuard(()=>time);check(job())
 time=FROZEN_NO_PROGRESS_MS-1;check(job({lastProgressAt:'2026-10-26T01:02:00Z',workerActive:true}))
 time++;expect(()=>check(job({lastProgressAt:'2026-10-26T01:02:01Z',workerActive:false}))).toThrow(FROZEN_STALL_MESSAGE)
})
it('returns ready replies immediately and releases the timeout',async()=>{
 vi.useFakeTimers();const result={state:'DONE'}
 await expect(boundedFrozenReply(()=>Promise.resolve(result))).resolves.toBe(result)
 expect(vi.getTimerCount()).toBe(0)
})
it('aborts an unresponsive transport with an uncertain-result message and never adopts its late answer',async()=>{
 vi.useFakeTimers();let signal:AbortSignal|undefined,release!:(v:string)=>void
 const held=Object.assign(new Promise<string>(resolve=>{release=resolve}),{abortSignal:(s:AbortSignal)=>{signal=s;return held}})
 const reply=boundedFrozenReply(()=>held),failure=expect(reply).rejects.toThrow(FROZEN_WAIT_MESSAGE)
 await vi.advanceTimersByTimeAsync(FROZEN_RPC_WAIT_MS);await failure
 expect(signal?.aborted).toBe(true);release('late DONE');await Promise.resolve();expect(vi.getTimerCount()).toBe(0)
})
it('preserves real server refusals and cleans up on synchronous transport errors',async()=>{
 vi.useFakeTimers();const error={code:'42501',message:'CURRENT_ACCESS_DENIED'}
 await expect(boundedFrozenReply(()=>Promise.reject(error))).rejects.toBe(error)
 await expect(boundedFrozenReply(()=>{throw error})).rejects.toBe(error)
 expect(vi.getTimerCount()).toBe(0)
})
