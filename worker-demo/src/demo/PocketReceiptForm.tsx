import { useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowRight, ClipboardList, Plus } from 'lucide-react'
import { amountText, fixtureDate } from './accessoryPricing'
import { browseMatch } from '../browseMatch'
import { ReasonDialog } from './planner/ReasonDialog'
import { ReceiptRollRows } from './ReceiptRollRows'
import {
  pocketBenchmark, pocketRollLabel, readReceipts, receivePocket, reviewPocketReceipt, reverseReceipt, seedRolls,
  type PocketReceipt, type ReceiptDraft,
} from './pocketReceipts'
import { readPocketNumber } from './pocketUsage'
import { lastWarehouseDay } from './warehouseDay'
import './warehouseForms.css'
import './pocketFabric.css'

const draftKey = 'erp.demo.pocket.receipt-draft.v1'
const rollPath = '/gudang/kain-kantong/'
const maxGeneratedRows = 999
const newRoll = () => ({ number: '', qty: '' })
const fresh = (): ReceiptDraft => ({
  request: crypto.randomUUID(), number: '', supplier: '', location: 'Gudang Bahan', material: '',
  day: fixtureDate, unit: 'yd', rate: '', reason: 'Penerimaan sesuai surat jalan', notes: '', rolls: [newRoll()],
})
const fmt = (n: number) => n.toLocaleString('id-ID', { maximumFractionDigits: 6 })
const link = (id: string) => rollPath + '?roll=' + encodeURIComponent(id)
const rateText = (value: number, unit: string) => amountText(value) + '/' + unit

export default function PocketReceiptForm() {
  const [saved, setSaved] = useState(() => sessionStorage.getItem(draftKey) !== null)
  const [draft, setDraft] = useState<ReceiptDraft>(() => JSON.parse(sessionStorage.getItem(draftKey) ?? 'null') ?? fresh())
  const [rollCountInput, setRollCountInput] = useState<string | null>(null)
  const [rollCountError, setRollCountError] = useState('')
  const [rows, setRows] = useState(readReceipts)
  const [expanded, setExpanded] = useState(() => new URLSearchParams(location.search).get('surat'))
  const [historyQuery, setHistoryQuery] = useState('')
  const [preview, setPreview] = useState<PocketReceipt | null>(null)
  const [posted, setPosted] = useState<PocketReceipt | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [undo, setUndo] = useState('')
  const [why, setWhy] = useState('')
  const [deleting, setDeleting] = useState(false)

  function patch(change: Partial<ReceiptDraft>) {
    setDraft(d => ({ ...d, ...change }))
    setError('')
    setNotice('')
    setPosted(null)
  }

  function editRoll(index: number, field: 'number' | 'qty', value: string) {
    patch({ rolls: draft.rolls.map((roll, i) => i === index ? { ...roll, [field]: value } : roll) })
  }

  function setRollRows(rolls: ReceiptDraft['rolls']) {
    patch({ rolls })
    setRollCountInput(null)
    setRollCountError('')
  }

  function applyRollCount() {
    const count = Number(rollCountInput ?? draft.rolls.length)
    if (!Number.isSafeInteger(count) || count < 1 || count > maxGeneratedRows) {
      setRollCountError(`Isi jumlah antara 1 dan ${maxGeneratedRows} untuk membuat baris roll.`)
      return
    }
    if (draft.rolls.slice(count).some(roll => roll.qty.trim() || roll.number.trim())) {
      setRollCountError('Ada roll yang sudah terisi di baris akhir. Hapus roll itu satu per satu jika memang perlu.')
      return
    }
    setRollRows(Array.from({ length: count }, (_, index) => draft.rolls[index] ?? newRoll()))
  }

  function review(event: FormEvent) {
    event.preventDefault()
    setError('')
    setNotice('')
    try { setPreview(reviewPocketReceipt(draft)) }
    catch (failure) { setError((failure as Error).message) }
  }

  function post() {
    try {
      const receipt = receivePocket(draft)
      setRows(readReceipts())
      setPosted(receipt)
      setExpanded(receipt.number)
      removeDraft()
      setPreview(null)
      setNotice('Penerimaan ' + receipt.number + ' disahkan. ' + receipt.rolls.length + ' roll masuk gudang.')
    } catch (failure) {
      setError((failure as Error).message)
    }
  }

  function removeDraft() {
    sessionStorage.removeItem(draftKey)
    setDraft(fresh())
    setRollCountInput(null)
    setRollCountError('')
    setSaved(false)
  }

  const complete = draft.rolls.map(r => readPocketNumber(r.qty)).filter(length => length > 0)
  const benchmark = pocketBenchmark(draft)
  const rate = draft.rate.trim() ? readPocketNumber(draft.rate) : benchmark
  const pricingKnown = rate !== null && Number.isFinite(rate)
  const receipts = rows.filter(r => browseMatch(historyQuery, r.number, r.supplier, r.day, ...r.rolls.flatMap(roll => [roll.id, roll.name, pocketRollLabel(roll)])))
  const openingShown = browseMatch(historyQuery, 'SJ-KT-001', 'Saldo pembukaan', ...seedRolls.map(r => r.id))

  return <section className="procurement-layout pocket-receipt" aria-label="Penerimaan kain kantong">
    <form className="panel receipt-editor" onSubmit={review} noValidate>
      <header className="pocket-panel-head">
        <div><h1>Penerimaan kain kantong</h1><p>Isi surat jalan, tentukan jumlah roll, lalu ketik panjangnya.</p></div>
        <a className="soft-btn" href={rollPath}><ArrowLeft size={16} aria-hidden="true"/>Stok kain kantong</a>
      </header>
      {notice && <div className="wh-feedback" role="status">
        <strong>{notice}</strong>
        {posted?.rolls.length === 1 && <a href={link(posted.rolls[0].id)}>Lihat {pocketRollLabel(posted.rolls[0])} di stok</a>}
        {posted && posted.rolls.length > 1 && <a href={rollPath + '?surat=' + encodeURIComponent(posted.number)}>Lihat roll yang baru masuk</a>}
      </div>}

      <section className="pocket-receipt-block">
        <h3>Surat jalan</h3>
        <div className="wh-fields">
          <label>Nomor surat jalan<input required value={draft.number} placeholder="Contoh SJ-KT-012" onChange={e => patch({ number: e.target.value })}/></label>
          <label>Tanggal barang datang<input type="date" required max={lastWarehouseDay()} value={draft.day} onChange={e => patch({ day: e.target.value })}/></label>
          <label>Supplier penerimaan<select required value={draft.supplier} onChange={e => patch({ supplier: e.target.value })}>
            <option value="">Pilih supplier</option>
            {['Sinaran','Malibu','Mitra Tekstil'].map(name => <option key={name}>{name}</option>)}
          </select></label>
          <label>Gudang penerimaan<select value={draft.location} onChange={e => patch({ location: e.target.value })}>
            {['Gudang Bahan','Gudang Bahan Cadangan'].map(name => <option key={name}>{name}</option>)}
          </select></label>
          <label>Nama kain kantong<select required value={draft.material} onChange={e => patch({ material: e.target.value })}>
            <option value="">Pilih kain</option><option>Kain kantong putih</option><option>Kain kantong hitam</option>
          </select></label>
          <label>Satuan surat jalan<select value={draft.unit} onChange={e => patch({ unit: e.target.value as ReceiptDraft['unit'], rate: '' })}>
            <option value="yd">Yard (yd)</option><option value="m">Meter (m)</option>
          </select></label>
        </div>
      </section>

      <section className="pocket-receipt-block pocket-roll-entry" aria-labelledby="pocket-roll-title">
        <div className="roll-entry-head"><h3 id="pocket-roll-title">Rincian gulung</h3>
          <button type="button" className="soft-btn add-roll" onClick={() => setRollRows([...draft.rolls, newRoll()])}><Plus size={16} aria-hidden="true"/>Tambah roll</button>
        </div>
        <div className="pocket-roll-count">
          <label>Jumlah roll<input className="erp-input" inputMode="numeric" enterKeyHint="done" value={rollCountInput ?? draft.rolls.length}
            aria-invalid={Boolean(rollCountError)} aria-describedby={rollCountError ? 'pocket-roll-count-feedback' : undefined}
            onChange={e => { setRollCountInput(e.target.value.replace(/[^0-9]/g, '')); setRollCountError('') }}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); applyRollCount() } }}/></label>
          <button type="button" className="soft-btn" onClick={applyRollCount}>Buat baris</button>
        </div>
        {rollCountError && <p className="wh-feedback" id="pocket-roll-count-feedback" role="alert">{rollCountError}</p>}
        <ReceiptRollRows rows={draft.rolls.map((roll, index) => ({ key: index, length: roll.qty }))} unit={draft.unit} byNumber readLength={readPocketNumber}
          onChange={(index, value) => editRoll(index, 'qty', value)} onRemove={index => setRollRows(draft.rolls.filter((_, i) => i !== index))}/>
        <details className="pocket-supplier-rolls" open={draft.rolls.some(roll => roll.number.trim()) || undefined}>
          <summary>Kode roll dari supplier (opsional)</summary>
          <div className="wh-fields">{draft.rolls.map((roll, index) => <label key={index}>Roll {String(index + 1).padStart(2, '0')}
            <input aria-label={'Nomor roll ' + (index + 1)} placeholder="Kode pada roll" value={roll.number} onChange={e => editRoll(index, 'number', e.target.value)}/>
          </label>)}</div>
        </details>
      </section>

      <section className="pocket-receipt-block">
        <h3>Nilai penerimaan</h3>
        <div className="wh-fields">
          <label>Harga sementara per {draft.unit} (Rp)
            <input aria-label="Harga sementara per satuan" aria-describedby="pocket-rate-help" inputMode="decimal"
              placeholder={benchmark === null ? 'Isi harga per ' + draft.unit : fmt(benchmark)} value={draft.rate} onChange={e => patch({ rate: e.target.value })}/>
            <small id="pocket-rate-help">{benchmark === null ? 'Isi harga jika tarif acuan belum tersedia.' : 'Jika kosong, pakai acuan ' + rateText(benchmark, draft.unit) + '.'}</small>
          </label>
          <label>Alasan penerimaan<input required value={draft.reason} onChange={e => patch({ reason: e.target.value })}/></label>
          <label>Catatan (opsional)<input value={draft.notes} onChange={e => patch({ notes: e.target.value })}/></label>
        </div>
      </section>

      <div className="pocket-receipt-totals" aria-label="Ringkasan penerimaan">
        <div><span>Roll terisi</span><strong>{complete.length} roll</strong></div>
        <div><span>Panjang masuk</span><strong>{fmt(complete.reduce((sum, length) => sum + length, 0))} {draft.unit}</strong></div>
        <div><span>Nilai sementara</span><strong>{complete.length && pricingKnown ? amountText(complete.reduce((sum, length) => sum + Math.round(length * rate * 100), 0) / 100) : '—'}</strong></div>
      </div>
      {error && !preview && !undo && <p className="wh-feedback" role="alert">{error}</p>}
      <footer className="receipt-actions">
        <button type="button" className="soft-btn" onClick={() => {
          sessionStorage.setItem(draftKey, JSON.stringify(draft))
          setSaved(true); setError(''); setPosted(null); setNotice('Draft penerimaan tersimpan.')
        }}>Simpan draft</button>
        {saved && <button type="button" className="soft-btn" onClick={() => setDeleting(true)}>Hapus draft</button>}
        <button className="primary-btn" type="submit">Review penerimaan <ArrowRight size={16}/></button>
      </footer>
    </form>

    <aside className="panel wh-receipt-register">
      <header className="pocket-panel-head"><h2>Riwayat penerimaan</h2><ClipboardList size={19} aria-hidden="true"/></header>
      <label className="pocket-search">Cari penerimaan<input type="search" placeholder="Surat jalan, supplier, atau roll" value={historyQuery} onChange={e => setHistoryQuery(e.target.value)}/></label>
      {receipts.map(r => <details key={r.number} open={expanded === r.number || undefined}>
        <summary><strong className="pocket-quantity">{r.rolls.length} roll · {fmt(r.rolls.reduce((total, roll) => total + roll.length, 0))} {r.rolls[0].unit}</strong>
          <small className="record-code">{r.number} · {r.day} · {r.supplier} · {r.reversal ? 'Dibalik' : 'Diterima'}</small></summary>
        <p>{r.rolls[0].location} · {r.rolls[0].name}</p>
        {r.rolls.map(roll => <div className="wh-register-row" key={roll.id}>
          <span><strong className="pocket-quantity">{fmt(roll.length)} {roll.unit}</strong><small className="record-code">{pocketRollLabel(roll)}</small></span>
          {!r.reversal && <a href={link(roll.id)}>Buka roll</a>}
        </div>)}
        {r.reversal ? <small>Alasan pembalikan · {r.reversal.reason}</small> :
          <button type="button" className="soft-btn" onClick={() => { setUndo(r.number); setWhy(''); setError('') }}>Balikkan penerimaan</button>}
      </details>)}
      {openingShown && <details open={expanded === 'SJ-KT-001' || undefined}>
        <summary><strong className="pocket-quantity">{seedRolls.length} roll · Saldo pembukaan</strong><small className="record-code">SJ-KT-001 · 20 Nov 2026</small></summary>
        {seedRolls.map(roll => <div className="wh-register-row" key={roll.id}>
          <span><strong className="pocket-quantity">{fmt(roll.length)} {roll.unit}</strong><small className="record-code">{roll.id}</small></span><a href={link(roll.id)}>Buka roll</a>
        </div>)}
      </details>}
      {!openingShown && !receipts.length && <p>Surat jalan atau roll tidak ditemukan.</p>}
    </aside>

    {preview && <ReasonDialog title={'Terima ' + preview.number} closeLabel="Kembali" onClose={() => { setPreview(null); setError('') }}>
      <div className="pocket-dialog-form">
        <p><strong>{preview.supplier} · {preview.rolls[0].location}</strong><br/>{preview.rolls[0].name} · {preview.day} · {rateText(preview.rolls[0].rate, preview.rolls[0].unit)}</p>
        <div className="pocket-review">
          {preview.rolls.map(r => <div className="wh-register-row" key={r.id}>
            <span><strong className="pocket-quantity">{fmt(r.length)} {r.unit} masuk</strong><small className="record-code">{pocketRollLabel(r)}</small></span><strong>{amountText(Math.round(r.length * r.rate * 100) / 100)}</strong>
          </div>)}
          <div className="pocket-total">
            <strong className="pocket-quantity">{preview.rolls.length} roll · {fmt(preview.rolls.reduce((sum, r) => sum + r.length, 0))} {preview.rolls[0].unit}</strong>
            <strong>{amountText(preview.rolls.reduce((sum, r) => sum + Math.round(r.length * r.rate * 100), 0) / 100)}</strong>
          </div>
        </div>
        {error && <p role="alert">{error}</p>}
        <button type="button" className="primary-btn" onClick={post}>Sahkan penerimaan</button>
      </div>
    </ReasonDialog>}

    {deleting && <ReasonDialog title="Hapus draft penerimaan?" closeLabel="Kembali" onClose={() => setDeleting(false)}>
      <button type="button" className="soft-btn" onClick={() => {
        removeDraft(); setDeleting(false); setError(''); setPosted(null); setNotice('Draft dihapus.')
      }}>Ya, hapus draft</button>
    </ReasonDialog>}

    {undo && <ReasonDialog title={'Balikkan ' + undo} closeLabel="Kembali" onClose={() => { setUndo(''); setError('') }}>
      <form className="pocket-dialog-form" onSubmit={event => {
        event.preventDefault()
        try { reverseReceipt(undo, why); setRows(readReceipts()); setUndo(''); setPosted(null); setNotice('Penerimaan ' + undo + ' dibalik.') }
        catch (failure) { setError((failure as Error).message) }
      }}>
        <p>Roll dari surat jalan ini dikeluarkan dari saldo penerimaan. Riwayat surat jalan tetap tampil.</p>
        <label>Alasan pembalikan<input required value={why} onChange={e => setWhy(e.target.value)}/></label>
        {error && <p role="alert">{error}</p>}
        <button type="submit" className="primary-btn" disabled={!why.trim()}>Konfirmasi pembalikan</button>
      </form>
    </ReasonDialog>}
  </section>
}
