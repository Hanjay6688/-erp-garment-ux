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

function numeric(value: string) {
  const parsed = Number(value.replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
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

export default function ConnectedCuttingPage() {
  const { runtime, identity } = useAuth()
  if (runtime.mode !== 'UAT_AUTH_SIMULATION') throw new Error('ConnectedCuttingPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const canCreate = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.create')
  const canEdit = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.edit_draft')
  const canPost = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.post')
  const [workspace, setWorkspace] = useState<CuttingWorkspace | null>(null)
  const [locationId, setLocationId] = useState('')
  const [rollQuery, setRollQuery] = useState('')
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
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const requestRef = useRef<{ fingerprint: string; id: string }>({ fingerprint: '', id: '' })

  const load = useCallback(async (nextLocation: string | null, nextQuery: string) => {
    setLoading(true)
    setError('')
    const { data, error: loadError } = await client.rpc('erp_get_cutting_workspace_v1', {
      p_roll_query: nextQuery.trim() || null,
      p_location_id: nextLocation || null,
      p_limit: 100,
      p_offset: 0,
    })
    if (loadError) setError(normalizeClientError(loadError).message)
    else {
      try {
        const parsed = parseCuttingWorkspace(data)
        setWorkspace(parsed)
        if (!nextLocation && parsed.locations[0]) setLocationId((current) => current || parsed.locations[0].id)
        setOrderId((current) => current || parsed.orders[0]?.id || '')
        setSlots((current) => current.length > 0 ? current : parsed.sizes
          .filter((size) => parsed.orders[0] && size.model_ids.includes(parsed.orders[0].model_id))
          .slice(0, 3)
          .map((size) => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
      } catch (parseError) {
        setError(parseError instanceof Error ? parseError.message : String(parseError))
      }
    }
    setLoading(false)
  }, [client])

  useEffect(() => { void load(null, '') }, [load])
  useEffect(() => { if (locationId) void load(locationId, '') }, [load, locationId])

  const selected = Object.values(selectedRolls)
  const selectedOrder = workspace?.orders.find((order) => order.id === orderId)
  const availableSizes = workspace?.sizes.filter((size) => selectedOrder && size.model_ids.includes(selectedOrder.model_id)) ?? []
  const selectedIds = new Set(Object.keys(selectedRolls))
  const totalIssued = selected.reduce((sum, item) => sum + item.issued, 0)
  const totalConsumed = selected.reduce((sum, item) => sum + numeric(item.consumed), 0)
  const totalRemaining = selected.reduce((sum, item) => sum + Math.max(0, item.issued - numeric(item.consumed)), 0)
  const totalPieces = selected.reduce((sum, item) => sum + slots.reduce((rollSum, slot) =>
    rollSum + Math.max(0, Math.floor(numeric(yields[item.roll.id]?.[slot.key] ?? '0'))), 0), 0)
  const cutAtValid = cutAt.length > 0 && Number.isFinite(new Date(cutAt).getTime())
  const formValid = Boolean(orderId && locationId && pattern && cutAtValid && slots.length > 0 && selected.length > 0)
    && selected.every((item) => numeric(item.consumed) > 0 && numeric(item.consumed) <= item.issued)
    && selected.every((item) => slots.some((slot) => numeric(yields[item.roll.id]?.[slot.key] ?? '0') > 0))

  const resetForm = () => {
    setDraftId(null)
    setDraftVersion(null)
    setPattern(null)
    setNotes('')
    setCutAt(datetimeLocal(new Date()))
    setSelectedRolls({})
    setYields({})
    requestRef.current = { fingerprint: '', id: '' }
    setNotice('Form baru siap. Belum ada data backend yang ditulis.')
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

  const changeOrder = (nextOrderId: string) => {
    const modelId = workspace?.orders.find((order) => order.id === nextOrderId)?.model_id
    const nextSlots = (workspace?.sizes ?? []).filter((size) => modelId && size.model_ids.includes(modelId)).slice(0, 3)
      .map((size) => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code }))
    setOrderId(nextOrderId)
    setSlots(nextSlots)
    setYields(Object.fromEntries(selected.map((item) => [item.roll.id, Object.fromEntries(nextSlots.map((slot) => [slot.key, '0']))])))
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
    setSlots(nextSlots.length > 0 ? nextSlots : (workspace?.sizes.slice(0, 3).map((size) => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })) ?? []))
    setSelectedRolls(nextRolls)
    setYields(nextYields)
    requestRef.current = { fingerprint: '', id: '' }
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
      qty_consumed: numeric(item.consumed),
      qty_reported_remaining: Math.max(0, item.issued - numeric(item.consumed)),
      yields: slots.map((slot, index) => ({
        slot_no: index + 1,
        qty_pcs: Math.max(0, Math.floor(numeric(yields[item.roll.id]?.[slot.key] ?? '0'))),
      })),
    })),
  })

  const save = async (action: 'SAVE_DRAFT' | 'POST') => {
    if (!formValid || saving || (draftId ? !canEdit : !canCreate) || (action === 'POST' && !canPost)) return
    setSaving(true)
    setError('')
    setNotice('')
    const nextPayload = payload(action)
    const fingerprint = JSON.stringify({ payload: nextPayload, expected: draftVersion })
    if (requestRef.current.fingerprint !== fingerprint) {
      requestRef.current = { fingerprint, id: globalThis.crypto.randomUUID() }
    }
    const { data, error: saveError } = await client.rpc('erp_save_cutting_group_before_sewing_v2', {
      p_payload: nextPayload,
      p_client_request_id: requestRef.current.id,
      p_expected_version: draftVersion,
    })
    if (saveError) setError(normalizeClientError(saveError).message)
    else {
      try {
        const result = parseCuttingSaveResult(data)
        const successNotice = result.material_issue_posted
          ? `${result.group_number} terposting · ${result.total_pieces} pcs masuk antrean Bagi Potongan.`
          : `${result.group_number} tersimpan sebagai draft backend · row version ${result.row_version}.`
        if (!result.material_issue_posted) {
          setDraftId(result.cutting_group_id)
          setDraftVersion(result.row_version)
        }
        await load(locationId, rollQuery)
        if (result.material_issue_posted) resetForm()
        setNotice(successNotice)
      } catch (parseError) {
        setError(parseError instanceof Error ? parseError.message : String(parseError))
      }
    }
    setSaving(false)
  }

  const removeDraft = async () => {
    if (!draftId || draftVersion === null || !canEdit || saving) return
    if (!globalThis.confirm('Hapus draft Potongan ini? Hanya draft yang belum diposting yang dapat dihapus.')) return
    setSaving(true)
    const { error: deleteError } = await client.rpc('erp_save_cutting_group_before_sewing_v2', {
      p_payload: { id: draftId, action: 'DELETE', change_reason: 'Hapus draft Potongan dari workspace connected' },
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: draftVersion,
    })
    if (deleteError) setError(normalizeClientError(deleteError).message)
    else { resetForm(); await load(locationId, rollQuery) }
    setSaving(false)
  }

  return <section className="connected-cutting-page">
    <header className="ccut-hero"><div><span>PRODUKSI · CUTTING CONNECTED</span><h1>Buat Potongan</h1><p>Satu transaksi atomik mengikat Pola, roll fisik, yard keluar/terpakai/sisa, hasil per size, stok, HPP, dan jurnal.</p></div><button type="button" onClick={() => void load(locationId || null, rollQuery)}><RefreshCw/> Refetch</button></header>
    <div className="ccut-truth"><Database/><strong>ERP ENTENG UAT · RPC CONNECTED</strong><span>Tidak ada fixture atau direct-table write pada mode ini.</span></div>
    {error && <div className="ccut-message error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}>Tutup</button></div>}
    {notice && <div className="ccut-message success" role="status"><Check/><span>{notice}</span></div>}

    <div className="ccut-layout">
      <aside className="ccut-drafts"><header><div><span>DRAFT BACKEND</span><strong>{workspace?.drafts.length ?? 0} Potongan</strong></div><button onClick={resetForm}>Baru</button></header>{workspace?.drafts.map((draft) => <button key={draft.cutting_group_id} className={draftId === draft.cutting_group_id ? 'active' : ''} onClick={() => resumeDraft(draft)}><FilePenLine/><span><strong>{draft.group_number}</strong><small>{draft.po_number} · {draft.pattern_code ? `${draft.pattern_code} ${draft.pattern_revision}` : 'Pola belum diikat'}</small></span><em>v{draft.row_version}</em></button>)}{!loading && workspace?.drafts.length === 0 && <p>Belum ada draft Potongan.</p>}</aside>

      <main className="ccut-form">
        <section className="ccut-card"><header><span>01 · IDENTITAS KANONIK</span><strong>PO, Pola, waktu, dan gudang sumber</strong></header><div className="ccut-fields"><label>Production Order<select value={orderId} onChange={(event) => changeOrder(event.target.value)}><option value="">Pilih PO…</option>{workspace?.orders.map((order) => <option value={order.id} key={order.id}>{order.po_number} · {order.model_code} · {order.model_name}</option>)}</select></label><label>Waktu potong<input type="datetime-local" value={cutAt} max={datetimeLocal(new Date())} onChange={(event) => setCutAt(event.target.value)}/></label><label>Gudang bahan<select value={locationId} onChange={(event) => setLocationId(event.target.value)}><option value="">Pilih gudang…</option>{workspace?.locations.map((location) => <option value={location.id} key={location.id}>{location.code} · {location.name}</option>)}</select></label><label>Catatan<input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Opsional"/></label></div><CuttingPatternPicker value={pattern} onChange={setPattern}/></section>

        <section className="ccut-card"><header><span>02 · UKURAN MODEL</span><strong>Kolom hasil potong mengikuti Master Model</strong></header><div className="ccut-size-list">{availableSizes.map((size) => <button className={slots.some((slot) => slot.sizeId === size.id) ? 'active' : ''} onClick={() => toggleSize(size.id, size.code)} key={size.id}>{size.code}</button>)}</div>{selectedOrder && availableSizes.length === 0 ? <small role="alert">Model ini belum memiliki mapping size aktif di Master Model.</small> : null}</section>

        <section className="ccut-card"><header><span>03 · ROLL FISIK</span><strong>{workspace?.roll_total ?? 0} tersedia di lokasi</strong></header><div className="ccut-search"><Search/><input value={rollQuery} onChange={(event) => setRollQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void load(locationId || null, rollQuery) }} placeholder="Nomor roll, bahan, supplier…"/><button onClick={() => void load(locationId || null, rollQuery)}>Cari</button></div><div className="ccut-roll-catalog">{loading ? <span><LoaderCircle className="spin"/> Memuat roll…</span> : workspace?.rolls.map((roll) => <button className={selectedIds.has(roll.id) ? 'active' : ''} onClick={() => toggleRoll(roll)} key={roll.id}><span><strong>{roll.roll_number}</strong><small>{roll.material_sku} · {roll.material_name}</small></span><em>{roll.available_qty} {roll.unit_code}</em></button>)}</div></section>

        <section className="ccut-card wide"><header><span>04 · HASIL PER ROLL & SIZE</span><strong>Angka sumber direkonsiliasi backend</strong></header>{selected.length === 0 ? <div className="ccut-empty">Pilih minimal satu roll dari gudang bahan.</div> : <div className="ccut-table-wrap"><table><thead><tr><th>Roll</th><th>Keluar</th><th>Terpakai</th><th>Sisa</th>{slots.map((slot) => <th key={slot.key}>Size {slot.sizeCode}</th>)}<th>Total pcs</th></tr></thead><tbody>{selected.map((item) => { const consumed = numeric(item.consumed); const rowPieces = slots.reduce((sum, slot) => sum + Math.max(0, Math.floor(numeric(yields[item.roll.id]?.[slot.key] ?? '0'))), 0); return <tr key={item.roll.id}><th><strong>{item.roll.roll_number}</strong><small>{item.roll.material_name}</small></th><td>{item.issued} {item.roll.unit_code}</td><td><input inputMode="decimal" value={item.consumed} onChange={(event) => setSelectedRolls((current) => ({ ...current, [item.roll.id]: { ...current[item.roll.id], consumed: event.target.value.replace(/[^0-9.,]/g, '') } }))}/></td><td className={consumed > item.issued ? 'bad' : ''}>{Math.max(0, item.issued - consumed).toFixed(2)}</td>{slots.map((slot) => <td key={slot.key}><input inputMode="numeric" value={yields[item.roll.id]?.[slot.key] ?? '0'} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setYields((current) => ({ ...current, [item.roll.id]: { ...current[item.roll.id], [slot.key]: event.target.value.replace(/\D/g, '') } }))}/></td>)}<td><strong>{rowPieces}</strong></td></tr>})}</tbody></table></div>}</section>

        <section className="ccut-review"><div><span>ROLL</span><strong>{selected.length}</strong></div><div><span>KELUAR</span><strong>{totalIssued.toFixed(2)}</strong></div><div><span>TERPAKAI</span><strong>{totalConsumed.toFixed(2)}</strong></div><div><span>SISA</span><strong>{totalRemaining.toFixed(2)}</strong></div><div><span>HASIL</span><strong>{totalPieces} pcs</strong></div></section>
        <footer className="ccut-actions"><span>{draftId ? `Draft ${draftId.slice(0, 8)} · row version ${draftVersion}` : 'Transaksi baru · ID dibuat backend'}</span><div>{draftId && <button className="danger" disabled={!canEdit || saving} onClick={() => void removeDraft()}><Trash2/> Hapus draft</button>}<button disabled={!formValid || saving || (draftId ? !canEdit : !canCreate)} onClick={() => void save('SAVE_DRAFT')}>Simpan draft</button><button className="primary" disabled={!formValid || saving || (draftId ? !canEdit : !canCreate) || !canPost} onClick={() => void save('POST')}>{saving ? <LoaderCircle className="spin"/> : <Check/>} Post ke WIP Potongan</button></div></footer>
      </main>
    </div>
  </section>
}
