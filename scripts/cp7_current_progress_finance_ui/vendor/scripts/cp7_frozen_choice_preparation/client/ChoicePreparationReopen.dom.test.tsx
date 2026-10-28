// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {ChoicePreparationGate} from './PreparedFrozenChoicePanel'
import {analogContext} from '../../../tests/fixtures/nativeProductAnalog'
import {prepReply} from './preparationFixture'

let root:Root,container:HTMLDivElement
const client={rpc:vi.fn()},lost=vi.fn()
const context={...analogContext(),sourceMethod:'FROZEN_V2' as const}
const response=(state:string)=>({data:prepReply(state),error:null})
const advance=async(ms:number)=>act(async()=>{await vi.advanceTimersByTimeAsync(ms)})
const mount=async()=>act(async()=>{
 root.render(<ChoicePreparationGate client={client} context={context} scope="test:reopen" enabled onAccessLost={lost}>{ready=><span data-ready={String(ready)}/>}</ChoicePreparationGate>)
 await vi.advanceTimersByTimeAsync(0)
})
const continuation=()=>[...container.querySelectorAll('button')].find(b=>b.textContent==='Lanjutkan persiapan yang sama')!
beforeEach(()=>{
 vi.useFakeTimers();Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true})
 client.rpc.mockReset();lost.mockReset()
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.useRealTimers();vi.restoreAllMocks()})

it('reopened running work reaches READY through status reads alone',async()=>{
 client.rpc.mockResolvedValueOnce(response('RUNNING')).mockResolvedValue(response('READY'))
 await mount();expect(container.textContent).toContain('Menyiapkan data pembanding')
 expect(continuation().disabled).toBe(false)
 await advance(2000)
 expect(container.textContent).toContain('Persiapan selesai. Pilihan belum disimpan.')
 expect(container.querySelector('[data-ready]')?.getAttribute('data-ready')).toBe('true')
 expect(client.rpc.mock.calls).toEqual(Array(2).fill(['erp_cp7_get_frozen_choice_preparation_v1',{p_source_request:context.requestId,p_access:context.accessEpoch}]))
 await advance(10000);expect(client.rpc).toHaveBeenCalledTimes(2)
})

it('reopened queued work observes a real terminal failure without starting work',async()=>{
 client.rpc.mockResolvedValueOnce(response('QUEUED')).mockResolvedValue(response('FAILED'))
 await mount();await advance(2000)
 expect(container.textContent).toContain('Persiapan gagal. Pilihan belum disimpan.')
 expect(container.querySelector('[data-ready]')?.getAttribute('data-ready')).toBe('false')
 await advance(10000);expect(client.rpc).toHaveBeenCalledTimes(2)
 expect(client.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_frozen_choice_preparation_v1')).toBe(true)
})

it('unchanged reopened work stops monitoring honestly and leaves same-work recovery enabled',async()=>{
 client.rpc.mockResolvedValue(response('RUNNING'))
 await mount();await advance(120000)
 expect(container.querySelector('[role=alert]')?.textContent).toContain('proses server belum dinyatakan gagal')
 expect(container.textContent).not.toContain('Persiapan gagal.')
 expect(continuation().disabled).toBe(false)
 const calls=client.rpc.mock.calls.length
 await advance(10000);expect(client.rpc).toHaveBeenCalledTimes(calls)
})

it('revoked access during reopened polling clears the state and stops further reads',async()=>{
 client.rpc.mockResolvedValueOnce(response('RUNNING')).mockResolvedValue({data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}})
 await mount();await advance(2000)
 expect(lost).toHaveBeenCalledOnce();expect(container.textContent).not.toContain('Menyiapkan data pembanding')
 expect(container.querySelector('[data-ready]')?.getAttribute('data-ready')).toBe('false')
 await advance(10000);expect(client.rpc).toHaveBeenCalledTimes(2)
})

it('does not overlap status reads and ignores a poll that completes after closing',async()=>{
 let resolve!:(r:unknown)=>void
 client.rpc.mockResolvedValueOnce(response('RUNNING')).mockImplementation(()=>new Promise(r=>{resolve=r}))
 await mount();await advance(2000);expect(client.rpc).toHaveBeenCalledTimes(2)
 await advance(6000);expect(client.rpc).toHaveBeenCalledTimes(2)
 await act(async()=>root.render(null))
 await act(async()=>{resolve(response('READY'));await vi.advanceTimersByTimeAsync(0)})
 await advance(10000);expect(container.textContent).toBe('');expect(client.rpc).toHaveBeenCalledTimes(2)
})

it('an older poll cannot replace the result of explicit continuation of the same work',async()=>{
 let resolve!:(r:unknown)=>void
 client.rpc.mockResolvedValueOnce(response('RUNNING')).mockImplementation((name:string)=>{
  if(name==='erp_cp7_get_frozen_choice_preparation_v1')return new Promise(r=>{resolve=r})
  return Promise.resolve(response(name==='erp_cp7_request_frozen_choice_preparation_v1'?'QUEUED':'READY'))
 })
 await mount();await advance(2000)
 await act(async()=>{continuation().click();await vi.advanceTimersByTimeAsync(0)})
 expect(container.querySelector('[data-ready]')?.getAttribute('data-ready')).toBe('true')
 await act(async()=>{resolve(response('FAILED'));await vi.advanceTimersByTimeAsync(0)})
 await advance(10000)
 expect(container.textContent).toContain('Persiapan selesai. Pilihan belum disimpan.')
 expect(client.rpc.mock.calls.map(([name])=>name)).toEqual(['erp_cp7_get_frozen_choice_preparation_v1','erp_cp7_get_frozen_choice_preparation_v1','erp_cp7_request_frozen_choice_preparation_v1','erp_cp7_step_frozen_choice_preparation_v1'])
 expect(client.rpc.mock.calls.every(([,args])=>args.p_source_request===context.requestId&&args.p_access===context.accessEpoch)).toBe(true)
})

it('a lost status response stops after the existing reply bound without creating another work',async()=>{
 client.rpc.mockResolvedValueOnce(response('RUNNING')).mockImplementation(()=>new Promise(()=>{}))
 await mount();await advance(32000)
 expect(container.querySelector('[role=alert]')?.textContent).toContain('Hasil permintaan belum diketahui')
 expect(continuation().disabled).toBe(false)
 await advance(10000);expect(client.rpc).toHaveBeenCalledTimes(2)
 expect(client.rpc.mock.calls.every(([name])=>name==='erp_cp7_get_frozen_choice_preparation_v1')).toBe(true)
})

it('disappeared work after an observed status is reported instead of silently keeping RUNNING',async()=>{
 client.rpc.mockResolvedValueOnce(response('RUNNING')).mockResolvedValue({data:null,error:{message:'CP7_CHOICE_PREPARATION_NOT_STARTED'}})
 await mount();await advance(2000)
 expect(container.querySelector('[role=alert]')).not.toBeNull()
 expect(continuation().disabled).toBe(false)
 await advance(10000);expect(client.rpc).toHaveBeenCalledTimes(2)
})
