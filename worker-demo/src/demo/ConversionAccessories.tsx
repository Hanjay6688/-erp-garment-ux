import NumberEntry from '../../../src/components/NumberEntry'
import { useState, type FormEvent } from 'react'
import { Boxes, PackageOpen, Plus, Scissors, Trash2, Undo2 } from 'lucide-react'
import { accessoryStockAt, amountText, mainAccessories, serviceAccessories, type AccessoryLocation, useAccessoryBook } from './accessoryPricing'
import { accessoryPcs, kitCost, receiveConversionAccessories, receivedConversionAccessories, reverseConversionAccessories, type ConversionAccessoryDraft } from './conversionAccessories'
import type { ConversionReturn, Session, StockEvent } from './planner/model'
import { ReasonDialog } from './planner/ReasonDialog'
import { changeSession } from './planner/session'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

export function ConversionAccessoryFields({value,onChange,session}:{value:ConversionAccessoryDraft;onChange:(value:ConversionAccessoryDraft)=>void;session:Session}) {
  const book=useAccessoryBook()
  const items=book.items.filter(item=>item.active&&item.stockUom.toLowerCase()==='pcs')
  function options(location?:AccessoryLocation) {
    return <><option value="">Pilih aksesori</option>{items.map(item=><option key={item.code} value={item.code}>
      {item.name}{location?' · '+accessoryStockAt(item,location,session).toLocaleString('id-ID')+' pcs':''}
    </option>)}</>
  }
  return <div className="conversion-accessory-sections">
    <section aria-label="Aksesori dipakai">
      <div className="demo-operation-heading"><i><Scissors aria-hidden="true"/></i><div><h3>Aksesori dipakai</h3><p>Keluar dari stok aksesori saat konversi disimpan.</p></div></div>
      {value.used.map((line,index)=><div key={index} className="conversion-accessory-line expected">
        <label>Aksesori pengganti<select value={line.code} onChange={event=>onChange({...value,used:value.used.map((row,i)=>i===index?{...row,code:event.target.value}:row)})}>{options(line.location??mainAccessories)}</select></label>
        <label>Jumlah dipakai (pcs)<NumberEntry inputMode="numeric" value={line.qty} onValueChange={rawInput =>onChange({...value,used:value.used.map((row,i)=>i===index?{...row,qty:rawInput}:row)})}/></label>
        <label>Lokasi stok sumber<select value={line.location??mainAccessories} onChange={event=>onChange({...value,used:value.used.map((row,i)=>i===index?{...row,location:event.target.value as AccessoryLocation}:row)})}>
          {[mainAccessories,serviceAccessories].map(location=><option key={location}>{location}</option>)}</select></label>
        <button type="button" className="soft-btn" aria-label={'Lepas aksesori pengganti '+(index+1)} onClick={()=>onChange({...value,used:value.used.filter((_,i)=>i!==index)})}><Trash2 size={16}/></button>
      </div>)}
      <button type="button" className="soft-btn" onClick={()=>onChange({...value,used:[...value.used,{code:'',qty:''}]})}><Plus size={16}/>Tambah aksesori dipakai</button>
    </section>
    <section aria-label="Aksesori bongkaran">
      <div className="demo-operation-heading"><i><PackageOpen aria-hidden="true"/></i><div><h3>Aksesori bongkaran</h3><p>Catat perkiraan bila perlu. Penerimaan bisa dilakukan belakangan dari <a href="/gudang/aksesori/?tab=bongkaran">Aksesori → Bongkaran</a>.</p></div></div>
      {value.expected.map((line,index)=><div key={index} className="conversion-accessory-line expected">
        <label>Aksesori yang ditunggu<select value={line.code} onChange={event=>onChange({...value,expected:value.expected.map((row,i)=>i===index?{...row,code:event.target.value}:row)})}>{options()}</select></label>
        <label>Jumlah ditunggu (pcs)<NumberEntry inputMode="numeric" value={line.qty} onValueChange={rawInput =>onChange({...value,expected:value.expected.map((row,i)=>i===index?{...row,qty:rawInput}:row)})}/></label>
        <label>Pemegang bongkaran<input value={line.holder} maxLength={120} onChange={event=>onChange({...value,expected:value.expected.map((row,i)=>i===index?{...row,holder:event.target.value}:row)})}/></label>
        <button type="button" className="soft-btn" aria-label={'Lepas aksesori bongkaran '+(index+1)} onClick={()=>onChange({...value,expected:value.expected.filter((_,i)=>i!==index)})}><Trash2 size={16}/></button>
      </div>)}
      <button type="button" className="soft-btn" onClick={()=>onChange({...value,expected:[...value.expected,{code:'',qty:'',holder:''}]})}><Plus size={16}/>Tambah aksesori bongkaran</button>
    </section>
  </div>
}

type ReceiptDraft = { doc:StockEvent; code:string; name:string; good:string; damaged:string; day:string; reason:string; id:string }
export function ConversionAccessoryHistory({session}:{session:Session}) {
  const [receipt,setReceipt]=useState<ReceiptDraft|null>(null)
  const [undo,setUndo]=useState<ConversionReturn|null>(null)
  const [undoReason,setUndoReason]=useState('')
  const [message,setMessage]=useState('')
  const [error,setError]=useState('')
  const docs=(session.stockEvents??[]).filter(doc=>doc.action==='convert'&&doc.kit)
  if(!docs.length)return null
  function post(event:FormEvent) {
    event.preventDefault()
    if(!receipt)return
    try {
      changeSession(live=>receiveConversionAccessories(live,{
        id:receipt.id,conversion:receipt.doc.id,code:receipt.code,day:receipt.day,reason:receipt.reason.trim(),
        good:accessoryPcs(receipt.good||'0'),damaged:accessoryPcs(receipt.damaged||'0'),
      }))
      setReceipt(null);setMessage('Penerimaan bongkaran tercatat dan saldo layak pakai diperbarui.')
    }catch(failure){setError((failure as Error).message)}
  }
  return <section className="panel conversion-accessory-history" id="aksesori-konversi" aria-labelledby="conversion-accessory-title">
    <div className="demo-operation-heading"><i><Boxes aria-hidden="true"/></i><div><h2 id="conversion-accessory-title">Aksesori dari Ganti Merek</h2>
      <p>Lihat pemakaian dan terima hasil bongkaran dari konversi terkait.</p></div></div>
    {[...docs].reverse().map(doc=>{
      const kit=doc.kit!
      const reversed=session.stockEvents?.some(event=>event.reverses===doc.id)
      const [from]=doc.changes.filter(row=>row.delta<0), [to]=doc.changes.filter(row=>row.delta>0)
      return <article className="conversion-accessory-document" key={doc.id} aria-label={from.key+' ke '+to.key}>
        <header><div><h3>{from.key} → {to.key}</h3><small>{doc.date} · {doc.reason}</small></div>
          <strong>{reversed?'Dibalik':doc.changes.reduce((sum,row)=>sum+Math.max(0,row.delta),0)+' pcs'}</strong></header>
        {kit.used.length>0&&<div className="conversion-used"><strong>Biaya aksesori dipakai · {amountText(kitCost(kit))}</strong>
          {kit.used.map(line=><small key={line.code+'|'+line.location}>{line.name} · {line.qty} pcs × {amountText(line.rate)} · {line.location??mainAccessories}</small>)}</div>}
        {kit.expected.map(line=>{
          const received=receivedConversionAccessories(session,doc.id,line.code)
          const left=line.qty-received.good-received.damaged-received.pending
          return <div className="conversion-return-line" key={line.code}>
            <div><strong>{line.name}</strong><small>{line.holder} · {received.good} pcs layak · {received.damaged} pcs rusak</small></div>
            <b>{left} pcs ditunggu</b>
            {received.pending>0&&<small>{received.pending} pcs menunggu pemeriksaan</small>}
            {!reversed&&left>received.held&&<button type="button" className="soft-btn" onClick={()=>{setError('');setReceipt({doc,code:line.code,name:line.name,good:'',damaged:'',day:lastWarehouseDay(),reason:'',id:crypto.randomUUID()})}}>Terima bongkaran</button>}
          </div>
        })}
        {(session.conversionReturns??[]).filter(row=>row.conversion===doc.id).map(row=><div key={row.id} className="conversion-return-log">
          <small>{row.day} · {row.good} pcs layak · {row.damaged} pcs rusak · {row.reversed?'Dibalik · '+row.reversed:row.reason}</small>
          {!row.reversed&&<button type="button" className="soft-btn" onClick={()=>{setError('');setUndoReason('');setUndo(row)}}><Undo2 size={15}/>Balikkan penerimaan</button>}
        </div>)}
      </article>
    })}
    {message&&<p role="status">{message}</p>}
    {receipt&&<ReasonDialog title="Terima aksesori bongkaran" closeLabel="Kembali" onClose={()=>setReceipt(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={post}>
        <h3>{receipt.name}</h3>
        <div className="demo-operation-fields">
          <label>Layak pakai (pcs)<NumberEntry inputMode="numeric" value={receipt.good} onValueChange={rawInput =>setReceipt({...receipt,good:rawInput})}/></label>
          <label>Rusak (pcs)<NumberEntry inputMode="numeric" value={receipt.damaged} onValueChange={rawInput =>setReceipt({...receipt,damaged:rawInput})}/></label>
        </div>
        <label>Tanggal kembali<input required type="date" max={lastWarehouseDay()} min={receipt.doc.date} value={receipt.day} onChange={event=>setReceipt({...receipt,day:event.target.value})}/></label>
        <label>Catatan pemeriksaan<textarea required maxLength={400} value={receipt.reason} onChange={event=>setReceipt({...receipt,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Sahkan penerimaan bongkaran</button></footer>
      </form>
    </ReasonDialog>}
    {undo&&<ReasonDialog title="Balikkan penerimaan bongkaran" closeLabel="Kembali" onClose={()=>setUndo(null)} className="demo-operation-dialog">
      <div className="demo-operation-form"><label>Alasan pembalikan<textarea value={undoReason} onChange={event=>setUndoReason(event.target.value)}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn" disabled={!undoReason.trim()} onClick={()=>{
          try{changeSession(live=>reverseConversionAccessories(live,undo.id,undoReason));setUndo(null);setMessage('Pembalikan penerimaan bongkaran tercatat.')}
          catch(failure){setError((failure as Error).message)}
        }}>Simpan pembalikan</button></footer></div>
    </ReasonDialog>}
  </section>
}
