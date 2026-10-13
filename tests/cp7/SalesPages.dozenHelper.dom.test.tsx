// @vitest-environment jsdom
// Coverage kept from the retired CP6 browser cases BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}
// (scripts/cp6_bf_browser.mjs salesManual; retired from the CP7 composition in
// docs/cp7/PREFREEZE_RUNTIME_MIGRATION_20261006.md). The same four checks on the same simulation screen
// (SalesPages, shown when the runtime is not the connected DISPOSABLE_TEST mode).
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it} from 'vitest'
import SalesPages from '../../src/SalesPages'

let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
const line=()=>container.querySelector<HTMLElement>('.biz-invoice-lines > article')!
const quantities=()=>[...line().querySelectorAll<HTMLInputElement>('.biz-size-entry input')]
const helper=()=>line().querySelector<HTMLInputElement>('.biz-dozen-helper input')!
async function fill(e:HTMLInputElement,value:string){await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function apply(){await act(async()=>[...line().querySelectorAll('button')].find(b=>b.textContent==='Terapkan')!.click());await flush()}
const values=()=>quantities().map(q=>q.value)

describe('sales simulation dozen helper (retired SALES_MANUAL_13 checks)',()=>{
 it('keeps manual 13 pcs, ignores a blank helper, refuses a fractional piece result and spreads one dozen 4/4/4',async()=>{
  await act(async()=>root.render(<SalesPages view="sales-invoice" onNavigate={()=>{}}/>));await flush()
  expect(quantities()).toHaveLength(3)
  for(const [i,n] of ['5','4','4'].entries())await fill(quantities()[i],n)
  expect(helper().value).toBe('')
  await apply()
  expect(values()).toEqual(['5','4','4'])
  expect(line().querySelector('.biz-line-total')!.textContent).toBe('QTY BARIS · SUMBER AKHIR13 pcs · 1 lusin · 1 potong')
  await fill(helper(),'1.1');await apply()
  expect(values()).toEqual(['5','4','4'])
  await fill(helper(),'1');await apply()
  expect(values()).toEqual(['4','4','4'])
 })
})
