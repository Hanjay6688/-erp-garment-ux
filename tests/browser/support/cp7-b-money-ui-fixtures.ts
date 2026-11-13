import { creditCohort, creditEvent, creditId, creditSource, creditTarget, creditTargetRow } from '../../fixtures/customerCredit'
import { LAU_POLICY_KEYS } from '../../../src/laundryBd'
import type { SalesRead } from '../../../src/salesReadContract'
import { fixtureActor, type Call } from './cp7-b-loopback-fixture'

export const capturedAt = '2026-11-13T05:00:00Z'
export const source = creditSource()
const { open_balance: _open, ...sourceFinance } = source.financial!
const target: NonNullable<SalesRead['detail']> = {
  ...source, id: creditTarget, number: creditTargetRow.number, status: 'PARTIAL_PAID',
  row_version: creditTargetRow.row_version, physical_at: creditTargetRow.physical_at, returned_qty: '0',
  review_token: 'c'.repeat(32),
  financial: { ...sourceFinance, gross_total: '400.00', return_total: '0.00', net_total: '400.00', paid_total: '80.00', open_balance: '320.00' },
  items: [{ ...source.items[0], id: creditId(27), financial: { unit_price: '40.00', discount: '0.00', line_total: '400.00' } }],
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
  id: creditCohort.return_id, number: creditCohort.return_number, physical_at: '2026-10-18T07:00:59.123456Z',
  status: 'POSTED', notes: null,
}
const application = creditEvent()
const refund = { ...creditEvent('REFUND', '20.00'), id: creditId(24) }
const events = [application, refund]
const journals = [creditId(25), creditId(26)]

function sale(id: unknown) { return id === target.id ? target : source }
function salesRead(selected: NonNullable<SalesRead['detail']> | null): SalesRead {
  return { contract_version: 'cp7.sales-workspace.v1', read_at: capturedAt, financial_captured: true, read_only: true,
    page: { rows: [source, target].map(({ items: _items, review_token: _token, ...header }) => header), total: '2', offset: 0, limit: 25, next_offset: null },
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
function returnCorrection() {
  const choice = { ...allocation, peer_returned_qty: '0', replacement_capacity: '10' }
  return {
    contract_version: 'cp7.sales-return-correction-workspace.v1', read_at: capturedAt,
    source: { sale_id: source.id, row_version: source.row_version, review_token: source.review_token },
    document: { ...returned, sale_id: source.id, items: [{ ...line, product_id: allocation.product_id, lot_id: allocation.lot_id }] },
    return_review_token: 'd'.repeat(32), financial: source.financial, eligible: true, can_correct: true,
    allocations: { rows: [choice], total: '1', offset: 0, limit: 25, next_offset: null }, current_allocations: [choice],
    previous: null, next: null, production_go: false,
    // Public workspace extension from cp7_credit_correction_de.workspace_v1.
    credit_correction: {
      contract_version: 'cp7.credit-correction-de.v1', state: 'REVIEW_REQUIRED', review_token: null,
      credit_delta: null, before_available: null, after_available: null, issues: [], families: [],
      source_authority_proven: false, increase_policy: 'AUTO_CREDIT_INCREMENT',
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
  if (name === 'erp_cp7_get_sales_return_correction_v1' && q.return_id === returned.id && q.sale_id === source.id) return { body: returnCorrection() }
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
