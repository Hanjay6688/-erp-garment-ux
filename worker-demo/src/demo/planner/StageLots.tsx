import { useState } from 'react'
import { confirmDestination, day, lotLabel, lotPattern, lotSeries, lotsIn, productFor, seriesLabel, stageName } from './model'
import { changeSession, usePlannerSession } from './session'
import { DestinationChoice } from './ProductionAdvice'
import './planner.css'

export function StageLots({stage}:{stage:'sewing'|'laundry'|'qc'}) {
  const session=usePlannerSession()
  const params=new URLSearchParams(location.search)
  const [filter,setFilter]=useState(params.get('sku')??'')
  const [message,setMessage]=useState('')
  const lots=lotsIn(session).filter(l=>l.stage===stage)
  const shown=lots.filter(l=>!filter||l.sku===filter||session.destinations?.some(d=>d.id===l.id&&d.sku===filter))
  return <section className="panel gar-panel">
    <div className="gar-panel-head"><div><p className="gar-kicker">Pesanan November · Data contoh</p><h2>{stage==='sewing'?'Barang yang sedang dijahit':stage==='laundry'?'Barang yang sedang dicuci':'Barang yang sedang diperiksa'}</h2></div><a href="/analisis/planner/">Kembali ke Planner</a></div>
    {filter&&<button type="button" className="gar-text" onClick={()=>setFilter('')}>SKU {filter} · Tampilkan semua</button>}
    <ul className="gar-lots">{shown.map(l=>{
      const p=productFor(l.sku)
      return <li key={l.id} id={l.id}><div><strong>{l.kind==='elsewhere'?'Pesanan lain':lotLabel(l)} · {l.qty} pcs</strong><small>{l.id} · {l.place} · {seriesLabel(lotSeries(l))} · ukuran {l.size}</small></div>
        <div>{lotPattern(l).name} · {l.material}<small>{p?p.colour+' · '+p.finish:'Tujuan belum ditentukan'}</small></div>
        <div>Siap {day(l.eta)}<small>{p?(l.eta&&l.eta>p.due?'Lewat tenggat ':'Tenggat ')+day(p.due):''}</small>
          {(!l.sku||!l.eta)&&<DestinationChoice lot={l}/>}
          {p&&l.kind==='candidate'?<div className="gar-actions"><button type="button" className="gar-button" onClick={()=>{try{changeSession(s=>confirmDestination(s,l.id));setMessage(l.id+' · tujuan '+p.brand+' '+p.sku+' sudah pasti. '+l.qty+' pcs tetap di jahit.')}catch(e){setMessage((e as Error).message)}}}>Pastikan tujuan {p.sku}</button><button type="button" className="gar-button" onClick={()=>{try{changeSession(s=>confirmDestination(s,l.id,'elsewhere'));setMessage(l.id+' · '+l.qty+' pcs tetap dijahit untuk pesanan lain. Planner sudah menghitung ulang '+p.sku+'.')}catch(e){setMessage((e as Error).message)}}}>Untuk pesanan lain</button></div>:<small>{l.kind==='elsewhere'?'Tujuan pesanan lain':l.sku?'Tujuan pasti':'Tujuan belum ditentukan'} · {stageName[stage]}</small>}</div>
      </li>
    })}</ul>
    {message&&<p className="gar-success" role="status">{message}</p>}
    {!shown.length&&<p>Belum ada potongan untuk pilihan ini.</p>}
  </section>
}
