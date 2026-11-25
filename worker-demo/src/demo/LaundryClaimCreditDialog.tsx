import { useState } from 'react'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { applyLaundryCredit, availableCredits, billRemaining, validCredit } from './laundryCredits'
import type { LaundryBillCredit, LaundryDelivery, LaundryFinalBill } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'

export type UpdateLaundry = (update:(rows: LaundryDelivery[])=>LaundryDelivery[])=>void
export type LaundryBillTarget = {delivery: LaundryDelivery; bill: LaundryFinalBill}
export const claimMoney = (cents:number) => amountText(cents/100)
export function openLaundryBills(rows:LaundryDelivery[],vendor:string) {
  return rows.filter(row=>row.vendor===vendor).flatMap(delivery=>(delivery.finalBills??[])
    .map(bill=>({delivery,bill,remaining:billRemaining(rows,delivery,bill)})))
    .filter(row=>row.remaining>0).sort((left,right)=>left.bill.day.localeCompare(right.bill.day)||left.bill.number.localeCompare(right.bill.number))
}

export function LaundryClaimCreditDialog({deliveries,vendor,claimId,target,update,onClose}:{
  deliveries:LaundryDelivery[];vendor:string;claimId?:string;target?:LaundryBillTarget;update:UpdateLaundry;onClose:()=>void
}) {
  const sources=availableCredits(deliveries,vendor)
  const bills=openLaundryBills(deliveries,vendor)
  const [sourceId,setSourceId]=useState(claimId??sources[0]?.claim.id??'')
  const [targetKey,setTargetKey]=useState('')
  const [amount,setAmount]=useState('')
  const [day,setDay]=useState(lastWarehouseDay)
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  const [id]=useState(()=>crypto.randomUUID())
  const source=sources.find(row=>row.claim.id===sourceId)
  const keyOf=(row:LaundryBillTarget)=>JSON.stringify([row.delivery.id,row.bill.number])
  const billTarget=target??bills.find(row=>keyOf(row)===targetKey)
  const remaining=billTarget?billRemaining(deliveries,billTarget.delivery,billTarget.bill):0
  const limit=Math.min(remaining,source?.remaining??0)
  const cents=Math.round(readRupiahInput(amount)*100)
  const minDay=[billTarget?.bill.day,billTarget?.bill.corrections?.at(-1)?.day,source?.claim.resolution?.day??source?.claim.approvedOn]
    .filter((date):date is string=>!!date).sort().at(-1)
  return <ReasonDialog title="Potong tagihan laundry" closeLabel="Kembali" onClose={onClose} className="demo-operation-dialog">
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      const credit:LaundryBillCredit={id,claim:sourceId,cents,day,reason:reason.trim()}
      if(!billTarget||!validCredit(deliveries,billTarget.delivery,billTarget.bill,credit)){
        setError('Periksa tanggal, bukti potongan, saldo kredit, dan sisa tagihan.');return
      }
      update(rows=>applyLaundryCredit(rows,billTarget.delivery.id,billTarget.bill.number,credit))
      onClose()
    }}>
      <p>{vendor}{target?' · '+target.bill.number:''}</p>
      {claimId&&source?<div className="laundry-credit-source"><strong>{source.claim.qty} pcs · {claimMoney(source.remaining)} kredit</strong><small>{source.delivery.id} · {source.claim.reason}</small></div>
        :<label>Sumber kredit<select required value={sourceId} onChange={event=>{setSourceId(event.target.value);setAmount('');setError('')}}>
          {sources.map(row=><option key={row.claim.id} value={row.claim.id}>{row.claim.type} · {row.claim.qty} pcs · {row.delivery.id} · {claimMoney(row.remaining)}</option>)}
        </select></label>}
      {!target&&<label>Tagihan tujuan<select required value={targetKey} onChange={event=>{setTargetKey(event.target.value);setAmount('');setError('')}}>
        <option value="">Pilih kontrabon vendor ini</option>{bills.map(row=><option key={keyOf(row)} value={keyOf(row)}>{row.bill.number} · {row.bill.day} · sisa {claimMoney(row.remaining)}</option>)}
      </select></label>}
      <div className="demo-operation-fields">
        <label>Nominal potongan (Rp)<input required inputMode="decimal" value={amount} onChange={event=>{setAmount(event.target.value);setError('')}}/>
          {limit>0&&<small>Batas {claimMoney(limit)}</small>}</label>
        <label>Tanggal potongan<input required type="date" min={minDay} max={lastWarehouseDay()} value={day} onChange={event=>setDay(event.target.value)}/></label>
      </div>
      {limit>0&&<div><button type="button" className="soft-btn" onClick={()=>setAmount(String(limit/100).replace('.',','))}>Isi potongan maksimum</button></div>}
      <label>Alasan potongan<textarea required minLength={4} maxLength={500} value={reason} onChange={event=>setReason(event.target.value)}/></label>
      {billTarget&&<div className="demo-operation-facts"><article><span>Sisa kontrabon sekarang</span><strong>{claimMoney(remaining)}</strong></article>
        <article><span>Sisa sesudah potongan</span><strong>{cents>0&&cents<=limit?claimMoney(remaining-cents):'—'}</strong></article></div>}
      {error&&<p role="alert">{error}</p>}
      <footer><button className="primary-btn" disabled={!limit||!Number.isSafeInteger(cents)||cents<=0||cents>limit}>Simpan potongan tagihan</button></footer>
    </form>
  </ReasonDialog>
}
