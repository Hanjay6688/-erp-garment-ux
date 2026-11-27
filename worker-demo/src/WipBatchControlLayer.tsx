import NumberEntry from '../../src/components/NumberEntry'
import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, LockKeyhole, Minus, Plus,
  RotateCcw, SlidersHorizontal, Undo2, X,
} from 'lucide-react'
import {sourceChoices,sourceCode,type CountOperation} from './demo/planner/recountDistribution'
import type {Source} from './demo/planner/distribution'
import {lastWarehouseDay} from './demo/warehouseDay'
import './wip-control.css'

export type WipControlMode = 'adjust' | 'reverse'
export type WipControlQty = number[]

export type WipControlBatch = {
  id: string
  number: number
  revision:number
  mandor:string
  at:string
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
  sources:Source[]
  sizeLabels: string[]
  batches: WipControlBatch[]
}

export type WipControlResult =
  | {kind:'ADJUST';operation:CountOperation;note:string;sizesByBatch:Record<string,WipControlQty>;chosen:Record<string,string>;physical:string}
  | {kind:'PARTIAL';note:string;sizes:WipControlQty;mandorNote:string;physical:string}
  | {kind:'REVERSE';note:string;physical:string}

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
  const [operation,setOperation] = useState<CountOperation|'PARTIAL'>(canRedistribute ? 'REDISTRIBUTION' : 'PHYSICAL_RECOUNT')
  const [drafts,setDrafts] = useState<Record<string,WipControlQty>>(()=>batchMap(parent))
  const [note,setNote] = useState('')
  const [physical,setPhysical]=useState(target.at>'2026-11-24T10:30'?target.at:'2026-11-24T10:30')
  const [chosen,setChosen]=useState<Record<string,string>>({})
  const [retained,setRetained]=useState([...target.sizes])
  const [mandorNote,setMandorNote]=useState(target.note)
  const [error,setError]=useState('')
  const sources=sourceChoices(parent.sources)
  const submit=(result:WipControlResult)=>{try{setError('');onApply(result)}catch(e){setError((e as Error).message)}}
  const physicalField=<label className="wip-control-note"><span>WAKTU FISIK (WIB)</span><input required type="datetime-local" min={target.at} max={lastWarehouseDay()+'T23:59'} value={physical} onChange={e=>setPhysical(e.target.value)}/></label>
  const reasonField=<label className="wip-control-note"><span>Alasan koreksi · wajib</span><textarea aria-label="Alasan koreksi" value={note} onChange={e=>setNote(e.target.value)} /></label>

  const originalTotals = useMemo<WipControlQty>(() => parent.sizeLabels.map((_,sizeIndex)=>parent.batches.reduce((sum,batch)=>sum+batch.sizes[sizeIndex],0)) as WipControlQty,[parent])
  const afterTotals = useMemo<WipControlQty>(() => parent.sizeLabels.map((_,sizeIndex)=>parent.batches.reduce((sum,batch)=>sum+(drafts[batch.id]?.[sizeIndex]??batch.sizes[sizeIndex]),0)) as WipControlQty,[drafts,parent])
  const changed = parent.batches.some((batch)=>batch.sizes.some((qty,sizeIndex)=>qty!==(drafts[batch.id]?.[sizeIndex]??qty)))
  const netDelta = total(afterTotals)-total(originalTotals)
  const redistributionExact = originalTotals.every((qty,index)=>qty===afterTotals[index])
  const valuesValid = parent.batches.every((batch)=>{
    const values=drafts[batch.id]??batch.sizes
    return values.every((qty)=>Number.isFinite(qty)&&qty>=0)&&total(values)>0
  })
  const noteValid = Boolean(note.trim())&&physical>=target.at&&physical<=lastWarehouseDay()+'T23:59'
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
    if(operation==='PARTIAL'){
      submit({kind:'PARTIAL',note:note.trim(),sizes:retained,mandorNote,physical});return
    }
    if(canApply)submit({kind:'ADJUST',operation,note:note.trim(),sizesByBatch:drafts,chosen,physical})
  }
  const confirmReverse = () => {
    if(!target||!noteValid)return
    submit({kind:'REVERSE',note:note.trim(),physical})
  }

  if(mode==='reverse')return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal reverse" role="alertdialog" aria-modal="true" aria-labelledby="wip-reverse-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>PRE-SEWING · BATCH DISTRIBUSI</span><h2 id="wip-reverse-title">Batalkan Batch Distribusi {String(target.number).padStart(2,'0')}?</h2><p>Batch Produksi {parent.id} · {target.id} · {target.qty} pcs</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>
      <div className="wip-reverse-impact"><Undo2/><div><strong>{target.qty} pcs kembali ke Bagi Potongan</strong><small>Form pembagian akan terbuka untuk Batch {target.number} ini. Lu bisa bagi sekarang atau menyusul.</small></div></div>
      <div className="wip-control-facts"><article><span>MANDOR</span><strong>{target.mandor}</strong></article><article><span>BATCH DISTRIBUSI</span><strong>{target.id}</strong></article><article><span>QTY KEMBALI</span><strong>{target.qty} pcs</strong></article></div>
      <div className="wip-control-facts">{parent.sizeLabels.map((size,i)=>target.sizes[i]>0&&<article key={size}><span>UKURAN {size}</span><strong>{target.sizes[i]} pcs</strong></article>)}</div>
      {physicalField}{reasonField}{error&&<p role="alert">{error}</p>}
      <footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className="danger-btn" disabled={!noteValid} onClick={confirmReverse}><Undo2/> Batalkan &amp; bagi ulang</button></footer>
    </section>
  </div>

  return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal" role="dialog" aria-modal="true" aria-labelledby="wip-adjust-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>WIP CONTROL · BATCH PRODUKSI</span><h2 id="wip-adjust-title">Koreksi Distribusi {parent.id}</h2><p>Fokus Batch Distribusi {String(target.number).padStart(2,'0')} · {parent.model} · {parent.material}</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>

      <div className="wip-operation-tabs" role="tablist" aria-label="Jenis penyesuaian">
        <button className={operation==='REDISTRIBUTION'?'active':''} disabled={!canRedistribute} onClick={()=>setOperation('REDISTRIBUTION')}><SlidersHorizontal/><span><strong>Redistribusi antar batch</strong><small>Total Batch Produksi wajib tetap sama</small></span></button>
        <button className={operation==='PHYSICAL_RECOUNT'?'active':''} onClick={()=>setOperation('PHYSICAL_RECOUNT')}><RotateCcw/><span><strong>Koreksi hasil fisik</strong><small>Total Batch Produksi dapat berubah</small></span></button>
        <button className={operation==='PARTIAL'?'active':''} onClick={()=>setOperation('PARTIAL')}><Undo2/><span><strong>Kembalikan sebagian</strong><small>Sisa tetap dibagikan ke mandor</small></span></button>
      </div>
      {operation==='PARTIAL'?<section className="dist-form wip-partial"><fieldset><legend>Jumlah yang tetap di mandor</legend><div className="dist-inputs">{parent.sizeLabels.map((size,i)=>target.sizes[i]>0&&<label key={size}>Ukuran {size}<NumberEntry type="number" min="0" max={target.sizes[i]} value={retained[i]} onValueChange={rawInput =>setRetained(retained.map((n,j)=>i===j?Number(rawInput):n))}/></label>)}</div></fieldset>
        <p>{target.qty-total(retained)} pcs kembali ke Bagi Potongan.</p><label>Arahan mandor (opsional)<input value={mandorNote} onChange={e=>setMandorNote(e.target.value)}/></label></section>:<>
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
            <div>{parent.sizeLabels.map((size,sizeIndex)=><label key={size}><span>SIZE {size}</span><div><button disabled={batch.locked} aria-label={`Kurangi ${batch.id} Size ${size}`} onClick={()=>updateQty(batch,sizeIndex,values[sizeIndex]-1)}><Minus/></button><NumberEntry disabled={batch.locked} inputMode="numeric" value={values[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onValueChange={rawInput =>updateQty(batch,sizeIndex,Number(rawInput.replace(/\D/g,'')))}/><button disabled={batch.locked} aria-label={`Tambah ${batch.id} Size ${size}`} onClick={()=>updateQty(batch,sizeIndex,values[sizeIndex]+1)}><Plus/></button></div><small>awal {batch.sizes[sizeIndex]}</small></label>)}</div>
          </article>
        })}</div>
      </section>

      {operation==='PHYSICAL_RECOUNT'&&parent.sizeLabels.map((size,i)=>{
        const choices=sources.filter(s=>s.size===size)
        if(afterTotals[i]<=originalTotals[i]||choices.length<2)return null
        return <label className="wip-control-note" key={size}>Asal tambahan ukuran {size}<select value={chosen[size]??''} onChange={e=>setChosen({...chosen,[size]:e.target.value})}><option value="">Pilih roll dan gambar</option>{choices.map(r=><option key={sourceCode(r)} value={sourceCode(r)}>{r.rollId} · gambar {r.slot}</option>)}</select></label>
      })}</>}
      {physicalField}{reasonField}{error&&<p role="alert">{error}</p>}
      {operation==='REDISTRIBUTION'&&changed&&!redistributionExact&&<p className="wip-control-hint">Jumlah tiap ukuran harus seimbang.</p>}
      <footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className="primary-btn" disabled={operation==='PARTIAL'?(!noteValid||total(retained)<1||retained.some((n,i)=>!Number.isSafeInteger(n)||n<0||n>target.sizes[i])||(total(retained)===target.qty&&mandorNote.trim()===target.note)):!canApply} onClick={confirm}>Simpan koreksi <ArrowRight/></button></footer>
    </section>
  </div>
}
