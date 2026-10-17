// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AttendanceHppPoolPanel from './AttendanceHppPoolPanel'
import { hppPoolRupiah, parseHppPoolOutcome, parseHppPoolWorkspace } from './hppPoolContract'
import type { ProductionEnvelope } from './productionRecovery'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))

// A stand-in server keeping pool rows as pool.sql returns them (exact strings, Native lifecycle shape); figures are test data.
const day = '2026-10-16', po = '22222222-2222-4222-8222-222222222222', poB = '44444444-4444-4444-8444-444444444444'
const sha = (c: string) => c.repeat(64), tok = (c: string) => c.repeat(32)
type Row = Record<string, unknown>
let seq = 0
function poolRow(extra: Row = {}): Row {
  seq += 1
  return { id: `00000000-0000-4000-8000-${String(seq).padStart(12, '0')}`, pool_number: `AHPP-${seq}`, status: 'DRAFT', period_start: day, period_end: day,
    numerator_amount: '1000.00', denominator_qty: 10, unit_cost_per_sewn_pcs: '100.000000000000', source_count: 1, po_count: 1,
    allocations: [{ po_id: po, po_number: 'PO-9', sewing_qty: 10, amount: '1000.00' }], correction_of: null, replaced_by: [],
    created_at: '2026-10-17T02:00:00.000000Z', created_by: 'Owner Uji', reason: 'Pool absensi minggu ini', activated_at: null, activated_by: null,
    activation_reason: null, cancelled_at: null, cancelled_by: null, cancellation_reason: null, journal_number: null, reversal_journal_number: null,
    row_version: 1, review_token: tok(String(seq % 10)), period_closed: false, stale: false, stale_message: null, actions: ['ACTIVATE', 'CANCEL'], ...extra }
}
function ready(extra: Row = {}): Row {
  return { period_start: day, period_end: day, status: 'READY', period_closed: false, existing_pool: null, cancelled_pools: [], numerator_amount: '1000.00',
    denominator_qty: 10, unit_cost_per_sewn_pcs: '100.000000000000', source_count: 1, destination_count: 1, po_count: 1,
    pos: [{ po_id: po, po_number: 'PO-9', sewing_qty: 10 }], manifest_sha256: sha('a'), review_token: tok('c'), blocker: null, can_create: true, ...extra }
}
function blocked(code: string, message: string, extra: Row = {}): Row {
  return { ...ready(), status: 'BLOCKED', numerator_amount: null, denominator_qty: null, unit_cost_per_sewn_pcs: null, source_count: null, destination_count: null,
    po_count: null, pos: [], manifest_sha256: null, review_token: null, blocker: { code, message }, can_create: false, ...extra }
}
function server() {
  const s = { pools: [] as Row[], closed: null as string | null, canManage: true, preview: (_a: Row) => ready() as Row, lose: false,
    refuse: null as null | { code: string; message: string }, effects: 0, cache: new Map<string, unknown>() }
  client.rpc.mockImplementation(async (name: string, args: Row) => {
    if (name === 'erp_cp7_get_hpp_pools_v1') {
      const page = s.pools.slice(args.p_offset as number, (args.p_offset as number) + (args.p_limit as number))
      return { data: { contract_version: 'cp7.hpp-pools.v1', business_DML: false, captured_at: '2026-10-17T03:00:00.000000Z', offset: args.p_offset,
        limit: args.p_limit, total: s.pools.length, next_offset: (args.p_offset as number) + page.length < s.pools.length ? (args.p_offset as number) + page.length : null,
        closed_through: s.closed, can_manage: s.canManage, pools: page, periods: [{ period_start: day, period_end: day, payroll_count: 1, pool: null }],
        preview: args.p_period_start === null ? null : { ...s.preview(args), period_start: args.p_period_start, period_end: args.p_period_end } }, error: null }
    }
    if (name === 'erp_cp7_save_hpp_pool_v1') {
      if (s.refuse) return { data: null, error: { ...s.refuse } }
      const key = args.p_request as string, p = args.p_payload as Row
      if (!s.cache.has(key)) {
        s.effects += 1
        let row: Row
        if (args.p_action === 'CREATE') {
          row = poolRow({ correction_of: p.correction_of_pool_id ? { id: p.correction_of_pool_id, pool_number: 'AHPP-OLD', status: 'CANCELLED' } : null })
          s.pools.unshift(row)
        } else {
          row = s.pools.find(x => x.id === p.pool_id)!
          const draft = row.status === 'DRAFT'
          Object.assign(row, args.p_action === 'ACTIVATE'
            ? { status: 'ACTIVE', activated_at: '2026-10-17T04:00:00.000000Z', activated_by: 'Owner Uji', activation_reason: p.reason, journal_number: 'JRN-1', actions: ['CANCEL'] }
            : draft ? { status: 'VOIDED', cancelled_at: '2026-10-17T05:00:00.000000Z', cancelled_by: 'Owner Uji', cancellation_reason: p.reason, actions: [] }
              : { status: 'CANCELLED', cancelled_at: '2026-10-17T05:00:00.000000Z', cancelled_by: 'Owner Uji', cancellation_reason: p.reason, reversal_journal_number: 'JRN-2', actions: ['REPLACE'] },
            { row_version: (row.row_version as number) + 1, review_token: tok('e') })
        }
        s.cache.set(key, { contract_version: 'cp7.hpp-pool-outcome.v1', kind: 'COMMITTED_OUTCOME', action: args.p_action, request_id: key, pool_id: row.id,
          pool_number: row.pool_number, status: row.status, row_version: row.row_version, period_start: day, period_end: day,
          correction_of_pool_id: (row.correction_of as Row | null)?.id ?? null,
          journal_entry_id: row.status === 'ACTIVE' || row.status === 'CANCELLED' ? '55555555-5555-4555-8555-555555555555' : null,
          reversal_journal_entry_id: row.status === 'CANCELLED' ? '66666666-6666-4666-8666-666666666666' : null })
      }
      return s.lose ? { data: null, error: { status: 503, message: 'Lost reply' } } : { data: s.cache.get(key), error: null }
    }
    throw new Error('Unexpected ' + name)
  })
  return s
}
const reads = () => client.rpc.mock.calls.filter(([n]) => n === 'erp_cp7_get_hpp_pools_v1').map(([, a]) => a as Row)
const writes = () => client.rpc.mock.calls.filter(([n]) => n === 'erp_cp7_save_hpp_pool_v1').map(([, a]) => a as Row)

let root: Root, container: HTMLDivElement
const onCommitted = vi.fn(async () => true)
function identity(role = 'OWNER', permissions = ['finance.hpp.view', 'finance.hpp.manage']) {
  return { ...recoveryIdentity, identity: { ...recoveryIdentity.identity, profile: { ...recoveryIdentity.identity.profile, role },
    permissions: [...recoveryIdentity.identity.permissions, ...permissions] } }
}
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); onCommitted.mockClear(); seq = 0; auth.current = identity()
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: 'shared', mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<AttendanceHppPoolPanel onCommitted={onCommitted}/>)); await settle() }
function button(name: string) {
  const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(x => x.getAttribute('aria-label') === name || x.textContent === name)
  if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
const hasButton = (name: string) => [...container.querySelectorAll('button')].some(x => x.getAttribute('aria-label') === name || x.textContent === name)
async function click(name: string) { await act(async () => button(name).click()); await settle() }
function el(label: string) { const e = container.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[aria-label="${label}"]`); if (!e) throw new Error(`Missing ${label}`); return e }
async function type(label: string, value: string) {
  const e = el(label), proto = e instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value); e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })) })
  await settle()
}
async function tick(label: string) { await act(async () => el(label).click()); await settle() }
async function previewDay() { await type('Mulai periode pool', day); await type('Akhir periode pool', day); await click('Pratinjau') }
const region = (name: string) => container.querySelector(`[aria-label="${name}"]`)

describe('Pool HPP absensi di HPP & Rekalkulasi (R3-04, owner D16-1)', () => {
  it('lists the pools with plain status words and exact id-ID amounts, without a preview until one is asked for', async () => {
    const s = server(); s.closed = '2026-10-10'
    s.pools = [poolRow(), poolRow({ status: 'ACTIVE', activated_at: '2026-10-17T03:00:00.000000Z', activated_by: 'Admin Satu', activation_reason: 'Sumber cocok', journal_number: 'JRN-7', actions: ['CANCEL'] }),
      poolRow({ status: 'CANCELLED', activated_at: '2026-10-17T03:00:00.000000Z', activated_by: 'Admin Satu', journal_number: 'JRN-8', cancelled_at: '2026-10-17T04:00:00.000000Z',
        cancelled_by: 'Owner Uji', cancellation_reason: 'Kebijakan mandor salah', reversal_journal_number: 'JRN-9', actions: ['REPLACE'], numerator_amount: '1234567.50',
        unit_cost_per_sewn_pcs: '33.333333333333' }),
      poolRow({ status: 'VOIDED', cancelled_at: '2026-10-17T04:00:00.000000Z', cancelled_by: 'Owner Uji', cancellation_reason: 'Draf salah', actions: [] })]
    await mount()
    expect(reads()).toEqual([{ p_offset: 0, p_limit: 20, p_period_start: null, p_period_end: null }])
    expect(region('Pratinjau pool')).toBeNull()
    expect(container.textContent).toContain('Pembukuan ditutup sampai 10 Okt 2026.')
    const status = [...container.querySelectorAll('.hpool-status')].map(x => x.textContent)
    expect(status).toEqual(['Draf', 'Aktif', 'Dibatalkan', 'Dihapus draf'])
    expect(region('Pool AHPP-3')!.textContent).toContain('biaya absensi Rp1.234.567,50')
    expect(region('Pool AHPP-3')!.textContent).toContain('Rp33,333333333333 per pcs')
    expect(region('Pool AHPP-1')!.textContent).toContain('PO-9: 10 pcs → Rp1.000')
    expect(region('Pool AHPP-2')!.textContent).toContain('Diaktifkan')
    expect(region('Pool AHPP-2')!.textContent).toContain('oleh Admin Satu: Sumber cocok · jurnal JRN-7')
    expect(region('Pool AHPP-3')!.textContent).toContain('oleh Owner Uji: Kebijakan mandor salah · jurnal JRN-9')
    expect(region('Pool AHPP-4')!.textContent).toContain('Draf dihapus')
    expect(hasButton('Aktifkan pool AHPP-1') && hasButton('Batalkan pool AHPP-1') && hasButton('Batalkan pool AHPP-2') && hasButton('Buat pool pengganti untuk AHPP-3')).toBe(true)
    expect(hasButton('Aktifkan pool AHPP-2') || hasButton('Batalkan pool AHPP-4')).toBe(false)
    expect(hppPoolRupiah('9007199254740993.01')).toBe('Rp9.007.199.254.740.993,01')
    expect(hppPoolRupiah('50.000000000000')).toBe('Rp50')
  })
  it('previews one period with the Native numbers and creates exactly the reviewed draft with a stable request UUID', async () => {
    const s = server(); await mount(); await previewDay()
    expect(reads().at(-1)).toEqual({ p_offset: 0, p_limit: 20, p_period_start: day, p_period_end: day })
    const preview = region('Pratinjau pool')!.textContent
    expect(preview).toContain('Biaya absensiRp1.000'); expect(preview).toContain('Potong selesai dijahit10 pcs'); expect(preview).toContain('Biaya per pcsRp100')
    expect(preview).toContain('PO-9: 10 pcs'); expect(preview).toContain('Siap dibuat sebagai draf')
    await click('Buat draf pool')
    expect(button('Buat draf pool').disabled).toBe(true)
    await type('Alasan buat draf pool', 'Gaji absensi minggu ini')
    expect(button('Buat draf pool').disabled).toBe(true)
    await tick('Draf pool sudah diperiksa'); expect(button('Buat draf pool').disabled).toBe(false)
    await click('Buat draf pool')
    expect(writes()).toHaveLength(1)
    expect(writes()[0]).toMatchObject({ p_action: 'CREATE', p_payload: { period_start: day, period_end: day, correction_of_pool_id: null, review_token: tok('c'), reason: 'Gaji absensi minggu ini' } })
    expect(writes()[0].p_request).toMatch(/^[0-9a-f-]{36}$/)
    expect(s.effects).toBe(1); expect(onCommitted).toHaveBeenCalledTimes(1)
    expect(container.textContent).toContain('Draf pool AHPP-1 dibuat untuk periode 16 Okt 2026.')
    // Owner rule D18b: after the save the screen is live again (the new draft can be activated, the period re-previewed).
    expect(button('Aktifkan pool AHPP-1').disabled).toBe(false); expect(button('Pratinjau').disabled).toBe(false)
  })
  it('shows a Native refusal as a plain blocker without any figure', async () => {
    const s = server(); s.preview = () => blocked('NO_SEWING_OUTPUT', 'POSITIVE_POOL_ZERO_SEWING_OUTPUT: attendance cost exists but immutable SELESAI_DIJAHIT denominator is zero')
    await mount(); await previewDay()
    const preview = region('Pratinjau pool')!.textContent ?? ''
    expect(preview).toContain('Belum bisa dibuat: Ada biaya absensi, tetapi belum ada setoran selesai jahit')
    expect(preview).not.toMatch(/Rp|pcs/); expect(hasButton('Buat draf pool')).toBe(false)
    s.preview = () => blocked('SOMETHING_NEW', 'Pesan server lain')
    await click('Pratinjau'); expect(region('Pratinjau pool')!.textContent).toContain('Server menolak pratinjau periode ini: Pesan server lain')
  })
  it('explains the closed books in plain words and offers no action there', async () => {
    const s = server(); s.closed = day; s.preview = () => ready({ period_closed: true, can_create: false })
    s.pools = [poolRow({ period_closed: true, actions: [] })]
    await mount(); await previewDay()
    expect(region('Pratinjau pool')!.textContent).toContain('Pembukuan periode ini sudah ditutup sampai 16 Okt 2026, jadi pool untuk periode ini tidak bisa dibuat. Bila memang perlu dibetulkan, buka kembali periodenya di Keuangan → Laporan & Tutup Buku → tab Tutup Buku.')
    expect(region('Pool AHPP-1')!.textContent).toContain('Pembukuan periode pool ini sudah ditutup')
    expect(hasButton('Buat draf pool') || hasButton('Aktifkan pool AHPP-1') || hasButton('Batalkan pool AHPP-1')).toBe(false)
    expect(writes()).toHaveLength(0)
  })
  it('activates, cancels and builds the replacement of the cancelled pool through the server actions only', async () => {
    const s = server(); s.pools = [poolRow()]; await mount()
    await click('Aktifkan pool AHPP-1'); await type('Alasan aktifkan pool AHPP-1', 'Sumber sudah diperiksa')
    expect(region('Form aktifkan pool AHPP-1')!.textContent).toContain('Mengaktifkan membuat jurnal biaya absensi Rp1.000 ke 1 PO')
    await tick('Aktifkan pool AHPP-1 sudah diperiksa'); await click('Simpan: aktifkan pool')
    expect(writes()[0]).toMatchObject({ p_action: 'ACTIVATE', p_payload: { pool_id: s.pools[0].id, review_token: tok('1'), reason: 'Sumber sudah diperiksa' } })
    expect(Object.keys(writes()[0].p_payload as Row).sort()).toEqual(['pool_id', 'reason', 'review_token'])
    expect(container.textContent).toContain('Pool AHPP-1 aktif. Jurnal biaya absensi ke PO sudah dibuat')
    await click('Batalkan pool AHPP-1'); await type('Alasan batalkan pool AHPP-1', 'Kebijakan mandor C belum diisi')
    await tick('Batalkan pool AHPP-1 sudah diperiksa'); await click('Simpan: batalkan pool')
    expect(writes()[1]).toMatchObject({ p_action: 'CANCEL', p_payload: { pool_id: s.pools[0].id, review_token: tok('e') } })
    expect(container.textContent).toContain('Pool AHPP-1 dibatalkan. Jurnal pembalik sudah dibuat')
    const cancelled = s.pools[0].id as string
    s.preview = () => ready({ cancelled_pools: [{ id: cancelled, pool_number: 'AHPP-1' }], denominator_qty: 20, unit_cost_per_sewn_pcs: '50.000000000000', review_token: tok('d'),
      po_count: 2, destination_count: 2, pos: [{ po_id: po, po_number: 'PO-9', sewing_qty: 10 }, { po_id: poB, po_number: 'PO-10', sewing_qty: 10 }] })
    await click('Buat pool pengganti untuk AHPP-1')
    expect(reads().at(-1)).toEqual({ p_offset: 0, p_limit: 20, p_period_start: day, p_period_end: day })
    expect(region('Pratinjau pool')!.textContent).toContain('Biaya per pcsRp50')
    expect(region('Buat draf pool')!.textContent).toContain('Pool ini akan mengganti pool AHPP-1 yang sudah dibatalkan.')
    await type('Alasan buat draf pool', 'Pengganti sesudah kebijakan dibetulkan'); await tick('Draf pool sudah diperiksa'); await click('Buat draf pool pengganti')
    expect(writes()[2]).toMatchObject({ p_action: 'CREATE', p_payload: { correction_of_pool_id: cancelled, review_token: tok('d') } })
    expect(container.textContent).toContain('sebagai pengganti pool yang dibatalkan')
    expect(new Set(writes().map(w => w.p_request)).size).toBe(3); expect(s.effects).toBe(3)
  })
  it('keeps the same request UUID and payload for an answer lost on the way, across a remount', async () => {
    const s = server(); s.pools = [poolRow()]; await mount()
    await click('Aktifkan pool AHPP-1'); await type('Alasan aktifkan pool AHPP-1', 'Sumber sudah diperiksa'); await tick('Aktifkan pool AHPP-1 sudah diperiksa')
    s.lose = true; await click('Simpan: aktifkan pool')
    const sent = structuredClone(writes()[0]); expect(container.textContent).toContain('Hasil transaksi masih belum pasti')
    await act(async () => root.unmount()); root = createRoot(container); s.lose = false; await mount()
    await click('Periksa hasil pool')
    expect(writes()[1]).toEqual(sent); expect(s.effects).toBe(1)
    expect(container.textContent).toContain('Pool AHPP-1 aktif.')
  })
  it('shows a server refusal in plain words and changes nothing on the screen state', async () => {
    const s = server(); s.pools = [poolRow()]; await mount()
    s.refuse = { code: 'P0001', message: 'CP7_HPP_POOL_REVIEW_CHANGED: pool ini berubah sejak diperiksa (mungkin di tab lain).' }
    await click('Aktifkan pool AHPP-1'); await type('Alasan aktifkan pool AHPP-1', 'Sumber sudah diperiksa'); await tick('Aktifkan pool AHPP-1 sudah diperiksa')
    await click('Simpan: aktifkan pool')
    expect(container.textContent).toContain('Data pool atau pratinjau berubah sejak Anda periksa (mungkin di tab lain).')
    expect(container.textContent).not.toContain('CP7_HPP_POOL'); expect(s.effects).toBe(0)
    // A definite refusal leaves no pending request behind (the next attempt gets a new UUID).
    expect(Object.keys(localStorage).some(k => k.includes('HPP_POOL'))).toBe(false)
  })
  it('hides every action without the HPP Rekalkulasi right but still shows the pools', async () => {
    auth.current = identity('ADMIN', ['finance.hpp.view'])
    const s = server(); s.canManage = false; s.pools = [poolRow()]; await mount(); await previewDay()
    expect(container.textContent).toContain('Anda bisa melihat pool. Membuat, mengaktifkan, dan membatalkan pool perlu hak HPP "Rekalkulasi".')
    expect(hasButton('Aktifkan pool AHPP-1') || hasButton('Batalkan pool AHPP-1') || hasButton('Buat draf pool')).toBe(false)
    expect(region('Pool AHPP-1')).not.toBeNull()
  })
  it('reads the pools again when another writer on the page committed, and its controls are live again (owner rule D18b)', async () => {
    const s = server(); s.pools = [poolRow()]; await mount(); expect(reads()).toHaveLength(1)
    await click('Aktifkan pool AHPP-1'); await type('Alasan aktifkan pool AHPP-1', 'Sumber sudah diperiksa')
    await act(async () => root.render(<AttendanceHppPoolPanel onCommitted={onCommitted} refresh={1}/>)); await settle()
    expect(reads()).toHaveLength(2); expect(region('Form aktifkan pool AHPP-1')).toBeNull()
    expect(button('Aktifkan pool AHPP-1').disabled).toBe(false)
  })
  it('renders nothing and reads nothing for a role other than Owner/Admin (KEUANGAN has the HPP rights but not the role)', async () => {
    auth.current = identity('KEUANGAN'); server(); await mount()
    expect(container.innerHTML).toBe(''); expect(client.rpc).not.toHaveBeenCalled()
  })
  it('refuses an answer with an unknown key, a blocked preview with figures, or an outcome for another request', () => {
    const q = { offset: 0, limit: 20, periodStart: day, periodEnd: day }
    const base = { contract_version: 'cp7.hpp-pools.v1', business_DML: false, captured_at: '2026-10-17T03:00:00.000000Z', offset: 0, limit: 20, total: 1, next_offset: null,
      closed_through: null, can_manage: true, pools: [poolRow()], periods: [], preview: ready() }
    expect(parseHppPoolWorkspace(base, q).preview?.reviewToken).toBe(tok('c'))
    expect(() => parseHppPoolWorkspace({ ...base, extra: 1 }, q)).toThrow()
    expect(() => parseHppPoolWorkspace({ ...base, pools: [{ ...poolRow(), secret: 1 }] }, q)).toThrow()
    expect(() => parseHppPoolWorkspace({ ...base, preview: { ...blocked('NO_ATTENDANCE_COST', 'x'), numerator_amount: '1.00' } }, q)).toThrow()
    expect(() => parseHppPoolWorkspace({ ...base, pools: [poolRow({ status: 'VOIDED', actions: ['ACTIVATE'] })] }, q)).toThrow()
    expect(() => parseHppPoolWorkspace({ ...base, pools: [poolRow({ period_closed: true })] }, q)).toThrow()
    expect(() => parseHppPoolWorkspace({ ...base, numerator_amount: 1000 }, q)).toThrow()
    const envelope = { action: 'ACTIVATE', payload: { pool_id: po, review_token: tok('a'), reason: 'alasan saja' }, expectedVersion: null, fingerprint: '', id: '77777777-7777-4777-8777-777777777777', createdAt: '' } as ProductionEnvelope
    const outcome = { contract_version: 'cp7.hpp-pool-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'ACTIVATE', request_id: envelope.id, pool_id: po, pool_number: 'AHPP-1',
      status: 'ACTIVE', row_version: 2, period_start: day, period_end: day, correction_of_pool_id: null, journal_entry_id: poB, reversal_journal_entry_id: null }
    expect(parseHppPoolOutcome(outcome, envelope).status).toBe('ACTIVE')
    expect(() => parseHppPoolOutcome({ ...outcome, request_id: poB }, envelope)).toThrow()
    expect(() => parseHppPoolOutcome({ ...outcome, status: 'DRAFT' }, envelope)).toThrow()
    expect(() => parseHppPoolOutcome({ ...outcome, pool_id: poB }, envelope)).toThrow()
  })
})
