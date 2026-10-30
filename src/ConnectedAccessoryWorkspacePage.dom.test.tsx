// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Workspace from './ConnectedAccessoryWorkspacePage'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { asrWorkspace } from '../tests/fixtures/accessoryStandardReport'
import type { AccessoryReportQuery } from './accessoryStandardReport'

const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
const source = vi.hoisted(() => ({ current: null as null | { key: string } }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
vi.mock('./TransactionSourceNavigation', () => ({ useTransactionSource: () => source.current }))
vi.mock('./ConnectedAccessoryIssuePage', () => ({ default: () => <section aria-label="Nota existing">Nota existing</section> }))

const permissions = ['finance.contractor_accessory.view', 'finance.hpp.view']
function identity(role = 'OWNER', rights = permissions) {
  const value = structuredClone(recoveryIdentity)
  value.identity.profile.role = role
  value.identity.permissions = rights
  return value
}
function query(a: Record<string, unknown>): AccessoryReportQuery {
  return { period_start: a.p_start as string, period_end: a.p_end as string,
    contractor_id: a.p_contractor as string | null, po_id: a.p_po as string | null,
    q: a.p_query as string, offset: a.p_offset as number, limit: a.p_limit as number }
}
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-10-16T06:00:00Z'))
  auth.current = identity(); source.current = null; client.rpc.mockReset()
  client.rpc.mockImplementation(async (_name: string, args: Record<string, unknown>) => ({ data: asrWorkspace(query(args)), error: null }))
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) }) }
async function render() { await act(async () => root.render(<Workspace/>)); await settle() }
function button(label: string) { return [...container.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === label) }
async function click(label: string) {
  await act(async () => {
    button(label)!.click()
    if (label === 'Diambil vs standar GOOD') await import('./ConnectedAccessoryStandardReportPage')
  })
  await settle()
}
const note = () => container.querySelector('[aria-label="Nota existing"]')
const report = () => container.querySelector('[aria-label="Laporan aksesori mandor"]')

describe('S05 connected workspace entry', () => {
  it('opens the existing note first and rereads the real report component after switching back', async () => {
    await render(); expect(note()).not.toBeNull(); expect(client.rpc).not.toHaveBeenCalled()
    await click('Diambil vs standar GOOD'); expect(note()).toBeNull(); expect(report()).not.toBeNull()
    expect(client.rpc).toHaveBeenCalledTimes(1)
    await click('Nota ambil aksesori'); expect(report()).toBeNull()
    await click('Diambil vs standar GOOD'); expect(client.rpc).toHaveBeenCalledTimes(2)
    expect(client.rpc.mock.calls.every(([name]) => name === 'erp_cp7_get_accessory_standard_report_v1')).toBe(true)
  })
  it.each([['STAFF', permissions], ['OWNER', [permissions[0]]], ['ADMIN', [permissions[1]]]])(
    'keeps the existing note and refuses report access for %s with incomplete scope', async (role, rights) => {
      auth.current = identity(role, rights); await render()
      expect(note()).not.toBeNull(); expect(button('Diambil vs standar GOOD')).toBeUndefined()
      expect(client.rpc).not.toHaveBeenCalled()
    })
  it('allows Admin with both permissions', async () => {
    auth.current = identity('ADMIN'); await render(); await click('Diambil vs standar GOOD')
    expect(report()).not.toBeNull(); expect(client.rpc).toHaveBeenCalledTimes(1)
  })
  it('retires a delayed report when switching to the note', async () => {
    let release!: () => void
    client.rpc.mockImplementationOnce((_name: string, args: Record<string, unknown>) => new Promise(resolve => {
      release = () => resolve({ data: asrWorkspace(query(args)), error: null })
    }))
    await render(); await click('Diambil vs standar GOOD'); await click('Nota ambil aksesori')
    await act(async () => release()); await settle()
    expect(note()).not.toBeNull(); expect(report()).toBeNull(); expect(container.textContent).not.toContain('Mandor Satu')
    await click('Diambil vs standar GOOD'); expect(client.rpc).toHaveBeenCalledTimes(2)
  })
  it('removes report figures immediately when rights or the signed-in identity change', async () => {
    await render(); await click('Diambil vs standar GOOD'); await click('Mandor Satu')
    expect(container.querySelector('[aria-label="Hasil laporan aksesori"]')).not.toBeNull()
    auth.current = identity('OWNER', [permissions[0]]); await render()
    expect(report()).toBeNull(); expect(button('Diambil vs standar GOOD')).toBeUndefined()
    auth.current = identity(); await render(); await click('Diambil vs standar GOOD')
    expect(report()).not.toBeNull()
    const next = identity()
    auth.current = { ...next, identity: { ...next.identity,
      profile: { ...next.identity.profile, authUserId: '77777777-7777-4777-8777-777777777777' } } }
    await render(); expect(note()).not.toBeNull(); expect(report()).toBeNull()
  })
  it('returns to the note for a new transaction-source key on the same App route', async () => {
    await render(); await click('Diambil vs standar GOOD'); expect(report()).not.toBeNull()
    source.current = { key: 'new-accessory-issue-source' }; await render()
    expect(note()).not.toBeNull(); expect(report()).toBeNull()
  })
})
