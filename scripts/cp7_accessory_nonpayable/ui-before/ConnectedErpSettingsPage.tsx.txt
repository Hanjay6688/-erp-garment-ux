import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import Cp6PolicyReadiness from './Cp6PolicyReadiness'
import { ownerChoice, policyValueText, type PolicyState } from './cp6Readiness'
import { policyValue as accessoryPolicyValue, validateServiceResult, type AccessoryPolicyKey } from './accessoryService'
import { policyValue as laundryPolicyValue, validateBdResult, type LauPolicyKey } from './laundryBd'
import { accessoryPolicyPayload, laundryPolicyPayload, parseErpSettingsWorkspace, settingsRefusalText, type ErpSettingsWorkspace,
  type SettingsChoices, type SettingsFamily, type SettingsFamilyKey, type SettingsPolicy, type SettingsPolicyKey } from './erpSettingsContract'
import type { ProductionEnvelope } from './productionRecovery'
import type { Json } from './types/database.preconnect'
import './erp-settings.css'

// R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): Pengaturan ERP in the Enteng build. Every owner policy of the
// accessory and laundry workflows, read from the server (erp_cp7_get_erp_settings_v1), and the official cutover date (read only,
// changed on Impor data awal). A change goes through the SAME Native writer as the Aksesori / Laundry page
// (erp_save_accessory_service_action_v1 / erp_save_laundry_bd_action_v1, SET_POLICY) with the same payload, the version that was
// read, a reason and one request UUID per attempt kept for recovery in the same recovery domain as those pages.
type Operation = 'SET' | 'CLEAR'
type Submit = (key: SettingsPolicyKey, operation: Operation, version: string, reason: string, value: Record<string, Json> | null) => void
type Named = { id: string; name: string }
const stamp = (iso: string) => `${new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Jakarta' }).format(new Date(iso))} WIB`
const longDate = (day: string) => new Intl.DateTimeFormat('id-ID', { dateStyle: 'long', timeZone: 'UTC' }).format(new Date(day + 'T00:00:00Z'))
const count = (n: number) => n.toLocaleString('id-ID')

export default function ConnectedErpSettingsPage({ onOpenImport }: { onOpenImport?: () => void } = {}) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel cset" aria-label="Pengaturan ERP"><h1>Pengaturan ERP</h1><p>Masuk ke ERP yang tersambung untuk melihat pengaturan.</p></section>
  if (!hasPermission(identity, 'settings.erp.view')) return <section className="panel cset" role="alert"><h1>Pengaturan ERP</h1><p>Hak melihat pengaturan ERP diperlukan.</p></section>
  return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} onOpenImport={onOpenImport}/>
}

function Workspace({ onOpenImport }: { onOpenImport?: () => void }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  // The same recovery domains as the Aksesori and Laundry pages: an unsure save is seen (and reconciled) on either screen.
  const accessory = useProductionMutation('ACCESSORY_SERVICE'), laundry = useProductionMutation('LAUNDRY_BD')
  const { beginRead: beginAccessory, finishRead: finishAccessory, isReadCurrent: accessoryCurrent } = accessory
  const { beginRead: beginLaundry, finishRead: finishLaundry, isReadCurrent: laundryCurrent } = laundry
  const [data, setData] = useState<ErpSettingsWorkspace | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const [done, setDone] = useState(''), [editing, setEditing] = useState<{ family: SettingsFamilyKey; key: SettingsPolicyKey } | null>(null)
  const sequence = useRef(0)
  // One read serves both writers, so both are marked read (or not) together (best practice D18b).
  const load = useCallback(async () => {
    const number = ++sequence.current, a = beginAccessory(), l = beginLaundry()
    setLoading(true); setError('')
    try {
      const result = await client.rpc('erp_cp7_get_erp_settings_v1')
      if (number !== sequence.current || !accessoryCurrent(a) || !laundryCurrent(l)) return false
      if (result.error) throw result.error
      setData(parseErpSettingsWorkspace(result.data))
      const fresh = [finishAccessory(a), finishLaundry(l)]
      return fresh[0] && fresh[1]
    } catch (failure) {
      if (number === sequence.current) { setData(null); setError(normalizeClientError(failure).message) }
      return false
    } finally { if (number === sequence.current) setLoading(false) }
  }, [client, beginAccessory, beginLaundry, finishAccessory, finishLaundry, accessoryCurrent, laundryCurrent])
  useEffect(() => { void load() }, [load])
  useEffect(() => () => { ++sequence.current }, [])

  const saved = (value: unknown, envelope: ProductionEnvelope) => {
    const r = value as Record<string, unknown>, p = envelope.payload as Record<string, Json>
    const key = String(p.policy_key).replace('_', '-'), version = typeof r.version === 'string' && /^\d+$/.test(r.version) ? r.version : null
    setDone(`${key} tersimpan: ${p.operation === 'SET' ? 'ditetapkan' : 'kembali menunggu keputusan owner'}${version ? `, versi ${version}` : ''}. Pengaturan dibaca ulang dari server.`)
    setEditing(null); setData(null)
  }
  // Exactly the calls and result checks of ConnectedAccessoryServicePage and LaundryBdPanel for SET_POLICY.
  const accessoryHandlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_accessory_service_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (value, envelope) => {
      const p = envelope.payload as Record<string, Json>
      validateServiceResult(value, envelope.action, envelope.id, typeof p.document_id === 'string' ? p.document_id : null)
    },
    retire: saved,
    reload: load,
  }
  const laundryHandlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_laundry_bd_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (value, envelope) => validateBdResult(value, envelope.action, envelope.id),
    retire: saved,
    reload: load,
  }
  const submit = (family: SettingsFamilyKey): Submit => (key, operation, version, reason, value) => {
    setDone('')
    if (family === 'ACCESSORY') void accessory.run('SET_POLICY', accessoryPolicyPayload(key as AccessoryPolicyKey, operation, version, reason, value), null, accessoryHandlers)
    else void laundry.run('SET_POLICY', laundryPolicyPayload(key as LauPolicyKey, operation, version, reason, value), null, laundryHandlers)
  }
  const busy = loading || accessory.busy || laundry.busy
  const locked = (family: SettingsFamilyKey) => busy || data === null || (family === 'ACCESSORY' ? accessory.writerLocked : laundry.writerLocked)
  const recovery = (m: typeof accessory, handlers: ProductionMutationHandlers, page: string) => m.pending
    ? m.pending.action === 'SET_POLICY'
      ? <ProductionRecoveryNotice recovery={m} onReconcile={() => m.reconcile(handlers)} className="cset-alert" messageText={m.error ? settingsRefusalText(m.error) : undefined}
          reconcileLabel="Periksa hasil simpan kebijakan"/>
      : <p className="cset-alert" role="alert">Ada transaksi di halaman {page} yang hasilnya belum pasti. Buka halaman {page} untuk memeriksanya; perubahan kebijakan di sini terkunci sampai selesai.</p>
    : m.error ? <p className="cset-alert" role="alert">{settingsRefusalText(m.error)}</p> : null
  const anyEditor = Boolean(data?.families.some(f => f.canSet))
  const blocked = anyEditor && !busy && data !== null && !accessory.pending && !laundry.pending && !accessory.error && !laundry.error
    && (accessory.writerLocked || laundry.writerLocked) ? accessory.blockReason || laundry.blockReason : ''
  const policies: PolicyState[] = data ? data.families.flatMap(f => (f.policies ?? []).map(p => ({ key: p.key, status: p.status, value: p.value }))) : []
  const names: Named[] = data?.choices ? [...data.choices.accounts, ...data.choices.categories, ...data.choices.users] : []
  return <main className="cset" aria-label="Pengaturan ERP">
    <header className="panel cset-heading"><div><div className="eyebrow">PENGATURAN & AUDIT</div><h1>Pengaturan ERP</h1>
      <p>Kebijakan owner untuk aksesori dan laundry, dibaca langsung dari server. Perubahan disimpan lewat penyimpan yang sama dengan halaman Aksesori dan Laundry: hanya owner, wajib alasan, dan ditolak bila pengaturan sudah diubah orang lain sejak dibuka.</p></div>
      <button type="button" disabled={busy} onClick={() => { setDone(''); void load() }}>Muat ulang pengaturan</button></header>
    {recovery(accessory, accessoryHandlers, 'Aksesori')}
    {recovery(laundry, laundryHandlers, 'Laundry')}
    {blocked ? <p className="cset-alert" role="alert">{blocked}</p> : null}
    {done ? <p className="cset-done" role="status">{done}</p> : null}
    {error ? <section className="panel cset-alert" role="alert"><p>Pengaturan belum terbaca. {error}</p></section> : null}
    {data === null ? (error ? null : <p className="panel" role="status">{loading ? 'Memuat pengaturan…' : 'Pengaturan belum terbaca.'}</p>) : <>
      <Cutover data={data} onOpenImport={onOpenImport}/>
      {policies.length ? <Cp6PolicyReadiness policies={policies}/> : null}
      {data.families.map(f => <Family key={f.family} family={f} canSeeValues={data.canSeeValues} names={names} choices={data.choices} locked={locked(f.family)}
        open={editing?.family === f.family ? editing.key : null} onEdit={key => { setDone(''); setEditing(key ? { family: f.family, key } : null) }} onSubmit={submit(f.family)}/>)}
    </>}
  </main>
}

function Cutover({ data, onOpenImport }: { data: ErpSettingsWorkspace; onOpenImport?: () => void }) {
  const c = data.cutover
  return <section className="panel cset-cutover" aria-label="Tanggal mulai pakai aplikasi">
    <h2>Tanggal mulai pakai aplikasi</h2>
    {!data.cutoverVisible ? <p>Tanggal mulai pakai aplikasi hanya terlihat oleh owner dan admin.</p>
      : c?.cutoverDate ? <p>Berlaku: <strong>{longDate(c.cutoverDate)}</strong>{c.setBy && c.setAt ? ` (disahkan ${c.setBy}, ${stamp(c.setAt)})` : ''}. Transaksi operasional baru tidak boleh bertanggal sebelum tanggal ini.</p>
        : <p>Belum disahkan. Selama belum ada tanggal resmi, server belum membatasi tanggal transaksi.</p>}
    <p className="cset-help">Tanggal ini hanya ditampilkan di sini. Owner mengubahnya di menu {c?.changeOn ?? 'Impor data awal'}.</p>
    {onOpenImport ? <button type="button" onClick={onOpenImport}>Buka Impor data awal</button> : null}
  </section>
}

function Family({ family, canSeeValues, names, choices, locked, open, onEdit, onSubmit }: { family: SettingsFamily; canSeeValues: boolean; names: Named[]
  choices: SettingsChoices | null; locked: boolean; open: SettingsPolicyKey | null; onEdit: (key: SettingsPolicyKey | null) => void; onSubmit: Submit }) {
  return <section className="panel cset-family" aria-label={family.label}>
    <h2>{family.label}</h2>
    <p className="cset-help">Kebijakan yang sama tampil di halaman {family.sourcePage}.</p>
    {!family.visible || family.policies === null
      ? <p>{family.family === 'ACCESSORY' ? 'Hak melihat aksesori diperlukan untuk membaca kebijakan ini.' : 'Hak melihat laundry diperlukan untuk membaca kebijakan ini.'}</p>
      : <>
        {!family.canSet ? <p className="cset-help">{canSeeValues ? 'Hanya owner yang dapat mengubah kebijakan ini.'
          : 'Isi kebijakan, alasan, dan siapa yang mengubahnya hanya terlihat oleh owner dan admin. Hanya owner yang dapat mengubahnya.'}</p> : null}
        <div className="cset-list">{family.policies.map(p => <Policy key={p.key} family={family.family} policy={p} canSet={family.canSet} names={names} choices={choices}
          locked={locked} open={open === p.key} onEdit={onEdit} onSubmit={onSubmit}/>)}</div>
      </>}
  </section>
}

function Policy({ family, policy: p, canSet, names, choices, locked, open, onEdit, onSubmit }: { family: SettingsFamilyKey; policy: SettingsPolicy; canSet: boolean
  names: Named[]; choices: SettingsChoices | null; locked: boolean; open: boolean; onEdit: (key: SettingsPolicyKey | null) => void; onSubmit: Submit }) {
  return <article className="cset-policy" aria-label={`Kebijakan ${p.key}`}>
    <div className="cset-policy-head"><h3>{p.key} · {p.label}</h3><span className={`cset-status ${p.status === 'SET' ? 'is-set' : 'is-pending'}`}>{p.statusText}</span></div>
    <p>{policyValueText({ key: p.key, status: p.status, value: p.value }, names)}</p>
    {p.pendingEffect ? <p className="cset-effect">{p.pendingEffect}</p> : null}
    <p className="cset-meta">Versi {p.version} · tercatat {stamp(p.setAt)}{p.setBy ? ` oleh ${p.setBy}` : ''}</p>
    {p.reason ? <p className="cset-meta">Alasan: {p.reason}</p> : null}
    {p.events.length ? <details><summary>Riwayat perubahan ({count(p.eventCount)})</summary>
      <ol className="cset-events">{p.events.map(e => <li key={e.version}>Versi {e.version} · {e.status === 'SET' ? 'ditetapkan' : 'menunggu keputusan'} · {stamp(e.setAt)}
        {e.setBy ? ` · ${e.setBy}` : ''}{e.reason ? ` · alasan: ${e.reason}` : ''}{e.value ? ` · ${policyValueText({ key: p.key, status: e.status, value: e.value }, names)}` : ''}</li>)}</ol>
      {p.eventCount > p.events.length ? <p className="cset-help">Menampilkan {count(p.events.length)} perubahan terakhir dari {count(p.eventCount)}.</p> : null}</details> : null}
    {canSet && choices && !open ? <button type="button" disabled={locked} onClick={() => onEdit(p.key)}>Ubah {p.key}</button> : null}
    {canSet && choices && open ? <Editor key={`${p.key}:${p.version}`} family={family} policy={p} names={names} choices={choices} locked={locked}
      onClose={() => onEdit(null)} onSubmit={onSubmit}/> : null}
  </article>
}

// The fields of the Aksesori page (Kebijakan & area) and the Laundry page (Kebijakan owner), with their policyValue builders.
function Editor({ family, policy, names, choices, locked, onClose, onSubmit }: { family: SettingsFamilyKey; policy: SettingsPolicy; names: Named[]
  choices: SettingsChoices; locked: boolean; onClose: () => void; onSubmit: Submit }) {
  const key = policy.key
  const [f, setF] = useState<Record<string, string>>({}), [pick, setPick] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState(''), [checked, setChecked] = useState(false)
  const value = family === 'ACCESSORY' ? accessoryPolicyValue(key as AccessoryPolicyKey, f) : laundryPolicyValue(key as LauPolicyKey, f, pick)
  const set = (patch: Record<string, string>) => { setF(v => ({ ...v, ...patch })); setChecked(false) }
  const toggle = (k: string, on: boolean) => { setPick(v => ({ ...v, [k]: on })); setChecked(false) }
  const choice = policy.status !== 'SET' ? ownerChoice(key) : null
  const accounts = (types: string[]) => choices.accounts.filter(a => types.includes(a.type))
  const select = (k: string, label: string, options: [string, string][], placeholder = 'Pilih…') => <label key={k}>{label}
    <select aria-label={label} value={f[k] ?? ''} disabled={locked} onChange={e => set({ [k]: e.target.value })}>
      <option value="">{placeholder}</option>{options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
  const account = (k: string, label: string, types: string[]) => select(k, label, accounts(types).map(a => [a.id, `${a.code} · ${a.name}`]), 'Pilih akun')
  const check = (k: string, label: string) => <label key={k} className="cset-check"><input type="checkbox" aria-label={label} checked={Boolean(pick[k])} disabled={locked}
    onChange={e => toggle(k, e.target.checked)}/>{label}</label>
  const input = (k: string, label: string, extra: { inputMode?: 'decimal'; upper?: boolean } = {}) => <label key={k}>{label}<input aria-label={label} inputMode={extra.inputMode}
    disabled={locked} value={f[k] ?? ''} onChange={e => set({ [k]: extra.upper ? e.target.value.toUpperCase() : e.target.value })}/></label>
  const fields = () => {
    switch (key) {
      case 'ACC-DEC01': return <p className="cset-help">Kedua garis waktu nyata: barang kembali lebih dulu lalu diperiksa kemudian, atau kembali dan diperiksa sekarang.</p>
      case 'ACC-DEC03': return <>{account('credit_account_id', 'Akun pengakuan nilai titipan', ['REVENUE', 'EXPENSE'])}
        {select('unit_value_cap', 'Batas nilai per buah', [['MOVING_AVERAGE', 'Tidak melebihi rata-rata stok'], ['NONE', 'Tanpa batas']], 'Pilih')}</>
      case 'ACC-DEC04': return <>{account('CUSTOMER_SERVICE_account_id', 'Akun biaya servis pelanggan', ['EXPENSE'])}{account('OWN_FG_REPAIR_account_id', 'Akun biaya perbaikan barang jadi', ['EXPENSE'])}</>
      case 'ACC-DEC05': return <>{select('mode', 'Cara kredit', [['CREDIT_UNPAID_ONLY', 'Hanya mengurangi tagihan yang belum dibayar'],
        ['CREDIT_THEN_CARRY', 'Kurangi tagihan, sisanya dibawa ke payroll'], ['CREDIT_THEN_REFUND', 'Kurangi tagihan, sisanya dikembalikan tunai']], 'Pilih')}
        {input('credit_conditions', 'Kondisi yang dikredit (USABLE, DAMAGED)', { upper: true })}</>
      case 'ACC-DEC06': return <>{account('gain_account_id', 'Akun pembulatan naik', ['REVENUE', 'EXPENSE'])}{account('loss_account_id', 'Akun pembulatan turun', ['REVENUE', 'EXPENSE'])}</>
      case 'ACC-DEC07': return <>{select('approval_mode', 'Persetujuan owner', [['NONE', 'Tanpa persetujuan owner (sementara)'], ['ABOVE', 'Perlu persetujuan di atas batas nilai']], 'Pilih')}
        {f.approval_mode === 'ABOVE' ? input('owner_approval_above', 'Persetujuan owner di atas nilai (Rp)', { inputMode: 'decimal' }) : null}
        {input('zone_users', 'Petugas area {lokasi: [pengguna]}')}
        <p className="cset-help">Area: {choices.zones.map(z => `${z.name} (${z.id})`).join(', ') || 'belum ada area terdaftar'}.</p>
        <p className="cset-help">Pengguna: {choices.users.map(u => `${u.name} (${u.id})`).join(', ') || '—'}.</p></>
      case 'ERP-DEC02': return <label>Kategori gratis mandor Special<select aria-label="Kategori gratis mandor Special" multiple disabled={locked}
        value={(f.special_free_category_ids ?? '').split(',').filter(Boolean)} onChange={e => set({ special_free_category_ids: [...e.target.selectedOptions].map(o => o.value).join(',') })}>
        {choices.categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
      case 'LAU-DEC01': return <>{check('BATCH', 'Borongan per batch')}{check('MINIMUM', 'Minimum charge')}</>
      case 'LAU-DEC02': return <>{check('GOOD', 'Hasil baik')}{check('BS', 'BS laundry')}{check('FAILED_ATTEMPT', 'Cuci gagal')}</>
      case 'LAU-DEC03': return <>{select('discount', 'Diskon', [['ALLOWED', 'Boleh'], ['REFUSED', 'Ditolak']])}{select('extra', 'Tambahan', [['ALLOWED', 'Boleh'], ['REFUSED', 'Ditolak']])}
        {select('rounding', 'Pembulatan', [['LAST_LINE', 'Di baris terakhir'], ['REFUSED', 'Ditolak']])}{account('tax_account_id', 'Akun pajak masukan', ['ASSET'])}</>
      case 'LAU-DEC04': return select('sale', 'Penjualan', [['REFUSE', 'Tolak sampai harga diketahui'], ['ALLOW_PENDING', 'Boleh, tutup buku tetap tertahan']])
      case 'LAU-DEC05': return <>{check('MODEL', 'Per model')}{check('MODEL_SIZE', 'Per model + ukuran')}{check('MODEL_SIZE_COLOR', 'Per model + ukuran + warna')}
        {select('fallback', 'Tanpa tarif khusus', [['BASE_RATE', 'Pakai tarif proses'], ['REFUSE', 'Tolak']])}</>
      case 'LAU-DEC06': return <>{select('variance_mode', 'Selisih invoice', [['PRODUCT_COST', 'Ke biaya produk'], ['VARIANCE_ACCOUNT', 'Ke akun beban selisih']])}
        {select('after_payment', 'Koreksi sesudah bayar', [['REFUSE', 'Ditolak'], ['CORRECTION_DOCUMENT', 'Dokumen koreksi']])}
        {f.variance_mode === 'VARIANCE_ACCOUNT' ? account('variance_account_id', 'Akun beban selisih', ['EXPENSE']) : null}</>
    }
  }
  const settable = typeof value !== 'string'
  const problem = reason.trim() === '' ? 'Tulis alasan perubahan.' : ''
  return <section className="cset-editor" aria-label={`Ubah kebijakan ${key}`}>
    <h4>Ubah {key}</h4>
    <p className="cset-help">{policy.status === 'SET' ? 'Nilai yang berlaku tertulis di atas. Perubahan memakai pilihan baru di bawah.' : policy.pendingEffect}</p>
    {choice ? <button type="button" disabled={locked} onClick={() => {
      setF(choice.fields); setPick(choice.picks); setReason(`Terapkan keputusan owner 26 Sep 2026 untuk ${key}`); setChecked(false)
    }}>Isi sesuai keputusan owner</button> : null}
    <div className="cset-fields">{fields()}</div>
    {choices.accounts.length < choices.accountsTotal ? <p className="cset-help">Sebagian akun tidak termuat di sini. Akun lain dapat dipilih di halaman {family === 'ACCESSORY' ? 'Aksesori' : 'Laundry'}.</p> : null}
    <label>Alasan perubahan<input aria-label={`Alasan perubahan ${key}`} maxLength={1000} disabled={locked} value={reason} onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
    <p className="cset-preview">{settable ? `Akan ditetapkan: ${policyValueText({ key, status: 'SET', value }, names)}.` : value}</p>
    <label className="cset-check"><input type="checkbox" aria-label={`Perubahan ${key} sudah diperiksa`} checked={checked} disabled={locked || problem !== ''}
      onChange={e => setChecked(e.target.checked)}/>Pilihan dan alasannya sudah saya periksa (versi {policy.version}).</label>
    {reason !== '' && problem ? <p className="cset-problem">{problem}</p> : null}
    <div className="cset-actions">
      <button type="button" className="primary" disabled={locked || !checked || !settable || problem !== ''}
        onClick={() => { if (settable) onSubmit(key, 'SET', policy.version, reason, value) }}>Tetapkan {key}</button>
      <button type="button" disabled={locked || !checked || policy.status !== 'SET' || problem !== ''}
        onClick={() => onSubmit(key, 'CLEAR', policy.version, reason, null)}>Kembalikan {key} ke menunggu</button>
      <button type="button" onClick={onClose}>Tutup</button>
    </div>
  </section>
}
