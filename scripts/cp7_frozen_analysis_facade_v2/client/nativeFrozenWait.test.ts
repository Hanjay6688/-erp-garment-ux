// @vitest-environment jsdom
import {afterEach,it,expect,vi} from 'vitest'
import {boundedFrozenLock,FROZEN_LOCK_MESSAGE} from './nativeFrozenWait'
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals()})
it('bounds only the lock queue and never runs a timed-out late callback',async()=>{
 vi.useFakeTimers();let enter!:(l:unknown)=>Promise<unknown>;let signal!:AbortSignal
 vi.stubGlobal('navigator',{locks:{request:(_k:string,o:{signal:AbortSignal},f:typeof enter)=>{signal=o.signal;enter=f;return new Promise(()=>{})}}})
 const action=vi.fn(),pending=boundedFrozenLock('same-durable-key',action,30),rejected=expect(pending).rejects.toThrow(FROZEN_LOCK_MESSAGE)
 await vi.advanceTimersByTimeAsync(30);await rejected;expect(signal.aborted).toBe(true)
 await expect(enter({})).rejects.toThrow(FROZEN_LOCK_MESSAGE);expect(action).not.toHaveBeenCalled()
})
it('retains an acquired lock until the bounded action completes even after queue deadline',async()=>{
 vi.useFakeTimers();let finish!:(v:string)=>void;let signal!:AbortSignal
 vi.stubGlobal('navigator',{locks:{request:async(_k:string,o:{signal:AbortSignal},f:()=>Promise<string>)=>{signal=o.signal;return await f()}}})
 const pending=boundedFrozenLock('same-durable-key',()=>new Promise<string>(r=>{finish=r}),30)
 await vi.advanceTimersByTimeAsync(60);expect(signal.aborted).toBe(false);finish('same-result');expect(await pending).toBe('same-result');expect(vi.getTimerCount()).toBe(0)
})
it('takes the original key, an exclusive lock and an abort signal',async()=>{
 const request=vi.fn(async(_k:string,_o:unknown,f:()=>unknown)=>f());vi.stubGlobal('navigator',{locks:{request}})
 expect(await boundedFrozenLock('original-actor-source',()=>17)).toBe(17)
 expect(request.mock.calls[0][0]).toBe('original-actor-source');expect(request.mock.calls[0][1]).toMatchObject({mode:'exclusive',signal:expect.any(AbortSignal)})
})
it('does not leave a queue timer behind on synchronous lock or callback failure',async()=>{
 vi.useFakeTimers();vi.stubGlobal('navigator',{locks:{request:()=>{throw Error('lock unavailable')}}})
 await expect(boundedFrozenLock('key',()=>0,30)).rejects.toThrow('lock unavailable');expect(vi.getTimerCount()).toBe(0)
 vi.stubGlobal('navigator',{locks:{request:async(_k:string,_o:unknown,f:()=>unknown)=>f()}})
 await expect(boundedFrozenLock('key',()=>{throw Error('callback failed')},30)).rejects.toThrow('callback failed');expect(vi.getTimerCount()).toBe(0)
})
