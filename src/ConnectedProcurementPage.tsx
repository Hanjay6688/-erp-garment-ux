import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatReceiptDecimal as numberText, parseProcurementOptions, parseProcurementOutcome, parseProcurementWorkspace, procurementObject, receiptDecimal, receiptEditableInBaseUnits, type OptionKind, type ProcurementOption, type ProcurementOptions, type ProcurementWorkspace, type ReceiptDetail } from './procurementContract'
import type { Json } from './types/database.preconnect'
import './procurement-connected.css'

type Client = ReturnType<typeof getUatSupabaseClient>
type Line = { key: string; material: ProcurementOption | null; qty: string; price: string; priceMode: 'BENCHMARK' | 'MANUAL_ESTIMATE' | 'SUPPLIER_QUOTE' | 'SUPPLIER_INVOICE'; lot?: string | null; notes?: string | null; rolls: { key: string; number: string; qty: string; notes?: string | null }[] }
type Draft = { id: string | null; version: string | null; number: string; supplier: ProcurementOption | null; location: ProcurementOption | null; at: string; notes: string; reason: string; originalAt?: string; invoiceNumber?: string | null; dueDate?: string | null; lines: Line[] }
const blankLine = (): Line => ({ key: crypto.randomUUID(), material: null, qty: '', price: '', priceMode: 'BENCHMARK', rolls: [{ key: crypto.randomUUID(), number: '', qty: '' }] })
const blank = (): Draft => ({ id: null, version: null, number: '', supplier: null, location: null, at: cp6WibDateTimeInput(), notes: '', reason: 'Penerimaan barang sesuai surat jalan', lines: [blankLine()] })
const statusLabel = { DRAFT: 'Draft', POSTED: 'Sudah diterima', REVERSED: 'Dibatalkan' }

function MasterPicker({ client, kind, label, value, disabled, onChange }: { client: Client; kind: OptionKind; label: string; value: ProcurementOption | null; disabled: boolean; onChange: (v: ProcurementOption) => void }) {
  const [search, setSearch] = useState(''), [query, setQuery] = useState({ q: '', offset: 0 })
  const [page, setPage] = useState<ProcurementOptions | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  useEffect(() => {
    let current = true; setLoading(true); setError(''); setPage(null)
    void (async () => {
      try {
        const r = await client.rpc('erp_cp7_get_procurement_options_v1', { p_kind: kind, p_q: query.q, p_offset: query.offset, p_limit: 25 })
        if (!current) return
        if (r.error) throw r.error
        const result = parseProcurementOptions(r.data, kind)
        if (result.offset !== query.offset) throw new Error('Halaman pilihan tidak cocok.')
        setPage(result)
      } catch (e) { if (current) setError(normalizeClientError(e).message) }
      finally { if (current) setLoading(false) }
    })()
    return () => { current = false }
  }, [client, kind, query])
  return <div className="cproc-picker">
    <label>{label}<select aria-label={label} value={value?.id ?? ''} disabled={disabled || loading} onChange={e => { const found = page?.rows.find(r => r.id === e.target.value); if (found) onChange(found) }}>
      <option value="">{loading ? 'Memuat pilihan…' : 'Pilih dari master'}</option>
      {value && !page?.rows.some(r => r.id === value.id) ? <option value={value.id}>{value.code} · {value.name}</option> : null}
      {page?.rows.map(r => <option key={r.id} value={r.id}>{r.code} · {r.name}{r.unit_code ? ` · ${r.unit_code}` : ''}</option>)}
    </select></label>
    <div className="cproc-inline"><input aria-label={`Cari ${label}`} placeholder={`Cari ${label.toLowerCase()}`} maxLength={120} value={search} disabled={disabled} onChange={e => setSearch(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); setQuery({ q: search.trim(), offset: 0 }) } }}/><button type="button" disabled={disabled || loading} onClick={() => setQuery({ q: search.trim(), offset: 0 })}>Cari</button>
      <button type="button" aria-label={`Pilihan ${label} sebelumnya`} disabled={disabled || loading || query.offset === 0} onClick={() => setQuery(v => ({ ...v, offset: Math.max(0, v.offset - 25) }))}>‹</button>
      <button type="button" aria-label={`Pilihan ${label} berikutnya`} disabled={disabled || loading || page?.next_offset == null} onClick={() => setQuery(v => ({ ...v, offset: page?.next_offset ?? v.offset }))}>›</button></div>
    {error ? <span role="alert">{error}</span> : page ? <small>{page.rows.length} pilihan pada halaman ini · total {page.total}</small> : null}
  </div>
}

function fromDetail(d: ReceiptDetail): Draft {
  return { id: d.id, version: d.row_version, number: d.purchase_number, supplier: d.supplier_id ? { id: d.supplier_id, code: '', name: d.supplier_name ?? '' } : null,
    location: d.location_id ? { id: d.location_id, code: '', name: d.location_name ?? '' } : null, at: cp6WibDateTimeInput(d.physical_at), notes: d.notes ?? '', reason: '', originalAt: d.physical_at, invoiceNumber: d.finance?.supplier_invoice_number, dueDate: d.finance?.due_date,
    lines: d.items.map(i => ({ key: i.id, material: { id: i.material_id, code: i.material_sku, name: i.material_name, material_type: i.material_type, unit_code: i.unit_code }, qty: i.qty,
      price: i.finance?.price_source === 'BENCHMARK' ? '' : i.finance?.unit_price ?? '', priceMode: ['BENCHMARK','MANUAL_ESTIMATE','SUPPLIER_QUOTE','SUPPLIER_INVOICE'].includes(i.finance?.price_source ?? '') ? i.finance!.price_source as Line['priceMode'] : 'MANUAL_ESTIMATE',
      lot: i.lot_number, notes: i.notes, rolls: i.rolls.map(r => ({ key: r.id, number: r.roll_number, qty: r.receipt_qty, notes: r.notes })) })) }
}
function document(d: Draft, valueAccess: boolean): Json | null {
  const at = d.originalAt && d.at === cp6WibDateTimeInput(d.originalAt) ? d.originalAt : cp6WibPhysicalTimeToIso(d.at)
  if (!d.number.trim() || !d.supplier || !d.location || !at || !d.reason.trim() || !d.lines.length || d.lines.length > 100) return null
  const lines: Json[] = []
  for (const l of d.lines) {
    if (!l.material) return null
    const qty = receiptDecimal(l.qty, true), price = receiptDecimal(l.price), fabric = l.material.material_type === 'FABRIC'
    const benchmark = fabric && l.priceMode === 'BENCHMARK'
    if (!qty || !benchmark && (!valueAccess || price === null)) return null
    const rolls: Json[] = []
    if (fabric) {
      if (!l.rolls.length) return null
      for (const r of l.rolls) { const q = receiptDecimal(r.qty, true); if (!r.number.trim() || !q) return null; rolls.push({ roll_number: r.number.trim(), qty: q, notes: r.notes ?? null }) }
    }
    lines.push({ material_id: l.material.id, qty, price_source: benchmark ? 'BENCHMARK' : l.priceMode === 'BENCHMARK' ? 'MANUAL_ESTIMATE' : l.priceMode,
      price_state: l.priceMode === 'SUPPLIER_INVOICE' ? 'FINAL' : 'ESTIMATED', ...(benchmark ? {} : { unit_price: price }), lot_number: l.lot ?? null, notes: l.notes ?? null, rolls })
  }
  return { ...(d.id ? { id: d.id } : {}), ...(valueAccess ? { supplier_invoice_number: d.invoiceNumber ?? null, due_date: d.dueDate ?? null } : {}), purchase_number: d.number.trim(), supplier_id: d.supplier.id, location_id: d.location.id, physical_at: at, notes: d.notes.trim(), change_reason: d.reason.trim(), lines }
}

export default function ConnectedProcurementPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel"><h1>Pembelian & penerimaan</h1><p>Masuk ke ERP yang tersambung untuk membuka penerimaan.</p></section>
  if (!identity.permissions.includes('warehouse.procurement.view')) return <section className="panel" role="alert">Hak melihat penerimaan belum diberikan.</section>
  return <ProcurementWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function ProcurementWorkspace() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi penerimaan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime]), valueAccess = identity.permissions.includes('finance.ap.view')
  const mutation = useProductionMutation('PROCUREMENT'), { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [data, setData] = useState<ProcurementWorkspace | null>(null), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const [query, setQuery] = useState(''), [status, setStatus] = useState('ALL'), [draft, setDraft] = useState<Draft | null>(null), [postReason, setPostReason] = useState('Penerimaan barang telah diperiksa')
  const requested = useRef({ q: '', status: 'ALL', offset: 0, purchase_id: null as string | null }), sequence = useRef(0)
  const load = useCallback(async () => {
    const s = ++sequence.current, ticket = beginRead(), filters = { ...requested.current }
    setLoading(true); setError('')
    try {
      const r = await client.rpc('erp_cp7_get_procurement_v1', { p_query: { ...filters, limit: 25 } })
      if (!isReadCurrent(ticket) || s !== sequence.current) return false
      if (r.error) throw r.error
      const w = parseProcurementWorkspace(r.data, valueAccess)
      if (w.page.offset !== filters.offset || (w.detail?.id ?? null) !== filters.purchase_id) throw new Error('Dokumen hasil tidak cocok dengan pilihan.')
      setData(w); return finishRead(ticket)
    } catch (e) { if (isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }; return false }
    finally { if (s === sequence.current) setLoading(false) }
  }, [client, valueAccess, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load])
  const handlers: ProductionMutationHandlers = {
    send: envelope => {
      const p = procurementObject(envelope.payload)
      return client.rpc('erp_cp7_save_procurement_v1', { p_action: envelope.action, p_payload: p.document as Json, p_request: envelope.id, p_expected: p.expected_version as string | null })
    },
    validate: (r, e) => { parseProcurementOutcome(r, e.id, e.action, procurementObject(e.payload).document as Json) },
    retire: (r, e) => { const result = parseProcurementOutcome(r, e.id, e.action, procurementObject(e.payload).document as Json); requested.current.purchase_id = result.purchase_id; setDraft(null) },
    reload: load,
  }
  const locked = mutation.writerLocked || loading, current = data?.detail
  const staleDraft = Boolean(draft?.id && (!current || current.id !== draft.id || current.row_version !== draft.version))
  const payload = draft ? document(draft, valueAccess) : null
  const changeLine = (key: string, fn: (l: Line) => Line) => setDraft(d => d ? { ...d, lines: d.lines.map(l => l.key === key ? fn(l) : l) } : d)
  const write = (action: string, doc: Json, version: string | null) => run(action, { document: doc, expected_version: version }, null, handlers)
  return <section className="cproc">
    <header className="panel cproc-heading"><div><div className="eyebrow">GUDANG · PENERIMAAN BARANG</div><h1>Pembelian & penerimaan</h1><p>Catat surat jalan, periksa roll atau jumlah barang, lalu sahkan penerimaan ke gudang.</p></div>
      <div className="cproc-inline"><button type="button" disabled={mutation.busy || loading} onClick={() => void load()}>Muat ulang</button><button className="primary-btn" type="button" disabled={locked || !data?.capabilities.create} onClick={() => setDraft(blank())}>Penerimaan baru</button></div></header>
    <ProductionRecoveryNotice recovery={{ ...mutation, notice: mutation.notice ? 'Data penerimaan sudah diperbarui.' : '',
      ...(mutation.pending && !mutation.corruptedEnvelope ? { error: 'Hasil pencatatan belum diketahui. Periksa kembali hasil transaksi; data kiriman sebelumnya tetap disimpan.', blockReason: '' } : {}) }}
      onReconcile={() => reconcile(handlers)} className="panel"/>
    {error ? <p className="panel" role="alert">{error}</p> : null}
    <form className="panel cproc-search" onSubmit={e => { e.preventDefault(); requested.current = { ...requested.current, q: query.trim(), status, offset: 0 }; void load() }}>
      <label>Cari surat jalan atau supplier<input aria-label="Cari penerimaan" value={query} maxLength={120} onChange={e => setQuery(e.target.value)}/></label>
      <label>Status<select aria-label="Status penerimaan" value={status} onChange={e => setStatus(e.target.value)}><option value="ALL">Semua</option><option value="DRAFT">Draft</option><option value="POSTED">Sudah diterima</option><option value="REVERSED">Dibatalkan</option></select></label><button disabled={mutation.busy || loading}>Cari penerimaan</button>
    </form>
    {draft ? <form className="panel cproc-editor" onSubmit={e => { e.preventDefault(); if (payload && !locked && !staleDraft && data?.capabilities.create) void write('SAVE_DRAFT', payload, draft.version) }}>
      <div className="cproc-heading"><div><div className="eyebrow">SURAT JALAN</div><h2>{draft.id ? 'Perbaiki draft penerimaan' : 'Penerimaan baru'}</h2><p>Draft belum menambah stok. Setelah disimpan, periksa dokumennya sebelum disahkan.</p></div><button type="button" disabled={mutation.busy} onClick={() => setDraft(null)}>Tutup formulir</button></div>
      {staleDraft ? <p role="alert">Versi draft sudah berubah. Tutup formulir dan buka ulang dokumen sebelum mengubahnya.</p> : null}
      <fieldset disabled={locked || staleDraft}><div className="cproc-grid">
        <label>Nomor surat jalan<input aria-label="Nomor surat jalan" required value={draft.number} onChange={e => setDraft({ ...draft, number: e.target.value })}/></label>
        <label>Waktu barang datang · WIB<input aria-label="Waktu barang datang WIB" type="datetime-local" required value={draft.at} onChange={e => setDraft({ ...draft, at: e.target.value })}/></label>
        <MasterPicker client={client} kind="SUPPLIER" label="Supplier penerimaan" value={draft.supplier} disabled={locked} onChange={supplier => setDraft(d => d ? { ...d, supplier } : d)}/>
        <MasterPicker client={client} kind="LOCATION" label="Gudang penerimaan" value={draft.location} disabled={locked} onChange={location => setDraft(d => d ? { ...d, location } : d)}/>
      </div>
      {draft.lines.map((l, index) => <section className="cproc-line" key={l.key}>
        <div className="cproc-heading"><h3>Barang {index + 1}</h3><button type="button" disabled={draft.lines.length === 1} onClick={() => setDraft(d => d ? { ...d, lines: d.lines.filter(x => x.key !== l.key) } : d)}>Hapus barang {index + 1}</button></div>
        <div className="cproc-grid"><MasterPicker client={client} kind="MATERIAL" label={`Bahan ${index + 1}`} value={l.material} disabled={locked} onChange={material => changeLine(l.key, old => ({ ...old, material, qty: '', price: '', priceMode: material.material_type === 'FABRIC' ? 'BENCHMARK' : 'MANUAL_ESTIMATE' }))}/>
          <label>Jumlah sesuai surat jalan {l.material?.unit_code ? `(${l.material.unit_code})` : ''}<input aria-label={`Jumlah barang ${index + 1}`} inputMode="decimal" required value={l.qty} onChange={e => changeLine(l.key, old => ({ ...old, qty: e.target.value }))}/></label></div>
        {l.material ? <p className="cproc-help">Satuan bahan: <strong>{l.material.unit_code}</strong>. Isi jumlah dan harga dalam satuan ini; Yard dan Meter tidak dikonversi otomatis.</p> : null}
        {l.material?.material_type === 'FABRIC' ? <div className="cproc-rolls"><h4>Rincian roll</h4>{l.rolls.map((r, ri) => <div className="cproc-inline" key={r.key}><label>Nomor roll<input aria-label={`Nomor roll ${index + 1}.${ri + 1}`} required value={r.number} onChange={e => changeLine(l.key, old => ({ ...old, rolls: old.rolls.map(x => x.key === r.key ? { ...x, number: e.target.value } : x) }))}/></label><label>Jumlah ({l.material?.unit_code})<input aria-label={`Jumlah roll ${index + 1}.${ri + 1}`} required inputMode="decimal" value={r.qty} onChange={e => changeLine(l.key, old => ({ ...old, rolls: old.rolls.map(x => x.key === r.key ? { ...x, qty: e.target.value } : x) }))}/></label><button type="button" disabled={l.rolls.length === 1} onClick={() => changeLine(l.key, old => ({ ...old, rolls: old.rolls.filter(x => x.key !== r.key) }))}>Hapus roll {ri + 1}</button></div>)}<button type="button" onClick={() => changeLine(l.key, old => ({ ...old, rolls: [...old.rolls, { key: crypto.randomUUID(), number: '', qty: '' }] }))}>Tambah roll barang {index + 1}</button></div> : null}
        {valueAccess ? <div className="cproc-grid"><label>Dasar harga<select aria-label={`Dasar harga ${index + 1}`} value={l.priceMode} onChange={e => changeLine(l.key, old => ({ ...old, priceMode: e.target.value as Line['priceMode'] }))}>{l.material?.material_type === 'FABRIC' ? <option value="BENCHMARK">Benchmark saat barang datang</option> : null}<option value="MANUAL_ESTIMATE">Perkiraan sementara</option><option value="SUPPLIER_QUOTE">Penawaran supplier</option><option value="SUPPLIER_INVOICE">Harga pada invoice supplier</option></select></label>
          {l.priceMode !== 'BENCHMARK' ? <label>Harga per {l.material?.unit_code ?? 'satuan'}<input aria-label={`Harga barang ${index + 1}`} inputMode="decimal" value={l.price} onChange={e => changeLine(l.key, old => ({ ...old, price: e.target.value }))}/></label> : <p>Benchmark yang berlaku pada waktu penerimaan diambil saat draft disimpan. Nilainya masih perkiraan sampai invoice final.</p>}</div>
          : <p className="cproc-help">Penerimaan kain memakai benchmark yang berlaku. Pengisian harga barang lain memerlukan petugas dengan akses nilai pembelian.</p>}
      </section>)}
      <button type="button" disabled={draft.lines.length >= 100} onClick={() => setDraft(d => d ? { ...d, lines: [...d.lines, blankLine()] } : d)}>Tambah barang</button>
      <div className="cproc-grid"><label>Catatan<input aria-label="Catatan penerimaan" value={draft.notes} onChange={e => setDraft({ ...draft, notes: e.target.value })}/></label><label>Alasan pencatatan<input aria-label="Alasan pencatatan penerimaan" required value={draft.reason} onChange={e => setDraft({ ...draft, reason: e.target.value })}/></label></div>
      <div className="cproc-actions"><button className="primary-btn" disabled={!payload || !data?.capabilities.create}>Simpan draft penerimaan</button><span>Jumlah roll akan dicocokkan dengan jumlah surat jalan.</span></div></fieldset>
    </form> : null}
    <div className="cproc-layout"><section className="panel cproc-history"><h2>Daftar penerimaan</h2>{loading ? <p role="status">Memuat penerimaan…</p> : null}{data?.page.rows.length === 0 ? <p>Belum ada penerimaan sesuai pencarian.</p> : null}
      {data?.page.rows.map(r => <button type="button" className="cproc-receipt" key={r.id} aria-pressed={r.id === current?.id} disabled={mutation.busy || loading} onClick={() => { requested.current.purchase_id = r.id; setDraft(null); void load() }}><span><strong>{r.purchase_number}</strong><small>{r.supplier_name ?? 'Supplier belum dipilih'} · {r.location_name ?? 'Gudang belum dipilih'}</small><small>{formatCp6WibDateTime(r.physical_at)} · {r.line_count} barang</small></span><span className={`cproc-status ${r.status.toLowerCase()}`}>{statusLabel[r.status]}</span></button>)}
      {data ? <div className="cproc-pagination"><span>{data.page.rows.length} dokumen pada halaman ini · total {data.page.total}</span><button type="button" disabled={loading || mutation.busy || !data.page.offset} onClick={() => { requested.current.offset = Math.max(0, data.page.offset - 25); void load() }}>Sebelumnya</button><button type="button" disabled={loading || mutation.busy || data.page.next_offset === null} onClick={() => { requested.current.offset = data.page.next_offset ?? data.page.offset; void load() }}>Berikutnya</button></div> : null}
    </section>
    <aside className="panel cproc-detail">{current ? <><div className="eyebrow">DOKUMEN PENERIMAAN</div><h2>{current.purchase_number}</h2><p>{current.supplier_name} · {current.location_name}</p><span className={`cproc-status ${current.status.toLowerCase()}`}>{statusLabel[current.status]}</span><p>{current.status === 'DRAFT' ? 'Belum menambah stok gudang.' : current.status === 'POSTED' ? 'Penerimaan sudah tercatat. Kuantitas di bawah mengikuti dokumen masuk.' : 'Penerimaan sudah dibatalkan.'}</p>
      {current.items.map(i => <article className="cproc-item" key={i.id}><h3>{i.material_name}</h3><strong>{numberText(i.qty)} {i.unit_code}</strong><small>{i.material_sku}</small>{i.purchase_uom_code && i.purchase_qty_entered ? <small>Di surat jalan: {numberText(i.purchase_qty_entered)} {i.purchase_uom_code}</small> : null}{i.finance ? <p>{i.finance.price_state === 'ESTIMATED' ? 'Perkiraan' : 'Harga invoice'} · Rp{numberText(i.finance.unit_price)} / {i.unit_code}<br/>Nilai baris Rp{numberText(i.finance.line_total)}</p> : null}
        {i.rolls.length ? <details><summary>{i.rolls.length} roll</summary><ul>{i.rolls.map(r => <li key={r.id}>{r.roll_number} · {numberText(r.receipt_qty)} {i.unit_code}</li>)}</ul></details> : null}</article>)}
      {current.finance ? <div className="cproc-total"><span>Nilai pada penerimaan</span><strong>Rp{numberText(current.finance.receipt_value)}</strong><small>Jumlah utang mengikuti invoice dan penyelesaian supplier.</small></div> : null}
      {current.status === 'DRAFT' ? <div className="cproc-review"><h3>Periksa sebelum menerima</h3><p>Pastikan supplier, gudang, waktu, bahan dan jumlah roll sudah sesuai barang datang.</p>{valueAccess && data?.capabilities.create && receiptEditableInBaseUnits(current) ? <button type="button" disabled={locked} onClick={() => setDraft(fromDetail(current))}>Perbaiki draft</button> : null}<label>Catatan pemeriksaan<input aria-label="Catatan pemeriksaan penerimaan" disabled={locked} value={postReason} onChange={e => setPostReason(e.target.value)}/></label><button className="primary-btn" type="button" disabled={locked || Boolean(draft) || !data?.capabilities.post || !postReason.trim()} onClick={() => void write('POST', { purchase_id: current.id, change_reason: postReason.trim() }, current.row_version)}>Sahkan penerimaan ke gudang</button></div> : null}
    </> : <><h2>Periksa dokumen</h2><p>Pilih surat jalan untuk melihat barang, rincian roll dan status penerimaannya.</p></>}</aside></div>
  </section>
}
