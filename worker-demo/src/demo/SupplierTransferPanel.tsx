import { useState } from 'react'
import { Banknote, FilePenLine, Undo2 } from 'lucide-react'
import { cashAccounts, type Payable } from '../financeData'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { reverseSupplierTransfer, saveSupplierTransfer, transferPayables, transferTotal, type SupplierTransfer } from './supplierTransfers'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

type Draft={id:string;day:string;account:string;reference:string;amount:string;lines:Record<string,string>;reason:string;replaces?:string}
const cents=(text:string)=>Math.round(readRupiahInput(text)*100)
const balance=(doc:Payable)=>Math.max(0,Math.round((doc.amount-doc.paid)*100))

export function SupplierTransferPanel({doc,transfers,onSaved}:{doc:Payable;transfers:SupplierTransfer[];onSaved:(transfers:SupplierTransfer[])=>void}) {
  const [draft,setDraft]=useState<Draft|null>(null)
  const [undo,setUndo]=useState<{doc:SupplierTransfer;day:string;reason:string}|null>(null)
  const [error,setError]=useState('')
  const history=transfers.filter(row=>row.party===doc.party).slice().reverse()
  const rows=transferPayables(transfers,draft?.replaces).filter(row=>row.party===doc.party&&row.kind!=='MATERIAL_GRNI'&&balance(row)>0)
  const allocations=Object.entries(draft?.lines??{}).filter(([,amount])=>amount.trim()!=='').map(([number,amount])=>({number,cents:cents(amount)}))
  const allocated=allocations.reduce((sum,row)=>sum+row.cents,0)
  const declared=draft?cents(draft.amount):NaN
  const valid=Number.isSafeInteger(allocated)&&allocated>0&&allocated===declared&&allocations.every(line=>line.cents>0&&line.cents<=balance(rows.find(row=>row.number===line.number)??{...doc,paid:doc.amount}))
  if(doc.kind==='MATERIAL_GRNI'&&!history.length)return null
  const open=(record?:SupplierTransfer)=>{setError('');setDraft({id:'TRF-'+crypto.randomUUID().slice(0,8).toUpperCase(),day:record?.day??lastWarehouseDay(),account:record?.account??'',reference:record?.reference??'',
    amount:record?String(transferTotal(record)):'',lines:record?Object.fromEntries(record.allocations.map(row=>[row.number,String(row.cents/100)])):{},reason:'',replaces:record?.id})}

  return <section className="demo-ops-card demo-supplier-transfers" aria-label="Pembayaran supplier">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><Banknote/></i><div><h3>Transfer ke {doc.party}</h3><p>Alokasikan satu bukti transfer ke satu atau beberapa tagihan terbuka.</p></div></div>
      {rows.length>0&&<button type="button" className="primary-btn" onClick={()=>open()}>Catat transfer</button>}</header>
    {history.length>0&&<details className="demo-operation-history" open><summary>Riwayat transfer ({history.length})</summary>
      {history.map(row=><article key={row.id}><strong>{amountText(transferTotal(row))} · {row.allocations.length} tagihan</strong><small>{row.id} · {row.day} · {row.account} · {row.reference}</small>
        {row.allocations.map(line=><small key={line.number}>{line.number} · {amountText(line.cents/100)}</small>)}
        {row.reversed?<small>Dibalik · {row.reversed.reason}{row.reversed.replacement?' · Pengganti '+row.reversed.replacement:''}</small>:<div className="demo-operation-actions">
          <button className="soft-btn" onClick={()=>open(row)}><FilePenLine size={16}/> Koreksi transfer</button>
          <button className="soft-btn" onClick={()=>{setError('');setUndo({doc:row,day:lastWarehouseDay(),reason:''})}}><Undo2 size={16}/> Balikkan transfer</button></div>}
      </article>)}
    </details>}
    {draft&&<ReasonDialog title={draft.replaces?'Koreksi transfer supplier':'Transfer supplier'} closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setDraft(null)}>
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        try{onSaved(saveSupplierTransfer({id:draft.id,party:doc.party,day:draft.day,account:draft.account,reference:draft.reference.trim(),allocations,replaces:draft.replaces},declared,draft.reason));setDraft(null)}
        catch(failure){setError((failure as Error).message)}
      }}><p>{doc.party}</p><div className="demo-operation-fields">
        <label>Nominal transfer (Rp)<input required inputMode="decimal" value={draft.amount} onChange={event=>setDraft({...draft,amount:event.target.value})}/></label>
        <label>Tanggal transfer<input type="date" required max={lastWarehouseDay()} value={draft.day} onChange={event=>setDraft({...draft,day:event.target.value})}/></label>
        <label>Rekening keluar<select required value={draft.account} onChange={event=>setDraft({...draft,account:event.target.value})}>
          <option value="">Pilih rekening</option>{cashAccounts.map(row=><option key={row.code}>{row.name}</option>)}</select></label>
        <label>Bukti transfer<input required minLength={3} maxLength={140} value={draft.reference} onChange={event=>setDraft({...draft,reference:event.target.value})}/></label>
      </div>
      <div className="demo-entry-list" aria-label="Alokasi transfer per tagihan">{rows.map(row=><article key={row.number}><div><strong>{row.number}</strong><small>{row.reference}</small></div>
        <div><strong>{amountText(balance(row)/100)}</strong><small>Sisa tagihan</small></div><label>Alokasi (Rp)<input aria-label={'Alokasi '+row.number} inputMode="decimal" placeholder="0"
          value={draft.lines[row.number]??''} onChange={event=>setDraft({...draft,lines:{...draft.lines,[row.number]:event.target.value}})}/></label></article>)}</div>
      <div className="demo-operation-facts"><article><span>Total dialokasikan</span><strong>{Number.isFinite(allocated)?amountText(allocated/100):'Periksa isian'}</strong><small>{allocations.length} tagihan</small></article>
        <article><span>Sisa untuk dialokasikan</span><strong>{Number.isFinite(allocated)&&Number.isFinite(declared)?amountText((declared-allocated)/100):'—'}</strong></article></div>
      {draft.replaces&&<label>Alasan koreksi<textarea required minLength={4} maxLength={400} value={draft.reason} onChange={event=>setDraft({...draft,reason:event.target.value})}/></label>}
      {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn" disabled={!valid}>{draft.replaces?'Simpan koreksi transfer':'Simpan transfer'}</button></footer>
      </form></ReasonDialog>}
    {undo&&<ReasonDialog title="Balikkan satu transfer" closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setUndo(null)}>
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        try{onSaved(reverseSupplierTransfer(undo.doc.id,undo.day,undo.reason));setUndo(null)}catch(failure){setError((failure as Error).message)}
      }}><p>{undo.doc.id} · {amountText(transferTotal(undo.doc))} dikembalikan ke saldo {undo.doc.allocations.length} tagihan.</p>
        <label>Tanggal pembalikan<input required type="date" min={undo.doc.day} max={lastWarehouseDay()} value={undo.day} onChange={event=>setUndo({...undo,day:event.target.value})}/></label>
        <label>Alasan pembalikan<textarea required minLength={4} maxLength={400} value={undo.reason} onChange={event=>setUndo({...undo,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan pembalikan transfer</button></footer>
      </form></ReasonDialog>}
  </section>
}
