// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UatRuntimeConfig } from '../config/runtime'
import { AuthGate } from './AuthGate'
import { AuthProvider } from './AuthProvider'

const mockedClient = vi.hoisted(() => ({ current: null as unknown }))

vi.mock('../lib/supabase', () => ({
  getUatSupabaseClient: () => mockedClient.current,
}))

const ownerId = '018f7c2e-7b8a-7ab1-8d4a-1234567890ab'
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
  bsResolutionMode: 'CONNECTED',
  laundryMode: 'CONNECTED',
  qcFinalMode: 'CONNECTED',
  fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE',
  projectRef: 'siimvrusnzxexizpyoib',
  supabaseUrl: 'https://siimvrusnzxexizpyoib.supabase.co',
  browserKey: 'sb_publishable_test_only_1234567890',
}

function authResult(userId: string | null) {
  return { data: { user: userId ? { id: userId } : null }, error: null }
}

function accessBundle() {
  return {
    allowed: true,
    profile: {
      id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ac',
      auth_user_id: ownerId,
      full_name: 'Owner UAT',
      role_id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ad',
      role_code: 'OWNER',
      role_name: 'Owner',
      is_active: true,
      row_version: 1,
      role_row_version: 1,
    },
    permissions: ['settings.access.manage', 'production.wip.view'],
    external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }
}

function makeClient(options: {
  getUser: () => Promise<ReturnType<typeof authResult>>
  signIn?: () => Promise<{ error: unknown }>
  access?: () => Promise<{ data: unknown; error: unknown }>
}) {
  const unsubscribe = vi.fn()
  return {
    rpc: vi.fn(options.access ?? (async () => ({ data: accessBundle(), error: null }))),
    auth: {
      getUser: vi.fn(options.getUser),
      signInWithPassword: vi.fn(options.signIn ?? (async () => ({ error: null }))),
      signOut: vi.fn(async () => ({ error: null })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe } } })),
    },
  }
}

function setInputValue(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
  if (!setter) throw new Error('HTMLInputElement value setter is unavailable.')
  setter.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
}

async function settle() {
  await act(async () => {
    await new Promise((resolve) => globalThis.setTimeout(resolve, 0))
  })
}

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  vi.restoreAllMocks()
})

async function renderFlow() {
  await act(async () => {
    root.render(
      <AuthProvider runtime={runtime}>
        <AuthGate><div data-testid="private-app">ERP terbuka</div></AuthGate>
      </AuthProvider>,
    )
  })
  await settle()
}

describe('Auth UAT DOM flow', () => {
  it('offers a safe retry after an initial transient identity error', async () => {
    const getUser = vi.fn()
      .mockRejectedValueOnce(new TypeError('fetch failed'))
      .mockResolvedValueOnce(authResult(ownerId))
    mockedClient.current = makeClient({ getUser })

    await renderFlow()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Layanan UAT belum dapat dihubungi')
    const retry = [...container.querySelectorAll('button')]
      .find((button) => button.textContent === 'Coba verifikasi sesi lagi')
    expect(retry).toBeTruthy()

    await act(async () => { retry!.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    await settle()

    expect(getUser).toHaveBeenCalledTimes(2)
    expect(container.querySelector('[data-testid="private-app"]')?.textContent).toBe('ERP terbuka')
  })

  it('retries a transient self-profile lookup without bypassing the blocked gate', async () => {
    const access = vi.fn()
      .mockRejectedValueOnce(new TypeError('profile fetch failed'))
      .mockResolvedValueOnce({
        data: accessBundle(),
        error: null,
      })
    mockedClient.current = makeClient({
      getUser: async () => authResult(ownerId),
      access,
    })

    await renderFlow()
    expect(container.textContent).toContain('Akun belum lolos guardrail')
    expect(container.querySelector('[data-testid="private-app"]')).toBeNull()
    const retry = [...container.querySelectorAll('button')]
      .find((button) => button.textContent === 'Periksa ulang')
    expect(retry).toBeTruthy()

    await act(async () => { retry!.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    await settle()

    expect(access).toHaveBeenCalledTimes(2)
    expect(container.querySelector('[data-testid="private-app"]')?.textContent).toBe('ERP terbuka')
  })

  it('renders a rejected password sign-in as a retryable error and re-enables the form', async () => {
    const signInWithPassword = vi.fn(async () => { throw new TypeError('network unavailable') })
    const client = makeClient({
      getUser: async () => authResult(null),
      signIn: signInWithPassword,
    })
    mockedClient.current = client

    await renderFlow()
    const inputs = container.querySelectorAll('input')
    const email = inputs[0] as HTMLInputElement
    const password = inputs[1] as HTMLInputElement
    await act(async () => {
      setInputValue(email, '  owner@example.test  ')
      setInputValue(password, 'not-a-real-password')
    })

    const form = container.querySelector('form')!
    await act(async () => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })
    await settle()

    expect(signInWithPassword).toHaveBeenCalledExactlyOnceWith({
      email: 'owner@example.test',
      password: 'not-a-real-password',
    })
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Layanan UAT belum dapat dihubungi')
    expect((container.querySelector('input[type="password"]') as HTMLInputElement).value).toBe('')
    const submit = container.querySelector('button[type="submit"]') as HTMLButtonElement
    expect(submit.disabled).toBe(false)
    expect(submit.textContent).toBe('Masuk')
  })
})
