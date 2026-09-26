import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { ACCESSORY_POLICY_KEYS, ACTION_LABEL, POLICY_LABEL, PURPOSE_LABEL, SERVICE_ACTIONS, displayQty, displayRupiah, moneyText, normalizeMoney,
  parseAccessoryServiceWorkspace, policyValue, validateServiceResult, wholePcs, wibTimestamp,
  type AccessoryPolicyKey, type AccessoryServiceWorkspace, type Purpose, type ServiceAction, type ServiceLot, type ZoneKind } from './accessoryService'
import type { Json } from './types/database.preconnect'
import './initial-import.css'

type Tab = 'stock' | 'record' | 'returns' | 'documents' | 'settings'
type Filters = { query: string; location_id: string; page: number; action: string; status: string; document_id: string; card: [string, string] | null;
  note_query: string; customer_query: string }
type Line = { material_id: string; qty: string; at: string; purpose: Purpose; custody: string; outstanding: string }
const emptyLine = (): Line => ({ material_id: '', qty: '', at: '', purpose: 'FACTORY_USE', custody: '', outstanding: '' })
const TABS: [Tab, string][] = [['stock', 'Stok aksesori'], ['record', 'Catat transaksi'], ['returns', 'Barang kembali'], ['documents', 'Dokumen'], ['settings', 'Kebijakan & area']]
const STOCK_ACTIONS: ServiceAction[] = ['FILL_POST', 'RETURN_TO_WAREHOUSE', 'INTERNAL_USE', 'RECEIVE_RETURN', 'INSPECT', 'DISPOSE_STOCK', 'CLOSE_CUSTODY',
  'CUSTOMER_GARMENT_IN', 'CUSTOMER_GARMENT_OUT', 'COUNT_POST', 'RESOLVE_VARIANCE']
const MONEY_ACTIONS: ServiceAction[] = ['VALUE_CUSTODY', 'CREDIT_NOTE_RETURN', 'ROUND_NOTE']

export default function ConnectedAccessoryServicePage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel"><h1>Aksesori</h1><p>Masuk ke ERP yang tersambung untuk mencatat pemakaian dan pengembalian aksesori.</p></section>
  if (!identity.permissions.includes('warehouse.accessory.view')) return <section className="panel" role="alert"><h1>Aksesori</h1><p>Hak melihat aksesori diperlukan.</p></section>
  return <ServiceWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function ServiceWorkspace() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('ACCESSORY_SERVICE')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [data, setData] = useState<AccessoryServiceWorkspace | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<Tab>('stock')
  const filters = useRef<Filters>({ query: '', location_id: '', page: 1, action: '', status: '', document_id: '', card: null, note_query: '', customer_query: '' })
  const [query, setQuery] = useState(''), sequence = useRef(0)
  const load = useCallback(async () => {
    const number = ++sequence.current, ticket = beginRead(), f = filters.current
    const request: Record<string, Json> = { page: f.page, page_size: 25 }
    if (f.query) request.query = f.query
    if (f.location_id) request.location_id = f.location_id
    if (f.action) request.action = f.action
    if (f.status) request.status = f.status
    if (f.document_id) request.document_id = f.document_id
    if (f.card) { request.card_material_id = f.card[0]; request.card_location_id = f.card[1] }
    if (f.note_query) request.note_query = f.note_query
    if (f.customer_query) request.customer_query = f.customer_query
    setLoading(true); setError('')
    try {
      const result = await client.rpc('erp_get_accessory_service_workspace_v1', { p_filters: request })
      if (!isReadCurrent(ticket) || number !== sequence.current) return false
      if (result.error) throw result.error
      const value = parseAccessoryServiceWorkspace(result.data)
      if (f.document_id && value.document?.id !== f.document_id) throw new Error('Detail dokumen tidak cocok dengan pilihan.')
      setData(value)
      return finishRead(ticket)
    } catch (failure) {
      if (isReadCurrent(ticket) && number === sequence.current) setError(failure instanceof Error ? failure.message : normalizeClientError(failure).message)
      return false
    } finally { if (number === sequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load])
  const refresh = (patch: Partial<Filters>) => { Object.assign(filters.current, patch); void load() }
  const handlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_accessory_service_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (value, envelope) => {
      const p = envelope.payload as Record<string, Json>
      validateServiceResult(value, envelope.action, envelope.id, typeof p.document_id === 'string' ? p.document_id : null)
    },
    retire: () => { setData(null) },
    reload: load,
  }
  const send = (action: string, payload: Record<string, Json>) => { void run(action, payload, null, handlers) }
  const locked = mutation.writerLocked || loading || mutation.busy
  const canStock = identity.permissions.includes('warehouse.stock.adjust')
  const pages = (total: number) => Math.max(1, Math.ceil(total / 25))
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">GUDANG · AKSESORI</div><h1>Pemakaian & Pengembalian Aksesori</h1>
      <p>Stok siap pakai, pos servis, barang kembali yang menunggu pemeriksaan, titipan belum dinilai, dan barang rusak ditampilkan terpisah. Setiap transaksi memakai waktu fisik WIB dan dapat dibatalkan dengan transaksi kebalikan tertaut.</p></div>
      <button type="button" disabled={mutation.busy || loading} onClick={() => void load()}>Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert" className="initial-import-message">{error}</p>}
    <nav className="panel initial-import-toolbar" aria-label="Bagian aksesori">{TABS.map(([key, label]) =>
      <button key={key} type="button" aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}</nav>
    {!data ? <p role="status">{loading ? 'Memuat data aksesori…' : 'Data aksesori belum terbaca.'}</p> : <>
      {tab === 'stock' && <section className="panel initial-import-table" aria-label="Stok aksesori">
        <form className="initial-import-toolbar" onSubmit={e => { e.preventDefault(); refresh({ query: query.trim(), page: 1 }) }}>
          <label>Cari aksesori atau lokasi<input aria-label="Cari stok aksesori" maxLength={120} value={query} onChange={e => setQuery(e.target.value)}/></label>
          <label>Lokasi<select aria-label="Lokasi stok aksesori" value={filters.current.location_id} onChange={e => refresh({ location_id: e.target.value, page: 1 })}>
            <option value="">Semua lokasi</option>{data.locations.map(l => <option key={l.id} value={l.id}>{l.name} · {l.label}</option>)}</select></label>
          <button disabled={locked}>Cari stok</button></form>
        <table><thead><tr><th>Aksesori</th><th>Lokasi</th><th>Keadaan</th><th>Jumlah</th><th>Nilai</th><th>Terakhir</th><th/></tr></thead><tbody>{data.stock.map(s =>
          <tr key={s.material_id + s.location_id}><td>{s.sku} · {s.name}<br/><small>{s.category}</small></td><td>{s.location}</td><td>{s.bucket}</td>
            <td>{displayQty(s.qty)} {s.unit}</td><td>{displayRupiah(s.value)}</td><td>{s.updated_local}</td>
            <td><button type="button" disabled={locked} onClick={() => refresh({ card: [s.material_id, s.location_id] })}>Kartu stok {s.sku}</button></td></tr>)}</tbody></table>
        {data.stock.length === 0 && <p>Tidak ada stok aksesori yang cocok.</p>}
        <p>Halaman {data.page} dari {pages(data.stock_total)} · {data.stock_total} baris stok
          <button type="button" disabled={locked || data.page <= 1} onClick={() => refresh({ page: data.page - 1 })}>Sebelumnya</button>
          <button type="button" disabled={locked || data.page >= pages(Math.max(data.stock_total, data.documents_total))} onClick={() => refresh({ page: data.page + 1 })}>Berikutnya</button></p>
        {data.card && <section aria-label="Kartu stok aksesori"><h2>Kartu stok</h2><table><thead><tr><th>Waktu fisik</th><th>Dicatat</th><th>Jenis</th><th>Sebelum</th><th>Jumlah</th><th>Sesudah</th></tr></thead>
          <tbody>{data.card.rows.map(r => <tr key={r.movement_id}><td>{r.physical_local}</td><td>{r.recorded_local}</td><td>{r.movement_type} · {r.source_type}</td>
            <td>{displayQty(r.before)}</td><td>{displayQty(r.qty)}</td><td>{displayQty(r.after)}</td></tr>)}</tbody></table>
          <p>{data.card.rows.length} dari {data.card.total} gerakan. <button type="button" onClick={() => refresh({ card: null })}>Tutup kartu stok</button></p></section>}
      </section>}
      {tab === 'record' && <RecordForm data={data} locked={locked} canStock={canStock} send={send} search={refresh}/>}
      {tab === 'returns' && <Returns data={data}/>}
      {tab === 'documents' && <Documents data={data} locked={locked} filters={filters.current} query={query} setQuery={setQuery} refresh={refresh} send={send} pages={pages}/>}
      {tab === 'settings' && <Settings data={data} locked={locked} send={send}/>}
    </>}
  </section>
}

function lotLabel(l: ServiceLot) {
  return `${l.document || l.reference || 'Saldo awal'} · ${l.sku} · menunggu ${displayQty(l.state.waiting)} · layak ${displayQty(l.state.usable)} · rusak ${displayQty(l.state.damaged)} · ${l.value_status}`
}

function RecordForm({ data, locked, canStock, send, search }: { data: AccessoryServiceWorkspace; locked: boolean; canStock: boolean;
  send: (action: string, payload: Record<string, Json>) => void; search: (patch: Partial<Filters>) => void }) {
  const [action, setAction] = useState<ServiceAction>('FILL_POST')
  const [f, setF] = useState<Record<string, string>>({ reason: '' }), [lines, setLines] = useState<Line[]>([emptyLine()])
  const [review, setReview] = useState(false), [noteQuery, setNoteQuery] = useState(''), [customerQuery, setCustomerQuery] = useState('')
  const set = (patch: Record<string, string>) => { setF(v => ({ ...v, ...patch })); setReview(false) }
  const setLine = (i: number, patch: Partial<Line>) => { setLines(ls => ls.map((l, j) => j === i ? { ...l, ...patch } : l)); setReview(false) }
  const where = (kinds: ZoneKind[]) => data.locations.filter(l => kinds.includes(l.kind))
  const lots = data.lots.filter(l => Number(l.state.open) > 0)
  const materials = new Map<string, string>()
  for (const m of data.materials) materials.set(m.id, `${m.sku} · ${m.name}`)
  for (const s of data.stock) materials.set(s.material_id, `${s.sku} · ${s.name}`)
  const at = (key = 'at') => wibTimestamp(f[key] ?? '')
  const itemLines = (extra: (l: Line) => Record<string, Json> | null = () => ({})) => {
    const out: Record<string, Json>[] = []
    for (const l of lines) {
      const more = extra(l)
      if (!l.material_id || !wholePcs(l.qty) || more === null) return null
      out.push({ material_id: l.material_id, qty: l.qty.trim(), ...more })
    }
    return out.length ? out : null
  }
  const optional = (payload: Record<string, Json>) => {
    if ((f.responsible ?? '').trim()) payload.responsible = f.responsible.trim()
    if ((f.reference ?? '').trim()) payload.reference = f.reference.trim()
    return payload
  }
  const build = (): Record<string, Json> | string => {
    const reason = (f.reason ?? '').trim()
    if (!reason) return 'Isi alasan transaksi.'
    switch (action) {
      case 'FILL_POST': case 'RETURN_TO_WAREHOUSE': {
        const items = itemLines(), time = at()
        if (!f.from || !f.to || !items || !time) return 'Lengkapi lokasi asal/tujuan, waktu WIB, aksesori, dan jumlah PCS utuh.'
        return optional({ from_location_id: f.from, to_location_id: f.to, physical_at: time, items, reason })
      }
      case 'INTERNAL_USE': {
        const items = itemLines(l => { const time = wibTimestamp(l.at); if (!time) return null
          return { physical_at: time, purpose: l.purpose, ...(l.custody ? { customer_custody_id: l.custody } : {}) } })
        if (!f.location || !items) return 'Lengkapi lokasi, dan untuk setiap baris: aksesori, jumlah PCS utuh, waktu pakai WIB, tujuan.'
        return optional({ location_id: f.location, items, reason })
      }
      case 'RECEIVE_RETURN': {
        const kind = f.source_kind ?? '', time = at()
        if (!f.location || !time || !kind) return 'Pilih asal pengembalian, area pemeriksaan, dan waktu terima WIB.'
        const base: Record<string, Json> = { source_kind: kind, location_id: f.location, physical_at: time, reason }
        if (kind === 'NOTE_RETURN') {
          if (!wholePcs(f.qty ?? '') || !f.note_line) return 'Pilih baris nota mandor dan jumlah PCS yang dikembalikan.'
          const [source, lineId] = f.note_line.split(':')
          return optional({ ...base, [source === 'OPENING' ? 'opening_note_line_id' : 'note_item_id']: lineId, qty: f.qty.trim() })
        }
        const items = itemLines((l): Record<string, Json> => l.outstanding ? { outstanding_id: l.outstanding } : {})
        if (!items) return 'Lengkapi aksesori dan jumlah PCS utuh.'
        if (kind === 'SERVICE_LEFTOVER') { if (!f.from) return 'Pilih pos asal sisa servis.'; return optional({ ...base, from_location_id: f.from, items }) }
        if (!(f.reference ?? '').trim()) return 'Isi referensi (nomor servis/bongkaran) untuk barang kembali ini.'
        return optional({ ...base, items })
      }
      case 'INSPECT': {
        const time = at(), usable = f.qty_usable ?? '', damaged = f.qty_damaged ?? ''
        if (!f.lot || !time || !(f.inspector ?? '').trim() || (!wholePcs(usable) && !wholePcs(damaged))) return 'Pilih barang, waktu periksa WIB, pemeriksa, dan jumlah layak/rusak.'
        const payload: Record<string, Json> = { lot_id: f.lot, inspected_at: time, inspector: f.inspector.trim(), reason }
        if (wholePcs(usable)) { if (!f.usable_to) return 'Pilih gudang untuk barang layak.'; payload.qty_usable = usable.trim(); payload.usable_location_id = f.usable_to }
        if (wholePcs(damaged)) { if (!f.damaged_to) return 'Pilih area rusak.'; payload.qty_damaged = damaged.trim(); payload.damaged_location_id = f.damaged_to }
        return optional(payload)
      }
      case 'VALUE_CUSTODY': {
        const time = at()
        if (!f.lot || !f.condition || !wholePcs(f.qty ?? '') || !moneyText(f.unit_value ?? '') || !f.location || !time) return 'Lengkapi barang, kondisi, jumlah, nilai per buah, lokasi, dan waktu WIB.'
        return optional({ lot_id: f.lot, condition: f.condition, qty: f.qty.trim(), unit_value: normalizeMoney(f.unit_value), location_id: f.location, physical_at: time, reason })
      }
      case 'CREDIT_NOTE_RETURN': {
        const time = at()
        if (!f.lot || !f.condition || !wholePcs(f.qty ?? '') || !time) return 'Lengkapi barang retur nota, kondisi, jumlah, dan waktu WIB.'
        const payload: Record<string, Json> = { lot_id: f.lot, condition: f.condition, qty: f.qty.trim(), physical_at: time, reason }
        if (f.location) payload.location_id = f.location
        if (f.cash) payload.cash_account_id = f.cash
        return optional(payload)
      }
      case 'DISPOSE_STOCK': {
        const items = itemLines(), time = at()
        if (!f.location || !items || !time) return 'Pilih area rusak, waktu WIB, aksesori, dan jumlah.'
        return optional({ location_id: f.location, physical_at: time, items, reason })
      }
      case 'CLOSE_CUSTODY': {
        const time = at()
        if (!f.lot || !f.disposition || !f.condition || !wholePcs(f.qty ?? '') || !time) return 'Lengkapi barang, cara menutup, kondisi, jumlah, dan waktu WIB.'
        return optional({ lot_id: f.lot, disposition: f.disposition, condition: f.condition, qty: f.qty.trim(), physical_at: time, reason })
      }
      case 'CUSTOMER_GARMENT_IN': {
        const time = at()
        if (!f.customer || !(f.description ?? '').trim() || !wholePcs(f.qty ?? '') || !time) return 'Pilih pelanggan, isi keterangan barang, jumlah, dan waktu terima WIB.'
        return optional({ customer_id: f.customer, description: f.description.trim(), qty: f.qty.trim(), physical_at: time, reason })
      }
      case 'CUSTOMER_GARMENT_OUT': {
        const time = at()
        if (!f.custody || !time) return 'Pilih titipan pelanggan dan waktu kembali WIB.'
        return optional({ custody_id: f.custody, physical_at: time, reason })
      }
      case 'COUNT_POST': {
        const time = at(), items: Record<string, Json>[] = []
        for (const l of lines) { if (!l.material_id || !/^\d{1,12}$/.test(l.qty.trim())) return 'Isi aksesori dan jumlah hitung (boleh 0).'; items.push({ material_id: l.material_id, counted_qty: l.qty.trim() }) }
        if (!f.location || !time || !items.length) return 'Pilih pos servis dan waktu hitung WIB.'
        return optional({ location_id: f.location, physical_at: time, items, reason })
      }
      case 'RESOLVE_VARIANCE': {
        const time = at()
        if (!f.variance || !f.resolution || !time) return 'Pilih selisih, keputusan, dan waktu WIB.'
        return optional({ variance_id: f.variance, resolution: f.resolution, physical_at: time, reason })
      }
      case 'ROUND_NOTE':
        if (!f.issue) return 'Pilih nota mandor yang dibulatkan.'
        return optional({ issue_id: f.issue, reason })
      case 'ALLOCATE_CARRY':
        return 'Bawa kredit ke payroll dari detail dokumen kredit (bagian Dokumen).'
    }
  }
  const built = build(), payload = typeof built === 'string' ? null : built
  const permitted = STOCK_ACTIONS.includes(action) ? canStock : MONEY_ACTIONS.includes(action) ? data.is_admin : true
  const multi = ['FILL_POST', 'RETURN_TO_WAREHOUSE', 'INTERNAL_USE', 'DISPOSE_STOCK', 'COUNT_POST'].includes(action)
    || (action === 'RECEIVE_RETURN' && f.source_kind && f.source_kind !== 'NOTE_RETURN')
  const locationSelect = (key: string, label: string, kinds: ZoneKind[]) => <label>{label}<select aria-label={label} disabled={locked} value={f[key] ?? ''} onChange={e => set({ [key]: e.target.value })}>
    <option value="">Pilih lokasi</option>{where(kinds).map(l => <option key={l.id} value={l.id}>{l.name} · {l.label}</option>)}</select></label>
  const timeInput = (key = 'at', label = 'Waktu fisik (WIB)') => <label>{label}<input aria-label={label} type="datetime-local" step="1" disabled={locked}
    value={f[key] ?? ''} onChange={e => set({ [key]: e.target.value })}/></label>
  const lotSelect = (filter: (l: ServiceLot) => boolean = () => true) => <label>Barang kembali<select aria-label="Barang kembali" disabled={locked} value={f.lot ?? ''} onChange={e => set({ lot: e.target.value })}>
    <option value="">Pilih barang</option>{lots.filter(filter).map(l => <option key={l.id} value={l.id}>{lotLabel(l)}</option>)}</select></label>
  const choice = (key: string, label: string, options: [string, string][]) => <label>{label}<select aria-label={label} disabled={locked} value={f[key] ?? ''} onChange={e => set({ [key]: e.target.value })}>
    <option value="">Pilih</option>{options.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></label>
  const input = (key: string, label: string, mode: 'numeric' | 'decimal' | 'text' = 'text') => <label>{label}<input aria-label={label} inputMode={mode} maxLength={200}
    disabled={locked} value={f[key] ?? ''} onChange={e => set({ [key]: e.target.value })}/></label>
  return <section className="panel initial-import-advances" aria-label="Catat transaksi aksesori">
    <h2>Catat transaksi</h2>
    <label>Jenis transaksi<select aria-label="Jenis transaksi aksesori" disabled={locked} value={action} onChange={e => { setAction(e.target.value as ServiceAction); setF({ reason: f.reason ?? '' }); setLines([emptyLine()]); setReview(false) }}>
      {SERVICE_ACTIONS.filter(a => a !== 'ALLOCATE_CARRY').map(a => <option key={a} value={a}>{ACTION_LABEL[a]}</option>)}</select></label>
    {!permitted && <p role="status">{MONEY_ACTIONS.includes(action) ? 'Transaksi bernilai hanya untuk owner/admin dengan hak keuangan.' : 'Hak penyesuaian stok gudang diperlukan.'}</p>}
    <div className="initial-import-toolbar">
      {action === 'FILL_POST' && <>{locationSelect('from', 'Gudang asal', ['MAIN'])}{locationSelect('to', 'Pos servis tujuan', ['SERVICE_POST'])}{timeInput()}</>}
      {action === 'RETURN_TO_WAREHOUSE' && <>{locationSelect('from', 'Pos servis asal', ['SERVICE_POST'])}{locationSelect('to', 'Gudang tujuan', ['MAIN'])}{timeInput()}</>}
      {action === 'INTERNAL_USE' && locationSelect('location', 'Lokasi pemakaian', ['MAIN', 'SERVICE_POST'])}
      {action === 'RECEIVE_RETURN' && <>{choice('source_kind', 'Asal pengembalian', [['SERVICE_LEFTOVER', 'Sisa pos servis'], ['TEARDOWN', 'Bongkaran / barang yang ditunggu'],
        ['NOTE_RETURN', 'Retur nota mandor'], ['LEGACY', 'Histori lama tanpa sumber (owner/admin)']])}{locationSelect('location', 'Area pemeriksaan', ['INSPECTION'])}{timeInput('at', 'Waktu terima (WIB)')}
        {f.source_kind === 'SERVICE_LEFTOVER' && locationSelect('from', 'Pos asal', ['SERVICE_POST'])}</>}
      {action === 'INSPECT' && <>{lotSelect(l => Number(l.state.waiting) > 0)}{timeInput('at', 'Waktu periksa (WIB)')}{input('inspector', 'Pemeriksa')}
        {input('qty_usable', 'Jumlah layak', 'numeric')}{locationSelect('usable_to', 'Gudang barang layak', ['MAIN'])}
        {input('qty_damaged', 'Jumlah rusak', 'numeric')}{locationSelect('damaged_to', 'Area rusak', ['DAMAGED'])}</>}
      {action === 'VALUE_CUSTODY' && <>{lotSelect(l => l.value_status === 'Belum dinilai')}{choice('condition', 'Kondisi', [['USABLE', 'Layak'], ['DAMAGED', 'Rusak']])}
        {input('qty', 'Jumlah PCS', 'numeric')}{input('unit_value', 'Nilai per buah (Rp)', 'decimal')}
        {locationSelect('location', f.condition === 'DAMAGED' ? 'Area rusak' : 'Gudang tujuan', f.condition === 'DAMAGED' ? ['DAMAGED'] : ['MAIN'])}{timeInput()}</>}
      {action === 'CREDIT_NOTE_RETURN' && <>{lotSelect(l => l.owner_kind === 'MANDOR')}{choice('condition', 'Kondisi', [['USABLE', 'Layak'], ['DAMAGED', 'Rusak']])}
        {input('qty', 'Jumlah PCS', 'numeric')}{locationSelect('location', 'Lokasi stok hasil kredit (bila dipakai)', f.condition === 'DAMAGED' ? ['DAMAGED'] : ['MAIN'])}
        {data.cash_accounts && choice('cash', 'Rekening refund (bila kebijakan refund)', data.cash_accounts.map(c => [c.id, c.name]))}{timeInput()}</>}
      {action === 'DISPOSE_STOCK' && <>{locationSelect('location', 'Area rusak', ['DAMAGED'])}{timeInput()}</>}
      {action === 'CLOSE_CUSTODY' && <>{lotSelect()}{choice('disposition', 'Cara menutup', [['RETURN_TO_OWNER', 'Dikembalikan ke pemilik'], ['DISCARD', 'Dibuang']])}
        {choice('condition', 'Kondisi', [['WAITING', 'Belum diperiksa'], ['USABLE', 'Layak'], ['DAMAGED', 'Rusak']])}{input('qty', 'Jumlah PCS', 'numeric')}{timeInput()}</>}
      {action === 'CUSTOMER_GARMENT_IN' && <>
        <label>Cari pelanggan<input aria-label="Cari pelanggan titipan" maxLength={120} disabled={locked} value={customerQuery} onChange={e => setCustomerQuery(e.target.value)}/></label>
        <button type="button" disabled={locked || !customerQuery.trim()} onClick={() => search({ customer_query: customerQuery.trim() })}>Cari pelanggan</button>
        {choice('customer', 'Pelanggan', (data.customers ?? []).map(c => [c.id, `${c.code} · ${c.name}`]))}{input('description', 'Keterangan barang')}{input('qty', 'Jumlah PCS', 'numeric')}{timeInput('at', 'Waktu terima (WIB)')}</>}
      {action === 'CUSTOMER_GARMENT_OUT' && <>{choice('custody', 'Titipan pelanggan', data.customer_custody.filter(c => !c.returned).map(c => [c.id, `${c.customer} · ${c.description} · ${displayQty(c.qty)} PCS`]))}{timeInput('at', 'Waktu kembali (WIB)')}</>}
      {action === 'COUNT_POST' && <>{locationSelect('location', 'Pos servis', ['SERVICE_POST'])}{timeInput('at', 'Waktu hitung (WIB)')}</>}
      {action === 'RESOLVE_VARIANCE' && <>{choice('variance', 'Selisih hitung', data.variances.filter(v => !v.resolved).map(v => [v.id, `${materials.get(v.material_id) ?? v.material_id} · buku ${displayQty(v.book)} · hitung ${displayQty(v.counted)} · selisih ${displayQty(v.variance)}`]))}
        {choice('resolution', 'Keputusan', [['LOSS', 'Hilang (dicatat sebagai kerugian)'], ['DISMISS', 'Hitung ulang — buku tetap']])}{timeInput()}</>}
    </div>
    {(action === 'ROUND_NOTE' || (action === 'RECEIVE_RETURN' && f.source_kind === 'NOTE_RETURN')) && <div className="initial-import-toolbar">
      <label>Cari nota mandor<input aria-label="Cari nota mandor" maxLength={120} disabled={locked} value={noteQuery} onChange={e => setNoteQuery(e.target.value)}/></label>
      <button type="button" disabled={locked || !noteQuery.trim()} onClick={() => search({ note_query: noteQuery.trim() })}>Cari nota</button>
      {action === 'ROUND_NOTE' ? choice('issue', 'Nota mandor', [...new Map((data.notes ?? []).map(n => [n.issue_id, `${n.number} · ${n.contractor}`])).entries()])
        : <>{choice('note_line', 'Baris nota', [...(data.notes ?? []).map(n => [`NOTE:${n.item_id}`, `${n.number} · ${n.contractor} · ${n.sku} · ${displayQty(n.qty)} PCS · kembali ${displayQty(n.returned)}`] as [string, string]),
          ...(data.opening_notes ?? []).map(n => [`OPENING:${n.line_id}`, `${n.number} (saldo awal) · ${n.contractor} · ${n.sku} · ${displayQty(n.qty)} PCS · kembali ${displayQty(n.returned)}`] as [string, string])])}
          {input('qty', 'Jumlah PCS kembali', 'numeric')}</>}</div>}
    {multi && <div className="initial-import-table"><table><thead><tr><th>Aksesori</th><th>{action === 'COUNT_POST' ? 'Jumlah hitung' : 'Jumlah PCS'}</th>
      {action === 'INTERNAL_USE' && <><th>Waktu pakai (WIB)</th><th>Tujuan</th><th>Titipan pelanggan</th></>}
      {action === 'RECEIVE_RETURN' && f.source_kind !== 'SERVICE_LEFTOVER' && <th>Barang yang ditunggu</th>}<th/></tr></thead>
      <tbody>{lines.map((l, i) => <tr key={i}>
        <td><select aria-label={`Aksesori baris ${i + 1}`} disabled={locked} value={l.material_id} onChange={e => setLine(i, { material_id: e.target.value })}>
          <option value="">Pilih aksesori</option>{[...materials.entries()].map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></td>
        <td><input aria-label={`Jumlah baris ${i + 1}`} inputMode="numeric" disabled={locked} value={l.qty} onChange={e => setLine(i, { qty: e.target.value })}/></td>
        {action === 'INTERNAL_USE' && <>
          <td><input aria-label={`Waktu pakai baris ${i + 1}`} type="datetime-local" step="1" disabled={locked} value={l.at} onChange={e => setLine(i, { at: e.target.value })}/></td>
          <td><select aria-label={`Tujuan baris ${i + 1}`} disabled={locked} value={l.purpose} onChange={e => setLine(i, { purpose: e.target.value as Purpose })}>
            {Object.entries(PURPOSE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
          <td><select aria-label={`Titipan baris ${i + 1}`} disabled={locked || l.purpose !== 'CUSTOMER_SERVICE'} value={l.custody} onChange={e => setLine(i, { custody: e.target.value })}>
            <option value="">Tanpa titipan</option>{data.customer_custody.filter(c => !c.returned).map(c => <option key={c.id} value={c.id}>{c.customer} · {c.description}</option>)}</select></td></>}
        {action === 'RECEIVE_RETURN' && f.source_kind !== 'SERVICE_LEFTOVER' && <td><select aria-label={`Barang ditunggu baris ${i + 1}`} disabled={locked} value={l.outstanding}
          onChange={e => setLine(i, { outstanding: e.target.value })}><option value="">Bukan barang yang ditunggu</option>
          {data.outstanding.filter(o => o.material_id === l.material_id).map(o => <option key={o.id} value={o.id}>{o.holder || o.reference} · sisa {displayQty(String(Number(o.expected) - Number(o.received)))}</option>)}</select></td>}
        <td><button type="button" disabled={locked || lines.length === 1} onClick={() => setLines(ls => ls.filter((_, j) => j !== i))}>Hapus baris {i + 1}</button></td></tr>)}</tbody></table>
      <button type="button" disabled={locked || lines.length >= 100} onClick={() => setLines(ls => [...ls, emptyLine()])}>Tambah baris</button>
      <div className="initial-import-toolbar"><label>Cari aksesori lain<input aria-label="Cari aksesori transaksi" maxLength={120} disabled={locked}
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); search({ query: (e.target as HTMLInputElement).value.trim() }) } }}/></label></div></div>}
    <div className="initial-import-toolbar">{input('responsible', 'Penanggung jawab (opsional)')}{input('reference', action === 'RECEIVE_RETURN' && f.source_kind !== 'SERVICE_LEFTOVER' && f.source_kind !== 'NOTE_RETURN' ? 'Referensi servis/bongkaran' : 'Referensi (opsional)')}
      {input('reason', 'Alasan transaksi')}</div>
    {typeof built === 'string' && <p role="status">{built}</p>}
    <button type="button" disabled={locked || !payload || !permitted} onClick={() => setReview(true)}>Periksa transaksi</button>
    {review && payload && <section className="initial-import-message" aria-label="Konfirmasi transaksi aksesori"><p>Sahkan {ACTION_LABEL[action].toLowerCase()}? Transaksi ini dapat dibatalkan hanya dengan transaksi kebalikan tertaut.</p>
      <button type="button" disabled={locked} onClick={() => { send(action, payload); setReview(false) }}>Sahkan {ACTION_LABEL[action].toLowerCase()}</button>
      <button type="button" onClick={() => setReview(false)}>Kembali</button></section>}
  </section>
}

function Returns({ data }: { data: AccessoryServiceWorkspace }) {
  return <section className="panel initial-import-table" aria-label="Barang kembali dan titipan">
    <h2>Barang kembali</h2><p>Barang yang menunggu pemeriksaan, titipan belum dinilai, dan milik mandor tidak dihitung sebagai stok siap pakai.</p>
    <table><thead><tr><th>Dokumen / referensi</th><th>Aksesori</th><th>Asal</th><th>Diterima</th><th>Menunggu</th><th>Layak</th><th>Rusak</th><th>Dikredit</th><th>Status nilai</th></tr></thead>
      <tbody>{data.lots.map(l => <tr key={l.id}><td>{l.document || l.reference || 'Saldo awal'}</td><td>{l.sku} · {l.name}</td><td>{l.source_kind} · {l.owner_kind === 'MANDOR' ? 'Milik mandor' : 'Perusahaan'}</td>
        <td>{l.received_local}</td><td>{displayQty(l.state.waiting)}</td><td>{displayQty(l.state.usable)}</td><td>{displayQty(l.state.damaged)}</td><td>{displayQty(l.state.credited)}</td><td>{l.value_status}</td></tr>)}</tbody></table>
    {data.lots.length === 0 && <p>Belum ada barang kembali.</p>}
    <h2>Belum kembali</h2><table><thead><tr><th>Pemegang</th><th>Keterangan</th><th>Ditunggu</th><th>Sudah diterima</th><th>Status</th></tr></thead>
      <tbody>{data.outstanding.map(o => <tr key={o.id}><td>{o.holder || '—'}</td><td>{o.description || o.reference}</td><td>{displayQty(o.expected)}</td><td>{displayQty(o.received)}</td><td>{o.label}</td></tr>)}</tbody></table>
    {data.outstanding.length === 0 && <p>Tidak ada barang yang ditunggu.</p>}
    <h2>Titipan pelanggan</h2><table><thead><tr><th>Pelanggan</th><th>Barang</th><th>Jumlah</th><th>Diterima</th><th>Status</th></tr></thead>
      <tbody>{data.customer_custody.map(c => <tr key={c.id}><td>{c.customer}</td><td>{c.description}</td><td>{displayQty(c.qty)}</td><td>{c.received_local}</td><td>{c.returned ? 'Sudah dikembalikan' : 'Milik pelanggan — dititipkan'}</td></tr>)}</tbody></table>
    {data.customer_custody.length === 0 && <p>Tidak ada titipan pelanggan.</p>}
    <h2>Selisih hitung pos</h2><table><thead><tr><th>Buku</th><th>Hitung</th><th>Selisih</th><th>Status</th></tr></thead>
      <tbody>{data.variances.map(v => <tr key={v.id}><td>{displayQty(v.book)}</td><td>{displayQty(v.counted)}</td><td>{displayQty(v.variance)}</td><td>{v.resolved ? 'Sudah diputuskan' : v.label}</td></tr>)}</tbody></table>
    {data.variances.length === 0 && <p>Tidak ada selisih hitung.</p>}
  </section>
}

function Documents({ data, locked, filters, query, setQuery, refresh, send, pages }: { data: AccessoryServiceWorkspace; locked: boolean; filters: Filters;
  query: string; setQuery: (value: string) => void
  refresh: (patch: Partial<Filters>) => void; send: (action: string, payload: Record<string, Json>) => void; pages: (total: number) => number }) {
  const [reason, setReason] = useState(''), [review, setReview] = useState(false), [payroll, setPayroll] = useState('')
  const d = data.document
  const carry = d?.events.find(e => e.kind === 'CREDIT' && e.carry_remaining !== null && Number(e.carry_remaining) > 0)
  // The search text and location are shared with the stock tab and also narrow this list, so they are shown and can be cleared here.
  const place = data.locations.find(l => l.id === filters.location_id)
  const narrowed = filters.query !== '' || filters.location_id !== ''
  return <section className="panel initial-import-table" aria-label="Dokumen aksesori">
    <form className="initial-import-toolbar" onSubmit={e => { e.preventDefault(); refresh({ query: query.trim(), page: 1 }) }}>
      <label>Cari nomor, referensi, penanggung jawab, atau alasan<input aria-label="Cari dokumen aksesori" maxLength={120} value={query} onChange={e => setQuery(e.target.value)}/></label>
      <button disabled={locked}>Cari dokumen</button>
      {narrowed && <button type="button" disabled={locked} onClick={() => { setQuery(''); refresh({ query: '', location_id: '', page: 1 }) }}>Hapus pencarian</button>}</form>
    {narrowed && <p role="status">Pencarian aktif{filters.query ? ` "${filters.query}"` : ''}{filters.location_id ? ` · lokasi ${place ? place.name : 'terpilih'}` : ''}: dokumen di luar pencarian ini tidak ditampilkan.</p>}
    <div className="initial-import-toolbar">
      <label>Jenis<select aria-label="Jenis dokumen aksesori" disabled={locked} value={filters.action} onChange={e => refresh({ action: e.target.value, page: 1 })}>
        <option value="">Semua</option>{SERVICE_ACTIONS.map(a => <option key={a} value={a}>{ACTION_LABEL[a]}</option>)}</select></label>
      <label>Status<select aria-label="Status dokumen aksesori" disabled={locked} value={filters.status} onChange={e => refresh({ status: e.target.value, page: 1 })}>
        <option value="">Semua</option><option value="POSTED">Disahkan</option><option value="REVERSED">Dibatalkan</option></select></label></div>
    <table><thead><tr><th>Nomor</th><th>Jenis</th><th>Waktu fisik</th><th>Dicatat</th><th>Status</th><th>Alasan</th><th/></tr></thead>
      <tbody>{data.documents.map(x => <tr key={x.id}><td>{x.number}</td><td>{ACTION_LABEL[x.action as ServiceAction] ?? x.action}</td><td>{x.physical_local}</td><td>{x.recorded_local}</td>
        <td>{x.status === 'POSTED' ? 'Disahkan' : 'Dibatalkan'}</td><td>{x.reason}</td><td><button type="button" disabled={locked} onClick={() => { setReview(false); refresh({ document_id: x.id }) }}>Buka {x.number}</button></td></tr>)}</tbody></table>
    {data.documents.length === 0 && <p>Belum ada dokumen yang cocok.</p>}
    <p>Halaman {data.page} dari {pages(data.documents_total)} · {data.documents_total} dokumen
      <button type="button" disabled={locked || data.page <= 1} onClick={() => refresh({ page: data.page - 1 })}>Dokumen sebelumnya</button>
      <button type="button" disabled={locked || data.page >= pages(data.documents_total)} onClick={() => refresh({ page: data.page + 1 })}>Dokumen berikutnya</button></p>
    {d && <section aria-label="Detail dokumen aksesori"><h2>{d.number} · {ACTION_LABEL[d.action as ServiceAction] ?? d.action} · {d.status === 'POSTED' ? 'Disahkan' : 'Dibatalkan'}</h2>
      {Object.keys(d.policy_versions).length > 0 && <p>Kebijakan yang dipakai: {Object.entries(d.policy_versions).map(([k, v]) => `${k} versi ${String(v)}`).join(', ')}</p>}
      {d.reversal_reason && <p>Alasan pembatalan: {d.reversal_reason}</p>}
      {d.events.length > 0 && <table><thead><tr><th>Kejadian</th><th>Kondisi</th><th>Jumlah</th><th>Layak</th><th>Rusak</th><th>Pemeriksa</th><th>Nominal</th><th>Kurangi tagihan</th><th>Dibawa payroll</th><th>Refund</th></tr></thead>
        <tbody>{d.events.map(e => <tr key={e.id}><td>{e.kind}</td><td>{e.condition ?? '—'}</td><td>{displayQty(e.qty)}</td><td>{e.qty_usable === null ? '—' : displayQty(e.qty_usable)}</td>
          <td>{e.qty_damaged === null ? '—' : displayQty(e.qty_damaged)}</td><td>{e.inspector ?? '—'}</td><td>{e.amount === null ? '—' : displayRupiah(e.amount)}</td>
          <td>{e.unpaid === null ? '—' : displayRupiah(e.unpaid)}</td><td>{e.carry === null ? '—' : displayRupiah(e.carry)}</td><td>{e.refund === null ? '—' : displayRupiah(e.refund)}</td></tr>)}</tbody></table>}
      <p>{d.links.length} transaksi tertaut: {d.links.map(k => k.kind).join(', ') || '—'}</p>
      {d.events.some(e => e.carry_payroll_lines && e.carry_payroll_lines.length > 0) && <table aria-label="Hak mandor di payroll"><thead><tr><th>Payroll</th><th>Periode sampai</th><th>Status</th><th>Hak mandor</th></tr></thead>
        <tbody>{d.events.flatMap(e => (e.carry_payroll_lines ?? []).map(t => <tr key={`${e.id}-${t.payroll_id}`}><td>{t.payroll_number}</td><td>{t.period_end}</td>
          <td>{t.status}</td><td>{displayRupiah(t.amount)}</td></tr>))}</tbody></table>}
      {carry && d.status === 'POSTED' && <div className="initial-import-toolbar" aria-label="Bawa kredit ke payroll"><span>Hak mandor yang belum dibayar: {displayRupiah(carry.carry_remaining)} · dibayar sekali penuh lewat payroll berikutnya</span>
        <label>Payroll berikutnya<select aria-label="Payroll kredit retur" disabled={locked} value={payroll} onChange={e => setPayroll(e.target.value)}>
          <option value="">Pilih payroll</option>{d.carry_payrolls.filter(p => p.is_next).map(p => <option key={p.id} value={p.id}>{p.number} · {p.status} · {p.period_end}</option>)}</select></label>
        {d.carry_payrolls.every(p => !p.is_next) && <span role="status">Belum ada payroll draft mandor ini sejak tanggal kredit; hak mandor menunggu payroll berikutnya.</span>}
        <button type="button" disabled={locked || !payroll || !carry.carry_remaining || !reason.trim()} onClick={() => carry.carry_remaining && send('ALLOCATE_CARRY', {
          event_id: carry.id, payroll_id: payroll, amount: carry.carry_remaining, reason: reason.trim() })}>Bawa ke payroll</button></div>}
      {d.status === 'POSTED' && <><label>Alasan<input aria-label="Alasan dokumen aksesori" maxLength={1000} disabled={locked} value={reason} onChange={e => { setReason(e.target.value); setReview(false) }}/></label>
        <button type="button" disabled={locked || !reason.trim()} onClick={() => setReview(true)}>Periksa pembatalan</button>
        {review && <section className="initial-import-message" aria-label="Konfirmasi pembatalan aksesori"><p>Batalkan {d.number} dengan transaksi kebalikan tertaut? Dokumen yang sudah dipakai dokumen lain harus dibatalkan lebih dahulu.</p>
          <button type="button" disabled={locked} onClick={() => { send('REVERSE', { document_id: d.id, expected_version: d.row_version, reason: reason.trim() }); setReview(false) }}>Sahkan pembatalan {d.number}</button>
          <button type="button" onClick={() => setReview(false)}>Kembali</button></section>}</>}
      <button type="button" disabled={locked} onClick={() => refresh({ document_id: '' })}>Tutup detail</button></section>}
  </section>
}

function Settings({ data, locked, send }: { data: AccessoryServiceWorkspace; locked: boolean; send: (action: string, payload: Record<string, Json>) => void }) {
  const [key, setKey] = useState<AccessoryPolicyKey>('ACC-DEC01'), [fields, setFields] = useState<Record<string, string>>({}), [reason, setReason] = useState('')
  const [zone, setZone] = useState({ zone_kind: 'SERVICE_POST', location_code: '', location_name: '', reason: '' })
  const policy = data.policies.find(p => p.key === key)!
  const value = policyValue(key, fields)
  const set = (patch: Record<string, string>) => setFields(v => ({ ...v, ...patch }))
  const accounts = (types: string[]) => (data.accounts ?? []).filter(a => types.includes(a.type))
  const accountSelect = (field: string, label: string, types: string[]) => <label>{label}<select aria-label={label} disabled={locked} value={fields[field] ?? ''} onChange={e => set({ [field]: e.target.value })}>
    <option value="">Pilih akun</option>{accounts(types).map(a => <option key={a.id} value={a.id}>{a.code} · {a.name}</option>)}</select></label>
  const submit = (operation: 'SET' | 'CLEAR') => send('SET_POLICY', { policy_key: key.replace('-', '_'), operation, expected_version: policy.version, reason: reason.trim(),
    ...(operation === 'SET' && typeof value !== 'string' ? { value } : {}) })
  return <section className="panel initial-import-advances" aria-label="Kebijakan aksesori">
    <h2>Kebijakan aksesori</h2><p>Setiap kebijakan menunggu nilai dari owner. Selama menunggu, transaksi yang memerlukannya ditolak; tidak ada nilai bawaan.</p>
    <div className="initial-import-table"><table><thead><tr><th>Kebijakan</th><th>Status</th><th>Versi</th><th>Isi</th></tr></thead><tbody>{data.policies.map(p =>
      <tr key={p.key}><td>{p.key} · {POLICY_LABEL[p.key]}</td><td>{p.status === 'SET' ? 'Ditetapkan' : 'Menunggu keputusan owner'}</td><td>{p.version}</td>
        <td>{p.value === null ? (p.status === 'SET' ? 'Hanya terlihat owner/admin' : '—') : <code>{JSON.stringify(p.value)}</code>}</td></tr>)}</tbody></table></div>
    {data.is_admin ? <>
      <label>Kebijakan<select aria-label="Kebijakan yang diubah" disabled={locked} value={key} onChange={e => { setKey(e.target.value as AccessoryPolicyKey); setFields({}) }}>
        {ACCESSORY_POLICY_KEYS.map(k => <option key={k} value={k}>{k} · {POLICY_LABEL[k]}</option>)}</select></label>
      <div className="initial-import-toolbar">
        {key === 'ACC-DEC01' && <p>Kedua garis waktu nyata: barang kembali lebih dulu lalu diperiksa kemudian, atau kembali dan diperiksa sekarang.</p>}
        {key === 'ACC-DEC03' && <>{accountSelect('credit_account_id', 'Akun pengakuan nilai titipan', ['REVENUE', 'EXPENSE'])}
          <label>Batas nilai per buah<select aria-label="Batas nilai per buah" disabled={locked} value={fields.unit_value_cap ?? ''} onChange={e => set({ unit_value_cap: e.target.value })}>
            <option value="">Pilih</option><option value="MOVING_AVERAGE">Tidak melebihi rata-rata stok</option><option value="NONE">Tanpa batas</option></select></label></>}
        {key === 'ACC-DEC04' && <>{accountSelect('CUSTOMER_SERVICE_account_id', 'Akun biaya servis pelanggan', ['EXPENSE'])}{accountSelect('OWN_FG_REPAIR_account_id', 'Akun biaya perbaikan barang jadi', ['EXPENSE'])}</>}
        {key === 'ACC-DEC05' && <><label>Cara kredit<select aria-label="Cara kredit retur" disabled={locked} value={fields.mode ?? ''} onChange={e => set({ mode: e.target.value })}>
          <option value="">Pilih</option><option value="CREDIT_UNPAID_ONLY">Hanya mengurangi tagihan yang belum dibayar</option>
          <option value="CREDIT_THEN_CARRY">Kurangi tagihan, sisanya dibawa ke payroll</option><option value="CREDIT_THEN_REFUND">Kurangi tagihan, sisanya dikembalikan tunai</option></select></label>
          <label>Kondisi yang dikredit (USABLE, DAMAGED)<input aria-label="Kondisi dikredit" disabled={locked} value={fields.credit_conditions ?? ''} onChange={e => set({ credit_conditions: e.target.value.toUpperCase() })}/></label></>}
        {key === 'ACC-DEC06' && <>{accountSelect('gain_account_id', 'Akun pembulatan naik', ['REVENUE', 'EXPENSE'])}{accountSelect('loss_account_id', 'Akun pembulatan turun', ['REVENUE', 'EXPENSE'])}</>}
        {key === 'ACC-DEC07' && <><label>Persetujuan owner<select aria-label="Persetujuan owner biaya aksesori" disabled={locked} value={fields.approval_mode ?? ''} onChange={e => set({ approval_mode: e.target.value })}>
            <option value="">Pilih</option><option value="NONE">Tanpa persetujuan owner (sementara)</option><option value="ABOVE">Perlu persetujuan di atas batas nilai</option></select></label>
          {fields.approval_mode === 'ABOVE' && <label>Persetujuan owner di atas nilai (Rp)<input aria-label="Batas persetujuan owner" inputMode="decimal" disabled={locked} value={fields.owner_approval_above ?? ''} onChange={e => set({ owner_approval_above: e.target.value })}/></label>}
          <label>Petugas area {'{lokasi: [pengguna]}'}<input aria-label="Petugas area" disabled={locked} value={fields.zone_users ?? ''} onChange={e => set({ zone_users: e.target.value })}/></label>
          <p>Pengguna: {(data.users ?? []).map(u => `${u.name} (${u.id})`).join(', ') || '—'}</p></>}
        {key === 'ERP-DEC02' && <label>Kategori gratis mandor Special<select aria-label="Kategori gratis" multiple disabled={locked}
          value={(fields.special_free_category_ids ?? '').split(',').filter(Boolean)} onChange={e => set({ special_free_category_ids: [...e.target.selectedOptions].map(o => o.value).join(',') })}>
          {(data.categories ?? []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
      </div>
      <label>Alasan perubahan kebijakan<input aria-label="Alasan kebijakan aksesori" maxLength={1000} disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      {typeof value === 'string' && <p role="status">{value}</p>}
      <button type="button" disabled={locked || typeof value === 'string' || !reason.trim()} onClick={() => submit('SET')}>Tetapkan {key}</button>
      <button type="button" disabled={locked || policy.status !== 'SET' || !reason.trim()} onClick={() => submit('CLEAR')}>Kembalikan {key} ke menunggu</button>
      <h2>Area aksesori</h2><p>Pos servis, area pemeriksaan, dan area rusak adalah lokasi gudang bahan khusus aksesori; nota mandor dan transfer biasa tidak memakainya.</p>
      <div className="initial-import-toolbar">
        <label>Jenis area<select aria-label="Jenis area aksesori" disabled={locked} value={zone.zone_kind} onChange={e => setZone({ ...zone, zone_kind: e.target.value })}>
          <option value="SERVICE_POST">Pos servis</option><option value="INSPECTION">Area pemeriksaan</option><option value="DAMAGED">Area rusak</option></select></label>
        <label>Kode lokasi<input aria-label="Kode area aksesori" maxLength={40} disabled={locked} value={zone.location_code} onChange={e => setZone({ ...zone, location_code: e.target.value })}/></label>
        <label>Nama lokasi<input aria-label="Nama area aksesori" maxLength={120} disabled={locked} value={zone.location_name} onChange={e => setZone({ ...zone, location_name: e.target.value })}/></label>
        <label>Alasan<input aria-label="Alasan area aksesori" maxLength={1000} disabled={locked} value={zone.reason} onChange={e => setZone({ ...zone, reason: e.target.value })}/></label>
        <button type="button" disabled={locked || !zone.location_code.trim() || !zone.location_name.trim() || !zone.reason.trim()}
          onClick={() => send('REGISTER_ZONE', { zone_kind: zone.zone_kind, location_code: zone.location_code.trim(), location_name: zone.location_name.trim(), reason: zone.reason.trim() })}>Daftarkan area</button></div>
    </> : <p role="status">Perubahan kebijakan dan area hanya oleh owner/admin.</p>}
  </section>
}
