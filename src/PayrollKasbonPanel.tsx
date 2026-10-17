import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { kasbonAmountText, kasbonCents, moneyCents, parseKasbonOutcome, parseKasbonWorkspace, type Kasbon, type KasbonAction, type KasbonWorkspace } from './payrollKasbonContract'
import type { Json } from './types/database.preconnect'

const rupiah = (v: string) => { const [whole, cents = '00'] = v.split('.'); return `Rp${whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents}` }
const rp = (c: bigint) => rupiah(kasbonAmountText(c))
type Form = { action: KasbonAction; kasbon: Kasbon | null }

// D14-6 kasbon tunai for the contractor of the selected payroll: give cash, cut it from a payroll draft, cancel unused.
export default function PayrollKasbonPanel({ contractorId, payrollId, parentReady, onChanged }: {
  contractorId: string | null; payrollId: string | null; parentReady: boolean; onChanged: () => Promise<unknown>
}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi kasbon belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('PAYROLL_KASBON'), { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role) && identity.permissions.includes('finance.payroll.view')
  const [data, setData] = useState<KasbonWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [form, setForm] = useState<Form | null>(null), [amount, setAmount] = useState(''), [date, setDate] = useState(''), [bank, setBank] = useState('')
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false), [open, setOpen] = useState(false)
  const seq = useRef(0), latestRead = useRef<Promise<boolean>>(Promise.resolve(false))
  const read = useCallback(async () => {
    const ticket = beginRead(), n = ++seq.current
    setData(null); setForm(null); setError('')
    if (!allowed || !contractorId) return false
    setBusy(true)
    try {
      const r = await client.rpc('erp_cp7_get_kasbon_v1', { p_contractor: contractorId })
      if (n !== seq.current || !isReadCurrent(ticket)) return false
      if (r.error) throw r.error
      setData(parseKasbonWorkspace(r.data, contractorId)); finishRead(ticket); return true
    } catch (e) {
      if (n === seq.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message)
      return false
    } finally { if (n === seq.current) setBusy(false) }
  }, [allowed, beginRead, client, contractorId, finishRead, isReadCurrent])
  const load = useCallback(() => { const p = read(); latestRead.current = p; return p }, [read])
  // Read only on request: opening the payroll page reads nothing else. The payroll page empties its detail while it
  // reloads (also right after a kasbon is saved), so the contractor is briefly null: only a different contractor
  // closes the panel and clears the saved-kasbon message.
  const shown = useRef(contractorId)
  useEffect(() => {
    if (!contractorId || contractorId === shown.current) return
    shown.current = contractorId; setOpen(false); setDone(''); ++seq.current; setData(null); setForm(null)
  }, [contractorId])
  useEffect(() => { if (open && parentReady) void load(); else { ++seq.current; setData(null) } return () => { ++seq.current } }, [load, open, parentReady])
  if (!allowed || !contractorId) return null
  const draft = data?.payroll_drafts.find(d => d.id === payrollId) ?? null
  const start = (action: KasbonAction, k: Kasbon | null = null) => {
    setForm({ action, kasbon: k }); setReviewed(false); setReason(''); setDate(data?.today ?? ''); setBank('')
    if (action === 'ALLOCATE' && k && draft) {
      const room = moneyCents(draft.net_payable) + (k.allocations.find(a => a.payroll_id === draft.id) ? moneyCents(k.allocations.find(a => a.payroll_id === draft.id)!.amount) : 0n)
      const free = moneyCents(k.free) + (k.allocations.find(a => a.payroll_id === draft.id) ? moneyCents(k.allocations.find(a => a.payroll_id === draft.id)!.amount) : 0n)
      setAmount(kasbonAmountText(room < free ? (room > 0n ? room : 0n) : free))
    } else setAmount('')
  }
  const cents = kasbonCents(amount)
  const problems: string[] = []
  if (form && data) {
    if (form.action !== 'CANCEL' && (cents === null || (form.action === 'GIVE' && cents <= 0n))) problems.push('Isi nominal dalam rupiah, paling banyak 2 angka di belakang koma.')
    if (form.action === 'GIVE') {
      if (!date || date > data.today) problems.push('Tanggal kasbon tidak boleh di masa depan.')
      else if (date < data.open_from) problems.push(`Tanggal kasbon ada di periode yang sudah ditutup. Pilih mulai ${data.open_from}.`)
      if (!bank) problems.push('Pilih rekening kas atau bank yang mengeluarkan uang.')
    }
    if (form.action === 'ALLOCATE' && form.kasbon && cents !== null) {
      const mine = form.kasbon.allocations.find(a => a.payroll_id === payrollId)
      const free = moneyCents(form.kasbon.free) + (mine ? moneyCents(mine.amount) : 0n)
      if (cents > free) problems.push(`Potongan melebihi sisa kasbon (${rp(free)}).`)
    }
    if (reason.trim().length < 5 && form.action !== 'ALLOCATE') problems.push('Tulis alasan minimal 5 huruf.')
  }
  const handlers: ProductionMutationHandlers = {
    send: e => { const p = e.payload as { document: Json; expected: string }; return client.rpc('erp_cp7_save_kasbon_v1', { p_action: e.action, p_payload: p.document, p_request: e.id, p_expected: p.expected }) },
    validate: (v, e) => { parseKasbonOutcome(v, e.id, e.action as KasbonAction, contractorId) },
    retire: (v, e) => {
      const k = parseKasbonOutcome(v, e.id, e.action as KasbonAction, contractorId)
      setForm(null); setData(null)
      setDone(e.action === 'GIVE' ? `Kasbon ${k.number} ${rupiah(k.amount)} tercatat. Uang keluar dari rekening yang dipilih; piutang mandor naik sebesar itu.`
        : e.action === 'CANCEL' ? `Kasbon ${k.number} dibatalkan. Uangnya kembali ke rekening asal.`
          : `Potongan kasbon ${k.number} pada payroll diperbarui. Sisa kasbon ${rupiah(k.free)}. Hitung dan setujui ulang payroll sebelum dibayar.`)
    },
    // The parent's reload re-renders this panel, and its own effect may start a newer read while this one is in flight.
    // A read superseded that way is not a failed refresh: the result is the newest read's (CI 39020856920, R3 guards
    // case: a refused kasbon showed "Refetch authoritative gagal" although the newer read succeeded).
    reload: async () => {
      await onChanged()
      let current = load(), ok = await current
      while (!ok && latestRead.current !== current) { current = latestRead.current; ok = await current }
      return ok
    },
  }
  const submit = () => {
    if (!form || !data || problems.length || !reviewed) return
    const base = { contractor_id: data.contractor.id }
    const document: Json = form.action === 'GIVE'
      ? { ...base, cash_account_id: bank, cash_review_token: data.cash_accounts.find(c => c.id === bank)?.review_token ?? '', advance_date: date, amount: kasbonAmountText(cents ?? 0n), reason: reason.trim() }
      : form.action === 'ALLOCATE'
        ? { ...base, advance_id: form.kasbon?.id ?? '', payroll_id: draft?.id ?? '', payroll_version: draft?.row_version ?? '', amount: kasbonAmountText(cents ?? 0n) }
        : { ...base, advance_id: form.kasbon?.id ?? '', reason: reason.trim() }
    const action = form.action; setForm(null)
    void run(action, { document, expected: data.review_token }, null, handlers)
  }
  const locked = busy || mutation.writerLocked || !parentReady
  return <section className="panel cpay-detail" aria-label="Kasbon tunai">
    <header className="cpay-actions"><h2>Kasbon tunai{data ? ` · ${data.contractor.name}` : ''}</h2>{open ? <button disabled={busy || mutation.busy} onClick={() => void load()}>Muat ulang kasbon</button> : <button disabled={!parentReady} onClick={() => { setOpen(true); setDone('') }}>Lihat kasbon mandor ini</button>}</header>
    <ProductionRecoveryNotice recovery={mutation} className="cpay-action" onReconcile={() => reconcile(handlers)} reconcileLabel="Periksa status kasbon" />
    {done ? <p role="status">{done}</p> : null}{error ? <p role="alert">{error}</p> : null}{busy ? <p role="status">Memuat kasbon…</p> : null}
    {data ? <>
      <p>Kasbon adalah uang yang diberikan sebelum upah jadi utang. Kasbon dipotong dari payroll draf mandor ini; yang dibayar tunai hanya sisa gajinya.</p>
      {data.can_write ? <button className="primary-btn" disabled={locked} onClick={() => start('GIVE')}>Beri kasbon</button> : null}
      {data.advances.length ? <div className="cpay-lines">{data.advances.map(k => <article className="cpay-line" key={k.id}>
        <header><strong>{k.number} · {rupiah(k.amount)}</strong><strong>{k.status === 'CANCELLED' ? 'Dibatalkan' : `Sisa ${rupiah(k.free)}`}</strong></header>
        <p>{k.advance_date} · {k.reason}</p>
        <p>Sudah terpotong {rupiah(k.recovered)} · Dipesan di payroll {rupiah(k.reserved)}</p>
        {k.allocations.map(a => <p key={a.deduction_id} className="cpay-reference">{a.payroll_number} · {a.payroll_status} · {rupiah(a.amount)}</p>)}
        {data.can_write && k.status === 'GIVEN' && draft ? <button disabled={locked} onClick={() => start('ALLOCATE', k)}>Potong dari payroll {draft.payroll_number}</button> : null}
        {data.can_write && k.status === 'GIVEN' && moneyCents(k.recovered) === 0n && moneyCents(k.reserved) === 0n ? <button disabled={locked} onClick={() => start('CANCEL', k)}>Batalkan kasbon {k.number}</button> : null}
      </article>)}</div> : <p>Mandor ini belum punya kasbon.</p>}
      {form ? <section className="cpay-action" aria-label="Periksa kasbon">
        <h3>{form.action === 'GIVE' ? 'Beri kasbon tunai' : form.action === 'ALLOCATE' ? `Potong kasbon ${form.kasbon?.number} dari payroll ${draft?.payroll_number}` : `Batalkan kasbon ${form.kasbon?.number}`}</h3>
        <fieldset disabled={locked}>
          {form.action !== 'CANCEL' ? <label>{form.action === 'GIVE' ? 'Nominal kasbon' : 'Nominal dipotong (0 untuk melepas)'}<input aria-label="Nominal kasbon" inputMode="decimal" value={amount} onChange={e => { setAmount(e.target.value); setReviewed(false) }} /></label> : null}
          {form.action === 'ALLOCATE' && draft ? <p>Pendapatan payroll {rupiah(draft.earnings)} · potongan sekarang {rupiah(draft.deduction_total)} · gaji bersih {rupiah(draft.net_payable)}.</p> : null}
          {form.action === 'GIVE' ? <>
            <label>Tanggal kasbon · WIB<input aria-label="Tanggal kasbon" type="date" min={data.open_from} max={data.today} value={date} onChange={e => { setDate(e.target.value); setReviewed(false) }} /></label>
            <label>Rekening yang mengeluarkan uang<select aria-label="Rekening kasbon" value={bank} onChange={e => { setBank(e.target.value); setReviewed(false) }}><option value="">Pilih rekening…</option>{data.cash_accounts.map(c => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
          </> : null}
          {form.action !== 'ALLOCATE' ? <label>Alasan<input aria-label="Alasan kasbon" maxLength={500} value={reason} onChange={e => { setReason(e.target.value); setReviewed(false) }} /></label> : null}
          {problems.length ? <ul role="alert">{problems.map(p => <li key={p}>{p}</li>)}</ul> : null}
          <label className="cpay-check"><input type="checkbox" aria-label="Kasbon sudah diperiksa" checked={reviewed} disabled={problems.length > 0} onChange={e => setReviewed(e.target.checked)} />Nominal, tanggal, rekening, dan mandor sudah saya periksa.</label>
          <div className="cpay-actions"><button className="primary-btn" disabled={!reviewed || problems.length > 0} onClick={submit}>{form.action === 'GIVE' ? 'Simpan kasbon' : form.action === 'ALLOCATE' ? 'Simpan potongan kasbon' : 'Batalkan kasbon sekarang'}</button><button onClick={() => setForm(null)}>Kembali</button></div>
        </fieldset>
      </section> : null}
    </> : null}
  </section>
}
