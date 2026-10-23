// @vitest-environment jsdom
import{act}from'react'
import{createRoot,type Root}from'react-dom/client'
import{beforeEach,afterEach,it,expect,vi}from'vitest'
import NativeDemandHistoryPanel from'./NativeDemandHistoryPanel'
import{recoveryIdentity}from'../tests/fixtures/productionRecovery'
import{demandWire}from'../tests/fixtures/nativeDemandHistory'
import{scheduleJobWire,stagedWorkspaceWire}from'../tests/fixtures/nativeProductionPlanning'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
// Existing manual-viewer controls remain read-on-click. Owner's new automatic
// entry is exercised separately through the real parent in its integration test.
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{role:'STAFF'});a.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container);vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-09-30T12:00:00Z'))})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.useRealTimers();vi.restoreAllMocks()})
async function render(){await act(async()=>root.render(<NativeDemandHistoryPanel/>))}
function button(name:string){return [...container.querySelectorAll('button')].find(b=>b.textContent===name)!}
async function click(name:string){await act(async()=>button(name).click())}
const captureReply=(_name:string,args:{p_request:string})=>Promise.resolve({data:demandWire(args.p_request),error:null})
it('opens a manual viewer without any read or business write, then displays one native run',async()=>{client.rpc.mockImplementation(captureReply);await render();await click('Data permintaan & stok');expect(client.rpc).not.toHaveBeenCalled();await click('Muat data permintaan');expect(container.textContent).toContain('SKU-NATIVE-WIRE');expect(container.textContent).toContain('76 PCS');expect(container.textContent).toContain('1 hari belum diketahui');expect(client.rpc).toHaveBeenCalledTimes(1);expect(client.rpc.mock.calls[0][0]).toBe('erp_cp7_capture_demand_history_v1')})
it('replays the identical saved query and UUID after committed reply loss and remount',async()=>{client.rpc.mockResolvedValueOnce({data:null,error:Error('reply lost')});await render();await click('Data permintaan & stok');await click('Muat data permintaan');const original=structuredClone(client.rpc.mock.calls[0]);expect(container.querySelector('table')).toBeNull();await act(async()=>root.unmount());root=createRoot(container);client.rpc.mockImplementation(captureReply);await render();expect((button('Muat data permintaan')as HTMLButtonElement).disabled).toBe(true);await click('Ulangi permintaan yang sama');expect(client.rpc.mock.calls[1]).toEqual(original);expect(container.textContent).toContain('76 PCS');expect(localStorage.length).toBe(0)})
it('drops the held source reply when the panel closes',async()=>{let release:(x:unknown)=>void=()=>{};client.rpc.mockImplementation(()=>new Promise(r=>release=r));await render();await click('Data permintaan & stok');await click('Muat data permintaan');const args=client.rpc.mock.calls[0][1];await click('Tutup data permintaan');await act(async()=>release({data:demandWire(args.p_request),error:null}));expect(container.querySelector('table')).toBeNull();await click('Data permintaan & stok');expect(button('Ulangi permintaan yang sama')).toBeTruthy();expect(container.querySelector('table')).toBeNull()})
it('clears old facts on current archive access denial',async()=>{client.rpc.mockImplementation(captureReply);await render();await click('Data permintaan & stok');await click('Muat data permintaan');client.rpc.mockResolvedValueOnce({data:null,error:Error('CP7_ACCESS_DENIED')});await click('Periksa sumber arsip');expect(container.querySelector('table')).toBeNull();expect(container.querySelector('[role=alert]')).toBeTruthy()})
it('does not expose the panel when a required permission is absent',async()=>{const a=structuredClone(recoveryIdentity);a.identity.permissions=['warehouse.stock.view'];state.auth=a;await render();expect(container.textContent).toBe('');expect(client.rpc).not.toHaveBeenCalled()})
it('refuses another request after corrupt recovery without erasing it',async()=>{localStorage.setItem('erp.cp7.native-demand-request.v1:cp6-disposable:actor-1','broken');await render();expect(container.textContent).toContain('Permintaan tersimpan belum bisa dibaca');expect((button('Muat data permintaan')as HTMLButtonElement).disabled).toBe(true);expect(client.rpc).not.toHaveBeenCalled();expect(localStorage.length).toBe(1)})
it('opens the work schedule directly without forcing the old whole-history capture first',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_request:string;p_source_request:string})=>({data:name==='erp_cp7_request_staged_analysis_v1'?scheduleJobWire(args.p_request):name==='erp_cp7_get_staged_production_schedule_v1'?stagedWorkspaceWire(args.p_source_request):null,error:null}))
 await render();await click('Data permintaan & stok');await click('Jadwal & kekurangan seluruh produk');expect(client.rpc).not.toHaveBeenCalled();expect(container.querySelector('[aria-label="Jadwal dan kekurangan produksi"]')).toBeTruthy()
 await click('Ambil stok proses terbaru');expect(client.rpc.mock.calls.map(([name])=>name)).toEqual(['erp_cp7_request_staged_analysis_v1','erp_cp7_get_staged_production_schedule_v1']);expect(container.querySelector('[aria-label="Tempat kerja pilihan"]')).toBeTruthy()
})
it('does not duplicate the direct work entry after a successful demand read',async()=>{
 client.rpc.mockImplementation(captureReply);await render();await click('Data permintaan & stok');await click('Muat data permintaan');expect([...container.querySelectorAll('button')].filter(b=>b.textContent==='Jadwal & kekurangan seluruh produk')).toHaveLength(1)
})
it('keeps direct work entry blocked while a legacy demand result remains uncertain',async()=>{
 client.rpc.mockResolvedValue({data:null,error:Error('reply lost')});await render();await click('Data permintaan & stok');await click('Muat data permintaan');expect(button('Jadwal & kekurangan seluruh produk').disabled).toBe(true);const saved=localStorage.getItem('erp.cp7.native-demand-request.v1:cp6-disposable:actor-1');expect(saved).not.toBeNull();await click('Jadwal & kekurangan seluruh produk');expect(localStorage.getItem('erp.cp7.native-demand-request.v1:cp6-disposable:actor-1')).toBe(saved);expect(client.rpc).toHaveBeenCalledTimes(1)
})
