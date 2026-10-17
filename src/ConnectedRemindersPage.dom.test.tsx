// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedRemindersPage from './ConnectedRemindersPage'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { productionKey, readProductionRecovery } from './productionRecovery'
import { parseRemindersWorkspace, reminderQuery, reminderRefusal } from './remindersContract'

// R3-03 (owner D16-1): the connected Reminder page. Synthetic DOM checks against a fake facade that keeps the Native rules
// (own rows, row_version, OPEN-only edit, CANCELLED final, one answer per request id); the Native, race, real-Auth HTTP
// and browser evidence is scripts/cp7_r3_reminders_cases.py and scripts/cp7_r3_reminders_browser.mjs.
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const scope = 'disposable:actor-1'
const identity = (permissions: string[]) => ({ ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions } })
const manager = identity(['settings.reminder.view', 'settings.reminder.manage'])
const viewer = identity(['settings.reminder.view'])
type Row = { id: string; title: string; note: string; due_at: string; priority: string; module: string; status: 'OPEN' | 'DONE' | 'CANCELLED'
  completed_at: string | null; cancelled_at: string | null; cancellation_reason: string | null; created_at: string; updated_at: string; row_version: number }
const ids = ['0f6c1d8e-0000-4000-8000-000000000001', '0f6c1d8e-0000-4000-8000-000000000002', '0f6c1d8e-0000-4000-8000-000000000003', '0f6c1d8e-0000-4000-8000-000000000004']
const row = (n: number, extra: Partial<Row> = {}): Row => ({ id: ids[n], title: `Pengingat ${n}`, note: '', due_at: '2026-10-18T02:00:00+00:00', priority: 'NORMAL',
  module: 'Laundry', status: 'OPEN', completed_at: null, cancelled_at: null, cancellation_reason: null, created_at: '2026-10-16T01:00:00+00:00',
  updated_at: '2026-10-16T01:00:00+00:00', row_version: 1, ...extra })
const now = Date.parse('2026-10-17T03:00:00Z')
const wibDay = (iso: string) => new Date(Date.parse(iso) + 7 * 3600e3).toISOString().slice(0, 10)
function dueState(r: Row) {
  if (r.status !== 'OPEN') return null
  const t = Date.parse(r.due_at)
  return t <= now ? 'OVERDUE' : wibDay(r.due_at) === '2026-10-17' ? 'TODAY' : wibDay(r.due_at) === '2026-10-18' ? 'TOMORROW' : 'LATER'
}
const rank = { OPEN: 0, DONE: 1, CANCELLED: 2 }, prio: Record<string, number> = { URGENT: 0, NORMAL: 1, LOW: 2 }
function server(initial: Row[], options: { loseReply?: boolean; refuse?: { code: string; message: string } } = {}) {
  const rows = initial.map(r => ({ ...r })), answers = new Map<string, unknown>(), saves: Record<string, unknown>[] = []
  let created = 0
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_get_reminders_v1') {
      const q = args.p_query as { filter: string; limit: number; offset: number }
      const want = { ACTIVE: ['OPEN', 'DONE'], OPEN: ['OPEN'], DONE: ['DONE'], CANCELLED: ['CANCELLED'], ALL: ['OPEN', 'DONE', 'CANCELLED'] }[q.filter]!
      const list = rows.filter(r => want.includes(r.status)).sort((a, b) => rank[a.status] - rank[b.status] || prio[a.priority] - prio[b.priority]
        || (a.status === 'OPEN' ? a.due_at : a.updated_at).localeCompare(b.status === 'OPEN' ? b.due_at : b.updated_at) || a.id.localeCompare(b.id))
      const open = rows.filter(r => r.status === 'OPEN'), window = Math.min(list.length, 200)
      const items = list.slice(q.offset, q.offset + q.limit).map(r => ({ ...r, due_state: dueState(r) }))
      return { data: { contract_version: 'cp7.reminders-workspace.v1', filter: q.filter,
        page: { limit: q.limit, offset: q.offset, total: list.length, shown: items.length, window, window_limit: 200,
          next_offset: q.offset + q.limit < window ? q.offset + q.limit : null, beyond_window: list.length - window },
        items, counts: { open: open.length, done: rows.filter(r => r.status === 'DONE').length, cancelled: rows.filter(r => r.status === 'CANCELLED').length },
        due: { overdue: open.filter(r => dueState(r) === 'OVERDUE').length, today: open.filter(r => dueState(r) === 'TODAY').length,
          tomorrow: open.filter(r => dueState(r) === 'TOMORROW').length, complete: open.length <= 200 },
        today: '2026-10-17', read_at: '2026-10-17T03:00:00+00:00', can_manage: true, business_DML: false }, error: null }
    }
    if (name !== 'erp_cp7_save_reminder_v1') throw new Error(name)
    saves.push(structuredClone(args))
    if (options.refuse) return { data: null, error: { ...options.refuse, details: null, hint: null } }
    const key = String(args.p_request)
    if (!answers.has(key)) {
      const p = args.p_payload as Record<string, string | null>, action = String(args.p_action), expected = args.p_expected === null ? null : Number(args.p_expected)
      let target = rows.find(r => r.id === p.id)
      if (action === 'SAVE' && p.id === null) {
        target = row(0, { id: `0f6c1d8e-0000-4000-8000-00000000010${created++}`, title: String(p.title), note: String(p.note), due_at: String(p.due_at),
          priority: String(p.priority), module: String(p.module) }); rows.push(target)
      } else {
        if (!target) return { data: null, error: { code: 'P0001', message: 'CP7_REMINDERS_NOT_FOUND' } }
        if (target.row_version !== expected) return { data: null, error: { code: 'P0001', message: 'CP7_REMINDERS_STALE' } }
        target.row_version += 1; target.updated_at = '2026-10-17T03:00:01+00:00'
        if (action === 'SAVE') Object.assign(target, { title: p.title, note: p.note, due_at: p.due_at, priority: p.priority, module: p.module })
        if (action === 'DONE') Object.assign(target, { status: 'DONE', completed_at: '2026-10-17T03:00:01+00:00' })
        if (action === 'UNDONE') Object.assign(target, { status: 'OPEN', completed_at: null })
        if (action === 'CANCEL') Object.assign(target, { status: 'CANCELLED', cancelled_at: '2026-10-17T03:00:01+00:00', cancellation_reason: p.reason })
      }
      answers.set(key, { contract_version: 'cp7.reminders-outcome.v1', kind: 'COMMITTED_OUTCOME', action, request_id: key, created: action === 'SAVE' && p.id === null,
        reminder_id: target.id, status: target.status, row_version: target.row_version })
      if (options.loseReply) { options.loseReply = false; throw new TypeError('Failed to fetch') }
    }
    return { data: answers.get(key), error: null }
  })
  return { rows, saves }
}
let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset(); auth.current = manager
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: n, mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { await act(async () => { await new Promise(r => setTimeout(r, 0)) }); await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<ConnectedRemindersPage/>)); await settle() }
function field<T extends HTMLElement = HTMLInputElement>(label: string) { const el = container.querySelector<T>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}: ${container.textContent}`); return el }
function button(name: string) { const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === name || x.getAttribute('aria-label') === name); if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b }
async function click(name: string) { await act(async () => button(name).click()); await settle() }
async function type(label: string, value: string) {
  const el = field<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(label)
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}

describe('Reminder page on real data (R3-03)', () => {
  it('reads the server list with its counts and WIB due state, and adds one through the facade', async () => {
    const s = server([row(1, { title: 'Telepon laundry', due_at: '2026-10-17T01:00:00+00:00', priority: 'URGENT' }), row(2, { status: 'DONE', completed_at: '2026-10-16T05:00:00+00:00' })])
    await mount()
    expect(client.rpc.mock.calls[0]).toEqual(['erp_cp7_get_reminders_v1', { p_query: { filter: 'ACTIVE', limit: 25, offset: 0 } }])
    expect(container.textContent).toContain('1 belum selesai · 1 sudah selesai · 0 dibatalkan')
    expect(container.textContent).toContain('1 lewat jatuh tempo · 0 jatuh tempo hari ini · 0 besok (WIB)')
    expect(field<HTMLElement>('Pengingat Telepon laundry').textContent).toContain('Lewat jatuh tempo')
    expect(field<HTMLElement>('Pengingat Pengingat 2').textContent).toContain('Selesai')
    // A DONE reminder is reopened first (Native rule): no "Ubah" on it.
    expect(container.querySelector('[aria-label="Ubah Pengingat 2"]')).toBeNull()
    expect(button('Tambah pengingat').disabled).toBe(true)
    await type('Judul pengingat', '  Cek kiriman susulan  '); await type('Catatan pengingat', 'POT-041')
    expect(container.textContent).toContain('Isi tanggal dan jam jatuh tempo (WIB).')
    await type('Jatuh tempo pengingat (WIB)', '2026-10-18T09:00'); await type('Prioritas pengingat', 'LOW'); await type('Modul pengingat', 'Laundry')
    await click('Tambah pengingat')
    expect(s.saves).toHaveLength(1)
    expect(s.saves[0]).toMatchObject({ p_action: 'SAVE', p_expected: null,
      p_payload: { id: null, title: 'Cek kiriman susulan', note: 'POT-041', due_at: '2026-10-18T02:00:00.000Z', priority: 'LOW', module: 'Laundry' } })
    expect(String(s.saves[0].p_request)).toMatch(/^[0-9a-f-]{36}$/)
    expect(container.textContent).toContain('Pengingat "Cek kiriman susulan" ditambahkan.')
    expect(field<HTMLElement>('Pengingat Cek kiriman susulan').textContent).toContain('Besok')
    expect(field('Judul pengingat').value).toBe('')
    expect(readProductionRecovery(scope).pending.REMINDER).toBeUndefined()
  })

  it('edits, completes, reopens and cancels with a reason, each with the version it read; a cancelled one has no action', async () => {
    const s = server([row(1, { title: 'Bayar laundry' })]); await mount()
    await click('Ubah Bayar laundry')
    expect(container.textContent).toContain('Belum ada yang diubah.'); expect(button('Simpan perubahan').disabled).toBe(true)
    await type('Judul pengingat', 'Bayar laundry Intan'); await click('Simpan perubahan')
    expect(s.saves[0]).toMatchObject({ p_action: 'SAVE', p_expected: '1', p_payload: { id: ids[1], title: 'Bayar laundry Intan' } })
    expect(container.textContent).toContain('Perubahan pengingat "Bayar laundry Intan" disimpan.')
    await click('Tandai selesai Bayar laundry Intan')
    expect(s.saves[1]).toMatchObject({ p_action: 'DONE', p_expected: '2', p_payload: { id: ids[1] } })
    expect(container.textContent).toContain('Pengingat "Bayar laundry Intan" ditandai selesai.')
    await click('Buka lagi Bayar laundry Intan')
    expect(s.saves[2]).toMatchObject({ p_action: 'UNDONE', p_expected: '3', p_payload: { id: ids[1] } })
    await click('Batalkan Bayar laundry Intan')
    expect(button('Batalkan pengingat').disabled).toBe(true); expect(container.textContent).toContain('Tulis alasan batal (minimal 5 huruf).')
    await type('Alasan batal Bayar laundry Intan', 'Sudah dibayar kemarin'); await click('Batalkan pengingat')
    expect(s.saves[3]).toEqual({ p_action: 'CANCEL', p_payload: { id: ids[1], reason: 'Sudah dibayar kemarin' }, p_request: s.saves[3].p_request, p_expected: '4' })
    expect(new Set(s.saves.map(x => x.p_request)).size).toBe(4)
    await click('Dibatalkan')
    const item = field<HTMLElement>('Pengingat Bayar laundry Intan')
    expect(item.textContent).toContain('Dibatalkan'); expect(item.textContent).toContain('Sudah dibayar kemarin'); expect(item.querySelectorAll('button')).toHaveLength(0)
  })

  it('keeps the request id of a lost reply and checks it with the same id and payload after a reload, writing once', async () => {
    const s = server([row(1, { title: 'Telepon mandor' })], { loseReply: true }); await mount()
    await click('Tandai selesai Telepon mandor')
    const first = structuredClone(s.saves[0])
    expect(localStorage.getItem(productionKey(scope, 'REMINDER'))).not.toBeNull()
    expect(container.textContent).toContain('Respons transaksi tidak pasti')
    await act(async () => root.unmount()); root = createRoot(container); await mount()
    // The lost reply did commit: the list shows it DONE, and every writer stays closed until the old request is checked.
    expect(button('Buka lagi Telepon mandor').disabled).toBe(true); expect(button('Tambah pengingat').disabled).toBe(true)
    await click('Periksa hasil simpan pengingat')
    expect(s.saves).toHaveLength(2); expect(s.saves[1]).toEqual(first)
    expect(s.rows[0]).toMatchObject({ status: 'DONE', row_version: 2 })
    expect(localStorage.getItem(productionKey(scope, 'REMINDER'))).toBeNull()
    expect(container.textContent).toContain('Pengingat "Telepon mandor" ditandai selesai.')
  })

  it('shows a refused write in plain words and clears its request; a stale one says to reload', async () => {
    server([row(1, { title: 'Cek stok' })], { refuse: { code: 'P0001', message: 'CP7_REMINDERS_STALE' } }); await mount()
    await click('Tandai selesai Cek stok')
    expect(container.textContent).toContain('Pengingat ini baru saja diubah di tab atau perangkat lain. Muat ulang daftar, periksa isinya, lalu ulangi.')
    expect(container.textContent).not.toContain('CP7_REMINDERS_STALE')
    expect(localStorage.getItem(productionKey(scope, 'REMINDER'))).toBeNull()
  })

  it('says plainly when the account may not use reminders, without any number, and hides writing for a view-only role', async () => {
    client.rpc.mockResolvedValue({ data: null, error: { code: '42501', message: 'CP7_REMINDERS_ROLE_DENIED', details: null, hint: null } })
    await mount()
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(reminderRefusal('CP7_REMINDERS_ROLE_DENIED'))
    expect(container.querySelector('[aria-label="Judul pengingat"]')).toBeNull(); expect(container.textContent).not.toMatch(/\d/)
    await act(async () => root.unmount()); root = createRoot(container)
    auth.current = viewer; client.rpc.mockReset(); server([row(1, { title: 'Hanya lihat' })]); await mount()
    expect(container.textContent).toContain('Akun ini hanya bisa melihat pengingat.')
    expect(field<HTMLElement>('Pengingat Hanya lihat').querySelectorAll('button')).toHaveLength(0)
    await act(async () => root.unmount()); root = createRoot(container)
    auth.current = identity(['dashboard.view']); client.rpc.mockReset(); await mount()
    expect(client.rpc).not.toHaveBeenCalled(); expect(container.textContent).toContain('Hak melihat Reminder diperlukan')
  })

  it('pages inside the server window and refuses a reply that does not match its own facts', async () => {
    server(Array.from({ length: 30 }, (_, n) => row(0, { id: `0f6c1d8e-0000-4000-8000-${String(n).padStart(12, '0')}`, title: `R${n}` }))); await mount()
    expect(container.textContent).toContain('1–25 dari 30')
    await click('Pengingat berikutnya')
    expect(client.rpc.mock.calls.at(-1)).toEqual(['erp_cp7_get_reminders_v1', { p_query: { filter: 'ACTIVE', limit: 25, offset: 25 } }])
    expect(container.textContent).toContain('26–30 dari 30')
    const good = (await client.rpc('erp_cp7_get_reminders_v1', { p_query: reminderQuery('ACTIVE') })).data as Record<string, unknown>
    expect(() => parseRemindersWorkspace({ ...good, extra: 1 }, reminderQuery('ACTIVE'))).toThrow('ruang kerja')
    expect(() => parseRemindersWorkspace({ ...good, counts: { open: 29, done: 0, cancelled: 0 } }, reminderQuery('ACTIVE'))).toThrow('jumlah')
    expect(() => parseRemindersWorkspace(good, reminderQuery('OPEN'))).toThrow('filter')
  })
})
