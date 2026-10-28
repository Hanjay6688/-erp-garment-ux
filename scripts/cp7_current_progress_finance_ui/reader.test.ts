import {beforeEach,expect,it,vi} from 'vitest'
import {createProgressReader,PROGRESS_RPC,type Observation} from './reader'
import {progressFixture} from './progressFixture'
let f:Awaited<ReturnType<typeof progressFixture>>
beforeEach(async()=>{f=await progressFixture()})
it('shares simultaneous reads but rechecks the server for every later read',async()=>{
 let release!:(v:unknown)=>void
 const rpc=vi.fn(()=>new Promise(resolve=>{release=resolve})),reader=createProgressReader({rpc},f.request,f.reference,()=>true)
 const one=reader.read(),two=reader.status(f.request.id);expect(rpc).toHaveBeenCalledTimes(1)
 release({data:f.wire,error:null});expect((await one).progress.state).toBe('RUNNING');expect((await two).data).toBe(f.wire.status)
 const three=reader.read();expect(rpc).toHaveBeenCalledTimes(2);release({data:f.wire,error:null});await three
 expect(rpc.mock.calls).toEqual([[PROGRESS_RPC,{p_request:f.request.id}],[PROGRESS_RPC,{p_request:f.request.id}]])
})
it('a lost response retries only the same read and never creates or advances work',async()=>{
 const rpc=vi.fn().mockRejectedValueOnce(Error('reply lost')).mockResolvedValue({data:f.wire,error:null})
 const reader=createProgressReader({rpc},f.request,f.reference,()=>true)
 await expect(reader.read()).rejects.toThrow('reply lost');await reader.read()
 expect(rpc.mock.calls.every(([name,args])=>name===PROGRESS_RPC&&args.p_request===f.request.id)).toBe(true)
})
it('current access refusal clears previously visible metadata instead of reusing it',async()=>{
 const denied={code:'42501',message:'CP7_ANALYSIS_JOB_UNAVAILABLE'}
 const rpc=vi.fn().mockResolvedValueOnce({data:f.wire,error:null}).mockResolvedValueOnce({data:null,error:denied})
 const reader=createProgressReader({rpc},f.request,f.reference,()=>true),seen:Observation[]=[];reader.subscribe(v=>seen.push(v))
 await reader.read();await expect(reader.read()).rejects.toBe(denied)
 expect(seen.at(-1)).toEqual({value:null,error:denied});expect(rpc).toHaveBeenCalledTimes(2)
})
it('rejects a different immutable source even when the request UUID is the same',async()=>{
 const rpc=vi.fn().mockResolvedValue({data:f.wire,error:null})
 const reader=createProgressReader({rpc},f.request,{...f.reference,sourceHash:'f'.repeat(64)},()=>true)
 await expect(reader.read()).rejects.toThrow('Sumber kemajuan berbeda')
})
it('rejects a late reply after another tab retires the durable request',async()=>{
 let release!:(v:unknown)=>void,current=true
 const rpc=vi.fn(()=>new Promise(resolve=>{release=resolve})),reader=createProgressReader({rpc},f.request,f.reference,()=>current)
 const pending=reader.read();current=false;release({data:f.wire,error:null});await expect(pending).rejects.toThrow('Acuan perhitungan')
 await expect(reader.read()).rejects.toThrow('Acuan perhitungan');expect(rpc).toHaveBeenCalledTimes(1)
})
it('disposal prevents late publication and all new reads',async()=>{
 let release!:(v:unknown)=>void
 const rpc=vi.fn(()=>new Promise(resolve=>{release=resolve})),reader=createProgressReader({rpc},f.request,f.reference,()=>true),listener=vi.fn()
 reader.subscribe(listener);const pending=reader.read();reader.dispose();release({data:f.wire,error:null})
 await expect(pending).rejects.toThrow('Acuan perhitungan');await expect(reader.read()).rejects.toThrow('Acuan perhitungan')
 expect(listener).toHaveBeenCalledTimes(1);expect(rpc).toHaveBeenCalledTimes(1)
})
it('rejects server observation time going backwards',async()=>{
 const rpc=vi.fn().mockResolvedValue({data:f.wire,error:null}),reader=createProgressReader({rpc},f.request,f.reference,()=>true)
 await reader.read();const earlier={...f.wire,observed_at:'2026-10-07T10:05:00Z'};rpc.mockResolvedValueOnce({data:earlier,error:null})
 await expect(reader.read()).rejects.toThrow('Urutan pengamatan server')
})
