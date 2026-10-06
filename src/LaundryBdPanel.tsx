// BD (LAU-05b, LAU-DEC01..06, ALL-W05): laundry prices, priced deliveries, unknown prices, vendor invoices and opening
// uninvoiced laundry work, on the Laundry page. BD writes and the BE redye-price facade use one request id
// (the server replays it); the server checks permissions, policies, capacity and versions again.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import Cp6PolicyReadiness from './Cp6PolicyReadiness'
import { invoicePolicyMessage, ownerChoice, POLICY_EFFECT, policyStatus, policyValueText } from './cp6Readiness'
import LaundrySkuHistory, { type LaundryHistoryItem } from './LaundrySkuHistory'
import { BD_RATE_LABEL, BD_RATE_STATUSES, CATEGORY_LABEL, CHARGE_KIND_LABEL, LAU_POLICY_KEYS, LAU_POLICY_LABEL, mergeLaundryBdPage, moneyInput, normalizeMoney, parseLaundryBdWorkspace, policyValue, rupiah,
  signedMoneyInput, validateBdResult, wholePcs, wibTimestamp, type BdInvoice, type BdPageKind, type BdPayables, type Category, type LaundryBdWorkspace, type LauPolicyKey } from './laundryBd'
import { validateConversionResult } from './productConversion'
import type { LaundryQcWorkspace } from './laundryQcModel'
import type { Json } from './types/database.preconnect'
import './initial-import.css'

type Section = 'policies' | 'master' | 'send' | 'unknown' | 'invoices' | 'payables' | 'opening'
const SECTIONS: [Section, string][] = [['policies', 'Kebijakan owner'], ['master', 'Harga vendor'], ['send', 'Kirim & rincian biaya'], ['unknown', 'Harga belum diketahui'],
  ['invoices', 'Invoice vendor'], ['payables', 'Pembayaran vendor'], ['opening', 'Laundry saldo awal']]
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
  const loadMore = async (kind: BdPageKind) => {
    if (!data || loading || mutation.writerLocked || mutation.busy) return
    const cursor = kind === 'invoices' ? data.pagination.invoice_next : data.pagination.receipt_next
    if (!cursor) return
    const previous = data, number = ++sequence.current, ticket = beginRead()
    setLoading(true); setError('')
    try {
      const result = await client.rpc('erp_get_laundry_bd_workspace_v1', { p_filters: {
        ...(vendorRef.current ? { vendor_id: vendorRef.current } : {}), page_as_of: previous.pagination.as_of,
        [kind === 'invoices' ? 'invoice_after' : 'receipt_after']: cursor,
      } })
      if (!isReadCurrent(ticket) || number !== sequence.current) return
      if (result.error) throw result.error
      setData(mergeLaundryBdPage(previous, parseLaundryBdWorkspace(result.data), kind))
      finishRead(ticket)
    } catch (failure) {
      if (isReadCurrent(ticket) && number === sequence.current) setError(failure instanceof Error ? failure.message : normalizeClientError(failure).message)
    } finally { if (number === sequence.current) setLoading(false) }
  }
  const handlers: ProductionMutationHandlers = {
    send: envelope => envelope.action === 'SET_REDYE_PRICE'
      ? client.rpc('erp_save_product_conversion_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id })
      : client.rpc('erp_save_laundry_bd_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (value, envelope) => envelope.action === 'SET_REDYE_PRICE'
      ? validateConversionResult(value, envelope.action, envelope.id, envelope.payload) : validateBdResult(value, envelope.action, envelope.id),
    retire: () => { setData(null) },
    reload: async () => {
      const refreshed = await load()
      // Every definite BD result retires the owning Laundry read too. Start its
      // new read after recovery clears; a ticket captured before that is stale.
      onPosted()
      return refreshed
    },
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
      <Cp6PolicyReadiness policies={data.policies}/>
      {section === 'invoices' && invoicePolicyMessage(data.policies) && <p role="status" className="initial-import-message">{invoicePolicyMessage(data.policies)}</p>}
      {section === 'policies' && <Policies data={data} locked={locked} send={send}/>}
      {section === 'master' && (vendor ? <Master key={vendor.id} data={data} vendor={vendor.id} locked={locked} send={send}/> : <p>Pilih vendor untuk melihat dan mengubah harganya.</p>)}
      {section === 'send' && (!laundry ? <p role="status">Data Laundry (batch siap kirim) belum terbaca; kirim dengan harga terkunci sampai halaman Laundry terbaca.</p>
        : vendor ? <PricedSend key={vendor.id} data={data} laundry={laundry} vendor={vendor.id} locked={locked} send={send}/> : <p>Pilih vendor laundry yang memakai harga BD.</p>)}
      {section === 'unknown' && <UnknownPrices data={data} locked={locked} send={send}/>}
      {section === 'invoices' && (data.invoices === null ? <p>Hak melihat nominal diperlukan untuk invoice vendor.</p>
        : <Invoices key={vendor?.id ?? ''} data={data} vendor={vendor?.id ?? ''} locked={locked} send={send} loadMore={kind => void loadMore(kind)}
          canSetRedye={data.can_set_price && identity.permissions.includes('warehouse.brand_conversion.view') && identity.permissions.includes('warehouse.brand_conversion.post')}/>)}
      {section === 'payables' && (!data.money_visible ? <p>Hak melihat nominal diperlukan untuk pembayaran vendor.</p>
        : !vendor || !data.payables ? <p>Pilih vendor untuk melihat tagihan, kredit klaim, dan pembayarannya.</p>
        : <Payables payables={data.payables} locked={locked} send={send}/>)}
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
      <tr key={p.key}><td>{p.key} · {LAU_POLICY_LABEL[p.key]}</td><td>{policyStatus(p)}</td>
        <td>{policyValueText(p, data.accounts ?? [])}</td><td>{p.version}</td><td>{p.set_at} · {p.reason}</td></tr>)}</tbody></table>
    {data.is_owner ? <div className="initial-import-toolbar">
      <label>Kebijakan<select aria-label="Kebijakan yang diubah" value={key} disabled={locked} onChange={e => { setKey(e.target.value as LauPolicyKey); setF({}); setPick({}) }}>
        {LAU_POLICY_KEYS.map(k => <option key={k} value={k}>{k} · {LAU_POLICY_LABEL[k]}</option>)}</select></label>
      <p>{policy.status === 'SET' ? 'Nilai yang berlaku terlihat pada tabel. Perubahan memakai pilihan baru di bawah.' : POLICY_EFFECT[key]}</p>
      {policy.status !== 'SET' && ownerChoice(key) && <button type="button" disabled={locked} onClick={() => {
        const choice = ownerChoice(key)!; setF(choice.fields); setPick(choice.picks); setReason(`Terapkan keputusan owner 26 Sep 2026 untuk ${key}`)
      }}>Isi sesuai keputusan owner</button>}
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
      <td>{c.current ? `${BD_RATE_LABEL[c.current.status]}${c.current.status === 'KNOWN' ? ` · ${rupiah(c.current.rate)}` : ''} sejak ${c.current.from} · ${c.current.reason}` : 'Belum ada versi harga'}</td>
      <td>{c.is_active ? 'Ya' : 'Tidak'}</td></tr>)}</tbody></table>
    <div className="initial-import-toolbar">{field('component_code', 'Kode komponen')}{field('component_name', 'Nama komponen')}
      <button type="button" disabled={!can || !f.component_code?.trim() || !f.component_name?.trim()} onClick={() => send('SAVE_COMPONENT', { vendor_id: vendor,
        component_code: f.component_code.trim(), component_name: f.component_name.trim(), is_active: true, reason: reason.trim() })}>Tambah komponen</button></div>
    <div className="initial-import-toolbar"><label>Komponen<select aria-label="Komponen harga" value={f.component_id ?? ''} disabled={locked} onChange={e => set({ component_id: e.target.value })}>
      <option value="">Pilih…</option>{components.map(c => <option key={c.id} value={c.id}>{c.code}</option>)}</select></label>
      <label>Status harga<select aria-label="Status harga komponen" value={f.rate_status ?? 'KNOWN'} disabled={locked} onChange={e => set({ rate_status: e.target.value })}>{BD_RATE_STATUSES.map(s => <option key={s} value={s}>{BD_RATE_LABEL[s]}</option>)}</select></label>
      {(f.rate_status ?? 'KNOWN') === 'KNOWN' && field('component_rate', 'Harga per PCS')}
      <button type="button" disabled={!can || !f.component_id || !from || ((f.rate_status ?? 'KNOWN') === 'KNOWN' && !moneyInput(f.component_rate ?? ''))} onClick={() => from &&
        send('SAVE_COMPONENT_RATE', { component_id: f.component_id, rate_status: f.rate_status ?? 'KNOWN', effective_from: from, reason: reason.trim(),
          ...((f.rate_status ?? 'KNOWN') === 'KNOWN' ? { rate_per_pcs: normalizeMoney(f.component_rate) } : f.rate_status === 'UNKNOWN' ? {} : { rate_per_pcs: '0.00' }) })}>Simpan versi harga komponen</button></div>
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
  const [selection, setSelection] = useState('PENDING')
  const mode = selection === 'VENDOR' ? v.pricing_mode : selection
  const unit = selection === 'VENDOR' ? v.pricing_unit : 'PCS'
  const [batchId, setBatchId] = useState(''), [process, setProcess] = useState(''), [color, setColor] = useState(''), [at, setAt] = useState('')
  const [reason, setReason] = useState(''), [qty, setQty] = useState<Record<string, string>>({}), [packageId, setPackageId] = useState(''), [lump, setLump] = useState('')
  const [covered, setCovered] = useState<Record<string, string>>({}), [extraReasons, setExtraReasons] = useState<Record<string, string>>({}), [confirmed, setConfirmed] = useState(false)
  const [scopes, setScopes] = useState<Record<string, 'NONE' | 'ALL' | 'PARTIAL'>>({})
  const chooseScope = (id: string, scope: 'NONE' | 'ALL' | 'PARTIAL') => {
    setScopes(x => ({ ...x, [id]: scope }))
    if (scope !== 'PARTIAL') setCovered(x => Object.fromEntries(Object.entries(x).filter(([key]) => !key.startsWith(`${id}:`))))
    if (scope === 'NONE') setExtraReasons(x => ({ ...x, [id]: '' }))
    setConfirmed(false)
  }
  const batch = laundry.ready_batches.find(b => b.distribution_batch_id === batchId)
  const lines = batch?.sizes.map(s => ({ size_id: s.size_id, qty_sent_pcs: wholePcs(qty[s.size_id] ?? '') ? Number(qty[s.size_id]) : 0 })).filter(l => l.qty_sent_pcs > 0) ?? []
  const physical = wibTimestamp(at)
  const components = data.components.filter(c => c.vendor_id === vendor && c.is_active)
  const selectedPackage = data.packages.find(p => p.id === packageId && p.vendor_id === vendor && p.is_active)
  const availableComponents = mode === 'PACKAGE' ? components.filter(c => !selectedPackage?.component_ids.includes(c.id)) : components
  const [historyNotice, setHistoryNotice] = useState('')
  const useHistory = (item: LaundryHistoryItem) => {
    if (item.charges.every(c => c.kind === 'PROCESS_REFERENCE')) {
      if (!laundry.lookups.wash_processes.some(p => p.id === item.process_id)) { setHistoryNotice('Jenis cucian lama sudah tidak aktif.'); return }
      setProcess(item.process_id); setSelection('PENDING'); setScopes({}); setCovered({}); setExtraReasons({}); setConfirmed(false)
      setHistoryNotice('Jenis cucian disalin. Riwayat ini tidak punya rincian komponen; pilih dari master vendor atau tunggu kontra bon.'); return
    }
    const packageCharge = item.charges.find(c => c.kind === 'PACKAGE')
    const chosenComponents = item.charges.filter(c => ['COMPONENT', 'EXTRA'].includes(c.kind))
    const entireBatch = batch?.sizes.every(s => item.target_size_ids.includes(s.size_id))
    if (packageCharge && (!entireBatch || !data.packages.some(p => p.id === packageCharge.ref_id && p.vendor_id === vendor && p.is_active))) {
      setHistoryNotice('Paket sebelumnya tidak cocok untuk seluruh batch ini. Pilih kombinasi dan penerimanya secara manual.'); return
    }
    if (chosenComponents.some(c => !components.some(x => x.id === c.ref_id))) {
      setHistoryNotice('Ada komponen lama yang sudah tidak aktif. Pilih komponen vendor yang masih berlaku.'); return
    }
    if (!packageCharge && !chosenComponents.length && (v.pricing_mode !== 'RATE' || !entireBatch)) {
      setHistoryNotice('Pengaturan tarif proses atau penerimanya sudah berbeda. Pilih rincian vendor yang sesuai secara manual.'); return
    }
    if (!laundry.lookups.wash_processes.some(p => p.id === item.process_id)) {
      setHistoryNotice('Jenis cucian lama sudah tidak aktif. Pilih jenis cucian yang masih berlaku.'); return
    }
    setSelection(packageCharge ? 'PACKAGE' : chosenComponents.length ? 'COMPONENTS' : 'VENDOR')
    setProcess(item.process_id); setPackageId(packageCharge?.ref_id ?? '')
    setScopes(Object.fromEntries(chosenComponents.map(c => [c.ref_id!, entireBatch ? 'ALL' : 'PARTIAL'])))
    setCovered(Object.fromEntries(chosenComponents.flatMap(c => lines.filter(l => item.target_size_ids.includes(l.size_id)).map(l => [`${c.ref_id}:${l.size_id}`, String(l.qty_sent_pcs)]))))
    setExtraReasons({}); setConfirmed(false)
    setHistoryNotice('Pilihan jasa disalin. Periksa penerima jasa dan alasan tambahan paket; harga lama tidak disalin.')
  }
  let coverageValid = true
  const componentPayload = availableComponents.flatMap(c => {
    const scope = scopes[c.id] ?? 'NONE'
    if (scope === 'NONE') return []
    const coverage = scope === 'ALL' ? lines.map(l => ({ size_id: l.size_id, qty: l.qty_sent_pcs })) : (batch?.sizes ?? []).flatMap(s => {
      const value = covered[`${c.id}:${s.size_id}`]?.trim() ?? ''
      if (!value || value === '0') return []
      if (!wholePcs(value) || Number(value) > (lines.find(l => l.size_id === s.size_id)?.qty_sent_pcs ?? 0)) { coverageValid = false; return [] }
      return [{ size_id: s.size_id, qty: Number(value) }]
    })
    if (!coverage.length) { coverageValid = false; return [] }
    const extraReason = extraReasons[c.id]?.trim() ?? ''
    if (mode === 'PACKAGE' && !extraReason) coverageValid = false
    return [{ component_id: c.id, covered_qty: coverage.reduce((n, s) => n + s.qty, 0), coverage,
      ...(mode === 'PACKAGE' ? { reason: extraReason } : {}) }]
  })
  const pricing: Record<string, Json> | null = mode === 'PENDING' ? { deferred: true } : unit === 'BATCH' ? (moneyInput(lump) ? { lump_sum: normalizeMoney(lump) } : null)
    : mode === 'PACKAGE' ? (selectedPackage && coverageValid ? { package_id: packageId, extras: componentPayload } : null)
    : mode === 'COMPONENTS' ? (coverageValid ? { components: componentPayload } : null) : {}
  const valid = batch && process && color.trim() && physical && reason.trim().length >= 4 && lines.length && pricing && confirmed
    && batch.sizes.every(s => !(qty[s.size_id] ?? '').trim() || qty[s.size_id].trim() === '0' || (wholePcs(qty[s.size_id]) && Number(qty[s.size_id]) <= s.available_qty_pcs))
  return <section className="initial-import-table" aria-label="Kirim laundry dengan harga BD">
    {batch && <LaundrySkuHistory key={`${vendor}:${batch.cutting_group_id}:${physical}`} vendor={vendor} wave={batch.cutting_group_id} at={physical} locked={locked} onSelect={useHistory}/>}
    {historyNotice && <p role="status">{historyNotice}</p>}
    <p>Tarif mengikuti master {v.code}. Pilih kombinasi yang dikenal atau centang komponen. Rincian boleh kosong sampai kontra bon; biaya tetap belum diketahui.</p>
    <label>Rincian biaya<select aria-label="Pilihan rincian biaya" value={selection} disabled={locked} onChange={e => { setSelection(e.target.value); setScopes({}); setCovered({}); setExtraReasons({}); setConfirmed(false) }}>
      <option value="PENDING">Kosongkan — tunggu kontra bon</option><option value="PACKAGE">Kombinasi / paket cucian</option><option value="COMPONENTS">Centang komponen cucian</option><option value="VENDOR">Tarif proses / satuan vendor</option>
    </select></label>
    {(mode === 'PENDING' || (mode === 'COMPONENTS' && componentPayload.length === 0)) && <p role="status">Biaya belum diketahui. Isi nilai aktual saat kontra bon diterima.</p>}
    <div className="initial-import-toolbar">
      <label>Batch<select aria-label="Batch kirim berharga" value={batchId} disabled={locked} onChange={e => { setBatchId(e.target.value); setQty({}); setCovered({}); setScopes({}); setExtraReasons({}); setConfirmed(false) }}>
        <option value="">Pilih batch…</option>{laundry.ready_batches.map(b => <option key={b.distribution_batch_id} value={b.distribution_batch_id}>{b.po_number} · {b.group_number} · Batch {b.batch_no} · siap {b.group_unsent_ready_qty_pcs} pcs</option>)}</select></label>
      <label>Proses<select aria-label="Proses kirim berharga" value={process} disabled={locked} onChange={e => { setProcess(e.target.value); setConfirmed(false) }}>
        <option value="">Pilih…</option>{laundry.lookups.wash_processes.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>
      <label>Warna<input aria-label="Warna kirim berharga" value={color} disabled={locked} onChange={e => { setColor(e.target.value); setConfirmed(false) }}/></label>
      <label>Waktu keluar (WIB)<input aria-label="Waktu kirim berharga" type="datetime-local" value={at} disabled={locked} onChange={e => { setAt(e.target.value); setConfirmed(false) }}/></label>
      <Reason value={reason} set={v => { setReason(v); setConfirmed(false) }} locked={locked} label="Bukti serah terima"/></div>
    {batch && <div className="initial-import-toolbar">{batch.sizes.map(s => <label key={s.size_id}>Ukuran {s.size_code} (bisa {s.available_qty_pcs})<input aria-label={`Qty kirim berharga ${s.size_code}`}
      inputMode="numeric" value={qty[s.size_id] ?? ''} disabled={locked} onChange={e => { setQty(x => ({ ...x, [s.size_id]: e.target.value })); setConfirmed(false) }}/></label>)}</div>}
    <div className="initial-import-toolbar">
      {unit === 'BATCH' && <label>Harga borongan batch<input aria-label="Harga borongan" value={lump} disabled={locked} onChange={e => { setLump(e.target.value); setConfirmed(false) }}/></label>}
      {unit === 'PCS' && mode === 'PACKAGE' && <label>Paket<select aria-label="Paket kirim berharga" value={packageId} disabled={locked} onChange={e => { setPackageId(e.target.value); setCovered({}); setScopes({}); setExtraReasons({}); setConfirmed(false) }}>
        <option value="">Pilih…</option>{data.packages.filter(p => p.vendor_id === vendor && p.is_active).map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>}
      {unit === 'PCS' && (mode === 'COMPONENTS' || (mode === 'PACKAGE' && selectedPackage)) && <fieldset>
        <legend>{mode === 'PACKAGE' ? 'Jasa tambahan di luar isi paket' : 'Jasa untuk kiriman ini'}</legend>
        <p>Centang jasa untuk seluruh PCS yang dikirim. Pilih sebagian ukuran/jumlah bila hanya sebagian barang menerima jasa itu.</p>
        {mode === 'PACKAGE' && <p>Sudah termasuk paket: {components.filter(c => selectedPackage?.component_ids.includes(c.id)).map(c => c.code).join(', ')}.</p>}
        {availableComponents.map(c => <div key={c.id} className="initial-import-toolbar">
          <label><input type="checkbox" aria-label={`Jasa ${c.code}`} checked={Boolean(scopes[c.id] && scopes[c.id] !== 'NONE')} disabled={locked || !batch}
            onChange={e => chooseScope(c.id, e.target.checked ? 'ALL' : 'NONE')}/>{c.code} · {c.name} · {c.current ? BD_RATE_LABEL[c.current.status] : 'Belum ada harga'}</label>
          {scopes[c.id] && scopes[c.id] !== 'NONE' && <>
          <label>Penerima jasa<select aria-label={`Penerima jasa ${c.code}`} value={scopes[c.id]} disabled={locked}
            onChange={e => chooseScope(c.id, e.target.value as 'ALL' | 'PARTIAL')}>
            <option value="ALL">Seluruh kiriman</option><option value="PARTIAL">Sebagian ukuran/jumlah</option></select></label>
          {scopes[c.id] === 'ALL' ? <span role="status">{c.code}: {lines.reduce((n, l) => n + l.qty_sent_pcs, 0)} PCS · seluruh kiriman</span>
            : <><p>Isi PCS penerima jasa per ukuran. Kosong atau 0 berarti tidak menerima jasa.</p>{(batch?.sizes ?? []).map(s => <label key={s.size_id}>{c.code} · {s.size_code}<input aria-label={`Cakupan ${c.code} ${s.size_code}`} inputMode="numeric"
            value={covered[`${c.id}:${s.size_id}`] ?? ''} disabled={locked} onChange={e => { setCovered(x => ({ ...x, [`${c.id}:${s.size_id}`]: e.target.value })); setConfirmed(false) }}/></label>)}
          </>}
          {mode === 'PACKAGE' && <Reason label={`Alasan tambahan ${c.code}`} value={extraReasons[c.id] ?? ''} locked={locked}
            set={value => { setExtraReasons(x => ({ ...x, [c.id]: value })); setConfirmed(false) }}/>}</>}
        </div>)}
        {!coverageValid && <p role="alert">Jasa yang dipilih harus memiliki penerima: PCS utuh, tidak melebihi kiriman pada ukuran itu. Tambahan paket wajib disertai alasan.</p>}
      </fieldset>}
    </div>
    <label><input type="checkbox" checked={confirmed} disabled={locked} onChange={e => setConfirmed(e.target.checked)}/>Vendor, batch, ukuran, jumlah, warna, waktu, dan pilihan rincian biaya sudah dicocokkan dengan serah-terima.</label>
    <button type="button" disabled={locked || !valid} onClick={() => batch && physical && pricing && send('POST_PRICED_DELIVERY', {
      expected_version: String(batch.cutting_group_row_version), pricing,
      delivery: { distribution_batch_id: batch.distribution_batch_id, vendor_id: vendor, wash_process_id: process, target_dyeing_color: color.trim(),
        physical_at: physical, reason: reason.trim(), notes: null, lines } })}>Catat kiriman berharga</button>
  </section>
}

const METHOD_LABEL = { CASH: 'Kas', CLAIM_CREDIT: 'Kredit klaim', CORRECTION_CREDIT: 'Kredit koreksi', CREDIT: 'Kredit/potongan' } as const
const creditName = (c: BdPayables['credits'][number]) => `${c.number}${c.kind === 'OPENING_CLAIM' ? ' (saldo awal)' : c.kind === 'INVOICE_CORRECTION' ? ` (koreksi turun atas ${c.corrects})` : ''}`
const cents = (v: string) => Math.round(Number(v) * 100)

/** D12: pay a vendor document in cash or with a claim credit of the same vendor (older documents included). */
function Payables({ payables, locked, send }: { payables: BdPayables; locked: boolean; send: Send }) {
  const open = payables.documents.filter(d => cents(d.remaining) > 0), usable = payables.credits.filter(c => cents(c.available) > 0)
  const [docId, setDocId] = useState(''), [date, setDate] = useState(today()), [reason, setReason] = useState('')
  const [creditId, setCreditId] = useState(''), [creditAmount, setCreditAmount] = useState(''), [cash, setCash] = useState(''), [cashAmount, setCashAmount] = useState('')
  const [undoReason, setUndoReason] = useState('')
  const doc = open.find(d => d.id === docId), credit = usable.find(c => c.id === creditId)
  const base = !locked && Boolean(doc) && /^\d{4}-\d{2}-\d{2}$/.test(date) && reason.trim().length >= 4
  const l = payables.ledger
  return <section className="initial-import-table" aria-label="Pembayaran vendor laundry">
    <p>Kredit klaim yang sudah disetujui boleh memotong tagihan vendor yang sama yang belum lunas, termasuk tagihan yang lebih tua dari kejadian reject. Utang vendor turun pada tanggal klaim disetujui; tagihan yang dipotong mencatat pelunasannya pada tanggal pemakaian kredit, jadi histori bulan tagihan tidak berubah. Kredit dari dokumen koreksi turun invoice lebih dulu melunasi sisa invoice asalnya; sisanya dipakai dengan cara yang sama.</p>
    <dl aria-label="Cocokkan saldo utang vendor">
      <div><dt>Saldo utang (buku besar)</dt><dd>{rupiah(l.ap_balance)}</dd></div>
      <div><dt>Sisa tagihan</dt><dd>{rupiah(l.documents_remaining)}</dd></div>
      <div><dt>Kredit klaim/koreksi belum dipakai</dt><dd>{rupiah(l.credit_available)}</dd></div>
      <div><dt>Pencocokan</dt><dd role="status">{l.matches ? 'Cocok: saldo utang = sisa tagihan − kredit belum dipakai' : 'Tidak cocok: periksa pelunasan dan klaim vendor ini'}</dd></div>
    </dl>
    <table aria-label="Tagihan vendor"><thead><tr><th>Tagihan</th><th>Tanggal</th><th>Total</th><th>Dibayar kas</th><th>Kredit klaim</th><th>Kredit koreksi</th><th>Sisa</th><th>Status</th></tr></thead>
      <tbody>{payables.documents.map(d => <tr key={d.id}><td>{d.number}{d.kind === 'OPENING_PAYABLE' ? ' (saldo awal)' : ''}{d.corrects ? ` (koreksi naik atas ${d.corrects})` : ''}</td><td>{d.date}</td><td>{rupiah(d.total)}</td>
        <td>{rupiah(d.paid_cash)}</td><td>{rupiah(d.claim_credit)}</td><td>{rupiah(d.correction_credit)}</td><td>{rupiah(d.remaining)}</td><td>{cents(d.remaining) === 0 ? 'Lunas' : d.status}</td></tr>)}</tbody></table>
    <table aria-label="Kredit klaim vendor"><thead><tr><th>Klaim / koreksi</th><th>Berlaku sejak</th><th>Kredit</th><th>Terpakai</th><th>Tersedia</th></tr></thead>
      <tbody>{payables.credits.map(c => <tr key={c.id}><td>{creditName(c)}</td><td>{c.approved_date}</td><td>{rupiah(c.amount)}</td>
        <td>{rupiah(c.applied)}</td><td>{rupiah(c.available)}</td></tr>)}</tbody></table>
    <div className="initial-import-toolbar">
      <label>Tagihan dilunasi<select aria-label="Tagihan dilunasi" value={docId} disabled={locked} onChange={e => setDocId(e.target.value)}>
        <option value="">Pilih tagihan…</option>{open.map(d => <option key={d.id} value={d.id}>{d.number} · sisa {rupiah(d.remaining)}</option>)}</select></label>
      <label>Tanggal pelunasan<input aria-label="Tanggal pelunasan" type="date" value={date} disabled={locked} onChange={e => setDate(e.target.value)}/></label>
      <Reason value={reason} set={setReason} locked={locked} label="Alasan pelunasan"/></div>
    <div className="initial-import-toolbar">
      <label>Kredit klaim<select aria-label="Kredit klaim dipakai" value={creditId} disabled={locked} onChange={e => setCreditId(e.target.value)}>
        <option value="">Pilih klaim/koreksi…</option>{usable.map(c => <option key={c.id} value={c.id}>{creditName(c)} · tersedia {rupiah(c.available)}</option>)}</select></label>
      <label>Nominal kredit<input aria-label="Nominal kredit klaim" value={creditAmount} disabled={locked} onChange={e => setCreditAmount(e.target.value)}/></label>
      <button type="button" disabled={!base || !credit || !moneyInput(creditAmount)} onClick={() => doc && credit && send('APPLY_CLAIM_CREDIT', {
        source_kind: credit.kind, source_id: credit.id, target_kind: doc.kind, target_id: doc.id, amount: normalizeMoney(creditAmount), date, reason: reason.trim() })}>Pakai kredit klaim</button></div>
    <div className="initial-import-toolbar">
      <label>Rekening kas<select aria-label="Rekening kas pembayaran" value={cash} disabled={locked} onChange={e => setCash(e.target.value)}>
        <option value="">Pilih rekening…</option>{payables.cash_accounts.map(a => <option key={a.id} value={a.id}>{a.code} · {a.name}</option>)}</select></label>
      <label>Nominal kas<input aria-label="Nominal bayar kas" value={cashAmount} disabled={locked} onChange={e => setCashAmount(e.target.value)}/></label>
      <button type="button" disabled={!base || !cash || !moneyInput(cashAmount)} onClick={() => doc && send('PAY_VENDOR_DOCUMENT', {
        target_kind: doc.kind, target_id: doc.id, amount: normalizeMoney(cashAmount), date, cash_account_id: cash, reason: reason.trim() })}>Bayar kas</button></div>
    <h4>Riwayat pelunasan</h4>
    <Reason value={undoReason} set={setUndoReason} locked={locked} label="Alasan pembatalan"/>
    <table aria-label="Riwayat pelunasan vendor"><thead><tr><th>Tagihan</th><th>Tanggal</th><th>Cara</th><th>Nominal</th><th>Rujukan</th><th>Status</th><th></th></tr></thead>
      <tbody>{payables.documents.flatMap(d => d.settlements.map(x => <tr key={x.id}><td>{d.number}</td><td>{x.date}</td><td>{METHOD_LABEL[x.method]}</td><td>{rupiah(x.amount)}</td>
        <td>{x.reference ?? '—'}</td><td>{x.status === 'POSTED' ? 'Diposting' : 'Dibatalkan'}</td>
        <td>{x.status === 'POSTED' && x.method !== 'CREDIT' && <button type="button" disabled={locked || undoReason.trim().length < 4} onClick={() => send('REVERSE_VENDOR_SETTLEMENT', {
          target_kind: d.kind, settlement_id: x.id, reason: undoReason.trim() })}>Batalkan {x.number}</button>}</td></tr>))}</tbody></table>
  </section>
}

function UnknownPrices({ data, locked, send }: { data: LaundryBdWorkspace; locked: boolean; send: Send }) {
  const [rate, setRate] = useState<Record<string, string>>({}), [reason, setReason] = useState('')
  const [resolution, setResolution] = useState<Record<string, string>>({})
  const pending = data.priced_deliveries.filter(d => !d.total_complete && !d.cost_invoiced && d.status !== 'REVERSED')
  return <section className="initial-import-table" aria-label="Harga laundry belum diketahui">
    <p>Selama harga komponen belum diketahui, biaya laundry kiriman ini baru bagian yang diketahui, HPP tetap estimasi, dan tutup buku tertahan (LAU-T12).</p>
    {pending.filter(d => d.charges.length === 0).map(d => <p key={d.delivery_line_id}>{d.delivery_number} · {d.qty_sent} PCS · biaya belum diketahui. Catat nilai aktual pada Invoice vendor setelah barang diterima.</p>)}
    {pending.some(d => d.has_invoice) && <p>Sebagian biaya sudah ditagih. Lengkapi kontra bon; perubahan biaya tertagih memakai dokumen koreksi.</p>}
    <Reason value={reason} set={setReason} locked={locked}/>
    {pending.length === 0 ? <p>Tidak ada harga laundry yang belum diketahui.</p> : <table><thead><tr><th>Kiriman</th><th>Rincian</th><th>PCS</th><th>Harga diketahui</th><th>Isi harga</th></tr></thead>
      <tbody>{pending.flatMap(d => d.charges.map(c => <tr key={c.id}><td>{d.delivery_number} · {d.physical_local}</td><td>{CHARGE_KIND_LABEL[c.kind]} · {c.label}</td><td>{c.covered_qty}</td>
        <td>{c.rate_status === 'KNOWN' ? rupiah(c.amount) : BD_RATE_LABEL[c.rate_status]}{c.price_reason ? ` · ${c.price_reason}` : ''}</td>
        <td>{c.rate_status === 'UNKNOWN' && !d.has_invoice && data.can_set_price && <><select aria-label={`Status harga ${c.label}`} disabled={locked} value={resolution[c.id] ?? 'KNOWN'}
          onChange={e => setResolution(x => ({ ...x, [c.id]: e.target.value }))}>{BD_RATE_STATUSES.filter(s => s !== 'UNKNOWN').map(s => <option key={s} value={s}>{BD_RATE_LABEL[s]}</option>)}</select>
          {(resolution[c.id] ?? 'KNOWN') === 'KNOWN' && <input aria-label={`Harga per PCS ${c.label}`} value={rate[c.id] ?? ''} disabled={locked} onChange={e => setRate(x => ({ ...x, [c.id]: e.target.value }))}/>}
          <button type="button" disabled={locked || ((resolution[c.id] ?? 'KNOWN') === 'KNOWN' && !moneyInput(rate[c.id] ?? '')) || !reason.trim()} onClick={() => send('SET_CHARGE_PRICE', { charge_line_id: c.id,
            rate_status: resolution[c.id] ?? 'KNOWN', rate_per_pcs: (resolution[c.id] ?? 'KNOWN') === 'KNOWN' ? normalizeMoney(rate[c.id]) : '0.00', reason: reason.trim() })}>Isi harga {c.label}</button></>}</td></tr>))}</tbody></table>}
    <PendingCost data={data}/>
  </section>
}

// Owner decision no. 11 (LAU-DEC04 ALLOW_PENDING): goods may be sold before their laundry price is known, but their HPP is shown as
// not final (never as zero or final) until the price is set; the sales made meanwhile stay listed, marked recosted afterwards.
function PendingCost({ data }: { data: LaundryBdWorkspace }) {
  const { goods, sales } = data.pending_cost
  return <section aria-label="HPP belum final">
    <h4>HPP belum final karena harga laundry belum diketahui</h4>
    <p>HPP barang ini baru memuat bagian harga yang sudah diketahui. Setelah harga diisi, HPP lot, stok, dan HPP penjualan yang sudah terjadi dihitung ulang, lalu tutup buku tidak lagi tertahan.</p>
    {goods.length === 0 ? <p>Tidak ada barang jadi dengan HPP belum final.</p> : <table aria-label="Barang jadi HPP belum final"><thead><tr><th>Barang</th><th>Lot</th><th>PO</th><th>Stok</th><th>Terjual</th><th>HPP per PCS sejauh ini</th><th>Status</th></tr></thead>
      <tbody>{goods.map(g => <tr key={g.lot_id}><td>{g.sku} · {g.product_name}</td><td>{g.lot_number}</td><td>{g.po_number}</td><td>{g.qty_now}</td><td>{g.qty_sold}</td>
        <td>{rupiah(g.hpp_per_pcs_so_far)}</td><td>HPP belum final</td></tr>)}</tbody></table>}
    {sales.length > 0 && <table aria-label="Penjualan saat harga laundry belum diketahui"><thead><tr><th>Penjualan</th><th>Tanggal</th><th>Barang</th><th>PCS</th><th>HPP saat dijual</th><th>Status HPP</th></tr></thead>
      <tbody>{sales.map(x => <tr key={x.id}><td>{x.sale_number}</td><td>{x.sale_date}</td><td>{x.sku} · {x.product_name}</td><td>{x.qty}</td><td>{rupiah(x.unit_hpp_at_sale)}</td>
        <td>{x.hpp_state === 'NOT_FINAL' ? 'HPP belum final' : 'Sudah dihitung ulang dengan harga laundry'}</td></tr>)}</tbody></table>}
  </section>
}

type DraftLine = { key: string; kind: 'BILL' | 'CORRECTION'; source: string; category: Category; qty: string; amount: string }
function Invoices({ data, vendor, locked, send, loadMore, canSetRedye }: { data: LaundryBdWorkspace; vendor: string; locked: boolean; send: Send; loadMore: (kind: BdPageKind) => void; canSetRedye: boolean }) {
  const [redyeRates, setRedyeRates] = useState<Record<string, string>>({})
  const [invoiceSearch, setInvoiceSearch] = useState(''), [receiptSearch, setReceiptSearch] = useState('')
  const redye = data.redye_services ?? []
  const [editing, setEditing] = useState<BdInvoice | null>(null)
  const [head, setHead] = useState<Record<string, string>>({ number: '', date: today(), due: '', total: '', discount: '', tax: '', rounding: '', corrects: '' })
  const [lines, setLines] = useState<DraftLine[]>([]), [reason, setReason] = useState('')
  const invoices = data.invoices ?? [], billable = data.billable_receipts ?? [], opening = data.opening_uninvoiced.filter(u => u.vendor_id === vendor && !u.invoiced)
  const visibleInvoices = invoices.filter(i => `${i.invoice_number} ${i.vendor_code}`.toLocaleLowerCase().includes(invoiceSearch.trim().toLocaleLowerCase()))
  const visibleReceipts = billable.filter(b => `${b.receipt_number} ${b.delivery_number} ${b.po_number}`.toLocaleLowerCase().includes(receiptSearch.trim().toLocaleLowerCase()))
  const sourceLabel = (s: string) => s.startsWith('d:') ? (redye.find(x => x.id === s.slice(2))?.number ?? 'Jasa celup') : s.startsWith('r:') ? (() => { const b = billable.find(x => x.receipt_line_id === s.slice(2)); return b ? `${b.receipt_number} · ${b.po_number}` : s })()
    : (() => { const u = data.opening_uninvoiced.find(x => x.id === s.slice(2)); return u ? `Saldo awal ${u.document_number} · ${CATEGORY_LABEL[u.category]}` : s })()
  const setLine = (i: number, patch: Partial<DraftLine>) => setLines(ls => ls.map((l, j) => j === i ? { ...l, ...patch } : l))
  // Owner decision no. 13: a correction is its own document linked to the posted invoice it corrects; its total is signed.
  const origins = invoices.filter(i => i.status === 'POSTED' && i.document_kind === 'INVOICE' && i.vendor_id === vendor)
  const correcting = Boolean(head.corrects)
  // A correction corrects only what its origin billed: its sources are the origin's billing lines (already fully billed ones included).
  const origin = invoices.find(i => i.invoice_id === head.corrects) ?? null
  const originSources = (origin?.lines ?? []).filter(l => l.line_kind === 'BILL').map(l => ({ value: l.receipt_line_id ? 'r:' + l.receipt_line_id : l.rework_service_id ? 'd:' + l.rework_service_id : 'o:' + l.opening_uninvoiced_id,
    category: l.category, label: `Baris ${l.line_no} ${origin?.invoice_number} · ${CATEGORY_LABEL[l.category]} · ${l.qty} PCS` }))
  const signed = (v: string) => (v.trim().startsWith('-') ? '-' : '') + normalizeMoney(v.trim().replace('-', ''))
  const edit = (i: BdInvoice | null) => {
    setEditing(i)
    setHead(i ? { number: i.invoice_number, date: i.invoice_date, due: i.due_date ?? '', total: i.header_total, discount: i.discount_amount === '0.00' ? '' : i.discount_amount,
      tax: i.tax_amount === '0.00' ? '' : i.tax_amount, rounding: i.rounding_amount === '0.00' ? '' : i.rounding_amount, corrects: i.corrects_invoice_id ?? '' }
      : { number: '', date: today(), due: '', total: '', discount: '', tax: '', rounding: '', corrects: '' })
    setLines(i ? i.lines.map(l => ({ key: l.id, kind: l.line_kind, source: l.receipt_line_id ? 'r:' + l.receipt_line_id : l.rework_service_id ? 'd:' + l.rework_service_id : 'o:' + l.opening_uninvoiced_id, category: l.category,
      qty: String(l.qty), amount: l.amount })) : [])
  }
  const lineOk = (l: DraftLine) => l.source && (l.kind === 'BILL' ? wholePcs(l.qty) && moneyInput(l.amount) : signedMoneyInput(l.amount) && !/^-?0+([.,]0+)?$/.test(l.amount.trim()))
  const valid = vendor && head.number.trim() && /^\d{4}-\d{2}-\d{2}$/.test(head.date) && lines.length > 0 && lines.every(lineOk) && (correcting
    ? signedMoneyInput(head.total) && !/^-?0+([.,]0+)?$/.test(head.total.trim()) && lines.every(l => l.kind === 'CORRECTION') && !head.discount && !head.tax && !head.rounding
    : moneyInput(head.total) && lines.every(l => l.kind === 'BILL')
      && (!head.discount || moneyInput(head.discount)) && (!head.tax || moneyInput(head.tax)) && (!head.rounding || signedMoneyInput(head.rounding)))
  const payload = (): Record<string, Json> => ({ ...(editing ? { invoice_id: editing.invoice_id, expected_version: editing.row_version } : {}), vendor_id: vendor,
    invoice_number: head.number.trim(), invoice_date: head.date, due_date: head.due || null, header_total: correcting ? signed(head.total) : normalizeMoney(head.total),
    ...(correcting ? { corrects_invoice_id: head.corrects } : {}),
    ...(head.discount ? { discount_amount: normalizeMoney(head.discount) } : {}), ...(head.tax ? { tax_amount: normalizeMoney(head.tax) } : {}),
    ...(head.rounding ? { rounding_amount: (head.rounding.trim().startsWith('-') ? '-' : '') + normalizeMoney(head.rounding.trim().replace('-', '')) } : {}),
    lines: lines.map(l => ({ line_kind: l.kind, category: l.category, qty: l.kind === 'BILL' ? Number(l.qty) : 0,
      amount: signed(l.amount),
      ...(l.source.startsWith('r:') ? { receipt_line_id: l.source.slice(2) } : l.source.startsWith('d:') ? { rework_service_id: l.source.slice(2) } : { opening_uninvoiced_id: l.source.slice(2) }) })) })
  return <section className="initial-import-table" aria-label="Invoice vendor laundry">
    {redye.length > 0 && <section aria-label="Jasa celup ulang"><h3>Jasa celup ulang</h3><p>Tarif diikat pada waktu kirim. Invoice mengganti estimasi; selisih mengikuti biaya produk.</p><table><thead><tr><th>Order / proses</th><th>Hasil</th><th>Tarif per PCS</th><th>Biaya kini</th></tr></thead><tbody>{redye.map(x => <tr key={x.id}><td>{x.number} · {x.process}<br/>{x.status}</td><td>{x.good} GOOD · {x.bs} BS</td><td>{x.price_known ? rupiah(x.rate) : 'Belum diketahui'}{!x.price_known && canSetRedye && x.status !== 'CANCELLED' && <><input aria-label={`Tarif celup ${x.number}`} value={redyeRates[x.id] ?? ''} disabled={locked} onChange={e => setRedyeRates(v => ({ ...v, [x.id]: e.target.value }))}/><button type="button" disabled={locked || !moneyInput(redyeRates[x.id] ?? '') || !reason.trim()} onClick={() => send('SET_REDYE_PRICE', { service_id: x.id, rate: normalizeMoney(redyeRates[x.id]), reason: reason.trim() })}>Isi tarif celup {x.number}</button></>}</td><td>{x.price_known ? rupiah(x.cost) : 'HPP belum final'}</td></tr>)}</tbody></table><p>Pengisian tarif memakai alasan pada formulir di bawah.</p></section>}

    <div className="initial-import-toolbar"><label>Cari invoice yang dimuat<input aria-label="Cari invoice yang dimuat" value={invoiceSearch} onChange={e => setInvoiceSearch(e.target.value)}/></label>
      <span>{invoices.length} invoice dimuat</span>{data.pagination.invoice_next && <button type="button" disabled={locked} onClick={() => loadMore('invoices')}>Muat invoice berikutnya</button>}</div>
    <table><thead><tr><th>Invoice</th><th>Vendor</th><th>Tanggal</th><th>Total</th><th>Dibayar</th><th>Status</th><th/></tr></thead><tbody>{visibleInvoices.map(i => <tr key={i.invoice_id}>
      <td>{i.invoice_number}{i.document_kind !== 'INVOICE' ? ` · koreksi ${i.document_kind === 'CORRECTION_UP' ? 'naik' : 'turun'} atas ${i.corrects_invoice_number}` : ''}</td><td>{i.vendor_code}</td><td>{i.invoice_date}</td><td>{rupiah(i.header_total)}</td><td>{rupiah(i.paid)}</td><td>{i.status}{i.variance_mode ? ` · selisih ${i.variance_mode === 'PRODUCT_COST' ? 'ke biaya produk' : 'ke akun selisih'}` : ''}</td>
      <td>{i.status === 'DRAFT' && <><button type="button" disabled={locked} onClick={() => edit(i)}>Ubah draf {i.invoice_number}</button>
        <button type="button" disabled={locked} onClick={() => send('POST_INVOICE', { invoice_id: i.invoice_id, expected_version: i.row_version })}>Posting {i.invoice_number}</button>
        <button type="button" disabled={locked} onClick={() => send('CANCEL_INVOICE_DRAFT', { invoice_id: i.invoice_id, expected_version: i.row_version })}>Batalkan draf {i.invoice_number}</button></>}
        {i.status === 'POSTED' && <button type="button" disabled={locked || !reason.trim() || i.paid !== '0.00'} onClick={() => send('REVERSE_INVOICE', { invoice_id: i.invoice_id,
          expected_version: i.row_version, reason: reason.trim() })}>Batalkan invoice {i.invoice_number}</button>}</td></tr>)}</tbody></table>
    <Reason value={reason} set={setReason} locked={locked} label="Alasan pembatalan invoice"/>
    {!vendor ? <p>Pilih vendor untuk membuat draf invoice.</p> : <>
      <h4>{editing ? `Ubah draf ${editing.invoice_number}` : 'Draf invoice baru'}</h4>
      <div className="initial-import-toolbar"><label>Cari penerimaan yang dimuat<input aria-label="Cari penerimaan yang dimuat" value={receiptSearch} onChange={e => setReceiptSearch(e.target.value)}/></label>
        <span>{billable.length} penerimaan dimuat</span>{data.pagination.receipt_next && <button type="button" disabled={locked} onClick={() => loadMore('receipts')}>Muat penerimaan berikutnya</button>}</div>
      <div className="initial-import-toolbar">
        {([['number', 'Nomor invoice vendor'], ['date', 'Tanggal invoice'], ['due', 'Jatuh tempo'], ['total', 'Total invoice'], ['discount', 'Diskon'], ['tax', 'Pajak masukan'],
          ['rounding', 'Pembulatan']] as const).map(([k, label]) => <label key={k}>{label}<input aria-label={label} type={k === 'date' || k === 'due' ? 'date' : 'text'} value={head[k]}
            disabled={locked} onChange={e => setHead(h => ({ ...h, [k]: e.target.value }))}/></label>)}
        <label>Koreksi atas invoice<select aria-label="Koreksi atas invoice" value={head.corrects} disabled={locked}
          onChange={e => { const v = e.target.value; setHead(h => ({ ...h, corrects: v })); setLines(ls => ls.map(l => ({ ...l, kind: v ? 'CORRECTION' : 'BILL' }))) }}>
          <option value="">Bukan koreksi (invoice biasa)</option>{origins.map(i => <option key={i.invoice_id} value={i.invoice_id}>{i.invoice_number} · {i.invoice_date} · {rupiah(i.header_total)}</option>)}</select></label></div>
      {lines.map((l, i) => <div key={l.key} className="initial-import-toolbar">
        <label>Jenis<select aria-label={`Jenis baris ${i + 1}`} value={l.kind} disabled={locked} onChange={e => setLine(i, { kind: e.target.value as DraftLine['kind'] })}><option value="BILL">Tagihan</option><option value="CORRECTION">Koreksi (qty 0)</option></select></label>
        <label>Sumber<select aria-label={`Sumber baris ${i + 1}`} value={l.source} disabled={locked} onChange={e => {
            const source = e.target.value, from = originSources.find(o => o.value === source)
            setLine(i, from ? { source, category: from.category } : { source }) }}><option value="">Pilih…</option>
          {correcting && originSources.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          {!correcting && redye.filter(x => x.status === 'COMPLETED').map(x => <option key={x.id} value={'d:' + x.id}>Celup {x.number} · {x.po_number} · baik {x.billed_good}/{x.good} · BS {x.billed_bs}/{x.bs}{x.price_known ? '' : ' · harga belum diketahui'}</option>)}
          {!correcting && billable.filter(b => visibleReceipts.includes(b) || 'r:' + b.receipt_line_id === l.source).map(b => <option key={b.receipt_line_id} value={'r:' + b.receipt_line_id}>{b.receipt_number} · {b.po_number} · baik {b.billed.GOOD}/{b.capacity.GOOD} · BS {b.billed.BS}/{b.capacity.BS} · gagal {b.billed.FAILED_ATTEMPT}/{b.capacity.FAILED_ATTEMPT}{b.price_known ? '' : ' · harga belum lengkap'}</option>)}
          {!correcting && opening.map(u => <option key={u.id} value={'o:' + u.id}>Saldo awal {u.document_number} · {CATEGORY_LABEL[u.category]} {u.billed}/{u.qty}{u.estimate_status === 'UNKNOWN' ? ' · estimasi belum diketahui' : ''}</option>)}
          {l.source && !(correcting ? originSources.some(o => o.value === l.source) : redye.some(x => 'd:' + x.id === l.source) || billable.some(b => 'r:' + b.receipt_line_id === l.source) || opening.some(u => 'o:' + u.id === l.source))
            && <option value={l.source}>{sourceLabel(l.source)}</option>}</select></label>
        <label>Kategori<select aria-label={`Kategori baris ${i + 1}`} value={l.category} disabled={locked} onChange={e => setLine(i, { category: e.target.value as Category })}>
          {(Object.keys(CATEGORY_LABEL) as Category[]).map(c => <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>)}</select></label>
        {l.kind === 'BILL' && <label>Qty<input aria-label={`Qty baris ${i + 1}`} inputMode="numeric" value={l.qty} disabled={locked} onChange={e => setLine(i, { qty: e.target.value })}/></label>}
        <label>Nominal<input aria-label={`Nominal baris ${i + 1}`} value={l.amount} disabled={locked} onChange={e => setLine(i, { amount: e.target.value })}/></label>
        <button type="button" disabled={locked} onClick={() => setLines(ls => ls.filter((_, j) => j !== i))}>Hapus baris {i + 1}</button></div>)}
      <div className="initial-import-toolbar"><button type="button" disabled={locked} onClick={() => setLines(ls => [...ls, { key: crypto.randomUUID(), kind: correcting ? 'CORRECTION' : 'BILL', source: '', category: 'GOOD', qty: '', amount: '' }])}>Tambah baris</button>
        <button type="button" disabled={locked || !valid} onClick={() => send('SAVE_INVOICE_DRAFT', payload())}>Simpan draf invoice</button>
        {editing && <button type="button" disabled={locked} onClick={() => edit(null)}>Draf baru</button>}</div>
      <p>Total invoice harus sama dengan baris − diskon + pembulatan + pajak. Posting memeriksa kebijakan LAU-DEC02/03/06, kapasitas tiap sumber, dan harga yang belum diketahui.</p>
      <p>Koreksi harga dibuat sebagai dokumen koreksi tersendiri yang tertaut ke invoice asal: pilih invoice asalnya, isi baris koreksi (qty 0) untuk sumber yang ditagih invoice itu, dan total bertanda. Plus menambah tagihan; minus menurunkan utang dan menjadi kredit yang lebih dulu melunasi sisa invoice asal. Invoice asal dan pembayarannya tidak diubah.</p>
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
