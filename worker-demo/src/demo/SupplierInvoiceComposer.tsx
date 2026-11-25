import { useState } from 'react'
import { Check, FilePlus2, Plus, ReceiptText, Search, X } from 'lucide-react'
import { browseMatchPieces } from '../browseMatch'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { kasbonSources, quoteSupplierInvoice, saveSupplierInvoice, supplierDateLabel, supplierInvoiceAmount, supplierSourceRemaining, type SupplierGroup, type SupplierInvoice, type SupplierInvoiceDraft } from './supplierInvoices'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

export function SupplierInvoiceComposer({group,rows,previous,onClose,onSave}:{
  group:SupplierGroup;rows:SupplierInvoice[];previous?:SupplierInvoice;onClose:()=>void;onSave:(saved:ReturnType<typeof saveSupplierInvoice>)=>void
}) {
  const sources=kasbonSources().filter(row=>row.group===group)
  const suppliers=[...new Set(sources.map(row=>row.supplier))]
  const [draft,setDraft]=useState<SupplierInvoiceDraft>(()=>previous?{...previous,
    lines:previous.lines.map(line=>({sourceId:line.source.id,qty:String(line.qty).replace('.',','),rate:String(line.rate).replace('.',',')}))}
    :{id:crypto.randomUUID(),number:'',day:lastWarehouseDay(),supplier:suppliers[0]??'',group,lines:[]})
  const [query,setQuery]=useState('')
  const [review,setReview]=useState<SupplierInvoice|null>(null)
  const [error,setError]=useState('')
  const remaining=sources.filter(row=>row.supplier===draft.supplier).map(source=>({source,qty:supplierSourceRemaining(rows,source,draft.id)}))
  const available=remaining.filter(({source,qty})=>qty>0&&!draft.lines.some(line=>line.sourceId===source.id)&&browseMatchPieces(query,source.unit==='pcs'?[qty]:[],source.name,source.number,source.day))
  const change=(patch:Partial<SupplierInvoiceDraft>)=>{setDraft({...draft,...patch});setReview(null);setError('')}
  function save(status:SupplierInvoice['status']) {
    try{onSave(saveSupplierInvoice(draft,status))}
    catch(failure){setError((failure as Error).message);setReview(null)}
  }
  return <ReasonDialog title={previous?'Edit draf invoice supplier':'Susun invoice supplier'} closeLabel="Kembali" className="demo-operation-dialog" onClose={onClose}>
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      try{setReview(quoteSupplierInvoice(draft,'POSTED'));setError('')}
      catch(failure){setError((failure as Error).message)}
    }}>
      <div className="demo-operation-fields"><label>Supplier<select required disabled={!!previous} value={draft.supplier} onChange={event=>change({supplier:event.target.value,lines:[]})}>
        {suppliers.map(supplier=><option key={supplier}>{supplier}</option>)}</select></label>
        <label>Nomor invoice supplier<input required maxLength={90} value={draft.number} onChange={event=>change({number:event.target.value})}/></label>
        <label>Tanggal invoice<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>change({day:event.target.value})}/></label></div>
      <div className="demo-ops-columns">
        <section className="demo-ops-card" aria-label="Kasbon tersedia"><div className="demo-operation-heading"><i><ReceiptText/></i><div><h3>Kasbon tersedia</h3><p>Pilih dari penerimaan supplier ini.</p></div></div>
          <label className="supplier-draft-search"><Search size={16}/><input type="search" aria-label="Cari kasbon" placeholder="Nomor, bahan, atau pcs…" value={query} onChange={event=>setQuery(event.target.value)}/></label>
          {available.map(({source,qty})=><article className="laundry-money-source" key={source.id}>
            <div className="demo-ops-header"><div><strong>{qty.toLocaleString('id-ID')} {source.unit}</strong><small>{source.name} · {source.number}</small><small>{supplierDateLabel(source.day)}</small></div>
              <button className="soft-btn" type="button" aria-label={'Tambah '+source.number} onClick={()=>change({lines:[...draft.lines,{sourceId:source.id,qty:String(qty).replace('.',','),rate:String(source.rate).replace('.',',')}]})}><Plus size={16}/> Tambah</button></div>
          </article>)}
          {!available.length&&<p>Tidak ada kasbon tersedia untuk pilihan ini.</p>}
        </section>
        <section className="demo-ops-card supplier-draft-selected" aria-label="Kasbon di invoice ini"><div className="demo-operation-heading"><i><Check/></i><div><h3>Di invoice ini</h3><p>{draft.lines.length} kasbon dipilih</p></div></div>
          {!draft.lines.length&&<p>Kasbon yang dipilih akan muncul di sini.</p>}
          {draft.lines.map(line=>{
            const source=remaining.find(row=>row.source.id===line.sourceId)
            const edit=(patch:Partial<typeof line>)=>change({lines:draft.lines.map(row=>row===line?{...row,...patch}:row)})
            return <article className="laundry-money-source" key={line.sourceId}>
              <div className="demo-ops-header"><div><strong>{source?.source.name??'Periksa sumber kasbon'}</strong><small>{source?.source.number??line.sourceId}</small></div>
                <button className="soft-btn" type="button" aria-label={'Lepas '+source?.source.number} onClick={()=>change({lines:draft.lines.filter(row=>row!==line)})}><X size={16}/> Lepas</button></div>
              <div className="demo-operation-fields"><label>Jumlah ditagih ({source?.source.unit??'unit'})<input required inputMode="decimal" value={line.qty} onChange={event=>edit({qty:event.target.value})}/>
                {source&&<small>Tersedia {source.qty.toLocaleString('id-ID')} {source.source.unit}</small>}</label>
                <label>Harga aktual (Rp per unit)<input required inputMode="decimal" value={line.rate} onChange={event=>edit({rate:event.target.value})}/><small>Cocokkan harga dengan invoice supplier.</small></label></div>
            </article>
          })}
        </section>
      </div>
      {review&&<div className="demo-operation-facts"><article><span>Total satu invoice</span><strong>{amountText(supplierInvoiceAmount(review))}</strong><small>{review.number} · {review.lines.length} kasbon</small></article></div>}
      {error&&<p role="alert">{error}</p>}
      <footer><button className="soft-btn" type="button" onClick={()=>save('DRAFT')}>Simpan draf</button>
        {review?<button className="primary-btn" type="button" onClick={()=>save('POSTED')}><Check size={16}/> Posting satu invoice</button>
          :<button className="primary-btn" disabled={!draft.lines.length}><FilePlus2 size={16}/> Review invoice</button>}</footer>
    </form>
  </ReasonDialog>
}
