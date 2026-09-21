import { isConnectedRuntime } from './config/runtime'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, Database, FilePenLine, LoaderCircle, RefreshCw, Search, Trash2 } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import CuttingPatternPicker from './CuttingPatternPicker'
import type { CuttingPatternChoice } from './CuttingPatternPicker'
import {
  parseCuttingSaveResult,
  parseCuttingWorkspace,
  type CuttingDraft,
  type CuttingWorkspace,
  type CuttingWorkspaceRoll,
} from './cuttingPersistence'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { ProductionEnvelope } from './productionRecovery'
import { parseQuantityInput, requireQuantityInput } from './quantityInput'
import './connected-cutting.css'

type SelectedRoll = {
  roll: CuttingWorkspaceRoll
  issued: number
  consumed: string
}

type SizeSlot = { key: string; sizeId: string; sizeCode: string }

function datetimeLocal(value: Date | string) {
  const date = value instanceof Date ? value : new Date(value)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

const numeric = (raw: string) => parseQuantityInput(raw, 'MEASURE') ?? Number.NaN
const count = (raw: string) => parseQuantityInput(raw) ?? Number.NaN
const display = (value: number, digits = 0) => Number.isFinite(value) ? value.toFixed(digits) : '—'

function validateCuttingCommit(data: unknown, envelope: ProductionEnvelope) {
  const payload = envelope.payload as Record<string, unknown>
  if (envelope.action === 'DELETE') {
    const result = data as Record<string, unknown> | null
    if (result?.status !== 'DELETED' || result.cutting_group_id !== payload.id) throw new Error('Respons delete tidak cocok')
    return
  }
  const result = parseCuttingSaveResult(data)
  if (payload.id && payload.id !== result.cutting_group_id || payload.pattern_id !== result.pattern_id
    || payload.source_location_id !== result.source_location_id || result.material_issue_posted !== (envelope.action === 'POST')) throw new Error('Respons Potongan tidak cocok')
}

function rollFromDraft(draft: CuttingDraft, rollId: string): CuttingWorkspaceRoll | null {
  const row = draft.rolls.find((candidate) => candidate.roll_id === rollId)
  if (!row) return null
  return {
    id: row.roll_id, roll_number: row.roll_number, material_id: row.material_id,
    material_sku: row.material_sku, material_name: row.material_name, unit_code: row.unit_code,
    supplier_id: row.supplier_id, supplier_code: null, supplier_name: row.supplier_name,
    original_qty: row.original_qty, available_qty: row.qty_issued, status: 'DRAFT_SELECTED', received_at: null,
  }
}

function sizesForOrder(workspace: CuttingWorkspace | null, orderId: string) {
  const modelId = workspace?.orders.find((order) => order.id === orderId)?.model_id
  return modelId ? workspace?.sizes.filter((size) => size.model_ids.includes(modelId)) ?? [] : []
}

export default function ConnectedCuttingPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ConnectedCuttingPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const canCreate = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.create')
  const canEdit = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.edit_draft')
  const canPost = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.post')
  const [workspace, setWorkspace] = useState<CuttingWorkspace | null>(null)
  const [locationId, setLocationId] = useState('')
  const [rollQuery, setRollQuery] = useState('')
  const [rollOffset, setRollOffset] = useState(0)
  const [orderId, setOrderId] = useState('')
  const [pattern, setPattern] = useState<CuttingPatternChoice | null>(null)
  const [cutAt, setCutAt] = useState(() => datetimeLocal(new Date()))
  const [notes, setNotes] = useState('')
  const [draftId, setDraftId] = useState<string | null>(null)
  const [draftVersion, setDraftVersion] = useState<number | null>(null)
  const [selectedRolls, setSelectedRolls] = useState<Record<string, SelectedRoll>>({})
  const [slots, setSlots] = useState<SizeSlot[]>([])
  const [yields, setYields] = useState<Record<string, Record<string, string>>>({})
  const [loading, setLoading] = useState(true)
  const mutation = useProductionMutation('CUTTING')
  const { beginRead, finishRead, run, reconcile } = mutation
  const saving = mutation.busy
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const loadRequestRef = useRef(0)
  const viewRef = useRef({ locationId, rollQuery })
  viewRef.current = { locationId, rollQuery }

  const load = useCallback(async (nextLocation: string | null, nextQuery = rollQuery, nextOffset = rollOffset) => {
    const ticket = beginRead()
    const requestId = ++loadRequestRef.current
    setLoading(true)
    setError('')
    try {
      const { data, error: loadError } = await client.rpc('erp_get_cutting_workspace_v1', {
        p_roll_query: nextQuery.trim() || null,
        p_location_id: nextLocation || null,
        p_limit: 100,
        p_offset: nextOffset,
      })
      if (requestId !== loadRequestRef.current) return false
      if (loadError) {
        setError(normalizeClientError(loadError).message)
        return false
      }
      try {
        const parsed = parseCuttingWorkspace(data)
        setWorkspace(parsed)
        setRollOffset(parsed.offset)
        if (!nextLocation && parsed.locations[0]) setLocationId(parsed.locations[0].id)
        const nextOrderId = orderId || parsed.orders[0]?.id || ''
        if (!orderId && nextOrderId) setOrderId(nextOrderId)
        const initialSizes = sizesForOrder(parsed, nextOrderId)
        if (slots.length === 0 && initialSizes.length > 0) {
          setSlots(initialSizes.slice(0, 3).map((size) => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
        }
        return finishRead(ticket)
      } catch (parseError) {
        setError(parseError instanceof Error ? parseError.message : String(parseError))
        return false
      }
    } catch (loadFailure) {
      if (requestId === loadRequestRef.current) setError(normalizeClientError(loadFailure).message)
      return false
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false)
    }
  }, [beginRead, finishRead, client, orderId, rollOffset, rollQuery, slots.length])

  useEffect(() => { void load(null, '', 0); return () => { loadRequestRef.current += 1 } }, [mutation.scope]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (locationId) { setRollOffset(0); void load(locationId, rollQuery, 0) } }, [locationId]) // eslint-disable-line react-hooks/exhaustive-deps

  const selected = Object.values(selectedRolls)
  const selectedIds = new Set(Object.keys(selectedRolls))
  const availableSizes = sizesForOrder(workspace, orderId)
  const totalIssued = selected.reduce((sum, item) => sum + item.issued, 0)
  const totalConsumed = selected.reduce((sum, item) => sum + numeric(item.consumed), 0)
  const totalRemaining = selected.reduce((sum, item) => sum + item.issued - numeric(item.consumed), 0)
  const totalPieces = selected.reduce((sum, item) => sum + slots.reduce((rollSum, slot) =>
    rollSum + count(yields[item.roll.id]?.[slot.key] ?? '0'), 0), 0)
  const cutAtValid = cutAt.length > 0 && Number.isFinite(new Date(cutAt).getTime())
  const formValid = Boolean(orderId && locationId && pattern && cutAtValid && slots.length > 0 && selected.length > 0)
    && selected.every((item) => numeric(item.consumed) > 0 && numeric(item.consumed) <= item.issued)
    && selected.every((item) => slots.every((slot) => parseQuantityInput(yields[item.roll.id]?.[slot.key] ?? '0') !== null)
      && slots.some((slot) => count(yields[item.roll.id]?.[slot.key] ?? '0') > 0))

  const resetForm = () => {
    setDraftId(null)
    setDraftVersion(null)
    setPattern(null)
    setNotes('')
    setCutAt(datetimeLocal(new Date()))
    setSelectedRolls({})
    setYields({})
    setNotice('Form baru siap. Belum ada data backend yang ditulis.')
  }

  const changeOrder = (nextOrderId: string) => {
    setOrderId(nextOrderId)
    const nextSizes = sizesForOrder(workspace, nextOrderId)
    setSlots(nextSizes.slice(0, 3).map((size) => ({
      key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code,
    })))
    setSelectedRolls({})
    setYields({})
    if (selected.length > 0) setNotice('Pilihan roll dikosongkan karena Production Order berubah.')
  }

  const toggleSize = (sizeId: string, sizeCode: string) => {
    const existing = slots.find((slot) => slot.sizeId === sizeId)
    if (existing) {
      if (slots.length === 1) return
      setSlots((current) => current.filter((slot) => slot.key !== existing.key))
      setYields((current) => Object.fromEntries(Object.entries(current).map(([rollId, values]) => {
        const next = { ...values }
        delete next[existing.key]
        return [rollId, next]
      })))
      return
    }
    setSlots((current) => [...current, { key: globalThis.crypto.randomUUID(), sizeId, sizeCode }])
  }

  const toggleRoll = (roll: CuttingWorkspaceRoll) => {
    if (selectedIds.has(roll.id)) {
      setSelectedRolls((current) => { const next = { ...current }; delete next[roll.id]; return next })
      setYields((current) => { const next = { ...current }; delete next[roll.id]; return next })
      return
    }
    setSelectedRolls((current) => ({ ...current, [roll.id]: { roll, issued: roll.available_qty, consumed: '' } }))
    setYields((current) => ({ ...current, [roll.id]: Object.fromEntries(slots.map((slot) => [slot.key, '0'])) }))
  }

  const resumeDraft = (draft: CuttingDraft) => {
    const nextSlots = draft.size_slots.map((slot) => ({
      key: `slot-${slot.slot_no}-${slot.size_id}`, sizeId: slot.size_id, sizeCode: slot.size_code,
    }))
    const nextRolls: Record<string, SelectedRoll> = {}
    const nextYields: Record<string, Record<string, string>> = {}
    draft.rolls.forEach((draftRoll) => {
      const roll = workspace?.rolls.find((candidate) => candidate.id === draftRoll.roll_id)
        ?? rollFromDraft(draft, draftRoll.roll_id)
      if (!roll) return
      nextRolls[roll.id] = { roll, issued: draftRoll.qty_issued, consumed: String(draftRoll.qty_consumed) }
      nextYields[roll.id] = Object.fromEntries(nextSlots.map((slot, index) => [
        slot.key,
        String(draftRoll.yields.find((candidate) => candidate.slot_no === draft.size_slots[index].slot_no)?.qty_pcs ?? 0),
      ]))
    })
    setDraftId(draft.cutting_group_id)
    setDraftVersion(draft.row_version)
    setOrderId(draft.po_id)
    setLocationId(draft.source_location_id ?? workspace?.locations[0]?.id ?? '')
    setPattern(draft.pattern_id && draft.pattern_code && draft.pattern_revision && draft.pattern_name ? {
      id: draft.pattern_id, code: draft.pattern_code, revision: draft.pattern_revision, name: draft.pattern_name,
    } : null)
    setCutAt(datetimeLocal(draft.cut_at))
    setNotes(draft.notes ?? '')
    setSlots(nextSlots.length > 0 ? nextSlots : sizesForOrder(workspace, draft.po_id).slice(0, 3).map((size) => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
    setSelectedRolls(nextRolls)
    setYields(nextYields)
    setNotice(`${draft.group_number} dimuat dari backend${draft.editable ? '.' : ' · read-only karena lifecycle downstream.'}`)
    setError('')
  }

  const payload = (action: 'SAVE_DRAFT' | 'POST') => ({
    ...(draftId ? { id: draftId } : {}),
    action,
    po_id: orderId,
    pattern_id: pattern?.id,
    source_location_id: locationId,
    cut_at: new Date(cutAt).toISOString(),
    notes: notes.trim() || null,
    change_reason: action === 'POST' ? 'Posting Potongan dari workspace connected' : 'Simpan draft Potongan dari workspace connected',
    size_slots: slots.map((slot, index) => ({ slot_no: index + 1, size_id: slot.sizeId, drawing_no: 1 })),
    rolls: selected.map((item) => ({
      roll_id: item.roll.id,
      qty_issued: item.issued,
      qty_consumed: requireQuantityInput(item.consumed, 'MEASURE', item.issued),
      qty_reported_remaining: Number((item.issued - requireQuantityInput(item.consumed, 'MEASURE', item.issued)).toFixed(6)),
      yields: slots.map((slot, index) => ({
        slot_no: index + 1,
        qty_pcs: requireQuantityInput(yields[item.roll.id]?.[slot.key] ?? '0'),
      })),
    })),
  })

  const sendExact = (envelope: ProductionEnvelope) => client.rpc('erp_save_cutting_group_before_sewing_v2', {
    p_payload: envelope.payload, p_client_request_id: envelope.id, p_expected_version: envelope.expectedVersion,
  })
  const reload = () => {
    const view = viewRef.current
    return load(view.locationId || null, view.rollQuery, 0)
  }
  const retire = (data: unknown, envelope: ProductionEnvelope) => {
    resetForm()
    if (envelope.action === 'DELETE') setNotice('Draft Potongan sudah dihapus.')
    else {
      const result = parseCuttingSaveResult(data)
      setNotice(`${result.group_number} ${result.material_issue_posted ? 'terposting' : 'tersimpan sebagai draft'}. Form lama ditutup; muat draft terbaru untuk melanjutkan.`)
    }
  }
  const handlers = { send: sendExact, validate: validateCuttingCommit, retire, reload }
  const save = async (action: 'SAVE_DRAFT' | 'POST') => {
    if (!formValid || mutation.writerLocked || (draftId ? !canEdit : !canCreate) || (action === 'POST' && !canPost)) return
    setError(''); setNotice('')
    await run(action, payload(action), draftVersion, handlers)
  }
  const removeDraft = async () => {
    if (!draftId || draftVersion === null || !canEdit || mutation.writerLocked) return
    if (!globalThis.confirm('Hapus draft Potongan ini? Hanya draft yang belum diposting yang dapat dihapus.')) return
    setError(''); setNotice('')
    await run('DELETE', { id: draftId, action: 'DELETE', change_reason: 'Hapus draft Potongan dari workspace connected' }, draftVersion, handlers)
  }

  return <section className="connected-cutting-page">
    <header className="ccut-hero"><div><span>PRODUKSI · CUTTING CONNECTED</span><h1>Buat Potongan</h1><p>Satu transaksi atomik mengikat Pola, roll fisik, yard keluar/terpakai/sisa, hasil per size, stok, HPP, dan jurnal.</p></div><button type="button" onClick={() => void load(locationId || null, rollQuery)}><RefreshCw/> Refetch</button></header>
    <div className="ccut-truth"><Database/><strong>ERP ENTENG UAT · RPC CONNECTED</strong><span>Tidak ada fixture atau direct-table write pada mode ini.</span></div>
    {error && <div className="ccut-message error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}>Tutup</button></div>}
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="ccut-message error"/>
    {notice && <div className="ccut-message success" role="status"><Check/><span>{notice}</span></div>}

    <div className="ccut-layout">
      <aside className="ccut-drafts"><header><div><span>DRAFT BACKEND</span><strong>{workspace?.drafts.length ?? 0} Potongan</strong></div><button disabled={mutation.writerLocked} onClick={resetForm}>Baru</button></header>{workspace?.drafts.map((draft) => <button key={draft.cutting_group_id} className={draftId === draft.cutting_group_id ? 'active' : ''} disabled={mutation.writerLocked} onClick={() => resumeDraft(draft)}><FilePenLine/><span><strong>{draft.group_number}</strong><small>{draft.po_number} · {draft.pattern_code ? `${draft.pattern_code} ${draft.pattern_revision}` : 'Pola belum diikat'}</small></span><em>v{draft.row_version}</em></button>)}{!loading && workspace?.drafts.length === 0 && <p>Belum ada draft Potongan.</p>}</aside>

      <main className="ccut-form">
        <section className="ccut-card"><header><span>01 · IDENTITAS KANONIK</span><strong>PO, Pola, waktu, dan gudang sumber</strong></header><div className="ccut-fields"><label>Production Order<select value={orderId} disabled={draftId !== null} onChange={(event) => changeOrder(event.target.value)}><option value="">Pilih PO…</option>{workspace?.orders.map((order) => <option value={order.id} key={order.id}>{order.po_number} · {order.model_code} · {order.model_name}</option>)}</select></label><label>Waktu potong<input type="datetime-local" value={cutAt} max={datetimeLocal(new Date())} onChange={(event) => setCutAt(event.target.value)}/></label><label>Gudang bahan<select value={locationId} onChange={(event) => { setLocationId(event.target.value); setRollOffset(0); setSelectedRolls({}); setYields({}); if (selected.length > 0) setNotice('Pilihan roll dikosongkan karena gudang bahan berubah.') }}><option value="">Pilih gudang…</option>{workspace?.locations.map((location) => <option value={location.id} key={location.id}>{location.code} · {location.name}</option>)}</select></label><label>Catatan<input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Opsional"/></label></div><CuttingPatternPicker value={pattern} onChange={setPattern}/></section>

        <section className="ccut-card"><header><span>02 · UKURAN AKTIF</span><strong>Kolom hasil potong sesuai model PO</strong></header><div className="ccut-size-list">{availableSizes.map((size) => <button className={slots.some((slot) => slot.sizeId === size.id) ? 'active' : ''} onClick={() => toggleSize(size.id, size.code)} key={size.id}>{size.code}</button>)}{orderId && availableSizes.length === 0 ? <span>Model PO ini belum memiliki ukuran aktif.</span> : null}</div></section>

        <section className="ccut-card"><header><span>03 · ROLL FISIK</span><strong>{workspace?.roll_total ?? 0} tersedia di lokasi</strong></header><div className="ccut-search"><Search/><input value={rollQuery} onChange={(event) => setRollQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { setRollOffset(0); void load(locationId || null, rollQuery, 0) } }} placeholder="Nomor roll, bahan, supplier…"/><button onClick={() => { setRollOffset(0); void load(locationId || null, rollQuery, 0) }}>Cari</button></div><div className="ccut-roll-catalog">{loading ? <span><LoaderCircle className="spin"/> Memuat roll…</span> : workspace?.rolls.map((roll) => <button className={selectedIds.has(roll.id) ? 'active' : ''} onClick={() => toggleRoll(roll)} key={roll.id}><span><strong>{roll.roll_number}</strong><small>{roll.material_sku} · {roll.material_name}</small></span><em>{roll.available_qty} {roll.unit_code}</em></button>)}</div><footer className="ccut-pagination"><span>{workspace?.roll_total ? `${rollOffset + 1}–${rollOffset + workspace.rolls.length} dari ${workspace.roll_total}` : '0 roll'}</span><div><button disabled={loading || rollOffset === 0} onClick={() => void load(locationId || null, rollQuery, Math.max(0, rollOffset - 100))}>Sebelumnya</button><button disabled={loading || !workspace || rollOffset + workspace.rolls.length >= workspace.roll_total} onClick={() => void load(locationId || null, rollQuery, rollOffset + 100)}>Berikutnya</button></div></footer></section>

        <section className="ccut-card wide"><header><span>04 · HASIL PER ROLL & SIZE</span><strong>Angka sumber direkonsiliasi backend</strong></header>{selected.length === 0 ? <div className="ccut-empty">Pilih minimal satu roll dari gudang bahan.</div> : <div className="ccut-table-wrap"><table><thead><tr><th>Roll</th><th>Keluar</th><th>Terpakai</th><th>Sisa</th>{slots.map((slot) => <th key={slot.key}>Size {slot.sizeCode}</th>)}<th>Total pcs</th></tr></thead><tbody>{selected.map((item) => { const consumed = numeric(item.consumed); const rowPieces = slots.reduce((sum, slot) => sum + count(yields[item.roll.id]?.[slot.key] ?? '0'), 0); return <tr key={item.roll.id}><th><strong>{item.roll.roll_number}</strong><small>{item.roll.material_name}</small></th><td>{item.issued} {item.roll.unit_code}</td><td><input aria-label={`${item.roll.roll_number} terpakai`} aria-invalid={parseQuantityInput(item.consumed, 'MEASURE', item.issued) === null} inputMode="decimal" value={item.consumed} onChange={(event) => setSelectedRolls((current) => ({ ...current, [item.roll.id]: { ...current[item.roll.id], consumed: event.target.value } }))}/></td><td className={consumed > item.issued ? 'bad' : ''}>{display(item.issued - consumed, 2)}</td>{slots.map((slot) => <td key={slot.key}><input aria-label={`${item.roll.roll_number} Size ${slot.sizeCode}`} aria-invalid={parseQuantityInput(yields[item.roll.id]?.[slot.key] ?? '0') === null} inputMode="numeric" value={yields[item.roll.id]?.[slot.key] ?? '0'} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setYields((current) => ({ ...current, [item.roll.id]: { ...current[item.roll.id], [slot.key]: event.target.value } }))}/></td>)}<td><strong>{display(rowPieces)}</strong></td></tr>})}</tbody></table></div>}</section>

        <section className="ccut-review"><div><span>ROLL</span><strong>{selected.length}</strong></div><div><span>KELUAR</span><strong>{totalIssued.toFixed(2)}</strong></div><div><span>TERPAKAI</span><strong>{display(totalConsumed, 2)}</strong></div><div><span>SISA</span><strong>{display(totalRemaining, 2)}</strong></div><div><span>HASIL</span><strong>{display(totalPieces)} pcs</strong></div></section>
        <footer className="ccut-actions"><span>{draftId ? `Draft ${draftId.slice(0, 8)} · row version ${draftVersion}` : 'Transaksi baru · ID dibuat backend'}</span><div>{draftId && <button className="danger" disabled={!canEdit || mutation.writerLocked} onClick={() => void removeDraft()}><Trash2/> Hapus draft</button>}<button disabled={!formValid || mutation.writerLocked || (draftId ? !canEdit : !canCreate)} onClick={() => void save('SAVE_DRAFT')}>Simpan draft</button><button className="primary" disabled={!formValid || mutation.writerLocked || (draftId ? !canEdit : !canCreate) || !canPost} onClick={() => void save('POST')}>{saving ? <LoaderCircle className="spin"/> : <Check/>} Post ke WIP Potongan</button></div></footer>
      </main>
    </div>
  </section>
}
