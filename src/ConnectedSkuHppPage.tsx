import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation } from './useProductionMutation'
import { cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { parseSkuHpp, skuMoney, type SkuHppWorkspace } from './skuHpp'
import './initial-import.css'

export default function ConnectedSkuHppPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !identity.permissions.includes('finance.hpp.view')) return <section className="panel" role="alert">Hak lihat HPP diperlukan.</section>
  return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace() {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const { beginRead, finishRead, isReadCurrent, blockReason } = useProductionMutation('SKU')
  const [data, setData] = useState<SkuHppWorkspace | null>(null), [error, setError] = useState('')
  const [query, setQuery] = useState(''), [date, setDate] = useState(''), [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState(''), filters = useRef({ query: '', at: '', page: 1 }), sequence = useRef(0)
  const load = useCallback(async () => {
    const s = ++sequence.current, ticket = beginRead(), f = { ...filters.current }
    setBusy(true); setData(null); setError('')
    try {
      const result = await client.rpc('erp_get_sku_hpp_v1', { p_filters: { query: f.query, page: f.page, ...(f.at ? { at: f.at } : {}) } })
      if (s !== sequence.current || !isReadCurrent(ticket)) return
      if (result.error) throw result.error
      const w = parseSkuHpp(result.data)
      if (w.page !== f.page || (f.at && Date.parse(w.at) !== Date.parse(f.at))) throw new Error('Tanggal atau halaman laporan tidak cocok.')
      setData(w); finishRead(ticket)
    } catch (e) { if (s === sequence.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message) }
    finally { if (s === sequence.current) setBusy(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load(); return () => { ++sequence.current } }, [load])
  const active = data?.groups.find(g => g.group_key === selected) ?? data?.groups[0]
  return <section className="initial-import">
    <header className="panel"><h1>HPP per SKU</h1><p>Nilai sisa stok seluruh ukuran ÷ jumlah PCS tersisa. Penjualan tetap memakai biaya lot asal.</p></header>
    <form className="panel initial-import-toolbar" onSubmit={e => { e.preventDefault(); const at = date ? cp6WibPhysicalTimeToIso(date) : ''; if (at === null) { setError('Tanggal WIB tidak valid.'); return } filters.current = { query: query.trim(), at, page: 1 }; void load() }}>
      <label>Cari SKU atau merek<input value={query} onChange={e => setQuery(e.target.value)} maxLength={120}/></label>
      <label>Posisi pada waktu WIB<input type="datetime-local" value={date} onChange={e => setDate(e.target.value)}/></label>
      <button disabled={busy}>Tampilkan</button><span>Kosongkan waktu untuk posisi sekarang.</span>
    </form>
    {(error || blockReason) && <p role="alert">{error || blockReason}</p>}
    {busy && <p role="status">Memuat stok dan biaya…</p>}
    {data && <><p>Posisi {formatCp6WibDateTime(data.at)}. Biaya memakai versi yang sudah tercatat pada waktu itu; status kelengkapan diperiksa saat ini.</p>
      <div className="panel"><table><thead><tr><th>SKU</th><th>Stok PCS</th><th>Nilai stok</th><th>HPP / PCS</th><th>Status biaya</th></tr></thead><tbody>{data.groups.map(g => <tr key={g.group_key}><td><button onClick={() => setSelected(g.group_key)}>{g.brand_name} · {g.sku}</button></td><td>{g.qty}</td><td>{skuMoney(g.value)}</td><td>{skuMoney(g.hpp_per_pcs)}</td><td>{g.provisional ? 'Belum lengkap' : 'Tercatat'}</td></tr>)}</tbody></table>
      {data.groups.length === 0 && <p>Tidak ada stok SKU yang cocok.</p>}
      <button disabled={busy || data.page <= 1} onClick={() => { filters.current.page--; void load() }}>Sebelumnya</button><span> Halaman {data.page} · {data.total} SKU </span><button disabled={busy || data.page * 50 >= data.total} onClick={() => { filters.current.page++; void load() }}>Berikutnya</button></div>
      {active && <section className="panel"><h2>Rincian {active.sku}</h2><table><thead><tr><th>Ukuran</th><th>Lot</th><th>Grade</th><th>PCS tersisa</th><th>Nilai sisa</th></tr></thead><tbody>{active.lots.map(l => <tr key={`${l.lot_id}:${l.product_id}:${l.location_id}:${l.grade}`}><td>{l.size}</td><td>{l.lot_number}</td><td>{l.grade}</td><td>{l.qty}</td><td>{skuMoney(l.value)}{l.provisional ? ' · sementara' : ''}</td></tr>)}</tbody></table></section>}
    </>}
  </section>
}
