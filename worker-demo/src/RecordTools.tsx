import {useId,useRef,useState,type FormEventHandler,type ReactNode} from 'react'
import {ArrowDownUp,FolderSearch,ListFilter,Search} from 'lucide-react'
import './record-tools.css'

export type RecordPageOrder='SOURCE'|'LABEL_ASC'|'LABEL_DESC'

/** Only orders the supplied page; official balances and server pagination stay attached to each record.
 * Screens whose reader orders the whole matching list (OW-09) pass orderScope="ALL_MATCHING" and do not call this. */
export function orderRecordPage<T>(rows:readonly T[]|undefined,order:RecordPageOrder,label:(row:T)=>string):T[]{
 const page=[...(rows??[])]
 if(order==='SOURCE')return page
 const collator=new Intl.Collator('id',{numeric:true,sensitivity:'base'})
 return page.sort((a,b)=>(order==='LABEL_DESC'?-1:1)*collator.compare(label(a),label(b)))
}

type Scope='ALL_MATCHING'|'PAGE'
const scopeText:Record<`${Scope}:${Scope}`,string>={
 'PAGE:PAGE':'Filter dan urutan hanya mengatur halaman yang sedang tampil.',
 'ALL_MATCHING:PAGE':'Urutan hanya mengatur halaman yang sedang tampil.',
 'PAGE:ALL_MATCHING':'Filter hanya mengatur halaman yang sedang tampil; urutan berlaku untuk seluruh hasil.',
 'ALL_MATCHING:ALL_MATCHING':'Filter dan urutan berlaku untuk seluruh hasil, termasuk halaman lain; jumlah hasil mengikuti filter yang sama.',
}
type Props={title:string;busy:boolean;submitDisabled?:boolean;browseLabel?:string;search:ReactNode;filters?:ReactNode;filterScope?:Scope;searchScope?:Scope;orderScope?:Scope;submitLabel:string;
 onSubmit:FormEventHandler<HTMLFormElement>;onBrowse:()=>void;
 order:RecordPageOrder;onOrder:(value:RecordPageOrder)=>void}

export default function RecordTools({title,busy,submitDisabled=false,browseLabel='Browse semua',search,filters,filterScope='ALL_MATCHING',searchScope='ALL_MATCHING',orderScope='PAGE',submitLabel,onSubmit,onBrowse,order,onOrder}:Props){
 const id=useId(),form=useRef<HTMLFormElement>(null),[showFilters,setShowFilters]=useState(true),whole=orderScope==='ALL_MATCHING'
 return <form ref={form} className="panel cproc-search record-tools" aria-label={`Cari, browse, urutkan dan filter ${title}`} onSubmit={onSubmit}>
  <header className="record-tools-heading"><h2>Telusuri {title}</h2><div className="record-tools-buttons">
   <button type="button" disabled={busy} onClick={()=>form.current?.querySelector<HTMLInputElement>('input:not([type=checkbox]):not([type=radio])')?.focus()}><Search aria-hidden="true"/>Cari</button>
   <button type="button" disabled={busy} onClick={onBrowse}><FolderSearch aria-hidden="true"/>{browseLabel}</button>
   {filters?<button type="button" disabled={busy} aria-expanded={showFilters} aria-controls={`${id}-filters`} onClick={()=>setShowFilters(v=>!v)}><ListFilter aria-hidden="true"/>Filter</button>:null}
   <label className="record-tools-order"><ArrowDownUp aria-hidden="true"/><span>{whole?'Urutkan semua hasil':'Urutkan halaman ini'}</span><select aria-label={whole?`Urutkan ${title}`:`Urutkan halaman ${title}`} value={order} disabled={busy} onChange={e=>onOrder(e.target.value as RecordPageOrder)}>
    <option value="SOURCE">Urutan standar</option><option value="LABEL_ASC">Nama / nomor A–Z</option><option value="LABEL_DESC">Nama / nomor Z–A</option>
   </select></label>
  </div></header>
  <div className="record-tools-fields">{search}{filters?<div id={`${id}-filters`} className="record-tools-filters" hidden={!showFilters}>{filters}</div>:null}<button disabled={busy||submitDisabled} className="primary-btn" type="submit">{submitLabel}</button></div>
  <small>{searchScope==='PAGE'?'Pencarian hanya menelusuri halaman yang sedang tampil.':'Pencarian menelusuri daftar yang berhak Anda lihat.'} {scopeText[`${filterScope}:${orderScope}`]}</small>
 </form>
}
