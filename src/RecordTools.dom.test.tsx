// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import RecordTools,{orderRecordPage} from './RecordTools'
let root:Root,host:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});host=document.createElement('div');document.body.append(host);root=createRoot(host)})
afterEach(async()=>{await act(async()=>root.unmount());host.remove()})
describe('record tools preserve the authorized source',()=>{
 it('opens actual controls, keeps hidden filter values, and browses without a business write',async()=>{
  const browse=vi.fn(),submit=vi.fn(),order=vi.fn()
  await act(async()=>root.render(<RecordTools title="invoice" busy={false} order="SOURCE" onOrder={order} onBrowse={browse} onSubmit={e=>{e.preventDefault();submit()}} submitLabel="Cari invoice" search={<label>Nomor<input aria-label="Nomor" defaultValue="INV-9"/></label>} filters={<label>Status<select aria-label="Status" defaultValue="PAID"><option value="PAID">Lunas</option></select></label>}/>))
  const button=(label:string)=>[...host.querySelectorAll('button')].find(x=>x.textContent===label)!
  await act(async()=>button('Cari').click());expect(document.activeElement).toBe(host.querySelector('[aria-label="Nomor"]'))
  await act(async()=>button('Filter').click());expect(button('Filter').getAttribute('aria-expanded')).toBe('false');expect(host.querySelector<HTMLSelectElement>('[aria-label="Status"]')!.value).toBe('PAID')
  await act(async()=>button('Browse semua').click());expect(browse).toHaveBeenCalledOnce();expect(submit).not.toHaveBeenCalled()
  const select=host.querySelector<HTMLSelectElement>('[aria-label="Urutkan halaman invoice"]')!
  await act(async()=>{select.value='LABEL_DESC';select.dispatchEvent(new Event('change',{bubbles:true}))});expect(order).toHaveBeenCalledWith('LABEL_DESC');expect(submit).not.toHaveBeenCalled()
 })
 it('does not mutate source order or detach exact balances, revisions, identities and selected records',()=>{
  const a=Object.freeze({id:'one',name:'INV-10',balance:'9007199254740993.01',revision:'9007199254740999'}),b=Object.freeze({id:'two',name:'INV-2',balance:'9007199254740991.99',revision:'9007199254740997'})
  const source=Object.freeze([a,b]),ordered=orderRecordPage(source,'LABEL_ASC',r=>r.name)
  expect(source).toEqual([a,b]);expect(ordered).toEqual([b,a]);expect(ordered[1]).toBe(a);expect(ordered[1].balance).toBe('9007199254740993.01');expect(ordered[1].revision).toBe('9007199254740999')
 })
})
