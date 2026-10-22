/** Parent owns source reads, mutation UUID and recovery for return settlement. */
import {useEffect, useMemo, useRef, useState} from 'react'
import {cp6WibDateTimeInput, cp6WibPhysicalTimeToIso} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {isUnansweredFailure} from './lib/clientError'
import {creditRefusalMessage, serverRefusalCode} from './lib/creditRefusalMessages'
import {
  acceptQuote, blankChoice, canCommit, commitIntent, emptyQuoteUi, inputIdentity,
  parseQuoteInput, parseSettlementAccountOptions, parseSettlementQuote, retireQuote, startQuote,
  type AccountOptions, type AccountOptionsQuery, type DraftChoice, type Issue,
  type Quote, type QuoteInput, type QuoteReply, type QuoteUi, type ReadContext, type RecoveryPayload, type Source,
} from './salesReturnSettlementContract'

export type SettlementSectionProps<TTicket> = {
  source: Source
  input: QuoteInput | null
  choice: DraftChoice
  /** Parent increments this for every return/choice edit, including A→B→A. */
  generation: number
  parentReadTicket: TTicket | null
  isReadCurrent: (ticket: TTicket) => boolean
  authorityScope: string
  locked: boolean
  stale: boolean
  pendingEnvelope: boolean
  getQuote: (query: QuoteInput) => Promise<unknown>
  getAccountOptions: (query: AccountOptionsQuery) => Promise<unknown>
  onChoiceChange: (choice: DraftChoice) => void
  onInvalid: (message: string) => void
  /** Exactly commitIntent(...).payload; parent supplies the action and UUID. */
  onIntent: (payload: RecoveryPayload) => void
}

type Kind = 'CREDIT' | 'CASH'
type Fence = object
type Page = {fence: Fence; request: number; loading: boolean; reply: AccountOptions | null}
type QuoteState = {fence: Fence | null; ui: QuoteUi}
type Snapshot<T> = SettlementSectionProps<T> & {fence: Fence; context: ReadContext | null; validInput: QuoteInput | null}
const money = (v: string) => `Rp${formatReceiptDecimal(v)}`
const issueLabels: Record<Issue, string> = {
  CHOOSE_MODE: 'Pilih penyelesaian nilai retur.',
  CHOOSE_CREDIT_ACCOUNT: 'Pilih akun saldo kredit pelanggan.',
  CHOOSE_REFUND_ACCOUNT: 'Pilih rekening pengembalian uang.',
  ENTER_REFUND_TIME: 'Isi waktu pengembalian uang WIB secara terpisah.',
  CLEAR_UNNEEDED_SETTLEMENT: 'Rencana ini tidak memerlukan penyelesaian saldo kredit. Kosongkan pilihan dan periksa ulang.',
  REFUND_ZERO_CURRENT_AMOUNT: 'Hak kredit saat ini Rp0. Tidak ada uang yang dapat dikembalikan.',
  REFUND_EXCEEDS_DATED_CAPACITY: 'Saldo pada tanggal yang dipilih belum cukup untuk pengembalian uang.',
  CREDIT_ACCOUNT_INELIGIBLE: 'Akun saldo kredit tidak lagi memenuhi syarat. Pilih dan periksa ulang.',
  CASH_ACCOUNT_INELIGIBLE: 'Rekening pengembalian uang tidak lagi memenuhi syarat. Pilih dan periksa ulang.',
  RETURN_PERMISSION_REQUIRED: 'Hak mencatat retur tidak tersedia.',
  RECOGNITION_PERMISSION_REQUIRED: 'Hak mencatat saldo kredit tidak tersedia.',
  REFUND_PERMISSION_REQUIRED: 'Hak mengembalikan uang tidak tersedia.',
  DEPENDENCY_BLOCKED: 'Dokumen terkait harus diselesaikan sebelum retur ini dapat dicatat.',
  PERIOD_CHANGED: 'Periode pembukuan berubah. Periksa ulang tanggal dan sumber retur.',
}
const totalLabels = [
  ['gross_total', 'Nilai invoice'], ['return_total', 'Nilai retur'], ['net_total', 'Sisa nilai invoice'],
  ['payments_received', 'Pembayaran diterima (P)'], ['credit_applied', 'Saldo kredit dipakai (U)'],
  ['credit_recognized', 'Pengakuan kredit bersih (I)'], ['effective_paid', 'Pelunasan efektif (E)'],
  ['receivable_remaining', 'Piutang tersisa (AR)'],
] as const

function completeInput<T>(props: SettlementSectionProps<T>): QuoteInput | null {
  if (props.input === null) return null
  try {
    const input = parseQuoteInput(props.input), s = props.source
    return input.sale_id === s.sale_id && input.expected_version === s.row_version && input.review_token === s.review_token
      && inputIdentity(input.settlement) === inputIdentity(props.choice) ? input : null
  } catch { return null }
}
function ticketCurrent<T>(s: Snapshot<T>): boolean {
  if (s.parentReadTicket === null || !s.authorityScope.trim() || s.locked || s.stale || s.pendingEnvelope) return false
  try { return s.isReadCurrent(s.parentReadTicket) } catch { return false }
}
function accessRefused(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const e = error as {status?: unknown; code?: unknown}
  return e.status === 401 || e.status === 403 || e.status === '401' || e.status === '403' || e.code === '42501'
}
/** OW-04b part 3: a refused read names the reason and the next step, never only "belum dapat diperiksa".
 * Raw server text is never shown; only a bare server code may be named, so the user can report it. */
function readRefusal(error: unknown, what: 'QUOTE' | 'OPTIONS'): string {
  if (accessRefused(error)) return what === 'QUOTE' ? 'Akses sumber retur berubah. Muat ulang invoice dan hak akses.' : 'Akses akun retur berubah. Muat ulang invoice dan hak akses.'
  const e = error && typeof error === 'object' ? error as {message?: unknown; details?: unknown} : {}
  const named = creditRefusalMessage(e.message, e.details)
  if (named) return named
  const label = what === 'QUOTE' ? 'Pemeriksaan retur' : 'Pencarian akun retur'
  if (isUnansweredFailure(error)) return `Server belum menjawab ${label.toLowerCase()}. Periksa koneksi, lalu ${what === 'QUOTE' ? 'tekan Periksa penyelesaian retur' : 'cari akun'} lagi.`
  const code = serverRefusalCode(e.message)
  return code ? `${label} ditolak server (kode ${code}). Muat ulang invoice lalu coba lagi; bila kode yang sama muncul lagi, beri tahu admin dengan kode ini.`
    : `${label} ditolak server tanpa kode yang dapat dibaca. Muat ulang invoice lalu coba lagi; bila berulang, beri tahu admin.`
}
const unreadable = (what: 'QUOTE' | 'OPTIONS') => `${what === 'QUOTE' ? 'Jawaban pemeriksaan retur' : 'Daftar akun'} dari server tidak lengkap atau tidak sesuai, jadi tidak ditampilkan. Muat ulang invoice lalu coba lagi; bila berulang, beri tahu admin.`

export default function SalesReturnSettlementSection<TTicket>(props: SettlementSectionProps<TTicket>) {
  const ticketSequence = useRef(0)
  // This label never serializes the actual parent ticket/session or grants authority.
  const ticket = useMemo(() => ({label: `parent-read-${++ticketSequence.current}`}), [props.parentReadTicket])
  const valueKey = inputIdentity({source: props.source, input: props.input, choice: props.choice, generation: props.generation,
    authority: props.authorityScope, locked: props.locked, stale: props.stale, pending: props.pendingEnvelope})
  // A new token on every observed transition also fences A→B→A with equal values.
  const fence = useMemo<Fence>(() => ({}), [valueKey, ticket])
  const validInput = completeInput(props)
  const context: ReadContext | null = validInput && props.parentReadTicket !== null ? {
    generation: props.generation, parent_ticket: ticket.label,
    authority_scope: props.authorityScope, input_identity: inputIdentity(validInput),
  } : null
  const snapshot: Snapshot<TTicket> = {...props, fence, context, validInput}
  const latest = useRef(snapshot); latest.current = snapshot
  const mounted = useRef(true), quoteRequest = useRef(0), optionRequest = useRef({CREDIT: 0, CASH: 0})
  const invalidFence = useRef<Fence | null>(null), choiceRetiredFence = useRef<Fence | null>(null), emitted = useRef(false)
  const [quote, setQuote] = useState<QuoteState>({fence: null, ui: emptyQuoteUi()})
  const quoteRef = useRef(quote); quoteRef.current = quote
  const [pages, setPages] = useState<Record<Kind, Page | null>>({CREDIT: null, CASH: null})
  const [search, setSearch] = useState<Record<Kind, string>>({CREDIT: '', CASH: ''})
  const [problem, setProblem] = useState<{fence: Fence; message: string} | null>(null)
  const [, renderLocalFence] = useState(0)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; ++quoteRequest.current; ++optionRequest.current.CREDIT; ++optionRequest.current.CASH } }, [])

  const current = (s: Snapshot<TTicket>) => mounted.current && latest.current.fence === s.fence && ticketCurrent(latest.current)
    && invalidFence.current !== s.fence && choiceRetiredFence.current !== s.fence && !emitted.current
  const sameRender = (s: Snapshot<TTicket>) => mounted.current && latest.current.fence === s.fence
  const retire = () => {
    ++quoteRequest.current; ++optionRequest.current.CREDIT; ++optionRequest.current.CASH
    setQuote({fence: null, ui: retireQuote()}); setPages({CREDIT: null, CASH: null})
  }
  const refuse = (s: Snapshot<TTicket>, message: string) => {
    if (!sameRender(s)) return
    invalidFence.current = s.fence; retire(); setProblem({fence: s.fence, message})
    latest.current.onInvalid(message)
  }
  const changeChoice = (next: DraftChoice, recheckedAccount = false) => {
    const s = latest.current
    if (!current(s) || !recheckedAccount && inputIdentity(next) === inputIdentity(s.choice)) return
    // Hide old facts before even a deferred controlled-parent update.
    choiceRetiredFence.current = s.fence; retire(); setProblem(null); renderLocalFence(x => x + 1)
    s.onChoiceChange(structuredClone(next))
  }
  const loadQuote = async () => {
    const s = latest.current
    if (!current(s) || !s.validInput || !s.context) return
    const request = ++quoteRequest.current, query = structuredClone(s.validInput), started = startQuote(s.context)
    setProblem(null); setQuote({fence: s.fence, ui: started})
    let raw: unknown, reply: QuoteReply
    try { raw = await s.getQuote(query) } catch (error) {
      if (request === quoteRequest.current && sameRender(s)) refuse(s, readRefusal(error, 'QUOTE'))
      return
    }
    if (request !== quoteRequest.current || !sameRender(s)) return
    if (!current(s)) { refuse(s, 'Sumber invoice berubah. Muat ulang invoice sebelum memeriksa retur.'); return }
    try { reply = parseSettlementQuote(raw, query) } catch { refuse(s, unreadable('QUOTE')); return }
    setQuote({fence: s.fence, ui: acceptQuote(started, s.context, latest.current.context!, reply)})
  }
  const loadOptions = async (kind: Kind, offset: number) => {
    const s = latest.current
    if (!current(s) || s.choice.mode === null || kind === 'CASH' && s.choice.mode !== 'REFUND') return
    const request = ++optionRequest.current[kind]
    const query: AccountOptionsQuery = {kind: 'ACCOUNT_OPTIONS', sale_id: s.source.sale_id, expected_version: s.source.row_version,
      review_token: s.source.review_token, account_kind: kind, q: search[kind].trim(), offset, limit: 25}
    setPages(old => ({...old, [kind]: {fence: s.fence, request, loading: true, reply: null}}))
    let raw: unknown, reply: AccountOptions
    try { raw = await s.getAccountOptions(query) } catch (error) {
      if (request === optionRequest.current[kind] && sameRender(s)) refuse(s, readRefusal(error, 'OPTIONS'))
      return
    }
    if (request !== optionRequest.current[kind] || !sameRender(s)) return
    if (!current(s)) { refuse(s, 'Sumber invoice berubah. Muat ulang invoice sebelum memilih akun.'); return }
    try { reply = parseSettlementAccountOptions(raw, query) } catch { refuse(s, unreadable('OPTIONS')); return }
    setPages(old => ({...old, [kind]: {fence: s.fence, request, loading: false, reply}}))
  }
  const chooseAccount = (kind: Kind, id: string, page: Page) => {
    const s = latest.current
    if (!current(s) || page.fence !== s.fence || page.request !== optionRequest.current[kind] || !page.reply?.rows.some(a => a.id === id)) return
    // A freshly vetted row is a new eligibility review even if its UUID stayed
    // selected. Never keep the old quote/review by comparing only typed IDs.
    changeChoice({...s.choice, [kind === 'CREDIT' ? 'credit_account_id' : 'cash_account_id']: id}, true)
  }
  const submit = () => {
    const s = latest.current, q = quoteRef.current
    if (!current(s)) {
      if (sameRender(s) && !emitted.current && !s.locked && !s.pendingEnvelope) refuse(s, 'Sumber invoice berubah. Muat ulang invoice sebelum mencatat retur.')
      return
    }
    if (!s.context || q.fence !== s.fence || !canCommit(q.ui, s.context, {writer_locked: s.locked, source_stale: s.stale, pending_envelope: s.pendingEnvelope}) || q.ui.reply?.kind !== 'QUOTE') return
    const payload = commitIntent(q.ui.reply).payload
    // No second emit while the parent is persisting/dispatching or recovering.
    emitted.current = true; retire(); renderLocalFence(x => x + 1)
    try { s.onIntent(payload) } catch { s.onInvalid('Hasil permintaan retur belum diketahui. Periksa pemulihan permintaan sebelum melanjutkan.') }
  }

  const readable = current(snapshot), disabled = !readable
  const visibleUi = readable && quote.fence === fence ? quote.ui : null
  const reply = visibleUi?.reply ?? null, result: Quote | null = reply?.kind === 'QUOTE' ? reply : null
  const ready = result?.readiness.state === 'READY'
  const canSave = Boolean(readable && context && visibleUi && canCommit(visibleUi, context, {writer_locked: props.locked, source_stale: props.stale, pending_envelope: props.pendingEnvelope}))
  const picker = (kind: Kind) => {
    const page = readable && pages[kind]?.fence === fence && pages[kind]?.request === optionRequest.current[kind] ? pages[kind] : null
    const selected = props.choice[kind === 'CREDIT' ? 'credit_account_id' : 'cash_account_id']
    const checkedAccount = result?.[kind === 'CREDIT' ? 'credit_account' : 'cash_account']
    const title = kind === 'CREDIT' ? 'Akun saldo kredit pelanggan' : 'Rekening pengembalian uang'
    const searchLabel = kind === 'CREDIT' ? 'Cari akun saldo kredit pelanggan' : 'Cari rekening pengembalian uang'
    return <section aria-label={title}>
      <h4>{title}</h4>
      <p>{checkedAccount ? `${checkedAccount.code} · ${checkedAccount.name}` : selected ? 'Akun dipilih; kelayakan perlu diperiksa ulang.' : 'Belum dipilih.'}</p>
      <label>{searchLabel}<input aria-label={searchLabel} value={search[kind]} maxLength={120} disabled={disabled} onChange={e => {
        ++optionRequest.current[kind]; setSearch(old => ({...old, [kind]: e.target.value})); setPages(old => ({...old, [kind]: null}))
      }}/></label>
      <button type="button" disabled={disabled || Boolean(page?.loading)} onClick={() => void loadOptions(kind, 0)}>{searchLabel}</button>
      {page?.loading ? <p role="status">Memuat pilihan akun…</p> : null}
      {page?.reply ? <>
        {page.reply.rows.map(a => <button type="button" data-account-id={a.id} key={a.id} disabled={disabled} aria-pressed={selected === a.id} onClick={() => chooseAccount(kind, a.id, page)}>{a.code} · {a.name}</button>)}
        {!page.reply.rows.length ? <p>Tidak ada akun sesuai pencarian.</p> : null}
        <p>Total {page.reply.total} akun; halaman ini {page.reply.rows.length} akun.</p>
        <button type="button" disabled={disabled || page.reply.offset === 0} onClick={() => void loadOptions(kind, Math.max(0, page.reply!.offset - 25))}>{title} sebelumnya</button>
        <button type="button" disabled={disabled || page.reply.next_offset === null} onClick={() => void loadOptions(kind, page.reply!.next_offset!)}>{title} berikutnya</button>
      </> : null}
    </section>
  }
  return <section aria-label="Penyelesaian nilai retur">
    <h3>Penyelesaian nilai retur</h3>
    {props.pendingEnvelope || emitted.current ? <p role="status">Penyelesaian menunggu hasil permintaan. Selesaikan pemulihan permintaan sebelum membuat perubahan.</p> : null}
    {props.stale ? <p role="alert">Invoice berubah. Muat ulang invoice sebelum memeriksa retur.</p> : null}
    {problem?.fence === fence ? <p role="alert">{problem.message}</p> : null}
    {!props.input ? <p>Lengkapi barang, jumlah, nilai dan waktu retur sebelum pemeriksaan penyelesaian.</p> : null}
    <fieldset disabled={disabled}>
      <label>Penyelesaian nilai retur<select aria-label="Penyelesaian nilai retur" value={props.choice.mode ?? ''} onChange={e => {
        const mode = e.target.value as DraftChoice['mode'] | ''
        changeChoice(mode === '' ? blankChoice() : {...props.choice, mode, cash_account_id: null, refund_physical_at: null, reference: null})
      }}><option value="">Pilih penyelesaian</option><option value="CREDIT">Simpan sebagai saldo kredit</option><option value="REFUND">Kembalikan uang</option></select></label>
      {props.choice.mode !== null ? picker('CREDIT') : null}
      {props.choice.mode === 'REFUND' ? <>
        {picker('CASH')}
        <label>Waktu pengembalian uang · WIB<input type="datetime-local" aria-label="Waktu pengembalian uang WIB" value={props.choice.refund_physical_at ? cp6WibDateTimeInput(props.choice.refund_physical_at) : ''} onChange={e => changeChoice({...props.choice, refund_physical_at: cp6WibPhysicalTimeToIso(e.target.value)})}/></label>
        <label>Referensi pengembalian uang<input aria-label="Referensi pengembalian uang" maxLength={100} value={props.choice.reference ?? ''} onChange={e => changeChoice({...props.choice, reference: e.target.value || null})}/></label>
        <p>Nominal pengembalian uang: <output aria-label="Nominal pengembalian uang">{result ? money(result.current_credit_amount) : 'Belum diperiksa'}</output></p>
      </> : null}
      <button type="button" disabled={disabled || !validInput || visibleUi?.phase === 'LOADING'} onClick={() => void loadQuote()}>Periksa penyelesaian retur</button>
    </fieldset>
    {visibleUi?.phase === 'LOADING' ? <p role="status">Memeriksa penyelesaian retur…</p> : null}
    {reply?.kind === 'UNAVAILABLE' ? <p role="alert">Riwayat sumber belum dapat dibuktikan lengkap. Nilai penyelesaian belum diketahui; muat ulang sumber retur.</p> : null}
    {result ? <section aria-label="Hasil pemeriksaan penyelesaian retur">
      <p>{result.source.sale_number} · {result.source.customer_name}</p>
      <p>Hak kredit saat ini: <output aria-label="Hak kredit saat ini">{money(result.current_credit_amount)}</output></p>
      {result.has_recognition_effect && result.current_credit_amount === '0.00' ? <p>Ada pengakuan kredit pada tanggal sebelumnya; hak kredit saat ini Rp0.</p> : null}
      {!result.has_recognition_effect ? <p>Retur ini tidak membentuk saldo kredit pelanggan.</p> : null}
      {result.return_projection.journal_effect === 'NO_JOURNAL' ? <p>Retur fisik tanpa jurnal baru.</p> : <p>Tanggal pengakuan retur: {result.return_projection.economic_date}; tanggal buku retur: <span data-return-book-date>{result.return_projection.planned_book_date}</span>.</p>}
      {result.return_projection.prior_causal.state === 'DATED' ? <p>Batas tanggal buku sumber: {result.return_projection.prior_causal.causal_book_floor}.</p> : <p>Sumber sebelumnya telah diperiksa tanpa tanggal buku penjualan atau retur yang mendahului.</p>}
      {result.components.length ? <table aria-label="Tanggal pengakuan kredit retur"><thead><tr><th>Pengakuan</th><th>Tanggal pengakuan</th><th>Tanggal buku</th><th>Nilai</th></tr></thead><tbody>{result.components.map(c => <tr key={c.component_key}><th>{c.signed_amount.startsWith('-') ? 'Penyesuaian pengakuan kredit' : 'Pengakuan kredit'}</th><td>{c.economic_date}</td><td>{c.book_date}</td><td data-signed-amount={c.signed_amount}>{money(c.signed_amount)}</td></tr>)}</tbody></table> : null}
      <table aria-label="Ringkasan invoice sebelum dan sesudah retur"><thead><tr><th>Nilai</th><th>Sebelum</th><th>Sesudah</th></tr></thead><tbody>{totalLabels.map(([key, label]) => <tr key={key} data-total={key}><th>{label}</th><td>{money(result.totals.before[key])}</td><td>{money(result.totals.after[key])}</td></tr>)}</tbody></table>
      {result.refund_projection ? <p>Batas pengembalian pada waktu dipilih: {result.refund_projection.safe_capacity === null ? 'Belum diketahui' : money(result.refund_projection.safe_capacity)}.{result.refund_projection.book_date ? ` Tanggal buku pengembalian: ${result.refund_projection.book_date}.` : ''}</p> : null}
      {result.readiness.issues.map(code => <p role="alert" key={code}>{issueLabels[code]}</p>)}
    </section> : null}
    <label><input type="checkbox" aria-label="Retur pelanggan sudah diperiksa" disabled={disabled || !ready} checked={Boolean(visibleUi?.reviewed && ready)} onChange={e => {
      const s = latest.current, q = quoteRef.current
      if (current(s) && q.fence === s.fence && q.ui.reply?.kind === 'QUOTE' && q.ui.reply.readiness.state === 'READY') setQuote({...q, ui: {...q.ui, reviewed: e.target.checked}})
    }}/>{result ? <>
      {`Barang, nilai, ${props.choice.mode === 'CREDIT' ? 'saldo kredit' : props.choice.mode === 'REFUND' ? 'pengembalian uang' : 'retur tanpa saldo kredit'}${result.credit_account ? ` pada ${result.credit_account.code} · ${result.credit_account.name}` : ''}${result.cash_account ? ` melalui ${result.cash_account.code} · ${result.cash_account.name}` : ''} sudah saya periksa. `}
      <span>Tanggal retur {result.return_projection.economic_date}{result.return_projection.journal_effect === 'JOURNAL_EXPECTED' ? `; buku retur ${result.return_projection.planned_book_date}` : '; tanpa jurnal baru'}.</span>
      {result.refund_projection ? <span> Tanggal pengembalian uang {result.refund_projection.economic_date ?? 'belum diperiksa'}; buku pengembalian {result.refund_projection.book_date ?? 'belum diperiksa'}.</span> : null}
    </> : 'Retur pelanggan sudah diperiksa.'}</label>
    <button type="button" disabled={!canSave} onClick={submit}>Catat retur dan penyelesaian</button>
  </section>
}
