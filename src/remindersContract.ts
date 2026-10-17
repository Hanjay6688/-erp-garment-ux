import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'
import { cp6WibPhysicalTimeToIso } from './cp6BusinessTime'

// R3-03 (owner D16-1): closed parsers for scripts/cp7-src/manual-reminders/facade.sql, the CP7 facade over the Native
// own-user manual reminders (erp.manual_reminders). The predicates below are the facade's own (title 1-200, note <= 4000,
// module 1-80, priority, due time with an offset, cancel reason 5-1000); the Native rules (only OPEN is edited, DONE is
// reopened first, CANCELLED is final) decide which actions the screen offers.
export const reminderFilters = ['ACTIVE', 'OPEN', 'DONE', 'CANCELLED', 'ALL'] as const
export type ReminderFilter = typeof reminderFilters[number]
export const reminderPriorities = ['URGENT', 'NORMAL', 'LOW'] as const
export type ReminderPriority = typeof reminderPriorities[number]
export type ReminderStatus = 'OPEN' | 'DONE' | 'CANCELLED'
export type ReminderDueState = 'OVERDUE' | 'TODAY' | 'TOMORROW' | 'LATER'
export type ReminderAction = 'SAVE' | 'DONE' | 'UNDONE' | 'CANCEL'
export type ConnectedReminder = {
  id: string; title: string; note: string; dueAt: string; priority: ReminderPriority; module: string; status: ReminderStatus
  completedAt: string | null; cancelledAt: string | null; cancellationReason: string | null; createdAt: string; updatedAt: string
  rowVersion: number; dueState: ReminderDueState | null
}
export type ReminderQuery = { filter: ReminderFilter; limit: number; offset: number }
export type RemindersWorkspace = {
  filter: ReminderFilter
  page: { limit: number; offset: number; total: number; shown: number; window: number; nextOffset: number | null; beyondWindow: number }
  items: ConnectedReminder[]
  counts: { open: number; done: number; cancelled: number }
  due: { overdue: number; today: number; tomorrow: number; complete: boolean }
  today: string; readAt: string; canManage: boolean
}
export type ReminderDraft = { title: string; note: string; dueWib: string; priority: ReminderPriority; module: string }
export type ReminderOutcome = { action: ReminderAction; requestId: string; reminderId: string; status: ReminderStatus; rowVersion: number; created: boolean }

export const REMINDER_PAGE_SIZE = 25
export const REMINDER_WINDOW = 200
export const reminderPriorityLabel: Record<ReminderPriority, string> = { URGENT: 'Penting', NORMAL: 'Normal', LOW: 'Santai' }
export const reminderFilterLabel: Record<ReminderFilter, string> = {
  ACTIVE: 'Aktif', OPEN: 'Belum selesai', DONE: 'Sudah selesai', CANCELLED: 'Dibatalkan', ALL: 'Semua',
}
const statusesByFilter: Record<ReminderFilter, readonly ReminderStatus[]> = {
  ACTIVE: ['OPEN', 'DONE'], OPEN: ['OPEN'], DONE: ['DONE'], CANCELLED: ['CANCELLED'], ALL: ['OPEN', 'DONE', 'CANCELLED'],
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const day = /^\d{4}-\d{2}-\d{2}$/
const dueText = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})$/

function fail(what: string): never { throw new Error(`Respons pengingat tidak cocok (${what}).`) }
type Obj = Record<string, unknown>
const obj = (v: unknown, what: string): Obj => Boolean(v) && typeof v === 'object' && !Array.isArray(v) ? v as Obj : fail(what)
const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
const instant = (v: unknown, what: string) => typeof v === 'string' && Number.isFinite(Date.parse(v)) ? v : fail(what)
const maybeInstant = (v: unknown, what: string) => v === null ? null : instant(v, what)
const count = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
const positive = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 1 ? v : fail(what)
function oneOf<T extends string>(v: unknown, values: readonly T[], what: string): T { return typeof v === 'string' && (values as readonly string[]).includes(v) ? v as T : fail(what) }
function keys(o: Obj, expected: readonly string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}

export function reminderQuery(filter: ReminderFilter, offset = 0): ReminderQuery {
  if (!reminderFilters.includes(filter) || !Number.isSafeInteger(offset) || offset < 0 || offset >= REMINDER_WINDOW) fail('pilihan daftar')
  return { filter, limit: REMINDER_PAGE_SIZE, offset }
}

function item(v: unknown, filter: ReminderFilter): ConnectedReminder {
  const o = obj(v, 'pengingat')
  keys(o, ['id', 'title', 'note', 'due_at', 'priority', 'module', 'status', 'completed_at', 'cancelled_at', 'cancellation_reason',
    'created_at', 'updated_at', 'row_version', 'due_state'], 'pengingat')
  const id = str(o.id, 'id'); if (!uuid.test(id)) fail('id')
  const status = oneOf(o.status, statusesByFilter[filter], 'status')
  const r: ConnectedReminder = {
    id, title: str(o.title, 'judul'), note: str(o.note, 'catatan'), dueAt: instant(o.due_at, 'jatuh tempo'),
    priority: oneOf(o.priority, reminderPriorities, 'prioritas'), module: str(o.module, 'modul'), status,
    completedAt: maybeInstant(o.completed_at, 'waktu selesai'), cancelledAt: maybeInstant(o.cancelled_at, 'waktu batal'),
    cancellationReason: o.cancellation_reason === null ? null : str(o.cancellation_reason, 'alasan batal'),
    createdAt: instant(o.created_at, 'dibuat'), updatedAt: instant(o.updated_at, 'diubah'), rowVersion: positive(o.row_version, 'versi'),
    dueState: o.due_state === null ? null : oneOf(o.due_state, ['OVERDUE', 'TODAY', 'TOMORROW', 'LATER'] as const, 'status jatuh tempo'),
  }
  if ((r.dueState === null) !== (status !== 'OPEN')) fail('status jatuh tempo')
  if (status === 'OPEN' && (r.completedAt !== null || r.cancelledAt !== null || r.cancellationReason !== null)) fail('status')
  if (status === 'DONE' && (r.completedAt === null || r.cancelledAt !== null || r.cancellationReason !== null)) fail('status')
  if (status === 'CANCELLED' && (r.cancelledAt === null || !r.cancellationReason)) fail('status')
  return r
}

export function parseRemindersWorkspace(value: unknown, query: ReminderQuery): RemindersWorkspace {
  const w = obj(value, 'ruang kerja')
  keys(w, ['contract_version', 'filter', 'page', 'items', 'counts', 'due', 'today', 'read_at', 'can_manage', 'business_DML'], 'ruang kerja')
  if (w.contract_version !== 'cp7.reminders-workspace.v1' || w.business_DML !== false || typeof w.can_manage !== 'boolean') fail('kontrak')
  if (w.filter !== query.filter) fail('filter')
  const p = obj(w.page, 'halaman')
  keys(p, ['limit', 'offset', 'total', 'shown', 'window', 'window_limit', 'next_offset', 'beyond_window'], 'halaman')
  const page = { limit: positive(p.limit, 'halaman'), offset: count(p.offset, 'halaman'), total: count(p.total, 'jumlah'), shown: count(p.shown, 'halaman'),
    window: count(p.window, 'halaman'), nextOffset: p.next_offset === null ? null : count(p.next_offset, 'halaman'), beyondWindow: count(p.beyond_window, 'halaman') }
  if (page.limit !== query.limit || page.offset !== query.offset || p.window_limit !== REMINDER_WINDOW) fail('halaman')
  if (page.window !== Math.min(page.total, REMINDER_WINDOW) || page.beyondWindow !== page.total - page.window) fail('jumlah')
  if (page.nextOffset !== (page.offset + page.limit < page.window ? page.offset + page.limit : null)) fail('halaman')
  if (page.shown !== Math.max(0, Math.min(page.limit, page.window - page.offset))) fail('halaman')
  const items = Array.isArray(w.items) ? w.items.map(x => item(x, query.filter)) : fail('daftar')
  if (items.length !== page.shown || new Set(items.map(x => x.id)).size !== items.length) fail('daftar')
  const c = obj(w.counts, 'jumlah'); keys(c, ['open', 'done', 'cancelled'], 'jumlah')
  const counts = { open: count(c.open, 'jumlah'), done: count(c.done, 'jumlah'), cancelled: count(c.cancelled, 'jumlah') }
  const total = query.filter === 'ACTIVE' ? counts.open + counts.done : query.filter === 'OPEN' ? counts.open : query.filter === 'DONE' ? counts.done
    : query.filter === 'CANCELLED' ? counts.cancelled : counts.open + counts.done + counts.cancelled
  if (total !== page.total) fail('jumlah')
  const d = obj(w.due, 'jatuh tempo'); keys(d, ['overdue', 'today', 'tomorrow', 'complete'], 'jatuh tempo')
  const due = { overdue: count(d.overdue, 'jatuh tempo'), today: count(d.today, 'jatuh tempo'), tomorrow: count(d.tomorrow, 'jatuh tempo'),
    complete: d.complete === true ? true : d.complete === false ? false : fail('jatuh tempo') }
  if (due.complete !== (counts.open <= REMINDER_WINDOW) || due.overdue + due.today + due.tomorrow > Math.min(counts.open, REMINDER_WINDOW)) fail('jatuh tempo')
  const today = typeof w.today === 'string' && day.test(w.today) ? w.today : fail('hari ini')
  return { filter: query.filter, page, items, counts, due, today, readAt: instant(w.read_at, 'waktu baca'), canManage: w.can_manage }
}

export function reminderDraftProblem(d: ReminderDraft): string {
  if (!d.title.trim()) return 'Isi judul pengingat.'
  if (d.title.trim().length > 200) return 'Judul paling banyak 200 huruf.'
  if (d.note.length > 4000) return 'Catatan paling banyak 4.000 huruf.'
  if (!cp6WibPhysicalTimeToIso(d.dueWib)) return 'Isi tanggal dan jam jatuh tempo (WIB).'
  if (!reminderPriorities.includes(d.priority)) return 'Pilih prioritas.'
  if (!d.module.trim()) return 'Isi modul atau konteks (misalnya Laundry).'
  if (d.module.trim().length > 80) return 'Modul paling banyak 80 huruf.'
  return ''
}
export function reminderCancelProblem(reason: string) {
  const n = reason.trim().length
  return n < 5 ? 'Tulis alasan batal (minimal 5 huruf).' : n > 1000 ? 'Alasan paling banyak 1.000 huruf.' : ''
}
export function reminderSavePayload(id: string | null, d: ReminderDraft): Json {
  const due = cp6WibPhysicalTimeToIso(d.dueWib)
  if (reminderDraftProblem(d) || !due || !dueText.test(due) || (id !== null && !uuid.test(id))) fail('isian')
  return { id, title: d.title.trim(), note: d.note, due_at: due, priority: d.priority, module: d.module.trim() }
}
export function reminderIdPayload(id: string): Json {
  if (!uuid.test(id)) fail('id')
  return { id }
}
export function reminderCancelPayload(id: string, reason: string): Json {
  if (!uuid.test(id) || reminderCancelProblem(reason)) fail('alasan')
  return { id, reason: reason.trim() }
}

export function validateReminderOutcome(value: unknown, envelope: ProductionEnvelope): ReminderOutcome {
  const o = obj(value, 'hasil')
  keys(o, ['contract_version', 'kind', 'action', 'request_id', 'created', 'reminder_id', 'status', 'row_version'], 'hasil')
  const payload = obj(envelope.payload, 'permintaan')
  const action = oneOf(o.action, ['SAVE', 'DONE', 'UNDONE', 'CANCEL'] as const, 'aksi')
  const sentId = payload.id === null ? null : str(payload.id, 'id')
  const reminderId = str(o.reminder_id, 'id'); if (!uuid.test(reminderId)) fail('id')
  const status = oneOf(o.status, ['OPEN', 'DONE', 'CANCELLED'] as const, 'status')
  const rowVersion = positive(o.row_version, 'versi')
  const expectedStatus = action === 'DONE' ? 'DONE' : action === 'CANCEL' ? 'CANCELLED' : 'OPEN'
  if (o.contract_version !== 'cp7.reminders-outcome.v1' || o.kind !== 'COMMITTED_OUTCOME' || action !== envelope.action || o.request_id !== envelope.id
    || (sentId !== null && reminderId.toLowerCase() !== sentId.toLowerCase()) || o.created !== (action === 'SAVE' && sentId === null)
    || status !== expectedStatus || rowVersion < (envelope.expectedVersion ?? 1) || (sentId === null) !== (envelope.expectedVersion === null)) fail('hasil')
  return { action, requestId: envelope.id, reminderId, status, rowVersion, created: o.created === true }
}

// The facade refusals in plain words, with the way out (best practice D18). 42501 refusals of a write keep the shared
// access text of normalizeClientError; the read path and the message of a refused write use this text.
const refusals: Record<string, string> = {
  CP7_REMINDERS_DENIED: 'Akun ini belum punya hak Reminder. Minta Owner menambahkannya di Pengguna & Hak Akses.',
  CP7_REMINDERS_ROLE_DENIED: 'Pengingat hanya untuk akun internal Owner, Admin, atau Staff. Peran akun ini tidak termasuk, jadi pengingat tidak bisa dibuka atau diubah.',
  CP7_REMINDERS_ACCESS_CHANGED: 'Hak akses akun berubah saat disimpan. Muat ulang halaman lalu coba lagi.',
  CP7_REMINDERS_STALE: 'Pengingat ini baru saja diubah di tab atau perangkat lain. Muat ulang daftar, periksa isinya, lalu ulangi.',
  CP7_REMINDERS_NOT_FOUND: 'Pengingat itu tidak ada di daftar akun ini. Muat ulang daftar.',
  CP7_REMINDERS_NOT_OPEN: 'Pengingat yang sudah selesai tidak bisa diubah. Tekan "Buka lagi" dulu, lalu ubah.',
  CP7_REMINDERS_CANCELLED: 'Pengingat yang sudah dibatalkan tidak bisa diubah atau dibuka lagi. Buat pengingat baru bila masih perlu.',
  CP7_REMINDERS_REQUEST_CHANGED: 'Permintaan ini sudah pernah dipakai dengan isi lain. Muat ulang daftar lalu kirim sebagai perubahan baru.',
  CP7_REMINDERS_FIELDS: 'Isian pengingat belum lengkap atau formatnya belum sesuai. Periksa judul, jatuh tempo, prioritas, modul, dan alasan.',
  CP7_REMINDERS_QUERY: 'Pilihan daftar pengingat tidak sah. Muat ulang halaman.',
  CP7_REMINDERS_SOURCE: 'Data pengingat dari server tidak cocok. Muat ulang daftar; bila tetap sama, laporkan ke admin.',
}
export function reminderRefusal(message: unknown): string | null {
  if (typeof message !== 'string') return null
  const code = /\bCP7_REMINDERS_[A-Z_]+\b/.exec(message)?.[0]
  return code ? refusals[code] ?? null : null
}
// A refused write keeps its code and status (so the recovery hook still knows the refusal was definite); only the message
// is put in words.
export function withReminderRefusal(error: unknown): unknown {
  if (!error || typeof error !== 'object') return error
  const text = reminderRefusal((error as { message?: unknown }).message)
  return text ? { ...(error as Record<string, unknown>), message: text } : error
}
