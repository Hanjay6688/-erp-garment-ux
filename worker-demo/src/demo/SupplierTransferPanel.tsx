import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { Banknote, FilePenLine, Undo2 } from 'lucide-react'
import { cashAccounts, type Payable } from '../financeData'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { reverseSupplierTransfer, saveSupplierTransfer, transferTotal, type SupplierTransfer } from './supplierTransfers'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

type Draft={id:string;day:string;account:string;reference:string;amount:string;reason:string;original?:SupplierTransfer}
const cents=(text:string)=>Math.round(readRupiahInput(text)*100)

export function SupplierTransferPanel({doc,transfers,onSaved}:{doc:Payable;transfers:SupplierTransfer[];onSaved:(transfers:SupplierTransfer[])=>void}) {
  const [draft,setDraft]=useState<Draft|null>(null)
  const [undo,setUndo]=useState<{doc:SupplierTransfer;day:string;reason:string}|null>(null)
  const [error,setError]=useState('')
  const history=transfers.filter(row=>row.party===doc.party&&row.allocations.some(line=>line.number===doc.number)).slice().reverse()
  const remaining=Math.max(0,Math.round((doc.amount-doc.paid)*100))
  const limit=remaining+(draft?.original?.allocations[0]?.cents??0)
  const amount=draft?cents(draft.amount):NaN
  const valid=Number.isSafeInteger(amount)&&amount>0&&amount<=limit
  const open=(record?:SupplierTransfer)=>{
    setError('')
    setDraft({id:'TRF-'+crypto.randomUUID().slice(0,8).toUpperCase(),day:record?.day??lastWarehouseDay(),
      account:record?.account??'',reference:record?.reference??'',amount:String(record?transferTotal(record):remaining/100).replace('.',','),reason:'',original:record})
  }
  return <section className="demo-ops-card demo-supplier-transfers" id="pembayaran-invoice" aria-label="Pembayaran supplier">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><Banknote/></i><div><h3>Pembayaran invoice</h3><p>{doc.party} · {doc.number}</p></div></div>
      {remaining>0&&<button type="button" className="primary-btn" onClick={()=>open()}><Banknote size={17}/> Bayar invoice</button>}</header>
    {history.length>0&&<details className="demo-operation-history" open><summary>Riwayat pembayaran ({history.length})</summary>
      {history.map(row=><article key={row.id}><strong>{amountText(transferTotal(row))}</strong><small>{row.day} · {row.account} · {row.reference}</small>
        {row.allocations.length>1&&<small>Transfer lama mencakup {row.allocations.map(line=>line.number).join(' · ')}</small>}
        {row.reversed?<small>Dibalik · {row.reversed.reason}{row.reversed.replacement?' · Pengganti '+row.reversed.replacement:''}</small>
          :<div className="demo-operation-actions">{row.allocations.length===1&&<button className="soft-btn" onClick={()=>open(row)}><FilePenLine size={16}/> Koreksi pembayaran</button>}
            <button className="soft-btn" onClick={()=>{setError('');setUndo({doc:row,day:lastWarehouseDay(),reason:''})}}><Undo2 size={16}/> Balikkan pembayaran</button></div>}
      </article>)}
    </details>}
    {draft&&<ReasonDialog title={draft.original?'Koreksi pembayaran invoice':'Bayar invoice supplier'} closeLabel="Kembali" className="demo-operation-dialog money-dialog" icon={<Banknote/>} onClose={()=>setDraft(null)}>
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        try{onSaved(saveSupplierTransfer({id:draft.id,party:doc.party,day:draft.day,account:draft.account,reference:draft.reference.trim(),
          allocations:[{number:doc.number,cents:amount}],replaces:draft.original?.id},amount,draft.reason));setDraft(null)}
        catch(failure){setError((failure as Error).message)}
      }}><p>{doc.party} · invoice <strong>{doc.number}</strong></p><div className="demo-operation-fields">
        <label>Nominal pembayaran (Rp)<NumberEntry rupiahDraft required inputMode="decimal" value={draft.amount} onValueChange={rawInput =>setDraft({...draft,amount:rawInput})}/><small>Maksimum {amountText(limit/100)}</small></label>
        <label>Tanggal pembayaran<input type="date" required max={lastWarehouseDay()} value={draft.day} onChange={event=>setDraft({...draft,day:event.target.value})}/></label>
        <label>Rekening keluar<select required value={draft.account} onChange={event=>setDraft({...draft,account:event.target.value})}>
          <option value="">Pilih rekening</option>{cashAccounts.map(row=><option key={row.code}>{row.name}</option>)}</select></label>
        <label>Bukti pembayaran<input required minLength={3} maxLength={140} value={draft.reference} onChange={event=>setDraft({...draft,reference:event.target.value})}/></label>
      </div>
      <div className="demo-operation-facts"><article><span>Sisa setelah pembayaran</span><strong>{valid?amountText((limit-amount)/100):'—'}</strong></article></div>
      {draft.original&&<label>Alasan koreksi<textarea required minLength={4} maxLength={400} value={draft.reason} onChange={event=>setDraft({...draft,reason:event.target.value})}/></label>}
      {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn" disabled={!valid}>{draft.original?'Simpan koreksi pembayaran':'Simpan pembayaran'}</button></footer>
      </form></ReasonDialog>}
    {undo&&<ReasonDialog title="Balikkan pembayaran invoice" closeLabel="Kembali" className="demo-operation-dialog money-dialog" icon={<Undo2/>} onClose={()=>setUndo(null)}>
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        try{onSaved(reverseSupplierTransfer(undo.doc.id,undo.day,undo.reason));setUndo(null)}catch(failure){setError((failure as Error).message)}
      }}><p>{undo.doc.reference} · {amountText(transferTotal(undo.doc))} dikembalikan ke saldo invoice.</p>
        <label>Tanggal pembalikan<input required type="date" min={undo.doc.day} max={lastWarehouseDay()} value={undo.day} onChange={event=>setUndo({...undo,day:event.target.value})}/></label>
        <label>Alasan pembalikan<textarea required minLength={4} maxLength={400} value={undo.reason} onChange={event=>setUndo({...undo,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan pembalikan pembayaran</button></footer>
      </form></ReasonDialog>}
  </section>
}
