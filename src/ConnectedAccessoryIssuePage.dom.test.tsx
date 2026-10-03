// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedAccessoryIssuePage from './ConnectedAccessoryIssuePage'
import { parseAccessoryWorkspace, previewAccessoryLine, type AccessoryChoice } from './accessoryIssue'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { persistProductionEnvelope, readProductionRecovery } from './productionRecovery'
import TransactionSourceLink, { TransactionSourceProvider } from './TransactionSourceNavigation'
const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',doc='22222222-2222-4222-8222-222222222222',lineId='33333333-3333-4333-8333-333333333333'
const quote:AccessoryChoice={id,sku:'BTN',name:'Kancing silver',category:'Kancing',unit:'PCS',stock:'300.000000',master_price:'36.000000',factor:'12.000000',price_unit:'LUSIN',price_version_id:lineId}
const at='2026-09-22T10:15:00'
let root:Root,container:HTMLDivElement
beforeEach(()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset()
  const a=structuredClone(recoveryIdentity);a.identity.permissions.push('finance.contractor_accessory.view','finance.contractor_accessory.create','finance.contractor_accessory.post','finance.contractor_accessory.reverse');auth.current=a
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}})
  container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})}
async function mount(){await act(async()=>root.render(<ConnectedAccessoryIssuePage/>));await flush()}
async function change(label:string,value:string){const el=container.querySelector<HTMLInputElement|HTMLSelectElement>(`[aria-label="${label}"]`)!;if(!el)throw new Error('Missing '+label)
  await act(async()=>{Object.getOwnPropertyDescriptor(el instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
function button(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent?.trim()===label);if(!b)throw new Error('Missing '+label);return b}
async function click(label:string){await act(async()=>button(label).click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_save_accessory_issue_action_v1')
function documentFixture(){return {id:doc,number:'ACC-001',contractor_id:id,location_id:id,po_id:null,physical_local:at,status:'DRAFT',row_version:'1',notes:'',total:'22.75',payroll_locked:false,
  items:[{id:lineId,material_id:id,sku:'BTN',name:'Kancing silver',unit:'PCS',qty:'7.000000',manual_price:'3.25',price:'3.250000',factor:'1.000000',price_unit:'PCS',price_version_id:null,amount:'22.750000',payroll_status:'UNALLOCATED'}]}}
function server(){
  const s={document:null as ReturnType<typeof documentFixture>|null,lose:false,effects:0,invalid:false,reject:false,stock:'300.000000',badReceipt:false};const cache=new Map<string,unknown>()
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
    if(name==='erp_get_accessory_issue_workspace_v1'){
      const f=args.p_filters as Record<string,unknown>,d=f.id?s.document:null
      const w={filters:f,contractor_id:f.contractor_id??d?.contractor_id??null,location_id:f.location_id??d?.location_id??null,physical_local:typeof f.physical_at==='string'?f.physical_at.slice(0,19):d?.physical_local??at,
        contractors:[{id,name:'Afui'}],locations:[{id,name:'Gudang aksesori'}],orders:[],materials:[{...quote,stock:s.stock}],material_count:1,
        history:s.document?[{id:doc,number:s.document.number,contractor:'Afui',status:s.document.status,row_version:s.document.row_version,date:'2026-09-22',total:s.document.total}]:[],history_count:s.document?1:0,document:d}
      return {data:s.invalid?{...w,materials:[{...quote,stock:300}]}:structuredClone(w),error:null}
    }
    if(s.reject)return {data:null,error:{code:'P0001',message:'Stok sudah berubah'}}
    const p=args.p_payload as Record<string,unknown>,key=String(args.p_client_request_id),action=String(args.p_action)
    if(!cache.has(key)){
      s.effects++
      if(action==='DELETE')s.document=null
      else if(action==='REVERSE'){s.document!.status='REVERSED';s.document!.row_version='4'}
      else {
        const item=(p.items as Record<string,string>[])[0],preview=previewAccessoryLine({material_id:id,qty:item.qty,mode:item.mode as 'MANUAL'|'MASTER',manual_price:item.manual_price??''},quote)
        const cents=(preview.amount!+5000n)/10000n,total=`${cents/100n}.${String(cents%100n).padStart(2,'0')}`
        s.document={...documentFixture(),number:String(p.number),status:action==='POST'?'POSTED':'DRAFT',row_version:'3',total,items:[{...documentFixture().items[0],qty:item.qty+'.000000',manual_price:item.manual_price??null,price:(item.manual_price??'36').replace(/(\.\d+)?$/,m=>(m||'.').padEnd(7,'0')),amount:(preview.amount!/1000000n)+'.'+String(preview.amount!%1000000n).padStart(6,'0')}] as ReturnType<typeof documentFixture>['items']}
      }
      cache.set(key,{id:doc,request_id:key,action,status:action==='DELETE'?'DELETED':s.document!.status,row_version:s.document?.row_version??null})
    }
    return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:s.badReceipt?{request_id:key,status:'POSTED'}:cache.get(key),error:null}
  });return s
}
async function prepare(){await change('Nomor nota aksesori','ACC-NEW');await change('Mandor aksesori',id);await change('Gudang aksesori',id);await click('Perbarui harga dan stok');await change('Tambah aksesori',id);await change('Jumlah PCS 1','7');await change('Harga per PCS 1','3,25')}

describe('connected accessory issue',()=>{
  it('opens an exact stock source outside the50-row history through the owning reader without a write or review',async()=>{
    const s=server();s.document={...documentFixture(),status:'POSTED'}
    const a=structuredClone(recoveryIdentity);Object.assign(a.identity.profile,{authUserId:id});a.identity.permissions=['finance.contractor_accessory.view'];auth.current=a
    const ordinary=client.rpc.getMockImplementation()!,navigate=vi.fn()
    client.rpc.mockImplementation(async(name,args)=>{
      if(name==='erp_cp7_resolve_transaction_source_v1')return{data:{contract_version:'cp7.transaction-source.v1',actor_scope_id:id,source:args.p_source,status:'AVAILABLE',business_DML:false,read_at:'2026-10-03T00:00:00Z',document:{domain:'ACCESSORY_ISSUE',route:'contractor-issue',id:doc,number:'ACC-001',status:'POSTED',revision:'1',focus:null}},error:null}
      const result=await ordinary(name,args)
      if(name==='erp_get_accessory_issue_workspace_v1')return{...result,data:{...result.data,history_count:51,history:Array.from({length:50},(_,i)=>({...result.data.history[0],id:`99999999-9999-4999-8999-${String(i+1).padStart(12,'0')}`,number:`LATEST-${i}`}))}}
      return result
    })
    await act(async()=>root.render(<TransactionSourceProvider scope="accessory-source" onNavigate={navigate}><TransactionSourceLink sourceType="CONTRACTOR_MATERIAL_ISSUE_ITEM" sourceId={lineId}/><ConnectedAccessoryIssuePage/></TransactionSourceProvider>));await flush()
    await click('Buka transaksi asal')
    expect(navigate).toHaveBeenCalledWith('contractor-issue')
    expect(client.rpc.mock.calls.filter(([name])=>name==='erp_get_accessory_issue_workspace_v1').at(-1)?.[1]).toEqual({p_filters:{query:'',material_query:'',id:doc}})
    expect(container.querySelector('[aria-label="Form nota aksesori"] h2')?.textContent).toContain('ACC-001 · POSTED')
    expect(container.querySelector('[aria-label="Riwayat nota aksesori"]')?.textContent).not.toContain('ACC-001')
    expect(container.querySelector('[aria-label="Konfirmasi nota"]')).toBeNull();expect(writes()).toHaveLength(0);expect(s.effects).toBe(0)
  })
  it('does not substitute another document when the exact owning source is missing from its reader',async()=>{
    const s=server();s.document=documentFixture();Object.assign((auth.current as typeof recoveryIdentity).identity.profile,{authUserId:id})
    const ordinary=client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async(name,args)=>{
      if(name==='erp_cp7_resolve_transaction_source_v1')return{data:{contract_version:'cp7.transaction-source.v1',actor_scope_id:id,source:args.p_source,status:'AVAILABLE',business_DML:false,read_at:'2026-10-03T00:00:00Z',document:{domain:'ACCESSORY_ISSUE',route:'contractor-issue',id:doc,number:'ACC-001',status:'DRAFT',revision:'1',focus:null}},error:null}
      const r=await ordinary(name,args);return name==='erp_get_accessory_issue_workspace_v1'&&args.p_filters.id?{...r,data:{...r.data,document:{...r.data.document,id}}}:r
    })
    await act(async()=>root.render(<TransactionSourceProvider scope="accessory-source" onNavigate={()=>{}}><TransactionSourceLink sourceType="CONTRACTOR_MATERIAL_ISSUE_ITEM" sourceId={lineId}/><ConnectedAccessoryIssuePage/></TransactionSourceProvider>));await flush();await click('Buka transaksi asal')
    expect(container.textContent).toContain('Identitas nota tidak cocok.')
    expect(container.querySelector('[aria-label="Form nota aksesori"] h2')?.textContent).toContain('Status belum dipastikan')
    expect(button('Simpan draft').disabled).toBe(true);expect(writes()).toHaveLength(0)
  })
  it('keeps unsent quantities and the selected note unchanged while ordering its history page',async()=>{
    const s=server();s.document={...documentFixture(),number:'ACC-10'}
    const ordinary=client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async(name,args)=>{const r=await ordinary(name,args);return name==='erp_get_accessory_issue_workspace_v1'?{...r,data:{...r.data,history_count:3,history:['ACC-10','ACC-2','ACC-1'].map((number,i)=>({...r.data.history[0],number,id:i?`99999999-9999-4999-8999-${String(i).padStart(12,'0')}`:doc}))}}:r})
    await mount();await click('Buka ACC-10');await change('Jumlah PCS 1','9');const calls=client.rpc.mock.calls.length
    await change('Urutkan halaman nota aksesori','LABEL_ASC')
    expect([...container.querySelectorAll('[aria-label="Riwayat nota aksesori"] tbody tr td:first-child')].map(row=>row.textContent)).toEqual(['ACC-1','ACC-2','ACC-10'])
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah PCS 1"]')!.value).toBe('9')
    expect(container.querySelector('[aria-label="Form nota aksesori"] h2')?.textContent).toContain('ACC-10')
    expect(client.rpc.mock.calls).toHaveLength(calls);expect(writes()).toHaveLength(0)
  })
  it('browses through the unchanged capped Native history reader and keeps unsent form edits',async()=>{
    server();await mount();await prepare();await change('Cari nota aksesori','ACC lama');await change('Status halaman nota aksesori','POSTED');await change('Urutkan halaman nota aksesori','LABEL_DESC')
    await click('Browse semua')
    const request=client.rpc.mock.calls.filter(([name])=>name==='erp_get_accessory_issue_workspace_v1').at(-1)![1].p_filters
    expect(request.query).toBe('');expect(request.id).toBeNull();expect(request).not.toHaveProperty('limit');expect(request).not.toHaveProperty('status')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah PCS 1"]')!.value).toBe('7')
    expect(container.querySelector<HTMLSelectElement>('[aria-label="Status halaman nota aksesori"]')!.value).toBe('ALL')
    expect(writes()).toHaveLength(0)
  })
  it('retires old totals and history on a failed refresh while preserving unsent quantity and price',async()=>{
    server();await mount();await prepare();expect(container.textContent).toContain('Rp 22,75')
    client.rpc.mockImplementation(async()=>({data:null,error:{code:'08006',message:'Read unavailable'}}))
    await click('Muat ulang')
    expect(container.textContent).not.toContain('Rp 22,75');expect(container.textContent).toContain('Total tagihan: —')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah PCS 1"]')!.value).toBe('7')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Harga per PCS 1"]')!.value).toBe('3,25')
    expect(button('Simpan draft').disabled).toBe(true);expect(writes()).toHaveLength(0)
  })
  it('keeps preparation inert and posts the latest edited quantity and exact manual price',async()=>{
    server();await mount();await prepare();expect(writes()).toHaveLength(0)
    expect(container.textContent).toContain('Rp 22,75');await click('Simpan draft')
    expect(writes()[0][1].p_action).toBe('SAVE_DRAFT');await change('Jumlah PCS 1','8');await click('Periksa pengesahan');expect(writes()).toHaveLength(1)
    await click('Sahkan nota');const p=writes()[1][1].p_payload
    expect(p.id).toBe(doc);expect(p.expected_version).toBe('3');expect(p.items).toEqual([{material_id:id,qty:'8',mode:'MANUAL',manual_price:'3.25'}]);expect(p.physical_at).toBe(at+'+07:00')
    expect(container.textContent).toContain('POSTED');expect(container.querySelector('[aria-label="Jumlah PCS 1"]')).toBeNull()
  })
  it('clears review when quantity changes and refuses fractional pcs without clamping',async()=>{
    server();await mount();await prepare();await click('Periksa pengesahan');await change('Jumlah PCS 1','7.5')
    expect(container.querySelector('[aria-label="Konfirmasi nota"]')).toBeNull();expect(button('Simpan draft').disabled).toBe(true)
    expect((container.querySelector('[aria-label="Jumlah PCS 1"]') as HTMLInputElement).value).toBe('7.5');expect(writes()).toHaveLength(0)
  })
  it('uses master pricing only when exact and does not convert seven pcs into a rounded package fraction',async()=>{
    server();await mount();await prepare();await change('Dasar harga 1','MASTER');expect(button('Simpan draft').disabled).toBe(true)
    await change('Jumlah PCS 1','12');expect(container.textContent).toContain('Rp 36,00');await click('Simpan draft')
    expect(writes()[0][1].p_payload.items).toEqual([{material_id:id,qty:'12',mode:'MASTER',price_version_id:lineId,factor:'12.000000'}])
  })
  it('does not require a nonzero manual price and treats empty price as incomplete',async()=>{
    server();await mount();await prepare();await change('Harga per PCS 1','');expect(button('Simpan draft').disabled).toBe(true)
    await change('Harga per PCS 1','0');expect(button('Simpan draft').disabled).toBe(false);await click('Simpan draft');expect(writes()[0][1].p_payload.items[0].manual_price).toBe('0')
  })
  it('requires a fresh quote after mandor, location or physical time changes',async()=>{
    server();await mount();await prepare();await change('Waktu ambil aksesori','2026-09-21T10:15:00')
    expect(button('Simpan draft').disabled).toBe(true);await click('Perbarui harga dan stok');expect(button('Simpan draft').disabled).toBe(false)
    await click('Simpan draft');expect(writes()[0][1].p_payload.physical_at).toBe('2026-09-21T10:15:00+07:00')
  })
  it('allows an overstock draft, blocks its posting and copies the visible balance explicitly',async()=>{
    const s=server();s.stock='7.000000';await mount();await prepare();await change('Jumlah PCS 1','8')
    expect(button('Simpan draft').disabled).toBe(false);expect(button('Periksa pengesahan').disabled).toBe(true)
    await click('Ambil sisa');expect((container.querySelector('[aria-label="Jumlah PCS 1"]') as HTMLInputElement).value).toBe('7');expect(writes()).toHaveLength(0)
  })
  it.each(['SAVE_DRAFT','POST'])('recovers a lost %s reply with the identical request after remount',async action=>{
    const s=server();await mount();await prepare();s.lose=true
    if(action==='POST'){await click('Periksa pengesahan');await click('Sahkan nota')}else await click('Simpan draft')
    const original=structuredClone(writes()[0][1]);expect(readProductionRecovery('disposable:actor-1').pending.ACCESSORY_ISSUE?.id).toBe(original.p_client_request_id)
    await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile transaksi')
    expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.ACCESSORY_ISSUE).toBeUndefined()
  })
  it('requires reason for reversal and keeps bigint versions exact',async()=>{
    const s=server();s.document={...documentFixture(),status:'POSTED',row_version:'9007199254740993'};await mount();await click('Buka ACC-001')
    expect(button('Periksa pembatalan').disabled).toBe(true);await change('Alasan pembatalan nota','Salah pengambilan');await click('Periksa pembatalan');await click('Sahkan pembatalan nota')
    expect(writes()[0][1].p_payload).toEqual({id:doc,expected_version:'9007199254740993',reason:'Salah pengambilan'})
  })
  it('locks a posted source that is already linked to payroll',async()=>{
    const s=server();s.document={...documentFixture(),status:'POSTED',payroll_locked:true};await mount();await click('Buka ACC-001')
    expect(button('Periksa pembatalan').disabled).toBe(true);expect(container.textContent).toContain('payroll aktif');expect(writes()).toHaveLength(0)
  })
  it('keeps form edits and the original draft version through refresh',async()=>{
    const s=server();s.document=documentFixture();await mount();await click('Buka ACC-001');await change('Jumlah PCS 1','9');s.document.row_version='2'
    await click('Muat ulang');await click('Simpan draft');expect(writes()[0][1].p_payload.expected_version).toBe('1');expect(writes()[0][1].p_payload.items[0].qty).toBe('9')
  })
  it('keeps uncertainty on malformed mutation receipts and does not issue a fresh write',async()=>{
    const s=server();s.badReceipt=true;await mount();await prepare();await click('Simpan draft')
    expect(readProductionRecovery('disposable:actor-1').pending.ACCESSORY_ISSUE).toBeDefined();expect(button('Simpan draft').disabled).toBe(true)
  })
  it('shares recovery exclusion with other writing domains',async()=>{
    server();const e={action:'REGISTER',payload:{material_id:id},expectedVersion:null,id:doc,createdAt:new Date().toISOString()}
    persistProductionEnvelope('disposable:actor-1','POCKET_FABRIC',{...e,fingerprint:JSON.stringify({action:e.action,payload:e.payload,expectedVersion:null})})
    await mount();expect(button('Nota baru').disabled).toBe(true);expect(writes()).toHaveLength(0)
  })
  it('denies reads without permission and preserves view-only access without write buttons',async()=>{
    server();const a=auth.current as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.contractor_accessory.view');await mount();expect(client.rpc).not.toHaveBeenCalled()
    a.identity.permissions=['finance.contractor_accessory.view'];await act(async()=>root.render(<ConnectedAccessoryIssuePage/>));await flush()
    expect(button('Nota baru').disabled).toBe(true);expect([...container.querySelectorAll('button')].some(b=>b.textContent==='Simpan draft')).toBe(false)
  })
  it('refuses malformed stock and inconsistent posted totals without simulated fallback',async()=>{
    const s=server();s.invalid=true;await mount();expect(container.textContent).toContain('Stok aksesori tidak valid');expect(writes()).toHaveLength(0)
    s.invalid=false;s.document=documentFixture();await click('Muat ulang');const call=client.rpc.mock.calls.find(([n])=>n==='erp_get_accessory_issue_workspace_v1')!
    const valid=(await client.rpc('erp_get_accessory_issue_workspace_v1',{...call[1],p_filters:{id:doc}})).data
    expect(parseAccessoryWorkspace(valid).document?.total).toBe('22.75');expect(()=>parseAccessoryWorkspace({...valid,document:{...valid.document,total:'22.76'}})).toThrow('Total nota')
  })
})
