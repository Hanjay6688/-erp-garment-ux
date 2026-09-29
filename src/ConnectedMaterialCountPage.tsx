import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatReceiptDecimal as numberText, receiptDecimal } from './procurementContract'
import { materialObject, parseMaterials, type MaterialBalance, type MaterialsWorkspace } from './materialContract'
import { parseCountPreview, parseCounts, parseCountOutcome, countPositive, countNonzero, type CountPreview, type CountWorkspace } from './materialCountContract'
import type { Json } from './types/database.preconnect'
import './procurement-connected.css'
import './materials-connected.css'
const canonicalQty=(v:string)=>v.replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,'')
const statusLabel={DRAFT:'Draft',POSTED:'Sudah disahkan',REVERSED:'Dibatalkan'}
type Form={source:MaterialBalance;qty:string;at:string;number:string;reason:string;note:string;cost:string}
export default function ConnectedMaterialCountPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')return <section className="panel">Masuk untuk mencatat hitung fisik bahan.</section>
 if(!identity.permissions.includes('warehouse.material.view')||!identity.permissions.includes('warehouse.stock.adjust'))return <section className="panel" role="alert">Hak melihat bahan dan menyesuaikan stok diperlukan.</section>
 return <CountPage key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function CountPage(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi hitung fisik belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),finance=identity.permissions.includes('finance.hpp.view')
 const mutation=useProductionMutation('MATERIAL_COUNT'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [stock,setStock]=useState<MaterialsWorkspace|null>(null),[documents,setDocuments]=useState<CountWorkspace|null>(null),[search,setSearch]=useState(''),[docSearch,setDocSearch]=useState('')
 const [form,setForm]=useState<Form|null>(null),[preview,setPreview]=useState<{key:string;value:CountPreview}|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('')
 const [reason,setReason]=useState('Jumlah fisik sudah dihitung ulang'),[reviewed,setReviewed]=useState(false)
 const request=useRef({q:'',offset:0,docQ:'',docOffset:0,selected:null as string|null}),sequence=useRef(0)
 const load=useCallback(async()=>{
  const q={...request.current},s=++sequence.current,ticket=beginRead();setLoading(true);setError('');setPreview(null);setReviewed(false)
  try{
   const [a,b]=await Promise.all([client.rpc('erp_cp7_get_materials_v1',{p_query:{q:q.q,show_zero:true,offset:q.offset,limit:25}}),client.rpc('erp_cp7_get_material_counts_v1',{p_query:{q:q.docQ,offset:q.docOffset,limit:25,adjustment_id:q.selected}})])
   if(!isReadCurrent(ticket)||s!==sequence.current)return false;if(a.error)throw a.error
   let documentsResult=b,selected=q.selected
   if(documentsResult.error?.message.includes('CP7_COUNT_NOT_FOUND')&&selected){
    documentsResult=await client.rpc('erp_cp7_get_material_counts_v1',{p_query:{q:q.docQ,offset:q.docOffset,limit:25,adjustment_id:null}})
    if(!isReadCurrent(ticket)||s!==sequence.current)return false
    selected=null;request.current.selected=null
   }
   if(documentsResult.error)throw documentsResult.error
   const st=parseMaterials(a.data,finance),ds=parseCounts(documentsResult.data,finance)
   if(st.page.offset!==q.offset||ds.page.offset!==q.docOffset||(ds.detail?.id??null)!==selected)throw Error('Dokumen hitung fisik tidak cocok dengan pilihan.')
   setStock(st);setDocuments(ds);return finishRead(ticket)
  }catch(e){if(isReadCurrent(ticket)){setStock(null);setDocuments(null);setError(normalizeClientError(e).message)}return false}
  finally{if(s===sequence.current)setLoading(false)}
 },[client,finance,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load()},[load])
 const handlers:ProductionMutationHandlers={
  send:envelope=>{const p=materialObject(envelope.payload);return client.rpc('erp_cp7_save_material_count_v1',{p_action:envelope.action,p_payload:p.document as Json,p_request:envelope.id,p_expected:p.expected_version as string|null})},
  validate:(v,e)=>{parseCountOutcome(v,e.id,e.action,materialObject(e.payload).document as Json)},
  retire:(v,e)=>{const r=parseCountOutcome(v,e.id,e.action,materialObject(e.payload).document as Json);request.current.selected=r.status==='DELETED'?null:r.adjustment_id;setDocuments(null);setPreview(null);setForm(null);setReviewed(false)},
  reload:load,
 }
 const locked=mutation.writerLocked||loading,qty=form?receiptDecimal(form.qty):null,at=form?cp6WibPhysicalTimeToIso(form.at):null
 const scope:Json|null=form&&qty!==null&&at?{location_id:form.source.location_id,physical_at:at,items:[{material_id:form.source.material_id,roll_id:form.source.roll_id,physical_qty:qty}]}:null
 const scopeKey=JSON.stringify(scope),scopeCurrent=useRef(scopeKey);scopeCurrent.current=scopeKey
 const checked=preview?.key===scopeKey?preview.value:null,line=checked?.items[0],positive=line?countPositive(line.qty_signed):false,cost=form?receiptDecimal(form.cost):null
 const payload:Json|null=form&&scope&&line&&countNonzero(line.qty_signed)&&(!positive||finance&&cost!==null)&&form.number.trim()&&form.note.trim()?{
  adjustment_number:form.number.trim(),location_id:form.source.location_id,physical_at:at,reason_code:form.reason==='FOUND'?'COUNT_CORRECTION':form.reason,change_reason:form.note.trim(),notes:(form.reason==='FOUND'?'Barang ditemukan. ':'')+form.note.trim(),
  items:[{material_id:line.material_id,roll_id:line.roll_id,physical_qty:qty,basis_token:line.basis_token,...(positive?{input_unit_cost:cost}:{})}],
 }:null
 const inspect=async()=>{
  if(!scope||locked)return;const key=scopeKey,ticket=beginRead(),s=++sequence.current;setLoading(true);setError('');setPreview(null)
  try{const r=await client.rpc('erp_cp7_preview_material_count_v1',{p_scope:scope});if(!isReadCurrent(ticket)||s!==sequence.current||key!==scopeCurrent.current)return;if(r.error)throw r.error
   const v=parseCountPreview(r.data)
   if(v.items.length!==1||canonicalQty(v.items[0].physical_qty)!==canonicalQty(qty!)||v.location_id!==form?.source.location_id||v.items[0].material_id!==form.source.material_id||v.items[0].roll_id!==form.source.roll_id||Date.parse(v.physical_at)!==Date.parse(at!))throw Error('Pratinjau hitung fisik tidak cocok.')
   if(finishRead(ticket))setPreview({key,value:v})
  }catch(e){if(isReadCurrent(ticket))setError(normalizeClientError(e).message)}finally{if(s===sequence.current)setLoading(false)}
 }
 const write=(action:string,document:Json,version:string|null)=>run(action,{document,expected_version:version},null,handlers)
 const current=documents?.detail
 return <section className="cproc cmat"><header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · HITUNG FISIK</div><h1>Penyesuaian bahan</h1><p>Isi jumlah barang yang benar-benar ada. Periksa saldo dan selisih sebelum mengesahkan.</p></div><button disabled={loading||mutation.busy} onClick={()=>void load()}>Muat ulang</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel"/>{error?<p className="panel" role="alert">{error}</p>:null}{loading?<p role="status">Memuat hitung fisik…</p>:null}
  <form className="panel cproc-search" onSubmit={e=>{e.preventDefault();request.current.q=search.trim();request.current.offset=0;void load()}}><label>Cari bahan, roll, atau gudang<input aria-label="Cari bahan hitung fisik" value={search} maxLength={120} onChange={e=>setSearch(e.target.value)}/></label><button disabled={loading||mutation.busy}>Cari bahan</button></form>
  <section className="panel"><h2>Pilih barang yang dihitung</h2>{stock?.page.rows.map(r=><article className="cmat-roll" key={`${r.material_id}:${r.roll_id}:${r.location_id}`}><div><strong>{r.roll_number??r.material_name}</strong><small>{r.material_sku} · {r.location_name}</small><small>Saldo sekarang {numberText(r.qty)} {r.unit_code}</small></div><button disabled={locked||!stock.capabilities.transfer||!['ON_HAND','EMPTY'].includes(r.availability)} onClick={()=>{setPreview(null);setForm({source:r,qty:'',at:cp6WibDateTimeInput(),number:'',reason:'COUNT_CORRECTION',note:'',cost:''})}}>Hitung {r.roll_number??r.material_name}</button></article>)}
   {stock?<div className="cproc-pagination"><span>Total {stock.page.total}</span><button disabled={loading||mutation.busy||!stock.page.offset} onClick={()=>{request.current.offset=Math.max(0,stock.page.offset-25);void load()}}>Bahan sebelumnya</button><button disabled={loading||mutation.busy||stock.page.next_offset===null} onClick={()=>{request.current.offset=stock.page.next_offset??0;void load()}}>Bahan berikutnya</button></div>:null}</section>
  {form?<form className="panel cmat-count-form" onSubmit={e=>{e.preventDefault();if(payload&&!locked)void write('SAVE',payload,null)}}><div className="cproc-heading"><div><h2>Hitung fisik {form.source.roll_number??form.source.material_name}</h2><p>{form.source.location_name} · jumlah dalam {form.source.unit_code}</p></div><button type="button" disabled={mutation.busy} onClick={()=>{setForm(null);setPreview(null)}}>Tutup formulir</button></div><fieldset disabled={locked}><div className="cproc-grid"><label>Nomor pemeriksaan<input aria-label="Nomor hitung fisik" required value={form.number} onChange={e=>setForm({...form,number:e.target.value})}/></label><label>Waktu hitung · WIB<input aria-label="Waktu hitung WIB" type="datetime-local" required value={form.at} onChange={e=>setForm({...form,at:e.target.value})}/></label><label>Jumlah fisik ({form.source.unit_code})<input aria-label="Jumlah fisik bahan" inputMode="decimal" required value={form.qty} onChange={e=>setForm({...form,qty:e.target.value})}/></label><label>Alasan<select aria-label="Alasan hitung fisik" value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}><option value="COUNT_CORRECTION">Koreksi hitung</option><option value="LOSS">Hilang / tidak ditemukan</option><option value="DAMAGE">Rusak / hama / bencana</option><option value="FOUND">Barang ditemukan</option></select></label><label>Catatan dan bukti pemeriksaan<textarea aria-label="Catatan hitung fisik" required value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/></label></div><button type="button" disabled={!scope} onClick={()=>void inspect()}>Periksa selisih</button>
   {line?<div className="cproc-review"><p>Saldo pada waktu hitung <strong>{numberText(line.system_qty)} {form.source.unit_code}</strong></p><p>Jumlah fisik <strong>{numberText(line.physical_qty)} {form.source.unit_code}</strong> · selisih <strong>{numberText(line.qty_signed)} {form.source.unit_code}</strong></p>{positive?(finance?<label>Harga satuan barang ditemukan (Rp)<input aria-label="Harga satuan hasil hitung" inputMode="decimal" value={form.cost} onChange={e=>setForm({...form,cost:e.target.value})}/></label>:<p role="alert">Barang tambahan memerlukan harga dari petugas yang memiliki hak nilai persediaan.</p>):null}{!countNonzero(line.qty_signed)?<p>Jumlah sudah sesuai; tidak perlu penyesuaian.</p>:<p>Draft belum mengubah stok. Saldo diperiksa lagi saat disahkan.</p>}</div>:<p>Periksa selisih setelah jumlah dan waktu hitung diisi.</p>}
   <button className="primary-btn" disabled={!payload}>Simpan draft hitung fisik</button></fieldset></form>:null}
  <form className="panel cproc-search" onSubmit={e=>{e.preventDefault();request.current.docQ=docSearch.trim();request.current.docOffset=0;void load()}}><label>Cari nomor pemeriksaan<input aria-label="Cari dokumen hitung fisik" value={docSearch} maxLength={120} onChange={e=>setDocSearch(e.target.value)}/></label><button disabled={loading||mutation.busy}>Cari pemeriksaan</button></form>
  <div className="cproc-layout"><section className="panel"><h2>Riwayat penyesuaian</h2>{documents?.page.rows.map(d=><button className="cproc-receipt" key={d.id} disabled={loading||mutation.busy} aria-pressed={d.id===current?.id} onClick={()=>{request.current.selected=d.id;void load()}}><span><strong>{d.number}</strong><small>{d.location_name??'Lokasi belum diketahui'} · {formatCp6WibDateTime(d.physical_at)}</small></span><span className={`cproc-status ${d.status.toLowerCase()}`}>{statusLabel[d.status]}</span></button>)}{documents?<div className="cproc-pagination"><span>Total {documents.page.total}</span><button disabled={loading||mutation.busy||!documents.page.offset} onClick={()=>{request.current.docOffset=Math.max(0,documents.page.offset-25);void load()}}>Pemeriksaan sebelumnya</button><button disabled={loading||mutation.busy||documents.page.next_offset===null} onClick={()=>{request.current.docOffset=documents.page.next_offset??0;void load()}}>Pemeriksaan berikutnya</button></div>:null}</section>
  <aside className="panel cmat-count-detail">{current?<><div className="eyebrow">DOKUMEN PENYESUAIAN</div><h2>{current.number}</h2><span className={`cproc-status ${current.status.toLowerCase()}`}>{statusLabel[current.status]}</span><p>{current.location_name??'Lokasi belum diketahui'} · {formatCp6WibDateTime(current.physical_at)}</p><p>{current.status==='DRAFT'?'Draft belum mengubah stok.':current.status==='POSTED'?'Penyesuaian stok sudah disahkan.':'Penyesuaian sudah dibatalkan dengan mutasi pembalik.'}</p>{current.notes?<p>{current.notes}</p>:null}{current.items.map(i=><article className="cproc-item" key={i.id}><h3>{i.material_name} · {i.roll_number??i.material_sku}</h3><p>Selisih {numberText(i.qty_signed)} {i.unit_code}{i.physical_qty!==null?` · fisik ${numberText(i.physical_qty)}`:''}</p>{i.valuation?<small>{i.valuation.restated_value===null?'Nilai penyesuaian tersedia setelah disahkan.':`Nilai dokumen Rp${numberText(i.valuation.restated_value)} · mengikuti perhitungan biaya terkini.`}</small>:null}</article>)}
   {!current.managed_count?<p>Dokumen ini berasal dari alur lain. Koreksi melalui transaksi sumbernya.</p>:current.status!=='REVERSED'?<div className="cproc-review"><label>Catatan pengesahan atau pembatalan<input aria-label="Catatan tindakan hitung fisik" disabled={locked} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label><label className="cmat-check"><input type="checkbox" checked={reviewed} disabled={locked} onChange={e=>setReviewed(e.target.checked)}/>Saya sudah memeriksa jumlah dan alasan tindakan ini.</label>{current.status==='DRAFT'?<><button className="primary-btn" disabled={locked||!reviewed||!reason.trim()||!documents?.capabilities.adjust} onClick={()=>void write('POST',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Sahkan hitung fisik</button><button disabled={locked||!reviewed||!reason.trim()||!documents?.capabilities.adjust} onClick={()=>void write('DELETE',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Hapus draft hitung fisik</button></>:documents?.capabilities.reverse?<button disabled={locked||!reviewed||!reason.trim()} onClick={()=>void write('REVERSE',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Batalkan hitung fisik</button>:null}</div>:null}</>:<><h2>Periksa penyesuaian</h2><p>Pilih dokumen untuk melihat hasil hitung dan tindak lanjutnya.</p></>}</aside></div>
 </section>
}
