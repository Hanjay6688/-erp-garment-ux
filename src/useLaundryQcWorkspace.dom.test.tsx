// @vitest-environment jsdom

import { act, useEffect, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLaundryQcWorkspace } from './useLaundryQcWorkspace'
import { readProductionRecovery } from './productionRecovery'
import type { LaundryQcScope } from './laundryQcModel'

const authState = vi.hoisted(() => ({ current: null as unknown }))
const mockedClient = vi.hoisted(() => ({ current: null as unknown }))

vi.mock('./auth/AuthProvider', () => ({ useAuth: () => authState.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mockedClient.current }))

const runtime = {
  mode: 'UAT_AUTH_SIMULATION', authMode: 'UAT_SUPABASE', businessDataMode: 'PARTIAL_CONNECTED',
  businessRpcEnabled: true, accessControlMode: 'CONNECTED', patternMode: 'CONNECTED', cuttingMode: 'CONNECTED',
  distributionMode: 'CONNECTED', wipStatusMode: 'CONNECTED', bsResolutionMode: 'CONNECTED',
  laundryMode: 'CONNECTED', qcFinalMode: 'CONNECTED', fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE',
  projectRef: 'siimvrusnzxexizpyoib', supabaseUrl: 'https://siimvrusnzxexizpyoib.supabase.co',
  browserKey: 'sb_publishable_cp6_dom_fixture_20260904',
} as const
const appUserId = '00000000-0000-4000-8000-000000000001'
const storageKey = `erp.cp6.pending-mutation.v1:${runtime.projectRef}:${appUserId}`

function lockManager() {
  let held = false
  return {
    request: vi.fn(async (
      name: string,
      options: LockOptions,
      callback: (lock: Lock | null) => Promise<unknown>,
    ) => {
      if (held && options.ifAvailable) return callback(null)
      held = true
      try {
        return await callback({ name, mode: 'exclusive' } as Lock)
      } finally {
        held = false
      }
    }),
  }
}

function workspace() {
  return {
    contract_version: 'CP6_V2620', scope: 'LAUNDRY', generated_at: '2026-09-04T12:00:00Z',
    lookups: { vendors: [], wash_processes: [], rate_versions: [], fg_locations: [], products: [] },
    readiness: {
      laundry_writer_ready: false, qc_writer_ready: false,
      lineage_integrity_ok: true, lineage_issue_count: 0,
      no_fixture_fallback: true, failed_wash_with_charge_supported: true,
    },
    collection_window: {
      transaction_limit: 200, product_limit: 500, query_required_for_more: true,
      transaction_query_scope: 'SOURCE_QUEUE_AND_HISTORY',
      product_search_contract: 'CP6_PRODUCT_SEARCH_V2620B', product_query_decoupled: true,
      products_relevant_to_live_qc: false, products_truncated: false,
      ready_batches_truncated: false, deliveries_truncated: false,
      qc_queue_truncated: false, qc_history_truncated: false, any_truncated: false,
    },
    ready_batches: [], deliveries: [], qc_queue: [], qc_history: [],
    legacy_unlinked: { delivery_count: 0, receipt_count: 0 },
  }
}

function committed(args: unknown) {
  const request = args as { p_action: string; p_client_request_id: string }
  return {
    contract_version: 'CP6_V2620', committed: true,
    action: request.p_action, client_request_id: request.p_client_request_id,
  }
}

function auth() {
  return {
    runtime,
    identity: {
      status: 'AUTHORIZED',
      profile: {
        id: appUserId, authUserId: '00000000-0000-4000-8000-000000000002', fullName: 'CP6 Owner',
        roleId: '00000000-0000-4000-8000-000000000003', role: 'OWNER', roleName: 'Owner',
        isActive: true, rowVersion: 1, roleRowVersion: 1,
      },
      permissions: ['production.laundry.view', 'production.laundry.create', 'production.laundry.post'],
      externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
    },
    signingOut: false, signOutError: null, signIn: vi.fn(), signOut: vi.fn(), retryIdentity: vi.fn(),
  }
}

function Harness({ prefix = '', scope = 'LAUNDRY' }: { prefix?: string; scope?: LaundryQcScope }) {
  const bridge = useLaundryQcWorkspace(scope)
  const [retired, setRetired] = useState(false)
  useEffect(() => {
    if (bridge.committedSequence > 0 && !bridge.workspaceStale) {
      setRetired(true)
      bridge.acknowledgeCommittedFormRetired(bridge.committedSequence)
    }
  }, [bridge.acknowledgeCommittedFormRetired, bridge.committedSequence, bridge.workspaceStale])
  return <div>
    <button id={`${prefix}run`} disabled={bridge.writerLocked || retired} onClick={() => void bridge.runAction(
      'POST_DELIVERY', { marker: 'same-payload' }, 7, () => setRetired(true),
    )}>run</button>
    <button id={`${prefix}reconcile`} disabled={!bridge.pending || bridge.busy} onClick={() => void bridge.reconcile()}>reconcile</button>
    <button id={`${prefix}load`} disabled={bridge.busy} onClick={() => void bridge.load()}>load</button>
    <button id={`${prefix}search`} onClick={() => bridge.search('operator query')}>search</button>
    <output id={`${prefix}facts`}>{bridge.workspace ? `${bridge.workspace.generated_at}:${bridge.workspace.legacy_unlinked.delivery_count}` : 'UNKNOWN'}</output>
    <output id={`${prefix}state`}>{JSON.stringify({
      retired, locked: bridge.writerLocked, pending: Boolean(bridge.pending), corrupt: bridge.corruptedEnvelope,
      stale: bridge.workspaceStale, committed: bridge.committedRefreshRequired, sequence: bridge.committedSequence,
    })}</output>
    <output id={`${prefix}error`}>{bridge.error}</output>
  </div>
}

async function settle(delay = 0) {
  await act(async () => { await new Promise((resolve) => globalThis.setTimeout(resolve, delay)) })
}

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  globalThis.localStorage.clear()
  authState.current = auth()
  Object.defineProperty(globalThis.navigator, 'locks', {
    configurable: true, value: lockManager(),
  })
  vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('00000000-0000-4000-8000-000000000099')
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  globalThis.localStorage.clear()
  Reflect.deleteProperty(globalThis.navigator, 'locks')
  vi.restoreAllMocks()
})

async function renderHarness() {
  await act(async () => { root.render(<Harness/>) })
  await settle()
}

function state() {
  return JSON.parse(container.querySelector<HTMLOutputElement>('#state')?.textContent ?? '{}') as Record<string, unknown>
}

async function click(id: string) {
  await act(async () => {
    container.querySelector<HTMLButtonElement>(id)?.click()
    await new Promise((resolve) => globalThis.setTimeout(resolve, 0))
  })
}

describe('useLaundryQcWorkspace durable mutation envelope', () => {
  it('retires a committed form and keeps it dead after refetch failure then recovery', async () => {
    let readCount = 0
    let mutationCount = 0
    const rpc = vi.fn(async (name: string, args: unknown) => {
      if (name === 'erp_save_laundry_qc_action_v1') {
        mutationCount += 1
        return { data: committed(args), error: null }
      }
      readCount += 1
      if (readCount === 2) return { data: null, error: { code: 'PGRST000', message: 'refetch failed' } }
      return { data: workspace(), error: null }
    })
    mockedClient.current = { rpc }
    await renderHarness()
    expect(state()).toMatchObject({ locked: false, stale: false, retired: false })

    await click('#run')
    await settle()
    expect(mutationCount).toBe(1)
    expect(state()).toMatchObject({ retired: true, locked: true, stale: true, sequence: 1 })

    await click('#load')
    await settle()
    expect(state()).toMatchObject({ retired: true, locked: false, stale: false, sequence: 1 })
    await click('#run')
    await settle()
    expect(mutationCount).toBe(1)
  })

  it('reconciles an ambiguous response with the exact same UUID, payload, and version', async () => {
    const mutationArgs: unknown[] = []
    let mutationCount = 0
    const rpc = vi.fn(async (name: string, args: unknown) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return { data: workspace(), error: null }
      mutationArgs.push(args)
      mutationCount += 1
      return mutationCount === 1 ? { data: null, error: {} } : { data: committed(args), error: null }
    })
    mockedClient.current = { rpc }
    await renderHarness()
    await click('#run')
    await settle()
    expect(state()).toMatchObject({ pending: true, locked: true, retired: false })
    expect(globalThis.localStorage.getItem(storageKey)).toContain('same-payload')

    await click('#reconcile')
    await settle()
    expect(mutationArgs).toHaveLength(2)
    expect(mutationArgs[1]).toEqual(mutationArgs[0])
    expect(state()).toMatchObject({ pending: false, locked: false, retired: true, sequence: 1 })
    expect(globalThis.localStorage.getItem(storageKey)).toBeNull()
  })

  it('treats a gateway 503 as ambiguous and never creates a replacement UUID', async () => {
    const mutationArgs: unknown[] = []
    let mutationCount = 0
    const rpc = vi.fn(async (name: string, args: unknown) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return { data: workspace(), error: null }
      mutationArgs.push(args)
      mutationCount += 1
      return mutationCount === 1
        ? { data: null, error: { status: 503, message: 'gateway response lost' } }
        : { data: committed(args), error: null }
    })
    mockedClient.current = { rpc }
    await renderHarness()
    await click('#run')
    await settle()
    expect(state()).toMatchObject({ pending: true, locked: true, retired: false })

    await click('#reconcile')
    await settle()
    expect(mutationArgs).toHaveLength(2)
    expect(mutationArgs[1]).toEqual(mutationArgs[0])
    expect(state()).toMatchObject({ pending: false, retired: true, sequence: 1 })
  })

  it('treats a PostgREST database-connection code as ambiguous and preserves the exact envelope', async () => {
    const mutationArgs: unknown[] = []
    let mutationCount = 0
    const rpc = vi.fn(async (name: string, args: unknown) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return { data: workspace(), error: null }
      mutationArgs.push(args)
      mutationCount += 1
      return mutationCount === 1
        ? { data: null, error: {
          code: 'PGRST000', status: 400, message: 'database connection outcome unknown',
        } }
        : { data: committed(args), error: null }
    })
    mockedClient.current = { rpc }
    await renderHarness()
    await click('#run')
    await settle()
    expect(state()).toMatchObject({ pending: true, locked: true, retired: false })
    expect(globalThis.localStorage.getItem(storageKey)).toContain('00000000-0000-4000-8000-000000000099')

    await click('#reconcile')
    await settle()
    expect(mutationArgs).toHaveLength(2)
    expect(mutationArgs[1]).toEqual(mutationArgs[0])
    expect(state()).toMatchObject({ pending: false, retired: true, sequence: 1 })
  })

  it('fails closed when a persisted envelope is corrupt', async () => {
    globalThis.localStorage.setItem(storageKey, '{broken-json')
    const rpc = vi.fn()
    mockedClient.current = { rpc }
    await renderHarness()
    expect(state()).toMatchObject({ corrupt: true, locked: true, stale: true })
    expect(container.querySelector<HTMLButtonElement>('#run')?.disabled).toBe(true)
    expect(container.querySelector('#error')?.textContent).toContain('Envelope idempotency lokal rusak')
    expect(rpc).not.toHaveBeenCalled()
  })

  it('does not send when the UUID envelope cannot be persisted', async () => {
    const rpc = vi.fn(async (name: string, args: unknown) => name === 'erp_get_laundry_qc_workspace_v1'
      ? { data: workspace(), error: null } : { data: committed(args), error: null })
    mockedClient.current = { rpc }
    await renderHarness()
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota') })
    await click('#run')
    await settle()
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(0)
    expect(container.querySelector('#error')?.textContent).toContain('Tidak ada request yang dikirim')
  })

  it('keeps the original envelope when a 2xx response has the wrong UUID contract', async () => {
    let mutationCount = 0
    const rpc = vi.fn(async (name: string) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return { data: workspace(), error: null }
      mutationCount += 1
      return {
        data: {
          contract_version: 'CP6_V2620', committed: true,
          action: 'POST_DELIVERY', client_request_id: '00000000-0000-4000-8000-000000000098',
        },
        error: null,
      }
    })
    mockedClient.current = { rpc }
    await renderHarness()
    await click('#run')
    await settle()
    expect(mutationCount).toBe(1)
    expect(state()).toMatchObject({ pending: true, locked: true, retired: false })
    expect(globalThis.localStorage.getItem(storageKey)).toContain('00000000-0000-4000-8000-000000000099')
    expect(container.querySelector('#error')?.textContent).toContain('UUID/action yang cocok')
  })

  it('refuses a second mounted writer while the global cross-tab envelope is in flight', async () => {
    let releaseFirst: (() => void) | undefined
    let firstStarted: (() => void) | undefined
    const started = new Promise<void>((resolve) => { firstStarted = resolve })
    const rpc = vi.fn(async (name: string) => {
      if (name === 'erp_get_laundry_qc_workspace_v1') return { data: workspace(), error: null }
      firstStarted?.()
      await new Promise<void>((resolve) => { releaseFirst = resolve })
      return { data: null, error: { status: 503, message: 'outcome unknown' } }
    })
    mockedClient.current = { rpc }
    await act(async () => { root.render(<><Harness prefix="a-"/><Harness prefix="b-"/></>) })
    await settle()

    container.querySelector<HTMLButtonElement>('#a-run')?.click()
    await started
    await click('#b-run')
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(1)
    expect(JSON.parse(container.querySelector('#b-state')?.textContent ?? '{}')).toMatchObject({
      locked: true, pending: true,
    })
    expect(container.querySelector('#b-error')?.textContent).toContain('tab lain')

    releaseFirst?.()
    await settle()
    expect(globalThis.localStorage.getItem(storageKey)).toContain('same-payload')
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(1)
  })

  it('fails closed without Web Locks and sends no mutation', async () => {
    Reflect.deleteProperty(globalThis.navigator, 'locks')
    const rpc = vi.fn(async (name: string, args: unknown) => name === 'erp_get_laundry_qc_workspace_v1'
      ? { data: workspace(), error: null } : { data: committed(args), error: null })
    mockedClient.current = { rpc }
    await renderHarness()
    expect(state()).toMatchObject({ locked: true, stale: false })
    await click('#run')
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(0)
    expect(container.querySelector('#error')?.textContent).toContain('Web Locks')
  })

  it('locks the writer synchronously when a refetch starts before React can rerender', async () => {
    let finishRefetch: (() => void) | undefined
    let workspaceReads = 0
    const rpc = vi.fn(async (name: string, args: unknown) => {
      if (name === 'erp_save_laundry_qc_action_v1') return { data: committed(args), error: null }
      workspaceReads += 1
      if (workspaceReads === 1) return { data: workspace(), error: null }
      await new Promise<void>((resolve) => { finishRefetch = resolve })
      return { data: workspace(), error: null }
    })
    mockedClient.current = { rpc }
    await renderHarness()
    expect(state()).toMatchObject({ locked: false, stale: false })

    await act(async () => {
      container.querySelector<HTMLButtonElement>('#load')?.click()
      // This callback still exists in the pre-render DOM. The synchronous
      // readiness ref, not a later React render, must reject it.
      container.querySelector<HTMLButtonElement>('#run')?.click()
      await Promise.resolve()
    })
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(0)
    finishRefetch?.()
    await settle()
    expect(state()).toMatchObject({ locked: false, stale: false })
  })

  it.each(['LAUNDRY', 'QC'] as const)('retires %s facts at read start and after a denied read, without displaying zero', async scope => {
    let complete!: (v: unknown) => void
    const dto = { ...workspace(), scope, collection_window: { ...workspace().collection_window, products_relevant_to_live_qc: scope === 'QC' }, legacy_unlinked: { delivery_count: 7, receipt_count: 3 } }
    const rpc = vi.fn().mockResolvedValue({ data: dto, error: null })
    mockedClient.current = { rpc }
    await act(async () => root.render(<Harness scope={scope}/>)); await settle()
    expect(container.querySelector('#facts')?.textContent).toContain(':7')
    rpc.mockImplementationOnce(() => new Promise(resolve => { complete = resolve }))
    await click('#load')
    expect(container.querySelector('#facts')?.textContent).toBe('UNKNOWN')
    await act(async () => complete({ data: null, error: { code: '42501', status: 403, message: 'CURRENT_VIEW_DENIED' } }))
    expect(container.querySelector('#facts')?.textContent).toBe('UNKNOWN')
    expect(state()).toMatchObject({ locked: true, stale: true })
    expect(container.querySelector('#error')?.textContent).toContain('tidak memiliki izin')
    await click('#load')
    expect(container.querySelector('#facts')?.textContent).toContain(':7')
    expect(rpc.mock.calls.every(([name]) => name === 'erp_get_laundry_qc_workspace_v1')).toBe(true)
  })

  it('refuses a held success after shared recovery changes, then admits a fresh explicit read', async () => {
    let complete!: (v: unknown) => void
    const rpc = vi.fn().mockResolvedValue({ data: workspace(), error: null })
    mockedClient.current = { rpc }; await renderHarness()
    rpc.mockImplementationOnce(() => new Promise(resolve => { complete = resolve }))
    await click('#load')
    await act(async () => window.dispatchEvent(new StorageEvent('storage', { key: null })))
    await act(async () => complete({ data: { ...workspace(), generated_at: '2026-09-04T13:00:00Z', legacy_unlinked: { delivery_count: 91, receipt_count: 0 } }, error: null }))
    expect(container.querySelector('#facts')?.textContent).toBe('UNKNOWN')
    expect(state()).toMatchObject({ locked: true, stale: true })
    await click('#load')
    expect(container.querySelector('#facts')?.textContent).toBe('2026-09-04T12:00:00Z:0')
    expect(state()).toMatchObject({ locked: false, stale: false })
  })

  it('retires old actor/role facts synchronously and ignores that role\'s held response', async () => {
    let oldRead!: (v: unknown) => void, newRead!: (v: unknown) => void
    const rpc = vi.fn().mockResolvedValue({ data: workspace(), error: null })
    mockedClient.current = { rpc }; await renderHarness()
    rpc.mockImplementationOnce(() => new Promise(resolve => { oldRead = resolve }))
    await click('#load')
    const next = auth(); next.identity.profile.roleRowVersion = 2
    next.identity.permissions = ['production.laundry.view']
    authState.current = next
    rpc.mockImplementationOnce(() => new Promise(resolve => { newRead = resolve }))
    await act(async () => root.render(<Harness/>))
    expect(container.querySelector('#facts')?.textContent).toBe('UNKNOWN')
    await act(async () => oldRead({ data: { ...workspace(), legacy_unlinked: { delivery_count: 91, receipt_count: 0 } }, error: null }))
    expect(container.querySelector('#facts')?.textContent).toBe('UNKNOWN')
    await act(async () => newRead({ data: { ...workspace(), legacy_unlinked: { delivery_count: 4, receipt_count: 0 } }, error: null }))
    expect(container.querySelector('#facts')?.textContent).toContain(':4')
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(0)
  })

  it('keeps source facts retired when an earlier query returns after its replacement', async () => {
    let earlier!: (v: unknown) => void
    const rpc = vi.fn().mockResolvedValue({ data: workspace(), error: null })
    mockedClient.current = { rpc }; await renderHarness()
    rpc.mockImplementationOnce(() => new Promise(resolve => { earlier = resolve }))
    await click('#load')
    rpc.mockResolvedValueOnce({ data: { ...workspace(), legacy_unlinked: { delivery_count: 4, receipt_count: 0 } }, error: null })
    await click('#search')
    expect(container.querySelector('#facts')?.textContent).toContain(':4')
    await act(async () => earlier({ data: { ...workspace(), legacy_unlinked: { delivery_count: 91, receipt_count: 0 } }, error: null }))
    expect(container.querySelector('#facts')?.textContent).toContain(':4')
    expect(rpc.mock.calls.at(-1)?.[1]).toEqual({ p_scope: 'LAUNDRY', p_query: 'operator query' })
  })

  it('admits current readonly facts while an uncertain command keeps its exact recovery envelope and all writes locked', async () => {
    const rpc = vi.fn(async (name: string) => name === 'erp_get_laundry_qc_workspace_v1'
      ? { data: { ...workspace(), legacy_unlinked: { delivery_count: 7, receipt_count: 0 } }, error: null }
      : { data: null, error: { status: 503, message: 'Lost reply' } })
    mockedClient.current = { rpc }; await renderHarness(); await click('#run')
    const original = localStorage.getItem(storageKey)
    expect(container.querySelector('#facts')?.textContent).toBe('UNKNOWN')
    expect(readProductionRecovery(`${runtime.projectRef}:${appUserId}`).pending.LAUNDRY_QC).toBeDefined()
    await click('#load')
    expect(container.querySelector('#facts')?.textContent).toContain(':7')
    expect(state()).toMatchObject({ locked: true, stale: false, pending: true })
    expect(localStorage.getItem(storageKey)).toBe(original)
    await click('#run')
    expect(rpc.mock.calls.filter(([name]) => name === 'erp_save_laundry_qc_action_v1')).toHaveLength(1)
  })

  it('keeps current source readable without Web Locks while refusing every write', async () => {
    Reflect.deleteProperty(navigator, 'locks')
    const rpc = vi.fn().mockResolvedValue({ data: { ...workspace(), legacy_unlinked: { delivery_count: 7, receipt_count: 0 } }, error: null })
    mockedClient.current = { rpc }; await renderHarness()
    expect(container.querySelector('#facts')?.textContent).toContain(':7')
    expect(state()).toMatchObject({ locked: true, stale: false })
    await click('#run')
    expect(rpc.mock.calls.every(([name]) => name === 'erp_get_laundry_qc_workspace_v1')).toBe(true)
  })
})
