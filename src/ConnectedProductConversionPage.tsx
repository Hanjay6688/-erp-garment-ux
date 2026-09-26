import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { conversionObject, conversionPayload, parseConversionWorkspace, validateConversionResult, type ConversionWorkspace } from './productConversion'
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
  const [reason, setReason] = useState(''), [preview, setPreview] = useState<{ payload: Record<string, Json>; source: string; target: string; value: string | null } | null>(null)
  const [returns, setReturns] = useState<{ material_id: string; qty: string; holder: string; name: string }[]>([])
  const [returnMaterial, setReturnMaterial] = useState(''), [returnQty, setReturnQty] = useState(''), [holder, setHolder] = useState('')
  const [costDocument, setCostDocument] = useState(''), [costMaterial, setCostMaterial] = useState(''), [costQty, setCostQty] = useState(''), [costLocation, setCostLocation] = useState('')
  const [reverseId, setReverseId] = useState(''), [reverseReason, setReverseReason] = useState('')
  const canAccessories = identity.permissions.includes('warehouse.accessory.view')
  const load = useCallback(async () => {
    const seq = ++sequence.current, ticket = beginRead()
    setLoading(true); setError(''); setPreview(null)
    try {
      const [r, a] = await Promise.all([
        client.rpc('erp_get_product_conversion_workspace_v1', { p_filters: filters.current }),
        canAccessories ? client.rpc('erp_get_accessory_service_workspace_v1', { p_filters: { query: accessoryQuery, page: 1, page_size: 25 } }) : Promise.resolve(null),
      ])
      if (seq !== sequence.current || !isReadCurrent(ticket)) return false
      if (r.error) throw r.error
      if (a?.error) throw a.error
      setData(parseConversionWorkspace(r.data)); setAccessories(a ? parseAccessoryServiceWorkspace(a.data) : null)
      return finishRead(ticket)
    } catch (e) { if (seq === sequence.current && isReadCurrent(ticket)) { setData(null); setAccessories(null); setError(e instanceof Error ? e.message : normalizeClientError(e).message) }; return false }
    finally { if (seq === sequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent, canAccessories, accessoryQuery])
  useEffect(() => { void load(); return () => { sequence.current += 1 } }, [load])
  const refresh = (patch: Record<string, Json>) => { filters.current = { ...filters.current, ...patch }; void load() }
  const handlers: ProductionMutationHandlers = {
    send: e => client.rpc('erp_save_product_conversion_action_v1', { p_action: e.action, p_payload: e.payload, p_client_request_id: e.id }),
    validate: (v, e) => validateConversionResult(v, e.action, e.id, e.payload),
    retire: () => { setData(null); setPreview(null); setReverseId(''); setCostDocument(''); setReturns([]) }, reload: load,
  }
  const locked = mutation.writerLocked || mutation.busy || loading
  const canPost = identity.permissions.includes('warehouse.brand_conversion.post')
  const canReverse = identity.permissions.includes('warehouse.brand_conversion.reverse') && ['OWNER', 'ADMIN'].includes(identity.profile.role)
  const lot = data?.lots.find(l => `${l.id}:${l.location_id}` === source)
  const invalidate = () => { previewVersion.current += 1; setPreview(null) }
  const prepare = async () => {
    setError(''); setPreview(null)
    try {
      const payload = conversionPayload(lot, target, quantity, at, reason)
      if (returnMaterial || returnQty || holder) throw new Error('Tambahkan baris bongkaran atau kosongkan ketiga isian sebelum pratinjau.')
      if (returns.length) payload.expected_returns = returns.map(({ material_id, qty, holder }) => ({ material_id, qty, holder }))
      const stamp = ++sequence.current, draftVersion = previewVersion.current, ticket = beginRead(); setLoading(true)
      const r = await client.rpc('erp_get_product_conversion_workspace_v1', { p_filters: { preview: payload } })
      if (stamp !== sequence.current || !isReadCurrent(ticket)) return
      if (r.error) throw r.error
      const p = conversionObject(conversionObject(r.data).preview), cost = conversionObject(p.cost)
      if (p.source_lot_id !== payload.source_lot_id || p.target_product_id !== payload.target_product_id || p.source_revision !== payload.expected_version || p.qty_pcs !== payload.qty_pcs) throw new Error('Pratinjau tidak cocok; muat ulang.')
      if (typeof p.source_sku !== 'string' || typeof p.target_sku !== 'string') throw new Error('SKU pratinjau tidak lengkap.')
      if (finishRead(ticket) && draftVersion === previewVersion.current) setPreview({ payload, source: p.source_sku, target: p.target_sku, value: typeof cost.source_value === 'string' ? cost.source_value : null })
    } catch (e) { setError(e instanceof Error ? e.message : normalizeClientError(e).message) }
    finally { setLoading(false) }
  }
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">GUDANG · KONVERSI</div><h1>Ganti Merek / SKU</h1><p>Pilih lot fisik dan SKU tujuan dengan model serta ukuran yang sama. Jumlah barang tetap; biaya tambahan dan barang bongkaran dicatat dari sumbernya.</p></div><button disabled={mutation.busy || loading} onClick={() => void load()}>Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert">{error}</p>}
    {!data ? <p role="status">{loading ? 'Memuat stok…' : 'Stok belum diketahui.'}</p> : <>
      <section className="panel"><h2>1. Lot sumber</h2><form className="initial-import-toolbar" onSubmit={e => { e.preventDefault(); setSource(''); setTarget(''); refresh({ query: query.trim(), source_lot_id: null, page: 1 }) }}>
        <label>Cari lot / SKU<input value={query} onChange={e => setQuery(e.target.value)}/></label><button disabled={locked}>Cari lot</button></form>
        <label>Lot dan gudang<select value={source} disabled={locked} onChange={e => { const value = e.target.value; setSource(value); setTarget(''); invalidate(); refresh({ source_lot_id: value.split(':')[0] || null, page: 1, target_page: 1 }) }}>
          <option value="">Pilih lot</option>{data.lots.map(l => <option key={l.id + l.location_id} value={`${l.id}:${l.location_id}`}>{l.lot_number} · {l.sku} · {l.location_name} · {l.qty} PCS</option>)}</select></label>
        <p>{data.total} lot/lokasi · halaman {data.page} <button disabled={locked || data.page <= 1} onClick={() => refresh({ page: data.page - 1 })}>Lot sebelumnya</button><button disabled={locked || data.page * data.page_size >= data.total} onClick={() => refresh({ page: data.page + 1 })}>Lot berikutnya</button></p>
      </section>
      <section className="panel"><h2>2. Tujuan dan waktu fisik</h2>
        <form className="initial-import-toolbar" onSubmit={e => { e.preventDefault(); refresh({ target_query: targetQuery.trim(), target_page: 1 }) }}><label>Cari SKU tujuan<input value={targetQuery} onChange={e => setTargetQuery(e.target.value)}/></label><button disabled={locked || !lot}>Cari tujuan</button></form>
        <label>SKU tujuan<select value={target} disabled={locked || !lot} onChange={e => { setTarget(e.target.value); invalidate() }}><option value="">Pilih SKU</option>{data.targets.map(t => <option key={t.id} value={t.id}>{t.sku} · {t.product_name}</option>)}</select></label>
        <p>{data.targets_total} SKU cocok <button disabled={locked || data.target_page <= 1} onClick={() => refresh({ target_page: data.target_page - 1 })}>Tujuan sebelumnya</button><button disabled={locked || data.target_page * data.page_size >= data.targets_total} onClick={() => refresh({ target_page: data.target_page + 1 })}>Tujuan berikutnya</button></p>
        <label>Jumlah PCS<input inputMode="numeric" value={quantity} onChange={e => { setQuantity(e.target.value); invalidate() }}/></label>
        <label>Waktu fisik · WIB<input type="datetime-local" value={at} onChange={e => { setAt(e.target.value); invalidate() }}/></label><label>Alasan<textarea value={reason} onChange={e => { setReason(e.target.value); invalidate() }}/></label>
        {accessories && <details><summary>Bongkaran yang diharapkan kembali</summary><p>Masih di pemegang sampai penerimaan dan pemeriksaan dicatat di Aksesori. Perkiraan ini belum menambah stok.</p>
          <label>Cari aksesori<input value={accessoryQuery} onChange={e => setAccessoryQuery(e.target.value)}/></label>
          <label>Aksesori bongkaran<select value={returnMaterial} onChange={e => { setReturnMaterial(e.target.value); invalidate() }}><option value="">Tidak ada</option>{accessories.materials.map(m => <option key={m.id} value={m.id}>{m.sku} · {m.name}</option>)}</select></label>
          <label>Jumlah bongkaran<input inputMode="numeric" value={returnQty} onChange={e => { setReturnQty(e.target.value); invalidate() }}/></label><label>Pemegang<input value={holder} onChange={e => { setHolder(e.target.value); invalidate() }}/></label><button type="button" disabled={locked || !returnMaterial || !/^[1-9]\d{0,8}$/.test(returnQty) || !holder.trim() || returns.length>=100} onClick={()=>{
            const name=accessories.materials.find(m=>m.id===returnMaterial)?.name ?? returnMaterial; setReturns([...returns,{material_id:returnMaterial,qty:returnQty,holder:holder.trim(),name}]);setReturnMaterial('');setReturnQty('');setHolder('');invalidate()
          }}>Tambahkan komponen bongkaran</button>
          <ul>{returns.map((r,i)=><li key={i}>{r.name} · {r.qty} PCS · {r.holder} <button type="button" disabled={locked} onClick={()=>{setReturns(returns.filter((_,n)=>n!==i));invalidate()}}>Hapus baris {i+1}</button></li>)}</ul></details>}
        <button disabled={locked || !canPost || !lot} onClick={() => void prepare()}>Lihat pratinjau</button>
        {preview && <div role="status"><p>{preview.source} → {preview.target} · {String(preview.payload.qty_pcs)} PCS · nilai sumber {displayRupiah(preview.value)}</p><button disabled={locked || !canPost} onClick={() => void run('POST', preview.payload, null, handlers)}>Catat konversi fisik</button></div>}
      </section>
      <section className="panel initial-import-table"><h2>Riwayat konversi</h2><table><thead><tr><th>Dokumen</th><th>Sumber → tujuan</th><th>Jumlah</th><th>Nilai tujuan kini</th><th>Status</th><th/></tr></thead><tbody>{data.documents.map(d => <tr key={d.id}><td>{d.conversion_number}<br/>{formatCp6WibDateTime(d.physical_at)}</td><td>{d.source_sku} → {d.target_sku}<br/>{d.notes}</td><td>{d.qty_pcs} PCS</td><td>{displayRupiah(d.target_value)}<br/>Tambahan/pulih {displayRupiah(d.extra_cost)}</td><td>{d.status} · {d.value_state==='PROVISIONAL_RECOVERY'?'Nilai sementara: bongkaran belum selesai':'Biaya bersumber sampai saat ini'}{d.returns.map(r=><small key={r.id} style={{display:'block'}}>{r.material} · belum kembali {r.unreturned} · menunggu nilai {r.awaiting_value} · {r.holder}</small>)}</td><td>{d.status === 'POSTED' && <><button disabled={locked || !canReverse} onClick={() => { setReverseId(d.id); setReverseReason('') }}>Batalkan {d.source_sku}</button>{accessories && <button disabled={locked || !canPost} onClick={() => setCostDocument(d.id)}>Catat pemakaian aksesori</button>}</>}</td></tr>)}</tbody></table>
        <p>{data.documents_total} dokumen · halaman {data.document_page} <button disabled={locked || data.document_page <= 1} onClick={() => refresh({ document_page: data.document_page - 1 })}>Dokumen sebelumnya</button><button disabled={locked || data.document_page * data.page_size >= data.documents_total} onClick={() => refresh({ document_page: data.document_page + 1 })}>Dokumen berikutnya</button></p>
        {reverseId && <form onSubmit={e => { e.preventDefault(); void run('REVERSE', { conversion_id: reverseId, reason: reverseReason.trim() }, null, handlers) }}><p>Pastikan perubahan fisik juga dibalik. Transaksi turunan aktif harus dibatalkan dahulu.</p><label>Alasan pembatalan<input value={reverseReason} onChange={e => setReverseReason(e.target.value)}/></label><button disabled={locked || !canReverse || !reverseReason.trim()}>Konfirmasi pembatalan</button></form>}
        {costDocument && accessories && <form onSubmit={e => { e.preventDefault(); const doc = data.documents.find(d => d.id === costDocument), time = wibTimestamp(at)
          if (!doc || !time || !costMaterial || !costLocation || !/^[1-9]\d{0,8}$/.test(costQty) || !reason.trim()) { setError('Lengkapi gudang, aksesori, jumlah, waktu dan alasan pemakaian.'); return }
          void run('POST_USAGE', { conversion_id: doc.id, expected_version: doc.revision, location_id: costLocation, physical_at: time, items: [{ material_id: costMaterial, qty: costQty }], reason: reason.trim() }, null, handlers)
        }}><h3>Pemakaian aktual untuk konversi</h3><label>Aksesori dipakai<select value={costMaterial} onChange={e => setCostMaterial(e.target.value)}><option value="">Pilih aksesori</option>{accessories.materials.map(m => <option key={m.id} value={m.id}>{m.sku} · {m.name}</option>)}</select></label><label>Gudang pemakaian<select value={costLocation} onChange={e => setCostLocation(e.target.value)}><option value="">Pilih gudang</option>{accessories.locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label><label>Jumlah dipakai<input value={costQty} onChange={e => setCostQty(e.target.value)} inputMode="numeric"/></label><p>Memakai waktu WIB dan alasan pada formulir di atas. Nilai berasal dari stok aksesori.</p><button disabled={locked || !canPost}>Catat pemakaian</button></form>}
      </section>
    </>}
  </section>
}
