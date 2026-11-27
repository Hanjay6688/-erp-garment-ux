import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { WalletCards } from 'lucide-react'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { applyLaundryCredits, availableCredits, billRemaining } from './laundryCredits'
import type { LaundryBillCredit, LaundryDelivery, LaundryFinalBill } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'

export type UpdateLaundry = (update:(rows:LaundryDelivery[])=>LaundryDelivery[])=>void
export const claimMoney = (cents:number) => amountText(cents/100)
const creditDay=(claim:ReturnType<typeof availableCredits>[number]['claim'])=>claim.resolution?.day??claim.approvedOn??''
const cents=(value:string|undefined)=>value?.trim()?Math.round(readRupiahInput(value)*100):0

export function LaundryClaimCreditDialog({deliveries,delivery,bill,update,onClose}:{
  deliveries:LaundryDelivery[];delivery:LaundryDelivery;bill:LaundryFinalBill;update:UpdateLaundry;onClose:()=>void
}) {
  const sources=availableCredits(deliveries,delivery.vendor).sort((a,b)=>creditDay(a.claim).localeCompare(creditDay(b.claim)))
  const [amounts,setAmounts]=useState<Record<string,string>>({})
  const [day,setDay]=useState(lastWarehouseDay)
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  const [id]=useState(()=>crypto.randomUUID())
  const remaining=billRemaining(deliveries,delivery,bill)
  const choices=sources.map(source=>({...source,cents:cents(amounts[source.claim.id])}))
  const selected=choices.filter(row=>row.cents>0)
  const total=selected.reduce((sum,row)=>sum+row.cents,0)
  const valid=Number.isSafeInteger(total)&&total>0&&total<=remaining
    &&choices.every(row=>Number.isSafeInteger(row.cents)&&row.cents>=0&&row.cents<=row.remaining)
  const minDay=[bill.day,bill.corrections?.at(-1)?.day??'',...selected.map(row=>creditDay(row.claim))].sort().at(-1)

  function fillMaximum() {
    const result:Record<string,string>={}
    let left=remaining
    for(const source of sources) {
      const amount=Math.min(left,source.remaining)
      if(amount>0)result[source.claim.id]=String(amount/100).replace('.',',')
      left-=amount
    }
    setAmounts(result);setError('')
  }
  return <ReasonDialog title="Potong invoice Laundry" closeLabel="Kembali" onClose={onClose} className="demo-operation-dialog money-dialog" icon={<WalletCards/>}>
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      const credits:LaundryBillCredit[]=selected.map(row=>({
        id:id+':'+row.claim.id,claim:row.claim.id,cents:row.cents,day,reason:reason.trim(),
      }))
      try {
        if(!valid)throw Error('Periksa nominal setiap kredit dan sisa invoice.')
        const next=applyLaundryCredits(deliveries,delivery.id,bill.number,credits)
        update(rows=>{
          if(rows===deliveries)return next
          try{return applyLaundryCredits(rows,delivery.id,bill.number,credits)}
          catch{return rows}
        })
        onClose()
      } catch(failure) {setError((failure as Error).message)}
    }}>
      <p><strong>{bill.number}</strong> · {delivery.vendor}</p>
      <div className="demo-ops-header"><div><strong>Kredit tersedia</strong><small>Pilih nominal dari satu atau beberapa klaim.</small></div>
        <button type="button" className="soft-btn" onClick={fillMaximum} disabled={!sources.length||!remaining}>Isi potongan maksimum</button>
      </div>
      <div className="invoice-credit-list">
        {choices.map((row,index)=><article className="invoice-source-card" key={row.claim.id}>
          <div><strong>{row.claim.qty} pcs · {row.claim.type}</strong><small>{row.delivery.id} · {creditDay(row.claim)} · Sisa {claimMoney(row.remaining)}</small>
            <span>{row.claim.reason}</span></div>
          <label>Nominal potongan kredit {index+1} (Rp)<NumberEntry rupiahDraft inputMode="decimal" value={amounts[row.claim.id]??''}
            placeholder="0" onValueChange={rawInput =>{setAmounts(current=>({...current,[row.claim.id]:rawInput}));setError('')}}/></label>
        </article>)}
        {!choices.length&&<p className="invoice-list-empty">Belum ada kredit siap dipakai.</p>}
      </div>
      <div className="demo-operation-fields">
        <label>Tanggal potongan<input required type="date" min={minDay} max={lastWarehouseDay()} value={day} onChange={event=>setDay(event.target.value)}/></label>
        <label>Alasan potongan<input required minLength={4} maxLength={500} value={reason} onChange={event=>setReason(event.target.value)}/></label>
      </div>
      <div className="demo-operation-facts">
        <article><span>Total potongan</span><strong>{claimMoney(total)}</strong></article>
        <article><span>Sisa invoice setelah potongan</span><strong>{valid?claimMoney(remaining-total):claimMoney(remaining)}</strong></article>
      </div>
      {error&&<p role="alert">{error}</p>}
      <footer><button className="primary-btn" disabled={!valid}>Simpan potongan invoice</button></footer>
    </form>
  </ReasonDialog>
}
