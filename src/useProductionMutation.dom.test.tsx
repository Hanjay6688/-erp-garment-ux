// @vitest-environment jsdom
import{act}from'react'
import{createRoot,type Root}from'react-dom/client'
import{afterEach,beforeEach,expect,it,vi}from'vitest'
import{useProductionMutation,type ProductionMutationHandlers}from'./useProductionMutation'
import{recoveryIdentity}from'../tests/fixtures/productionRecovery'
import{readProductionRecovery}from'./productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
let root:Root,container:HTMLDivElement,recovery:ReturnType<typeof useProductionMutation>
function Harness(){recovery=useProductionMutation('PAYROLL_INSTALLMENT');return <div><span>{recovery.writerLocked?'LOCKED':'READY'}</span><p>{recovery.error}</p><p>{recovery.notice}</p></div>}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});state.auth=structuredClone(recoveryIdentity);localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function mount(){await act(async()=>root.render(<Harness/>));await act(async()=>{const ticket=recovery.beginRead();expect(recovery.finishRead(ticket)).toBe(true)})}
function handlers(reload:ProductionMutationHandlers['reload']){return{send:vi.fn(async e=>({data:{request_id:e.id},error:null})),validate:(data:unknown,e)=>{expect((data as{request_id:string}).request_id).toBe(e.id)},retire:vi.fn(),reload}as ProductionMutationHandlers}
const run=(h:ProductionMutationHandlers)=>recovery.run('PAY',{document:{payroll_id:'00000000-0000-4000-8000-000000000001'},expected_version:'1'},null,h)
it('accepts the completed newer source read when parent refresh cancels the older request',async()=>{
 await mount();const h=handlers(async()=>{const older=recovery.beginRead();const newer=recovery.beginRead();await Promise.resolve();expect(recovery.finishRead(newer)).toBe(true);expect(recovery.finishRead(older)).toBe(false);return false})
 await act(async()=>{expect(await run(h)).toBe(true)})
 expect(h.send).toHaveBeenCalledTimes(1);expect(recovery.writerLocked).toBe(false);expect(recovery.error).toBe('');expect(recovery.notice).not.toBe('');expect(readProductionRecovery('disposable:actor-1').pending).toEqual({})
})
it('keeps all writes locked after a committed action when every source refresh fails',async()=>{
 await mount();const h=handlers(async()=>{recovery.beginRead();return false});await act(async()=>{expect(await run(h)).toBe(false)})
 expect(recovery.writerLocked).toBe(true);expect(recovery.error).toContain('refresh authoritative gagal');await act(async()=>{expect(await run(h)).toBe(false)});expect(h.send).toHaveBeenCalledTimes(1)
})
it('rejects a pre-commit held source reply as proof of recovery',async()=>{
 await mount();let held:ReturnType<typeof recovery.beginRead>;await act(async()=>{held=recovery.beginRead();expect(recovery.finishRead(held)).toBe(true)})
 const h=handlers(async()=>{expect(recovery.finishRead(held!)).toBe(false);return false});await act(async()=>{expect(await run(h)).toBe(false)})
 expect(recovery.writerLocked).toBe(true);expect(recovery.error).toContain('refresh authoritative gagal');expect(h.send).toHaveBeenCalledTimes(1)
})
it('clears a failed-refresh notice only after a later current source read completes without another payment',async()=>{
 await mount();let current:ReturnType<typeof recovery.beginRead>;const h=handlers(async()=>{current=recovery.beginRead();return false});await act(async()=>{expect(await run(h)).toBe(false)})
 expect(recovery.error).toContain('refresh authoritative gagal');await act(async()=>{expect(recovery.finishRead(current!)).toBe(true)})
 expect(recovery.error).toBe('');expect(recovery.writerLocked).toBe(false);expect(h.send).toHaveBeenCalledTimes(1)
})
it('retires a prior successful-read notice as soon as a newer read or shared invalidation retires its proof',async()=>{
 await mount();const h=handlers(async()=>{const ticket=recovery.beginRead();return recovery.finishRead(ticket)})
 await act(async()=>{expect(await run(h)).toBe(true)});expect(recovery.notice).toContain('sudah dimuat ulang')
 await act(async()=>{recovery.beginRead()});expect(recovery.notice).toBe('');expect(recovery.writerLocked).toBe(true)
 await act(async()=>{const ticket=recovery.beginRead();expect(recovery.finishRead(ticket)).toBe(true);expect(await run(h)).toBe(true)})
 expect(recovery.notice).toContain('sudah dimuat ulang');await act(async()=>window.dispatchEvent(new StorageEvent('storage',{key:null})))
 expect(recovery.notice).toBe('');expect(recovery.writerLocked).toBe(true);expect(h.send).toHaveBeenCalledTimes(2)
})
it('rejects a held reply after explicit invalidation even when the recovery signature has not changed',async()=>{
 await mount();let held:ReturnType<typeof recovery.beginRead>
 await act(async()=>{held=recovery.beginRead();recovery.invalidate()})
 expect(recovery.isReadCurrent(held!)).toBe(false)
 await act(async()=>{expect(recovery.finishRead(held!)).toBe(false)})
 expect(recovery.writerLocked).toBe(true)
})
it('binds a child read to the exact completed parent proof and retires it on a shared invalidation',async()=>{
 await mount();const ticket=recovery.currentReadTicket()
 expect(ticket).not.toBeNull();expect(recovery.writerLocked).toBe(false)
 expect(recovery.isReadCurrent(ticket!)).toBe(true)
 await act(async()=>window.dispatchEvent(new StorageEvent('storage',{key:null})))
 expect(recovery.currentReadTicket()).toBeNull();expect(recovery.isReadCurrent(ticket!)).toBe(false)
 await act(async()=>{expect(recovery.finishRead(ticket!)).toBe(false)})
 expect(recovery.writerLocked).toBe(true)
})
