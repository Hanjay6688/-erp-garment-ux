import NumberEntry from '../../../src/components/NumberEntry'
import { useEffect, useState } from 'react'
import { ArrowRight, Check, Plus, ReceiptText, Waves, X } from 'lucide-react'
import { PayableInvoiceDesk, useInvoiceWork, type DeskList } from './PayableInvoiceDesk'
import { browseMatchPieces } from '../browseMatch'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { readRupiahInput } from '../moneyInput'
import { dayOk, lastWarehouseDay } from './warehouseDay'
import { billGross } from './laundryCredits'
import { laundryContractKey, laundryPhysicalTime, laundryProcesses, unbilledLaundryPieces, type LaundryBillPart, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import type { UpdateLaundry } from './LaundryClaimCreditDialog'
import { invoiceForLaundryContract, laundryContracts, laundryContractsPath, quoteLaundryInvoice, saveLaundryInvoice, type LaundryInvoiceDraft } from './laundryVendorInvoices'

type DraftLine=Omit<LaundryBillPart,'qty'|'rate'>&{qty:string;rate:string}
type Draft={number:string;day:string;lines:DraftLine[]}
const keyOf=(vendor:string)=>'erp.demo.laundry-bill-draft.v1:'+vendor

function groupedBill(rows:LaundryDelivery[],vendor:string,draft:Draft):LaundryFinalBill {
  const number=draft.number.trim()
  if(!number||!dayOk(draft.day)||!draft.lines.length||rows.some(row=>row.vendor===vendor&&row.finalBills?.some(bill=>bill.kind!=='INVOICE'&&bill.number.toLowerCase()===number.toLowerCase()))){
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
  const bill={kind:'CONTRABON' as const,number,day:draft.day,parts,process:'Beberapa penerimaan',rate:0,qty:parts.reduce((sum,part)=>sum+part.qty,0)}
  if(!Number.isSafeInteger(billGross(bill)))throw Error('Periksa total tagihan.')
  return bill
}

export function LaundryContractComposer({vendor,deliveries,update,onClose,onSaved}:{
  vendor:string;deliveries:LaundryDelivery[];update:UpdateLaundry;onClose:()=>void;onSaved:(number:string)=>void
}) {
  const [draft,setDraft]=useState<Draft>(()=>JSON.parse(sessionStorage.getItem(keyOf(vendor))??'null')??{number:'',day:lastWarehouseDay(),lines:[]})
  const [error,setError]=useState('')
  const [review,setReview]=useState<LaundryFinalBill|null>(null)
  const receipts=deliveries.filter(row=>row.vendor===vendor&&unbilledLaundryPieces(deliveries,row)>0)
  const available=receipts.filter(row=>!draft.lines.some(line=>line.delivery===row.id))
  const change=(value:Partial<Draft>)=>{setDraft({...draft,...value});setError('');setReview(null)}
  const edit=(delivery:string,values:Partial<DraftLine>)=>change({lines:draft.lines.map(line=>line.delivery===delivery?{...line,...values}:line)})
  return <ReasonDialog title="Buat kontrabon Laundry" closeLabel="Kembali" onClose={onClose} className="demo-operation-dialog money-dialog invoice-composer" icon={<ReceiptText/>}>
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      try{setReview(groupedBill(deliveries,vendor,draft));setError('')}
      catch(failure){setError((failure as Error).message)}
    }}>
      <div className="invoice-composer-body">
        <div className="demo-operation-fields invoice-composer-meta">
          <div className="invoice-composer-vendor"><span>Laundry</span><strong><Waves aria-hidden="true"/> {vendor}</strong></div>
          <label>Nomor kontrabon<input required value={draft.number} onChange={event=>change({number:event.target.value})}/></label>
          <label>Tanggal kontrabon<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>change({day:event.target.value})}/></label></div>
        <div className="invoice-composer-columns">
          <section className="invoice-composer-pane" aria-label="Penerimaan siap ditagih">
            <div className="demo-operation-heading"><i><ReceiptText aria-hidden="true"/></i><div><h3>Siap ditagih</h3><p>Penerimaan milik {vendor}</p></div></div>
            <div className="invoice-composer-list">
              {available.map(row=><article className="invoice-source-card" key={row.id}><header className="demo-ops-header">
                <div><strong>{unbilledLaundryPieces(deliveries,row)} pcs</strong><span>{row.model}</span><small>{row.id}</small></div>
                <button type="button" className="soft-btn invoice-add" aria-label={'Tambah '+row.id} onClick={()=>change({lines:[...draft.lines,{delivery:row.id,qty:String(unbilledLaundryPieces(deliveries,row)),process:row.process,rate:''}]})}><Plus aria-hidden="true"/> Tambah</button>
              </header></article>)}
              {!available.length&&<p className="invoice-list-empty">{receipts.length?'Semua penerimaan tersedia sudah dipilih.':'Belum ada penerimaan siap ditagih.'}</p>}
            </div>
          </section>
          <section className="invoice-composer-pane invoice-composer-selected" aria-label="Penerimaan di kontrabon ini">
            <div className="demo-operation-heading"><i><Check aria-hidden="true"/></i><div><h3>Di kontrabon ini</h3><p aria-live="polite">{draft.lines.length} penerimaan dipilih</p></div></div>
            <div className="invoice-composer-list">
              {!draft.lines.length&&<p className="invoice-list-empty">Klik Tambah pada penerimaan yang masuk kontrabon ini.</p>}
              {draft.lines.map(line=>{
                const source=receipts.find(row=>row.id===line.delivery)
                return <article className="invoice-source-card" key={line.delivery}>
                  <header className="demo-ops-header"><div><strong>{source?unbilledLaundryPieces(deliveries,source)+' pcs tersedia':'Sumber perlu diperiksa'}</strong><span>{source?.model}</span><small>{line.delivery}</small></div>
                    <button type="button" className="soft-btn invoice-remove" aria-label={'Lepas '+line.delivery} onClick={()=>change({lines:draft.lines.filter(row=>row!==line)})}><X aria-hidden="true"/> Lepas</button></header>
                  <div className="demo-operation-fields">
                    <label>Qty ditagih (pcs)<NumberEntry inputMode="numeric" required value={line.qty} onValueChange={rawInput =>edit(line.delivery,{qty:rawInput.replace(/\D/g,'').slice(0,9)})}/></label>
                    <label>Harga aktual (Rp/pcs)<NumberEntry rupiahDraft inputMode="decimal" required value={line.rate} onValueChange={rawInput =>edit(line.delivery,{rate:rawInput})}/></label>
                    <label className="invoice-line-service">Jenis layanan<select required value={line.process} onChange={event=>edit(line.delivery,{process:event.target.value})}><option value="">Pilih layanan</option>{laundryProcesses.map(service=><option key={service}>{service}</option>)}</select></label>
                  </div>
                </article>
              })}
            </div>
          </section>
        </div>
        {error&&<p role="alert">{error}</p>}
      </div>
      <footer className="invoice-composer-footer">
        {review&&<div className="invoice-review-total" role="status"><span>Satu kontrabon untuk {review.parts?.length} penerimaan</span><strong>{amountText(billGross(review)/100)}</strong><small>{review.qty} pcs · {review.number}</small></div>}
        <div className="invoice-composer-actions"><button className="soft-btn" type="button" onClick={()=>{sessionStorage.setItem(keyOf(vendor),JSON.stringify(draft));onClose()}}>Simpan draf</button>
          {review?<button className="primary-btn" type="button" onClick={()=>{
            update(rows=>{
              try { const bill=groupedBill(rows,vendor,draft);return rows.map(row=>row.id===bill.parts?.[0].delivery?{...row,finalBills:[...(row.finalBills??[]),bill]}:row) }
              catch {return rows}
            })
            sessionStorage.removeItem(keyOf(vendor));onSaved(review.number);onClose()
          }}><Check aria-hidden="true"/> Simpan kontrabon</button>:<button className="primary-btn" disabled={!draft.lines.length}>Review kontrabon <ArrowRight aria-hidden="true"/></button>}</div>
      </footer>
    </form>
  </ReasonDialog>
}

export function LaundryVendorInvoiceComposer({deliveries,vendor,previous,update,onSaved,...desk}:DeskList & {
  deliveries:LaundryDelivery[];vendor:string;previous?:LaundryFinalBill;update:UpdateLaundry;onSaved:(invoice:LaundryFinalBill)=>void
}) {
  const work=useInvoiceWork<LaundryInvoiceDraft>(['LAUNDRY',vendor,previous?.invoiceId??'new'],previous,()=>({
    id:previous?.invoiceId??crypto.randomUUID(),vendor,number:previous?.number??'',day:previous?.day??lastWarehouseDay(),contracts:previous?.contracts??[],
  }))
  const draft=work.value
  const [query,setQuery]=useState('')
  const [review,setReview]=useState<LaundryFinalBill|null>(null)
  const [error,setError]=useState('')
  const [pending,setPending]=useState<LaundryFinalBill|null>(null)
  const hasDelivery=deliveries.some(row=>row.vendor===vendor)
  useEffect(()=>{
    if(!pending)return
    setPending(null);setReview(null)
    if(deliveries.some(row=>row.finalBills?.includes(pending))) {
      work.clear();setError('');onSaved(pending)
    } else setError('Data laundry berubah. Periksa lagi kontrabon sebelum menyimpan invoice.')
  },[deliveries,pending,onSaved,work])
  const chosen=new Set(draft.contracts.map(laundryContractKey))
  const own=laundryContracts(deliveries,vendor)
  const available=own.filter(row=>!chosen.has(laundryContractKey(row.ref))&&!invoiceForLaundryContract(deliveries,row.ref,draft.id))
  const shown=available.filter(({bill,delivery})=>browseMatchPieces(query,[bill.qty],bill.number,bill.day,delivery.model,billGross(bill)/100))
  const total=own.filter(row=>chosen.has(laundryContractKey(row.ref))).reduce((sum,row)=>sum+billGross(row.bill),0)/100
  function change(patch:Partial<LaundryInvoiceDraft>) {work.change({...draft,...patch});setError('');setReview(null)}
  function save(status:'DRAFT'|'POSTED') {
    try {
      const next=saveLaundryInvoice(deliveries,draft,status)
      const invoice=next.flatMap(row=>row.finalBills??[]).find(bill=>bill.invoiceId===draft.id)!
      update(current=>current===deliveries?next:current)
      setPending(invoice)
    } catch(failure) {setError((failure as Error).message);setReview(null)}
  }
  return <PayableInvoiceDesk {...desk} party={vendor} editing={previous?.invoiceId} sourceName="kontrabon" sourceCount={available.length} chosen={draft.contracts.length}
    query={query} onSearch={setQuery} total={total} error={error} onReview={event=>{
      event.preventDefault()
      try{setReview(quoteLaundryInvoice(deliveries,draft,'POSTED'));setError('')}
      catch(failure){setError((failure as Error).message)}
    }} sources={<>
      {shown.map(({bill,ref})=><article className="invoice-source-card" key={laundryContractKey(ref)}><header className="demo-ops-header">
        <div><strong>{bill.qty} pcs</strong><span>{bill.number}</span><small>{bill.day} · {amountText(billGross(bill)/100)}</small></div>
        <button className="soft-btn invoice-add" type="button" aria-label={'Tambah '+bill.number} onClick={()=>change({contracts:[...draft.contracts,ref]})}><Plus size={15}/> Tambah</button>
      </header></article>)}
      {!shown.length&&<p className="invoice-list-empty">{query?'Tidak ada kontrabon yang cocok.':'Belum ada kontrabon tersedia untuk laundry ini.'}</p>}
    </>} sourceAction={<a className="soft-btn ap-source-action" href={laundryContractsPath(vendor)}>Buka Klaim &amp; Kontrabon <ArrowRight size={16}/></a>}
    meta={<><label>Nomor invoice Laundry<input required maxLength={90} value={draft.number} onChange={event=>change({number:event.target.value})}/></label>
      <label>Tanggal invoice<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>change({day:event.target.value})}/></label></>}
    lines={<>{!draft.contracts.length&&<p className="invoice-list-empty">{hasDelivery?'Pilih kontrabon dengan tombol Tambah.':'Catat penerimaan laundry ini sebelum menyimpan draf invoice.'}</p>}
      {draft.contracts.map(ref=>{
        const bill=own.find(row=>laundryContractKey(row.ref)===laundryContractKey(ref))?.bill
        return <article className="invoice-source-card" key={laundryContractKey(ref)}><header className="demo-ops-header">
          <div><strong>{bill?bill.qty+' pcs':'Periksa kontrabon'}</strong><span>{ref.number}</span>{bill&&<small>{amountText(billGross(bill)/100)}</small>}</div>
          <button className="soft-btn invoice-remove" type="button" aria-label={'Lepas '+ref.number} onClick={()=>change({contracts:draft.contracts.filter(row=>row!==ref)})}><X size={15}/> Lepas</button>
        </header></article>
      })}
    </>} review={review&&<span>{review.qty} pcs · {review.contracts?.length} kontrabon siap diposting</span>}
    actions={<><button className="soft-btn" type="button" disabled={!!pending||!hasDelivery} onClick={()=>save('DRAFT')}>Simpan draf</button>
      {review?<button className="primary-btn" type="button" disabled={!!pending} onClick={()=>save('POSTED')}><Check size={16}/> Posting satu invoice</button>
        :<button className="primary-btn" disabled={!draft.contracts.length}>Review invoice <ArrowRight size={16}/></button>}</>}/>
}
