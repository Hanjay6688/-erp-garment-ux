import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso,formatCp6WibDateTime} from './cp6BusinessTime'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseFgWorkspace,fgPositionKey,type FgPosition,type FgWorkspace} from './fgContract'
import {fgAdjustmentObject,fgAdjustmentQty,parseFgAdjustments,parseFgAdjustmentOutcome,type FgAdjustments} from './fgAdjustmentContract'
import type {Json} from './types/database.preconnect'
import RecordTools,{orderRecordPage,type RecordPageOrder} from './RecordTools'
import './procurement-connected.css'
import './fg-connected.css'
type Line=Pick<FgPosition,'product_id'|'commercial_sku'|'size_code'|'lot_id'|'lot_number'|'quality_grade'>&{qty:string;notes:string|null}
type Form={id:string|null;version:string|null;location:string;locationName:string;number:string;at:string;originalAt:string|null;reasonCode:string;reason:string;notes:string|null;lines:Line[]}
const statusLabel={DRAFT:'Draft',POSTED:'Sudah disahkan',REVERSED:'Dibatalkan'}
export default function ConnectedFgAdjustmentPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('warehouse.fg.view'))return <section className="panel" role="alert">Hak melihat barang jadi diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi gudang belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),finance=identity.permissions.includes('finance.hpp.view')
 const mutation=useProductionMutation('FG_ADJUSTMENT'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [stock,setStock]=useState<FgWorkspace|null>(null),[docs,setDocs]=useState<FgAdjustments|null>(null),[form,setForm]=useState<Form|null>(null)
 const [search,setSearch]=useState(''),[docSearch,setDocSearch]=useState(''),[loading,setLoading]=useState(false),[error,setError]=useState(''),[reviewed,setReviewed]=useState(false),[reason,setReason]=useState('Jumlah dan alasan sudah diperiksa')
 const [stockOrder,setStockOrder]=useState<RecordPageOrder>('SOURCE'),[docOrder,setDocOrder]=useState<RecordPageOrder>('SOURCE'),[docStatus,setDocStatus]=useState('')
 const request=useRef({q:'',offset:0,docQ:'',docOffset:0,selected:null as string|null}),sequence=useRef(0)
 const load=useCallback(async()=>{
  const q={...request.current},s=++sequence.current,ticket=beginRead();setLoading(true);setError('');setStock(null);setDocs(null);setReviewed(false)
  try{
   const [a,b]=await Promise.all([client.rpc('erp_cp7_get_fg_v1',{p_query:{purpose:'SUMMARY',q:q.q,show_zero:true,offset:q.offset,limit:25}}),client.rpc('erp_cp7_get_fg_adjustments_v1',{p_query:{q:q.docQ,offset:q.docOffset,limit:25,adjustment_id:q.selected}})])
   if(!isReadCurrent(ticket)||s!==sequence.current)return false;if(a.error)throw a.error
   let result=b,selected=q.selected
   if(result.error?.message.includes('CP7_FG_ADJUST_NOT_FOUND')&&selected){result=await client.rpc('erp_cp7_get_fg_adjustments_v1',{p_query:{q:q.docQ,offset:q.docOffset,limit:25,adjustment_id:null}});if(!isReadCurrent(ticket)||s!==sequence.current)return false;selected=null;request.current.selected=null}
   if(result.error)throw result.error
   const st=parseFgWorkspace(a.data,finance,'SUMMARY'),ds=parseFgAdjustments(result.data,finance)
   if(st.page.offset!==q.offset||ds.page.offset!==q.docOffset||(ds.detail?.id??null)!==selected)throw Error('Dokumen atau halaman berubah. Muat ulang.')
   setStock(st);setDocs(ds);return finishRead(ticket)
  }catch(e){if(isReadCurrent(ticket)&&s===sequence.current)setError(normalizeClientError(e).message);return false}
  finally{if(s===sequence.current)setLoading(false)}
 },[client,finance,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 const handlers:ProductionMutationHandlers={
  send:e=>{const p=fgAdjustmentObject(e.payload);return client.rpc('erp_cp7_save_fg_adjustment_v1',{p_action:e.action,p_payload:p.document as Json,p_request:e.id,p_expected:p.expected_version as string|null})},
  validate:(v,e)=>{parseFgAdjustmentOutcome(v,e.id,e.action,fgAdjustmentObject(e.payload).document as Json)},
  retire:(v,e)=>{const r=parseFgAdjustmentOutcome(v,e.id,e.action,fgAdjustmentObject(e.payload).document as Json);request.current.selected=r.status==='DELETED'?null:r.adjustment_id;setForm(null);setDocs(null);setStock(null);setReviewed(false)},reload:load,
 }
 const write=(action:string,document:Json,version:string|null)=>run(action,{document,expected_version:version},null,handlers)
 const locked=mutation.writerLocked||loading,current=docs?.detail,canWrite=docs?.can_adjust===true
 const stale=Boolean(form?.id&&(!current||current.id!==form.id||current.row_version!==form.version||!current.editable))
 const at=form?(form.originalAt&&form.at===cp6WibDateTimeInput(form.originalAt)?form.originalAt:cp6WibPhysicalTimeToIso(form.at)):null
 const payload:Json|null=form&&at&&form.number.trim()&&form.reason.trim()&&form.lines.length>0&&form.lines.every(l=>l.lot_id&&fgAdjustmentQty(l.qty))?{
  ...(form.id?{id:form.id}:{}),adjustment_number:form.number.trim(),location_id:form.location,physical_at:at,reason_code:form.reasonCode,reason:form.reason.trim(),change_reason:form.reason.trim(),notes:form.notes,
  items:form.lines.map(l=>({product_id:l.product_id,lot_id:l.lot_id,quality_grade:l.quality_grade,qty_signed:l.qty,notes:l.notes})),
 }:null
 const add=(p:FgPosition)=>{
  const line:Line={product_id:p.product_id,commercial_sku:p.commercial_sku,size_code:p.size_code,lot_id:p.lot_id,lot_number:p.lot_number,quality_grade:p.quality_grade,qty:'',notes:null}
  if(form)setForm({...form,lines:[...form.lines,line]})
  else setForm({id:null,version:null,location:p.location_id,locationName:p.location_name,number:'',at:cp6WibDateTimeInput(),originalAt:null,reasonCode:'COUNT_CORRECTION',reason:'',notes:null,lines:[line]})
 }
 const edit=()=>{if(!current?.editable)return;setForm({id:current.id,version:current.row_version,location:current.location_id,locationName:current.location_name,number:current.number,at:cp6WibDateTimeInput(current.physical_at),originalAt:current.physical_at,reasonCode:current.reason_code,reason:current.reason,notes:current.notes,lines:current.items.map(i=>({...i,qty:i.qty_signed}))});setReviewed(false)}
 return <section className="cproc cfg cfga"><header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · KOREKSI BARANG JADI</div><h1>Penyesuaian barang jadi</h1><p>Pilih lot dan ukuran yang diperiksa. Isi perubahan jumlah: minus untuk pengurangan, plus untuk penambahan.</p></div><button disabled={loading||mutation.busy} onClick={()=>void load()}>Muat ulang FG</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel"/>{error?<p className="panel" role="alert">{error}</p>:null}{loading?<p role="status">Memuat penyesuaian…</p>:null}
  <RecordTools title="sumber penyesuaian FG" busy={loading||mutation.busy} order={stockOrder} onOrder={setStockOrder} onBrowse={()=>{setSearch('');request.current.q='';request.current.offset=0;void load()}} submitLabel="Cari sumber FG" onSubmit={e=>{e.preventDefault();request.current.q=search.trim();request.current.offset=0;void load()}} search={<label>Cari SKU, ukuran atau lot<input aria-label="Cari sumber penyesuaian FG" value={search} maxLength={120} onChange={e=>setSearch(e.target.value)}/></label>}/>
  <section className="panel"><h2>Pilih barang</h2>{orderRecordPage(stock?.page.rows,stockOrder,p=>`${p.commercial_sku} ${p.size_code} ${p.lot_number??''}`).map(p=><article className="cfg-position" key={fgPositionKey(p)}><h3>{p.commercial_sku} · {p.size_code}</h3><p>{p.lot_number??'Lot belum diketahui'} · {p.quality_grade.replaceAll('_',' ')} · {p.location_name}</p><p>Fisik {numberText(p.physical_qty)} · cadangan {numberText(p.reserved_qty)} · tersedia {numberText(p.available_qty)} PCS</p><button disabled={locked||!canWrite||p.quality!=='KNOWN'||!p.lot_id||Boolean(form&&(form.location!==p.location_id||form.lines.length>=100||form.lines.some(l=>l.lot_id===p.lot_id&&l.quality_grade===p.quality_grade)))} onClick={()=>add(p)}>Tambahkan {p.commercial_sku} · {p.size_code}</button></article>)}{stock?<div className="cproc-pagination"><span>Total {stock.page.total} posisi</span><button disabled={loading||mutation.busy||!stock.page.offset} onClick={()=>{request.current.offset=Math.max(0,stock.page.offset-25);void load()}}>Sumber sebelumnya</button><button disabled={loading||mutation.busy||stock.page.next_offset===null} onClick={()=>{request.current.offset=stock.page.next_offset??0;void load()}}>Sumber berikutnya</button></div>:null}</section>
  {form?<form className="panel" onSubmit={e=>{e.preventDefault();if(payload&&!locked&&!stale&&canWrite)void write('SAVE',payload,form.version)}}><div className="cproc-heading"><h2>Draft koreksi · {form.locationName}</h2><button type="button" disabled={mutation.busy} onClick={()=>setForm(null)}>Tutup draft</button></div>{stale?<p role="alert">Draft berubah. Tutup lalu buka kembali dengan versi terbaru.</p>:null}<fieldset disabled={locked||stale||!canWrite}><div className="cproc-grid"><label>Nomor dokumen<input aria-label="Nomor penyesuaian FG" required value={form.number} onChange={e=>setForm({...form,number:e.target.value})}/></label><label>Waktu fisik · WIB<input type="datetime-local" aria-label="Waktu penyesuaian FG WIB" required value={form.at} onChange={e=>setForm({...form,at:e.target.value})}/></label><label>Jenis koreksi<select value={form.reasonCode} aria-label="Jenis koreksi FG" onChange={e=>setForm({...form,reasonCode:e.target.value})}><option value="COUNT_CORRECTION">Selisih hitung</option><option value="LOSS">Hilang</option><option value="DAMAGE">Rusak</option></select></label><label>Alasan dan bukti<textarea aria-label="Alasan penyesuaian FG" required value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}/></label></div>
   {form.lines.map((l,i)=><article className="cproc-item" key={`${l.lot_id}:${l.quality_grade}`}><h3>{l.commercial_sku} · {l.size_code}</h3><p>{l.lot_number} · {l.quality_grade.replaceAll('_',' ')}</p><label>Perubahan jumlah (PCS)<input aria-label={`Perubahan FG ${i+1}`} inputMode="text" placeholder="Contoh: -2 atau 3" value={l.qty} onChange={e=>setForm({...form,lines:form.lines.map((x,n)=>n===i?{...x,qty:e.target.value}:x)})}/></label><button type="button" onClick={()=>setForm({...form,lines:form.lines.filter((_,n)=>n!==i)})}>Hapus baris {i+1}</button></article>)}
   <p>Draft belum mengubah stok. Nilai biaya mengikuti lot barang saat disahkan.</p><button className="primary-btn" disabled={!payload}>Simpan draft FG</button></fieldset></form>:null}
  <RecordTools title="dokumen penyesuaian FG" busy={loading||mutation.busy} order={docOrder} onOrder={setDocOrder} filterScope="PAGE" onBrowse={()=>{setDocSearch('');setDocStatus('');request.current.docQ='';request.current.docOffset=0;void load()}} submitLabel="Cari koreksi FG" onSubmit={e=>{e.preventDefault();request.current.docQ=docSearch.trim();request.current.docOffset=0;void load()}}
   search={<label>Cari dokumen<input aria-label="Cari dokumen penyesuaian FG" value={docSearch} maxLength={120} onChange={e=>setDocSearch(e.target.value)}/></label>}
   filters={<label>Status di halaman ini<select aria-label="Status halaman penyesuaian FG" value={docStatus} onChange={e=>setDocStatus(e.target.value)}><option value="">Semua status</option>{Object.entries(statusLabel).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}/>
  <div className="cfg-layout"><section className="panel"><h2>Riwayat koreksi</h2>{orderRecordPage(docs?.page.rows.filter(d=>!docStatus||d.status===docStatus),docOrder,d=>d.number).map(d=><button className="cproc-receipt" key={d.id} disabled={loading||mutation.busy||Boolean(form)} aria-pressed={d.id===current?.id} onClick={()=>{request.current.selected=d.id;void load()}}><span><strong>{d.number}</strong><small>{d.location_name} · {formatCp6WibDateTime(d.physical_at)}</small></span><span>{statusLabel[d.status]}</span></button>)}{docs?<div className="cproc-pagination"><span>Total {docs.page.total}</span><button disabled={loading||mutation.busy||!docs.page.offset} onClick={()=>{request.current.docOffset=Math.max(0,docs.page.offset-25);void load()}}>Dokumen sebelumnya</button><button disabled={loading||mutation.busy||docs.page.next_offset===null} onClick={()=>{request.current.docOffset=docs.page.next_offset??0;void load()}}>Dokumen berikutnya</button></div>:null}</section>
  <aside className="panel cfga-detail">{current?<><h2>{current.number}</h2><strong>{statusLabel[current.status]}</strong><p>{current.location_name} · {formatCp6WibDateTime(current.physical_at)}</p><p>{current.reason}</p>{current.notes?<p>{current.notes}</p>:null}{current.items.map(i=><article className="cproc-item" key={i.id}><h3>{i.commercial_sku} · {i.size_code}</h3><p>{i.lot_number} · {i.quality_grade.replaceAll('_',' ')} · perubahan {numberText(i.qty_signed)} PCS</p>{i.notes?<p>{i.notes}</p>:null}{i.valuation?<p>{i.valuation.state==='KNOWN'?`Nilai berdasarkan HPP lot terkini Rp${numberText(i.valuation.value!)}${current.status==='DRAFT'?' · belum dibukukan':''}`:'Biaya belum lengkap · nilai belum diketahui'}</p>:null}</article>)}
   {!current.managed?<p>Koreksi dokumen ini melalui transaksi asalnya.</p>:current.status!=='REVERSED'&&canWrite?<div className="cproc-review"><label>Catatan tindakan<input aria-label="Catatan tindakan FG" disabled={locked} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label><label className="cfg-check"><input type="checkbox" disabled={locked} checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Jumlah, lot, ukuran, dan alasan sudah saya periksa.</label>{current.status==='DRAFT'?<>{current.editable?<button disabled={locked||Boolean(form)} onClick={edit}>Edit draft FG</button>:<p role="alert">Dokumen sumber berubah. Periksa melalui alur asalnya.</p>}<button className="primary-btn" disabled={locked||Boolean(form)||!current.editable||!reviewed||!reason.trim()} onClick={()=>void write('POST',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Sahkan koreksi FG</button><button disabled={locked||Boolean(form)||!reviewed||!reason.trim()} onClick={()=>void write('DELETE',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Hapus draft FG</button></>:<button disabled={locked||Boolean(form)||!reviewed||!reason.trim()} onClick={()=>void write('REVERSE',{adjustment_id:current.id,change_reason:reason.trim()},current.row_version)}>Batalkan koreksi FG</button>}</div>:null}</>:<><h2>Periksa koreksi</h2><p>Pilih dokumen untuk melihat seluruh baris dan tindak lanjutnya.</p></>}</aside></div>
 </section>
}
