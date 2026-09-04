import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, Database, LoaderCircle, RefreshCw, Search, Trash2, UserRound } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import ConnectedPatternFilter from './ConnectedPatternFilter'
import {
  draftPickupAllocations,
  parsePickupQueue,
  parsePickupSaveResult,
  pickupAllocationState,
  pickupBatchesPayload,
  seedPickupAllocations,
  type PickupAllocationMatrix,
  type PickupQueue,
  type PickupQueueRow,
} from './cuttingPersistence'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import './connected-pickup.css'

type PickupFilter = 'WAITING' | 'PICKED' | 'ALL'
type AllocationMode = 'ROLL' | 'SIZE'

function datetimeLocal(value: Date | string) {
  const date = value instanceof Date ? value : new Date(value)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function initialBatchCount(row: PickupQueueRow) {
  if (row.pickup?.batches.length) return Math.max(...row.pickup.batches.map((batch) => batch.batch_no))
  return Math.max(1, Math.min(3, row.rolls.length))
}

export default function ConnectedPickupPage() {
  const { runtime, identity } = useAuth()
  if (runtime.mode !== 'UAT_AUTH_SIMULATION') throw new Error('ConnectedPickupPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const canCreate = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.distribution.create')
  const canEdit = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.distribution.edit_draft')
  const canPost = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.distribution.post')
  const [queue, setQueue] = useState<PickupQueue | null>(null)
  const [filter, setFilter] = useState<PickupFilter>('WAITING')
  const [patternId, setPatternId] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [selectedId, setSelectedId] = useState('')
  const [contractorId, setContractorId] = useState('')
  const [pickedUpAt, setPickedUpAt] = useState(() => datetimeLocal(new Date()))
  const [mode, setMode] = useState<AllocationMode>('ROLL')
  const [batchCount, setBatchCount] = useState(1)
  const [notes, setNotes] = useState<string[]>([''])
  const [matrix, setMatrix] = useState<PickupAllocationMatrix>({})
  const [pickupId, setPickupId] = useState<string | null>(null)
  const [pickupVersion, setPickupVersion] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const requestRef = useRef<{ fingerprint: string; id: string }>({ fingerprint: '', id: '' })
  const savingRef = useRef(false)
  const loadRequestRef = useRef(0)
  const viewRef = useRef({ filter, patternId, query })
  viewRef.current = { filter, patternId, query }

  const fetchQueue = useCallback(async (
    nextFilter: PickupFilter, nextPattern: string, nextQuery: string, nextOffset = 0,
  ) => {
    const requestId = ++loadRequestRef.current
    setLoading(true)
    setError('')
    try {
      const { data, error: loadError } = await client.rpc('erp_get_cutting_pickup_queue_v1', {
        p_filter: nextFilter,
        p_pattern_id: nextPattern || null,
        p_query: nextQuery.trim() || null,
        p_limit: 100,
        p_offset: nextOffset,
      })
      if (requestId !== loadRequestRef.current) return null
      if (loadError) {
        setError(normalizeClientError(loadError).message)
        return null
      }
      const parsed = parsePickupQueue(data)
      setQueue(parsed)
      setOffset(parsed.offset)
      return parsed
    } catch (loadFailure) {
      if (requestId === loadRequestRef.current) {
        setError(loadFailure instanceof Error ? loadFailure.message : normalizeClientError(loadFailure).message)
      }
      return null
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false)
    }
  }, [client])

  useEffect(() => { void fetchQueue('WAITING', '', '') }, [fetchQueue])

  const selected = queue?.rows.find((row) => row.cutting_group_id === selectedId) ?? queue?.rows[0] ?? null
  const selectedGroupId = selected?.cutting_group_id ?? ''
  const selectedPickupVersion = selected?.pickup?.row_version ?? null
  const selectedGroupVersion = selected?.row_version ?? null
  const selectedAssignedContractor = selected?.assigned_contractor_id ?? ''
  const contractorSignature = queue?.contractors.map((contractor) => contractor.id).join('|') ?? ''

  useEffect(() => {
    if (!selected) return
    const count = initialBatchCount(selected)
    const nextMode = selected.pickup?.allocation_mode ?? 'ROLL'
    setSelectedId(selected.cutting_group_id)
    setContractorId(selected.pickup?.contractor_id ?? selected.assigned_contractor_id ?? queue?.contractors[0]?.id ?? '')
    setPickedUpAt(datetimeLocal(selected.pickup?.picked_up_at ?? new Date()))
    setMode(nextMode)
    setBatchCount(count)
    setNotes(Array.from({ length: count }, (_, index) => selected.pickup?.batches.find((batch) => batch.batch_no === index + 1)?.notes ?? ''))
    setMatrix(selected.pickup ? draftPickupAllocations(selected.pickup, count) : seedPickupAllocations(selected, count, nextMode))
    setPickupId(selected.pickup?.status === 'DRAFT' ? selected.pickup.id : null)
    setPickupVersion(selected.pickup?.status === 'DRAFT' ? selected.pickup.row_version : null)
    requestRef.current = { fingerprint: '', id: '' }
  }, [contractorSignature, selectedAssignedContractor, selectedGroupId, selectedGroupVersion, selectedPickupVersion]) // eslint-disable-line react-hooks/exhaustive-deps

  const changeFilter = async (next: PickupFilter) => {
    setFilter(next)
    setOffset(0)
    setSelectedId('')
    await fetchQueue(next, patternId, query, 0)
  }
  const changePattern = async (next: string) => {
    setPatternId(next)
    setOffset(0)
    setSelectedId('')
    await fetchQueue(filter, next, query, 0)
  }
  const refresh = () => fetchQueue(filter, patternId, query, offset)
  const search = () => { setOffset(0); setSelectedId(''); return fetchQueue(filter, patternId, query, 0) }

  const sourceRows = selected?.rolls.flatMap((roll) => roll.yields.map((yieldRow) => ({ roll, yieldRow }))) ?? []
  const allocation = selected ? pickupAllocationState(selected, matrix, batchCount) : {
    sourceTotal: 0, allocatedTotal: 0, exact: false, batchTotals: [], everyBatchUsed: false,
  }
  const overAllocated = sourceRows.some(({ yieldRow }) =>
    (matrix[yieldRow.yield_id] ?? []).reduce((sum, qty) => sum + Math.max(0, Number(qty) || 0), 0) > yieldRow.qty_pcs)
  const posted = selected?.pickup?.status === 'POSTED' || selected?.picked_up_at !== null
  const editable = Boolean(selected?.pickup_eligible && !posted)
  const mutationAllowed = pickupId ? canEdit : canCreate
  const pickedAtValid = pickedUpAt.length > 0 && Number.isFinite(new Date(pickedUpAt).getTime())
  const contractorOptions = selected?.assigned_contractor_id
    ? queue?.contractors.filter((contractor) => contractor.id === selected.assigned_contractor_id) ?? []
    : queue?.contractors ?? []
  const selectedContractorMissing = Boolean(
    contractorId && !queue?.contractors.some((contractor) => contractor.id === contractorId),
  )
  const assignedContractorMissing = Boolean(selected?.assigned_contractor_id && selectedContractorMissing)
  const draftValid = Boolean(
    selected && editable && contractorId && pickedAtValid && !overAllocated
      && !selectedContractorMissing && batchCount >= 1,
  )
  const postValid = draftValid && allocation.exact && allocation.everyBatchUsed

  const resizeBatches = (nextRaw: number) => {
    const next = Math.max(1, Math.min(12, Math.floor(nextRaw) || 1))
    setBatchCount(next)
    setNotes((current) => Array.from({ length: next }, (_, index) => current[index] ?? ''))
    setMatrix((current) => Object.fromEntries(sourceRows.map(({ yieldRow }) => [
      yieldRow.yield_id,
      Array.from({ length: next }, (_, index) => current[yieldRow.yield_id]?.[index] ?? 0),
    ])))
  }

  const changeMode = (next: AllocationMode) => {
    if (!selected) return
    setMode(next)
    setMatrix(seedPickupAllocations(selected, batchCount, next))
  }

  const payload = (action: 'SAVE_DRAFT' | 'POST') => ({
    ...(pickupId ? { id: pickupId } : {}),
    action,
    cutting_group_id: selected?.cutting_group_id,
    contractor_id: contractorId,
    picked_up_at: new Date(pickedUpAt).toISOString(),
    allocation_mode: mode,
    expected_group_version: selected?.row_version,
    change_reason: action === 'POST' ? 'Posting pickup dari Bagi Potongan connected' : 'Simpan draft Bagi Potongan connected',
    batches: pickupBatchesPayload(matrix, notes, batchCount),
  })

  const save = async (action: 'SAVE_DRAFT' | 'POST') => {
    if (savingRef.current || !mutationAllowed || (action === 'POST' ? !postValid || !canPost : !draftValid)) return
    savingRef.current = true
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const nextPayload = payload(action)
      const fingerprint = JSON.stringify({ payload: nextPayload, expected: pickupVersion })
      if (requestRef.current.fingerprint !== fingerprint) requestRef.current = { fingerprint, id: globalThis.crypto.randomUUID() }
      const { data, error: saveError } = await client.rpc('erp_save_cutting_pickup_v1', {
        p_payload: nextPayload,
        p_client_request_id: requestRef.current.id,
        p_expected_version: pickupVersion,
      })
      if (saveError) throw normalizeClientError(saveError)
      const result = parsePickupSaveResult(data)
      setNotice(result.status === 'POSTED'
        ? `${selected?.group_number} terposting · ${result.batch_count} batch / ${result.allocated_pieces} pcs masuk Sewing.`
        : `Draft pickup tersimpan · row version ${result.row_version}.`)
      const currentView = viewRef.current
      await fetchQueue(currentView.filter, currentView.patternId, currentView.query, 0)
    } catch (saveFailure) {
      setError(saveFailure instanceof Error ? saveFailure.message : String(saveFailure))
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  const removeDraft = async () => {
    if (!selected || !pickupId || pickupVersion === null || savingRef.current || !canEdit) return
    if (!globalThis.confirm('Hapus draft pembagian ini? Potongan tetap aman di antrean.')) return
    savingRef.current = true
    setSaving(true)
    setError('')
    try {
      const { data, error: deleteError } = await client.rpc('erp_save_cutting_pickup_v1', {
        p_payload: {
          id: pickupId, action: 'DELETE', cutting_group_id: selected.cutting_group_id,
          expected_group_version: selected.row_version, change_reason: 'Hapus draft Bagi Potongan connected',
        },
        p_client_request_id: globalThis.crypto.randomUUID(),
        p_expected_version: pickupVersion,
      })
      if (deleteError) throw normalizeClientError(deleteError)
      parsePickupSaveResult(data)
      setNotice('Draft pembagian dihapus; Potongan kembali bersih di antrean.')
      const currentView = viewRef.current
      await fetchQueue(currentView.filter, currentView.patternId, currentView.query, 0)
    } catch (deleteFailure) {
      setError(deleteFailure instanceof Error ? deleteFailure.message : String(deleteFailure))
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return <section className="connected-pickup-page">
    <header className="cpick-hero"><div><span>PRODUKSI · DISTRIBUSI CONNECTED</span><h1>Bagi Potongan</h1><p>Pola, roll, dan hasil per size dibaca dari Potongan kanonik. Pickup hanya membagi sumber itu ke Mandor dan Batch Distribusi.</p></div><button type="button" onClick={() => void refresh()}><RefreshCw/> Refetch</button></header>
    <div className="cpick-truth"><Database/><strong>ERP ENTENG UAT · RPC CONNECTED</strong><span>Tidak ada selector Pola kedua dan tidak ada direct-table write.</span></div>
    {error ? <div className="cpick-message error" role="alert"><AlertTriangle/><span>{error}</span><button type="button" onClick={() => setError('')}>Tutup</button></div> : null}
    {notice ? <div className="cpick-message success" role="status"><Check/><span>{notice}</span></div> : null}

    <section className="cpick-toolbar">
      <div className="cpick-tabs">{(['WAITING', 'PICKED', 'ALL'] as const).map((value) => <button type="button" className={filter === value ? 'active' : ''} onClick={() => void changeFilter(value)} key={value}>{value === 'WAITING' ? 'Menunggu' : value === 'PICKED' ? 'Sudah diambil' : 'Semua'}</button>)}</div>
      <label className="cpick-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void search() }} placeholder="Nomor Potongan, PO, model, Pola, Mandor…"/><button type="button" onClick={() => void search()}>Cari</button></label>
      <ConnectedPatternFilter value={patternId} onChange={(next) => void changePattern(next)}/>
    </section>

    <div className="cpick-layout">
      <aside className="cpick-queue"><header><span>ANTREAN BACKEND</span><strong>{queue?.total ?? 0} Potongan</strong></header>{loading ? <div className="cpick-empty"><LoaderCircle className="spin"/> Memuat antrean…</div> : queue?.rows.map((row) => <button type="button" className={selected?.cutting_group_id === row.cutting_group_id ? 'active' : ''} onClick={() => setSelectedId(row.cutting_group_id)} key={row.cutting_group_id}><span><small>{row.po_number}</small><strong>{row.group_number}</strong><em>{row.model_code} · {row.model_name}</em></span><span><b>{row.total_pieces} pcs</b><small>{row.pattern_code ? `${row.pattern_code} · ${row.pattern_revision}` : 'Pola legacy kosong'}</small></span></button>)}{!loading && queue?.rows.length === 0 ? <div className="cpick-empty">Tidak ada Potongan pada filter ini.</div> : null}<footer className="cpick-pagination"><span>{queue?.total ? `${offset + 1}–${offset + (queue?.rows.length ?? 0)} dari ${queue.total}` : '0 Potongan'}</span><div><button type="button" disabled={loading || offset === 0} onClick={() => void fetchQueue(filter, patternId, query, Math.max(0, offset - 100))}>Sebelumnya</button><button type="button" disabled={loading || !queue || offset + queue.rows.length >= queue.total} onClick={() => void fetchQueue(filter, patternId, query, offset + 100)}>Berikutnya</button></div></footer></aside>

      <main className="cpick-workspace">
        {!selected ? <div className="cpick-empty large">Pilih Potongan dari antrean.</div> : <>
          <header className="cpick-selected"><div><span>{selected.po_number} · ROW VERSION {selected.row_version}</span><h2>{selected.group_number} · {selected.model_name}</h2><p>{selected.pattern_code ? `${selected.pattern_code} · ${selected.pattern_revision} · ${selected.pattern_name}` : 'Histori legacy tanpa Pola'} · {selected.source_location_code ?? 'Lokasi legacy kosong'}</p></div><em className={posted ? 'posted' : selected.pickup_eligible ? 'ready' : 'blocked'}>{posted ? 'SUDAH DIAMBIL' : selected.pickup_eligible ? 'SIAP DIBAGI' : 'BUTUH REVIEW'}</em></header>
          <section className="cpick-facts"><div><span>POTONGAN</span><strong>{selected.total_pieces} pcs</strong></div><div><span>ROLL</span><strong>{selected.rolls.length}</strong></div><div><span>BAHAN KELUAR</span><strong>{selected.total_qty_issued}</strong></div><div><span>POLA SNAPSHOT</span><strong>{selected.pattern_code ?? '—'} · {selected.pattern_revision ?? '—'}</strong></div></section>
          <section className="cpick-setup"><label>Mandor<select value={contractorId} disabled={!editable || Boolean(selected.assigned_contractor_id)} onChange={(event) => setContractorId(event.target.value)}><option value="">Pilih Mandor…</option>{contractorOptions.map((contractor) => <option value={contractor.id} key={contractor.id}>{contractor.code} · {contractor.name}</option>)}{selectedContractorMissing ? <option value={contractorId}>{selected.assigned_contractor_name ?? selected.pickup?.contractor_name ?? 'Mandor tidak aktif'} · TIDAK AKTIF</option> : null}</select>{assignedContractorMissing ? <small role="alert">Mandor yang dikunci di Production Order sudah tidak aktif. Aktifkan kembali atau ubah penugasan PO sebelum pickup.</small> : selectedContractorMissing ? <small role="alert">Mandor pada draft sudah tidak aktif. Pilih Mandor aktif sebelum menyimpan atau posting.</small> : selected.assigned_contractor_id ? <small>Mandor dikunci mengikuti penugasan Production Order.</small> : null}</label><label>Waktu fisik diambil<input type="datetime-local" value={pickedUpAt} disabled={!editable} onChange={(event) => setPickedUpAt(event.target.value)}/></label><label>Jumlah batch<div><button type="button" disabled={!editable || batchCount <= 1} onClick={() => resizeBatches(batchCount - 1)}>−</button><strong>{batchCount}</strong><button type="button" disabled={!editable || batchCount >= 12} onClick={() => resizeBatches(batchCount + 1)}>+</button></div></label><fieldset disabled={!editable}><legend>Susun awal</legend><button type="button" className={mode === 'ROLL' ? 'active' : ''} onClick={() => changeMode('ROLL')}>Per roll</button><button type="button" className={mode === 'SIZE' ? 'active' : ''} onClick={() => changeMode('SIZE')}>Per size</button></fieldset></section>
          <section className="cpick-table-wrap"><table><thead><tr><th>Sumber kanonik</th><th>Size</th><th>Qty</th>{Array.from({ length: batchCount }, (_, index) => <th key={index}>Batch {index + 1}</th>)}</tr></thead><tbody>{sourceRows.map(({ roll, yieldRow }) => <tr key={yieldRow.yield_id}><th><strong>{roll.roll_number}</strong><small>{roll.material_name}</small></th><td>{yieldRow.size_code}{yieldRow.label ? ` · ${yieldRow.label}` : ''}</td><td><strong>{yieldRow.qty_pcs}</strong></td>{Array.from({ length: batchCount }, (_, batchIndex) => <td key={batchIndex}><input aria-label={`${roll.roll_number} ${yieldRow.size_code} Batch ${batchIndex + 1}`} inputMode="numeric" disabled={!editable} value={matrix[yieldRow.yield_id]?.[batchIndex] ?? 0} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setMatrix((current) => ({ ...current, [yieldRow.yield_id]: Array.from({ length: batchCount }, (_, index) => index === batchIndex ? Math.max(0, Math.floor(Number(event.target.value.replace(/\D/g, '')) || 0)) : current[yieldRow.yield_id]?.[index] ?? 0) }))}/></td>)}</tr>)}</tbody><tfoot><tr><th colSpan={3}>TOTAL BATCH</th>{allocation.batchTotals.map((qty, index) => <th key={index}>{qty} pcs</th>)}</tr></tfoot></table></section>
          <section className="cpick-notes">{Array.from({ length: batchCount }, (_, index) => <label key={index}><span>Catatan Batch {index + 1}</span><input disabled={!editable} value={notes[index] ?? ''} onChange={(event) => setNotes((current) => Array.from({ length: batchCount }, (_, noteIndex) => noteIndex === index ? event.target.value : current[noteIndex] ?? ''))} placeholder="Warna / arahan jahitan…"/></label>)}</section>
          <section className={`cpick-reconcile ${allocation.exact && allocation.everyBatchUsed ? 'ready' : 'blocked'}`}><div><span>SUMBER</span><strong>{allocation.sourceTotal} pcs</strong></div><div><span>TERBAGI</span><strong>{allocation.allocatedTotal} pcs</strong></div><div><span>SELISIH</span><strong>{allocation.sourceTotal - allocation.allocatedTotal} pcs</strong></div><p>{overAllocated ? 'Ada baris melebihi sumber Potongan.' : allocation.exact && allocation.everyBatchUsed ? 'Seluruh sumber persis terbagi dan setiap batch terpakai.' : 'Draft boleh belum penuh; posting menunggu rekonsiliasi persis.'}</p></section>
          <footer className="cpick-actions"><span>{posted ? `Posted oleh ${selected.pickup?.contractor_name}` : pickupId ? `Draft ${pickupId.slice(0, 8)} · version ${pickupVersion}` : 'Pickup baru · ID dibuat backend'}</span><div>{pickupId ? <button type="button" className="danger" disabled={saving || !canEdit} onClick={() => void removeDraft()}><Trash2/> Hapus draft</button> : null}<button type="button" disabled={saving || !mutationAllowed || !draftValid} onClick={() => void save('SAVE_DRAFT')}>Simpan draft</button><button type="button" className="primary" disabled={saving || !mutationAllowed || !canPost || !postValid} onClick={() => void save('POST')}>{saving ? <LoaderCircle className="spin"/> : <UserRound/>} Catat pickup & masuk Sewing</button></div></footer>
        </>}
      </main>
    </div>
  </section>
}
