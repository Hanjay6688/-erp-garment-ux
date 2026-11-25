import { useState, type FormEvent } from 'react'
import { ArrowRight, ReceiptText, ShieldCheck, WalletCards } from 'lucide-react'
import { readRupiahInput } from '../moneyInput'
import { availableCredits, billCredit, billGross, billRemaining, claimUse, eligibleClaimPieces, validClaim, validClaimResolution, vendorBalance, vendorCreditApplied } from './laundryCredits'
import { LaundrySettlement } from './LaundrySettlement'
import { LaundryClaimResolutionDialog } from './LaundryClaimResolutionDialog'
import { LaundryClaimCreditDialog, claimMoney as money, openLaundryBills, type UpdateLaundry } from './LaundryClaimCreditDialog'
import type { LaundryBillCredit, LaundryClaim, LaundryClaimResolution, LaundryDelivery, LaundryFinalBill } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

const labels = {BS:'BS karena laundry',STUCK:'Stuck di laundry',MISSING:'Hilang di laundry'}

export function LaundryClaims({delivery,deliveries,update,onShowBills}:{delivery:LaundryDelivery;deliveries:LaundryDelivery[];update:UpdateLaundry;onShowBills?:()=>void}) {
  const [draft,setDraft]=useState<{id:string;type:LaundryClaim['type'];qty:string;amount:string;reason:string;day:string}|null>(null)
  const [undo,setUndo]=useState<LaundryClaim|null>(null)
  const [resolveId,setResolveId]=useState<string|null>(null)
  const [creditId,setCreditId]=useState<string|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [error,setError]=useState('')
  const claims=delivery.claims??[]
  const bs=eligibleClaimPieces(delivery,'BS')
  const stuck=eligibleClaimPieces(delivery,'STUCK')
  const canStart=bs>0||stuck>0
  const resolving=claims.find(row=>row.id===resolveId)
  const available=availableCredits(deliveries,delivery.vendor)
  const hasBill=openLaundryBills(deliveries,delivery.vendor).length>0
  if(!claims.length&&!canStart)return null

  function create(event:FormEvent) {
    event.preventDefault()
    if(!draft)return
    const claim:LaundryClaim={id:draft.id,type:draft.type,qty:/^[1-9]\d{0,8}$/.test(draft.qty)?Number(draft.qty):NaN,
      cents:draft.amount.trim()?Math.round(readRupiahInput(draft.amount)*100):0,day:draft.day,reason:draft.reason.trim(),needsResolution:true}
    if(!validClaim(delivery,claim)){setError('Periksa jumlah pcs, nilai kompensasi, tanggal, dan alasan klaim.');return}
    update(rows=>rows.map(row=>row.id===delivery.id&&validClaim(row,claim)&&!row.claims?.some(current=>current.id===claim.id)
      ? {...row,claims:[...(row.claims??[]),claim]} : row))
    setDraft(null)
  }
  function approve(claim:LaundryClaim) {
    update(rows=>rows.map(row=>row.id===delivery.id ? {...row,claims:row.claims?.map(current=>current.id===claim.id&&!current.reversed&&!current.approvedOn
      ? {...current,approvedOn:lastWarehouseDay()} : current)} : row))
  }
  function resolve(resolution:LaundryClaimResolution) {
    update(rows=>rows.map(row=>row.id===delivery.id?{...row,claims:row.claims?.map(claim=>claim.id===resolveId
      &&validClaimResolution(row,claim,resolution)&&(resolution.kind!=='REPLACEMENT'||claimUse(rows,claim.id)===0)?{...claim,resolution}:claim)}:row))
    setResolveId(null)
  }
  function reverse() {
    if(!undo||undoReason.trim().length<4)return
    update(rows=>claimUse(rows,undo.id)>0?rows:rows.map(row=>row.id===delivery.id ? {...row,claims:row.claims?.map(claim=>claim.id===undo.id&&!claim.resolution?.qcPosted
      ? {...claim,reversed:undoReason.trim()} : claim)} : row))
    setUndo(null)
  }

  return <section className="laundry-claim-box" aria-label="Klaim laundry">
    <div className="demo-operation-heading"><i><ShieldCheck aria-hidden="true"/></i><div><h3>Klaim laundry</h3>
      <p>Catat klaim, konfirmasi persetujuan, lalu selesaikan saat vendor sudah mengganti.</p></div></div>
    {canStart&&<button className="soft-btn" type="button" onClick={()=>{setError('');setDraft({id:crypto.randomUUID(),type:stuck>0?'STUCK':'BS',qty:'',amount:'',reason:'',day:lastWarehouseDay()})}}>Buat klaim BS / Stuck</button>}
    {claims.length>0&&<details className="demo-operation-history" open>
      <summary>Riwayat klaim ({claims.length})</summary>
      {claims.map(claim=>{
        const used=claimUse(deliveries,claim.id)
        const credit=available.find(row=>row.claim.id===claim.id)
        const status=claim.reversed?'Dibalik':claim.resolution?.kind==='REPLACEMENT'?'Selesai · barang pengganti diterima'
          :claim.resolution?'Selesai · kompensasi tercatat':claim.approvedOn?'Disetujui · siap diselesaikan':'Menunggu persetujuan'
        return <article key={claim.id}>
          <strong>{claim.qty} pcs · {labels[claim.type]}</strong>
          <span>{status}{claim.resolution?.kind!=='REPLACEMENT'&&claim.cents>0?' · '+money(claim.cents):''}</span>
          {credit&&<small>Sisa kredit {money(credit.remaining)}</small>}
          <small>{claim.reversed||claim.reason}</small>
          {claim.resolution&&!claim.reversed&&<small>{claim.resolution.day} · {claim.resolution.reason}</small>}
          {!claim.reversed&&<div className="demo-operation-actions">
            {!claim.approvedOn&&<button type="button" className="soft-btn" onClick={()=>approve(claim)}>Setujui klaim {claim.type}</button>}
            {claim.approvedOn&&!claim.resolution&&<button type="button" className="primary-btn" onClick={()=>setResolveId(claim.id)}>Selesaikan klaim</button>}
            {credit&&hasBill&&<button type="button" className="primary-btn" onClick={()=>setCreditId(claim.id)}><WalletCards size={16}/> Pakai kredit ke tagihan</button>}
            {credit&&!hasBill&&<small>Catat dulu kontrabon terbuka untuk {delivery.vendor}.</small>}
            {credit&&!hasBill&&onShowBills&&<button className="soft-btn" type="button" onClick={onShowBills}>Buka Klaim &amp; Tagihan <ArrowRight size={16}/></button>}
            {!used&&!claim.resolution?.qcPosted&&<button type="button" className="soft-btn" onClick={()=>{setUndo(claim);setUndoReason('')}}>Balikkan klaim</button>}
            {claim.resolution?.qcPosted&&<small>Barang pengganti sudah diproses di QC.</small>}
          </div>}
        </article>
      })}
    </details>}
    {draft&&<ReasonDialog title="Buat klaim laundry" closeLabel="Kembali" onClose={()=>setDraft(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={create}>
        <p>{delivery.vendor} · {delivery.id}</p>
        <label>Jenis klaim<select value={draft.type} onChange={event=>{setError('');setDraft({...draft,type:event.target.value as LaundryClaim['type'],qty:''})}}>
          {bs>0&&<option value="BS">{labels.BS}</option>}
          {stuck>0&&(['STUCK','MISSING'] as const).map(type=><option key={type} value={type}>{labels[type]}</option>)}
        </select></label>
        <div className="demo-operation-fields">
          <label>Jumlah diklaim (pcs)<input required inputMode="numeric" value={draft.qty} onChange={event=>setDraft({...draft,qty:event.target.value})}/>
            <small>Tersedia {eligibleClaimPieces(delivery,draft.type)} pcs</small></label>
          <label>Nilai kompensasi (Rp)<input required={draft.type==='BS'} inputMode="decimal" placeholder="Contoh 15.000" value={draft.amount} onChange={event=>setDraft({...draft,amount:event.target.value})}/>{draft.type!=='BS'&&<small>Boleh kosong untuk penggantian barang.</small>}</label>
        </div>
        <label>Tanggal klaim<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>setDraft({...draft,day:event.target.value})}/></label>
        <label>Alasan dan kesepakatan dengan laundry<textarea required value={draft.reason} maxLength={500} onChange={event=>setDraft({...draft,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Simpan klaim</button></footer>
      </form>
    </ReasonDialog>}
    {resolving&&<LaundryClaimResolutionDialog delivery={delivery} claim={resolving} used={claimUse(deliveries,resolving.id)} onClose={()=>setResolveId(null)} onSave={resolve}/>}
    {creditId&&<LaundryClaimCreditDialog deliveries={deliveries} vendor={delivery.vendor} claimId={creditId} update={update} onClose={()=>setCreditId(null)}/>}
    {undo&&<ReasonDialog title="Balikkan klaim laundry" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog">
      <div className="demo-operation-form"><label>Alasan pembalikan<textarea value={undoReason} onChange={event=>setUndoReason(event.target.value)}/></label>
        <footer><button className="primary-btn" disabled={undoReason.trim().length<4} onClick={reverse}>Simpan pembalikan</button></footer></div>
    </ReasonDialog>}
  </section>
}

export function LaundryBillCard({delivery,bill,deliveries,update}:{delivery:LaundryDelivery;bill:LaundryFinalBill;deliveries:LaundryDelivery[];update:UpdateLaundry}) {
  const [formOpen,setFormOpen]=useState(false)
  const [undo,setUndo]=useState<LaundryBillCredit|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [error,setError]=useState('')
  const remaining=billRemaining(deliveries,delivery,bill)
  const applied=billCredit(bill)+vendorCreditApplied(deliveries,delivery.id,bill.number)
  const credits=availableCredits(deliveries,delivery.vendor)
  function updateBill(rows:LaundryDelivery[], next:(live: LaundryFinalBill)=>LaundryFinalBill) {
    return rows.map(row=>row.id!==delivery.id?row:{...row,finalBills:row.finalBills?.map(live=>live.number===bill.number?next(live):live)})
  }
  return <section className="laundry-bill-card" aria-label={'Kontrabon '+bill.number}>
    <div className="laundry-final-bill"><ReceiptText size={17} aria-hidden="true"/><span><strong>Kontrabon {bill.number}</strong>
      <small>{bill.day} · {bill.parts?`${bill.parts.length} penerimaan · ${bill.qty} pcs`:`${bill.process} · ${bill.qty} pcs × ${money(bill.rate*100)}`}</small><small>Total {money(billGross(bill))} · Kredit {money(applied)}</small></span>
      <div><small>Sisa tagihan</small><b>{money(remaining)}</b></div></div>
    {!!bill.parts?.length&&<details className="demo-operation-history"><summary>Penerimaan dalam kontrabon ({bill.parts.length})</summary>
      {bill.parts.map(line=><article key={line.delivery}><strong>{line.qty} pcs · {line.process}</strong><small>{line.delivery} · {money(line.rate*100)} / pcs</small></article>)}
    </details>}
    {remaining>0&&<div className="laundry-credit-control">
      <button type="button" className="primary-btn" disabled={credits.length===0} onClick={()=>setFormOpen(true)}><WalletCards size={16}/> Potong tagihan</button>
      {credits.length===0&&<small>Selesaikan dulu klaim yang memberi kredit untuk {delivery.vendor}.</small>}
    </div>}
    {bill.credits?.length? <details className="demo-operation-history"><summary>Riwayat kredit ({bill.credits.length})</summary>
      {bill.credits.map(credit=><article key={credit.id}>
        <strong>{money(credit.cents)} · {credit.reversed?'Dibalik':'Kredit klaim'}</strong><small>{credit.day} · {credit.reversed||credit.reason}</small>
        {!credit.reversed&&<button className="soft-btn" onClick={()=>{setError('');setUndo(credit);setUndoReason('')}}>Balikkan potongan</button>}
      </article>)}</details>:null}
    <LaundrySettlement delivery={delivery} bill={bill} deliveries={deliveries} update={update}/>
    {formOpen&&<LaundryClaimCreditDialog deliveries={deliveries} vendor={delivery.vendor} target={{delivery,bill}} update={update} onClose={()=>setFormOpen(false)}/>}
    {undo&&<ReasonDialog title="Balikkan potongan tagihan" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog">
      <div className="demo-operation-form"><label>Alasan pembalikan<textarea value={undoReason} onChange={event=>setUndoReason(event.target.value)}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn" disabled={undoReason.trim().length<4} onClick={()=>{
          const reverse=(live: LaundryFinalBill)=>({...live,credits:live.credits?.map(credit=>credit.id===undo.id&&!credit.reversed
            ? {...credit,reversed:undoReason.trim()} : credit)})
          if(vendorBalance(deliveries,delivery,reverse(bill))<0){setError('Piutang dari pembayaran ini sudah digunakan. Periksa riwayat penyelesaian vendor.');return}
          update(rows=>updateBill(rows,live=>vendorBalance(rows,delivery,reverse(live))>=0?reverse(live):live));setUndo(null)
        }}>Simpan pembalikan</button></footer></div>
    </ReasonDialog>}
  </section>
}
