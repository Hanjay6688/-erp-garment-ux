import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, GitMerge, LockKeyhole, Minus, PencilLine, Plus,
  RotateCcw, Scissors, ShieldCheck, SlidersHorizontal, Undo2, X,
} from 'lucide-react'
import { splitCompletedBounds, validateWipSplit, WIP_SPLIT_ISSUE_LABEL } from './wipSplit'
import './wip-control.css'

export type WipControlMode = 'adjust' | 'reverse' | 'split' | 'note' | 'merge'
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
  /** Display number incl. split suffix, e.g. "02B". */
  label?: string
  /** For a split piece: label of the batch it merges back into. */
  sourceLabel?: string
  /** Labels the source and the new piece will carry after a split. */
  splitLabels?: { source: string; piece: string }
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
  | {
    kind: 'SPLIT'
    batchId: string
    moveSizes: WipControlQty
    completedMoved: number
    newNote: string
    sourceNote: string
    note: string
  }
  | { kind: 'NOTE'; batchId: string; nextNote: string; note: string }
  | { kind: 'MERGE'; batchId: string; note: string }

type Props = {
  mode: WipControlMode
  parent: WipControlParent
  targetBatchId: string
  onClose: () => void
  onApply: (result: WipControlResult) => void
}

const total = (values: WipControlQty) => values.reduce((sum, value) => sum + value, 0)
const batchMap = (parent: WipControlParent) => Object.fromEntries(parent.batches.map((batch) => [batch.id, [...batch.sizes] as WipControlQty]))
const labelOf = (batch: WipControlBatch) => batch.label ?? String(batch.number).padStart(2, '0')

export default function WipBatchControlLayer(props: Props) {
  if (props.mode === 'split') return <WipSplitLayer {...props}/>
  if (props.mode === 'note') return <WipNoteLayer {...props}/>
  if (props.mode === 'merge') return <WipMergeLayer {...props}/>
  return <WipAdjustLayer {...props}/>
}

function WipAdjustLayer({ mode, parent, targetBatchId, onClose, onApply }: Props) {
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
      <header><div><span>PRE-SEWING · BATCH DISTRIBUSI</span><h2 id="wip-reverse-title">Batalkan Batch Distribusi {labelOf(target)}?</h2><p>Batch Produksi {parent.id} · {target.id} · {target.qty} pcs</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>
      <div className="wip-reverse-impact"><Undo2/><div><strong>Kuantitas kembali ke Batch Produksi</strong><small>Instruksi Mandor dan distribusi batch ini dibatalkan. Hasil potong produksi tetap ada dan dapat didistribusikan ulang.</small></div></div>
      <div className="wip-control-facts"><article><span>MANDOR</span><strong>{parent.mandor}</strong></article><article><span>BATCH DISTRIBUSI</span><strong>{target.id}</strong></article><article><span>QTY KEMBALI</span><strong>{target.qty} pcs</strong></article></div>
      <div className="wip-server-guard"><ShieldCheck/><span><strong>Server akan mengecek ulang dependency</strong><small>Satu pcs selesai dijahit, Laundry, QC, FG, BS, payroll, stok, atau jurnal aktif akan langsung memblokir aksi.</small></span></div>
      <label className="wip-control-note"><span>CATATAN SINGKAT · WAJIB</span><textarea autoFocus value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Contoh: salah batch mandor, bagi ulang."/><small>{note.trim().length}/4</small></label>
      <footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className="danger-btn" disabled={!noteValid} onClick={confirmReverse}><Undo2/> Batalkan distribusi</button></footer>
    </section>
  </div>

  return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal" role="dialog" aria-modal="true" aria-labelledby="wip-adjust-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>WIP CONTROL · BATCH PRODUKSI</span><h2 id="wip-adjust-title">Koreksi Distribusi {parent.id}</h2><p>Fokus Batch Distribusi {labelOf(target)} · {parent.model} · {parent.material}</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>

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
            <header><div><span>BATCH {labelOf(batch)} · {batch.id}</span><strong>{total(values)} pcs</strong><small>{batch.note}</small></div>{batch.locked?<em><LockKeyhole/> {batch.lockLabel||'Terkunci'}</em>:batchChanged?<em className="changed"><Check/> Berubah</em>:<em>Pre-sewing</em>}</header>
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

function WipSplitLayer({ parent, targetBatchId, onClose, onApply }: Props) {
  const target = parent.batches.find((batch) => batch.id === targetBatchId) ?? parent.batches[0]
  const [moveSizes,setMoveSizes] = useState<WipControlQty>([0,0,0])
  const [completedText,setCompletedText] = useState<string|null>(null)
  const [newNote,setNewNote] = useState('')
  const [sourceNote,setSourceNote] = useState(target.note)
  const [reason,setReason] = useState('')
  const moved = total(moveSizes)
  const bounds = splitCompletedBounds(target.qty, target.completed, moved)
  // Until the user types a number, all sewn pcs that fit move with the piece.
  const completedMoved = completedText === null ? bounds.max : Number(completedText || 0)
  const issues = validateWipSplit({ sourceSizes:target.sizes, sourceCompleted:target.completed, moveSizes, completedMoved, newNote, sourceNote, reason })
  const setMove = (sizeIndex:number,value:number) => setMoveSizes((current)=>current.map((qty,index)=>index===sizeIndex?Math.min(target.sizes[index],Math.max(0,Math.round(value||0))):qty) as WipControlQty)
  const confirm = () => {
    if (issues.length > 0) return
    onApply({ kind:'SPLIT', batchId:target.id, moveSizes, completedMoved, newNote:newNote.trim(), sourceNote:sourceNote.trim(), note:reason.trim() })
  }
  return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal split" role="dialog" aria-modal="true" aria-labelledby="wip-split-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>PECAH BATCH · BATCH PRODUKSI {parent.id}</span><h2 id="wip-split-title">Pecah Batch Distribusi {labelOf(target)}</h2><p>{target.qty} pcs · {target.completed} pcs sudah dijahit · {parent.mandor} · arahan sekarang: {target.note}</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>
      <div className="wip-control-hint neutral"><Scissors/><span><strong>Pcs tidak bertambah atau hilang.</strong> Jumlah yang dipindah keluar dari batch asal dan menjadi batch baru dengan arahan sendiri (mis. warna cucian lain). Mandor, Pola, dan hasil jahit tetap tercatat.</span></div>
      <section className="wip-split-grid" aria-label="Jumlah pindah per size">{parent.sizeLabels.map((size,sizeIndex)=><label key={size}><span>SIZE {size}</span><div><button type="button" aria-label={`Kurangi pindah Size ${size}`} disabled={moveSizes[sizeIndex]<=0} onClick={()=>setMove(sizeIndex,moveSizes[sizeIndex]-1)}><Minus/></button><input inputMode="numeric" aria-label={`Pindah ke batch baru Size ${size}`} disabled={target.sizes[sizeIndex]===0} value={moveSizes[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setMove(sizeIndex,Number(event.target.value.replace(/\D/g,'')))}/><button type="button" aria-label={`Tambah pindah Size ${size}`} disabled={moveSizes[sizeIndex]>=target.sizes[sizeIndex]} onClick={()=>setMove(sizeIndex,moveSizes[sizeIndex]+1)}><Plus/></button></div><small>Asal {target.sizes[sizeIndex]} → tinggal <b>{target.sizes[sizeIndex]-moveSizes[sizeIndex]}</b> · baru <b>{moveSizes[sizeIndex]}</b></small></label>)}</section>
      <div className="wip-split-summary"><article><span>TETAP DI BATCH {target.splitLabels?.source ?? labelOf(target)}</span><strong>{target.qty-moved} pcs</strong><small>{target.completed-completedMoved} pcs sudah dijahit</small></article><ArrowRight/><article className="new"><span>BATCH BARU {target.splitLabels?.piece ?? ''}</span><strong>{moved} pcs</strong><small>{completedMoved} pcs sudah dijahit</small></article></div>
      <label className="wip-control-field"><span>PCS SUDAH DIJAHIT YANG IKUT PINDAH</span><input inputMode="numeric" value={completedText ?? String(bounds.max)} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setCompletedText(event.target.value.replace(/\D/g,''))}/><small>Boleh {bounds.min}–{bounds.max} pcs, supaya setiap batch tidak punya hasil jahit melebihi isinya. Total hasil jahit {parent.mandor} tetap {target.completed} pcs.</small></label>
      <div className="wip-split-notes"><label className="wip-control-field"><span>ARAHAN BATCH BARU {target.splitLabels?.piece ?? ''} · WAJIB</span><input value={newNote} onChange={(event)=>setNewNote(event.target.value)} placeholder="Contoh: BS bahan · cuci warna hitam"/></label><label className="wip-control-field"><span>ARAHAN BATCH {target.splitLabels?.source ?? labelOf(target)} (TETAP)</span><input value={sourceNote} onChange={(event)=>setSourceNote(event.target.value)} placeholder="Contoh: cuci warna putih"/></label></div>
      <label className="wip-control-note"><span>CATATAN SINGKAT · WAJIB</span><textarea value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Contoh: 25 pcs BS bahan, dipisah untuk dicuci hitam."/><small>{reason.trim().length}/4</small></label>
      <div className={`wip-control-validation ${issues.length===0?'safe':'warn'}`}>{issues.length===0?<ShieldCheck/>:<AlertTriangle/>}<span><strong>{issues.length===0?'Siap dipecah':WIP_SPLIT_ISSUE_LABEL[issues[0]]}</strong><small>Per size: tinggal + baru = asal. Riwayat pecah batch tercatat di kedua batch.</small></span></div>
      <footer><span><small>INTERNAL AUDIT OTOMATIS</small><strong>Pecah batch · total per size tetap</strong></span><button className="soft-btn" onClick={onClose}>Batal</button><button className="primary-btn" disabled={issues.length>0} onClick={confirm}><Scissors/> Pecah batch</button></footer>
    </section>
  </div>
}

function WipNoteLayer({ parent, targetBatchId, onClose, onApply }: Props) {
  const target = parent.batches.find((batch) => batch.id === targetBatchId) ?? parent.batches[0]
  const [nextNote,setNextNote] = useState(target.note)
  const [reason,setReason] = useState('')
  const valid = nextNote.trim().length > 0 && nextNote.trim() !== target.note && reason.trim().length >= 4
  return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal note" role="dialog" aria-modal="true" aria-labelledby="wip-note-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>ARAHAN MANDOR · BATCH DISTRIBUSI</span><h2 id="wip-note-title">Ubah arahan Batch {labelOf(target)}</h2><p>{parent.id} · {target.qty} pcs · {parent.mandor}</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>
      <label className="wip-control-field"><span>ARAHAN BARU · WAJIB</span><input autoFocus value={nextNote} onChange={(event)=>setNextNote(event.target.value)} placeholder="Contoh: cuci warna putih · obras rapat"/><small>Sebelumnya: {target.note}</small></label>
      <label className="wip-control-note"><span>CATATAN SINGKAT · WAJIB</span><textarea value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Contoh: owner minta ganti warna."/><small>{reason.trim().length}/4</small></label>
      <footer><span><small>INTERNAL AUDIT OTOMATIS</small><strong>Ubah arahan · riwayat tersimpan</strong></span><button className="soft-btn" onClick={onClose}>Batal</button><button className="primary-btn" disabled={!valid} onClick={()=>valid&&onApply({kind:'NOTE',batchId:target.id,nextNote:nextNote.trim(),note:reason.trim()})}><PencilLine/> Simpan arahan</button></footer>
    </section>
  </div>
}

function WipMergeLayer({ parent, targetBatchId, onClose, onApply }: Props) {
  const target = parent.batches.find((batch) => batch.id === targetBatchId) ?? parent.batches[0]
  const [reason,setReason] = useState('')
  const valid = reason.trim().length >= 4
  return <div className="wip-control-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wip-control-modal reverse" role="alertdialog" aria-modal="true" aria-labelledby="wip-merge-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>PECAH BATCH · BATALKAN</span><h2 id="wip-merge-title">Gabungkan Batch {labelOf(target)} kembali ke {target.sourceLabel ?? 'batch asal'}?</h2><p>{parent.id} · {target.qty} pcs · {target.completed} pcs sudah dijahit</p></div><button onClick={onClose} aria-label="Tutup"><X/></button></header>
      <div className="wip-reverse-impact"><GitMerge/><div><strong>Pcs dan hasil jahit kembali ke batch asal</strong><small>Batch {labelOf(target)} dihapus dari daftar; isi per size dan pcs sudah dijahit dijumlahkan lagi ke {target.sourceLabel ?? 'batch asal'}. Riwayatnya tetap tercatat.</small></div></div>
      <label className="wip-control-note"><span>CATATAN SINGKAT · WAJIB</span><textarea autoFocus value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Contoh: salah pecah, semua dicuci warna sama."/><small>{reason.trim().length}/4</small></label>
      <footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className="danger-btn" disabled={!valid} onClick={()=>valid&&onApply({kind:'MERGE',batchId:target.id,note:reason.trim()})}><GitMerge/> Gabungkan kembali</button></footer>
    </section>
  </div>
}
