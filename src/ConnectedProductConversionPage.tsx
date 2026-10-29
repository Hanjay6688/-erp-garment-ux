import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { conversionObject, autoConversionPayload, parseAutoConversionPreview, parseConversionWorkspace, validateConversionResult, type AutoConversionPreview, type ConversionWorkspace } from './productConversion'
import { displayRupiah, parseAccessoryServiceWorkspace, wibTimestamp, type AccessoryServiceWorkspace } from './accessoryService'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import type { Json } from './types/database.preconnect'
import './initial-import.css'

export default function ConnectedProductConversionPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel"><h1>Ganti Merek / SKU</h1><p>Masuk ke ERP untuk membaca stok.</p></section>
  if (!identity.permissions.includes('warehouse.brand_conversion.view')) return <section className="panel" role="alert">Hak melihat konversi diperlukan.</section>
  return <ConversionWorkspaceView key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function ConversionWorkspaceView() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('PRODUCT_CONVERSION')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [data, setData] = useState<ConversionWorkspace | null>(null), [accessories, setAccessories] = useState<AccessoryServiceWorkspace | null>(null)
  const [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const previewVersion = useRef(0)
  const filters = useRef<Record<string, Json>>({ page: 1, target_page: 1, document_page: 1 }), sequence = useRef(0)
  const [query, setQuery] = useState(''), [targetQuery, setTargetQuery] = useState(''), [accessoryQuery, setAccessoryQuery] = useState('')
  const [source, setSource] = useState(''), [target, setTarget] = useState(''), [quantity, setQuantity] = useState(''), [at, setAt] = useState('')
  const [reason, setReason] = useState(''), [preview, setPreview] = useState<{ payload: Record<string, Json>; detail: AutoConversionPreview } | null>(null)
  const [returns, setReturns] = useState<{ material_id: string; qty: string; holder: string; name: string }[]>([])
  const [returnMaterial, setReturnMaterial] = useState(''), [returnQty, setReturnQty] = useState(''), [holder, setHolder] = useState('')
  const [costDocument, setCostDocument] = useState(''), [costMaterial, setCostMaterial] = useState(''), [costQty, setCostQty] = useState(''), [costLocation, setCostLocation] = useState('')
  const [reverseId, setReverseId] = useState(''), [reverseReason, setReverseReason] = useState('')
  const canAccessories = identity.permissions.includes('warehouse.accessory.view')
  const load = useCallback(async () => {
    const seq = ++sequence.current, ticket = beginRead(), requested = { ...filters.current }
    setLoading(true); setError(''); setPreview(null)
    try {
      const [r, a] = await Promise.all([
        client.rpc('erp_get_product_conversion_workspace_v1', { p_filters: requested }),
        canAccessories ? client.rpc('erp_get_accessory_service_workspace_v1', { p_filters: { query: accessoryQuery, page: 1, page_size: 25 } }) : Promise.resolve(null),
      ])
      if (seq !== sequence.current || !isReadCurrent(ticket)) return false
      if (r.error) throw r.error
      if (a?.error) throw a.error
      const workspace = parseConversionWorkspace(r.data)
      if (workspace.contract_version !== 'cp7.sku-conversion.v1') throw new Error('Pembaruan konversi belum terpasang. Hubungi pengelola ERP.')
      if (requested.selection) {
        const expected = conversionObject(requested.selection), selected = workspace.selection
        if (!selected || selected.source_product_id !== expected.source_product_id || selected.target_product_id !== expected.target_product_id || selected.location_id !== expected.location_id) throw new Error('Lingkup stok berubah atau tidak cocok. Muat ulang pilihan SKU dan gudang.')
      }
      setData(workspace); setAccessories(a ? parseAccessoryServiceWorkspace(a.data) : null)
      return finishRead(ticket)
    } catch (e) { if (seq === sequence.current && isReadCurrent(ticket)) { setData(null); setAccessories(null); setError(e instanceof Error ? e.message : normalizeClientError(e).message) }; return false }
    finally { if (seq === sequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent, canAccessories, accessoryQuery])
  useEffect(() => { void load(); return () => { sequence.current += 1 } }, [load])
  const refresh = (patch: Record<string, Json>) => { filters.current = { ...filters.current, ...patch }; if (filters.current.selection === null) delete filters.current.selection; void load() }
  const handlers: ProductionMutationHandlers = {
    send: e => client.rpc('erp_save_product_conversion_action_v1', { p_action: e.action, p_payload: e.payload, p_client_request_id: e.id }),
    validate: (v, e) => validateConversionResult(v, e.action, e.id, e.payload),
    retire: () => { setData(null); setPreview(null); setReverseId(''); setCostDocument(''); setReturns([]) }, reload: load,
  }
  const locked = mutation.writerLocked || mutation.busy || loading
  const canPost = identity.permissions.includes('warehouse.brand_conversion.post')
  const canReverse = identity.permissions.includes('warehouse.brand_conversion.reverse') && ['OWNER', 'ADMIN'].includes(identity.profile.role)
  const selected = data?.sources?.find(s => `${s.product_id}:${s.location_id}` === source)
  const visibleTarget = data?.targets.find(t => t.id === target)
  const selection = data?.selection
  const stock = selection?.source_product_id === selected?.product_id && selection?.location_id === selected?.location_id ? selection : null
  const previewQty = /^[1-9]\d{0,8}$/.test(quantity) ? Number(quantity) : null
  const invalidate = () => { previewVersion.current += 1; setPreview(null) }
  const browseTargets = (patch: Record<string, Json>) => {
    setTarget(''); invalidate()
    refresh({ ...patch, selection: selected ? { source_product_id: selected.product_id, location_id: selected.location_id, target_product_id: null } : null })
  }
  const prepare = async () => {
    setError(''); setPreview(null)
    try {
      if (!visibleTarget) throw new Error('Pilih kembali SKU dan ukuran tujuan yang terlihat sebelum meninjau konversi.')
      const payload = autoConversionPayload(selected, target, quantity, at, reason)
      if (returnMaterial || returnQty || holder) throw new Error('Tambahkan baris bongkaran atau kosongkan ketiga isian sebelum pratinjau.')
      if (returns.length) payload.expected_returns = returns.map(({ material_id, qty, holder }) => ({ material_id, qty, holder }))
      const stamp = ++sequence.current, draftVersion = previewVersion.current, ticket = beginRead(); setLoading(true)
      const r = await client.rpc('erp_get_product_conversion_workspace_v1', { p_filters: { preview: payload } })
      if (stamp !== sequence.current || !isReadCurrent(ticket)) return
      if (r.error) throw r.error
      const detail = parseAutoConversionPreview(conversionObject(r.data).preview, payload)
      if (finishRead(ticket) && draftVersion === previewVersion.current) setPreview({ payload: { ...payload, expected_version: detail.source_revision }, detail })
    } catch (e) { setError(e instanceof Error ? e.message : normalizeClientError(e).message) }
    finally { setLoading(false) }
  }
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">GUDANG · KONVERSI</div><h1>Ganti Merek / SKU</h1><p>Pilih SKU asal, SKU tujuan dan jumlah PCS. Model atau ukuran tujuan boleh berbeda. Sistem memilih stok sumber secara berurutan; jumlah barang dan nilai sumber tetap terlacak.</p></div><button disabled={mutation.busy || loading} onClick={() => void load()}>Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert">{error}</p>}
    {loading && data && <p role="status">Memuat stok terbaru…</p>}
    {!data ? <p role="status">{loading ? 'Memuat stok…' : 'Stok belum diketahui.'}</p> : <>
      <section className="panel"><h2>1. SKU asal dan gudang</h2><form className="initial-import-toolbar" onSubmit={e => { e.preventDefault(); setSource(''); setTarget(''); refresh({ query: query.trim(), source_product_id: null, selection: null, page: 1 }) }}>
        <label>Cari SKU asal<input value={query} onChange={e => setQuery(e.target.value)}/></label><button disabled={locked}>Cari SKU asal</button></form>
        <label>SKU asal dan gudang<select value={source} disabled={locked} onChange={e => { const value = e.target.value, [productId, locationId] = value.split(':'); setSource(value); setTarget(''); invalidate(); refresh({ source_product_id: productId || null, selection: productId ? { source_product_id: productId, location_id: locationId, target_product_id: null } : null, page: 1, target_page: 1 }) }}>
          <option value="">Pilih SKU asal</option>{data.sources?.map(s => <option key={`${s.product_id}:${s.location_id}`} value={`${s.product_id}:${s.location_id}`}>{s.brand_name} · {s.sku} · ukuran {s.size} · {s.location_name} · tersedia {s.stock.available} PCS</option>)}</select></label>
        <p>{data.sources_total} SKU/lokasi · halaman {data.page} <button disabled={locked || data.page <= 1} onClick={() => refresh({ page: data.page - 1 })}>Asal sebelumnya</button><button disabled={locked || data.page * data.page_size >= (data.sources_total ?? 0)} onClick={() => refresh({ page: data.page + 1 })}>Asal berikutnya</button></p>
      </section>
      <section className="panel"><h2>2. Tujuan dan waktu fisik</h2>
        <form className="initial-import-toolbar" onSubmit={e => { e.preventDefault(); browseTargets({ target_query: targetQuery.trim(), target_page: 1 }) }}><label>Cari SKU tujuan<input value={targetQuery} onChange={e => setTargetQuery(e.target.value)}/></label><button disabled={locked || !selected}>Cari tujuan</button></form>
        <label>SKU tujuan<select value={target} disabled={locked || !selected} onChange={e => { const value = e.target.value; setTarget(value); invalidate(); if (selected) refresh({ selection: { source_product_id: selected.product_id, location_id: selected.location_id, target_product_id: value || null } }) }}><option value="">Pilih SKU dan ukuran tujuan</option>{data.targets.map(t => <option key={t.id} value={t.id}>{t.recommended ? 'Padanan · ' : ''}{t.brand_name} · {t.sku} · ukuran {t.size} · {t.product_name}</option>)}</select></label>
        <p>Padanan hanya pilihan cepat. SKU aktif lainnya tetap boleh dipilih; ukuran tujuan harus dipilih dengan jelas.</p>
        <p>{data.targets_total} SKU aktif <button disabled={locked || data.target_page <= 1} onClick={() => browseTargets({ target_page: data.target_page - 1 })}>Tujuan sebelumnya</button><button disabled={locked || data.target_page * data.page_size >= data.targets_total} onClick={() => browseTargets({ target_page: data.target_page + 1 })}>Tujuan berikutnya</button></p>
        {stock && <div role="status"><p>Lingkup: {selected?.location_name}, kualitas GOOD, masing-masing produk dan ukuran yang dipilih.</p><p>Asal · fisik {stock.source_stock.physical} → {previewQty !== null && previewQty <= stock.source_stock.available ? stock.source_stock.physical - previewQty : '—'} PCS · tersedia {stock.source_stock.available} PCS · dicadangkan {stock.source_stock.reserved} PCS.</p>{stock.target_stock && visibleTarget && stock.target_product_id === target && <p>Tujuan · fisik {stock.target_stock.physical} → {previewQty !== null && previewQty <= stock.source_stock.available ? stock.target_stock.physical + previewQty : '—'} PCS · tersedia {stock.target_stock.available} PCS · dicadangkan {stock.target_stock.reserved} PCS.</p>}</div>}
        <label>Jumlah PCS<input inputMode="numeric" value={quantity} onChange={e => { setQuantity(e.target.value); invalidate() }}/></label>
        <label>Waktu fisik · WIB<input type="datetime-local" value={at} onChange={e => { setAt(e.target.value); invalidate() }}/></label><label>Alasan<textarea value={reason} onChange={e => { setReason(e.target.value); invalidate() }}/></label>
        {accessories && <details><summary>Bongkaran yang diharapkan kembali</summary><p>Masih di pemegang sampai penerimaan dan pemeriksaan dicatat di Aksesori. Perkiraan ini belum menambah stok.</p>
          <label>Cari aksesori<input value={accessoryQuery} onChange={e => setAccessoryQuery(e.target.value)}/></label>
          <label>Aksesori bongkaran<select value={returnMaterial} onChange={e => { setReturnMaterial(e.target.value); invalidate() }}><option value="">Tidak ada</option>{accessories.materials.map(m => <option key={m.id} value={m.id}>{m.sku} · {m.name}</option>)}</select></label>
          <label>Jumlah bongkaran<input inputMode="numeric" value={returnQty} onChange={e => { setReturnQty(e.target.value); invalidate() }}/></label><label>Pemegang<input value={holder} onChange={e => { setHolder(e.target.value); invalidate() }}/></label><button type="button" disabled={locked || !returnMaterial || !/^[1-9]\d{0,8}$/.test(returnQty) || !holder.trim() || returns.length>=100} onClick={()=>{
            const name=accessories.materials.find(m=>m.id===returnMaterial)?.name ?? returnMaterial; setReturns([...returns,{material_id:returnMaterial,qty:returnQty,holder:holder.trim(),name}]);setReturnMaterial('');setReturnQty('');setHolder('');invalidate()
          }}>Tambahkan komponen bongkaran</button>
          <ul>{returns.map((r,i)=><li key={i}>{r.name} · {r.qty} PCS · {r.holder} <button type="button" disabled={locked} onClick={()=>{setReturns(returns.filter((_,n)=>n!==i));invalidate()}}>Hapus baris {i+1}</button></li>)}</ul></details>}
        <button disabled={locked || !canPost || !selected || !stock || !stock.target_stock || !visibleTarget} onClick={() => void prepare()}>Lihat pratinjau</button>
        {preview && <div role="status"><p>{preview.detail.source_sku} → {preview.detail.target_sku} · {preview.detail.qty_pcs} PCS · nilai sumber {displayRupiah(preview.detail.cost.source_value ?? null)}</p><p>Asal: {preview.detail.source_stock.physical} → {preview.detail.source_after.physical} PCS; tersedia {preview.detail.source_stock.available} → {preview.detail.source_after.available} PCS.</p><p>Tujuan: {preview.detail.target_stock.physical} → {preview.detail.target_after.physical} PCS; tersedia {preview.detail.target_stock.available} → {preview.detail.target_after.available} PCS. Reservasi tetap.</p><button disabled={locked || !canPost} onClick={() => void run('POST', preview.payload, null, handlers)}>Catat konversi fisik</button></div>}
      </section>
      <section className="panel initial-import-table"><h2>Riwayat konversi</h2><table><thead><tr><th>Dokumen</th><th>Sumber → tujuan</th><th>Jumlah</th><th>Nilai tujuan kini</th><th>Status</th><th/></tr></thead><tbody>{data.documents.map(d => <tr key={d.id}><td>{d.conversion_number}<br/>{formatCp6WibDateTime(d.physical_at)}</td><td>{d.source_sku} → {d.target_sku}<br/>{d.notes}</td><td>{d.qty_pcs} PCS{d.group_part_count && d.group_part_count > 1 ? <small style={{ display: 'block' }}>Bagian {d.group_line_no}/{d.group_part_count} dari konversi {d.group_qty_pcs} PCS. Pembatalan berlaku untuk seluruh konversi.</small> : null}</td><td>{displayRupiah(d.target_value)}<br/>Tambahan/pulih {displayRupiah(d.extra_cost)}</td><td>{d.status} · {d.value_state==='PROVISIONAL_RECOVERY'?'Nilai sementara: bongkaran belum selesai':'Biaya bersumber sampai saat ini'}{d.returns.map(r=><small key={r.id} style={{display:'block'}}>{r.material} · belum kembali {r.unreturned} · menunggu nilai {r.awaiting_value} · {r.holder}</small>)}</td><td>{d.status === 'POSTED' && <><button disabled={locked || !canReverse} onClick={() => { setReverseId(d.id); setReverseReason('') }}>Batalkan {d.source_sku}</button>{accessories && <button disabled={locked || !canPost} onClick={() => setCostDocument(d.id)}>Catat pemakaian aksesori</button>}</>}</td></tr>)}</tbody></table>
        <p>{data.documents_total} dokumen · halaman {data.document_page} <button disabled={locked || data.document_page <= 1} onClick={() => refresh({ document_page: data.document_page - 1 })}>Dokumen sebelumnya</button><button disabled={locked || data.document_page * data.page_size >= data.documents_total} onClick={() => refresh({ document_page: data.document_page + 1 })}>Dokumen berikutnya</button></p>
        {reverseId && <form onSubmit={e => { e.preventDefault(); void run('REVERSE', { conversion_id: reverseId, reason: reverseReason.trim() }, null, handlers) }}><p>Pastikan perubahan fisik juga dibalik. Transaksi turunan aktif harus dibatalkan dahulu.{data.documents.find(d => d.id === reverseId)?.group_part_count ? ` Seluruh konversi ${data.documents.find(d => d.id === reverseId)!.group_qty_pcs} PCS akan dibatalkan bersama.` : ''}</p><label>Alasan pembatalan<input value={reverseReason} onChange={e => setReverseReason(e.target.value)}/></label><button disabled={locked || !canReverse || !reverseReason.trim()}>Konfirmasi pembatalan</button></form>}
        {costDocument && accessories && <form onSubmit={e => { e.preventDefault(); const doc = data.documents.find(d => d.id === costDocument), time = wibTimestamp(at)
          if (!doc || !time || !costMaterial || !costLocation || !/^[1-9]\d{0,8}$/.test(costQty) || !reason.trim()) { setError('Lengkapi gudang, aksesori, jumlah, waktu dan alasan pemakaian.'); return }
          void run('POST_USAGE', { conversion_id: doc.id, expected_version: doc.revision, location_id: costLocation, physical_at: time, items: [{ material_id: costMaterial, qty: costQty }], reason: reason.trim() }, null, handlers)
        }}><h3>Pemakaian aktual untuk konversi</h3><label>Aksesori dipakai<select value={costMaterial} onChange={e => setCostMaterial(e.target.value)}><option value="">Pilih aksesori</option>{accessories.materials.map(m => <option key={m.id} value={m.id}>{m.sku} · {m.name}</option>)}</select></label><label>Gudang pemakaian<select value={costLocation} onChange={e => setCostLocation(e.target.value)}><option value="">Pilih gudang</option>{accessories.locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label><label>Jumlah dipakai<input value={costQty} onChange={e => setCostQty(e.target.value)} inputMode="numeric"/></label><p>Memakai waktu WIB dan alasan pada formulir di atas. Nilai berasal dari stok aksesori.</p><button disabled={locked || !canPost}>Catat pemakaian</button></form>}
      </section>
    </>}
  </section>
}
