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
 it('labels the scope honestly: whole-result screens say so, page-only screens keep their page wording',async()=>{
  const tools=(props:{filterScope?:'ALL_MATCHING'|'PAGE';searchScope?:'ALL_MATCHING'|'PAGE';orderScope?:'ALL_MATCHING'|'PAGE'})=><RecordTools title="nota" busy={false} order="SOURCE" onOrder={()=>{}} onBrowse={()=>{}} onSubmit={e=>e.preventDefault()} submitLabel="Cari" search={<input aria-label="q"/>} filters={<select aria-label="s"/>} {...props}/>
  await act(async()=>root.render(tools({orderScope:'ALL_MATCHING'})))
  expect(host.querySelector('[aria-label="Urutkan nota"]')).not.toBeNull();expect(host.querySelector('[aria-label="Urutkan halaman nota"]')).toBeNull()
  expect(host.textContent).toContain('Urutkan semua hasil');expect(host.textContent).toContain('Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain; jumlah hasil mengikuti filter yang sama.');expect(host.textContent).not.toContain('halaman yang sedang tampil')
  await act(async()=>root.render(tools({filterScope:'PAGE'})))
  expect(host.querySelector('[aria-label="Urutkan halaman nota"]')).not.toBeNull();expect(host.textContent).toContain('Urutkan halaman ini');expect(host.textContent).toContain('Filter dan urutan hanya mengatur halaman yang sedang tampil.')
  await act(async()=>root.render(tools({})))
  expect(host.textContent).toContain('Urutan hanya mengatur halaman yang sedang tampil.');expect(host.textContent).not.toContain('Filter dan urutan')
  await act(async()=>root.render(tools({searchScope:'PAGE',filterScope:'PAGE'})))
  expect(host.textContent).toContain('Pencarian hanya menelusuri halaman yang sedang tampil.')
 })
 it('does not mutate source order or detach exact balances, revisions, identities and selected records',()=>{
  const a=Object.freeze({id:'one',name:'INV-10',balance:'9007199254740993.01',revision:'9007199254740999'}),b=Object.freeze({id:'two',name:'INV-2',balance:'9007199254740991.99',revision:'9007199254740997'})
  const source=Object.freeze([a,b]),ordered=orderRecordPage(source,'LABEL_ASC',r=>r.name)
  expect(source).toEqual([a,b]);expect(ordered).toEqual([b,a]);expect(ordered[1]).toBe(a);expect(ordered[1].balance).toBe('9007199254740993.01');expect(ordered[1].revision).toBe('9007199254740999')
 })
})
