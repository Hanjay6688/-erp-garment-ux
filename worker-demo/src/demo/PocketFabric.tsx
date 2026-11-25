import { BrowsePane } from '../components/BrowsePane'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowDownLeft, ArrowRight, ClipboardList, Layers3, MapPin, Ruler, Scissors, Search } from 'lucide-react'
import { browseMatch } from '../browseMatch'
import RecordTable from '../RecordTable'
import { amountText, fixtureDate } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { pocketRollLabel, pocketRolls, readReceipts, receiptPath, type PocketRoll, type PocketUnit } from './pocketReceipts'
import { pocketMasterPath, pocketMaterialLabel, readPocketMaterials } from './pocketMaterials'
import {
  periodActive, planPocketAllocation, planPocketUsage, pocketBalance, pocketBookKey,
  pocketScale, readPocketBook, type PocketAllocation, type PocketBook, type UsageLine,
} from './pocketUsage'
import { lastWarehouseDay } from './warehouseDay'
import '../warehouse.css'
import './warehouseForms.css'
import './pocketFabric.css'

const length = (qty: number, unit: string) => (qty / pocketScale).toLocaleString('id-ID', { maximumFractionDigits: 6 }) + ' ' + unit
const rupiah = (cents: number) => amountText(cents / 100)

type RollPosition = { roll: PocketRoll; incoming: number; left: number }
type UsageMode = 'keluar' | 'sisa' | 'utuh'
type UsageDraft = { mode: UsageMode; amount: string }
type UsageSelection = { rolls: PocketRoll[]; whole: boolean }
type Reverse = { id: string; kind: 'issue' | 'period' }
type Feedback = { text: string; error?: boolean }

function sumLengths<T extends { roll: PocketRoll }>(rows: T[], quantity: (row: T) => number) {
  const sums = new Map<PocketUnit, number>()
  for (const row of rows) sums.set(row.roll.unit, (sums.get(row.roll.unit) ?? 0) + quantity(row))
  return Array.from(sums, ([unit, qty]) => length(qty, unit)).join(' · ') || '—'
}

export default function PocketFabric() {
  const rolls = pocketRolls()
  const [detailId, setDetailId] = useState(() => new URLSearchParams(location.search).get('roll'))
  const [book, setBook] = useState(readPocketBook)
  const [tab, setTab] = useState<'stock' | 'cost'>('stock')
  const [query, setQuery] = useState(() => new URLSearchParams(location.search).get('surat') ?? '')
  const [material, setMaterial] = useState('')
  const [warehouse, setWarehouse] = useState('')
  const [onlyAvailable, setOnlyAvailable] = useState(() => {
    const linked = rolls.find(roll => roll.id === detailId)
    return !linked || pocketBalance(book, linked) > 0
  })
  const [checked, setChecked] = useState<string[]>([])
  const [usage, setUsage] = useState<UsageSelection | null>(null)
  const [start, setStart] = useState('2026-11-23')
  const [end, setEnd] = useState(fixtureDate)
  const [allocReason, setAllocReason] = useState('Pembagian biaya kain kantong')
  const [preview, setPreview] = useState<PocketAllocation | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [undo, setUndo] = useState<Reverse | null>(null)
  const [why, setWhy] = useState('')
  const detail = rolls.find(r => r.id === detailId)
  const materialKey = (roll: PocketRoll) => roll.materialId ?? roll.name
  const catalog = new Map(readPocketMaterials().map(item => [item.id, pocketMaterialLabel(item)]))
  const records: RollPosition[] = rolls.map(roll => ({ roll, incoming: Math.round(roll.length * pocketScale), left: pocketBalance(book, roll) }))
  const matched = records.filter(({ roll, incoming, left }) => (!warehouse || roll.location === warehouse)
    && browseMatch(query, roll.id, pocketRollLabel(roll), roll.name, catalog.get(materialKey(roll)), roll.factory, roll.supplier, roll.receipt, roll.location, roll.unit, roll.date,
      length(incoming, roll.unit), length(left, roll.unit), length(incoming-left, roll.unit)))
  const materialNames = new Map(matched.map(({roll})=>[materialKey(roll),catalog.get(materialKey(roll)) ?? roll.name]))
  const materialIds = [...materialNames.keys()].sort((a,b)=>(materialNames.get(a)??a).localeCompare(materialNames.get(b)??b,'id'))
  const activeMaterial = materialNames.has(material) ? material : ''
  const scoped = matched.filter(row => !activeMaterial || materialKey(row.roll) === activeMaterial)
  const visible = onlyAvailable ? scoped.filter(row => row.left > 0) : scoped
  const selected = rolls.filter(roll => checked.includes(roll.id))
  const feedbackRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    if (feedback && !undo) feedbackRef.current?.focus({ preventScroll: true })
  }, [feedback, undo])

  function save(next: PocketBook, message: string) {
    sessionStorage.setItem(pocketBookKey, JSON.stringify(next))
    setBook(next)
    setPreview(null)
    setFeedback({ text: message })
  }

  function confirmUsage(form: UsageSelection, date: string, reason: string, drafts: UsageDraft[], shown: UsageLine[]) {
    const current = readPocketBook()
    const liveRolls = new Map(pocketRolls().map(roll => [roll.id, roll]))
    const lines = form.rolls.map((item, index) => {
      const roll = liveRolls.get(item.id)
      if (!roll) throw Error('Roll ' + item.id + ' sudah tidak tersedia. Pilih ulang roll.')
      const { mode, amount } = drafts[index]
      return planPocketUsage(current, [roll], date, reason, mode, amount)[0]
    })
    if (JSON.stringify(lines) !== JSON.stringify(shown)) throw Error('Saldo roll berubah. Tutup dan periksa kembali.')
    const issues = lines.map(({ roll, qty, cents }, index) => ({
      id: 'KT-' + String(current.issues.length + index + 1).padStart(3, '0') + '-OUT',
      roll: roll.id, unit: roll.unit, date, qty, cents, reason: reason.trim(),
    }))
    const message = lines.length > 1 ? lines.length + ' roll dikeluarkan.' : length(lines[0].qty, lines[0].roll.unit) + ' keluar dari ' + pocketRollLabel(lines[0].roll) + '.'
    save({ ...current, issues: [...current.issues, ...issues] }, message)
    setChecked(ids => ids.filter(id => !issues.some(issue => issue.roll === id)))
    setDetailId(lines.length === 1 ? lines[0].roll.id : null)
    setUsage(null)
  }

  function showAllocation() {
    try {
      setPreview(planPocketAllocation(readPocketBook(), start, end))
      setFeedback(null)
    } catch (error) {
      setPreview(null)
      setFeedback({ text: (error as Error).message, error: true })
    }
  }

  function postAllocation() {
    try {
      const current = readPocketBook()
      const latest = planPocketAllocation(current, start, end)
      if (!allocReason.trim() || JSON.stringify(latest) !== JSON.stringify(preview)) {
        throw Error('Periksa lagi perhitungan dan isi alasan pembagian.')
      }
      const id = 'BAGI-' + String(current.allocations.length + 1).padStart(3, '0')
      const allocations = [...current.allocations, { ...latest, id, reason: allocReason.trim() }]
      save({ ...current, allocations }, id + ' disahkan. Nilai kain masuk HPP sesuai pembagian.')
    } catch (error) {
      setFeedback({ text: (error as Error).message, error: true })
    }
  }

  function reverse(event: FormEvent) {
    event.preventDefault()
    if (!undo || !why.trim()) return
    try {
      const current = readPocketBook()
      if (undo.kind === 'period') {
        if (!current.allocations.some(a => a.id === undo.id && !a.reversal)) throw Error('Pembagian sudah dibatalkan.')
        const allocations = current.allocations.map(a => a.id === undo.id ? { ...a, reversal: why.trim() } : a)
        save({ ...current, allocations }, 'Pembagian dibalik. Nilai kain kembali ke biaya periode.')
      } else {
        const issue = current.issues.find(i => i.id === undo.id && !i.reversal)
        if (!issue) throw Error('Pemakaian sudah dibalik.')
        if (periodActive(current, issue.date, issue.date)) throw Error('Balikkan pembagian biaya periode ini lebih dulu.')
        const issues = current.issues.map(i => i.id === issue.id ? { ...i, reversal: why.trim() } : i)
        save({ ...current, issues }, 'Pemakaian dibalik. Panjang kembali ke saldo roll.')
      }
      setUndo(null)
    } catch (error) {
      setFeedback({ text: (error as Error).message, error: true })
    }
  }

  const openUsage = (choice: UsageSelection) => { setUsage(choice); setFeedback(null) }
  const openReverse = (choice: Reverse) => { setUndo(choice); setWhy(''); setFeedback(null) }
  const switchTab = (choice: typeof tab) => { setTab(choice); setFeedback(null) }

  return <div className="pocket-workspace">
    <header className="hero-copy compact wh-hero pocket-heading">
      <div><div className="eyebrow">GUDANG · BAHAN PER ROLL</div><h1>Kain kantong</h1><p>Pilih bahan, cek sisa tiap roll, lalu catat panjang yang dipakai.</p></div>
      <div className="pocket-heading-actions"><a className="soft-btn" href={pocketMasterPath}><Layers3 size={17} aria-hidden="true"/>Master kain kantong</a>
        <a className="primary-btn" href={receiptPath}><ArrowDownLeft size={17} aria-hidden="true"/>Terima kain kantong</a></div>
    </header>
    <nav className="pocket-navigation" aria-label="Kain kantong">
      <button type="button" aria-current={tab === 'stock'} onClick={() => switchTab('stock')}>Stok &amp; pemakaian</button>
      <button type="button" aria-current={tab === 'cost'} onClick={() => switchTab('cost')}>Biaya per periode</button>
    </nav>
    {tab === 'stock' ? <>
      {feedback && !undo && <p ref={feedbackRef} tabIndex={-1} className="wh-feedback" role={feedback.error ? 'alert' : 'status'}>{feedback.text}</p>}
      <section className="panel wh-workspace material-rolls-workspace pocket-stock-workspace">
        <div className="wh-toolbar pocket-toolbar">
          <label className="wh-search"><Search aria-hidden="true"/><input type="search" aria-label="Cari roll" value={query} onChange={e => setQuery(e.target.value)} placeholder="Cari roll, bahan, pabrik, atau surat jalan…"/></label>
          <label className="pocket-filter">Gudang<select value={warehouse} onChange={e => setWarehouse(e.target.value)}><option value="">Semua gudang</option>
            {[...new Set(rolls.map(roll => roll.location))].map(location => <option key={location}>{location}</option>)}</select></label>
          <label className="pocket-filter">Saldo<select value={onlyAvailable ? 'available' : ''} onChange={e => setOnlyAvailable(e.target.value === 'available')}>
            <option value="">Semua saldo</option><option value="available">Masih bersaldo</option></select></label>
        </div>
        <div className="wh-master-detail rolls">
          <BrowsePane embedded className="wh-browser pocket-browser" aria-label="Daftar stok kain kantong">
            <header><div><span>BAHAN</span><strong>{materialIds.length} jenis kain kantong</strong></div><Layers3 size={18} aria-hidden="true"/></header>
            <div className="wh-browser-list">
              {['', ...materialIds].map(id => {
                const group = id ? matched.filter(row => materialKey(row.roll) === id) : matched
                return <button key={id} type="button" aria-pressed={id === activeMaterial} className={id === activeMaterial ? 'active' : ''}
                  onClick={() => setMaterial(id)}><span className="wh-index"><Ruler size={17} aria-hidden="true"/></span>
                  <div><strong>{materialNames.get(id) ?? 'Semua kain kantong'}</strong><small>{group.filter(row => row.left > 0).length} roll bersaldo</small></div><b>{sumLengths(group, row => row.left)}</b>
                </button>
              })}
            </div>
          </BrowsePane>
          <div className="wh-detail">
            <header className="wh-detail-head"><div><span>STOK PER ROLL</span><h2>{materialNames.get(activeMaterial) ?? 'Semua kain kantong'}</h2><p>{scoped.filter(row => row.left > 0).length} dari {scoped.length} roll masih bersaldo</p></div></header>
            <dl className="pocket-stock-totals" aria-label="Ringkasan panjang kain kantong">
              <div className="pocket-incoming"><dt>Panjang masuk</dt><dd>{sumLengths(scoped, row => row.incoming)}</dd></div>
              <div className="pocket-spent"><dt>Terpakai</dt><dd>{sumLengths(scoped, row => row.incoming - row.left)}</dd></div>
              <div className="pocket-remaining"><dt>Sisa gudang</dt><dd>{sumLengths(scoped, row => row.left)}</dd></div>
            </dl>
            <div className="wh-roll-head pocket-roll-head">
              <strong>Roll di gudang</strong>
              {selected.length > 0 && <span>{selected.length} roll dipilih</span>}
            </div>
            <ul className="wh-roll-list pocket-stock-list" aria-label="Stok per roll">
              {visible.map(({ roll, incoming, left }) => <li key={roll.id} className="pocket-stock-row">
                <article>
                  <header><div className="wh-roll-id"><i><Ruler aria-hidden="true"/></i><div><strong>{roll.name}</strong>{(roll.factory||roll.supplier)&&<small>{[roll.factory,roll.supplier].filter(Boolean).join(' · ')}</small>}<small className="record-code">{pocketRollLabel(roll)} · {roll.receipt} · {roll.date}</small></div></div>
                    <label className="pocket-check"><input type="checkbox" aria-label={'Pilih roll ' + roll.id} disabled={left <= 0} checked={checked.includes(roll.id)}
                      onChange={e => setChecked(ids => e.target.checked ? [...ids, roll.id] : ids.filter(id => id !== roll.id))}/><span>Pilih</span></label>
                  </header>
                  <dl className="pocket-stock-metrics">
                    <div className="pocket-incoming"><dt>Masuk</dt><dd>{length(incoming, roll.unit)}</dd></div>
                    <div className="pocket-spent"><dt>Terpakai</dt><dd>{length(incoming - left, roll.unit)}</dd></div>
                    <div className="pocket-remaining"><dt>Sisa</dt><dd className="pocket-quantity">{length(left, roll.unit)}</dd></div>
                  </dl>
                  <div className="wh-roll-progress" aria-hidden="true"><span style={{ width: `${100 * left / Math.max(incoming, 1)}%` }}/></div>
                  <footer><span><MapPin aria-hidden="true"/>{roll.location}</span><span>{amountText(roll.rate)} / {roll.unit}</span>
                    <div className="wh-roll-actions"><button type="button" className="wh-roll-history" aria-expanded={detailId === roll.id}
                      onClick={() => setDetailId(detailId === roll.id ? null : roll.id)}>Riwayat roll <ArrowRight aria-hidden="true"/></button>
                    <button type="button" className="pocket-use-button" aria-label={'Catat pemakaian ' + roll.id} disabled={left <= 0}
                      onClick={() => openUsage({ rolls: [roll], whole: false })}><Scissors aria-hidden="true"/>{left > 0 ? 'Pakai roll' : 'Saldo habis'}</button></div>
                  </footer>
                </article>
                {detail?.id === roll.id && <section className="wh-roll-ledger" aria-label={'Mutasi roll ' + roll.id}>
                  <h3>Mutasi roll · {pocketRollLabel(roll)}</h3>
                  <div className="wh-register-row">
                    <span><strong>Masuk · {length(incoming, roll.unit)}</strong><small>{roll.date} · {roll.receipt}</small></span>
                    <a href={receiptPath + '&surat=' + encodeURIComponent(roll.receipt)}>Lihat penerimaan</a>
                  </div>
                  {book.issues.filter(i => i.roll === roll.id).map(issue => <div className="wh-register-row" key={issue.id}>
                    <span><strong>Keluar · {length(issue.qty, roll.unit)}</strong><small>{issue.date} · {issue.id} · {rupiah(issue.cents)}</small></span>
                    {issue.reversal ? <span>Dibalik · {issue.reversal}</span> : <button type="button" className="soft-btn" onClick={() => openReverse({ kind: 'issue', id: issue.id })}>Balikkan {issue.id}</button>}
                  </div>)}
                </section>}
              </li>)}
            </ul>
            {!visible.length && (onlyAvailable && scoped.length > 0
              ? <div className="pocket-empty"><p>Semua roll di daftar ini sudah habis.</p><button type="button" className="soft-btn" onClick={() => setOnlyAvailable(false)}>Lihat roll habis</button></div>
              : <p className="pocket-empty">Tidak ada roll yang cocok dengan pencarian.</p>)}
            {selected.length > 0 && <div className="pocket-bulk">
              <p><strong>{selected.length} roll dipilih</strong><small>{selected.map(pocketRollLabel).join(', ')}</small></p>
              <button type="button" className="soft-btn" onClick={() => openUsage({ rolls: selected, whole: true })}>Pakai seluruh sisa · {selected.length} roll</button>
              <button type="button" className="primary-btn" onClick={() => openUsage({ rolls: selected, whole: false })}>Atur pemakaian <ArrowRight size={16} aria-hidden="true"/></button>
            </div>}
          </div>
        </div>
      </section>
      {usage && <PocketUsageForm key={JSON.stringify([usage.whole, ...usage.rolls.map(r => r.id)])} selection={usage} book={book} onClose={() => setUsage(null)}
        onConfirm={(date, reason, drafts, lines) => confirmUsage(usage, date, reason, drafts, lines)}/>}
      <details className="panel wh-pocket-use pocket-history">
        <summary><ClipboardList size={16} aria-hidden="true"/>Riwayat pemakaian <span>{book.issues.length}</span></summary>
        {book.issues.length === 0 && <p>Belum ada pemakaian.</p>}
        {[...book.issues].reverse().map(issue => {
          const roll = rolls.find(r => r.id === issue.roll)
          const previous = roll ?? readReceipts().flatMap(r => r.rolls).find(r => r.id === issue.roll)
          const unit = issue.unit ?? previous?.unit ?? 'yd'
          return <div className="wh-register-row" key={issue.id}>
            <span><strong className="pocket-quantity">{length(issue.qty, unit)} keluar</strong><small>{previous ? `${pocketRollLabel(previous)} · ${previous.receipt}` : issue.roll} · {issue.date} · {issue.id} · {rupiah(issue.cents)} · {issue.reason}</small></span>
            {roll && <a href={'/gudang/kain-kantong/?roll=' + encodeURIComponent(roll.id)}>Buka mutasi roll</a>}
            {issue.reversal ? <span>Dibalik · {issue.reversal}</span> : <button type="button" className="soft-btn" onClick={() => openReverse({ kind: 'issue', id: issue.id })}>Balikkan pemakaian</button>}
          </div>
        })}
      </details>
    </> : <section className="panel wh-pocket-use">
      <header className="pocket-panel-head">
        <div><h2>Bagi biaya ke HPP</h2><p>Biaya kain keluar dibagi per potong yang selesai dijahit dalam periode, termasuk hasil Afui.</p></div>
      </header>
      <form onSubmit={event => { event.preventDefault(); showAllocation() }}>
        <div className="wh-fields pocket-period-fields">
          <label>Mulai periode<input type="date" required value={start} max={end || lastWarehouseDay()} onChange={e => { setStart(e.target.value); setPreview(null); setFeedback(null) }}/></label>
          <label>Akhir periode<input type="date" required value={end} min={start} max={lastWarehouseDay()} onChange={e => { setEnd(e.target.value); setPreview(null); setFeedback(null) }}/></label>
          <label>Alasan pembagian<input value={allocReason} onChange={e => setAllocReason(e.target.value)}/></label>
        </div>
        <button className="soft-btn" type="submit">Lihat perhitungan</button>
      </form>
      {feedback && !undo && <p className="wh-feedback" role={feedback.error ? 'alert' : 'status'}>{feedback.text}</p>}
      {preview && <div className="gar-box pocket-allocation">
        <h3>{rupiah(preview.cents)} ÷ {preview.pcs} pcs = {amountText(preview.cents / 100 / preview.pcs)}/pcs</h3>
        <p>Sumber {preview.sources.join(', ')}</p>
        <div className="pocket-table-scroll" tabIndex={0} role="region" aria-label="Rincian alokasi HPP">
          <RecordTable><thead><tr><th>PO / mandor</th><th>Selesai dijahit</th><th>WIP</th><th>FG tersedia</th><th>HPP terjual</th></tr></thead>
            <tbody>{preview.parts.map(p => <tr key={p.po}><td>{p.mandor} <small className="record-code">{p.po}</small></td><td><strong className="pocket-quantity">{p.pcs} pcs</strong></td><td>{rupiah(p.wip)}</td><td>{rupiah(p.fg)}</td><td>{rupiah(p.sold)}</td></tr>)}</tbody>
          </RecordTable>
        </div>
        <button className="primary-btn" type="button" disabled={!allocReason.trim()} onClick={postAllocation}>Sahkan pembagian</button>
      </div>}
      <section className="pocket-history">
        <h3>Riwayat pembagian biaya</h3>
        {book.allocations.length === 0 && <p>Belum ada pembagian biaya.</p>}
        {[...book.allocations].reverse().map(a => <div className="wh-register-row" key={a.id}>
          <span><strong><span className="pocket-quantity">{a.pcs} pcs</span> · {rupiah(a.cents)}</strong><small>{a.start} – {a.end} · {a.id} · {a.reason}</small></span>
          {a.reversal ? <span>Dibatalkan · {a.reversal}</span> : <button type="button" className="soft-btn" onClick={() => openReverse({ kind: 'period', id: a.id })}>Batalkan pembagian</button>}
        </div>)}
      </section>
    </section>}
    {undo && <ReasonDialog title={'Pembalikan ' + undo.id} onClose={() => setUndo(null)} closeLabel="Kembali">
      <form className="pocket-dialog-form" onSubmit={reverse}>
        <p>{undo.kind === 'issue' ? 'Panjang yang keluar akan kembali ke saldo roll.' : 'Nilai kembali ke biaya periode dan saldo roll tetap.'}</p>
        <label>Alasan pembalikan<input required value={why} onChange={e => setWhy(e.target.value)}/></label>
        {feedback && <p role="alert">{feedback.text}</p>}
        <button className="primary-btn" disabled={!why.trim()} type="submit">Konfirmasi pembalikan</button>
      </form>
    </ReasonDialog>}
  </div>
}

function PocketUsageForm({ selection, book, onClose, onConfirm }: {
  selection: UsageSelection
  book: PocketBook
  onClose: () => void
  onConfirm: (date: string, reason: string, drafts: UsageDraft[], lines: UsageLine[]) => void
}) {
  const { rolls, whole } = selection
  const first = rolls[0]
  const minDay = rolls.map(r => r.date).sort().at(-1)!
  const [date, setDate] = useState(minDay > fixtureDate ? minDay : fixtureDate)
  const [reason, setReason] = useState('Pemakaian kain kantong')
  const [drafts, setDrafts] = useState<UsageDraft[]>(() => rolls.map(() => ({ mode: whole ? 'utuh' : 'keluar', amount: '' })))
  const [error, setError] = useState('')
  const [tried, setTried] = useState(false)
  const rows = rolls.map((roll, index) => {
    const draft = drafts[index]
    const left = pocketBalance(book, roll)
    let line: UsageLine | undefined
    let invalid = ''
    if (draft.mode === 'utuh' || draft.amount.trim() || tried) {
      try { line = planPocketUsage(book, [roll], date, reason, draft.mode, draft.amount)[0] }
      catch (failure) { invalid = (failure as Error).message }
    }
    return { roll, draft, left, line, invalid }
  })
  const lines = rows.flatMap(row => row.line ? [row.line] : [])
  const ready = lines.length === rolls.length

  function updateDraft(index: number, patch: Partial<UsageDraft>) {
    setDrafts(current => current.map((draft, i) => i === index ? { ...draft, ...patch } : draft))
    setError('')
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setTried(true)
    setError('')
    if (!ready) return
    try { onConfirm(date, reason, drafts, lines) }
    catch (failure) { setError((failure as Error).message) }
  }

  const title = whole ? `Pakai seluruh sisa · ${rolls.length} roll` : rolls.length > 1 ? `Atur pemakaian · ${rolls.length} roll` : 'Pakai ' + (first.sequence ? pocketRollLabel(first) : 'roll ' + first.id)
  return <ReasonDialog title={title} onClose={onClose} closeLabel="Kembali" className="pocket-usage-modal">
    <form className="pocket-dialog-form pocket-usage-form" onSubmit={submit} noValidate>
      <div className="wh-fields pocket-usage-meta">
        <label>Tanggal pemakaian<input type="date" required min={minDay} max={lastWarehouseDay()} value={date} onChange={e => { setDate(e.target.value); setError('') }}/></label>
        <label>Alasan pemakaian<input required value={reason} onChange={e => { setReason(e.target.value); setError('') }}/></label>
      </div>
      <section className="pocket-usage-workbench" aria-label="Panjang yang dipakai per roll">
        <h3>Panjang yang dipakai per roll</h3>
        <div className="pocket-usage-rows">
          {rows.map(({ roll, left, draft, line, invalid }, index) => <article key={roll.id} className="pocket-usage-row">
            <header className="wh-roll-id"><i><Ruler aria-hidden="true"/></i><div><strong>{roll.name}</strong><small className="record-code">{pocketRollLabel(roll)} · {roll.receipt} · {roll.location}</small></div></header>
            <div className="pocket-usage-before"><small>Sebelum</small><strong>{length(left, roll.unit)}</strong></div>
            {!whole ? <div className="wh-fields pocket-usage-inputs">
              <label>Cara mencatat<select value={draft.mode} onChange={e => updateDraft(index, { mode: e.target.value as UsageMode, amount: '' })}>
                <option value="keluar">Isi yang dipakai</option><option value="sisa">Isi sisa fisik</option><option value="utuh">Pakai semua sisa</option>
              </select></label>
              {draft.mode !== 'utuh' && <label>{(draft.mode === 'sisa' ? 'Sisa fisik' : 'Keluar') + ' (' + roll.unit + ')'}
                <input required inputMode="decimal" aria-invalid={Boolean(invalid)} placeholder="0" value={draft.amount} onChange={e => updateDraft(index, { amount: e.target.value })}/>
              </label>}
            </div> : <div className="pocket-usage-before"><small>Dipakai</small><strong>Seluruh sisa</strong></div>}
            <div className="pocket-usage-after"><small>Sisa setelah dipakai</small><strong>{line ? length(line.left, roll.unit) : '—'}</strong></div>
            {invalid && <p className="wh-feedback" role="alert">{invalid}</p>}
          </article>)}
        </div>
      </section>
      {error && <p className="wh-feedback" role="alert">{error}</p>}
      {ready && <div className="pocket-review" aria-label="Ringkasan pemakaian">
        {lines.map(({ roll, qty, left, cents }) => <div key={roll.id} className="wh-register-row">
          <span><strong className="pocket-quantity">Keluar {length(qty, roll.unit)}</strong><small>{pocketRollLabel(roll)} · Sisa gudang {length(left, roll.unit)}</small></span>
          <strong>{rupiah(cents)}</strong>
        </div>)}
        <div className="pocket-total"><span><small>Total keluar</small><strong>{sumLengths(lines, line => line.qty)}</strong></span>
          <span><small>Masuk biaya periode</small><strong>{rupiah(lines.reduce((sum, row) => sum + row.cents, 0))}</strong></span></div>
      </div>}
      <footer className="pocket-usage-actions">
        <button className="primary-btn" type="submit">{rolls.length > 1 ? 'Catat ' + rolls.length + ' roll keluar' : 'Catat pemakaian'} <ArrowRight size={16} aria-hidden="true"/></button>
      </footer>
    </form>
  </ReasonDialog>
}
