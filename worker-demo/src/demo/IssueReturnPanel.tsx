import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { PackageOpen, Undo2 } from 'lucide-react'
import { amountText } from './accessoryPricing'
import { outstandingIssue, type IssueDocument } from './issueDocuments'
import { issuePaid, issueReturnBlockers, postIssueReturn, quoteIssueReturn, returnableIssueLines, reverseIssueReturn } from './issueReturns'
import { StockSourceReversal } from './StockSourceReversal'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

type Draft={id:string;day:string;reason:string;quantities:Record<string,string>}

export function IssueReturnPanel({doc}:{doc:IssueDocument}) {
  const [draft,setDraft]=useState<Draft|null>(null)
  const [error,setError]=useState('')
  const linked=new URLSearchParams(location.search).get('retur')
  const paid=issuePaid(doc)
  const rows=returnableIssueLines(doc)
  const quote=draft?quoteIssueReturn(doc,draft.quantities,paid):null
  return <section className="demo-ops-card demo-issue-return" aria-label="Retur dari mandor">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><PackageOpen/></i><div><h3>Retur dari mandor</h3><p>Sisa tagihan nota {amountText(outstandingIssue(doc,paid))}</p></div></div>
      {rows.some(row=>row.remaining>0&&row.sellingPrice!==null)&&<button type="button" className="primary-btn" onClick={()=>{setError('');setDraft({id:'RAM-'+crypto.randomUUID().slice(0,8).toUpperCase(),day:lastWarehouseDay(),reason:'',quantities:{}})}}><Undo2 size={16}/> Terima retur aksesori</button>}</header>
    {!!doc.returns?.length&&<details className="demo-operation-history" open><summary>Riwayat retur ({doc.returns.length})</summary>
      {doc.returns.map(row=><article key={row.id} id={row.id} data-source-selected={row.id===linked||undefined}><strong>{row.lines.reduce((sum,line)=>sum+line.qty,0)} pcs kembali</strong>
        <small>{row.id} · {row.day} · {row.reason}</small><small>Potong tagihan {amountText(row.chargeReduction)} · Kredit payroll {amountText(row.credit)}</small>
        {row.credit>0&&!row.reversal&&<a className="soft-btn" href={'/keuangan/payroll-kasbon/?'+new URLSearchParams({mandor:doc.mandor})}>Buka Payroll</a>}
        <StockSourceReversal label="Balikkan retur aksesori" document={row.id} reversal={row.reversal} blockers={issueReturnBlockers(doc,row)}
          onReverse={reason=>reverseIssueReturn(doc.number,row.id,reason)}/>
      </article>)}
    </details>}
    {draft&&quote&&<ReasonDialog title="Terima retur aksesori dari mandor" closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setDraft(null)}>
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        try{postIssueReturn(doc.number,draft.id,draft.day,draft.reason,draft.quantities);setDraft(null)}catch(failure){setError((failure as Error).message)}
      }}><p>{doc.mandor} · {doc.number} · Isi jumlah yang sudah diterima dalam kondisi layak pakai.</p>
        <div className="demo-entry-list">{rows.map(row=><article key={row.id}><div><strong>{row.item}</strong><small>{row.qty} {row.unit} di nota</small></div>
          <div><strong>{row.remaining} {row.unit}</strong><small>Sisa dapat diretur</small></div><label>Jumlah kembali<NumberEntry aria-label={'Retur '+row.item} className="demo-qty" inputMode="numeric" placeholder="0"
            disabled={!row.remaining||row.sellingPrice===null} value={draft.quantities[row.id]??''} onValueChange={rawInput =>setDraft({...draft,quantities:{...draft.quantities,[row.id]:rawInput.replace(/\D/g,'').slice(0,9)}})}/></label></article>)}</div>
        <div className="demo-operation-facts"><article><span>Nilai retur</span><strong>{amountText(quote.value)}</strong></article>
          <article><span>Potong tagihan nota</span><strong>{amountText(quote.chargeReduction)}</strong></article><article><span>Kredit ke payroll</span><strong>{amountText(quote.credit)}</strong></article></div>
        <label>Tanggal fisik<input type="date" required min={doc.issuedOn} max={lastWarehouseDay()} value={draft.day} onChange={event=>setDraft({...draft,day:event.target.value})}/></label>
        <label>Alasan retur<textarea required minLength={4} maxLength={400} value={draft.reason} onChange={event=>setDraft({...draft,reason:event.target.value})}/></label>
        {(!quote.valid||error)&&<p role="alert">{!quote.valid?'Periksa sisa jumlah yang dapat diretur.':error}</p>}
        <footer><button className="primary-btn" disabled={!quote.valid||!quote.lines.length}>Simpan retur mandor</button></footer>
      </form>
    </ReasonDialog>}
  </section>
}
