// @vitest-environment jsdom
// UI entry/binding checks, using the existing analysis panel as a controlled
// boundary. Native arithmetic, access and server feasibility are not asserted.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeCuttingSuggestionsPanel from './NativeCuttingSuggestionsPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown,props:null as null|Record<string,unknown>}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./NativeAnalysisPanel',()=>({default:(props:Record<string,unknown>)=>{state.props=props;return <p>Controlled same analysis panel</p>}}))
let root:Root,container:HTMLDivElement
const start=vi.fn(),end=vi.fn()
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});state.props=null
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'})
 a.identity.permissions.push('master.product.view','warehouse.stock.view','sales.invoice.view','production.cutting.view');state.auth=a
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
const render=async(disabled=false)=>act(async()=>root.render(<NativeCuttingSuggestionsPanel disabled={disabled} onSourceReadStart={start} onSourceReadEnd={end}/>))
const button=()=>container.querySelector('button')!
const fill=async(label:string,value:string)=>act(async()=>{
 const n=container.querySelector(`[aria-label="${label}"]`)as HTMLInputElement
 Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(n,value)
 n.dispatchEvent(new Event('input',{bubbles:true}));n.dispatchEvent(new Event('change',{bubbles:true}))
})
it('asks for the period and reuses the same analysis with explicit checked cutting mode',async()=>{
 await render();expect(button().disabled).toBe(true);expect(state.props).toBeNull()
 await fill('Penjualan mulai untuk saran potong','2026-09-01');await fill('Penjualan sampai untuk saran potong','2026-09-30')
 expect(button().disabled).toBe(false);await act(async()=>button().click())
 expect(state.props).toMatchObject({cuttingSuggestion:true,query:{from_date:'2026-09-01',through_date:'2026-09-30',group_mode:'AS_SOLD'},onSourceReadStart:start,onSourceReadEnd:end})
 expect(container.querySelector('input')?.disabled).toBe(true)
 await act(async()=>{(state.props!.onClose as()=>void)()});expect(container.textContent).not.toContain('Controlled same analysis panel')
 expect(container.querySelector('input')?.disabled).toBe(false)
})
it('refuses a reversed range and stays closed while the parent has an active writer',async()=>{
 await render();await fill('Penjualan mulai untuk saran potong','2026-09-30');await fill('Penjualan sampai untuk saran potong','2026-09-01')
 expect(button().disabled).toBe(true);await fill('Penjualan sampai untuk saran potong','2026-09-30');await render(true)
 expect(button().disabled).toBe(true);expect(state.props).toBeNull()
})
it('hides all suggestion facts when the current view permission is removed',async()=>{
 await render();const a=state.auth as typeof recoveryIdentity
 a.identity.permissions=a.identity.permissions.filter(p=>p!=='production.cutting.view');await render()
 expect(container.textContent).toBe('')
})
