import { useState } from 'react'
import { ArrowRight, ChevronRight, History, LockKeyhole, RotateCcw, SlidersHorizontal } from 'lucide-react'
import { applyBatch, correctionLock, distribution, pickupsIn, returnId, total, type Batch, type Command } from './planner/distribution'
import { lotLabel, lotPattern, lotSeries, lotsIn, seriesLabel, type Session } from './planner/model'
import { changeSession, usePlannerSession } from './planner/session'
import { ReasonDialog } from './planner/ReasonDialog'
import './wipDistribution.css'

type Action='Reverse'|'Adjust'|'Proses'
type Selection={group:string;row:Batch;action:Action}
const count=(pcs:number)=>pcs+' pcs'
const label=(no:number)=>'Batch '+no
const pickupUrl=(id:string,no:number)=>'/produksi/bagi-potongan/?pot='+encodeURIComponent(returnId(id,no))
export function WipDistributionLedger(){
  const session=usePlannerSession()
  const [selection,setSelection]=useState<Selection|null>(null)
  const [notice,setNotice]=useState('')
  const [query,setQuery]=useState('')
  const origins=lotsIn(session)
  const groups=pickupsIn(session).map(p=>{
    const ledger=distribution(p,session)
    const origin=origins.find(l=>(l.originId??l.id)===p.id)
    return {ledger,origin}
  }).filter(({ledger,origin})=>[ledger.id,origin&&lotLabel(origin),origin?.material,...ledger.batches.map(b=>b.mandor)].join(' ').toLowerCase().includes(query.trim().toLowerCase()))
  return <section className="panel gar-panel dist-ledger" aria-label="Batch distribusi aktif">
    <div className="gar-panel-head"><div><p className="gar-kicker">Jahit · Distribusi mandor</p><h2>Batch distribusi</h2></div>
      {pickupsIn(session).length>1&&<label className="dist-search"><span>Cari batch produksi</span><input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Nomor, mandor, SKU…"/></label>}</div>
    {notice&&<p className="gar-success" role="status">{notice}</p>}
    {groups.map(({ledger,origin})=>{
      const active=ledger.batches.filter(b=>!b.closed)
      const waiting=ledger.returns.reduce((n,r)=>n+total(r.sources),0)
      return <article key={ledger.id} className="dist-group" aria-label={'Distribusi '+ledger.id}>
        <header className="dist-group-head"><div><h3>{ledger.id}{origin&&' · '+lotLabel(origin)}</h3>
          {origin&&<p>{lotPattern(origin).name} · {origin.material} · {seriesLabel(lotSeries(origin))}</p>}</div>
          <div className="dist-totals"><strong>{active.reduce((n,b)=>n+b.qty,0)} pcs di WIP</strong><span>{waiting} pcs di Bagi Potongan</span></div></header>
        {ledger.batches.map(b=>{
          const lock=correctionLock(b)
          const pending=ledger.returns.find(r=>r.no===b.no)
          const children=ledger.batches.filter(row=>row.previous===b.no)
          return <section className={'dist-row'+(b.closed?' dist-closed':'')} key={b.no} aria-label={ledger.id+' '+label(b.no)}>
            <div className="dist-row-head"><div><strong>{label(b.no)}</strong><span>{b.mandor}</span></div><div className={'dist-status '+(b.closed?'closed':b.proof?'locked':'waiting')}>{b.closed?(b.closed==='Reverse'?'Dibatalkan':'Disesuaikan'):b.proof?(b.proof==='Jahit'&&b.sewn===b.qty?'Selesai jahit':lock):'Menunggu jahit'}</div><strong>{count(b.qty)}</strong></div>
            {b.previous&&<small>Asal {label(b.previous)} · {ledger.id}</small>}
            {children.length>0&&<small>Terbagi ke {children.map(row=>label(row.no)+' ('+count(row.qty)+')').join(' dan ')}</small>}
            <div className="dist-controls"><details><summary>Ukuran & asal</summary><div className="dist-sizes">{Object.entries(b.sizes).filter(([,n])=>n>0).map(([size,n])=><div key={size}><small>Uk. {size}</small><strong>{count(n)}</strong></div>)}</div>
              {b.sources.length>0?<ul>{b.sources.map((r,i)=><li key={i}>{r.rollId} · slot gambar {r.slot} · ukuran {r.size} · {count(r.qty)}</li>)}</ul>:<p>Rincian gambar asal belum tersedia.</p>}
              <small>Diambil {b.at.replace('T',' ')} WIB{b.note?' · '+b.note:''}</small></details>
              {!b.closed&&<div className="dist-buttons"><button className="gar-button" disabled={Boolean(lock)} title={lock||undefined} onClick={()=>setSelection({group:ledger.id,row:b,action:'Adjust'})}><SlidersHorizontal/> Adjust</button>
                <button className="gar-button dist-reverse" disabled={Boolean(lock)} title={lock||undefined} onClick={()=>setSelection({group:ledger.id,row:b,action:'Reverse'})}><RotateCcw/> Reverse</button>
                {b.sewn<b.qty&&(!b.proof||b.proof==='Jahit')&&<button className="gar-button" onClick={()=>setSelection({group:ledger.id,row:b,action:'Proses'})}>Catat jahit</button>}</div>}</div>
            {!b.closed&&lock&&!b.proof&&<small className="dist-lock"><LockKeyhole/>{lock}</small>}
            {pending&&<a className="dist-link" href={pickupUrl(ledger.id,b.no)}>Bagi ulang {count(total(pending.sources))} <ArrowRight/></a>}
          </section>
        })}
        {ledger.events.length>0&&<details className="dist-history"><summary><History/> Riwayat distribusi ({ledger.events.length})</summary><ol>{ledger.events.map(e=><li key={e.id}><strong>{e.kind==='Proses'?e.proof:e.kind} · {label(e.no)}</strong>
          <span>{e.physical.replace('T',' ')} WIB{e.reason?' · '+e.reason:''}{e.pcs?' · '+count(e.pcs):''}</span>
          {e.released.length>0&&<span>Kembali ke Bagi Potongan · {count(total(e.released))}</span>}
          {e.created.length>0&&<span>{e.created.map(b=>label(b.no)+' · '+count(b.qty)).join(' / ')}</span>}</li>)}</ol></details>}
      </article>
    })}
    {!groups.length&&<p>Tidak ada batch yang cocok.</p>}
    {selection&&<CorrectionDialog key={selection.group+'-'+selection.row.no+'-'+selection.action} selection={selection} onClose={()=>setSelection(null)} onSaved={message=>{setNotice(message);setSelection(null)}}/>}
  </section>
}
function CorrectionDialog({selection,onClose,onSaved}:{selection:Selection;onClose:()=>void;onSaved:(message:string)=>void}){
  const {row,group,action}=selection
  const [reason,setReason]=useState('')
  const [note,setNote]=useState(row.note)
  const [sizes,setSizes]=useState({...row.sizes})
  const [pcs,setPcs]=useState('1')
  const [physical,setPhysical]=useState(row.at>'2026-11-24T10:30'?row.at:'2026-11-24T10:30')
  const [request]=useState(()=>crypto.randomUUID())
  const [error,setError]=useState('')
  const returned=row.qty-Object.values(sizes).reduce((n,x)=>n+x,0)
  const submit=()=>{
    const common={id:request,group,no:row.no,revision:row.revision,recorded:new Date().toISOString(),physical}
    const command:Command=action==='Reverse'?{...common,kind:'Reverse',reason}:action==='Adjust'?{...common,kind:'Adjust',reason,sizes,note}:{...common,kind:'Proses',proof:'Jahit',pcs:Number(pcs)}
    try{
      changeSession((current:Session)=>applyBatch(current,command))
      onSaved(action==='Reverse'?label(row.no)+' dibatalkan. '+count(row.qty)+' tersedia di Bagi Potongan.':action==='Adjust'?label(row.no)+' disesuaikan. '+count(returned)+' kembali ke Bagi Potongan.':count(Number(pcs))+' tercatat dijahit pada '+label(row.no)+'.')
    }catch(e){setError((e as Error).message)}
  }
  return <ReasonDialog title={(action==='Proses'?'Catat jahit':action)+' '+label(row.no)} onClose={onClose} closeLabel="Tutup">
    <form onSubmit={e=>{e.preventDefault();submit()}} className="dist-form">
      <p><strong>{group}</strong> · {row.mandor} · {count(row.qty)}</p>
      {action==='Reverse'&&<p>Seluruh isi {label(row.no)} kembali ke Bagi Potongan. Nomor dan rincian asalnya tetap ada di riwayat.</p>}
      {action==='Adjust'&&<><fieldset><legend>Jumlah yang tetap dibagikan</legend><div className="dist-inputs">{Object.entries(row.sizes).filter(([,n])=>n>0).map(([size,n])=><label key={size}>Ukuran {size}<input type="number" inputMode="numeric" min="0" max={n} value={sizes[size]??0} onChange={e=>setSizes({...sizes,[size]:Number(e.target.value)})}/><small>Asal {count(n)}</small></label>)}</div></fieldset><p>{count(returned)} kembali ke Bagi Potongan. Bagian yang tetap di mandor mendapat nomor batch pengganti.</p>
        <label>Catatan mandor (opsional)<input value={note} onChange={e=>setNote(e.target.value)}/></label></>}
      {action==='Proses'?<label>Tambahan selesai dijahit (pcs)<input type="number" min="1" max={row.qty-row.sewn} value={pcs} required onChange={e=>setPcs(e.target.value)}/></label>:<label>Alasan koreksi<input value={reason} onChange={e=>setReason(e.target.value)} required/></label>}
      <label>Waktu fisik (WIB)<input type="datetime-local" min={row.at} max="2026-11-24T23:59" value={physical} onChange={e=>setPhysical(e.target.value)} required/></label>
      {error&&<p role="alert">{error}</p>}<div className="dist-buttons"><button className="gar-button" type="button" onClick={onClose}>Kembali</button><button className="primary-btn" type="submit">{action==='Proses'?'Simpan hasil jahit':action==='Reverse'?'Konfirmasi reverse':'Simpan adjust'} <ChevronRight/></button></div>
    </form>
  </ReasonDialog>
}
