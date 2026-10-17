import { ACCESSORY_POLICY_KEYS, type AccessoryPolicyKey } from './accessoryService'
import { LAU_POLICY_KEYS, type LauPolicyKey } from './laundryBd'
import type { Json } from './types/database.preconnect'

// R3-03 (owner D16-1): the Pengaturan ERP screen. Closed parser for scripts/cp7-src/erp-settings/settings.sql
// (public.erp_cp7_get_erp_settings_v1) and the exact SET_POLICY payloads the Aksesori and Laundry pages send to their Native
// writers. Values, reasons, names, pick lists and the cutover date come only to OWNER/ADMIN; a reply that carries them to
// anyone else, or misses a policy, is refused (the page then says the settings could not be read, without figures).
export type SettingsFamilyKey = 'ACCESSORY' | 'LAUNDRY'
export type SettingsPolicyKey = AccessoryPolicyKey | LauPolicyKey
export type SettingsStatus = 'SET' | 'PENDING_POLICY_VALUE'
export type SettingsEvent = { version: string; status: SettingsStatus; value: Record<string, unknown> | null; reason: string | null; setAt: string; setBy: string | null }
export type SettingsPolicy = {
  key: SettingsPolicyKey; label: string; status: SettingsStatus; statusText: string; pendingEffect: string | null; ownerChoice: boolean
  version: string; setAt: string; setBy: string | null; reason: string | null; value: Record<string, unknown> | null
  eventCount: number; events: SettingsEvent[]
}
export type SettingsFamily = { family: SettingsFamilyKey; label: string; sourcePage: string; visible: boolean; canSet: boolean; policies: SettingsPolicy[] | null }
export type SettingsCutover = { version: number; cutoverDate: string | null; setAt: string | null; setBy: string | null; reason: string | null; changeOn: string }
export type SettingsChoice = { id: string; name: string }
export type SettingsAccount = { id: string; code: string; name: string; type: 'ASSET' | 'EXPENSE' | 'REVENUE' }
export type SettingsZone = { id: string; code: string; name: string; kind: 'SERVICE_POST' | 'INSPECTION' | 'DAMAGED' }
export type SettingsChoices = {
  accounts: SettingsAccount[]; accountsTotal: number; categories: SettingsChoice[]; categoriesTotal: number
  users: SettingsChoice[]; usersTotal: number; zones: SettingsZone[]; zonesTotal: number
}
export type ErpSettingsWorkspace = {
  readAt: string; canSeeValues: boolean; families: [SettingsFamily, SettingsFamily]
  cutoverVisible: boolean; cutover: SettingsCutover | null; choices: SettingsChoices | null
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const instantText = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/
type Obj = Record<string, unknown>
function fail(what: string): never { throw new Error(`Pengaturan ERP tidak terbaca lengkap (${what}). Muat ulang pengaturan.`) }
const obj = (v: unknown, what: string): Obj => v !== null && typeof v === 'object' && !Array.isArray(v) ? v as Obj : fail(what)
const list = (v: unknown, what: string): unknown[] => Array.isArray(v) ? v : fail(what)
const text = (v: unknown, what: string) => typeof v === 'string' && v.trim() !== '' ? v : fail(what)
const nullableText = (v: unknown, what: string) => v === null ? null : text(v, what)
const bool = (v: unknown, what: string) => typeof v === 'boolean' ? v : fail(what)
const count = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
const id = (v: unknown, what: string) => typeof v === 'string' && uuid.test(v) ? v : fail(what)
const instant = (v: unknown, what: string) => typeof v === 'string' && instantText.test(v) && Number.isFinite(Date.parse(v)) ? v : fail(what)
const versionText = (v: unknown, what: string) => typeof v === 'string' && /^[1-9]\d{0,18}$/.test(v) ? v : fail(what)
function oneOf<T extends string>(v: unknown, allowed: readonly T[], what: string): T { return allowed.includes(v as T) ? v as T : fail(what) }
function keys(o: Obj, expected: readonly string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}
function value(v: unknown, what: string): Record<string, unknown> | null {
  if (v === null) return null
  return obj(v, what)
}

const FAMILY_KEYS: Record<SettingsFamilyKey, readonly SettingsPolicyKey[]> = { ACCESSORY: ACCESSORY_POLICY_KEYS, LAUNDRY: LAU_POLICY_KEYS }
const STATUSES = ['SET', 'PENDING_POLICY_VALUE'] as const

function parseEvent(v: unknown, canSeeValues: boolean): SettingsEvent {
  const e = obj(v, 'riwayat'); keys(e, ['version', 'status', 'value', 'reason', 'set_at', 'set_by'], 'riwayat')
  const status = oneOf(e.status, STATUSES, 'status riwayat'), val = value(e.value, 'isi riwayat')
  const reason = e.reason === null ? null : typeof e.reason === 'string' ? e.reason : fail('alasan riwayat')
  const setBy = nullableText(e.set_by, 'pengubah riwayat')
  if (!canSeeValues && (val !== null || reason !== null || setBy !== null)) fail('isi riwayat hanya untuk owner/admin')
  if (status === 'PENDING_POLICY_VALUE' && val !== null) fail('riwayat menunggu tanpa isi')
  if (canSeeValues && (status === 'SET') !== (val !== null)) fail('isi riwayat')
  if (canSeeValues && reason === null) fail('alasan riwayat')
  return { version: versionText(e.version, 'versi riwayat'), status, value: val, reason, setAt: instant(e.set_at, 'waktu riwayat'), setBy }
}

function parsePolicy(v: unknown, expectedKey: SettingsPolicyKey, canSeeValues: boolean): SettingsPolicy {
  const p = obj(v, 'kebijakan')
  keys(p, ['key', 'label', 'status', 'status_text', 'pending_effect', 'owner_choice', 'version', 'set_at', 'set_by', 'reason', 'value', 'event_count', 'events'], 'kebijakan')
  if (p.key !== expectedKey) fail('urutan kebijakan')
  const status = oneOf(p.status, STATUSES, 'status kebijakan'), val = value(p.value, 'isi kebijakan')
  const reason = p.reason === null ? null : text(p.reason, 'alasan kebijakan'), setBy = nullableText(p.set_by, 'pengubah kebijakan')
  if (!canSeeValues && (val !== null || reason !== null || setBy !== null)) fail('isi kebijakan hanya untuk owner/admin')
  if (status === 'PENDING_POLICY_VALUE' && val !== null) fail('kebijakan menunggu tanpa isi')
  if (canSeeValues && ((status === 'SET') !== (val !== null) || reason === null)) fail('isi kebijakan')
  const pendingEffect = nullableText(p.pending_effect, 'dampak kebijakan')
  if ((status === 'SET') !== (pendingEffect === null)) fail('dampak kebijakan')
  const version = versionText(p.version, 'versi kebijakan'), eventCount = count(p.event_count, 'jumlah riwayat')
  const events = list(p.events, 'riwayat kebijakan').map(e => parseEvent(e, canSeeValues))
  if (events.length > 5 || events.length > eventCount || (eventCount > 0 && events.length === 0)) fail('jumlah riwayat')
  for (let i = 1; i < events.length; i++) if (BigInt(events[i - 1].version) <= BigInt(events[i].version)) fail('urutan riwayat')
  return { key: expectedKey, label: text(p.label, 'nama kebijakan'), status, statusText: text(p.status_text, 'status kebijakan'), pendingEffect,
    ownerChoice: bool(p.owner_choice, 'keputusan owner'), version, setAt: instant(p.set_at, 'waktu kebijakan'), setBy, reason, value: val, eventCount, events }
}

function parseFamily(v: unknown, expected: SettingsFamilyKey, canSeeValues: boolean): SettingsFamily {
  const f = obj(v, 'kelompok'); keys(f, ['family', 'label', 'source_page', 'visible', 'can_set', 'policies'], 'kelompok')
  if (f.family !== expected) fail('kelompok')
  const visible = bool(f.visible, 'hak lihat'), canSet = bool(f.can_set, 'hak ubah')
  if ((!visible || !canSeeValues) && canSet) fail('hak ubah')
  let policies: SettingsPolicy[] | null = null
  if (visible) {
    const raw = list(f.policies, 'daftar kebijakan'), want = FAMILY_KEYS[expected]
    if (raw.length !== want.length) fail('daftar kebijakan tidak lengkap')
    policies = raw.map((p, i) => parsePolicy(p, want[i], canSeeValues))
  } else if (f.policies !== null) fail('kebijakan tanpa hak lihat')
  return { family: expected, label: text(f.label, 'nama kelompok'), sourcePage: text(f.source_page, 'halaman asal'), visible, canSet, policies }
}

function parseCutover(v: unknown): SettingsCutover {
  const c = obj(v, 'tanggal mulai'); keys(c, ['version', 'cutover_date', 'set_at', 'set_by', 'reason', 'change_on'], 'tanggal mulai')
  const version = count(c.version, 'versi tanggal mulai')
  const cutoverDate = c.cutover_date === null ? null : typeof c.cutover_date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(c.cutover_date) ? c.cutover_date : fail('tanggal mulai')
  if ((version === 0) !== (cutoverDate === null)) fail('versi tanggal mulai')
  const setAt = c.set_at === null ? null : instant(c.set_at, 'waktu tanggal mulai'), setBy = nullableText(c.set_by, 'pengesah tanggal mulai')
  const reason = nullableText(c.reason, 'alasan tanggal mulai')
  if ((cutoverDate === null) !== (setAt === null) || (setAt === null) !== (setBy === null)) fail('riwayat tanggal mulai')
  return { version, cutoverDate, setAt, setBy, reason, changeOn: text(c.change_on, 'tempat ubah tanggal mulai') }
}

function parseChoices(v: unknown): SettingsChoices {
  const c = obj(v, 'pilihan')
  keys(c, ['accounts', 'accounts_total', 'categories', 'categories_total', 'users', 'users_total', 'zones', 'zones_total'], 'pilihan')
  const accounts = list(c.accounts, 'akun').map(a => { const x = obj(a, 'akun'); keys(x, ['id', 'code', 'name', 'type'], 'akun')
    return { id: id(x.id, 'akun'), code: text(x.code, 'kode akun'), name: text(x.name, 'nama akun'), type: oneOf(x.type, ['ASSET', 'EXPENSE', 'REVENUE'] as const, 'jenis akun') } })
  const named = (raw: unknown, what: string) => list(raw, what).map(a => { const x = obj(a, what); keys(x, ['id', 'name'], what); return { id: id(x.id, what), name: text(x.name, what) } })
  const zones = list(c.zones, 'area').map(a => { const x = obj(a, 'area'); keys(x, ['id', 'code', 'name', 'kind'], 'area')
    return { id: id(x.id, 'area'), code: text(x.code, 'kode area'), name: text(x.name, 'nama area'), kind: oneOf(x.kind, ['SERVICE_POST', 'INSPECTION', 'DAMAGED'] as const, 'jenis area') } })
  const out = { accounts, accountsTotal: count(c.accounts_total, 'jumlah akun'), categories: named(c.categories, 'kategori'), categoriesTotal: count(c.categories_total, 'jumlah kategori'),
    users: named(c.users, 'pengguna'), usersTotal: count(c.users_total, 'jumlah pengguna'), zones, zonesTotal: count(c.zones_total, 'jumlah area') }
  if (out.accounts.length > out.accountsTotal || out.categories.length > Math.min(100, out.categoriesTotal) || out.users.length > Math.min(100, out.usersTotal)
    || out.zones.length > Math.min(100, out.zonesTotal)) fail('jumlah pilihan')
  return out
}

export function parseErpSettingsWorkspace(raw: unknown): ErpSettingsWorkspace {
  const w = obj(raw, 'ruang kerja')
  keys(w, ['contract_version', 'read_at', 'can_see_values', 'families', 'cutover_visible', 'cutover', 'choices', 'business_DML'], 'ruang kerja')
  if (w.contract_version !== 'cp7.erp-settings.v1' || w.business_DML !== false) fail('kontrak')
  const canSeeValues = bool(w.can_see_values, 'hak lihat isi'), cutoverVisible = bool(w.cutover_visible, 'hak lihat tanggal mulai')
  const families = list(w.families, 'kelompok')
  if (families.length !== 2) fail('kelompok')
  if (!canSeeValues && (cutoverVisible || w.cutover !== null || w.choices !== null)) fail('isi hanya untuk owner/admin')
  if (cutoverVisible !== canSeeValues || (canSeeValues && (w.cutover === null || w.choices === null))) fail('tanggal mulai dan pilihan')
  return { readAt: instant(w.read_at, 'waktu baca'), canSeeValues,
    families: [parseFamily(families[0], 'ACCESSORY', canSeeValues), parseFamily(families[1], 'LAUNDRY', canSeeValues)],
    cutoverVisible, cutover: w.cutover === null ? null : parseCutover(w.cutover), choices: w.choices === null ? null : parseChoices(w.choices) }
}

/** The payload the Aksesori page (ConnectedAccessoryServicePage, Kebijakan & area) sends with SET_POLICY, built the same way. */
export function accessoryPolicyPayload(key: AccessoryPolicyKey, operation: 'SET' | 'CLEAR', expectedVersion: string, reason: string,
  value: Record<string, Json> | null): Record<string, Json> {
  return { policy_key: key.replace('-', '_'), operation, expected_version: expectedVersion, reason: reason.trim(),
    ...(operation === 'SET' && value !== null ? { value } : {}) }
}

/** The payload the Laundry page (LaundryBdPanel, Kebijakan owner) sends with SET_POLICY, built the same way. */
export function laundryPolicyPayload(key: LauPolicyKey, operation: 'SET' | 'CLEAR', expectedVersion: string, reason: string,
  value: Record<string, Json> | null): Record<string, Json> {
  return operation === 'SET' && value !== null
    ? { policy_key: key, operation: 'SET', expected_version: expectedVersion, reason: reason.trim(), value }
    : { policy_key: key, operation: 'CLEAR', expected_version: expectedVersion, reason: reason.trim() }
}

/** A Native refusal said in everyday words with the way out; anything else is shown as the server said it. */
export function settingsRefusalText(message: string): string {
  const m = message.trim()
  if (/STALE_VERSION/.test(m)) return 'Pengaturan ini baru saja diubah di layar lain. Muat ulang pengaturan, periksa nilai terbaru, lalu simpan lagi bila masih perlu.'
  if (/B[CD]_OWNER_ONLY/.test(m)) return 'Hanya owner yang dapat mengubah kebijakan ini. Minta owner menyimpannya dari halaman ini.'
  if (/Internal ERP access required/i.test(m)) return 'Hanya owner yang dapat mengubah kebijakan ini. Minta owner menyimpannya dari halaman ini.'
  const value = /^B[CD]_POLICY_VALUE:\s*(.+)$/.exec(m)
  if (value) return `Nilai belum diterima server: ${value[1]}. Periksa pilihan lalu simpan lagi.`
  const reason = /^B[CD]_REASON_REQUIRED:\s*(.+)$/.exec(m)
  if (reason) return `${reason[1].charAt(0).toUpperCase()}${reason[1].slice(1)}.`
  return m
}
