import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { Json } from './types/database.preconnect'
import './initial-import.css'
import BePocketHistory from './BePocketHistory'
import { parsePocketOpening, type PocketOpening } from './pocketOpening'

type Roll = { id: string; material_id: string; roll_number: string; material_name: string; unit_code: string;
  location_id: string; location_name: string; qty: string; revision: string }
type Entry = { id: string; number: string; status: 'POSTED' | 'REVERSED'; row_version: string; date: string;
  reason: string; roll_id: string; roll_number: string; material_name: string; unit_code: string;
  issued_quantity: string; current_cost: string; cost_policy: 'PERIOD_EXPENSE' }
type Period = { id: string; period_start: string; period_end: string; status: 'ACTIVE' | 'CANCELLED'; reason: string;
  quantity: string; original_amount: string; current_amount: string; per_piece: string; revision: string }
type Preview = { period_start: string; period_end: string; amount: string; quantity: string; per_piece: string;
  source_count: number; blocked: boolean; can_post: boolean; revision: string }
type Workspace = { opening_history: PocketOpening | null; rolls: Roll[]; roll_count: number; materials: { id: string; sku: string; name: string }[]; history: Entry[]; periods: Period[] }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
class PocketDataError extends Error {}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new PocketDataError('Data kain kantong tidak lengkap.')
  return value as Record<string, unknown>
}
const id = (v: unknown): v is string => typeof v === 'string' && uuid.test(v)
const quantity = (v: unknown): v is string => typeof v === 'string' && /^\d{1,14}\.\d{6}$/.test(v)
const rate = (v: unknown): v is string => typeof v === 'string' && /^\d{1,18}\.\d{6}$/.test(v)
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,18}\.\d{2}$/.test(v)
const text = (v: unknown): v is string => typeof v === 'string'
const fixed = (v: string) => v.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '').replace('.', ',')
const micro = (v: string) => { const [whole, part = ''] = v.replace(',', '.').split('.'); return BigInt(whole) * 1000000n + BigInt(part.padEnd(6, '0')) }
const rollKey = (r: Roll) => `${r.id}:${r.location_id}`
const revision = (v: unknown): v is string => text(v) && /^[a-f0-9]{64}$/.test(v)
const day = (v: unknown): v is string => text(v) && /^\d{4}-\d{2}-\d{2}$/.test(v)
const whole = (v: unknown): v is string => text(v) && /^\d{1,19}$/.test(v)
export function parsePocketPreview(value: unknown): Preview {
  const p = object(value)
  if (!day(p.period_start) || !day(p.period_end) || p.period_start > p.period_end || !money(p.amount)
    || !whole(p.quantity) || !rate(p.per_piece) || !revision(p.revision) || !Number.isSafeInteger(p.source_count)
    || Number(p.source_count) < 0 || typeof p.blocked !== 'boolean' || typeof p.can_post !== 'boolean'
    || p.can_post !== (!p.blocked && BigInt(p.quantity) > 0n && micro(p.amount) > 0n && Number(p.source_count) > 0)) throw new PocketDataError('Pembagian periode tidak valid.')
  return p as Preview
}
export function parsePocketWorkspace(value: unknown): Workspace {
  const w = object(value)
  if (!Array.isArray(w.rolls) || !Array.isArray(w.materials) || !Array.isArray(w.history) || !Array.isArray(w.periods)
    || !Number.isSafeInteger(w.roll_count) || Number(w.roll_count) < w.rolls.length) throw new Error('Daftar kain kantong tidak lengkap.')
  const keys = new Set<string>()
  for (const value of w.rolls) {
    const r = object(value)
    if (!id(r.id) || !id(r.material_id) || !id(r.location_id) || !quantity(r.qty) || micro(r.qty) <= 0n
      || ![r.roll_number, r.material_name, r.unit_code, r.location_name].every(text)
      || !text(r.revision) || !/^[a-f0-9]{64}$/.test(r.revision)) throw new Error('Saldo roll tidak valid.')
    const key = `${r.id}:${r.location_id}`
    if (keys.has(key)) throw new Error('Roll ditampilkan dua kali.')
    keys.add(key)
  }
  for (const value of w.materials) { const m = object(value); if (!id(m.id) || !text(m.sku) || !text(m.name)) throw new Error('Bahan tidak valid.') }
  for (const value of w.history) {
    const h = object(value)
    if (!id(h.id) || !id(h.roll_id) || ![h.number,h.reason,h.roll_number,h.material_name,h.unit_code].every(text)
      || !['POSTED','REVERSED'].includes(String(h.status)) || !text(h.row_version) || !/^[1-9]\d{0,18}$/.test(h.row_version)
      || !text(h.date) || !/^\d{4}-\d{2}-\d{2}$/.test(h.date) || !quantity(h.issued_quantity) || !money(h.current_cost)
      || h.cost_policy !== 'PERIOD_EXPENSE') throw new Error('Riwayat pengurangan tidak valid.')
  }
  for (const value of w.periods) {
    const p = object(value)
    if (!id(p.id) || !day(p.period_start) || !day(p.period_end) || p.period_start > p.period_end
      || !text(p.reason) || !whole(p.quantity) || BigInt(p.quantity) <= 0n || !money(p.original_amount)
      || !money(p.current_amount) || !rate(p.per_piece) || !revision(p.revision)
      || !['ACTIVE','CANCELLED'].includes(String(p.status))) throw new Error('Riwayat pembagian tidak valid.')
  }
  return { ...w, opening_history: parsePocketOpening(w) } as Workspace
}

export default function ConnectedPocketFabricPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel"><h1>Kain kantong</h1><p>Masuk ke ERP yang tersambung untuk mencatat stok kain kantong.</p></section>
  if (!['OWNER','ADMIN'].includes(identity.profile.role) || !identity.permissions.includes('warehouse.stock.adjust')) return <section className="panel" role="alert"><h1>Kain kantong</h1><p>Pengurangan stok tersedia untuk owner/admin dengan hak penyesuaian stok.</p></section>
  return <PocketWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function PocketWorkspace() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('POCKET_FABRIC')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [workspace, setWorkspace] = useState<Workspace | null>(null), [error, setError] = useState('')
  const [query, setQuery] = useState(''), queryRef = useRef('')
  const [loading, setLoading] = useState(false), sequence = useRef(0)
  const [selected, setSelected] = useState<Roll | null>(null), [mode, setMode] = useState('REMAINING')
  const [amount, setAmount] = useState(''), [date, setDate] = useState(''), [reason, setReason] = useState('Pemakaian bebas kain kantong')
  const [material, setMaterial] = useState(''), [reversing, setReversing] = useState<Entry | null>(null), [reverseReason, setReverseReason] = useState('')
  const canAllocate = identity.status === 'AUTHORIZED' && identity.permissions.includes('finance.hpp.manage')
  const [periodStart, setPeriodStart] = useState(''), [periodEnd, setPeriodEnd] = useState('')
  const periodRef = useRef({ start: '', end: '' })
  const [preview, setPreview] = useState<Preview | null>(null), [periodReason, setPeriodReason] = useState('Pembagian kain kantong periode')
  const [cancelling, setCancelling] = useState<Period | null>(null), [cancelReason, setCancelReason] = useState('')
  const load = useCallback(async () => {
    const s = ++sequence.current, ticket = beginRead(), requested = queryRef.current
    setLoading(true); setError(''); setPreview(null)
    try {
      const result = await client.rpc('erp_get_pocket_fabric_workspace_v1', { p_query: requested })
      if (!isReadCurrent(ticket) || requested !== queryRef.current) return false
      if (result.error) throw result.error
      const data = parsePocketWorkspace(result.data)
      setWorkspace(data); return finishRead(ticket)
    } catch (failure) { if (isReadCurrent(ticket)) setError(normalizeClientError(failure).message); return false }
    finally { if (s === sequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load])
  const previewPeriod = async () => {
    const s = ++sequence.current, ticket = beginRead(), requested = { ...periodRef.current }
    setLoading(true); setError(''); setPreview(null)
    try {
      const result = await client.rpc('erp_preview_pocket_fabric_period_v1', { p_period_start: requested.start, p_period_end: requested.end })
      if (!isReadCurrent(ticket) || requested.start !== periodRef.current.start || requested.end !== periodRef.current.end) return
      if (result.error) throw result.error
      const value = parsePocketPreview(result.data)
      if (value.period_start !== requested.start || value.period_end !== requested.end) throw new PocketDataError('Periode hasil tidak cocok.')
      setPreview(value); finishRead(ticket)
    } catch (failure) { if (isReadCurrent(ticket)) setError(failure instanceof PocketDataError ? failure.message : normalizeClientError(failure).message) }
    finally { if (s === sequence.current) setLoading(false) }
  }
  const handlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_pocket_fabric_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (data, envelope) => {
      const r = object(data), p = object(envelope.payload)
      if (r.request_id !== envelope.id || r.action !== envelope.action || !id(r.id)
        || r.status !== ({ REGISTER:'REGISTERED', POST:'POSTED', REVERSE:'REVERSED', POST_PERIOD:'ACTIVE', CANCEL_PERIOD:'CANCELLED', CORRECT_OPENING_USAGE:'CORRECTED' } as Record<string,string>)[envelope.action]
        || (envelope.action === 'CORRECT_OPENING_USAGE' && (r.id !== p.usage_id || !money(r.amount)))
        || (['REVERSE','CANCEL_PERIOD'].includes(envelope.action) && r.id !== p.id) || (envelope.action === 'REGISTER' && r.id !== p.material_id)) throw new Error('Respons transaksi tidak cocok.')
    },
    retire: () => { setSelected(null); setAmount(''); setMaterial(''); setReversing(null); setReverseReason(''); setPreview(null); setCancelling(null); setCancelReason('') },
    reload: load,
  }
  const act = (action: string, payload: Record<string, Json>) => run(action, payload, null, handlers)
  const locked = mutation.writerLocked || loading
  const current = workspace?.rolls.find(r => selected && rollKey(r) === rollKey(selected))
  const stale = Boolean(selected && current?.revision !== selected.revision)
  const validQuantity = /^[0-9]{1,14}([.,][0-9]{1,6})?$/.test(amount)
  const delta = selected && validQuantity ? mode === 'USED' ? micro(amount) : micro(selected.qty) - micro(amount) : null
  const valid = selected && !stale && delta !== null && delta > 0n && delta <= micro(selected.qty) && /^\d{4}-\d{2}-\d{2}$/.test(date) && reason.trim()
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">GUDANG</div><h1>Kain kantong</h1><p>Catat kain yang keluar dari stok gudang untuk pemakaian bersama. Sisa pada setiap mandor tidak perlu dirinci.</p></div><button type="button" disabled={mutation.busy} onClick={() => void load()}>Muat ulang</button></header>
    <p className="initial-import-help">Nilai pengeluaran tercatat sebagai biaya periode. Untuk memasukkannya ke HPP celana, lihat pembagian periode lalu sahkan. Pengambilan per mandor tetap tidak perlu dirinci.</p>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert" className="initial-import-message">{error}</p>}
    <form className="panel initial-import-toolbar" onSubmit={e => { e.preventDefault(); queryRef.current = query.trim(); void load() }}>
      <label>Cari bahan atau roll<input aria-label="Cari kain kantong" maxLength={120} value={query} onChange={e => setQuery(e.target.value)}/></label><button disabled={mutation.busy}>Cari</button>
      {workspace && <span>{workspace.rolls.length} dari {workspace.roll_count} stok roll. Persempit pencarian bila belum terlihat.</span>}
    </form>
    <div className="panel initial-import-advances">
      <h2>Kurangi stok gudang</h2>
      <label>Roll dan gudang<select aria-label="Roll kain kantong" disabled={locked} value={selected ? rollKey(selected) : ''} onChange={e => { setSelected(workspace?.rolls.find(r => rollKey(r) === e.target.value) ?? null); setAmount('') }}><option value="">Pilih roll</option>{workspace?.rolls.map(r => <option key={rollKey(r)} value={rollKey(r)}>{r.roll_number} · {r.material_name} · {r.location_name} · {fixed(r.qty)} {r.unit_code}</option>)}</select></label>
      {selected && <p>Stok tercatat: <strong>{fixed(selected.qty)} {selected.unit_code}</strong>. Tanggal dan catatan dapat disiapkan sebelum disahkan.</p>}
      {stale && <p role="alert">Stok roll sudah berubah. Pilih ulang roll dan periksa angka pengurangan sebelum mengesahkan.</p>}
      <div className="initial-import-toolbar">
        <label>Cara mencatat<select aria-label="Cara mencatat" disabled={locked} value={mode} onChange={e => { setMode(e.target.value); setAmount('') }}><option value="REMAINING">Isi sisa roll di gudang</option><option value="USED">Isi jumlah yang dikeluarkan</option></select></label>
        <label>{mode === 'REMAINING' ? 'Sisa yang masih terlihat' : 'Jumlah keluar'}{selected ? ` (${selected.unit_code})` : ''}<input aria-label="Jumlah kain kantong" inputMode="decimal" disabled={locked} value={amount} onChange={e => setAmount(e.target.value)}/></label>
        <label>Tanggal pengurangan<input aria-label="Tanggal pengurangan" type="date" disabled={locked} value={date} onChange={e => setDate(e.target.value)}/></label>
        <label>Catatan<input aria-label="Catatan kain kantong" maxLength={1000} disabled={locked} value={reason} onChange={e => setReason(e.target.value)}/></label>
      </div>
      {delta !== null && delta >= 0n && <p>Pengurangan: <strong>{fixed(`${delta / 1000000n}.${(delta % 1000000n).toString().padStart(6,'0')}`)} {selected?.unit_code}</strong>. Isi sisa 0 jika seluruh roll sudah dikeluarkan.</p>}
      <button className="primary" type="button" disabled={locked || !valid} onClick={() => { if (selected) void act('POST', { roll_id:selected.id, location_id:selected.location_id, expected_revision:selected.revision, mode, quantity:amount, date, reason:reason.trim() }) }}>Sahkan pengurangan stok</button>
      {!workspace?.rolls.length && <p>Belum ada stok kain kantong yang cocok. Cari bahannya atau tambahkan jenis kain kantong di bawah.</p>}
    </div>
    <details className="panel"><summary>Tambahkan jenis kain kantong</summary><p>Pilih master bahan yang khusus dipakai untuk kantong. Bahan yang sudah terkait potongan produksi perlu master tersendiri.</p>
      <div className="initial-import-toolbar"><label>Bahan<select aria-label="Bahan kain kantong" disabled={locked} value={material} onChange={e => setMaterial(e.target.value)}><option value="">Pilih bahan</option>{workspace?.materials.map(m => <option key={m.id} value={m.id}>{m.sku} · {m.name}</option>)}</select></label><button type="button" disabled={locked || !workspace?.materials.some(m => m.id === material)} onClick={() => void act('REGISTER', { material_id:material, reason:'Ditetapkan sebagai kain kantong untuk pemakaian bersama' })}>Tetapkan sebagai kain kantong</button></div>
    </details>
    {canAllocate && <section className="panel initial-import-advances"><h2>Bagi ke HPP per periode</h2>
      <p>Nilai kain keluar dibagi rata ke seluruh celana selesai dijahit dalam periode, termasuk hasil Afui. Ini alokasi bersama berdasarkan pengeluaran gudang.</p>
      <div className="initial-import-toolbar">
        <label>Mulai<input aria-label="Awal periode kain kantong" type="date" disabled={locked} value={periodStart} onChange={e => { setPeriodStart(e.target.value); periodRef.current.start=e.target.value; setPreview(null) }}/></label>
        <label>Sampai<input aria-label="Akhir periode kain kantong" type="date" disabled={locked} value={periodEnd} onChange={e => { setPeriodEnd(e.target.value); periodRef.current.end=e.target.value; setPreview(null) }}/></label>
        <label>Alasan<input aria-label="Alasan pembagian kain kantong" maxLength={1000} disabled={locked} value={periodReason} onChange={e => setPeriodReason(e.target.value)}/></label>
        <button type="button" disabled={locked || !periodStart || !periodEnd || periodStart>periodEnd} onClick={() => void previewPeriod()}>Lihat pembagian</button>
      </div>
      {preview && <div><p>{preview.source_count} pengeluaran: <strong>Rp {preview.amount.replace('.',',')}</strong> ÷ <strong>{preview.quantity} pcs selesai dijahit</strong> = sekitar <strong>Rp {fixed(preview.per_piece)} per pcs</strong>. Selisih pembulatan tetap dibagi sampai total tepat.</p>
        {preview.blocked ? <p role="alert">Sudah ada alokasi aktif yang bertumpang tindih. Batalkan alokasi terkait untuk menghitung ulang.</p> : !preview.can_post && <p>Belum ada nilai kain atau hasil jahit yang bisa dibagi.</p>}
        <p>Saat disahkan, biaya periode dialihkan ke produksi. Stok tidak dikurangi lagi. Koreksi harga nota memperbarui HPP dan jurnal terkait.</p>
        <button type="button" className="primary" disabled={locked || !preview.can_post || !periodReason.trim()} onClick={() => void act('POST_PERIOD',{ period_start:preview.period_start,period_end:preview.period_end,expected_revision:preview.revision,reason:periodReason.trim() })}>Sahkan pembagian ke HPP</button>
      </div>}
    </section>}
    {workspace?.opening_history && <BePocketHistory data={workspace.opening_history} locked={locked} canCorrect={canAllocate} onCorrect={p => void act('CORRECT_OPENING_USAGE', p)}/>}
    <section className="panel initial-import-table"><h2>Riwayat pembagian periode</h2><p>50 alokasi terbaru. Pembatalan mengembalikan biaya periode dan menghitung ulang HPP; stok tetap.</p>
      <table><thead><tr><th>Periode</th><th>Hasil jahit</th><th>Nilai terkini</th><th>Status</th><th>Tindakan</th></tr></thead><tbody>{workspace?.periods.map(p => <tr key={p.id}>
        <td>{p.period_start} — {p.period_end}</td><td>{p.quantity} pcs</td><td>Rp {p.current_amount.replace('.',',')}</td><td>{p.status==='ACTIVE'?'Aktif':'Dibatalkan'}</td>
        <td>{canAllocate && p.status==='ACTIVE' && <button type="button" disabled={locked} onClick={() => { setCancelling(p); setCancelReason('') }}>Batalkan alokasi {p.period_start}</button>}</td>
      </tr>)}</tbody></table>
      {cancelling && <div className="initial-import-toolbar"><label>Alasan pembatalan alokasi<input aria-label="Alasan pembatalan alokasi" disabled={locked} maxLength={1000} value={cancelReason} onChange={e => setCancelReason(e.target.value)}/></label>
        <button type="button" disabled={locked || !cancelReason.trim()} onClick={() => void act('CANCEL_PERIOD',{id:cancelling.id,expected_revision:cancelling.revision,reason:cancelReason.trim()})}>Sahkan pembatalan alokasi</button><button type="button" disabled={mutation.busy} onClick={() => setCancelling(null)}>Tutup alokasi</button></div>}
    </section>
    <section className="panel initial-import-table"><h2>Riwayat pengurangan</h2><p>50 catatan terbaru sesuai pencarian. Nilai keluar mengikuti koreksi harga; pembagian ke HPP dicatat pada riwayat periode.</p><table><thead><tr><th>Tanggal</th><th>Roll</th><th>Keluar</th><th>Nilai keluar</th><th>Catatan</th><th>Status</th><th>Tindakan</th></tr></thead><tbody>{workspace?.history.map(h => <tr key={h.id}><td>{h.date}</td><td>{h.roll_number}<small> · {h.material_name}</small></td><td>{fixed(h.issued_quantity)} {h.unit_code}</td><td>Rp {h.current_cost.replace('.', ',')}</td><td>{h.reason}</td><td>{h.status === 'POSTED' ? 'Disahkan' : 'Dibatalkan'}</td><td>{h.status === 'POSTED' && <button type="button" disabled={locked} onClick={() => { setReversing(h); setReverseReason('') }}>Batalkan {h.roll_number}</button>}</td></tr>)}</tbody></table></section>
    {reversing && <div className="panel initial-import-toolbar"><p>Pembatalan {reversing.roll_number} mengembalikan stok dan membalik biaya.</p><label>Alasan pembatalan<input aria-label="Alasan pembatalan" disabled={locked} maxLength={1000} value={reverseReason} onChange={e => setReverseReason(e.target.value)}/></label><button type="button" disabled={locked || !reverseReason.trim()} onClick={() => void act('REVERSE', { id:reversing.id, expected_version:reversing.row_version, reason:reverseReason.trim() })}>Sahkan pembatalan</button><button type="button" disabled={mutation.busy} onClick={() => setReversing(null)}>Tutup</button></div>}
  </section>
}
