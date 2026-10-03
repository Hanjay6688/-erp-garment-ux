// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import LaundryReceiptDependencies from './LaundryReceiptDependencies'
import { TransactionSourceProvider } from './TransactionSourceNavigation'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'

const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const source = { source_type: 'LAUNDRY_RECEIPT', source_id: id(1) }
function identity() { return { runtime: recoveryRuntime, identity: { status: 'AUTHORIZED', profile: {
  id: id(2), authUserId: id(3), rowVersion: 1, roleRowVersion: 1, role: 'STAFF', roleName: 'QC viewer', isActive: true,
}, permissions: ['production.laundry.view', 'production.final_sku.view'] } } }
function result(offset = 0, total = 26) {
  return { contract_version: 'cp7.transaction-dependencies.v1', actor_scope_id: id(3), source,
    parent: { id: id(1), number: 'LR-001', status: 'POSTED', revision: '2' },
    page: { offset, limit: 25, total, has_more: offset + 25 < total },
    dependencies: Array.from({ length: Math.min(25, Math.max(0, total - offset)) }, (_, n) => ({ source_type: 'QC_INSPECTION', source_id: id(100 + offset + n), number: `QC-${100 + offset + n}`, status: 'POSTED', revision: '1' })),
    read_at: '2026-10-03T00:00:00Z', business_DML: false }
}
let box: HTMLDivElement, root: Root
const navigate = vi.fn()
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); mock.auth = identity(); mock.rpc.mockReset(); navigate.mockReset()
  mock.rpc.mockImplementation((name, args) => {
    if (name === 'erp_cp7_get_transaction_dependencies_v1') return Promise.resolve({ data: result(args.p_offset), error: null })
    if (name === 'erp_cp7_resolve_transaction_source_v1') return Promise.resolve({ data: {
      contract_version: 'cp7.transaction-source.v1', actor_scope_id: id(3), source: args.p_source, status: 'AVAILABLE',
      document: { domain: 'QC', route: 'qc', id: args.p_source.source_id, number: 'QC-125', status: 'POSTED', revision: '1', focus: null },
      read_at: '2026-10-03T00:00:00Z', business_DML: false,
    }, error: null })
    throw Error('Unexpected business writer: ' + name)
  })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove() })
const settle = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
async function render(current = true, receiptRevision = 2) {
  await act(async () => root.render(<TransactionSourceProvider scope="current-authority" onNavigate={navigate}>
    <LaundryReceiptDependencies receiptId={id(1)} receiptNumber="LR-001" receiptRevision={receiptRevision} current={current}/>
  </TransactionSourceProvider>)); await settle()
}
const button = (name: string) => [...box.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent?.trim() === name)!
async function click(name: string) { expect(button(name)).toBeDefined(); await act(async () => button(name).click()); await settle() }
const allReads = () => expect(mock.rpc.mock.calls.every(([name]) => ['erp_cp7_get_transaction_dependencies_v1', 'erp_cp7_resolve_transaction_source_v1'].includes(name))).toBe(true)
describe('Readonly Laundry receipt dependency navigation', () => {
  it('lets a viewer inspect complete pages and open the exact 26th QC without a writer', async () => {
    await render(); expect(mock.rpc).not.toHaveBeenCalled(); await click('Lihat QC terkait')
    expect(box.querySelectorAll('[data-laundry-qc-dependency-id]')).toHaveLength(25); expect(box.textContent).toContain('1–25 dari 26')
    await click('QC berikutnya'); expect(box.querySelectorAll('[data-laundry-qc-dependency-id]')).toHaveLength(1)
    expect(box.textContent).toContain('26–26 dari 26'); expect(box.textContent).not.toContain('QC-100')
    expect(mock.rpc).toHaveBeenCalledWith('erp_cp7_get_transaction_dependencies_v1', { p_source: source, p_offset: 25 })
    await click('Buka QC terkait'); expect(navigate).toHaveBeenCalledExactlyOnceWith('qc')
    expect(mock.rpc).toHaveBeenCalledWith('erp_cp7_resolve_transaction_source_v1', { p_source: { source_type: 'QC_INSPECTION', source_id: id(125) } }); allReads()
  })
  it('retires prior-page facts when a new read is denied and never calls a failure an empty list', async () => {
    await render(); await click('Lihat QC terkait'); expect(box.textContent).toContain('QC-100')
    mock.rpc.mockResolvedValueOnce({ data: null, error: { code: '42501', message: 'current QC view denied' } }); await click('QC berikutnya')
    expect(box.querySelectorAll('[data-laundry-qc-dependency-id]')).toHaveLength(0); expect(box.querySelector('[role="alert"]')?.textContent).toContain('izin')
    expect(box.textContent).not.toContain('Tidak ada QC aktif'); allReads()
  })
  it('keeps a way back when another device removes the last QC on the next page', async () => {
    await render(); await click('Lihat QC terkait')
    mock.rpc.mockResolvedValueOnce({ data: result(25, 25), error: null }); await click('QC berikutnya')
    expect(box.querySelectorAll('[data-laundry-qc-dependency-id]')).toHaveLength(0)
    expect(box.textContent).toContain('25 QC aktif'); expect(box.textContent).toContain('Halaman ini kosong')
    expect(box.textContent).not.toContain('26–25'); expect(button('QC sebelumnya').disabled).toBe(false)
    await click('QC sebelumnya'); expect(box.querySelectorAll('[data-laundry-qc-dependency-id]')).toHaveLength(25); allReads()
  })
  it('discards a held reply after current view revocation or current workspace retirement', async () => {
    await render(); let release!: (value: unknown) => void
    mock.rpc.mockImplementationOnce(() => new Promise(resolve => { release = resolve })); await click('Lihat QC terkait')
    const auth = identity(); auth.identity.permissions = ['production.laundry.view']; auth.identity.profile.roleRowVersion = 2; mock.auth = auth; await render()
    await act(async () => release({ data: result(), error: null })); await settle()
    expect(box.textContent).not.toContain('QC-100'); expect(button('Lihat QC terkait').disabled).toBe(true)
    mock.auth = identity(); await render(); await click('Lihat QC terkait'); expect(box.textContent).toContain('QC-100')
    await render(false); expect(box.textContent).not.toContain('QC-100'); expect(button('Lihat QC terkait').disabled).toBe(true); allReads()
  })
  it('refuses a changed parent version and then reads a confirmed empty current list', async () => {
    await render(true, 1); await click('Lihat QC terkait'); expect(box.textContent).toContain('Penerimaan berubah'); expect(box.textContent).not.toContain('QC-100')
    await render(); mock.rpc.mockResolvedValueOnce({ data: result(0, 0), error: null }); await click('Lihat QC terkait')
    expect(box.textContent).toContain('Tidak ada QC aktif'); expect(box.querySelectorAll('[data-laundry-qc-dependency-id]')).toHaveLength(0); allReads()
  })
})
