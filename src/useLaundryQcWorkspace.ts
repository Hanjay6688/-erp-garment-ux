import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import {
  parseFinalSkuProductSearch, parseLaundryBsProductSearch, parseLaundryQcWorkspace,
  type Cp6LaundryBsProductSearchPage, type Cp6ProductSearchPage,
  type LaundryQcAction, type LaundryQcScope,
  type LaundryQcWorkspace,
} from './laundryQcModel'
import type { Json } from './types/database.preconnect'

type PendingMutation = {
  action: LaundryQcAction
  payload: Json
  expectedVersion: number | null
  fingerprint: string
  id: string
  createdAt: string
}

const actions = new Set<LaundryQcAction>([
  'POST_DELIVERY', 'POST_RECEIPT', 'POST_FAILED_WASH', 'REVERSE_DELIVERY',
  'REVERSE_RECEIPT', 'POST_FINAL_SKU', 'REVERSE_FINAL_SKU',
])
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function storageKey(projectRef: string, appUserId: string) {
  // One user may have Laundry and QC open in different tabs. The envelope is
  // intentionally global to every CP6 writer surface so an uncertain action
  // can never be hidden by navigating to another scope.
  return `erp.cp6.pending-mutation.v1:${projectRef}:${appUserId}`
}

function mutationLockName(key: string) {
  return `${key}:exclusive-writer`
}

function mutationLockManager() {
  try {
    const manager = globalThis.navigator?.locks
    return manager && typeof manager.request === 'function' ? manager : null
  } catch {
    return null
  }
}

type PendingRead = { envelope: PendingMutation | null; corrupted: boolean }

function readPending(key: string): PendingRead {
  try {
    const raw = globalThis.localStorage?.getItem(key)
    if (!raw) return { envelope: null, corrupted: false }
    const candidate = JSON.parse(raw) as Partial<PendingMutation>
    const expectedVersionValid = candidate.expectedVersion === null
      || typeof candidate.expectedVersion === 'number' && Number.isSafeInteger(candidate.expectedVersion)
    const fingerprint = JSON.stringify({
      action: candidate.action,
      payload: candidate.payload,
      expectedVersion: candidate.expectedVersion,
    })
    if (!candidate.action || !actions.has(candidate.action)
      || !uuidPattern.test(candidate.id ?? '')
      || typeof candidate.createdAt !== 'string'
      || !expectedVersionValid || candidate.payload === undefined
      || candidate.fingerprint !== fingerprint) {
      return { envelope: null, corrupted: true }
    }
    return { envelope: candidate as PendingMutation, corrupted: false }
  } catch {
    return { envelope: null, corrupted: true }
  }
}

function persistPending(key: string, pending: PendingMutation) {
  try {
    const serialized = JSON.stringify(pending)
    globalThis.localStorage?.setItem(key, serialized)
    return globalThis.localStorage?.getItem(key) === serialized
  } catch {
    return false
  }
}

function clearPending(key: string) {
  try {
    globalThis.localStorage?.removeItem(key)
    return globalThis.localStorage?.getItem(key) === null
  } catch {
    return false
  }
}

function preserveExactPending(key: string, envelope: PendingMutation) {
  const current = readPending(key)
  if (current.corrupted) return false
  if (current.envelope) {
    return current.envelope.id === envelope.id
      && current.envelope.fingerprint === envelope.fingerprint
  }
  return persistPending(key, envelope)
}

function isDefiniteRejection(error: unknown) {
  if (error === null || typeof error !== 'object') return false
  const candidate = error as { code?: unknown; status?: unknown }
  const code = typeof candidate.code === 'string' ? candidate.code.trim().toUpperCase() : ''
  const status = typeof candidate.status === 'number' ? candidate.status : Number.NaN

  // PostgREST group-0 connection failures and internal X failures remain
  // ambiguous even when an intermediary attaches a 4xx status. Only a
  // received, non-retriable 4xx or a database statement error outside
  // connection/resource/shutdown classes proves rollback strongly enough to
  // retire the UUID. Clearing an uncertain envelope could turn a lost COMMIT
  // response into a second business transaction with a fresh UUID.
  if (/^PGRST(?:0[0-9]{2}|X[0-9]{2})$/.test(code)) return false
  if (Number.isFinite(status) && status >= 400 && status < 500
    && ![408, 425, 429].includes(status)) return true
  if (!/^[0-9A-Z]{5}$/.test(code) || /^PGRST/.test(code)) return false
  return !['08', '53', '57', '58'].includes(code.slice(0, 2))
}

function isAmbiguousFailure(error: unknown) {
  return !isDefiniteRejection(error)
}

function isExactCommittedResponse(data: unknown, envelope: PendingMutation) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return false
  const value = data as Record<string, unknown>
  return value.contract_version === 'CP6_V2620'
    && value.committed === true
    && value.action === envelope.action
    && value.client_request_id === envelope.id
}

export function useLaundryQcWorkspace(scope: LaundryQcScope) {
  const { runtime, identity } = useAuth()
  if (runtime.mode !== 'UAT_AUTH_SIMULATION' || identity.status !== 'AUTHORIZED') {
    throw new Error('Connected Laundry/QC hanya untuk sesi ERP Enteng UAT yang authorized.')
  }
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const key = useMemo(
    () => storageKey(runtime.projectRef, identity.profile.id),
    [identity.profile.id, runtime.projectRef],
  )
  const mutationLockSupported = mutationLockManager() !== null
  const initialPending = useMemo(() => readPending(key), [key])
  const [workspace, setWorkspace] = useState<LaundryQcWorkspace | null>(null)
  const [pending, setPending] = useState<PendingMutation | null>(initialPending.envelope)
  const [corruptedEnvelope, setCorruptedEnvelope] = useState(initialPending.corrupted)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [workspaceStale, setWorkspaceStale] = useState(true)
  const [externalMutationBlocked, setExternalMutationBlocked] = useState(false)
  const [committedRefreshRequired, setCommittedRefreshRequired] = useState(false)
  const [committedSequence, setCommittedSequence] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const busyRef = useRef(false)
  // React state reaches the DOM on the next render. This synchronous flag
  // closes the writer in the current event turn, including refetch/search and
  // cross-tab storage events, so a stale callback cannot dispatch old facts.
  const workspaceReadyRef = useRef(false)
  const loadRequestRef = useRef(0)
  const queryRef = useRef(query)
  queryRef.current = query

  const load = useCallback(async (nextQuery = queryRef.current) => {
    const requestId = ++loadRequestRef.current
    workspaceReadyRef.current = false
    setLoading(true)
    setWorkspaceStale(true)
    try {
      const { data, error: loadError } = await client.rpc('erp_get_laundry_qc_workspace_v1', {
        p_scope: scope,
        p_query: nextQuery.trim() || null,
      })
      if (requestId !== loadRequestRef.current) return false
      if (loadError) throw loadError
      const parsed = parseLaundryQcWorkspace(data)
      setWorkspace(parsed)
      const observed = readPending(key)
      if (!observed.corrupted && observed.envelope === null) setExternalMutationBlocked(false)
      setError(mutationLockSupported ? '' : 'Browser ini tidak menyediakan Web Locks. Data tetap bisa dibaca, tetapi semua writer CP6 dikunci agar dua tab tidak dapat menggandakan transaksi.')
      workspaceReadyRef.current = true
      setWorkspaceStale(false)
      return true
    } catch (failure) {
      if (requestId === loadRequestRef.current) {
        workspaceReadyRef.current = false
        setWorkspaceStale(true)
        setError(normalizeClientError(failure).message)
      }
      return false
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false)
    }
  }, [client, key, mutationLockSupported, scope])

  const sendExact = useCallback(async (envelope: PendingMutation) => {
    return client.rpc('erp_save_laundry_qc_action_v1', {
      p_action: envelope.action,
      p_payload: envelope.payload,
      p_client_request_id: envelope.id,
      p_expected_version: envelope.expectedVersion,
    })
  }, [client])

  const searchFinalSkuProducts = useCallback(async (
    sourceBatchSizeLineId: string,
    physicalAt: string,
    productQuery: string,
    afterSortKey: string | null = null,
  ): Promise<Cp6ProductSearchPage> => {
    const { data, error: searchError } = await client.rpc('erp_search_final_sku_products_v1', {
      p_source_laundry_receipt_batch_size_line_id: sourceBatchSizeLineId,
      p_physical_at: physicalAt,
      p_query: productQuery.trim() || null,
      p_after_sort_key: afterSortKey,
      p_limit: 50,
    })
    if (searchError) throw searchError
    const page = parseFinalSkuProductSearch(data)
    if (page.source_laundry_receipt_batch_size_line_id !== sourceBatchSizeLineId
      || Date.parse(page.physical_at) !== Date.parse(physicalAt)
      || page.page_limit !== 50) {
      throw new Error('Respons pencarian Final SKU tidak cocok dengan sumber/waktu yang diminta.')
    }
    return page
  }, [client])

  const searchLaundryBsProducts = useCallback(async (
    deliveryBatchSizeLineId: string,
    physicalAt: string,
    productQuery: string,
    afterSortKey: string | null = null,
  ): Promise<Cp6LaundryBsProductSearchPage> => {
    const { data, error: searchError } = await client.rpc('erp_search_laundry_bs_products_v1', {
      p_delivery_batch_size_line_id: deliveryBatchSizeLineId,
      p_physical_at: physicalAt,
      p_query: productQuery.trim() || null,
      p_after_sort_key: afterSortKey,
      p_limit: 50,
    })
    if (searchError) throw searchError
    const page = parseLaundryBsProductSearch(data)
    if (page.source_delivery_batch_size_line_id !== deliveryBatchSizeLineId
      || Date.parse(page.physical_at) !== Date.parse(physicalAt)
      || page.page_limit !== 50) {
      throw new Error('Respons pencarian SKU Laundry-BS tidak cocok dengan sumber/waktu yang diminta.')
    }
    return page
  }, [client])

  const reconcile = useCallback(async () => {
    const manager = mutationLockManager()
    if (!manager) {
      setError('Web Lock lintas-tab tidak tersedia. Writer CP6 tetap dikunci; gunakan browser UAT yang didukung sebelum rekonsiliasi.')
      return false
    }
    if (corruptedEnvelope || busyRef.current) return false
    busyRef.current = true
    setBusy(true)
    setError('')
    setNotice('Mencocokkan UUID dan payload lama dengan hasil transaksi authoritative…')
    try {
      return await manager.request(mutationLockName(key), {
        mode: 'exclusive', ifAvailable: true,
      }, async (lock) => {
        if (!lock) {
          const observed = readPending(key)
          setExternalMutationBlocked(true)
          setWorkspaceStale(true)
          if (observed.corrupted) setCorruptedEnvelope(true)
          if (observed.envelope) setPending(observed.envelope)
          setError('Writer CP6 sedang aktif di tab lain. Tab ini tetap dikunci sampai envelope global selesai dan fakta authoritative dimuat ulang.')
          return false
        }
        setExternalMutationBlocked(false)
        const persisted = readPending(key)
        if (persisted.corrupted) {
          setCorruptedEnvelope(true)
          setError('Envelope idempotency lokal rusak. Writer dikunci agar transaksi lama tidak terkirim ulang sebagai transaksi baru; minta rekonsiliasi teknis.')
          return false
        }
        const envelope = persisted.envelope ?? pending
        if (!envelope) return false
        if (!preserveExactPending(key, envelope)) {
          setCorruptedEnvelope(true)
          setError('Envelope UUID/payload global tidak dapat dipertahankan tepat. Tidak ada request rekonsiliasi yang dikirim.')
          return false
        }
        const { data, error: mutationError } = await sendExact(envelope)
        if (mutationError) {
          if (isAmbiguousFailure(mutationError)) {
            if (!preserveExactPending(key, envelope)) setCorruptedEnvelope(true)
            setPending(envelope)
            setError('Hasil transaksi masih belum pasti. Writer tetap terkunci; reconcile lagi saat koneksi stabil.')
            return false
          }
          if (!clearPending(key)) {
            setError('Server sudah memberi jawaban pasti, tetapi envelope lokal belum bisa dibersihkan. Writer tetap terkunci.')
            return false
          }
          setPending(null)
          const rejection = normalizeClientError(mutationError).message
          const refreshed = await load()
          setError(refreshed
            ? rejection
            : `${rejection} Refetch authoritative juga gagal; writer tetap terkunci.`)
          return false
        }
        if (!isExactCommittedResponse(data, envelope)) {
          if (!preserveExactPending(key, envelope)) setCorruptedEnvelope(true)
          setPending(envelope)
          setError('Respons sukses tidak membawa envelope CP6/UUID/action yang cocok. Hasil dianggap belum pasti; reconcile wajib memakai UUID/payload lama.')
          return false
        }
        if (!clearPending(key)) {
          setError('Transaksi cocok, tetapi envelope lokal belum bisa dibersihkan. Writer tetap terkunci.')
          return false
        }
        setPending(null)
        setCorruptedEnvelope(false)
        setCommittedRefreshRequired(true)
        setCommittedSequence((current) => current + 1)
        setNotice('Transaksi ditemukan tepat satu kali. Memuat ulang fakta authoritative…')
        const refreshed = await load()
        if (refreshed) setNotice('Reconcile selesai; UUID lama cocok dan workspace sudah authoritative.')
        else setError('Transaksi sudah committed, tetapi refetch gagal. Form lama tetap mati sampai refetch berhasil.')
        return refreshed
      })
    } catch (failure) {
      setError(`Kunci/reconcile CP6 gagal: ${normalizeClientError(failure).message}. Writer tetap terkunci.`)
      setWorkspaceStale(true)
      return false
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }, [corruptedEnvelope, key, load, pending, sendExact])

  const runAction = useCallback(async (
    action: LaundryQcAction,
    payload: Json,
    expectedVersion: number | null,
    retireCommittedForm: () => void,
  ) => {
    if (busyRef.current || !workspaceReadyRef.current || pending || corruptedEnvelope || committedRefreshRequired
      || workspaceStale || externalMutationBlocked) return false
    const manager = mutationLockManager()
    if (!manager) {
      setError('Web Lock lintas-tab tidak tersedia. Tidak ada request yang dikirim; writer CP6 tetap read-only.')
      return false
    }
    busyRef.current = true
    setBusy(true)
    setError('')
    try {
      return await manager.request(mutationLockName(key), {
        mode: 'exclusive', ifAvailable: true,
      }, async (lock) => {
        if (!lock) {
          const observed = readPending(key)
          workspaceReadyRef.current = false
          setExternalMutationBlocked(true)
          setWorkspaceStale(true)
          if (observed.corrupted) setCorruptedEnvelope(true)
          if (observed.envelope) setPending(observed.envelope)
          setError('Writer CP6 sedang aktif di tab lain. Request kedua tidak dikirim dan tab ini dikunci sampai refetch authoritative.')
          return false
        }
        setExternalMutationBlocked(false)
        const observed = readPending(key)
        if (observed.corrupted) {
          setCorruptedEnvelope(true)
          setError('Envelope global rusak. Tidak ada request baru yang dikirim; minta rekonsiliasi teknis.')
          return false
        }
        if (observed.envelope) {
          setPending(observed.envelope)
          setError('Masih ada transaksi CP6 yang belum direkonsiliasi. Request baru tidak dikirim; gunakan UUID/payload global yang lama.')
          return false
        }
        const id = globalThis.crypto.randomUUID()
        const fingerprint = JSON.stringify({ action, payload, expectedVersion })
        const envelope: PendingMutation = {
          action, payload, expectedVersion, fingerprint, id, createdAt: new Date().toISOString(),
        }
        if (!persistPending(key, envelope)) {
          setError('Envelope idempotency tidak dapat disimpan. Tidak ada request yang dikirim ke server.')
          return false
        }
        setPending(envelope)
        setNotice('Mengirim satu transaksi atomic dengan UUID yang sudah dipersist…')
        try {
          const { data, error: mutationError } = await sendExact(envelope)
          if (mutationError) {
            if (isAmbiguousFailure(mutationError)) {
              if (!preserveExactPending(key, envelope)) setCorruptedEnvelope(true)
              setError('Respons jaringan tidak pasti. UUID/payload lama disimpan dan semua writer dikunci sampai reconcile.')
              return false
            }
            if (!clearPending(key)) {
              setError('Server menolak transaksi, tetapi envelope lokal belum bisa dibersihkan. Writer tetap terkunci.')
              return false
            }
            setPending(null)
            const rejection = normalizeClientError(mutationError).message
            setNotice('')
            const refreshed = await load()
            setError(refreshed
              ? rejection
              : `${rejection} Refetch authoritative juga gagal; writer tetap terkunci.`)
            return false
          }
          if (!isExactCommittedResponse(data, envelope)) {
            if (!preserveExactPending(key, envelope)) setCorruptedEnvelope(true)
            setError('Respons sukses tidak membawa envelope CP6/UUID/action yang cocok. UUID/payload lama tetap disimpan dan writer dikunci untuk reconcile.')
            return false
          }
          if (!clearPending(key)) {
            setError('Server berhasil, tetapi envelope lokal belum bisa dibersihkan. Form dinonaktifkan untuk mencegah duplikasi.')
            setCommittedRefreshRequired(true)
            setCommittedSequence((current) => current + 1)
            retireCommittedForm()
            return false
          }
          setPending(null)
          setCommittedRefreshRequired(true)
          setCommittedSequence((current) => current + 1)
          retireCommittedForm()
          setNotice('Server committed tepat satu kali. Form lama sudah dimatikan; refetch authoritative berjalan…')
          const refreshed = await load()
          if (refreshed) setNotice('Transaksi committed dan workspace authoritative sudah dimuat ulang.')
          else setError('Transaksi sudah committed, tetapi refetch gagal. Form lama tetap mati dan writer terkunci.')
          return refreshed
        } catch (failure) {
          if (!preserveExactPending(key, envelope)) setCorruptedEnvelope(true)
          setPending(envelope)
          setError(`Respons transaksi tidak pasti: ${normalizeClientError(failure).message}. Reconcile wajib memakai UUID/payload yang sama.`)
          return false
        }
      })
    } catch (failure) {
      workspaceReadyRef.current = false
      setWorkspaceStale(true)
      setError(`Kunci writer CP6 gagal: ${normalizeClientError(failure).message}. Tidak ada request baru yang boleh dikirim.`)
      return false
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }, [committedRefreshRequired, corruptedEnvelope, externalMutationBlocked, key, load, pending, sendExact, workspaceStale])

  useEffect(() => {
    const synchronizeGlobalEnvelope = (event: StorageEvent) => {
      if (event.key !== key || event.storageArea && event.storageArea !== globalThis.localStorage) return
      const observed = readPending(key)
      workspaceReadyRef.current = false
      setWorkspaceStale(true)
      setExternalMutationBlocked(true)
      if (observed.corrupted) {
        setPending(null)
        setCorruptedEnvelope(true)
        setError('Envelope global berubah menjadi rusak di tab lain. Semua writer CP6 dikunci untuk rekonsiliasi teknis.')
        return
      }
      setCorruptedEnvelope(false)
      setPending(observed.envelope)
      if (observed.envelope) {
        setError('Ada transaksi CP6 aktif di tab lain. Semua halaman Laundry/QC dikunci pada UUID global yang sama.')
        return
      }
      setNotice('Transaksi CP6 dari tab lain selesai; memuat ulang fakta authoritative…')
      void load().then((refreshed) => {
        if (refreshed) setNotice('Fakta authoritative lintas-tab sudah dimuat ulang.')
      })
    }
    globalThis.addEventListener('storage', synchronizeGlobalEnvelope)
    return () => globalThis.removeEventListener('storage', synchronizeGlobalEnvelope)
  }, [key, load])

  useEffect(() => {
    if (initialPending.corrupted) {
      setError('Envelope idempotency lokal rusak. Writer dikunci agar transaksi lama tidak digandakan; minta rekonsiliasi teknis.')
    } else if (initialPending.envelope) void reconcile()
    else void load()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const acknowledgeCommittedFormRetired = useCallback((sequence: number) => {
    if (sequence <= 0 || sequence !== committedSequence || workspaceStale
      || !workspaceReadyRef.current || pending !== null || corruptedEnvelope || busyRef.current) return false
    setCommittedRefreshRequired(false)
    return true
  }, [committedSequence, corruptedEnvelope, pending, workspaceStale])

  const search = (next: string) => {
    setQuery(next)
    void load(next)
  }
  const writerLocked = busy || pending !== null || corruptedEnvelope || committedRefreshRequired
    || workspaceStale || externalMutationBlocked || !mutationLockSupported
  return {
    workspace, query, loading, busy, error, notice, pending,
    corruptedEnvelope, workspaceStale, externalMutationBlocked,
    committedRefreshRequired, committedSequence, writerLocked,
    search, load, runAction, reconcile, searchFinalSkuProducts, searchLaundryBsProducts,
    acknowledgeCommittedFormRetired,
  }
}
