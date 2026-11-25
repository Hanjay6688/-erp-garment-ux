import { useState, type FormEvent } from 'react'
import { ArrowRight, FilePlus2, ReceiptText, ShieldCheck, Undo2, WalletCards } from 'lucide-react'
import { readRupiahInput } from '../moneyInput'
import { availableCredits, billRemaining, claimUse, eligibleOutsideClaims, validClaim, validClaimResolution, vendorBalance } from './laundryCredits'
import { LaundrySettlement } from './LaundrySettlement'
import { LaundryClaimResolutionDialog } from './LaundryClaimResolutionDialog'
import { LaundryClaimCreditDialog, claimMoney as money, type UpdateLaundry } from './LaundryClaimCreditDialog'
import { isPostedLaundryInvoice, type LaundryBillCredit, type LaundryClaim, type LaundryClaimResolution, type LaundryDelivery, type LaundryFinalBill } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'
import { laundryPayablesPath } from './laundryVendorInvoices'
import './demoCorrection.css'

const labels = {BS:'BS karena laundry',STUCK:'Stuck di laundry',MISSING:'Hilang di laundry'}

export function LaundryClaims({delivery,deliveries,update}:{delivery:LaundryDelivery;deliveries:LaundryDelivery[];update:UpdateLaundry}) {
  const [draft,setDraft]=useState<{id:string;type:LaundryClaim['type'];qty:string;amount:string;reason:string;day:string}|null>(null)
  const [undo,setUndo]=useState<LaundryClaim|null>(null)
  const [resolveId,setResolveId]=useState<string|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [error,setError]=useState('')
  const claims=delivery.claims??[]
  const stuck=eligibleOutsideClaims(delivery)
  const resolving=claims.find(row=>row.id===resolveId)
  const available=availableCredits(deliveries,delivery.vendor)

  function create(event:FormEvent) {
    event.preventDefault()
    if(!draft)return
    const claim:LaundryClaim={id:draft.id,type:draft.type,qty:/^[1-9]\d*$/.test(draft.qty)?Number(draft.qty):NaN,
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
    <button className="soft-btn laundry-claim-start" type="button" onClick={()=>{setError('');setDraft({id:crypto.randomUUID(),type:stuck>0?'STUCK':'BS',qty:'',amount:'',reason:'',day:lastWarehouseDay()})}}><FilePlus2 aria-hidden="true"/> Buat klaim BS / Stuck</button>
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
            {credit&&<a className="soft-btn" href={laundryPayablesPath(delivery.vendor)}><WalletCards size={16}/> Pakai kredit di Hutang <ArrowRight size={16}/></a>}
            {!used&&!claim.resolution?.qcPosted&&<button type="button" className="soft-btn" onClick={()=>{setUndo(claim);setUndoReason('')}}>Balikkan klaim</button>}
            {claim.resolution?.qcPosted&&<small>Barang pengganti sudah diproses di QC.</small>}
          </div>}
        </article>
      })}
    </details>}
    {draft&&<ReasonDialog title="Buat klaim laundry" closeLabel="Kembali" onClose={()=>setDraft(null)} className="demo-operation-dialog money-dialog" icon={<ShieldCheck/>}>
      <form className="demo-operation-form" onSubmit={create}>
        <p>{delivery.vendor} · {delivery.id}</p>
        <label>Jenis klaim<select value={draft.type} onChange={event=>{setError('');setDraft({...draft,type:event.target.value as LaundryClaim['type'],qty:''})}}>
          <option value="BS">{labels.BS}</option>
          {stuck>0&&(['STUCK','MISSING'] as const).map(type=><option key={type} value={type}>{labels[type]}</option>)}
        </select></label>
        <div className="demo-operation-fields">
          <label>Jumlah diklaim (pcs)<input required inputMode="numeric" value={draft.qty} onChange={event=>setDraft({...draft,qty:event.target.value})}/>
            <small>{draft.type==='BS'?'Termasuk BS yang baru ditemukan di QC akhir.':`${stuck} pcs masih bisa diklaim`}</small></label>
          <label>Nilai kompensasi (Rp)<input required={draft.type==='BS'} inputMode="decimal" placeholder="Contoh 15.000" value={draft.amount} onChange={event=>setDraft({...draft,amount:event.target.value})}/>{draft.type!=='BS'&&<small>Boleh kosong untuk penggantian barang.</small>}</label>
        </div>
        <label>Tanggal klaim<input required type="date" max={lastWarehouseDay()} value={draft.day} onChange={event=>setDraft({...draft,day:event.target.value})}/></label>
        <label>Alasan dan kesepakatan dengan laundry<textarea required value={draft.reason} maxLength={500} onChange={event=>setDraft({...draft,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Simpan klaim</button></footer>
      </form>
    </ReasonDialog>}
    {resolving&&<LaundryClaimResolutionDialog delivery={delivery} claim={resolving} used={claimUse(deliveries,resolving.id)} onClose={()=>setResolveId(null)} onSave={resolve}/>}
    {undo&&<ReasonDialog title="Balikkan klaim laundry" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog money-dialog" icon={<Undo2/>}>
      <div className="demo-operation-form"><label>Alasan pembalikan<textarea value={undoReason} onChange={event=>setUndoReason(event.target.value)}/></label>
        <footer><button className="primary-btn" disabled={undoReason.trim().length<4} onClick={reverse}>Simpan pembalikan</button></footer></div>
    </ReasonDialog>}
  </section>
}

export function LaundryInvoiceActions({delivery,bill,deliveries,update}:{delivery:LaundryDelivery;bill:LaundryFinalBill;deliveries:LaundryDelivery[];update:UpdateLaundry}) {
  const [formOpen,setFormOpen]=useState(false)
  const [undo,setUndo]=useState<LaundryBillCredit|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [error,setError]=useState('')
  const remaining=billRemaining(deliveries,delivery,bill)
  const credits=availableCredits(deliveries,delivery.vendor)
  function updateBill(rows:LaundryDelivery[], next:(live: LaundryFinalBill)=>LaundryFinalBill) {
    return rows.map(row=>row.id!==delivery.id?row:{...row,finalBills:row.finalBills?.map(live=>live.number===bill.number&&isPostedLaundryInvoice(live)?next(live):live)})
  }
  return <section className="demo-ops-card demo-supplier-transfers laundry-invoice-actions" id="pembayaran-invoice" aria-label={'Penyelesaian invoice '+bill.number}>
    <header className="demo-operation-heading"><i><ReceiptText aria-hidden="true"/></i><div><h3>Penyelesaian invoice</h3><p>{delivery.vendor} · {bill.number}</p></div></header>
    {remaining>0&&<div className="laundry-credit-control" data-credit-available={credits.length>0}>
      <div><strong>Kredit klaim tersedia</strong><small>{money(credits.reduce((sum,row)=>sum+row.remaining,0))} · {credits.length} klaim</small></div>
      <button type="button" className="soft-btn" disabled={credits.length===0} onClick={()=>setFormOpen(true)}><WalletCards aria-hidden="true"/> Pakai kredit</button>
    </div>}
    {bill.credits?.length? <details className="demo-operation-history"><summary>Riwayat kredit ({bill.credits.length})</summary>
      {bill.credits.map(credit=><article key={credit.id}>
        <strong>{money(credit.cents)} · {credit.reversed?'Dibalik':'Kredit klaim'}</strong><small>{credit.day} · {credit.reversed||credit.reason}</small>
        {!credit.reversed&&<button className="soft-btn" onClick={()=>{setError('');setUndo(credit);setUndoReason('')}}>Balikkan potongan</button>}
      </article>)}</details>:null}
    <LaundrySettlement delivery={delivery} bill={bill} deliveries={deliveries} update={update}/>
    {formOpen&&<LaundryClaimCreditDialog deliveries={deliveries} delivery={delivery} bill={bill} update={update} onClose={()=>setFormOpen(false)}/>}
    {undo&&<ReasonDialog title="Balikkan potongan invoice" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog money-dialog" icon={<Undo2/>}>
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
