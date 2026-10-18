// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedAuditTrailPage from './ConnectedAuditTrailPage'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))
const A='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',B='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const entity=(n:number)=>`${String(n).padStart(8,'0')}-0000-4000-8000-000000000000`
type Q=Record<string,unknown>
// 30 log rows, ids 130 (newest) down to 101, one minute apart; even ids are customers made by A, odd ids products changed by B.
const log=Array.from({length:30},(_,i)=>{const n=130-i;return{id:String(n),at:new Date(Date.UTC(2026,9,17,3,59-i,0)).toISOString().replace('Z','+00:00'),
 entity_type:n%2?'products':'customers',entity_id:entity(n),action:n%2?'UPDATE':'INSERT',actor_id:n%2?B:A,actor_name:n%2?'Budi Admin':'Ani Owner',
 reason:n===128?'=HYPERLINK("x")':`Alasan ${n}`,changed_keys:n%2?['customer_name']:['code','name'],changed_key_count:n%2?1:2,has_before:n%2===1,has_after:true}})
const wib=(at:string)=>new Date(Date.parse(at)+7*3600e3).toISOString().slice(0,10)
let extra:Partial<{can_export:boolean;newer:boolean;changed:boolean;total:string;detail:Q}>={}
function serve(q:Q){
 const asOf=(q.as_of as string|null)??'130'
 const hit=log.filter(r=>Number(r.id)<=Number(asOf)&&(!q.entity_type||r.entity_type===q.entity_type)&&(!q.action||r.action===q.action)&&(!q.actor_id||r.actor_id===q.actor_id)
  &&(!q.from||wib(r.at)>=String(q.from))&&(!q.to||wib(r.at)<=String(q.to))&&(!q.q||r.reason.toLowerCase().includes(String(q.q).toLowerCase())||r.entity_id.includes(String(q.q))))
 // The listing's mark (count-sum of its ids inside the cutoff); the keyset cursor is '<id>:<mark>'.
 const mark=`${hit.length}-${hit.reduce((n,r)=>n+Number(r.id),0)}`,[after,cursorMark]=q.after?String(q.after).split(':'):[null,null]
 const listed=(q.listed as string|null|undefined)??cursorMark??mark,changed=extra.changed??listed!==mark
 const start=after?hit.findIndex(r=>r.id===after)+1:0,limit=Number(q.limit),offset=Number(q.offset),rest=hit.slice(start+offset),rows=rest.slice(0,limit),more=rest.length>limit
 const row=log.find(r=>r.id===q.id)
 return{contract_version:'cp7.audit-trail.v1',read_at:'2026-10-17T04:00:00.123456+00:00',business_DML:false,can_export:extra.can_export??true,
  query:{from:q.from??null,to:q.to??null,entity_type:q.entity_type??null,action:q.action??null,actor_id:q.actor_id??null,q:q.q??null},
  snapshot:{as_of:asOf,newer:(extra.newer??false)||changed,listed,changed},
  page:{rows,total:extra.total??String(hit.length),before:String(start),offset,limit,after:q.after??null,next_after:more?`${rows[rows.length-1].id}:${listed}`:null,next_offset:more?offset+limit:null},
  options:{entity_types:['customers','products'],actions:['INSERT','UPDATE'],actors:[{id:A,name:'Ani Owner'},{id:B,name:'Budi Admin'}]},
  detail:q.id?extra.detail??{...row,data_bytes:120,too_large:false,fields_total:3,raw_before:null,raw_after:null,
   fields:row!.changed_key_count===1?[{key:'customer_name',before:'Toko A',after:'Toko B',changed:true},{key:'phone',before:'0812',after:'0812',changed:false},{key:'row_version',before:null,after:null,changed:false}]
    :[{key:'code',before:null,after:'CUS-1',changed:true},{key:'name',before:null,after:'Toko A',changed:true},{key:'phone',before:null,after:null,changed:false}]}:null}
}
let root:Root,container:HTMLDivElement
function identity(...extraPermissions:string[]){const auth=structuredClone(recoveryIdentity) as typeof recoveryIdentity&{identity:{permissions:string[]}};auth.identity.permissions.push(...extraPermissions);return auth}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});extra={};mock.rpc.mockReset();mock.auth=identity('settings.audit.view','settings.audit.export')
 mock.rpc.mockImplementation((_name:string,{p_query}:{p_query:Q})=>Promise.resolve({data:serve(p_query),error:null}))
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedAuditTrailPage/>));await flush()}
const button=(name:string)=>{const b=[...container.querySelectorAll('button')].find(e=>e.textContent===name);if(!b)throw Error(`Missing ${name}: ${container.textContent}`);return b}
async function click(e:HTMLElement){await act(async()=>e.click());await flush()}
async function fill(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function choose(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`)!;e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
const shown=()=>[...container.querySelectorAll<HTMLElement>('[data-audit-id]')].map(e=>e.dataset.auditId)
const lastQuery=()=>mock.rpc.mock.calls.at(-1)![1].p_query as Q
const blobText=(b:Blob)=>new Promise<string>(resolve=>{const r=new FileReader();r.onload=()=>resolve(String(r.result));r.readAsText(b)})
const ids=(from:number,to:number)=>Array.from({length:from-to+1},(_,i)=>String(from-i))

describe('Audit Trail connected (R3-03)',()=>{
 it('needs settings.audit.view and reads nothing without it',async()=>{
  mock.auth=identity();await mount()
  expect(container.textContent).toContain('Hak melihat jejak audit diperlukan.');expect(mock.rpc).not.toHaveBeenCalled()
 })
 it('reads the newest page through the one facade with a closed query, and shows actor, data, reason and changed keys',async()=>{
  await mount()
  expect(mock.rpc).toHaveBeenCalledTimes(1)
  expect(mock.rpc.mock.calls[0]).toEqual(['erp_cp7_get_audit_trail_v1',{p_query:{from:null,to:null,entity_type:null,action:null,actor_id:null,q:null,as_of:null,after:null,listed:null,id:null,offset:0,limit:25}}])
  expect(shown()).toEqual(ids(130,106))
  expect(container.textContent).toContain('Baris 1–25 dari 30 catatan')
  const first=container.querySelector('[data-audit-id="130"]')!.textContent!
  for(const t of ['Dibuat · Pelanggan','Ani Owner','Alasan 130','Kolom berubah: code, name',entity(130),'WIB'])expect(first).toContain(t)
  expect(container.querySelector('[data-audit-id="129"]')!.textContent).toContain('Diubah · Produk & SKU')
 })
 it('pages inside the listing fixed by the first page (as_of + keyset) and back',async()=>{
  await mount()
  await click(button('Halaman berikutnya'))
  expect(lastQuery()).toMatchObject({as_of:'130',after:'106:30-3465',listed:'30-3465',offset:0,limit:25,id:null})
  expect(shown()).toEqual(ids(105,101));expect(container.textContent).toContain('Baris 26–30 dari 30 catatan')
  expect(button('Halaman berikutnya').disabled).toBe(true)
  await click(button('Halaman sebelumnya'))
  expect(lastQuery()).toMatchObject({as_of:'130',after:null,listed:'30-3465'});expect(shown()).toEqual(ids(130,106))
  expect(button('Halaman sebelumnya').disabled).toBe(true)
  // Muat ulang starts a new listing: a new cutoff from the server.
  await click(button('Muat ulang'));expect(lastQuery()).toMatchObject({as_of:null,after:null,listed:null})
 })
 it('stops paging and asks for Muat ulang when a lower id committed late inside the listing (ASTRA-R3-02)',async()=>{
  await mount();expect(container.textContent).not.toContain('Daftar ini berubah')
  extra.changed=true
  await click(button('Halaman berikutnya'))
  expect(lastQuery()).toMatchObject({as_of:'130',after:'106:30-3465',listed:'30-3465'})
  expect(container.querySelector('[role="alert"]')!.textContent).toContain('Daftar ini berubah sejak dibuka')
  expect(container.textContent).not.toContain('Ada catatan baru sesudah daftar ini dibuka')
  expect(button('Halaman berikutnya').disabled).toBe(true);expect(button('Halaman sebelumnya').disabled).toBe(true)
  extra.changed=undefined
  await click(button('Muat ulang'));expect(lastQuery()).toMatchObject({as_of:null,after:null,listed:null})
  expect(container.textContent).not.toContain('Daftar ini berubah');expect(button('Halaman berikutnya').disabled).toBe(false)
 })
 it('applies the filters only on Tampilkan, retiring the shown rows while they are edited',async()=>{
  await mount();const calls=mock.rpc.mock.calls.length
  await fill('Cari jejak audit','  alasan 1  ')
  expect(shown()).toEqual([]);expect(container.textContent).toContain('Filter belum diterapkan');expect(mock.rpc.mock.calls).toHaveLength(calls)
  await choose('Jenis data audit','customers');await choose('Aksi audit','INSERT');await choose('Pengguna audit',A)
  await fill('Audit dari tanggal','2026-10-17');await fill('Audit sampai tanggal','2026-10-17')
  await click(button('Tampilkan'))
  expect(lastQuery()).toEqual({from:'2026-10-17',to:'2026-10-17',entity_type:'customers',action:'INSERT',actor_id:A,q:'alasan 1',as_of:null,after:null,listed:null,id:null,offset:0,limit:25})
  expect(shown()).toEqual(['130','126','124','122','120','118','116','114','112','110','108','106','104','102'])
  expect(container.textContent).toContain('Baris 1–14 dari 14 catatan')
  await fill('Audit dari tanggal','2026-10-18');await click(button('Tampilkan'))
  expect(container.textContent).toContain('Tanggal mulai harus sama atau sebelum tanggal akhir.');expect(lastQuery().from).toBe('2026-10-17')
  await click(button('Hapus filter'));expect(lastQuery()).toMatchObject({from:null,to:null,entity_type:null,action:null,actor_id:null,q:null})
 })
 it('shows one row in detail with the value before and after each changed key',async()=>{
  await mount()
  await click(container.querySelector<HTMLElement>('[data-audit-id="129"]')!)
  expect(lastQuery()).toMatchObject({id:'129',as_of:'130',after:null})
  const aside=container.querySelector('[aria-label="Rincian catatan audit"]')!
  expect(aside.textContent).toContain('Catatan audit #129');expect(aside.textContent).toContain('Budi Admin');expect(aside.textContent).toContain('Alasan 129')
  const field=aside.querySelector('[data-audit-field="customer_name"]')!
  expect(field.textContent).toContain('Sebelum: Toko A');expect(field.textContent).toContain('Sesudah: Toko B')
  expect(aside.querySelector('[data-audit-field="phone"]')).toBeNull();expect(aside.querySelector('details')!.textContent).toContain('Kolom lain yang tidak berubah (2)')
  expect(container.querySelector('[data-audit-id="129"]')!.getAttribute('aria-pressed')).toBe('true')
  const calls=mock.rpc.mock.calls.length;await click(button('Tutup rincian'))
  expect(mock.rpc.mock.calls).toHaveLength(calls);expect(aside.textContent).not.toContain('Catatan audit #129')
 })
 it('says plainly when one row is too large to show',async()=>{
  extra.detail={...log[1],data_bytes:700000,too_large:true,fields:[],fields_total:0,raw_before:null,raw_after:null}
  await mount();await click(container.querySelector<HTMLElement>('[data-audit-id="129"]')!)
  expect(container.textContent).toContain('Isi data catatan ini terlalu besar untuk ditampilkan di layar.')
 })
 it('downloads the shown rows as CSV only with settings.audit.export and the server agreeing',async()=>{
  let blob:Blob|null=null
  const create=vi.fn((b:Blob)=>{blob=b;return 'blob:audit'}),revoke=vi.fn()
  Object.assign(URL,{createObjectURL:create,revokeObjectURL:revoke})
  const clicked=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
  await mount();await click(button('Unduh CSV halaman ini'))
  expect(create).toHaveBeenCalledTimes(1);expect(clicked).toHaveBeenCalledTimes(1)
  const lines=(await blobText(blob!)).replace(/^﻿/,'').trimEnd().split('\r\n')
  expect(lines).toHaveLength(26)
  expect(lines[0]).toBe('"ID catatan","Waktu (WIB)","Pengguna","Jenis data","Nomor data","Aksi","Alasan","Kolom berubah"')
  expect(lines.slice(1).map(l=>l.slice(1,4))).toEqual(ids(130,106))
  expect(lines[3]).toContain(`"'=HYPERLINK(""x"")"`)
  expect(lines[1]).toContain('"Ani Owner","customers","'+entity(130)+'","INSERT","Alasan 130","code, name"')
  await act(async()=>root.unmount());root=createRoot(container)
  mock.auth=identity('settings.audit.view');await mount()
  expect([...container.querySelectorAll('button')].some(b=>b.textContent==='Unduh CSV halaman ini')).toBe(false)
  expect(container.textContent).toContain('Unduh CSV hanya untuk pengguna dengan hak ekspor audit.')
  await act(async()=>root.unmount());root=createRoot(container)
  mock.auth=identity('settings.audit.view','settings.audit.export');extra.can_export=false;await mount()
  expect([...container.querySelectorAll('button')].some(b=>b.textContent==='Unduh CSV halaman ini')).toBe(false)
 })
 it('formats counts id-ID and tells when newer rows exist',async()=>{
  extra={total:'1234567',newer:true};await mount()
  expect(container.textContent).toContain('Baris 1–25 dari 1.234.567 catatan')
  expect(container.textContent).toContain('Ada catatan baru sesudah daftar ini dibuka')
 })
 it('shows no rows and no numbers when the answer does not match the request or the server refuses',async()=>{
  await mount();expect(shown()).toHaveLength(25)
  mock.rpc.mockImplementationOnce((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:{...serve(p_query),extra:1},error:null}))
  await click(button('Muat ulang'));expect(shown()).toEqual([]);expect(container.textContent).toContain('Jawaban jejak audit tidak cocok dengan permintaan.');expect(container.textContent).not.toContain('Baris')
  mock.rpc.mockImplementationOnce((_n:string,{p_query}:{p_query:Q})=>{const d=serve(p_query);d.page.rows=[d.page.rows[1],d.page.rows[0],...d.page.rows.slice(2)];return Promise.resolve({data:d,error:null})})
  await click(button('Muat ulang'));expect(shown()).toEqual([]);expect(container.textContent).toContain('tidak cocok')
  mock.rpc.mockImplementationOnce((_n:string,{p_query}:{p_query:Q})=>{const d=serve(p_query);d.page.rows=d.page.rows.map(r=>({...r,entity_type:'products'}));return Promise.resolve({data:d,error:null})})
  await choose('Jenis data audit','customers');await click(button('Tampilkan'));expect(lastQuery().entity_type).toBe('customers');expect(shown()).toEqual([]);expect(container.textContent).toContain('tidak cocok')
  await click(button('Hapus filter'));expect(shown()).toHaveLength(25)
  mock.rpc.mockImplementationOnce((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:{...serve(p_query),snapshot:{as_of:'131',newer:false}},error:null}))
  await click(button('Halaman berikutnya'));expect(lastQuery().as_of).toBe('130');expect(shown()).toEqual([]);expect(container.textContent).toContain('tidak cocok')
  mock.rpc.mockResolvedValueOnce({data:null,error:{code:'42501',message:'CP7_AUDIT_DENIED'}})
  await click(button('Muat ulang'));expect(container.textContent).toContain('Akun ini tidak punya hak melihat jejak audit.');expect(container.textContent).not.toContain('Baris')
  mock.rpc.mockResolvedValueOnce({data:null,error:{code:'P0001',message:'CP7_AUDIT_CURSOR_GONE'}})
  await click(button('Muat ulang'));expect(container.textContent).toContain('Tekan Muat ulang untuk membaca dari halaman pertama.')
 })
 it('does not paint an answer that arrives after the filter changed',async()=>{
  let late:((v:unknown)=>void)|null=null
  mock.rpc.mockImplementationOnce(()=>new Promise(resolve=>{late=resolve}))
  await mount();await fill('Cari jejak audit','baru')
  await act(async()=>late!({data:serve({offset:0,limit:25}),error:null}));await flush()
  expect(shown()).toEqual([]);expect(container.textContent).not.toContain('Baris')
 })
})
