import type { Json } from '../types/database.preconnect'
import { parseAnalysisStatus } from './alerts'
import {
  arr,
  bool,
  clock,
  count,
  fail,
  instant,
  keys,
  maybeInstant,
  maybeStr,
  obj,
  oneOf,
  positive,
  tick,
  within,
} from './fields'
import { WA_DIGEST_SLOTS, dispatchKinds, dispatchStatuses, outboxStates, waKinds, waPhonePattern, waTickJobs } from './model'
import type {
  DispatchOutcome,
  OutboxState,
  Tick,
  WaDispatch,
  WaDraft,
  WaKeyResult,
  WaResolveResult,
  WaSaveResult,
  WaSettings,
  WaTestResult,
  WaTickJob,
  WaWorkspace,
} from './model'
const settingsKeys = ['revision', 'enabled', 'phone_e164', 'detail', 'digest_times', 'kinds', 'repeat_minutes', 'burst_after_per_day', 'burst_merge_minutes',
  'max_items', 'quiet_enabled', 'quiet_start', 'quiet_end', 'analysis_every_minutes', 'analysis_start', 'analysis_end'] as const

function settings(v: unknown, what: string): WaSettings {
  const o = obj(v, what)
  const revision = count(o.revision, what)
  keys(o, revision === 0 ? settingsKeys : [...settingsKeys, 'saved_at'], what)
  const times = arr(o.digest_times, what).map(t => typeof t === 'string' && clock.test(t) ? t : fail(what))
  const kinds = arr(o.kinds, what).map(k => oneOf(k, waKinds, what))
  const s: WaSettings = { revision, enabled: bool(o.enabled, what), phone: maybeStr(o.phone_e164, what), detail: oneOf(o.detail, ['SUMMARY', 'DETAILED'] as const, what),
    digestTimes: times, kinds, repeatMinutes: within(o.repeat_minutes, 60, 10080, what, true), burstAfterPerDay: within(o.burst_after_per_day, 1, 200, what),
    burstMergeMinutes: within(o.burst_merge_minutes, 5, 240, what), maxItems: within(o.max_items, 1, 20, what), quietEnabled: bool(o.quiet_enabled, what),
    quietStart: typeof o.quiet_start === 'string' && clock.test(o.quiet_start) ? o.quiet_start : fail(what),
    quietEnd: typeof o.quiet_end === 'string' && clock.test(o.quiet_end) ? o.quiet_end : fail(what),
    analysisEveryMinutes: within(o.analysis_every_minutes, 15, 1440, what, true),
    analysisStart: typeof o.analysis_start === 'string' && clock.test(o.analysis_start) ? o.analysis_start : fail(what),
    analysisEnd: typeof o.analysis_end === 'string' && clock.test(o.analysis_end) ? o.analysis_end : fail(what),
    savedAt: revision === 0 ? null : instant(o.saved_at, what) }
  if (times.length > WA_DIGEST_SLOTS || new Set(times).size !== times.length || new Set(kinds).size !== kinds.length) fail(what)
  if (s.phone !== null && !waPhonePattern.test(s.phone)) fail(what)
  if ((s.enabled && s.phone === null) || s.quietStart === s.quietEnd || s.analysisStart >= s.analysisEnd) fail(what)
  return s
}

/** erp_cp7_get_wa_settings_v1 (owner only). */
export function parseWaWorkspace(value: unknown): WaWorkspace {
  const w = obj(value, 'sambungan')
  keys(w, ['contract_version', 'read_at', 'settings', 'defaults', 'key_present', 'key_set_at', 'transport_is_callmebot', 'quiet_now', 'analysis', 'ticks',
    'outbox', 'dispatches'], 'sambungan')
  if (w.contract_version !== 'cp7.wa-settings.v1') fail('kontrak')
  const defaults = settings(w.defaults, 'pengaturan bawaan')
  if (defaults.revision !== 0) fail('pengaturan bawaan')
  const t = obj(w.ticks, 'jadwal'), ticks: Partial<Record<WaTickJob, Tick>> = {}
  for (const [job, x] of Object.entries(t)) ticks[oneOf(job, waTickJobs, 'jadwal')] = tick(x, 'jadwal')
  const q = obj(w.outbox, 'antrean'), outbox: Partial<Record<OutboxState, number>> = {}
  for (const [state, n] of Object.entries(q)) outbox[oneOf(state, outboxStates, 'antrean')] = positive(n, 'antrean')
  const dispatches = arr(w.dispatches, 'riwayat').map((x): WaDispatch => {
    const d = obj(x, 'riwayat')
    keys(d, ['id', 'kind', 'status', 'queued_at', 'answered_at', 'http_status', 'provider_text', 'body', 'digest_slot', 'resolved_outcome', 'resolved_at', 'items'], 'riwayat')
    const r: WaDispatch = { id: positive(d.id, 'riwayat'), kind: oneOf(d.kind, dispatchKinds, 'riwayat'), status: oneOf(d.status, dispatchStatuses, 'riwayat'),
      queuedAt: instant(d.queued_at, 'riwayat'), answeredAt: maybeInstant(d.answered_at, 'riwayat'),
      httpStatus: d.http_status === null ? null : typeof d.http_status === 'number' && Number.isSafeInteger(d.http_status) ? d.http_status : fail('riwayat'),
      providerText: maybeStr(d.provider_text, 'riwayat'), body: maybeStr(d.body, 'riwayat'), digestSlot: maybeInstant(d.digest_slot, 'riwayat'),
      resolvedOutcome: d.resolved_outcome === null ? null : oneOf(d.resolved_outcome, ['DELIVERED', 'NOT_DELIVERED'] as const, 'riwayat'),
      resolvedAt: maybeInstant(d.resolved_at, 'riwayat'), items: count(d.items, 'riwayat') }
    if ((r.kind === 'DIGEST') !== (r.digestSlot !== null) || (r.status === 'NOTHING_DUE') !== (r.body === null) || (r.status === 'NOTHING_DUE' && r.kind !== 'DIGEST')
      || (r.resolvedOutcome === null) !== (r.resolvedAt === null) || (r.resolvedOutcome !== null && r.status !== 'UNKNOWN')) fail('riwayat')
    return r
  })
  if (dispatches.length > 30 || dispatches.some((d, i) => i > 0 && d.id >= dispatches[i - 1].id)) fail('riwayat')
  return { readAt: instant(w.read_at, 'waktu baca'), settings: settings(w.settings, 'pengaturan'), defaults, keyPresent: bool(w.key_present, 'kunci'),
    keySetAt: maybeInstant(w.key_set_at, 'kunci'), transportIsCallmebot: bool(w.transport_is_callmebot, 'alamat kirim'), quietNow: bool(w.quiet_now, 'jam tenang'),
    analysis: parseAnalysisStatus(w.analysis), ticks, outbox, dispatches }
}

// ---------------------------------------------------------------- the form --
export function waDraftFromSettings(s: WaSettings): WaDraft {
  const slots = [...s.digestTimes].sort()
  return { enabled: s.enabled, phone: s.phone ?? '', detail: s.detail, digestTimes: Array.from({ length: WA_DIGEST_SLOTS }, (_, i) => slots[i] ?? ''),
    kinds: waKinds.filter(k => s.kinds.includes(k)), repeatMinutes: String(s.repeatMinutes), burstAfterPerDay: String(s.burstAfterPerDay),
    burstMergeMinutes: String(s.burstMergeMinutes), maxItems: String(s.maxItems), quietEnabled: s.quietEnabled, quietStart: s.quietStart, quietEnd: s.quietEnd,
    analysisEveryMinutes: String(s.analysisEveryMinutes), analysisStart: s.analysisStart, analysisEnd: s.analysisEnd }
}

export function sameWaDraft(a: WaDraft, b: WaDraft) {
  const norm = (d: WaDraft) => ({ ...d, phone: d.phone.trim(), digestTimes: d.digestTimes.filter(Boolean).sort(), kinds: waKinds.filter(k => d.kinds.includes(k)) })
  return JSON.stringify(norm(a)) === JSON.stringify(norm(b))
}
const whole = (v: string) => /^\d{1,5}$/.test(v.trim()) ? Number(v.trim()) : null
const inRange = (v: string, lo: number, hi: number, orZero = false) => { const n = whole(v); return n !== null && ((orZero && n === 0) || (n >= lo && n <= hi)) }

/** The ranges and formats of wa_settings_save, in plain words; '' when the draft may be sent. */
export function waDraftProblem(d: WaDraft): string {
  const phone = d.phone.trim()
  if (phone !== '' && !waPhonePattern.test(phone)) return 'Nomor WA ditulis dengan kode negara, tanpa spasi atau tanda hubung: 0812… ditulis +62812….'
  if (d.enabled && phone === '') return 'Isi nomor WA Bos sebelum menyalakan WhatsApp.'
  const times = d.digestTimes.map(t => t.trim()).filter(Boolean)
  if (d.digestTimes.length > WA_DIGEST_SLOTS || times.some(t => !clock.test(t))) return 'Jam ringkasan ditulis jam dan menit, misalnya 08:00.'
  if (new Set(times).size !== times.length) return 'Ada jam ringkasan yang sama. Kosongkan yang dobel.'
  if (d.kinds.some(k => !waKinds.includes(k)) || new Set(d.kinds).size !== d.kinds.length) return 'Pilihan jenis pengingat tidak sah. Muat ulang halaman.'
  if (d.detail !== 'SUMMARY' && d.detail !== 'DETAILED') return 'Pilih isi pesan: Ringkas atau Rinci.'
  if (!inRange(d.repeatMinutes, 60, 10080, true)) return 'Ulangan pesan: isi 0 (tidak diulang) atau 60 sampai 10.080 menit.'
  if (!inRange(d.burstAfterPerDay, 1, 200)) return 'Batas pesan sehari: isi 1 sampai 200.'
  if (!inRange(d.burstMergeMinutes, 5, 240)) return 'Jeda pesan gabungan: isi 5 sampai 240 menit.'
  if (!inRange(d.maxItems, 1, 20)) return 'Baris per jenis dalam satu pesan: isi 1 sampai 20.'
  if (!clock.test(d.quietStart) || !clock.test(d.quietEnd)) return 'Jam tenang ditulis jam dan menit, misalnya 21:00 dan 06:00.'
  if (d.quietStart === d.quietEnd) return 'Jam tenang mulai dan selesai tidak boleh sama.'
  if (!inRange(d.analysisEveryMinutes, 15, 1440, true)) return 'Analisis otomatis: isi 0 (mati) atau 15 sampai 1.440 menit.'
  if (!clock.test(d.analysisStart) || !clock.test(d.analysisEnd)) return 'Jam analisis ditulis jam dan menit, misalnya 07:00 dan 20:00.'
  if (d.analysisStart >= d.analysisEnd) return 'Jam analisis: jam mulai harus lebih awal dari jam selesai, di hari yang sama.'
  return ''
}

/** The server refuses to switch WhatsApp on without a number and a stored key (CP7_WA_ENABLE_NEEDS_PHONE_AND_KEY). */
export function waEnableProblem(d: WaDraft, keyPresent: boolean): string {
  return d.enabled && !keyPresent ? 'Simpan kunci CallMeBot dulu sebelum menyalakan WhatsApp.' : ''
}

/** The exact payload of erp_cp7_save_wa_settings_v1: the settings keys minus revision/saved_at, plus expected_revision. */
export function waSettingsPayload(d: WaDraft, expectedRevision: number): Json {
  if (waDraftProblem(d) || !Number.isSafeInteger(expectedRevision) || expectedRevision < 0) fail('isian')
  return { expected_revision: expectedRevision, enabled: d.enabled, phone_e164: d.phone.trim() === '' ? null : d.phone.trim(), detail: d.detail,
    digest_times: d.digestTimes.map(t => t.trim()).filter(Boolean).sort(), kinds: waKinds.filter(k => d.kinds.includes(k)),
    repeat_minutes: whole(d.repeatMinutes)!, burst_after_per_day: whole(d.burstAfterPerDay)!, burst_merge_minutes: whole(d.burstMergeMinutes)!,
    max_items: whole(d.maxItems)!, quiet_enabled: d.quietEnabled, quiet_start: d.quietStart, quiet_end: d.quietEnd,
    analysis_every_minutes: whole(d.analysisEveryMinutes)!, analysis_start: d.analysisStart, analysis_end: d.analysisEnd }
}

// ----------------------------------------------------------- write answers --
/** erp_cp7_save_wa_settings_v1: a replay answers the settings of the first request, which carried the same payload. */
export function parseWaSaveResult(value: unknown, payload: Json): WaSaveResult {
  const o = obj(value, 'hasil simpan'); keys(o, ['replay', 'settings'], 'hasil simpan')
  const p = obj(payload, 'hasil simpan'), s = settings(o.settings, 'hasil simpan')
  const sorted = (v: unknown) => JSON.stringify([...arr(v, 'hasil simpan')].map(x => String(x)).sort())
  if (s.revision !== Number(p.expected_revision) + 1 || s.enabled !== p.enabled || s.phone !== p.phone_e164 || s.detail !== p.detail
    || sorted(s.digestTimes) !== sorted(p.digest_times) || sorted(s.kinds) !== sorted(p.kinds) || s.repeatMinutes !== p.repeat_minutes
    || s.burstAfterPerDay !== p.burst_after_per_day || s.burstMergeMinutes !== p.burst_merge_minutes || s.maxItems !== p.max_items
    || s.quietEnabled !== p.quiet_enabled || s.quietStart !== p.quiet_start || s.quietEnd !== p.quiet_end
    || s.analysisEveryMinutes !== p.analysis_every_minutes || s.analysisStart !== p.analysis_start || s.analysisEnd !== p.analysis_end) fail('hasil simpan')
  return { replay: bool(o.replay, 'hasil simpan'), settings: s }
}

export function parseWaKeyResult(value: unknown): WaKeyResult {
  const o = obj(value, 'hasil kunci'); keys(o, ['replay', 'key_present', 'key_set_at'], 'hasil kunci')
  const r = { replay: bool(o.replay, 'hasil kunci'), keyPresent: bool(o.key_present, 'hasil kunci'), keySetAt: instant(o.key_set_at, 'hasil kunci') }
  if (!r.replay && !r.keyPresent) fail('hasil kunci')
  return r
}

export function parseWaTestResult(value: unknown): WaTestResult {
  const o = obj(value, 'hasil pesan uji'); keys(o, ['replay', 'dispatch_id', 'status'], 'hasil pesan uji')
  const r = { replay: bool(o.replay, 'hasil pesan uji'), dispatchId: positive(o.dispatch_id, 'hasil pesan uji'), status: oneOf(o.status, dispatchStatuses, 'hasil pesan uji') }
  if ((!r.replay && r.status !== 'QUEUED') || r.status === 'NOTHING_DUE') fail('hasil pesan uji')
  return r
}

export function waResolvePayload(dispatchId: number, outcome: DispatchOutcome): Json {
  if (!Number.isSafeInteger(dispatchId) || dispatchId < 1 || (outcome !== 'DELIVERED' && outcome !== 'NOT_DELIVERED')) fail('pilihan')
  return { dispatch_id: dispatchId, outcome }
}

export function parseWaResolveResult(value: unknown, payload: Json): WaResolveResult {
  const o = obj(value, 'hasil tanda'); keys(o, ['replay', 'dispatch_id', 'resolved_outcome'], 'hasil tanda')
  const p = obj(payload, 'hasil tanda')
  const r = { replay: bool(o.replay, 'hasil tanda'), dispatchId: positive(o.dispatch_id, 'hasil tanda'),
    outcome: oneOf(o.resolved_outcome, ['DELIVERED', 'NOT_DELIVERED'] as const, 'hasil tanda') }
  if (r.dispatchId !== p.dispatch_id || r.outcome !== p.outcome) fail('hasil tanda')
  return r
}
