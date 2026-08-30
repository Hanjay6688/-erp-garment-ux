import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { PropsWithChildren } from 'react'
import type { SupabaseClient } from '@supabase/supabase-js'
import { isUatRuntime, type RuntimeConfig } from '../config/runtime'
import { ClientAppError, normalizeAuthError, normalizeClientError } from '../lib/clientError'
import { getUatSupabaseClient } from '../lib/supabase'
import type { PreconnectDatabase } from '../types/database.preconnect'
import {
  identityFromProfileLookupError,
  identityFromProfileRead,
  planAuthEvent,
  resolveOwnProfile,
} from './authPolicy'
import type { AuthIdentity } from './authPolicy'
export type { AppRole, AppUserProfile, AuthIdentity } from './authPolicy'

type AuthActionResult = { ok: true } | { ok: false; error: ClientAppError }

type AuthContextValue = {
  runtime: RuntimeConfig
  identity: AuthIdentity
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

async function readOwnProfile(client: SupabaseClient<PreconnectDatabase>, authUserId: string) {
  return resolveOwnProfile(async (expectedAuthUserId) => {
    const { data, error } = await client
      .from('v_erp_my_profile')
      .select('id, auth_user_id, full_name, role, is_active, row_version')
      .eq('auth_user_id', expectedAuthUserId)
      .maybeSingle()
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
  const client = useMemo(() => isUatRuntime(runtime) ? getUatSupabaseClient(runtime) : null, [runtime])

  const commitIdentity = useCallback((next: AuthIdentity) => {
    identityRef.current = next
    if (mounted.current) setIdentity(next)
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

      let profileRead
      try {
        profileRead = await readOwnProfile(client, data.user.id)
      } catch (error) {
        if (sequence === refreshSequence.current && mounted.current) {
          commitIdentity(identityFromProfileLookupError(error))
        }
        return
      }

      if (sequence !== refreshSequence.current || !mounted.current) return
      commitIdentity(identityFromProfileRead(profileRead))
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
    const { data: { subscription } } = client.auth.onAuthStateChange((event, session) => {
      const plan = planAuthEvent(identityRef.current, event, session?.user.id ?? null)
      if (plan.invalidatePending) refreshSequence.current += 1
      if (plan.immediateIdentity) commitIdentity(plan.immediateIdentity)
      if (!plan.refreshAfterCallback) return

      // Supabase warns against awaiting client calls inside this callback. The UI is
      // already locked above; verified user/profile refresh starts after callback exit.
      globalThis.setTimeout(() => {
        if (mounted.current) void refreshIdentity(false)
      }, 0)
    })

    return () => {
      mounted.current = false
      subscription.unsubscribe()
    }
  }, [client, commitIdentity, refreshIdentity])

  const signIn = useCallback(async (email: string, password: string): Promise<AuthActionResult> => {
    if (!client) {
      const error = new ClientAppError('AUTH_FAILED', 'Auth tidak aktif pada mode demo.')
      return { ok: false, error }
    }
    const { error } = await client.auth.signInWithPassword({ email: email.trim(), password })
    if (error) {
      const normalized = normalizeAuthError(error)
      if (mounted.current) commitIdentity({ status: 'ANONYMOUS', error: normalized })
      return { ok: false, error: normalized }
    }
    await refreshIdentity()
    return { ok: true }
  }, [client, commitIdentity, refreshIdentity])

  const signOut = useCallback(async (): Promise<AuthActionResult> => {
    if (!client) return { ok: true }
    const previousIdentity = identityRef.current
    refreshSequence.current += 1
    commitIdentity({ status: 'LOADING' })
    const { error } = await client.auth.signOut()
    if (error) {
      const normalized = normalizeAuthError(error)
      if (identityRef.current.status === 'LOADING') commitIdentity(previousIdentity)
      return { ok: false, error: normalized }
    }
    refreshSequence.current += 1
    if (mounted.current) commitIdentity({ status: 'ANONYMOUS', error: null })
    return { ok: true }
  }, [client, commitIdentity])

  const value = useMemo<AuthContextValue>(() => ({
    runtime,
    identity,
    signIn,
    signOut,
    retryIdentity: () => refreshIdentity(),
  }), [identity, refreshIdentity, runtime, signIn, signOut])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth harus dipakai di dalam AuthProvider.')
  return value
}
