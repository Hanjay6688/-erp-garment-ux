import { sourceId, type SourceReference } from './transactionSource'

export type QcDependency = { source_type: 'QC_INSPECTION'; source_id: string; number: string; status: string; revision: string }
export type TransactionDependencies = {
  parent: { id: string; number: string; status: string; revision: string }
  page: { offset: number; limit: 25; total: number; has_more: boolean }
  dependencies: QcDependency[]
  readAt: string
}
const fail = (): never => { throw Error('Hubungan QC belum sesuai penerimaan dan akses saat ini. Muat ulang data.') }
function object(v: unknown, keys: string[]) {
  if (!v || typeof v !== 'object' || Array.isArray(v) || Object.keys(v).sort().join('|') !== [...keys].sort().join('|')) fail()
  return v as Record<string, unknown>
}
const label = (v: unknown): v is string => typeof v === 'string' && !!v.trim() && v.length <= 256
const status = (v: unknown): v is string => typeof v === 'string' && /^[A-Z][A-Z0-9_]{0,39}$/.test(v)
const revision = (v: unknown): v is string => typeof v === 'string' && /^[1-9][0-9]{0,18}$/.test(v) && BigInt(v) <= 9223372036854775807n
export function parseTransactionDependencies(v: unknown, source: SourceReference, actor: string, offset: number): TransactionDependencies {
  const e = object(v, ['contract_version', 'actor_scope_id', 'source', 'parent', 'page', 'dependencies', 'read_at', 'business_DML'])
  const s = object(e.source, ['source_type', 'source_id']), h = object(e.parent, ['id', 'number', 'status', 'revision'])
  const p = object(e.page, ['offset', 'limit', 'total', 'has_more'])
  if (source.source_type !== 'LAUNDRY_RECEIPT' || !sourceId(source.source_id) || !Number.isSafeInteger(offset) || offset < 0 || offset > 1000000 || offset % 25 !== 0
    || e.contract_version !== 'cp7.transaction-dependencies.v1' || e.actor_scope_id !== actor || e.business_DML !== false
    || s.source_type !== source.source_type || s.source_id !== source.source_id || h.id !== source.source_id
    || !label(h.number) || !status(h.status) || !revision(h.revision)
    || p.offset !== offset || p.limit !== 25 || !Number.isSafeInteger(p.total) || Number(p.total) < 0 || typeof p.has_more !== 'boolean'
    || !Array.isArray(e.dependencies) || e.dependencies.length !== Math.min(25, Math.max(0, Number(p.total) - offset))
    || p.has_more !== (offset + e.dependencies.length < Number(p.total))
    || typeof e.read_at !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(e.read_at) || !Number.isFinite(Date.parse(e.read_at))) fail()
  const seen = new Set<string>()
  const dependencies = (e.dependencies as unknown[]).map(raw => {
    const d = object(raw, ['source_type', 'source_id', 'number', 'status', 'revision'])
    if (d.source_type !== 'QC_INSPECTION' || !sourceId(d.source_id) || seen.has(d.source_id) || !label(d.number) || !status(d.status) || d.status === 'REVERSED' || !revision(d.revision)) fail()
    seen.add(d.source_id as string)
    return { ...d } as QcDependency
  })
  return { parent: { ...h } as TransactionDependencies['parent'], page: { ...p } as TransactionDependencies['page'], dependencies, readAt: e.read_at as string }
}
