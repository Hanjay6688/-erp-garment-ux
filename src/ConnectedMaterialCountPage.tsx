import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import RecordTools,{orderRecordPage,type RecordPageOrder} from './RecordTools'
import MaterialCountSourcePicker from './MaterialCountSourcePicker'
import { formatReceiptDecimal as numberText, receiptDecimal } from './procurementContract'
import { materialObject, parseMaterials, type MaterialBalance, type MaterialsWorkspace } from './materialContract'
import { parseCountPreview, parseCounts, parseCountOutcome, countPositive, countNonzero, type CountPreview, type CountWorkspace } from './materialCountContract'
import type { Json } from './types/database.preconnect'
import './procurement-connected.css'
import './materials-connected.css'
const canonicalQty=(v:string)=>v.replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,'')
const statusLabel={DRAFT:'Draft',POSTED:'Sudah disahkan',REVERSED:'Dibatalkan'}
const countAvailability:Record<MaterialBalance['availability'],string>={
 ON_HAND:'Siap dihitung.',
 EMPTY:'Saldo sistem nol. Isi jumlah fisik yang ditemukan.',
 REVIEW_REQUIRED:'Saldo atau identitas roll perlu diperiksa sebelum hitung fisik.',
 MATERIAL_INACTIVE:'Bahan nonaktif; belum bisa dipilih untuk hitung fisik.',
 LOCATION_INACTIVE:'Gudang nonaktif; belum bisa dipilih untuk hitung fisik.',
 SPECIAL_ZONE:'Zona jasa. Koreksi melalui transaksi sumbernya.',
 LOCATION_REVIEW:'Lokasi ini bukan gudang bahan. Periksa lokasi barang terlebih dahulu.',
}
type CountSource=Pick<MaterialBalance,'material_id'|'material_sku'|'material_name'|'unit_code'|'roll_id'|'roll_number'|'location_id'|'location_name'>
type FormLine={source:CountSource;qty:string;cost:string;lineNotes:string|null}
type Form={lines:FormLine[];at:string;originalAt:string|null;id:string|null;version:string|null;number:string;reason:string;note:string}
const sourceKey=(source:Pick<CountSource,'material_id'|'roll_id'>)=>`${source.material_id}:${source.roll_id}`
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
 const [showRegistered,setShowRegistered]=useState(false)
 const [stockOrder,setStockOrder]=useState<RecordPageOrder>('SOURCE'),[docOrder,setDocOrder]=useState<RecordPageOrder>('SOURCE'),[docStatus,setDocStatus]=useState('')
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
 const locked=mutation.writerLocked||loading,first=form?.lines[0]?.source,at=form?(form.originalAt&&form.at===cp6WibDateTimeInput(form.originalAt)?form.originalAt:cp6WibPhysicalTimeToIso(form.at)):null
 const scope:Json|null=form&&first&&form.lines.length<=100&&at&&form.lines.every(l=>receiptDecimal(l.qty)!==null)?{location_id:first.location_id,physical_at:at,items:form.lines.map(l=>({material_id:l.source.material_id,roll_id:l.source.roll_id,physical_qty:receiptDecimal(l.qty)}))}:null
 const scopeKey=JSON.stringify(scope),scopeCurrent=useRef(scopeKey);scopeCurrent.current=scopeKey
 const checked=preview?.key===scopeKey?preview.value:null,checkedByKey=new Map(checked?.items.map(l=>[sourceKey(l),l]))
 const payload:Json|null=form&&first&&scope&&checked&&checked.items.some(l=>countNonzero(l.qty_signed))&&form.lines.every(l=>{const p=checkedByKey.get(sourceKey(l.source));return p&&(!countPositive(p.qty_signed)||finance&&receiptDecimal(l.cost)!==null)})&&form.number.trim()&&form.note.trim()?{
  ...(form.id?{id:form.id}:{}),adjustment_number:form.number.trim(),location_id:first.location_id,physical_at:at,reason_code:form.reason==='FOUND'?'COUNT_CORRECTION':form.reason,change_reason:form.note.trim(),notes:(form.reason==='FOUND'?'Barang ditemukan. ':'')+form.note.trim(),
  items:form.lines.map(l=>{const p=checkedByKey.get(sourceKey(l.source))!;return {material_id:p.material_id,roll_id:p.roll_id,physical_qty:receiptDecimal(l.qty),basis_token:p.basis_token,...(countPositive(p.qty_signed)?{input_unit_cost:receiptDecimal(l.cost)}:{}),...(l.lineNotes!==null?{notes:l.lineNotes}:{})}}),
 }:null
 const inspect=async()=>{
  if(!scope||locked)return;const key=scopeKey,ticket=beginRead(),s=++sequence.current;setLoading(true);setError('');setPreview(null)
  try{const r=await client.rpc('erp_cp7_preview_material_count_v1',{p_scope:scope});if(!isReadCurrent(ticket)||s!==sequence.current||key!==scopeCurrent.current)return;if(r.error)throw r.error
   const v=parseCountPreview(r.data)
   if(!form||v.items.length!==form.lines.length||v.location_id!==first?.location_id||Date.parse(v.physical_at)!==Date.parse(at!)||form.lines.some(l=>{const p=v.items.find(p=>sourceKey(p)===sourceKey(l.source));return !p||canonicalQty(p.physical_qty)!==canonicalQty(receiptDecimal(l.qty)!)||p.unit_code!==l.source.unit_code}))throw Error('Pratinjau hitung fisik tidak cocok.')
   if(finishRead(ticket))setPreview({key,value:v})
  }catch(e){if(isReadCurrent(ticket))setError(normalizeClientError(e).message)}finally{if(s===sequence.current)setLoading(false)}
 }
 const write=(action:string,document:Json,version:string|null)=>run(action,{document,expected_version:version},null,handlers)
 const current=documents?.detail,stale=Boolean(form?.id&&(!current||current.id!==form.id||current.row_version!==form.version||!current.edit))
 const edit=()=>{if(!current?.edit||!current.location_id||!current.location_name||locked)return;const location_id=current.location_id,location_name=current.location_name,inputs='items' in current.edit?current.edit.items:[{...current.items[0],...current.edit}];setReviewed(false);setPreview(null);setForm({lines:inputs.map(item=>({source:{material_id:item.material_id,material_sku:item.material_sku,material_name:item.material_name,unit_code:item.unit_code,roll_id:item.roll_id,roll_number:item.roll_number,location_id,location_name},qty:item.physical_qty,cost:item.input_unit_cost??'',lineNotes:item.notes})),at:cp6WibDateTimeInput(current.physical_at),originalAt:current.physical_at,id:current.id,version:current.row_version,number:current.number,reason:current.reason_code,note:current.notes??''})}
 const selectSource=(source:CountSource)=>{setPreview(null);setForm(f=>{const line={source,qty:'',cost:'',lineNotes:null};if(!f)return {lines:[line],at:cp6WibDateTimeInput(),originalAt:null,id:null,version:null,number:'',reason:'COUNT_CORRECTION',note:''};if(f.lines.length>=100||f.lines[0].source.location_id!==source.location_id||f.lines.some(l=>sourceKey(l.source)===sourceKey(source)))return f;return {...f,lines:[...f.lines,line]}})}
 const updateLine=(index:number,patch:Partial<FormLine>)=>setForm(f=>f?{...f,lines:f.lines.map((l,i)=>i===index?{...l,...patch}:l)}:f)
 return <section className="cproc cmat"><header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · HITUNG FISIK</div><h1>Penyesuaian bahan</h1><p>Isi jumlah barang yang benar-benar ada. Periksa saldo dan selisih sebelum mengesahkan.</p></div><button disabled={loading||mutation.busy} onClick={()=>void load()}>Muat ulang</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel"/>{error?<p className="panel" role="alert">{error}</p>:null}{loading?<p role="status">Memuat hitung fisik…</p>:null}
  <RecordTools title="sumber hitung fisik" busy={loading||mutation.busy} order={stockOrder} onOrder={setStockOrder} onBrowse={()=>{setSearch('');request.current.q='';request.current.offset=0;void load()}} submitLabel="Cari bahan" onSubmit={e=>{e.preventDefault();request.current.q=search.trim();request.current.offset=0;void load()}} search={<label>Cari bahan, roll, atau gudang<input aria-label="Cari bahan hitung fisik" value={search} maxLength={120} onChange={e=>setSearch(e.target.value)}/></label>}/>
  <section className="panel"><h2>Pilih barang yang dihitung</h2>
   {!loading&&stock?.page.rows.length===0?<p>Tidak ada bahan sesuai pencarian.</p>:null}
   {stock&&!stock.capabilities.transfer?<p role="alert">Hak penyesuaian stok tidak tersedia. Muat ulang atau hubungi admin.</p>:null}
   {form?<p>{form.lines.length} barang dipilih di {first?.location_name}. Tambahkan barang dari gudang yang sama, maksimal 100 baris.</p>:null}
   {orderRecordPage(stock?.page.rows,stockOrder,r=>`${r.material_name} ${r.roll_number??r.material_sku}`).map(r=>{const selected=first?.location_id===r.location_id&&form?.lines.some(l=>sourceKey(l.source)===sourceKey(r)),otherLocation=first&&first.location_id!==r.location_id;return <article className="cmat-roll" key={`${r.material_id}:${r.roll_id}:${r.location_id}`}>
    <div><strong>{r.roll_number??r.material_name}</strong><small>{r.material_sku} · {r.location_name}</small><small>Saldo sekarang {numberText(r.qty)} {r.unit_code}</small><small>{countAvailability[r.availability]}</small>{otherLocation?<small>Tutup pemeriksaan saat ini untuk menghitung di gudang ini.</small>:null}</div>
    <button disabled={locked||stale||stock?.capabilities.transfer!==true||!['ON_HAND','EMPTY'].includes(r.availability)||selected||Boolean(otherLocation)||Boolean(form&&form.lines.length>=100)} onClick={()=>selectSource(r)}>{selected?'Sudah dipilih':`Hitung ${r.roll_number??r.material_name}`}</button>
   </article>})}
   {stock?<div className="cproc-pagination"><span>Total {stock.page.total}</span><button disabled={loading||mutation.busy||!stock.page.offset} onClick={()=>{request.current.offset=Math.max(0,stock.page.offset-25);void load()}}>Bahan sebelumnya</button><button disabled={loading||mutation.busy||stock.page.next_offset===null} onClick={()=>{request.current.offset=stock.page.next_offset??0;void load()}}>Bahan berikutnya</button></div>:null}
  </section>
  <button disabled={locked||stale} aria-expanded={showRegistered} onClick={()=>setShowRegistered(v=>!v)}>{showRegistered?'Tutup pilihan bahan terdaftar':'Pilih bahan di luar daftar saldo'}</button>
  {showRegistered?<MaterialCountSourcePicker client={client} location={first?{id:first.location_id,name:first.location_name}:undefined} selected={form?.lines.map(l=>sourceKey(l.source))??[]} disabled={locked||stale} onSelect={selectSource}/>:null}
  {form?<form className="panel cmat-count-form" onSubmit={e=>{e.preventDefault();if(payload&&!locked&&!stale)void write('SAVE',payload,form.version)}}>
   <div className="cproc-heading"><div><h2>Hitung fisik {form.lines.length===1?(first?.roll_number??first?.material_name):`${form.lines.length} barang`}</h2><p>{first?.location_name} · satu dokumen pemeriksaan</p></div><button type="button" disabled={mutation.busy} onClick={()=>{setForm(null);setPreview(null)}}>Tutup formulir</button></div>
   {stale?<p role="alert">Draft berubah. Tutup formulir lalu buka kembali dengan data terbaru.</p>:null}
   <fieldset disabled={locked||stale}>
    <div className="cproc-grid">
     <label>Nomor pemeriksaan<input aria-label="Nomor hitung fisik" required value={form.number} onChange={e=>setForm({...form,number:e.target.value})}/></label>
     <label>Waktu hitung · WIB<input aria-label="Waktu hitung WIB" type="datetime-local" required value={form.at} onChange={e=>setForm({...form,at:e.target.value})}/></label>
     <label>Alasan<select aria-label="Alasan hitung fisik" value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}><option value="COUNT_CORRECTION">Koreksi hitung</option><option value="LOSS">Hilang / tidak ditemukan</option><option value="DAMAGE">Rusak / hama / bencana</option><option value="FOUND">Barang ditemukan</option></select></label>
     <label>Catatan dan bukti pemeriksaan<textarea aria-label="Catatan hitung fisik" required value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/></label>
    </div>
    {form.lines.map((entry,index)=>{const line=checkedByKey.get(sourceKey(entry.source)),positive=line&&countPositive(line.qty_signed),label=entry.source.roll_number??`${entry.source.material_name} ${entry.source.material_sku}`;return <article className="cproc-item cmat-count-input" key={sourceKey(entry.source)}>
     <h3>{label} · {entry.source.material_sku}</h3>
     <label>Jumlah fisik ({entry.source.unit_code})<input aria-label={form.lines.length===1?'Jumlah fisik bahan':`Jumlah fisik ${label}`} inputMode="decimal" required value={entry.qty} onChange={e=>updateLine(index,{qty:e.target.value})}/></label>
     {form.lines.length>1?<button type="button" aria-label={`Lepas ${label} dari pemeriksaan`} onClick={()=>{setPreview(null);setForm({...form,lines:form.lines.filter((_,i)=>i!==index)})}}>Lepas barang</button>:null}
     {line?<div className="cproc-review"><p>Saldo pada waktu hitung <strong>{numberText(line.system_qty)} {entry.source.unit_code}</strong></p><p>Jumlah fisik <strong>{numberText(line.physical_qty)} {entry.source.unit_code}</strong> · selisih <strong>{numberText(line.qty_signed)} {entry.source.unit_code}</strong></p>
      {positive?(finance?<label>Harga satuan barang ditemukan (Rp)<input aria-label={form.lines.length===1?'Harga satuan hasil hitung':`Harga satuan hasil hitung ${label}`} inputMode="decimal" value={entry.cost} onChange={e=>updateLine(index,{cost:e.target.value})}/></label>:<p role="alert">Barang tambahan memerlukan harga dari petugas yang memiliki hak nilai persediaan.</p>):null}
      {!countNonzero(line.qty_signed)?<p>Jumlah sudah sesuai. Hasil hitung tetap disimpan tanpa mutasi penyesuaian.</p>:null}
     </div>:null}
    </article>})}
    <button type="button" disabled={!scope} onClick={()=>void inspect()}>Periksa selisih</button>
    {checked?<p>{checked.items.some(l=>countNonzero(l.qty_signed))?'Draft belum mengubah stok. Seluruh saldo diperiksa lagi saat disahkan.':'Semua jumlah sudah sesuai; tidak perlu penyesuaian.'}</p>:<p>Periksa selisih setelah seluruh jumlah dan waktu hitung diisi.</p>}
    <button className="primary-btn" disabled={!payload}>Simpan draft hitung fisik</button>
   </fieldset>
  </form>:null}
  <RecordTools title="dokumen hitung fisik" busy={loading||mutation.busy} order={docOrder} onOrder={setDocOrder} filterScope="PAGE" onBrowse={()=>{setDocSearch('');setDocStatus('');request.current.docQ='';request.current.docOffset=0;void load()}} submitLabel="Cari pemeriksaan" onSubmit={e=>{e.preventDefault();request.current.docQ=docSearch.trim();request.current.docOffset=0;void load()}}
   search={<label>Cari nomor pemeriksaan<input aria-label="Cari dokumen hitung fisik" value={docSearch} maxLength={120} onChange={e=>setDocSearch(e.target.value)}/></label>}
   filters={<label>Status di halaman ini<select aria-label="Status halaman hitung fisik" value={docStatus} onChange={e=>setDocStatus(e.target.value)}><option value="">Semua status</option>{Object.entries(statusLabel).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}/>
  <div className="cproc-layout"><section className="panel"><h2>Riwayat penyesuaian</h2>{!loading&&documents?.page.rows.length===0?<p>Belum ada pemeriksaan sesuai pencarian.</p>:null}{orderRecordPage(documents?.page.rows.filter(d=>!docStatus||d.status===docStatus),docOrder,d=>d.number).map(d=><button className="cproc-receipt" key={d.id} disabled={loading||mutation.busy} aria-pressed={d.id===current?.id} onClick={()=>{request.current.selected=d.id;void load()}}><span><strong>{d.number}</strong><small>{d.location_name??'Lokasi belum diketahui'} · {formatCp6WibDateTime(d.physical_at)}</small></span><span className={`cproc-status ${d.status.toLowerCase()}`}>{statusLabel[d.status]}</span></button>)}{documents?<div className="cproc-pagination"><span>Total {documents.page.total}</span><button disabled={loading||mutation.busy||!documents.page.offset} onClick={()=>{request.current.docOffset=Math.max(0,documents.page.offset-25);void load()}}>Pemeriksaan sebelumnya</button><button disabled={loading||mutation.busy||documents.page.next_offset===null} onClick={()=>{request.current.docOffset=documents.page.next_offset??0;void load()}}>Pemeriksaan berikutnya</button></div>:null}</section>
  <aside className="panel cmat-count-detail">{current?<><div className="eyebrow">DOKUMEN PENYESUAIAN</div><h2>{current.number}</h2><span className={`cproc-status ${current.status.toLowerCase()}`}>{statusLabel[current.status]}</span><p>{current.location_name??'Lokasi belum diketahui'} · {formatCp6WibDateTime(current.physical_at)}</p><p>{current.status==='DRAFT'?'Draft belum mengubah stok.':current.status==='POSTED'?'Penyesuaian stok sudah disahkan.':'Penyesuaian sudah dibatalkan dengan mutasi pembalik.'}</p>{current.notes?<p>{current.notes}</p>:null}{current.items.map(i=><article className="cproc-item" key={i.id}><h3>{i.material_name} · {i.roll_number??i.material_sku}</h3><p>Selisih {numberText(i.qty_signed)} {i.unit_code}{i.physical_qty!==null?` · fisik ${numberText(i.physical_qty)}`:''}</p>{i.valuation?<small>{i.valuation.restated_value===null?'Nilai penyesuaian tersedia setelah disahkan.':`Nilai dokumen Rp${numberText(i.valuation.restated_value)} · mengikuti perhitungan biaya terkini.`}</small>:null}</article>)}
   {!current.managed_count?<p>Dokumen ini berasal dari alur lain. Koreksi melalui transaksi sumbernya.</p>:current.status!=='REVERSED'?<div className="cproc-review"><label>Catatan pengesahan atau pembatalan<input aria-label="Catatan tindakan hitung fisik" disabled={locked} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label><label className="cmat-check"><input type="checkbox" checked={reviewed} disabled={locked} onChange={e=>setReviewed(e.target.checked)}/>Saya sudah memeriksa jumlah dan alasan tindakan ini.</label>{current.status==='DRAFT'?<>{current.edit?<button disabled={locked||Boolean(form)} onClick={edit}>Edit draft hitung fisik</button>:null}<button className="primary-btn" disabled={locked||Boolean(form)||!reviewed||!reason.trim()||!documents?.capabilities.adjust} onClick={()=>void write('POST',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Sahkan hitung fisik</button><button disabled={locked||Boolean(form)||!reviewed||!reason.trim()||!documents?.capabilities.adjust} onClick={()=>void write('DELETE',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Hapus draft hitung fisik</button></>:documents?.capabilities.reverse?<button disabled={locked||Boolean(form)||!reviewed||!reason.trim()} onClick={()=>void write('REVERSE',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Batalkan hitung fisik</button>:null}</div>:null}</>:<><h2>Periksa penyesuaian</h2><p>Pilih dokumen untuk melihat hasil hitung dan tindak lanjutnya.</p></>}</aside></div>
 </section>
}
