// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import PreparedFrozenChoicePanel from './PreparedFrozenChoicePanel'
import {analogChoiceFixture} from '../../../tests/fixtures/nativeProductAnalogChoice'
import {prepReply} from './preparationFixture'

let root:Root,container:HTMLDivElement
const rpc=vi.fn(),lost=vi.fn(),f=analogChoiceFixture(),context={...f.context,sourceMethod:'FROZEN_V2' as const},candidates={...f.candidates,sourceMethod:'FROZEN_V2' as const}
const tick=()=>new Promise<void>(resolve=>setTimeout(resolve,0))
const mount=async(manage=true)=>act(async()=>{root.render(<PreparedFrozenChoicePanel client={{rpc}} context={context} candidates={candidates} scope="test:prep" canManage={manage} onAccessLost={lost}/>);await tick()})
const button=(text:string)=>[...container.querySelectorAll('button')].find(b=>b.textContent===text)!
const click=async(text:string)=>act(async()=>{expect(button(text)).toBeDefined();button(text).click();await tick()})
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();rpc.mockReset();lost.mockReset()
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:()=>unknown)=>fn()}})
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:name==='erp_cp7_get_frozen_choice_preparation_v1'?{data:null,error:{message:'CP7_CHOICE_PREPARATION_NOT_STARTED'}}:{data:prepReply(name.includes('_step_')?'READY':'QUEUED'),error:null})
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
it('separates preparation from saving and exposes candidates only after actual READY',async()=>{
 await mount();expect(button('Simpan pilihan pembanding').disabled).toBe(true);expect(container.querySelectorAll('select option')).toHaveLength(1)
 await click('Siapkan pemeriksaan pilihan')
 expect(container.textContent).toContain('Persiapan selesai. Pilihan belum disimpan.')
 expect(container.textContent).toContain('1 dari 1 langkah persiapan selesai')
 expect(container.querySelectorAll('select option')).toHaveLength(2)
 expect(rpc.mock.calls.some(([n])=>n==='erp_cp7_save_product_analog_choice_v2')).toBe(false)
})
it('reopening displays same queued work and offers resumption without creating new source',async()=>{
 rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_get_product_analog_choices_v1'?f.raw:prepReply(),error:null}))
 await mount();expect(container.textContent).toContain('Persiapan mengantre.');expect(button('Lanjutkan persiapan yang sama')).toBeDefined()
 expect(container.textContent).toContain('Kelanjutan otomatis di server belum dikonfirmasi.')
 expect(rpc.mock.calls.filter(([n])=>n.includes('frozen_choice_preparation')).map(([,a])=>a.p_source_request)).toEqual([context.requestId])
})
it('failed unit shows recovery explanation and cannot masquerade as saved or complete analysis',async()=>{
 rpc.mockImplementation(async(name:string)=>({data:name==='erp_cp7_get_product_analog_choices_v1'?f.raw:{...prepReply('FAILED'),failure_code:'CP7_CHOICE_PREPARATION_TIME_LIMIT',unit_attempts:3},error:null}))
 await mount();expect(container.textContent).toContain('Persiapan gagal. Pilihan belum disimpan.');expect(container.textContent).toContain('tiga percobaan pada langkah yang sama melampaui batas')
 expect(button('Simpan pilihan pembanding').disabled).toBe(true);expect(container.querySelectorAll('select option')).toHaveLength(1)
})
it('reader without management never starts preparation or receives write controls',async()=>{
 await mount(false);expect(rpc.mock.calls.map(([n])=>n)).toEqual(['erp_cp7_get_product_analog_choices_v1'])
 expect((container.querySelector('fieldset')as HTMLFieldSetElement).disabled).toBe(true)
})
it('current access rejection retires ready data and delegates parent access loss',async()=>{
 rpc.mockImplementation(async(name:string)=>name==='erp_cp7_get_product_analog_choices_v1'?{data:f.raw,error:null}:{data:null,error:{code:'42501',status:403,message:'CP7_ACCESS_DENIED'}})
 await mount();expect(lost).toHaveBeenCalled();expect(container.querySelectorAll('select option')).toHaveLength(1)
})
