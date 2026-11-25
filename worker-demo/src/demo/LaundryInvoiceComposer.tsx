import { useState } from 'react'
import { Check, Plus, ReceiptText, X } from 'lucide-react'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { readRupiahInput } from '../moneyInput'
import { dayOk, lastWarehouseDay } from './warehouseDay'
import { billGross } from './laundryCredits'
import { laundryPhysicalTime, laundryProcesses, unbilledLaundryPieces, type LaundryBillPart, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import type { UpdateLaundry } from './LaundryClaimCreditDialog'

type DraftLine=Omit<LaundryBillPart,'qty'|'rate'>&{qty:string;rate:string}
type Draft={number:string;day:string;lines:DraftLine[]}
const keyOf=(vendor:string)=>'erp.demo.laundry-bill-draft.v1:'+vendor

function groupedBill(rows:LaundryDelivery[],vendor:string,draft:Draft):LaundryFinalBill {
  const number=draft.number.trim()
  if(!number||!dayOk(draft.day)||!draft.lines.length||rows.some(row=>row.vendor===vendor&&row.finalBills?.some(bill=>bill.number.toLowerCase()===number.toLowerCase()))){
    throw Error('Isi nomor kontrabon yang belum dipakai, tanggal, dan setidaknya satu penerimaan.')
  }
  const parts=draft.lines.map(line=>{
    const delivery=rows.find(row=>row.id===line.delivery&&row.vendor===vendor)
    const qty=Number(line.qty),rate=readRupiahInput(line.rate)
    const earliest=delivery?[laundryPhysicalTime(delivery.sentAt).slice(0,10),...(delivery.returns??[]).map(row=>row.at.slice(0,10))].sort().at(-1)??'':''
    if(!delivery||!Number.isSafeInteger(qty)||qty<=0||qty>unbilledLaundryPieces(rows,delivery)||draft.day<earliest
      ||!laundryProcesses.includes(line.process)||!Number.isSafeInteger(Math.round(qty*rate*100)))throw Error('Periksa jumlah, tanggal, jenis layanan, dan tarif aktual pada tiap penerimaan.')
    return {...line,qty,rate}
  })
  if(new Set(parts.map(line=>line.delivery)).size!==parts.length)throw Error('Penerimaan yang sama cukup dipilih satu kali.')
  const bill={number,day:draft.day,parts,process:'Beberapa penerimaan',rate:0,qty:parts.reduce((sum,part)=>sum+part.qty,0)}
  if(!Number.isSafeInteger(billGross(bill)))throw Error('Periksa total tagihan.')
  return bill
}

export function LaundryInvoiceComposer({vendor,deliveries,update,onClose,onSaved}:{
  vendor:string;deliveries:LaundryDelivery[];update:UpdateLaundry;onClose:()=>void;onSaved:(number:string)=>void
}) {
  const [draft,setDraft]=useState<Draft>(()=>JSON.parse(sessionStorage.getItem(keyOf(vendor))??'null')??{number:'',day:lastWarehouseDay(),lines:[]})
  const [error,setError]=useState('')
  const [review,setReview]=useState<LaundryFinalBill|null>(null)
  const available=deliveries.filter(row=>row.vendor===vendor&&unbilledLaundryPieces(deliveries,row)>0)
  const change=(value:Partial<Draft>)=>{setDraft({...draft,...value});setError('');setReview(null)}
  const edit=(delivery:string,values:Partial<DraftLine>)=>change({lines:draft.lines.map(line=>line.delivery===delivery?{...line,...values}:line)})
  return <ReasonDialog title="Susun satu kontrabon laundry" closeLabel="Kembali" onClose={onClose} className="demo-operation-dialog">
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      try{setReview(groupedBill(deliveries,vendor,draft));setError('')}
      catch(failure){setError((failure as Error).message)}
    }}>
      <p>{vendor} · pilih penerimaan yang tercantum di kontrabon ini.</p>
      <div className="demo-operation-fields"><label>Nomor kontrabon<input required value={draft.number} onChange={event=>change({number:event.target.value})}/></label>
        <label>Tanggal kontrabon<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>change({day:event.target.value})}/></label></div>
      <div className="demo-ops-columns">
        <section className="demo-ops-card"><div className="demo-operation-heading"><i><ReceiptText/></i><div><h3>Siap ditagih</h3></div></div>
          {available.filter(row=>!draft.lines.some(line=>line.delivery===row.id)).map(row=><div className="demo-ops-header" key={row.id}>
            <div><strong>{unbilledLaundryPieces(deliveries,row)} pcs</strong><small>{row.model} · {row.id}</small></div>
            <button type="button" className="soft-btn" aria-label={'Tambah '+row.id} onClick={()=>change({lines:[...draft.lines,{delivery:row.id,qty:String(unbilledLaundryPieces(deliveries,row)),process:row.process,rate:''}]})}><Plus size={16}/> Tambah</button>
          </div>)}
          {available.every(row=>draft.lines.some(line=>line.delivery===row.id))&&<p>Semua penerimaan tersedia sudah dipilih.</p>}
        </section>
        <section className="demo-ops-card"><div className="demo-operation-heading"><i><Check/></i><div><h3>Di kontrabon ini</h3><p>{draft.lines.length} penerimaan dipilih</p></div></div>
          {draft.lines.map(line=>{
            const source=available.find(row=>row.id===line.delivery)
            return <article className="laundry-money-source" key={line.delivery}>
              <div className="demo-ops-header"><div><strong>{source?unbilledLaundryPieces(deliveries,source)+' pcs tersedia':'Sumber perlu diperiksa'}</strong><small>{line.delivery} · {source?.model}</small></div>
                <button type="button" className="soft-btn" aria-label={'Lepas '+line.delivery} onClick={()=>change({lines:draft.lines.filter(row=>row!==line)})}><X size={16}/> Lepas</button></div>
              <div className="demo-operation-fields"><label>Qty ditagih (pcs)<input inputMode="numeric" required value={line.qty} onChange={event=>edit(line.delivery,{qty:event.target.value.replace(/\D/g,'').slice(0,9)})}/></label>
                <label>Jenis layanan<select required value={line.process} onChange={event=>edit(line.delivery,{process:event.target.value})}><option value="">Pilih layanan</option>{laundryProcesses.map(service=><option key={service}>{service}</option>)}</select></label>
                <label>Harga aktual (Rp/pcs)<input inputMode="decimal" required value={line.rate} onChange={event=>edit(line.delivery,{rate:event.target.value})}/></label></div>
            </article>
          })}
        </section>
      </div>
      {review&&<div className="demo-operation-facts"><article><span>Satu kontrabon untuk {review.parts?.length} penerimaan</span><strong>{amountText(billGross(review)/100)}</strong><small>{review.qty} pcs · {review.number}</small></article></div>}
      {error&&<p role="alert">{error}</p>}
      <footer><button className="soft-btn" type="button" onClick={()=>{sessionStorage.setItem(keyOf(vendor),JSON.stringify(draft));onClose()}}>Simpan draf</button>
        {review?<button className="primary-btn" type="button" onClick={()=>{
          update(rows=>{
            try { const bill=groupedBill(rows,vendor,draft);return rows.map(row=>row.id===bill.parts?.[0].delivery?{...row,finalBills:[...(row.finalBills??[]),bill]}:row) }
            catch {return rows}
          })
          sessionStorage.removeItem(keyOf(vendor));onSaved(review.number);onClose()
        }}>Posting kontrabon</button>:<button className="primary-btn" disabled={!draft.lines.length}>Review satu kontrabon</button>}</footer>
    </form>
  </ReasonDialog>
}
