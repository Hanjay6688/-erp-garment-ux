import { useState, type FormEvent } from 'react'
import { ReceiptText, ShieldCheck } from 'lucide-react'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { availableCredits, billCredit, billGross, claimUse, eligibleClaimPieces, validClaim, validCredit } from './laundryCredits'
import type { LaundryBillCredit, LaundryClaim, LaundryDelivery, LaundryFinalBill } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

type UpdateLaundry = (update:(rows: LaundryDelivery[])=>LaundryDelivery[])=>void
const money = (cents:number) => amountText(cents/100)
const kind = (type: LaundryClaim['type']) => type==='BS' ? 'BS karena laundry' : 'Stuck di laundry'

export function LaundryClaims({delivery,deliveries,update}:{delivery:LaundryDelivery;deliveries:LaundryDelivery[];update:UpdateLaundry}) {
  const [draft,setDraft]=useState<{id:string;type:LaundryClaim['type'];qty:string;amount:string;reason:string;day:string}|null>(null)
  const [undo,setUndo]=useState<LaundryClaim|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [error,setError]=useState('')
  const claims=delivery.claims??[]
  const bs=eligibleClaimPieces(delivery,'BS')
  const stuck=eligibleClaimPieces(delivery,'STUCK')
  const canStart=bs>0||stuck>0
  if(!claims.length&&!canStart)return null

  function create(event:FormEvent) {
    event.preventDefault()
    if(!draft)return
    const claim:LaundryClaim={id:draft.id,type:draft.type,qty:/^[1-9]\d{0,8}$/.test(draft.qty)?Number(draft.qty):NaN,
      cents:Math.round(readRupiahInput(draft.amount)*100),day:draft.day,reason:draft.reason.trim()}
    if(!validClaim(delivery,claim)){setError('Periksa jumlah pcs, nilai kompensasi, tanggal, dan alasan klaim.');return}
    update(rows=>rows.map(row=>row.id===delivery.id&&validClaim(row,claim)&&!row.claims?.some(current=>current.id===claim.id)
      ? {...row,claims:[...(row.claims??[]),claim]} : row))
    setDraft(null)
  }
  function approve(claim:LaundryClaim) {
    update(rows=>rows.map(row=>row.id===delivery.id ? {...row,claims:row.claims?.map(current=>current.id===claim.id&&!current.reversed&&!current.approvedOn
      ? {...current,approvedOn:lastWarehouseDay()} : current)} : row))
  }
  function reverse() {
    if(!undo||undoReason.trim().length<4)return
    update(rows=>claimUse(rows,undo.id)>0?rows:rows.map(row=>row.id===delivery.id ? {...row,claims:row.claims?.map(claim=>claim.id===undo.id
      ? {...claim,reversed:undoReason.trim()} : claim)} : row))
    setUndo(null)
  }

  return <section className="laundry-claim-box" aria-label="Klaim laundry">
    <div className="demo-operation-heading"><i><ShieldCheck aria-hidden="true"/></i><div><h3>Klaim laundry</h3>
      <p>Klaim yang disetujui menjadi kredit untuk tagihan vendor ini.</p></div></div>
    {canStart&&<button className="soft-btn" type="button" onClick={()=>{setError('');setDraft({id:crypto.randomUUID(),type:bs>0?'BS':'STUCK',qty:'',amount:'',reason:'',day:lastWarehouseDay()})}}>Buat klaim BS / Stuck</button>}
    {claims.length>0&&<details className="demo-operation-history" open>
      <summary>Riwayat klaim ({claims.length})</summary>
      {claims.map(claim=>{
        const used=claimUse(deliveries,claim.id)
        return <article key={claim.id}>
          <strong>{claim.qty} pcs · {kind(claim.type)}</strong>
          <span>{money(claim.cents)} · {claim.reversed?'Dibalik':claim.approvedOn?'Disetujui':'Menunggu persetujuan'}</span>
          {claim.approvedOn&&!claim.reversed&&<small>Sisa kredit {money(claim.cents-used)}</small>}
          <small>{claim.reversed||claim.reason}</small>
          {!claim.reversed&&<div className="demo-operation-actions">
            {!claim.approvedOn&&<button type="button" className="soft-btn" onClick={()=>approve(claim)}>Setujui klaim {claim.type}</button>}
            {!used&&<button type="button" className="soft-btn" onClick={()=>{setUndo(claim);setUndoReason('')}}>Balikkan klaim</button>}
          </div>}
        </article>
      })}
    </details>}
    {draft&&<ReasonDialog title="Buat klaim laundry" closeLabel="Kembali" onClose={()=>setDraft(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={create}>
        <p>{delivery.vendor} · {delivery.id}</p>
        <label>Jenis klaim<select value={draft.type} onChange={event=>{setError('');setDraft({...draft,type:event.target.value==='BS'?'BS':'STUCK',qty:''})}}>
          {bs>0&&<option value="BS">BS karena laundry</option>}{stuck>0&&<option value="STUCK">Stuck di laundry</option>}
        </select></label>
        <div className="demo-operation-fields">
          <label>Jumlah diklaim (pcs)<input required inputMode="numeric" value={draft.qty} onChange={event=>setDraft({...draft,qty:event.target.value})}/>
            <small>Tersedia {eligibleClaimPieces(delivery,draft.type)} pcs</small></label>
          <label>Nilai kompensasi (Rp)<input required inputMode="decimal" placeholder="Contoh 15.000" value={draft.amount} onChange={event=>setDraft({...draft,amount:event.target.value})}/></label>
        </div>
        <label>Tanggal klaim<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>setDraft({...draft,day:event.target.value})}/></label>
        <label>Alasan dan kesepakatan dengan laundry<textarea required value={draft.reason} maxLength={500} onChange={event=>setDraft({...draft,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Simpan klaim</button></footer>
      </form>
    </ReasonDialog>}
    {undo&&<ReasonDialog title="Balikkan klaim laundry" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog">
      <div className="demo-operation-form"><label>Alasan pembalikan<textarea value={undoReason} onChange={event=>setUndoReason(event.target.value)}/></label>
        <footer><button className="primary-btn" disabled={undoReason.trim().length<4} onClick={reverse}>Simpan pembalikan</button></footer></div>
    </ReasonDialog>}
  </section>
}

export function LaundryBillCard({delivery,bill,deliveries,update}:{delivery:LaundryDelivery;bill:LaundryFinalBill;deliveries:LaundryDelivery[];update:UpdateLaundry}) {
  const [form,setForm]=useState<{id:string;claim:string;amount:string;day:string;reason:string}|null>(null)
  const [undo,setUndo]=useState<LaundryBillCredit|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [error,setError]=useState('')
  const remaining=billGross(bill)-billCredit(bill)
  const credits=availableCredits(deliveries,delivery.vendor)
  const selected=credits.find(row=>row.claim.id===form?.claim)
  function updateBill(rows:LaundryDelivery[], next:(live: LaundryFinalBill)=>LaundryFinalBill) {
    return rows.map(row=>row.id!==delivery.id?row:{...row,finalBills:row.finalBills?.map(live=>live.number===bill.number?next(live):live)})
  }
  function save(event:FormEvent) {
    event.preventDefault()
    if(!form)return
    const credit:LaundryBillCredit={id:form.id,claim:form.claim,cents:Math.round(readRupiahInput(form.amount)*100),day:form.day,reason:form.reason.trim()}
    if(!validCredit(deliveries,delivery,bill,credit)){setError('Periksa tanggal, alasan, saldo kredit, dan sisa tagihan.');return}
    update(rows=>updateBill(rows,live=>validCredit(rows,delivery,live,credit)&&!live.credits?.some(row=>row.id===credit.id)
      ? {...live,credits:[...(live.credits??[]),credit]} : live))
    setForm(null)
  }
  return <section className="laundry-bill-card" aria-label={'Kontrabon '+bill.number}>
    <div className="laundry-final-bill"><ReceiptText size={17} aria-hidden="true"/><span><strong>Kontrabon {bill.number}</strong>
      <small>{bill.day} · {bill.process} · {bill.qty} pcs × {amountText(bill.rate)}</small><small>Total {money(billGross(bill))} · Kredit {money(billCredit(bill))}</small></span>
      <div><small>Sisa tagihan</small><b>{money(remaining)}</b></div></div>
    {remaining>0&&credits.length>0&&<button className="soft-btn" onClick={()=>{setError('');setForm({id:crypto.randomUUID(),claim:credits[0].claim.id,amount:'',day:lastWarehouseDay(),reason:''})}}>Potong tagihan</button>}
    {bill.credits?.length? <details className="demo-operation-history"><summary>Riwayat kredit ({bill.credits.length})</summary>
      {bill.credits.map(credit=><article key={credit.id}>
        <strong>{money(credit.cents)} · {credit.reversed?'Dibalik':'Kredit klaim'}</strong><small>{credit.day} · {credit.reversed||credit.reason}</small>
        {!credit.reversed&&<button className="soft-btn" onClick={()=>{setUndo(credit);setUndoReason('')}}>Balikkan potongan</button>}
      </article>)}</details>:null}
    {form&&<ReasonDialog title="Potong tagihan laundry" closeLabel="Kembali" onClose={()=>setForm(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={save}>
        <p>{delivery.vendor} · {bill.number} · sisa {money(remaining)}</p>
        <label>Sumber kredit<select value={form.claim} onChange={event=>setForm({...form,claim:event.target.value,amount:''})}>
          {credits.map(row=><option key={row.claim.id} value={row.claim.id}>{row.claim.type} · {row.claim.qty} pcs · {row.delivery.id} · {money(row.remaining)}</option>)}
        </select></label>
        <div className="demo-operation-fields">
          <label>Nominal potongan (Rp)<input required inputMode="decimal" value={form.amount} onChange={event=>setForm({...form,amount:event.target.value})}/>
            {selected&&<small>Batas {money(Math.min(remaining,selected.remaining))}</small>}</label>
          <label>Tanggal potongan<input required type="date" max={lastWarehouseDay()} value={form.day} onChange={event=>setForm({...form,day:event.target.value})}/></label>
        </div>
        <label>Alasan potongan<textarea required maxLength={500} value={form.reason} onChange={event=>setForm({...form,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Simpan potongan tagihan</button></footer>
      </form>
    </ReasonDialog>}
    {undo&&<ReasonDialog title="Balikkan potongan tagihan" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog">
      <div className="demo-operation-form"><label>Alasan pembalikan<textarea value={undoReason} onChange={event=>setUndoReason(event.target.value)}/></label>
        <footer><button className="primary-btn" disabled={undoReason.trim().length<4} onClick={()=>{
          update(rows=>updateBill(rows,live=>({...live,credits:live.credits?.map(credit=>credit.id===undo.id&&!credit.reversed
            ? {...credit,reversed:undoReason.trim()} : credit)})));setUndo(null)
        }}>Simpan pembalikan</button></footer></div>
    </ReasonDialog>}
  </section>
}
