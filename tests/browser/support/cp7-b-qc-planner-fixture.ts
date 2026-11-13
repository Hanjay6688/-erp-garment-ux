// Synthetic HTTP replies. Only the browser contract is exercised here.
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import initialReady from '../../fixtures/initialAnalysisReadyActual.json' with { type: 'json' }
import { laundryQcInputFixture } from '../../fixtures/laundryQcInput'
import { reorderWire } from '../../fixtures/fgReorder'
import { job, report as reportWire, section as sectionWire } from '../../fixtures/nativeStagedReports'
import { stagedCheckFixture, stagedFreshnessFixture, stagedRun } from '../../fixtures/nativeAnalysisPages'
import { planningConfig, profileWire } from '../../fixtures/nativePlanningProfile'
import { recoveryPatterns } from '../../fixtures/productionRecovery'
import { autoRpc, profileRpc, qcRpc, reportRpc } from '../../../scripts/cp7-b-qc-planner/operator.mjs'
import type { Call, Reply } from './cp7-b-loopback-fixture'

const at = '2026-11-12T04:00:00Z', after = '2026-11-12T07:00:00Z'
const id = (n: number) => '00000000-0000-4000-8000-' + String(n).padStart(12, '0')
const digest = (s: string) => createHash('sha256').update(s).digest('hex')
const denied = { body: { code: '42501', message: 'CP7_ACCESS_DENIED' }, status: 403 }
export const query = { from_date: '2026-11-10', through_date: '2026-11-12', group_mode: 'AS_SOLD' as const }
export const rights = ['dashboard.view', 'warehouse.fg.view', 'warehouse.stock.view', 'production.wip.view', 'master.pattern.view',
  'master.product.view', 'master.product.manage', 'sales.invoice.view', 'production.final_sku.view', 'production.final_sku.post',
  'finance.hpp.view', 'finance.reports.view', 'production.laundry.view']
const qc = laundryQcInputFixture('QC')
const source = qc.qc_queue[0], sku = qc.lookups.products[0], location = qc.lookups.fg_locations[0]
export const qcCase = {
  poNumber: source.po_number, group: source.cutting_group_id, groupNumber: source.group_number, sku: sku.sku, sizeCode: sku.size_code,
  product: sku.id, location: location.id, locationName: location.name, qcLocal: '2026-11-11T13:00', qcAt: '2026-11-11T06:00:00.000Z',
  lot: id(56), lotNumber: 'LOT-QC-3', movement: id(57), qcItem: id(58), receiptLine: source.receipt_line_id, receiptSize: source.source_batch_size_line_id,
  targetKey: sku.id + ':' + sku.size_id,
}
const rpcPage = (rows: unknown[]) => ({ rows, total: String(rows.length), offset: 0, limit: 25, next_offset: null })
const fgPosition = { product_id: sku.id, product_sku: sku.sku, commercial_sku: sku.sku, product_name: sku.name, size_code: sku.size_code,
  brand_name: sku.brand_name, lot_id: qcCase.lot, lot_number: qcCase.lotNumber, location_id: location.id, location_name: location.name, quality_grade: 'GRADE_A' }
const balance = (qty: number) => ({ physical_qty: String(qty), available_qty: String(qty), reserved_qty: '0', quality: 'KNOWN' })
function stock(purpose: string, count: number, money: boolean, includeRow: boolean) {
  const totals = balance(includeRow ? count : 0), readAt = count ? after : at
  return { body: { contract_version: 'cp7.fg-workspace.v1', purpose, read_at: readAt, knowledge: 'CURRENT',
    quantity_basis: 'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION', financial_captured: money,
    capabilities: { card: true }, unit_code: 'PCS', totals, page: rpcPage(count && includeRow ? [{ ...fgPosition, ...totals, last_movement_at: qcCase.qcAt,
      ...(money ? { valuation: { state: 'KNOWN', hpp_version_id: id(59), hpp_version: '1', cost_state: 'FINAL',
        calculated_at: after, unit_cost: '36.00', value: '108.00', basis: 'CURRENT_RESTATED_LOT_VALUE' } } : {}) }] : []) } }
}
function card(q: Record<string, unknown>) {
  const movement = { id: qcCase.movement, physical_at: qcCase.qcAt, recorded_at: after,
    movement_type: 'QC_GOOD', source_type: 'QC_ITEM', source_id: qcCase.qcItem, reversal_of_id: null, customer_name: null,
    notes: null, book_order: '1', commercial_sku_at_transaction: sku.sku, qty_signed: '3', reservation_delta: '0',
    physical_delta: '3', available_balance: '3', reserved_balance: '0', physical_balance: '3',
    original_physical_delta: '3', correction_count: '0', correction_recorded_at: null,
    audit_movements: [{ id: qcCase.movement, physical_at: qcCase.qcAt, recorded_at: after, lot_id: qcCase.lot, source_type: 'QC_ITEM',
      source_id: qcCase.qcItem, reversal_of_id: null, available_delta: '3', reservation_delta: '0' }],
    valuation: { state: 'KNOWN', unit_cost: '36.00', basis: 'CURRENT_RESTATED_MOVEMENT_SNAPSHOT' } }
  return { body: { contract_version: 'cp7.fg-ledger.v2', purpose: q.purpose, read_at: after, knowledge: 'CURRENT', financial_captured: true,
    position: fgPosition, balances: balance(3), balance_basis: 'COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',
    page: { ...rpcPage([movement]), list: { q: q.q, movement_type: q.movement_type, order: q.order, movement_types: ['QC_GOOD'] } } } }
}
function wip(args: Call['args'], remaining: number) {
  return { body: { filter: args.p_filter, sort: args.p_sort, pattern_id: args.p_pattern_id, opening_rows: [],
    rows: args.p_filter === 'COMPLETED' || args.p_query && args.p_query !== source.po_number ? [] : [{
      cutting_group_id: source.cutting_group_id, po_number: source.po_number, group_number: source.group_number,
      model_code: source.model_code, model_name: source.model_name, executor_name: 'Mandor A', pattern_id: null,
      pattern_code: null, pattern_revision: null, pattern_name: null, pattern_sort_order: null, pattern_is_active: null,
      effective_qty_pcs: 8, sewn_qty_pcs: 8, unfinished_sewing_qty_pcs: 0, unsent_ready_qty_pcs: 0, laundry_draft_qty_pcs: 0,
      laundry_in_transit_qty_pcs: 0, unresolved_laundry_issue_qty_pcs: 0, pending_final_sku_handoff_qty_pcs: remaining,
      remaining_final_sku_qty_pcs: remaining, open_bs_count: 0, open_rework_count: 0, open_flag_count: 0, open_flags: [],
      distribution: null, control_status: 'ACTIVE', updated_at: remaining === 8 ? at : after, row_version: remaining === 8 ? 5 : 6,
    }] } }
}
const first = { rootId: id(81), sizeId: id(82), sku: 'B-PLAN-001', name: 'Celana pertama', stock: '6', targetQty: null }
export const second = { rootId: id(83), sizeId: id(84), sku: 'B-PLAN-002', name: 'Celana kedua', stock: '17', targetQty: '120' }
export const plannerJobId = id(85)

function serveRun(call: Call, run: Awaited<ReturnType<typeof stagedRun>>, changed = false, checked = false) {
  const { name, args } = call
  if (name === 'erp_cp7_read_staged_analysis_pages_v1' && args.p_run === run.runId) return { body: run.pageSet }
  if (name === 'erp_cp7_read_staged_analysis_page_v1' && args.p_run === run.runId && args.p_access === run.pageSet.access_epoch) return { body: run.page(args.p_index) }
  if (name === 'erp_cp7_staged_snapshot_freshness_v1' && args.p_run === run.runId) {
    const check = checked ? { source_state: 'ARCHIVED_STALE' as const, checked_at: after } : undefined
    const freshness = stagedFreshnessFixture(run, changed ? { rows: { FG_STOCK: [1, 0], PRODUCTION: [1, 0] }, last: after, check } : {})
    return { body: { ...freshness, evaluated_at: changed ? after : run.reference.captured_at } }
  }
  if (name === 'erp_cp7_check_staged_snapshot_v1' && args.p_run === run.runId) {
    return { body: stagedCheckFixture(run.runId, { source_state: changed ? 'ARCHIVED_STALE' : 'UNCHANGED', checked_at: after }) }
  }
  return undefined
}
function defaultReply(call: Call) {
  if (call.name === 'erp_cp7_get_fg_reorder_v1') return { body: reorderWire([]) }
  if (call.name === 'erp_list_patterns_v1') return { body: recoveryPatterns }
  return undefined
}

export async function plannerFixture() {
  const run = await stagedRun({ targets: 2, requestId: plannerJobId, fixtures: [first, second] })
  let saved = false, state: 'NOT_READY' | 'READY' | 'RUNNING' | 'DONE' = 'NOT_READY', revoked = false
  const effects = { profiles: 0, jobs: 0 }
  const candidate = (p: typeof first | typeof second, ready: boolean) => ({ root_id: p.rootId, product_id: p.rootId, size_id: p.sizeId,
    sku: p.sku, product_name: p.name, profile_ready: ready })
  const getJob = () => state === 'DONE' ? run.job('DONE') : run.job('RUNNING', {
    targets_done_in_stage: 0, worker_active: true, server_runner: { active: true, last_tick_at: run.reference.captured_at },
  })
  const status = () => ({ ...initialReady, actor: run.actor, query: run.query, state,
    readiness: { ...initialReady.readiness, ready: saved, reasons: saved ? [] : ['PLANNING_PROFILE_INCOMPLETE'],
      products_total: 2, active_products: 2, eligible_targets: saved ? 1 : 0, candidates: [candidate(first, false), candidate(second, saved)] },
    ...(state === 'RUNNING' || state === 'DONE' ? { job: getJob(), job_query: run.query, job_semantic_hash: initialReady.semantic_hash } : {}),
  })
  const resolve = (call: Call): Reply | undefined => {
    const { name, args } = call
    if (name === autoRpc && args.p_request === null) {
      if (revoked) return denied
      if (args.p_query.initial_auto === 'ENSURE' && state === 'READY') { effects.jobs++; state = 'RUNNING' }
      return { body: status() }
    }
    if (name === 'erp_cp7_get_planning_profiles_v1' && args.p_roots[0] === second.rootId) {
      const wire = profileWire(saved)
      return { body: { ...wire, rows: [{ ...wire.rows[0], config: saved ? { ...planningConfig, minimum_available_days: '14', buffer_days: '2' } : null,
        root_id: second.rootId, product_version_id: second.rootId,
        size_id: second.sizeId, sku: second.sku, product_name: second.name }] } }
    }
    if (name === profileRpc) {
      const p = args.p_payload
      assert.equal(effects.profiles, 0)
      assert.equal(p.root_id, second.rootId)
      assert.equal(p.product_version_id, second.rootId)
      assert.equal(p.expected_revision, '0')
      assert.equal(p.config.daily_pcs, planningConfig.daily_pcs)
      assert.deepEqual([p.config.lead_days, p.config.review_days, p.config.buffer_days], ['3', '7', '2'])
      saved = true; state = 'READY'; effects.profiles++
      return { body: { contract_version: 'cp7.planning-profile-outcome.v1', request_id: args.p_request, root_id: second.rootId,
        quality: 'SELECTED_ASSUMPTION', revision: '1', profile_id: id(86) } }
    }
    if (name === 'erp_cp7_get_staged_analysis_v1' && args.p_request === plannerJobId) return { body: getJob() }
    if (name === 'erp_cp7_get_fg_v1') return stock(args.p_query.purpose, 0, true, false)
    return serveRun(call, run) ?? defaultReply(call)
  }
  return { run, effects, resolve, finish: () => { assert.equal(state, 'RUNNING'); state = 'DONE' }, revoke: () => { revoked = true } }
}

type AnalysisRun = Awaited<ReturnType<typeof stagedRun>>
type Publication = ReturnType<typeof reportWire>
const reportSeries = id(61)
export const qcReportTitles = ['Posisi sebelum QC', 'Posisi sesudah QC']

function publication(run: AnalysisRun, request: string, revision: number, title: string, reason: string, stale: boolean) {
  const changed = revision === 2
  const asOf = changed ? after : at
  const summary = [
    title, 'LAPORAN PERIODE · 2026-11-10 s.d. 2026-11-12',
    'Nilai barang dalam proses: ' + (changed ? '180.00' : '288.00') + ' IDR',
    'Nilai persediaan barang jadi: ' + (changed ? '108.00' : '0.00') + ' IDR',
    'HPP penjualan tercatat: 0.00 IDR',
    'Produksi dalam proses; siap Belum diketahui.',
  ].join('\n')
  const body = [
    'BAGIAN 1 dari 1 · Target 1–1 dari 1',
    `${sku.sku} · ${sku.name} · size ${sku.size_code} · stok fisik saat analisis 0 PCS; stok fisik aktual ${changed ? 3 : 0} PCS`,
  ].join('\n')
  const summaryHash = digest(summary), sectionHash = digest(body)
  const doc = reportWire({
    actor_scope_id: run.actor, id: id(61 + revision), series_id: reportSeries, revision: String(revision),
    run_id: run.runId, request_id: request, identity_hash: run.identityHash, data_as_of: run.reference.captured_at,
    kind: 'PERIOD', finance: 'INCLUDED', financial_source_hash: digest('finance-' + revision),
    period_query: query, title, reason, report_date: query.through_date, targets_total: 1,
    actuals_read_at: asOf, published_at: asOf, summary, summary_sha256: summaryHash,
    freshness: { state: stale ? 'STALE_VERIFIED' : changed ? 'CHANGES_RECORDED' : 'NO_RECORDED_CHANGE',
      evaluated_at: asOf, changes_total: changed ? '2' : '0' },
    sections: [{ index: 0, target_lo: 1, target_hi: 1, sha256: sectionHash, utf8_bytes: Buffer.byteLength(body) }],
    report_hash: digest(summaryHash + '\n' + sectionHash),
  })
  return { doc, body }
}

export function qcReportFixture() {
  let run: AnalysisRun | null = null, checked = false, refuseIdentity = false
  const effects = { analysis: 0, qc: 0, publications: 0, refused: 0 }
  const documents: ReturnType<typeof publication>[] = []
  const pending = new Map<string, { units: number; data: ReturnType<typeof publication> }>()
  const stages = ['ACTUALS', 'SECTION', 'FRESHNESS', 'SUMMARY']
  const reportJob = (request: string) => {
    const active = pending.get(request)
    assert.ok(active)
    const { units, data: { doc } } = active
    return { body: job(units, units === 4 ? 'DONE' : 'RUNNING', {
      request_id: request, stage: stages[units] ?? null, unit_count: 4, sections_done: units >= 2 ? 1 : 0, section_count: 1,
      run_id: doc.run_id, identity_hash: doc.identity_hash, data_as_of: doc.data_as_of,
      kind: doc.kind, finance: doc.finance, series_id: doc.series_id, revision: doc.revision,
      last_progress_at: doc.actuals_read_at, publication_id: units === 4 ? doc.id : null,
    }) }
  }
  const resolve = async (call: Call): Promise<Reply | undefined> => {
    const { name, args } = call
    if (name === autoRpc) {
      if (args.p_request === null) {
        return { body: { ...initialReady, state: 'NOT_READY', readiness: { ...initialReady.readiness, ready: false,
          reasons: ['PLANNING_PROFILE_INCOMPLETE'], eligible_targets: 0,
          candidates: initialReady.readiness.candidates.map(p => ({ ...p, profile_ready: false })) } } }
      }
      assert.equal(effects.analysis, 0)
      assert.deepEqual(args.p_query, query)
      run = await stagedRun({ targets: 1, requestId: args.p_request, runId: id(60), actor: initialReady.actor, capturedAt: at, query,
        fixtures: [{ rootId: sku.id, sizeId: sku.size_id, sku: sku.sku, name: sku.name, stock: '0' }] })
      effects.analysis++
      return { body: run.job('DONE') }
    }
    const count = effects.qc ? 3 : 0
    if (name === 'erp_get_wip_control_v1') return wip(args, 8 - count)
    if (name === 'erp_cp7_get_fg_v1') return stock(args.p_query.purpose, count, true, ['', sku.sku].includes(args.p_query.q))
    if (name === 'erp_cp7_get_fg_ledger_v2') {
      assert.ok(count)
      const q = args.p_query
      assert.deepEqual([q.product_id, q.location_id, q.lot_id, q.quality_grade], [sku.id, location.id, qcCase.lot, 'GRADE_A'])
      return card(q)
    }
    if (name === 'erp_get_laundry_qc_workspace_v1' && args.p_scope === 'QC') {
      return { body: { ...qc, generated_at: count ? after : at, qc_queue: [{ ...source,
        qc_accounted_qty_pcs: count, available_for_qc_qty_pcs: 8 - count, remaining_qc_qty_pcs: 8 - count,
        cutting_group_row_version: 5 + effects.qc,
      }] } }
    }
    if (name === 'erp_search_final_sku_products_v1') {
      assert.equal(args.p_source_laundry_receipt_batch_size_line_id, qcCase.receiptSize)
      assert.equal(args.p_physical_at, qcCase.qcAt)
      assert.equal(args.p_query, sku.sku)
      return { body: { contract_version: 'CP6_PRODUCT_SEARCH_V2620B',
        source_laundry_receipt_batch_size_line_id: qcCase.receiptSize, physical_at: qcCase.qcAt,
        query: sku.sku.toLowerCase(), page_limit: 50, products: [sku], has_more: false, next_cursor: null } }
    }
    if (name === qcRpc) {
      assert.equal(effects.qc, 0)
      assert.equal(args.p_action, 'POST_FINAL_SKU')
      assert.equal(args.p_expected_version, 5)
      const p = args.p_payload
      assert.deepEqual([p.cutting_group_id, p.destination_location_id, p.physical_at, p.good_qty_pcs, p.completion_mode],
        [qcCase.group, qcCase.location, qcCase.qcAt, 3, 'PARTIAL_SELECTION'])
      const [line, extra] = p.lines
      assert.equal(extra, undefined)
      assert.deepEqual([line.final_product_id, line.qty_good_pcs, line.qty_bs_pcs, line.source_laundry_receipt_line_id,
        line.source_laundry_receipt_batch_size_line_id], [qcCase.product, 3, 0, qcCase.receiptLine, qcCase.receiptSize])
      effects.qc++
      return { body: { contract_version: 'CP6_V2620', action: args.p_action, committed: true, client_request_id: args.p_client_request_id } }
    }
    if (name === 'erp_cp7_get_staged_analysis_v1' && run && args.p_request === run.pageSet.request_id) return { body: run.job('DONE') }
    if (name === 'erp_cp7_check_staged_snapshot_v1' && run && args.p_run === run.runId) checked = count > 0
    if (name === 'erp_cp7_get_staged_ai_brief_v1' && run && args.p_run === run.runId) {
      return { body: { message: 'Ringkasan AI sementara belum tersedia.' }, status: 503 }
    }
    if (name === reportRpc) {
      assert.ok(run)
      const p = args.p_payload
      assert.deepEqual([p.run_id, p.identity_hash, p.kind, p.finance, p.explicit_review],
        [run.runId, run.identityHash, 'PERIOD', 'INCLUDED', true])
      if (refuseIdentity) {
        effects.refused++
        return { body: { code: 'P0001', message: 'CP7_REPORT_V2_IDENTITY_CHANGED' }, status: 400 }
      }
      assert.equal(pending.has(args.p_request), false)
      assert.equal(documents.length, effects.qc)
      assert.deepEqual([p.series_id, p.expected_revision], count ? [reportSeries, '1'] : [null, null])
      const data = publication(run, args.p_request, documents.length + 1, p.title, p.reason, checked)
      pending.set(args.p_request, { units: 0, data })
      return reportJob(args.p_request)
    }
    if (name === 'erp_cp7_step_report_v2') {
      const active = pending.get(args.p_request)
      assert.ok(active && active.units < 4)
      if (++active.units === 4) {
        documents.push(active.data)
        effects.publications++
      }
      return reportJob(args.p_request)
    }
    if (name === 'erp_cp7_read_report_v2') {
      const record = documents.find(({ doc }) => doc.id === args.p_id)
      assert.ok(record)
      return { body: { ...record.doc, is_latest: record === documents.at(-1) } }
    }
    if (name === 'erp_cp7_read_report_section_v2') {
      const record = documents.find(({ doc }) => doc.id === args.p_id)
      assert.ok(record)
      const { doc, body } = record
      assert.deepEqual([args.p_access, args.p_index], [doc.access_epoch, 0])
      return { body: sectionWire(0, { ...doc.sections[0], publication_id: doc.id, report_hash: doc.report_hash, section_count: 1, body }) }
    }
    if (name === 'erp_cp7_list_reports_v2') {
      assert.ok(run)
      const row = ({ id, series_id, revision, run_id, kind, title, period_query, data_as_of, finance, published_at, report_hash }: Publication) =>
        ({ id, series_id, revision, run_id, kind, title, period_query, data_as_of, finance, published_at, report_hash })
      return { body: { contract_version: 'cp7.report-index.v2', actor_scope_id: run.actor, total: String(documents.length),
        rows: documents.toReversed().map(d => row(d.doc)), next_before_id: null, page_complete: true, production_go: false } }
    }
    return (run && serveRun(call, run, count > 0, checked)) || defaultReply(call)
  }
  return { actor: initialReady.actor, effects, resolve, documents, refuseNextPublication: () => { refuseIdentity = true } }
}
