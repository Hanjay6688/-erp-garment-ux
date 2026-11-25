import { useState, type FormEvent } from 'react'
import { ArrowDownLeft, ClipboardList, Scissors } from 'lucide-react'
import { browseMatch } from '../browseMatch'
import RecordTable from '../RecordTable'
import { amountText, fixtureDate } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { pocketRolls, readReceipts, receiptPath, type PocketRoll } from './pocketReceipts'
import {
  periodActive, planPocketAllocation, planPocketUsage, pocketBalance, pocketBookKey,
  pocketScale, readPocketBook, type PocketAllocation, type PocketBook,
} from './pocketUsage'
import { lastWarehouseDay } from './warehouseDay'
import './warehouseForms.css'
import './pocketFabric.css'

const length = (qty: number, unit: string) => (qty / pocketScale).toLocaleString('id-ID', { maximumFractionDigits: 6 }) + ' ' + unit
const rupiah = (cents: number) => amountText(cents / 100)

type UsageSelection = { rolls: PocketRoll[]; whole: boolean }
type Reverse = { id: string; kind: 'issue' | 'period' }
type Feedback = { text: string; error?: boolean }

export default function PocketFabric() {
  const rolls = pocketRolls()
  const [detailId, setDetailId] = useState(() => new URLSearchParams(location.search).get('roll'))
  const [book, setBook] = useState(readPocketBook)
  const [tab, setTab] = useState<'stock' | 'cost'>('stock')
  const [query, setQuery] = useState(() => new URLSearchParams(location.search).get('surat') ?? '')
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
  const visible = rolls.filter(r => browseMatch(query, r.id, r.name, r.receipt, r.location, r.unit, r.date))

  function save(next: PocketBook, message: string) {
    sessionStorage.setItem(pocketBookKey, JSON.stringify(next))
    setBook(next)
    setPreview(null)
    setFeedback({ text: message })
  }

  function confirmUsage(current: PocketBook, form: UsageSelection, date: string, reason: string, mode: 'keluar' | 'sisa' | 'utuh', amount: string) {
    const liveRolls = pocketRolls()
    const selected = liveRolls.filter(r => form.rolls.some(item => item.id === r.id))
    if (selected.length !== form.rolls.length) throw Error('Ada roll yang sudah tidak tersedia. Tutup dan pilih ulang roll.')
    const lines = planPocketUsage(current, selected, date, reason, mode, amount)
    const shown = planPocketUsage(book, form.rolls, date, reason, mode, amount)
    if (JSON.stringify(lines) !== JSON.stringify(shown)) throw Error('Saldo roll berubah. Tutup dan periksa kembali.')
    const issues = lines.map(({ roll, qty, cents }, index) => ({
      id: 'KT-' + String(current.issues.length + index + 1).padStart(3, '0') + '-OUT',
      roll: roll.id, unit: roll.unit, date, qty, cents, reason: reason.trim(),
    }))
    const message = form.whole ? lines.length + ' roll dikeluarkan.' : length(lines[0].qty, lines[0].roll.unit) + ' keluar dari ' + lines[0].roll.id + '.'
    save({ ...current, issues: [...current.issues, ...issues] }, message)
    setChecked(ids => ids.filter(id => !issues.some(issue => issue.roll === id)))
    setDetailId(form.whole ? null : lines[0].roll.id)
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
    <header className="hero-copy compact pocket-heading">
      <div><h1>Kain kantong</h1><p>Terima kain dan catat pemakaian sesuai panjang setiap roll.</p></div>
      <a className="primary-btn" href={receiptPath}><ArrowDownLeft size={17} aria-hidden="true"/>Terima kain kantong</a>
    </header>
    <nav className="pocket-navigation" aria-label="Kain kantong">
      <button type="button" aria-current={tab === 'stock'} onClick={() => switchTab('stock')}>Stok &amp; pemakaian</button>
      <button type="button" aria-current={tab === 'cost'} onClick={() => switchTab('cost')}>Biaya per periode</button>
    </nav>
    {tab === 'stock' ? <section className="panel wh-pocket-use">
      <header className="pocket-panel-head">
        <div><h2>Stok per roll</h2><p>{rolls.filter(r => pocketBalance(book, r) > 0).length} roll bersaldo di gudang</p></div>
        <label className="pocket-search"><span>Cari roll</span>
          <input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Nomor roll atau surat jalan"/>
        </label>
      </header>
      <ul className="pocket-stock-list" aria-label="Stok per roll">
        {visible.map(roll => {
          const left = pocketBalance(book, roll)
          const incoming = Math.round(roll.length * pocketScale)
          return <li key={roll.id} className="pocket-stock-row">
            <label className="pocket-check" title="Pilih untuk memakai seluruh sisa">
              <input type="checkbox" aria-label={'Pakai seluruh ' + roll.id} disabled={left <= 0} checked={checked.includes(roll.id)}
                onChange={e => setChecked(ids => e.target.checked ? [...ids, roll.id] : ids.filter(id => id !== roll.id))}/>
            </label>
            <div className="pocket-stock-id">
              <button type="button" className="gar-text" aria-expanded={detailId === roll.id}
                onClick={() => setDetailId(detailId === roll.id ? null : roll.id)}>{roll.id}</button>
              <small>{roll.name}</small><small>{roll.location} · {roll.receipt}</small>
            </div>
            <dl className="pocket-stock-metrics">
              <div><dt>Masuk</dt><dd>{length(incoming, roll.unit)}</dd></div>
              <div><dt>Terpakai</dt><dd>{length(incoming - left, roll.unit)}</dd></div>
              <div className={left ? 'pocket-in-stock' : ''}><dt>Sisa</dt><dd className="pocket-quantity">{length(left, roll.unit)}</dd></div>
            </dl>
            <button type="button" className="soft-btn pocket-use-button" aria-label={'Catat pemakaian ' + roll.id} disabled={left <= 0}
              onClick={() => openUsage({ rolls: [roll], whole: false })}><Scissors size={15} aria-hidden="true"/>Pakai roll</button>
          </li>
        })}
      </ul>
      {visible.length === 0 && <p className="pocket-empty">Tidak ada roll yang cocok dengan pencarian.</p>}
      {rolls.length > 0 && <div className="pocket-bulk">
        <p>{checked.length ? checked.join(', ') : 'Centang roll untuk memakai seluruh sisanya sekaligus.'}</p>
        <button type="button" className="soft-btn" disabled={!checked.length}
          onClick={() => openUsage({ rolls: rolls.filter(r => checked.includes(r.id)), whole: true })}>
          Pakai seluruh sisa{checked.length ? ' · ' + checked.length + ' roll' : ''}
        </button>
      </div>}
      {feedback && !undo && <p className="wh-feedback" role={feedback.error ? 'alert' : 'status'}>{feedback.text}</p>}
      {detail && <section className="wh-roll-ledger" aria-label={'Mutasi roll ' + detail.id}>
        <h3>Mutasi roll · {detail.id}</h3>
        <div className="wh-register-row">
          <span><strong>Masuk · {length(Math.round(detail.length * pocketScale), detail.unit)}</strong><small>{detail.date} · {detail.receipt}</small></span>
          <a href={receiptPath + '&surat=' + encodeURIComponent(detail.receipt)}>Lihat penerimaan</a>
        </div>
        {book.issues.filter(i => i.roll === detail.id).map(issue => <div className="wh-register-row" key={issue.id}>
          <span><strong>Keluar · {length(issue.qty, detail.unit)}</strong><small>{issue.date} · {issue.id} · {rupiah(issue.cents)}</small></span>
          {issue.reversal ? <span>Dibalik · {issue.reversal}</span> : <button type="button" className="soft-btn" onClick={() => openReverse({ kind: 'issue', id: issue.id })}>Balikkan {issue.id}</button>}
        </div>)}
      </section>}
      <details className="pocket-history">
        <summary><ClipboardList size={16} aria-hidden="true"/>Riwayat pemakaian <span>{book.issues.length}</span></summary>
        {book.issues.length === 0 && <p>Belum ada pemakaian.</p>}
        {[...book.issues].reverse().map(issue => {
          const unit = issue.unit ?? rolls.find(r => r.id === issue.roll)?.unit
            ?? readReceipts().flatMap(r => r.rolls).find(r => r.id === issue.roll)?.unit ?? 'yd'
          return <div className="wh-register-row" key={issue.id}>
            <span><strong className="pocket-quantity">{length(issue.qty, unit)} keluar</strong><small>{issue.roll} · {issue.date} · {issue.id} · {rupiah(issue.cents)} · {issue.reason}</small></span>
            {issue.reversal ? <span>Dibalik · {issue.reversal}</span> : <button type="button" className="soft-btn" onClick={() => openReverse({ kind: 'issue', id: issue.id })}>Balikkan pemakaian</button>}
          </div>
        })}
      </details>
    </section> : <section className="panel wh-pocket-use">
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
    {usage && <PocketUsageForm selection={usage} book={book} onClose={() => setUsage(null)}
      onConfirm={(date, reason, mode, amount) => confirmUsage(readPocketBook(), usage, date, reason, mode, amount)}/>}
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
  onConfirm: (date: string, reason: string, mode: 'keluar' | 'sisa' | 'utuh', amount: string) => void
}) {
  const { rolls, whole } = selection
  const first = rolls[0]
  const minDay = rolls.map(r => r.date).sort().at(-1)!
  const [date, setDate] = useState(minDay > fixtureDate ? minDay : fixtureDate)
  const [reason, setReason] = useState('Pemakaian kain kantong')
  const [mode, setMode] = useState<'keluar' | 'sisa'>('keluar')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')
  const [tried, setTried] = useState(false)
  const action = whole ? 'utuh' : mode
  let lines: ReturnType<typeof planPocketUsage> = []
  let invalid = ''
  if (whole || amount.trim() || tried) {
    try { lines = planPocketUsage(book, rolls, date, reason, action, amount) }
    catch (failure) { invalid = (failure as Error).message }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setTried(true)
    setError('')
    if (!lines.length) return
    try { onConfirm(date, reason, action, amount) }
    catch (failure) { setError((failure as Error).message) }
  }

  return <ReasonDialog title={whole ? 'Pakai seluruh sisa · ' + rolls.length + ' roll' : 'Pakai roll ' + first.id}
    onClose={onClose} closeLabel="Kembali">
    <form className="pocket-dialog-form" onSubmit={submit}>
      {whole ? <p>Seluruh sisa dari roll terpilih dicatat sebagai kain keluar.</p> : <p>{first.name} · {first.location} <br/>Sisa saat ini <strong>{length(pocketBalance(book, first), first.unit)}</strong></p>}
      <div className="wh-fields">
        <label>Tanggal pemakaian<input type="date" required min={minDay} max={lastWarehouseDay()} value={date} onChange={e => { setDate(e.target.value); setError('') }}/></label>
        <label>Alasan pemakaian<input required value={reason} onChange={e => { setReason(e.target.value); setError('') }}/></label>
        {!whole && <>
          <label>Cara mencatat<select value={mode} onChange={e => { setMode(e.target.value as typeof mode); setAmount(''); setTried(false); setError('') }}>
            <option value="keluar">Isi panjang yang dipakai</option><option value="sisa">Isi sisa setelah dipakai</option>
          </select></label>
          <label>{(mode === 'sisa' ? 'Sisa fisik' : 'Keluar') + ' (' + first.unit + ')'}
            <input required inputMode="decimal" placeholder={first.unit === 'm' ? 'Contoh 3,5' : 'Contoh 10'} value={amount} onChange={e => { setAmount(e.target.value); setError('') }}/>
          </label>
        </>}
      </div>
      {(error || invalid) && <p className="wh-feedback" role="alert">{error || invalid}</p>}
      {lines.length > 0 && <div className="pocket-review">
        {lines.map(({ roll, qty, left, cents }) => <div key={roll.id} className="wh-register-row">
          <span><strong className="pocket-quantity">Keluar {length(qty, roll.unit)}</strong><small>{roll.id} · Sisa gudang {length(left, roll.unit)}</small></span>
          <strong>{rupiah(cents)}</strong>
        </div>)}
        <div className="pocket-total"><span>Masuk biaya periode</span><strong>{rupiah(lines.reduce((sum, row) => sum + row.cents, 0))}</strong></div>
      </div>}
      <button className="primary-btn" type="submit" disabled={whole && !lines.length}>
        {whole ? 'Catat ' + rolls.length + ' roll keluar' : 'Catat pemakaian'}
      </button>
    </form>
  </ReasonDialog>
}
