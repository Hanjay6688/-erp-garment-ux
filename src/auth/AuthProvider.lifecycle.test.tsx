// @vitest-environment jsdom

import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UatRuntimeConfig } from '../config/runtime'
import { AuthProvider, useAuth } from './AuthProvider'

const mockedClient = vi.hoisted(() => ({ current: null as unknown }))

vi.mock('../lib/supabase', () => ({
  getUatSupabaseClient: () => mockedClient.current,
}))

const ownerA = '018f7c2e-7b8a-7ab1-8d4a-1234567890ab'
const ownerB = '018f7c2e-7b8a-7ab1-8d4a-1234567890bb'
const runtime: UatRuntimeConfig = {
  mode: 'UAT_AUTH_SIMULATION',
  authMode: 'UAT_SUPABASE',
  businessDataMode: 'PARTIAL_CONNECTED',
  businessRpcEnabled: true,
  accessControlMode: 'CONNECTED',
  patternMode: 'CONNECTED',
  cuttingMode: 'CONNECTED',
  distributionMode: 'CONNECTED',
  wipStatusMode: 'CONNECTED',
  projectRef: 'siimvrusnzxexizpyoib',
  supabaseUrl: 'https://siimvrusnzxexizpyoib.supabase.co',
  browserKey: 'sb_publishable_test_only_1234567890',
}

const profileRows = {
  [ownerA]: {
    id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ac',
    auth_user_id: ownerA,
    full_name: 'Owner A',
    role_id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ad',
    role_code: 'OWNER',
    role_name: 'Owner',
    is_active: true,
    row_version: 1,
    role_row_version: 1,
  },
  [ownerB]: {
    id: '018f7c2e-7b8a-7ab1-8d4a-1234567890bc',
    auth_user_id: ownerB,
    full_name: 'Owner B',
    role_id: '018f7c2e-7b8a-7ab1-8d4a-1234567890bd',
    role_code: 'OWNER',
    role_name: 'Owner',
    is_active: true,
    row_version: 2,
    role_row_version: 1,
  },
}

function accessBundle(authUserId: string) {
  return {
    allowed: true,
    profile: profileRows[authUserId as keyof typeof profileRows] ?? null,
    permissions: ['settings.access.manage', 'production.wip.view'],
    external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }
}

type AuthCallback = (event: string, session: { user: { id: string } } | null) => unknown

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolver) => { resolve = resolver })
  return { promise, resolve }
}

function authResult(userId: string | null) {
  return { data: { user: userId ? { id: userId } : null }, error: null }
}

function makeClient(options: {
  getUser: () => Promise<ReturnType<typeof authResult>>
  signIn?: () => Promise<{ error: unknown }>
  signOut?: () => Promise<{ error: unknown }>
  accessForUser?: (authUserId: string) => unknown
}) {
  let callback: AuthCallback | null = null
  let currentAuthUserId = ''
  const unsubscribe = vi.fn()
  const getUser = vi.fn(async () => {
    const result = await options.getUser()
    currentAuthUserId = result.data.user?.id ?? ''
    return result
  })
  const client = {
    rpc: vi.fn(async () => ({
      data: options.accessForUser
        ? options.accessForUser(currentAuthUserId)
        : accessBundle(currentAuthUserId),
      error: null,
    })),
    auth: {
      getUser,
      signInWithPassword: vi.fn(options.signIn ?? (async () => ({ error: null }))),
      signOut: vi.fn(options.signOut ?? (async () => ({ error: null }))),
      onAuthStateChange: vi.fn((nextCallback: AuthCallback) => {
        callback = nextCallback
        return { data: { subscription: { unsubscribe } } }
      }),
    },
  }

  return {
    client,
    unsubscribe,
    fire(event: string, userId: string | null) {
      if (!callback) throw new Error('Auth listener was not registered.')
      return callback(event, userId ? { user: { id: userId } } : null)
    },
  }
}

let container: HTMLDivElement
let root: Root
let observed: ReturnType<typeof useAuth> | null

function Harness() {
  observed = useAuth()
  return <div data-status={observed.identity.status}>{observed.identity.status}</div>
}

function status() {
  return container.firstElementChild?.getAttribute('data-status')
}

async function settle() {
  await act(async () => {
    await new Promise((resolve) => globalThis.setTimeout(resolve, 0))
  })
}

async function mount(strict = false) {
  await act(async () => {
    root.render(strict
      ? <StrictMode><AuthProvider runtime={runtime}><Harness /></AuthProvider></StrictMode>
      : <AuthProvider runtime={runtime}><Harness /></AuthProvider>)
  })
  await settle()
}

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  observed = null
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  vi.restoreAllMocks()
})

describe('AuthProvider mounted lifecycle', () => {
  it('locks a signed-out event immediately and ignores the stale in-flight user response', async () => {
    const firstUser = deferred<ReturnType<typeof authResult>>()
    const fake = makeClient({ getUser: () => firstUser.promise })
    mockedClient.current = fake.client

    await mount()
    let callbackResult: unknown
    await act(async () => {
      callbackResult = fake.fire('SIGNED_OUT', null)
    })
    expect(callbackResult).toBeUndefined()
    expect(status()).toBe('ANONYMOUS')

    firstUser.resolve(authResult(ownerA))
    await settle()
    expect(status()).toBe('ANONYMOUS')
  })

  it('locks an account switch before the deferred replacement profile is verified', async () => {
    const switchedUser = deferred<ReturnType<typeof authResult>>()
    const getUser = vi.fn()
      .mockResolvedValueOnce(authResult(ownerA))
      .mockImplementationOnce(() => switchedUser.promise)
    const fake = makeClient({ getUser })
    mockedClient.current = fake.client

    await mount()
    expect(status()).toBe('AUTHORIZED')
    expect(observed?.identity).toMatchObject({ profile: { authUserId: ownerA } })

    await act(async () => {
      expect(fake.fire('SIGNED_IN', ownerB)).toBeUndefined()
    })
    await settle()
    expect(status()).toBe('LOADING')

    switchedUser.resolve(authResult(ownerB))
    await settle()
    expect(status()).toBe('AUTHORIZED')
    expect(observed?.identity).toMatchObject({ profile: { authUserId: ownerB } })
  })

  it('restores the verified identity when sign-out fails after the immediate lock', async () => {
    const signOut = deferred<{ error: unknown }>()
    const fake = makeClient({
      getUser: async () => authResult(ownerA),
      signOut: () => signOut.promise,
    })
    mockedClient.current = fake.client

    await mount()
    expect(status()).toBe('AUTHORIZED')

    let outcomePromise!: ReturnType<NonNullable<typeof observed>['signOut']>
    await act(async () => {
      outcomePromise = observed!.signOut()
      await Promise.resolve()
    })
    expect(status()).toBe('LOADING')

    signOut.resolve({ error: { message: 'network unavailable', status: 503 } })
    let outcome: Awaited<typeof outcomePromise>
    await act(async () => { outcome = await outcomePromise })
    expect(outcome!).toMatchObject({ ok: false })
    expect(status()).toBe('AUTHORIZED')
    expect(observed?.identity).toMatchObject({ profile: { authUserId: ownerA } })
  })

  it('normalizes a rejected sign-in and remains fail-closed', async () => {
    const fake = makeClient({
      getUser: async () => authResult(null),
      signIn: async () => { throw new TypeError('fetch failed') },
    })
    mockedClient.current = fake.client

    await mount()
    let outcome: Awaited<ReturnType<NonNullable<typeof observed>['signIn']>>
    await act(async () => {
      outcome = await observed!.signIn('owner@example.test', 'not-a-real-password')
    })

    expect(outcome!).toMatchObject({
      ok: false,
      error: { code: 'BACKEND_UNAVAILABLE', retryable: true },
    })
    expect(status()).toBe('ANONYMOUS')
    expect(observed?.identity).toMatchObject({
      status: 'ANONYMOUS',
      error: { code: 'BACKEND_UNAVAILABLE' },
    })
  })

  it('normalizes a rejected sign-out and restores only the unchanged verified identity', async () => {
    const fake = makeClient({
      getUser: async () => authResult(ownerA),
      signOut: async () => { throw new TypeError('network unavailable') },
    })
    mockedClient.current = fake.client

    await mount()
    let outcome: Awaited<ReturnType<NonNullable<typeof observed>['signOut']>>
    await act(async () => { outcome = await observed!.signOut() })

    expect(outcome!).toMatchObject({ ok: false, error: { code: 'BACKEND_UNAVAILABLE' } })
    expect(status()).toBe('AUTHORIZED')
    expect(observed?.signOutError).toMatchObject({ code: 'BACKEND_UNAVAILABLE' })
  })

  it('does not restore an old identity when SIGNED_OUT wins a rejected sign-out race', async () => {
    const deferredSignOut = deferred<{ error: unknown }>()
    const fake = makeClient({
      getUser: async () => authResult(ownerA),
      signOut: () => deferredSignOut.promise,
    })
    mockedClient.current = fake.client

    await mount()
    let outcomePromise!: ReturnType<NonNullable<typeof observed>['signOut']>
    await act(async () => {
      outcomePromise = observed!.signOut()
      await Promise.resolve()
      fake.fire('SIGNED_OUT', null)
    })
    expect(status()).toBe('ANONYMOUS')

    deferredSignOut.resolve({ error: { message: 'late network error', status: 503 } })
    await act(async () => { await outcomePromise })
    expect(status()).toBe('ANONYMOUS')
    expect(observed?.signOutError).toBeNull()
  })

  it('deduplicates concurrent sign-out calls into one provider request', async () => {
    const deferredSignOut = deferred<{ error: unknown }>()
    const fake = makeClient({
      getUser: async () => authResult(ownerA),
      signOut: () => deferredSignOut.promise,
    })
    mockedClient.current = fake.client

    await mount()
    let first!: ReturnType<NonNullable<typeof observed>['signOut']>
    let second!: ReturnType<NonNullable<typeof observed>['signOut']>
    await act(async () => {
      first = observed!.signOut()
      second = observed!.signOut()
      await Promise.resolve()
    })
    expect(first).toBe(second)
    expect(fake.client.auth.signOut).toHaveBeenCalledTimes(1)
    expect(observed?.signingOut).toBe(true)

    deferredSignOut.resolve({ error: null })
    await act(async () => { await Promise.all([first, second]) })
    expect(status()).toBe('ANONYMOUS')
    expect(observed?.signingOut).toBe(false)
  })

  it('revalidates an active profile on focus and blocks it when the backend deactivates it', async () => {
    let active = true
    const fake = makeClient({
      getUser: async () => authResult(ownerA),
      accessForUser: (authUserId) => active
        ? accessBundle(authUserId)
        : { allowed: false, reason: 'APP_USER_INACTIVE' },
    })
    mockedClient.current = fake.client

    await mount()
    expect(status()).toBe('AUTHORIZED')
    active = false
    await act(async () => {
      globalThis.window.dispatchEvent(new Event('focus'))
    })
    await settle()

    expect(fake.client.auth.getUser).toHaveBeenCalledTimes(2)
    expect(observed?.identity).toMatchObject({ status: 'BLOCKED', reason: 'ACCOUNT_INACTIVE' })
  })

  it('deduplicates focus plus visible events and ignores visibility while hidden', async () => {
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    const fake = makeClient({ getUser: async () => authResult(ownerA) })
    mockedClient.current = fake.client

    await mount()
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
      globalThis.window.dispatchEvent(new Event('focus'))
    })
    await settle()
    expect(fake.client.auth.getUser).toHaveBeenCalledTimes(1)

    visibility.mockReturnValue('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
      globalThis.window.dispatchEvent(new Event('focus'))
    })
    await settle()
    expect(fake.client.auth.getUser).toHaveBeenCalledTimes(2)
  })

  it('never lets a stale focus response reopen a signed-out account', async () => {
    const focusUser = deferred<ReturnType<typeof authResult>>()
    const getUser = vi.fn()
      .mockResolvedValueOnce(authResult(ownerA))
      .mockImplementationOnce(() => focusUser.promise)
    const fake = makeClient({ getUser })
    mockedClient.current = fake.client

    await mount()
    await act(async () => { globalThis.window.dispatchEvent(new Event('focus')) })
    await settle()
    expect(fake.client.auth.getUser).toHaveBeenCalledTimes(2)

    await act(async () => { fake.fire('SIGNED_OUT', null) })
    focusUser.resolve(authResult(ownerA))
    await settle()
    expect(status()).toBe('ANONYMOUS')
  })

  it('subscribes and unsubscribes cleanly under React StrictMode', async () => {
    const removeWindowListener = vi.spyOn(globalThis.window, 'removeEventListener')
    const removeDocumentListener = vi.spyOn(globalThis.document, 'removeEventListener')
    const fake = makeClient({ getUser: async () => authResult(null) })
    mockedClient.current = fake.client

    await mount(true)
    expect(fake.client.auth.onAuthStateChange.mock.calls.length).toBeGreaterThanOrEqual(2)
    const unsubscribeBeforeFinalUnmount = fake.unsubscribe.mock.calls.length

    await act(async () => { root.unmount() })
    expect(fake.unsubscribe.mock.calls.length).toBe(unsubscribeBeforeFinalUnmount + 1)
    expect(removeWindowListener).toHaveBeenCalledWith('focus', expect.any(Function))
    expect(removeDocumentListener).toHaveBeenCalledWith('visibilitychange', expect.any(Function))

    root = createRoot(container)
  })
})
