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
  businessDataMode: 'SIMULATION',
  businessRpcEnabled: false,
  projectRef: 'siimvrusnzxexizpyoib',
  supabaseUrl: 'https://siimvrusnzxexizpyoib.supabase.co',
  browserKey: 'sb_publishable_test_only_1234567890',
}

const profileRows = {
  [ownerA]: {
    id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ac',
    auth_user_id: ownerA,
    full_name: 'Owner A',
    role: 'OWNER',
    is_active: true,
    row_version: 1,
  },
  [ownerB]: {
    id: '018f7c2e-7b8a-7ab1-8d4a-1234567890bc',
    auth_user_id: ownerB,
    full_name: 'Owner B',
    role: 'OWNER',
    is_active: true,
    row_version: 2,
  },
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
  signOut?: () => Promise<{ error: unknown }>
}) {
  let callback: AuthCallback | null = null
  let selectedAuthUserId = ''
  const unsubscribe = vi.fn()
  const query = {
    select: vi.fn(() => query),
    eq: vi.fn((_column: string, value: string) => {
      selectedAuthUserId = value
      return query
    }),
    maybeSingle: vi.fn(async () => ({
      data: profileRows[selectedAuthUserId as keyof typeof profileRows] ?? null,
      error: null,
    })),
  }
  const client = {
    from: vi.fn(() => query),
    auth: {
      getUser: vi.fn(options.getUser),
      signInWithPassword: vi.fn(async () => ({ error: null })),
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

  it('subscribes and unsubscribes cleanly under React StrictMode', async () => {
    const fake = makeClient({ getUser: async () => authResult(null) })
    mockedClient.current = fake.client

    await mount(true)
    expect(fake.client.auth.onAuthStateChange.mock.calls.length).toBeGreaterThanOrEqual(2)
    const unsubscribeBeforeFinalUnmount = fake.unsubscribe.mock.calls.length

    await act(async () => { root.unmount() })
    expect(fake.unsubscribe.mock.calls.length).toBe(unsubscribeBeforeFinalUnmount + 1)

    root = createRoot(container)
  })
})
