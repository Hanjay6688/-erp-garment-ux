import SkuWaveReferences from './SkuWaveReferences'
import NativeCuttingYieldPanel from './NativeCuttingYieldPanel'
import NativeCuttingInputsPanel from './NativeCuttingInputsPanel'
import NativeCuttingLearningPanel from './NativeCuttingLearningPanel'
import { isConnectedRuntime } from './config/runtime'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, Database, FilePenLine, LoaderCircle, RefreshCw, Search, Trash2 } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import CuttingPatternPicker from './CuttingPatternPicker'
import type { CuttingPatternChoice } from './CuttingPatternPicker'
import {
  parseCuttingSaveResult,
  type CuttingDraft,
  type CuttingWorkspaceRoll,
} from './cuttingPersistence'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { ProductionEnvelope } from './productionRecovery'
import { parseQuantityInput, requireQuantityInput } from './quantityInput'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso } from './cp6BusinessTime'
import { parseCuttingSelectorWorkspace, cuttingOrder, cuttingSelectionIssue, type CuttingSelectorWorkspace, type CuttingSelectorDraft } from './cuttingSelectors'
import { autoPoPayload, parseAutoPoWorkspace, validateAutoPoOutcome, type AutoPoAction, type AutoPoCutting, type AutoPoModel, type AutoPoWorkspace } from './cuttingAutoPoContract'
import './connected-cutting.css'

type SelectedRoll = {
  roll: CuttingWorkspaceRoll
  issued: number
  consumed: string
}

type SizeSlot = { key: string; sizeId: string; sizeCode: string }

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

function sizesForOrder(workspace: CuttingSelectorWorkspace | null, orderId: string) {
  const modelId = cuttingOrder(workspace, orderId)?.model_id
    ?? (workspace?.selected_draft?.po_id === orderId ? workspace.selected_draft.model_id : undefined)
  return modelId ? workspace?.sizes.filter((size) => size.model_ids.includes(modelId)) ?? [] : []
}

export default function ConnectedCuttingPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ConnectedCuttingPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const canCreate = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.create')
  const canEdit = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.edit_draft')
  const canPost = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.cutting.post')
  const authorityKey = JSON.stringify([runtime.projectRef, identity.status,
    identity.status === 'AUTHORIZED' ? [identity.profile.id, identity.profile.rowVersion, identity.profile.roleRowVersion, identity.permissions] : null])
  const [loadedAuthority, setLoadedAuthority] = useState<string | null>(null)
  const [sourceWorkspace, setWorkspace] = useState<CuttingSelectorWorkspace | null>(null)
  const workspace = loadedAuthority === authorityKey ? sourceWorkspace : null
  const [sourceEpoch, setSourceEpoch] = useState(0)
  const [locationId, setLocationId] = useState('')
  const [rollQuery, setRollQuery] = useState('')
  const [rollOffset, setRollOffset] = useState(0)
  const [orderId, setOrderId] = useState('')
  const [orderQuery, setOrderQuery] = useState('')
  const [draftQuery, setDraftQuery] = useState('')
  const [pattern, setPattern] = useState<CuttingPatternChoice | null>(null)
  const [cutAt, setCutAt] = useState(() => cp6WibDateTimeInput())
  const [notes, setNotes] = useState('')
  const [draftId, setDraftId] = useState<string | null>(null)
  const [draftVersion, setDraftVersion] = useState<number | null>(null)
  const [lastCommittedGroupId, setLastCommittedGroupId] = useState<string | null>(null)
  const [selectedRolls, setSelectedRolls] = useState<Record<string, SelectedRoll>>({})
  const [slots, setSlots] = useState<SizeSlot[]>([])
  const [yields, setYields] = useState<Record<string, Record<string, string>>>({})
  const [loading, setLoading] = useState(true)
  const mutation = useProductionMutation('CUTTING')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  // Owner D15-6: by default the PO is made automatically when the cutting is posted (one transaction); an existing PO
  // (e.g. an imported open PO) can still be chosen.
  const autoMutation = useProductionMutation('CUTTING_AUTO_PO')
  // A pending existing-PO cutting (recovery after a lost reply) opens in that mode so its form and reconcile stay together.
  const [poMode, setPoMode] = useState<'AUTO' | 'EXISTING'>(() => mutation.pending ? 'EXISTING' : 'AUTO')
  const [autoWorkspace, setAutoWorkspace] = useState<AutoPoWorkspace | null>(null)
  const [autoError, setAutoError] = useState('')
  const [modelId, setModelId] = useState('')
  const [modelQuery, setModelQuery] = useState('')
  const [autoModelPinned, setAutoModelPinned] = useState<AutoPoModel | null>(null)
  const [autoDraft, setAutoDraft] = useState<{ id: string; version: number } | null>(null)
  const autoRequestRef = useRef(0)
  const saving = mutation.busy || autoMutation.busy
  const writerLocked = mutation.writerLocked || autoMutation.writerLocked
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const loadRequestRef = useRef(0)
  const selectionRef = useRef({ orderId, draftId, draftVersion })
  selectionRef.current = { orderId, draftId, draftVersion }
  const selectionReadyRef = useRef(false)
  const selectorsRef = useRef({ orderQuery: '', orderOffset: 0, draftQuery: '', draftOffset: 0 })
  const viewRef = useRef({ locationId, rollQuery, rollOffset })
  viewRef.current = { locationId, rollQuery, rollOffset }

  const load = useCallback(async (nextLocation: string | null, nextQuery = viewRef.current.rollQuery,
    nextOffset = viewRef.current.rollOffset, changes: Partial<typeof selectorsRef.current> = {}) => {
    const ticket = beginRead()
    const requestId = ++loadRequestRef.current
    const selection = { ...selectionRef.current }
    const selectors = { ...selectorsRef.current, ...changes }
    selectorsRef.current = selectors
    selectionReadyRef.current = false
    setWorkspace(null)
    setLoadedAuthority(null)
    setLoading(true)
    setError('')
    try {
      const { data, error: loadError } = await client.rpc('erp_get_cutting_workspace_v2', {
        p_roll_query: nextQuery.trim() || null, p_location_id: nextLocation || null,
        p_limit: 100, p_offset: nextOffset,
        p_order_query: selectors.orderQuery.trim() || null, p_order_limit: 50, p_order_offset: selectors.orderOffset,
        p_draft_query: selectors.draftQuery.trim() || null, p_draft_limit: 25, p_draft_offset: selectors.draftOffset,
        p_selected_order_id: selection.orderId || null, p_selected_draft_id: selection.draftId,
      })
      if (requestId !== loadRequestRef.current) return false
      if (loadError) { setError(normalizeClientError(loadError).message); return false }
      const parsed = parseCuttingSelectorWorkspace(data)
      if (parsed.selected_order_id !== (selection.orderId || null) || parsed.selected_draft_id !== selection.draftId
        || parsed.order_page.offset !== selectors.orderOffset || parsed.draft_page.offset !== selectors.draftOffset
        || parsed.order_page.limit !== 50 || parsed.draft_page.limit !== 25
        || parsed.offset !== nextOffset || parsed.location_id !== (nextLocation || null)) throw new Error('Respons Potongan tidak cocok dengan halaman yang diminta.')
      const nextOrderId = selection.orderId || parsed.orders[0]?.id || ''
      // A pending transaction keeps this view readable while writes stay locked.
      if (!isReadCurrent(ticket)) return false
      const ready = finishRead(ticket)
      selectionReadyRef.current = ready && !cuttingSelectionIssue(parsed, nextOrderId, selection.draftId, selection.draftVersion)
      setWorkspace(parsed)
      setLoadedAuthority(authorityKey)
      setRollOffset(parsed.offset)
      if (!nextLocation && parsed.locations[0]) setLocationId(parsed.locations[0].id)
      if (!selection.orderId && nextOrderId) {
        selectionRef.current = { ...selectionRef.current, orderId: nextOrderId }
        setOrderId(nextOrderId)
        const initialSizes = sizesForOrder(parsed, nextOrderId)
        setSlots(initialSizes.map(size => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
      }
      return ready
    } catch (failure) {
      if (requestId === loadRequestRef.current) setError(normalizeClientError(failure).message)
      return false
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false)
    }
  }, [beginRead, finishRead, isReadCurrent, client, authorityKey])

  useEffect(() => { void load(viewRef.current.locationId || null); return () => { loadRequestRef.current += 1 } }, [mutation.scope, authorityKey]) // eslint-disable-line react-hooks/exhaustive-deps
  const loadAuto = useCallback(async (q: { q: string; draftId: string | null }) => {
    const ticket = autoMutation.beginRead(), n = ++autoRequestRef.current
    setAutoError('')
    try {
      const { data, error: readError } = await client.rpc('erp_cp7_get_cutting_auto_po_v1', { p_query: { q: q.q.trim(), offset: 0, draft_id: q.draftId } })
      if (n !== autoRequestRef.current || !autoMutation.isReadCurrent(ticket)) return null
      if (readError) throw readError
      const parsed = parseAutoPoWorkspace(data)
      setAutoWorkspace(parsed); autoMutation.finishRead(ticket); return parsed
    } catch (failure) {
      if (n === autoRequestRef.current) { setAutoWorkspace(null); setAutoError(normalizeClientError(failure).message) }
      return null
    }
  }, [autoMutation.beginRead, autoMutation.finishRead, autoMutation.isReadCurrent, client]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { void loadAuto({ q: '', draftId: null }); return () => { autoRequestRef.current += 1 } }, [autoMutation.scope, authorityKey]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (locationId) { setRollOffset(0); void load(locationId, rollQuery, 0) } }, [locationId]) // eslint-disable-line react-hooks/exhaustive-deps

  const onAuthorityLost = useCallback(() => {
    ++loadRequestRef.current
    selectionReadyRef.current = false
    setWorkspace(null); setLoadedAuthority(null); setLoading(false)
    mutation.invalidate()
    setSourceEpoch(epoch => epoch + 1)
    setError('Sumber belum dapat dibaca dengan izin sesi sekarang. Muat ulang sebelum melanjutkan.')
  }, [mutation.invalidate])
  const formFactsReady = workspace !== null && !loading

  const selectionIssue = poMode === 'EXISTING' ? cuttingSelectionIssue(workspace, orderId, draftId, draftVersion) : null
  const selectedOrder = cuttingOrder(workspace, orderId)
  const orderOptions = workspace ? [...(selectedOrder && !workspace.orders.some(row => row.id === selectedOrder.id) ? [selectedOrder] : []), ...workspace.orders] : []
  const openDraft = workspace?.selected_draft?.cutting_group_id === draftId ? workspace.selected_draft : workspace?.drafts.find(row => row.cutting_group_id === draftId)
  const searchOrders = () => void load(locationId || null, rollQuery, rollOffset, { orderQuery, orderOffset: 0 })
  const searchDrafts = () => void load(locationId || null, rollQuery, rollOffset, { draftQuery, draftOffset: 0 })
  const pageLabel = (offset: number | undefined, length: number | undefined, total: number | undefined) =>
    total === undefined ? 'Belum dimuat' : length ? `${(offset ?? 0) + 1}–${(offset ?? 0) + length} dari ${total}` : `0 dari ${total}`

  const selected = Object.values(selectedRolls)
  const selectedIds = new Set(Object.keys(selectedRolls))
  const autoModel = poMode !== 'AUTO' || !modelId ? null : autoWorkspace?.models.rows.find(m => m.id === modelId) ?? (autoModelPinned?.id === modelId ? autoModelPinned : null)
  const autoModels = autoWorkspace ? [...(autoModel && !autoWorkspace.models.rows.some(m => m.id === autoModel.id) ? [autoModel] : []), ...autoWorkspace.models.rows] : []
  const availableSizes = poMode === 'AUTO' ? autoModel?.sizes ?? [] : sizesForOrder(workspace, orderId)
  const totalIssued = selected.reduce((sum, item) => sum + item.issued, 0)
  const totalConsumed = selected.reduce((sum, item) => sum + numeric(item.consumed), 0)
  const totalRemaining = selected.reduce((sum, item) => sum + item.issued - numeric(item.consumed), 0)
  const totalPieces = selected.reduce((sum, item) => sum + slots.reduce((rollSum, slot) =>
    rollSum + count(yields[item.roll.id]?.[slot.key] ?? '0'), 0), 0)
  const cutAtIso = cp6WibPhysicalTimeToIso(cutAt)
  const cutAtValid = cutAtIso !== null
  const identityValid = poMode === 'AUTO' ? Boolean(autoModel && autoWorkspace) : Boolean(orderId)
  const formValid = Boolean(identityValid && locationId && pattern && cutAtValid && slots.length > 0 && selected.length > 0)
    && selected.every((item) => numeric(item.consumed) > 0 && numeric(item.consumed) <= item.issued)
    && selected.every((item) => slots.every((slot) => parseQuantityInput(yields[item.roll.id]?.[slot.key] ?? '0') !== null)
      && slots.some((slot) => count(yields[item.roll.id]?.[slot.key] ?? '0') > 0))

  const resetForm = () => {
    selectionRef.current = { orderId: selectionRef.current.orderId, draftId: null, draftVersion: null }
    selectionReadyRef.current = Boolean(cuttingOrder(workspace, selectionRef.current.orderId))
    setDraftId(null)
    setDraftVersion(null)
    setAutoDraft(null)
    setPattern(null)
    setNotes('')
    setCutAt(cp6WibDateTimeInput())
    setSelectedRolls({})
    setYields({})
    setNotice('Form baru siap. Belum ada data backend yang ditulis.')
  }

  const changeOrder = (nextOrderId: string) => {
    selectionRef.current = { ...selectionRef.current, orderId: nextOrderId }
    selectionReadyRef.current = Boolean(cuttingOrder(workspace, nextOrderId))
    setOrderId(nextOrderId)
    const nextSizes = sizesForOrder(workspace, nextOrderId)
    setSlots(nextSizes.map((size) => ({
      key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code,
    })))
    setSelectedRolls({})
    setYields({})
    if (selected.length > 0) setNotice('Pilihan roll dikosongkan karena Production Order berubah.')
    void load(locationId || null, rollQuery, rollOffset)
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

  const resumeDraft = (draft: CuttingSelectorDraft) => {
    selectionRef.current = { orderId: draft.po_id, draftId: draft.cutting_group_id, draftVersion: draft.row_version }
    selectionReadyRef.current = false
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
    setPoMode('EXISTING')
    setAutoDraft(null)
    setDraftId(draft.cutting_group_id)
    setDraftVersion(draft.row_version)
    setOrderId(draft.po_id)
    setLocationId(draft.source_location_id ?? workspace?.locations[0]?.id ?? '')
    setPattern(draft.pattern_id && draft.pattern_code && draft.pattern_revision && draft.pattern_name ? {
      id: draft.pattern_id, code: draft.pattern_code, revision: draft.pattern_revision, name: draft.pattern_name,
    } : null)
    setCutAt(cp6WibDateTimeInput(draft.cut_at))
    setNotes(draft.notes ?? '')
    setSlots(nextSlots.length > 0 ? nextSlots : sizesForOrder(workspace, draft.po_id).map((size) => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
    setSelectedRolls(nextRolls)
    setYields(nextYields)
    setNotice(`${draft.group_number} dimuat dari backend${draft.editable ? '.' : ' · read-only karena lifecycle downstream.'}`)
    setError('')
    void load(draft.source_location_id ?? workspace?.locations[0]?.id ?? null, rollQuery, 0)
  }

  const cuttingPart = () => ({
    pattern_id: pattern?.id ?? '',
    source_location_id: locationId,
    cut_at: cutAtIso ?? '',
    notes: notes.trim() || null,
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
  const payload = (action: 'SAVE_DRAFT' | 'POST') => ({
    ...(draftId ? { id: draftId } : {}),
    action,
    po_id: orderId,
    change_reason: action === 'POST' ? 'Posting Potongan dari workspace connected' : 'Simpan draft Potongan dari workspace connected',
    ...cuttingPart(),
  })

  const sendExact = (envelope: ProductionEnvelope) => client.rpc('erp_save_cutting_group_before_sewing_v2', {
    p_payload: envelope.payload, p_client_request_id: envelope.id, p_expected_version: envelope.expectedVersion,
  })
  // A commit writes and clears its envelope in the recovery store both writers of this page share, so both stop being
  // ready; both reads must be current again, or every writer on the page stays locked (the auto-PO one came with D15-6).
  const refetchAll = (view: { locationId: string; rollQuery: string }, offset?: number) =>
    Promise.all([load(view.locationId || null, view.rollQuery, offset), loadAuto({ q: modelQuery, draftId: null })])
      .then(([native, autoRead]) => native && autoRead !== null)
  const reload = () => refetchAll(viewRef.current, 0)
  const retire = (data: unknown, envelope: ProductionEnvelope) => {
    resetForm()
    if (envelope.action === 'DELETE') { setLastCommittedGroupId(null); setNotice('Draft Potongan sudah dihapus.') }
    else {
      const result = parseCuttingSaveResult(data)
      setLastCommittedGroupId(result.cutting_group_id)
      setNotice(`${result.group_number} ${result.material_issue_posted ? 'terposting' : 'tersimpan sebagai draft'}. Form lama ditutup; muat draft terbaru untuk melanjutkan.`)
    }
  }
  const handlers = { send: sendExact, validate: validateCuttingCommit, retire, reload }
  const save = async (action: 'SAVE_DRAFT' | 'POST') => {
    if (!selectionReadyRef.current || !formValid || writerLocked || (draftId ? !canEdit : !canCreate) || (action === 'POST' && !canPost)) return
    setError(''); setNotice('')
    await run(action, payload(action), draftVersion, handlers)
  }
  const autoHandlers = {
    send: (envelope: ProductionEnvelope) => client.rpc('erp_cp7_save_cutting_auto_po_v1', { p_payload: envelope.payload, p_request: envelope.id }),
    validate: (data: unknown, envelope: ProductionEnvelope) => { validateAutoPoOutcome(data, envelope) },
    retire: (data: unknown, envelope: ProductionEnvelope) => {
      const result = validateAutoPoOutcome(data, envelope)
      resetForm()
      if (result.action === 'POST') {
        setLastCommittedGroupId(result.groupId)
        setNotice(`${result.poNumber} dibuat otomatis; ${result.groupNumber} terposting (${result.totalPieces} pcs). Nomor PO ini dipakai untuk pelacakan di Bagi Potongan dan WIP.`)
      } else setNotice(result.action === 'DELETE' ? 'Draf PO otomatis dihapus.' : 'Draf PO otomatis tersimpan. Belum ada PO, stok, atau jurnal yang berubah.')
    },
    reload,
  }
  const saveAuto = async (action: AutoPoAction) => {
    if (!autoWorkspace || writerLocked || (action !== 'DELETE' && (!formValid || !autoModel)) || !canCreate || (action === 'POST' && !canPost)) return
    setError(''); setNotice('')
    const body = autoPoPayload(action, autoDraft, autoModel?.id ?? null, action === 'DELETE' ? null : cuttingPart() as AutoPoCutting,
      'Posting Potongan dengan PO otomatis dari workspace connected')
    await autoMutation.run(action, body, null, autoHandlers)
  }
  const changeMode = (next: 'AUTO' | 'EXISTING') => {
    if (next === poMode) return
    resetForm()
    setPoMode(next)
    if (next === 'AUTO') setSlots((autoModel?.sizes ?? []).map(size => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
    else setSlots(sizesForOrder(workspace, orderId).map(size => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
  }
  const changeModel = (nextId: string) => {
    const next = autoModels.find(m => m.id === nextId) ?? null
    setModelId(nextId); setAutoModelPinned(next)
    setSlots((next?.sizes ?? []).map(size => ({ key: globalThis.crypto.randomUUID(), sizeId: size.id, sizeCode: size.code })))
    setSelectedRolls({}); setYields({})
    if (selected.length > 0) setNotice('Pilihan roll dikosongkan karena model berubah.')
  }
  const resumeAutoDraft = async (id: string) => {
    const read = await loadAuto({ q: modelQuery, draftId: id })
    const d = read?.selected
    if (!d || d.id !== id) { setError('Draf PO otomatis tidak ditemukan lagi. Muat ulang.'); return }
    const c = d.cutting
    const nextSlots = c.size_slots.map(slot => ({ key: `auto-${slot.slot_no}-${slot.size_id}`, sizeId: slot.size_id,
      sizeCode: d.model.sizes.find(size => size.id === slot.size_id)?.code ?? '?' }))
    const nextRolls: Record<string, SelectedRoll> = {}, nextYields: Record<string, Record<string, string>> = {}
    c.rolls.forEach(r => {
      const info = d.rolls.find(x => x.rollId === r.roll_id)
      if (!info) return
      nextRolls[r.roll_id] = { roll: { id: info.rollId, roll_number: info.rollNumber, material_id: info.materialId, material_sku: info.materialSku,
        material_name: info.materialName, unit_code: info.unitCode, supplier_id: null, supplier_code: null, supplier_name: info.supplierName,
        original_qty: info.originalQty, available_qty: info.availableQty, status: 'DRAFT_SELECTED', received_at: null }, issued: r.qty_issued, consumed: String(r.qty_consumed) }
      nextYields[r.roll_id] = Object.fromEntries(nextSlots.map((slot, index) => [slot.key, String(r.yields.find(y => y.slot_no === c.size_slots[index].slot_no)?.qty_pcs ?? 0)]))
    })
    resetForm()
    setPoMode('AUTO'); setModelId(d.model.id); setAutoModelPinned(d.model); setAutoDraft({ id: d.id, version: d.rowVersion })
    setPattern(d.pattern); setLocationId(c.source_location_id); setCutAt(cp6WibDateTimeInput(c.cut_at)); setNotes(c.notes ?? '')
    setSlots(nextSlots); setSelectedRolls(nextRolls); setYields(nextYields)
    setNotice(`Draf PO otomatis ${d.model.code} dimuat. PO baru dibuat saat potongan disahkan.`)
  }
  const removeDraft = async () => {
    if (!selectionReadyRef.current || !draftId || draftVersion === null || !canEdit || writerLocked) return
    if (!globalThis.confirm('Hapus draft Potongan ini? Hanya draft yang belum diposting yang dapat dihapus.')) return
    setError(''); setNotice('')
    await run('DELETE', { id: draftId, action: 'DELETE', change_reason: 'Hapus draft Potongan dari workspace connected' }, draftVersion, handlers)
  }

  return <section className="connected-cutting-page">
    <header className="ccut-hero"><div><span>PRODUKSI · CUTTING CONNECTED</span><h1>Buat Potongan</h1><p>Satu transaksi atomik mengikat Pola, roll fisik, yard keluar/terpakai/sisa, hasil per size, stok, HPP, dan jurnal.</p></div><button type="button" onClick={() => void refetchAll({ locationId, rollQuery })}><RefreshCw/> Refetch</button></header>
    <div className="ccut-truth"><Database/><strong>ERP ENTENG UAT · RPC CONNECTED</strong><span>Tidak ada fixture atau direct-table write pada mode ini.</span></div>
    {error && <div className="ccut-message error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}>Tutup</button></div>}
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="ccut-message error"/>
    <ProductionRecoveryNotice recovery={autoMutation} onReconcile={() => autoMutation.reconcile(autoHandlers)} className="ccut-message error" reconcileLabel="Periksa hasil Potongan dengan PO otomatis"/>
    {autoError && <div className="ccut-message error" role="alert"><AlertTriangle/><span>{autoError}</span><button onClick={() => setAutoError('')}>Tutup</button></div>}
    {selectionIssue && <div className="ccut-message error" role="status"><AlertTriangle/><span>{selectionIssue}</span>{openDraft && <button disabled={writerLocked} onClick={() => resumeDraft(openDraft)}>Muat draft terbaru</button>}</div>}
    {notice && <div className="ccut-message success" role="status"><Check/><span>{notice}</span></div>}

    <div className="ccut-layout">
      <aside className="ccut-drafts">
        <header><div><span>DRAFT BACKEND</span><strong>{workspace ? `${workspace.draft_page.total} Potongan` : 'Belum dimuat'}</strong></div><button disabled={writerLocked} onClick={resetForm}>Baru</button></header>
        <div className="ccut-search"><input aria-label="Cari draft Potongan" maxLength={200} value={draftQuery} onChange={event => setDraftQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') searchDrafts() }} placeholder="Nomor Potongan, PO, model, pola…"/><button disabled={loading || saving} onClick={searchDrafts}>Cari draft</button></div>
        {openDraft && !workspace?.drafts.some(row => row.cutting_group_id === openDraft.cutting_group_id) && <button className="active" disabled={writerLocked} onClick={() => resumeDraft(openDraft)}><FilePenLine/><span><strong>{openDraft.group_number}</strong><small>Draft terbuka · di luar hasil pencarian</small></span></button>}
        {workspace?.drafts.map(draft => <button key={draft.cutting_group_id} className={draftId === draft.cutting_group_id ? 'active' : ''} disabled={writerLocked} onClick={() => resumeDraft(draft)}><FilePenLine/><span><strong>{draft.group_number}</strong><small>{draft.po_number} · {draft.pattern_code ? `${draft.pattern_code} ${draft.pattern_revision}` : 'Pola belum diikat'}</small></span><em>v{draft.row_version}</em></button>)}
        {!loading && workspace?.drafts.length === 0 && <p>Tidak ada draft yang cocok.</p>}
        <footer className="ccut-pagination"><span>{pageLabel(workspace?.draft_page.offset, workspace?.drafts.length, workspace?.draft_page.total)}</span><div><button aria-label="Draft sebelumnya" disabled={loading || !workspace || workspace.draft_page.offset === 0} onClick={() => void load(locationId || null, rollQuery, rollOffset, { draftOffset: Math.max(0, selectorsRef.current.draftOffset - 25) })}>Sebelumnya</button><button aria-label="Draft berikutnya" disabled={loading || !workspace || workspace.draft_page.offset + workspace.drafts.length >= workspace.draft_page.total} onClick={() => void load(locationId || null, rollQuery, rollOffset, { draftOffset: selectorsRef.current.draftOffset + 25 })}>Berikutnya</button></div></footer>
        <section className="ccut-auto-drafts" aria-label="Draf PO otomatis"><header><div><span>DRAF PO OTOMATIS</span><strong>{autoWorkspace ? `${autoWorkspace.drafts.length} draf` : 'Belum dimuat'}</strong></div></header>
          {autoWorkspace?.drafts.map(d => <button key={d.id} className={autoDraft?.id === d.id ? 'active' : ''} disabled={writerLocked} aria-label={`Muat draf PO otomatis ${d.modelCode} ${d.id.slice(0, 8)}`} onClick={() => void resumeAutoDraft(d.id)}><FilePenLine/><span><strong>{d.modelCode} · {d.modelName}</strong><small>{d.pieces} pcs · PO dibuat saat disahkan</small></span><em>v{d.rowVersion}</em></button>)}
          {autoWorkspace && autoWorkspace.drafts.length === 0 ? <p>Belum ada draf PO otomatis.</p> : null}
        </section>
      </aside>

      <main className="ccut-form">
        <section className="ccut-card"><header><span>01 · IDENTITAS KANONIK</span><strong>PO, Pola, waktu, dan gudang sumber</strong></header><fieldset className="ccut-po-mode" disabled={writerLocked || draftId !== null || autoDraft !== null}><legend>Production Order</legend><label><input type="radio" name="ccut-po-mode" checked={poMode === 'AUTO'} onChange={() => changeMode('AUTO')}/>PO baru otomatis</label><label><input type="radio" name="ccut-po-mode" checked={poMode === 'EXISTING'} onChange={() => changeMode('EXISTING')}/>PO yang sudah ada</label></fieldset>{poMode === 'AUTO' ? <><div className="ccut-search"><Search/><input aria-label="Cari model" maxLength={80} value={modelQuery} onChange={event => setModelQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void loadAuto({ q: modelQuery, draftId: null }) }} placeholder="Kode atau nama model…"/><button disabled={saving} onClick={() => void loadAuto({ q: modelQuery, draftId: null })}>Cari model</button></div><p className="ccut-auto-note">Nomor PO dibuat otomatis saat potongan disahkan, dalam satu simpan dengan posting potongan. Draf belum membuat PO dan belum mengubah stok maupun keuangan.</p></> : <><div className="ccut-search"><Search/><input aria-label="Cari PO" maxLength={200} value={orderQuery} onChange={event => setOrderQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') searchOrders() }} placeholder="Nomor PO, model, mandor…"/><button disabled={loading || saving} onClick={searchOrders}>Cari PO</button></div><div className="ccut-pagination"><span>{pageLabel(workspace?.order_page.offset, workspace?.orders.length, workspace?.order_page.total)}</span><div><button aria-label="PO sebelumnya" disabled={loading || !workspace || workspace.order_page.offset === 0} onClick={() => void load(locationId || null, rollQuery, rollOffset, { orderOffset: Math.max(0, selectorsRef.current.orderOffset - 50) })}>Sebelumnya</button><button aria-label="PO berikutnya" disabled={loading || !workspace || workspace.order_page.offset + workspace.orders.length >= workspace.order_page.total} onClick={() => void load(locationId || null, rollQuery, rollOffset, { orderOffset: selectorsRef.current.orderOffset + 50 })}>Berikutnya</button></div></div></>}<div className="ccut-fields">{poMode === 'AUTO' ? <label>Model<select aria-label="Model potongan" value={modelId} disabled={autoDraft !== null && writerLocked} onChange={(event) => changeModel(event.target.value)}><option value="">Pilih model…</option>{autoModels.map((m) => <option value={m.id} key={m.id}>{m.code} · {m.name}</option>)}</select></label> : <label>Production Order<select value={orderId} disabled={draftId !== null} onChange={(event) => changeOrder(event.target.value)}><option value="">Pilih PO…</option>{orderId && !selectedOrder && <option value={orderId} disabled>PO terpilih tidak tersedia</option>}{orderOptions.map((order) => <option value={order.id} key={order.id}>{order.po_number} · {order.model_code} · {order.model_name}</option>)}</select></label>}<label>Waktu potong (WIB)<input type="datetime-local" value={cutAt} max={cp6WibDateTimeInput()} onChange={(event) => setCutAt(event.target.value)}/></label><label>Gudang bahan<select value={locationId} onChange={(event) => { setLocationId(event.target.value); setRollOffset(0); setSelectedRolls({}); setYields({}); if (selected.length > 0) setNotice('Pilihan roll dikosongkan karena gudang bahan berubah.') }}><option value="">Pilih gudang…</option>{workspace?.locations.map((location) => <option value={location.id} key={location.id}>{location.code} · {location.name}</option>)}</select></label><label>Catatan<input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Opsional"/></label></div><CuttingPatternPicker value={pattern} onChange={setPattern} suspended={!formFactsReady} onAuthorityLost={onAuthorityLost}/></section>

        <section className="ccut-card"><header><span>02 · UKURAN AKTIF</span><strong>{poMode === 'AUTO' ? 'Kolom hasil potong sesuai model' : 'Kolom hasil potong sesuai model PO'}</strong></header><div className="ccut-size-list">{availableSizes.map((size) => <button className={slots.some((slot) => slot.sizeId === size.id) ? 'active' : ''} onClick={() => toggleSize(size.id, size.code)} key={size.id}>{size.code}</button>)}{(poMode === 'AUTO' ? autoModel !== null : Boolean(orderId)) && availableSizes.length === 0 ? <span>Model ini belum memiliki ukuran aktif.</span> : null}</div></section>

        <section className="ccut-card"><header><span>03 · ROLL FISIK</span><strong>{workspace?.roll_total ?? '—'} tersedia di lokasi</strong></header><div className="ccut-search"><Search/><input value={rollQuery} onChange={(event) => setRollQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { setRollOffset(0); void load(locationId || null, rollQuery, 0) } }} placeholder="Nomor roll, bahan, supplier…"/><button onClick={() => { setRollOffset(0); void load(locationId || null, rollQuery, 0) }}>Cari</button></div><div className="ccut-roll-catalog">{loading ? <span><LoaderCircle className="spin"/> Memuat roll…</span> : workspace?.rolls.map((roll) => <button className={selectedIds.has(roll.id) ? 'active' : ''} onClick={() => toggleRoll(roll)} key={roll.id}><span><strong>{roll.roll_number}</strong><small>{roll.material_sku} · {roll.material_name}</small></span><em>{roll.available_qty} {roll.unit_code}</em></button>)}</div><footer className="ccut-pagination"><span>{workspace?.roll_total ? `${rollOffset + 1}–${rollOffset + workspace.rolls.length} dari ${workspace.roll_total}` : '0 roll'}</span><div><button disabled={loading || rollOffset === 0} onClick={() => void load(locationId || null, rollQuery, Math.max(0, rollOffset - 100))}>Sebelumnya</button><button disabled={loading || !workspace || rollOffset + workspace.rolls.length >= workspace.roll_total} onClick={() => void load(locationId || null, rollQuery, rollOffset + 100)}>Berikutnya</button></div></footer></section>

        {draftId && selectedOrder && <SkuWaveReferences waveId={draftId} modelId={selectedOrder.model_id}/>}
        <section className="ccut-card wide"><header><span>04 · HASIL PER ROLL & SIZE</span><strong>Angka sumber direkonsiliasi backend</strong></header>{!formFactsReady ? <p data-cutting-form-retired>Muat ulang sumber sebelum memeriksa jumlah roll dan hasil rencana. Isian operator tetap disimpan.</p> : selected.length === 0 ? <div className="ccut-empty">Pilih minimal satu roll dari gudang bahan.</div> : <div className="ccut-table-wrap"><table><thead><tr><th>Roll</th><th>Keluar</th><th>Terpakai</th><th>Sisa</th>{slots.map((slot) => <th key={slot.key}>Size {slot.sizeCode}</th>)}<th>Total pcs</th></tr></thead><tbody>{selected.map((item) => { const consumed = numeric(item.consumed); const rowPieces = slots.reduce((sum, slot) => sum + count(yields[item.roll.id]?.[slot.key] ?? '0'), 0); return <tr key={item.roll.id}><th><strong>{item.roll.roll_number}</strong><small>{item.roll.material_name}</small></th><td>{item.issued} {item.roll.unit_code}</td><td><input aria-label={`${item.roll.roll_number} terpakai`} aria-invalid={parseQuantityInput(item.consumed, 'MEASURE', item.issued) === null} inputMode="decimal" value={item.consumed} onChange={(event) => setSelectedRolls((current) => ({ ...current, [item.roll.id]: { ...current[item.roll.id], consumed: event.target.value } }))}/></td><td className={consumed > item.issued ? 'bad' : ''}>{display(item.issued - consumed, 2)}</td>{slots.map((slot) => <td key={slot.key}><input aria-label={`${item.roll.roll_number} Size ${slot.sizeCode}`} aria-invalid={parseQuantityInput(yields[item.roll.id]?.[slot.key] ?? '0') === null} inputMode="numeric" value={yields[item.roll.id]?.[slot.key] ?? '0'} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setYields((current) => ({ ...current, [item.roll.id]: { ...current[item.roll.id], [slot.key]: event.target.value } }))}/></td>)}<td><strong>{display(rowPieces)}</strong></td></tr>})}</tbody></table></div>}</section>

        <NativeCuttingYieldPanel groupId={draftId ?? lastCommittedGroupId} sourceKey={JSON.stringify([authorityKey,sourceEpoch,draftId,draftVersion,orderId,pattern,selectedRolls,slots,yields,cutAt])} parentBusy={writerLocked} onAuthorityLost={onAuthorityLost}/>
        <NativeCuttingInputsPanel groupId={draftId ?? lastCommittedGroupId} sourceKey={JSON.stringify([authorityKey,sourceEpoch,draftId,draftVersion,orderId,pattern,selectedRolls,slots,yields,cutAt])} parentBusy={writerLocked} onAuthorityLost={onAuthorityLost}/>
        <NativeCuttingLearningPanel groupId={draftId ?? lastCommittedGroupId} sourceKey={JSON.stringify([authorityKey,sourceEpoch,draftId,draftVersion,orderId,pattern,selectedRolls,slots,yields,cutAt])} parentBusy={writerLocked} onAuthorityLost={onAuthorityLost}/>
        <section className="ccut-review"><div><span>ROLL</span><strong>{formFactsReady ? selected.length : "—"}</strong></div><div><span>KELUAR</span><strong>{formFactsReady ? totalIssued.toFixed(2) : "—"}</strong></div><div><span>TERPAKAI</span><strong>{formFactsReady ? display(totalConsumed, 2) : "—"}</strong></div><div><span>SISA</span><strong>{formFactsReady ? display(totalRemaining, 2) : "—"}</strong></div><div><span>HASIL</span><strong>{formFactsReady ? display(totalPieces) + " pcs" : "—"}</strong></div></section>
        {poMode === 'AUTO' ? <footer className="ccut-actions"><span>{autoDraft ? `Draf PO otomatis · versi ${autoDraft.version}` : 'PO baru · nomor dibuat saat disahkan'}</span><div>{autoDraft && <button className="danger" disabled={!canCreate || writerLocked} onClick={() => void saveAuto('DELETE')}><Trash2/> Hapus draf</button>}<button disabled={!formValid || writerLocked || !canCreate || !autoWorkspace?.canDraft} onClick={() => void saveAuto('SAVE_DRAFT')}>Simpan draft</button><button className="primary" disabled={!formValid || writerLocked || !canCreate || !canPost || !autoWorkspace?.canPost} onClick={() => void saveAuto('POST')}>{saving ? <LoaderCircle className="spin"/> : <Check/>} Sahkan & buat PO</button></div></footer> : <footer className="ccut-actions"><span>{draftId ? `Draft ${draftId.slice(0, 8)} · row version ${draftVersion}` : 'Transaksi baru · ID dibuat backend'}</span><div>{draftId && <button className="danger" disabled={Boolean(selectionIssue) || !canEdit || writerLocked} onClick={() => void removeDraft()}><Trash2/> Hapus draft</button>}<button disabled={Boolean(selectionIssue) || !formValid || writerLocked || (draftId ? !canEdit : !canCreate)} onClick={() => void save('SAVE_DRAFT')}>Simpan draft</button><button className="primary" disabled={Boolean(selectionIssue) || !formValid || writerLocked || (draftId ? !canEdit : !canCreate) || !canPost} onClick={() => void save('POST')}>{saving ? <LoaderCircle className="spin"/> : <Check/>} Post ke WIP Potongan</button></div></footer>}
      </main>
    </div>
  </section>
}
