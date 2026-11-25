import { useState } from 'react'
import { ArrowRight, FileText, ListChecks, ShieldCheck, UserRound } from 'lucide-react'
import { allPayrollSources, readPayDrafts } from './payrollSources'
import { readNotes } from './issueDocuments'
import { laundryOutstanding, type LaundryDelivery } from './laundryModel'
import { applyBatch, total } from './planner/distribution'
import { changeSession } from './planner/session'
import { sewingGroups, type SewingGroup } from './sewingGroups'
import { pickupUrl } from './SewingTrace'
import { ReasonDialog } from './planner/ReasonDialog'
import './demoCorrection.css'

type Props={group:SewingGroup;deliveries:LaundryDelivery[];drafts:Record<string,string>;qc:{batchId:string}[];onCorrect:(ids:string[])=>void}
type Blocker={title:string;ref:string;href?:string}

function blockers({group,deliveries,drafts,qc}:Props):Blocker[] {
  const active=group.batches.filter(batch=>!batch.line.closed)
  const ids=new Set(active.map(batch=>batch.id))
  const rows:Blocker[]=[]
  for(const batch of active){
    if(total(batch.line.sources)!==batch.qty)rows.push({title:'Rincian roll dan gambar belum lengkap',ref:'Batch '+batch.number})
    if(drafts[batch.id])rows.push({title:'Draft surat kirim',ref:batch.id+' · '+drafts[batch.id],href:'/produksi/laundry/'})
    if(qc.some(row=>row.batchId===batch.id))rows.push({title:'Hasil QC / barang jadi',ref:batch.id,href:'/produksi/qc/'})
  }
  for(const delivery of deliveries.filter(row=>ids.has(row.batchId))){
    if(laundryOutstanding(delivery)>0||delivery.good+delivery.bs>0){rows.push({title:'Surat kirim atau penerimaan Laundry',ref:delivery.id,href:'/produksi/laundry/?tab=kembali'})}
    if(delivery.finalBills?.length||delivery.failedWashes?.some(row=>row.rate!==0))rows.push({title:'Harga aktual atau HPP Laundry',ref:delivery.id,href:'/produksi/laundry/?tab=kembali'})
  }
  const sources=allPayrollSources().filter(row=>row.kind==='FG'&&[row.doc.source,...(row.doc.regularCards??[]).map(card=>card.source)].some(source=>source.includes(group.id)))
  const sourceIds=new Set(sources.map(row=>row.doc.number))
  for(const note of sources)rows.push({title:'Nota FG posted',ref:note.doc.number,href:'/produksi/susun-nota-fg/?nota='+encodeURIComponent(note.doc.number)})
  const accessories=readNotes().filter(row=>row.status==='POSTED'&&row.productionBatch===group.id)
  for(const note of accessories)rows.push({title:'Nota ambil aksesori',ref:note.number,href:'/keuangan/nota-ambil-mandor/?nota='+encodeURIComponent(note.number)})
  const accessoryIds=new Set(accessories.map(row=>row.number))
  for(const payroll of readPayDrafts().filter(row=>row.status!=='REVERSED'&&(row.fgNotes.some(doc=>sourceIds.has(doc.number))||row.accessoryNotes.some(doc=>accessoryIds.has(doc.number))))){
    rows.push({title:'Payroll terkait',ref:payroll.number,href:'/keuangan/payroll-kasbon/?mandor='+encodeURIComponent(payroll.contractor)})
  }
  return rows
}

function wibTime() {
  return new Date(Date.now()+7*3600000).toISOString().slice(0,16)
}

export function MandorCorrectionDemo(props:Props) {
  const {group,onCorrect}=props
  const [open,setOpen]=useState(false)
  const [error,setError]=useState('')
  const [reason,setReason]=useState('')
  const [physical,setPhysical]=useState(wibTime)
  const [request,setRequest]=useState('')
  const active=group.batches.filter(batch=>!batch.line.closed)
  const pending=group.ledger.returns.filter(row=>group.ledger.events.some(event=>event.no===row.no&&event.reason.startsWith('Koreksi mandor · ')))
  const locks=open?blockers(props):[]
  const sewn=active.reduce((sum,row)=>sum+row.completed,0)
  if(!sewn&&!pending.length)return null
  function post() {
    try {
      changeSession(session=>{
        const live=sewingGroups(session).find(row=>row.id===group.id)
        if(!live)throw Error('PO asal tidak ditemukan.')
        if(blockers({...props,group:live,deliveries:session.laundry??props.deliveries}).length)throw Error('Masih ada dokumen pengunci pada PO ini.')
        const candidates=live.batches.filter(row=>!row.line.closed)
        if(reason.trim().length<4||candidates.length!==active.length||candidates.some((row,index)=>row.line.revision!==active[index]?.line.revision||row.id!==active[index]?.id)){
          throw Error('Periksa ulang batch yang masih aktif dan isi alasan koreksi.')
        }
        const recorded=new Date().toISOString()
        return candidates.reduce((next,row)=>applyBatch(next,{kind:'Reverse',mandorCorrection:true,id:request+'-'+row.number,group:live.id,no:row.number,
          revision:row.line.revision,physical,recorded,reason:'Koreksi mandor · '+reason.trim()}),session)
      })
      onCorrect(active.map(row=>row.id));setOpen(false)
    }catch(failure){setError((failure as Error).message)}
  }
  return <section className="demo-ops-card demo-mandor-correction" aria-label="Koreksi mandor sesudah jahit">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><UserRound/></i><div><h3>Koreksi mandor sesudah jahit</h3>
      <p>Periksa dokumen terkait sebelum membagi ulang PO.</p></div></div>
      {sewn>0&&<button type="button" className="soft-btn" onClick={()=>{setError('');setReason('');setRequest(crypto.randomUUID());setPhysical(wibTime());setOpen(true)}}><ListChecks size={16}/> Periksa koreksi mandor</button>}
    </header>
    {pending.length>0&&<div className="demo-operation-actions">{pending.map(row=><a key={row.no} className="soft-btn" href={pickupUrl(group.id,row.no)}>Batch {row.no} · Bagi ulang {total(row.sources)} pcs <ArrowRight size={16}/></a>)}</div>}
    {open&&<ReasonDialog title="Koreksi mandor seluruh PO" closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setOpen(false)}>
      <form className="demo-operation-form" onSubmit={event=>{event.preventDefault();post()}}><p>{group.model} · {group.id}</p>
        <div className="demo-operation-facts"><article><span>Kembali ke Bagi Potongan</span><strong>{active.reduce((sum,row)=>sum+row.qty,0)} pcs</strong><small>{active.length} batch aktif</small></article>
          <article><span>Jahit yang sudah tercatat</span><strong>{sewn} pcs</strong><small>{[...new Set(active.map(row=>row.line.mandor))].join(' · ')}</small></article></div>
        {locks.length>0?<section className="demo-operation-history"><div className="demo-operation-heading"><i><FileText/></i><div><h3>Dokumen yang mengunci PO</h3><p>Buka sumber untuk memeriksa pembalikan yang diperlukan.</p></div></div>
          {locks.map((lock,index)=><article key={lock.title+lock.ref+index}><strong>{lock.title}</strong>{lock.href?<a className="gar-text" href={lock.href}>{lock.ref}</a>:<small>{lock.ref}</small>}</article>)}</section>
          :<><p>Pilih mandor yang benar dari Bagi Potongan setelah koreksi. Pencatatan jahit untuk pembagian baru dimulai dari nol.</p>
          <label>Waktu fisik (WIB)<input required type="datetime-local" min={group.at} max={wibTime()} value={physical} onChange={event=>setPhysical(event.target.value)}/></label>
          <label>Alasan koreksi<textarea required minLength={4} maxLength={400} value={reason} onChange={event=>setReason(event.target.value)}/></label>
          {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn"><ShieldCheck size={16}/> Kembalikan seluruh PO</button></footer></>}
      </form>
    </ReasonDialog>}
  </section>
}
