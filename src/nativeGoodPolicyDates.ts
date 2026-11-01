export type GoodPolicyEvent = {
  id: string; version: string; status: 'SET' | 'PENDING_POLICY_VALUE'
  recorded_at: string; reason: string; categories: { id: string; name: string }[]
}
export type GoodPolicyVersion = {
  id: string; effective_from: string; source_event: GoodPolicyEvent; reason: string; recorded_at: string
}
export type GoodPolicyPage = { beforeVersion: string | null; beforeDate: string | null }
export type GoodPolicyDates = {
  actor: string; access_epoch: string; can_write: boolean; timeline_token: string
  current_source: GoodPolicyEvent; current_source_registered: boolean
  source_events: GoodPolicyEvent[]; source_has_more: boolean; next_source_before: string | null
  versions: GoodPolicyVersion[]; version_has_more: boolean; next_version_before: string | null
}
export type GoodDatePayload = {
  contract_version: 'cp7.good-policy-date-command.v1'; actor: string; access_epoch: string
  effective_from: string; source_event_id: string; expected_current_version: string
  expected_timeline: string; reason: string; reviewed: true
}
export type PreparedGoodDate = {
  requestId: string; actor: string; payload: GoodDatePayload; sourceEvent: GoodPolicyEvent
}
export type GoodDateOutcome = {
  status: 'SAVED' | 'CANCELLED'; id: string | null; effective_from: string; source_version: string | null
}
type Obj = Record<string, unknown>
const firstPage: GoodPolicyPage = { beforeVersion: null, beforeDate: null }
function fail(): never { throw Error('Tanggal berlaku GOOD belum dapat dipastikan. Baca ulang versi dan periksa permintaan tersimpan.') }
const obj = (value: unknown): Obj => value && typeof value === 'object' && !Array.isArray(value) ? value as Obj : fail()
const exact = (value: Obj, fields: readonly string[]) => {
  if (Object.keys(value).sort().join('|') !== [...fields].sort().join('|')) fail()
}
const uuid = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value) ? value : fail()
const hash = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value) ? value : fail()
const text = (value: unknown) => typeof value === 'string' && value.trim() ? value : fail()
const bool = (value: unknown) => typeof value === 'boolean' ? value : fail()
const version = (value: unknown) => typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value)
  && BigInt(value) <= 9223372036854775807n ? value : fail()
const reason = (value: unknown) => typeof value === 'string' && value === value.trim()
  && Array.from(value).length > 0 && Array.from(value).length <= 1000 ? value : fail()
export function goodPolicyDate(value: unknown): string {
  if (typeof value !== 'string' || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) || value.startsWith('0000')) fail()
  const instant = Date.parse(value + 'T00:00:00Z')
  if (!Number.isFinite(instant) || new Date(instant).toISOString().slice(0, 10) !== value) fail()
  return value
}
function stamp(value: unknown): string {
  if (typeof value !== 'string' || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$/.test(value)) fail()
  goodPolicyDate(value.slice(0, 10))
  const time = Date.parse(value)
  if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 19) !== value.slice(0, 19)) fail()
  return value
}
function event(value: unknown): GoodPolicyEvent {
  const row = obj(value)
  exact(row, ['id', 'version', 'status', 'recorded_at', 'reason', 'categories'])
  if ((row.status !== 'SET' && row.status !== 'PENDING_POLICY_VALUE') || !Array.isArray(row.categories) || row.categories.length > 50) fail()
  const categories = row.categories.map(value => {
    const category = obj(value); exact(category, ['id', 'name'])
    return { id: uuid(category.id), name: text(category.name) }
  })
  if (new Set(categories.map(c => c.id)).size !== categories.length
    || row.status === 'PENDING_POLICY_VALUE' && categories.length !== 0) fail()
  return { id: uuid(row.id), version: version(row.version), status: row.status as GoodPolicyEvent['status'],
    recorded_at: stamp(row.recorded_at), reason: text(row.reason), categories }
}
function policyVersion(value: unknown): GoodPolicyVersion {
  const row = obj(value); exact(row, ['id', 'effective_from', 'source_event', 'reason', 'recorded_at'])
  return { id: uuid(row.id), effective_from: goodPolicyDate(row.effective_from), source_event: event(row.source_event),
    reason: reason(row.reason), recorded_at: stamp(row.recorded_at) }
}
function page(value: GoodPolicyPage): GoodPolicyPage {
  return { beforeVersion: value.beforeVersion === null ? null : version(value.beforeVersion),
    beforeDate: value.beforeDate === null ? null : goodPolicyDate(value.beforeDate) }
}
export function parseGoodPolicyDates(value: unknown, actor: string, cursor = firstPage): GoodPolicyDates {
  const w = obj(value), requested = page(cursor)
  exact(w, ['contract_version', 'actor', 'access_epoch', 'can_write', 'timeline_token', 'current_source',
    'current_source_registered', 'source_events', 'source_has_more', 'next_source_before', 'versions', 'version_has_more', 'next_version_before'])
  if (w.contract_version !== 'cp7.good-policy-date-workspace.v1' || uuid(w.actor) !== uuid(actor)
    || !Array.isArray(w.source_events) || w.source_events.length > 30 || !Array.isArray(w.versions) || w.versions.length > 30) fail()
  const current = event(w.current_source), sources = w.source_events.map(event), versions = w.versions.map(policyVersion)
  if (new Set(sources.map(e => e.id)).size !== sources.length || new Set(sources.map(e => e.version)).size !== sources.length
    || new Set(versions.map(v => v.id)).size !== versions.length || new Set(versions.map(v => v.effective_from)).size !== versions.length) fail()
  if (sources.some((e, i) => BigInt(e.version) > BigInt(current.version)
    || i > 0 && BigInt(e.version) >= BigInt(sources[i - 1].version)
    || requested.beforeVersion !== null && BigInt(e.version) >= BigInt(requested.beforeVersion))) fail()
  if (versions.some((v, i) => BigInt(v.source_event.version) > BigInt(current.version)
    || i > 0 && v.effective_from >= versions[i - 1].effective_from
    || requested.beforeDate !== null && v.effective_from >= requested.beforeDate)) fail()
  const sourceMore = bool(w.source_has_more), versionMore = bool(w.version_has_more)
  const sourceBefore = w.next_source_before === null ? null : version(w.next_source_before)
  const versionBefore = w.next_version_before === null ? null : goodPolicyDate(w.next_version_before)
  if (sourceMore ? sources.length !== 30 || sourceBefore !== sources.at(-1)?.version : sourceBefore !== null) fail()
  if (versionMore ? versions.length !== 30 || versionBefore !== versions.at(-1)?.effective_from : versionBefore !== null) fail()
  const registered = bool(w.current_source_registered)
  if (!registered && versions.some(v => v.source_event.id === current.id)) fail()
  return { actor, access_epoch: hash(w.access_epoch), can_write: bool(w.can_write), timeline_token: hash(w.timeline_token),
    current_source: current, current_source_registered: registered, source_events: sources, source_has_more: sourceMore,
    next_source_before: sourceBefore, versions, version_has_more: versionMore, next_version_before: versionBefore }
}
export function parsePreparedGoodDate(value: unknown, actor: string): PreparedGoodDate {
  const row = obj(value); exact(row, ['requestId', 'actor', 'payload', 'sourceEvent'])
  const p = obj(row.payload), source = event(row.sourceEvent)
  exact(p, ['contract_version', 'actor', 'access_epoch', 'effective_from', 'source_event_id', 'expected_current_version', 'expected_timeline', 'reason', 'reviewed'])
  if (uuid(row.actor) !== uuid(actor) || uuid(p.actor) !== actor || p.contract_version !== 'cp7.good-policy-date-command.v1'
    || p.reviewed !== true || uuid(p.source_event_id) !== source.id || BigInt(source.version) > BigInt(version(p.expected_current_version))) fail()
  uuid(row.requestId); hash(p.access_epoch); hash(p.expected_timeline); goodPolicyDate(p.effective_from); reason(p.reason)
  return structuredClone(row) as PreparedGoodDate
}
export function prepareGoodPolicyDate(w: GoodPolicyDates, sourceId: string, day: string, explanation: string,
  reviewed: boolean, requestId: string): PreparedGoodDate {
  const source = [w.current_source, ...w.source_events].find(e => e.id === sourceId)
  if (!w.can_write || !reviewed || !source) fail()
  return parsePreparedGoodDate({ requestId, actor: w.actor, sourceEvent: source,
    payload: { contract_version: 'cp7.good-policy-date-command.v1', actor: w.actor, access_epoch: w.access_epoch,
      effective_from: goodPolicyDate(day), source_event_id: source.id, expected_current_version: w.current_source.version,
      expected_timeline: w.timeline_token, reason: reason(explanation.trim()), reviewed: true } }, w.actor)
}
export function parseGoodDateOutcome(value: unknown, command: PreparedGoodDate): GoodDateOutcome {
  parsePreparedGoodDate(command, command.actor)
  const row = obj(value), p = command.payload
  exact(row, ['contract_version', 'request_id', 'actor', 'effective_from', 'id', 'source_event_id', 'source_version', 'reason', 'status'])
  if (row.contract_version !== 'cp7.good-policy-date-outcome.v1' || row.request_id !== command.requestId || row.actor !== command.actor
    || row.effective_from !== p.effective_from || row.source_event_id !== p.source_event_id || row.reason !== p.reason) fail()
  if (row.status === 'SAVED') {
    if (version(row.source_version) !== command.sourceEvent.version) fail()
    return { status: 'SAVED', id: uuid(row.id), effective_from: goodPolicyDate(row.effective_from), source_version: row.source_version as string }
  }
  if (row.status !== 'CANCELLED' || row.id !== null || row.source_version !== null) fail()
  return { status: 'CANCELLED', id: null, effective_from: goodPolicyDate(row.effective_from), source_version: null }
}
type Reply = { data: unknown; error: unknown }
type Client = {
  rpc(name: 'erp_cp7_get_good_policy_dates_v1', args: { p_payload: { before_version: string | null; before_date: string | null } }): PromiseLike<Reply>
  rpc(name: 'erp_cp7_save_good_policy_date_v1', args: { p_payload: GoodDatePayload; p_request: string; p_cancel: boolean }): PromiseLike<Reply>
}
export async function readGoodPolicyDates(client: unknown, actor: string, cursor = firstPage): Promise<GoodPolicyDates> {
  const p = page(cursor), r = await (client as Client).rpc('erp_cp7_get_good_policy_dates_v1', {
    p_payload: { before_version: p.beforeVersion, before_date: p.beforeDate } })
  if (r.error) throw r.error
  return parseGoodPolicyDates(r.data, actor, p)
}
export async function saveGoodPolicyDate(client: unknown, command: PreparedGoodDate, cancel = false): Promise<GoodDateOutcome> {
  parsePreparedGoodDate(command, command.actor)
  const r = await (client as Client).rpc('erp_cp7_save_good_policy_date_v1', {
    p_payload: structuredClone(command.payload), p_request: command.requestId, p_cancel: cancel })
  if (r.error) throw r.error
  return parseGoodDateOutcome(r.data, command)
}
const canonical = (value: unknown): string => JSON.stringify(value, (_key, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item)
export const goodPolicyDateRequestKey = (scope: string) => 'erp.cp7.good-policy-date.v1:' + scope
export function readGoodDateRequest(scope: string, actor: string): { pending: PreparedGoodDate | null; error: string } {
  try {
    const raw = localStorage.getItem(goodPolicyDateRequestKey(scope))
    return { pending: raw === null ? null : parsePreparedGoodDate(JSON.parse(raw), actor), error: '' }
  } catch { return { pending: null, error: 'Catatan tanggal berlaku belum terbaca. Pulihkan catatan sebelum menyimpan lagi.' } }
}
export function persistGoodDateRequest(scope: string, command: PreparedGoodDate): void {
  parsePreparedGoodDate(command, command.actor)
  const held = readGoodDateRequest(scope, command.actor)
  if (held.error || held.pending) throw Error('Periksa permintaan tanggal berlaku sebelumnya terlebih dahulu.')
  const key = goodPolicyDateRequestKey(scope), raw = JSON.stringify(command)
  localStorage.setItem(key, raw)
  if (localStorage.getItem(key) !== raw) throw Error('Permintaan belum tercatat di perangkat. Penyimpanan belum dikirim.')
}
export function clearGoodDateRequest(scope: string, command: PreparedGoodDate): void {
  const held = readGoodDateRequest(scope, command.actor)
  if (held.error || canonical(held.pending) !== canonical(command)) throw Error('Catatan permintaan berubah. Periksa permintaan yang sama.')
  const key = goodPolicyDateRequestKey(scope)
  localStorage.removeItem(key)
  if (localStorage.getItem(key) !== null) throw Error('Catatan permintaan belum dapat diselesaikan.')
}
export function goodDateRefusalText(message: string): string {
  if (/NONPAYABLE_POSTED_GOOD_/.test(message)) return 'Tanggal ini memengaruhi GOOD yang sudah dicatat. Koreksi atau balik hasil terkait melalui alur yang sah sebelum mengubah dasar kebijakannya.'
  if (/NONPAYABLE_(CURRENT_SOURCE_STALE|TIMELINE_STALE|SETTINGS_ACCESS_CHANGED)/.test(message)) return 'Versi kategori, tanggal berlaku, atau hak akses berubah. Baca ulang dan tinjau kembali sebelum menyimpan.'
  if (/NONPAYABLE_EFFECTIVE_DATE_ALREADY_RECORDED/.test(message)) return 'Tanggal berlaku tersebut sudah tercatat. Periksa riwayat; tanggal dan hasil lama tetap dipertahankan.'
  if (/NONPAYABLE_(SETTINGS_DENIED|OWNER_DATE_REQUIRED)/.test(message)) return 'Hanya owner dengan hak mengelola pengaturan dan melihat aksesori yang dapat mencatat tanggal berlaku.'
  if (/NONPAYABLE_DATE_REQUEST_INTENT_CHANGED/.test(message)) return 'Permintaan ini berbeda dari catatan sebelumnya. Pertahankan nomor dan isi permintaan lama untuk memastikan hasilnya.'
  return message
}
