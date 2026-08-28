import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, LockKeyhole, Minus, Plus,
  RotateCcw, ShieldCheck, SlidersHorizontal, Undo2, X,
} from 'lucide-react'
import './wip-control.css'

export type WipControlMode = 'adjust' | 'reverse'
export type WipControlQty = [number, number, number]

export type WipControlBatch = {
  id: string
  number: number
  qty: number
  sizes: WipControlQty
  completed: number
  note: string
  locked: boolean
  lockLabel?: string
}

export type WipControlParent = {
  id: string
  model: string
  material: string
  mandor: string
  sizeLabels: [string, string, string]
  batches: WipControlBatch[]
}

export type WipControlResult =
  | {
    kind: 'ADJUST'
    operation: 'REDISTRIBUTION' | 'PHYSICAL_RECOUNT'
    autoReasonCode: 'SIZE_SWAP' | 'PHYSICAL_RECOUNT'
    note: string
    sizesByBatch: Record<string, WipControlQty>
  }
  | {
    kind: 'REVERSE'
    batchId: string
    autoReasonCode: 'PRE_SEWING_REVERSAL'
    note: string
  }

type Props = {
  mode: WipControlMode
  parent: WipControlParent
  targetBatchId: string
  onClose: () => void
  onApply: (result: WipControlResult) => void
}

const total = (values: WipControlQty) => values.reduce((sum, value) => sum + value, 0)
const batchMap = (parent: WipControlParent) => Object.fromEntries(parent.batches.map((batch) => [batch.id, [...batch.sizes] as WipControlQty]))

export default function WipBatchControlLayer({ mode, parent, targetBatchId, onClose, onApply }: Props) {
  const editableBatches = parent.batches.filter((batch) => !batch.locked)
  const target = parent.batches.find((batch) => batch.id === targetBatchId) ?? parent.batches[0]
  const canRedistribute = editableBatches.length > 1
  const [operation,setOperation] = useState<'REDISTRIBUTION' | 'PHYSICAL_RECOUNT'>(canRedistribute ? 'REDISTRIBUTION' : 'PHYSICAL_RECOUNT')
  const [drafts,setDrafts] = useState<Record<string,WipControlQty>>(()=>batchMap(parent))
  const [note,setNote] = useState('')

  const originalTotals = useMemo<WipControlQty>(() => [0,1,2].map((sizeIndex)=>parent.batches.reduce((sum,batch)=>sum+batch.sizes[sizeIndex],0)) as WipControlQty,[parent])
  const afterTotals = useMemo<WipControlQty>(() => [0,1,2].map((sizeIndex)=>parent.batches.reduce((sum,batch)=>sum+(drafts[batch.id]?.[sizeIndex]??batch.sizes[sizeIndex]),0)) as WipControlQty,[drafts,parent])
  const changed = parent.batches.some((batch)=>batch.sizes.some((qty,sizeIndex)=>qty!==(drafts[batch.id]?.[sizeIndex]??qty)))
  const netDelta = total(afterTotals)-total(originalTotals)
  const redistributionExact = originalTotals.every((qty,index)=>qty===afterTotals[index])
  const valuesValid = parent.batches.every((batch)=>{
    const values=drafts[batch.id]??batch.sizes
    return values.every((qty)=>Number.isFinite(qty)&&qty>=0)&&total(values)>0
  })
  const noteValid = note.trim().length>=4
  const canApply = changed && valuesValid && noteValid && (operation==='PHYSICAL_RECOUNT'||(canRedistribute&&redistributionExact))

  const updateQty = (batch:WipControlBatch,sizeIndex:number,value:number) => {
    if(batch.locked)return
    setDrafts((current)=>({
      ...current,
      [batch.id]:(current[batch.id]??batch.sizes).map((qty,index)=>index===sizeIndex?Math.max(0,Math.round(value||0)):qty) as WipControlQty,
    }))
  }
  const reset = () => setDrafts(batchMap(parent))
  const confirm = () => {
    if(!canApply)return
    onApply({
      kind:'ADJUST', operation,
      autoReasonCode:operation==='REDISTRIBUTION'?'SIZE_SWAP':'PHYSICAL_RECOUNT',
      note:note.trim(), sizesByBatch:drafts,
    })
  }
  const confirmReverse = () => {
    if(!target||!noteValid)return
    onApply({kind:'REVERSE',batchId:target.id,autoReasonCode:'PRE_SEWING_REVERSAL',note:note.trim()})
  }

  if(mode==='reverse')return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal reverse" role="alertdialog" aria-modal="true" aria-labelledby="wip-reverse-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>PRE-SEWING · BATCH DISTRIBUSI</span><h2 id="wip-reverse-title">Batalkan Batch Distribusi {String(target.number).padStart(2,'0')}?</h2><p>Batch Produksi {parent.id} · {target.id} · {target.qty} pcs</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>
      <div className="wip-reverse-impact"><Undo2/><div><strong>Kuantitas kembali ke Batch Produksi</strong><small>Instruksi Mandor dan distribusi batch ini dibatalkan. Hasil potong produksi tetap ada dan dapat didistribusikan ulang.</small></div></div>
      <div className="wip-control-facts"><article><span>MANDOR</span><strong>{parent.mandor}</strong></article><article><span>BATCH DISTRIBUSI</span><strong>{target.id}</strong></article><article><span>QTY KEMBALI</span><strong>{target.qty} pcs</strong></article></div>
      <div className="wip-server-guard"><ShieldCheck/><span><strong>Server akan mengecek ulang dependency</strong><small>Satu pcs selesai dijahit, Laundry, QC, FG, BS, payroll, stok, atau jurnal aktif akan langsung memblokir aksi.</small></span></div>
      <label className="wip-control-note"><span>CATATAN SINGKAT · WAJIB</span><textarea autoFocus value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Contoh: salah batch mandor, bagi ulang."/><small>{note.trim().length}/4</small></label>
      <footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className="danger-btn" disabled={!noteValid} onClick={confirmReverse}><Undo2/> Batalkan distribusi</button></footer>
    </section>
  </div>

  return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal" role="dialog" aria-modal="true" aria-labelledby="wip-adjust-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>WIP CONTROL · BATCH PRODUKSI</span><h2 id="wip-adjust-title">Koreksi Distribusi {parent.id}</h2><p>Fokus Batch Distribusi {String(target.number).padStart(2,'0')} · {parent.model} · {parent.material}</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>

      <div className="wip-operation-tabs" role="tablist" aria-label="Jenis penyesuaian">
        <button className={operation==='REDISTRIBUTION'?'active':''} disabled={!canRedistribute} onClick={()=>setOperation('REDISTRIBUTION')}><SlidersHorizontal/><span><strong>Redistribusi antar batch</strong><small>Total Batch Produksi wajib tetap sama</small></span></button>
        <button className={operation==='PHYSICAL_RECOUNT'?'active':''} onClick={()=>setOperation('PHYSICAL_RECOUNT')}><RotateCcw/><span><strong>Koreksi hasil fisik</strong><small>Total Batch Produksi dapat berubah</small></span></button>
      </div>
      {!canRedistribute&&<div className="wip-control-hint"><AlertTriangle/><span><strong>Redistribusi belum tersedia untuk Batch Produksi ini.</strong> Hanya satu Batch Distribusi yang masih pre-sewing; batch lain sudah mempunyai bukti jahit. Koreksi fisik tetap dapat dilakukan.</span></div>}

      <div className="wip-father-equation">{parent.sizeLabels.map((size,index)=>{
        const delta=afterTotals[index]-originalTotals[index]
        return <article className={delta===0?'':delta>0?'positive':'negative'} key={size}><span>SIZE {size}</span><strong>{afterTotals[index]} pcs</strong><small>{originalTotals[index]} awal {delta===0?'· tetap':`· ${delta>0?'+':''}${delta}`}</small></article>
      })}<i><span>NET BATCH PRODUKSI</span><strong>{netDelta>0?'+':''}{netDelta} pcs</strong><small>{operation==='REDISTRIBUTION'?'wajib 0':'mengikuti cek fisik'}</small></i></div>

      <section className="wip-child-editor">
        <div className="wip-child-editor-head"><div><span>BATCH DISTRIBUSI DALAM PRODUKSI</span><strong>Ubah jumlah per size dan tulis catatan singkat</strong></div><button onClick={reset}><RotateCcw/> Reset</button></div>
        <div className="wip-child-list">{parent.batches.map((batch)=>{
          const values=drafts[batch.id]??batch.sizes
          const batchChanged=batch.sizes.some((qty,index)=>qty!==values[index])
          return <article className={`${batch.id===targetBatchId?'focus':''} ${batch.locked?'locked':''}`} key={batch.id}>
            <header><div><span>BATCH {String(batch.number).padStart(2,'0')} · {batch.id}</span><strong>{total(values)} pcs</strong><small>{batch.note}</small></div>{batch.locked?<em><LockKeyhole/> {batch.lockLabel||'Terkunci'}</em>:batchChanged?<em className="changed"><Check/> Berubah</em>:<em>Pre-sewing</em>}</header>
            <div>{parent.sizeLabels.map((size,sizeIndex)=><label key={size}><span>SIZE {size}</span><div><button disabled={batch.locked} aria-label={`Kurangi ${batch.id} Size ${size}`} onClick={()=>updateQty(batch,sizeIndex,values[sizeIndex]-1)}><Minus/></button><input disabled={batch.locked} inputMode="numeric" value={values[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateQty(batch,sizeIndex,Number(event.target.value.replace(/\D/g,'')))}/><button disabled={batch.locked} aria-label={`Tambah ${batch.id} Size ${size}`} onClick={()=>updateQty(batch,sizeIndex,values[sizeIndex]+1)}><Plus/></button></div><small>awal {batch.sizes[sizeIndex]}</small></label>)}</div>
          </article>
        })}</div>
      </section>

      <label className="wip-control-note"><span>CATATAN SINGKAT · WAJIB</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Contoh: hitung fisik ulang, Size 33 kurang 2 pcs."/><small>{note.trim().length}/4</small></label>
      <div className={`wip-control-validation ${canApply?'safe':'warn'}`}>{canApply?<ShieldCheck/>:<AlertTriangle/>}<span><strong>{!changed?'Belum ada angka yang berubah':!valuesValid?'Batch Distribusi tidak boleh 0; gunakan Batalkan Distribusi':operation==='REDISTRIBUTION'&&!redistributionExact?'Redistribusi belum seimbang per size':!noteValid?'Isi catatan singkat dulu':'Siap direview'}</strong><small>{operation==='REDISTRIBUTION'?'Sistem otomatis mencatat redistribusi; total Batch Produksi tidak berubah.':'Sistem otomatis mencatat koreksi fisik dan menjaga batas transaksi downstream.'}</small></span></div>
      <footer><span><small>INTERNAL AUDIT OTOMATIS</small><strong>{operation==='REDISTRIBUTION'?'Redistribusi batch':'Koreksi fisik'} · row-version checked</strong></span><button className="soft-btn" onClick={onClose}>Batal</button><button className="primary-btn" disabled={!canApply} onClick={confirm}>Terapkan simulasi <ArrowRight/></button></footer>
    </section>
  </div>
}
