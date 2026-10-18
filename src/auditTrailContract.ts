// R3-03 (owner D16-1): the connected Audit Trail screen. A closed parser for the answer of
// public.erp_cp7_get_audit_trail_v1 (scripts/cp7-src/audit/audit.sql) and the CSV of the rows shown.
export type AuditQuery = { from: string | null; to: string | null; entity_type: string | null; action: string | null; actor_id: string | null; q: string | null }
// as_of fixes the listing's cutoff; listed is the mark of its rows inside the cutoff (the first page's), and the keyset cursor
// (after / next_after) is '<last row id>:<listed>' (ASTRA-R3-02: a lower id committed late inside the cutoff is told, not skipped).
export type AuditRequest = AuditQuery & { as_of: string | null; after: string | null; listed: string | null; id: string | null; offset: number; limit: number }
export type AuditRow = {
  id: string; at: string | null; entityType: string | null; entityId: string | null; action: string | null
  actorId: string | null; actorName: string | null; reason: string | null; changedKeys: string[]; changedKeyCount: number
  hasBefore: boolean; hasAfter: boolean
}
export type AuditField = { key: string; before: string | null; after: string | null; changed: boolean }
export type AuditDetail = AuditRow & { dataBytes: number; tooLarge: boolean; fields: AuditField[]; fieldsTotal: number; rawBefore: string | null; rawAfter: string | null }
export type AuditActor = { id: string; name: string | null }
export type AuditTrail = {
  readAt: string; canExport: boolean; query: AuditQuery; asOf: string; newer: boolean; listed: string; changed: boolean
  page: { rows: AuditRow[]; total: bigint; before: bigint; offset: number; limit: number; after: string | null; nextAfter: string | null; nextOffset: number | null }
  options: { entityTypes: string[]; actions: string[]; actors: AuditActor[] }
  detail: AuditDetail | null
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const logId = /^[1-9][0-9]{0,17}$/
const whole = /^(0|[1-9][0-9]{0,18})$/
const day = /^\d{4}-\d{2}-\d{2}$/
const mark = /^\d{1,18}-\d{1,40}$/
const cursor = /^([1-9][0-9]{0,17}):(\d{1,18}-\d{1,40})$/
function fail(): never { throw new Error('Jawaban jejak audit tidak cocok dengan permintaan. Tekan Muat ulang.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function closed(value: unknown, expected: string[]) {
  const r = record(value)
  if (Object.keys(r).sort().join('|') !== [...expected].sort().join('|')) fail()
  return r
}
function text(value: unknown) { if (typeof value !== 'string' || value === '') fail(); return value }
function nullableText(value: unknown) { if (value === null) return null; if (typeof value !== 'string') fail(); return value }
function bool(value: unknown) { if (typeof value !== 'boolean') fail(); return value }
function count(value: unknown) { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) fail(); return value }
function big(value: unknown) { if (typeof value !== 'string' || !whole.test(value)) fail(); return BigInt(value) }
function id(value: unknown) { if (typeof value !== 'string' || !logId.test(value)) fail(); return value }
function nullableUuid(value: unknown) { if (value === null) return null; if (typeof value !== 'string' || !uuid.test(value)) fail(); return value }
function strings(value: unknown, max: number) {
  if (!Array.isArray(value) || value.length > max) fail()
  const out = value.map(text)
  if (new Set(out).size !== out.length) fail()
  return out
}
// Microseconds since the epoch of a server instant (the answer keeps six fraction digits; Date keeps three).
export function auditInstant(value: string) {
  const m = /^(.*?)(?:\.(\d{1,6}))?([+-]\d{2}:\d{2}|Z)$/.exec(value)
  if (!m) fail()
  const ms = Date.parse(m[1] + m[3])
  if (!Number.isFinite(ms)) fail()
  return BigInt(ms) * 1000n + BigInt((m[2] ?? '').padEnd(6, '0'))
}
// The WIB calendar day of an instant (Asia/Jakarta has no daylight saving time).
export function auditWibDay(value: string) {
  return new Date(Number(auditInstant(value) / 1000n) + 7 * 3600 * 1000).toISOString().slice(0, 10)
}

const ROW = ['id', 'at', 'entity_type', 'entity_id', 'action', 'actor_id', 'actor_name', 'reason', 'changed_keys', 'changed_key_count', 'has_before', 'has_after']
function row(value: unknown, keys = ROW): AuditRow & { raw: Record<string, unknown> } {
  const r = closed(value, keys)
  const at = r.at === null ? null : text(r.at)
  if (at !== null) auditInstant(at)
  const out = {
    id: id(r.id), at, entityType: nullableText(r.entity_type), entityId: nullableText(r.entity_id), action: nullableText(r.action),
    actorId: nullableUuid(r.actor_id), actorName: nullableText(r.actor_name), reason: nullableText(r.reason),
    changedKeys: strings(r.changed_keys, 30), changedKeyCount: count(r.changed_key_count), hasBefore: bool(r.has_before), hasAfter: bool(r.has_after), raw: r,
  }
  if (out.changedKeys.length > out.changedKeyCount || (out.changedKeyCount > 0 && out.changedKeys.length < Math.min(30, out.changedKeyCount))
    || (out.changedKeyCount > 0 && !out.hasBefore && !out.hasAfter) || (out.actorName !== null && out.actorId === null)) fail()
  return out
}
function strip<T extends { raw: unknown }>(value: T): Omit<T, 'raw'> { const { raw: _raw, ...rest } = value; return rest }

export function auditRequestQuery(request: AuditRequest): AuditQuery {
  const q = request.q?.trim() ?? ''
  return { from: request.from || null, to: request.to || null, entity_type: request.entity_type || null, action: request.action || null,
    actor_id: request.actor_id || null, q: q === '' ? null : q }
}

export function parseAuditTrail(value: unknown, request: AuditRequest): AuditTrail {
  const r = closed(value, ['contract_version', 'read_at', 'business_DML', 'can_export', 'query', 'snapshot', 'page', 'options', 'detail'])
  if (r.contract_version !== 'cp7.audit-trail.v1' || r.business_DML !== false) fail()
  const readAt = text(r.read_at); auditInstant(readAt)
  const expected = auditRequestQuery(request)
  const q = closed(r.query, ['from', 'to', 'entity_type', 'action', 'actor_id', 'q'])
  for (const key of Object.keys(expected) as (keyof AuditQuery)[]) if (q[key] !== expected[key]) fail()
  if ((expected.from !== null && !day.test(expected.from)) || (expected.to !== null && !day.test(expected.to))) fail()
  const s = closed(r.snapshot, ['as_of', 'newer', 'listed', 'changed'])
  const asOf = typeof s.as_of === 'string' && whole.test(s.as_of) ? s.as_of : fail()
  if (request.as_of !== null && asOf !== request.as_of) fail()
  const listed = typeof s.listed === 'string' && mark.test(s.listed) ? s.listed : fail()
  if (typeof s.newer !== 'boolean' || typeof s.changed !== 'boolean' || (s.changed && !s.newer)) fail()
  if (request.listed !== null && listed !== request.listed) fail()
  if (request.after !== null && cursor.exec(request.after)?.[2] !== listed) fail()
  const p = closed(r.page, ['rows', 'total', 'before', 'offset', 'limit', 'after', 'next_after', 'next_offset'])
  if (!Array.isArray(p.rows) || p.limit !== request.limit || p.offset !== request.offset || p.after !== request.after) fail()
  const total = big(p.total), before = big(p.before), rows = p.rows.map(v => row(v))
  if (rows.length > request.limit || (request.after === null && before !== 0n)) fail()
  const seen = new Set<string>()
  rows.forEach((x, i) => {
    if (seen.has(x.id) || BigInt(x.id) > BigInt(asOf)) fail()
    seen.add(x.id)
    // Newest first: changed time, then log id, both strictly descending (a row without a time sorts last).
    if (i > 0) {
      const prev = rows[i - 1], a = prev.at === null ? null : auditInstant(prev.at), b = x.at === null ? null : auditInstant(x.at)
      const order = a === b ? 0 : a === null ? -1 : b === null ? 1 : a > b ? 1 : -1
      if (order < 0 || (order === 0 && BigInt(prev.id) <= BigInt(x.id))) fail()
    }
    // Every row shown matches the filters asked (the search text is the server's).
    if ((expected.entity_type !== null && x.entityType !== expected.entity_type) || (expected.action !== null && x.action !== expected.action)
      || (expected.actor_id !== null && x.actorId !== expected.actor_id)) fail()
    if ((expected.from !== null || expected.to !== null) && (x.at === null || (expected.from !== null && auditWibDay(x.at) < expected.from)
      || (expected.to !== null && auditWibDay(x.at) > expected.to))) fail()
  })
  const shown = before + BigInt(request.offset) + BigInt(rows.length)
  const next = p.next_after === null ? null : cursor.exec(text(p.next_after)) ?? fail()
  if (next !== null && next[2] !== listed) fail()
  const nextAfter = next === null ? null : next[0]
  const nextOffset = p.next_offset === null ? null : count(p.next_offset)
  if (nextAfter === null) {
    if (nextOffset !== null || (rows.length > 0 || request.offset === 0) && shown !== total) fail()
  } else if (rows.length !== request.limit || next![1] !== rows[rows.length - 1].id || nextOffset !== request.offset + request.limit || shown >= total) fail()
  const o = closed(r.options, ['entity_types', 'actions', 'actors'])
  if (!Array.isArray(o.actors) || o.actors.length > 200) fail()
  const actors = o.actors.map(v => { const a = closed(v, ['id', 'name']); return { id: nullableUuid(a.id) ?? fail(), name: nullableText(a.name) } })
  if (new Set(actors.map(a => a.id)).size !== actors.length) fail()
  let detail: AuditDetail | null = null
  if (request.id === null) { if (r.detail !== null) fail() }
  else {
    const d = row(r.detail, [...ROW, 'data_bytes', 'too_large', 'fields', 'fields_total', 'raw_before', 'raw_after'])
    if (d.id !== request.id || !Array.isArray(d.raw.fields) || d.raw.fields.length > 500) fail()
    const fields = d.raw.fields.map(v => {
      const f = closed(v, ['key', 'before', 'after', 'changed'])
      return { key: text(f.key), before: nullableText(f.before), after: nullableText(f.after), changed: bool(f.changed) }
    })
    const tooLarge = bool(d.raw.too_large), fieldsTotal = count(d.raw.fields_total), rawBefore = nullableText(d.raw.raw_before), rawAfter = nullableText(d.raw.raw_after)
    const changed = fields.filter(f => f.changed).length
    if (new Set(fields.map(f => f.key)).size !== fields.length || fieldsTotal < fields.length || (fieldsTotal > fields.length && fields.length < 500)
      || (tooLarge && (fields.length > 0 || fieldsTotal > 0 || rawBefore !== null || rawAfter !== null))
      || (!tooLarge && fields.length === fieldsTotal && changed !== d.changedKeyCount) || changed > d.changedKeyCount) fail()
    detail = { ...strip(d), dataBytes: count(d.raw.data_bytes), tooLarge, fields, fieldsTotal, rawBefore, rawAfter }
  }
  return {
    readAt, canExport: bool(r.can_export), query: expected, asOf, newer: bool(s.newer), listed, changed: bool(s.changed),
    page: { rows: rows.map(strip), total, before, offset: request.offset, limit: request.limit, after: request.after, nextAfter, nextOffset },
    options: { entityTypes: strings(o.entity_types, 200), actions: strings(o.actions, 200), actors },
    detail,
  }
}

// CSV of the rows shown (owner rule: the export is of what the screen shows). A cell that a spreadsheet would read as a
// formula is prefixed with an apostrophe.
export const AUDIT_CSV_HEADER = ['ID catatan', 'Waktu (WIB)', 'Pengguna', 'Jenis data', 'Nomor data', 'Aksi', 'Alasan', 'Kolom berubah']
function cell(value: string) {
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value
  return `"${safe.replace(/"/g, '""')}"`
}
export function auditCsv(rows: AuditRow[], time: (at: string | null) => string, actor: (row: AuditRow) => string) {
  const lines = [AUDIT_CSV_HEADER, ...rows.map(r => [r.id, time(r.at), actor(r), r.entityType ?? '', r.entityId ?? '', r.action ?? '', r.reason ?? '',
    r.changedKeys.join(', ') + (r.changedKeyCount > r.changedKeys.length ? ` (+${r.changedKeyCount - r.changedKeys.length})` : '')])]
  return '﻿' + lines.map(line => line.map(cell).join(',')).join('\r\n') + '\r\n'
}
