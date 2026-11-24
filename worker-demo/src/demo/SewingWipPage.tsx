import '../wip-control.css'
import {StageLots} from './planner/StageLots'
import {Icon} from '../components/AppIcon'
import type {QcFinalResult} from '../QcFinalPage'
import type {WipControlMode,WipControlParent,WipControlResult} from '../WipBatchControlLayer'
import {deriveWipControlStatus} from '../wipControlPolicy'
import {MultiCheckFilter} from './controls'
import {browseMatch} from '../browseMatch'
import {cellQuantity} from './cuttingAllocation'
import {laundryOutstanding,summarizeLaundryBatch,laundryReadyFromRows,type LaundryDelivery,type LaundryReadyBatch,type LaundryView} from './laundryModel'
import {patternSnapshotLabel} from './productionModel'
import {laundryVendorNames} from './sewingModel'
import {downstreamLock,sewingGroups,sewingStatus,type SewingGroup,type SewingRow} from './sewingGroups'
import {BatchTrace,SewingHistory,pickupUrl} from './SewingTrace'
import {applyBatch,correctionLock,total,type Command,type Source} from './planner/distribution'
import {changeSession,usePlannerSession} from './planner/session'
import {RotateCcw,ShieldCheck,SlidersHorizontal,X} from 'lucide-react'
import {lazy,Suspense,useState} from 'react'

const WipBatchControlLayer=lazy(()=>import('../WipBatchControlLayer'))
type Target={group:string;id:string;no:number;revision:number;mode:WipControlMode;request:string;form:WipControlParent}

export function SewingWipPage({
  batchNotes,deliveries,finalizedResults,laundryDrafts,reverseNotice,onClearReverseNotice,
  onConfirmLaundry,onOpenLaundry,onOpenQc,
}:{
  batchNotes:string[];deliveries:LaundryDelivery[];finalizedResults:QcFinalResult[];laundryDrafts:Record<string,string>
  reverseNotice:string|null;onClearReverseNotice:()=>void
  onConfirmLaundry:(ready:LaundryReadyBatch)=>void
  onOpenLaundry:(id:string,vendor:string,view:LaundryView)=>void;onOpenQc:(group:string,id:string)=>void
}){
  const session=usePlannerSession(),parentGroups=sewingGroups(session)
  const [controlTarget,setControlTarget]=useState<Target|null>(null)
  const [controlNotice,setControlNotice]=useState<{title:string;message:string}|null>(null)
  const [completedInputs,setCompletedInputs]=useState<Record<string,string>>({})
  const [query,setQuery]=useState(()=>new URLSearchParams(location.search).get('cari')??'')
  const [patternFilter,setPatternFilter]=useState('')
  const [statusFilter,setStatusFilter]=useState<'ACTIVE'|'COMPLETED'|'ALL'>('ACTIVE')
  const [mandorFilter,setMandors]=useState<string[]|null>(null)
  const [pendingLaundry,setPendingLaundry]=useState<{batchId:string;vendor:string;qty:number}|null>(null)
  const mandorOptions=[...new Set(parentGroups.flatMap(p=>p.batches.map(b=>b.line.mandor)))]
  const selectedMandors=mandorFilter??mandorOptions
  const patternOptions=Array.from(new Map(parentGroups.flatMap(p=>p.pattern?[[p.pattern.id,p.pattern] as const]:[])).values())
  const recordedDownstream=(id:string)=>downstreamLock(id,deliveries,laundryDrafts,finalizedResults)
  const noteOf=(p:SewingGroup,b:SewingRow)=>p.id==='POT-260827-042'&&b.number<=3?(batchNotes[b.number-1]||b.note):b.note
  const completedOf=(b:SewingRow)=>Math.min(b.qty,completedInputs[b.id]===undefined?b.completed:cellQuantity(completedInputs[b.id]))
  function parentIsCompleted(p:SewingGroup){
    return !p.ledger.returns.length&&deriveWipControlStatus(p.batches.filter(b=>!b.line.closed).map(b=>{
      const summary=summarizeLaundryBatch(deliveries,b.id),finished=finalizedResults.some(r=>r.batchId===b.id&&r.completionStatus==='COMPLETE')
      return {finalSkuComplete:finished,unfinishedSewing:b.completed<b.qty,
        unsentReady:b.completed===b.qty&&!summary.returned&&!summary.outside&&!laundryDrafts[b.id],
        laundryDraft:!!laundryDrafts[b.id],laundryInTransit:summary.outside>0,unresolvedLaundryIssue:summary.outside>0,
        pendingFinalSkuHandoff:summary.returned>0&&!finished,openDependency:false,operatorActionRequired:false}
    }))==='COMPLETED'
  }
  const completedParentCount=parentGroups.filter(parentIsCompleted).length
  const visibleGroups=parentGroups.filter(p=>p.batches.some(b=>selectedMandors.includes(b.line.mandor))
    &&(!patternFilter||p.pattern?.id===patternFilter)
    &&browseMatch(query,p.id,p.model,p.material,p.plannedBrand,p.skuRef,p.pattern?.code,p.pattern?.name,p.pattern?.revision,...p.batches.flatMap(b=>[b.id,'Batch '+b.number,b.line.mandor,noteOf(p,b),sewingStatus(b.line,b.id,deliveries,laundryDrafts),...b.line.sources.map(s=>s.rollId)]))
    &&(statusFilter==='ALL'||(statusFilter==='COMPLETED')===parentIsCompleted(p)))
  const visibleBatches=visibleGroups.flatMap(p=>p.batches.filter(b=>!b.line.closed))
  const visibleQty=visibleBatches.reduce((n,b)=>n+b.qty,0)
  const visibleCompleted=visibleBatches.reduce((n,b)=>n+completedOf(b),0)
  const readyLaundryCount=visibleBatches.filter(b=>completedOf(b)===b.qty&&sewingStatus(b.line,b.id,deliveries,laundryDrafts)==='Siap laundry').length
  function startControl(p:SewingGroup,b:SewingRow,mode:WipControlMode){
    if(correctionLock(b.line)||recordedDownstream(b.id))return
    const form:WipControlParent={id:p.id,model:p.model,material:p.material,mandor:b.line.mandor,sizeLabels:p.sizes,
      sources:p.pickup.batches.flatMap(line=>line.sources??[]).filter((r):r is Source=>!!r.slot),
      batches:p.batches.filter(r=>!r.line.closed).map(row=>{
        const lockLabel=recordedDownstream(row.id)||correctionLock(row.line)
        return {...row,note:noteOf(p,row),at:row.line.at,mandor:row.line.mandor,revision:row.line.revision,lockLabel,locked:!!lockLabel}
      })}
    setControlTarget({group:p.id,id:b.id,no:b.number,revision:b.line.revision,mode,request:crypto.randomUUID(),form})
  }
  function applyWipControl(result:WipControlResult){
    const target=controlTarget
    if(!target)return
    if(recordedDownstream(target.id))throw Error('Batch sudah mempunyai bukti proses lanjutan.')
    const sizes=(values:number[])=>Object.fromEntries(target.form.sizeLabels.map((s,i)=>[s,values[i]]))
    const common={id:target.request,group:target.group,no:target.no,revision:target.revision,recorded:new Date().toISOString(),physical:result.physical,reason:result.note}
    let command:Command
    if(result.kind==='REVERSE')command={...common,kind:'Reverse'}
    else if(result.kind==='PARTIAL')command={...common,kind:'Adjust',sizes:sizes(result.sizes),note:result.mandorNote}
    else{
      const edited=target.form.batches.filter(b=>b.sizes.some((n,i)=>n!==result.sizesByBatch[b.id][i]))
      if(edited.some(b=>recordedDownstream(b.id)))throw Error('Salah satu batch sudah mempunyai bukti proses lanjutan.')
      command={...common,kind:'Koreksi',operation:result.operation,chosen:result.chosen,edits:edited.map(b=>({no:b.number,revision:b.revision,sizes:sizes(result.sizesByBatch[b.id])}))}
    }
    changeSession(s=>applyBatch(s,command))
    setControlTarget(null)
    if(result.kind==='REVERSE'){window.location.assign(pickupUrl(target.group,target.no));return}
    setControlNotice({title:'Koreksi tersimpan',message:target.group+' · Batch '+target.no})
  }
  function saveSewing(p:SewingGroup,b:SewingRow,value:string){
    const qty=cellQuantity(value)
    setCompletedInputs(current=>{const next={...current};delete next[b.id];return next})
    if(qty===b.completed)return
    try{
      if(qty<b.completed||qty>b.qty||recordedDownstream(b.id))throw Error('Periksa jumlah terhadap bukti jahit yang sudah tercatat.')
      changeSession(s=>applyBatch(s,{id:crypto.randomUUID(),group:p.id,no:b.number,revision:b.line.revision,kind:'Proses',
        proof:'Jahit',pcs:qty-b.completed,recorded:new Date().toISOString(),physical:b.line.at>'2026-11-24T10:30'?b.line.at:'2026-11-24T10:30'}))
    }catch(e){setControlNotice({title:'Jumlah jahit belum tersimpan',message:(e as Error).message})}
  }

  return <>
    <section className="hero-copy compact sewing-hero"><div className="eyebrow">PRODUKSI · SETELAH PICKUP</div><h1>WIP & Sewing</h1><p>Seluruh pekerjaan jahit dikelompokkan berdasarkan Batch Produksi. Mandor menyelesaikan setiap Batch Distribusi, lalu tujuan laundry dapat dipilih ketika kuantitas jahitan sudah penuh.</p></section>
    <StageLots stage="sewing"/>
    <div className="sewing-simulation-strip"><ShieldCheck/><strong>DATA SIMULASI</strong><span>Pilih batch untuk mencatat jahit atau mengubah pembagiannya.</span></div>
    {reverseNotice&&<div className="sewing-reverse-notice"><Icon name="reset"/><div><strong>Kembali ke WIP</strong><span>{reverseNotice}</span></div><button type="button" aria-label="Tutup pemberitahuan" onClick={onClearReverseNotice}><Icon name="close"/></button></div>}
    {controlNotice&&<div className="wip-control-notice"><ShieldCheck/><div><strong>{controlNotice.title}</strong><span>{controlNotice.message}</span></div><button type="button" aria-label="Tutup pemberitahuan" onClick={()=>setControlNotice(null)}><X/></button></div>}
    <section className="sewing-kpi-grid"><div className="panel"><span>BATCH PRODUKSI</span><strong>{visibleGroups.length}</strong><small>Urut dari produksi terbaru</small></div><div className="panel"><span>BATCH DISTRIBUSI</span><strong>{visibleBatches.length}</strong><small>{visibleQty} pcs sedang dikelola</small></div><div className="panel"><span>SELESAI DIJAHIT</span><strong>{visibleCompleted} pcs</strong><small>{visibleQty-visibleCompleted} pcs belum selesai</small></div><div className="panel ready"><span>SIAP PILIH LAUNDRY</span><strong>{readyLaundryCount} batch</strong><small>Tujuan laundry sudah dapat dipilih</small></div></section>
    <section className="panel sewing-workspace">
      <div className="sewing-toolbar"><div><span>SEMUA JAHITAN</span><strong>Batch Produksi → Batch Distribusi</strong><small>{visibleGroups.length} Batch Produksi · {visibleBatches.length} distribusi tampil</small></div><label className="sewing-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari produksi, model, Pola, bahan, Mandor, status..."/></label><label className="simulation-pattern-filter compact"><span>POLA</span><select aria-label="Filter Pola WIP" value={patternFilter} onChange={(event)=>setPatternFilter(event.target.value)}><option value="">Semua Pola</option>{patternOptions.map((item)=><option value={item.id} key={item.id}>{item.code} · {item.revision}</option>)}</select><small>DATA SIMULASI</small></label><MultiCheckFilter label="Mandor" options={mandorOptions} selected={selectedMandors} onChange={setMandors}/><div className="sewing-status-tabs" role="tablist" aria-label="Status WIP">{(['ACTIVE','COMPLETED','ALL'] as const).map((value)=><button type="button" role="tab" aria-selected={statusFilter===value} className={statusFilter===value?'active':''} onClick={()=>setStatusFilter(value)} key={value}>{value==='ACTIVE'?'Aktif':value==='COMPLETED'?`Selesai · ${completedParentCount}`:'Semua'}</button>)}</div></div>
      <div className="sewing-parent-list" data-keyboard-grid>{visibleGroups.map((parent,parentIndex)=>{
        const active=parent.batches.filter(b=>!b.line.closed)
        const parentCompleted=active.reduce((sum,batch)=>sum+completedOf(batch),0)
        const parentQty=active.reduce((sum,batch)=>sum+batch.qty,0)
        const parentProgress=Math.round((parentCompleted/Math.max(1,parentQty))*100)
        const parentDeliveries=deliveries.filter((delivery)=>delivery.parentId===parent.id)
        const parentOutside=parentDeliveries.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
        const parentReturned=parentDeliveries.reduce((sum,delivery)=>sum+delivery.good+delivery.bs,0)
        const parentVendors=Array.from(new Set(parentDeliveries.filter((delivery)=>laundryOutstanding(delivery)>0).map((delivery)=>delivery.vendor)))
        return <article className="sewing-parent-card" key={parent.id} aria-label={'Distribusi '+parent.id}>
          <header className="sewing-parent-head"><span className="sewing-parent-order">{String(parentIndex+1).padStart(2,'0')}</span><div><small>{parent.plannedBrand ? `MEREK RENCANA · OPSIONAL · ${parent.plannedBrand}` : 'MEREK BELUM DITENTUKAN'} · BATCH PRODUKSI</small><h2>{parent.id} · {parent.model}</h2><p>{parent.material} · pickup {parent.pickupAt}{parent.skuRef?' · '+parent.skuRef:''}</p><div className="sewing-parent-pattern" data-pattern-snapshot={parent.pattern?.id??'legacy-null'}><Icon name="audit"/><span><small>POLA SNAPSHOT</small><strong>{patternSnapshotLabel(parent.pattern)}</strong></span></div></div><span className="sewing-mandor-pill"><Icon name="user"/><span><small>MANDOR</small><strong>{[...new Set(active.map(b=>b.line.mandor))].join(' · ')||parent.mandor}</strong></span></span><div className="sewing-parent-total"><strong>{parentCompleted}/{parentQty} pcs</strong><small>{parentQty} pcs di WIP · {parent.ledger.returns.reduce((n,r)=>n+total(r.sources),0)} pcs di Bagi Potongan</small><small>{parentVendors.length>0?`${parentVendors.join(' & ')} · ${parentOutside} di luar · ${parentReturned} kembali`:`${active.length} Batch Distribusi · ${parentProgress}%`}</small></div></header>
          <div className="sewing-parent-progress"><span style={{width:`${parentProgress}%`}}/></div>
          <div className="sewing-child-grid">{parent.batches.map((batch,batchIndex)=>{
            const completed=completedOf(batch)
            const progress=Math.round((completed/Math.max(1,batch.qty))*100)
            const isReady=completed===batch.qty
            const summary=summarizeLaundryBatch(deliveries,batch.id)
            const draftLaundry=laundryDrafts[batch.id]
            const inLaundry=summary.outside>0
            const returnedToQc=summary.returned>0
            const availableLaundryQty=Math.max(0,batch.qty-summary.returned-summary.outside)
            const dependency=recordedDownstream(batch.id)
            const locked=!!dependency||!!batch.line.closed
            const lockReason=dependency||correctionLock(batch.line)
            const preSewing=!lockReason&&completed===0
            const status=sewingStatus(batch.line,batch.id,deliveries,laundryDrafts)
            return <section className={`sewing-batch-card ${batch.line.closed?'sewing-closed':''} ${isReady&&!locked?'ready':''} ${draftLaundry?'laundry-draft':''} ${inLaundry?'laundry-in-transit':''} ${returnedToQc?'laundry-returned':''} ${reverseNotice?.includes(batch.id)?'reverse-focus':''}`} key={batch.id} aria-label={parent.id+' Batch '+batch.number}>
              <div className="sewing-batch-head"><div><span>BATCH DISTRIBUSI {String(batch.number).padStart(2,'0')}</span><strong>{batch.qty} pcs</strong></div><em>{status}</em></div>
              <div className="sewing-batch-sizes">{parent.sizes.map((size,sizeIndex)=><span className={batch.sizes[sizeIndex]>0?'active':''} key={size}><small>SIZE {size}</small><strong>{batch.sizes[sizeIndex]}</strong></span>)}</div>
              <div className="sewing-batch-note"><Icon name="document"/><div><span>ARAHAN MANDOR</span><strong>{noteOf(parent,batch)||'—'}</strong></div></div>
              <BatchTrace row={batch.line} group={parent.ledger}/>
              {!batch.line.closed&&<><div className={`wip-child-controls ${preSewing?'editable':''}`}>
                <span><ShieldCheck/>{preSewing?'Menunggu jahit':lockReason||'Periksa jumlah jahit.'}</span>
                <button type="button" disabled={!preSewing} onClick={()=>startControl(parent,batch,'adjust')}><SlidersHorizontal/> Koreksi</button>
                <button type="button" disabled={!preSewing} className="reverse" onClick={()=>startControl(parent,batch,'reverse')}><RotateCcw/> Batalkan</button>
              </div>
              <label className={`sewing-completed-input ${locked?'disabled':''}`}><span>SELESAI DIJAHIT</span><div><input disabled={locked} type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={parentIndex*100+batchIndex} data-grid-col={0} aria-label={'Selesai dijahit Batch '+batch.number} value={completedInputs[batch.id]??String(batch.completed)} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={e=>setCompletedInputs(current=>({...current,[batch.id]:e.target.value.replace(/[^0-9]/g,'')}))}
                onBlur={e=>saveSewing(parent,batch,e.currentTarget.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();e.currentTarget.blur()}}}/><b>/ {batch.qty} pcs</b></div></label>
              <div className="sewing-batch-progress"><span style={{width:`${progress}%`}}/></div>
              {returnedToQc?<div className="sewing-laundry-gate returned"><div><span>{summary.outside>0?'KEMBALI SEBAGIAN · SIAP QC':'SUDAH KEMBALI · SIAP QC'}</span><small>{summary.returned} pcs kembali · {summary.outside} pcs otomatis Stuck Laundry saat review.</small></div><div className="laundry-name-grid">{[...new Set([...summary.activeVendors,...summary.returnedVendors])].map((name)=><button type="button" className="active jump" onClick={()=>onOpenLaundry(batch.id,name,'return')} key={name}><Icon name="arrow"/>{name}</button>)}</div><p><Icon name="check"/><span>{summary.good} Good · {summary.bs} BS tercatat. Riwayat laundry tetap terlihat.</span></p><button type="button" className="wip-review-finishing" onClick={()=>onOpenQc(parent.id,batch.id)}>Review finishing <Icon name="arrow"/></button></div>
              :inLaundry?<div className="sewing-laundry-gate open tracking"><div><span>SEDANG DI LAUNDRY</span><small>{summary.outside} pcs masih di luar · belum ada fisik yang kembali</small></div><div className="laundry-name-grid">{summary.activeVendors.map((name)=><button type="button" className="active jump" onClick={()=>onOpenLaundry(batch.id,name,'return')} key={name}><Icon name="arrow"/>{name}</button>)}</div><p><Icon name="history"/><span>Tekan nama laundry untuk buka surat kirim aktif.</span></p></div>
              :<div className={`sewing-laundry-gate ${isReady?'open':'locked'} ${draftLaundry?'draft':''}`}><div><span>{isReady?(draftLaundry?'DRAFT TUJUAN LAUNDRY':'PILIH NAMA LAUNDRY'):'LAUNDRY TERKUNCI'}</span><small>{isReady?(draftLaundry?'Belum mengubah stok. Tekan nama aktif untuk kembali ke review.':summary.returned>0?`${availableLaundryQty} pcs sisa siap dipilihkan laundry baru.`:'Tekan nama tujuan, lalu konfirmasi pindah halaman.'):`Selesaikan ${batch.qty-completed} pcs lagi.`}</small></div>{isReady&&availableLaundryQty>0&&<div className="laundry-name-grid">{laundryVendorNames.map((name)=><button type="button" className={draftLaundry===name?'active':''} aria-pressed={draftLaundry===name} onClick={()=>draftLaundry===name?onOpenLaundry(batch.id,name,'send'):setPendingLaundry({batchId:batch.id,vendor:name,qty:availableLaundryQty})} key={name}>{draftLaundry===name&&<Icon name="check"/>}{name}</button>)}</div>}{draftLaundry&&<p><Icon name="arrow"/><span><strong>{draftLaundry}</strong> · draft surat kirim siap dilanjutkan.</span></p>}</div>}
              </>}
            </section>
          })}</div>
          <SewingHistory ledger={parent.ledger}/>
        </article>
      })}{visibleGroups.length===0&&<div className="sewing-empty"><Icon name={statusFilter==='ACTIVE'&&completedParentCount>0?'check':'search'}/><strong>{statusFilter==='ACTIVE'&&completedParentCount>0?'Semua hasil yang cocok sudah selesai':'Tidak ada jahitan yang cocok'}</strong><small>{statusFilter==='ACTIVE'&&completedParentCount>0?'Buka tab “Selesai” atau “Semua” untuk melihat riwayat.':'Cek status, pilihan mandor, atau kata pencarian.'}</small></div>}</div>
    </section>
    {controlTarget&&<Suspense fallback={null}><WipBatchControlLayer key={controlTarget.request} mode={controlTarget.mode} parent={controlTarget.form} targetBatchId={controlTarget.id} onClose={()=>setControlTarget(null)} onApply={applyWipControl}/></Suspense>}
    {pendingLaundry&&<div className="wip-confirm-layer" role="presentation"><section className="wip-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-laundry-title"><div className="wip-confirm-icon"><Icon name="boxes"/></div><div><span>PINDAH KE HALAMAN LAUNDRY</span><h2 id="confirm-laundry-title">Siapkan ke {pendingLaundry.vendor}?</h2><p>Batch {pendingLaundry.batchId} · {pendingLaundry.qty} pcs. Ini baru membuat draft tujuan; stok belum berpindah sampai lu menekan <strong>Catat dikirim</strong> di halaman Laundry.</p></div><div className="wip-confirm-actions"><button type="button" className="soft-btn" onClick={()=>setPendingLaundry(null)}>Batal</button><button type="button" className="primary-btn" onClick={()=>{const p=parentGroups.find(g=>g.batches.some(b=>b.id===pendingLaundry.batchId));const b=p?.batches.find(r=>r.id===pendingLaundry.batchId);if(p&&b&&!b.line.closed&&b.completed===b.qty)onConfirmLaundry(laundryReadyFromRows(p,b,pendingLaundry.vendor));setPendingLaundry(null)}}>Buka Laundry <Icon name="arrow"/></button></div></section></div>}
  </>
}
