import type {SalesRead} from './salesReadContract'

export type CreditDependencySource = Pick<NonNullable<SalesRead['detail']>, 'id'|'number'|'status'|'row_version'|'review_token'>
export type CreditDependency = {
  event_id: string; kind: 'REFUND'|'APPLY'; amount: string
  economic_date: string; book_date: string
  source_sale_id: string; source_sale_number: string
  source_return_id: string; source_return_number: string
  target_sale: {id: string; number: string}|null; journal_id: string
}
export type SalesCreditDependencies = {
  contract_version: 'cp7.sales-credit-dependencies.v1'; actor_scope_id: string
  read_at: string; read_only: true; business_DML: false
  source: {sale_id: string; number: string; status: string; row_version: string; review_token: string}
  dependency_sha256: string
  page: {offset: number; limit: 25; total: string; next_offset: number|null}
  dependencies: CreditDependency[]
}

const fail = (): never => {throw Error('Hubungan saldo kredit belum lengkap atau sumber invoice berubah. Muat ulang invoice dan periksa kembali.')}
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const label = (v: unknown): v is string => typeof v === 'string' && v.trim().length > 0 && v.length <= 256
const money = (v: unknown): v is string => typeof v === 'string' && /^(0|[1-9][0-9]*)\.\d{2}$/.test(v) && v !== '0.00'
const day = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10) === v
function object(v: unknown, keys: readonly string[]): Record<string,unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return fail()
  const row = v as Record<string,unknown>
  if (Object.keys(row).length !== keys.length || keys.some(k => !Object.hasOwn(row,k))) fail()
  return row
}

/** Strict display protocol; financial eligibility and money stay on the server. */
export function parseSalesCreditDependencies(v: unknown, source: CreditDependencySource, actor: string, offset = 0): SalesCreditDependencies {
  const r = object(v,['contract_version','actor_scope_id','read_at','read_only','business_DML','source','dependency_sha256','page','dependencies'])
  const s = object(r.source,['sale_id','number','status','row_version','review_token'])
  const page = object(r.page,['offset','limit','total','next_offset'])
  if (!uuid(source.id) || !uuid(actor) || typeof source.review_token !== 'string' || !/^[0-9a-f]{32}$/.test(source.review_token)
    || !Number.isSafeInteger(offset) || offset < 0 || offset > 1000000 || offset % 25 !== 0
    || r.contract_version !== 'cp7.sales-credit-dependencies.v1' || r.actor_scope_id !== actor
    || r.read_only !== true || r.business_DML !== false || s.sale_id !== source.id
    || s.number !== source.number || s.status !== source.status || s.row_version !== source.row_version || s.review_token !== source.review_token
    || typeof r.read_at !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(r.read_at) || !Number.isFinite(Date.parse(r.read_at))
    || typeof r.dependency_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(r.dependency_sha256)
    || page.offset !== offset || page.limit !== 25 || typeof page.total !== 'string' || !/^(0|[1-9][0-9]{0,18})$/.test(page.total)
    || BigInt(page.total) > 9223372036854775807n || !Array.isArray(r.dependencies)) fail()
  const remaining = BigInt(page.total as string)-BigInt(offset)
  const expectedRows = remaining <= 0n ? 0 : remaining >= 25n ? 25 : Number(remaining)
  if ((r.dependencies as unknown[]).length !== expectedRows
    || page.next_offset !== (BigInt(offset+expectedRows) < BigInt(page.total as string) ? offset+25 : null)) fail()
  const seen = new Set<string>()
  for (const value of r.dependencies as unknown[]) {
    const row = object(value,['event_id','kind','amount','economic_date','book_date','source_sale_id','source_sale_number','source_return_id','source_return_number','target_sale','journal_id'])
    if (!uuid(row.event_id) || seen.has(row.event_id.toLowerCase()) || !['REFUND','APPLY'].includes(String(row.kind)) || !money(row.amount)
      || !day(row.economic_date) || !day(row.book_date) || row.book_date < row.economic_date
      || !uuid(row.source_sale_id) || !label(row.source_sale_number) || !uuid(row.source_return_id) || !label(row.source_return_number) || !uuid(row.journal_id)) fail()
    seen.add((row.event_id as string).toLowerCase())
    if (row.kind === 'REFUND') {if (row.target_sale !== null) fail()}
    else {
      const target = object(row.target_sale,['id','number'])
      if (!uuid(target.id) || !label(target.number)) fail()
    }
  }
  return r as unknown as SalesCreditDependencies
}
