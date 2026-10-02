import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibPhysicalTimeToIso,formatCp6WibDateTime} from './cp6BusinessTime'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseCorrectedFgBook,parseFgBookOptions,parseFgBookOutcome,bookDozens,type CorrectedFgBook,type CorrectedFgBookRow,type FgBookOptions,type BookOption,type BookFilterKind} from './fgBookContract'
import './procurement-connected.css'
import './fg-book-connected.css'

type Filters=Record<BookFilterKind,BookOption[]>
const emptyFilters=():Filters=>({BRAND:[],CUSTOMER:[],TYPE:[]})
const kinds:BookFilterKind[]=['BRAND','CUSTOMER','TYPE']
const filterLabels={BRAND:'Merek',CUSTOMER:'Toko',TYPE:'Jenis mutasi'}
const movementLabels:Record<string,string>={SALE:'Penjualan',SALE_RESERVE:'Cadangan penjualan',FG_ADJUSTMENT:'Koreksi stok',REVERSAL:'Pembatalan',SALES_RETURN:'Retur penjualan',QC_GOOD:'Hasil QC',REWORK_IN:'Hasil rework'}
export default function ConnectedFgBookPage({bookName}:{bookName:'Vivo'|'Widie'}){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('warehouse.movement.view'))return <section className="panel" role="alert">Hak melihat mutasi barang jadi diperlukan.</section>
 return <Workspace bookName={bookName} key={`${bookName}:${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({bookName}:{bookName:'Vivo'|'Widie'}){
 const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw Error('Sesi gudang belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
 const mutation=useProductionMutation('FG_BOOK'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [data,setData]=useState<CorrectedFgBook|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false)
 const [filters,setFilters]=useState<Filters>(emptyFilters),[search,setSearch]=useState(''),[from,setFrom]=useState(''),[to,setTo]=useState('')
 const drag=useRef<string|null>(null)
 const [over,setOver]=useState<string|null>(null),[resetReview,setResetReview]=useState(false)
 const request=useRef({initialized:false,q:'',from:null as string|null,to:null as string|null,filters:emptyFilters(),offset:0}),sequence=useRef(0)
 const options=useCallback(async(kind:BookFilterKind,q:string,offset:number)=>{
  const r=await client.rpc('erp_cp7_get_fg_book_options_v1',{p_kind:kind,p_q:q,p_offset:offset,p_limit:25});if(r.error)throw r.error
  const v=parseFgBookOptions(r.data,kind);if(v.page.offset!==offset)throw Error('Halaman pilihan berubah. Cari ulang.');return v
 },[client])
 const load=useCallback(async()=>{
  const s=++sequence.current,ticket=beginRead();setData(null);setError('');setLoading(true);drag.current=null;setOver(null);setResetReview(false)
  try{
   if(!request.current.initialized){
    const v=await options('BRAND',bookName,0);if(s!==sequence.current||!isReadCurrent(ticket))return false
    const found=v.page.rows.filter(r=>r.label.toLowerCase()===bookName.toLowerCase()||r.code.toLowerCase()===bookName.toLowerCase())
    const initial=emptyFilters();if(found.length===1)initial.BRAND=found
    request.current.filters=initial;request.current.initialized=true;setFilters(initial)
   }
   const q=request.current
   const r=await client.rpc('erp_cp7_get_fg_book_v2',{p_query:{q:q.q,from:q.from,to:q.to,brand_ids:q.filters.BRAND.map(x=>x.id),customer_ids:q.filters.CUSTOMER.map(x=>x.id),movement_types:q.filters.TYPE.map(x=>x.id),offset:q.offset,limit:25}})
   if(s!==sequence.current||!isReadCurrent(ticket))return false;if(r.error)throw r.error
   const v=parseCorrectedFgBook(r.data);if(v.page.offset!==q.offset)throw Error('Halaman buku berubah. Muat ulang.')
   setData(v);return finishRead(ticket)
  }catch(e){if(s===sequence.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}
  finally{if(s===sequence.current)setLoading(false)}
 },[client,bookName,options,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 const handlers:ProductionMutationHandlers={
  send:e=>client.rpc('erp_cp7_save_fg_book_v1',{p_action:e.action,p_payload:e.payload,p_request:e.id}),
  validate:(v,e)=>{parseFgBookOutcome(v,e.id,e.action,e.payload)},
  retire:()=>{setData(null);drag.current=null;setOver(null);setResetReview(false)},reload:load,
 }
 const locked=loading||mutation.writerLocked,canOrder=data?.can_order===true
 const move=(source:string,target:string,placement:'BEFORE'|'AFTER')=>{
  if(!data||locked||!canOrder||source===target||![source,target].every(id=>data.page.rows.some(r=>r.id===id)))return
  void run('MOVE',{book_token:data.book_token,source_id:source,target_id:target,placement},null,handlers)
 }
 const apply=()=>{
  const start=from?cp6WibPhysicalTimeToIso(from):null,end=to?cp6WibPhysicalTimeToIso(to):null
  if(from&&!start||to&&!end||start&&end&&start>=end){setError('Periksa rentang waktu: akhir harus sesudah awal.');return}
  request.current={initialized:true,q:search.trim(),from:start,to:end,filters,offset:0};void load()
 }
 const label=(r:CorrectedFgBookRow)=>`${r.commercial_sku} · ${r.size_code}`
 return <section className="cproc cfgb"><header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · BUKU MUTASI</div><h1>Mutasi Barang Jadi · {bookName}</h1><p>Atur urutan kartu untuk memeriksa mutasi. Saldo buku mengikuti urutan ini; kartu stok tetap mengikuti waktu transaksi.</p></div><button disabled={loading||mutation.busy} onClick={()=>void load()}>Muat ulang buku</button></header>
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel"/>{error?<p className="panel" role="alert">{error}</p>:null}
  <section className="panel cfgb-filters" aria-label="Filter buku"><div className="cproc-grid"><label>Cari SKU, lot, toko, atau catatan<input aria-label="Cari buku mutasi" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)}/></label><label>Mulai · WIB<input aria-label="Awal buku WIB" type="datetime-local" value={from} onChange={e=>setFrom(e.target.value)}/></label><label>Sebelum · WIB<input aria-label="Akhir buku WIB" type="datetime-local" value={to} onChange={e=>setTo(e.target.value)}/></label></div>
   <div className="cfgb-filter-grid">{kinds.map(kind=><Filter key={kind} kind={kind} chosen={filters[kind]} disabled={loading||mutation.busy} onChange={values=>setFilters({...filters,[kind]:values})} load={options}/>)}</div><button disabled={loading||mutation.busy} className="primary-btn" onClick={apply}>Terapkan filter buku</button>
  </section>
  {loading?<p role="status">Memuat buku mutasi…</p>:null}
  {data?<><div className="cfgb-book-heading"><div><h2>Kartu mutasi</h2><small>{data.page.total} mutasi · {formatCp6WibDateTime(data.read_at)}</small></div><span>{request.current.filters.BRAND.length?request.current.filters.BRAND.map(r=>r.label).join(', '):'Semua merek'}</span></div>
   <p className="cfgb-caption">Saldo per produk fisik, ukuran, gudang, dan grade, mencakup seluruh lot serta transaksi di luar filter dan halaman ini.</p>
   {canOrder?<p className="cfgb-caption">Tarik kartu ke atas atau bawah kartu tujuan, atau gunakan tombol pindah. Urutan tersimpan untuk seluruh buku FG.</p>:null}
   {!data.page.rows.length?<div className="panel">Tidak ada mutasi yang cocok.</div>:null}
   <div className="cfgb-cards">{data.page.rows.map((r,i)=><article className={`panel cfgb-card${over===r.id?' cfgb-drop':''}`} key={r.id} data-movement-id={r.id} draggable={canOrder&&!locked}
    onDragStart={e=>{if(locked||!canOrder){e.preventDefault();return}e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',r.id);drag.current=r.id}} onDragEnd={()=>{drag.current=null;setOver(null)}}
    onDragOver={e=>{if(drag.current&&drag.current!==r.id&&canOrder&&!locked){e.preventDefault();e.dataTransfer.dropEffect='move';setOver(r.id)}}} onDragLeave={()=>setOver(null)}
    onDrop={e=>{e.preventDefault();const source=drag.current,rect=e.currentTarget.getBoundingClientRect();drag.current=null;setOver(null);if(source)move(source,r.id,e.clientY<rect.top+rect.height/2?'BEFORE':'AFTER')}}>
    <header><div><span className="cfgb-brand">{r.brand_name}</span><h3>{label(r)}</h3><p>{r.product_name}</p></div><div className="cfgb-date"><strong>{movementLabels[r.movement_type]??r.movement_type.replaceAll('_',' ')}</strong><time>{formatCp6WibDateTime(r.physical_at)}</time></div></header>
    <div className="cfgb-destination"><span>{r.customer_name??'Tanpa toko'}</span><small>{r.location_name} · {r.quality_grade.replaceAll('_',' ')}</small></div>
    <dl className="cfgb-balances">{([['book_physical_before','Awal buku'],['physical_delta','Perubahan fisik'],['book_physical_after','Akhir buku']] as const).map(([key,title])=><div key={key}><dt>{title}</dt><dd>{numberText(r[key])}<small> PCS</small></dd><span>{bookDozens(r[key])}</span></div>)}</dl>
    {r.correction_count!=='0'?<details><summary>Nota dibetulkan {r.correction_count} kali</summary><p>Jumlah asli {bookDozens(r.original_physical_delta)}. Jumlah yang berlaku {bookDozens(r.physical_delta)}.</p><p>Pembetulan terakhir dicatat {formatCp6WibDateTime(r.correction_recorded_at!)}. Saldo kartu berikutnya mengikuti jumlah yang berlaku.</p><ul>{r.audit_movements.map(m=><li key={m.id}>{m.id} · {bookDozens(m.available_delta)} · berlaku {formatCp6WibDateTime(m.physical_at)} · dicatat {formatCp6WibDateTime(m.recorded_at)}</li>)}</ul></details>:null}
    {r.reservation_delta!=='0'?<p>Perubahan cadangan {numberText(r.reservation_delta)} PCS · fisik tetap.</p>:null}{r.notes?<p className="cfgb-notes">{r.notes}</p>:null}
    <details><summary>Saldo resmi dan sumber</summary><dl className="cfgb-official"><div><dt>Fisik setelah transaksi</dt><dd>{numberText(r.official_physical_after)} PCS</dd></div><div><dt>Cadangan</dt><dd>{numberText(r.official_reserved_after)} PCS</dd></div><div><dt>Tersedia</dt><dd>{numberText(r.official_available_after)} PCS</dd></div></dl><small>Saldo resmi memakai urutan waktu transaksi. Saldo buku bisa berbeda setelah kartu dipindah.</small><p>{r.lot_number??'Tanpa lot'} · {r.source_type} · {r.source_id??'Tanpa nomor sumber'}</p>{r.reversal_of_id?<p>Pembalik transaksi {r.reversal_of_id}</p>:null}<small>Dicatat {formatCp6WibDateTime(r.recorded_at)}</small></details>
    {canOrder?<footer><span className="cfgb-grip" aria-hidden="true" title="Tarik kartu">⠿</span><button disabled={locked||i===0} aria-label={`Pindahkan ${label(r)} ke atas`} onClick={()=>move(r.id,data.page.rows[i-1].id,'BEFORE')}>↑ Pindah ke atas</button><button disabled={locked||i===data.page.rows.length-1} aria-label={`Pindahkan ${label(r)} ke bawah`} onClick={()=>move(r.id,data.page.rows[i+1].id,'AFTER')}>↓ Pindah ke bawah</button></footer>:null}
   </article>)}</div>
   <div className="panel cproc-pagination"><span>{data.page.rows.length} dari {data.page.total} mutasi</span><button disabled={loading||mutation.busy||!data.page.offset} onClick={()=>{request.current.offset=Math.max(0,data.page.offset-25);void load()}}>Buku sebelumnya</button><button disabled={loading||mutation.busy||data.page.next_offset===null} onClick={()=>{request.current.offset=data.page.next_offset??0;void load()}}>Buku berikutnya</button></div>
   {canOrder?<section className="panel cfgb-reset"><h2>Urutan seluruh buku</h2><p>Kembalikan seluruh kartu FG ke urutan waktu transaksi, termasuk kartu di luar filter ini.</p><label><input type="checkbox" checked={resetReview} disabled={locked} onChange={e=>setResetReview(e.target.checked)}/>Saya ingin mengatur ulang seluruh buku FG.</label><button disabled={locked||!resetReview} onClick={()=>void run('RESET',{book_token:data.book_token},null,handlers)}>Kembalikan seluruh urutan buku</button></section>:null}
  </>:null}
 </section>
}
function Filter({kind,chosen,disabled,onChange,load}:{kind:BookFilterKind;chosen:BookOption[];disabled:boolean;onChange:(v:BookOption[])=>void;load:(kind:BookFilterKind,q:string,offset:number)=>Promise<FgBookOptions>}){
 const [q,setQ]=useState(''),[data,setData]=useState<FgBookOptions|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),seq=useRef(0),requested=useRef('')
 useEffect(()=>()=>{++seq.current},[])
 const read=async(offset:number)=>{const n=++seq.current;setData(null);setError('');setBusy(true);try{const r=await load(kind,requested.current,offset);if(n===seq.current)setData(r)}catch(e){if(n===seq.current)setError(normalizeClientError(e).message)}finally{if(n===seq.current)setBusy(false)}}
 return <details className="cfgb-filter"><summary>{filterLabels[kind]} · {chosen.length?chosen.map(x=>x.label).join(', '):'Semua'}</summary><div><label>Cari {filterLabels[kind].toLowerCase()}<input value={q} aria-label={`Cari pilihan ${kind}`} maxLength={120} disabled={disabled||busy} onChange={e=>setQ(e.target.value)}/></label><button disabled={disabled||busy} onClick={()=>{requested.current=q.trim();void read(0)}}>Cari pilihan {filterLabels[kind].toLowerCase()}</button><button disabled={disabled||!chosen.length} onClick={()=>onChange([])}>Semua {filterLabels[kind].toLowerCase()}</button>{chosen.length?<div className="cfgb-chips">{chosen.map(x=><button key={x.id} disabled={disabled} onClick={()=>onChange(chosen.filter(v=>v.id!==x.id))}>× {x.label}</button>)}</div>:null}{error?<p role="alert">{error}</p>:null}{busy?<p role="status">Memuat pilihan…</p>:null}{data?.page.rows.map(x=><label className="cfgb-option" key={x.id}><input type="checkbox" checked={chosen.some(v=>v.id===x.id)} disabled={disabled||chosen.length>=100&&!chosen.some(v=>v.id===x.id)} onChange={e=>onChange(e.target.checked?[...chosen,x]:chosen.filter(v=>v.id!==x.id))}/>{x.label}</label>)}{data?<div className="cproc-pagination"><span>Total {data.page.total}</span><button disabled={disabled||busy||data.page.offset===0} onClick={()=>void read(Math.max(0,data.page.offset-25))}>Pilihan sebelumnya</button><button disabled={disabled||busy||data.page.next_offset===null} onClick={()=>void read(data.page.next_offset??0)}>Pilihan berikutnya</button></div>:null}</div></details>
}
