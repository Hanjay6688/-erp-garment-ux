import { Icon } from '../components/AppIcon'
import { Field } from './controls'
import {
  balancedBatchTargets,
  cellQuantity,
  createEmptyRollBatchSizeMatrix,
  createRollBatchSizeMatrix,
  createSizeAllocationMatrix,
  cuttingSizes,
  fabricRollCatalog,
  rollSizeQuantities,
} from './cuttingAllocation'
import type { AllocationMatrix, RollBatchSizeMatrix } from './cuttingAllocation'
import { RollBatchQuickMenu, UnassignedRollCard } from './CuttingRollPage'
import { formatQuantity } from './format'
import { patternSnapshotLabel, simulationPatternSnapshots } from './productionModel'
import type { ProductionPatternSnapshot, QtyTuple } from './productionModel'
import { useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'

type WipAllocationMode = 'roll' | 'size'

type PickupQueueFilter = 'WAITING' | 'PICKED' | 'ALL'

type PickupQueueStatus = 'READY' | 'REVIEW' | 'PICKED'

type PickupQueueRoll = {
  id: string
  sequence: number
  material: string
  sourceYards: number
  usedYards: number
  remainingYards: number
  slots: Array<{
    size: string
    image: string
    qty: number
  }>
  batchNumbers: number[]
}

type PickupQueueItem = {
  id: string
  model: string
  material: string
  supplier: string
  sizes: string[]
  pattern: ProductionPatternSnapshot | null
  status: PickupQueueStatus
  mandor?: string
  pickupAt?: string
  rolls: PickupQueueRoll[]
}

const pickupRollTotal = (roll: PickupQueueRoll) => roll.slots.reduce((sum, slot) => sum + slot.qty, 0)

const pickupItemTotal = (item: PickupQueueItem) => item.rolls.reduce((sum, roll) => sum + pickupRollTotal(roll), 0)

const pickupItemUsedYards = (item: PickupQueueItem) => item.rolls.reduce((sum, roll) => sum + roll.usedYards, 0)

const pairedPickupSlots = (sizes: readonly string[], quantities: readonly number[]) => sizes.flatMap((size, sizeIndex) => [
  { size, image: 'A', qty: quantities[sizeIndex * 2] ?? 0 },
  { size, image: 'B', qty: quantities[(sizeIndex * 2) + 1] ?? 0 },
])

export function MandorWipPage({ batchNotes, setBatchNotes }: { batchNotes: string[]; setBatchNotes: (updater: (current: string[]) => string[]) => void }) {
  const wipRolls = fabricRollCatalog.slice(0, 9)
  const wipRollRows = wipRolls.map((roll) => {
    const sizes = rollSizeQuantities(roll.allocation)
    return { roll, sizes, quantity: sizes.reduce((sum, qty) => sum + qty, 0) }
  })
  const wipSizeTotals = wipRollRows.reduce<QtyTuple>((totals, row) => totals.map((qty, index) => qty + row.sizes[index]) as QtyTuple, [0, 0, 0])
  const wipTotal = wipSizeTotals.reduce((sum, qty) => sum + qty, 0)
  const [mandor,setMandor] = useState('Mandor Afat')
  const [pickupAt,setPickupAt] = useState('2026-08-27T10:30')
  const [batchCountInput,setBatchCountInput] = useState('3')
  const [batchCount,setBatchCount] = useState(3)
  const [allocationMode,setAllocationMode] = useState<WipAllocationMode>('roll')
  const [rollBatchMatrix,setRollBatchMatrix] = useState<RollBatchSizeMatrix>(() => createEmptyRollBatchSizeMatrix(wipRolls, 3))
  const [sizeMatrix,setSizeMatrix] = useState<AllocationMatrix>(() => createSizeAllocationMatrix(wipSizeTotals, 3))
  const [rollAllocationTouched,setRollAllocationTouched] = useState(false)
  const [sizeAllocationTouched,setSizeAllocationTouched] = useState(false)
  const [batchResizeMessage,setBatchResizeMessage] = useState('')
  const [splitEditorRollId,setSplitEditorRollId] = useState<string | null>(null)
  const [allocationMessage,setAllocationMessage] = useState('')
  const [rollDrag,setRollDrag] = useState<{ rollId: string; target: number | null; x: number; y: number } | null>(null)
  const [queueFilter,setQueueFilter] = useState<PickupQueueFilter>('WAITING')
  const [queuePatternId,setQueuePatternId] = useState('')
  const [queueQuery,setQueueQuery] = useState('')
  const [queueDetailId,setQueueDetailId] = useState<string|null>(null)
  const rollDragRef = useRef<{ rollId: string; target: number | null; x: number; y: number } | null>(null)
  const effectiveBatchCount = batchCount
  const targetTotals = balancedBatchTargets(wipTotal, batchCount)
  const sourceChecks = allocationMode === 'roll'
    ? wipRollRows.flatMap((row) => row.sizes.map((total, sizeIndex) => ({
      key: `${row.roll.id} · Size ${cuttingSizes[sizeIndex]}`,
      total,
      assigned: (rollBatchMatrix[row.roll.id] ?? []).reduce((sum, batchSizes) => sum + cellQuantity(batchSizes[sizeIndex]), 0),
    })))
    : cuttingSizes.map((size, sizeIndex) => ({
      key: `Size ${size}`,
      total: wipSizeTotals[sizeIndex],
      assigned: (sizeMatrix[size] ?? []).reduce((sum, value) => sum + cellQuantity(value), 0),
    }))
  const sourcesExact = sourceChecks.every((source) => source.assigned === source.total)
  const batchSizeMix = Array.from({ length: effectiveBatchCount }, (_, batchIndex) => cuttingSizes.map((size, sizeIndex) => {
    if (allocationMode === 'size') return cellQuantity(sizeMatrix[size]?.[batchIndex])
    return wipRollRows.reduce((sum, row) => sum + cellQuantity(rollBatchMatrix[row.roll.id]?.[batchIndex]?.[sizeIndex]), 0)
  }) as QtyTuple)
  const batchTotals = batchSizeMix.map((sizes) => sizes.reduce((sum, qty) => sum + qty, 0))
  const assignedTotal = batchTotals.reduce((sum, qty) => sum + qty, 0)
  const remainingTotal = wipTotal - assignedTotal
  const splitRolls = wipRollRows.filter((row) => (rollBatchMatrix[row.roll.id] ?? []).filter((sizes) => sizes.reduce((sum, value) => sum + cellQuantity(value), 0) > 0).length > 1)
  const wholeRolls = wipRollRows.filter((row) => {
    const batches = rollBatchMatrix[row.roll.id] ?? []
    const usedBatches = batches.filter((sizes) => sizes.reduce((sum, value) => sum + cellQuantity(value), 0) > 0)
    return usedBatches.length === 1 && row.sizes.every((source, sizeIndex) => cellQuantity(usedBatches[0][sizeIndex]) === source)
  })
  const unassignedRollRows = wipRollRows.filter((row) => (rollBatchMatrix[row.roll.id] ?? []).every((sizes) => sizes.reduce((sum, value) => sum + cellQuantity(value), 0) === 0))
  const queueItems:PickupQueueItem[] = [
    {
      id:'POT-260827-042',model:'Kulot Lucy',material:'Lucy',supplier:'Sinaran',sizes:cuttingSizes,pattern:simulationPatternSnapshots.lucyRegular,status:'READY',
      rolls:wipRollRows.map((row)=>({
        id:row.roll.id,
        sequence:row.roll.sequence,
        material:row.roll.material,
        sourceYards:row.roll.yards,
        usedYards:row.roll.yards,
        remainingYards:0,
        slots:pairedPickupSlots(cuttingSizes,row.roll.allocation),
        batchNumbers:(rollBatchMatrix[row.roll.id]??[]).flatMap((sizes,batchIndex)=>sizes.some((value)=>cellQuantity(value)>0)?[batchIndex+1]:[]),
      })),
    },
    {
      id:'POT-260827-043',model:'Nevada Loose',material:'Nevada 12 Oz',supplier:'Sumber Cahaya',sizes:['30','31','32'],pattern:simulationPatternSnapshots.nevadaLoose,status:'REVIEW',
      rolls:[
        {id:'NV-260827-01',sequence:1,material:'Nevada 12 Oz',sourceYards:112,usedYards:108.5,remainingYards:3.5,slots:pairedPickupSlots(['30','31','32'],[18,18,18,18,18,18]),batchNumbers:[]},
        {id:'NV-260827-02',sequence:2,material:'Nevada 12 Oz',sourceYards:110.5,usedYards:107,remainingYards:3.5,slots:pairedPickupSlots(['30','31','32'],[18,18,18,18,18,18]),batchNumbers:[]},
      ],
    },
    {
      id:'POT-260827-041',model:'Malibu Regular',material:'Malibu',supplier:'Sinaran',sizes:['28','29','30'],pattern:simulationPatternSnapshots.malibuRegular,status:'PICKED',mandor:'Mandor Epi',pickupAt:'27 Agu 2026 · 08:40',
      rolls:[
        {id:'MLB-260826-11',sequence:11,material:'Malibu',sourceYards:119.5,usedYards:116,remainingYards:3.5,slots:pairedPickupSlots(['28','29','30'],[21,21,21,21,21,21]),batchNumbers:[1]},
        {id:'MLB-260826-12',sequence:12,material:'Malibu',sourceYards:113,usedYards:110.5,remainingYards:2.5,slots:pairedPickupSlots(['28','29','30'],[20,20,20,20,20,20]),batchNumbers:[1]},
        {id:'MLB-260826-13',sequence:13,material:'Malibu',sourceYards:114.5,usedYards:111,remainingYards:3.5,slots:pairedPickupSlots(['28','29','30'],[20,20,20,20,20,20]),batchNumbers:[2]},
        {id:'MLB-260826-14',sequence:14,material:'Malibu',sourceYards:116,usedYards:112.5,remainingYards:3.5,slots:pairedPickupSlots(['28','29','30'],[20,20,20,21,20,21]),batchNumbers:[3]},
      ],
    },
    {
      id:'POT-260827-039',model:'Zodiak KW',material:'Zodiak',supplier:'Sumber Cahaya',sizes:['34','35','36'],pattern:simulationPatternSnapshots.zodiakJumbo,status:'PICKED',mandor:'Mandor Afui',pickupAt:'26 Agu 2026 · 16:20',
      rolls:[
        {id:'ZDK-260826-07',sequence:7,material:'Zodiak KW',sourceYards:107,usedYards:103.5,remainingYards:3.5,slots:pairedPickupSlots(['34','35','36'],[19,19,19,19,19,19]),batchNumbers:[1]},
        {id:'ZDK-260826-08',sequence:8,material:'Zodiak KW',sourceYards:106.5,usedYards:103,remainingYards:3.5,slots:pairedPickupSlots(['34','35','36'],[19,19,19,19,19,19]),batchNumbers:[2]},
        {id:'ZDK-260826-09',sequence:9,material:'Zodiak KW',sourceYards:105,usedYards:101.5,remainingYards:3.5,slots:pairedPickupSlots(['34','35','36'],[19,19,19,19,19,19]),batchNumbers:[3]},
      ],
    },
  ]
  const normalizedQueueQuery=queueQuery.trim().toLowerCase()
  const visibleQueueItems=queueItems.filter((item)=>{
    const statusMatch=queueFilter==='ALL'||(queueFilter==='PICKED'?item.status==='PICKED':item.status!=='PICKED')
    const queryMatch=!normalizedQueueQuery||`${item.id} ${item.model} ${item.material} ${item.supplier} ${item.mandor??''} ${item.pattern?.code??''} ${item.pattern?.revision??''} ${item.pattern?.name??''}`.toLowerCase().includes(normalizedQueueQuery)
    const patternMatch=!queuePatternId||item.pattern?.id===queuePatternId
    return statusMatch&&patternMatch&&queryMatch
  })
  const selectedQueueItem=queueItems.find((item)=>item.id==='POT-260827-042')!
  const queueDetailItem=queueItems.find((item)=>item.id===queueDetailId)??null
  const queueDetailSlots=queueDetailItem?.rolls[0]?.slots.map(({size,image})=>({size,image}))??[]
  const queueDetailSourceYards=queueDetailItem?.rolls.reduce((sum,roll)=>sum+roll.sourceYards,0)??0
  const queueDetailRemainingYards=queueDetailItem?.rolls.reduce((sum,roll)=>sum+roll.remainingYards,0)??0
  const resizeBatchCount = (requestedCount: number) => {
    const nextCount = Math.max(1, Math.round(requestedCount || 1))
    if (nextCount === batchCount) {
      setBatchCountInput(String(batchCount))
      setBatchResizeMessage('Jumlah batch tidak berubah; pembagian lu tetap aman.')
      return
    }
    if (nextCount < batchCount) {
      const removedIndexes = Array.from({ length: batchCount - nextCount }, (_, index) => nextCount + index)
      const rollBlocked = rollAllocationTouched && removedIndexes.some((batchIndex) => wipRollRows.some((row) => (rollBatchMatrix[row.roll.id]?.[batchIndex] ?? []).some((value) => cellQuantity(value) > 0)))
      const sizeBlocked = sizeAllocationTouched && removedIndexes.some((batchIndex) => cuttingSizes.some((size) => cellQuantity(sizeMatrix[size]?.[batchIndex]) > 0))
      if (rollBlocked || sizeBlocked) {
        const blockedModes = [rollBlocked ? 'Per Roll' : '', sizeBlocked ? 'Per Size' : ''].filter(Boolean).join(' & ')
        setBatchCountInput(String(batchCount))
        setBatchResizeMessage(`Tidak bisa hapus: batch terakhir masih berisi pembagian ${blockedModes}. Pindahkan atau kosongkan dulu.`)
        return
      }
    }
    setRollBatchMatrix((current) => {
      const currentHasQuantity = wipRolls.some((roll) => (current[roll.id] ?? []).some((sizes) => sizes.some((value) => cellQuantity(value) > 0)))
      if (nextCount === 1 && !currentHasQuantity) return createRollBatchSizeMatrix(wipRolls, 1)
      return Object.fromEntries(wipRolls.map((roll) => {
        const currentBatches = current[roll.id] ?? []
        const resized = Array.from({ length: nextCount }, (_, batchIndex) => currentBatches[batchIndex] ? [...currentBatches[batchIndex]] : ['0', '0', '0'])
        return [roll.id, resized]
      }))
    })
    setSizeMatrix((current) => sizeAllocationTouched
      ? Object.fromEntries(cuttingSizes.map((size) => [size, Array.from({ length: nextCount }, (_, batchIndex) => current[size]?.[batchIndex] ?? '0')]))
      : createSizeAllocationMatrix(wipSizeTotals, nextCount))
    setBatchNotes((current) => Array.from({ length: nextCount }, (_, batchIndex) => current[batchIndex] ?? ''))
    setBatchCountInput(String(nextCount))
    setBatchCount(nextCount)
    setSplitEditorRollId(null)
    setAllocationMessage('')
    setBatchResizeMessage(nextCount > batchCount ? `Batch ${String(nextCount).padStart(2, '0')} ditambahkan; isi lama tetap di tempatnya.` : 'Batch terakhir yang kosong sudah dihapus; isi lain tetap aman.')
  }
  const applyBatchCount = () => resizeBatchCount(Number(batchCountInput))
  const selectAllocationMode = (nextMode: WipAllocationMode) => {
    if (nextMode === allocationMode) return
    setSplitEditorRollId(null)
    setAllocationMessage('')
    setAllocationMode(nextMode)
  }
  const updateSplitAllocation = (rollId: string, batchIndex: number, sizeIndex: number, rawValue: string) => {
    if (/[+-]/.test(rawValue)) {
      setAllocationMessage('Gunakan jumlah absolut. +/− adalah koreksi sumber, bukan pembagian batch.')
      return
    }
    const digits = rawValue.replace(/[^0-9]/g, '')
    const normalized = digits.replace(/^0+(?=\d)/, '')
    setAllocationMessage('')
    setRollAllocationTouched(true)
    setRollBatchMatrix((current) => {
      const rollBatches = (current[rollId] ?? Array.from({ length: batchCount }, () => ['0', '0', '0'])).map((sizes) => [...sizes])
      rollBatches[batchIndex][sizeIndex] = normalized
      return { ...current, [rollId]: rollBatches }
    })
  }
  const updateSizeAllocation = (size: string, batchIndex: number, rawValue: string) => {
    if (/[+-]/.test(rawValue)) {
      setAllocationMessage('Gunakan jumlah absolut. Pindahkan qty antarbatch tanpa mengubah sumber size.')
      return
    }
    const digits = rawValue.replace(/[^0-9]/g, '')
    const normalized = digits.replace(/^0+(?=\d)/, '')
    setAllocationMessage('')
    setSizeAllocationTouched(true)
    setSizeMatrix((current) => ({
      ...current,
      [size]: (current[size] ?? Array(batchCount).fill('0')).map((value, index) => index === batchIndex ? normalized : value),
    }))
  }
  const assignWholeRoll = (rollId: string, targetBatch: number) => {
    const sourceRow = wipRollRows.find((row) => row.roll.id === rollId)
    if (!sourceRow) return
    setRollBatchMatrix((current) => ({
      ...current,
      [rollId]: Array.from({ length: batchCount }, (_, batchIndex) => batchIndex === targetBatch ? sourceRow.sizes.map(String) : ['0', '0', '0']),
    }))
    setRollAllocationTouched(true)
    setAllocationMessage(`Roll ${String(sourceRow.roll.sequence).padStart(2,'0')} masuk ke Batch ${String(targetBatch+1).padStart(2,'0')}.`)
  }
  const unassignRoll = (rollId: string) => {
    setRollBatchMatrix((current) => ({ ...current, [rollId]: Array.from({ length: batchCount }, () => ['0', '0', '0']) }))
    setRollAllocationTouched(true)
    if (splitEditorRollId === rollId) setSplitEditorRollId(null)
    setAllocationMessage('')
  }
  const beginRollDrag = (event: ReactPointerEvent<HTMLButtonElement>, rollId: string) => {
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    const next = { rollId, target: null, x: event.clientX, y: event.clientY }
    rollDragRef.current = next
    setRollDrag(next)
  }
  const moveRollDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const current = rollDragRef.current
    if (!current) return
    const targetElement = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>('[data-wip-drop-batch]')
    const parsedTarget = Number(targetElement?.dataset.wipDropBatch)
    const target = Number.isFinite(parsedTarget) && parsedTarget >= 0 && parsedTarget < batchCount ? parsedTarget : null
    const next = { ...current, target, x: event.clientX, y: event.clientY }
    rollDragRef.current = next
    setRollDrag(next)
  }
  const finishRollDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const current = rollDragRef.current
    if (current?.target !== null && current?.target !== undefined) assignWholeRoll(current.rollId, current.target)
    rollDragRef.current = null
    setRollDrag(null)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const cancelRollDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    rollDragRef.current = null
    setRollDrag(null)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const tidyWholeRolls = () => {
    setRollBatchMatrix(createRollBatchSizeMatrix(wipRolls, batchCount))
    setRollAllocationTouched(true)
    setSplitEditorRollId(null)
    setAllocationMessage('')
  }
  const splitEditorRow = wipRollRows.find((row) => row.roll.id === splitEditorRollId)
  const splitEditorChecks = splitEditorRow?.sizes.map((source, sizeIndex) => {
    const assigned = (rollBatchMatrix[splitEditorRow.roll.id] ?? []).reduce((sum, sizes) => sum + cellQuantity(sizes[sizeIndex]), 0)
    return { source, assigned, remaining: source - assigned }
  }) ?? []
  const splitEditorExact = splitEditorChecks.every((check) => check.remaining === 0)
  const isReady = sourcesExact && assignedTotal === wipTotal && mandor.length > 0 && pickupAt.length > 0
  const pickupReviewAt = pickupAt ? new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(pickupAt)) : 'Belum diisi'

  return <>
    <section className="hero-copy compact cutting-hero"><div className="eyebrow">PRODUKSI · PICKUP MANDOR</div><h1>Bagi Potongan</h1><p>Pilih Potongan yang sudah selesai cutting. Setelah mandor mengambil, baru bentuk batch kerja dan beri arahan jahitan atau warna untuk setiap batch.</p></section>
    <section className="wip-flow-rail panel" aria-label="Alur pickup dan pembentukan batch">{['Pilih WIP Potongan','Catat mandor mengambil','Tentukan jumlah batch','Drag roll / batch per size'].map((label,index)=><div className={index===0?'active':''} key={label}><span>{String(index+1).padStart(2,'0')}</span><strong>{label}</strong>{index<3&&<Icon name="arrow"/>}</div>)}</section>
    <section className="wip-pickup-layout">
      <aside className="panel wip-queue-panel">
        <div className="wip-queue-head"><div><span>01 · WIP POTONGAN</span><h2>{queueFilter==='WAITING'?'Menunggu diambil':queueFilter==='PICKED'?'Sudah diambil':'Semua potongan'}</h2><p>Filter tidak mengubah status atau isi pembagian.</p></div><span className="selection-pill">{visibleQueueItems.length} tampil</span></div>
        <div className="wip-queue-tabs" role="group" aria-label="Filter status pickup">{(['WAITING','PICKED','ALL'] as const).map((filter)=><button type="button" className={queueFilter===filter?'active':''} aria-pressed={queueFilter===filter} key={filter} onClick={()=>setQueueFilter(filter)}>{filter==='WAITING'?'Menunggu':filter==='PICKED'?'Sudah diambil':'Semua'}</button>)}</div>
        <label className="wip-search"><Icon name="search"/><input value={queueQuery} onChange={(event)=>setQueueQuery(event.target.value)} placeholder="Cari kode, Pola, bahan, model, mandor..."/></label>
        <label className="simulation-pattern-filter"><span>POLA</span><select aria-label="Filter Pola Bagi Potongan" value={queuePatternId} onChange={(event)=>setQueuePatternId(event.target.value)}><option value="">Semua Pola</option>{Object.values(simulationPatternSnapshots).map((item)=><option value={item.id} key={item.id}>{item.code} · {item.revision} · {item.name}</option>)}</select><small>DATA SIMULASI · filter tidak mengubah transaksi</small></label>
        <div className="wip-queue-list">{visibleQueueItems.map((item)=>{const itemTotal=pickupItemTotal(item);const usedYards=pickupItemUsedYards(item);return <article className={`wip-queue-card ${item.id==='POT-260827-042'?'selected':''} ${item.status.toLowerCase()}`} key={item.id}>
          <div className="wip-queue-card-main">
            <span className="wip-queue-status">{item.status==='PICKED'?'SUDAH DIAMBIL':item.status==='REVIEW'?'MENUNGGU REVIEW':'SIAP DIAMBIL'}</span>
            <strong>{item.id}</strong><small>{item.model}</small>
            <div className="wip-queue-card-meta"><span><small>BAHAN</small><strong>{item.material}</strong></span><span><small>PABRIK</small><strong>{item.supplier}</strong></span><span className="wip-queue-pattern" data-pattern-snapshot={item.pattern?.id??'legacy-null'}><small>POLA · SNAPSHOT</small><strong>{patternSnapshotLabel(item.pattern)}</strong></span></div>
            <div className="wip-queue-card-numbers"><span><b>{itemTotal} pcs</b><small>{item.rolls.length} roll sumber</small></span><span><b>{formatQuantity(usedYards,2)} yd</b><small>yard dipakai</small></span><em>{item.sizes.join(' · ')}</em></div>
            {item.status==='PICKED'?<p><Icon name="user"/><span><small>DIAMBIL OLEH</small><strong>{item.mandor}</strong><em>{item.pickupAt}</em></span></p>:null}
          </div>
          <footer><span>{item.status==='PICKED'?`${new Set(item.rolls.flatMap((roll)=>roll.batchNumbers)).size} batch distribusi`:'Belum masuk Sewing'}</span><button type="button" onClick={()=>setQueueDetailId(item.id)}>Lihat detail roll <Icon name="arrow"/></button></footer>
        </article>})}{visibleQueueItems.length===0?<div className="wip-queue-empty"><Icon name="search"/><strong>Potongan tidak ditemukan</strong><small>Ubah filter status atau kata pencarian.</small></div>:null}</div>
      </aside>

      <div className="panel wip-batch-workspace">
        <div className="wip-selected-head"><div><span>WIP TERPILIH</span><h2>POT-260827-042 · Kulot Lucy</h2><p>{wipTotal} pcs dari 9 roll · selesai potong 27 Agu 2026</p><div className="wip-selected-pattern" data-pattern-snapshot={selectedQueueItem.pattern?.id??'legacy-null'}><Icon name="audit"/><span><small>POLA SNAPSHOT · TERKUNCI</small><strong>{patternSnapshotLabel(selectedQueueItem.pattern)}</strong></span></div></div><span className="wip-waiting-pill"><span/> Belum diambil</span></div>
        <div className="pickup-meta-grid">
          <Field label="Diambil oleh / mandor"><select className="erp-input" value={mandor} onChange={(event)=>setMandor(event.target.value)}><option>Mandor Afat</option><option>Mandor Asep</option><option>Mandor Dedi</option></select></Field>
          <Field label="Tanggal & waktu ambil"><input className="erp-input" type="datetime-local" value={pickupAt} onChange={(event)=>setPickupAt(event.target.value)}/></Field>
          <div className="pickup-pattern-note" data-pattern-snapshot={selectedQueueItem.pattern?.id??'legacy-null'}><Icon name="audit"/><div><span>POLA DARI POTONGAN</span><strong>{selectedQueueItem.pattern ? `${selectedQueueItem.pattern.code} · ${selectedQueueItem.pattern.revision}` : 'Belum tercatat'}</strong><small>{selectedQueueItem.pattern?.name??'Histori lama tetap bisa dibaca.'} · tidak dapat diganti saat pickup.</small></div></div>
          <div className="pickup-flow-note"><Icon name="link"/><div><span>BATCH YANG SAMA</span><strong>Jahit → Laundry</strong><small>Vendor laundry dipilih saat barang benar-benar dikirim.</small></div></div>
        </div>

        <section className="batch-builder-setup">
          <div className="batch-builder-copy"><span>03 · BENTUK BATCH SETELAH PICKUP</span><h2>Mau dibuat menjadi berapa batch?</h2><p>{allocationMode==='roll'?'Satu batch juga boleh. Setelah diterapkan, tarik roll yang belum ditempatkan ke batch tujuan.':'Jumlah batch bebas. Sistem hanya menyusun awal berdasarkan size; setelah itu angkanya tetap bisa lu atur sendiri.'}</p></div>
          <div className="batch-count-control"><label><span>JUMLAH BATCH · MINIMAL 1</span><div><input type="text" pattern="[0-9]*" inputMode="numeric" value={batchCountInput} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setBatchCountInput(event.target.value.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,''))}/><b>batch</b></div></label><div className="batch-count-buttons"><button type="button" aria-label="Hapus batch terakhir" disabled={batchCount<=1} onClick={()=>resizeBatchCount(batchCount-1)}>−</button><button type="button" aria-label="Tambah satu batch" onClick={()=>resizeBatchCount(batchCount+1)}>+</button><button type="button" className="soft-btn" onClick={applyBatchCount}>Terapkan</button></div>{batchResizeMessage&&<small className={batchResizeMessage.startsWith('Tidak bisa')?'warn':'success'}>{batchResizeMessage}</small>}</div>
        </section>

        <div className="wip-allocation-mode" role="group" aria-label="Dasar pembagian batch">
          <button type="button" className={allocationMode==='roll'?'active':''} aria-pressed={allocationMode==='roll'} onClick={()=>selectAllocationMode('roll')}><Icon name="boxes"/><div><span>UTAMA</span><strong>Drag per roll</strong><small>Bagi per roll; kalau bisa jangan dipisah.</small></div></button>
          <button type="button" className={allocationMode==='size'?'active':''} aria-pressed={allocationMode==='size'} onClick={()=>selectAllocationMode('size')}><Icon name="ruler"/><div><span>AWAL PER SIZE</span><strong>Kelompokkan dari size</strong><small>Jumlah batch dan isi akhirnya tetap bebas.</small></div></button>
        </div>

        <div className="wip-reconcile-strip">
          <div><span>SUMBER POTONGAN · TERKUNCI</span><strong>{wipTotal} pcs</strong><small>{cuttingSizes.map((size,index)=>`${size}: ${wipSizeTotals[index]}`).join(' · ')}</small></div>
          <div className={assignedTotal===wipTotal?'success':'warn'}><span>SUDAH DIBAGI</span><strong>{assignedTotal} pcs</strong><small>{effectiveBatchCount} batch · angka absolut</small></div>
          <div className={remainingTotal===0&&sourcesExact?'success':'warn'}><span>SISA / SELISIH</span><strong>{remainingTotal===0&&sourcesExact?'0 pcs · Pas':remainingTotal>0?`${remainingTotal} pcs tersisa`:`${Math.abs(remainingTotal)} pcs berlebih`}</strong><small>{sourcesExact?'Semua sumber cocok':'Ada roll atau size yang tidak cocok'}</small></div>
        </div>

        {allocationMode==='roll'?<div className="golden-roll-rule"><Icon name="boxes"/><div><span>GOLDEN RULE</span><strong>Bagi per roll kalau bisa jangan dipisah</strong><small>{wholeRolls.length} roll utuh · {splitRolls.length} roll terpecah · {unassignedRollRows.length} belum ditempatkan.</small></div><div><button type="button" onClick={tidyWholeRolls}>Susun otomatis tanpa pecah</button></div></div>:<div className="golden-roll-rule size-mode"><Icon name="ruler"/><div><span>PEMBAGIAN AWAL PER SIZE</span><strong>Size utuh dikelompokkan dulu, lalu bebas lu pecah atau gabung</strong><small>Contoh 2 batch: Size 31 sendiri, Size 32+33 bersama. Total setiap size tetap harus sama dengan sumber.</small></div></div>}

        {allocationMode==='roll'&&<section className={`wip-roll-tray ${unassignedRollRows.length===0?'all-assigned':''}`}><div className="wip-roll-tray-head"><div><span>ROLL BELUM DITEMPATKAN</span><strong>{unassignedRollRows.length===0?'Semua roll sudah masuk batch':'Tarik roll atau pilih nomor batch'}</strong><small>{unassignedRollRows.length===0?'Kalau mau pindah, tarik dari kartu batch atau pakai pilihan Batch.':'Pilihan Batch lebih mudah dipakai di HP dan tetap memasukkan roll secara utuh.'}</small></div><span>{unassignedRollRows.length} roll tersisa</span></div><p className="sr-only" role="status" aria-live="polite">{allocationMessage}</p>{unassignedRollRows.length>0?<div className="wip-roll-token-grid">{unassignedRollRows.map((row)=><UnassignedRollCard key={row.roll.id} row={row} batchCount={batchCount} onAssignWhole={assignWholeRoll} onOpenSplit={(rollId)=>{setSplitEditorRollId(rollId);setAllocationMessage('')}} onDragStart={beginRollDrag} onDragMove={moveRollDrag} onDragEnd={finishRollDrag} onDragCancel={cancelRollDrag}/>)}</div>:<div className="wip-roll-tray-empty"><Icon name="check"/><span>Area sumber bersih</span></div>}</section>}

        {allocationMode==='size'&&<div className="split-source-locks size-allocation-source-locks">{cuttingSizes.map((size,sizeIndex)=>{const check=sourceChecks[sizeIndex];const remaining=(check?.total??0)-(check?.assigned??0);return <div className={remaining===0?'success':'warn'} key={size}><span>SIZE {size} · SUMBER</span><strong>{check?.total??wipSizeTotals[sizeIndex]} pcs</strong><small>Terbagi {check?.assigned??0} · Sisa {remaining}</small></div>})}</div>}

        {allocationMode==='roll'&&splitEditorRow&&<section className={`roll-split-editor ${splitEditorExact?'exact':'warn'}`} role="dialog" aria-label={`Atur pecahan Roll ${splitEditorRow.roll.sequence}`}><div className="roll-split-editor-head"><div><span>PENGECUALIAN · ROLL {String(splitEditorRow.roll.sequence).padStart(2,'0')}</span><h3>Pecah {splitEditorRow.roll.id} per size</h3><p>Isi jumlah absolut untuk setiap batch. Angka sumber Potongan di bawah ini tidak bisa diubah.</p></div><button type="button" aria-label="Tutup editor pecahan" onClick={()=>{setSplitEditorRollId(null);setAllocationMessage('')}}><Icon name="close"/></button></div><div className="split-source-locks">{cuttingSizes.map((size,sizeIndex)=>{const check=splitEditorChecks[sizeIndex];return <div className={check?.remaining===0?'success':'warn'} key={size}><span>SIZE {size} · SUMBER</span><strong>{check?.source??0} pcs</strong><small>Terbagi {check?.assigned??0} · Sisa {check?.remaining??0}</small></div>})}</div><div className="split-batch-grid" data-keyboard-grid>{Array.from({length:batchCount},(_,batchIndex)=>{const batchValues=rollBatchMatrix[splitEditorRow.roll.id]?.[batchIndex]??['0','0','0'];return <article key={batchIndex}><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span>{cuttingSizes.map((size,sizeIndex)=><label key={size}><small>Size {size}</small><div><input type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={batchIndex} aria-label={`Roll ${splitEditorRow.roll.sequence}, batch ${batchIndex+1}, size ${size}`} value={batchValues[sizeIndex]??'0'} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateSplitAllocation(splitEditorRow.roll.id,batchIndex,sizeIndex,event.target.value)}/><b>pcs</b></div></label>)}<strong>{batchValues.reduce((sum,value)=>sum+cellQuantity(value),0)} pcs</strong></article>})}</div><div className="roll-split-editor-foot"><span className={allocationMessage?'error':splitEditorExact?'success':'warn'}>{allocationMessage|| (splitEditorExact?'Pas dengan sumber Potongan.':'Belum pas—cek Sumber, Terbagi, dan Sisa per size.')}</span><button type="button" className="soft-btn" onClick={()=>setSplitEditorRollId(null)}>Selesai</button></div></section>}

        <div className="wip-batch-grid" data-keyboard-grid>
          {Array.from({length:effectiveBatchCount},(_,batchIndex)=>{const assignedRows=allocationMode==='roll'?wipRollRows.filter((row)=>(rollBatchMatrix[row.roll.id]?.[batchIndex]??[]).reduce((sum,value)=>sum+cellQuantity(value),0)>0):[];return <article data-wip-drop-batch={allocationMode==='roll'?batchIndex:undefined} className={`wip-batch-card ${rollDrag?.target===batchIndex?'drop-target':''} ${allocationMode==='size'?'size-batch-card':''}`} key={batchIndex}>
            <div className="wip-batch-card-head"><div><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span><strong>{batchTotals[batchIndex]} pcs</strong></div><label className="batch-mandor-note"><span>CATATAN JAHITAN / WARNA</span><input type="text" value={batchNotes[batchIndex]??''} placeholder="Contoh: navy · obras rapat..." aria-label={`Catatan jahitan atau warna Batch ${batchIndex+1}`} onChange={(event)=>setBatchNotes((current)=>Array.from({length:effectiveBatchCount},(_,noteIndex)=>noteIndex===batchIndex?event.target.value:current[noteIndex]??''))}/></label><small>Saran {targetTotals[batchIndex]}</small></div>
            <div className="wip-batch-size-mix">{cuttingSizes.map((size,sizeIndex)=><span className={batchSizeMix[batchIndex][sizeIndex]>0?'active':''} key={size}><small>SIZE {size}</small><strong>{batchSizeMix[batchIndex][sizeIndex]}</strong></span>)}</div>
            <div className="wip-batch-source-list">
            {allocationMode==='roll'?(assignedRows.length>0?assignedRows.map((row)=>{const sizes=rollBatchMatrix[row.roll.id]?.[batchIndex]??['0','0','0'];const allocated=sizes.reduce((sum,value)=>sum+cellQuantity(value),0);const usedIn=(rollBatchMatrix[row.roll.id]??[]).filter((batchSizes)=>batchSizes.reduce((sum,value)=>sum+cellQuantity(value),0)>0).length;const sourceExact=row.sizes.every((source,sizeIndex)=>(rollBatchMatrix[row.roll.id]??[]).reduce((sum,batchSizes)=>sum+cellQuantity(batchSizes[sizeIndex]),0)===source);const draggable=usedIn===1&&sourceExact;return <div className="wip-batch-source locked-source movable-source" key={row.roll.id}><button type="button" disabled={!draggable} className="batch-roll-drag-handle" aria-label={`Pindahkan Roll ${row.roll.sequence} ke batch lain`} title={draggable?'Tarik ke batch lain':'Roll pecah dipindahkan lewat Atur'} onPointerDown={(event)=>draggable&&beginRollDrag(event,row.roll.id)} onPointerMove={moveRollDrag} onPointerUp={finishRollDrag} onPointerCancel={cancelRollDrag}><Icon name="drag"/></button><div className="batch-roll-body"><header><div><span>ROLL {String(row.roll.sequence).padStart(2,'0')}</span><strong>{row.roll.id}</strong></div><b>{allocated} pcs</b></header><div className="batch-roll-size-pills">{cuttingSizes.map((size,sizeIndex)=><span className={cellQuantity(sizes[sizeIndex])>0?'active':''} key={size}><small>{size}</small><strong>{cellQuantity(sizes[sizeIndex])}</strong></span>)}</div><small className="batch-roll-lineage">Sumber {row.quantity} pcs · {usedIn>1?`tersebar di ${usedIn} Batch Distribusi`:'masuk utuh ke Batch Distribusi ini'}</small></div><em className={usedIn>1?'pecah':'utuh'}>{usedIn>1?'Pecah':'Utuh'}</em><div className="batch-source-actions"><RollBatchQuickMenu rollId={row.roll.id} batchCount={batchCount} currentBatch={usedIn===1?batchIndex:null} split={usedIn>1} onAssign={(targetBatch)=>assignWholeRoll(row.roll.id,targetBatch)}/><button type="button" onClick={()=>{setSplitEditorRollId(row.roll.id);setAllocationMessage('')}}>Atur pembagian</button><button type="button" onClick={()=>unassignRoll(row.roll.id)}>Keluarkan roll</button></div></div>}):<div className="wip-batch-empty"><Icon name="drag"/><strong>Tarik roll ke sini</strong><small>Roll masuk utuh secara default</small></div>):cuttingSizes.map((size,sizeIndex)=>{const allocated=sizeMatrix[size]?.[batchIndex]??'0';const check=sourceChecks[sizeIndex];return <label className={`wip-batch-source editable-size-source ${cellQuantity(allocated)===0?'empty':''}`} key={size}><div><strong>Size {size}</strong><small>Sumber {check?.total??wipSizeTotals[sizeIndex]} · terbagi {check?.assigned??0}</small></div><div className="wip-free-input"><input type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={batchIndex} aria-label={`Batch ${batchIndex+1}, Size ${size}`} value={allocated} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateSizeAllocation(size,batchIndex,event.target.value)}/><span>pcs</span></div></label>})}
            </div>
            <div className="wip-batch-route"><span>JAHIT</span><Icon name="arrow"/><span>LAUNDRY</span><small>Kode batch tetap sama</small></div>
          </article>})}
        </div>

        {rollDrag&&<div className="roll-drag-ghost" style={{left:rollDrag.x,top:rollDrag.y}}><Icon name="drag"/><span>{rollDrag.rollId}</span><small>{rollDrag.target===null?'Arahkan ke batch':`Lepas di Batch ${String(rollDrag.target+1).padStart(2,'0')}`}</small></div>}
        <div className="wip-source-audit"><Icon name={sourcesExact?'check':'history'}/><div><strong>{sourcesExact?'Pembagian cocok dengan seluruh sumber':'Masih ada sumber roll atau size yang tidak cocok'}</strong><span>{sourceChecks.filter((source)=>source.assigned!==source.total).map((source)=>`${source.key}: ${source.assigned}/${source.total}`).join(' · ')||`${wipRollRows.length} roll · Size 31/32/33 seluruhnya rekonsiliasi`}</span></div></div>
        <section className={`pickup-final-review ${isReady?'ready':'blocked'}`} aria-label="Review akhir pickup"><div className="pickup-review-head"><Icon name={isReady?'check':'history'}/><div><span>04 · REVIEW SEBELUM POSTING</span><strong>{isReady?'Siap dicatat sebagai pickup mandor':'Belum siap diposting'}</strong><small>{isReady?'Sesudah konfirmasi, PO masuk tahap SEWING.':'Rapikan pembagian sampai sumber, size, dan total seluruh batch pas.'}</small></div></div><div className="pickup-review-facts"><div><span>MANDOR</span><strong>{mandor||'Belum dipilih'}</strong></div><div><span>WAKTU AMBIL</span><strong>{pickupReviewAt}</strong></div><div><span>POLA SNAPSHOT</span><strong>{selectedQueueItem.pattern ? `${selectedQueueItem.pattern.code} · ${selectedQueueItem.pattern.revision}` : 'Histori lama'}</strong></div><div><span>PEMBAGIAN</span><strong>{allocationMode==='roll'?'Per roll':'Awal per size'}</strong></div><div><span>TOTAL</span><strong>{effectiveBatchCount} batch · {assignedTotal} pcs</strong></div></div><div className="pickup-review-batches">{batchTotals.map((total,batchIndex)=><div className={total>0?'filled':'empty'} key={batchIndex}><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span><strong>{total} pcs</strong><small>{batchNotes[batchIndex]||'Belum ada catatan mandor'}</small><em>{cuttingSizes.map((size,sizeIndex)=>`${size}: ${batchSizeMix[batchIndex][sizeIndex]}`).join(' · ')}</em></div>)}</div><div className="pickup-review-next"><Icon name="arrow"/><span><strong>Setelah posting: SEWING</strong> · Pola snapshot ikut Batch Produksi; Laundry baru boleh dicatat ketika batch benar-benar dikirim keluar.</span></div></section>
        <div className="allocation-footer"><small>{isReady?'Ringkasan final di atas sudah cocok. Backend belum disentuh selama prototype.':'Tombol posting terbuka setelah seluruh sumber dan total batch cocok.'}</small><div><button type="button" className="soft-btn">Simpan draft pickup</button><button type="button" className="primary-btn" disabled={!isReady}>Review & catat pickup <Icon name="arrow"/></button></div></div>
      </div>
    </section>
    {queueDetailItem?<div className="wip-detail-backdrop" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)setQueueDetailId(null)}}><section className="wip-detail-modal" role="dialog" aria-modal="true" aria-labelledby="wip-detail-title">
      <header><div><span>DETAIL POTONGAN · {queueDetailItem.status==='PICKED'?'SUDAH DIAMBIL':'MENUNGGU DIAMBIL'}</span><h2 id="wip-detail-title">{queueDetailItem.id} · {queueDetailItem.model}</h2><p>{queueDetailItem.material} · {queueDetailItem.supplier} · Pola {patternSnapshotLabel(queueDetailItem.pattern)}</p></div><button type="button" aria-label="Tutup detail potongan" onClick={()=>setQueueDetailId(null)}><Icon name="close"/></button></header>
      <div className="wip-detail-facts">
        <article><span>TOTAL POTONGAN</span><strong>{pickupItemTotal(queueDetailItem)} pcs</strong><small>{queueDetailItem.rolls.length} roll sumber</small></article>
        <article><span>YARD DIPAKAI</span><strong>{formatQuantity(pickupItemUsedYards(queueDetailItem),2)} yd</strong><small>dari {formatQuantity(queueDetailSourceYards,2)} yd · sisa {formatQuantity(queueDetailRemainingYards,2)} yd</small></article>
        <article><span>STATUS PICKUP</span><strong>{queueDetailItem.status==='PICKED'?queueDetailItem.mandor:'Belum diambil'}</strong><small>{queueDetailItem.pickupAt??'Belum punya waktu pickup'}</small></article>
        <article><span>BATCH DISTRIBUSI</span><strong>{new Set(queueDetailItem.rolls.flatMap((roll)=>roll.batchNumbers)).size||'—'}</strong><small>{queueDetailItem.status==='PICKED'?'Snapshot pembagian':'Terbentuk setelah dialokasikan'}</small></article>
        <article data-pattern-snapshot={queueDetailItem.pattern?.id??'legacy-null'}><span>POLA · SNAPSHOT</span><strong>{queueDetailItem.pattern ? `${queueDetailItem.pattern.code} · ${queueDetailItem.pattern.revision}` : 'Belum tercatat'}</strong><small>{queueDetailItem.pattern?.name??'Histori lama tetap terbaca'} · identitas tidak berubah saat master diedit</small></article>
      </div>
      <div className="wip-detail-section-head"><div><span>LINEAGE HASIL POTONG</span><strong>Bahan, yard, dan ukuran per gambar</strong><small>Kolom ukuran sama seperti saat hasil dicatat di Buat Potongan.</small></div><em>Geser tabel →</em></div>
      <div className="wip-detail-table">
        <table aria-label={`Detail roll dan hasil potong ${queueDetailItem.id}`}>
          <thead><tr><th>Bahan & kode roll</th><th>Yard asal</th><th>Dipakai</th><th>Sisa</th>{queueDetailSlots.map((slot)=><th key={`${slot.size}-${slot.image}`}>Size {slot.size}<small>{slot.image}</small></th>)}<th>Total</th><th>Masuk batch</th></tr></thead>
          <tbody>{queueDetailItem.rolls.map((roll)=><tr key={roll.id}>
            <th scope="row"><strong>{roll.material}</strong><small>{roll.id} · kode roll sumber</small></th>
            <td>{formatQuantity(roll.sourceYards,2)} <small>yd</small></td><td>{formatQuantity(roll.usedYards,2)} <small>yd</small></td><td>{formatQuantity(roll.remainingYards,2)} <small>yd</small></td>
            {queueDetailSlots.map((slot,slotIndex)=><td key={`${slot.size}-${slot.image}`}>{roll.slots[slotIndex]?.qty??0} <small>pcs</small></td>)}
            <td className="wip-detail-total">{pickupRollTotal(roll)} <small>pcs</small></td>
            <td><em className={roll.batchNumbers.length?'assigned':'waiting'}>{roll.batchNumbers.length?roll.batchNumbers.map((batch)=>`Batch ${batch}`).join(' + '):'Belum dibagi'}</em></td>
          </tr>)}</tbody>
        </table>
      </div>
      <footer><span><Icon name="audit"/> Detail ini menampilkan lineage Pola, roll, dan ukuran tanpa mengubah pembagian.</span><button type="button" className="primary-btn" onClick={()=>setQueueDetailId(null)}>Tutup detail</button></footer>
    </section></div>:null}
  </>
}
