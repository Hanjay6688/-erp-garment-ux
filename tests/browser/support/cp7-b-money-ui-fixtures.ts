import { creditCohort, creditEvent, creditId, creditOutcome, creditReview, creditSource, creditTarget, creditTargetRow, creditWorkspace } from '../../fixtures/customerCredit'
import { LAU_POLICY_KEYS } from '../../../src/laundryBd'
import type { SalesRead } from '../../../src/salesReadContract'
import { fixtureActor, type Call, type Reply } from './cp7-b-loopback-fixture'

export const capturedAt = '2026-11-13T05:00:00Z'
export const source = creditSource()
export const salesCase = {
  returnWriter: 'erp_cp7_correct_sales_return_v1', noteWriter: 'erp_cp7_correct_note_v1',
  creditWriter: 'erp_cp7_customer_credit_command_v1', replacementReturn: creditId(41),
  replacementNote: creditId(42), noteRevision: creditId(43), readyToken: 'f'.repeat(64),
  targetItem: creditId(27), returnAt: '2026-10-18T07:00:59.123456Z',
}
const { open_balance: _open, ...sourceFinance } = source.financial!
const target: NonNullable<SalesRead['detail']> = {
  ...source, id: creditTarget, number: creditTargetRow.number, status: 'PARTIAL_PAID',
  row_version: creditTargetRow.row_version, physical_at: creditTargetRow.physical_at, returned_qty: '0',
  review_token: 'c'.repeat(32),
  financial: { ...sourceFinance, gross_total: '400', return_total: '0.00', net_total: '400.00', paid_total: '80.00', open_balance: '320.00' },
  items: [{ ...source.items[0], id: salesCase.targetItem, financial: { unit_price: '40.00', discount: '0.00', line_total: '400.00' } }],
}
const allocation = {
  allocation_id: creditId(21), sale_item_id: source.items[0].id, product_id: source.items[0].product_id, product_sku: 'SKU-1',
  product_name: 'Barang', size_code: 'S', lot_id: creditId(22), lot_number: 'LOT-1', source_location_name: 'Gudang',
  allocated_qty: '10', sale_item_qty: '10', sale_item_net: '1000.00',
}
const line = {
  id: creditId(23), allocation_id: allocation.allocation_id, product_sku: 'SKU-1', lot_number: 'LOT-1',
  location_id: source.location_id, location_name: 'Gudang', qty_pcs: '2', quality_grade: 'GRADE_A',
  refund_amount: '200.00', notes: null,
}
const returned = {
  id: creditCohort.return_id, number: creditCohort.return_number, physical_at: salesCase.returnAt,
  status: 'POSTED', notes: null,
}
const application = creditEvent()
const refund = { ...creditEvent('REFUND', '20.00'), id: creditId(24) }
const events = [application, refund]
const journals = [creditId(25), creditId(26)]

function sale(id: unknown) { return id === target.id ? target : source }
function salesRead(selected: NonNullable<SalesRead['detail']> | null, rows = [source, target]): SalesRead {
  return { contract_version: 'cp7.sales-workspace.v1', read_at: capturedAt, financial_captured: true, read_only: true,
    page: { rows: rows.map(({ items: _items, review_token: _token, ...header }) => header), total: String(rows.length), offset: 0, limit: 25, next_offset: null },
    detail: selected }
}
function creditDependencies(selected: NonNullable<SalesRead['detail']>) {
  const rows = selected.id === source.id ? events : [application]
  return {
    contract_version: 'cp7.sales-credit-dependencies.v1', actor_scope_id: fixtureActor, read_at: capturedAt,
    read_only: true, business_DML: false, dependency_sha256: 'b'.repeat(64),
    source: { sale_id: selected.id, number: selected.number, status: selected.status, row_version: selected.row_version, review_token: selected.review_token },
    page: { offset: 0, limit: 25, total: String(rows.length), next_offset: null },
    dependencies: rows.map((e, i) => ({
      event_id: e.id, kind: e.kind, amount: e.amount, economic_date: e.economic_date, book_date: e.book_date,
      source_sale_id: source.id, source_sale_number: source.number, source_return_id: returned.id, source_return_number: returned.number,
      target_sale: e.kind === 'APPLY' ? { id: target.id, number: target.number } : null, journal_id: journals[i],
    })),
  }
}
function returnCorrection(proposedAmount?: string) {
  const choice = { ...allocation, peer_returned_qty: '0', replacement_capacity: '10' }
  const review = proposedAmount === '50.00'
    ? { state: 'REFUSE', review_token: '9'.repeat(64), credit_delta: '-150.00', before_available: '100.00', after_available: '-50.00',
      issues: ['SIGNED_DECREASE_ADAPTER_REQUIRED', 'UNDO_ACTIVE_CONSUMERS_FIRST'], source_authority_proven: true }
    : proposedAmount === '250.00'
      ? { state: 'READY', review_token: salesCase.readyToken, credit_delta: '50.00', before_available: '100.00', after_available: '150.00',
        issues: [], source_authority_proven: true }
      : { state: 'REVIEW_REQUIRED', review_token: null, credit_delta: null, before_available: null, after_available: null,
        issues: [], source_authority_proven: false }
  return {
    contract_version: 'cp7.sales-return-correction-workspace.v1', read_at: capturedAt,
    source: { sale_id: source.id, row_version: source.row_version, review_token: source.review_token },
    document: { ...returned, sale_id: source.id, items: [{ ...line, product_id: allocation.product_id, lot_id: allocation.lot_id }] },
    return_review_token: 'd'.repeat(32), financial: source.financial, eligible: true, can_correct: true,
    allocations: { rows: [choice], total: '1', offset: 0, limit: 25, next_offset: null }, current_allocations: [choice],
    previous: null, next: null, production_go: false,
    // Public workspace extension from cp7_credit_correction_de.workspace_v1.
    credit_correction: {
      contract_version: 'cp7.credit-correction-de.v1', ...review, families: [],
      increase_policy: 'AUTO_CREDIT_INCREMENT',
      shortfall_policy: 'UNDO_ACTIVE_CONSUMERS_FIRST', replacement_invoice_policy: 'AUTO_TRANSFER_TO_REPLACEMENT',
      active_consumers: events.map((e, i) => ({ event_id: e.id, event_kind: e.kind, amount: e.amount,
        cohort_id: e.cohort_id, family_ordinal: '1', target_sale_id: e.target_sale_id, journal_id: journals[i],
        undo_action: e.kind === 'APPLY' ? 'Batalkan penggunaan kredit di invoice tujuan' : 'Batalkan pengembalian uang kredit' })),
    },
  }
}
function noteHistory() {
  return {
    contract_version: 'cp7.note-correction-workspace.v2', read_at: capturedAt, root_sale_id: target.id, current_sale_id: target.id,
    history: [], current: salesRead(target), original_note_number: target.number, production_go: false,
    // Public workspace extension from cp7_credit_note_carry_de.workspace_v1.
    credit_carry: {
      contract_version: 'cp7.note-credit-carry-basis.v1', sale_id: target.id, root_sale_id: target.id,
      row_version: target.row_version, review_token: target.review_token, basis_sha256: 'e'.repeat(64),
      transfer_amount: '80.00', minimum_replacement_net: '80.00', original_net: '400.00',
      policy: 'AUTO_TRANSFER_TO_REPLACEMENT', issues: [],
      consumers: [{ event_id: application.id, amount: application.amount, cohort_id: application.cohort_id,
        journal_id: journals[0], historical_target_id: target.id, economic_date: application.economic_date, transaction_date: application.book_date }],
    },
  }
}

export function saleRpc({ name, args }: Call) {
  const q = args.p_query
  if (name === 'erp_cp7_get_sales_v1') return { body: salesRead(q.sale_id ? sale(q.sale_id) : null) }
  if (name === 'erp_cp7_get_sales_credit_dependencies_v1') return { body: creditDependencies(sale(q.sale_id)) }
  if (name === 'erp_cp7_get_sales_return_correction_v1' && q.return_id === returned.id && q.sale_id === source.id) {
    return { body: returnCorrection(q.proposed?.replacement.items[0]?.refund_amount) }
  }
  if (name === 'erp_cp7_get_note_correction_v2' && args.p_sale === target.id) return { body: noteHistory() }
  if (name === 'erp_cp7_resolve_transaction_source_v1') {
    const reference = args.p_source
    if (reference.source_type === 'SALES_RETURN' && reference.source_id === returned.id) return {
      body: { contract_version: 'cp7.transaction-source.v1', actor_scope_id: fixtureActor, source: reference,
        status: 'AVAILABLE', document: { domain: 'SALE', route: 'sales-returns', id: source.id, number: source.number,
          status: source.status, revision: source.row_version, focus: { kind: 'SALES_RETURN', id: returned.id, page_offset: 0 } },
        read_at: capturedAt, business_DML: false },
    }
  }
  if (name === 'erp_cp7_get_sales_returns_v1') {
    const d = sale(q.sale_id)
    let rows: unknown[]
    if (q.kind === 'RETURNS') rows = d.id === source.id ? [{ ...returned, line_count: '1', items: [line] }] : []
    else if (q.kind === 'LOCATIONS') rows = [{ id: source.location_id, name: source.location_name }]
    else if (q.kind === 'ALLOCATIONS') rows = [{ ...allocation, commercial_sku: 'SKU-1', returned_qty: '2', remaining_qty: '8' }]
    else return undefined
    const list = q.kind === 'RETURNS' && 'history_q' in q ? { q: q.history_q, status: q.history_status, order: q.history_order } : null
    return { body: { contract_version: 'cp7.sales-returns.v1', kind: q.kind, sale_id: d.id, row_version: d.row_version,
      review_token: d.review_token, page: { rows, total: String(rows.length), offset: 0, limit: 25, next_offset: null, ...(list ? { list } : {}) } } }
  }
  return undefined
}

/** Per-browser synthetic response state. Ledger and stock are not simulated. */
export function salesCorrectionFixture() {
  let currentSource = source
  let currentNote: typeof target | null = null
  let undo: ReturnType<typeof creditOutcome> | null = null
  const notes = new Map<string, { intent: string; outcome: object }>()
  const effects = { return: 0, note: 0, undo: 0 }
  const nextVersion = (v: string) => (BigInt(v) + 1n).toString()
  const refusal = { body: { code: 'P0001', message: 'CP7_FIXTURE_UNEXPECTED_INTENT' }, status: 400 }
  const resolve = (call: Call): Reply | undefined => {
    const { name, args } = call, q = args.p_query, p = args.p_payload
    if (name === 'erp_cp7_get_sales_v1') {
      const oldTarget: typeof target = currentNote
        ? { ...target, status: 'REVERSED', financial: { ...target.financial!, state: 'INACTIVE_DOCUMENT', open_balance: null } }
        : target
      const rows = currentNote ? [currentSource, oldTarget, currentNote] : [currentSource, oldTarget]
      return { body: salesRead(rows.find(row => row.id === q.sale_id) ?? null, rows) }
    }
    if (name === salesCase.returnWriter) {
      if (effects.return || args.p_expected !== source.row_version || p.sale_id !== source.id || p.return_id !== returned.id
        || p.credit_review_token !== salesCase.readyToken || p.replacement.physical_at !== returned.physical_at
        || p.replacement.items[0]?.refund_amount !== '250.00') return refusal
      effects.return++
      currentSource = { ...source, row_version: nextVersion(source.row_version), review_token: '3'.repeat(32),
        financial: { ...source.financial!, return_total: '250.00', net_total: '750.00', paid_total: '750.00' } }
      return { body: { contract_version: 'cp7.sales-return-correction.v1', kind: 'COMMITTED_OUTCOME', action: 'RETURN_CORRECT',
        request_id: args.p_request, sale_id: source.id, row_version: currentSource.row_version, status: source.status,
        original_return_id: returned.id, original_return_status: 'REVERSED', return_id: salesCase.replacementReturn,
        return_status: 'POSTED', return_page_offset: 0, production_go: false,
        link: { id: creditId(44), original_id: returned.id, replacement_id: salesCase.replacementReturn, sale_id: source.id,
          actor_scope_id: fixtureActor, request_id: args.p_request, reason: p.change_reason, recorded_at: capturedAt, time_restatement: null } } }
    }
    if (name === salesCase.noteWriter) {
      const intent = JSON.stringify(args), prior = notes.get(args.p_request)
      if (prior) return prior.intent === intent ? { body: prior.outcome } : refusal
      if (effects.note || args.p_expected !== target.row_version || p.sale_id !== target.id || p.item_lineage[0] !== salesCase.targetItem
        || p.items[0]?.qty_pcs !== '10' || p.items[0]?.unit_price_snapshot !== '45.00'
        || p.credit_carry_review?.basis_sha256 !== 'e'.repeat(64) || p.credit_carry_review?.remaining_amount !== '370.00') return refusal
      effects.note++
      currentNote = { ...target, id: salesCase.replacementNote, number: 'INV-TARGET · R1-' + args.p_request.slice(0, 8),
        row_version: '2', review_token: '4'.repeat(32),
        financial: { ...target.financial!, gross_total: '450.00', net_total: '450.00', open_balance: '370.00' },
        items: [{ ...target.items[0], id: creditId(45), financial: { unit_price: '45.00', discount: '0.00', line_total: '450.00' } }] }
      const outcome = { contract_version: 'cp7.note-correction-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'CORRECT',
        request_id: args.p_request, root_sale_id: target.id, previous_sale_id: target.id, sale_id: currentNote.id,
        revision_id: salesCase.noteRevision, revision: '1', effective_at: target.physical_at }
      notes.set(args.p_request, { intent, outcome })
      return { abort: true }
    }
    if (name === 'erp_cp7_get_customer_credit_workspace_v1' && q.sale_id === source.id && q.kind === 'EVENTS') {
      const rows = undo ? [
        { ...application, undone_by: undo.consumption_event_id },
        { ...application, id: undo.consumption_event_id, amount: undo.amount, restores_event_id: application.id,
          physical_at: undo.physical_at, economic_date: undo.economic_date, book_date: undo.transaction_date,
          target_sale_id: currentNote!.id, target_number: currentNote!.number }, refund,
      ] : events
      return { body: { ...creditWorkspace('EVENTS', currentSource, rows), actor_scope_id: fixtureActor } }
    }
    if (currentNote && (name === 'erp_cp7_get_customer_credit_review_v1' || name === salesCase.creditWriter)) {
      if (p.action !== 'UNDO' || p.restores_event_id !== application.id) return refusal
      const review = creditReview(p, application)
      review.available_credit_after = '180.00'
      review.selection.target_sale_id = currentNote.id
      review.selection.target_current_leaf_id = currentNote.id
      review.expected_versions = { [currentSource.id]: currentSource.row_version, [currentNote.id]: currentNote.row_version }
      review.target_assignment = { contract_version: 'cp7.note-credit-target-assignment.v1', root_sale_id: target.id,
        historical_target_id: target.id, current_sale_id: currentNote.id, current_number: currentNote.number,
        revision_id: salesCase.noteRevision, original_event_id: application.id, proof_sha256: '1'.repeat(64) }
      if (name !== salesCase.creditWriter) return { body: review }
      if (effects.undo || p.quote_sha256 !== review.quote_sha256 || JSON.stringify(args.p_expected_versions) !== JSON.stringify(review.expected_versions)) return refusal
      effects.undo++
      undo = creditOutcome(args.p_request, review)
      currentSource = { ...currentSource, row_version: undo.invoice_versions[currentSource.id], review_token: '5'.repeat(32) }
      currentNote = { ...currentNote, row_version: undo.invoice_versions[currentNote.id], review_token: '6'.repeat(32), status: 'POSTED',
        financial: { ...currentNote.financial!, paid_total: '0.00', open_balance: '450.00' } }
      return { body: undo }
    }
    return saleRpc(call)
  }
  return { resolve, effects }
}

const vendorId = creditId(61), correctionId = creditId(62), claimId = creditId(63), targetInvoice = creditId(64), cashAccount = creditId(65)
export const vendorCase = { vendorId, correctionId, claimId, targetInvoice, cashAccount, beforeBookDate: '2026-11-12' }
export const vendorDatedRefusal = 'CP7_VENDOR_RECEIVABLE_NEGATIVE_DATED: saldo piutang vendor tidak cukup pada tanggal ekonomi atau tanggal buku'
export const vendorWriter = 'erp_save_laundry_bd_action_v1'
export function vendorWorkspace(selected: boolean) {
  return {
    pagination: { as_of: capturedAt, invoice_next: null, receipt_next: null },
    money_visible: true, can_manage_master: false, can_set_price: false, is_owner: true,
    policies: LAU_POLICY_KEYS.map(key => ({ key, status: 'PENDING_POLICY_VALUE', value: null, version: '1', set_at: '2026-11-10T07:00:00', reason: 'Fixture UI' })),
    vendors: [{ id: vendorId, code: 'V1', name: 'Laundry A', pricing_mode: 'RATE', pricing_unit: 'PCS', minimum_charge: null, terms_version: '1', bd_priced: false }],
    processes: [], components: [], packages: [], process_rates: [], scoped_rates: [], priced_deliveries: [], opening_uninvoiced: [],
    invoices: [], billable_receipts: [], accounts: [], pending_cost: { goods: [], sales: [] },
    vendor_receivable_contract: 'cp7.vendor-receivable.v1', vendor_receivable_accounts: [{ id: creditId(66), code: 'ARV', name: 'Piutang vendor' }],
    payables: !selected ? null : {
      vendor_receivable_contract: 'cp7.vendor-receivable.v1',
      documents: [{ kind: 'VENDOR_INVOICE', id: targetInvoice, number: 'INV-NEXT', date: '2026-11-11', total: '80.00', paid_cash: '0.00',
        claim_credit: '0.00', correction_credit: '0.00', corrects: null, remaining: '80.00', status: 'POSTED', settlements: [] }],
      cash_accounts: [{ id: cashAccount, code: 'BANK', name: 'Bank Utama' }],
      credits: [
        { kind: 'INVOICE_CORRECTION', id: correctionId, number: 'KOR-LDR-A', approved_date: '2026-11-10', amount: '100.00', applied: '0.00',
          available: '100.00', receivable: '100.00', refunded: '0.00', corrects: 'INV-ORIGINAL' },
        { kind: 'DAILY_CLAIM', id: claimId, number: 'CLM-RUSAK-A', approved_date: '2026-11-10', amount: '20.00', applied: '0.00',
          available: '20.00', receivable: '0.00', refunded: '0.00' },
      ],
      refunds: [], ledger: { ap_balance: '60.00', documents_remaining: '80.00', credit_available: '120.00',
        receivable_balance: '100.00', receivable_gl: '100.00', matches: true },
    },
  }
}
