import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseSalesFormOptions,salesQtyInput,salesMoneyInput,salesLineTotal,type SalesRead,type SalesFormOptions,type SalesCustomerOption,type SalesStockOption} from './salesReadContract'
import type {Json} from './types/database.preconnect'
import {dozensText,seriesTotal,splitSeriesDozens} from './sales/seriesDozens'
type Detail=NonNullable<SalesRead['detail']>
type Line={key:string;product_id:string;sku:string;series:string;size:string;qty:string;price:string;discount:string;notes:string|null;dozens:string;pieces:string;available:string|null}
type SeriesInput={dozens:string;pieces:string;message:string}
// Owner D14-5: one series is every size line of one commercial SKU, in the order it was first added. Picking any size
// adds every size of that SKU in stock at the warehouse (as the UX demo adds a product with all its sizes), and a new
// series starts at 1 lusin split evenly when it divides (one size: 12 PCS; three sizes: 4/4/4).
// A series is one brand's commercial SKU: the same SKU number is lawful for Vivo and Widie (bf_skus_v1 UNIQUE(brand_id,
// sku)), so the key carries the server's brand name too (erp.brands.brand_name is UNIQUE) (Astra ASTRA-C17-01).
const seriesKey=(brand:string,sku:string)=>`${sku} · ${brand}`
const seriesGroups=(lines:Line[])=>{const groups=new Map<string,{line:Line;index:number}[]>();lines.forEach((line,index)=>groups.set(line.series,[...(groups.get(line.series)??[]),{line,index}]));return [...groups.entries()]}
type Form={customer:SalesCustomerOption|null;location:{id:string;name:string}|null;number:string;at:string;originalAt:string|null;due:string;terms:string;notes:string;reason:string;lines:Line[]}
type Kind='CUSTOMER'|'STOCK'
export default function SalesDraftPanel({initial,locked,stale,onSave,onClose,correction=false}:{initial:Detail|null;locked:boolean;stale:boolean;correction?:boolean;onSave:(action:'CREATE'|'EDIT',document:Json,version:string|null)=>void;onClose:()=>void}){
 const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw Error('Sesi penjualan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
 const [form,setForm]=useState<Form>(()=>({customer:initial?{id:initial.customer_id,code:'',name:initial.customer_name}:null,location:initial?.location_id?{id:initial.location_id,name:initial.location_name??''}:null,number:initial?.number??'',at:cp6WibDateTimeInput(initial?.physical_at),originalAt:initial?.physical_at??null,due:initial?.due_date??'',terms:initial?.payment_terms??'',notes:initial?.notes??'',reason:'',lines:initial?.items.map(i=>({key:i.id,product_id:i.product_id,sku:i.product_sku,series:seriesKey(i.brand_name,i.commercial_sku),size:i.size_code,qty:i.qty_pcs,price:i.financial?.unit_price??'',discount:i.financial?.discount??'',notes:i.notes,dozens:'',pieces:'',available:null}))??[]}))
 const [seriesInput,setSeriesInput]=useState<Record<string,SeriesInput>>({})
 const [reviewed,setReviewed]=useState(false),[options,setOptions]=useState<Partial<Record<Kind,SalesFormOptions>>>({}),[query,setQuery]=useState({CUSTOMER:'',STOCK:''}),[loading,setLoading]=useState({CUSTOMER:false,STOCK:false}),[error,setError]=useState('')
 const sequences=useRef({CUSTOMER:0,STOCK:0}),queryUsed=useRef({CUSTOMER:'',STOCK:''}),seriesSeq=useRef(0),formRef=useRef(form);formRef.current=form
 const [seriesBusy,setSeriesBusy]=useState('')
 const at=form.originalAt&&form.at===cp6WibDateTimeInput(form.originalAt)?form.originalAt:cp6WibPhysicalTimeToIso(form.at),location=form.location?.id??null
 useEffect(()=>{sequences.current.CUSTOMER++;sequences.current.STOCK++;seriesSeq.current++;setOptions({});setLoading({CUSTOMER:false,STOCK:false});setSeriesBusy('');setError('');return()=>{sequences.current.CUSTOMER++;sequences.current.STOCK++;seriesSeq.current++}},[at,location,client])
 const update=(patch:Partial<Form>)=>{setForm(f=>({...f,...patch}));setReviewed(false)}
 const editLine=(key:string,patch:Partial<Line>)=>{setForm(f=>({...f,lines:f.lines.map(l=>l.key===key?{...l,...patch}:l)}));setReviewed(false)}
 const editSeries=(series:string,patch:Partial<SeriesInput>)=>setSeriesInput(v=>({...v,[series]:{...(v[series]??{dozens:'',pieces:'',message:''}),...patch}}))
 function splitSeries(series:string,sizes:number){const input=seriesInput[series]??{dozens:'',pieces:'',message:''},r=splitSeriesDozens(input.dozens,input.pieces,sizes)
  if(!r.ok){editSeries(series,{message:r.message});return}
  setForm(f=>({...f,lines:f.lines.map(l=>l.series===series?{...l,qty:r.perSize}:l)}));setReviewed(false);editSeries(series,{message:''})}
 async function addSeries(p:SalesStockOption){
  // While the sizes load the review is void and nothing can be saved (Astra ASTRA-C17-02).
  if(!at)return;const s=++seriesSeq.current,series=seriesKey(p.brand_name,p.commercial_sku),loc=p.location_id,found:SalesStockOption[]=[];setSeriesBusy(series);setReviewed(false);setError('')
  try{
   let offset:number|null=0
   for(let page=0;offset!==null&&page<10;page++){const r=await client.rpc('erp_cp7_get_sales_form_v1',{p_query:{kind:'STOCK',q:p.commercial_sku,physical_at:at,location_id:loc,offset,limit:100}});if(s!==seriesSeq.current)return;if(r.error)throw r.error;const o=parseSalesFormOptions(r.data,'STOCK',at,loc);if(o.offset!==offset||o.limit!==100)throw Error('Pilihan sumber berubah. Cari ulang sumber invoice.');found.push(...(o.rows as SalesStockOption[]).filter(x=>x.commercial_sku===p.commercial_sku&&x.brand_name===p.brand_name));offset=o.next_offset}
   if(offset!==null)throw Error(`Ukuran seri ${series} belum terbaca semua. Cari dengan SKU yang lebih tepat.`)
   if(!found.some(x=>x.product_id===p.product_id))found.push(p)
   const current=formRef.current,have=new Set(current.lines.map(l=>l.product_id)),fresh=found.filter(x=>!have.has(x.product_id)),started=current.lines.some(l=>l.series===series)
   if(!fresh.length){editSeries(series,{message:`Semua ukuran seri ${series} yang ada stoknya sudah ada di invoice.`});return}
   if(current.lines.length+fresh.length>100)throw Error('Satu invoice paling banyak 100 baris barang.')
   const split=started?null:splitSeriesDozens('1','',fresh.length),qty=split?.ok?split.perSize:''
   setForm(f=>({...f,location:{id:p.location_id,name:p.location_name},lines:[...f.lines,...fresh.map(x=>({key:crypto.randomUUID(),product_id:x.product_id,sku:x.product_sku,series,size:x.size_code,qty,price:'',discount:'0',notes:null,dozens:'',pieces:'',available:x.available_qty}))]}));setReviewed(false)
   if(split)editSeries(series,split.ok?{dozens:'1',pieces:'',message:''}:{dozens:'',pieces:'',message:split.message})
  }catch(e){if(s===seriesSeq.current)setError(normalizeClientError(e).message)}finally{if(s===seriesSeq.current)setSeriesBusy('')}
 }
 async function search(kind:Kind,offset=0,continued=false){
  if(!at)return;const s=++sequences.current[kind],q=continued?queryUsed.current[kind]:query[kind].trim(),loc=kind==='STOCK'?location:null;queryUsed.current[kind]=q
  setLoading(v=>({...v,[kind]:true}));setOptions(v=>({...v,[kind]:undefined}));setError('')
  try{const r=await client.rpc('erp_cp7_get_sales_form_v1',{p_query:{kind,q,physical_at:at,location_id:loc,offset,limit:25}});if(s!==sequences.current[kind])return;if(r.error)throw r.error;const o=parseSalesFormOptions(r.data,kind,at,loc);if(o.offset!==offset||o.limit!==25)throw Error('Pilihan sumber berubah. Cari ulang sumber invoice.');setOptions(v=>({...v,[kind]:o}))}catch(e){if(s===sequences.current[kind])setError(normalizeClientError(e).message)}finally{if(s===sequences.current[kind])setLoading(v=>({...v,[kind]:false}))}
 }
 const amounts=form.lines.map(l=>salesLineTotal(l.qty,l.price,l.discount)),valid=!!at&&!!form.customer&&!!form.location&&form.number.trim().length>0&&form.reason.trim().length>=5&&form.lines.length>0&&form.lines.length<=100&&amounts.every(a=>a!==null)&&!seriesBusy
 const total=form.lines.length>0&&amounts.every(a=>a!==null)?amounts.reduce((n,a)=>n+BigInt(a!.replace('.','')),0n):null
 const blocked=locked||stale
 function save(){
  if(!valid||blocked||!reviewed)return
  onSave(initial?'EDIT':'CREATE',{...(initial?{sale_id:initial.id,review_token:initial.review_token!}:{}),...(correction&&initial?{item_lineage:form.lines.map(l=>initial.items.some(i=>i.id===l.key)?l.key:null)}:{}),sale_number:form.number.trim(),customer_id:form.customer!.id,source_location_id:form.location!.id,sale_date:at!,due_date:form.due||null,payment_terms:form.terms||null,notes:form.notes||null,change_reason:form.reason.trim(),items:form.lines.map(l=>({product_id:l.product_id,qty_pcs:salesQtyInput(l.qty)!,unit_price_snapshot:salesMoneyInput(l.price)!,discount_amount:salesMoneyInput(l.discount)!,notes:l.notes}))},initial?.row_version??null)
 }
 const picker=(kind:Kind)=>{const candidate=options[kind],o=candidate&&at&&Date.parse(candidate.physical_at)===Date.parse(at)&&candidate.location_id===(kind==='STOCK'?location:null)?candidate:undefined;return <section className="cproc-line" aria-label={kind==='CUSTOMER'?'Pilih pelanggan invoice':'Pilih barang invoice'}>
  <div className="cproc-inline"><label>{kind==='CUSTOMER'?'Cari pelanggan':'Cari SKU, ukuran, atau gudang'}<input aria-label={kind==='CUSTOMER'?'Cari pelanggan draft':'Cari barang draft'} value={query[kind]} maxLength={120} onChange={e=>setQuery(v=>({...v,[kind]:e.target.value}))} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();void search(kind)}}}/></label><button type="button" disabled={loading[kind]||!at} onClick={()=>void search(kind)}>{kind==='CUSTOMER'?'Cari pelanggan draft':'Cari barang draft'}</button></div>
  {loading[kind]?<p role="status">Memuat pilihan…</p>:null}{o?.rows.length===0?<p>Tidak ada sumber sesuai pencarian.</p>:null}
  {kind==='STOCK'?<p>Memilih satu ukuran menambahkan semua ukuran seri itu yang ada stoknya di gudang ini. Seri baru langsung diisi 1 lusin dibagi rata bila pas; jumlah per ukuran tetap bisa diubah.</p>:null}{kind==='STOCK'&&seriesBusy?<p role="status">Memuat semua ukuran seri {seriesBusy}…</p>:null}
  {o?.rows.map(row=>{if(kind==='CUSTOMER'){const c=row as SalesCustomerOption;return <button className="cproc-receipt" type="button" key={c.id} aria-pressed={form.customer?.id===c.id} onClick={()=>update({customer:c})}><strong>{c.code} · {c.name}</strong></button>}
   const p=row as SalesStockOption;return <button className="cproc-receipt" type="button" key={`${p.product_id}/${p.location_id}`} disabled={form.lines.length>=100||!!seriesBusy||!!form.location&&form.location.id!==p.location_id} onClick={()=>void addSeries(p)}><span><strong>{p.commercial_sku} · {p.size_code}</strong><small>{p.product_name} · {p.brand_name} · {p.location_name}</small></span><span>{numberText(p.available_qty)} PCS tersedia sekarang</span></button>})}
  {o?<div className="cproc-pagination"><span>Total {o.total}</span><button type="button" disabled={loading[kind]||o.offset===0} onClick={()=>void search(kind,Math.max(0,o.offset-25),true)}>Sumber sebelumnya</button><button type="button" disabled={loading[kind]||o.next_offset===null} onClick={()=>void search(kind,o.next_offset??0,true)}>Sumber berikutnya</button></div>:null}
 </section>}
 return <form className="panel" aria-label={correction?'Benerin nota':'Draft invoice'} onSubmit={e=>{e.preventDefault();save()}}>
  <div className="cproc-heading"><h2>{correction?'Benerin nota':initial?'Edit draft invoice':'Buat draft invoice'}</h2><button type="button" disabled={locked} onClick={onClose}>Tutup formulir invoice</button></div>
  {correction?<p>Isi jumlah dan nilai yang benar. Nota asal tetap tersimpan; pembetulan berlaku pada waktu kejadian asal dan memperbarui saldo setelahnya. Pembayaran dan retur yang masih sah dipertahankan. Jika pemeriksaan stok atau keuangan gagal, seluruh pembetulan batal.</p>:null}
  {stale?<p role="alert">Dokumen berubah. Tutup formulir, muat ulang, lalu periksa versi terbaru.</p>:null}{error?<p role="alert">{error}</p>:null}
  <fieldset disabled={blocked}><div className="cproc-grid"><label>Nomor invoice<input aria-label="Nomor draft invoice" readOnly={correction} required maxLength={60} value={form.number} onChange={e=>update({number:e.target.value})}/></label><label>Waktu invoice · WIB<input type="datetime-local" aria-label="Waktu draft invoice WIB" readOnly={correction} required value={form.at} onChange={e=>update({at:e.target.value})}/></label><label>Jatuh tempo<input type="date" aria-label="Jatuh tempo draft invoice" value={form.due} onChange={e=>update({due:e.target.value})}/></label><label>Syarat pembayaran<input aria-label="Syarat pembayaran draft" maxLength={100} value={form.terms} onChange={e=>update({terms:e.target.value})}/></label></div>
   {!correction?picker('CUSTOMER'):null}<p>Pelanggan terpilih: <strong>{form.customer?.name??'Belum dipilih'}</strong></p>
   {picker('STOCK')}<p>Gudang invoice: <strong>{form.location?.name??'Pilih barang untuk menentukan gudang'}</strong>. Stok tersedia saat ini menjadi referensi; penyimpanan memeriksa stok pada tanggal transaksi.</p>
   {seriesGroups(form.lines).map(([series,members])=>{const lines=members.map(m=>m.line),total=seriesTotal(lines.map(l=>l.qty)),input=seriesInput[series]??{dozens:'',pieces:'',message:''};return <section className="cproc-line cproc-series" key={series} aria-label={`Seri ${series}`}>
    <h3>Seri {series} · {lines.length} ukuran ({lines.map(l=>l.size).join('/')})</h3>
    <p className="cproc-series-total">{total===null?'Isi jumlah semua ukuran untuk melihat total lusin seri ini.':`Total seri: ${dozensText(total)} (${total} PCS)`}</p>
    {/* As in the UX demo: the sizes of one series side by side, PCS per size with the stock under it. */}
    <div className="cproc-size-grid">{members.map(({line:l,index:i})=>{const over=l.available!==null&&salesQtyInput(l.qty)&&BigInt(l.qty.trim())>BigInt(l.available);return <article className={over?'cproc-size-cell over':'cproc-size-cell'} key={l.key}>
     <span className="cproc-sr">{l.sku} · </span><label><span>Ukuran {l.size}</span><input aria-label={`Jumlah invoice ${i+1}`} inputMode="numeric" value={l.qty} onFocus={e=>e.currentTarget.select()} onChange={e=>editLine(l.key,{qty:e.target.value})}/></label>
     {l.available!==null?<small>stok {numberText(l.available)} PCS{over?' · melebihi stok':''}</small>:null}
    </article>})}</div>
    <div className="cproc-inline cproc-series-dozens"><label>Lusin seri<input aria-label={`Lusin seri ${series}`} inputMode="numeric" value={input.dozens} onChange={e=>editSeries(series,{dozens:e.target.value,message:''})} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();splitSeries(series,lines.length)}}}/></label><label>Sisa potong seri<input aria-label={`Sisa potong seri ${series}`} inputMode="numeric" value={input.pieces} onChange={e=>editSeries(series,{pieces:e.target.value,message:''})}/></label><button type="button" onClick={()=>splitSeries(series,lines.length)}>Bagi rata ke {lines.length} ukuran seri {series}</button></div>
    {input.message?<p role="alert">{input.message}</p>:null}
    <div className="cproc-size-prices"><div className="cproc-size-prices-head" aria-hidden="true"><span>Ukuran</span><span>Harga per PCS</span><span>Potongan baris</span><span className="cproc-wide-only">Catatan barang</span></div>{members.map(({line:l,index:i})=><div className="cproc-size-price" key={l.key}>
     <strong>{l.size}</strong><input aria-label={`Harga invoice ${i+1}`} placeholder="Harga per PCS" inputMode="decimal" value={l.price} onChange={e=>editLine(l.key,{price:e.target.value})}/><input aria-label={`Potongan invoice ${i+1}`} placeholder="Potongan" inputMode="decimal" value={l.discount} onChange={e=>editLine(l.key,{discount:e.target.value})}/>
     <input className="cproc-size-note" aria-label={`Catatan barang invoice ${i+1}`} placeholder="Catatan barang (boleh kosong)" maxLength={4000} value={l.notes??''} onChange={e=>editLine(l.key,{notes:e.target.value||null})}/>
     <span className="cproc-size-amount">Jumlah baris {amounts[i]===null?'belum valid':`Rp${numberText(amounts[i]!)}`}</span><button type="button" onClick={()=>{const lines=form.lines.filter(x=>x.key!==l.key);update({lines,location:lines.length||correction?form.location:null})}}>Hapus barang {i+1}</button>
    </div>)}</div>
    <details><summary>Isi dengan lusin + PCS</summary>{members.map(({line:l,index:i})=><div className="cproc-inline" key={l.key}><strong>{l.size}</strong><label>Lusin<input aria-label={`Lusin invoice ${i+1}`} inputMode="numeric" value={l.dozens} onChange={e=>editLine(l.key,{dozens:e.target.value})}/></label><label>Sisa PCS<input aria-label={`Sisa PCS invoice ${i+1}`} inputMode="numeric" value={l.pieces} onChange={e=>editLine(l.key,{pieces:e.target.value})}/></label><button type="button" disabled={!/^[0-9]{1,7}$/.test(l.dozens)||!/^[0-9]{1,2}$/.test(l.pieces)||Number(l.pieces)>11||BigInt(l.dozens||0)*12n+BigInt(l.pieces||0)===0n} onClick={()=>editLine(l.key,{qty:String(BigInt(l.dozens)*12n+BigInt(l.pieces))})}>Terapkan lusin baris {i+1}</button></div>)}</details>
   </section>})}
   <label>Catatan invoice<input aria-label="Catatan draft invoice" maxLength={4000} value={form.notes} onChange={e=>update({notes:e.target.value})}/></label><label>Alasan penyimpanan<input aria-label="Alasan simpan invoice" required minLength={5} maxLength={1000} value={form.reason} onChange={e=>update({reason:e.target.value})}/></label>
   <div className="cproc-total"><span>{correction?'Nilai nota setelah dibetulkan':'Nilai draft'}</span><strong>{total===null?'Belum lengkap':`Rp${numberText(`${total/100n}.${String(total%100n).padStart(2,'0')}`)}`}</strong><p>{correction?'Pembetulan memperbarui nota, stok, piutang dan HPP bersama. Periode keuangan yang ditutup tetap dilindungi.':'Menyimpan draft memesan stok siap jual. Piutang belum dibukukan sampai invoice disahkan.'}</p></div>
   <label className="cproc-check"><input type="checkbox" aria-label={correction?'Pembetulan nota sudah diperiksa':'Draft invoice sudah diperiksa'} checked={reviewed} disabled={!!seriesBusy} onChange={e=>setReviewed(e.target.checked)}/>Pelanggan, tanggal, jumlah, harga, dan potongan sudah saya periksa.</label><button className="primary-btn" disabled={!valid||!reviewed}>{correction?'Simpan pembetulan nota':'Simpan draft invoice'}</button>
  </fieldset>
 </form>
}
