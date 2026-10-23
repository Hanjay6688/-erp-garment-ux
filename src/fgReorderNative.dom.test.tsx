// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import FgReorderPanel from './FgReorderPanel'
import SystemRemindersPanel from './SystemRemindersPanel'
import {formatReorderWhole,parseFgReorderManualResult,parseFgReorderWorkspace,reorderChip,reorderFormulaLines,type ReorderQuery} from './fgReorderContract'
import {alertSummary,parseSystemAlerts} from './waContract'
import sql from '../tests/fixtures/reorderCallerSql.json'
import {reorderId,reorderWire,type ReorderWireRow} from '../tests/fixtures/fgReorder'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'

// Outputs captured by the actual caller SQL over synthetic ERP facts. Browser
// transport below is controlled; these tests do not claim Auth/PostgREST.
const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const Q:ReorderQuery={q:'',filter:'ALL',offset:0,limit:25}
const copy=<T,>(v:T):T=>structuredClone(v)
const wire=(rows:unknown[]=copy(sql.initial.page.rows))=>reorderWire(rows as ReorderWireRow[],Q,{contract_version:'cp7.fg-reorder.v2'})
const native=(index=0)=>copy(sql.initial.page.rows[index])
const parse=(rows:unknown[]=copy(sql.initial.page.rows))=>parseFgReorderWorkspace(wire(rows),Q)
const alertWire=(detail:unknown=sql.alert.detail)=>({contract_version:'cp7.system-alerts.v1',read_at:sql.initial.read_at,configured:true,collector:null,analysis:null,
  kinds:[{kind:'FG_AT_REORDER_POINT',last_try_at:null,last_ok_at:null,last_error:null,open_count:1}],rows:[{...sql.alert,detail,id:reorderId(999),episode:1,
    state:'OPEN',opened_at:sql.initial.read_at,refreshed_at:sql.initial.read_at,resolved_at:null,resolution:null,wa:null}]})

describe('OW10 versioned Native reorder wire from actual SQL',()=>{
  it('keeps actual Native profile choices, including selected demand and known zero',()=>{
    const w=parseFgReorderWorkspace(sql.initial,Q)
    expect(w.contractVersion).toBe('cp7.fg-reorder.v2')
    expect(w.page.rows.map(r=>r.point)).toEqual(['2','10','0'])
    expect(w.page.rows[1].dailyMean).toBe('2.0000000000000000')
    expect(reorderFormulaLines(w.page.rows[1],30,'0.95')[0]).toContain('2,00 pcs')
    expect(reorderChip(w.page.rows[2],30).label).toBe('Kebutuhan menurut rumus 0 pcs')
    expect(w.page.rows[0].wipPcs).toBeNull()
  })
  it('retains directed and candidate positions separately, without muting a manual25 alert',()=>{
    const r=parseFgReorderWorkspace(sql.projected,Q).page.rows.find(r=>r.rootId===sql.manual.root_id)!
    expect(r).toMatchObject({point:'25',wipPcs:'4',state:'AT_OR_BELOW',projection:{basePositionPcs:'4',candidatePcs:'3',conditionalPositionPcs:'7',
      targetPcs:'5',productionBasePcs:'1',productionConditionalPcs:'0'}})
    const wrong=copy(sql.projected.page.rows);wrong.find(r=>r.root_id===sql.manual.root_id)!.state='ABOVE'
    expect(()=>parse(wrong)).toThrow('(status)')
  })
  it('refuses mixed versions, numeric v2 PCS, extra fields and missing projected facts',()=>{
    const r=native()
    for(const change of[{free_pcs:90},{point:2},{point:'2e1'},{surprise:true},{contract_version:'cp7.fg-reorder-row.v1'}]){
      expect(()=>parse([{...r,...change}as typeof r])).toThrow('Respons titik pesan ulang tidak cocok')
    }
    const missing=copy(r)as Record<string,unknown>;delete missing.projection
    expect(()=>parse([missing as typeof r])).toThrow('(barang)')
    expect(()=>parseFgReorderWorkspace({...wire([r]),contract_version:'cp7.fg-reorder.v1'},Q)).toThrow('(barang)')
  })
  it('refuses raw WIP credit, candidates muting alerts and a false current position',()=>{
    const r=copy(sql.projected.page.rows[0])
    for(const change of[{raw_WIP_credited:true},{candidate_mutes_alert:true},{base_position_pcs:'5'},{conditional_position_pcs:'8'}]){
      expect(()=>parse([{...r,projection:{...r.projection,...change}}])).toThrow('Respons titik pesan ulang tidak cocok')
    }
  })
  it('keeps a point above JS safe integer exact through comparison and display',()=>{
    const r=native();r.point='10000000000000001';r.formula_point=r.point;r.free_pcs='10000000000000000';r.state='AT_OR_BELOW'
    r.projection.target_pcs=r.point
    const p=parse([r]).page.rows[0]
    expect(p.point).toBe('10000000000000001')
    expect(formatReorderWhole(p.point!)).toBe('10.000.000.000.000.001')
    expect(()=>parse([{...r,state:'ABOVE'}])).toThrow('(status)')
  })
  it('accepts actual save, clear and replay envelopes while retaining revision checks',()=>{
    const payload={root_id:sql.manual.root_id,expected_revision:0,reorder_point_pcs:25,reason:'CONTROLLED_MANUAL'}
    expect(parseFgReorderManualResult(sql.manual,payload).evaluation?.point).toBe('25')
    expect(parseFgReorderManualResult(sql.cleared,{...payload,expected_revision:1,reorder_point_pcs:null}).evaluation?.point).toBe('2')
    const {evaluation:_,...replay}=sql.manual
    expect(parseFgReorderManualResult({...replay,replay:true},payload).evaluation).toBeNull()
    expect(()=>parseFgReorderManualResult(sql.manual,{...payload,expected_revision:1})).toThrow('(hasil angka manual)')
  })
  it('keeps the stale manual number as reference only after a physical successor',()=>{
    const r=parseFgReorderWorkspace(sql.successor,Q).page.rows.find(r=>r.productId.endsWith('111111111111')&&r.sku==='SUCCESSOR-L')!
    expect(r).toMatchObject({point:null,manualPoint:null,state:'NO_POINT',reason:'MANUAL_POINT_VERSION_CHANGED',projection:{manualState:'STALE_IDENTITY',manualReference:{point:'25'}}})
  })
  it('renders the actual alert SQL line and rejects an inconsistent candidate or raw credit flag',()=>{
    const a=parseSystemAlerts(alertWire(),{owner:false}).rows[0]
    expect(alertSummary(a)).toBe(sql.alertLine)
    expect(alertSummary(a)).toContain('perkiraan tepat waktu 4 pcs, titik 25 pcs')
    const detail=copy(sql.alert.detail)
    expect(()=>parseSystemAlerts(alertWire({...detail,projection:{...detail.projection,candidate_mutes_alert:true}}),{owner:false})).toThrow('(rincian barang jadi)')
    expect(()=>parseSystemAlerts(alertWire({...detail,position_pcs:'7'}),{owner:false})).toThrow('(rincian barang jadi)')
  })
  it('preserves large exact alert facts by shortening only the Unicode product label',()=>{
    const detail={...copy(sql.alert.detail),product_name:'🧵'.repeat(300),reorder_point_pcs:'10000000000000001'}
    const text=alertSummary(parseSystemAlerts(alertWire(detail),{owner:false}).rows[0])
    expect(Array.from(text)).toHaveLength(256)
    expect(text).toContain('…: bebas 0 pcs, perkiraan tepat waktu 4 pcs, titik 10000000000000001 pcs')
  })
})

let container:HTMLDivElement,root:Root
const settle=async()=>{await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})}
beforeEach(()=>{
  (globalThis as unknown as {IS_REACT_ACT_ENVIRONMENT:boolean}).IS_REACT_ACT_ENVIRONMENT=true
  auth.current=recoveryIdentity;client.rpc.mockReset();container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
describe('OW10 screens over actual SQL DTOs and controlled transport',()=>{
  it('shows exact profile mean, projected supply, candidate warning and clocks',async()=>{
    client.rpc.mockResolvedValue({data:sql.projected,error:null})
    await act(async()=>root.render(<FgReorderPanel/>));await settle()
    expect(container.querySelector('[role="alert"]')).toBeNull()
    expect(container.textContent).toContain('Perkiraan tepat waktu')
    expect(container.textContent).toContain('Target rencana: 5 pcs. Tambahan produksi dari stok dan suplai terarah: 1 pcs.')
    expect(container.textContent).toContain('Kandidat tambahan: 3 pcs')
    expect(container.textContent).toContain('Kandidat perlu dikonfirmasi')
    expect(container.textContent).toContain('Rata-rata yang dipakai untuk target: 2,00 pcs')
    expect(container.textContent).toContain('Stok diperiksa')
  })
  it('shows stale manual reference and unknown supply without calling it zero',async()=>{
    client.rpc.mockResolvedValue({data:sql.successor,error:null})
    await act(async()=>root.render(<FgReorderPanel/>));await settle()
    const row=container.querySelector('[data-target-key="'+sql.successor.page.rows.find(r=>r.sku==='SUCCESSOR-L')!.target_key+'"]')!
    expect(row.textContent).toContain('Referensi angka manual sebelumnya: 25 pcs')
    expect(row.querySelector('[data-cfr="point"]')?.textContent).toBe('belum ada')
    expect(row.querySelector('[data-cfr="wip"]')?.textContent).toBe('belum bisa dihitung')
  })
  it('retries a lost v2 manual-save response with the same request UUID and parses its replay',async()=>{
    let attempts=0
    const {evaluation:_,...replay}=sql.manual
    client.rpc.mockImplementation(async(name:string)=>{
      if(name==='erp_cp7_get_fg_reorder_v1')return{data:attempts?sql.projected:sql.initial,error:null}
      if(name==='erp_cp7_save_fg_reorder_manual_v1'){
        if(++attempts===1)throw new TypeError('Failed to fetch')
        return{data:{...replay,replay:true},error:null}
      }
      throw Error('Unexpected RPC '+name)
    })
    await act(async()=>root.render(<FgReorderPanel/>));await settle()
    const row=()=>container.querySelector<HTMLElement>('[data-target-key="'+sql.initial.page.rows[0].target_key+'"]')!
    const click=async(text:string)=>{await act(async()=>{[...row().querySelectorAll('button')].find(b=>b.textContent===text)!.click()});await settle()}
    const type=async(label:string,value:string)=>{const input=row().querySelector<HTMLInputElement>('[aria-label="'+label+'"]')!
      await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,value)
        input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}))})}
    await click('Atur angka manual');await type('Titik pesan ulang manual (pcs)','25');await type('Alasan angka manual','CONTROLLED_MANUAL')
    await click('Simpan angka manual')
    expect(container.textContent).toContain('Jawaban server tidak sampai')
    await click('Simpan angka manual')
    const sent=client.rpc.mock.calls.filter(c=>c[0]==='erp_cp7_save_fg_reorder_manual_v1')
    expect(sent).toHaveLength(2);expect(sent[1][1]).toEqual(sent[0][1])
    expect(container.textContent).toContain('Permintaan ini ternyata sudah tersimpan sebelumnya')
  })
  it('hides all old figures when a v2 response contains an unsupported field',async()=>{
    client.rpc.mockResolvedValue({data:{...sql.initial,page:{...sql.initial.page,rows:[{...native(),raw_wip_pcs:'100'}]}},error:null})
    await act(async()=>root.render(<FgReorderPanel/>));await settle()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Respons titik pesan ulang tidak cocok')
    expect(container.querySelector('article.cfr-row')).toBeNull()
  })
  it('shows the same alert facts, analysis time and conditional candidate warning',async()=>{
    client.rpc.mockResolvedValue({data:alertWire(),error:null})
    await act(async()=>root.render(<SystemRemindersPanel owner={false}/>));await settle()
    expect(container.querySelector('[role="alert"]')).toBeNull()
    expect(container.textContent).toContain(sql.alertLine)
    expect(container.textContent).toContain('Perkiraan barang baik dari analisis')
    expect(container.textContent).toContain('Kandidat tambahan 3 pcs perlu dikonfirmasi')
  })
})
