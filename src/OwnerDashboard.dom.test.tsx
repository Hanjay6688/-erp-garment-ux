// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it} from 'vitest'
import {OwnerDashboard} from './OwnerDashboard'
import {initialReminders} from './reminders'

// Owner 12 Oct 2026 (independent audit Fable F-UI-01): the dashboard's sample figures are never shown in a connected build.
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
const noop=()=>{}
async function mount(connected:boolean){await act(async()=>root.render(<OwnerDashboard connected={connected} reminders={initialReminders.map(r=>({...r}))} onOpenSales={noop} onOpenReminders={noop} onToggleReminder={noop}/>))}
const SAMPLE=['Rp284,6 jt','Rp418,2 jt','Rp176,8 jt','Rp298,4 jt','Rp480,5 jt','Rp182,1 jt','Rp18,4 jt','27 Agustus 2026','1.482 pcs','34 pcs']

describe('OwnerDashboard',()=>{
 it('shows no sample figure, date or reminder in a connected build',async()=>{
  await mount(true)
  const text=container.textContent??''
  for(const sample of SAMPLE)expect(text).not.toContain(sample)
  expect(text).not.toMatch(/Rp\s?\d/)
  for(const item of initialReminders)expect(text).not.toContain(item.title)
  expect(container.querySelector('[role="status"][aria-label="Ringkasan dashboard belum tersambung"]')?.textContent).toContain('belum tersambung ke data ERP')
  expect(container.querySelectorAll('.kpi-card').length).toBe(0)
 })
 it('points only to menus that are connected in this build (owner D15-2)',async()=>{
  await act(async()=>root.render(<OwnerDashboard connected connectedMenus={['Produksi','Gudang','Keuangan','Master Data']} reminders={[]} onOpenSales={noop} onOpenReminders={noop} onToggleReminder={noop}/>))
  const notice=container.querySelector('[role="status"][aria-label="Ringkasan dashboard belum tersambung"]')?.textContent??''
  expect(notice).toContain('menu yang sudah tersambung: Produksi, Gudang, Keuangan, Master Data.')
  expect(notice).not.toContain('Penjualan')
 })
 it('keeps the sample dashboard in the demo build',async()=>{
  await mount(false)
  const text=container.textContent??''
  for(const sample of ['Rp284,6 jt','Rp418,2 jt','27 Agustus 2026'])expect(text).toContain(sample)
  expect(container.querySelectorAll('.kpi-card').length).toBe(4)
 })
})
