import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// Owner D15-5 (FABLE-011): the official cutover date (WIB) the owner sets in the app. Closed parsers for
// scripts/cp7-src/cutover/cutover.sql. The server refuses operational rows dated before it; the screen only shows and sets it.
export type CutoverVersion = { version: number; cutoverDate: string; previousDate: string | null; reason: string; setAt: string; setBy: string }
export type CutoverWorkspace = {
  today: string; canSet: boolean; version: number; current: CutoverVersion | null; history: CutoverVersion[]
  earliestOperational: { date: string; kind: string; sourceType: string } | null
  earliestImport: { date: string; batchCode: string } | null
  latestAllowed: string | null
}
export type CutoverOutcome = { version: number; cutoverDate: string; previousDate: string | null }

const day = /^\d{4}-\d{2}-\d{2}$/
function fail(what: string): never { throw new Error(`Respons tanggal mulai pakai aplikasi tidak cocok (${what}).`) }
type Obj = Record<string, unknown>
const obj = (v: unknown, what: string): Obj => Boolean(v) && typeof v === 'object' && !Array.isArray(v) ? v as Obj : fail(what)
const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
const date = (v: unknown, what: string) => typeof v === 'string' && day.test(v) ? v : fail(what)
const int = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
function keys(o: Obj, expected: string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}

function version(v: unknown): CutoverVersion {
  const o = obj(v, 'versi'); keys(o, ['version', 'cutover_date', 'previous_date', 'reason', 'set_at', 'set_by'], 'versi')
  return { version: int(o.version, 'versi'), cutoverDate: date(o.cutover_date, 'tanggal'),
    previousDate: o.previous_date === null ? null : date(o.previous_date, 'tanggal lama'), reason: str(o.reason, 'alasan'),
    setAt: str(o.set_at, 'waktu'), setBy: str(o.set_by, 'pengubah') }
}

export function parseCutoverWorkspace(value: unknown): CutoverWorkspace {
  const w = obj(value, 'ruang kerja')
  keys(w, ['contract_version', 'today', 'can_set', 'version', 'current', 'history', 'earliest_operational', 'earliest_import', 'latest_allowed', 'business_DML'], 'ruang kerja')
  if (w.contract_version !== 'cp7.cutover-workspace.v1' || w.business_DML !== false || typeof w.can_set !== 'boolean') fail('kontrak')
  const current = w.current === null ? null : version(w.current)
  const history = Array.isArray(w.history) ? w.history.map(version) : fail('riwayat')
  const v = int(w.version, 'versi')
  if ((v === 0) !== (current === null) || (current && (current.version !== v || history[0]?.version !== v))) fail('versi')
  let earliestOperational: CutoverWorkspace['earliestOperational'] = null, earliestImport: CutoverWorkspace['earliestImport'] = null
  if (w.earliest_operational !== null) {
    const e = obj(w.earliest_operational, 'transaksi'); keys(e, ['date', 'kind', 'source_type'], 'transaksi')
    earliestOperational = { date: date(e.date, 'transaksi'), kind: str(e.kind, 'jenis'), sourceType: str(e.source_type, 'sumber') }
  }
  if (w.earliest_import !== null) {
    const e = obj(w.earliest_import, 'impor'); keys(e, ['date', 'batch_code'], 'impor')
    earliestImport = { date: date(e.date, 'impor'), batchCode: str(e.batch_code, 'kode impor') }
  }
  const latestAllowed = w.latest_allowed === null ? null : date(w.latest_allowed, 'batas')
  const least = [earliestOperational?.date, earliestImport?.date].filter((d): d is string => Boolean(d)).sort()[0] ?? null
  if (latestAllowed !== least) fail('batas')
  return { today: date(w.today, 'hari ini'), canSet: w.can_set, version: v, current, history, earliestOperational, earliestImport, latestAllowed }
}

export function cutoverPayload(expectedVersion: number, cutoverDate: string, reason: string): Json {
  if (!day.test(cutoverDate)) fail('tanggal')
  if (reason.trim().length < 5) fail('alasan')
  return { action: 'SET', expected_version: expectedVersion, cutover_date: cutoverDate, reason: reason.trim() }
}

export function validateCutoverOutcome(value: unknown, envelope: ProductionEnvelope): CutoverOutcome {
  const o = obj(value, 'hasil')
  keys(o, ['contract_version', 'kind', 'action', 'request_id', 'version', 'cutover_date', 'previous_date'], 'hasil')
  const payload = obj(envelope.payload, 'permintaan')
  if (o.contract_version !== 'cp7.cutover-outcome.v1' || o.kind !== 'COMMITTED_OUTCOME' || o.action !== 'SET' || envelope.action !== 'SET'
    || o.request_id !== envelope.id || o.cutover_date !== payload.cutover_date || o.version !== Number(payload.expected_version) + 1) fail('hasil')
  return { version: int(o.version, 'versi'), cutoverDate: date(o.cutover_date, 'tanggal'), previousDate: o.previous_date === null ? null : date(o.previous_date, 'tanggal lama') }
}
