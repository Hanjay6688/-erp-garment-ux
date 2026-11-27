import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { Ruler } from 'lucide-react'
import { formatQuantity } from './format'
import { readPocketNumber } from './pocketUsage'
import { ReasonDialog } from './planner/ReasonDialog'
import type { ReceiptRoll } from './receiptRollCorrection'

export function ReceiptRollEditor({roll,receipt,unit,onSave,onClose}:{
  roll:ReceiptRoll;receipt:string;unit:'yd'|'m';onSave:(input:{id:string;code:string;length:number;reason:string;at:string})=>void;onClose:()=>void
}) {
  const [code,setCode]=useState(roll.physicalCode??roll.id)
  const [length,setLength]=useState(String(roll.length).replace('.',','))
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  const [id]=useState(()=>crypto.randomUUID())
  const parsed=readPocketNumber(length)
  return <ReasonDialog title="Koreksi roll penerimaan" closeLabel="Kembali" className="demo-operation-dialog money-dialog" icon={<Ruler/>} onClose={onClose}>
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      try {onSave({id,code,length:parsed,reason,at:new Date().toISOString()});onClose()}
      catch(failure){setError((failure as Error).message)}
    }}>
      <p><strong>{roll.physicalCode??roll.id}</strong> · {receipt}</p>
      <div className="demo-operation-fields">
        <label>Nomor roll fisik<input value={code} required maxLength={90} onChange={event=>setCode(event.target.value)}/></label>
        <label>Panjang benar ({unit})<NumberEntry inputMode="decimal" value={length} required onValueChange={rawInput =>setLength(rawInput)}/></label>
      </div>
      <div className="demo-operation-facts"><article><span>Panjang semula → hasil koreksi</span>
        <strong>{formatQuantity(roll.length)} → {Number.isFinite(parsed)?formatQuantity(parsed):'—'} {unit}</strong></article></div>
      <label>Alasan koreksi<textarea required minLength={4} maxLength={500} value={reason} onChange={event=>setReason(event.target.value)}/></label>
      {error&&<p role="alert">{error}</p>}
      <footer><button className="primary-btn">Simpan koreksi roll</button></footer>
    </form>
  </ReasonDialog>
}
