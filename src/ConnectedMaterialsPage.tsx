import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatReceiptDecimal as numberText, receiptDecimal } from './procurementContract'
import { materialObject, parseMaterials, parseMaterialLedger, parseMaterialTransfers, parseMaterialLocations, parseMaterialOutcome, type MaterialsWorkspace, type MaterialBalance, type MaterialLedger, type MaterialTransfers, type MaterialLocation, type MaterialPage } from './materialContract'
import type { Json } from './types/database.preconnect'
import './procurement-connected.css'
import './materials-connected.css'

const statusLabel = { DRAFT: 'Draft', POSTED: 'Sudah dipindahkan', REVERSED: 'Dibatalkan' }
const availabilityLabel = { ON_HAND: 'Tersedia', EMPTY: 'Habis', REVIEW_REQUIRED: 'Perlu diperiksa', MATERIAL_INACTIVE: 'Bahan nonaktif', LOCATION_INACTIVE: 'Gudang nonaktif', SPECIAL_ZONE: 'Zona khusus', LOCATION_REVIEW: 'Periksa lokasi' }
type Client = ReturnType<typeof getUatSupabaseClient>
type TransferForm = { source: MaterialBalance; destination: MaterialLocation | null; qty: string; number: string; at: string; reason: string }
type SelectedRoll = { material_id: string; roll_id: string; location_id: string; roll_number: string }

function Destination({ client, value, disabled, onChange }: { client: Client; value: MaterialLocation | null; disabled: boolean; onChange: (v: MaterialLocation) => void }) {
  const [search,setSearch] = useState(''),[query,setQuery] = useState({q:'',offset:0}),[data,setData] = useState<MaterialPage<MaterialLocation> | null>(null),[error,setError] = useState('')
  useEffect(()=>{let current=true;setData(null);setError('');void(async()=>{
    try { const r=await client.rpc('erp_cp7_get_material_locations_v1',{p_q:query.q,p_offset:query.offset,p_limit:25});if(!current)return;if(r.error)throw r.error;const p=parseMaterialLocations(r.data);if(p.offset!==query.offset)throw Error('Halaman gudang tidak cocok.');setData(p) }
    catch(e){if(current)setError(normalizeClientError(e).message)}
  })();return()=>{current=false}},[client,query])
  return <div className="cproc-picker"><label>Gudang tujuan<select aria-label="Gudang tujuan transfer" disabled={disabled||!data} value={value?.id??''} onChange={e=>{const v=data?.rows.find(x=>x.id===e.target.value);if(v)onChange(v)}}><option value="">Pilih gudang tujuan</option>{value&&!data?.rows.some(x=>x.id===value.id)?<option value={value.id}>{value.name}</option>:null}{data?.rows.map(x=><option key={x.id} value={x.id}>{x.code} · {x.name}</option>)}</select></label>
    <div className="cproc-inline"><input aria-label="Cari gudang tujuan" value={search} maxLength={120} disabled={disabled} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();setQuery({q:search.trim(),offset:0})}}}/><button type="button" disabled={disabled} onClick={()=>setQuery({q:search.trim(),offset:0})}>Cari</button><button type="button" aria-label="Gudang sebelumnya" disabled={disabled||!data||!query.offset} onClick={()=>setQuery(x=>({...x,offset:Math.max(0,x.offset-25)}))}>‹</button><button type="button" aria-label="Gudang berikutnya" disabled={disabled||data?.next_offset==null} onClick={()=>setQuery(x=>({...x,offset:data?.next_offset??x.offset}))}>›</button></div>
    {error?<span role="alert">{error}</span>:data?<small>{data.rows.length} pilihan · total {data.total}</small>:null}</div>
}

export default function ConnectedMaterialsPage() {
  const { runtime,identity }=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')return <section className="panel"><h1>Bahan & roll</h1><p>Masuk ke ERP untuk melihat stok bahan.</p></section>
  if(!identity.permissions.includes('warehouse.material.view'))return <section className="panel" role="alert">Hak melihat bahan belum diberikan.</section>
  return <MaterialsWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function MaterialsWorkspace() {
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi gudang belum siap.')
  const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),finance=identity.permissions.includes('finance.hpp.view')
  const mutation=useProductionMutation('MATERIALS'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
  const [stock,setStock]=useState<MaterialsWorkspace|null>(null),[transfers,setTransfers]=useState<MaterialTransfers|null>(null),[ledger,setLedger]=useState<MaterialLedger|null>(null)
  const [loading,setLoading]=useState(false),[error,setError]=useState(''),[tab,setTab]=useState<'stock'|'transfer'>('stock')
  const [search,setSearch]=useState(''),[zero,setZero]=useState(false),[transferSearch,setTransferSearch]=useState(''),[form,setForm]=useState<TransferForm|null>(null)
  const [reason,setReason]=useState('Barang sudah diperiksa sebelum dipindahkan'),[confirmReverse,setConfirmReverse]=useState(false)
  const requested=useRef({q:'',zero:false,stockOffset:0,transferQ:'',transferOffset:0,transferId:null as string|null,roll:null as SelectedRoll|null,ledgerOffset:0}),sequence=useRef(0)
  const load=useCallback(async()=>{
    const request={...requested.current},s=++sequence.current,ticket=beginRead();setLoading(true);setError('')
    try {
      const [sr,tr,lr]=await Promise.all([
        client.rpc('erp_cp7_get_materials_v1',{p_query:{q:request.q,show_zero:request.zero,offset:request.stockOffset,limit:25}}),
        client.rpc('erp_cp7_get_material_transfers_v1',{p_query:{q:request.transferQ,offset:request.transferOffset,limit:25,transfer_id:request.transferId}}),
        request.roll?client.rpc('erp_cp7_get_material_ledger_v1',{p_material:request.roll.material_id,p_roll:request.roll.roll_id,p_location:request.roll.location_id,p_offset:request.ledgerOffset,p_limit:25}):Promise.resolve(null),
      ])
      if(!isReadCurrent(ticket)||s!==sequence.current)return false
      for(const r of [sr,tr,lr])if(r?.error)throw r.error
      const a=parseMaterials(sr.data,finance),b=parseMaterialTransfers(tr.data),c=lr?parseMaterialLedger(lr.data,finance):null
      if(a.page.offset!==request.stockOffset||b.page.offset!==request.transferOffset||(b.detail?.id??null)!==request.transferId||c&&(c.material_id!==request.roll?.material_id||c.roll_id!==request.roll.roll_id||c.location_id!==request.roll.location_id||c.page.offset!==request.ledgerOffset))throw Error('Hasil tidak cocok dengan dokumen yang dipilih.')
      setStock(a);setTransfers(b);setLedger(c);return finishRead(ticket)
    } catch(e){if(isReadCurrent(ticket)){setStock(null);setTransfers(null);setLedger(null);setError(normalizeClientError(e).message)}return false}
    finally{if(s===sequence.current)setLoading(false)}
  },[client,finance,beginRead,finishRead,isReadCurrent])
  useEffect(()=>{void load()},[load])
  const handlers:ProductionMutationHandlers={
    send:envelope=>{const p=materialObject(envelope.payload);return client.rpc('erp_cp7_save_materials_v1',{p_action:envelope.action,p_payload:p.document as Json,p_request:envelope.id,p_expected:p.expected_version as string|null})},
    validate:(v,e)=>{parseMaterialOutcome(v,e.id,e.action,materialObject(e.payload).document as Json)},
    retire:(v,e)=>{const r=parseMaterialOutcome(v,e.id,e.action,materialObject(e.payload).document as Json);requested.current.transferId=r.transfer_id;setForm(null);setConfirmReverse(false);setTab('transfer')},
    reload:load,
  }
  const locked=mutation.writerLocked||loading,current=transfers?.detail,qty=form?receiptDecimal(form.qty,true):null,at=form?cp6WibPhysicalTimeToIso(form.at):null
  const payload:Json|null=form&&qty&&at&&form.destination&&form.destination.id!==form.source.location_id&&form.number.trim()&&form.reason.trim()?{
    transfer_number:form.number.trim(),from_location_id:form.source.location_id,to_location_id:form.destination.id,physical_at:at,change_reason:form.reason.trim(),
    items:[{material_id:form.source.material_id,roll_id:form.source.roll_id,qty}],
  }:null
  const write=(action:string,document:Json,version:string|null)=>run(action,{document,expected_version:version},null,handlers)
  const openRoll=(r:MaterialBalance)=>{if(!r.roll_id)return;requested.current.roll={material_id:r.material_id,roll_id:r.roll_id,location_id:r.location_id,roll_number:r.roll_number??'Roll'};requested.current.ledgerOffset=0;void load()}
  return <section className="cproc cmat"><header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · BAHAN & ROLL</div><h1>Bahan & roll</h1><p>Lihat stok kain per gudang, telusuri mutasinya, dan catat perpindahan barang.</p></div><button disabled={mutation.busy||loading} onClick={()=>void load()}>Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={{...mutation,notice:mutation.notice?'Data stok dan transfer sudah diperbarui.':'',...(mutation.pending&&!mutation.corruptedEnvelope?{error:'Hasil pencatatan belum diketahui. Periksa hasil transaksi dengan data kiriman yang masih tersimpan.',blockReason:''}:{})}} onReconcile={()=>reconcile(handlers)} className="panel"/>
    {error?<p className="panel" role="alert">{error}</p>:null}
    <nav className="cmat-tabs" aria-label="Tampilan bahan"><button aria-pressed={tab==='stock'} onClick={()=>setTab('stock')}>Stok per gudang</button><button aria-pressed={tab==='transfer'} onClick={()=>setTab('transfer')}>Transfer gudang</button></nav>
    {loading?<p role="status">Memuat data gudang…</p>:null}
    {tab==='stock'?<>
      <form className="panel cproc-search" onSubmit={e=>{e.preventDefault();requested.current.q=search.trim();requested.current.zero=zero;requested.current.stockOffset=0;setForm(null);void load()}}><label>Cari bahan, roll, atau gudang<input aria-label="Cari stok bahan" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)}/></label><label className="cmat-check"><input type="checkbox" checked={zero} onChange={e=>setZero(e.target.checked)}/>Tampilkan roll habis</label><button disabled={mutation.busy||loading}>Cari stok</button></form>
      <div className="cmat-totals">{stock?.totals_by_unit.map(x=><article className="panel" key={x.unit_code}><span>Total sesuai pencarian · {x.unit_code}</span><strong>{numberText(x.qty)}</strong>{x.quality==='CONFLICT'?<small>Saldo perlu diperiksa</small>:null}</article>)}</div>
      <div className="cproc-layout"><section className="panel"><h2>Roll di gudang</h2><p>Draft penerimaan belum masuk saldo. Satuan berbeda ditampilkan terpisah.</p>{stock?.page.rows.length===0?<p>Tidak ada stok sesuai pencarian.</p>:null}
        {stock?.page.rows.map(r=><article className="cmat-roll" key={`${r.material_id}:${r.roll_id}:${r.location_id}`}><div><strong>{r.roll_number??'Roll belum diketahui'}</strong><small>{r.material_name} · {r.material_sku}</small><small>{r.location_name}</small></div><div className="cmat-quantity"><strong>{numberText(r.qty)} {r.unit_code}</strong><small>{availabilityLabel[r.availability]}</small></div>
          {r.valuation?<small className="cmat-value">{r.valuation.state==='KNOWN'?<>Nilai stok Rp{numberText(r.valuation.value!)} · rata-rata Rp{numberText(r.valuation.unit_cost!)} / {r.unit_code}</>:'Nilai stok belum diketahui'}</small>:null}
          <div className="cproc-inline"><button disabled={mutation.busy||loading||!r.roll_id} onClick={()=>openRoll(r)}>Mutasi {r.roll_number??'roll'}</button><button disabled={locked||!stock.capabilities.transfer||r.availability!=='ON_HAND'||!r.roll_id} onClick={()=>setForm({source:r,destination:null,qty:'',number:'',at:cp6WibDateTimeInput(),reason:'Perpindahan barang antar gudang'})}>Pindahkan {r.roll_number??'roll'}</button></div></article>)}
        {stock?<div className="cproc-pagination"><span>{stock.page.rows.length} baris · total {stock.page.total}</span><button disabled={loading||mutation.busy||!stock.page.offset} onClick={()=>{requested.current.stockOffset=Math.max(0,stock.page.offset-25);void load()}}>Stok sebelumnya</button><button disabled={loading||mutation.busy||stock.page.next_offset===null} onClick={()=>{requested.current.stockOffset=stock.page.next_offset??0;void load()}}>Stok berikutnya</button></div>:null}
      </section><aside className="panel cmat-ledger"><h2>Mutasi {requested.current.roll?.roll_number??'roll'}</h2>{ledger?<><p>Saldo berjalan mengikuti waktu fisik. Biaya mengikuti perhitungan terkini yang sudah tercatat.</p>{ledger.page.rows.length===0?<p>Belum ada mutasi yang diposting.</p>:null}{ledger.page.rows.map(m=><article className="cproc-item" key={m.movement_id}><div className="cproc-heading"><strong>{numberText(m.qty_signed)}</strong><span>Saldo {numberText(m.running_qty)}</span></div><small>{formatCp6WibDateTime(m.physical_at)}</small><small>{m.movement_type.replaceAll('_',' ')}</small>{m.note?<p>{m.note}</p>:null}{m.reversal_of_id?<small>Pembalik transaksi sebelumnya</small>:null}{m.valuation?<small>{m.valuation.state==='KNOWN'?`Nilai mutasi Rp${numberText(m.valuation.movement_value!)}`:'Nilai mutasi belum diketahui'}</small>:null}<details><summary>Referensi pencatatan</summary><small>{m.source_type} · {m.source_id??'Tanpa dokumen'}</small><small>Dicatat {formatCp6WibDateTime(m.recorded_at)}</small></details></article>)}<div className="cproc-pagination"><button disabled={loading||mutation.busy||!ledger.page.offset} onClick={()=>{requested.current.ledgerOffset=Math.max(0,ledger.page.offset-25);void load()}}>Mutasi sebelumnya</button><button disabled={loading||mutation.busy||ledger.page.next_offset===null} onClick={()=>{requested.current.ledgerOffset=ledger.page.next_offset??0;void load()}}>Mutasi berikutnya</button></div></>:<p>Pilih roll untuk melihat asal dan perpindahan stoknya.</p>}</aside></div>
      {form?<form className="panel" onSubmit={e=>{e.preventDefault();if(payload&&!locked&&stock?.capabilities.transfer)void write('SAVE_TRANSFER',payload,null)}}><div className="cproc-heading"><div><div className="eyebrow">TRANSFER GUDANG</div><h2>Pindahkan {form.source.roll_number}</h2><p>{form.source.material_name} · dari {form.source.location_name}. Draft belum memindahkan stok.</p></div><button type="button" disabled={mutation.busy} onClick={()=>setForm(null)}>Tutup formulir</button></div><fieldset disabled={locked}><div className="cproc-grid"><label>Nomor transfer<input aria-label="Nomor transfer" required value={form.number} onChange={e=>setForm({...form,number:e.target.value})}/></label><label>Waktu perpindahan · WIB<input aria-label="Waktu transfer WIB" type="datetime-local" required value={form.at} onChange={e=>setForm({...form,at:e.target.value})}/></label><Destination client={client} value={form.destination} disabled={locked} onChange={destination=>setForm(f=>f?{...f,destination}:f)}/><label>Jumlah ({form.source.unit_code})<input aria-label="Jumlah transfer" inputMode="decimal" required value={form.qty} onChange={e=>setForm({...form,qty:e.target.value})}/></label><label>Alasan perpindahan<input aria-label="Alasan transfer" required value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}/></label></div><p>Gudang asal dan tujuan harus berbeda. Jumlah tersedia akan diperiksa kembali saat transfer disahkan.</p><button className="primary-btn" disabled={!payload||!stock?.capabilities.transfer}>Simpan draft transfer</button></fieldset></form>:null}
    </>:<>
      <form className="panel cproc-inline" onSubmit={e=>{e.preventDefault();requested.current.transferQ=transferSearch.trim();requested.current.transferOffset=0;void load()}}><label>Cari nomor transfer<input aria-label="Cari transfer" maxLength={120} value={transferSearch} onChange={e=>setTransferSearch(e.target.value)}/></label><button disabled={loading||mutation.busy}>Cari transfer</button></form>
      <div className="cproc-layout"><section className="panel"><h2>Daftar transfer</h2>{transfers?.page.rows.length===0?<p>Belum ada transfer sesuai pencarian.</p>:null}{transfers?.page.rows.map(t=><button className="cproc-receipt" key={t.id} aria-pressed={t.id===current?.id} disabled={loading||mutation.busy} onClick={()=>{requested.current.transferId=t.id;setConfirmReverse(false);void load()}}><span><strong>{t.number}</strong><small>{t.from_location_name} → {t.to_location_name}</small><small>{formatCp6WibDateTime(t.physical_at)}</small></span><span className={`cproc-status ${t.status.toLowerCase()}`}>{statusLabel[t.status]}</span></button>)}{transfers?<div className="cproc-pagination"><span>Total {transfers.page.total}</span><button disabled={loading||mutation.busy||!transfers.page.offset} onClick={()=>{requested.current.transferOffset=Math.max(0,transfers.page.offset-25);void load()}}>Transfer sebelumnya</button><button disabled={loading||mutation.busy||transfers.page.next_offset===null} onClick={()=>{requested.current.transferOffset=transfers.page.next_offset??0;void load()}}>Transfer berikutnya</button></div>:null}</section>
      <aside className="panel cmat-transfer-detail">{current?<><div className="eyebrow">DOKUMEN TRANSFER</div><h2>{current.number}</h2><span className={`cproc-status ${current.status.toLowerCase()}`}>{statusLabel[current.status]}</span><p>{current.from_location_name} → {current.to_location_name}</p><p>{current.status==='DRAFT'?'Draft belum mengubah stok.':current.status==='POSTED'?'Stok sudah dipindahkan sesuai dokumen.':'Transfer sudah dibatalkan dengan mutasi pembalik.'}</p>{current.items.map(i=><article className="cproc-item" key={i.id}><h3>{i.material_name}</h3><strong>{numberText(i.qty)} {i.unit_code}</strong><small>{i.roll_number??'Tanpa roll'}</small>{i.notes?<p>{i.notes}</p>:null}</article>)}
      {current.status!=='REVERSED'?<div className="cproc-review"><label>Catatan pemeriksaan atau pembatalan<input aria-label="Catatan transfer" value={reason} disabled={locked} onChange={e=>setReason(e.target.value)}/></label>{current.status==='DRAFT'?<button className="primary-btn" disabled={locked||!transfers?.capabilities.transfer||!reason.trim()} onClick={()=>void write('POST_TRANSFER',{transfer_id:current.id,change_reason:reason.trim()},current.row_version)}>Sahkan perpindahan stok</button>:transfers?.capabilities.reverse_transfer?<><label className="cmat-check"><input type="checkbox" checked={confirmReverse} disabled={locked} onChange={e=>setConfirmReverse(e.target.checked)}/>Saya sudah memeriksa alasan pembatalan transfer ini.</label><button disabled={locked||!reason.trim()||!confirmReverse} onClick={()=>void write('REVERSE_TRANSFER',{transfer_id:current.id,change_reason:reason.trim()},current.row_version)}>Batalkan transfer</button><small>Pembatalan memerlukan barang yang masih tersedia di tujuan. Pemakaian lanjutan harus diselesaikan terlebih dahulu.</small></>:null}</div>:null}</>:<><h2>Periksa transfer</h2><p>Pilih dokumen untuk melihat rincian, mengesahkan, atau membatalkan transfer.</p></>}</aside></div>
    </>}
  </section>
}
