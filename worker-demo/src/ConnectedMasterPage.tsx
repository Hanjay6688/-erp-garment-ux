import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import MaterialNamePanel from './MaterialNamePanel'
import WorkRatePanel from './WorkRatePanel'
import MaterialReorderPanel from './MaterialReorderPanel'
import {
  blockerText, emptyForm, fieldsPayload, formFromEntity, formProblems, kindLabels, locationTypeLabels, masterFields, masterPayload,
  parseMasterWorkspace, policyAt, rupiah, supplierTypeLabels, usageLabels, validateMasterOutcome, wibDay,
  type MasterAction, type MasterForm, type MasterKind, type MasterWorkspace,
} from './masterContract'
import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'
import './master-connected.css'

export type ConnectedMasterView = 'master-customers' | 'master-partners' | 'master-workforce' | 'master-locations' | 'master-fabric' | 'master-accessory'
const views: Record<ConnectedMasterView, { kinds: MasterKind[]; eyebrow: string; title: string; description: string }> = {
  'master-customers': { kinds: ['CUSTOMER'], eyebrow: 'MASTER DATA · PELANGGAN', title: 'Pelanggan',
    description: 'Pelanggan baru langsung bisa dipilih di Penjualan. Pelanggan yang sudah punya transaksi tidak dihapus; nonaktifkan bila tidak dipakai lagi.' },
  'master-partners': { kinds: ['SUPPLIER', 'LAUNDRY_VENDOR'], eyebrow: 'MASTER DATA · SUPPLIER & VENDOR', title: 'Supplier & Vendor',
    description: 'Supplier baru langsung bisa dipilih di Pembelian & Penerimaan; vendor laundry di Laundry. Yang sudah punya transaksi dinonaktifkan, tidak dihapus.' },
  'master-workforce': { kinds: ['MANDOR'], eyebrow: 'MASTER DATA · MANDOR', title: 'Mandor & tarif upah',
    description: 'Mandor baru langsung bisa dipilih di Bagi Potongan. Tarif upah per model dan komponen kerja diisi di bawah; upah dihitung dengan tarif yang berlaku pada tanggal jahit.' },
  'master-locations': { kinds: ['LOCATION'], eyebrow: 'MASTER DATA · GUDANG & LOKASI', title: 'Gudang & Lokasi',
    description: 'Lokasi yang masih berisi stok tidak bisa dinonaktifkan. Pemindahan stok tetap lewat mutasi, bukan dengan mengubah lokasi.' },
  'master-fabric': { kinds: ['FABRIC'], eyebrow: 'MASTER DATA · KAIN', title: 'Kain & harga acuan',
    description: 'Kain baru langsung bisa dipilih di penerimaan. Harga acuan berlaku mulai tanggal yang diisi; harga lama tetap tercatat.' },
  'master-accessory': { kinds: ['ACCESSORY_CATEGORY', 'ACCESSORY'], eyebrow: 'MASTER DATA · AKSESORI', title: 'Aksesori & harga mandor',
    description: 'Kategori menentukan satuan dasar dan harga aksesori ke mandor; varian adalah barang yang diterima dan dibagi.' },
}

export default function ConnectedMasterPage({ view }: { view: ConnectedMasterView }) {
  const config = views[view]
  const [kind, setKind] = useState<MasterKind>(config.kinds[0])
  // The selected Mandor and its review token: the rate panel reloads when the Mandor changes (e.g. becomes Special).
  const [mandor, setMandor] = useState<{ id: string; token: string } | null>(null)
  const pickMandor = useCallback((id: string | null, token: string | null) =>
    setMandor(old => old?.id === id && old?.token === token ? old : id && token ? { id, token } : null), [])
  useEffect(() => { setKind(config.kinds[0]); setMandor(null) }, [view]) // eslint-disable-line react-hooks/exhaustive-deps
  return <><section className="cmd-page" aria-label={config.title}>
    <header className="cmd-hero"><span>{config.eyebrow}</span><h1>{config.title}</h1><p>{config.description}</p></header>
    {config.kinds.length > 1 ? <div className="cmd-tabs" role="tablist">{config.kinds.map(k =>
      <button type="button" role="tab" key={k} aria-selected={kind === k} onClick={() => setKind(k)}>{kindLabels[k].plural}</button>)}</div> : null}
    <MasterPanel key={`${view}:${kind}`} kind={kind} onSelected={kind === 'MANDOR' ? pickMandor : undefined}/>
    {view === 'master-workforce' ? <WorkRatePanel contractorId={mandor?.id ?? null} contractorVersion={mandor?.token ?? null}/> : null}
  </section>
    {/* SS-2/SS-3: lama kirim (and an accessory's manual number) is filled per material here, as on the warehouse pages. */}
    {view === 'master-fabric' ? <MaterialReorderPanel materialType="FABRIC"/> : view === 'master-accessory' ? <MaterialReorderPanel materialType="ACCESSORY"/> : null}</>
}

type Mode = 'VIEW' | 'CREATE' | 'EDIT' | 'DEACTIVATE' | 'REACTIVATE' | 'SET_BENCHMARK' | 'SET_MANDOR_PRICE'
type PriceForm = { price: string; effective_date: string; contractor_id: string; uom: string; notes: string }

function MasterPanel({ kind, onSelected }: { kind: MasterKind; onSelected?: (id: string | null, token: string | null) => void }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi data master belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('MASTER_DATA')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const label = kindLabels[kind]
  const serial = useRef(0)
  const [query, setQuery] = useState(''), [status, setStatus] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ACTIVE'), [offset, setOffset] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [data, setData] = useState<MasterWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [mode, setMode] = useState<Mode>('VIEW'), [form, setForm] = useState<MasterForm>(() => emptyForm(kind))
  const [price, setPrice] = useState<PriceForm>({ price: '', effective_date: '', contractor_id: '', uom: '', notes: '' })
  const [reason, setReason] = useState(''), [reviewed, setReviewed] = useState(false)
  const committed = useRef<string | null>(null)
  const resetForm = () => { setReason(''); setReviewed(false) }

  const load = useCallback(async (q: { query: string; status: string; offset: number; id: string | null }) => {
    const ticket = beginRead(), n = ++serial.current
    setBusy(true); setError('')
    try {
      const reply = await client.rpc('erp_cp7_get_master_v1', { p_kind: kind, p_query: { q: q.query.trim(), status: q.status, offset: q.offset, limit: 20, id: q.id } })
      if (n !== serial.current || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      const ws = parseMasterWorkspace(reply.data, kind)
      setData(ws); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [beginRead, client, finishRead, isReadCurrent, kind])
  useEffect(() => { void load({ query: '', status: 'ACTIVE', offset: 0, id: null }) }, [load, recovery.scope])
  useEffect(() => () => { ++serial.current }, [])
  const selected = data?.selected && data.selected.entity.id === selectedId ? data.selected : null
  useEffect(() => { onSelected?.(selected ? String(selected.entity.id) : null, selected?.reviewToken ?? null) }, [selected, onSelected])

  const select = (id: string | null) => { setSelectedId(id); setMode('VIEW'); resetForm(); setDone(''); void load({ query, status, offset, id }) }
  const startEdit = () => { if (!selected || !data) return; setForm(formFromEntity(kind, selected.entity, data.today)); resetForm(); setMode('EDIT') }
  const startCreate = () => { setSelectedId(null); setForm(emptyForm(kind)); resetForm(); setDone(''); setMode('CREATE') }
  const startPrice = (m: 'SET_BENCHMARK' | 'SET_MANDOR_PRICE') => {
    if (!data) return
    setPrice({ price: '', effective_date: data.today, contractor_id: '', uom: kind === 'ACCESSORY_CATEGORY' ? String(selected?.entity.base_uom ?? '') : '', notes: '' })
    resetForm(); setMode(m)
  }

  const handlers: ProductionMutationHandlers = {
    send: (e: ProductionEnvelope) => {
      const p = e.payload as { kind: string; payload: Json }
      return client.rpc('erp_cp7_save_master_v1', { p_kind: p.kind, p_payload: p.payload, p_request: e.id })
    },
    validate: (value: unknown, e: ProductionEnvelope) => { validateMasterOutcome(value, (e.payload as { kind: MasterKind }).kind, e.action, e.id) },
    retire: (value: unknown, e: ProductionEnvelope) => {
      const r = validateMasterOutcome(value, (e.payload as { kind: MasterKind }).kind, e.action, e.id)
      committed.current = r.id
      const what = `${label.singular} ${String(r.entity.code)} · ${String(r.entity.name)}`
      setDone(e.action === 'CREATE' ? `Tersimpan: ${what} dibuat dan langsung bisa dipakai.`
        : e.action === 'DEACTIVATE' ? `Tersimpan: ${what} dinonaktifkan. Transaksi lamanya tetap tercatat.`
        : e.action === 'REACTIVATE' ? `Tersimpan: ${what} aktif lagi.`
        : e.action === 'SET_BENCHMARK' ? `Tersimpan: harga acuan baru untuk ${what}.`
        : e.action === 'SET_MANDOR_PRICE' ? `Tersimpan: harga aksesori ke mandor untuk ${what}.` : `Tersimpan: perubahan ${what}.`)
      setMode('VIEW'); resetForm()
    },
    reload: async () => {
      const id = committed.current ?? selectedId; committed.current = null
      if (id) setSelectedId(id)
      return load({ query, status, offset, id })
    },
  }
  const fresh = data !== null && !recovery.workspaceStale
  const writable = fresh && data.canWrite && !recovery.writerLocked && !busy
  const problems = mode === 'CREATE' || mode === 'EDIT' ? formProblems(kind, form, mode === 'CREATE') : []
  const canSubmit = writable && reason.trim().length >= 5 && reviewed && problems.length === 0
  const submit = (action: MasterAction, fields?: Json) => {
    if (!canSubmit || !data) return
    void run(action, { kind, payload: masterPayload(action, reason, action === 'CREATE' ? null : selected, fields) }, null, handlers)
  }
  const priceProblem = mode === 'SET_BENCHMARK' || mode === 'SET_MANDOR_PRICE'
    ? (!/^[0-9]{1,12}(\.[0-9]{1,4})?$/.test(price.price.trim()) || (mode === 'SET_BENCHMARK' && Number(price.price) <= 0) ? 'Harga harus angka (pakai titik untuk desimal).'
      : !/^\d{4}-\d{2}-\d{2}$/.test(price.effective_date) ? 'Tanggal mulai berlaku wajib diisi.' : mode === 'SET_MANDOR_PRICE' && !price.uom ? 'Satuan harga wajib dipilih.' : '')
    : ''
  const reviewBlock = (what: string) => <>
    <label>Alasan<input aria-label={`Alasan ${what}`} value={reason} maxLength={1000} disabled={!writable} onChange={e => { setReason(e.target.value); setReviewed(false) }}/></label>
    <label className="cmd-check"><input type="checkbox" aria-label={`${what} sudah diperiksa`} checked={reviewed} disabled={!writable || reason.trim().length < 5}
      onChange={e => setReviewed(e.target.checked)}/>Isian dan alasannya sudah saya periksa.</label>
  </>

  return <section className="panel cmd-panel" aria-label={label.plural}>
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="" reconcileLabel="Periksa hasil simpan data master"/> : null}
    <form className="cmd-search" onSubmit={e => { e.preventDefault(); setOffset(0); setDone(''); void load({ query, status, offset: 0, id: selectedId }) }}>
      <label>Cari {label.singular}<input aria-label={`Cari ${label.singular}`} value={query} maxLength={80} onChange={e => setQuery(e.target.value)} placeholder="Kode atau nama"/></label>
      <label>Tampilkan<select aria-label={`Tampilkan ${label.singular}`} value={status} onChange={e => { const s = e.target.value as typeof status; setStatus(s); setOffset(0); void load({ query, status: s, offset: 0, id: selectedId }) }}>
        <option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option><option value="ALL">Semua</option></select></label>
      <button type="submit" disabled={busy}>Cari</button>
      {data?.canWrite ? <button type="button" className="primary-btn" disabled={busy || recovery.writerLocked} onClick={startCreate}>Tambah {label.singular}</button> : null}
    </form>
    {done ? <p role="status" className="cmd-done">{done}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {data && !data.canWrite ? <p className="cmd-note">Akun ini hanya bisa melihat {label.plural.toLowerCase()}. Menambah dan mengubah perlu hak kelola data master (Owner/Admin).</p> : null}
    <div className="cmd-layout">
      <div className="cmd-list" aria-label={`Daftar ${label.singular}`}>
        {data && data.page.rows.length === 0 ? <p>Belum ada {label.singular} yang cocok.</p> : null}
        {data?.page.rows.map(r => <button type="button" key={r.id} aria-label={`Pilih ${label.singular} ${r.code}`} aria-pressed={selectedId === r.id}
          disabled={busy} onClick={() => select(r.id)}>
          <strong>{r.code} · {r.name}</strong>
          <span>{r.active ? 'Aktif' : 'Nonaktif'}{rowExtra(kind, r.extra)}</span>
        </button>)}
        {data ? <div className="cmd-pages">
          <button type="button" disabled={busy || data.page.offset === 0} onClick={() => { const o = Math.max(0, offset - 20); setOffset(o); void load({ query, status, offset: o, id: selectedId }) }}>Sebelumnya</button>
          <span>{data.page.total} data</span>
          <button type="button" disabled={busy || data.page.offset + data.page.rows.length >= data.page.total} onClick={() => { const o = offset + 20; setOffset(o); void load({ query, status, offset: o, id: selectedId }) }}>Berikutnya</button>
        </div> : null}
      </div>
      <div className="cmd-detail">
        {mode === 'CREATE' || mode === 'EDIT' ? <section className="cmd-form" aria-label={`Form ${label.singular}`}>
          <h2>{mode === 'CREATE' ? `Tambah ${label.singular}` : `Ubah ${label.singular} ${String(selected?.entity.code ?? '')}`}</h2>
          {data ? masterFields[kind].map(f => {
            const locked = mode === 'EDIT' && (f.lockedAfterCreate === true || (f.key === 'code' && selected?.used === true))
            const value = form[f.key]
            const set = (v: string | boolean) => { setForm(old => ({ ...old, [f.key]: v })); setReviewed(false) }
            return <label key={f.key} className={f.type === 'boolean' ? 'cmd-check' : undefined}>
              {f.type === 'boolean' ? <><input type="checkbox" aria-label={f.label} checked={value === true} disabled={!writable} onChange={e => set(e.target.checked)}/>{f.label}</> : <>{f.label}{f.optional ? ' (boleh kosong)' : ''}
                {f.type === 'select' ? <select aria-label={f.label} value={String(value)} disabled={!writable || locked} onChange={e => set(e.target.value)}>
                  {f.optional || value === '' ? <option value="">—</option> : null}
                  {f.options?.(data, selected?.entity ?? null).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                  : f.type === 'textarea' ? <textarea aria-label={f.label} value={String(value)} maxLength={f.max} disabled={!writable || locked} onChange={e => set(e.target.value)}/>
                  : <input aria-label={f.label} type={f.type === 'date' ? 'date' : 'text'} inputMode={f.type === 'decimal' ? 'decimal' : undefined}
                    value={String(value)} maxLength={f.max} disabled={!writable || locked} onChange={e => set(e.target.value)}/>}</>}
              {locked && f.key === 'code' && selected?.used ? <small>Kode tetap karena sudah dipakai transaksi.</small>
                : locked ? <small>Nama dan kode bahan dibetulkan lewat "Benerin nama bahan".</small> : f.help ? <small>{f.help}</small> : null}
            </label>
          }) : null}
          {problems.length ? <ul className="cmd-problems">{problems.map(p => <li key={p}>{p}</li>)}</ul> : null}
          {reviewBlock(`simpan ${label.singular}`)}
          <div className="cmd-actions">
            <button type="button" className="primary-btn" disabled={!canSubmit} onClick={() => submit(mode === 'CREATE' ? 'CREATE' : 'UPDATE', fieldsPayload(kind, form))}>Simpan {label.singular}</button>
            <button type="button" onClick={() => { setMode('VIEW'); resetForm() }}>Batal</button>
          </div>
        </section> : null}
        {mode !== 'CREATE' && selected && data ? <section className="cmd-view" aria-label={`${label.singular} ${String(selected.entity.code)}`}>
          <h2>{String(selected.entity.code)} · {String(selected.entity.name)} <em className={selected.entity.active ? 'cmd-on' : 'cmd-off'}>{selected.entity.active ? 'AKTIF' : 'NONAKTIF'}</em></h2>
          <dl className="cmd-facts">{facts(kind, selected.entity, data.today).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
          <div className="cmd-usage"><strong>Dipakai di</strong>{Object.entries(selected.usage).filter(([, v]) => String(v) !== '0').length === 0
            ? <span>Belum dipakai transaksi.</span>
            : Object.entries(selected.usage).filter(([, v]) => String(v) !== '0').map(([k, v]) => <span key={k}>{usageLabels[k] ?? k}: {String(v)}</span>)}</div>
          {mode === 'VIEW' && data.canWrite ? <div className="cmd-actions">
            <button type="button" disabled={!writable} onClick={startEdit}>Ubah</button>
            {selected.entity.active ? <button type="button" disabled={!writable} onClick={() => { resetForm(); setMode('DEACTIVATE') }}>Nonaktifkan</button>
              : <button type="button" disabled={!writable} onClick={() => { resetForm(); setMode('REACTIVATE') }}>Aktifkan lagi</button>}
            {kind === 'FABRIC' && data.canPrice ? <button type="button" disabled={!writable} onClick={() => startPrice('SET_BENCHMARK')}>Harga acuan baru</button> : null}
            {kind === 'ACCESSORY_CATEGORY' && data.canPrice && selected.entity.active ? <button type="button" disabled={!writable} onClick={() => startPrice('SET_MANDOR_PRICE')}>Harga ke mandor</button> : null}
          </div> : null}
          {mode === 'DEACTIVATE' || mode === 'REACTIVATE' ? <section className="cmd-form" aria-label={mode === 'DEACTIVATE' ? `Nonaktifkan ${label.singular}` : `Aktifkan lagi ${label.singular}`}>
            {mode === 'DEACTIVATE' && selected.deactivateBlockers.length ? <div role="alert"><p>Belum bisa dinonaktifkan:</p><ul>{selected.deactivateBlockers.map(b => <li key={b.kind}>{blockerText(b)}</li>)}</ul></div>
              : <p className="cmd-note">{mode === 'DEACTIVATE' ? 'Data tidak dihapus. Transaksi lama tetap memakai data ini; transaksi baru tidak bisa memilihnya lagi.' : 'Data bisa dipilih lagi di transaksi baru.'}</p>}
            {mode === 'DEACTIVATE' && selected.deactivateBlockers.length ? null : <>
              {reviewBlock(mode === 'DEACTIVATE' ? 'nonaktif' : 'aktifkan lagi')}
              <button type="button" className="primary-btn" disabled={!canSubmit} onClick={() => submit(mode)}>{mode === 'DEACTIVATE' ? `Nonaktifkan ${label.singular}` : `Aktifkan lagi ${label.singular}`}</button>
            </>}
            <button type="button" onClick={() => { setMode('VIEW'); resetForm() }}>Batal</button>
          </section> : null}
          {mode === 'SET_BENCHMARK' || mode === 'SET_MANDOR_PRICE' ? <section className="cmd-form" aria-label={mode === 'SET_BENCHMARK' ? 'Harga acuan baru' : 'Harga aksesori ke mandor'}>
            {mode === 'SET_MANDOR_PRICE' ? <label>Untuk mandor<select aria-label="Harga untuk mandor" value={price.contractor_id} disabled={!writable}
              onChange={e => { setPrice(p => ({ ...p, contractor_id: e.target.value })); setReviewed(false) }}>
              <option value="">Semua mandor (harga umum)</option>
              {(Array.isArray(data.options.mandors) ? data.options.mandors as Record<string, unknown>[] : []).map(m => <option key={String(m.id)} value={String(m.id)}>{String(m.code)} · {String(m.name)}</option>)}
            </select></label> : null}
            <label>{mode === 'SET_BENCHMARK' ? `Harga acuan per ${String(selected.entity.unit)}` : 'Harga'}<input aria-label={mode === 'SET_BENCHMARK' ? 'Harga acuan' : 'Harga ke mandor'} inputMode="decimal" value={price.price} disabled={!writable}
              onChange={e => { setPrice(p => ({ ...p, price: e.target.value })); setReviewed(false) }}/></label>
            {mode === 'SET_MANDOR_PRICE' ? <label>Satuan harga<select aria-label="Satuan harga ke mandor" value={price.uom} disabled={!writable}
              onChange={e => { setPrice(p => ({ ...p, uom: e.target.value })); setReviewed(false) }}>
              {(Array.isArray(data.options.uoms) ? data.options.uoms as Record<string, unknown>[] : []).map(u => <option key={String(u.code)} value={String(u.code)}>{String(u.code)}</option>)}
            </select></label> : null}
            <label>Berlaku mulai (WIB)<input aria-label="Harga berlaku mulai" type="date" value={price.effective_date} disabled={!writable}
              onChange={e => { setPrice(p => ({ ...p, effective_date: e.target.value })); setReviewed(false) }}/></label>
            {mode === 'SET_MANDOR_PRICE' ? <label>Catatan (boleh kosong)<input aria-label="Catatan harga ke mandor" value={price.notes} maxLength={1000} disabled={!writable}
              onChange={e => setPrice(p => ({ ...p, notes: e.target.value }))}/></label> : null}
            {priceProblem ? <p className="cmd-problems">{priceProblem}</p> : null}
            {reviewBlock(mode === 'SET_BENCHMARK' ? 'harga acuan' : 'harga ke mandor')}
            <button type="button" className="primary-btn" disabled={!canSubmit || priceProblem !== ''} onClick={() => submit(mode, mode === 'SET_BENCHMARK'
              ? { price: price.price.trim(), effective_date: price.effective_date }
              : { contractor_id: price.contractor_id || null, price: price.price.trim(), uom: price.uom, effective_date: price.effective_date, notes: price.notes.trim() || null })}>
              {mode === 'SET_BENCHMARK' ? 'Simpan harga acuan' : 'Simpan harga ke mandor'}</button>
            <button type="button" onClick={() => { setMode('VIEW'); resetForm() }}>Batal</button>
          </section> : null}
          {(kind === 'FABRIC' || kind === 'ACCESSORY') ? <MaterialNamePanel materialId={String(selected.entity.id)} onRenamed={() => load({ query, status, offset, id: selectedId })}/> : null}
          <section className="cmd-audit" aria-label={`Riwayat ${label.singular}`}>
            <h3>Riwayat perubahan</h3>
            {selected.audit.length === 0 ? <p>Belum ada catatan perubahan.</p> : <ol>{selected.audit.slice(0, 20).map((a, i) => <li key={`${a.at}:${i}`}>
              <strong>{formatCp6WibDateTime(a.at)}</strong> · {auditAction(a.action)}{a.fields.length ? ` (${a.fields.join(', ')})` : ''}{a.actor ? ` · ${a.actor}` : ''}{a.reason ? ` · "${a.reason}"` : ''}
            </li>)}</ol>}
          </section>
        </section> : null}
        {mode === 'VIEW' && !selected && data?.selectedMissing ? <p role="alert">Data yang dipilih tidak ditemukan lagi. Muat ulang daftar.</p> : null}
        {mode === 'VIEW' && !selectedId ? <p className="cmd-note">Pilih {label.singular} di daftar untuk melihat rinciannya{data?.canWrite ? `, atau tekan "Tambah ${label.singular}"` : ''}.</p> : null}
      </div>
    </div>
  </section>
}

function auditAction(a: string) { return a === 'INSERT' ? 'Dibuat' : a === 'UPDATE' ? 'Diubah' : a === 'DELETE' ? 'Dihapus' : a }
function rowExtra(kind: MasterKind, extra: Record<string, unknown>) {
  if (kind === 'SUPPLIER') return ` · ${supplierTypeLabels[String(extra.supplier_type)] ?? String(extra.supplier_type)}`
  if (kind === 'LOCATION') return ` · ${locationTypeLabels[String(extra.location_type)] ?? String(extra.location_type)}`
  if (kind === 'MANDOR') return `${extra.is_special === true ? ' · Special' : ''}${extra.attendance_required === true ? ' · wajib absensi' : ''}`
  if (kind === 'FABRIC' || kind === 'ACCESSORY') return ` · stok ${String(extra.stock ?? '0').replace(/\.?0+$/, '') || '0'} ${String(extra.unit ?? '')}${kind === 'ACCESSORY' && extra.category_name ? ` · ${String(extra.category_name)}` : ''}`
  if (kind === 'ACCESSORY_CATEGORY') return ` · satuan ${String(extra.base_uom ?? '')}`
  return extra.phone ? ` · ${String(extra.phone)}` : ''
}
const shown = (v: unknown) => v === null || v === undefined || v === '' ? '—' : String(v)
function facts(kind: MasterKind, e: Record<string, unknown>, today: string): [string, string][] {
  switch (kind) {
    case 'CUSTOMER': return [['Telepon', shown(e.phone)], ['Alamat', shown(e.address)]]
    case 'SUPPLIER': return [['Jenis', supplierTypeLabels[String(e.supplier_type)] ?? shown(e.supplier_type)], ['Telepon', shown(e.phone)], ['Alamat', shown(e.address)]]
    case 'LAUNDRY_VENDOR': return [['Telepon', shown(e.phone)], ['Catatan', shown(e.notes)]]
    case 'MANDOR': {
      const p = policyAt(e, today), list = Array.isArray(e.policies) ? e.policies as Record<string, unknown>[] : []
      return [['Wajib absensi', e.attendance_required ? 'Ya' : 'Tidak'], ['Mandor Special hari ini', p ? (p.is_special ? 'Ya' : 'Tidak') : 'Belum diatur'],
        ['Aturan absensi/Special', list.length ? list.map(x => `${x.is_special ? 'Special' : 'Biasa'}${x.attendance_required ? ', wajib absensi' : ''} mulai ${String(x.effective_from)}${x.effective_to ? ` s.d. ${String(x.effective_to)}` : ''}`).join(' · ') : '—'],
        ['Catatan', shown(e.notes)]]
    }
    case 'LOCATION': return [['Jenis', locationTypeLabels[String(e.location_type)] ?? shown(e.location_type)], ['Zona aksesori', shown(e.zone)]]
    case 'FABRIC': {
      const p = (e.profile ?? {}) as Record<string, unknown>, bench = Array.isArray(e.benchmarks) ? e.benchmarks as Record<string, unknown>[] : []
      const open = bench.find(b => b.effective_to === null)
      return [['Satuan', shown(e.unit)], ['Stok', shown(e.stock)], ['Kategori', shown(p.fabric_category)], ['Warna', shown(p.color_name)], ['Komposisi', shown(p.composition)],
        ['Lebar', p.width_cm ? `${String(p.width_cm)} cm` : '—'], ['Gramasi', p.gsm ? `${String(p.gsm)} gsm` : '—'], ['Referensi minimum lama', shown(p.minimum_stock_qty)],
        ['Supplier utama', shown(p.preferred_supplier_name)], ['Harga acuan', open ? `${rupiah(String(open.price))}/${String(open.unit)} mulai ${wibDay(String(open.effective_from))}` : 'Belum ada'],
        ['Riwayat harga acuan', bench.length ? bench.map(b => `${rupiah(String(b.price))} mulai ${wibDay(String(b.effective_from))}`).join(' · ') : '—']]
    }
    case 'ACCESSORY_CATEGORY': {
      const prices = Array.isArray(e.prices) ? e.prices as Record<string, unknown>[] : []
      return [['Satuan dasar', shown(e.base_uom)], ['Catatan', shown(e.notes)],
        ['Harga ke mandor', prices.length ? prices.map(p => `${p.contractor_name ? String(p.contractor_name) : 'Semua mandor'}: ${rupiah(String(p.price))}/${String(p.uom)} mulai ${wibDay(String(p.effective_from))}${p.effective_to ? ` s.d. ${wibDay(String(p.effective_to))}` : ''}`).join(' · ') : 'Belum ada']]
    }
    case 'ACCESSORY': return [['Kategori', shown(e.category_name)], ['Satuan', shown(e.unit)], ['Stok', shown(e.stock)]]
  }
}

