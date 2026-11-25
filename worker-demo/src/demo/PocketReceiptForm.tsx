import { useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowRight, ClipboardList, Plus, Trash2 } from 'lucide-react'
import { amountText, fixtureDate } from './accessoryPricing'
import { browseMatch } from '../browseMatch'
import { ReasonDialog } from './planner/ReasonDialog'
import {
  pocketBenchmark, readReceipts, receivePocket, reviewPocketReceipt, reverseReceipt, seedRolls,
  type PocketReceipt, type ReceiptDraft,
} from './pocketReceipts'
import { readPocketNumber } from './pocketUsage'
import { lastWarehouseDay } from './warehouseDay'
import './warehouseForms.css'
import './pocketFabric.css'

const draftKey = 'erp.demo.pocket.receipt-draft.v1'
const rollPath = '/gudang/kain-kantong/'
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
    setSaved(false)
  }

  const complete = draft.rolls.map(r => ({ id: r.number.trim(), length: readPocketNumber(r.qty) }))
    .filter(r => r.id && r.length > 0)
  const benchmark = pocketBenchmark(draft)
  const rate = draft.rate.trim() ? readPocketNumber(draft.rate) : benchmark
  const pricingKnown = rate !== null && Number.isFinite(rate)
  const receipts = rows.filter(r => browseMatch(historyQuery, r.number, r.supplier, r.day, ...r.rolls.flatMap(roll => [roll.id, roll.name])))
  const openingShown = browseMatch(historyQuery, 'SJ-KT-001', 'Saldo pembukaan', ...seedRolls.map(r => r.id))

  return <section className="procurement-layout pocket-receipt" aria-label="Penerimaan kain kantong">
    <form className="panel receipt-editor" onSubmit={review} noValidate>
      <header className="pocket-panel-head">
        <div><h1>Penerimaan kain kantong</h1><p>Isi satu surat jalan, lalu masukkan nomor dan panjang tiap roll.</p></div>
        <a className="soft-btn" href={rollPath}><ArrowLeft size={16} aria-hidden="true"/>Stok kain kantong</a>
      </header>
      {notice && <div className="wh-feedback" role="status">
        <strong>{notice}</strong>
        {posted?.rolls.length === 1 && <a href={link(posted.rolls[0].id)}>Lihat {posted.rolls[0].id} di stok</a>}
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

      <section className="pocket-receipt-block">
        <h3>Roll yang datang</h3>
        <div className="wh-roll-inputs">
          {draft.rolls.map((roll, i) => <div key={i}>
            <span className="roll-number" aria-hidden="true">{i + 1}</span>
            <label>Nomor roll<input aria-label={'Nomor roll ' + (i + 1)} placeholder="Kode pada roll" value={roll.number} onChange={e => editRoll(i, 'number', e.target.value)}/></label>
            <label>Panjang ({draft.unit})<input aria-label={'Panjang roll ' + (i + 1)} inputMode="decimal" placeholder={draft.unit === 'm' ? '12,5' : '100'} value={roll.qty} onChange={e => editRoll(i, 'qty', e.target.value)}/></label>
            <button type="button" className="remove-roll" aria-label={'Hapus roll ' + (i + 1)} disabled={draft.rolls.length === 1}
              onClick={() => patch({ rolls: draft.rolls.filter((_, j) => j !== i) })}><Trash2 size={16}/></button>
          </div>)}
        </div>
        <button type="button" className="soft-btn" onClick={() => patch({ rolls: [...draft.rolls, newRoll()] })}><Plus size={16}/>Tambah roll</button>
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
        <div><span>Panjang masuk</span><strong>{fmt(complete.reduce((sum, r) => sum + r.length, 0))} {draft.unit}</strong></div>
        <div><span>Nilai sementara</span><strong>{complete.length && pricingKnown ? amountText(complete.reduce((sum, r) => sum + Math.round(r.length * rate * 100), 0) / 100) : '—'}</strong></div>
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
          <span><strong className="pocket-quantity">{fmt(roll.length)} {roll.unit}</strong><small className="record-code">{roll.id}</small></span>
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
            <span><strong className="pocket-quantity">{fmt(r.length)} {r.unit} masuk</strong><small className="record-code">{r.id}</small></span><strong>{amountText(Math.round(r.length * r.rate * 100) / 100)}</strong>
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
