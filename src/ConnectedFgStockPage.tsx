import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { formatReceiptDecimal as numberText } from './procurementContract'
import { fgPositionKey, parseFgWorkspace, parseFgLedger, type FgPurpose, type FgPosition, type FgWorkspace, type FgLedger } from './fgContract'
import './procurement-connected.css'
import './fg-connected.css'
import NativeDemandHistoryPanel from './NativeDemandHistoryPanel'
import RecordTools,{orderRecordPage,type RecordPageOrder} from './RecordTools'

const permission:Record<FgPurpose,string>={SUMMARY:'warehouse.fg.view',CARD:'warehouse.stock.view',MOVEMENTS:'warehouse.movement.view'}
const labels:Record<string,string>={QC_GOOD:'Hasil QC',SALE_RESERVE:'Dicadangkan untuk penjualan',SALE:'Penjualan',REVERSAL:'Pembatalan',SALES_RETURN:'Retur penjualan',OPENING:'Saldo awal',REWORK_IN:'Hasil rework',TRANSFER_IN:'Masuk gudang',TRANSFER_OUT:'Keluar gudang'}
import TransactionSourceLink from './TransactionSourceNavigation'

export default function ConnectedFgStockPage({purpose='SUMMARY'}:{purpose?:FgPurpose}){
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes(permission[purpose]))return <section className="panel" role="alert">Hak melihat stok barang jadi belum diberikan.</section>
  return <Workspace purpose={purpose} key={`${purpose}:${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({purpose}:{purpose:FgPurpose}){
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi gudang belum siap.')
  const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),finance=identity.permissions.includes('finance.hpp.view')
  const {beginRead,finishRead,isReadCurrent,blockReason,workspaceStale}=useProductionMutation('SKU')
  const [data,setData]=useState<FgWorkspace|null>(null),[ledger,setLedger]=useState<FgLedger|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [search,setSearch]=useState(''),[zero,setZero]=useState(false),[movementSearch,setMovementSearch]=useState('')
  const [stockOrder,setStockOrder]=useState<RecordPageOrder>('SOURCE'),[movementOrder,setMovementOrder]=useState<RecordPageOrder>('SOURCE'),[movementType,setMovementType]=useState('')
  const requested=useRef({q:'',zero:false,offset:0,position:null as FgPosition|null,movementQ:'',movementOffset:0}),sequence=useRef(0),alive=useRef(false)
  const cardPurpose=purpose==='MOVEMENTS'?'MOVEMENTS':'CARD'
  const load=useCallback(async()=>{
    const f={...requested.current},s=++sequence.current,ticket=beginRead();setBusy(true);setData(null);setLedger(null);setError('')
    try{
      const [stock,card]=await Promise.all([
        client.rpc('erp_cp7_get_fg_v1',{p_query:{purpose,q:f.q,show_zero:f.zero,offset:f.offset,limit:25}}),
        f.position?client.rpc('erp_cp7_get_fg_ledger_v2',{p_query:{purpose:cardPurpose,product_id:f.position.product_id,lot_id:f.position.lot_id,location_id:f.position.location_id,quality_grade:f.position.quality_grade,q:f.movementQ,offset:f.movementOffset,limit:25}}):Promise.resolve(null),
      ])
      if(s!==sequence.current||!isReadCurrent(ticket))return
      if(stock.error)throw stock.error;if(card?.error)throw card.error
      const a=parseFgWorkspace(stock.data,finance,purpose),b=card?parseFgLedger(card.data,finance,cardPurpose,true):null
      if(a.page.offset!==f.offset||b&&(b.page.offset!==f.movementOffset||!f.position||fgPositionKey(b.position)!==fgPositionKey(f.position)))throw Error('Pilihan barang atau halaman berubah. Muat ulang.')
      setData(a);setLedger(b);finishRead(ticket)
    }catch(e){if(s===sequence.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message)}
    finally{if(s===sequence.current)setBusy(false)}
  },[client,finance,purpose,cardPurpose,beginRead,finishRead,isReadCurrent])
  useEffect(()=>{alive.current=true;void load();return()=>{alive.current=false;++sequence.current}},[load])
  const retireSource=useCallback(()=>{++sequence.current;setData(null);setLedger(null);setBusy(true);setError('')},[])
  const refreshSource=useCallback(()=>{if(alive.current)void load()},[load])
  const open=(p:FgPosition)=>{requested.current.position=p;requested.current.movementOffset=0;requested.current.movementQ='';setMovementSearch('');setMovementType('');void load()}
  const visible=workspaceStale?null:data,currentLedger=workspaceStale?null:ledger
  const title=purpose==='SUMMARY'?'Barang jadi':purpose==='CARD'?'Kartu stok barang jadi':'Mutasi barang jadi'
  return <><NativeDemandHistoryPanel onSourceReadStart={retireSource} onSourceReadEnd={refreshSource}/><section className="cproc cfg"><header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · BARANG JADI</div><h1>{title}</h1><p>Stok per ukuran, lot, grade, dan gudang. Cadangan penjualan ditampilkan terpisah.</p></div><button disabled={busy} onClick={()=>void load()}>Muat ulang stok</button></header>
    {(error||blockReason)?<p className="panel" role="alert">{error||blockReason}</p>:null}
    <RecordTools title="barang jadi" busy={busy} order={stockOrder} onOrder={setStockOrder} submitLabel="Cari stok" onSubmit={e=>{e.preventDefault();requested.current={q:search.trim(),zero,offset:0,position:null,movementQ:'',movementOffset:0};void load()}} onBrowse={()=>{setSearch('');setZero(false);requested.current={q:'',zero:false,offset:0,position:null,movementQ:'',movementOffset:0};void load()}} search={<label>Cari SKU, ukuran, lot, atau gudang<input aria-label="Cari barang jadi" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)}/></label>} filters={<label className="cfg-check"><input type="checkbox" checked={zero} onChange={e=>setZero(e.target.checked)}/>Sertakan stok habis</label>}/>
    {busy?<p role="status">Memuat stok barang jadi…</p>:null}
    {visible?<><div className="cfg-totals">{([['physical_qty','Fisik di gudang'],['reserved_qty','Dicadangkan'],['available_qty','Tersedia untuk dijual']] as const).map(([key,label])=><article className="panel" key={key}><span>{label}</span><strong>{numberText(visible.totals[key])}<small> PCS</small></strong><small>Seluruh hasil pencarian</small></article>)}</div>
      {visible.totals.quality==='CONFLICT'?<p role="alert">Ada saldo yang perlu diperiksa. Buka rincian sumber sebelum melanjutkan transaksi.</p>:null}
      <div className="cfg-layout"><section className="panel"><div className="cproc-heading"><h2>Posisi stok</h2><small>{formatCp6WibDateTime(visible.read_at)}</small></div>{!visible.page.rows.length?<p>Tidak ada stok yang cocok.</p>:null}
        {orderRecordPage(visible.page.rows,stockOrder,p=>`${p.commercial_sku} ${p.size_code} ${p.lot_number??''} ${p.location_name}`).map(p=><article className="cfg-position" key={fgPositionKey(p)}><header><div><small>{p.brand_name}</small><h3>{p.commercial_sku}</h3><p>{p.product_name}</p></div><span className="cfg-size">{p.size_code}</span></header><p>{p.location_name} · {p.quality_grade.replaceAll('_',' ')} · {p.lot_number??'Lot perlu diperiksa'}</p><dl><div><dt>Fisik</dt><dd>{numberText(p.physical_qty)}</dd></div><div><dt>Cadangan</dt><dd>{numberText(p.reserved_qty)}</dd></div><div><dt>Tersedia</dt><dd>{numberText(p.available_qty)}</dd></div></dl>
          {p.quality==='CONFLICT'?<p role="alert">Saldo atau asal lot perlu diperiksa.</p>:null}
          {p.valuation?<p className="cfg-value">{p.valuation.state==='KNOWN'?`Nilai fisik Rp${numberText(p.valuation.value!)} · HPP Rp${numberText(p.valuation.unit_cost!)} / PCS`:'Biaya belum lengkap · nilai stok belum diketahui'}</p>:null}
          <button disabled={busy||!(purpose==='MOVEMENTS'||visible.capabilities.card)} onClick={()=>open(p)}>Lihat mutasi {p.commercial_sku} · {p.size_code}</button></article>)}
        <div className="cproc-pagination"><span>{visible.page.rows.length} posisi · total {visible.page.total}</span><button disabled={busy||!visible.page.offset} onClick={()=>{requested.current.offset=Math.max(0,visible.page.offset-25);void load()}}>Stok sebelumnya</button><button disabled={busy||visible.page.next_offset===null} onClick={()=>{requested.current.offset=visible.page.next_offset??0;void load()}}>Stok berikutnya</button></div></section>
      <aside className="panel cfg-ledger"><h2>{currentLedger?`${currentLedger.position.commercial_sku} · ${currentLedger.position.size_code}`:'Asal dan mutasi stok'}</h2>{currentLedger?<><p>{currentLedger.position.location_name} · {currentLedger.position.lot_number??'Tanpa lot'}</p><p>Saldo mengikuti seluruh urutan waktu fisik, termasuk transaksi di halaman lain. Identitas SKU pada setiap mutasi mengikuti tanggal transaksinya.</p>
        <RecordTools title="mutasi posisi FG" busy={busy} order={movementOrder} onOrder={setMovementOrder} filterScope="PAGE" submitLabel="Cari mutasi" onSubmit={e=>{e.preventDefault();requested.current.movementQ=movementSearch.trim();requested.current.movementOffset=0;void load()}} onBrowse={()=>{setMovementSearch('');setMovementType('');requested.current.movementQ='';requested.current.movementOffset=0;void load()}} search={<label>Cari catatan atau pelanggan<input aria-label="Cari mutasi barang jadi" value={movementSearch} maxLength={120} onChange={e=>setMovementSearch(e.target.value)}/></label>} filters={<label>Jenis mutasi di halaman ini<select aria-label="Jenis mutasi FG di halaman" value={movementType} onChange={e=>setMovementType(e.target.value)}><option value="">Semua jenis</option>{[...new Set(currentLedger.page.rows.map(m=>m.movement_type))].map(kind=><option key={kind} value={kind}>{labels[kind]??kind.replaceAll('_',' ')}</option>)}</select></label>}/>
        {!currentLedger.page.rows.length?<p>Tidak ada mutasi yang cocok.</p>:null}{orderRecordPage(currentLedger.page.rows.filter(m=>!movementType||m.movement_type===movementType),movementOrder,m=>`${m.commercial_sku_at_transaction} ${m.customer_name??''} ${m.movement_type}`).map(m=><article className="cfg-movement" key={m.id} data-fg-movement-id={m.id}><header><strong>{labels[m.movement_type]??m.movement_type.replaceAll('_',' ')}</strong><time>{formatCp6WibDateTime(m.physical_at)}</time></header><p>{m.commercial_sku_at_transaction}{m.customer_name?` · ${m.customer_name}`:''}</p><dl><div><dt>Perubahan fisik</dt><dd>{numberText(m.physical_delta)}</dd></div><div><dt>Saldo fisik</dt><dd>{numberText(m.physical_balance)}</dd></div><div><dt>Tersedia</dt><dd>{numberText(m.available_balance)}</dd></div></dl><small>Perubahan cadangan {numberText(m.reservation_delta)} · saldo cadangan {numberText(m.reserved_balance)}</small>{m.notes?<p>{m.notes}</p>:null}{m.correction_count&&m.correction_count!=='0'?<p>Nota dibetulkan {m.correction_count} kali · perubahan asal di lot ini {numberText(m.original_physical_delta!)} PCS. Angka di atas adalah yang berlaku.</p>:null}{m.audit_movements&&m.correction_count!=='0'?<details><summary>Riwayat mutasi asal dan pembetulan</summary>{m.audit_movements.map(a=><p key={a.id}>{a.source_type} · {numberText((BigInt(a.available_delta)+BigInt(a.reservation_delta)).toString())} PCS · dicatat {formatCp6WibDateTime(a.recorded_at)}</p>)}</details>:null}{m.reversal_of_id?<small>Pembalik transaksi sebelumnya</small>:null}{m.valuation?<p>{m.valuation.state==='KNOWN'?`${currentLedger.contract_version==='cp7.fg-ledger.v2'?'HPP lot saat ini':'HPP tercatat'} Rp${numberText(m.valuation.unit_cost!)} / PCS`:'Biaya belum lengkap'}</p>:null}<TransactionSourceLink sourceType={m.source_type} sourceId={m.source_id} disabled={busy||Boolean(blockReason)}/><details><summary>Referensi pencatatan</summary><small>{m.source_type} · {m.source_id??'Tanpa dokumen'}</small><small>Dicatat {formatCp6WibDateTime(m.recorded_at)}</small></details></article>)}
        <div className="cproc-pagination"><span>Total {currentLedger.page.total} mutasi</span><button disabled={busy||!currentLedger.page.offset} onClick={()=>{requested.current.movementOffset=Math.max(0,currentLedger.page.offset-25);void load()}}>Mutasi sebelumnya</button><button disabled={busy||currentLedger.page.next_offset===null} onClick={()=>{requested.current.movementOffset=currentLedger.page.next_offset??0;void load()}}>Mutasi berikutnya</button></div>{finance?<small>Biaya memakai perhitungan terkini yang sudah tercatat.</small>:null}
      </>:<p>Pilih posisi barang untuk melihat mutasi, reservasi, dan pembatalannya.</p>}</aside></div></>:null}
  </section></>
}
