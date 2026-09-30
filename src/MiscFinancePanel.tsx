import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import type { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { formatReceiptDecimal } from './procurementContract'
import { miscAmount, miscCents, parseMiscRead, parseMiscOutcome, type MiscType, type MiscCategory, type MiscCash, type MiscQuery, type MiscRead, type MiscOutcome } from './miscFinanceContract'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'

type Props = { client: ReturnType<typeof getUatSupabaseClient>; onChanged: () => Promise<boolean>; onRetire: () => void }
const money = (n: string) => 'Rp' + formatReceiptDecimal(n)
const emptyQuery = (): MiscQuery => ({ q: '', status: null, transaction_id: null, offset: 0, category_offset: 0, cash_offset: 0 })
const typeLabel = { OTHER_INCOME: 'Pendapatan lain', OTHER_EXPENSE: 'Biaya lain' }
const statusLabel = { DRAFT: 'Draft', POSTED: 'Tercatat', REVERSED: 'Sudah dibalik' }
export default function MiscFinancePanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !['OWNER', 'ADMIN'].includes(identity.profile.role) || !identity.permissions.includes('finance.journal.view') || !identity.permissions.includes('finance.cash.view')) return <p role="alert">Transaksi lain tersedia untuk Owner atau Admin dengan hak melihat jurnal dan kas.</p>
  return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} {...props}/>
}
function Workspace({ client, onChanged, onRetire }: Props) {
  const mutation = useProductionMutation('FINANCE_MISC'), { beginRead, finishRead, isReadCurrent, run, reconcile, invalidate } = mutation
  const query = useRef(emptyQuery())
  const [data, setData] = useState<MiscRead | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [q, setQ] = useState(''), [status, setStatus] = useState<MiscQuery['status']>(null), [outcome, setOutcome] = useState<MiscOutcome | null>(null)
  const [formOpen, setFormOpen] = useState(false), [editing, setEditing] = useState<string | null>(null)
  const [number, setNumber] = useState(''), [type, setType] = useState<MiscType>('OTHER_EXPENSE'), [category, setCategory] = useState<MiscCategory | null>(null), [bank, setBank] = useState<MiscCash | null>(null)
  const [at, setAt] = useState(() => cp6WibDateTimeInput()), [amount, setAmount] = useState(''), [counterparty, setCounterparty] = useState(''), [reference, setReference] = useState(''), [notes, setNotes] = useState('')
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false), [actionReason, setActionReason] = useState(''), [actionReviewed, setActionReviewed] = useState(false)
  const load = useCallback(async () => {
    const scope = { ...query.current }, ticket = beginRead()
    setData(null); setBusy(true); setError(''); setReviewed(false); setActionReviewed(false)
    try {
      const r = await client.rpc('erp_cp7_get_misc_finance_v1', { p_query: scope })
      if (!isReadCurrent(ticket)) return false
      if (r.error) throw r.error
      const parsed = parseMiscRead(r.data, scope)
      if (!finishRead(ticket)) return false
      setData(parsed)
      setCategory(current => current ? parsed.categories.rows.find(c => c.id === current.id && c.review_token === current.review_token) ?? (parsed.detail?.category_source?.id === current.id && parsed.detail.category_source.review_token === current.review_token && parsed.detail.category_source.eligible ? parsed.detail.category_source : null) : null)
      setBank(current => current ? parsed.cash_accounts.rows.find(c => c.id === current.id && c.review_token === current.review_token) ?? (parsed.detail?.cash_source?.id === current.id && parsed.detail.cash_source.review_token === current.review_token && parsed.detail.cash_source.eligible ? parsed.detail.cash_source : null) : null)
      return true
    } catch (e) { if (isReadCurrent(ticket)) setError(normalizeClientError(e).message); return false }
    finally { if (isReadCurrent(ticket)) setBusy(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load])
  const pendingBlocked = Boolean(mutation.pending) || mutation.externalMutationBlocked || mutation.corruptedEnvelope
  useEffect(() => { if (pendingBlocked) { beginRead(); setData(null); setReviewed(false); setActionReviewed(false); setBusy(false) } }, [pendingBlocked, beginRead])
  const retire = () => { setData(null); setReviewed(false); setActionReviewed(false); invalidate(); onRetire() }
  const handlers: ProductionMutationHandlers = {
    send: e => { retire(); return client.rpc('erp_cp7_save_misc_finance_v1', { p_action: e.action, p_payload: e.payload, p_request: e.id, p_expected: null }) },
    validate: (v, e) => { parseMiscOutcome(v, e.id, e.action, e.payload) },
    retire: (v, e) => {
      const committed = parseMiscOutcome(v, e.id, e.action, e.payload)
      setOutcome(committed); setData(null); setFormOpen(false); setEditing(null); setCategory(null); setBank(null); setAmount(''); setNumber(''); setReason(''); setActionReason(''); setReviewed(false); setActionReviewed(false)
      query.current = { ...query.current, q: '', status: null, offset: 0, transaction_id: committed.transaction_id }; setQ(''); setStatus(null)
    },
    reload: async () => { const native = await load(); const book = await onChanged(); return native && book },
  }
  const locked = busy || mutation.writerLocked, detail = data?.detail
  const physical = cp6WibPhysicalTimeToIso(at), exact = miscAmount(amount)
  const amountValid = exact !== null && miscCents(exact) > 0n
  const valid = !locked && reviewed && number.trim().length > 0 && number.trim().length <= 60 && physical !== null && Date.parse(physical) <= Date.now() && amountValid && category?.eligible && category.type === type && bank?.eligible && reason.trim().length >= 5 && reason.trim().length <= 1000 && (!editing || detail?.id === editing && detail.status === 'DRAFT')
  const save = () => {
    if (!valid || !category || !bank || !exact || !physical) return
    void run('SAVE', { transaction_id: editing, review_token: editing ? detail!.review_token : null, transaction_number: number.trim(), transaction_type: type, category_id: category.id, category_review_token: category.review_token, cash_account_id: bank.id, cash_review_token: bank.review_token, physical_at: physical, amount: exact, counterparty_name: counterparty.trim() || null, reference_number: reference.trim() || null, notes: notes.trim() || null, change_reason: reason.trim() }, null, handlers)
  }
  const action = (name: 'POST' | 'REVERSE') => {
    if (locked || !detail || !actionReviewed || actionReason.trim().length < 5 || actionReason.trim().length > 1000 || (name === 'POST' ? detail.status !== 'DRAFT' || !detail.category_eligible || !detail.cash_eligible : detail.status !== 'POSTED')) return
    void run(name, { transaction_id: detail.id, review_token: detail.review_token, change_reason: actionReason.trim() }, null, handlers)
  }
  const openForm = (edit: boolean) => {
    if (locked || edit && (!detail || detail.status !== 'DRAFT')) return
    setEditing(edit ? detail!.id : null); setNumber(edit ? detail!.number : ''); setType(edit ? detail!.type : 'OTHER_EXPENSE')
    setCategory(edit && detail!.category_source?.eligible ? detail!.category_source : null); setBank(edit && detail!.cash_source?.eligible ? detail!.cash_source : null)
    setAt(edit ? cp6WibDateTimeInput(detail!.physical_at) : cp6WibDateTimeInput()); setAmount(edit ? detail!.amount : ''); setCounterparty(edit ? detail!.counterparty_name ?? '' : ''); setReference(edit ? detail!.reference_number ?? '' : ''); setNotes(edit ? detail!.notes ?? '' : ''); setReason(''); setReviewed(false); setFormOpen(true)
  }
  const filter = () => { query.current = { ...query.current, q: q.trim(), status, transaction_id: null, offset: 0 }; setFormOpen(false); void load() }
  const editFilter = () => { beginRead(); setData(null); setBusy(false); setReviewed(false); setActionReviewed(false) }
  return <section className="panel cmisc" aria-label="Pendapatan dan biaya lain">
    <div className="cproc-heading"><div><h2>Pendapatan & Biaya Lain</h2><p>Catat transaksi kas di luar penjualan, pembelian, dan biaya produksi melalui kategori yang tersedia.</p></div><button disabled={busy || mutation.busy} onClick={() => { if (query.current.q !== q.trim() || query.current.status !== status) filter(); else void load() }}>Muat ulang transaksi lain</button></div>
    <ProductionRecoveryNotice recovery={mutation} className="" onReconcile={() => reconcile(handlers)}/>
    {busy ? <p role="status">Memeriksa transaksi, kategori dan rekening…</p> : null}{error ? <p role="alert">{error}</p> : null}
    {outcome ? <p role="status">Permintaan terakhir: {outcome.document.number} · {statusLabel[outcome.document.status]}. Hasil permintaan ini sudah tersimpan; tindakan berikutnya mengikuti sumber yang dimuat ulang.</p> : null}
    <form className="cproc-grid" onSubmit={e => { e.preventDefault(); filter() }}>
      <label>Cari transaksi<input aria-label="Cari transaksi lain" maxLength={120} value={q} onChange={e => { editFilter(); setQ(e.target.value) }}/></label>
      <label>Status<select aria-label="Status transaksi lain" value={status ?? ''} onChange={e => { editFilter(); setStatus(e.target.value === '' ? null : e.target.value as MiscQuery['status']) }}><option value="">Semua status</option><option value="DRAFT">Draft</option><option value="POSTED">Tercatat</option><option value="REVERSED">Sudah dibalik</option></select></label><button disabled={busy || mutation.busy}>Cari transaksi lain</button>
    </form>
    {data ? <>
      <p>Dibaca {formatCp6WibDateTime(data.captured_at)}. Draft belum memengaruhi kas atau laba. Nama kategori dan rekening mengikuti data saat ini; transaksi tercatat tetap mengikuti jurnal sumber.</p>
      <button disabled={locked} onClick={() => openForm(false)}>Buat transaksi lain</button>
      <div className="cproc-layout"><section aria-label="Daftar transaksi lain"><h3>Transaksi</h3>{data.page.rows.length === 0 ? <p>Tidak ada transaksi sesuai pencarian.</p> : null}
        {data.page.rows.map(t => <button className="cproc-receipt" data-misc-id={t.id} key={t.id} disabled={locked} aria-pressed={detail?.id === t.id} onClick={() => { query.current = { ...query.current, transaction_id: t.id }; setFormOpen(false); setActionReason(''); void load() }}><span><strong>{t.number}</strong><small>{typeLabel[t.type]} · {statusLabel[t.status]}</small><small>{formatCp6WibDateTime(t.physical_at)}</small></span><span>{money(t.amount)}</span></button>)}
        <div className="cproc-pagination"><span>Total {data.page.total} dokumen</span><button disabled={locked || data.page.offset === 0} onClick={() => { query.current = { ...query.current, offset: Math.max(0, data.page.offset - 25) }; void load() }}>Transaksi lain sebelumnya</button><button disabled={locked || data.page.next_offset === null} onClick={() => { query.current = { ...query.current, offset: data.page.next_offset ?? 0 }; void load() }}>Transaksi lain berikutnya</button></div>
      </section><aside aria-label="Rincian transaksi lain">{detail ? <>
        <h3>{detail.number}</h3><p>{typeLabel[detail.type]} · {statusLabel[detail.status]} · {money(detail.amount)}</p><p>{detail.category_name ?? 'Kategori belum tersedia'} · {detail.cash_account_name ?? 'Rekening belum tersedia'}.</p><p>Kejadian {formatCp6WibDateTime(detail.physical_at)}.</p>{detail.counterparty_name ? <p>Pihak {detail.counterparty_name}</p> : null}{detail.reference_number ? <p>Referensi {detail.reference_number}</p> : null}{detail.notes ? <p>{detail.notes}</p> : null}
        {detail.journals.map(j => <article className="cproc-item" data-misc-journal-id={j.id} key={j.id}><strong>{j.number}</strong><p>{j.reversal_of_id ? 'Jurnal pembalikan' : 'Jurnal sumber'} · kejadian {j.economic_date} · pembukuan {j.transaction_date} · {j.status === 'REVERSED' ? 'asli sudah dibalik' : 'tercatat'}.</p><p>Debit {money(j.debit)} · kredit {money(j.credit)}.</p>{j.period_shifted ? <p>Pembukuan dipindahkan ke periode terbuka; tanggal kejadian tetap.</p> : null}</article>)}
        {detail.status === 'DRAFT' ? <button disabled={locked} onClick={() => openForm(true)}>Ubah draft transaksi lain</button> : null}
        {detail.status !== 'REVERSED' ? <fieldset disabled={locked} className="cproc-fieldset"><p>{detail.status === 'DRAFT' ? 'Posting mencatat kas dan pendapatan/biaya pada jurnal. Tanggal pembukuan mengikuti kontrol periode.' : 'Pembalikan membuat jurnal lawan pada tanggalnya sendiri. Transaksi dan jurnal asli tetap tersimpan.'}</p>
          <label>Alasan tindakan<textarea aria-label="Alasan posting atau pembalikan transaksi lain" value={actionReason} maxLength={1000} onChange={e => { setActionReason(e.target.value); setActionReviewed(false) }}/></label>
          <label className="cproc-check"><input type="checkbox" aria-label="Transaksi lain untuk posting atau pembalikan sudah diperiksa" checked={actionReviewed} onChange={e => setActionReviewed(e.target.checked)}/>Transaksi, nominal, rekening dan alasan tindakan sudah saya periksa.</label>
          <button className="primary-btn" disabled={!actionReviewed || actionReason.trim().length < 5 || actionReason.trim().length > 1000 || detail.status === 'DRAFT' && (!detail.category_eligible || !detail.cash_eligible)} onClick={() => action(detail.status === 'DRAFT' ? 'POST' : 'REVERSE')}>{detail.status === 'DRAFT' ? 'Posting transaksi lain' : 'Balikkan transaksi lain'}</button>
        </fieldset> : <p>Transaksi asli sudah dibalik. Catat transaksi pengganti dengan sumber dan nominal yang sudah diperiksa.</p>}
      </> : <p>Pilih dokumen untuk memeriksa transaksi dan jurnal sumber.</p>}</aside></div>
      {formOpen ? <form aria-label="Draft pendapatan atau biaya lain" onSubmit={e => { e.preventDefault(); save() }} onChange={() => setReviewed(false)}><fieldset disabled={locked} className="cproc-fieldset">
        <h3>{editing ? 'Ubah draft' : 'Draft baru'}</h3><div className="cproc-grid"><label>Nomor transaksi<input aria-label="Nomor transaksi lain" maxLength={60} value={number} onChange={e => setNumber(e.target.value)}/></label><label>Jenis<select aria-label="Jenis transaksi lain" value={type} onChange={e => { setType(e.target.value as MiscType); setCategory(null) }}><option value="OTHER_EXPENSE">Biaya lain</option><option value="OTHER_INCOME">Pendapatan lain</option></select></label><label>Waktu kejadian · WIB<input type="datetime-local" aria-label="Waktu transaksi lain WIB" value={at} max={cp6WibDateTimeInput()} onChange={e => setAt(e.target.value)}/></label><label>Nominal<input inputMode="decimal" aria-label="Nominal transaksi lain" value={amount} onChange={e => setAmount(e.target.value)}/></label></div>
        {amount && !amountValid ? <p role="alert">Isi nominal positif dengan maksimal dua desimal.</p> : null}
        <section aria-label="Kategori transaksi lain"><h4>Pilih kategori</h4>{data.categories.rows.filter(c => c.type === type).map(c => <button type="button" className="cproc-receipt" data-misc-category-id={c.id} key={c.id} aria-pressed={category?.id === c.id} onClick={() => { setCategory(c); setReviewed(false) }}><span><strong>{c.code} · {c.name}</strong><small>{c.account_code} · {c.account_name}</small></span></button>)}<p>Terpilih: {category?.name ?? 'belum dipilih'}. Total {data.categories.total} kategori aktif dari kedua jenis.</p><button type="button" disabled={data.categories.offset === 0} onClick={() => { query.current.category_offset = Math.max(0, data.categories.offset - 25); void load() }}>Kategori sebelumnya</button><button type="button" disabled={data.categories.next_offset === null} onClick={() => { query.current.category_offset = data.categories.next_offset ?? 0; void load() }}>Kategori berikutnya</button></section>
        <section aria-label="Rekening transaksi lain"><h4>Pilih kas atau bank</h4>{data.cash_accounts.rows.map(b => <button type="button" className="cproc-receipt" data-misc-cash-id={b.id} key={b.id} aria-pressed={bank?.id === b.id} onClick={() => { setBank(b); setReviewed(false) }}><span><strong>{b.code} · {b.name}</strong><small>{b.account_code} · {b.account_name}</small></span></button>)}<p>Terpilih: {bank?.name ?? 'belum dipilih'}. Total {data.cash_accounts.total} rekening aktif.</p><button type="button" disabled={data.cash_accounts.offset === 0} onClick={() => { query.current.cash_offset = Math.max(0, data.cash_accounts.offset - 25); void load() }}>Rekening transaksi lain sebelumnya</button><button type="button" disabled={data.cash_accounts.next_offset === null} onClick={() => { query.current.cash_offset = data.cash_accounts.next_offset ?? 0; void load() }}>Rekening transaksi lain berikutnya</button></section>
        <div className="cproc-grid"><label>Pihak terkait<input aria-label="Pihak transaksi lain" value={counterparty} maxLength={150} onChange={e => setCounterparty(e.target.value)}/></label><label>Nomor referensi<input aria-label="Referensi transaksi lain" value={reference} maxLength={100} onChange={e => setReference(e.target.value)}/></label></div><label>Catatan<textarea aria-label="Catatan transaksi lain" value={notes} maxLength={2000} onChange={e => setNotes(e.target.value)}/></label><label>Alasan penyimpanan<textarea aria-label="Alasan simpan transaksi lain" value={reason} maxLength={1000} onChange={e => setReason(e.target.value)}/></label>
        <label className="cproc-check"><input type="checkbox" aria-label="Draft transaksi lain sudah diperiksa" checked={reviewed} onChange={e => { e.stopPropagation(); setReviewed(e.target.checked) }}/>Jenis, kategori, rekening, nominal dan waktu kejadian sudah saya periksa.</label><button className="primary-btn" disabled={!valid}>Simpan draft transaksi lain</button><button type="button" onClick={() => { setFormOpen(false); setReviewed(false) }}>Urungkan draft transaksi lain</button>
      </fieldset></form> : null}
    </> : null}
  </section>
}
