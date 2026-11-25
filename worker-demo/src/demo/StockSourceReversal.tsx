import { useState } from 'react'
import { ArrowRight, Undo2 } from 'lucide-react'
import type { ReceiptReversal, StockSourceLink } from './receiptRollCorrection'
import { ReasonDialog } from './planner/ReasonDialog'
import './demoCorrection.css'

export function StockSourceReversal({label,title,document:documentNumber,blockers,reversal,onReverse}:{
  label:string;title?:string;document:string;blockers:StockSourceLink[];reversal?:ReceiptReversal;onReverse:(reason:string)=>void
}) {
  const [open,setOpen]=useState(false)
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  if(reversal)return <small className="stock-source-reversed">Dibalik · {reversal.reason}</small>
  return <div className="stock-source-reversal">
    <button className="soft-btn" type="button" onClick={()=>{setReason('');setError('');setOpen(true)}}><Undo2 aria-hidden="true"/> {label}</button>
    {blockers.length>0&&<small>{blockers.length} dokumen atau saldo perlu diperiksa</small>}
    {open&&<ReasonDialog title={title??label} closeLabel="Kembali" onClose={()=>setOpen(false)} className="demo-operation-dialog money-dialog" icon={<Undo2/>}>
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        if(blockers.length||reason.trim().length<4)return
        try{onReverse(reason.trim());setOpen(false)}
        catch(failure){setError((failure as Error).message)}
      }}>
        <p>{documentNumber}</p>
        {blockers.length?<section className="stock-source-blockers">
          <h3>Bereskan dokumen terkait dulu</h3>
          {blockers.map(({label,href})=><a className="soft-btn" key={href+label} href={href} onClick={()=>{
            setOpen(false)
            if(href.startsWith('#'))requestAnimationFrame(()=>document.getElementById(href.slice(1))?.scrollIntoView({block:'start'}))
          }}>{label} <ArrowRight aria-hidden="true"/></a>)}
        </section>:<>
          <label>Alasan pembalikan<textarea required minLength={4} maxLength={500} value={reason} onChange={event=>setReason(event.target.value)}/></label>
          <footer><button className="primary-btn" disabled={reason.trim().length<4}>Simpan pembalikan</button></footer>
        </>}
        {error&&<p role="alert">{error}</p>}
      </form>
    </ReasonDialog>}
  </div>
}
