import {lazy,Suspense,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import type {NativeDemandQuery} from './nativeDemandHistory'
import {cp6WibDateTimeInput} from './cp6BusinessTime'

const NativeAnalysisPanel=lazy(()=>import('./NativeAnalysisPanel'))
const NativeBoundedQuantityPanel=lazy(()=>import('./NativeBoundedQuantityPanel'))
type Props={onSourceReadStart:()=>void;onSourceReadEnd:()=>void;disabled:boolean}
const required=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','production.cutting.view']
export default function NativeCuttingSuggestionsPanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!required.every(p=>identity.permissions.includes(p)))return null
 return<Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({onSourceReadStart,onSourceReadEnd,disabled}:Props){
 const[from,setFrom]=useState(''),[through,setThrough]=useState(''),[selection,setSelection]=useState<{query:NativeDemandQuery;view:'QUANTITY'|'ARCHIVE'}|null>(null)
 const query=selection?.query??null
 const today=cp6WibDateTimeInput().slice(0,10)
 const ready=/^\d{4}-\d\d-\d\d$/.test(from)&&/^\d{4}-\d\d-\d\d$/.test(through)&&from<=through&&through<today
 return<section className="ccut-card" aria-label="Saran potong"><h2>Saran potong</h2>
  <p>Pilih periode penjualan untuk membuka mesin rencana seluruh produk yang sama. Pilih SKU dan ukuran dengan jelas; waktu data dan alasan saran ditampilkan bersama jumlahnya.</p>
  <label>Penjualan mulai (WIB)<input aria-label="Penjualan mulai untuk saran potong" type="date" value={from} disabled={disabled||query!==null} onChange={e=>setFrom(e.target.value)}/></label>
  <label>Penjualan sampai (WIB)<input aria-label="Penjualan sampai untuk saran potong" type="date" max={today} value={through} disabled={disabled||query!==null} onChange={e=>setThrough(e.target.value)}/></label><p>Pakai hari yang sudah selesai dalam WIB.</p>
  <button type="button" disabled={disabled||!ready||query!==null} onClick={()=>setSelection({query:{from_date:from,through_date:through,group_mode:'AS_SOLD'},view:'QUANTITY'})}>Buka saran potong</button>
  <button type="button" disabled={disabled||!ready||query!==null} onClick={()=>setSelection({query:{from_date:from,through_date:through,group_mode:'AS_SOLD'},view:'ARCHIVE'})}>Buka analisis &amp; arsip saran potong</button>
  {selection?<Suspense fallback={<p role="status">Membuka rencana produksi…</p>}>{selection.view==='QUANTITY'?<NativeBoundedQuantityPanel query={selection.query} onSourceReadStart={onSourceReadStart} onSourceReadEnd={onSourceReadEnd} onClose={()=>setSelection(null)}/>:<NativeAnalysisPanel query={selection.query} cuttingSuggestion onSourceReadStart={onSourceReadStart} onSourceReadEnd={onSourceReadEnd} onClose={()=>setSelection(null)}/>}</Suspense>:null}
 </section>
}
