// BD (LAU-05b, LAU-DEC01..06, ALL-W05): laundry prices, priced deliveries, unknown prices, vendor invoices and opening
// uninvoiced laundry work, on the Laundry page. Every write goes through erp_save_laundry_bd_action_v1 with one request id
// (the server replays it); the server checks permissions, policies, capacity and versions again.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { CATEGORY_LABEL, CHARGE_KIND_LABEL, LAU_POLICY_KEYS, LAU_POLICY_LABEL, moneyInput, normalizeMoney, parseLaundryBdWorkspace, policyValue, rupiah,
  signedMoneyInput, validateBdResult, wholePcs, wibTimestamp, type BdInvoice, type Category, type LaundryBdWorkspace, type LauPolicyKey } from './laundryBd'
import type { LaundryQcWorkspace } from './laundryQcModel'
import type { Json } from './types/database.preconnect'

type Section = 'policies' | 'master' | 'send' | 'unknown' | 'invoices' | 'opening'
const SECTIONS: [Section, string][] = [['policies', 'Kebijakan owner'], ['master', 'Harga vendor'], ['send', 'Kirim dengan harga'], ['unknown', 'Harga belum diketahui'],
  ['invoices', 'Invoice vendor'], ['opening', 'Laundry saldo awal']]
type Send = (action: string, payload: Record<string, Json>) => void
const today = () => new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 10)

export default function LaundryBdPanel({ laundry, onPosted }: { laundry: LaundryQcWorkspace | null; onPosted: () => void }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('LAUNDRY_BD')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [data, setData] = useState<LaundryBdWorkspace | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const [section, setSection] = useState<Section>('policies'), [vendorId, setVendorId] = useState('')
  const sequence = useRef(0), vendorRef = useRef('')
  const load = useCallback(async () => {
    const number = ++sequence.current, ticket = beginRead()
    setLoading(true); setError('')
    try {
      const result = await client.rpc('erp_get_laundry_bd_workspace_v1', { p_filters: vendorRef.current ? { vendor_id: vendorRef.current } : {} })
      if (!isReadCurrent(ticket) || number !== sequence.current) return false
      if (result.error) throw result.error
      setData(parseLaundryBdWorkspace(result.data))
      return finishRead(ticket)
    } catch (failure) {
      if (isReadCurrent(ticket) && number === sequence.current) setError(failure instanceof Error ? failure.message : normalizeClientError(failure).message)
      return false
    } finally { if (number === sequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load])
  const chooseVendor = (id: string) => { vendorRef.current = id; setVendorId(id); void load() }
  const handlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_laundry_bd_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (value, envelope) => validateBdResult(value, envelope.action, envelope.id),
    retire: (_value, envelope) => { setData(null); if (envelope.action === 'POST_PRICED_DELIVERY') onPosted() },
    reload: load,
  }
  const send: Send = (action, payload) => { void run(action, payload, null, handlers) }
  const locked = mutation.writerLocked || loading || mutation.busy
  const vendor = data?.vendors.find(v => v.id === vendorId) ?? null
  return <section className="panel initial-import" aria-label="Harga dan tagihan laundry">
    <header className="initial-import-heading"><div><div className="eyebrow">LAUNDRY · HARGA & TAGIHAN</div><h2>Harga laundry dan invoice vendor</h2>
      <p>Harga paket, komponen, borongan, dan tarif khusus mengikuti kebijakan owner. Harga yang belum diketahui tetap tercatat “belum diketahui”, tidak pernah nol. Invoice vendor menagih penerimaan yang sudah diposting, tidak lebih dari yang diterima.</p></div>
      <button type="button" disabled={mutation.busy || loading} onClick={() => void load()}>Muat ulang harga</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert" className="initial-import-message">{error}</p>}
    <nav className="initial-import-toolbar" aria-label="Bagian harga laundry">{SECTIONS.map(([key, label]) =>
      <button key={key} type="button" aria-pressed={section === key} onClick={() => setSection(key)}>{label}</button>)}
      <label>Vendor<select aria-label="Vendor harga laundry" value={vendorId} disabled={locked} onChange={e => chooseVendor(e.target.value)}>
        <option value="">Semua vendor</option>{data?.vendors.map(v => <option key={v.id} value={v.id}>{v.code} · {v.name}{v.bd_priced ? ' · harga BD' : ''}</option>)}</select></label></nav>
    {!data ? <p role="status">{loading ? 'Memuat harga laundry…' : 'Harga laundry belum terbaca.'}</p> : <>
      {section === 'policies' && <Policies data={data} locked={locked} send={send}/>}
      {section === 'master' && (vendor ? <Master data={data} vendor={vendor.id} locked={locked} send={send}/> : <p>Pilih vendor untuk melihat dan mengubah harganya.</p>)}
      {section === 'send' && (!laundry ? <p role="status">Data Laundry (batch siap kirim) belum terbaca; kirim dengan harga terkunci sampai halaman Laundry terbaca.</p>
        : vendor ? <PricedSend data={data} laundry={laundry} vendor={vendor.id} locked={locked} send={send}/> : <p>Pilih vendor laundry yang memakai harga BD.</p>)}
      {section === 'unknown' && <UnknownPrices data={data} locked={locked} send={send}/>}
      {section === 'invoices' && (data.invoices === null ? <p>Hak melihat nominal diperlukan untuk invoice vendor.</p>
        : <Invoices data={data} vendor={vendor?.id ?? ''} locked={locked} send={send}/>)}
      {section === 'opening' && <Opening data={data} locked={locked} send={send}/>}
    </>}
  </section>
}

function Reason({ value, set, locked, label = 'Alasan' }: { value: string; set: (v: string) => void; locked: boolean; label?: string }) {
  return <label>{label}<input aria-label={label} maxLength={1000} value={value} disabled={locked} onChange={e => set(e.target.value)}/></label>
}

function Policies({ data, locked, send }: { data: LaundryBdWorkspace; locked: boolean; send: Send }) {
  const [key, setKey] = useState<LauPolicyKey>('LAU-DEC01'), [f, setF] = useState<Record<string, string>>({}), [pick, setPick] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState('')
  const policy = data.policies.find(p => p.key === key)!
  const value = policyValue(key, f, pick)
  const accounts = (type: 'ASSET' | 'EXPENSE') => (data.accounts ?? []).filter(a => a.type === type)
  const check = (k: string, label: string) => <label key={k}><input type="checkbox" checked={Boolean(pick[k])} disabled={locked} onChange={e => setPick(v => ({ ...v, [k]: e.target.checked }))}/>{label}</label>
  const select = (k: string, label: string, options: [string, string][]) => <label key={k}>{label}<select aria-label={label} value={f[k] ?? ''} disabled={locked} onChange={e => setF(v => ({ ...v, [k]: e.target.value }))}>
    <option value="">Pilih…</option>{options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
  return <section className="initial-import-table" aria-label="Kebijakan laundry">
    <table><thead><tr><th>Kebijakan</th><th>Status</th><th>Nilai</th><th>Versi</th><th>Diubah</th></tr></thead><tbody>{data.policies.map(p =>
      <tr key={p.key}><td>{p.key} · {LAU_POLICY_LABEL[p.key]}</td><td>{p.status === 'SET' ? 'Ditetapkan' : 'Menunggu keputusan owner (ditolak aman)'}</td>
        <td>{p.value ? JSON.stringify(p.value) : '—'}</td><td>{p.version}</td><td>{p.set_at} · {p.reason}</td></tr>)}</tbody></table>
    {data.is_owner ? <div className="initial-import-toolbar">
      <label>Kebijakan<select aria-label="Kebijakan yang diubah" value={key} disabled={locked} onChange={e => { setKey(e.target.value as LauPolicyKey); setF({}); setPick({}) }}>
        {LAU_POLICY_KEYS.map(k => <option key={k} value={k}>{k} · {LAU_POLICY_LABEL[k]}</option>)}</select></label>
      {key === 'LAU-DEC01' && [check('BATCH', 'Borongan per batch'), check('MINIMUM', 'Minimum charge')]}
      {key === 'LAU-DEC02' && [check('GOOD', 'Hasil baik'), check('BS', 'BS laundry'), check('FAILED_ATTEMPT', 'Cuci gagal')]}
      {key === 'LAU-DEC03' && [select('discount', 'Diskon', [['ALLOWED', 'Boleh'], ['REFUSED', 'Ditolak']]), select('extra', 'Tambahan', [['ALLOWED', 'Boleh'], ['REFUSED', 'Ditolak']]),
        select('rounding', 'Pembulatan', [['LAST_LINE', 'Di baris terakhir'], ['REFUSED', 'Ditolak']]),
        select('tax_account_id', 'Akun pajak masukan', accounts('ASSET').map(a => [a.id, `${a.code} · ${a.name}`]))]}
      {key === 'LAU-DEC04' && select('sale', 'Penjualan', [['REFUSE', 'Tolak sampai harga diketahui'], ['ALLOW_PENDING', 'Boleh, tutup buku tetap tertahan']])}
      {key === 'LAU-DEC05' && [check('MODEL', 'Per model'), check('MODEL_SIZE', 'Per model + ukuran'), check('MODEL_SIZE_COLOR', 'Per model + ukuran + warna'),
        select('fallback', 'Tanpa tarif khusus', [['BASE_RATE', 'Pakai tarif proses'], ['REFUSE', 'Tolak']])]}
      {key === 'LAU-DEC06' && [select('variance_mode', 'Selisih invoice', [['PRODUCT_COST', 'Ke biaya produk'], ['VARIANCE_ACCOUNT', 'Ke akun beban selisih']]),
        select('after_payment', 'Koreksi sesudah bayar', [['REFUSE', 'Ditolak'], ['CORRECTION_DOCUMENT', 'Dokumen koreksi']]),
        ...(f.variance_mode === 'VARIANCE_ACCOUNT' ? [select('variance_account_id', 'Akun beban selisih', accounts('EXPENSE').map(a => [a.id, `${a.code} · ${a.name}`]))] : [])]}
      <Reason value={reason} set={setReason} locked={locked}/>
      {typeof value === 'string' && <small>{value}</small>}
      <button type="button" disabled={locked || typeof value === 'string' || !reason.trim()} onClick={() => typeof value !== 'string' &&
        send('SET_POLICY', { policy_key: key, operation: 'SET', expected_version: policy.version, reason: reason.trim(), value })}>Tetapkan {key}</button>
      <button type="button" disabled={locked || policy.status !== 'SET' || !reason.trim()} onClick={() =>
        send('SET_POLICY', { policy_key: key, operation: 'CLEAR', expected_version: policy.version, reason: reason.trim() })}>Kembalikan {key} ke menunggu</button>
    </div> : <p>Hanya owner yang dapat menetapkan kebijakan laundry.</p>}
  </section>
}

function Master({ data, vendor, locked, send }: { data: LaundryBdWorkspace; vendor: string; locked: boolean; send: Send }) {
  const v = data.vendors.find(x => x.id === vendor)!
  const [f, setF] = useState<Record<string, string>>({ mode: v.pricing_mode, unit: v.pricing_unit, from: '' }), [reason, setReason] = useState('')
  const [pkgComponents, setPkgComponents] = useState<string[]>([])
  const set = (patch: Record<string, string>) => setF(x => ({ ...x, ...patch }))
  const components = data.components.filter(c => c.vendor_id === vendor), packages = data.packages.filter(p => p.vendor_id === vendor)
  const from = wibTimestamp(f.from ?? '')
  const can = data.can_manage_master && !locked && Boolean(reason.trim())
  const field = (k: string, label: string, type = 'text') => <label key={k}>{label}<input aria-label={label} type={type} value={f[k] ?? ''} disabled={locked} onChange={e => set({ [k]: e.target.value })}/></label>
  return <section className="initial-import-table" aria-label="Harga vendor">
    <h3>{v.code} · {v.name}</h3>
    <p>Cara harga {v.pricing_mode} · satuan {v.pricing_unit}{v.minimum_charge !== null ? ` · minimum ${rupiah(v.minimum_charge)}` : ''} · versi ketentuan {v.terms_version}</p>
    {!data.can_manage_master && <p>Hak master mitra diperlukan untuk mengubah harga vendor.</p>}
    <div className="initial-import-toolbar"><Reason value={reason} set={setReason} locked={locked}/>{field('from', 'Berlaku sejak (WIB)', 'datetime-local')}</div>
    <div className="initial-import-toolbar">
      <label>Cara harga<select aria-label="Cara harga vendor" value={f.mode} disabled={locked} onChange={e => set({ mode: e.target.value })}><option value="RATE">Tarif per proses</option><option value="PACKAGE">Paket</option><option value="COMPONENTS">Komponen</option></select></label>
      <label>Satuan<select aria-label="Satuan harga vendor" value={f.unit} disabled={locked} onChange={e => set({ unit: e.target.value })}><option value="PCS">Per PCS</option><option value="BATCH">Borongan per batch</option></select></label>
      {field('minimum', 'Minimum charge (kosong = tidak ada)')}
      <button type="button" disabled={!can || (Boolean(f.minimum?.trim()) && !moneyInput(f.minimum))} onClick={() => send('SAVE_VENDOR_TERMS', { vendor_id: vendor, pricing_mode: f.mode,
        pricing_unit: f.unit, minimum_charge: f.minimum?.trim() ? normalizeMoney(f.minimum) : null, expected_version: v.terms_version, reason: reason.trim() })}>Simpan ketentuan</button></div>
    <h4>Komponen</h4>
    <table><thead><tr><th>Komponen</th><th>Harga berlaku</th><th>Aktif</th></tr></thead><tbody>{components.map(c => <tr key={c.id}><td>{c.code} · {c.name}</td>
      <td>{c.current ? (c.current.status === 'UNKNOWN' ? `Belum diketahui sejak ${c.current.from}` : `${rupiah(c.current.rate)} sejak ${c.current.from}`) : 'Belum ada versi harga'}</td>
      <td>{c.is_active ? 'Ya' : 'Tidak'}</td></tr>)}</tbody></table>
    <div className="initial-import-toolbar">{field('component_code', 'Kode komponen')}{field('component_name', 'Nama komponen')}
      <button type="button" disabled={!can || !f.component_code?.trim() || !f.component_name?.trim()} onClick={() => send('SAVE_COMPONENT', { vendor_id: vendor,
        component_code: f.component_code.trim(), component_name: f.component_name.trim(), is_active: true, reason: reason.trim() })}>Tambah komponen</button></div>
    <div className="initial-import-toolbar"><label>Komponen<select aria-label="Komponen harga" value={f.component_id ?? ''} disabled={locked} onChange={e => set({ component_id: e.target.value })}>
      <option value="">Pilih…</option>{components.map(c => <option key={c.id} value={c.id}>{c.code}</option>)}</select></label>
      <label>Status harga<select aria-label="Status harga komponen" value={f.rate_status ?? 'KNOWN'} disabled={locked} onChange={e => set({ rate_status: e.target.value })}><option value="KNOWN">Diketahui</option><option value="UNKNOWN">Belum diketahui</option></select></label>
      {(f.rate_status ?? 'KNOWN') === 'KNOWN' && field('component_rate', 'Harga per PCS')}
      <button type="button" disabled={!can || !f.component_id || !from || ((f.rate_status ?? 'KNOWN') === 'KNOWN' && !moneyInput(f.component_rate ?? ''))} onClick={() => from &&
        send('SAVE_COMPONENT_RATE', { component_id: f.component_id, rate_status: f.rate_status ?? 'KNOWN', effective_from: from, reason: reason.trim(),
          ...((f.rate_status ?? 'KNOWN') === 'KNOWN' ? { rate_per_pcs: normalizeMoney(f.component_rate) } : {}) })}>Simpan versi harga komponen</button></div>
    <h4>Paket</h4>
    <table><thead><tr><th>Paket</th><th>Isi</th><th>Harga berlaku</th></tr></thead><tbody>{packages.map(p => <tr key={p.id}><td>{p.code} · {p.name}</td>
      <td>{p.component_ids.map(id => components.find(c => c.id === id)?.code ?? id).join(', ')}</td><td>{p.current_rate === null ? '—' : rupiah(p.current_rate)}</td></tr>)}</tbody></table>
    <div className="initial-import-toolbar">{field('package_code', 'Kode paket')}{field('package_name', 'Nama paket')}
      <fieldset><legend>Isi paket</legend>{components.map(c => <label key={c.id}><input type="checkbox" checked={pkgComponents.includes(c.id)} disabled={locked}
        onChange={e => setPkgComponents(x => e.target.checked ? [...x, c.id] : x.filter(y => y !== c.id))}/>{c.code}</label>)}</fieldset>
      <button type="button" disabled={!can || !f.package_code?.trim() || !f.package_name?.trim() || !pkgComponents.length} onClick={() => send('SAVE_PACKAGE', { vendor_id: vendor,
        package_code: f.package_code.trim(), package_name: f.package_name.trim(), component_ids: pkgComponents, is_active: true, reason: reason.trim() })}>Tambah paket</button></div>
    <div className="initial-import-toolbar"><label>Paket<select aria-label="Paket harga" value={f.package_id ?? ''} disabled={locked} onChange={e => set({ package_id: e.target.value })}>
      <option value="">Pilih…</option>{packages.map(p => <option key={p.id} value={p.id}>{p.code}</option>)}</select></label>{field('package_rate', 'Harga paket per PCS')}
      <button type="button" disabled={!can || !f.package_id || !from || !moneyInput(f.package_rate ?? '')} onClick={() => from && send('SAVE_PACKAGE_RATE', { package_id: f.package_id,
        rate_per_pcs: normalizeMoney(f.package_rate), effective_from: from, reason: reason.trim() })}>Simpan versi harga paket</button></div>
    <h4>Tarif proses</h4>
    <table><thead><tr><th>Proses</th><th>Tarif</th><th>Berlaku</th></tr></thead><tbody>{data.process_rates.filter(r => r.vendor_id === vendor).map(r => <tr key={r.id}>
      <td>{data.processes.find(p => p.id === r.wash_process_id)?.name ?? r.wash_process_id}</td><td>{rupiah(r.rate)}</td><td>{r.from} – {r.to ?? 'sekarang'}</td></tr>)}</tbody></table>
    <div className="initial-import-toolbar"><label>Proses<select aria-label="Proses tarif" value={f.process_id ?? ''} disabled={locked} onChange={e => set({ process_id: e.target.value })}>
      <option value="">Pilih…</option>{data.processes.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>{field('process_rate', 'Tarif per PCS')}
      <button type="button" disabled={!can || !f.process_id || !from || !moneyInput(f.process_rate ?? '')} onClick={() => from && send('SAVE_PROCESS_RATE', { vendor_id: vendor,
        wash_process_id: f.process_id, rate_per_pcs: normalizeMoney(f.process_rate), effective_from: from, reason: reason.trim() })}>Simpan versi tarif proses</button></div>
    <p>Tarif khusus per model, ukuran, atau warna mengikuti LAU-DEC05; tercatat {data.scoped_rates.filter(r => r.vendor_id === vendor).length} tarif khusus untuk vendor ini.</p>
  </section>
}

function PricedSend({ data, laundry, vendor, locked, send }: { data: LaundryBdWorkspace; laundry: LaundryQcWorkspace; vendor: string; locked: boolean; send: Send }) {
  const v = data.vendors.find(x => x.id === vendor)!
  const [batchId, setBatchId] = useState(''), [process, setProcess] = useState(''), [color, setColor] = useState(''), [at, setAt] = useState('')
  const [reason, setReason] = useState(''), [qty, setQty] = useState<Record<string, string>>({}), [packageId, setPackageId] = useState(''), [lump, setLump] = useState('')
  const [covered, setCovered] = useState<Record<string, string>>({}), [confirmed, setConfirmed] = useState(false)
  const batch = laundry.ready_batches.find(b => b.distribution_batch_id === batchId)
  const lines = batch?.sizes.map(s => ({ size_id: s.size_id, qty_sent_pcs: wholePcs(qty[s.size_id] ?? '') ? Number(qty[s.size_id]) : 0 })).filter(l => l.qty_sent_pcs > 0) ?? []
  const physical = wibTimestamp(at)
  const components = data.components.filter(c => c.vendor_id === vendor && c.is_active)
  const pricing: Record<string, Json> | null = v.pricing_unit === 'BATCH' ? (moneyInput(lump) ? { lump_sum: normalizeMoney(lump) } : null)
    : v.pricing_mode === 'PACKAGE' ? (packageId ? { package_id: packageId } : null)
    : v.pricing_mode === 'COMPONENTS' ? (() => { const c = components.filter(x => wholePcs(covered[x.id] ?? '')).map(x => ({ component_id: x.id, covered_qty: Number(covered[x.id]) }))
      return c.length ? { components: c } : null })() : {}
  const valid = batch && process && color.trim() && physical && reason.trim().length >= 4 && lines.length && pricing && confirmed
    && batch.sizes.every(s => !qty[s.size_id] || (wholePcs(qty[s.size_id]) && Number(qty[s.size_id]) <= s.available_qty_pcs))
  return <section className="initial-import-table" aria-label="Kirim laundry dengan harga BD">
    <p>{v.code} memakai {v.pricing_mode === 'RATE' ? 'tarif proses' : v.pricing_mode === 'PACKAGE' ? 'harga paket' : 'harga komponen'} per {v.pricing_unit === 'BATCH' ? 'batch (borongan)' : 'PCS'}.
      Kiriman dicatat sekali: fisik, WIP, dan estimasi biaya bersama-sama. Harga komponen yang belum diketahui tetap “belum diketahui”.</p>
    <div className="initial-import-toolbar">
      <label>Batch<select aria-label="Batch kirim berharga" value={batchId} disabled={locked} onChange={e => { setBatchId(e.target.value); setQty({}); setConfirmed(false) }}>
        <option value="">Pilih batch…</option>{laundry.ready_batches.map(b => <option key={b.distribution_batch_id} value={b.distribution_batch_id}>{b.po_number} · {b.group_number} · Batch {b.batch_no} · siap {b.group_unsent_ready_qty_pcs} pcs</option>)}</select></label>
      <label>Proses<select aria-label="Proses kirim berharga" value={process} disabled={locked} onChange={e => { setProcess(e.target.value); setConfirmed(false) }}>
        <option value="">Pilih…</option>{laundry.lookups.wash_processes.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>
      <label>Warna<input aria-label="Warna kirim berharga" value={color} disabled={locked} onChange={e => { setColor(e.target.value); setConfirmed(false) }}/></label>
      <label>Waktu keluar (WIB)<input aria-label="Waktu kirim berharga" type="datetime-local" value={at} disabled={locked} onChange={e => { setAt(e.target.value); setConfirmed(false) }}/></label>
      <Reason value={reason} set={v => { setReason(v); setConfirmed(false) }} locked={locked} label="Bukti serah terima"/></div>
    {batch && <div className="initial-import-toolbar">{batch.sizes.map(s => <label key={s.size_id}>Ukuran {s.size_code} (bisa {s.available_qty_pcs})<input aria-label={`Qty kirim berharga ${s.size_code}`}
      inputMode="numeric" value={qty[s.size_id] ?? ''} disabled={locked} onChange={e => { setQty(x => ({ ...x, [s.size_id]: e.target.value })); setConfirmed(false) }}/></label>)}</div>}
    <div className="initial-import-toolbar">
      {v.pricing_unit === 'BATCH' && <label>Harga borongan batch<input aria-label="Harga borongan" value={lump} disabled={locked} onChange={e => { setLump(e.target.value); setConfirmed(false) }}/></label>}
      {v.pricing_unit === 'PCS' && v.pricing_mode === 'PACKAGE' && <label>Paket<select aria-label="Paket kirim berharga" value={packageId} disabled={locked} onChange={e => { setPackageId(e.target.value); setConfirmed(false) }}>
        <option value="">Pilih…</option>{data.packages.filter(p => p.vendor_id === vendor && p.is_active).map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>}
      {v.pricing_unit === 'PCS' && v.pricing_mode === 'COMPONENTS' && components.map(c => <label key={c.id}>{c.code} (PCS tercakup{c.current?.status === 'UNKNOWN' ? ', harga belum diketahui' : ''})
        <input aria-label={`Cakupan ${c.code}`} inputMode="numeric" value={covered[c.id] ?? ''} disabled={locked} onChange={e => { setCovered(x => ({ ...x, [c.id]: e.target.value })); setConfirmed(false) }}/></label>)}
    </div>
    <label><input type="checkbox" checked={confirmed} disabled={locked} onChange={e => setConfirmed(e.target.checked)}/>Vendor, batch, ukuran, jumlah, warna, waktu, dan harga sudah dicocokkan dengan serah-terima.</label>
    <button type="button" disabled={locked || !valid} onClick={() => batch && physical && pricing && send('POST_PRICED_DELIVERY', {
      expected_version: String(batch.cutting_group_row_version), pricing,
      delivery: { distribution_batch_id: batch.distribution_batch_id, vendor_id: vendor, wash_process_id: process, target_dyeing_color: color.trim(),
        physical_at: physical, reason: reason.trim(), notes: null, lines } })}>Catat kiriman berharga</button>
  </section>
}

function UnknownPrices({ data, locked, send }: { data: LaundryBdWorkspace; locked: boolean; send: Send }) {
  const [rate, setRate] = useState<Record<string, string>>({}), [reason, setReason] = useState('')
  const pending = data.priced_deliveries.filter(d => !d.total_complete)
  return <section className="initial-import-table" aria-label="Harga laundry belum diketahui">
    <p>Selama harga komponen belum diketahui, biaya laundry kiriman ini baru bagian yang diketahui, HPP tetap estimasi, dan tutup buku tertahan (LAU-T12).</p>
    <Reason value={reason} set={setReason} locked={locked}/>
    {pending.length === 0 ? <p>Tidak ada harga laundry yang belum diketahui.</p> : <table><thead><tr><th>Kiriman</th><th>Rincian</th><th>PCS</th><th>Harga diketahui</th><th>Isi harga</th></tr></thead>
      <tbody>{pending.flatMap(d => d.charges.map(c => <tr key={c.id}><td>{d.delivery_number} · {d.physical_local}</td><td>{CHARGE_KIND_LABEL[c.kind]} · {c.label}</td><td>{c.covered_qty}</td>
        <td>{c.rate_status === 'KNOWN' ? rupiah(c.amount) : 'Belum diketahui'}</td>
        <td>{c.rate_status === 'UNKNOWN' && data.can_set_price && <><input aria-label={`Harga per PCS ${c.label}`} value={rate[c.id] ?? ''} disabled={locked} onChange={e => setRate(x => ({ ...x, [c.id]: e.target.value }))}/>
          <button type="button" disabled={locked || !moneyInput(rate[c.id] ?? '') || !reason.trim()} onClick={() => send('SET_CHARGE_PRICE', { charge_line_id: c.id,
            rate_per_pcs: normalizeMoney(rate[c.id]), reason: reason.trim() })}>Isi harga {c.label}</button></>}</td></tr>))}</tbody></table>}
  </section>
}

type DraftLine = { key: string; kind: 'BILL' | 'CORRECTION'; source: string; category: Category; qty: string; amount: string }
function Invoices({ data, vendor, locked, send }: { data: LaundryBdWorkspace; vendor: string; locked: boolean; send: Send }) {
  const [editing, setEditing] = useState<BdInvoice | null>(null)
  const [head, setHead] = useState<Record<string, string>>({ number: '', date: today(), due: '', total: '', discount: '', tax: '', rounding: '' })
  const [lines, setLines] = useState<DraftLine[]>([]), [reason, setReason] = useState('')
  const invoices = data.invoices ?? [], billable = data.billable_receipts ?? [], opening = data.opening_uninvoiced.filter(u => u.vendor_id === vendor && !u.invoiced)
  const sourceLabel = (s: string) => s.startsWith('r:') ? (() => { const b = billable.find(x => x.receipt_line_id === s.slice(2)); return b ? `${b.receipt_number} · ${b.po_number}` : s })()
    : (() => { const u = data.opening_uninvoiced.find(x => x.id === s.slice(2)); return u ? `Saldo awal ${u.document_number} · ${CATEGORY_LABEL[u.category]}` : s })()
  const setLine = (i: number, patch: Partial<DraftLine>) => setLines(ls => ls.map((l, j) => j === i ? { ...l, ...patch } : l))
  const edit = (i: BdInvoice | null) => {
    setEditing(i)
    setHead(i ? { number: i.invoice_number, date: i.invoice_date, due: i.due_date ?? '', total: i.header_total, discount: i.discount_amount === '0.00' ? '' : i.discount_amount,
      tax: i.tax_amount === '0.00' ? '' : i.tax_amount, rounding: i.rounding_amount === '0.00' ? '' : i.rounding_amount } : { number: '', date: today(), due: '', total: '', discount: '', tax: '', rounding: '' })
    setLines(i ? i.lines.map(l => ({ key: l.id, kind: l.line_kind, source: l.receipt_line_id ? 'r:' + l.receipt_line_id : 'o:' + l.opening_uninvoiced_id, category: l.category,
      qty: String(l.qty), amount: l.amount })) : [])
  }
  const lineOk = (l: DraftLine) => l.source && (l.kind === 'BILL' ? wholePcs(l.qty) && moneyInput(l.amount) : signedMoneyInput(l.amount) && !/^-?0+([.,]0+)?$/.test(l.amount.trim()))
  const valid = vendor && head.number.trim() && /^\d{4}-\d{2}-\d{2}$/.test(head.date) && moneyInput(head.total) && lines.length > 0 && lines.every(lineOk)
    && (!head.discount || moneyInput(head.discount)) && (!head.tax || moneyInput(head.tax)) && (!head.rounding || signedMoneyInput(head.rounding))
  const payload = (): Record<string, Json> => ({ ...(editing ? { invoice_id: editing.invoice_id, expected_version: editing.row_version } : {}), vendor_id: vendor,
    invoice_number: head.number.trim(), invoice_date: head.date, due_date: head.due || null, header_total: normalizeMoney(head.total),
    ...(head.discount ? { discount_amount: normalizeMoney(head.discount) } : {}), ...(head.tax ? { tax_amount: normalizeMoney(head.tax) } : {}),
    ...(head.rounding ? { rounding_amount: (head.rounding.trim().startsWith('-') ? '-' : '') + normalizeMoney(head.rounding.trim().replace('-', '')) } : {}),
    lines: lines.map(l => ({ line_kind: l.kind, category: l.category, qty: l.kind === 'BILL' ? Number(l.qty) : 0,
      amount: (l.amount.trim().startsWith('-') ? '-' : '') + normalizeMoney(l.amount.trim().replace('-', '')),
      ...(l.source.startsWith('r:') ? { receipt_line_id: l.source.slice(2) } : { opening_uninvoiced_id: l.source.slice(2) }) })) })
  return <section className="initial-import-table" aria-label="Invoice vendor laundry">
    <table><thead><tr><th>Invoice</th><th>Vendor</th><th>Tanggal</th><th>Total</th><th>Dibayar</th><th>Status</th><th/></tr></thead><tbody>{invoices.map(i => <tr key={i.invoice_id}>
      <td>{i.invoice_number}</td><td>{i.vendor_code}</td><td>{i.invoice_date}</td><td>{rupiah(i.header_total)}</td><td>{rupiah(i.paid)}</td><td>{i.status}{i.variance_mode ? ` · selisih ${i.variance_mode === 'PRODUCT_COST' ? 'ke biaya produk' : 'ke akun selisih'}` : ''}</td>
      <td>{i.status === 'DRAFT' && <><button type="button" disabled={locked} onClick={() => edit(i)}>Ubah draf {i.invoice_number}</button>
        <button type="button" disabled={locked} onClick={() => send('POST_INVOICE', { invoice_id: i.invoice_id, expected_version: i.row_version })}>Posting {i.invoice_number}</button>
        <button type="button" disabled={locked} onClick={() => send('CANCEL_INVOICE_DRAFT', { invoice_id: i.invoice_id, expected_version: i.row_version })}>Batalkan draf {i.invoice_number}</button></>}
        {i.status === 'POSTED' && <button type="button" disabled={locked || !reason.trim() || i.paid !== '0.00'} onClick={() => send('REVERSE_INVOICE', { invoice_id: i.invoice_id,
          expected_version: i.row_version, reason: reason.trim() })}>Batalkan invoice {i.invoice_number}</button>}</td></tr>)}</tbody></table>
    <Reason value={reason} set={setReason} locked={locked} label="Alasan pembatalan invoice"/>
    {!vendor ? <p>Pilih vendor untuk membuat draf invoice.</p> : <>
      <h4>{editing ? `Ubah draf ${editing.invoice_number}` : 'Draf invoice baru'}</h4>
      <div className="initial-import-toolbar">
        {([['number', 'Nomor invoice vendor'], ['date', 'Tanggal invoice'], ['due', 'Jatuh tempo'], ['total', 'Total invoice'], ['discount', 'Diskon'], ['tax', 'Pajak masukan'],
          ['rounding', 'Pembulatan']] as const).map(([k, label]) => <label key={k}>{label}<input aria-label={label} type={k === 'date' || k === 'due' ? 'date' : 'text'} value={head[k]}
            disabled={locked} onChange={e => setHead(h => ({ ...h, [k]: e.target.value }))}/></label>)}</div>
      {lines.map((l, i) => <div key={l.key} className="initial-import-toolbar">
        <label>Jenis<select aria-label={`Jenis baris ${i + 1}`} value={l.kind} disabled={locked} onChange={e => setLine(i, { kind: e.target.value as DraftLine['kind'] })}><option value="BILL">Tagihan</option><option value="CORRECTION">Koreksi (qty 0)</option></select></label>
        <label>Sumber<select aria-label={`Sumber baris ${i + 1}`} value={l.source} disabled={locked} onChange={e => setLine(i, { source: e.target.value })}><option value="">Pilih…</option>
          {billable.map(b => <option key={b.receipt_line_id} value={'r:' + b.receipt_line_id}>{b.receipt_number} · {b.po_number} · baik {b.billed.GOOD}/{b.capacity.GOOD} · BS {b.billed.BS}/{b.capacity.BS} · gagal {b.billed.FAILED_ATTEMPT}/{b.capacity.FAILED_ATTEMPT}{b.price_known ? '' : ' · harga belum lengkap'}</option>)}
          {opening.map(u => <option key={u.id} value={'o:' + u.id}>Saldo awal {u.document_number} · {CATEGORY_LABEL[u.category]} {u.billed}/{u.qty}{u.estimate_status === 'UNKNOWN' ? ' · estimasi belum diketahui' : ''}</option>)}
          {l.source && !billable.some(b => 'r:' + b.receipt_line_id === l.source) && !opening.some(u => 'o:' + u.id === l.source) && <option value={l.source}>{sourceLabel(l.source)}</option>}</select></label>
        <label>Kategori<select aria-label={`Kategori baris ${i + 1}`} value={l.category} disabled={locked} onChange={e => setLine(i, { category: e.target.value as Category })}>
          {(Object.keys(CATEGORY_LABEL) as Category[]).map(c => <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>)}</select></label>
        {l.kind === 'BILL' && <label>Qty<input aria-label={`Qty baris ${i + 1}`} inputMode="numeric" value={l.qty} disabled={locked} onChange={e => setLine(i, { qty: e.target.value })}/></label>}
        <label>Nominal<input aria-label={`Nominal baris ${i + 1}`} value={l.amount} disabled={locked} onChange={e => setLine(i, { amount: e.target.value })}/></label>
        <button type="button" disabled={locked} onClick={() => setLines(ls => ls.filter((_, j) => j !== i))}>Hapus baris {i + 1}</button></div>)}
      <div className="initial-import-toolbar"><button type="button" disabled={locked} onClick={() => setLines(ls => [...ls, { key: crypto.randomUUID(), kind: 'BILL', source: '', category: 'GOOD', qty: '', amount: '' }])}>Tambah baris</button>
        <button type="button" disabled={locked || !valid} onClick={() => send('SAVE_INVOICE_DRAFT', payload())}>Simpan draf invoice</button>
        {editing && <button type="button" disabled={locked} onClick={() => edit(null)}>Draf baru</button>}</div>
      <p>Total invoice harus sama dengan baris − diskon + pembulatan + pajak. Posting memeriksa kebijakan LAU-DEC02/03/06, kapasitas tiap sumber, dan harga yang belum diketahui.</p>
    </>}
  </section>
}

function Opening({ data, locked, send }: { data: LaundryBdWorkspace; locked: boolean; send: Send }) {
  const [estimate, setEstimate] = useState<Record<string, string>>({}), [reason, setReason] = useState('')
  return <section className="initial-import-table" aria-label="Laundry saldo awal belum ditagih">
    <p>Hasil laundry yang sudah kembali sebelum saldo awal tetapi belum ditagih vendor. Estimasi yang terbukti menjadi akrual saldo awal; tanpa estimasi nilainya belum diketahui dan tutup buku tertahan sampai estimasi diisi atau invoice vendor menagihnya.</p>
    <Reason value={reason} set={setReason} locked={locked}/>
    {data.opening_uninvoiced.length === 0 ? <p>Tidak ada laundry saldo awal yang belum ditagih.</p> : <table><thead><tr><th>Terima lama</th><th>Vendor</th><th>Kategori</th><th>Qty</th><th>Ditagih</th><th>Estimasi</th><th>Dilepas</th><th>Status</th></tr></thead>
      <tbody>{data.opening_uninvoiced.map(u => <tr key={u.id}><td>{u.document_number} · {u.receipt_date}{u.po_number ? ` · ${u.po_number}` : ''}</td><td>{u.vendor_code}</td><td>{CATEGORY_LABEL[u.category]}</td>
        <td>{u.qty}</td><td>{u.billed}</td><td>{u.estimate_status === 'UNKNOWN' ? 'Belum diketahui' : rupiah(u.estimated_amount)}</td><td>{rupiah(u.released)}</td>
        <td>{u.invoiced ? 'Ditagih penuh' : u.estimate_status === 'UNKNOWN' ? <>{data.can_set_price && u.billed === 0 && <><input aria-label={`Estimasi ${u.document_number}`} value={estimate[u.id] ?? ''} disabled={locked}
          onChange={e => setEstimate(x => ({ ...x, [u.id]: e.target.value }))}/><button type="button" disabled={locked || !moneyInput(estimate[u.id] ?? '') || !reason.trim()} onClick={() =>
            send('SET_OPENING_ESTIMATE', { opening_uninvoiced_id: u.id, expected_version: u.row_version, estimated_amount: normalizeMoney(estimate[u.id]), reason: reason.trim() })}>Isi estimasi {u.document_number}</button></>}
          </> : 'Menunggu invoice vendor'}</td></tr>)}</tbody></table>}
  </section>
}
