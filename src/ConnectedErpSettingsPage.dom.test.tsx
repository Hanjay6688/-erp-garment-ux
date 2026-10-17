// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedErpSettingsPage from './ConnectedErpSettingsPage'
import { ACCESSORY_POLICY_KEYS, POLICY_LABEL } from './accessoryService'
import { LAU_POLICY_KEYS, LAU_POLICY_LABEL } from './laundryBd'
import { POLICY_EFFECT, ownerChoice, policyStatus, type Cp6PolicyKey } from './cp6Readiness'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { productionKey } from './productionRecovery'

// R3-03 (owner D16-1): Pengaturan ERP lists every owner policy from the server and changes one only through the Native writer of
// its own page (Aksesori / Laundry), with the version that was read, a reason and one request UUID kept for recovery.
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const at = '2026-10-16T03:00:00.000000Z', owner = 'Owner Satu'
const expense = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1', asset = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2', revenue = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3'
type Over = Record<string, unknown>
function policy(key: Cp6PolicyKey, label: string, admin: boolean, over: Over = {}) {
  const status = (over.status ?? 'PENDING_POLICY_VALUE') as 'SET' | 'PENDING_POLICY_VALUE', value = (over.value ?? null) as Record<string, unknown> | null
  const reason = admin ? (over.reason as string | undefined) ?? 'Default fail-closed: belum ditetapkan owner' : null
  const version = (over.version as string | undefined) ?? '1'
  return { key, label, status, status_text: policyStatus({ key, status, value }), pending_effect: status === 'SET' ? null : POLICY_EFFECT[key],
    owner_choice: ownerChoice(key) !== null, version, set_at: at, set_by: admin && status === 'SET' ? owner : null, reason, value: admin ? value : null,
    event_count: Number(version), events: [{ version, status, value: admin ? value : null, reason, set_at: at, set_by: admin && status === 'SET' ? owner : null }],
    ...(over.raw as Over | undefined) }
}
function ws(admin = true, over: { acc?: Record<string, Over>; lau?: Record<string, Over>; top?: Over; accFamily?: Over; lauFamily?: Over } = {}) {
  return { contract_version: 'cp7.erp-settings.v1', read_at: at, can_see_values: admin,
    families: [
      { family: 'ACCESSORY', label: 'Kebijakan aksesori', source_page: 'Aksesori, bagian Kebijakan & area', visible: true, can_set: admin,
        policies: ACCESSORY_POLICY_KEYS.map(k => policy(k, POLICY_LABEL[k], admin, over.acc?.[k])), ...over.accFamily },
      { family: 'LAUNDRY', label: 'Kebijakan laundry', source_page: 'Laundry, bagian Harga & Tagihan, Kebijakan owner', visible: true, can_set: admin,
        policies: LAU_POLICY_KEYS.map(k => policy(k, LAU_POLICY_LABEL[k], admin, over.lau?.[k])), ...over.lauFamily }],
    cutover_visible: admin,
    cutover: admin ? { version: 1, cutover_date: '2026-09-01', set_at: at, set_by: owner, reason: 'Mulai pakai aplikasi', change_on: 'Impor data awal' } : null,
    choices: admin ? { accounts: [{ id: asset, code: '1150', name: 'PPN Masukan', type: 'ASSET' }, { id: expense, code: '6100', name: 'Beban Servis', type: 'EXPENSE' },
      { id: revenue, code: '4900', name: 'Pendapatan Lain', type: 'REVENUE' }], accounts_total: 3, categories: [], categories_total: 0, users: [], users_total: 0,
      zones: [], zones_total: 0 } : null,
    business_DML: false, ...over.top }
}
const saved = (args: Record<string, unknown>, version: string, status = 'SET') => {
  const p = args.p_payload as Record<string, unknown>
  return args.p_action === 'SET_POLICY' && String(p.policy_key).startsWith('LAU')
    ? { action: 'SET_POLICY', request_id: args.p_client_request_id, status, policy_key: String(p.policy_key).replace('-', '_'), value: p.value ?? null, version }
    : { policy_key: p.policy_key, status: 'SAVED', value: p.value ?? null, version, request_id: args.p_client_request_id, action: 'SET_POLICY', document_id: null, row_version: null }
}
let root: Root, container: HTMLDivElement
const identity = (permissions: string[]) => ({ ...recoveryIdentity, identity: { ...recoveryIdentity.identity, permissions } })
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); client.rpc.mockReset()
  auth.current = identity(['settings.erp.view', 'settings.erp.manage', 'warehouse.accessory.view', 'production.laundry.view'])
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: n, mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { for (let i = 0; i < 3; i++) await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount(onOpenImport?: () => void) { await act(async () => root.render(<ConnectedErpSettingsPage onOpenImport={onOpenImport}/>)); await settle() }
const card = (key: string) => { const el = container.querySelector(`[aria-label="Kebijakan ${key}"]`); if (!el) throw new Error(`Missing ${key}: ${container.textContent}`); return el }
function button(name: string, scope: ParentNode = container) {
  const b = [...scope.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === name); if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
async function click(name: string, scope?: ParentNode) { await act(async () => button(name, scope).click()); await settle() }
function field<T extends HTMLElement>(label: string) { const el = container.querySelector<T>(`[aria-label="${label}"]`); if (!el) throw new Error(`Missing ${label}`); return el }
async function type(label: string, value: string) {
  const el = field<HTMLInputElement>(label)
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })) })
}
async function tick(label: string) { await act(async () => field<HTMLInputElement>(label).click()); await settle() }
const calls = (name: string) => client.rpc.mock.calls.filter(([n]) => n === name)

describe('Pengaturan ERP (R3-03, owner D16-1)', () => {
  it('lists every owner policy of both pages with the server status, the readiness texts and the read-only cutover date', async () => {
    client.rpc.mockResolvedValue({ data: ws(true, { acc: { 'ACC-DEC01': { status: 'SET', value: { mode: 'BOTH_REAL_TIMELINES' }, version: '3', reason: 'Garis waktu nyata' } } }), error: null })
    const openImport = vi.fn()
    await mount(openImport)
    expect(client.rpc).toHaveBeenCalledWith('erp_cp7_get_erp_settings_v1')
    for (const key of [...ACCESSORY_POLICY_KEYS, ...LAU_POLICY_KEYS]) expect(card(key)).toBeTruthy()
    expect(card('ACC-DEC01').textContent).toContain('Ditetapkan di aplikasi')
    expect(card('ACC-DEC01').textContent).toContain('Cara: Tanggal fisik dan pencatatan terpisah')
    expect(card('ACC-DEC01').textContent).toContain('Versi 3')
    expect(card('ACC-DEC01').textContent).toContain('Alasan: Garis waktu nyata')
    expect(card('ACC-DEC03').textContent).toContain('Perlu isian owner')
    expect(card('ACC-DEC03').textContent).toContain(POLICY_EFFECT['ACC-DEC03'])
    expect(card('LAU-DEC04').textContent).toContain('Keputusan owner belum diterapkan')
    expect(card('LAU-DEC05').textContent).toContain('Sengaja tidak diaktifkan')
    expect(container.querySelector('[aria-label="Kesiapan pengaturan transaksi"]')?.textContent).toContain('11 pengaturan belum diterapkan')
    const cutover = container.querySelector('[aria-label="Tanggal mulai pakai aplikasi"]')!
    expect(cutover.textContent).toContain('Berlaku: 1 September 2026')
    expect(cutover.textContent).toContain('Owner mengubahnya di menu Impor data awal')
    expect(cutover.querySelector('input')).toBeNull()
    await click('Buka Impor data awal'); expect(openImport).toHaveBeenCalledTimes(1)
  })

  it('sets an accessory policy through the Aksesori writer with the read version, then reads again and frees both writers', async () => {
    let version = '1'
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_erp_settings_v1') return { data: ws(true, { acc: { 'ACC-DEC01': version === '1' ? {} : { status: 'SET', value: { mode: 'BOTH_REAL_TIMELINES' }, version } } }), error: null }
      if (name === 'erp_save_accessory_service_action_v1') { version = '2'; return { data: saved(args, '2'), error: null } }
      throw new Error(name)
    })
    await mount()
    await click('Ubah ACC-DEC01', card('ACC-DEC01'))
    expect(button('Tetapkan ACC-DEC01').disabled).toBe(true)
    expect(field<HTMLInputElement>('Perubahan ACC-DEC01 sudah diperiksa').disabled).toBe(true)
    await type('Alasan perubahan ACC-DEC01', 'Garis waktu nyata')
    expect(container.textContent).toContain('Akan ditetapkan: Cara: Tanggal fisik dan pencatatan terpisah.')
    expect(button('Kembalikan ACC-DEC01 ke menunggu').disabled).toBe(true)
    await tick('Perubahan ACC-DEC01 sudah diperiksa')
    await click('Tetapkan ACC-DEC01')
    const sent = calls('erp_save_accessory_service_action_v1')
    expect(sent).toHaveLength(1)
    expect(sent[0][1]).toEqual({ p_action: 'SET_POLICY', p_client_request_id: expect.stringMatching(/^[0-9a-f-]{36}$/),
      p_payload: { policy_key: 'ACC_DEC01', operation: 'SET', expected_version: '1', reason: 'Garis waktu nyata', value: { mode: 'BOTH_REAL_TIMELINES' } } })
    expect(calls('erp_save_laundry_bd_action_v1')).toHaveLength(0)
    expect(calls('erp_cp7_get_erp_settings_v1')).toHaveLength(2)
    expect(container.querySelector('[role="status"].cset-done')?.textContent).toBe('ACC-DEC01 tersimpan: ditetapkan, versi 2. Pengaturan dibaca ulang dari server.')
    expect(card('ACC-DEC01').textContent).toContain('Ditetapkan di aplikasi')
    expect(localStorage.getItem(productionKey('disposable:actor-1', 'ACCESSORY_SERVICE'))).toBeNull()
    // Both writers are free again after the save (best practice D18b).
    expect(button('Ubah ACC-DEC03', card('ACC-DEC03')).disabled).toBe(false)
    expect(button('Ubah LAU-DEC01', card('LAU-DEC01')).disabled).toBe(false)
  })

  it('sets a laundry policy with the owner decision through the Laundry writer, and clears an accessory one without a value', async () => {
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_erp_settings_v1') return { data: ws(true, { lau: { 'LAU-DEC04': { version: '2' } }, acc: { 'ACC-DEC05': { status: 'SET', version: '4', value: { mode: 'CREDIT_UNPAID_ONLY', credit_conditions: ['USABLE'] } } } }), error: null }
      if (name === 'erp_save_laundry_bd_action_v1') return { data: saved(args, '3'), error: null }
      if (name === 'erp_save_accessory_service_action_v1') return { data: saved(args, '5'), error: null }
      throw new Error(name)
    })
    await mount()
    await click('Ubah LAU-DEC04', card('LAU-DEC04'))
    await click('Isi sesuai keputusan owner', card('LAU-DEC04'))
    expect(field<HTMLSelectElement>('Penjualan').value).toBe('ALLOW_PENDING')
    await tick('Perubahan LAU-DEC04 sudah diperiksa')
    await click('Tetapkan LAU-DEC04')
    expect(calls('erp_save_laundry_bd_action_v1')[0][1]).toEqual({ p_action: 'SET_POLICY', p_client_request_id: expect.any(String),
      p_payload: { policy_key: 'LAU-DEC04', operation: 'SET', expected_version: '2', reason: 'Terapkan keputusan owner 26 Sep 2026 untuk LAU-DEC04', value: { sale_with_unknown_laundry: 'ALLOW_PENDING' } } })
    expect(container.textContent).toContain('LAU-DEC04 tersimpan: ditetapkan, versi 3.')
    await click('Ubah ACC-DEC05', card('ACC-DEC05'))
    await type('Alasan perubahan ACC-DEC05', 'Kembali menunggu keputusan')
    await tick('Perubahan ACC-DEC05 sudah diperiksa')
    await click('Kembalikan ACC-DEC05 ke menunggu')
    expect(calls('erp_save_accessory_service_action_v1')[0][1].p_payload).toEqual({ policy_key: 'ACC_DEC05', operation: 'CLEAR', expected_version: '4', reason: 'Kembali menunggu keputusan' })
  })

  it('says a stale version in plain words, reads again and keeps no unsure request', async () => {
    client.rpc.mockImplementation(async (name: string) => {
      if (name === 'erp_cp7_get_erp_settings_v1') return { data: ws(), error: null }
      return { data: null, error: { code: 'P0001', message: 'STALE_VERSION: pengaturan ACC_DEC01 berubah; muat ulang' } }
    })
    await mount()
    await click('Ubah ACC-DEC01', card('ACC-DEC01'))
    await type('Alasan perubahan ACC-DEC01', 'Garis waktu nyata'); await tick('Perubahan ACC-DEC01 sudah diperiksa')
    await click('Tetapkan ACC-DEC01')
    expect(container.textContent).toContain('Pengaturan ini baru saja diubah di layar lain. Muat ulang pengaturan, periksa nilai terbaru, lalu simpan lagi bila masih perlu.')
    expect(calls('erp_cp7_get_erp_settings_v1')).toHaveLength(2)
    expect(localStorage.getItem(productionKey('disposable:actor-1', 'ACCESSORY_SERVICE'))).toBeNull()
  })

  it('keeps an unanswered save with its UUID and reconciles it with the same UUID and payload', async () => {
    let lost = true
    client.rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
      if (name === 'erp_cp7_get_erp_settings_v1') return { data: ws(), error: null }
      if (lost) { lost = false; throw new TypeError('Failed to fetch') }
      return { data: saved(args, '2'), error: null }
    })
    await mount()
    await click('Ubah LAU-DEC01', card('LAU-DEC01'))
    await tick('Borongan per batch'); await type('Alasan perubahan LAU-DEC01', 'Borongan diizinkan'); await tick('Perubahan LAU-DEC01 sudah diperiksa')
    await click('Tetapkan LAU-DEC01')
    expect(localStorage.getItem(productionKey('disposable:actor-1', 'LAUNDRY_BD'))).not.toBeNull()
    expect(button('Ubah ACC-DEC01', card('ACC-DEC01')).disabled).toBe(true)
    await click('Periksa hasil simpan kebijakan')
    const sent = calls('erp_save_laundry_bd_action_v1')
    expect(sent).toHaveLength(2)
    expect(sent[1][1]).toEqual(sent[0][1])
    expect(sent[0][1].p_payload).toEqual({ policy_key: 'LAU-DEC01', operation: 'SET', expected_version: '1', reason: 'Borongan diizinkan', value: { units: ['BATCH'] } })
    expect(localStorage.getItem(productionKey('disposable:actor-1', 'LAUNDRY_BD'))).toBeNull()
  })

  it('shows statuses without values, names or edit controls to a reader who is not owner/admin', async () => {
    auth.current = identity(['settings.erp.view', 'warehouse.accessory.view', 'production.laundry.view'])
    client.rpc.mockResolvedValue({ data: ws(false, { acc: { 'ACC-DEC01': { status: 'SET', value: { mode: 'BOTH_REAL_TIMELINES' }, version: '2' } } }), error: null })
    await mount()
    expect(card('ACC-DEC01').textContent).toContain('Ditetapkan di aplikasi')
    expect(card('ACC-DEC01').textContent).toContain('Rincian hanya terlihat owner/admin')
    expect(card('ACC-DEC01').textContent).not.toContain('Tanggal fisik dan pencatatan terpisah')
    expect(container.querySelectorAll('button').length).toBe(1)
    expect(container.textContent).toContain('Tanggal mulai pakai aplikasi hanya terlihat oleh owner dan admin.')
    expect(container.textContent).toContain('Isi kebijakan, alasan, dan siapa yang mengubahnya hanya terlihat oleh owner dan admin.')
  })

  it('refuses a reply that gives a value to a reader who may not see it, or misses a policy, and says so without figures', async () => {
    auth.current = identity(['settings.erp.view'])
    const leaky = ws(false); (leaky.families[0].policies as Array<Record<string, unknown>>)[0].value = { mode: 'BOTH_REAL_TIMELINES' }
    client.rpc.mockResolvedValueOnce({ data: leaky, error: null })
    await mount()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Pengaturan belum terbaca. Pengaturan ERP tidak terbaca lengkap (isi kebijakan hanya untuk owner/admin).')
    expect(container.querySelector('[aria-label="Kebijakan ACC-DEC01"]')).toBeNull()
    await act(async () => root.unmount()); root = createRoot(container)
    const short = ws(); (short.families[1].policies as unknown[]).pop()
    client.rpc.mockResolvedValueOnce({ data: short, error: null })
    await mount()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('daftar kebijakan tidak lengkap')
    expect(container.textContent).not.toMatch(/\d+ pengaturan belum diterapkan/)
  })

  it('names the missing family right and the denied read, and needs settings.erp.view to open', async () => {
    client.rpc.mockResolvedValueOnce({ data: ws(true, { lauFamily: { visible: false, can_set: false, policies: null } }), error: null })
    await mount()
    expect(container.querySelector('[aria-label="Kebijakan laundry"]')?.textContent).toContain('Hak melihat laundry diperlukan untuk membaca kebijakan ini.')
    expect(card('ACC-DEC01')).toBeTruthy()
    await act(async () => root.unmount()); root = createRoot(container)
    client.rpc.mockResolvedValueOnce({ data: null, error: { code: '42501', message: 'CP7_ERP_SETTINGS_DENIED' } })
    await mount()
    expect(container.querySelector('[role="alert"]')?.textContent).toBe('Pengaturan belum terbaca. Akun tidak memiliki izin untuk operasi ini.')
    await act(async () => root.unmount()); root = createRoot(container)
    client.rpc.mockClear(); auth.current = identity(['warehouse.accessory.view'])
    await mount()
    expect(container.textContent).toContain('Hak melihat pengaturan ERP diperlukan.')
    expect(client.rpc).not.toHaveBeenCalled()
  })

  it('keeps every save closed while the settings are being read again', async () => {
    let release: (() => void) | null = null
    client.rpc.mockResolvedValueOnce({ data: ws(), error: null })
    await mount()
    await click('Ubah ACC-DEC01', card('ACC-DEC01'))
    await type('Alasan perubahan ACC-DEC01', 'Garis waktu nyata'); await tick('Perubahan ACC-DEC01 sudah diperiksa')
    expect(button('Tetapkan ACC-DEC01').disabled).toBe(false)
    client.rpc.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve({ data: ws(), error: null }) }))
    await act(async () => button('Muat ulang pengaturan').click())
    expect(button('Tetapkan ACC-DEC01').disabled).toBe(true)
    await act(async () => { release!() }); await settle()
    expect(calls('erp_save_accessory_service_action_v1')).toHaveLength(0)
  })
})
