import { useEffect, useMemo, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { parseConversionWorkspace, type ConversionTarget } from './productConversion'
export type BeTarget = { enabled: boolean; target: string; process: string; priceStatus: 'KNOWN' | 'UNKNOWN'; ready: boolean }
export const emptyBeTarget: BeTarget = { enabled: false, target: '', process: '', priceStatus: 'KNOWN', ready: false }
export default function BeReworkTargetFields({ source, laundry, locked, value, onChange }: {
  source: string | null; laundry: boolean; locked: boolean; value: BeTarget; onChange: (v: BeTarget) => void
}) {
  const { runtime, identity } = useAuth()
  const client = useMemo(() => isConnectedRuntime(runtime) ? getUatSupabaseClient(runtime) : null, [runtime])
  const allowed = identity.status === 'AUTHORIZED' && identity.permissions.includes('warehouse.brand_conversion.post') && identity.permissions.includes('warehouse.brand_conversion.view')
  const [query, setQuery] = useState(''), [search, setSearch] = useState(''), [page, setPage] = useState(1)
  const [targets, setTargets] = useState<ConversionTarget[]>([]), [total, setTotal] = useState(0), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [processes, setProcesses] = useState<{ id: string; name: string }[]>([])
  useEffect(() => {
    let current = true
    if (!client || !source || !allowed || !value.enabled) return
    setBusy(true); setError('')
    void Promise.all([
      client.rpc('erp_get_product_conversion_workspace_v1', { p_filters: { source_product_id: source, target_query: search, target_page: page } }),
      laundry ? client.rpc('erp_get_laundry_bd_workspace_v1', { p_filters: {} }) : Promise.resolve(null),
    ]).then(([r, l]) => {
      if (!current) return
      if (r.error) throw r.error
      if (l?.error) throw l.error
      const ws = parseConversionWorkspace(r.data); setTargets(ws.targets); setTotal(ws.targets_total)
      if (l) {
        const raw = l.data as { processes?: { id: unknown; name: unknown }[] }
        if (!Array.isArray(raw?.processes) || raw.processes.some(p => typeof p.id !== 'string' || typeof p.name !== 'string')) throw new Error('Daftar proses celup tidak lengkap.')
        setProcesses(raw.processes as { id: string; name: string }[])
      }
    }).catch(e => { if (current) { setTargets([]); setProcesses([]); setError(e instanceof Error ? e.message : 'Pilihan tujuan belum terbaca.') } }).finally(() => { if (current) setBusy(false) })
    return () => { current = false }
  }, [client, source, search, page, allowed, value.enabled, laundry])
  const change = (patch: Partial<BeTarget>) => {
    const next = { ...value, ...patch }; next.ready = Boolean(next.target && (!laundry || next.process)); onChange(next)
  }
  return <fieldset disabled={locked || !allowed || !source}><legend>SKU hasil</legend>
    <label><input type="checkbox" checked={value.enabled} onChange={e => onChange({ ...emptyBeTarget, enabled: e.target.checked })}/>Hasil GOOD menjadi SKU lain</label>
    {!allowed && <p>Hak konversi SKU diperlukan untuk pilihan ini.</p>}
    {value.enabled && <><p>{laundry ? 'Celup ulang ke SKU baru adalah jasa berbayar tersendiri. Tarif memakai proses pada waktu kirim; tanpa tarif harus ditandai belum diketahui.' : 'Model dan ukuran tetap. Hasil GOOD dipindahkan ke SKU tujuan saat seluruh hasil diposting.'}</p>
      <label>Cari SKU hasil<input value={query} onChange={e => setQuery(e.target.value)}/></label><button type="button" disabled={busy} onClick={() => { setSearch(query); setPage(1); change({ target: '' }) }}>Cari SKU hasil</button>
      {error && <p role="alert">{error}</p>}
      <label>SKU hasil baru<select value={value.target} disabled={busy || Boolean(error)} onChange={e => change({ target: e.target.value })}><option value="">Pilih SKU</option>{targets.map(t => <option key={t.id} value={t.id}>{t.sku} · {t.product_name}</option>)}</select></label>
      <p>{total} pilihan <button type="button" disabled={busy || page <= 1} onClick={() => { setPage(page - 1); change({ target: '' }) }}>SKU sebelumnya</button><button type="button" disabled={busy || page * 25 >= total} onClick={() => { setPage(page + 1); change({ target: '' }) }}>SKU berikutnya</button></p>
      {laundry && <><label>Proses celup berbayar<select value={value.process} disabled={busy || Boolean(error)} onChange={e => change({ process: e.target.value })}><option value="">Pilih proses</option>{processes.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Harga jasa<select value={value.priceStatus} onChange={e => change({ priceStatus: e.target.value as BeTarget['priceStatus'] })}><option value="KNOWN">Sudah ada tarif vendor/proses</option><option value="UNKNOWN">Belum diketahui — perlu pengisian owner</option></select></label></>}
    </>}
  </fieldset>
}
