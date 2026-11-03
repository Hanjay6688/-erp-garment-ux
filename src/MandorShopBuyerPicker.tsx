import {useCallback, useEffect, useMemo, useRef, useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {parseMandorShopBuyerOptions, type MandorShopBuyerOptions} from './mandorShopContract'
import {parseMandorShopCustomerBuyer, salesBuyerCurrent, type BuyerFence, type SalesBuyerChoice} from './mandorShopSalesContract'

type Props = {action: 'CREATE' | 'EDIT'; initialCustomer: string | null; choice: SalesBuyerChoice
  onChange: (choice: SalesBuyerChoice, resetCustomer: boolean) => void; locked: boolean; readFence?: BuyerFence}

// Selection only reads the master. Buyer preparation is part of the existing
// durable SALES CREATE/EDIT intent, so unsaved invoice lines stay in the form.
export default function MandorShopBuyerPicker({action, initialCustomer, choice, onChange, locked, readFence}: Props) {
  const {runtime, identity} = useAuth()
  if (!isConnectedRuntime(runtime)) throw Error('Sesi penjualan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const allowed = identity.status === 'AUTHORIZED' && ['sales.invoice.view', 'finance.ar.view',
    action === 'EDIT' ? 'sales.invoice.edit_draft' : 'sales.invoice.create'].every(p => identity.permissions.includes(p))
  const [query, setQuery] = useState(''), [data, setData] = useState<MandorShopBuyerOptions | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [classifyFailed, setClassifyFailed] = useState(false)
  const [history, setHistory] = useState<(string | null)[]>([])
  const sequence = useRef(0), searched = useRef(''), resultTicket = useRef<SalesBuyerChoice['ticket']>(null), pageAfter = useRef<string | null>(null)
  const latest = useRef({choice, locked, allowed}); latest.current = {choice, locked, allowed}
  const currentReadTicket = readFence?.currentReadTicket, isReadCurrent = readFence?.isReadCurrent
  const current = useCallback((seq: number, ticket: SalesBuyerChoice['ticket']) => seq === sequence.current
    && latest.current.allowed && (!isReadCurrent || !!ticket && isReadCurrent(ticket)), [isReadCurrent])
  const classify = useCallback(async () => {
    if (!initialCustomer || !allowed || latest.current.locked) return
    const seq = ++sequence.current, ticket = currentReadTicket?.() ?? null
    setBusy(true); setError(''); setClassifyFailed(false); setData(null); resultTicket.current = null
    onChange({...latest.current.choice, ready: false, ticket: null}, false)
    try {
      if (currentReadTicket && !ticket) throw Error('Muat ulang invoice sebelum membaca pembelinya.')
      const r = await client.rpc('erp_cp7_get_mandor_shop_customer_buyer_v1', {p_sales_action: action, p_customer: initialCustomer})
      if (!current(seq, ticket)) return
      if (r.error) throw r.error
      onChange({...parseMandorShopCustomerBuyer(r.data, action, initialCustomer), ready: true, ticket}, false)
    } catch (e) {
      if (seq === sequence.current) { setError(normalizeClientError(e).message); setClassifyFailed(true) }
    } finally { if (seq === sequence.current) setBusy(false) }
  }, [initialCustomer, allowed, currentReadTicket, client, action, current, onChange])
  useEffect(() => { if (initialCustomer) void classify(); return () => { ++sequence.current } }, [initialCustomer, classify])
  const category = (value: 'TOKO' | 'MANDOR') => {
    if (locked || !allowed || value === choice.category && choice.ready) return
    ++sequence.current; setBusy(false); setData(null); setHistory([]); setError(''); setClassifyFailed(false); resultTicket.current = null
    onChange({category: value, mandor: null, ready: value === 'TOKO', ticket: null}, true)
  }
  const search = async (after: string | null = null, pages: (string | null)[] = [], continued = false) => {
    if (locked || !allowed || choice.category !== 'MANDOR') return
    const seq = ++sequence.current, ticket = currentReadTicket?.() ?? null, q = continued ? searched.current : query.trim()
    searched.current = q; setBusy(true); setData(null); setError(''); setClassifyFailed(false); resultTicket.current = null
    onChange({...choice, mandor: null, ready: false, ticket: null}, true)
    try {
      if (currentReadTicket && !ticket) throw Error('Muat ulang invoice sebelum membaca master mandor.')
      const r = await client.rpc('erp_cp7_get_mandor_shop_buyers_v1', {p_sales_action: action, p_query: q, p_after: after, p_limit: 25})
      if (!current(seq, ticket)) return
      if (r.error) throw r.error
      const parsed = parseMandorShopBuyerOptions(r.data, action)
      if (after && parsed.rows.some(row => row.contractor_id <= after)) throw Error('Urutan master mandor berubah. Cari ulang.')
      setData(parsed); setHistory(pages); pageAfter.current = after; resultTicket.current = ticket
    } catch (e) { if (seq === sequence.current) setError(normalizeClientError(e).message) }
    finally { if (seq === sequence.current) setBusy(false) }
  }
  const optionsCurrent = !isReadCurrent || !!resultTicket.current && isReadCurrent(resultTicket.current)
  return <section className="cproc-line" aria-label="Kategori pembeli invoice">
    <fieldset disabled={locked || !allowed || busy}><legend>Kategori pembeli</legend>
      <label><input type="radio" name="sales-buyer-category" value="TOKO" checked={choice.category === 'TOKO'} onChange={() => category('TOKO')}/>Toko</label>
      <label><input type="radio" name="sales-buyer-category" value="MANDOR" checked={choice.category === 'MANDOR'} onChange={() => category('MANDOR')}/>Mandor</label>
    </fieldset>
    {!allowed ? <p role="alert">Hak menyimpan invoice dan melihat piutang diperlukan.</p> : null}
    {busy ? <p role="status">Memuat identitas pembeli…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {classifyFailed ? <button type="button" disabled={locked || busy || !allowed} onClick={() => void classify()}>Baca ulang pembeli draft tersimpan</button> : null}
    {choice.category === 'MANDOR' ? <>
      <div className="cproc-inline"><label>Cari nama atau kode mandor<input aria-label="Cari mandor pembeli" value={query} maxLength={120}
        disabled={locked || busy || !allowed} onChange={e => setQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); void search() } }}/></label>
        <button type="button" disabled={locked || busy || !allowed} onClick={() => void search()}>Cari mandor</button></div>
      {data && optionsCurrent ? <div>{data.rows.map(row => <button type="button" className="cproc-receipt" key={row.contractor_id}
        disabled={locked || busy || !allowed || !row.can_select} aria-pressed={choice.mandor?.contractor_id === row.contractor_id}
        onClick={() => { if (optionsCurrent && !latest.current.locked && latest.current.allowed) onChange({category: 'MANDOR', mandor: row, ready: true, ticket: resultTicket.current}, true) }}>
        <strong>{row.code} · {row.name}</strong>{!row.can_select ? <span>Akun pembeli tidak aktif</span> : null}</button>)}</div> : null}
      {data && optionsCurrent && !data.rows.length ? <p>Tidak ada mandor aktif yang cocok.</p> : null}
      {data && optionsCurrent ? <div className="cproc-pagination"><button type="button" disabled={locked || busy || !history.length}
        onClick={() => void search(history.at(-1) ?? null, history.slice(0, -1), true)}>Mandor sebelumnya</button>
        <button type="button" disabled={locked || busy || !data.has_more} onClick={() => void search(data.next_after, [...history, pageAfter.current], true)}>Mandor berikutnya</button></div> : null}
      <p>Mandor terpilih: <strong>{salesBuyerCurrent(choice, readFence) ? `${choice.mandor?.code} · ${choice.mandor?.name}` : 'Pilih dan periksa mandor'}</strong></p>
    </> : null}
  </section>
}
