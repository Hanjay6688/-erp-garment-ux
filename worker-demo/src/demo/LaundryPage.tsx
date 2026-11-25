import {browseMatch} from '../browseMatch'
import {allSkus} from './skuCatalog'
import {usePlannerSession} from './planner/session'
import { StageLots } from './planner/StageLots'
import { Icon } from '../components/AppIcon'
import { cellQuantity } from './cuttingAllocation'
import { colourProcesses, instructionsFor, laundryRecipePath, readLaundryRecipes, type LaundryInstructions } from './laundryRecipes'
import './laundryRecipe.css'
import { money } from './format'
import {
  laundryDeliveryStatus,
  laundryDigits,
  laundryOutstanding,
  laundryOutstandingSizes,
  laundryProcesses,
  laundryRateAt,
  returnLaundry,
  validLaundryTime,
  laundryPhysicalTime,
  laundryReadyFromDelivery,
  laundryReadyFromSewingBatch,
  laundryReturnedSizes,
  proportionalLaundrySizes,
} from './laundryModel'
import type { LaundryDelivery, LaundryPrefill, LaundryReadyBatch, LaundryView } from './laundryModel'
import { patternSnapshotLabel } from './productionModel'
import type { ProductionPatternSnapshot, QtyTuple } from './productionModel'
import { laundryVendorNames } from './sewingModel'
import { useMemo, useState } from 'react'

const trainingSendTime = '2026-08-27T16:00'
const trainingReturnTime = '2026-08-27T17:30'
const defaultSendTime = (batch?: LaundryReadyBatch) => {
  const latest = [trainingSendTime, laundryPhysicalTime(batch?.pickupAt ?? ''), laundryPhysicalTime(batch?.sewingDoneAt ?? '')].sort().at(-1)!
  return validLaundryTime(latest) ? latest : trainingSendTime
}
const defaultReturnTime = (delivery: LaundryDelivery) => [trainingReturnTime, laundryPhysicalTime(delivery.sentAt)].sort().at(-1)!

import { LAUNDRY_ALL_MANDORS, laundryMandorOf, laundryMandorOptions, matchesLaundryMandor } from './laundryMandor'

export function LaundryPage({prefill,readyBatches,setReadyBatches,deliveries,setDeliveries,onDraftVendor,onPosted,onReturnToWip,onOpenQc}:{
  prefill:LaundryPrefill|null
  readyBatches:LaundryReadyBatch[]
  setReadyBatches:(value:LaundryReadyBatch[]|((current:LaundryReadyBatch[])=>LaundryReadyBatch[]))=>void
  deliveries:LaundryDelivery[]
  setDeliveries:(value:LaundryDelivery[]|((current:LaundryDelivery[])=>LaundryDelivery[]))=>void
  onDraftVendor:(ids:string[],vendor:string)=>void
  onPosted:(batchIds:string[])=>void
  onReturnToWip:(batchId:string,vendor:string,qty:number)=>void
  onOpenQc:(parentId:string,batchId:string)=>void
}) {
  const articles=allSkus(usePlannerSession(),true)
  const linkQuery=new URLSearchParams(location.search).get('cari')??''
  const [saved]=useState(()=>{try{return JSON.parse(sessionStorage.getItem('erp.demo.laundry.ticket.v1')??'null')}catch{return null}})
  const linked=linkQuery?readyBatches.find(b=>browseMatch(linkQuery,b.id,b.parentId,b.skuRef,b.vendor)):undefined
  const initialBatch=linked??readyBatches.find(b=>b.id===prefill?.batchId)??readyBatches.find(b=>saved?.ids?.includes(b.id))??readyBatches[0]
  const restore=!!initialBatch&&!linkQuery&&!prefill&&saved?.ids?.includes(initialBatch.id)
  const [activeTab,setActiveTab]=useState<LaundryView>(new URLSearchParams(location.search).get('tab')==='kembali'?'return':prefill?.view??'send')
  const [vendorFilter,setVendorFilter]=useState(prefill?.vendor??'Semua laundry')
  const [patternFilter,setPatternFilter]=useState('')
  const [mandorFilter,setMandorFilter]=useState(LAUNDRY_ALL_MANDORS)
  const [query,setQuery]=useState(()=>new URLSearchParams(location.search).get('cari')??'')
  const [selectedIds,setSelectedIds]=useState<string[]>(restore?readyBatches.filter(b=>saved.ids.includes(b.id)&&b.vendor===initialBatch.vendor&&b.parentId===initialBatch.parentId).map(b=>b.id):initialBatch?[initialBatch.id]:[])
  const [sendSizeInputs,setSendSizeInputs]=useState<Record<string,string[]>>(()=>Object.fromEntries(readyBatches.map((batch)=>[batch.id,restore&&Array.isArray(saved.quantities?.[batch.id])?saved.quantities[batch.id]:batch.sizes.map(String)])))
  const [skuRef, setSkuRef] = useState<string>(restore ? saved.skuRef ?? '' : initialBatch?.skuRef ?? '')
  const [overrides, setOverrides] = useState<Partial<LaundryInstructions>>(() => restore
    ? saved.overrides ?? { service: saved.process, colour: saved.colour, colourProcess: saved.colourProcess }
    : { service: initialBatch?.process || undefined })
  const [recipes] = useState(readLaundryRecipes)
  const sku = articles.find(a => a.key === skuRef)
  const [sentAt,setSentAt]=useState<string>(restore ? saved.sentAt ?? defaultSendTime(initialBatch) : defaultSendTime(initialBatch))
  const [sendNote,setSendNote]=useState<string>(restore?saved.note??'':'')
  const [notice,setNotice]=useState('')
  const [returnInputs,setReturnInputs]=useState<Record<string,{good:string[];bs:string[]}>>({})
  const [returnTimes,setReturnTimes]=useState<Record<string,string>>({})
  const [pendingReverse,setPendingReverse]=useState<LaundryDelivery|null>(null)
  const vendorOptions=['Semua laundry',...laundryVendorNames]
  const patternOptions=useMemo(()=>{
    const patterns=new Map<string,ProductionPatternSnapshot>()
    ;[...readyBatches,...deliveries].forEach((row)=>{if(row.pattern)patterns.set(row.pattern.id,row.pattern)})
    return [...patterns.values()].sort((left,right)=>left.code.localeCompare(right.code)||left.revision.localeCompare(right.revision))
  },[readyBatches,deliveries])
  const mandorOptions=useMemo(()=>laundryMandorOptions([...readyBatches,...deliveries]),[readyBatches,deliveries])
  const mandorFiltered=mandorFilter!==LAUNDRY_ALL_MANDORS
  const scopedReady=readyBatches.filter((batch)=>matchesLaundryMandor(batch,mandorFilter))
  const scopedDeliveries=deliveries.filter((delivery)=>matchesLaundryMandor(delivery,mandorFilter))

  const visibleReady=scopedReady.filter((batch)=>vendorFilter==='Semua laundry'||batch.vendor===vendorFilter).filter((batch)=>!patternFilter||batch.pattern?.id===patternFilter).filter(batch=>browseMatch(query,batch.parentId,batch.id,'batch '+Number(batch.id.split('-').at(-1)),batch.skuRef,batch.model,batch.material,batch.mandor,batch.vendor,batch.note,patternSnapshotLabel(batch.pattern),...batch.sizeLabels)).sort((a,b)=>b.sequence-a.sequence)
  const groupedReady=Array.from(visibleReady.reduce((groups,batch)=>groups.set(batch.parentId,[...(groups.get(batch.parentId)??[]),batch]),new Map<string,LaundryReadyBatch[]>()).entries())
  const selectedBatches=readyBatches.filter((batch)=>selectedIds.includes(batch.id))
  const selectedParent=selectedBatches[0]?.parentId??''
  const selectedVendor=selectedBatches[0]?.vendor??''
  const selectedTotal=selectedBatches.reduce((sum,batch)=>sum+(sendSizeInputs[batch.id]??batch.sizes.map(String)).reduce((subtotal,value)=>subtotal+cellQuantity(value),0),0)
  const earliestSend = selectedBatches.map(batch => laundryPhysicalTime(batch.sewingDoneAt) || laundryPhysicalTime(batch.pickupAt)).sort().at(-1) ?? ''
  const sendTimeOk = validLaundryTime(sentAt) && sentAt >= earliestSend
  const recipe = instructionsFor(recipes, deliveries, sku, selectedVendor, sentAt)
  const colour = overrides.colour ?? recipe.colour
  const colourProcess = overrides.colourProcess ?? recipe.colourProcess
  const selectedProcess = overrides.service ?? recipe.service
  const colourAdjusted = (colour || colourProcess) && (colour !== recipe.colour || colourProcess !== recipe.colourProcess)
  const instructionSource = [recipe.source, colourAdjusted ? 'Diubah untuk surat ini' : ''].filter(Boolean).join(' · ')
  const rate = sendTimeOk ? laundryRateAt(selectedVendor, selectedProcess, sentAt.slice(0, 10)) : null
  const estimatedCost = rate === null ? null : selectedTotal * rate
  const choices = [...new Set([...colourProcesses, recipe.colourProcess, colourProcess].filter(Boolean))]
  const changeInstruction = (field: keyof LaundryInstructions, value: string) => setOverrides(current => ({ ...current, [field]: value }))
  function changeSku(value: string) {
    setSkuRef(value)
    if (value) setOverrides({})
  }
  function changeVendor(vendor: string) {
    if (!laundryVendorNames.includes(vendor)) return
    setReadyBatches(current => current.map(b => selectedIds.includes(b.id) ? { ...b, vendor } : b))
    onDraftVendor(selectedIds, vendor)
    setOverrides(current => ({ colour: current.colour }))
    if (vendorFilter !== 'Semua laundry') setVendorFilter(vendor)
    setNotice('')
  }
  function saveTicket(show = true) {
    sessionStorage.setItem('erp.demo.laundry.ticket.v1', JSON.stringify({
      ids: selectedIds, quantities: sendSizeInputs, process: selectedProcess, skuRef,
      colour, colourProcess, overrides, sentAt, note: sendNote,
    }))
    if (show) setNotice('Draft surat kirim tersimpan.')
  }
  const masterLink = laundryRecipePath + '&' + new URLSearchParams({
    vendor: selectedVendor, sku: skuRef, tanggal: sentAt.slice(0, 10),
  })
  const visibleDeliveries=scopedDeliveries.filter((delivery)=>vendorFilter==='Semua laundry'||delivery.vendor===vendorFilter).filter((delivery)=>!patternFilter||delivery.pattern?.id===patternFilter).filter(d=>browseMatch(query,d.id,d.parentId,d.batchId,d.skuRef,d.model,d.material,d.mandor,d.vendor,d.targetColor,d.colourProcess,d.process,patternSnapshotLabel(d.pattern),...d.sizeLabels)).sort((a,b)=>b.sequence-a.sequence)
  const outsideQty=scopedDeliveries.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
  const partialCount=scopedDeliveries.filter((delivery)=>laundryDeliveryStatus(delivery)==='Kembali sebagian').length
  const totalBs=scopedDeliveries.reduce((sum,delivery)=>sum+delivery.bs,0)

  const toggleBatch=(batch:LaundryReadyBatch)=>{
    setNotice('')
    if(selectedIds.includes(batch.id)){setSelectedIds(selectedIds.filter(id=>id!==batch.id));return}
    const replace=!selectedBatches.length||selectedParent!==batch.parentId||selectedVendor!==batch.vendor
    if (replace) {
      setOverrides({ service: batch.process || undefined })
      setSkuRef(batch.skuRef ?? '')
      setSendNote('')
      setSentAt(defaultSendTime(batch))
    }
    setSelectedIds(replace?[batch.id]:[...selectedIds,batch.id])
  }

  const postDelivery=()=>{
    const posted=selectedBatches.map((batch)=>{
      const sizes=(sendSizeInputs[batch.id]??batch.sizes.map(String)).map((value,index)=>Math.min(batch.sizes[index],cellQuantity(value))) as QtyTuple
      return{batch,sizes,qty:sizes.reduce((sum,value)=>sum+value,0)}
    }).filter((row)=>row.qty>0)
    if(!posted.length||!laundryVendorNames.includes(selectedVendor)||!sendTimeOk)return
    const startNo=deliveries.length+12
    const [physicalDate,physicalTime]=sentAt.split('T')
    const physicalSentAt=physicalDate==='2026-08-27'?`27 Agu 2026 · ${physicalTime}`:`${physicalDate} · ${physicalTime}`
    setDeliveries((current)=>[
      ...posted.map(({batch,qty,sizes},index)=>({id:`LDR-${physicalDate.replaceAll('-','').slice(2)}-${String(startNo+index).padStart(3,'0')}`,parentId:batch.parentId,sequence:batch.sequence,batchId:batch.id,plannedBrand:batch.plannedBrand,pattern:batch.pattern,model:batch.model,material:batch.material,mandor:batch.mandor,vendor:selectedVendor,process:selectedProcess,skuRef:skuRef||undefined,targetColor:colour.trim()||null,colourProcess:colourProcess||null,instructionSource:instructionSource||null,sendNote:sendNote.trim()||null,sentAt:physicalSentAt,estimatedRate:rate,qty,sizes,sizeLabels:batch.sizeLabels,good:0,bs:0,goodSizes:sizes.map(() => 0),bsSizes:sizes.map(() => 0),reversed:0,reversedSizes:sizes.map(() => 0)})),
      ...current,
    ])
    const sentById=new Map(posted.map((row)=>[row.batch.id,row.sizes]))
    setReadyBatches((current)=>current.flatMap((batch)=>{const sent=sentById.get(batch.id)??batch.sizes.map(() => 0);const sizes=batch.sizes.map((value,index)=>Math.max(0,value-sent[index])) as QtyTuple;const remaining=sizes.reduce((sum,value)=>sum+value,0);return remaining<=0?[]:[{...batch,qty:remaining,sizes}]}))
    setSendSizeInputs((current)=>{const next={...current};posted.forEach(({batch,sizes})=>{const remaining=batch.sizes.map((value,index)=>Math.max(0,value-sizes[index])) as QtyTuple;if(remaining.some((value)=>value>0))next[batch.id]=remaining.map(String) as string[];else delete next[batch.id]});return next})
    sessionStorage.removeItem('erp.demo.laundry.ticket.v1')
    onPosted(posted.map(({batch})=>batch.id))
    setSelectedIds([])
    setNotice(`${posted.reduce((sum,row)=>sum+row.qty,0)} pcs dicatat keluar ke ${selectedVendor}.`)
    setQuery('');setActiveTab('return')
  }

  const emptyReturnDraft=(delivery: LaundryDelivery)=>({good:delivery.sizeLabels.map(() => ''),bs:delivery.sizeLabels.map(() => '')})
  const updateReturn=(delivery:LaundryDelivery,sizeIndex:number,field:'good'|'bs',raw:string)=>{
    const outstanding=laundryOutstandingSizes(delivery)[sizeIndex]
    setReturnInputs((current)=>{
      const row=current[delivery.id]??emptyReturnDraft(delivery)
      const other=cellQuantity(row[field==='good'?'bs':'good'][sizeIndex])
      const nextField=[...row[field]] as string[]
      nextField[sizeIndex]=laundryDigits(raw,Math.max(0,outstanding-other))
      return{...current,[delivery.id]:{...row,[field]:nextField}}
    })
  }

  const postReturn=(delivery:LaundryDelivery)=>{
    const values=returnInputs[delivery.id]??emptyReturnDraft(delivery)
    const goodSizes=values.good.map(cellQuantity) as QtyTuple
    const bsSizes=values.bs.map(cellQuantity) as QtyTuple
    try {
      const updated = returnLaundry(delivery, returnTimes[delivery.id] ?? defaultReturnTime(delivery), goodSizes, bsSizes)
      setDeliveries(current => current.map(item => item.id === delivery.id ? updated : item))
      setReturnInputs(current => ({ ...current, [delivery.id]: emptyReturnDraft(delivery) }))
      setNotice((updated.good - delivery.good) + ' Good + ' + (updated.bs - delivery.bs) + ' BS diterima dari ' + delivery.vendor + '.')
    } catch (error) {
      setNotice((error as Error).message)
    }
  }

  const confirmReverse=()=>{
    if(!pendingReverse)return
    const outstanding=laundryOutstanding(pendingReverse)
    if(outstanding<=0){setPendingReverse(null);return}
    const reverseSizes=laundryOutstandingSizes(pendingReverse)
    setDeliveries((current)=>current.map((delivery)=>delivery.id===pendingReverse.id?{...delivery,reversed:delivery.reversed+outstanding,reversedSizes:delivery.reversedSizes.map((value,index)=>value+reverseSizes[index]) as QtyTuple,reverseNote:'Pindah laundry di detik akhir'}:delivery))
    const restored=laundryReadyFromDelivery(pendingReverse,outstanding)
    setReadyBatches((current)=>{
      const existing=current.find((batch)=>batch.id===pendingReverse.batchId)
      return existing?current.map((batch)=>{
        if(batch.id!==pendingReverse.batchId)return batch
        const nextQty=batch.qty+outstanding
        const source=laundryReadyFromSewingBatch(batch.id,'Belum dipilih')
        return {...batch,qty:nextQty,sizes:source?proportionalLaundrySizes(source.sizes,source.qty,nextQty):batch.sizes,vendor:'Belum dipilih'}
      }):[restored,...current]
    })
    const existingReady=readyBatches.find((batch)=>batch.id===pendingReverse.batchId)
    const restoredSizes=(existingReady?existingReady.sizes.map((value,index)=>value+reverseSizes[index]):reverseSizes) as QtyTuple
    setSendSizeInputs((current)=>({...current,[pendingReverse.batchId]:restoredSizes.map(String) as string[]}))
    const batchId=pendingReverse.batchId
    const vendor=pendingReverse.vendor
    setPendingReverse(null)
    onReturnToWip(batchId,vendor,outstanding)
  }

  return <>
    <section className="hero-copy compact laundry-hero"><div className="eyebrow">PRODUKSI · SETELAH SEWING</div><h1>Laundry</h1><p>Kirim Batch Distribusi yang jahitannya sudah penuh, lalu catat Good dan BS ketika kembali. Urutannya tetap mengikuti Batch Produksi.</p></section>
    <StageLots stage="laundry"/>
    <h2 className="gar-archive-heading">Arsip latihan Agustus</h2>
    <div className={`laundry-summary-scope ${mandorFiltered?'filtered':''}`} role="status" aria-live="polite"><Icon name={mandorFiltered?'filter':'user'}/>{mandorFiltered
      ?<span>Ringkasan &amp; daftar difilter untuk <b>{mandorFilter}</b> · {scopedReady.length} batch siap · {scopedDeliveries.length} surat kirim</span>
      :<span>Ringkasan untuk <b>semua mandor</b> ({mandorOptions.length} mandor)</span>}
      {mandorFiltered&&<button type="button" onClick={()=>setMandorFilter(LAUNDRY_ALL_MANDORS)}>Tampilkan semua mandor</button>}</div>
    <section className="laundry-kpi-grid" aria-label={mandorFiltered?`Ringkasan Laundry · ${mandorFilter}`:'Ringkasan Laundry · semua mandor'}>
      <div className="panel"><span>SIAP DIKIRIM</span><strong>{scopedReady.reduce((sum,batch)=>sum+batch.qty,0)} pcs</strong><small>{scopedReady.length} batch jahit</small></div>
      <div className="panel"><span>SEDANG DI LUAR</span><strong>{outsideQty} pcs</strong><small>{scopedDeliveries.filter((item)=>laundryOutstanding(item)>0).length} surat kirim aktif</small></div>
      <div className="panel"><span>KEMBALI SEBAGIAN</span><strong>{partialCount} kiriman</strong><small>tetap terbuka sampai habis</small></div>
      <div className="panel alert"><span>LAUNDRY BS</span><strong>{totalBs} pcs</strong><small>langsung masuk kasus BS</small></div>
    </section>
    {notice&&<div className="laundry-notice"><Icon name="check"/><strong>{notice}</strong></div>}
    <section className="panel laundry-workspace">
      <div className="laundry-toolbar">
        <div className="laundry-tabs"><button className={activeTab==='send'?'active':''} onClick={()=>{setActiveTab('send');setNotice('')}}><Icon name="arrow"/> Kirim ke laundry</button><button className={activeTab==='return'?'active':''} onClick={()=>{setActiveTab('return');setNotice('')}}><Icon name="boxes"/> Terima kembali</button></div>
        <label className="laundry-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari Potongan, batch, Pola, bahan..."/></label>
        <label className="laundry-pattern-filter"><span>POLA</span><select aria-label="Filter Pola Laundry" value={patternFilter} onChange={(event)=>setPatternFilter(event.target.value)}><option value="">Semua Pola</option>{patternOptions.map((pattern)=><option value={pattern.id} key={pattern.id}>{pattern.code} · {pattern.revision}</option>)}</select><small>DATA SIMULASI</small></label>
        <label className="laundry-mandor-filter"><span>MANDOR</span><select aria-label="Filter Mandor Laundry" value={mandorFilter} onChange={(event)=>setMandorFilter(event.target.value)}><option value={LAUNDRY_ALL_MANDORS}>{LAUNDRY_ALL_MANDORS}</option>{mandorOptions.map((mandor)=><option value={mandor} key={mandor}>{mandor}</option>)}</select><small>{mandorFiltered?'FILTER AKTIF':'PENANGGUNG JAWAB'}</small></label>
        <div className="laundry-vendors">{vendorOptions.map((vendor)=><button type="button" className={vendorFilter===vendor?'active':''} onClick={()=>setVendorFilter(vendor)} key={vendor}>{vendor}</button>)}</div>
      </div>

      {activeTab==='send'?<div className="laundry-send-layout">
        <div className="laundry-ready-pane">
          <div className="laundry-section-head"><div><span>SIAP BERANGKAT</span><h2>Pilih batch selesai jahit</h2><p>Satu surat kirim hanya berisi satu Batch Produksi dan satu laundry.</p></div><b>{visibleReady.length} batch</b></div>
          <div className="laundry-parent-list" data-keyboard-grid>{groupedReady.map(([parentId,batches],groupIndex)=>{const first=batches[0];return <article className="laundry-parent-card" key={parentId}>
            <header><span>{String(groupIndex+1).padStart(2,'0')}</span><div><small>{first.plannedBrand ? `MEREK RENCANA · OPSIONAL · ${first.plannedBrand}` : 'MEREK BELUM DITENTUKAN'} · BATCH PRODUKSI</small><h3>{first.model}</h3><small className="record-code">{parentId}</small><p className="laundry-pattern-snapshot">POLA · {patternSnapshotLabel(first.pattern)}</p><p className="laundry-mandor-line"><Icon name="user"/><span><small>MANDOR</small><strong>{laundryMandorOf(first)}</strong></span><em>{first.material}</em></p></div><div><strong className="piece-total">{batches.reduce((sum,batch)=>sum+batch.qty,0)} pcs</strong><small>{first.vendor}</small></div></header>
            <div className="laundry-batch-rows">{batches.map((batch,batchIndex)=>{const selected=selectedIds.includes(batch.id);const foreign=selectedBatches.length>0&&(selectedParent!==batch.parentId||selectedVendor!==batch.vendor);return <div className={`laundry-batch-row ${selected?'selected':''}`} key={batch.id}>
              <button type="button" className="laundry-batch-select" onClick={()=>toggleBatch(batch)}><span className="laundry-check">{selected&&<Icon name="check"/>}</span><div><span className="record-code">Batch {batch.id}</span><strong>{batch.note}</strong><small>Selesai {batch.sewingDoneAt}</small></div><b className="piece-total">{batch.qty} pcs</b></button>
              <div className="laundry-size-pills">{batch.sizeLabels.map((size,index)=>batch.sizes[index]>0&&<span key={size}>Size <b>{size}</b> · {batch.sizes[index]}</span>)}</div>
              {selected&&<div className="laundry-send-by-size"><span>QTY DIKIRIM PER SIZE</span><div>{batch.sizeLabels.map((size,sizeIndex)=><label key={size}><small>SIZE {size}</small><input inputMode="numeric" data-grid-row={groupIndex*100+batchIndex} data-grid-col={sizeIndex} value={(sendSizeInputs[batch.id]??batch.sizes.map(String))[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setSendSizeInputs((current)=>{const row=[...(current[batch.id]??batch.sizes.map(String))] as string[];row[sizeIndex]=laundryDigits(event.target.value,batch.sizes[sizeIndex]);return{...current,[batch.id]:row}})}/><em>/ {batch.sizes[sizeIndex]}</em></label>)}</div></div>}
              {foreign&&!selected&&<small className="laundry-switch-note">Memilih ini akan pindah ke surat kirim Potongan tersebut.</small>}
            </div>})}</div>
          </article>})}{groupedReady.length===0&&<div className="laundry-empty"><Icon name="search"/><strong>Batch tidak ditemukan</strong><small>Coba ganti laundry, mandor, Pola, atau kata pencarian.</small></div>}</div>
        </div>
        <aside className="laundry-ticket"><div className="laundry-section-head"><div><span>SURAT KIRIM</span><h2>Review sebelum keluar</h2></div></div>
          {selectedBatches.length>0?<div className="laundry-ticket-content">
            <div className="laundry-destination"><label>Laundry terpilih<select aria-label="Laundry terpilih" value={selectedVendor==='Belum dipilih'?'':selectedVendor} onChange={e=>changeVendor(e.target.value)}><option value="" disabled>Pilih laundry tujuan</option>{laundryVendorNames.map(v=><option key={v}>{v}</option>)}</select></label><small>{selectedParent} · {selectedBatches[0].material}</small></div>
            <fieldset className="laundry-colour-fields"><legend>Instruksi warna · opsional</legend>
              <label>Ambil dari SKU<select aria-label="Referensi SKU laundry" value={skuRef} onChange={e => changeSku(e.target.value)}>
                <option value="">Tanpa SKU</option>{articles.map(article => <option key={article.key} value={article.key}>{article.key} · {article.colour}</option>)}
              </select></label>
              {instructionSource && <p className="laundry-recipe-origin">{instructionSource}</p>}
              <label>Proses warna<select aria-label="Proses warna" value={colourProcess} onChange={e => changeInstruction('colourProcess', e.target.value)}>
                <option value="">Belum ditentukan</option>{choices.map(value => <option key={value}>{value}</option>)}
              </select></label>
              <label>Warna target<input aria-label="Warna target" value={colour} onChange={e => changeInstruction('colour', e.target.value)} placeholder="Isi jika sudah tahu"/></label>
              <a className="laundry-master-link" href={masterLink} onClick={() => saveTicket(false)}>Atur proses warna per laundry dan SKU</a>
            </fieldset>
            <label><span>Waktu fisik dikirim (WIB)</span><input type="datetime-local" value={sentAt} onChange={(event)=>setSentAt(event.target.value)}/></label>
            <label><span>CATATAN · OPSIONAL</span><input value={sendNote} onChange={(event)=>setSendNote(event.target.value)} placeholder="Contoh: pisahkan warna maroon"/></label>
            <details className="laundry-service-choice">
              <summary>Layanan untuk estimasi biaya</summary>
              <label>Layanan untuk estimasi<select aria-label="Layanan untuk estimasi" value={selectedProcess} onChange={e => changeInstruction('service', e.target.value)}>
                <option value="">Lengkapi saat kontra bon</option>{laundryProcesses.map(process => <option key={process}>{process}</option>)}
              </select></label>
            </details>
            <div className="laundry-cost-review"><p><span>Batch terpilih</span><b>{selectedBatches.length} batch</b></p><p><span>Qty dikirim</span><b>{selectedTotal} pcs</b></p><p><span>Tarif estimasi</span><b>{rate===null?'Belum diketahui':money(rate)+' / pcs'}</b></p><div><span>ESTIMASI BIAYA</span><strong>{estimatedCost===null?'Belum diketahui':money(estimatedCost)}</strong></div></div>
            <p className="laundry-estimate-note">{!sendTimeOk ? 'Waktu kirim harus sama atau sesudah batch selesai dijahit.' : rate === null
              ? 'Barang tetap bisa dikirim dan diterima. Jenis cucian serta biaya dapat dilengkapi saat kontra bon.'
              : 'Tarif estimasi mengikuti laundry, jenis cucian, dan tanggal kirim.'}</p>
            <div className="laundry-ticket-actions"><button type="button" className="soft-btn" onClick={() => saveTicket()}>Simpan draft</button><button type="button" className="primary-btn" disabled={selectedTotal<=0||!sendTimeOk||!laundryVendorNames.includes(selectedVendor)} onClick={postDelivery}>Catat dikirim <Icon name="arrow"/></button></div>
          </div>:<div className="laundry-empty ticket"><Icon name="boxes"/><strong>Belum ada batch dipilih</strong><small>Tekan batch di kiri. Surat kirim otomatis mengikuti Batch Produksi dan laundry tujuan.</small></div>}
        </aside>
      </div>:<div className="laundry-return-pane">
        <div className="laundry-section-head"><div><span>BARANG KEMBALI</span><h2>Good + BS dari laundry</h2><p>Boleh kembali sebagian. Good lanjut ke QC; BS otomatis menjadi kasus terbuka.</p></div><b>{visibleDeliveries.length} surat kirim</b></div>
        <div className="laundry-return-list">{visibleDeliveries.map((delivery,index)=>{
          const received=delivery.good+delivery.bs
          const outstanding=laundryOutstanding(delivery)
          const outstandingSizes=laundryOutstandingSizes(delivery)
          const returnedSizes=laundryReturnedSizes(delivery)
          const progress=Math.round((received+delivery.reversed)/Math.max(1,delivery.qty)*100)
          const status=laundryDeliveryStatus(delivery)
          const values=returnInputs[delivery.id]??emptyReturnDraft(delivery)
          const returnedAt = returnTimes[delivery.id] ?? defaultReturnTime(delivery)
          const returnTimeOk = validLaundryTime(returnedAt) && returnedAt >= laundryPhysicalTime(delivery.sentAt)
          const inputGood=values.good.map(cellQuantity) as QtyTuple
          const inputBs=values.bs.map(cellQuantity) as QtyTuple
          const inputTotal=inputGood.reduce((sum,value)=>sum+value,0)+inputBs.reduce((sum,value)=>sum+value,0)
          const reversedStatus=status==='Kembali ke WIP'||status==='Sisa kembali WIP'
          return <article className={`laundry-return-card ${reversedStatus?'reversed':''}`} key={delivery.id}>
          <header><span>{String(index+1).padStart(2,'0')}</span><div><small>{delivery.plannedBrand ? `MEREK RENCANA · ${delivery.plannedBrand}` : 'MEREK BELUM DITENTUKAN'} · {delivery.id}</small><h3>{delivery.model}</h3><p className="record-code">{delivery.parentId} · Batch {delivery.batchId} · {delivery.material}</p>{(delivery.skuRef||delivery.targetColor||delivery.colourProcess)&&<p>{[delivery.skuRef,delivery.colourProcess,delivery.targetColor].filter(Boolean).join(' · ')}</p>}{delivery.sendNote&&<p>{delivery.sendNote}</p>}{delivery.instructionSource&&<small>{delivery.instructionSource}</small>}<p className="laundry-pattern-snapshot">POLA · {patternSnapshotLabel(delivery.pattern)}</p></div><em className={status==='Selesai'?'done':status==='Kembali sebagian'?'partial':reversedStatus?'reversed':''}>{status}</em><div><strong>{delivery.vendor}</strong><small>{delivery.process||'Jenis cucian belum ditentukan'}</small></div></header>
          <div className="laundry-return-body"><div className="laundry-return-facts"><div className="laundry-mandor-hero"><Icon name="user"/><span><small>MANDOR PENANGGUNG JAWAB</small><strong>{laundryMandorOf(delivery)}</strong></span></div><div className="laundry-counts"><span><small>DIKIRIM</small><strong className="piece-total">{delivery.qty} pcs</strong></span><span><small>SUDAH KEMBALI</small><strong className="piece-total">{received} pcs</strong></span><span><small>MASIH DI LUAR</small><strong className="piece-total">{outstanding} pcs</strong></span></div><div className="laundry-progress"><span style={{width:`${progress}%`}}/></div><p><Icon name="calendar"/> Dikirim {delivery.sentAt} WIB</p>
            {delivery.estimatedRate !== undefined && <small>Estimasi saat kirim · {delivery.estimatedRate === null ? 'Belum diketahui' : money(delivery.estimatedRate) + ' / pcs'}</small>}
            {delivery.returns?.length ? <details className="laundry-return-history"><summary>Riwayat kembali ({delivery.returns.length})</summary>
              {delivery.returns.map((row, i) => <p key={i}><time dateTime={row.at + '+07:00'}>{row.at.replace('T', ' · ')} WIB</time> · {row.good.reduce((sum, qty) => sum + qty, 0)} Good · {row.bs.reduce((sum, qty) => sum + qty, 0)} BS</p>)}
            </details> : null}{received>0&&<><small>Akumulasi: <b className="good">{delivery.good} Good</b> · <b className="bs">{delivery.bs} BS</b></small><button type="button" className="laundry-open-qc" onClick={()=>onOpenQc(delivery.parentId,delivery.batchId)}><Icon name="audit"/><span><strong>Buka QC & Final SKU</strong><small>{received} pcs sudah bisa diperiksa sekarang</small></span><Icon name="arrow"/></button></>}{delivery.reversed>0&&<small className="reversed-note"><b>{delivery.reversed} pcs kembali ke WIP</b> · {delivery.reverseNote}</small>}{outstanding>0&&<button type="button" className="laundry-reverse-btn" onClick={()=>setPendingReverse(delivery)}><Icon name="reset"/><span><strong>Kembalikan ke WIP</strong><small>{outstanding} pcs bisa pilih laundry lain</small></span></button>}</div>
            {outstanding>0?<div className="laundry-return-entry size-mode" data-keyboard-grid><div className="laundry-return-entry-head"><span>TERIMA PER SIZE</span><small>Good ke QC dan Stuck dihitung persis per ukuran.</small></div><div className="laundry-return-size-head"><span>Size</span><span>Dikirim</span><span>Kembali</span><span>Good → QC</span><span>BS</span><span>Stuck sesudah</span></div><div className="laundry-return-size-rows">{delivery.sizeLabels.map((size,sizeIndex)=><div className="laundry-return-size-row" key={size}><strong>{size}</strong><span>{delivery.sizes[sizeIndex]}</span><span>{returnedSizes[sizeIndex]}</span><label><input aria-label={'Good kembali ukuran '+size} inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={0} value={values.good[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateReturn(delivery,sizeIndex,'good',event.target.value)} placeholder="0"/></label><label className="bs"><input aria-label={'BS kembali ukuran '+size} inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={1} value={values.bs[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateReturn(delivery,sizeIndex,'bs',event.target.value)} placeholder="0"/></label><strong className="stuck">{Math.max(0,outstandingSizes[sizeIndex]-inputGood[sizeIndex]-inputBs[sizeIndex])}</strong></div>)}</div><label className="return-time"><span>Waktu fisik kembali (WIB)</span><input type="datetime-local" min={laundryPhysicalTime(delivery.sentAt)} value={returnedAt} onChange={(event)=>setReturnTimes((current)=>({...current,[delivery.id]:event.target.value}))}/></label>{!returnTimeOk && <small role="alert">Waktu kembali harus sama atau sesudah waktu kirim.</small>}<div className="laundry-return-action"><span>Total input <b>{inputTotal} pcs</b> · sisa <b>{Math.max(0,outstanding-inputTotal)} pcs</b></span><button type="button" className="primary-btn" disabled={inputTotal<=0||!returnTimeOk} onClick={()=>postReturn(delivery)}>Catat kembali <Icon name="arrow"/></button></div></div>:<div className="laundry-return-done"><Icon name={delivery.reversed>0?'reset':'check'}/><strong>{delivery.reversed>0?'Qty aktif sudah kembali ke WIP':'Pengiriman selesai'}</strong><small>{delivery.reversed>0?`${delivery.reversed} pcs siap dipilihkan laundry baru · histori lama tetap ada`:`${delivery.good} Good sudah bisa dibuka di QC · ${delivery.bs} BS tercatat`}</small></div>}
          </div>
        </article>})}{visibleDeliveries.length===0&&<div className="laundry-empty"><Icon name="search"/><strong>Surat kirim tidak ditemukan</strong><small>Coba ganti laundry, mandor, Pola, atau kata pencarian.</small></div>}</div>
      </div>}
    </section>
    {pendingReverse&&<div className="wip-confirm-layer" role="presentation"><section className="wip-confirm-dialog laundry-reverse-dialog" role="alertdialog" aria-modal="true" aria-labelledby="reverse-laundry-title"><div className="wip-confirm-icon reverse"><Icon name="reset"/></div><div><span>REVERSE PENGIRIMAN</span><h2 id="reverse-laundry-title">Kembalikan ke WIP?</h2><p><strong>{laundryOutstanding(pendingReverse)} pcs</strong> yang masih di {pendingReverse.vendor} akan muncul lagi di WIP dan bisa langsung dipilihkan laundry lain. {pendingReverse.good+pendingReverse.bs>0&&`${pendingReverse.good+pendingReverse.bs} pcs yang sudah kembali tetap tercatat.`}</p><small>Jejak surat kirim lama tidak dihapus; statusnya berubah menjadi Kembali ke WIP.</small></div><div className="wip-confirm-actions"><button type="button" className="soft-btn" onClick={()=>setPendingReverse(null)}>Jangan</button><button type="button" className="primary-btn reverse" onClick={confirmReverse}>Ya, kembali ke WIP <Icon name="arrow"/></button></div></section></div>}
  </>
}
