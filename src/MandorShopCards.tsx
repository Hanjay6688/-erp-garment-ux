import { useEffect, useId, useRef, useState } from 'react'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { normalizeClientError } from './lib/clientError'
import {
  mandorShopAmount, mandorShopCents, mandorShopRupiah as money, mandorShopSignedCents,
  type MandorShopAllocation, type MandorShopCard, type MandorShopWorkspace,
} from './mandorShopContract'
import './mandor-shop.css'

type Form = { sale: string; token: string; action: 'RESERVE' | 'RELEASE'; allocation: string | null; amount: string; reviewed: boolean }
export type MandorShopCardsProps = {
  open: boolean; payrollId: string; payrollNumber: string; contractorId: string; contractorName: string
  workspace: MandorShopWorkspace | null; ready: boolean; busy: boolean; error?: string
  onClose: () => void; onReload: () => Promise<unknown>; onNext: (after: string) => Promise<unknown>
  onReserve: (card: MandorShopCard, amount: string) => Promise<unknown>
  onRelease: (card: MandorShopCard, allocation: MandorShopAllocation) => Promise<unknown>
}

/** Controlled source cards. The owning controller retains requests and performs authoritative reloads. */
export default function MandorShopCards(props: MandorShopCardsProps) {
  const { open, payrollId, contractorId, workspace, ready, busy } = props
  const dialog = useRef<HTMLDialogElement>(null), title = useId(), sending = useRef(false)
  const [working, setWorking] = useState(false), [error, setError] = useState(''), [form, setForm] = useState<Form | null>(null)
  const data = ready && workspace?.payroll_id === payrollId && workspace.contractor_id === contractorId ? workspace : null
  const locked = busy || working || !data, writable = !locked && data?.can_change === true
  const selected = form && data?.cards.find(c => c.sale_id === form.sale && c.review_token === form.token)
  const assigned = selected?.allocations.find(a => a.id === form?.allocation && a.payroll_id === payrollId && a.state === 'RESERVED')
  const cents = form ? mandorShopCents(form.amount) : null
  const net = data ? mandorShopSignedCents(data.net_payable_preview) : 0n
  const free = selected ? mandorShopSignedCents(selected.available_to_reserve) : 0n
  const valid = writable && selected && form?.reviewed && (form.action === 'RELEASE'
    ? Boolean(assigned) : cents !== null && cents > 0n && cents <= free && cents <= net
      && !selected.allocations.some(a => a.payroll_id === payrollId && a.state !== 'RELEASED'))

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (open && !el.open) el.showModal()
    else if (!open && el.open) el.close()
  }, [open])
  useEffect(() => { setForm(null); setError('') }, [workspace, payrollId, contractorId, open])
  async function perform(operation: () => Promise<unknown>) {
    if (sending.current) return
    sending.current = true; setWorking(true); setError('')
    try { await operation() } catch (failure) { setError(normalizeClientError(failure).message) }
    finally { sending.current = false; setWorking(false) }
  }
  function choose(card: MandorShopCard, allocation: MandorShopAllocation | null = null) {
    const available = mandorShopSignedCents(card.available_to_reserve), maximum = available < net ? available : net
    setForm({ sale: card.sale_id, token: card.review_token, action: allocation ? 'RELEASE' : 'RESERVE',
      allocation: allocation?.id ?? null, amount: allocation?.amount ?? (maximum > 0n ? mandorShopAmount(maximum) : ''), reviewed: false })
  }
  function submit() {
    if (!valid || !selected || !form || sending.current) return
    const card = selected
    if (form.action === 'RELEASE' && assigned) void perform(async () => { await props.onRelease(card, assigned); setForm(null) })
    else if (form.action === 'RESERVE' && cents !== null) {
      const amount = mandorShopAmount(cents)
      void perform(async () => { await props.onReserve(card, amount); setForm(null) })
    }
  }
  return <dialog ref={dialog} className="mandor-shop-dialog" aria-labelledby={title}
    onCancel={event => { event.preventDefault(); if (!busy && !working) props.onClose() }}>
    <header className="mandor-shop-heading"><div><h2 id={title}>Pasang tagihan belanja</h2>
      <p>{props.contractorName} · {props.payrollNumber}</p>
      {data ? <p>{data.period_start} sampai {data.period_end}</p> : null}
    </div><button type="button" autoFocus disabled={busy || working} onClick={props.onClose}>Tutup kartu tagihan</button></header>
    <p>Tagihan dipasang pada minggu payroll ini. Tagihan dilunasi ketika payroll dibayar.</p>
    {props.error || error ? <p role="alert">{props.error || error}</p> : null}
    {busy || working ? <p role="status">{working ? 'Memproses pilihan…' : 'Memuat kartu tagihan…'}</p> : null}
    <div className="mandor-shop-toolbar"><button type="button" disabled={busy || working} onClick={() => void perform(props.onReload)}>Muat ulang tagihan</button>
      {data ? <p>Potongan belanja <strong>{money(data.reserved_amount)}</strong> · Upah bersih <strong>{money(data.net_payable_preview)}</strong></p> : null}</div>
    {!data && !busy && !working ? <p role="status">Muat ulang tagihan dari payroll yang dipilih.</p> : null}
    {data ? <div className="mandor-shop-grid">{data.cards.length ? data.cards.map(card => {
      const mine = card.allocations.find(a => a.payroll_id === payrollId && a.state === 'RESERVED')
      const active = card.allocations.some(a => a.payroll_id === payrollId && a.state !== 'RELEASED')
      const canReserve = writable && !active && mandorShopSignedCents(card.available_to_reserve) > 0n && net > 0n
      return <article key={card.sale_id} className="mandor-shop-card" aria-label={`Nota ${card.number}`}>
        <header><strong>{card.number}</strong><span>{formatCp6WibDateTime(card.physical_at)}</span></header>
        <dl><div><dt>Nilai nota</dt><dd>{money(card.net_invoice)}</dd></div>
          <div><dt>Sudah dilunasi</dt><dd>{money(card.paid_amount)}</dd></div>
          <div><dt>Sisa tagihan</dt><dd>{money(card.outstanding)}</dd></div>
          <div><dt>Sudah dialokasikan</dt><dd>{money(card.allocated_amount)}</dd></div>
          <div><dt>Belum dipasang</dt><dd>{money(card.available_to_reserve)}</dd></div></dl>
        {card.allocations.length ? <details><summary>Riwayat pemasangan dan minggu payroll</summary><ul>{card.allocations.map(a =>
          <li key={a.id}><strong>{a.payroll_number} · {money(a.amount)}</strong><span>{a.period_start} sampai {a.period_end}</span>
            <span>{a.state === 'RESERVED' ? 'Dialokasikan' : a.state === 'SETTLED' ? 'Dilunasi' : 'Dilepas'}{a.payroll_id === payrollId ? ' · payroll ini' : ''}</span></li>)}</ul></details> : null}
        <div className="mandor-shop-actions">{canReserve ? <button type="button" disabled={!writable} onClick={() => choose(card)}>Pilih nota {card.number}</button> : null}
          {mine && data.can_change ? <button type="button" disabled={!writable} onClick={() => choose(card, mine)}>Lepas nota {card.number}</button> : null}</div>
      </article>
    }) : <p>Belum ada tagihan belanja untuk mandor ini.</p>}</div> : null}
    {data?.has_more && data.next_after ? <button type="button" disabled={locked} onClick={() => {
      const after = data.next_after; if (after) void perform(() => props.onNext(after))
    }}>Kartu berikutnya</button> : null}
    {selected && form ? <section className="mandor-shop-review" aria-label="Periksa pemasangan tagihan">
      <h3>{form.action === 'RELEASE' ? 'Lepas' : 'Pasang'} nota {selected.number}</h3>
      <p>{props.payrollNumber} · {data?.period_start} sampai {data?.period_end}</p>
      <fieldset disabled={!writable}>
        {form.action === 'RESERVE' ? <><label>Nominal potongan<input aria-label="Nominal potongan belanja" inputMode="decimal" maxLength={21} value={form.amount}
          onChange={event => setForm({ ...form, amount: event.target.value, reviewed: false })}/></label>
          {cents !== null && cents > 0n && cents <= free && cents <= net ? <p>Perkiraan upah bersih setelah dipasang: <strong>{money(mandorShopAmount(net - cents))}</strong></p>
            : <p role="alert">Isi nominal positif, paling banyak sisa yang belum dipasang dan kapasitas payroll.</p>}</>
          : assigned ? <p>Potongan {money(assigned.amount)} dilepas dari payroll ini.</p> : null}
        <label className="mandor-shop-confirm"><input type="checkbox" checked={form.reviewed}
          onChange={event => setForm({ ...form, reviewed: event.target.checked })}/> Saya sudah memeriksa nota, nominal, mandor, dan minggu payroll.</label>
        <button type="button" className="primary-btn" disabled={!valid} onClick={submit}>{form.action === 'RELEASE' ? 'Lepas tagihan dari payroll' : 'Pasang tagihan ke payroll'}</button>
        <button type="button" onClick={() => setForm(null)}>Batal memilih tagihan</button>
      </fieldset>
    </section> : null}
    {data && !data.can_change ? <p>Payroll ini sudah dibekukan. Perubahan potongan mengikuti alur koreksi payroll.</p> : null}
  </dialog>
}
