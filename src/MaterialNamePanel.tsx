import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { procurementObject } from './procurementContract'
import { materialNamePayload, parseMaterialNameOutcome, parseMaterialNameWorkspace, type MaterialNameWorkspace } from './receiptCorrectionContract'
import type { Json } from './types/database.preconnect'

type Props = { materialId: string | null; onRenamed: () => void }

export default function MaterialNamePanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!props.materialId || !isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !['OWNER', 'ADMIN'].includes(identity.profile.role)
    || !identity.permissions.includes('warehouse.material.view') || !['master.fabric.manage', 'master.accessory.manage'].some(p => identity.permissions.includes(p))) return null
  return <NameWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}:${props.materialId}`} materialId={props.materialId} onRenamed={props.onRenamed}/>
}

function NameWorkspace({ materialId, onRenamed }: { materialId: string; onRenamed: () => void }) {
  const { runtime } = useAuth(); if (!isConnectedRuntime(runtime)) throw Error('Sesi bahan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime]), mutation = useProductionMutation('MATERIAL_NAME')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [data, setData] = useState<MaterialNameWorkspace | null>(null), [open, setOpen] = useState(false), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const [name, setName] = useState(''), [reason, setReason] = useState(''), [checked, setChecked] = useState(false)
  const sequence = useRef(0)
  const load = useCallback(async () => {
    const s = ++sequence.current, ticket = beginRead()
    setLoading(true); setError('')
    try {
      const r = await client.rpc('erp_cp7_get_material_name_v1', { p_material: materialId })
      if (!isReadCurrent(ticket) || s !== sequence.current) return false
      if (r.error) throw r.error
      const w = parseMaterialNameWorkspace(r.data, materialId); setData(w); setName(n => n || w.material_name); return finishRead(ticket)
    } catch (e) { if (isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }; return false }
    finally { if (s === sequence.current) setLoading(false) }
  }, [client, materialId, beginRead, finishRead, isReadCurrent])
  useEffect(() => { if (open && !mutation.busy) void load() }, [open, load, mutation.busy])
  const handlers: ProductionMutationHandlers = {
    send: envelope => { const p = procurementObject(envelope.payload); return client.rpc('erp_cp7_rename_material_v1', { p_payload: p.document as Json, p_request: envelope.id, p_expected: p.expected_version as string }) },
    validate: (r, e) => { parseMaterialNameOutcome(r, e.id, procurementObject(procurementObject(e.payload).document).material_id as string) },
    retire: () => { setName(''); setReason(''); setChecked(false); void load(); onRenamed() },
    reload: load,
  }
  const built = data ? materialNamePayload(data, name, reason) : null, locked = mutation.writerLocked || loading
  return <section className="cproc-item" aria-label="Benerin nama bahan">
    <div className="cproc-heading"><strong>Benerin nama bahan</strong><button type="button" disabled={mutation.busy} onClick={() => setOpen(o => !o)}>{open ? 'Tutup' : 'Salah ketik nama?'}</button></div>
    <ProductionRecoveryNotice recovery={{ ...mutation, notice: mutation.notice ? 'Nama bahan sudah dibetulkan.' : '' }} onReconcile={() => reconcile(handlers)} className="cproc-review"/>
    {!open ? null : loading && !data ? <p role="status">Memuat bahan…</p> : error ? <p role="alert">{error}</p> : data ? <form onSubmit={e => { e.preventDefault(); if (built?.payload && checked && !locked) void run('RENAME', { document: built.payload as Json, expected_version: data.row_version }, null, handlers) }}>
      <p>{data.material_sku} · {data.unit_code}. Hanya nama yang berubah; kode, satuan, stok, roll, dan riwayat mutasi tetap bahan yang sama. Kalau barang yang datang ternyata bahan lain, pakai Benerin penerimaan di Pembelian &amp; Penerimaan.</p>
      <fieldset disabled={locked}>
        <label>Nama yang benar<input aria-label="Nama bahan yang benar" maxLength={150} value={name} onChange={e => { setName(e.target.value); setChecked(false) }}/></label>
        <label>Alasan<input aria-label="Alasan pembetulan nama bahan" maxLength={500} value={reason} onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
        {built?.problem && (name || reason) ? <p role="alert">{built.problem}</p> : null}
        <label className="cproc-check"><input type="checkbox" aria-label="Nama bahan sudah diperiksa" checked={checked} onChange={e => setChecked(e.target.checked)}/>Ini hanya salah ketik nama; bahannya sama.</label>
        <button className="primary-btn" disabled={!built?.payload || !checked}>Simpan nama</button>
      </fieldset>
      {data.history.length ? <details><summary>Riwayat nama ({data.history.length})</summary><ul>{data.history.map(h => <li key={h.id}>{h.previous_name} → {h.corrected_name} · {formatCp6WibDateTime(h.recorded_at)}{h.actor_name ? ` oleh ${h.actor_name}` : ''} · {h.reason}</li>)}</ul></details> : null}
    </form> : null}
  </section>
}
