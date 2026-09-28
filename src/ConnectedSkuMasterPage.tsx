import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { emptySkuSettings, parseSkuMaster, skuGroupChanges, type SkuGroup, type SkuMasterWorkspace, type SkuProduct } from './skuMaster'
import { skuMoney, skuObject } from './skuHpp'
import SkuSettingsFields from './SkuSettingsFields'
import type { Json } from './types/database.preconnect'
import './initial-import.css'
import './sku.css'

export default function ConnectedSkuMasterPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !identity.permissions.includes('master.product.view')) return <section className="panel" role="alert">Hak lihat produk diperlukan.</section>
  return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace() {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('SKU'), { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const [data, setData] = useState<SkuMasterWorkspace | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [query, setQuery] = useState(''), filters = useRef({ query: '', page: 1 }), sequence = useRef(0)
  const [draft, setDraft] = useState<SkuGroup | null>(null), [date, setDate] = useState(cp6WibDateTimeInput), [reason, setReason] = useState('')
  const [preview, setPreview] = useState<{ payload: Json; groups: ReturnType<typeof skuGroupChanges>; basis: Json[]; members: SkuProduct[] } | null>(null)
  const [approved, setApproved] = useState(false)
  const load = useCallback(async () => {
    const seq = ++sequence.current, ticket = beginRead(), requested = { ...filters.current }
    setBusy(true); setData(null); setError(''); setPreview(null); setApproved(false)
    try {
      const result = await client.rpc('erp_get_sku_workspace_v1', { p_filters: requested })
      if (seq !== sequence.current || !isReadCurrent(ticket)) return false
      if (result.error) throw result.error
      const w = parseSkuMaster(result.data)
      if (w.page !== requested.page) throw new Error('Halaman SKU tidak cocok.')
      setData(w); return finishRead(ticket)
    } catch (e) { if (seq === sequence.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message); return false }
    finally { if (seq === sequence.current) setBusy(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load(); return () => { ++sequence.current } }, [load])
  const edit = (g: SkuGroup) => { setDraft(structuredClone(g)); setPreview(null); setApproved(false); setDate(cp6WibDateTimeInput()); setReason('') }
  const create = (p: SkuProduct) => edit({ id: crypto.randomUUID(), sku: p.sku, brand_id: p.brand_id, brand_name: p.brand_name, model_id: p.model_id, model_name: p.model_name, color_name: p.color_name, revision: '0', effective_from: '', members: [p], settings: emptySkuSettings() })
  const review = async () => {
    if (!draft || !reason.trim()) { setError('Isi alasan perubahan.'); return }
    const at = cp6WibPhysicalTimeToIso(date)
    if (!at) { setError('Waktu berlaku WIB tidak valid.'); return }
    const seq = ++sequence.current, ticket = beginRead(), captured = structuredClone(draft)
    setBusy(true); setError(''); setPreview(null); setApproved(false)
    try {
      const first = await client.rpc('erp_get_sku_workspace_v1', { p_filters: { at, roots: captured.members.map(m => m.id) } })
      if (first.error) throw first.error
      const related = parseSkuMaster(first.data).related_groups
      const allRoots = [...new Set([...captured.members.map(m => m.id), ...related.flatMap(g => g.members.map(m => m.id))])]
      const second = await client.rpc('erp_get_sku_workspace_v1', { p_filters: { at, roots: allRoots } })
      if (seq !== sequence.current || !isReadCurrent(ticket)) return
      if (second.error) throw second.error
      const fresh = parseSkuMaster(second.data), current = fresh.related_groups.find(g => g.id === captured.id)
      if (current && current.revision !== captured.revision) throw new Error('SKU sudah diubah operator lain. Muat ulang dan pilih ulang SKU.')
      const groups = skuGroupChanges(captured, fresh.related_groups, fresh.legacy_basis ?? [])
      setPreview({ payload: { effective_from: at, reason: reason.trim(), groups } as Json, groups, basis: fresh.legacy_basis ?? [], members: fresh.selected_products }); finishRead(ticket)
    } catch (e) { if (seq === sequence.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message) }
    finally { if (seq === sequence.current) setBusy(false) }
  }
  const handlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_sku_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (data, envelope) => {
      const r = skuObject(data), p = skuObject(envelope.payload)
      if (r.request_id !== envelope.id || r.action !== envelope.action || r.status !== 'SAVED' || !Array.isArray(r.groups) || !Array.isArray(p.groups) || r.groups.length !== p.groups.length) throw new Error('Respons SKU tidak cocok.')
      for (const x of p.groups) { const requested = skuObject(x), saved = r.groups.map(skuObject).filter(g => g.id === requested.id); if (saved.length !== 1 || saved[0].revision !== (BigInt(String(requested.expected_version)) + 1n).toString() || typeof saved[0].version_id !== 'string') throw new Error('Revisi SKU tidak cocok.') }
    },
    retire: () => { setDraft(null); setPreview(null); setApproved(false) }, reload: load,
  }
  const locked = busy || recovery.writerLocked
  return <section className="initial-import sku-workspace">
    <header className="panel"><h1>Produk & SKU</h1><p>Satu SKU memiliki satu harga jual, resep aksesori, dan pengaturan tarif jasa. Stok tetap dicatat per ukuran.</p></header>
    <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert">{error}</p>}
    <form className="panel initial-import-toolbar" onSubmit={e => { e.preventDefault(); filters.current = { query: query.trim(), page: 1 }; void load() }}><label>Cari SKU atau merek<input value={query} maxLength={120} onChange={e => setQuery(e.target.value)}/></label><button disabled={busy || recovery.busy}>Cari / muat ulang</button></form>
    {data && <><section className="panel"><h2>SKU bersama</h2><table><thead><tr><th>SKU</th><th>Model · warna</th><th>Ukuran anggota</th><th>Harga / PCS</th><th>Mulai berlaku</th><th>Pengaturan</th></tr></thead><tbody>{data.groups.map(g => <tr key={g.id}><td>{g.brand_name} · {g.sku}</td><td>{g.model_name} · {g.color_name}</td><td>{g.members.map(m => m.size).join(', ') || 'Sudah dipindah'}</td><td>{g.settings ? skuMoney(g.settings.price === null ? null : String(g.settings.price)) : 'Terbatas'}</td><td>{formatCp6WibDateTime(g.effective_from)}</td><td><button disabled={!data.can_edit || locked} onClick={() => edit(g)}>Ubah SKU {g.sku}</button></td></tr>)}</tbody></table>{data.groups.length === 0 && <p>Belum ada SKU bersama yang cocok.</p>}</section>
      {data.can_edit && <section className="panel"><h2>Anggota fisik tersedia</h2><p>Pilih ukuran yang sudah terdaftar untuk membuat SKU baru atau menambah anggota. Ukuran khusus 27 dapat dibuat menjadi SKU tersendiri.</p><table><thead><tr><th>Produk</th><th>Model · warna</th><th>Ukuran</th><th>Pilih</th></tr></thead><tbody>{data.products.map(p => <tr key={p.id}><td>{p.brand_name} · {p.sku}</td><td>{p.model_name} · {p.color_name}</td><td>{p.size}</td><td>{draft ? <button disabled={locked || Boolean(preview) || p.brand_id !== draft.brand_id || p.model_id !== draft.model_id || p.color_name !== draft.color_name || draft.members.some(m => m.size_id === p.size_id)} onClick={() => setDraft({ ...draft, members: [...draft.members, p] })}>Tambah ukuran {p.size}</button> : <button disabled={locked} onClick={() => create(p)}>Buat SKU dari ukuran {p.size}</button>}</td></tr>)}</tbody></table></section>}
      <div className="panel"><button disabled={busy || data.page <= 1} onClick={() => { filters.current.page--; void load() }}>Sebelumnya</button> Halaman {data.page} · {data.groups_total} SKU / {data.products_total} ukuran <button disabled={busy || data.page * 50 >= Math.max(data.groups_total, data.products_total)} onClick={() => { filters.current.page++; void load() }}>Berikutnya</button></div>
    </>}
    {draft && data?.lookups && <section className="panel"><h2>{draft.revision === '0' ? 'Buat SKU' : `Revisi ${draft.sku}`}</h2><fieldset disabled={locked || Boolean(preview)}>
      <label>Kode SKU<input value={draft.sku} disabled={draft.revision !== '0'} maxLength={100} onChange={e => setDraft({ ...draft, sku: e.target.value })}/></label><p>{draft.brand_name} · {draft.model_name} · {draft.color_name}</p>
      <p>Anggota: {draft.members.map(m => m.size).join(', ')}.</p><p>Untuk memindahkan ukuran ke SKU lain, buka SKU tujuan lalu tambahkan ukuran tersebut; kelompok asal ikut direvisi dalam satu penyimpanan.</p>
      <label>Mulai berlaku WIB<input type="datetime-local" value={date} onChange={e => setDate(e.target.value)}/></label><label>Alasan perubahan<input value={reason} maxLength={1000} onChange={e => setReason(e.target.value)}/></label>
      <SkuSettingsFields value={draft.settings ?? emptySkuSettings()} lookups={data.lookups} change={settings => setDraft({ ...draft, settings })}/>
      <button type="button" disabled={!draft.sku.trim() || !reason.trim()} onClick={() => void review()}>Periksa seluruh dampak perubahan</button>
    </fieldset>
    {preview && <section><h3>Periksa sebelum menyimpan</h3>{preview.groups.map(g => <p key={g.id}>{g.sku}: {g.members.map(id=>preview.members.find(m=>m.id===id)?.size ?? 'Ukuran belum terbaca').join(', ') || 'Tidak ada anggota'} setelah perubahan. Revisi lama {g.expected_version}; harga baru {skuMoney(g.settings.price === null ? null : String(g.settings.price))}.</p>)}
      <table><thead><tr><th>Ukuran</th><th>Harga sebelumnya</th><th>Resep sebelumnya</th></tr></thead><tbody>{preview.basis.map(x => { const b = skuObject(x), m = preview.members.find(m => m.id === b.product_root); return <tr key={String(b.product_root)}><td>{m?.size ?? 'Anggota kelompok asal'}</td><td>{skuMoney(b.price === null ? null : String(b.price))}</td><td>{b.bom === null ? 'Belum ditentukan' : Array.isArray(b.bom) ? b.bom.length === 0 ? 'Tanpa aksesori' : b.bom.map((v,i) => { const item=skuObject(v), category=data.lookups?.accessories.find(a=>a.id===item.category_id); return <p key={i}>{category?.name ?? String(item.category_id)}: {String(item.qty_per_good_fg_base)} {category?.unit} / PCS · {item.hpp_method === 'BOM_STANDARD' ? `Standar ${skuMoney(String(item.hpp_standard_rate))} / ${String(item.hpp_uom_code)}` : 'Rata-rata kategori stok'} · penggantian {skuMoney(String(item.reimbursement_rate))} / {String(item.reimbursement_uom_code)}</p> }) : 'Tidak valid'}</td></tr> })}</tbody></table>
      <p>Harga/resep lama tetap menjadi riwayat. Pengaturan bersama di atas berlaku untuk semua anggota baru, termasuk ukuran yang dipindah.</p>
      <label><input type="checkbox" checked={approved} disabled={locked} onChange={e => setApproved(e.target.checked)}/>Saya sudah memeriksa anggota dan pengaturan seluruh kelompok yang berubah.</label>
      <button disabled={locked || !approved} onClick={() => void run('SAVE_GROUPS', preview.payload, null, handlers)}>Simpan seluruh perubahan SKU</button><button disabled={locked} onClick={() => { setPreview(null); setApproved(false) }}>Kembali mengubah</button>
    </section>}
    <button disabled={locked} onClick={() => { setDraft(null); setPreview(null) }}>Tutup penyunting</button></section>}
  </section>
}
