import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { procurementObject } from './procurementContract'
import { correctionRefusal, materialNamePayload, parseMaterialNameOutcome, parseMaterialNameWorkspace, type MaterialNameWorkspace } from './receiptCorrectionContract'
import type { Json } from './types/database.preconnect'

type Props = { materialId: string | null; onRenamed: () => Promise<boolean> }

export default function MaterialNamePanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !['OWNER', 'ADMIN'].includes(identity.profile.role)
    || !identity.permissions.includes('warehouse.material.view') || !['master.fabric.manage', 'master.accessory.manage'].some(p => identity.permissions.includes(p))) return null
  return <NameWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}:${props.materialId ?? ''}`} materialId={props.materialId} onRenamed={props.onRenamed}/>
}

function NameWorkspace({ materialId, onRenamed }: Props) {
  const { runtime } = useAuth(); if (!isConnectedRuntime(runtime)) throw Error('Sesi bahan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime]), mutation = useProductionMutation('MATERIAL_NAME')
  const { beginRead, finishRead, isReadCurrent, run, reconcile, invalidate } = mutation
  const [data, setData] = useState<MaterialNameWorkspace | null>(null), [open, setOpen] = useState(false), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const [name, setName] = useState(''), [sku, setSku] = useState(''), [reason, setReason] = useState(''), [checked, setChecked] = useState(false)
  const sequence = useRef(0)
  const load = useCallback(async () => {
    const s = ++sequence.current, ticket = beginRead()
    setLoading(true); setError('')
    try {
      if (!materialId) { setData(null); return false }
      const r = await client.rpc('erp_cp7_get_material_name_v1', { p_material: materialId })
      if (!isReadCurrent(ticket) || s !== sequence.current) return false
      if (r.error) throw r.error
      const w = parseMaterialNameWorkspace(r.data, materialId); setData(w); setName(n => n || w.material_name); setSku(c => c || w.material_sku); return finishRead(ticket)
    } catch (e) { if (isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }; return false }
    finally { if (s === sequence.current) setLoading(false) }
  }, [client, materialId, beginRead, finishRead, isReadCurrent])
  useEffect(() => { if (open && !mutation.busy) void load() }, [open, load, mutation.busy])
  const handlers: ProductionMutationHandlers = {
    send: async envelope => { const p = procurementObject(envelope.payload); const r = await client.rpc('erp_cp7_rename_material_v1', { p_payload: p.document as Json, p_request: envelope.id, p_expected: p.expected_version as string }); return { data: r.data, error: r.error ? correctionRefusal(r.error) : null } },
    validate: (r, e) => { parseMaterialNameOutcome(r, e.id, procurementObject(procurementObject(e.payload).document).material_id as string) },
    retire: () => { setName(''); setSku(''); setReason(''); setChecked(false); setData(null) },
    // The page reloads first (after the envelope is cleared), then this panel.
    reload: async () => { if (!await onRenamed()) { invalidate(); setData(null); return false }; return load() },
  }
  const built = data ? materialNamePayload(data, name, reason, sku || data.material_sku) : null, locked = mutation.writerLocked || loading
  if (!materialId && !mutation.pending && !mutation.error) return null
  return <section className="cproc-item" aria-label="Benerin nama bahan">
    <div className="cproc-heading"><strong>Benerin nama / kode bahan</strong>{materialId ? <button type="button" disabled={mutation.busy} onClick={() => setOpen(o => !o)}>{open ? 'Tutup' : 'Salah ketik nama?'}</button> : null}</div>
    <ProductionRecoveryNotice recovery={{ ...mutation, notice: mutation.notice ? 'Nama bahan sudah dibetulkan.' : '' }} onReconcile={() => reconcile(handlers)} className="cproc-review"/>
    {!open || !materialId ? null : loading && !data ? <p role="status">Memuat bahan…</p> : error ? <p role="alert">{error}</p> : data ? <form onSubmit={e => { e.preventDefault(); if (built?.payload && checked && !locked) void run('RENAME', { document: built.payload as Json, expected_version: data.row_version }, null, handlers) }}>
      <p>{data.material_sku} · {data.unit_code}. Hanya nama dan kode (SKU) yang berubah; satuan, stok, roll, dan riwayat mutasi tetap bahan yang sama. Kalau barang yang datang ternyata bahan lain, pakai Benerin penerimaan di Pembelian &amp; Penerimaan.</p>
      <fieldset disabled={locked}>
        <label>Nama yang benar<input aria-label="Nama bahan yang benar" maxLength={150} value={name} onChange={e => { setName(e.target.value); setChecked(false) }}/></label>
        <label>Kode (SKU) yang benar<input aria-label="Kode bahan yang benar" maxLength={60} value={sku} onChange={e => { setSku(e.target.value); setChecked(false) }}/></label>
        <label>Alasan<input aria-label="Alasan pembetulan nama bahan" maxLength={500} value={reason} onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
        {built?.problem && reason ? <p role="alert">{built.problem}</p> : null}
        <label className="cproc-check"><input type="checkbox" aria-label="Nama bahan sudah diperiksa" checked={checked} onChange={e => setChecked(e.target.checked)}/>Ini hanya salah ketik nama/kode; bahannya sama.</label>
        <button className="primary-btn" disabled={!built?.payload || !checked}>Simpan nama</button>
      </fieldset>
      {data.history.length ? <details><summary>Riwayat nama ({data.history.length})</summary><ul>{data.history.map(h => <li key={h.id}>{h.previous_sku !== h.corrected_sku ? `${h.previous_sku} → ${h.corrected_sku} · ` : ''}{h.previous_name !== h.corrected_name ? `${h.previous_name} → ${h.corrected_name} · ` : ''} {formatCp6WibDateTime(h.recorded_at)}{h.actor_name ? ` oleh ${h.actor_name}` : ''} · {h.reason}</li>)}</ul></details> : null}
    </form> : null}
  </section>
}
