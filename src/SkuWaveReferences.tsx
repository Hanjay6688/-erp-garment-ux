import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { parseSkuMaster, type SkuGroup } from './skuMaster'
import { skuObject } from './skuHpp'
type Wave = { id: string; number: string; revision: string; can_bind: boolean; sizes: { id: string; name: string; sku_id: string | null; sku: string | null }[] }
export default function SkuWaveReferences({ waveId, modelId }: { waveId: string; modelId: string }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !identity.permissions.includes('master.product.view')) return null
  return <Editor key={`${waveId}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} waveId={waveId} modelId={modelId}/>
}
function Editor({ waveId, modelId }: { waveId: string; modelId: string }) {
  const { runtime } = useAuth(); if (!isConnectedRuntime(runtime)) throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('SKU'), { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const [wave, setWave] = useState<Wave | null>(null), [groups, setGroups] = useState<SkuGroup[]>([])
  const [choices, setChoices] = useState<Record<string,string>>({}), [query, setQuery] = useState(''), requested = useRef('')
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), generation = useRef(0)
  const load = useCallback(async () => {
    const seq = ++generation.current, ticket = beginRead(); setBusy(true); setError(''); setWave(null)
    try {
      const result = await client.rpc('erp_get_sku_workspace_v1', { p_filters: { wave_id: waveId, query: requested.current } })
      if (seq !== generation.current || !isReadCurrent(ticket)) return false
      if (result.error) throw result.error
      const w = skuObject(skuObject(result.data).wave)
      if (w.id !== waveId || typeof w.number !== 'string' || typeof w.revision !== 'string' || !/^[a-f0-9]{32}$/.test(w.revision) || !Array.isArray(w.sizes) || typeof w.can_bind !== 'boolean') throw new Error('Referensi wave tidak valid.')
      for (const s of w.sizes) { const row = skuObject(s); if (typeof row.id !== 'string' || typeof row.name !== 'string' || !(row.sku_id === null || typeof row.sku_id === 'string')) throw new Error('Ukuran wave tidak lengkap.') }
      const next = w as Wave; setWave(next); setGroups(parseSkuMaster(result.data).groups.filter(g => g.model_id === modelId && Date.parse(g.effective_from) <= Date.now()))
      setChoices(Object.fromEntries(next.sizes.map(s => [s.id,s.sku_id ?? '']))); return finishRead(ticket)
    } catch (e) { if (seq === generation.current && isReadCurrent(ticket)) setError(normalizeClientError(e).message); return false }
    finally { if (seq === generation.current) setBusy(false) }
  }, [client, waveId, modelId, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load(); return () => { ++generation.current } }, [load])
  const handlers: ProductionMutationHandlers = {
    send: e => client.rpc('erp_save_sku_action_v1', { p_action: e.action, p_payload: e.payload, p_client_request_id: e.id }),
    validate: (v,e) => { const r=skuObject(v), p=skuObject(e.payload); if (r.action !== 'BIND_WAVE' || r.request_id !== e.id || r.status !== 'SAVED' || r.cutting_group_id !== p.cutting_group_id || typeof r.revision !== 'string') throw new Error('Respons referensi SKU tidak cocok.') },
    retire: () => setWave(null), reload: load,
  }
  const locked = busy || recovery.writerLocked
  const save = (clear: boolean) => { if (wave) void run('BIND_WAVE', { cutting_group_id: wave.id, expected_version: wave.revision, references: clear ? [] : wave.sizes.map(s => ({ size_id:s.id, sku_id:choices[s.id] })) }, null, handlers) }
  return <section className="ccut-card wide"><h3>Referensi tarif SKU wave</h3><p>Opsional sebelum pekerjaan dimulai. Satu wave boleh memuat beberapa SKU; identitas barang jadi tetap dipilih saat QC.</p>
    <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>{error && <p role="alert">{error}</p>}
    <label>Cari kode SKU referensi<input value={query} onChange={e => setQuery(e.target.value)}/></label><button type="button" disabled={locked} onClick={() => { requested.current=query.trim(); void load() }}>Cari referensi</button><p>Maksimal 50 hasil; persempit kode pencarian jika SKU belum terlihat. Pencarian memuat ulang pilihan tersimpan.</p>
    {wave && <fieldset disabled={locked || !wave.can_bind}><legend>{wave.number}</legend>{wave.sizes.map(s => <label key={s.id}>SKU untuk ukuran {s.name}<select value={choices[s.id] ?? ''} onChange={e => setChoices({ ...choices,[s.id]:e.target.value })}><option value="">Pilih SKU</option>{s.sku_id && !groups.some(g=>g.id===s.sku_id) && <option value={s.sku_id}>{s.sku} (tersimpan)</option>}{groups.filter(g => g.members.some(m=>m.size_id===s.id)).map(g=><option key={g.id} value={g.id}>{g.brand_name} · {g.sku} · {g.color_name}</option>)}</select></label>)}
      <button type="button" disabled={!wave.sizes.length || !wave.sizes.every(s=>choices[s.id])} onClick={()=>save(false)}>Simpan referensi tarif wave</button><button type="button" onClick={()=>save(true)}>Tanpa referensi SKU</button>
    </fieldset>}
  </section>
}
