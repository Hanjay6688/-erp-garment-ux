import { useState } from 'react'
import { ArrowRight, CalendarClock, ReceiptText } from 'lucide-react'
import { amountText, normalizeMandor } from './accessoryPricing'
import { pickupsIn, distribution, sampleGroup } from './planner/distribution'
import { readPlannerSession } from './planner/session'
import { laundryReadySeeds, laundryPhysicalTime } from './laundryModel'
import { sewingBatchId, sewingReceipts } from './sewingReceipts'
import { dayOk, lastWarehouseDay } from './warehouseDay'
import { ReasonDialog } from './planner/ReasonDialog'
import './demoCorrection.css'

type Choice='CARRY'|'EXPENSE'
type Decision={id:string;choice:Choice;reason:string;day:string;cost:number;allocated?:{start:string;end:string;qty:number;reason:string}}
type History=Record<string,Decision[]>
const key='erp.demo.attendance-cost-choice.v1'
const read=():History=>JSON.parse(sessionStorage.getItem(key)??'{}')
const copy={CARRY:'Bawa ke periode hasil jahit',EXPENSE:'Bebankan di periode ini'}

function recordedOutput(mandor:string,start:string,end:string) {
  const session=readPlannerSession()
  const eligible=(name:string,time:string)=>normalizeMandor(name)===normalizeMandor(mandor)&&time.slice(0,10)>=start&&time.slice(0,10)<=end
  return pickupsIn(session).reduce((sum,pickup)=>{
    const state=distribution(pickup,session)
    return sum+state.batches.filter(row=>!row.closed).reduce((qty,row)=>{
      const seed=sewingReceipts.find(source=>source.parent.id===pickup.id)?.parent.batches.find(source=>source.number===row.no)
      const batchId=sewingBatchId(pickup.id,row.no)
      const known=laundryReadySeeds.find(item=>item.id===batchId)?.sewingDoneAt
      const at=known?laundryPhysicalTime(known):row.at
      const initial=eligible(row.mandor,at)?seed?.completed??(pickup.id===sampleGroup&&row.no===1?1:0):0
      return qty+initial+state.events.reduce((count,event)=>count+(event.no===row.no&&event.proof==='Jahit'&&eligible(row.mandor,event.physical)?event.pcs??0:0),0)
    },0)
  },0)
}

export function AttendanceCostChoice({mandor,start,end,cost}:{mandor:string;start:string;end:string;cost:number}) {
  const id=[mandor,start,end].join('|')
  const [history,setHistory]=useState(read)
  const [form,setForm]=useState<{action:Choice|'ALLOCATE';start:string;end:string;reason:string}|null>(null)
  const [error,setError]=useState('')
  const decisions=history[id]??[]
  const current=decisions.at(-1)
  const output=recordedOutput(mandor,start,end)
  const targetQty=form?.action==='ALLOCATE'&&form.start&&form.end?recordedOutput(mandor,form.start,form.end):0
  const open=(action:Choice|'ALLOCATE')=>{setError('');setForm({action,start:'',end:'',reason:''})}
  if(!cost||output>0&&!current)return null
  function save() {
    if(!form)return
    const live=read(),old=live[id]??[],previous=old.at(-1)
    const reason=form.reason.trim()
    if(reason.length<4||previous?.allocated||recordedOutput(mandor,start,end)>0&&!previous){setError('Periksa hasil jahit pada periode asal dan isi alasan.');return}
    let next:Decision[]
    if(form.action==='ALLOCATE'){
      if(!previous||previous.choice!=='CARRY'||!dayOk(form.start)||!dayOk(form.end)||form.start<=end||form.end<form.start||!targetQty){setError('Pilih periode sesudahnya yang sudah memiliki hasil jahit.');return}
      next=[...old.slice(0,-1),{...previous,allocated:{start:form.start,end:form.end,qty:targetQty,reason}}]
    } else {
      if(previous?.choice===form.action){setError('Pilihan ini sudah berlaku untuk periode tersebut.');return}
      next=[...old,{id:crypto.randomUUID(),choice:form.action,day:lastWarehouseDay(),reason,cost}]
    }
    const updated={...live,[id]:next}
    sessionStorage.setItem(key,JSON.stringify(updated));setHistory(updated);setForm(null)
  }
  return <section className="panel demo-ops-panel" aria-label="Biaya absensi tanpa hasil jahit">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><CalendarClock/></i><div><h2>Biaya absensi tanpa hasil jahit</h2>
      <p>{mandor} · {start} – {end}</p></div></div></header>
    <div className="demo-operation-facts"><article><span>Biaya absensi terposting</span><strong>{amountText(cost)}</strong></article>
      <article><span>Hasil jahit periode asal</span><strong>{output.toLocaleString('id-ID')} pcs</strong></article></div>
    <div className="demo-ops-columns">{(['CARRY','EXPENSE'] as const).map(choice=><article className="demo-ops-card" key={choice}>
      <div className="demo-operation-heading"><i>{choice==='CARRY'?<ArrowRight/>:<ReceiptText/>}</i><div><h3>{copy[choice]}</h3>
        <p>{choice==='CARRY'?'Tahan biaya hingga ada periode yang memiliki hasil jahit.':'Masukkan biaya sebagai beban pada periode asal.'}</p></div></div>
      <div>{current?.choice===choice?<strong>Pilihan aktif</strong>:!current?.allocated&&<button type="button" className="soft-btn" onClick={()=>open(choice)}>{choice==='CARRY'?'Pilih bawa biaya':'Pilih beban periode'}</button>}</div>
    </article>)}</div>
    {current?.choice==='CARRY'&&!current.allocated&&<div><button type="button" className="primary-btn" onClick={()=>open('ALLOCATE')}>Alokasikan ke hasil jahit</button></div>}
    {decisions.length>0&&<details className="demo-operation-history"><summary>Riwayat keputusan</summary>{decisions.slice().reverse().map(row=><article key={row.id}>
      <strong>{copy[row.choice]} · {amountText(row.cost)}</strong><small>{row.day} · {row.reason}</small>
      {row.allocated&&<small>{row.allocated.start} – {row.allocated.end} · {row.allocated.qty} pcs · {row.allocated.reason}</small>}
    </article>)}</details>}
    {form&&<ReasonDialog title={form.action==='ALLOCATE'?'Alokasikan biaya ke periode hasil jahit':copy[form.action]} closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setForm(null)}>
      <form className="demo-operation-form" onSubmit={event=>{event.preventDefault();save()}}><p>{mandor} · {amountText(cost)} · {start} – {end}</p>
        {form.action==='ALLOCATE'&&<><div className="demo-operation-fields"><label>Mulai periode tujuan<input required type="date" max={lastWarehouseDay()} value={form.start} onChange={event=>setForm({...form,start:event.target.value})}/></label>
          <label>Akhir periode tujuan<input required type="date" max={lastWarehouseDay()} value={form.end} onChange={event=>setForm({...form,end:event.target.value})}/></label></div><p>Hasil jahit periode tujuan <strong>{targetQty} pcs</strong></p></>}
        <label>Alasan keputusan<textarea required minLength={4} maxLength={400} value={form.reason} onChange={event=>setForm({...form,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan keputusan</button></footer>
      </form>
    </ReasonDialog>}
  </section>
}
