import { StageLots } from './planner/StageLots'
import { Icon } from '../components/AppIcon'
import type { QcFinalResult } from '../QcFinalPage'
import type { WipControlMode, WipControlParent, WipControlResult } from '../WipBatchControlLayer'
import { deriveWipControlStatus } from '../wipControlPolicy'
import { MultiCheckFilter } from './controls'
import { cellQuantity } from './cuttingAllocation'
import { laundryOutstanding, summarizeLaundryBatch } from './laundryModel'
import type { LaundryDelivery, LaundryView } from './laundryModel'
import { patternSnapshotLabel, simulationPatternSnapshots } from './productionModel'
import type { QtyTuple } from './productionModel'
import { laundryVendorNames, sewingWipSeeds } from './sewingModel'
import type { SewingBatchSeed, SewingParentSeed } from './sewingModel'
import { RotateCcw, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { lazy, Suspense, useMemo, useState } from 'react'

const WipBatchControlLayer = lazy(() => import('../WipBatchControlLayer'))

type WipAdjustmentHistoryEntry = {
  id: string
  operation: 'REDISTRIBUTION' | 'PHYSICAL_RECOUNT'
  note: string
  at: string
  before: QtyTuple
  after: QtyTuple
}

export function SewingWipPage({
  batchNotes, deliveries, finalizedResults, laundryDrafts, reverseNotice, onClearReverseNotice,
  onClearLaundryDraft, onConfirmLaundry, onOpenLaundry, onOpenQc,
}: {
  batchNotes: string[]
  deliveries: LaundryDelivery[]
  finalizedResults: QcFinalResult[]
  laundryDrafts: Record<string,string>
  reverseNotice: string|null
  onClearReverseNotice: () => void
  onClearLaundryDraft: (batchId:string) => void
  onConfirmLaundry: (batchId:string,vendor:string,snapshot?:{qty:number;sizes:QtyTuple}) => void
  onOpenLaundry: (batchId:string,vendor:string,view:LaundryView) => void
  onOpenQc: (parentId:string,batchId:string) => void
}) {
  const [batchOverrides,setBatchOverrides] = useState<Record<string,QtyTuple>>({})
  const [reversedBatchIds,setReversedBatchIds] = useState<string[]>([])
  const [controlTarget,setControlTarget] = useState<{parentId:string;batchId:string;mode:WipControlMode}|null>(null)
  const [controlNotice,setControlNotice] = useState<{title:string;message:string}|null>(null)
  const [adjustmentHistory,setAdjustmentHistory] = useState<Record<string,WipAdjustmentHistoryEntry[]>>({})
  const parentGroups = useMemo(() => sewingWipSeeds.map((parent) => ({
    ...parent,
    batches:parent.batches
      .filter((batch)=>!reversedBatchIds.includes(batch.id))
      .map((batch)=>{
        const sizes=batchOverrides[batch.id]??batch.sizes
        const noteIndex=parent.batches.findIndex((source)=>source.id===batch.id)
        return {...batch,sizes,qty:sizes.reduce((sum,qty)=>sum+qty,0),note:parent.id==='POT-260827-042'?(batchNotes[noteIndex]||batch.note):batch.note}
      }),
  })), [batchNotes,batchOverrides,reversedBatchIds])
  const mandorOptions = Array.from(new Set(parentGroups.map((parent) => parent.mandor)))
  const [selectedMandors,setSelectedMandors] = useState([...mandorOptions])
  const [query,setQuery] = useState('')
  const [patternFilter,setPatternFilter] = useState('')
  const [completedInputs,setCompletedInputs] = useState<Record<string,string>>(() => Object.fromEntries(sewingWipSeeds.flatMap((parent) => parent.batches.map((batch) => [batch.id,String(batch.completed)]))))
  const [statusFilter,setStatusFilter] = useState<'ACTIVE'|'COMPLETED'|'ALL'>('ACTIVE')
  const [pendingLaundry,setPendingLaundry] = useState<{batchId:string;vendor:string;qty:number}|null>(null)
  const completedBatchIds = new Set(finalizedResults.filter((result)=>result.completionStatus==='COMPLETE').map((result)=>result.batchId))
  const parentControlStatus=(parent:SewingParentSeed)=>deriveWipControlStatus(parent.batches.map((batch)=>{
    const summary=summarizeLaundryBatch(deliveries,batch.id)
    const completed=Math.min(batch.qty,cellQuantity(completedInputs[batch.id]))
    const finalSkuComplete=completedBatchIds.has(batch.id)
    return {
      finalSkuComplete,
      unfinishedSewing:completed<batch.qty,
      unsentReady:completed===batch.qty&&summary.returned===0&&summary.outside===0&&!laundryDrafts[batch.id],
      laundryDraft:Boolean(laundryDrafts[batch.id]),
      laundryInTransit:summary.outside>0,
      unresolvedLaundryIssue:summary.outside>0,
      pendingFinalSkuHandoff:summary.returned>0&&!finalSkuComplete,
      openDependency:false,
      operatorActionRequired:false,
    }
  }))
  const parentIsCompleted=(parent:SewingParentSeed)=>parentControlStatus(parent)==='COMPLETED'
  const completedParentCount=parentGroups.filter(parentIsCompleted).length
  const visibleGroups = parentGroups
    .filter((parent) => selectedMandors.includes(parent.mandor))
    .filter((parent)=>!patternFilter||parent.pattern?.id===patternFilter)
    .filter((parent) => `${parent.id} ${parent.model} ${parent.material} ${parent.mandor} ${parent.pattern?.code??''} ${parent.pattern?.revision??''} ${parent.pattern?.name??''} ${parent.batches.map((batch) => `${batch.number} ${batch.note}`).join(' ')}`.toLowerCase().includes(query.toLowerCase()))
    .filter((parent)=>statusFilter==='ALL'||(statusFilter==='COMPLETED'?parentIsCompleted(parent):!parentIsCompleted(parent)))
    .sort((a,b) => b.sequence-a.sequence)
  const visibleBatches = visibleGroups.flatMap((parent) => parent.batches)
  const visibleQty = visibleBatches.reduce((sum,batch) => sum+batch.qty,0)
  const visibleCompleted = visibleBatches.reduce((sum,batch) => sum+Math.min(batch.qty,cellQuantity(completedInputs[batch.id])),0)
  const readyLaundryCount = visibleBatches.filter((batch) => {
    const summary=summarizeLaundryBatch(deliveries,batch.id)
    return cellQuantity(completedInputs[batch.id])===batch.qty&&summary.outside===0&&summary.returned<batch.qty
  }).length
  const updateCompleted = (batch: SewingBatchSeed, rawValue: string) => {
    const digits = rawValue.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'')
    const nextValue = digits===''?'':String(Math.min(batch.qty,cellQuantity(digits)))
    setCompletedInputs((current)=>({...current,[batch.id]:nextValue}))
    if(cellQuantity(nextValue)<batch.qty&&laundryDrafts[batch.id])onClearLaundryDraft(batch.id)
  }
  const controlParent=controlTarget?parentGroups.find((parent)=>parent.id===controlTarget.parentId):undefined
  const controlPayload:WipControlParent|null=controlParent?{
    id:controlParent.id,model:controlParent.model,material:controlParent.material,mandor:controlParent.mandor,sizeLabels:controlParent.sizes,
    batches:controlParent.batches.map((batch)=>{
      const completed=Math.min(batch.qty,cellQuantity(completedInputs[batch.id]))
      const summary=summarizeLaundryBatch(deliveries,batch.id)
      const draft=laundryDrafts[batch.id]
      const lockLabel=summary.returned>0?'Sudah kembali':summary.outside>0?'Di Laundry':draft?'Draft Laundry':completed>0?`${completed} pcs dijahit`:'Pre-sewing'
      return {...batch,completed,locked:completed>0||summary.returned>0||summary.outside>0||Boolean(draft),lockLabel}
    }),
  }:null
  const applyWipControl=(result:WipControlResult)=>{
    if(!controlParent)return
    if(result.kind==='ADJUST'){
      const before=controlParent.batches.reduce((sum,batch)=>sum+batch.qty,0)
      const after=Object.values(result.sizesByBatch).reduce((sum,sizes)=>sum+sizes.reduce((lineTotal,qty)=>lineTotal+qty,0),0)
      const changedBatches=controlParent.batches.filter((batch)=>{
        const next=result.sizesByBatch[batch.id]
        return next&&batch.sizes.some((qty,index)=>qty!==next[index])
      })
      setBatchOverrides((current)=>({...current,...result.sizesByBatch}))
      setAdjustmentHistory((current)=>{
        const next={...current}
        changedBatches.forEach((batch,index)=>{
          const entry:WipAdjustmentHistoryEntry={
            id:`${result.operation}-${Date.now()}-${index}`,
            operation:result.operation,
            note:result.note,
            at:'28 Agu 2026 · baru saja',
            before:[...batch.sizes] as QtyTuple,
            after:[...result.sizesByBatch[batch.id]] as QtyTuple,
          }
          next[batch.id]=[entry,...(next[batch.id]??[])]
        })
        return next
      })
      setCompletedInputs((current)=>Object.fromEntries(Object.entries(current).map(([batchId,value])=>{
        const sizes=result.sizesByBatch[batchId]
        return [batchId,sizes?String(Math.min(cellQuantity(value),sizes.reduce((sum,qty)=>sum+qty,0))):value]
      })))
      setControlNotice({
        title:result.operation==='REDISTRIBUTION'?'Distribusi batch diperbarui':'Hasil fisik diperbarui',
        message:result.operation==='REDISTRIBUTION'
          ? `Batch Produksi ${controlParent.id} tetap ${after} pcs; redistribusi tersimpan sebagai simulasi berjejak.`
          : `Batch Produksi ${controlParent.id} berubah dari ${before} menjadi ${after} pcs (${after-before>=0?'+':''}${after-before}). Batas transaksi downstream tetap dijaga server.`,
      })
    }else{
      setReversedBatchIds((current)=>current.includes(result.batchId)?current:[...current,result.batchId])
      setControlNotice({title:`Distribusi ${result.batchId} dibatalkan`,message:`Kuantitas kembali ke Batch Produksi ${controlParent.id}. Dokumen hasil potong tidak dihapus.`})
    }
    setControlTarget(null)
  }

  return <>
    <section className="hero-copy compact sewing-hero"><div className="eyebrow">PRODUKSI · SETELAH PICKUP</div><h1>WIP & Sewing</h1><p>Seluruh pekerjaan jahit dikelompokkan berdasarkan Batch Produksi. Mandor menyelesaikan setiap Batch Distribusi, lalu tujuan laundry dapat dipilih ketika kuantitas jahitan sudah penuh.</p></section>
    <StageLots stage="sewing"/>
    <h2 className="gar-archive-heading">Arsip latihan Agustus</h2>
    <div className="sewing-simulation-strip"><ShieldCheck/><strong>DATA SIMULASI</strong><span>Filter demo mengikuti seluruh child sampai Final SKU lengkap; mode UAT membaca status authoritative dari backend.</span></div>
    {reverseNotice&&<div className="sewing-reverse-notice"><Icon name="reset"/><div><strong>Kembali ke WIP</strong><span>{reverseNotice}</span></div><button type="button" aria-label="Tutup pemberitahuan" onClick={onClearReverseNotice}><Icon name="close"/></button></div>}
    {controlNotice&&<div className="wip-control-notice"><ShieldCheck/><div><strong>{controlNotice.title}</strong><span>{controlNotice.message} Backend belum berubah selama mode simulasi.</span></div><button type="button" aria-label="Tutup pemberitahuan" onClick={()=>setControlNotice(null)}><X/></button></div>}
    <section className="sewing-kpi-grid"><div className="panel"><span>BATCH PRODUKSI</span><strong>{visibleGroups.length}</strong><small>Urut dari produksi terbaru</small></div><div className="panel"><span>BATCH DISTRIBUSI</span><strong>{visibleBatches.length}</strong><small>{visibleQty} pcs sedang dikelola</small></div><div className="panel"><span>SELESAI DIJAHIT</span><strong>{visibleCompleted} pcs</strong><small>{visibleQty-visibleCompleted} pcs belum selesai</small></div><div className="panel ready"><span>SIAP PILIH LAUNDRY</span><strong>{readyLaundryCount} batch</strong><small>Tujuan laundry sudah dapat dipilih</small></div></section>
    <section className="panel sewing-workspace">
      <div className="sewing-toolbar"><div><span>SEMUA JAHITAN</span><strong>Batch Produksi → Batch Distribusi</strong><small>{visibleGroups.length} Batch Produksi · {visibleBatches.length} distribusi tampil</small></div><label className="sewing-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari produksi, model, Pola, bahan, Mandor, status..."/></label><label className="simulation-pattern-filter compact"><span>POLA</span><select aria-label="Filter Pola WIP" value={patternFilter} onChange={(event)=>setPatternFilter(event.target.value)}><option value="">Semua Pola</option>{Object.values(simulationPatternSnapshots).map((item)=><option value={item.id} key={item.id}>{item.code} · {item.revision}</option>)}</select><small>DATA SIMULASI</small></label><MultiCheckFilter label="Mandor" options={mandorOptions} selected={selectedMandors} onChange={setSelectedMandors}/><div className="sewing-status-tabs" role="tablist" aria-label="Status WIP">{(['ACTIVE','COMPLETED','ALL'] as const).map((value)=><button type="button" role="tab" aria-selected={statusFilter===value} className={statusFilter===value?'active':''} onClick={()=>setStatusFilter(value)} key={value}>{value==='ACTIVE'?'Aktif':value==='COMPLETED'?`Selesai · ${completedParentCount}`:'Semua'}</button>)}</div></div>
      <div className="sewing-parent-list" data-keyboard-grid>{visibleGroups.map((parent,parentIndex)=>{
        const parentCompleted=parent.batches.reduce((sum,batch)=>sum+Math.min(batch.qty,cellQuantity(completedInputs[batch.id])),0)
        const parentQty=parent.batches.reduce((sum,batch)=>sum+batch.qty,0)
        const parentProgress=Math.round((parentCompleted/Math.max(1,parentQty))*100)
        const parentDeliveries=deliveries.filter((delivery)=>delivery.parentId===parent.id)
        const parentOutside=parentDeliveries.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
        const parentReturned=parentDeliveries.reduce((sum,delivery)=>sum+delivery.good+delivery.bs,0)
        const parentVendors=Array.from(new Set(parentDeliveries.filter((delivery)=>laundryOutstanding(delivery)>0).map((delivery)=>delivery.vendor)))
        return <article className="sewing-parent-card" key={parent.id}>
          <header className="sewing-parent-head"><span className="sewing-parent-order">{String(parentIndex+1).padStart(2,'0')}</span><div><small>{parent.plannedBrand ? `MEREK RENCANA · OPSIONAL · ${parent.plannedBrand}` : 'MEREK BELUM DITENTUKAN'} · BATCH PRODUKSI</small><h2>{parent.id} · {parent.model}</h2><p>{parent.material} · pickup {parent.pickupAt}</p><div className="sewing-parent-pattern" data-pattern-snapshot={parent.pattern?.id??'legacy-null'}><Icon name="audit"/><span><small>POLA SNAPSHOT</small><strong>{patternSnapshotLabel(parent.pattern)}</strong></span></div></div><span className="sewing-mandor-pill"><Icon name="user"/><span><small>MANDOR</small><strong>{parent.mandor}</strong></span></span><div className="sewing-parent-total"><strong>{parentCompleted}/{parentQty} pcs</strong><small>{parentVendors.length>0?`${parentVendors.join(' & ')} · ${parentOutside} di luar · ${parentReturned} kembali`:`${parent.batches.length} Batch Distribusi · ${parentProgress}%`}</small></div></header>
          <div className="sewing-parent-progress"><span style={{width:`${parentProgress}%`}}/></div>
          <div className="sewing-child-grid">{parent.batches.map((batch,batchIndex)=>{
            const completed=Math.min(batch.qty,cellQuantity(completedInputs[batch.id]))
            const progress=Math.round((completed/Math.max(1,batch.qty))*100)
            const isReady=completed===batch.qty
            const summary=summarizeLaundryBatch(deliveries,batch.id)
            const draftLaundry=laundryDrafts[batch.id]
            const inLaundry=summary.outside>0
            const returnedToQc=summary.returned>0
            const availableLaundryQty=Math.max(0,batch.qty-summary.returned-summary.outside)
            const locked=inLaundry||returnedToQc
            const preSewing=completed===0&&!locked&&!draftLaundry
            const batchHistory=adjustmentHistory[batch.id]??[]
            const status=returnedToQc?(summary.outside>0?'Kembali sebagian · siap QC':'Kembali · siap QC'):inLaundry?'Di laundry':draftLaundry?'Draft laundry':isReady?'Siap laundry':completed>0?'Sedang dijahit':'Menunggu jahit · Pre-sewing'
            return <section className={`sewing-batch-card ${isReady&&!locked?'ready':''} ${draftLaundry?'laundry-draft':''} ${inLaundry?'laundry-in-transit':''} ${returnedToQc?'laundry-returned':''} ${reverseNotice?.includes(batch.id)?'reverse-focus':''}`} key={batch.id}>
              <div className="sewing-batch-head"><div><span>BATCH DISTRIBUSI {String(batch.number).padStart(2,'0')}</span><strong>{batch.qty} pcs</strong></div><em>{status}</em></div>
              <div className="sewing-batch-sizes">{parent.sizes.map((size,sizeIndex)=><span className={batch.sizes[sizeIndex]>0?'active':''} key={size}><small>SIZE {size}</small><strong>{batch.sizes[sizeIndex]}</strong></span>)}</div>
              <div className="sewing-batch-note"><Icon name="document"/><div><span>ARAHAN MANDOR</span><strong>{batch.note}</strong></div></div>
              <div className={`wip-child-controls ${preSewing?'editable':''}`}>{preSewing?<><span><ShieldCheck/> Belum ada bukti jahit; distribusi masih aman dikoreksi.</span><button type="button" onClick={()=>setControlTarget({parentId:parent.id,batchId:batch.id,mode:'adjust'})}><SlidersHorizontal/> Koreksi</button><button type="button" className="reverse" onClick={()=>setControlTarget({parentId:parent.id,batchId:batch.id,mode:'reverse'})}><RotateCcw/> Batalkan</button></>:<span><ShieldCheck/> Kontrol distribusi terkunci oleh {returnedToQc?'hasil return':inLaundry?'Laundry':draftLaundry?'draft Laundry':`${completed} pcs selesai dijahit`}.</span>}</div>
              {batchHistory.length>0&&<details className="wip-adjust-history"><summary><Icon name="history"/><span><strong>Riwayat koreksi batch</strong><small>{batchHistory[0].operation==='REDISTRIBUTION'?'Redistribusi terakhir':'Koreksi fisik terakhir'} · {batchHistory[0].at}</small></span><b>{batchHistory.length}</b></summary><div>{batchHistory.map((entry)=><article key={entry.id}><header><strong>{entry.operation==='REDISTRIBUTION'?'Redistribusi Batch':'Koreksi hasil fisik'}</strong><span>{entry.at}</span></header><div>{parent.sizes.map((size,sizeIndex)=><span key={size}><small>SIZE {size}</small><strong>{entry.before[sizeIndex]} → {entry.after[sizeIndex]}</strong></span>)}</div><p>{entry.note}</p></article>)}</div></details>}
              <label className={`sewing-completed-input ${locked?'disabled':''}`}><span>SELESAI DIJAHIT</span><div><input disabled={locked} type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={parentIndex*100+batchIndex} data-grid-col={0} value={completedInputs[batch.id]??''} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateCompleted(batch,event.target.value)}/><b>/ {batch.qty} pcs</b></div></label>
              <div className="sewing-batch-progress"><span style={{width:`${progress}%`}}/></div>
              {returnedToQc?<div className="sewing-laundry-gate returned"><div><span>{summary.outside>0?'KEMBALI SEBAGIAN · SIAP QC':'SUDAH KEMBALI · SIAP QC'}</span><small>{summary.returned} pcs kembali · {summary.outside} pcs otomatis Stuck Laundry saat review.</small></div><div className="laundry-name-grid">{[...new Set([...summary.activeVendors,...summary.returnedVendors])].map((name)=><button type="button" className="active jump" onClick={()=>onOpenLaundry(batch.id,name,'return')} key={name}><Icon name="arrow"/>{name}</button>)}</div><p><Icon name="check"/><span>{summary.good} Good · {summary.bs} BS tercatat. Riwayat laundry tetap terlihat.</span></p><button type="button" className="wip-review-finishing" onClick={()=>onOpenQc(parent.id,batch.id)}>Review finishing <Icon name="arrow"/></button></div>
              :inLaundry?<div className="sewing-laundry-gate open tracking"><div><span>SEDANG DI LAUNDRY</span><small>{summary.outside} pcs masih di luar · belum ada fisik yang kembali</small></div><div className="laundry-name-grid">{summary.activeVendors.map((name)=><button type="button" className="active jump" onClick={()=>onOpenLaundry(batch.id,name,'return')} key={name}><Icon name="arrow"/>{name}</button>)}</div><p><Icon name="history"/><span>Tekan nama laundry untuk buka surat kirim aktif.</span></p></div>
              :<div className={`sewing-laundry-gate ${isReady?'open':'locked'} ${draftLaundry?'draft':''}`}><div><span>{isReady?(draftLaundry?'DRAFT TUJUAN LAUNDRY':'PILIH NAMA LAUNDRY'):'LAUNDRY TERKUNCI'}</span><small>{isReady?(draftLaundry?'Belum mengubah stok. Tekan nama aktif untuk kembali ke review.':summary.returned>0?`${availableLaundryQty} pcs sisa siap dipilihkan laundry baru.`:'Tekan nama tujuan, lalu konfirmasi pindah halaman.'):`Selesaikan ${batch.qty-completed} pcs lagi.`}</small></div>{isReady&&availableLaundryQty>0&&<div className="laundry-name-grid">{laundryVendorNames.map((name)=><button type="button" className={draftLaundry===name?'active':''} aria-pressed={draftLaundry===name} onClick={()=>draftLaundry===name?onOpenLaundry(batch.id,name,'send'):setPendingLaundry({batchId:batch.id,vendor:name,qty:availableLaundryQty})} key={name}>{draftLaundry===name&&<Icon name="check"/>}{name}</button>)}</div>}{draftLaundry&&<p><Icon name="arrow"/><span><strong>{draftLaundry}</strong> · draft surat kirim siap dilanjutkan.</span></p>}</div>}
            </section>
          })}</div>
        </article>
      })}{visibleGroups.length===0&&<div className="sewing-empty"><Icon name={statusFilter==='ACTIVE'&&completedParentCount>0?'check':'search'}/><strong>{statusFilter==='ACTIVE'&&completedParentCount>0?'Semua hasil yang cocok sudah selesai':'Tidak ada jahitan yang cocok'}</strong><small>{statusFilter==='ACTIVE'&&completedParentCount>0?'Buka tab “Selesai” atau “Semua” untuk melihat riwayat.':'Cek status, pilihan mandor, atau kata pencarian.'}</small></div>}</div>
    </section>
    {controlTarget&&controlPayload&&<Suspense fallback={null}><WipBatchControlLayer key={`${controlTarget.parentId}-${controlTarget.batchId}-${controlTarget.mode}`} mode={controlTarget.mode} parent={controlPayload} targetBatchId={controlTarget.batchId} onClose={()=>setControlTarget(null)} onApply={applyWipControl}/></Suspense>}
    {pendingLaundry&&<div className="wip-confirm-layer" role="presentation"><section className="wip-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-laundry-title"><div className="wip-confirm-icon"><Icon name="boxes"/></div><div><span>PINDAH KE HALAMAN LAUNDRY</span><h2 id="confirm-laundry-title">Siapkan ke {pendingLaundry.vendor}?</h2><p>Batch {pendingLaundry.batchId} · {pendingLaundry.qty} pcs. Ini baru membuat draft tujuan; stok belum berpindah sampai lu menekan <strong>Catat dikirim</strong> di halaman Laundry.</p></div><div className="wip-confirm-actions"><button type="button" className="soft-btn" onClick={()=>setPendingLaundry(null)}>Batal</button><button type="button" className="primary-btn" onClick={()=>{const source=parentGroups.flatMap((parent)=>parent.batches).find((batch)=>batch.id===pendingLaundry.batchId);onConfirmLaundry(pendingLaundry.batchId,pendingLaundry.vendor,source?{qty:source.qty,sizes:source.sizes}:undefined);setPendingLaundry(null)}}>Buka Laundry <Icon name="arrow"/></button></div></section></div>}
  </>
}
