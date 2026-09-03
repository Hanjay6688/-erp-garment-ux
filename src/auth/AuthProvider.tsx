import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { PropsWithChildren } from 'react'
import type { SupabaseClient } from '@supabase/supabase-js'
import { isUatRuntime, type RuntimeConfig } from '../config/runtime'
import { ClientAppError, normalizeAuthError, normalizeClientError } from '../lib/clientError'
import { getUatSupabaseClient } from '../lib/supabase'
import type { PreconnectDatabase } from '../types/database.preconnect'
import {
  identityFromAccessLookupError,
  identityFromAccessRead,
  planAuthEvent,
  resolveOwnAccess,
} from './authPolicy'
import type { AuthIdentity } from './authPolicy'
export type { AppRole, AppUserProfile, AuthIdentity, AuthorizedAccess } from './authPolicy'

type AuthActionResult = { ok: true } | { ok: false; error: ClientAppError }

type AuthContextValue = {
  runtime: RuntimeConfig
  identity: AuthIdentity
  signingOut: boolean
  signOutError: ClientAppError | null
  signIn: (email: string, password: string) => Promise<AuthActionResult>
  signOut: () => Promise<AuthActionResult>
  retryIdentity: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function isExpectedMissingSession(error: unknown) {
  if (!error || typeof error !== 'object') return false
  const candidate = error as { name?: unknown; code?: unknown; message?: unknown }
  const code = typeof candidate.code === 'string' ? candidate.code.toLowerCase() : ''
  const message = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : ''
  return candidate.name === 'AuthSessionMissingError'
    || code === 'session_not_found'
    || code === 'auth_session_missing'
    || message.includes('auth session missing')
}

async function readOwnAccess(client: SupabaseClient<PreconnectDatabase>, authUserId: string) {
  return resolveOwnAccess(async () => {
    const { data, error } = await client.rpc('erp_get_my_access_v1')
    return { data, error }
  }, authUserId)
}

export function AuthProvider({ runtime, children }: PropsWithChildren<{ runtime: RuntimeConfig }>) {
  const [identity, setIdentity] = useState<AuthIdentity>(() => runtime.mode === 'DEMO_SIMULATION'
    ? { status: 'DEMO' }
    : { status: 'LOADING' })
  const identityRef = useRef<AuthIdentity>(runtime.mode === 'DEMO_SIMULATION'
    ? { status: 'DEMO' }
    : { status: 'LOADING' })
  const mounted = useRef(false)
  const refreshSequence = useRef(0)
  const signOutInFlight = useRef<Promise<AuthActionResult> | null>(null)
  const [signingOut, setSigningOut] = useState(false)
  const [signOutError, setSignOutError] = useState<ClientAppError | null>(null)
  const client = useMemo(() => isUatRuntime(runtime) ? getUatSupabaseClient(runtime) : null, [runtime])

  const commitIdentity = useCallback((next: AuthIdentity) => {
    identityRef.current = next
    if (mounted.current) {
      setIdentity(next)
      if (next.status === 'AUTHORIZED' || next.status === 'ANONYMOUS') setSignOutError(null)
    }
  }, [])

  const refreshIdentity = useCallback(async (showLoading = true) => {
    if (!client) {
      if (mounted.current) commitIdentity({ status: 'DEMO' })
      return
    }

    const sequence = ++refreshSequence.current
    if (showLoading && mounted.current) commitIdentity({ status: 'LOADING' })

    try {
      const { data, error } = await client.auth.getUser()
      if (error || !data.user) {
        if (sequence === refreshSequence.current && mounted.current) {
          commitIdentity({
            status: 'ANONYMOUS',
            error: error && !isExpectedMissingSession(error) ? normalizeAuthError(error) : null,
          })
        }
        return
      }

      let accessRead
      try {
        accessRead = await readOwnAccess(client, data.user.id)
      } catch (error) {
        if (sequence === refreshSequence.current && mounted.current) {
          commitIdentity(identityFromAccessLookupError(error))
        }
        return
      }

      if (sequence !== refreshSequence.current || !mounted.current) return
      commitIdentity(identityFromAccessRead(accessRead))
    } catch (error) {
      const normalized = normalizeClientError(error)
      if (sequence === refreshSequence.current && mounted.current) {
        commitIdentity({ status: 'ANONYMOUS', error: normalized })
      }
    }
  }, [client, commitIdentity])

  useEffect(() => {
    mounted.current = true
    void refreshIdentity()

    if (!client) return () => { mounted.current = false }
    let revalidationTimer: ReturnType<typeof globalThis.setTimeout> | null = null
    let revalidationInFlight = false
    const authRefreshTimers = new Set<ReturnType<typeof globalThis.setTimeout>>()

    const scheduleProfileRevalidation = () => {
      if (!mounted.current || signOutInFlight.current || revalidationTimer !== null || revalidationInFlight) return
      revalidationTimer = globalThis.setTimeout(() => {
        revalidationTimer = null
        if (!mounted.current || signOutInFlight.current || revalidationInFlight) return
        revalidationInFlight = true
        void refreshIdentity(false).finally(() => { revalidationInFlight = false })
      }, 0)
    }
    const handleFocus = () => {
      if (document.visibilityState === 'visible') scheduleProfileRevalidation()
    }
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') scheduleProfileRevalidation()
    }

    const { data: { subscription } } = client.auth.onAuthStateChange((event, session) => {
      const plan = planAuthEvent(identityRef.current, event, session?.user.id ?? null)
      if (plan.invalidatePending) refreshSequence.current += 1
      if (plan.immediateIdentity) commitIdentity(plan.immediateIdentity)
      if (!plan.refreshAfterCallback) return

      // Supabase warns against awaiting client calls inside this callback. The UI is
      // already locked above; verified user/profile refresh starts after callback exit.
      const timer = globalThis.setTimeout(() => {
        authRefreshTimers.delete(timer)
        if (mounted.current) void refreshIdentity(false)
      }, 0)
      authRefreshTimers.add(timer)
    })
    globalThis.window.addEventListener('focus', handleFocus)
    globalThis.document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      mounted.current = false
      refreshSequence.current += 1
      if (revalidationTimer !== null) globalThis.clearTimeout(revalidationTimer)
      authRefreshTimers.forEach((timer) => globalThis.clearTimeout(timer))
      authRefreshTimers.clear()
      globalThis.window.removeEventListener('focus', handleFocus)
      globalThis.document.removeEventListener('visibilitychange', handleVisibilityChange)
      subscription.unsubscribe()
    }
  }, [client, commitIdentity, refreshIdentity])

  const signIn = useCallback(async (email: string, password: string): Promise<AuthActionResult> => {
    if (!client) {
      const error = new ClientAppError('AUTH_FAILED', 'Auth tidak aktif pada mode demo.')
      return { ok: false, error }
    }
    const sequence = ++refreshSequence.current
    try {
      const { error } = await client.auth.signInWithPassword({ email: email.trim(), password })
      if (error) {
        const normalized = normalizeAuthError(error)
        if (sequence === refreshSequence.current && mounted.current) {
          commitIdentity({ status: 'ANONYMOUS', error: normalized })
        }
        return { ok: false, error: normalized }
      }
    } catch (error) {
      const normalized = normalizeAuthError(error)
      if (sequence === refreshSequence.current && mounted.current) {
        commitIdentity({ status: 'ANONYMOUS', error: normalized })
      }
      return { ok: false, error: normalized }
    }
    await refreshIdentity()
    return { ok: true }
  }, [client, commitIdentity, refreshIdentity])

  const signOut = useCallback((): Promise<AuthActionResult> => {
    if (!client) return Promise.resolve({ ok: true })
    if (signOutInFlight.current) return signOutInFlight.current

    const previousIdentity = identityRef.current
    const sequence = ++refreshSequence.current
    if (mounted.current) {
      setSigningOut(true)
      setSignOutError(null)
    }
    commitIdentity({ status: 'LOADING' })

    const operation = (async (): Promise<AuthActionResult> => {
      const failed = (error: unknown): AuthActionResult => {
        const normalized = normalizeAuthError(error)
        const canRestore = sequence === refreshSequence.current && identityRef.current.status === 'LOADING'
        if (canRestore) {
          commitIdentity(previousIdentity)
          if (mounted.current) setSignOutError(normalized)
        }
        return { ok: false, error: normalized }
      }

      try {
        const { error } = await client.auth.signOut()
        if (error) return failed(error)
      } catch (error) {
        return failed(error)
      }

      refreshSequence.current += 1
      commitIdentity({ status: 'ANONYMOUS', error: null })
      return { ok: true }
    })()

    signOutInFlight.current = operation
    const finish = () => {
      if (signOutInFlight.current === operation) signOutInFlight.current = null
      if (mounted.current) setSigningOut(false)
    }
    void operation.then(finish, finish)
    return operation
  }, [client, commitIdentity])

  const value = useMemo<AuthContextValue>(() => ({
    runtime,
    identity,
    signingOut,
    signOutError,
    signIn,
    signOut,
    retryIdentity: () => refreshIdentity(),
  }), [identity, refreshIdentity, runtime, signIn, signOut, signOutError, signingOut])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth harus dipakai di dalam AuthProvider.')
  return value
}
