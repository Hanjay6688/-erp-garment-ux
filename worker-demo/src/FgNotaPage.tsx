import {trainingBom} from './demo/trainingBom'
import { BrowsePane } from './components/BrowsePane'
import { FgIncompleteWork } from './demo/FgIncompleteWork'
import { laborBomComponents } from './demo/laundryModel'
import {fgQuantity} from './fgQuantity'
import {fgDrafts, claimedFgCards, storeFgDraft, closeFgDraft, type FgDraft} from './demo/fgDraft'
import {ReasonDialog} from './demo/planner/ReasonDialog'
import FgRegister from './demo/FgRegister'
import PostedFgDetail from './demo/PostedFgDetail'
import {payForSource,postedPayrollCards,savePostedFg} from './demo/payrollSources'
import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, CheckCircle2, FileText, ShieldCheck, UserRound, Wrench } from 'lucide-react'
import type { QcFinalResult } from './QcFinalPage'
import { regularFgNotaCardId, selectRegularFgNotaSources, type ReadyFgNotaCard, type RegularFgNotaSnapshot } from './fgNota'
import { calculateRegularWorkEntitlement } from './payroll/regularWorkEntitlement'

type NotaFocus = { kind: 'REGULAR' | 'REPAIR'; id: string }
type NotaOrigin = 'MENU' | 'QC' | 'BS_REWORK' | 'PAYROLL'

type RegularNotaCard = {
  id: string
  result: QcFinalResult
  source: string
  sku: string
  sewnQty: number
  returned: number
  good: number
  bs: number
  rewash: number
  hold: number
  sewingRate: number
  commissionRate: number
  bomRate: number
  bsComponents: Array<{ id: string; name: string; rate: number }>
  stuckComponents: Array<{ id: string; name: string; rate: number }>
  gross: number
  bsDeduction: number
  stuckDeduction: number
  deduction: number
  subtotal: number
}


const money = (value: number) => `Rp${Math.round(value).toLocaleString('id-ID')}`
const total = (values: number[]) => values.reduce((sum, value) => sum + value, 0)
const toRegularCard = (result: QcFinalResult, savedSnapshot?: RegularFgNotaSnapshot): RegularNotaCard => {
  const good = total(result.postedGoodBySize)
  const bs = total(result.postedBsBySize)
  const rewash = total(result.postedRewashBySize)
  const hold = total(result.stuckBySize)
  const returned = good + bs + rewash
  const sewnQty = total(result.expected)
  const defaultFullRate = total(laborBomComponents.map((component) => component.rate))
  const defaultBsComponents = bs > 0
    ? laborBomComponents.filter((component) => ['finishing-detail', 'centang', 'lipat'].includes(component.id))
    : []
  const defaultStuckComponents = hold > 0
    ? laborBomComponents.filter((component) => ['finishing-detail', 'centang', 'lipat'].includes(component.id))
    : []
  const fullRate = savedSnapshot?.fullRate ?? defaultFullRate
  const bsComponents = savedSnapshot?.bsComponents ?? defaultBsComponents
  const stuckComponents = savedSnapshot?.stuckComponents ?? defaultStuckComponents
  const formula = calculateRegularWorkEntitlement({
    sewnQty,
    fullRate,
    bsQty: bs,
    bsComponents,
    stuckQty: hold,
    stuckComponents,
  })
  return {
    id: regularFgNotaCardId(result),
    result,
    source: `${result.parentId} · Batch ${result.batchId} · Completion ${String(result.completionCount).padStart(2, '0')}`,
    sku: `${result.brand} · ${result.finalSku}`,
    sewnQty,
    returned,
    good,
    bs,
    rewash,
    hold,
    sewingRate: savedSnapshot?.sewingRate ?? 14_050,
    commissionRate: savedSnapshot?.commissionRate ?? 1_800,
    bomRate: savedSnapshot?.bomRate ?? Math.max(0, fullRate - 15_850),
    bsComponents,
    stuckComponents,
    gross: formula.gross,
    bsDeduction: formula.bsDeduction,
    stuckDeduction: formula.stuckDeduction,
    deduction: formula.totalDeduction,
    subtotal: formula.subtotal,
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
  onOpenBs: (result?: QcFinalResult) => void
}) {
  const [requestedDraft] = useState(() => new URLSearchParams(location.search).get('draft'))
  const [savedDraft, setSavedDraft] = useState<FgDraft | undefined>(() => fgDrafts().find(d => d.number === requestedDraft))
  const [draftMessage,setDraftMessage] = useState('')
  const [voidOpen,setVoidOpen] = useState(false)
  const [voidReason,setVoidReason] = useState('')
  const [postReason,setPostReason] = useState('Pengesahan susunan nota FG')
  const [fresh,setFresh] = useState(false)
  const [workOverrides, setWorkOverrides] = useState<Record<string, RegularFgNotaSnapshot>>({})
  const [workCard, setWorkCard] = useState<string | null>(null)
  const allResults = useMemo(() => selectRegularFgNotaSources([...(result ? [result] : []), ...eligibleResults, ...(savedDraft?.results ?? [])]), [result, eligibleResults, savedDraft])
  const allRepairs = [...new Map([...(savedDraft?.repairs ?? []), ...repairCards].map(c => [c.id,c])).values()]
  const snapshots = {...regularSnapshots,...savedDraft?.snapshots,...workOverrides}
  const focusedResult = focus?.kind === 'REGULAR' ? allResults.find((item) => regularFgNotaCardId(item) === focus.id) : undefined
  const focusedRepair = focus?.kind === 'REPAIR' ? allRepairs.find((item) => item.id === focus.id) : undefined
  const requestedMandor=origin==='PAYROLL'?sessionStorage.getItem('erp.owner.payroll.mandor'):null
  const initialMandor = savedDraft?.mandor ?? focusedResult?.mandor ?? focusedRepair?.mandor ?? requestedMandor ?? allResults[0]?.mandor ?? repairCards[0]?.mandor ?? ''
  const [selectedMandor, setSelectedMandor] = useState(initialMandor)
  const [regularIds, setRegularIds] = useState<string[]>(savedDraft?.results.map(regularFgNotaCardId) ?? [])
  const [repairIds, setRepairIds] = useState<string[]>(savedDraft?.repairs.map(c=>c.id) ?? [])
  const [noteReviewed, setNoteReviewed] = useState(false)
  const [note, setNote] = useState(savedDraft?.note ?? '')
  const [noteStatus, setNoteStatus] = useState<'DRAFT' | 'POSTED'>('DRAFT')
  const [postedNote, setPostedNote] = useState<{
    mandor: string
    regularCards: RegularNotaCard[]
    repairCards: ReadyFgNotaCard[]
    regularSubtotal: number
    repairSubtotal: number
    total: number
  } | null>(null)

  const postedIds = new Set([...postedCardIds,...postedPayrollCards(),...claimedFgCards(savedDraft?.number)])
  const mandors = Array.from(new Set([...(savedDraft?[savedDraft.mandor]:[]),...(requestedMandor?[requestedMandor]:[]),...allResults.map((item) => item.mandor), ...allRepairs.map((item) => item.mandor)])).filter(Boolean)
  const activeResult = focusedResult?.mandor === selectedMandor
    ? focusedResult
    : allResults.find((item) => item.mandor === selectedMandor)
  const regularCards = allResults.filter((item) => item.mandor === selectedMandor).map((item) => toRegularCard(item, snapshots[regularFgNotaCardId(item)]))
  const visibleRepairCards = allRepairs.filter((item) => item.mandor === selectedMandor)
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
  const [cardDetail,setCardDetail]=useState<string|null>(null)
  const inspectRegular=regularCards.find(c=>c.id===cardDetail),inspectRepair=visibleRepairCards.find(c=>c.id===cardDetail)
  const editWork = regularCards.find(card => card.id === workCard && !postedIds.has(card.id))
  function applyWork(card: RegularNotaCard, value: Pick<RegularFgNotaSnapshot,'bsComponents'|'stuckComponents'>) {
    if (!editable || postedIds.has(card.id)) return
    setWorkOverrides(current => ({
      ...current,
      [card.id]: {
        cardId: card.id, fullRate: snapshots[card.id]?.fullRate ?? card.sewingRate + card.commissionRate + card.bomRate,
        sewingRate: card.sewingRate, commissionRate: card.commissionRate, bomRate: card.bomRate,
        ...value,
      },
    }))
    setNoteReviewed(false)
    setWorkCard(null)
  }
  const [payMessage,setPayMessage]=useState('')
  const [postedNumber,setPostedNumber]=useState('')
  function draftSnapshot(): FgDraft {
    return {number:savedDraft?.number ?? 'DFG-SIM-'+crypto.randomUUID().slice(0,8).toUpperCase(), version:savedDraft?.version ?? 0, mandor:selectedMandor, note, results:selectedRegular.map(c=>c.result), repairs:selectedRepair, snapshots:Object.fromEntries(selectedRegular.filter(c=>snapshots[c.id]).map(c=>[c.id,snapshots[c.id]]))}
  }
  function saveDraft(){
    try {
      const d=storeFgDraft(draftSnapshot())
      setSavedDraft(d);setDraftMessage('Draft '+d.number+' tersimpan.')
      const url=new URL(location.href);url.searchParams.set('draft',d.number);history.replaceState(history.state,'',url)
    } catch(error){setDraftMessage((error as Error).message)}
  }
  function voidDraft(){
    if(!savedDraft)return
    try {
      closeFgDraft(savedDraft.number,savedDraft.version,'VOID',voidReason)
      if(origin==='PAYROLL')location.assign('/keuangan/payroll-kasbon/')
      else location.assign('/produksi/susun-nota-fg/')
    } catch(error){setDraftMessage((error as Error).message);setVoidOpen(false)}
  }
  const postNota = () => {
    if (!editable || selectedIds.length === 0 || selectedIds.length > 50 || noteTotal <= 0 || !noteReviewed || postReason.trim().length < 5) return
    try {
    const d=storeFgDraft(draftSnapshot());setSavedDraft(d)
    const staged=selectedRegular.map(c=>({...c,standardBom:trainingBom(c.sku),completionCount:c.result.completionCount,qcQty:c.returned,returnedQty:c.returned,grossValue:c.gross,sizeRows:c.result.sizes.map((size,i)=>({size,sewn:c.result.expected[i],good:c.result.postedGoodBySize[i],bs:c.result.postedBsBySize[i],hold:c.result.stuckBySize[i],rewash:c.result.postedRewashBySize[i]}))}))
    const repairs=selectedRepair.map(c=>({id:c.id,source:c.sourceLabel,sku:[c.brand,c.sku].join(' ')+' · '+(c.sizes.length===1?c.sizes[0]:c.sizes[0]+'–'+c.sizes.at(-1)),qty:c.qty,components:c.components,unitRate:c.unitRate,subtotal:c.subtotal,sizeRows:c.sizes.map((size,i)=>({size,qty:c.qtyBySize[i]}))}))
    const reimbursement=selectedRegular.reduce((n,c)=>n+c.sewnQty*c.bomRate-c.bs*c.bsComponents.filter(x=>x.id.startsWith('bom:')).reduce((a,x)=>a+x.rate,0)-c.hold*c.stuckComponents.filter(x=>x.id.startsWith('bom:')).reduce((a,x)=>a+x.rate,0),0)
    const number='NFG-SIM-'+crypto.randomUUID().slice(0,8).toUpperCase()
    const actual=savePostedFg({mandor:selectedMandor,day:'2026-11-24',cards:selectedIds,doc:{number,date:'24 Nov 2026',status:'POSTED',source:[...staged.map(c=>c.source),...repairs.map(c=>c.source)].join(' · '),sku:[...new Set([...staged,...repairs].map(c=>c.sku))].join(' · '),good:staged.reduce((n,c)=>n+c.good,0),bs:staged.reduce((n,c)=>n+c.bs,0),stuck:staged.reduce((n,c)=>n+c.hold,0),labor:noteTotal-reimbursement,reimbursement,note:note.trim()||'Nota dari Susun Nota FG.',regularCards:staged,repairCards:repairs}})
    closeFgDraft(d.number,d.version,'POSTED',postReason)
    const url=new URL(location.href);url.searchParams.delete('draft');url.searchParams.set('nota',actual);history.replaceState(history.state,'',url)
    setPostedNumber(actual)
    setPostedNote({ mandor: selectedMandor, regularCards: selectedRegular, repairCards: selectedRepair, regularSubtotal, repairSubtotal, total: noteTotal })
    onPost(selectedIds)
    setNoteStatus('POSTED')
    } catch(error){setDraftMessage((error as Error).message)}
  }
  const startNextNota = () => {
    setWorkOverrides({});setWorkCard(null)
    setFresh(true);setSavedDraft(undefined);setDraftMessage('');setNote('');setPayMessage('');setPostedNumber('')
    const url=new URL(location.href);url.searchParams.delete('draft');url.searchParams.delete('nota');history.replaceState(history.state,'',url)
    setRegularIds([])
    setRepairIds([])
    setNoteReviewed(false)
    setPostedNote(null)
    setNoteStatus('DRAFT')
  }

  const returnLabel = origin === 'PAYROLL'?'Kembali ke Payroll & Kasbon':origin === 'QC' ? 'Kembali ke QC' : 'Kembali ke Bikin Bagus'
  const queueCount = regularCards.length + visibleRepairCards.length
  const availableCount = [...regularCards, ...visibleRepairCards].filter((card) => !postedIds.has(card.id)).length

  const openedNumber=new URLSearchParams(location.search).get('nota')
  if(openedNumber&&!postedNote)return <PostedFgDetail number={openedNumber}/>
  if(requestedDraft&&!fresh&&!savedDraft)return <section className="panel gar-panel"><h1>Draft nota FG sudah ditutup atau tidak ditemukan</h1><a href="/keuangan/payroll-kasbon/">Kembali ke Payroll &amp; Kasbon</a></section>
  return <>
    <section className="hero-copy compact fg-handoff-hero">
      <div><div className="eyebrow">PRODUKSI · HALAMAN ANTREAN NOTA FG</div><h1>Susun Nota FG</h1><p>Buka langsung tanpa lewat QC. Card FG Reguler, Bikin Bagus, dan Susulan Good tetap membawa sumbernya lalu dikelompokkan per Mandor.</p></div>
      <div className="handoff-page-actions">{origin !== 'MENU' && <button type="button" className="soft-btn handoff-back" onClick={onReturn}><ArrowLeft/> {returnLabel}</button>}<button type="button" className="soft-btn" onClick={onOpenQc}>Buka QC</button><button type="button" className="soft-btn" onClick={() => onOpenBs(activeResult)}>Buka Bikin Bagus</button></div>
    </section>
    <div className="handoff-flow-strip"><span className="done"><b>1</b>QC / rework terkunci</span><i/><span className="done"><b>2</b>Card siap</span><i/><span className="active"><b>3</b>Susun Nota FG</span><i/><span><b>4</b>Payroll</span></div>
    <div className={`handoff-queue-banner ${queueCount === 0 ? 'empty' : ''}`}><FileText/><div><strong>{focusedId ? `${focusedId} dibuka dari sumbernya` : 'Antrean Nota FG mandiri'}</strong><span>Card yang sudah masuk Nota tetap terkunci. Ganti Mandor akan mengosongkan draft supaya nota tidak mencampur penerima.</span></div>{mandors.length > 0 ? <label className="nota-mandor-filter"><span>MANDOR NOTA</span><select value={selectedMandor} disabled={!editable} onChange={(event) => changeMandor(event.target.value)}>{mandors.map((mandor) => <option key={mandor}>{mandor}</option>)}</select><small>{availableCount} siap · {queueCount - availableCount} posted</small></label> : <em>Belum ada card</em>}</div>
    <FgRegister payroll={origin==='PAYROLL'}/>
    {editable&&<details className="panel owner-source-drafts"><summary>Draft nota FG · {selectedMandor} ({fgDrafts().filter(d=>d.mandor===selectedMandor).length})</summary>
      {fgDrafts().filter(d=>d.mandor===selectedMandor).map(d=><div className="owner-doc-row" key={d.number}><span><strong>{d.number}</strong><small>{d.results.length+d.repairs.length} kartu</small></span><a className="gar-button" href={'?draft='+encodeURIComponent(d.number)+(origin==='PAYROLL'?'&dari=payroll':'')}>Buka &amp; edit</a></div>)}</details>}
    {noteStatus === 'POSTED' && <div className="handoff-success"><CheckCircle2/><div><strong>Nota FG sudah posted dan card terkunci</strong><span>{postedNumber} · {money(displayTotal)} · masuk antrean Payroll, belum mengubah kas.</span></div><button type="button" className="primary-btn" onClick={()=>{try{payForSource(postedNumber,sessionStorage.getItem('erp.owner.payroll.focus'),true);location.assign('/keuangan/payroll-kasbon/')}catch(e){setPayMessage((e as Error).message)}}}>Masukkan ke payroll · {money(displayTotal)}</button>{payMessage&&<p role="alert">{payMessage}</p>}<a className="soft-btn" href={'/produksi/susun-nota-fg/?nota='+encodeURIComponent(postedNumber)+(origin==='PAYROLL'?'&dari=payroll':'')}>Buka detail nota ini</a><button type="button" className="soft-btn" onClick={startNextNota}>Susun nota berikutnya <ArrowRight/></button></div>}
    <section className="handoff-layout">
      <BrowsePane as="div" className="panel handoff-workbench" aria-label="Daftar sumber barang jadi">
        {activeResult ? <>
          <header className="handoff-source-head"><span>01</span><div><small>QC {activeResult.completionStatus === 'PARTIAL_SELECTION' ? 'SELESAI SEBAGIAN' : activeResult.completionStatus === 'WAITING_LAUNDRY' ? 'MENUNGGU LAUNDRY' : activeResult.completionStatus === 'WAITING_REWORK' ? 'MENUNGGU CUCI ULANG' : 'LENGKAP'} · {activeResult.parentId} · BATCH {activeResult.batchId}</small><h2>{activeResult.brand} · SKU {activeResult.finalSku}</h2><p>{activeResult.finalProductName} · {activeResult.finalColor} · Range {activeResult.finalRange} · bahan {activeResult.material}</p><div className="handoff-mandor-hero"><UserRound/><span><small>MANDOR PENERIMA NOTA</small><strong>{activeResult.mandor}</strong></span></div></div><strong>{returnedTotal} pulang · {fgQuantity(goodTotal)} Good</strong></header>
          <div className="handoff-section-title"><div><span>02</span><div><strong>Rekonsiliasi fisik dari QC</strong><small>Selesai Dijahit menjadi dasar hak gaji. Good menentukan FG; Stuck hanya menahan komponen yang belum dipasang. Hold → BS tidak memotong kedua kali.</small></div></div><em className="ok">QC read-only</em></div>
          <div className="handoff-size-breakdown" role="table" aria-label="Rekonsiliasi serah FG per size"><div className="handoff-size-breakdown-head" role="row"><span>SIZE</span><span>POTONGAN</span><span>BAGUS → FG</span><span>BS</span><span>CUCI ULANG</span><span>SISA OPEN</span></div>{activeResult.sizes.map((size, index) => <div className={`handoff-size-breakdown-row ${activeResult.remainingBySize[index] > 0 ? 'has-outstanding' : ''}`} role="row" key={size}><strong data-label="SIZE">{size}</strong><strong data-label="POTONGAN" className="piece-total">{activeResult.expected[index]} pcs</strong><strong className="good" data-label="BAGUS → FG">{fgQuantity(activeResult.postedGoodBySize[index])}</strong><span className="bs" data-label="BS">{activeResult.postedBsBySize[index]} pcs</span><span className="rewash" data-label="CUCI ULANG">{activeResult.postedRewashBySize[index]} pcs</span><span className="stuck" data-label="SISA OPEN">{activeResult.remainingBySize[index]} pcs</span></div>)}<div className="handoff-size-breakdown-total" role="row"><strong>TOTAL</strong><span>{expectedTotal} pcs</span><strong>{fgQuantity(goodTotal)}</strong><span>{bsTotal} pcs</span><span>{rewashTotal} pcs</span><span>{outstanding} pcs</span></div></div>
          <div className="handoff-equation"><span><small>GOOD → FG</small><strong>{fgQuantity(goodTotal)}</strong></span><b>+</b><span><small>BS</small><strong>{bsTotal} pcs</strong></span><b>+</b><span><small>CUCI ULANG</small><strong>{rewashTotal} pcs</strong></span><b>=</b><span className="total"><small>TOTAL PULANG</small><strong>{returnedTotal} pcs</strong></span><b>+</b><span className="outside"><small>SISA OPEN</small><strong>{outstanding} pcs</strong></span></div>
        </> : <section className="nota-source-empty"><FileText/><div><span>01 · ANTREAN MANDIRI</span><h2>{selectedMandor ? `Belum ada card QC ${selectedMandor}` : 'Belum ada card siap Nota FG'}</h2><p>{selectedMandor ? 'Bikin Bagus atau Susulan Good tetap bisa disusun sendiri. Card QC baru muncul otomatis setelah posting finishing.' : 'Posting hasil QC atau buka card siap dari halaman Barang BS & Rework.'}</p></div></section>}

        <section className="nota-work-group regular"><header><div><span>03 · ANTREAN FG REGULER</span><h2>Card finishing belum masuk Nota FG</h2><p>Hanya card milik Mandor terpilih. Penyelesaian sebagian menjadi card terpisah dan tidak menghapus sisa yang masih open.</p></div><em>{displayRegular.length} {noteStatus==='POSTED'?'di nota posted':'di draft'} · {regularCards.length} tampil</em></header><div>{regularCards.map((card) => {
          const added = regularIds.includes(card.id)
          const posted = postedIds.has(card.id)
          const focused = card.id === focusedId
          const rate = card.sewingRate + card.commissionRate + card.bomRate
          const status = posted ? 'SUDAH MASUK NOTA' : added ? 'SEDANG DI DRAFT' : focused ? 'DIBUKA DARI QC' : 'SIAP DISUSUN'
          return <article className={`nota-work-card regular ${added ? 'added' : ''} ${focused ? 'focused' : ''} ${posted ? 'posted' : ''}`} key={card.id}><header><div><small>{card.source}</small><strong>{card.sku}</strong></div><span>{status}</span></header><div className="nota-work-facts"><span><small>SELESAI DIJAHIT</small><strong className="piece-total">{card.sewnQty} pcs</strong></span><span className="good"><small>GOOD → FG</small><strong>{fgQuantity(card.good)}</strong></span><span className="bs"><small>BS</small><strong>{card.bs} pcs</strong></span><span className="rewash"><small>CUCI ULANG</small><strong>{card.rewash} pcs</strong></span><span className="hold"><small>STUCK</small><strong>{card.hold} pcs</strong></span></div><div className="nota-bs-components"><span>KOMPONEN BS BELUM DIKERJAKAN · SNAPSHOT</span><div>{card.bsComponents.length > 0 ? card.bsComponents.map((component) => <em key={component.id}><Check/>{component.name}<b>{money(component.rate)}</b></em>) : <small>Tidak ada pengurang BS</small>}</div></div><div className="nota-bs-components stuck-components"><span>KOMPONEN STUCK BELUM DIPASANG · SNAPSHOT</span><div>{card.stuckComponents.length > 0 ? card.stuckComponents.map((component) => <em key={component.id}><Check/>{component.name}<b>{money(component.rate)}</b></em>) : <small>Tidak ada komponen Stuck yang ditahan</small>}</div></div><div className="nota-value-formula"><span><small>SELESAI DIJAHIT × HARGA</small><strong>{card.sewnQty} × {money(rate)}</strong><em>{money(card.gross)}</em></span><b>−</b><span className="deduction"><small>BS × KOMPONEN BELUM DIKERJAKAN</small><strong>{card.bs} × {money(total(card.bsComponents.map((component) => component.rate)))}</strong><em>{money(card.bsDeduction)}</em></span><b>−</b><span className="deduction stuck"><small>STUCK × KOMPONEN BELUM DIPASANG</small><strong>{card.hold} × {money(total(card.stuckComponents.map((component) => component.rate)))}</strong><em>{money(card.stuckDeduction)}</em></span><b>=</b><span className="result"><small>NILAI FG REGULER</small><strong>{money(card.subtotal)}</strong><em>Good bukan pengali upah</em></span></div><footer><small>ID {card.id} menjaga hak jahit dan setiap nilai komponen hanya dibayar sekali.</small>{editable && !posted && (card.bs > 0 || card.hold > 0) && <button type="button" className="soft-btn" onClick={() => setWorkCard(card.id)}>Atur komponen BS &amp; Stuck</button>}<button type="button" className="soft-btn" onClick={()=>setCardDetail(card.id)}>Detail kartu</button><button type="button" disabled={!editable || posted} onClick={() => toggleRegular(card.id)}>{posted ? 'Terkunci di Nota' : added ? 'Keluarkan dari Draft' : 'Tambah ke Nota FG'}</button></footer></article>
        })}{regularCards.length === 0 && <div className="nota-work-empty"><FileText/><strong>Belum ada card FG Reguler</strong><small>Selesaikan QC atau pilih Mandor lain.</small></div>}</div></section>

        <section className="nota-work-group repair"><header><div><span>04 · BIKIN BAGUS & SUSULAN GOOD</span><h2>Card plus yang sudah diterima</h2><p>Nilai mengikuti snapshot sumber: komponen Bikin Bagus atau nilai Hold yang benar-benar dilepas, bukan tarif master hari ini.</p></div><button type="button" className="soft-btn" onClick={() => onOpenBs(activeResult)}>Buka Browser Kasus <ArrowRight/></button></header><div>{visibleRepairCards.map((card) => {
          const added = repairIds.includes(card.id)
          const posted = postedIds.has(card.id)
          const focused = card.id === focusedId
          const status = posted ? 'SUDAH MASUK NOTA' : added ? 'SEDANG DI DRAFT' : focused ? 'DIBUKA DARI BIKIN BAGUS' : 'SIAP DISUSUN'
          return <article className={`nota-work-card repair ${added ? 'added' : ''} ${focused ? 'focused' : ''} ${posted ? 'posted' : ''}`} key={card.id}><header><div><small>{card.id} · {card.sourceLabel}</small><strong>{card.brand} · {card.sku}</strong></div><span>{status}</span></header><div className="nota-repair-lineage"><ShieldCheck/><span><small>{card.kind === 'STUCK_RELEASE' ? 'SUSULAN GOOD · LEPAS HOLD' : 'BIKIN BAGUS · QC ULANG LULUS'}</small><strong>Kasus {card.caseId} · sumber {card.originId ?? '—'}</strong></span></div><div className="nota-repair-components">{card.components.map((component) => <span key={component.id}><Check/><small>{component.name}</small><strong>{money(component.rate)}</strong></span>)}</div><div className="nota-work-rate repair"><span>Qty diterima <b>{card.qty} pcs</b></span><span>Tarif snapshot <b>{money(card.unitRate)}</b></span><strong>{card.qty} × {money(card.unitRate)} = {money(card.subtotal)}</strong></div><footer><small>{card.createdAt} · penerima {card.mandor}</small><button type="button" className="soft-btn" onClick={()=>setCardDetail(card.id)}>Detail kartu</button><button type="button" disabled={!editable || posted} onClick={() => toggleRepair(card.id)}>{posted ? 'Terkunci di Nota' : added ? 'Keluarkan dari Draft' : 'Tambah ke Nota FG'}</button></footer></article>
        })}{visibleRepairCards.length === 0 && <div className="nota-work-empty repair"><Wrench/><strong>Belum ada card Bikin Bagus / Susulan</strong><small>Buka Browser Kasus untuk melihat pekerjaan yang sudah diterima.</small></div>}</div></section>
        <label className="handoff-note nota-note"><span>CATATAN NOTA FG</span><textarea maxLength={2000} placeholder="Opsional" disabled={!editable} value={note} onChange={(event) => { setNote(event.target.value); setNoteReviewed(false) }}/></label>
      </BrowsePane>

      <aside className="panel handoff-payroll-ticket"><div className="handoff-ticket-title"><span>NOTA FG · {noteStatus==='POSTED'?postedNumber:savedDraft?.number??'Draft'}</span><h2>{displayMandor || 'Pilih Mandor'}</h2><p>{displayRegular.length} FG Reguler · {displayRepair.length} Bikin Bagus / Susulan</p><small>24 Nov 2026 · {noteStatus === 'POSTED' ? 'posted, belum dibayar' : 'draft dapat disusun'}</small></div><div className="nota-ticket-groups"><article className="regular"><span><small>FG REGULER</small><strong>{displayRegular.length} card</strong></span><b>{money(displayRegularSubtotal)}</b></article><article className="repair"><span><small>BIKIN BAGUS / SUSULAN</small><strong>{displayRepair.length} card</strong></span><b>{money(displayRepairSubtotal)}</b></article></div><div className="handoff-net"><span>TOTAL NOTA FG</span><strong>{money(displayTotal)}</strong><small>Masuk Payroll setelah posted. Belum ada pembayaran atau pergerakan kas.</small></div><div className="handoff-output"><span>DOKUMEN INI MEMBAWA</span><p><Check/><b>{total(displayRegular.map((card) => card.sewnQty))} pcs</b> Selesai Dijahit sebagai dasar</p><p><ShieldCheck/><b>{money(total(displayRegular.map((card) => card.deduction)))}</b> komponen BS + Stuck ditahan</p><p><Wrench/><b>{total(displayRepair.map((card) => card.qty))} pcs</b> plus eligible</p></div>{editable&&<div className="fg-draft-actions"><button type="button" className="soft-btn" disabled={!selectedIds.length||selectedIds.length>50} onClick={saveDraft}>Simpan draft nota FG</button>{savedDraft&&<button type="button" className="soft-btn" onClick={()=>setVoidOpen(true)}>Batalkan draft ini</button>}</div>}
        {draftMessage&&<p role="status">{draftMessage}</p>}
        {editable&&<label className="handoff-note"><span>Alasan posting</span><input aria-label="Alasan posting" maxLength={1000} value={postReason} onChange={e=>{setPostReason(e.target.value);setNoteReviewed(false)}}/></label>}
        <label className="handoff-final-check"><input type="checkbox" disabled={!editable || selectedIds.length === 0} checked={noteReviewed} onChange={(event) => setNoteReviewed(event.target.checked)}/><span><strong>Susunan Nota FG sudah gue review</strong><small>Semua card milik {displayMandor || 'Mandor yang dipilih'}; ID sumber dan formula terlihat.</small></span></label><button type="button" className="primary-btn handoff-submit" disabled={!editable || selectedIds.length === 0 || noteTotal <= 0 || !noteReviewed || selectedIds.length>50 || postReason.trim().length<5} onClick={postNota}>{noteStatus === 'POSTED' ? 'Nota FG sudah posted' : 'Post Nota FG ke Payroll'} <ArrowRight/></button><p className="handoff-audit-note">Card yang tidak dipilih tetap di antrean. Dalam prototipe ini lock bertahan selama sesi aplikasi; backend wajib memakai idempotency dan unique card ID.</p></aside>
    </section>
    {editWork && editable && <FgIncompleteWork source={editWork.sku + ' · ' + editWork.source}
      bs={editWork.bs} hold={editWork.hold} value={editWork} onClose={() => setWorkCard(null)} onSave={value => applyWork(editWork, value)}/>}
    {cardDetail&&(inspectRegular||inspectRepair)&&<ReasonDialog title={'Detail kartu · '+cardDetail} closeLabel="Kembali" onClose={()=>setCardDetail(null)}>
      {inspectRegular&&<><h3>{inspectRegular.sku}</h3><p>{inspectRegular.source} · {selectedMandor}</p><div className="wh-size-boxes">{inspectRegular.result.sizes.map((x,i)=><div className="wh-size-box" key={x}><header>Ukuran <strong>{x}</strong></header><p>Good {fgQuantity(inspectRegular.result.postedGoodBySize[i])}</p><small>BS {inspectRegular.result.postedBsBySize[i]} · Stuck {inspectRegular.result.stuckBySize[i]}</small></div>)}</div><p>Nilai kartu · {money(inspectRegular.subtotal)}</p></>}
      {inspectRepair&&<><h3>{inspectRepair.brand} {inspectRepair.sku}</h3><p>{inspectRepair.sourceLabel} · {selectedMandor}</p><div className="wh-size-boxes">{inspectRepair.sizes.map((x,i)=><div className="wh-size-box" key={x}><header>Ukuran <strong>{x}</strong></header><p>{fgQuantity(inspectRepair.qtyBySize[i])}</p></div>)}</div>{inspectRepair.components.map(c=><div className="wh-register-row" key={c.id}><span>{c.name}</span><strong>{money(c.rate)}/pcs</strong></div>)}<p>{inspectRepair.qty} × {money(inspectRepair.unitRate)} = {money(inspectRepair.subtotal)}</p></>}
    </ReasonDialog>}
    {voidOpen&&<ReasonDialog title="Batalkan draft nota FG?" onClose={()=>setVoidOpen(false)}><p>{savedDraft?.number} · Kartu akan tersedia untuk nota berikut.</p><label>Alasan pembatalan<input aria-label="Alasan pembatalan" maxLength={1000} value={voidReason} onChange={e=>setVoidReason(e.target.value)}/></label><button type="button" className="soft-btn" disabled={voidReason.trim().length<5} onClick={voidDraft}>Ya, batalkan draft</button></ReasonDialog>}
  </>
}
