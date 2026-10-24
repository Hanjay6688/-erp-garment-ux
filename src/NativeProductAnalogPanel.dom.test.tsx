// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,it,expect,vi} from 'vitest'
import NativeProductAnalogPanel from './NativeProductAnalogPanel'
import {analogContext,analogReply,analogId} from '../tests/fixtures/nativeProductAnalog'
let root:Root,container:HTMLDivElement
const client={rpc:vi.fn()},closed=vi.fn(),lost=vi.fn()
const tick=()=>new Promise<void>(resolve=>setTimeout(resolve,0))
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();closed.mockReset();lost.mockReset();container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
it('retires a held reply when another target is opened',async()=>{
 const first=analogContext(),next={...first,targetKey:analogId(99)+':'+first.targetKey.split(':')[1]}
 let release:(v:unknown)=>void=()=>{}
 client.rpc.mockImplementation((_name:string,args:{p_target:string})=>args.p_target===first.targetKey?new Promise(resolve=>release=resolve):Promise.resolve({data:{...analogReply(next),result:{...analogReply(next).result,candidates:analogReply(next).result.candidates.map(r=>({...r,sku:'NEW-TARGET-CANDIDATE'}))}},error:null}))
 await act(async()=>root.render(<NativeProductAnalogPanel client={client} context={first} label="Lama" onClose={closed} onAccessLost={lost}/>))
 await act(async()=>{root.render(<NativeProductAnalogPanel client={client} context={next} label="Baru" onClose={closed} onAccessLost={lost}/>);await tick()})
 await act(async()=>{release({data:analogReply(first),error:null});await tick()})
 expect(container.textContent).toContain('NEW-TARGET-CANDIDATE');expect(container.textContent).not.toContain('PEMBANDING-0')
 expect(lost).not.toHaveBeenCalled()
})
it('clears the prior page and reports revoked access when requesting the next50 candidates',async()=>{
 const c=analogContext();client.rpc.mockResolvedValueOnce({data:analogReply(c,51),error:null}).mockResolvedValueOnce({data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}})
 await act(async()=>{root.render(<NativeProductAnalogPanel client={client} context={c} label="Produk" onClose={closed} onAccessLost={lost}/>);await tick()})
 expect(container.querySelectorAll('[data-analog-target]')).toHaveLength(50)
 const next=[...container.querySelectorAll('button')].find(b=>b.textContent==='50 kandidat berikutnya')!
 await act(async()=>{next.click();await tick()})
 expect(container.querySelector('tbody')).toBeNull();expect(lost).toHaveBeenCalledOnce();expect(container.textContent).toContain('tidak memiliki izin')
})
