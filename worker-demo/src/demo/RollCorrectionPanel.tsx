import { useState } from 'react'
import { ArrowRight, History, Ruler } from 'lucide-react'
import { amountText } from './accessoryPricing'
import { cutDay, cutRolls, correctionRolls, originalCutLots, physicalRollId, yardsLeft, type RollCorrection, type Session } from './planner/model'
import { changeSession, usePlannerSession } from './planner/session'
import { ReasonDialog } from './planner/ReasonDialog'
import './demoCorrection.css'

const yard = (qty:number) => qty.toLocaleString('id-ID',{maximumFractionDigits:6}) + ' yd'
function sources(session:Session) {
  const rollsById=new Set(correctionRolls(session).map(roll=>roll.id))
  return originalCutLots(session).flatMap(lot=>cutRolls(lot).flatMap(roll=>{
    const current=physicalRollId(lot.id,roll.id,session)
    return rollsById.has(current) && roll.usedYards>0 ? [{key:lot.id+'|'+roll.id,lot,roll,current}] : []
  }))
}

function alternatives(session:Session,source:ReturnType<typeof sources>[number]) {
  const at=cutDay(source.lot)
  return correctionRolls(session).filter(roll=>roll.id!==source.current && roll.day<=at && yardsLeft(roll.id,session)>=source.roll.usedYards)
}

function evaluateSwitch(session:Session,sourceKey:string,destination:string,reason:string) {
  const source=sources(session).find(row=>row.key===sourceKey)
  const target=source && alternatives(session,source).find(roll=>roll.id===destination)
  if (!source || !target || reason.trim().length<4) throw Error('Pilih pemakaian, roll yang cukup saat potong, dan isi alasan.')
  const from=correctionRolls(session).find(roll=>roll.id===source.current)!
  const qty=source.roll.usedYards
  const beforeFrom=yardsLeft(from.id,session)
  const beforeTo=yardsLeft(target.id,session)
  const correction = {
    cut:source.lot.id, original:source.roll.id, from:from.id, to:target.id, yards:qty, reason:reason.trim(),
    costDifference: from.rate!==undefined && target.rate!==undefined ? Math.round(qty*(target.rate-from.rate)*100)/100 : null,
  }
  return {correction,from,target,beforeFrom,beforeTo,cutDate:cutDay(source.lot)}
}

export default function RollCorrectionPanel() {
  const session=usePlannerSession()
  const [open,setOpen]=useState(()=>new URLSearchParams(location.search).get('koreksi')==='ganti-roll')
  const [sourceKey,setSource]=useState(()=>{
    const params=new URLSearchParams(location.search)
    return sources(session).find(row=>row.lot.id===params.get('pot')&&(!params.has('roll')||row.current===params.get('roll')))?.key??''
  })
  const [destination,setDestination]=useState('')
  const [reason,setReason]=useState('')
  const [review,setReview]=useState<ReturnType<typeof evaluateSwitch>|null>(null)
  const [message,setMessage]=useState('')
  const [error,setError]=useState('')
  const issues=sources(session)
  const source=issues.find(row=>row.key===sourceKey)
  const choices=source ? alternatives(session,source) : []
  const history=session.rollCorrections??[]
  const linkedEvent=new URLSearchParams(location.search).get('switch')
  function resetReview(){setReview(null);setError('')}
  function post() {
    if(!review) return
    try {
      const id=crypto.randomUUID()
      changeSession(live=>{
        const latest=evaluateSwitch(live,sourceKey,destination,reason)
        if(JSON.stringify(latest)!==JSON.stringify(review))throw Error('Saldo atau sumber berubah. Tinjau dampaknya sekali lagi.')
        const event:RollCorrection={...latest.correction,id,at:new Date().toISOString()}
        return {...live,rollCorrections:[...(live.rollCorrections??[]),event]}
      })
      setDestination('');setReason('');setReview(null);setOpen(false)
      setMessage('Sumber '+review.correction.cut+' dipindah ke '+review.correction.to+'. Saldo kedua roll diperbarui.')
    } catch(failure) { setError((failure as Error).message) }
  }
  return <section className="panel roll-correction" aria-label="Ganti roll sumber pemakaian">
    <div className="demo-operation-heading"><i><Ruler aria-hidden="true"/></i><div><h3>Switch Roll</h3>
      <p>Pilih pemakaian di Potongan, lalu pilih roll yang benar-benar dipakai. Tinjau perubahan saldo dan selisih biaya kain.</p></div></div>
    <button type="button" className="primary-btn" onClick={()=>{setOpen(true);resetReview()}}>Buka Ganti roll <ArrowRight aria-hidden="true"/></button>
    {message&&<p className="wh-feedback" role="status">{message}</p>}
    {history.length>0&&<details className="demo-operation-history" id="riwayat-ganti-roll" open={!!linkedEvent||undefined}><summary><History size={15} aria-hidden="true"/> Riwayat Ganti roll ({history.length})</summary>
      {[...history].reverse().map(event=><article key={event.id} ref={node=>{if(node && event.id===linkedEvent)node.scrollIntoView({block:'center'})}} data-source-selected={event.id===linkedEvent||undefined}><strong>{yard(event.yards)}</strong>
        <span>{event.cut} · {event.from} → {event.to}</span><small>{event.reason}</small></article>)}</details>}
    {open&&<ReasonDialog title="Ganti roll sumber pemakaian" closeLabel="Kembali" onClose={()=>setOpen(false)} className="demo-operation-dialog money-dialog" icon={<Ruler/>}>
      <div className="demo-operation-form">
        <label>Pemakaian yang dikoreksi<select value={sourceKey} onChange={event=>{setSource(event.target.value);setDestination('');resetReview()}}>
          <option value="">Pilih potongan dan roll</option>{issues.map(row=><option key={row.key} value={row.key}>{yard(row.roll.usedYards)} · {row.current} · {row.lot.id}</option>)}
        </select></label>
        {source&&<label>Roll yang dipakai fisik<select value={destination} onChange={event=>{setDestination(event.target.value);resetReview()}}>
          <option value="">Pilih roll pengganti</option>{choices.map(roll=><option key={roll.id} value={roll.id}>{roll.physicalCode??roll.id} · {roll.material} · {yard(yardsLeft(roll.id,session))}</option>)}
        </select>{!choices.length&&<small>Belum ada roll dengan tanggal masuk dan saldo yang sesuai.</small>}</label>}
        <label>Alasan ganti roll<textarea value={reason} maxLength={500} onChange={event=>{setReason(event.target.value);resetReview()}}/></label>
        {review&&<section aria-label="Dampak Ganti roll">
          <div className="demo-operation-facts">
            <article><small>Roll semula · {review.from.material}</small><strong>{yard(review.beforeFrom)} → {yard(review.beforeFrom+review.correction.yards)}</strong><span>{review.from.id} · {review.from.source}</span></article>
            <article><small>Roll fisik · {review.target.material}</small><strong>{yard(review.beforeTo)} → {yard(review.beforeTo-review.correction.yards)}</strong><span>{review.target.id} · {review.target.source}</span></article>
          </div>
          <p><strong>{yard(review.correction.yards)}</strong> dipindah untuk {review.correction.cut} · {review.cutDate}.</p>
          <p>Selisih biaya kain latihan <strong>{review.correction.costDifference===null?'Harga belum tersedia':amountText(review.correction.costDifference)}</strong></p>
        </section>}
        {error&&<p role="alert">{error}</p>}
        <footer>{review?<button className="primary-btn" onClick={post}>Simpan Ganti roll</button>:<button className="primary-btn" disabled={!destination||reason.trim().length<4}
          onClick={()=>{try{setReview(evaluateSwitch(session,sourceKey,destination,reason));setError('')}catch(failure){setError((failure as Error).message)}}}>Tinjau dampak Ganti roll</button>}</footer>
      </div>
    </ReasonDialog>}
  </section>
}
