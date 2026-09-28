/** P01 boundary for the P02 diagnostic query. It cannot authorize a caller. */
type SourceValue = { state: 'UNKNOWN'; reason: string } |
  { state: 'KNOWN'; value: string; unit: 'IDR' }
type Physical = {
  product_id: string; root_id: string; size_id: string; model_id: string;
  brand_id: string; effective_from: string
}
type Commercial = { sku_id: string; version_id: string; revision: string; sku: string }
type Cutting = {
  source_key: string; yield_id: string; cutting_group_id: string; po_id: string;
  slot_id: string; size_id: string; pattern_id: string | null;
  pattern_revision: string | null; group_revision: string;
  cut_at: string; cut_qty_pcs: string; match: 'UNBOUND_CANDIDATE'
}
type Movement = {
  source_key: string; product_id: string; lot_id: string | null;
  location_id: string; quality_grade: string; qty_signed_pcs: string;
  physical_at: string; system_created_at: string; reversal_of_id: string | null
}
type SaleLine = {
  source_key: string; sale_id: string; product_id: string; status: string;
  header_revision: string; sale_date: string; created_at: string; qty_pcs: string
}
type LotCost = {
  source_key: string; lot_id: string; product_id: string;
  produced_at: string; hpp_version_id: string | null;
  hpp_revision: string | null; calculated_at: string | null;
  cost_state: string | null; valuation: SourceValue
}

type Sources = {
  physical: Physical[]; commercial: Commercial[];
  cutting_candidates: Cutting[]; stock_movements: Movement[];
  sales_lines: SaleLine[]; lot_cost: LotCost[]
}
type Domain = keyof Sources
const domains: Domain[] = ['physical', 'commercial', 'cutting_candidates', 'stock_movements', 'sales_lines', 'lot_cost']

export type SourceProbe = {
  contract_version: 'cp7.source-probe.v1'; status: 'COMPLETE';
  scope: { root_id: string; exact_size_id: string; commercial_status: 'BOUND' | 'LEGACY_UNMAPPED' };
  snapshot: {
    effective_as_of: string; known_as_of: string; generated_at: string;
    knowledge_mode: 'CURRENT'; time_zone: 'Asia/Jakarta';
    completeness_proven_only_for: 'SOURCE_PROBE_SIX_DOMAINS'
  };
  counts: Record<Domain, number>; sources: Sources; snapshot_hash: string
}

const fail = (code: string): never => { throw new Error(`CP7_SOURCE_PROBE_${code}`) }
const record = (v: unknown): Record<string, unknown> =>
  v && typeof v === 'object' && !Array.isArray(v) ? v as Record<string, unknown> : fail('SHAPE')
const exactKeys = (v: Record<string, unknown>, keys: string[]) => {
  if (Object.keys(v).length !== keys.length || keys.some(key => !Object.hasOwn(v, key))) fail('FIELDS')
}
const uuid = (v: unknown) => typeof v === 'string' && /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(v)
const id = (v: unknown) => { if (!uuid(v)) fail('IDENTITY') }
const nullableId = (v: unknown) => { if (v !== null) id(v) }
const string = (v: unknown) => { if (typeof v !== 'string' || v.trim().length === 0) fail('STRING') }
const nullableString = (v: unknown) => { if (v !== null) string(v) }
const timestamp = (v: unknown) => {
  if (typeof v !== 'string') return fail('TIMESTAMP')
  const parts = /^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?(Z|[+-]\d\d:\d\d)$/.exec(v)
  if (!parts) return fail('TIMESTAMP')
  const milliseconds = Date.parse(parts[1] + parts[3])
  if (Number.isNaN(milliseconds)) return fail('TIMESTAMP')
  return BigInt(milliseconds) * 1000n + BigInt((parts[2] ?? '').padEnd(6, '0'))
}
const nullableTimestamp = (v: unknown) => { if (v !== null) timestamp(v) }
const count = (v: unknown, signed = false) => {
  if (typeof v !== 'string' || !(signed ? /^-?(?:0|[1-9][0-9]*)$/ : /^(?:0|[1-9][0-9]*)$/).test(v)) fail('COUNT')
}
const money = (v: unknown) => {
  if (typeof v !== 'string' || !/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?$/.test(v)) fail('MONEY')
}
const fields: Record<Domain, string[]> = {
  physical: ['product_id', 'root_id', 'size_id', 'model_id', 'brand_id', 'effective_from'],
  commercial: ['sku_id', 'version_id', 'revision', 'sku'],
  cutting_candidates: ['source_key', 'yield_id', 'cutting_group_id', 'po_id', 'slot_id',
    'size_id', 'pattern_id', 'pattern_revision', 'group_revision', 'cut_at', 'cut_qty_pcs', 'match'],
  stock_movements: ['source_key', 'product_id', 'lot_id', 'location_id', 'quality_grade',
    'qty_signed_pcs', 'physical_at', 'system_created_at', 'reversal_of_id'],
  sales_lines: ['source_key', 'sale_id', 'product_id', 'status', 'header_revision',
    'sale_date', 'created_at', 'qty_pcs'],
  lot_cost: ['source_key', 'lot_id', 'product_id', 'produced_at', 'hpp_version_id',
    'hpp_revision', 'calculated_at', 'cost_state', 'valuation'],
}

function validateRow(domain: Domain, source: Record<string, unknown>, scope: SourceProbe['scope']) {
  exactKeys(source, fields[domain])
  if (domain === 'physical') {
    id(source.product_id); id(source.root_id); id(source.size_id); id(source.model_id); id(source.brand_id)
    timestamp(source.effective_from)
    if (source.root_id !== scope.root_id || source.size_id !== scope.exact_size_id) fail('PHYSICAL_SCOPE')
  } else if (domain === 'commercial') {
    id(source.sku_id); id(source.version_id); count(source.revision); string(source.sku)
  } else if (domain === 'cutting_candidates') {
    id(source.yield_id); id(source.cutting_group_id); id(source.po_id); id(source.slot_id)
    id(source.size_id); nullableId(source.pattern_id); nullableString(source.pattern_revision)
    count(source.group_revision); timestamp(source.cut_at); count(source.cut_qty_pcs)
    if (source.cut_qty_pcs === '0') fail('COUNT')
    if (source.match !== 'UNBOUND_CANDIDATE' || source.size_id !== scope.exact_size_id
      || source.source_key !== `CUTTING_YIELD:${source.yield_id}`) fail('CANDIDATE_LINEAGE')
  } else if (domain === 'stock_movements') {
    id(source.product_id); nullableId(source.lot_id); id(source.location_id)
    nullableId(source.reversal_of_id); string(source.quality_grade)
    timestamp(source.physical_at); timestamp(source.system_created_at); count(source.qty_signed_pcs, true)
    if (typeof source.source_key !== 'string' || !uuid(source.source_key.slice('FG_MOVEMENT:'.length))
      || !source.source_key.startsWith('FG_MOVEMENT:')) fail('STOCK_LINEAGE')
  } else if (domain === 'sales_lines') {
    id(source.sale_id); id(source.product_id); string(source.status)
    count(source.header_revision); count(source.qty_pcs)
    if (source.qty_pcs === '0') fail('COUNT')
    timestamp(source.sale_date); timestamp(source.created_at)
    if (typeof source.source_key !== 'string' || !uuid(source.source_key.slice('SALE_LINE:'.length))
      || !source.source_key.startsWith('SALE_LINE:')) fail('SALE_LINEAGE')
  } else {
    id(source.lot_id); id(source.product_id); nullableId(source.hpp_version_id)
    nullableString(source.hpp_revision); nullableString(source.cost_state)
    timestamp(source.produced_at); nullableTimestamp(source.calculated_at)
    if (source.source_key !== `LOT_COST:${source.lot_id}`) fail('COST_LINEAGE')
    const value = record(source.valuation)
    if (value.state === 'KNOWN') {
      exactKeys(value, ['state', 'unit', 'value'])
      if (value.unit !== 'IDR' || source.hpp_version_id === null) fail('COST_SOURCE')
      money(value.value)
    } else if (value.state === 'UNKNOWN') {
      exactKeys(value, ['state', 'reason']); string(value.reason)
    } else fail('COST_QUALITY')
  }
}

/** Shape and semantic guard for the diagnostic; server permission is separate. */
export function parseSourceProbe(value: unknown): SourceProbe {
  const raw = record(value)
  exactKeys(raw, ['contract_version', 'status', 'scope', 'snapshot', 'counts', 'sources', 'snapshot_hash'])
  if (raw.contract_version !== 'cp7.source-probe.v1' || raw.status !== 'COMPLETE') fail('INCOMPLETE')
  const scope = record(raw.scope)
  exactKeys(scope, ['root_id', 'exact_size_id', 'commercial_status'])
  id(scope.root_id); id(scope.exact_size_id)
  if (!['BOUND', 'LEGACY_UNMAPPED'].includes(scope.commercial_status as string)) fail('COMMERCIAL_STATUS')
  const snapshot = record(raw.snapshot)
  exactKeys(snapshot, ['effective_as_of', 'known_as_of', 'generated_at', 'knowledge_mode',
    'time_zone', 'completeness_proven_only_for'])
  if (snapshot.knowledge_mode !== 'CURRENT' || snapshot.time_zone !== 'Asia/Jakarta'
    || snapshot.completeness_proven_only_for !== 'SOURCE_PROBE_SIX_DOMAINS') fail('SNAPSHOT_SCOPE')
  for (const key of ['effective_as_of', 'known_as_of', 'generated_at']) timestamp(snapshot[key])
  if (snapshot.effective_as_of !== snapshot.known_as_of
    || snapshot.known_as_of !== snapshot.generated_at) fail('MIXED_CLOCKS')
  const cutoff = timestamp(snapshot.effective_as_of)
  if (typeof raw.snapshot_hash !== 'string' || !/^[a-f0-9]{64}$/.test(raw.snapshot_hash)) fail('HASH')
  const counts = record(raw.counts)
  const sources = record(raw.sources)
  exactKeys(counts, domains); exactKeys(sources, domains)
  const seen = new Set<string>()
  for (const domain of domains) {
    const rows = sources[domain]
    if (!Array.isArray(rows)) return fail('PARTIAL_PAGE')
    const expected = counts[domain]
    if (typeof expected !== 'number' || !Number.isInteger(expected)
      || expected !== rows.length || rows.length > 500) fail('PARTIAL_PAGE')
    for (const row of rows) {
      const source = record(row)
      validateRow(domain, source, scope as SourceProbe['scope'])
      const effectiveTime = domain === 'physical' ? source.effective_from
        : domain === 'cutting_candidates' ? source.cut_at
          : domain === 'stock_movements' ? source.physical_at
            : domain === 'sales_lines' ? source.sale_date
              : domain === 'lot_cost' ? source.produced_at : null
      if (effectiveTime && timestamp(effectiveTime) > cutoff) fail('FUTURE_EFFECTIVE_FACT')
      const recordedTime = domain === 'stock_movements' ? source.system_created_at
        : domain === 'sales_lines' ? source.created_at
          : domain === 'lot_cost' ? source.calculated_at : null
      if (recordedTime && timestamp(recordedTime) > cutoff) fail('FUTURE_KNOWLEDGE')
      if (source.source_key !== undefined) {
        const key = source.source_key
        if (typeof key !== 'string') return fail('DUPLICATE_SOURCE')
        if (seen.has(key)) fail('DUPLICATE_SOURCE')
        seen.add(key)
      }
    }
  }
  if (counts.physical !== 1 || typeof counts.commercial !== 'number' || counts.commercial > 1
    || (counts.commercial === 1) !== (scope.commercial_status === 'BOUND')) fail('SCOPE_COUNT')
  return structuredClone(raw) as SourceProbe
}
