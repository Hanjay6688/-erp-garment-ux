import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { ArrowRight, Check, Plus, X } from 'lucide-react'
import { browseMatchPieces } from '../browseMatch'
import { readRupiahInput } from '../moneyInput'
import { PayableInvoiceDesk, useInvoiceWork, type DeskList } from './PayableInvoiceDesk'
import { kasbonSources, quoteSupplierInvoice, saveSupplierInvoice, supplierDateLabel, supplierSourceRemaining, type SupplierGroup, type SupplierInvoice, type SupplierInvoiceDraft } from './supplierInvoices'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

export function SupplierInvoiceComposer({group,party,rows,previous,onSave,...desk}:DeskList & {
  group:SupplierGroup;party:string;rows:SupplierInvoice[];previous?:SupplierInvoice;onSave:(saved:ReturnType<typeof saveSupplierInvoice>)=>void
}) {
  const work=useInvoiceWork<SupplierInvoiceDraft>([group,party,previous?.id??'new'],previous,()=>previous?{...previous,
    lines:previous.lines.map(line=>({sourceId:line.source.id,qty:String(line.qty).replace('.',','),rate:String(line.rate).replace('.',',')}))}
    :{id:crypto.randomUUID(),number:'',day:lastWarehouseDay(),supplier:party,group,lines:[]})
  const draft=work.value
  const [query,setQuery]=useState('')
  const [review,setReview]=useState<SupplierInvoice|null>(null)
  const [error,setError]=useState('')
  const remaining=kasbonSources().filter(row=>row.group===group&&row.supplier===party)
    .map(source=>({source,qty:supplierSourceRemaining(rows,source,draft.id)}))
  const available=remaining.filter(({source,qty})=>qty>0&&!draft.lines.some(line=>line.sourceId===source.id))
  const shown=available.filter(({source,qty})=>browseMatchPieces(query,source.unit==='pcs'?[qty]:[],source.name,source.number,source.day,qty,source.unit))
  const total=draft.lines.reduce((sum,line)=>{
    const cents=Math.round(Number(line.qty.replace(',','.'))*readRupiahInput(line.rate)*100)
    return sum+(Number.isSafeInteger(cents)?cents:0)
  },0)/100
  function change(patch:Partial<SupplierInvoiceDraft>) {work.change({...draft,...patch});setReview(null);setError('')}
  function save(status:SupplierInvoice['status']) {
    try {const saved=saveSupplierInvoice(draft,status);work.clear();setReview(null);setError('');onSave(saved)}
    catch(failure){setError((failure as Error).message);setReview(null)}
  }
  return <PayableInvoiceDesk {...desk} party={party} editing={previous?.id} sourceName="kontrabon" sourceCount={available.length} chosen={draft.lines.length}
    query={query} onSearch={setQuery} total={total} error={error} onReview={event=>{
      event.preventDefault()
      try{setReview(quoteSupplierInvoice(draft,'POSTED'));setError('')}
      catch(failure){setError((failure as Error).message)}
    }} sources={<>
      {shown.map(({source,qty})=><article className="invoice-source-card" key={source.id}><header className="demo-ops-header">
        <div><strong>{qty.toLocaleString('id-ID')} {source.unit}</strong><span>{source.name}</span><small>{source.number} · {supplierDateLabel(source.day)}</small></div>
        <button className="soft-btn invoice-add" type="button" aria-label={'Tambah '+source.number} onClick={()=>change({lines:[...draft.lines,{sourceId:source.id,qty:String(qty).replace('.',','),rate:String(source.rate).replace('.',',')}]})}><Plus size={15}/> Tambah</button>
      </header></article>)}
      {!shown.length&&<p className="invoice-list-empty">{query?'Tidak ada kontrabon yang cocok.':'Semua sumber yang tersedia sudah dipilih atau masuk invoice.'}</p>}
    </>} meta={<>
      <label>Nomor invoice supplier<input required maxLength={90} value={draft.number} onChange={event=>change({number:event.target.value})}/></label>
      <label>Tanggal invoice<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>change({day:event.target.value})}/></label>
    </>} lines={<>
      {!draft.lines.length&&<p className="invoice-list-empty">Pilih kontrabon dengan tombol Tambah.</p>}
      {draft.lines.map(line=>{
        const source=remaining.find(row=>row.source.id===line.sourceId)
        const edit=(patch:Partial<typeof line>)=>change({lines:draft.lines.map(row=>row===line?{...row,...patch}:row)})
        return <article className="invoice-source-card" key={line.sourceId}><header className="demo-ops-header">
          <div><strong>{source?.source.name??'Periksa sumber kontrabon'}</strong><small>{source?.source.number??line.sourceId}</small></div>
          <button className="soft-btn invoice-remove" type="button" aria-label={'Lepas '+(source?.source.number??line.sourceId)} onClick={()=>change({lines:draft.lines.filter(row=>row!==line)})}><X size={15}/> Lepas</button></header>
          <div className="demo-operation-fields"><label>Jumlah ditagih ({source?.source.unit??'unit'})<NumberEntry required inputMode="decimal" value={line.qty} onValueChange={rawInput =>edit({qty:rawInput})}/>
            {source&&<small>Tersedia {source.qty.toLocaleString('id-ID')} {source.source.unit}</small>}</label>
            <label>Harga aktual (Rp per unit)<NumberEntry rupiahDraft required inputMode="decimal" value={line.rate} onValueChange={rawInput =>edit({rate:rawInput})}/></label></div>
        </article>
      })}
    </>} review={review&&<span>{review.number} · {review.lines.length} kasbon siap diposting</span>}
    actions={<><button className="soft-btn" type="button" onClick={()=>save('DRAFT')}>Simpan draf</button>
      {review?<button className="primary-btn" type="button" onClick={()=>save('POSTED')}><Check size={16}/> Posting satu invoice</button>
        :<button className="primary-btn" disabled={!draft.lines.length}>Review invoice <ArrowRight size={16}/></button>}</>}/>
}
