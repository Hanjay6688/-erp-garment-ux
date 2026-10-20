// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedRemindersPage from './ConnectedRemindersPage'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import {
  alertNumber, alertSummary, isMaterialReorderDetail, parseSystemAlerts, parseWaSaveResult, parseWaWorkspace, resolutionLabel, waDraftFromSettings, waRefusal,
  waSettingsPayload, type SystemAlert, type WaDraft,
} from './waContract'

// WA-4 (owner D17-3..D17-6): the Pengingat sistem and Sambungan WhatsApp tabs against a fake of the six public RPCs of
// scripts/cp7-src/alerts/alerts.sql that keeps their rules (owner only, revision check, digest outside quiet hours, enable
// needs number and key, three tests an hour, one answer per request id, only UNKNOWN can be marked). Test data only:
// phone +620000000000 and keys FAKEKEY-*.
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))

const as = (role: string, permissions: string[]) => ({ ...recoveryIdentity, identity: { ...recoveryIdentity.identity, profile: { ...recoveryIdentity.identity.profile, role }, permissions } })
const owner = as('OWNER', ['settings.reminder.view', 'settings.reminder.manage'])
const staff = as('STAFF', ['settings.reminder.view', 'settings.reminder.manage', 'finance.ar.view'])
const PHONE = '+620000000000'
const NOW = '2026-10-19T03:00:00+00:00', LATER = '2026-10-19T03:05:00+00:00'
const id = (n: number) => `0f6c1d8e-0000-4000-8000-${String(n).padStart(12, '0')}`
const RUN = id(900)
const wib = formatCp6WibDateTime

// ------------------------------------------------------------ Pengingat sistem --
const analysisDetail = (extra: Record<string, unknown>) => ({ run_id: RUN, data_as_of: '2026-10-19T01:00:00+00:00', checked_at: '2026-10-19T02:30:00+00:00',
  label: null, target_key: null, need_snapshot_pcs: null, need_now_pcs: null, increase_pcs: null, material_id: null, material_name: null, value: null, unit: null,
  threshold: null, reason: 'NEED_STILL_OPEN_NOW', ...extra })
const waState = (state: string, extra: Record<string, unknown> = {}) => ({ state, round: 0, reason: null, dispatch_id: null, dispatch_status: null, settled_at: null, ...extra })
const row = (n: number, kind: string, title: string, detail: Record<string, unknown>, extra: Record<string, unknown> = {}) => ({
  id: id(n), kind, subject_key: `${kind}:${n}`, episode: 1, title, detail, party_names: [] as string[], state: 'OPEN', opened_at: '2026-10-19T02:00:00+00:00',
  refreshed_at: '2026-10-19T02:40:00+00:00', resolved_at: null as string | null, resolution: null as string | null, wa: null as unknown, ...extra })
const fabric = (sku: string, name: string, qty: string) => ({ material_id: id(100 + qty.length), material_sku: sku, material_name: name, unit_code: 'kg', qty, minimum_qty: '60' })
const resolved = (resolution: string) => ({ state: 'RESOLVED', resolved_at: '2026-10-18T05:00:00+00:00', resolution })
// SS-1: cp7_stock_formula.alert_row of a finished good at or under its reorder point (its subject is the item, root:size).
const fgDetail = (n: number, extra: Record<string, unknown> = {}) => ({ root_id: id(200 + n), size_id: id(300 + n), sku: 'KML-M', product_name: 'Kemeja Linen',
  size_code: 'M', free_pcs: '23', wip_pcs: '0', wip_status: 'COMPLETE', position_pcs: '23', reorder_point_pcs: '36', basis: 'FORMULA', daily_mean: '3.90',
  lead_days: '7', lead_basis: 'PROFILE', buffer_mode: 'STATISTICAL', safety_pcs: '8.3', service_level: '0.95', ...extra })
const fgSubject = (n: number) => `${id(200 + n)}:${id(300 + n)}`
// SS-2/SS-3, owner D17-10/D17-12: cp7_stock_formula.material_alert_row of a fabric on the formula (on order counted; a row of
// FABRIC_BELOW_MINIMUM, "Stok kain di bawah minimum") and of an accessory at or under its typed minimum (no formula).
const fabricReorder = (n: number, extra: Record<string, unknown> = {}) => ({ material_id: id(400 + n), material_type: 'FABRIC', sku: 'KC-HTM-2', name: 'Katun Hitam',
  unit_code: 'YD', free_qty: '56', on_order_qty: '20', reorder_point_qty: '98.51', basis: 'FORMULA', daily_mean: '7.47', lead_days: '6', safety_qty: '17.08',
  service_level: '0.95', ...extra })
const accessoryReorder = (n: number, extra: Record<string, unknown> = {}) => ({ material_id: id(400 + n), material_type: 'ACCESSORY', sku: 'KCG-12', name: 'Kancing 12 mm',
  unit_code: 'PCS', free_qty: '180', on_order_qty: '0', reorder_point_qty: '250', basis: 'MANUAL', daily_mean: '3.33', lead_days: null, safety_qty: null,
  service_level: null, ...extra })
function alertRows(withWa: boolean) {
  const w = (state: string, extra: Record<string, unknown> = {}) => withWa ? waState(state, extra) : null
  return [
    row(1, 'FABRIC_BELOW_MINIMUM', 'Stok kain di bawah minimum: Katun Combed 30s Hitam', fabric('KC30-HTM', 'Katun Combed 30s Hitam', '42.50'),
      { wa: w('ACCEPTED', { dispatch_id: 7, dispatch_status: 'PROVIDER_ACCEPTED', settled_at: '2026-10-19T02:01:00+00:00' }) }),
    row(2, 'AR_DUE', 'Piutang jatuh tempo: S-0012', { sale_id: id(102), number: 'S-0012', open_balance: '1250000.00', due_date: '2026-10-18', state: 'OVERDUE', as_of: '2026-10-19' },
      { party_names: ['Toko Contoh'], wa: w('HELD_QUIET') }),
    row(3, 'AP_DUE', 'Tagihan supplier jatuh tempo: PO-0007', { purchase_id: id(103), purchase_number: 'PO-0007', invoice_numbers: '["INV-9"]', remaining: '3000000',
      due_date: '2026-10-19', state: 'DUE_TODAY', as_of: '2026-10-19' }, { party_names: ['Supplier Contoh'], wa: w('PENDING') }),
    row(4, 'PRODUCTION_GAP', 'Kekurangan produksi: Kemeja A M', analysisDetail({ label: 'Kemeja A M', target_key: 'P1:M', need_snapshot_pcs: 150, need_now_pcs: '120',
      increase_pcs: '30', threshold: 50 }), { wa: w('UNKNOWN', { dispatch_id: 12, dispatch_status: 'UNKNOWN', settled_at: '2026-10-19T02:50:00+00:00' }) }),
    row(5, 'FABRIC_NEED', 'Kain perlu dibeli: Drill Navy untuk Celana B', analysisDetail({ label: 'Celana B', material_id: id(105), material_name: 'Drill Navy', value: '35.5',
      unit: 'm', threshold: '10', reason: 'FABRIC_NEED_UNCHANGED_SINCE_SNAPSHOT' }), { wa: w('KIND_OFF', { reason: 'KIND_OFF', settled_at: '2026-10-19T02:01:00+00:00' }) }),
    row(6, 'FABRIC_BELOW_MINIMUM', 'Stok kain di bawah minimum: Rayon Merah', fabric('RY-MRH', 'Rayon Merah', '61'),
      { ...resolved('AT_OR_ABOVE_MINIMUM'), wa: w('RESOLVED_BEFORE_SEND', { reason: 'AT_OR_ABOVE_MINIMUM', settled_at: '2026-10-18T05:00:00+00:00' }) }),
    row(7, 'PRODUCTION_GAP', 'Kekurangan produksi: Kaos C S', analysisDetail({ label: 'Kaos C S', need_now_pcs: '5' }),
      { ...resolved('RECHECK_SOMETHING_NEW'), episode: 2, wa: w('ACCEPTED', { round: 1, dispatch_id: 6, dispatch_status: 'PROVIDER_ACCEPTED', settled_at: '2026-10-18T01:00:00+00:00' }) }),
    row(8, 'AR_DUE', 'Piutang jatuh tempo: S-0009', { sale_id: id(108), number: 'S-0009', open_balance: '0', due_date: '2026-10-10', state: 'OVERDUE', as_of: '2026-10-17' },
      { ...resolved('SOMETHING_UNMAPPED'), party_names: ['Toko Lain'], wa: w('ACCEPTED') }),
    row(9, 'FG_AT_REORDER_POINT', 'Stok barang jadi menipis: Kemeja Linen M', fgDetail(9), { subject_key: fgSubject(9),
      wa: w('ACCEPTED', { dispatch_id: 8, dispatch_status: 'PROVIDER_ACCEPTED', settled_at: '2026-10-19T02:41:00+00:00' }) }),
    row(12, 'FABRIC_BELOW_MINIMUM', 'Stok kain di bawah minimum: Katun Hitam', fabricReorder(12), { subject_key: id(412), wa: w('PENDING') }),
    row(13, 'ACCESSORY_AT_REORDER_POINT', 'Stok aksesori menipis: Kancing 12 mm', accessoryReorder(13), { subject_key: id(413), wa: w('HELD_QUIET') }),
  ]
}
const kindsOwner = [
  { kind: 'ACCESSORY_AT_REORDER_POINT', last_try_at: '2026-10-19T02:59:00+00:00', last_ok_at: '2026-10-19T02:59:00+00:00', last_error: null, open_count: 1 },
  { kind: 'AP_DUE', last_try_at: '2026-10-19T02:59:00+00:00', last_ok_at: '2026-10-19T02:59:00+00:00', last_error: null, open_count: 1 },
  { kind: 'AR_DUE', last_try_at: '2026-10-19T02:59:00+00:00', last_ok_at: '2026-10-19T02:00:00+00:00', last_error: '42501 CP7_ALERT_AR_SOURCE_DENIED', open_count: 1 },
  { kind: 'FABRIC_BELOW_MINIMUM', last_try_at: '2026-10-19T02:59:00+00:00', last_ok_at: '2026-10-19T02:59:00+00:00', last_error: null, open_count: 2 },
  { kind: 'FABRIC_NEED', last_try_at: null, last_ok_at: null, last_error: null, open_count: null },
  { kind: 'FG_AT_REORDER_POINT', last_try_at: '2026-10-19T02:59:00+00:00', last_ok_at: '2026-10-19T02:59:00+00:00', last_error: null, open_count: 1 },
  { kind: 'PRODUCTION_GAP', last_try_at: null, last_ok_at: null, last_error: null, open_count: null },
]
const analysisStatus = {
  run: { run_id: RUN, data_as_of: '2026-10-19T01:00:00+00:00', phase: 'DONE', rule: 'FABRIC_NEED', next_offset: 4, checked: 9, still_open: 2, closed: 6, rule_off: 1,
    error: null, started_at: '2026-10-19T02:20:00+00:00', updated_at: '2026-10-19T02:31:00+00:00', finished_at: '2026-10-19T02:31:00+00:00' },
  request: { request_id: id(950), state: 'SKIPPED_NO_CHANGE', query: null, freshness: 'NO_RECORDED_CHANGE', created_at: '2026-10-19T02:45:00+00:00', requested_at: null, error: null },
  tick: { at: '2026-10-19T02:59:00+00:00', outcome: 'NOT_DUE' },
}
function alertsReply(who: 'OWNER' | 'STAFF', configured = true) {
  const rows = alertRows(who === 'OWNER')
  return { contract_version: 'cp7.system-alerts.v1', read_at: NOW, configured, collector: configured ? { at: '2026-10-19T02:59:00+00:00', outcome: 'COLLECTED' } : null,
    analysis: who === 'OWNER' ? analysisStatus : null, kinds: who === 'OWNER' ? kindsOwner : kindsOwner.filter(k => k.kind === 'AR_DUE'),
    rows: who === 'OWNER' ? rows : rows.filter(r => r.kind === 'AR_DUE') }
}


// OW01_UI_01..09: expected results were declared in ACCESSORY_NEED_UI_EXPECTED.md
// before execution. These twenty keys describe a review notice, never a known
// purchase quantity. Deep-clone the old reply: kindsOwner/analysisStatus are shared.
const ACCESSORY_TITLE = 'Kebutuhan aksesori perlu diperiksa: Kemeja A M'
const ACCESSORY_KIND_LABEL = 'Kebutuhan aksesori perlu diperiksa (dari analisis)'
const accessoryNeedDetail = (extra: Record<string, unknown> = {}) => ({
  run_id: RUN, data_as_of: '2026-10-19T01:00:00+00:00', checked_at: '2026-10-19T02:30:00+00:00',
  label: 'Kemeja A M', target_key: `${id(601)}:${id(602)}`, category_key: `ACCESSORY_CATEGORY:${id(603)}`, category_name: 'Kancing',
  state: 'DATA_REVIEW', verdict: 'REVIEW_REQUIRED_NOW', gross_state: 'ASSUMED', gross_qty: '186', unit: 'PCS',
  installed_state: 'UNKNOWN', installed_proven: null, unused_allocated_state: 'UNKNOWN', unused_allocated_proven: null,
  additional_external_state: 'UNKNOWN', additional_external: null, threshold_status: 'NOT_EVALUATED_UNKNOWN',
  reason: 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN', ...extra,
})
function accessoryAlertsReply(extra: Record<string, unknown> = {}) {
  const reply = structuredClone(alertsReply('OWNER')), d = accessoryNeedDetail(extra)
  reply.kinds.push({ kind: 'ACCESSORY_NEED', last_try_at: null, last_ok_at: null, last_error: null, open_count: null })
  reply.rows.push(row(61, 'ACCESSORY_NEED', ACCESSORY_TITLE, d, {
    subject_key: `ACCESSORY_NEED:${d.target_key}:${d.category_key}`, wa: waState('PENDING'),
  }))
  if (!reply.analysis) throw new Error('The owner fixture must include analysis status.')
  reply.analysis.run = { ...reply.analysis.run, rule: 'ACCESSORY_NEED', next_offset: 1, checked: 10, still_open: 3 }
  return reply
}
const accessoryRow = () => field<HTMLElement>(`[aria-label="Pengingat sistem ${ACCESSORY_TITLE}"]`)
const accessRefusal = (status: number) => ({ data: null, error: {
  status, code: status === 401 ? 'PGRST301' : '42501', message: 'Current source read refused', details: null, hint: null,
} })
const accessRefusalText = (status: number) => status === 401
  ? 'Sesi berakhir. Silakan masuk ulang.' : 'Akun tidak memiliki izin untuk operasi ini.'
function expectAccessoryFactsRetired(status: number) {
  const system = panel('Pengingat sistem')
  expect(system.querySelector('[role="alert"]')?.textContent).toBe(accessRefusalText(status))
  expect(system.querySelector(`[aria-label="Pengingat sistem ${ACCESSORY_TITLE}"]`)).toBeNull()
  expect(system.querySelector('[aria-label="Status analisis"]')).toBeNull()
  for (const oldFact of ['Kemeja A M', 'Kancing', '186', 'kebutuhan BOM', 'WA: menunggu',
    `Data analisis per ${wib('2026-10-19T01:00:00+00:00')}`, `dicek ulang ${wib('2026-10-19T02:30:00+00:00')}`])
    expect(system.textContent).not.toContain(oldFact)
}

// ---------------------------------------------------------- Sambungan WhatsApp --
// The server defaults (alerts.sql defaults()): the finished-goods kind forwarded (SS-1), automatic analysis every 240 minutes (D17-7).
const defaults = { revision: 0, enabled: false, phone_e164: null as string | null, detail: 'SUMMARY', digest_times: ['08:00', '15:00'],
  kinds: ['MANUAL_REMINDER', 'FABRIC_BELOW_MINIMUM', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
    'PRODUCTION_GAP', 'FABRIC_NEED', 'ACCESSORY_NEED', 'OPENING_AR', 'OPENING_AP', 'PAYROLL_AP', 'ACCESSORY_AP', 'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED'], repeat_minutes: 1440,
  burst_after_per_day: 30, burst_merge_minutes: 30, max_items: 10, quiet_enabled: true, quiet_start: '21:00', quiet_end: '06:00', analysis_every_minutes: 240,
  analysis_start: '07:00', analysis_end: '20:00' }
type Settings = typeof defaults & { saved_at?: string }
type Dispatch = { id: number; kind: string; status: string; queued_at: string; answered_at: string | null; http_status: number | null; provider_text: string | null
  body: string | null; digest_slot: string | null; resolved_outcome: string | null; resolved_at: string | null; items: number }
const dispatch = (n: number, extra: Partial<Dispatch>): Dispatch => ({ id: n, kind: 'INSTANT', status: 'PROVIDER_ACCEPTED', queued_at: '2026-10-19T01:00:00+00:00',
  answered_at: '2026-10-19T01:00:05+00:00', http_status: 200, provider_text: 'Message queued', body: `⚠ ERP Enteng · 19 Okt 08.00\nPesan ${n}\nBuka ERP > Reminder`,
  digest_slot: null, resolved_outcome: null, resolved_at: null, items: 2, ...extra })
type WaFake = { settings: Settings; keyPresent: boolean; keySetAt: string | null; transport: boolean; quietNow: boolean; dispatches: Dispatch[]; tests: number
  lose: Set<string>; calls: [string, Record<string, unknown>][] }
const refuse = (code: string, message: string) => ({ data: null, error: { code, message, details: null, hint: null } })
const inQuiet = (s: { quiet_start: string; quiet_end: string }, t: string) => s.quiet_start < s.quiet_end ? t >= s.quiet_start && t < s.quiet_end : t >= s.quiet_start || t < s.quiet_end
function server(options: { alerts?: 'OWNER' | 'STAFF'; configured?: boolean; wa?: Partial<WaFake>; alertsData?: ReturnType<typeof alertsReply> } = {}) {
  const fake: WaFake = { settings: { ...defaults }, keyPresent: false, keySetAt: null, transport: true, quietNow: false, dispatches: [], tests: 0, lose: new Set(), calls: [], ...options.wa }
  const answers = new Map<string, { args: string; data: unknown }>()
  const once = (key: string, args: unknown, run: () => { data: unknown; error: unknown }) => {
    const prior = answers.get(key)
    if (prior) return prior.args === JSON.stringify(args) ? { data: { ...(prior.data as object), replay: true }, error: null } : refuse('22023', 'CP7_WA_REQUEST_REUSED')
    const out = run()
    if (!out.error) answers.set(key, { args: JSON.stringify(args), data: out.data })
    return out
  }
  client.rpc.mockImplementation(async (name: string, args: Record<string, unknown> = {}) => {
    fake.calls.push([name, structuredClone(args)])
    const isOwner = (auth.current as typeof owner).identity.profile.role === 'OWNER'
    if (name === 'erp_cp7_get_reminders_v1') {
      const q = args.p_query as { filter: string; limit: number; offset: number }
      return { data: { contract_version: 'cp7.reminders-workspace.v1', filter: q.filter,
        page: { limit: q.limit, offset: q.offset, total: 0, shown: 0, window: 0, window_limit: 200, next_offset: null, beyond_window: 0 }, items: [],
        counts: { open: 0, done: 0, cancelled: 0 }, due: { overdue: 0, today: 0, tomorrow: 0, complete: true }, today: '2026-10-19', read_at: NOW, can_manage: true,
        business_DML: false }, error: null }
    }
    if (name === 'erp_cp7_get_alerts_v1') return { data: options.alertsData ?? alertsReply(options.alerts ?? (isOwner ? 'OWNER' : 'STAFF'), options.configured ?? true), error: null }
    if (!isOwner) return refuse('42501', 'CP7_WA_OWNER_ONLY')
    const key = String(args.p_request ?? '')
    const lost = fake.lose.has(name)
    const answer = (() => {
      if (name === 'erp_cp7_get_wa_settings_v1') return { data: { contract_version: 'cp7.wa-settings.v1', read_at: NOW, settings: fake.settings, defaults,
        key_present: fake.keyPresent, key_set_at: fake.keySetAt, transport_is_callmebot: fake.transport, quiet_now: fake.quietNow, analysis: analysisStatus,
        ticks: { COLLECT: { at: '2026-10-19T02:59:00+00:00', outcome: 'COLLECTED' }, SEND: { at: '2026-10-19T02:59:30+00:00', outcome: 'WA_OFF' } },
        outbox: { ACCEPTED: 4, PENDING: 2 }, dispatches: [...fake.dispatches].sort((a, b) => b.id - a.id) }, error: null }
      if (name === 'erp_cp7_save_wa_settings_v1') return once(key, args.p, () => {
        const p = args.p as Record<string, unknown> & typeof defaults & { expected_revision: number }
        if (p.quiet_enabled && p.digest_times.some(t => inQuiet(p, t))) return refuse('22023', 'CP7_WA_DIGEST_IN_QUIET_HOURS')
        if (p.expected_revision !== fake.settings.revision) return refuse('40001', 'CP7_WA_SETTINGS_STALE')
        if (p.enabled && (!p.phone_e164 || !fake.keyPresent)) return refuse('22023', 'CP7_WA_ENABLE_NEEDS_PHONE_AND_KEY')
        const { expected_revision, ...rest } = p
        fake.settings = { ...rest, revision: expected_revision + 1, digest_times: [...rest.digest_times].sort(), kinds: [...rest.kinds].sort(), saved_at: LATER }
        return { data: { replay: false, settings: fake.settings }, error: null }
      })
      if (name === 'erp_cp7_set_wa_key_v1') return once(key, {}, () => {
        if (!/^[A-Za-z0-9_-]{4,64}$/.test(String(args.p_key))) return refuse('22023', 'CP7_WA_KEY_FORMAT')
        fake.keyPresent = true; fake.keySetAt = LATER
        return { data: { replay: false, key_present: true, key_set_at: LATER }, error: null }
      })
      if (name === 'erp_cp7_send_wa_test_v1') return once(key, {}, () => {
        if (!fake.settings.phone_e164) return refuse('22023', 'CP7_WA_PHONE_MISSING')
        if (!fake.keyPresent) return refuse('22023', 'CP7_WA_KEY_MISSING')
        if (fake.tests >= 3) return refuse('22023', 'CP7_WA_TEST_LIMIT')
        fake.tests += 1
        const d = dispatch(Math.max(0, ...fake.dispatches.map(x => x.id)) + 1, { kind: 'TEST', status: 'QUEUED', queued_at: LATER, answered_at: null, http_status: null,
          provider_text: null, body: '✅ Pesan uji ERP Enteng · 19 Okt 10.05. Kalau pesan ini masuk, sambungan WhatsApp sudah benar.', items: 0 })
        fake.dispatches.push(d)
        return { data: { replay: false, dispatch_id: d.id, status: 'QUEUED' }, error: null }
      })
      if (name === 'erp_cp7_resolve_wa_dispatch_v1') return once(key, args.p, () => {
        const p = args.p as { dispatch_id: number; outcome: string }
        const d = fake.dispatches.find(x => x.id === p.dispatch_id)
        if (!d || d.status !== 'UNKNOWN' || d.resolved_outcome) return refuse('22023', 'CP7_WA_RESOLVE_NOT_UNKNOWN')
        d.resolved_outcome = p.outcome; d.resolved_at = LATER
        return { data: { replay: false, dispatch_id: d.id, resolved_outcome: p.outcome }, error: null }
      })
      throw new Error(`unexpected ${name}`)
    })()
    if (lost) { fake.lose.delete(name); throw new TypeError('Failed to fetch') }
    return answer
  })
  return fake
}

let root: Root, container: HTMLDivElement
beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear(); client.rpc.mockReset(); auth.current = owner
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (n: string, _o: LockOptions, cb: (l: Lock | null) => Promise<unknown>) => cb({ name: n, mode: 'exclusive' } as Lock) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); sessionStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function settle() { for (let i = 0; i < 3; i++) await act(async () => { await new Promise(r => setTimeout(r, 0)) }) }
async function mount() { await act(async () => root.render(<ConnectedRemindersPage/>)); await settle() }
function field<T extends HTMLElement = HTMLInputElement>(selector: string) { const el = container.querySelector<T>(selector); if (!el) throw new Error(`Missing ${selector}: ${container.textContent}`); return el }
const input = (label: string) => field<HTMLInputElement>(`input[aria-label="${label}"], select[aria-label="${label}"]`)
function button(name: string) {
  const b = [...container.querySelectorAll<HTMLButtonElement>('button')].find(x => x.textContent === name || x.getAttribute('aria-label') === name || x.getAttribute('aria-label')?.startsWith(`${name} (`))
  if (!b) throw new Error(`Missing ${name}: ${container.textContent}`); return b
}
async function click(name: string) { await act(async () => button(name).click()); await settle() }
async function tab(name: string) { const t = [...container.querySelectorAll<HTMLButtonElement>('[role="tab"]')].find(x => x.textContent === name); if (!t) throw new Error(`No tab ${name}`); await act(async () => t.click()); await settle() }
async function type(label: string, value: string) {
  const el = input(label)
  const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  await act(async () => { Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, value); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) })
}
async function check(label: string) { await act(async () => input(label).click()) }
const panel = (label: string) => field<HTMLElement>(`[aria-label="${label}"]`)
const tabs = () => [...container.querySelectorAll('[role="tab"]')].map(t => t.textContent)
const calls = (fake: WaFake, name: string) => fake.calls.filter(c => c[0] === name).map(c => c[1])

describe('Reminder tabs: Pengingat sistem and Sambungan WhatsApp (WA-4)', () => {
  it('D17-14 renders all seven obligation domains with exact known money and honest unknowns', async () => {
    const domains = ['OPENING_AR', 'OPENING_AP', 'PAYROLL_AP', 'ACCESSORY_AP', 'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED']
    const labels = ['Piutang saldo awal', 'Utang saldo awal', 'Tagihan gaji', 'Kredit retur aksesori mandor', 'Tagihan laundry',
      'Penerimaan laundry perlu diperiksa', 'Laundry awal belum ditagih']
    const reply = alertsReply('OWNER')
    const newRows = domains.map((domain, i) => row(700 + i, domain, `Perlu diperiksa: Dokumen ${i}`, {
      domain, source_id: id(800 + i), label: `Dokumen ${i}`, remaining_state: i < 5 ? 'KNOWN' : 'UNKNOWN',
      remaining: i < 5 ? '9007199254740993.01' : null, due_date: null, state: 'DATA_REVIEW',
      reason: i < 5 ? 'MISSING_RECORDED_DUE_DATE' : 'VALUE_PENDING', economic_state: i < 5 ? 'OPEN' : 'UNKNOWN', as_of: '2026-10-19', source_hash: 'a'.repeat(64),
    }, { subject_key: `${domain === 'OPENING_AR' ? 'AR_DUE' : 'AP_DUE'}:${domain}:${id(800 + i)}`, wa: waState('PENDING') }))
    reply.rows = newRows
    reply.kinds = [...reply.kinds, ...domains.map(kind => ({ kind, last_try_at: NOW, last_ok_at: NOW, last_error: null, open_count: 1 }))]
    const parsed = parseSystemAlerts(reply, { owner: true })
    expect(parsed.rows.map(r => r.kind)).toEqual(domains)
    expect(alertSummary(parsed.rows[0])).toContain('9.007.199.254.740.993,01')
    expect(alertSummary(parsed.rows[5])).toContain('Nilai belum diketahui')
    expect(alertSummary(parsed.rows[5])).not.toContain('Rp0')
    const fake = server({ alertsData: reply }); await mount(); await tab('Pengingat sistem')
    for (const label of labels) expect(panel('Pengingat sistem').querySelector(`section[aria-label="${label}"]`)).not.toBeNull()
    expect(panel('Pengingat sistem').textContent).toContain('Tanggal jatuh tempo belum tercatat')
    expect(panel('Pengingat sistem').textContent).toContain('Nilai tagihan final belum tersedia')
    await tab('Sambungan WhatsApp')
    for (const label of labels) expect(input(`Teruskan ${label}`).checked).toBe(true)
    await click('Simpan pengaturan')
    expect((calls(fake, 'erp_cp7_save_wa_settings_v1')[0].p as { kinds: string[] }).kinds).toEqual(defaults.kinds)
  })

  it('D17-14 rejects mismatched obligation identity and money coerced to a JS number', () => {
    const reply = alertsReply('OWNER')
    reply.rows = [row(700, 'PAYROLL_AP', 'Gaji perlu diperiksa', { domain: 'PAYROLL_AP', source_id: id(800), label: 'Gaji',
      remaining_state: 'KNOWN', remaining: '0.01', due_date: null, state: 'DATA_REVIEW', reason: 'MISSING_RECORDED_DUE_DATE',
      economic_state: 'OPEN', as_of: '2026-10-19', source_hash: 'a'.repeat(64) }, { subject_key: `AP_DUE:PAYROLL_AP:${id(800)}` })]
    reply.kinds = [...reply.kinds, { kind: 'PAYROLL_AP', last_try_at: NOW, last_ok_at: NOW, last_error: null, open_count: 1 }]
    expect(() => parseSystemAlerts(reply, { owner: true })).not.toThrow()
    const malformed = (change: Record<string, unknown>) => ({ ...reply, rows: [{ ...reply.rows[0], detail: { ...reply.rows[0].detail, ...change } }] })
    expect(() => parseSystemAlerts(malformed({ remaining: 0.01 }), { owner: true })).toThrow('nilai kewajiban')
    expect(() => parseSystemAlerts(malformed({ remaining: null }), { owner: true })).toThrow('nilai kewajiban')
    expect(() => parseSystemAlerts(malformed({ domain: 'OPENING_AP' }), { owner: true })).toThrow('jenis kewajiban')
    expect(() => parseSystemAlerts(malformed({ state: 'ACTIVE' }), { owner: true })).toThrow('nilai kewajiban')
    expect(() => parseSystemAlerts({ ...reply, rows: [{ ...reply.rows[0], subject_key: `AP_DUE:PAYROLL_AP:${id(801)}` }] }, { owner: true })).toThrow('pengingat')
  })

  it('parses the documented shapes and refuses unknown or missing keys', () => {
    const good = alertsReply('OWNER')
    const parsed = parseSystemAlerts(good, { owner: true })
    expect(parsed.rows).toHaveLength(11)
    expect(parsed.kinds.map(k => k.kind)).toEqual(['ACCESSORY_AT_REORDER_POINT', 'AP_DUE', 'AR_DUE', 'FABRIC_BELOW_MINIMUM', 'FABRIC_NEED',
      'FG_AT_REORDER_POINT', 'PRODUCTION_GAP'])
    expect(parsed.rows[3].detail).toMatchObject({ kind: 'PRODUCTION_GAP', needSnapshotPcs: '150', needNowPcs: '120', threshold: '50' })
    // The analysis detail as the brief lists it (only the keys of its kind) is the same contract.
    const lean = structuredClone(good); const gap = lean.rows[3].detail as Record<string, unknown>
    for (const k of ['material_id', 'material_name', 'value', 'unit']) delete gap[k]
    expect(parseSystemAlerts(lean, { owner: true }).rows[3].detail.kind).toBe('PRODUCTION_GAP')
    expect(() => parseSystemAlerts({ ...good, extra: 1 }, { owner: true })).toThrow('Respons pengingat sistem tidak cocok (pengingat sistem)')
    const noRows: Record<string, unknown> = structuredClone(good); delete noRows.rows
    expect(() => parseSystemAlerts(noRows, { owner: true })).toThrow('(pengingat sistem)')
    expect(() => parseSystemAlerts({ ...good, rows: [{ ...good.rows[0], surprise: true }] }, { owner: true })).toThrow('(pengingat)')
    expect(() => parseSystemAlerts({ ...good, rows: [{ ...good.rows[0], detail: { ...good.rows[0].detail, extra: 1 } }] }, { owner: true })).toThrow('rincian stok')
    expect(() => parseSystemAlerts({ ...good, rows: [{ ...good.rows[3], detail: { ...good.rows[3].detail, mystery: 1 } }] }, { owner: true })).toThrow('rincian analisis')
    expect(() => parseSystemAlerts(good, { owner: false })).toThrow('status WA')
    expect(() => parseSystemAlerts({ ...good, rows: [{ ...good.rows[0], state: 'RESOLVED' }] }, { owner: true })).toThrow('status')
    expect(() => parseSystemAlerts({ ...good, analysis: null }, { owner: true })).toThrow('analisis')
    expect(() => parseSystemAlerts(alertsReply('STAFF'), { owner: false })).not.toThrow()
    expect(() => parseSystemAlerts({ ...alertsReply('STAFF'), rows: alertRows(false) }, { owner: false })).toThrow('jenis pengingat')

    const ws = { contract_version: 'cp7.wa-settings.v1', read_at: NOW, settings: defaults, defaults, key_present: false, key_set_at: null, transport_is_callmebot: true,
      quiet_now: false, analysis: analysisStatus, ticks: {}, outbox: {}, dispatches: [dispatch(2, {}), dispatch(1, { kind: 'DIGEST', digest_slot: NOW, status: 'NOTHING_DUE', body: null, http_status: null })] }
    expect(parseWaWorkspace(ws).dispatches.map(d => d.id)).toEqual([2, 1])
    expect(() => parseWaWorkspace({ ...ws, api_key: 'x' })).toThrow('sambungan')
    const missing: Record<string, unknown> = { ...defaults }; delete missing.quiet_end
    expect(() => parseWaWorkspace({ ...ws, settings: missing })).toThrow('Respons sambungan WhatsApp tidak cocok (pengaturan)')
    expect(() => parseWaWorkspace({ ...ws, settings: { ...defaults, revision: 2 } })).toThrow('pengaturan')
    expect(() => parseWaWorkspace({ ...ws, dispatches: [dispatch(1, { status: 'NOTHING_DUE' })] })).toThrow('riwayat')
    expect(() => parseWaWorkspace({ ...ws, ticks: { SLEEP: { at: NOW, outcome: null } } })).toThrow('jadwal')
    // D17-10: the separate fabric kind is gone; settings or defaults that still name it are refused.
    expect(() => parseWaWorkspace({ ...ws, settings: { ...defaults, kinds: [...defaults.kinds, 'FABRIC_AT_REORDER_POINT'] } })).toThrow('pengaturan')

    const draft: WaDraft = { ...waDraftFromSettings(parseWaWorkspace(ws).settings), phone: PHONE, digestTimes: ['15:00', '', '08:00', ''] }
    const payload = waSettingsPayload(draft, 0)
    expect(Object.keys(payload as object).sort()).toEqual(['analysis_end', 'analysis_every_minutes', 'analysis_start', 'burst_after_per_day', 'burst_merge_minutes', 'detail',
      'digest_times', 'enabled', 'expected_revision', 'kinds', 'max_items', 'phone_e164', 'quiet_enabled', 'quiet_end', 'quiet_start', 'repeat_minutes'])
    expect(payload).toMatchObject({ expected_revision: 0, phone_e164: PHONE, digest_times: ['08:00', '15:00'], repeat_minutes: 1440 })
    const saved = { ...defaults, phone_e164: PHONE, revision: 1, saved_at: LATER, kinds: [...defaults.kinds].sort() }
    expect(parseWaSaveResult({ replay: false, settings: saved }, payload).settings.revision).toBe(1)
    expect(() => parseWaSaveResult({ replay: false, settings: { ...saved, revision: 3 } }, payload)).toThrow('hasil simpan')
    expect(() => parseWaSaveResult({ replay: false, settings: { ...saved, max_items: 9 } }, payload)).toThrow('hasil simpan')
    expect(waRefusal('CP7_WA_TEST_LIMIT')).toContain('3 kali dalam satu jam')
  })

  it('shows the WhatsApp tab to the owner only, and tells each who receives their own reminders', async () => {
    let fake = server(); auth.current = staff; await mount()
    expect(tabs()).toEqual(['Pengingat saya', 'Pengingat sistem'])
    expect(container.querySelector('[role="tablist"]')?.getAttribute('aria-label')).toBe('Bagian pengingat')
    expect(container.textContent).toContain('Pengingat ini tidak dikirim ke mana pun: tidak lewat WhatsApp, email, atau notifikasi.')
    expect(container.textContent).not.toContain('Sambungan WhatsApp')
    // Opening a tab is what reads it: before that only the own reminders are read.
    expect(fake.calls.map(c => c[0])).toEqual(['erp_cp7_get_reminders_v1'])
    await act(async () => root.unmount()); root = createRoot(container)
    client.rpc.mockReset(); fake = server(); auth.current = owner; await mount()
    expect(tabs()).toEqual(['Pengingat saya', 'Pengingat sistem', 'Sambungan WhatsApp'])
    expect(container.textContent).toContain('Bila Sambungan WhatsApp menyala, pengingat Bos yang waktunya sudah tiba juga diteruskan ke WhatsApp Bos sendiri.')
    expect(container.textContent).not.toContain('tidak dikirim lewat WhatsApp')
    await tab('Sambungan WhatsApp')
    expect(calls(fake, 'erp_cp7_get_wa_settings_v1')).toEqual([{}])
    expect(panel('Sambungan WhatsApp').closest('[role="tabpanel"]')?.hasAttribute('hidden')).toBe(false)
    expect(field<HTMLElement>('#creminders-panel-MINE').hidden).toBe(true)
    await tab('Pengingat saya')
    expect(field<HTMLElement>('#creminders-panel-WA').hidden).toBe(true)
    expect(button('Muat ulang pengingat').disabled).toBe(false)
  })

  it('lists the system reminders by kind with their numbers, analysis time, WhatsApp state and resolution', async () => {
    const fake = server(); await mount(); await tab('Pengingat sistem')
    expect(calls(fake, 'erp_cp7_get_alerts_v1')).toEqual([{ p: { resolved_days: 7 } }])
    const groups = [...panel('Pengingat sistem').querySelectorAll('.csys-group')].map(g => g.getAttribute('aria-label'))
    expect(groups).toEqual(['Stok kain di bawah minimum', 'Stok aksesori menipis', 'Stok barang jadi menipis', 'Kain perlu dibeli (dari analisis)',
      'Kekurangan produksi (dari analisis)',
      'Tagihan supplier jatuh tempo', 'Piutang pelanggan jatuh tempo'])
    const text = (title: string) => field<HTMLElement>(`[aria-label="Pengingat sistem ${title}"]`).textContent ?? ''
    expect(text('Stok kain di bawah minimum: Katun Combed 30s Hitam')).toContain('Sisa 42,5 kg, minimum 60 kg · SKU KC30-HTM')
    expect(text('Stok kain di bawah minimum: Katun Combed 30s Hitam')).toContain(`Muncul ${wib('2026-10-19T02:00:00+00:00')} · diperbarui ${wib('2026-10-19T02:40:00+00:00')}`)
    expect(text('Stok kain di bawah minimum: Katun Combed 30s Hitam')).toContain('WA: terkirim')
    expect(text('Piutang jatuh tempo: S-0012')).toContain('Nota S-0012 · sisa Rp1.250.000 · jatuh tempo 18 Okt 2026 (lewat jatuh tempo) · Pelanggan Toko Contoh')
    expect(text('Piutang jatuh tempo: S-0012')).toContain('WA: jam tenang')
    expect(text('Tagihan supplier jatuh tempo: PO-0007')).toContain('Pembelian PO-0007 · sisa Rp3.000.000 · jatuh tempo 19 Okt 2026 (jatuh tempo hari ini) · faktur INV-9 · Supplier Supplier Contoh')
    expect(text('Tagihan supplier jatuh tempo: PO-0007')).toContain('WA: menunggu')
    const analysisLine = `Data analisis per ${wib('2026-10-19T01:00:00+00:00')}, dicek ulang ${wib('2026-10-19T02:30:00+00:00')}`
    expect(text('Kekurangan produksi: Kemeja A M')).toContain('Kemeja A M: kurang 120 pcs sekarang (di analisis 150 pcs, sudah bertambah 30 pcs) · ambang pengingat 50 pcs')
    expect(text('Kekurangan produksi: Kemeja A M')).toContain(analysisLine)
    expect(text('Kekurangan produksi: Kemeja A M')).toContain('WA: belum pasti')
    expect(text('Kain perlu dibeli: Drill Navy untuk Celana B')).toContain('Drill Navy untuk Celana B: perlu 35,5 m · ambang pengingat 10 m')
    expect(text('Kain perlu dibeli: Drill Navy untuk Celana B')).toContain(analysisLine)
    expect(text('Kain perlu dibeli: Drill Navy untuk Celana B')).toContain('WA: jenis dimatikan')
    expect(panel('Piutang pelanggan jatuh tempo').textContent).toContain(`Sumber belum bisa dibaca (dicoba ${wib('2026-10-19T02:59:00+00:00')}): 42501 CP7_ALERT_AR_SOURCE_DENIED.`)
    expect(panel('Stok kain di bawah minimum').textContent).toContain(`Sumber terakhir dibaca ${wib('2026-10-19T02:59:00+00:00')}.`)
    const status = panel('Status analisis').textContent
    expect(status).toContain(`Analisis terbaru: data per ${wib('2026-10-19T01:00:00+00:00')}, selesai dicek ulang ${wib('2026-10-19T02:31:00+00:00')}. 2 masih terbuka, 6 sudah beres, 1 tidak diteruskan`)
    expect(status).toContain(`Analisis otomatis terakhir dilewati ${wib('2026-10-19T02:45:00+00:00')}: data ERP tidak berubah sejak analisis sebelumnya.`)
    expect(status).toContain('belum waktunya analisis baru')
    expect(container.textContent).toContain(`Pengumpul pengingat terakhir jalan ${wib('2026-10-19T02:59:00+00:00')}: sumber sudah dibaca.`)
    expect(container.textContent).not.toContain('Rayon Merah')
    await click('Tampilkan pengingat sistem yang sudah beres 7 hari terakhir')
    expect(text('Stok kain di bawah minimum: Rayon Merah')).toContain(`Beres ${wib('2026-10-18T05:00:00+00:00')} · Stok sudah mencapai minimum`)
    expect(text('Stok kain di bawah minimum: Rayon Merah')).toContain('WA: beres sebelum dikirim')
    expect(text('Kekurangan produksi: Kaos C S')).toContain('Dicek ulang: sudah tidak terbuka')
    expect(text('Kekurangan produksi: Kaos C S')).toContain('(muncul lagi, ke-2)')
    expect(text('Kekurangan produksi: Kaos C S')).toContain('WA: terkirim (ulangan ke-1)')
    expect(text('Piutang jatuh tempo: S-0009')).toContain('Sudah beres menurut data terbaru')
    expect(container.textContent).not.toContain('Katun Combed')

    // Staff reading receivables only: no WhatsApp state, no analysis, only its own kind.
    await act(async () => root.unmount()); root = createRoot(container); client.rpc.mockReset(); server(); auth.current = staff
    await mount(); await tab('Pengingat sistem')
    expect([...panel('Pengingat sistem').querySelectorAll('.csys-group')].map(g => g.getAttribute('aria-label'))).toEqual(['Piutang pelanggan jatuh tempo'])
    expect(panel('Pengingat sistem').textContent).not.toContain('WA:')
    expect(container.querySelector('[aria-label="Status analisis"]')).toBeNull()
    expect(text('Piutang jatuh tempo: S-0012')).toContain('Rp1.250.000')
  })

  it('explains that system reminders start after the owner saves the WhatsApp settings once', async () => {
    server({ configured: false }); await mount(); await tab('Pengingat sistem')
    expect(container.textContent).toContain('Pengingat sistem mulai dikumpulkan sesudah Owner menyimpan pengaturan di tab Sambungan WhatsApp satu kali. WhatsApp boleh tetap mati')
    expect(container.textContent).toContain('Pengumpul pengingat belum pernah jalan.')
    await click('Buka tab Sambungan WhatsApp')
    expect(field<HTMLElement>('#creminders-panel-WA').hidden).toBe(false)
    expect(container.textContent).toContain('Pengaturan belum pernah disimpan. Simpan sekali supaya Pengingat sistem mulai berjalan')
    // Saving the defaults once is allowed (WhatsApp stays off).
    expect(button('Simpan pengaturan').disabled).toBe(false)
  })

  it('sends the key once, in its own request only, then empties the input; the key is never shown or stored', async () => {
    const KEY = 'FAKEKEY-a1B2_c3', fake = server({ wa: { settings: { ...defaults, revision: 1, phone_e164: PHONE, saved_at: NOW } } })
    await mount(); await tab('Sambungan WhatsApp')
    expect(panel('Status sambungan').textContent).toContain('Belum ada kunci')
    expect(input('Kunci CallMeBot').type).toBe('password')
    await type('Kunci CallMeBot', 'ab cd')
    expect(container.textContent).toContain('Kunci berisi 4 sampai 64 huruf'); expect(button('Simpan kunci').disabled).toBe(true)
    await type('Kunci CallMeBot', KEY)
    expect(button('Simpan kunci').disabled).toBe(false)
    expect(container.innerHTML).not.toContain(KEY)
    await click('Simpan kunci')
    const keyCalls = calls(fake, 'erp_cp7_set_wa_key_v1')
    expect(keyCalls).toHaveLength(1)
    expect(Object.keys(keyCalls[0]).sort()).toEqual(['p_key', 'p_request'])
    expect(keyCalls[0].p_key).toBe(KEY); expect(String(keyCalls[0].p_request)).toMatch(/^[0-9a-f-]{36}$/)
    expect(input('Kunci CallMeBot').value).toBe('')
    expect(container.textContent).toContain(`Kunci tersimpan (${wib(LATER)}).`)
    expect(panel('Status sambungan').textContent).toContain(`Kunci tersimpan sejak ${wib(LATER)}`)
    // A second key is another request with a fresh id.
    await type('Kunci CallMeBot', 'FAKEKEY-second'); await click('Simpan kunci')
    const again = calls(fake, 'erp_cp7_set_wa_key_v1')
    expect(again).toHaveLength(2); expect(again[1].p_request).not.toBe(again[0].p_request)
    // Do something else on the screen so other requests exist, then look for the key everywhere.
    await check('Nyalakan WhatsApp'); await click('Simpan pengaturan'); await click('Kirim pesan uji')
    for (const secret of [KEY, 'FAKEKEY-second']) {
      expect(container.textContent).not.toContain(secret); expect(container.innerHTML).not.toContain(secret)
      expect(JSON.stringify({ ...localStorage })).not.toContain(secret); expect(JSON.stringify({ ...sessionStorage })).not.toContain(secret)
      expect(fake.calls.filter(c => c[0] !== 'erp_cp7_set_wa_key_v1').map(c => JSON.stringify(c))).not.toContainEqual(expect.stringContaining(secret))
    }
    expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0)
    expect(fake.calls.filter(c => 'p_key' in c[1]).every(c => c[0] === 'erp_cp7_set_wa_key_v1')).toBe(true)
  })

  it('a refused or lost key reply shows codes only and still empties the input', async () => {
    const fake = server({ wa: { lose: new Set(['erp_cp7_set_wa_key_v1']) } })
    await mount(); await tab('Sambungan WhatsApp')
    await type('Kunci CallMeBot', 'FAKEKEY-lost'); await click('Simpan kunci')
    expect(input('Kunci CallMeBot').value).toBe('')
    expect(container.textContent).toContain('Jawaban server tidak sampai, jadi belum pasti kunci tersimpan.')
    expect(container.textContent).not.toContain('FAKEKEY-lost'); expect(container.textContent).not.toContain('Failed to fetch')
    expect(calls(fake, 'erp_cp7_set_wa_key_v1')).toHaveLength(1)
  })

  it('checks the settings like the server, shows the digest/quiet refusal in words and asks to reload when stale', async () => {
    const fake = server({ wa: { settings: { ...defaults, revision: 1, saved_at: NOW } } })
    await mount(); await tab('Sambungan WhatsApp')
    expect(button('Simpan pengaturan').disabled).toBe(true); expect(container.textContent).toContain('Belum ada yang diubah.')
    await type('Nomor WA Bos', '0812-000')
    expect(container.textContent).toContain('Nomor WA ditulis dengan kode negara, tanpa spasi atau tanda hubung: 0812… ditulis +62812….')
    expect(button('Simpan pengaturan').disabled).toBe(true)
    await type('Nomor WA Bos', PHONE)
    await check('Nyalakan WhatsApp')
    expect(container.textContent).toContain('Simpan kunci CallMeBot dulu sebelum menyalakan WhatsApp.'); expect(button('Simpan pengaturan').disabled).toBe(true)
    await check('Nyalakan WhatsApp')
    await type('Ulangi pesan tiap (menit)', '30')
    expect(container.textContent).toContain('Ulangan pesan: isi 0 (tidak diulang) atau 60 sampai 10.080 menit.')
    await type('Ulangi pesan tiap (menit)', '0')
    await type('Jam analisis selesai', '06:00')
    expect(container.textContent).toContain('Jam analisis: jam mulai harus lebih awal dari jam selesai')
    await type('Jam analisis selesai', '20:00')
    await type('Jam ringkasan 2', '22:00')
    expect(button('Simpan pengaturan').disabled).toBe(false)
    await click('Simpan pengaturan')
    expect(container.textContent).toContain('Jam ringkasan jatuh di jam tenang, jadi ringkasan itu tidak akan pernah terkirim. Geser jam ringkasan ke luar jam tenang')
    expect(container.textContent).not.toContain('CP7_WA_DIGEST_IN_QUIET_HOURS')
    await click('Kosongkan jam ringkasan 2')
    // Meanwhile another device saves revision 2.
    fake.settings = { ...fake.settings, revision: 2, max_items: 5, saved_at: LATER }
    await click('Simpan pengaturan')
    expect(container.textContent).toContain('Pengaturan ini baru saja diubah di tab atau perangkat lain. Tekan "Muat ulang sambungan", periksa isinya, lalu simpan lagi.')
    const saves = calls(fake, 'erp_cp7_save_wa_settings_v1')
    expect(saves).toHaveLength(2)
    expect((saves[1].p as Record<string, unknown>)).toMatchObject({ expected_revision: 1, phone_e164: PHONE, digest_times: ['08:00'], repeat_minutes: 0, enabled: false })
    expect(saves[1].p_request).not.toBe(saves[0].p_request)
    await click('Muat ulang sambungan sekarang')
    expect(input('Baris per jenis dalam satu pesan').value).toBe('5'); expect(input('Nomor WA Bos').value).toBe('')
    await type('Nomor WA Bos', PHONE); await click('Simpan pengaturan')
    expect((calls(fake, 'erp_cp7_save_wa_settings_v1')[2].p as Record<string, unknown>)).toMatchObject({ expected_revision: 2, max_items: 5, phone_e164: PHONE })
    expect(container.textContent).toContain('Tersimpan (revisi 3).')
    expect(panel('Status sambungan').textContent).toContain(`Revisi 3, disimpan ${wib(LATER)}`)
    expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0)
  })

  it('resends a settings save whose reply was lost with the same request id, and the server answers it once', async () => {
    const fake = server({ wa: { lose: new Set(['erp_cp7_save_wa_settings_v1']) } })
    await mount(); await tab('Sambungan WhatsApp')
    await type('Nomor WA Bos', PHONE); await click('Simpan pengaturan')
    expect(container.textContent).toContain('Jawaban server tidak sampai, jadi belum pasti pengaturan tersimpan.')
    await click('Simpan pengaturan')
    const saves = calls(fake, 'erp_cp7_save_wa_settings_v1')
    expect(saves).toHaveLength(2); expect(saves[1]).toEqual(saves[0])
    expect(fake.settings.revision).toBe(1)
    expect(container.textContent).toContain('Tersimpan (revisi 1). Permintaan ini ternyata sudah tersimpan sebelumnya.')
  })

  it('sends a test message, keeps the id of a lost reply, and says plainly when the hourly limit is reached', async () => {
    const fake = server({ wa: { settings: { ...defaults, revision: 1, phone_e164: PHONE, saved_at: NOW }, keyPresent: true, keySetAt: NOW, tests: 1,
      lose: new Set(['erp_cp7_send_wa_test_v1']) } })
    await mount(); await tab('Sambungan WhatsApp')
    await click('Kirim pesan uji')
    expect(container.textContent).toContain('Jawaban server tidak sampai, jadi belum pasti pesan uji terkirim.')
    await click('Kirim pesan uji')
    const sent = calls(fake, 'erp_cp7_send_wa_test_v1')
    expect(sent).toHaveLength(2); expect(sent[1]).toEqual(sent[0]); expect(Object.keys(sent[0])).toEqual(['p_request'])
    expect(fake.dispatches).toHaveLength(1)
    expect(container.textContent).toContain('Pesan uji masuk antrean kirim (pesan nomor 1).')
    expect(panel('Pesan 1').textContent).toContain('Pesan uji · nomor 1'); expect(panel('Pesan 1').textContent).toContain('Sedang dikirim')
    await click('Kirim pesan uji')
    expect(calls(fake, 'erp_cp7_send_wa_test_v1')[2].p_request).not.toBe(sent[0].p_request)
    await click('Kirim pesan uji')
    expect(container.textContent).toContain('Pesan uji paling banyak 3 kali dalam satu jam. Tunggu sebentar lalu coba lagi.')
    expect(container.textContent).not.toContain('CP7_WA_TEST_LIMIT')
  })

  it('shows the status and history in plain words and marks an UNKNOWN message delivered or not', async () => {
    const fake = server({ wa: { settings: { ...defaults, revision: 4, enabled: true, phone_e164: PHONE, saved_at: NOW }, keyPresent: true, keySetAt: NOW, transport: false,
      quietNow: true, dispatches: [
        dispatch(9, {}),
        dispatch(10, { status: 'PROVIDER_REFUSED', http_status: 500, provider_text: 'Error: limit' }),
        dispatch(11, { kind: 'DIGEST', digest_slot: '2026-10-19T01:00:00+00:00', status: 'NOTHING_DUE', body: null, http_status: null, provider_text: null, items: 0 }),
        dispatch(12, { status: 'UNKNOWN', http_status: null, provider_text: null, body: `⚠ ERP Enteng · 19 Okt 09.50\n${'Baris panjang sekali '.repeat(30)}` }),
        dispatch(13, { status: 'TRANSPORT_FAILED', http_status: null, provider_text: 'Could not resolve host' }),
      ] } })
    await mount(); await tab('Sambungan WhatsApp')
    const status = panel('Status sambungan').textContent
    for (const words of ['Menyala', PHONE, `Kunci tersimpan sejak ${wib(NOW)}`, 'Ringkas', 'sekarang jam tenang', 'Pengumpul pengingat: terakhir jalan', 'sumber sudah dibaca',
      'Pengirim WhatsApp: terakhir jalan', 'WhatsApp mati, tidak ada yang dikirim', 'Pemeriksa analisis: belum pernah jalan',
      'Antrean pesan: 2 menunggu dikirim · 4 terkirim.']) expect(status).toContain(words)
    expect(container.textContent).toContain('Alamat uji (bukan CallMeBot)')
    expect([...container.querySelectorAll('.cwa-history > li')].map(li => li.getAttribute('aria-label'))).toEqual(['Pesan 13', 'Pesan 12', 'Pesan 11', 'Pesan 10', 'Pesan 9'])
    expect(panel('Pesan 9').textContent).toContain('Diterima CallMeBot'); expect(panel('Pesan 9').textContent).toContain('Jawaban CallMeBot: Message queued')
    expect(panel('Pesan 9').textContent).toContain('2 pengingat')
    expect(panel('Pesan 10').textContent).toContain('Ditolak CallMeBot (HTTP 500)')
    expect(panel('Pesan 11').textContent).toContain('Ringkasan kosong, tidak dikirim')
    expect(panel('Pesan 13').textContent).toContain('Gagal tersambung')
    expect(panel('Pesan 12').textContent).toContain('Belum pasti')
    expect(field<HTMLElement>('pre[aria-label="Isi pesan 12"]').textContent).toContain('Baris panjang sekali')
    expect(container.querySelector('[aria-label="Tandai pesan 9 masuk"]')).toBeNull()
    await click('Tandai pesan 12 tidak masuk')
    expect(calls(fake, 'erp_cp7_resolve_wa_dispatch_v1')).toEqual([{ p: { dispatch_id: 12, outcome: 'NOT_DELIVERED' }, p_request: expect.stringMatching(/^[0-9a-f-]{36}$/) }])
    expect(container.textContent).toContain('Pesan nomor 12 ditandai tidak masuk; pengingat di dalamnya akan dikirim lagi.')
    expect(container.querySelector('[aria-label="Tandai pesan 12 masuk"]')).toBeNull()
    expect(panel('Pesan 12').textContent).toContain(`Bos menandai pesan ini tidak masuk (isinya dikirim lagi) ${wib(LATER)}.`)
  })

  it('marks an UNKNOWN message delivered with its own payload; a second mark is refused in words', async () => {
    const fake = server({ wa: { dispatches: [dispatch(5, { status: 'UNKNOWN', http_status: null, provider_text: null }), dispatch(6, { status: 'UNKNOWN', http_status: null, provider_text: null })] } })
    await mount(); await tab('Sambungan WhatsApp')
    await click('Tandai pesan 6 masuk')
    expect(calls(fake, 'erp_cp7_resolve_wa_dispatch_v1')[0].p).toEqual({ dispatch_id: 6, outcome: 'DELIVERED' })
    expect(container.textContent).toContain('Pesan nomor 6 ditandai masuk.')
    fake.dispatches[0].resolved_outcome = 'DELIVERED'; fake.dispatches[0].resolved_at = LATER
    await click('Tandai pesan 5 tidak masuk')
    expect(container.textContent).toContain('Pesan ini sudah tidak berstatus "belum pasti"')
  })

  it('shows a finished good at or under its reorder point with its WhatsApp line, and forwards the kind by default (SS-1)', async () => {
    const good = alertsReply('OWNER'), parsed = parseSystemAlerts(good, { owner: true })
    const fg = parsed.rows.find(r => r.kind === 'FG_AT_REORDER_POINT')!
    expect(fg.detail).toEqual({ kind: 'FG_AT_REORDER_POINT', rootId: id(209), sizeId: id(309), sku: 'KML-M', productName: 'Kemeja Linen', sizeCode: 'M', freePcs: '23',
      wipPcs: '0', wipStatus: 'COMPLETE', positionPcs: '23', reorderPointPcs: '36', basis: 'FORMULA', dailyMean: '3.90', leadDays: '7', leadBasis: 'PROFILE',
      bufferMode: 'STATISTICAL', safetyPcs: '8.3', serviceLevel: '0.95' })
    // The same line item_line (alerts.sql) writes into the WhatsApp message, numbers as cp7_alert_native.num writes them.
    expect(alertSummary(fg)).toBe('Kemeja Linen M: sisa 23 pcs, sedang diproduksi 0 pcs, titik pesan ulang 36 pcs')
    const variant = (detail: Record<string, unknown>) => ({ ...fg, detail: { ...fg.detail, ...detail } }) as SystemAlert
    expect(alertSummary(variant({ wipStatus: 'UNKNOWN', wipPcs: null, positionPcs: null, sizeCode: null, freePcs: '1234.505', reorderPointPcs: '1500' })))
      .toBe('Kemeja Linen: sisa 1234,51 pcs, sedang diproduksi belum diketahui, titik pesan ulang 1500 pcs')
    expect(alertSummary(variant({ productName: 'K'.repeat(130) }))).toBe('K'.repeat(120))
    expect(['23', '4.065', '0.5', '-0.001', '-2.345', '12.30', '1234.5', '0.004', null].map(alertNumber)).toEqual(['23', '4,07', '0,5', '0', '-2,35', '12,3', '1234,5', '0', '?'])
    const withFg = (detail: Record<string, unknown>, extra: Record<string, unknown> = {}) => ({ ...good, rows: good.rows.map(r => r.kind === 'FG_AT_REORDER_POINT'
      ? { ...r, detail: { ...(r.detail as object), ...detail }, ...extra } : r) })
    expect(() => parseSystemAlerts(withFg({ extra: 1 }), { owner: true })).toThrow('Respons pengingat sistem tidak cocok (rincian barang jadi)')
    const missing = withFg({}); delete (missing.rows[8].detail as Record<string, unknown>).service_level
    expect(() => parseSystemAlerts(missing, { owner: true })).toThrow('(rincian barang jadi)')
    expect(() => parseSystemAlerts(withFg({ wip_pcs: null }), { owner: true })).toThrow('(rincian barang jadi)')
    expect(() => parseSystemAlerts(withFg({ free_pcs: 23 }), { owner: true })).toThrow('(rincian barang jadi)')
    expect(() => parseSystemAlerts(withFg({ basis: 'MANUAL' }), { owner: true })).toThrow('(rincian barang jadi)')
    expect(() => parseSystemAlerts(withFg({ basis: 'NO_SALES' }), { owner: true })).toThrow('(rincian barang jadi)')
    expect(parseSystemAlerts(withFg({ basis: 'MANUAL', buffer_mode: null, safety_pcs: null, service_level: null }), { owner: true }).rows[8].detail.kind).toBe('FG_AT_REORDER_POINT')
    expect(() => parseSystemAlerts(withFg({}, { subject_key: 'FG_AT_REORDER_POINT:9' }), { owner: true })).toThrow('(pengingat)')
    expect(() => parseSystemAlerts(withFg({}, { party_names: ['Toko'] }), { owner: true })).toThrow('(nama pihak)')
    expect(resolutionLabel('ABOVE_REORDER_POINT')).toBe('Stok sudah di atas titik pesan ulang')
    expect(resolutionLabel('NO_REORDER_POINT')).toBe('Titik pesan ulangnya tidak ada lagi')

    // Pengingat sistem: its own group after fabric, the line, the source of the number, and the WhatsApp state.
    const fake = server(), rpc = client.rpc.getMockImplementation()!
    const back = row(10, 'FG_AT_REORDER_POINT', 'Stok barang jadi menipis: Kemeja Linen L', fgDetail(10, { size_code: 'L' }), { subject_key: fgSubject(10),
      ...resolved('ABOVE_REORDER_POINT'), wa: waState('RESOLVED_BEFORE_SEND', { reason: 'ABOVE_REORDER_POINT', settled_at: '2026-10-18T05:00:00+00:00' }) })
    client.rpc.mockImplementation(async (name: string, args?: Record<string, unknown>) => name === 'erp_cp7_get_alerts_v1'
      ? { data: { ...good, rows: [...good.rows, back] }, error: null } : rpc(name, args))
    await mount(); await tab('Pengingat sistem')
    const item = field<HTMLElement>('[aria-label="Pengingat sistem Stok barang jadi menipis: Kemeja Linen M"]').textContent ?? ''
    expect(item).toContain('Kemeja Linen M: sisa 23 pcs, sedang diproduksi 0 pcs, titik pesan ulang 36 pcs')
    expect(item).toContain('SKU KML-M · titik pesan ulang dari rumus · rinciannya di Gudang › Ringkasan Barang Jadi')
    expect(item).toContain('WA: terkirim')
    expect(panel('Stok barang jadi menipis').textContent).toContain(`Sumber terakhir dibaca ${wib('2026-10-19T02:59:00+00:00')}.`)
    expect(panel('Pengingat sistem').textContent).toContain('Stok kain di bawah minimum, stok aksesori dan barang jadi yang menipis')
    expect(panel('Pengingat sistem').textContent).not.toContain('Stok kain menipis')
    await click('Tampilkan pengingat sistem yang sudah beres 7 hari terakhir')
    const gone = field<HTMLElement>('[aria-label="Pengingat sistem Stok barang jadi menipis: Kemeja Linen L"]').textContent ?? ''
    expect(gone).toContain(`Beres ${wib('2026-10-18T05:00:00+00:00')} · Stok sudah di atas titik pesan ulang`)
    expect(gone).toContain('WA: beres sebelum dikirim')

    // Sambungan WhatsApp: the kind is one of the choices, on by default, and saved with the others.
    await tab('Sambungan WhatsApp')
    expect([...container.querySelectorAll('.cwa-kinds input')].map(i => i.getAttribute('aria-label'))).toEqual(['Teruskan Pengingat pribadi Bos',
      'Teruskan Stok kain di bawah minimum', 'Teruskan Stok aksesori menipis', 'Teruskan Stok barang jadi menipis',
      'Teruskan Piutang pelanggan jatuh tempo', 'Teruskan Tagihan supplier jatuh tempo',
      'Teruskan Kekurangan produksi (dari analisis)', 'Teruskan Kain perlu dibeli (dari analisis)',
      'Teruskan Kebutuhan aksesori perlu diperiksa (dari analisis)',
      'Teruskan Piutang saldo awal', 'Teruskan Utang saldo awal', 'Teruskan Tagihan gaji', 'Teruskan Kredit retur aksesori mandor',
      'Teruskan Tagihan laundry', 'Teruskan Penerimaan laundry perlu diperiksa', 'Teruskan Laundry awal belum ditagih'])
    expect(input('Teruskan Stok barang jadi menipis').checked).toBe(true)
    expect(input('Analisis otomatis tiap (menit)').value).toBe('240')
    await click('Simpan pengaturan')
    expect((calls(fake, 'erp_cp7_save_wa_settings_v1')[0].p as { kinds: string[]; analysis_every_minutes: number })).toMatchObject({
      kinds: ['MANUAL_REMINDER', 'FABRIC_BELOW_MINIMUM', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
        'PRODUCTION_GAP', 'FABRIC_NEED', 'ACCESSORY_NEED', 'OPENING_AR', 'OPENING_AP', 'PAYROLL_AP', 'ACCESSORY_AP', 'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED'], analysis_every_minutes: 240 })
    expect(container.textContent).toContain('Tersimpan (revisi 1).')
    await check('Teruskan Stok barang jadi menipis'); await click('Simpan pengaturan')
    expect((calls(fake, 'erp_cp7_save_wa_settings_v1')[1].p as { kinds: string[] }).kinds).not.toContain('FG_AT_REORDER_POINT')
    expect(fake.settings.kinds).not.toContain('FG_AT_REORDER_POINT')
    expect(input('Teruskan Stok barang jadi menipis').checked).toBe(false)
  })

  it('shows a fabric on the formula under "Stok kain di bawah minimum" and an accessory under its manual minimum, with their WhatsApp lines (D17-10)', async () => {
    const good = alertsReply('OWNER'), parsed = parseSystemAlerts(good, { owner: true })
    const fab = parsed.rows.find(r => r.subjectKey === id(412))!, acc = parsed.rows.find(r => r.kind === 'ACCESSORY_AT_REORDER_POINT')!
    const minimum = parsed.rows.find(r => r.title === 'Stok kain di bawah minimum: Katun Combed 30s Hitam')!
    expect(fab.detail).toEqual({ kind: 'FABRIC_BELOW_MINIMUM', materialId: id(412), materialType: 'FABRIC', sku: 'KC-HTM-2', name: 'Katun Hitam', unitCode: 'YD',
      freeQty: '56', onOrderQty: '20', reorderPointQty: '98.51', basis: 'FORMULA', dailyMean: '7.47', leadDays: '6', safetyQty: '17.08', serviceLevel: '0.95' })
    expect(acc.detail).toEqual({ kind: 'ACCESSORY_AT_REORDER_POINT', materialId: id(413), materialType: 'ACCESSORY', sku: 'KCG-12', name: 'Kancing 12 mm',
      unitCode: 'PCS', freeQty: '180', onOrderQty: '0', reorderPointQty: '250', basis: 'MANUAL', dailyMean: '3.33', leadDays: null, safetyQty: null, serviceLevel: null })
    expect([isMaterialReorderDetail(fab.detail), isMaterialReorderDetail(acc.detail), isMaterialReorderDetail(minimum.detail)]).toEqual([true, true, false])
    // The same lines item_line (alerts.sql) writes into the WhatsApp message: the unit after every number.
    expect(alertSummary(fab)).toBe('Katun Hitam: sisa 56 YD, dipesan 20 YD, minimum rumus 98,51 YD')
    expect(alertSummary(acc)).toBe('Kancing 12 mm: sisa 180 PCS, minimum 250 PCS')
    expect(alertSummary(minimum)).toBe('Sisa 42,5 kg, minimum 60 kg · SKU KC30-HTM')
    const variant = (a: SystemAlert, detail: Record<string, unknown>) => ({ ...a, detail: { ...a.detail, ...detail } }) as SystemAlert
    expect(alertSummary(variant(acc, { unitCode: null, freeQty: '0.125', reorderPointQty: '12.3456' }))).toBe('Kancing 12 mm: sisa 0,13 , minimum 12,35 ')
    expect(alertSummary(variant(fab, { name: 'K'.repeat(130) }))).toBe('K'.repeat(120))
    const withRow = (subject: string, detail: Record<string, unknown>, extra: Record<string, unknown> = {}) => ({ ...good, rows: good.rows.map(r => r.subject_key === subject
      ? { ...r, detail: { ...(r.detail as object), ...detail }, ...extra } : r) })
    const F = id(412), A = id(413), M = 'FABRIC_BELOW_MINIMUM:1'
    // The fabric on the formula: exactly the material shape, FABRIC and FORMULA with its lama kirim, cadangan and tingkat layanan.
    expect(() => parseSystemAlerts(withRow(F, { extra: 1 }), { owner: true })).toThrow('Respons pengingat sistem tidak cocok (rincian bahan)')
    const missing = withRow(F, {}); delete (missing.rows[9].detail as Record<string, unknown>).on_order_qty
    expect(() => parseSystemAlerts(missing, { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { material_type: 'ACCESSORY' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { basis: 'MANUAL', safety_qty: null, service_level: null }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { basis: 'MANUAL' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { free_qty: 56 }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { safety_qty: null }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { lead_days: null }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, { qty: '56' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(F, {}, { subject_key: id(999) }), { owner: true })).toThrow('(pengingat)')
    expect(() => parseSystemAlerts(withRow(F, {}, { party_names: ['Supplier'] }), { owner: true })).toThrow('(nama pihak)')
    // The fabric minimum's shape stays as it was: one of the material keys makes it the material shape, which then fails.
    expect(() => parseSystemAlerts(withRow(M, { basis: 'MANUAL' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(M, { material_type: 'FABRIC' }), { owner: true })).toThrow('(rincian bahan)')
    // The accessory: MANUAL (typed) or ESTIMATE (from the owner's numbers, with its lama kirim, D17-12); never the formula, no
    // cadangan or tingkat layanan, nothing on order.
    expect(() => parseSystemAlerts(withRow(A, { on_order_qty: '5' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(A, { service_level: '0.95' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(A, { basis: 'FORMULA', safety_qty: '4.2', service_level: '0.99' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(A, { basis: 'FORMULA', lead_days: '5', safety_qty: '4.2', service_level: '0.99' }), { owner: true })).toThrow('(rincian bahan)')
    expect(parseSystemAlerts(withRow(A, { lead_days: '5' }), { owner: true }).rows[10].detail).toMatchObject({ basis: 'MANUAL', leadDays: '5' })
    expect(parseSystemAlerts(withRow(A, { basis: 'ESTIMATE', lead_days: '20', reorder_point_qty: '250' }), { owner: true }).rows[10].detail)
      .toMatchObject({ basis: 'ESTIMATE', leadDays: '20', reorderPointQty: '250' })
    expect(() => parseSystemAlerts(withRow(A, { basis: 'ESTIMATE', lead_days: null }), { owner: true })).toThrow('(rincian bahan)')
    for (const basis of ['NOT_SET', 'NO_USAGE', 'NOT_ENOUGH_DATA'])
      expect(() => parseSystemAlerts(withRow(A, { basis }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(A, { safety_qty: '4.2' }), { owner: true })).toThrow('(rincian bahan)')
    expect(() => parseSystemAlerts(withRow(A, { material_type: 'FABRIC' }), { owner: true })).toThrow('(rincian bahan)')
    expect(parseSystemAlerts(withRow(A, { daily_mean: null }), { owner: true }).rows[10].detail.kind).toBe('ACCESSORY_AT_REORDER_POINT')
    expect(() => parseSystemAlerts(withRow(A, {}, { subject_key: id(999) }), { owner: true })).toThrow('(pengingat)')
    // The kind FABRIC_AT_REORDER_POINT no longer exists: as a row or as a source it is refused.
    expect(() => parseSystemAlerts(withRow(F, {}, { kind: 'FABRIC_AT_REORDER_POINT', title: 'Stok kain menipis: Katun Hitam' }), { owner: true })).toThrow('(jenis pengingat)')
    expect(() => parseSystemAlerts({ ...good, kinds: [...good.kinds, { ...good.kinds[0], kind: 'FABRIC_AT_REORDER_POINT' }] }, { owner: true })).toThrow('(jenis)')
    expect(resolutionLabel('MANUAL_MINIMUM_IN_FORCE')).toBe('Kain ini sekarang memakai angka minimum (Master Data › Kain & Benchmark)')
    expect([resolutionLabel('ABOVE_REORDER_POINT', 'FABRIC_BELOW_MINIMUM'), resolutionLabel('NO_REORDER_POINT', 'FABRIC_BELOW_MINIMUM'),
      resolutionLabel('ABOVE_REORDER_POINT', 'ACCESSORY_AT_REORDER_POINT'), resolutionLabel('NO_REORDER_POINT', 'ACCESSORY_AT_REORDER_POINT'),
      resolutionLabel('ABOVE_REORDER_POINT', 'FG_AT_REORDER_POINT'), resolutionLabel('AT_OR_ABOVE_MINIMUM', 'FABRIC_BELOW_MINIMUM')]).toEqual([
      'Stok sudah di atas minimum rumus', 'Minimum rumusnya tidak ada lagi', 'Stok sudah di atas batas minimum', 'Batas minimumnya dikosongkan atau diisi 0',
      'Stok sudah di atas titik pesan ulang', 'Stok sudah mencapai minimum'])

    // Pengingat sistem: the fabric on the formula in the one fabric group, next to the fabric with a minimum.
    const fake = server(), rpc = client.rpc.getMockImplementation()!
    const back = row(14, 'ACCESSORY_AT_REORDER_POINT', 'Stok aksesori menipis: Sleting 20 cm', accessoryReorder(14, { name: 'Sleting 20 cm', sku: 'SLT-20',
      basis: 'ESTIMATE', lead_days: '20' }),
      { subject_key: id(414), ...resolved('ABOVE_REORDER_POINT'), wa: waState('RESOLVED_BEFORE_SEND', { reason: 'ABOVE_REORDER_POINT', settled_at: '2026-10-18T05:00:00+00:00' }) })
    client.rpc.mockImplementation(async (name: string, args?: Record<string, unknown>) => name === 'erp_cp7_get_alerts_v1'
      ? { data: { ...good, rows: [...good.rows, back] }, error: null } : rpc(name, args))
    await mount(); await tab('Pengingat sistem')
    const fabricGroup = panel('Stok kain di bawah minimum')
    expect([...fabricGroup.querySelectorAll('li.csys-row')].map(li => li.getAttribute('aria-label'))).toEqual([
      'Pengingat sistem Stok kain di bawah minimum: Katun Combed 30s Hitam', 'Pengingat sistem Stok kain di bawah minimum: Katun Hitam'])
    expect(fabricGroup.querySelector('header')?.textContent).toContain('2 terbuka')
    const fabric = field<HTMLElement>('[aria-label="Pengingat sistem Stok kain di bawah minimum: Katun Hitam"]').textContent ?? ''
    expect(fabric).toContain('Katun Hitam: sisa 56 YD, dipesan 20 YD, minimum rumus 98,51 YD')
    expect(fabric).toContain('SKU KC-HTM-2 · minimum dari rumus, karena kain ini belum punya minimum di Kain & Benchmark · rinciannya di Gudang › Bahan & Roll')
    expect(fabric).toContain('WA: menunggu')
    const accessory = field<HTMLElement>('[aria-label="Pengingat sistem Stok aksesori menipis: Kancing 12 mm"]').textContent ?? ''
    expect(accessory).toContain('Kancing 12 mm: sisa 180 PCS, minimum 250 PCS')
    expect(accessory).toContain('SKU KCG-12 · batas minimum diketik manual · rinciannya di Gudang › Aksesori')
    expect(accessory).toContain('WA: jam tenang')
    expect(panel('Stok aksesori menipis').textContent).toContain(`Sumber terakhir dibaca ${wib('2026-10-19T02:59:00+00:00')}.`)
    expect(panel('Pengingat sistem').textContent).not.toContain('Stok kain menipis')
    for (const group of ['Stok kain di bawah minimum', 'Stok aksesori menipis']) for (const word of ['titik pesan ulang', 'angka manual'])
      expect(panel(group).textContent).not.toContain(word)
    await click('Tampilkan pengingat sistem yang sudah beres 7 hari terakhir')
    expect(field<HTMLElement>('[aria-label="Pengingat sistem Stok aksesori menipis: Sleting 20 cm"]').textContent)
      .toContain(`Beres ${wib('2026-10-18T05:00:00+00:00')} · Stok sudah di atas batas minimum`)
    expect(field<HTMLElement>('[aria-label="Pengingat sistem Stok aksesori menipis: Sleting 20 cm"]').textContent)
      .toContain('SKU SLT-20 · batas minimum dari isian hitungan · rinciannya di Gudang › Aksesori')
    await tab('Sambungan WhatsApp')
    expect(container.querySelector('input[aria-label="Teruskan Stok kain menipis"]')).toBeNull()
    expect(input('Teruskan Stok kain di bawah minimum').checked).toBe(true); expect(input('Teruskan Stok aksesori menipis').checked).toBe(true)
    await click('Simpan pengaturan')
    expect((calls(fake, 'erp_cp7_save_wa_settings_v1')[0].p as { kinds: string[] }).kinds).not.toContain('FABRIC_AT_REORDER_POINT')
  })


  it('OW01_UI_01_SETTINGS_ROUNDTRIP saves the accessory review kind, retries a lost choice exactly and restores it with a fresh UUID', async () => {
    const fake = server(), label = `Teruskan ${ACCESSORY_KIND_LABEL}`
    await mount(); await tab('Sambungan WhatsApp')
    expect(input(label).checked).toBe(true)
    await click('Simpan pengaturan')
    const first = calls(fake, 'erp_cp7_save_wa_settings_v1')[0]
    expect(Object.keys(first).sort()).toEqual(['p', 'p_request'])
    expect(first.p_request).toMatch(/^[0-9a-f-]{36}$/)
    expect(first.p).toMatchObject({ expected_revision: 0, kinds: defaults.kinds })
    expect(fake.settings.kinds).toContain('ACCESSORY_NEED')
    expect(input(label).checked).toBe(true)

    fake.lose.add('erp_cp7_save_wa_settings_v1')
    await check(label); await click('Simpan pengaturan')
    const lost = calls(fake, 'erp_cp7_save_wa_settings_v1')[1]
    expect(lost.p_request).not.toBe(first.p_request)
    expect(lost.p).toMatchObject({ expected_revision: 1, kinds: defaults.kinds.filter(k => k !== 'ACCESSORY_NEED') })
    expect(container.textContent).toContain('Jawaban server tidak sampai, jadi belum pasti pengaturan tersimpan.')
    expect(fake.settings.revision).toBe(2)
    expect(fake.settings.kinds).not.toContain('ACCESSORY_NEED')
    await click('Simpan pengaturan')
    const retry = calls(fake, 'erp_cp7_save_wa_settings_v1')[2]
    expect(retry).toEqual(lost)
    expect(fake.settings.revision).toBe(2)
    expect(input(label).checked).toBe(false)
    expect(container.textContent).toContain('Tersimpan (revisi 2). Permintaan ini ternyata sudah tersimpan sebelumnya.')

    await check(label); await click('Simpan pengaturan')
    const saves = calls(fake, 'erp_cp7_save_wa_settings_v1'), restored = saves[3]
    expect(saves).toHaveLength(4)
    expect(restored.p_request).toMatch(/^[0-9a-f-]{36}$/)
    expect(restored.p_request).not.toBe(first.p_request)
    expect(restored.p_request).not.toBe(lost.p_request)
    expect(restored.p).toMatchObject({ expected_revision: 2, kinds: defaults.kinds })
    expect(fake.settings.revision).toBe(3)
    expect(fake.settings.kinds).toEqual([...defaults.kinds].sort())
    expect(input(label).checked).toBe(true)
    const analysisLegend = [...panel('Sambungan WhatsApp').querySelectorAll('legend')].find(l => l.textContent?.startsWith('Analisis otomatis'))
    expect(analysisLegend?.textContent).toContain('aksesori')
  })

  it('OW01_UI_02_GROSS_REVIEW renders unknown additional need and gross186 only as assumed BOM need', async () => {
    const before = structuredClone(alertsReply('OWNER')), reply = accessoryAlertsReply()
    expect(alertsReply('OWNER')).toEqual(before)
    expect(Object.keys(reply.rows.at(-1)!.detail)).toHaveLength(20)
    server({ alertsData: reply }); await mount(); await tab('Pengingat sistem')
    const text = accessoryRow().textContent ?? ''
    expect(text).toContain('Kemeja A M · Kancing: kebutuhan aksesori perlu diperiksa; jumlah tambahan belum diketahui')
    expect(text).toContain('kebutuhan BOM (perkiraan) 186 PCS')
    expect(text).toContain('Pemasangan dan sisa yang dialokasikan belum terbukti')
    expect(text).toContain(`Data analisis per ${wib('2026-10-19T01:00:00+00:00')}, dicek ulang ${wib('2026-10-19T02:30:00+00:00')}`)
    expect(text).toContain('WA: menunggu')
    expect(text).not.toMatch(/perlu dibeli|perlu beli|tambahan 186|tambahan 0|ambang pengingat/)
    expect(panel(ACCESSORY_KIND_LABEL).querySelector('header')?.textContent).toContain('1 terbuka')
    expect(panel('Status analisis').textContent).toContain('3 masih terbuka')
    expect(panel('Status analisis').textContent).toContain('aksesori')
  })

  it.each([
    { caseId: 'OW01_UI_03_BOM_NOT_RECORDED', extra: { category_key: 'UNKNOWN_BOM', category_name: null,
      gross_state: 'UNKNOWN', gross_qty: null, reason: 'BOM_NOT_RECORDED' }, message: 'BOM aksesori belum dicatat' },
    { caseId: 'OW01_UI_04_BOM_AMBIGUOUS', extra: { category_key: 'UNKNOWN_BOM', category_name: null,
      gross_state: 'UNKNOWN', gross_qty: null, reason: 'BOM_AMBIGUOUS' }, message: 'BOM aksesori tumpang tindih; perlu diperiksa' },
    { caseId: 'OW01_UI_05_CATEGORY_UNAVAILABLE', extra: { category_key: `ACCESSORY_CATEGORY:${id(603)}`, category_name: 'Kancing tidak aktif',
      gross_state: 'UNKNOWN', gross_qty: null, reason: 'CATEGORY_UNAVAILABLE' }, message: 'Kategori aksesori tidak tersedia' },
  ])('$caseId renders the source review reason without inventing zero or purchase quantity', async ({ extra, message }) => {
    server({ alertsData: accessoryAlertsReply(extra) }); await mount(); await tab('Pengingat sistem')
    const text = accessoryRow().textContent ?? ''
    expect(text).toContain('kebutuhan aksesori perlu diperiksa; jumlah tambahan belum diketahui')
    expect(text).toContain(message)
    expect(text).toContain('dicek ulang')
    expect(text).toContain('WA: menunggu')
    expect(text).not.toMatch(/kebutuhan BOM|186|0 PCS|perlu dibeli|perlu beli|tambahan 0|ambang pengingat/)
    expect(panel(ACCESSORY_KIND_LABEL).querySelector('header')?.textContent).toContain('1 terbuka')
  })

  it.each([
    { caseId: 'OW01_UI_06_HTTP_401_RETIRE', status: 401 },
    { caseId: 'OW01_UI_07_HTTP_403_RETIRE', status: 403 },
  ])('$caseId retires already displayed review facts while AuthProvider remains AUTHORIZED', async ({ status }) => {
    server({ alertsData: accessoryAlertsReply() }); const rpc = client.rpc.getMockImplementation()!
    let denied = false
    client.rpc.mockImplementation(async (name: string, args?: Record<string, unknown>) =>
      name === 'erp_cp7_get_alerts_v1' && denied ? accessRefusal(status) : rpc(name, args))
    await mount(); await tab('Pengingat sistem')
    expect(accessoryRow().textContent).toContain('kebutuhan BOM (perkiraan) 186 PCS')
    expect(accessoryRow().textContent).toContain('WA: menunggu')
    const identity = auth.current
    denied = true; await click('Muat ulang pengingat sistem')
    expect(auth.current).toBe(identity)
    expect((auth.current as typeof owner).identity.status).toBe('AUTHORIZED')
    expectAccessoryFactsRetired(status)
    expect(client.rpc.mock.calls.filter(([name]) => name === 'erp_cp7_get_alerts_v1')).toHaveLength(2)
    expect(client.rpc.mock.calls.some(([name]) => /erp_cp7_(save|set|send|resolve)_/.test(String(name)))).toBe(false)
  })

  it.each([
    { caseId: 'OW01_UI_08_LATE_401', status: 401 },
    { caseId: 'OW01_UI_09_LATE_403', status: 403 },
  ])('$caseId cannot restore an old identity response after the new identity read is refused', async ({ status }) => {
    const reply = accessoryAlertsReply()
    server({ alertsData: reply }); const rpc = client.rpc.getMockImplementation()!
    let reads = 0
    let finishOld: ((value: { data: ReturnType<typeof accessoryAlertsReply>; error: null }) => void) | null = null
    client.rpc.mockImplementation(async (name: string, args?: Record<string, unknown>) => {
      if (name !== 'erp_cp7_get_alerts_v1') return rpc(name, args)
      reads += 1
      if (reads === 1) return { data: structuredClone(reply), error: null }
      if (reads === 2) return new Promise(resolve => { finishOld = resolve })
      return accessRefusal(status)
    })
    await mount(); await tab('Pengingat sistem')
    expect(accessoryRow().textContent).toContain('186 PCS')
    await click('Muat ulang pengingat sistem')
    expect(reads).toBe(2)
    expect(finishOld).not.toBeNull()
    expect(button('Muat ulang pengingat sistem').disabled).toBe(true)
    expect(container.querySelector(`[aria-label="Pengingat sistem ${ACCESSORY_TITLE}"]`)).toBeNull()

    // An actual identity revision remounts Workspace; no second disabled refresh
    // is manufactured. The new identity remains AUTHORIZED but its RPC is denied.
    auth.current = { ...owner, identity: { ...owner.identity, profile: { ...owner.identity.profile, rowVersion: 1 } } }
    await mount(); await tab('Pengingat sistem')
    expect(reads).toBe(3)
    expect((auth.current as typeof owner).identity.status).toBe('AUTHORIZED')
    expectAccessoryFactsRetired(status)
    const complete = finishOld as unknown as (value: { data: ReturnType<typeof accessoryAlertsReply>; error: null }) => void
    await act(async () => { complete({ data: structuredClone(reply), error: null }) }); await settle()
    expect(reads).toBe(3)
    expectAccessoryFactsRetired(status)
  })

  it('shows the server refusal in words when the connection read is refused', async () => {
    // An owner account that the server no longer counts as an active owner (CP7_WA_OWNER_ONLY, 42501).
    server(); const rpc = client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async (name: string, args?: Record<string, unknown>) => name === 'erp_cp7_get_wa_settings_v1'
      ? refuse('42501', 'CP7_WA_OWNER_ONLY') : rpc(name, args))
    await mount(); await tab('Sambungan WhatsApp')
    expect(container.querySelector('#creminders-panel-WA [role="alert"]')?.textContent).toBe('Sambungan WhatsApp hanya bisa dibuka dan diubah oleh akun Owner yang aktif.')
    expect(container.querySelector('input[aria-label="Kunci CallMeBot"]')).toBeNull()
  })
})
