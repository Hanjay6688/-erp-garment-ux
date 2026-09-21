import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { normalizeClientError } from './lib/clientError'
import type { Json } from './types/database.preconnect'
import {
  clearProductionEnvelope, domainLabels, hasProductionPending, isDefiniteInitialRejection,
  observeProductionRecovery, persistProductionEnvelope, productionLockManager, productionLockName,
  readProductionRecovery, type ProductionDomain, type ProductionEnvelope,
} from './productionRecovery'

type ReadTicket = { sequence: number; scope: string; signature: string | null; session: object }
export type ProductionMutationHandlers = {
  send: (envelope: ProductionEnvelope) => PromiseLike<{ data: unknown; error: unknown }>
  validate: (data: unknown, envelope: ProductionEnvelope) => void
  retire: (data: unknown, envelope: ProductionEnvelope) => void
  reload: () => Promise<boolean>
}

export function useProductionMutation(domain: ProductionDomain) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi produksi belum authorized.')
  const scope = `${runtime.projectRef}:${identity.profile.id}`
  const permissionSignature = identity.permissions.join('|')
  const session = useMemo(() => ({ scope }), [scope, identity.profile.rowVersion, identity.profile.roleRowVersion, permissionSignature])
  const sessionRef = useRef(session)
  sessionRef.current = session
  const mountedRef = useRef(false)
  const scopeRef = useRef(scope)
  scopeRef.current = scope
  const initial = useMemo(() => readProductionRecovery(scope), [scope])
  const [observed, setObserved] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [committedSequence, setCommittedSequence] = useState(0)
  const busyRef = useRef(false)
  const readyRef = useRef(false)
  const readSequence = useRef(0)
  const readySignature = useRef<string | null>(null)
  const readScope = useRef(scope)
  const supported = productionLockManager() !== null

  const invalidate = useCallback(() => { readyRef.current = false; setReady(false) }, [])
  const synchronize = useCallback(() => {
    invalidate()
    setObserved(readProductionRecovery(scope))
  }, [invalidate, scope])
  useEffect(() => {
    mountedRef.current = true
    busyRef.current = false
    setBusy(false)
    readSequence.current += 1
    readySignature.current = null
    setError(''); setNotice(''); setCommittedSequence(0)
    synchronize()
    const stop = observeProductionRecovery(scope, synchronize)
    return () => { mountedRef.current = false; readyRef.current = false; readSequence.current += 1; stop() }
  }, [scope, session, synchronize])

  const beginRead = useCallback((): ReadTicket => {
    invalidate()
    setError('')
    const current = readProductionRecovery(scope)
    setObserved(current)
    return { sequence: ++readSequence.current, scope, signature: current.signature, session }
  }, [invalidate, scope, session])
  const isReadCurrent = useCallback((ticket: ReadTicket) =>
    mountedRef.current && ticket.scope === scopeRef.current && ticket.sequence === readSequence.current
      && ticket.session === sessionRef.current && ticket.signature === readProductionRecovery(scope).signature, [scope])
  const finishRead = useCallback((ticket: ReadTicket) => {
    if (!isReadCurrent(ticket)) return false
    const current = readProductionRecovery(scope)
    setObserved(current)
    const fresh = !current.corrupted && !hasProductionPending(current)
      && ticket.signature !== null && current.signature === ticket.signature
    readyRef.current = fresh
    readySignature.current = fresh ? current.signature : null
    readScope.current = ticket.scope
    setReady(fresh)
    return fresh
  }, [scope, isReadCurrent])

  const execute = useCallback(async (
    input: { action: string; payload: Json; expectedVersion: number | null } | null,
    handlers: ProductionMutationHandlers,
  ) => {
    if (!mountedRef.current || busyRef.current || sessionRef.current !== session) return false
    if (input && (!readyRef.current || readScope.current !== scope)) return false
    const manager = productionLockManager()
    if (!manager) { setError('Web Locks tidak tersedia. Data bisa dibaca; transaksi tetap terkunci.'); return false }
    busyRef.current = true
    setBusy(true); setError(''); setNotice('')
    try {
      return await manager.request(productionLockName(scope), { mode: 'exclusive', ifAvailable: true }, async (lock) => {
        if (!mountedRef.current || sessionRef.current !== session) return false
        const current = readProductionRecovery(scope)
        setObserved(current)
        if (!lock || current.corrupted) {
          invalidate()
          setError(current.corrupted ? 'Recovery envelope rusak atau tidak terbaca. Writer dikunci; jejak lama dipertahankan untuk rekonsiliasi teknis.' : 'Transaksi produksi sedang berjalan di tab lain. Refetch sesudah transaksi itu selesai.')
          return false
        }
        if (input && (hasProductionPending(current) || current.signature !== readySignature.current || !readyRef.current)) {
          invalidate()
          setError('Transaksi/state produksi berubah. Selesaikan recovery yang tertunda lalu Refetch sebelum aksi baru.')
          return false
        }
        let envelope = current.pending[domain]
        if (input) {
          const canonical = JSON.parse(JSON.stringify(input, (_key, value: unknown) => {
            if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Payload memuat angka tidak valid.')
            return value
          })) as typeof input
          envelope = { ...canonical, fingerprint: JSON.stringify(canonical), id: globalThis.crypto.randomUUID(), createdAt: new Date().toISOString() }
          if (!persistProductionEnvelope(scope, domain, envelope)) {
            synchronize()
            setError('Envelope idempotency tidak dapat disimpan. Tidak ada request yang dikirim ke server.')
            return false
          }
        }
        if (!envelope) { invalidate(); return false }
        invalidate()
        setObserved(readProductionRecovery(scope))
        let result: { data: unknown; error: unknown }
        try { result = await handlers.send(envelope) }
        catch (failure) {
          if (sessionRef.current === session) setError(`Respons transaksi tidak pasti: ${normalizeClientError(failure).message}. Reconcile memakai UUID/payload lama.`)
          return false
        }
        if (!mountedRef.current || sessionRef.current !== session) return false
        if (result.error) {
          // A rejection on replay (e.g. permission revoked before the server's
          // idempotency lookup) says nothing about the original COMMIT.
          if (!input || !isDefiniteInitialRejection(result.error)) {
            setError('Hasil transaksi masih belum pasti. UUID/payload lama disimpan; reconcile lagi saat hasil lama dapat dipastikan.')
            return false
          }
          if (!clearProductionEnvelope(scope, domain, envelope)) {
            synchronize(); setError('Server menolak transaksi, tetapi envelope lokal belum bisa dibersihkan. Writer tetap terkunci.'); return false
          }
          setObserved(readProductionRecovery(scope))
          const refreshed = await handlers.reload()
          setError(`${normalizeClientError(result.error).message}${refreshed ? '' : ' Refetch authoritative gagal; writer tetap terkunci.'}`)
          return false
        }
        try { handlers.validate(result.data, envelope) }
        catch {
          setError('Respons sukses tidak membawa UUID/action yang cocok dengan kontrak transaksi. UUID/payload lama tetap disimpan untuk Reconcile transaksi.')
          return false
        }
        handlers.retire(result.data, envelope)
        setCommittedSequence((sequence) => sequence + 1)
        if (!clearProductionEnvelope(scope, domain, envelope)) {
          synchronize(); setError('Server committed, tetapi envelope lokal belum bisa dibersihkan. Form lama tetap mati dan writer terkunci.'); return false
        }
        setObserved(readProductionRecovery(scope))
        const refreshed = await handlers.reload()
        if (!mountedRef.current || sessionRef.current !== session) return false
        if (refreshed) setNotice(input ? 'Workspace authoritative sudah dimuat ulang.' : 'Transaksi sudah direconcile dengan UUID lama; workspace authoritative dimuat ulang.')
        else setError('Aksi sudah tersimpan, tetapi refresh authoritative gagal. Jangan ulangi aksi; seluruh writer terkunci sampai Refetch berhasil.')
        return refreshed
      })
    } catch (failure) {
      if (sessionRef.current === session) { invalidate(); setError(`Transaksi belum dapat dipastikan: ${normalizeClientError(failure).message}. Writer tetap terkunci.`) }
      return false
    } finally {
      if (sessionRef.current === session) { busyRef.current = false; setBusy(false); setObserved(readProductionRecovery(scope)) }
    }
  }, [domain, invalidate, scope, session, synchronize])
  const run = useCallback((action: string, payload: Json, expectedVersion: number | null, handlers: ProductionMutationHandlers) =>
    execute({ action, payload, expectedVersion }, handlers), [execute])
  const reconcile = useCallback((handlers: ProductionMutationHandlers) => execute(null, handlers), [execute])
  const pending = observed.pending[domain] ?? null
  const foreignDomain = (Object.keys(observed.pending) as ProductionDomain[]).find((name) => name !== domain)
  const blockReason = observed.corrupted
    ? 'Envelope idempotency lokal rusak atau tidak terbaca. Jejak transaksi lama dipertahankan; writer dikunci untuk rekonsiliasi teknis.'
    : foreignDomain ? `Transaksi ${domainLabels[foreignDomain]} belum selesai. Buka halaman itu untuk recovery; penulisan produksi terkait tetap terkunci.`
      : !supported ? 'Web Locks tidak tersedia. Data tetap bisa dibaca, tetapi writer dikunci.'
        : pending ? 'Hasil transaksi belum diketahui di halaman ini atau tab lain. Reconcile transaksi memakai UUID dan payload lama, termasuk setelah reload.'
          : !ready ? 'Data belum dimuat ulang. Refetch wajib berhasil sebelum transaksi berikutnya.' : ''
  return {
    scope, busy, pending, error, notice, blockReason, committedSequence,
    corruptedEnvelope: observed.corrupted, externalMutationBlocked: Boolean(foreignDomain),
    workspaceStale: !ready, writerLocked: busy || !ready || readScope.current !== scope || !supported || observed.corrupted || hasProductionPending(observed),
    beginRead, finishRead, isReadCurrent, invalidate, run, reconcile,
  }
}
