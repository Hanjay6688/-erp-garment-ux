import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, CheckCircle2, FileText, ShieldCheck, UserRound, Wrench } from 'lucide-react'
import type { QcFinalResult } from './QcFinalPage'
import type { ReadyFgNotaCard, RegularFgNotaSnapshot } from './fgNota'

type NotaFocus = { kind: 'REGULAR' | 'REPAIR'; id: string }
type NotaOrigin = 'MENU' | 'QC' | 'BS_REWORK'

type RegularNotaCard = {
  id: string
  result: QcFinalResult
  source: string
  sku: string
  returned: number
  good: number
  bs: number
  rewash: number
  hold: number
  sewingRate: number
  commissionRate: number
  bomRate: number
  bsComponents: Array<{ id: string; name: string; rate: number }>
  gross: number
  deduction: number
  subtotal: number
}

const laborComponents = [
  { id: 'jahit-utama', name: 'Jahit utama', rate: 8_250 },
  { id: 'finishing-detail', name: 'Ceming / finishing detail', rate: 2_500 },
  { id: 'pinggang', name: 'Ban & pinggang', rate: 2_600 },
  { id: 'saku', name: 'Saku & ritsleting', rate: 2_300 },
  { id: 'centang', name: 'Centang / bartack', rate: 800 },
  { id: 'kancing', name: 'Kancing', rate: 500 },
  { id: 'plastik', name: 'Plastik & packing', rate: 500 },
  { id: 'hangtag', name: 'Hangtag / label', rate: 600 },
  { id: 'lipat', name: 'Lipat akhir', rate: 400 },
]

const money = (value: number) => `Rp${Math.round(value).toLocaleString('id-ID')}`
const total = (values: number[]) => values.reduce((sum, value) => sum + value, 0)
const regularCardId = (result: QcFinalResult) => `qc-${result.parentId}-${result.batchId}-${result.completionCount}`

const toRegularCard = (result: QcFinalResult, savedSnapshot?: RegularFgNotaSnapshot): RegularNotaCard => {
  const good = total(result.postedGoodBySize)
  const bs = total(result.postedBsBySize)
  const rewash = total(result.postedRewashBySize)
  const hold = total(result.remainingBySize)
  const returned = good + bs + rewash
  const defaultFullRate = total(laborComponents.map((component) => component.rate))
  const defaultBsComponents = bs > 0
    ? laborComponents.filter((component) => ['finishing-detail', 'centang', 'lipat'].includes(component.id))
    : []
  const fullRate = savedSnapshot?.fullRate ?? defaultFullRate
  const bsComponents = savedSnapshot?.bsComponents ?? defaultBsComponents
  const deduction = bs * total(bsComponents.map((component) => component.rate))
  return {
    id: regularCardId(result),
    result,
    source: `${result.parentId} · Batch ${result.batchId} · Completion ${String(result.completionCount).padStart(2, '0')}`,
    sku: `${result.brand} · ${result.finalSku}`,
    returned,
    good,
    bs,
    rewash,
    hold,
    sewingRate: savedSnapshot?.sewingRate ?? 14_050,
    commissionRate: savedSnapshot?.commissionRate ?? 1_800,
    bomRate: savedSnapshot?.bomRate ?? Math.max(0, fullRate - 15_850),
    bsComponents,
    gross: returned * fullRate,
    deduction,
    subtotal: returned * fullRate - deduction,
  }
}

export default function FgNotaPage({
  result,
  eligibleResults,
  repairCards,
  regularSnapshots,
  focus,
  origin,
  postedCardIds,
  onPost,
  onReturn,
  onOpenQc,
  onOpenBs,
}: {
  result: QcFinalResult | null
  eligibleResults: QcFinalResult[]
  repairCards: ReadyFgNotaCard[]
  regularSnapshots: Record<string, RegularFgNotaSnapshot>
  focus: NotaFocus | null
  origin: NotaOrigin
  postedCardIds: string[]
  onPost: (ids: string[]) => void
  onReturn: () => void
  onOpenQc: () => void
  onOpenBs: () => void
}) {
  const allResults = useMemo(() => {
    const unique = new Map<string, QcFinalResult>()
    if (result) unique.set(regularCardId(result), result)
    eligibleResults.forEach((item) => unique.set(regularCardId(item), item))
    return Array.from(unique.values())
  }, [result, eligibleResults])
  const focusedResult = focus?.kind === 'REGULAR' ? allResults.find((item) => regularCardId(item) === focus.id) : undefined
  const focusedRepair = focus?.kind === 'REPAIR' ? repairCards.find((item) => item.id === focus.id) : undefined
  const initialMandor = focusedResult?.mandor ?? focusedRepair?.mandor ?? allResults[0]?.mandor ?? repairCards[0]?.mandor ?? ''
  const [selectedMandor, setSelectedMandor] = useState(initialMandor)
  const [regularIds, setRegularIds] = useState<string[]>([])
  const [repairIds, setRepairIds] = useState<string[]>([])
  const [noteReviewed, setNoteReviewed] = useState(false)
  const [note, setNote] = useState('Nilai FG reguler memakai Total Pulang × harga lengkap, lalu dikurangi BS × komponen Bikin Bagus. Hold yang kemudian menjadi BS hanya direklasifikasi tanpa pengurang kedua.')
  const [noteStatus, setNoteStatus] = useState<'DRAFT' | 'POSTED'>('DRAFT')
  const [postedNote, setPostedNote] = useState<{
    mandor: string
    regularCards: RegularNotaCard[]
    repairCards: ReadyFgNotaCard[]
    regularSubtotal: number
    repairSubtotal: number
    total: number
  } | null>(null)

  const postedIds = useMemo(() => new Set(postedCardIds), [postedCardIds])
  const mandors = Array.from(new Set([...allResults.map((item) => item.mandor), ...repairCards.map((item) => item.mandor)])).filter(Boolean)
  const activeResult = focusedResult?.mandor === selectedMandor
    ? focusedResult
    : allResults.find((item) => item.mandor === selectedMandor)
  const regularCards = allResults.filter((item) => item.mandor === selectedMandor).map((item) => toRegularCard(item, regularSnapshots[regularCardId(item)]))
  const visibleRepairCards = repairCards.filter((item) => item.mandor === selectedMandor)
  const selectedRegular = regularCards.filter((card) => regularIds.includes(card.id) && !postedIds.has(card.id))
  const selectedRepair = visibleRepairCards.filter((card) => repairIds.includes(card.id) && !postedIds.has(card.id))
  const regularSubtotal = total(selectedRegular.map((card) => card.subtotal))
  const repairSubtotal = total(selectedRepair.map((card) => card.subtotal))
  const noteTotal = regularSubtotal + repairSubtotal
  const displayRegular = postedNote?.regularCards ?? selectedRegular
  const displayRepair = postedNote?.repairCards ?? selectedRepair
  const displayRegularSubtotal = postedNote?.regularSubtotal ?? regularSubtotal
  const displayRepairSubtotal = postedNote?.repairSubtotal ?? repairSubtotal
  const displayTotal = postedNote?.total ?? noteTotal
  const displayMandor = postedNote?.mandor ?? selectedMandor
  const selectedIds = [...selectedRegular.map((card) => card.id), ...selectedRepair.map((card) => card.id)]
  const editable = noteStatus === 'DRAFT'
  const goodTotal = activeResult ? total(activeResult.postedGoodBySize) : 0
  const bsTotal = activeResult ? total(activeResult.postedBsBySize) : 0
  const rewashTotal = activeResult ? total(activeResult.postedRewashBySize) : 0
  const outstanding = activeResult ? total(activeResult.remainingBySize) : 0
  const returnedTotal = goodTotal + bsTotal + rewashTotal
  const expectedTotal = activeResult ? total(activeResult.expected) : 0
  const focusedId = focus?.id

  const changeMandor = (mandor: string) => {
    setSelectedMandor(mandor)
    setRegularIds([])
    setRepairIds([])
    setNoteReviewed(false)
  }
  const toggleRegular = (id: string) => {
    if (!editable || postedIds.has(id)) return
    setRegularIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
    setNoteReviewed(false)
  }
  const toggleRepair = (id: string) => {
    if (!editable || postedIds.has(id)) return
    setRepairIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
    setNoteReviewed(false)
  }
  const postNota = () => {
    if (!editable || selectedIds.length === 0 || noteTotal <= 0 || !noteReviewed) return
    setPostedNote({ mandor: selectedMandor, regularCards: selectedRegular, repairCards: selectedRepair, regularSubtotal, repairSubtotal, total: noteTotal })
    onPost(selectedIds)
    setNoteStatus('POSTED')
  }
  const startNextNota = () => {
    setRegularIds([])
    setRepairIds([])
    setNoteReviewed(false)
    setPostedNote(null)
    setNoteStatus('DRAFT')
  }

  const returnLabel = origin === 'QC' ? 'Kembali ke QC' : 'Kembali ke Bikin Bagus'
  const queueCount = regularCards.length + visibleRepairCards.length
  const availableCount = [...regularCards, ...visibleRepairCards].filter((card) => !postedIds.has(card.id)).length

  return <>
    <section className="hero-copy compact fg-handoff-hero">
      <div><div className="eyebrow">PRODUKSI · HALAMAN ANTREAN NOTA FG</div><h1>Susun Nota FG</h1><p>Buka langsung tanpa lewat QC. Card FG Reguler, Bikin Bagus, dan Susulan Good tetap membawa sumbernya lalu dikelompokkan per Mandor.</p></div>
      <div className="handoff-page-actions">{origin !== 'MENU' && <button type="button" className="soft-btn handoff-back" onClick={onReturn}><ArrowLeft/> {returnLabel}</button>}<button type="button" className="soft-btn" onClick={onOpenQc}>Buka QC</button><button type="button" className="soft-btn" onClick={onOpenBs}>Buka Bikin Bagus</button></div>
    </section>
    <div className="handoff-flow-strip"><span className="done"><b>1</b>QC / rework terkunci</span><i/><span className="done"><b>2</b>Card siap</span><i/><span className="active"><b>3</b>Susun Nota FG</span><i/><span><b>4</b>Payroll</span></div>
    <div className={`handoff-queue-banner ${queueCount === 0 ? 'empty' : ''}`}><FileText/><div><strong>{focusedId ? `${focusedId} dibuka dari sumbernya` : 'Antrean Nota FG mandiri'}</strong><span>Card yang sudah masuk Nota tetap terkunci. Ganti Mandor akan mengosongkan draft supaya nota tidak mencampur penerima.</span></div>{mandors.length > 0 ? <label className="nota-mandor-filter"><span>MANDOR NOTA</span><select value={selectedMandor} disabled={!editable} onChange={(event) => changeMandor(event.target.value)}>{mandors.map((mandor) => <option key={mandor}>{mandor}</option>)}</select><small>{availableCount} siap · {queueCount - availableCount} posted</small></label> : <em>Belum ada card</em>}</div>
    {noteStatus === 'POSTED' && <div className="handoff-success"><CheckCircle2/><div><strong>Nota FG sudah posted dan card terkunci</strong><span>NFG-260828-NEW · {money(displayTotal)} · masuk antrean Payroll, belum mengubah kas.</span></div><button type="button" className="soft-btn" onClick={startNextNota}>Susun nota berikutnya <ArrowRight/></button></div>}
    <section className="handoff-layout">
      <div className="panel handoff-workbench">
        {activeResult ? <>
          <header className="handoff-source-head"><span>01</span><div><small>QC {activeResult.completionStatus === 'PARTIAL_SELECTION' ? 'SELESAI SEBAGIAN' : activeResult.completionStatus === 'WAITING_LAUNDRY' ? 'MENUNGGU LAUNDRY' : activeResult.completionStatus === 'WAITING_REWORK' ? 'MENUNGGU CUCI ULANG' : 'LENGKAP'} · {activeResult.parentId} · BATCH {activeResult.batchId}</small><h2>{activeResult.brand} · SKU {activeResult.finalSku}</h2><p>{activeResult.finalProductName} · {activeResult.finalColor} · Range {activeResult.finalRange} · bahan {activeResult.material}</p><div className="handoff-mandor-hero"><UserRound/><span><small>MANDOR PENERIMA NOTA</small><strong>{activeResult.mandor}</strong></span></div></div><strong>{returnedTotal} pulang · {goodTotal} Good</strong></header>
          <div className="handoff-section-title"><div><span>02</span><div><strong>Rekonsiliasi fisik dari QC</strong><small>Good menentukan FG. Stuck belum ikut sampai fisik kembali; Hold → BS hanya reklasifikasi dan tidak memotong kedua kali.</small></div></div><em className="ok">QC read-only</em></div>
          <div className="handoff-size-breakdown" role="table" aria-label="Rekonsiliasi serah FG per size"><div className="handoff-size-breakdown-head" role="row"><span>SIZE</span><span>POTONGAN</span><span>BAGUS → FG</span><span>BS</span><span>CUCI ULANG</span><span>SISA OPEN</span></div>{activeResult.sizes.map((size, index) => <div className={`handoff-size-breakdown-row ${activeResult.remainingBySize[index] > 0 ? 'has-outstanding' : ''}`} role="row" key={size}><strong data-label="SIZE">{size}</strong><span data-label="POTONGAN">{activeResult.expected[index]} pcs</span><strong className="good" data-label="BAGUS → FG">{activeResult.postedGoodBySize[index]} pcs</strong><span className="bs" data-label="BS">{activeResult.postedBsBySize[index]} pcs</span><span className="rewash" data-label="CUCI ULANG">{activeResult.postedRewashBySize[index]} pcs</span><span className="stuck" data-label="SISA OPEN">{activeResult.remainingBySize[index]} pcs</span></div>)}<div className="handoff-size-breakdown-total" role="row"><strong>TOTAL</strong><span>{expectedTotal} pcs</span><strong>{goodTotal} pcs</strong><span>{bsTotal} pcs</span><span>{rewashTotal} pcs</span><span>{outstanding} pcs</span></div></div>
          <div className="handoff-equation"><span><small>GOOD → FG</small><strong>{goodTotal} pcs</strong></span><b>+</b><span><small>BS</small><strong>{bsTotal} pcs</strong></span><b>+</b><span><small>CUCI ULANG</small><strong>{rewashTotal} pcs</strong></span><b>=</b><span className="total"><small>TOTAL PULANG</small><strong>{returnedTotal} pcs</strong></span><b>+</b><span className="outside"><small>SISA OPEN</small><strong>{outstanding} pcs</strong></span></div>
        </> : <section className="nota-source-empty"><FileText/><div><span>01 · ANTREAN MANDIRI</span><h2>{selectedMandor ? `Belum ada card QC ${selectedMandor}` : 'Belum ada card siap Nota FG'}</h2><p>{selectedMandor ? 'Bikin Bagus atau Susulan Good tetap bisa disusun sendiri. Card QC baru muncul otomatis setelah posting finishing.' : 'Posting hasil QC atau buka card siap dari halaman Barang BS & Rework.'}</p></div></section>}

        <section className="nota-work-group regular"><header><div><span>03 · ANTREAN FG REGULER</span><h2>Card finishing belum masuk Nota FG</h2><p>Hanya card milik Mandor terpilih. Penyelesaian sebagian menjadi card terpisah dan tidak menghapus sisa yang masih open.</p></div><em>{displayRegular.length} {noteStatus==='POSTED'?'di nota posted':'di draft'} · {regularCards.length} tampil</em></header><div>{regularCards.map((card) => {
          const added = regularIds.includes(card.id)
          const posted = postedIds.has(card.id)
          const focused = card.id === focusedId
          const rate = card.sewingRate + card.commissionRate + card.bomRate
          const status = posted ? 'SUDAH MASUK NOTA' : added ? 'SEDANG DI DRAFT' : focused ? 'DIBUKA DARI QC' : 'SIAP DISUSUN'
          return <article className={`nota-work-card regular ${added ? 'added' : ''} ${focused ? 'focused' : ''} ${posted ? 'posted' : ''}`} key={card.id}><header><div><small>{card.source}</small><strong>{card.sku}</strong></div><span>{status}</span></header><div className="nota-work-facts"><span><small>TOTAL PULANG</small><strong>{card.returned} pcs</strong></span><span className="good"><small>GOOD → FG</small><strong>{card.good} pcs</strong></span><span className="bs"><small>BS</small><strong>{card.bs} pcs</strong></span><span className="rewash"><small>CUCI ULANG</small><strong>{card.rewash} pcs</strong></span><span className="hold"><small>STUCK</small><strong>{card.hold} pcs</strong></span></div><div className="nota-bs-components"><span>KOMPONEN BS DARI SNAPSHOT</span><div>{card.bsComponents.length > 0 ? card.bsComponents.map((component) => <em key={component.id}><Check/>{component.name}<b>{money(component.rate)}</b></em>) : <small>Tidak ada pengurang BS</small>}</div></div><div className="nota-value-formula"><span><small>TOTAL PULANG × HARGA</small><strong>{card.returned} × {money(rate)}</strong><em>{money(card.gross)}</em></span><b>−</b><span className="deduction"><small>BS × KOMPONEN SNAPSHOT</small><strong>{card.bs} × {money(total(card.bsComponents.map((component) => component.rate)))}</strong><em>{money(card.deduction)}</em></span><b>=</b><span className="result"><small>NILAI FG REGULER</small><strong>{money(card.subtotal)}</strong><em>Good bukan pengali upah</em></span></div><footer><small>ID {card.id} menjaga setiap completion hanya dibayar sekali.</small><button type="button" disabled={!editable || posted} onClick={() => toggleRegular(card.id)}>{posted ? 'Terkunci di Nota' : added ? 'Keluarkan dari Draft' : 'Tambah ke Nota FG'}</button></footer></article>
        })}{regularCards.length === 0 && <div className="nota-work-empty"><FileText/><strong>Belum ada card FG Reguler</strong><small>Selesaikan QC atau pilih Mandor lain.</small></div>}</div></section>

        <section className="nota-work-group repair"><header><div><span>04 · BIKIN BAGUS & SUSULAN GOOD</span><h2>Card plus yang sudah diterima</h2><p>Nilai mengikuti snapshot sumber: komponen Bikin Bagus atau nilai Hold yang benar-benar dilepas, bukan tarif master hari ini.</p></div><button type="button" className="soft-btn" onClick={onOpenBs}>Buka Browser Kasus <ArrowRight/></button></header><div>{visibleRepairCards.map((card) => {
          const added = repairIds.includes(card.id)
          const posted = postedIds.has(card.id)
          const focused = card.id === focusedId
          const status = posted ? 'SUDAH MASUK NOTA' : added ? 'SEDANG DI DRAFT' : focused ? 'DIBUKA DARI BIKIN BAGUS' : 'SIAP DISUSUN'
          return <article className={`nota-work-card repair ${added ? 'added' : ''} ${focused ? 'focused' : ''} ${posted ? 'posted' : ''}`} key={card.id}><header><div><small>{card.id} · {card.sourceLabel}</small><strong>{card.brand} · {card.sku}</strong></div><span>{status}</span></header><div className="nota-repair-lineage"><ShieldCheck/><span><small>{card.kind === 'STUCK_RELEASE' ? 'SUSULAN GOOD · LEPAS HOLD' : 'BIKIN BAGUS · QC ULANG LULUS'}</small><strong>Kasus {card.caseId} · sumber {card.originId ?? '—'}</strong></span></div><div className="nota-repair-components">{card.components.map((component) => <span key={component.id}><Check/><small>{component.name}</small><strong>{money(component.rate)}</strong></span>)}</div><div className="nota-work-rate repair"><span>Qty diterima <b>{card.qty} pcs</b></span><span>Tarif snapshot <b>{money(card.unitRate)}</b></span><strong>{card.qty} × {money(card.unitRate)} = {money(card.subtotal)}</strong></div><footer><small>{card.createdAt} · penerima {card.mandor}</small><button type="button" disabled={!editable || posted} onClick={() => toggleRepair(card.id)}>{posted ? 'Terkunci di Nota' : added ? 'Keluarkan dari Draft' : 'Tambah ke Nota FG'}</button></footer></article>
        })}{visibleRepairCards.length === 0 && <div className="nota-work-empty repair"><Wrench/><strong>Belum ada card Bikin Bagus / Susulan</strong><small>Buka Browser Kasus untuk melihat pekerjaan yang sudah diterima.</small></div>}</div></section>
        <label className="handoff-note nota-note"><span>CATATAN NOTA FG</span><textarea disabled={!editable} value={note} onChange={(event) => { setNote(event.target.value); setNoteReviewed(false) }}/></label>
      </div>

      <aside className="panel handoff-payroll-ticket"><div className="handoff-ticket-title"><span>NOTA FG · NFG-260828-NEW</span><h2>{displayMandor || 'Pilih Mandor'}</h2><p>{displayRegular.length} FG Reguler · {displayRepair.length} Bikin Bagus / Susulan</p><small>28 Agu 2026 · {noteStatus === 'POSTED' ? 'posted, belum dibayar' : 'draft dapat disusun'}</small></div><div className="nota-ticket-groups"><article className="regular"><span><small>FG REGULER</small><strong>{displayRegular.length} card</strong></span><b>{money(displayRegularSubtotal)}</b></article><article className="repair"><span><small>BIKIN BAGUS / SUSULAN</small><strong>{displayRepair.length} card</strong></span><b>{money(displayRepairSubtotal)}</b></article></div><div className="handoff-net"><span>TOTAL NOTA FG</span><strong>{money(displayTotal)}</strong><small>Masuk Payroll setelah posted. Belum ada pembayaran atau pergerakan kas.</small></div><div className="handoff-output"><span>DOKUMEN INI MEMBAWA</span><p><Check/><b>{total(displayRegular.map((card) => card.returned))} pcs</b> Total Pulang sebagai dasar</p><p><ShieldCheck/><b>{money(total(displayRegular.map((card) => card.deduction)))}</b> pengurang BS tercatat</p><p><Wrench/><b>{total(displayRepair.map((card) => card.qty))} pcs</b> plus eligible</p></div><label className="handoff-final-check"><input type="checkbox" disabled={!editable || selectedIds.length === 0} checked={noteReviewed} onChange={(event) => setNoteReviewed(event.target.checked)}/><span><strong>Susunan Nota FG sudah gue review</strong><small>Semua card milik {displayMandor || 'Mandor yang dipilih'}; ID sumber dan formula terlihat.</small></span></label><button type="button" className="primary-btn handoff-submit" disabled={!editable || selectedIds.length === 0 || noteTotal <= 0 || !noteReviewed} onClick={postNota}>{noteStatus === 'POSTED' ? 'Nota FG sudah posted' : 'Post Nota FG ke Payroll'} <ArrowRight/></button><p className="handoff-audit-note">Card yang tidak dipilih tetap di antrean. Dalam prototipe ini lock bertahan selama sesi aplikasi; backend wajib memakai idempotency dan unique card ID.</p></aside>
    </section>
  </>
}
