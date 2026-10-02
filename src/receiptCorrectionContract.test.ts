import { describe, expect, it } from 'vitest'
import { correctionDraft, correctionInvoices, correctionPayload, materialNamePayload, parseMaterialNameOutcome, parseMaterialNameWorkspace, parseMaterialCard, parseReceiptCorrectionOutcome, parseReceiptCorrectionWorkspace } from './receiptCorrectionContract'

const ids = { root: '11111111-1111-4111-8111-111111111111', rep: '22222222-2222-4222-8222-222222222222', item: '33333333-3333-4333-8333-333333333333', mat: '44444444-4444-4444-8444-444444444444', roll: '55555555-5555-4555-8555-555555555555', sup: '66666666-6666-4666-8666-666666666666', loc: '77777777-7777-4777-8777-777777777777', rev: '88888888-8888-4888-8888-888888888888' }
const at = '2026-09-29T03:00:00+00:00'
const inv = { id: '99999999-9999-4999-8999-999999999999', line: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' }
function workspace(history = false, invoiced = false) {
  return {
    contract_version: 'cp7.receipt-correction-workspace.v1', read_at: at, root_purchase_id: ids.root, current_purchase_id: history ? ids.rep : ids.root, original_purchase_number: 'SJ-1',
    purchase: { purchase_id: history ? ids.rep : ids.root, purchase_number: history ? 'SJ-1 · R1-abcd' : 'SJ-1', status: 'POSTED', row_version: '3', supplier_id: ids.sup, supplier_name: 'Supplier', location_id: ids.loc, location_name: 'Gudang', physical_at: at, payment_status: 'UNPAID', supplier_invoice_number: null, due_date: null, notes: null },
    lines: [{ item_id: ids.item, material_id: ids.mat, material_sku: 'KAIN', material_name: 'Kain', material_type: 'FABRIC', unit_code: 'yd', qty: '100.000000', unit_price: '10.000000', line_total: '1000.000000', price_state: invoiced ? 'ESTIMATED' : 'FINAL', price_source: invoiced ? 'MANUAL_ESTIMATE' : 'SUPPLIER_INVOICE', invoice_match_state: invoiced ? 'MATCHED' : 'DIRECT_FINAL', lot_number: null, notes: null,
      rolls: [{ roll_id: ids.roll, roll_number: 'R1', qty: '100.000000', cached_qty: '40.000000', status: 'HALF_USED', used_qty: '60.000000', min_qty: '60.000000', movable: true, uses: [{ source_type: 'CUTTING_GROUP', movement_type: 'CUTTING_ISSUE', count: 1 }] }] }],
    invoices: invoiced ? [{ invoice_id: inv.id, invoice_number: 'INV-7', invoice_date: '2026-09-29', received_at: at, due_date: null, row_version: '2', notes: null,
      lines: [{ invoice_line_id: inv.line, purchase_item_id: ids.item, qty_invoiced: '100.000000', unit_price: '12.000000', discount_amount: '0.000000', net_amount: '1200.000000', notes: null }] }] : [],
    payments: [], paid_total: '0', blockers: [], can_correct: true, review_token: 'a'.repeat(32),
    history: history ? [{ revision_id: ids.rev, revision: '1', previous_purchase_id: ids.root, previous_purchase_number: 'SJ-1', replacement_purchase_id: ids.rep, replacement_purchase_number: 'SJ-1 · R1-abcd', effective_at: at, recorded_at: at, reason: 'Salah ketik jumlah', actor_name: 'Owner', previous_document: {}, corrected_document: {} }] : [],
    production_go: false,
  }
}
describe('receipt correction contract', () => {
  it('accepts the exact workspace, follows lineage and refuses unknown fields', () => {
    expect(parseReceiptCorrectionWorkspace(workspace(), ids.root).can_correct).toBe(true)
    expect(parseReceiptCorrectionWorkspace(workspace(true), ids.root).current_purchase_id).toBe(ids.rep)
    expect(() => parseReceiptCorrectionWorkspace({ ...workspace(), extra: 1 }, ids.root)).toThrow()
    expect(() => parseReceiptCorrectionWorkspace({ ...workspace(true), current_purchase_id: ids.root }, ids.root)).toThrow()
  })
  it('builds the exact corrected document and refuses a quantity below physical use', () => {
    const w = parseReceiptCorrectionWorkspace(workspace(), ids.root), lines = correctionDraft(w)
    expect(lines[0].rolls[0]).toMatchObject({ qty: '100', minQty: '60.000000', locked: true })
    lines[0].rolls[0].qty = '50'
    expect(correctionPayload(w, lines, 'Salah ketik jumlah').problem).toContain('sudah terpakai')
    lines[0].rolls[0].qty = '80'
    const out = correctionPayload(w, lines, 'Salah ketik jumlah')
    expect(out.payload).toEqual({ purchase_id: ids.root, review_token: 'a'.repeat(32), change_reason: 'Salah ketik jumlah', lines: [{ replaces_item_id: ids.item, material_id: ids.mat, unit_price: '10', price_state: 'FINAL', price_source: 'SUPPLIER_INVOICE', rolls: [{ replaces_roll_id: ids.roll, roll_number: 'R1', qty: '80' }] }] })
    expect(correctionPayload(w, [{ ...lines[0], rolls: [] }], 'Salah ketik jumlah').problem).toBeTruthy()
    expect(correctionPayload(w, lines, 'abc').problem).toContain('alasan')
  })
  it('corrects every posted supplier invoice with the receipt and refuses invoicing more than received', () => {
    const w = parseReceiptCorrectionWorkspace(workspace(false, true), ids.root), lines = correctionDraft(w), invoices = correctionInvoices(w)
    expect(invoices).toEqual([{ replaces: inv.id, number: 'INV-7', date: '2026-09-29', lines: [{ replaces: inv.line, itemId: ids.item, qty: '100', price: '12', discount: '0' }] }])
    expect(correctionPayload(w, lines, 'Harga final salah ketik').problem).toContain('invoice')
    invoices[0].lines[0].price = '11'
    expect(correctionPayload(w, lines, 'Harga final salah ketik', invoices).payload).toMatchObject({ lines: [{ price_state: 'ESTIMATED', price_source: 'MANUAL_ESTIMATE' }],
      invoices: [{ replaces_invoice_id: inv.id, lines: [{ replaces_invoice_line_id: inv.line, qty_invoiced: '100', unit_price: '11', discount_amount: '0' }] }] })
    lines[0].rolls[0].qty = '80'
    expect(correctionPayload(w, lines, 'Jumlah salah ketik', invoices).problem).toContain('lebih besar dari jumlah diterima')
    invoices[0].lines[0].qty = '80'
    expect(correctionPayload(w, lines, 'Jumlah salah ketik', invoices).problem).toBeNull()
    invoices[0].lines[0].discount = '5000'
    expect(correctionPayload(w, lines, 'Jumlah salah ketik', invoices).problem).toContain('Diskon')
    expect(() => parseReceiptCorrectionWorkspace({ ...workspace(false, true), invoices: [{ ...workspace(false, true).invoices[0], lines: [{ ...workspace(false, true).invoices[0].lines[0], purchase_item_id: ids.rev }] }] }, ids.root)).toThrow()
  })
  it('fixes only the name of the same material', () => {
    const w = parseMaterialNameWorkspace({ contract_version: 'cp7.material-name-workspace.v1', read_at: at, material_id: ids.mat, material_sku: 'KAIN', material_name: 'Katun Combad', material_type: 'FABRIC', unit_code: 'yd', row_version: '4',
      history: [], production_go: false }, ids.mat)
    expect(materialNamePayload(w, '  Katun   Combed ', 'Salah ketik nama').payload).toEqual({ material_id: ids.mat, material_name: 'Katun Combed', change_reason: 'Salah ketik nama' })
    expect(materialNamePayload(w, 'Katun Combad', 'Salah ketik nama').problem).toContain('belum berubah')
    expect(materialNamePayload(w, 'Katun Combed', 'typo').problem).toContain('alasan')
    expect(() => parseMaterialNameWorkspace({ ...w, unit_code: 'yd', extra: true }, ids.mat)).toThrow()
    expect(() => parseMaterialNameWorkspace(w, ids.item)).toThrow()
    const out = { contract_version: 'cp7.material-name-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'RENAME', request_id: ids.rev, material_id: ids.mat, previous_name: 'Katun Combad', material_name: 'Katun Combed', row_version: '5' }
    expect(parseMaterialNameOutcome(out, ids.rev, ids.mat).material_name).toBe('Katun Combed')
    expect(() => parseMaterialNameOutcome(out, ids.rev, ids.item)).toThrow()
  })
  it('validates the committed outcome against the request and source', () => {
    const out = { contract_version: 'cp7.receipt-correction-outcome.v1', kind: 'COMMITTED_OUTCOME', action: 'CORRECT', request_id: ids.rev, root_purchase_id: ids.root, previous_purchase_id: ids.root, purchase_id: ids.rep, revision_id: ids.rev, revision: '1', effective_at: at, row_version: '2' }
    expect(parseReceiptCorrectionOutcome(out, ids.rev, ids.root).purchase_id).toBe(ids.rep)
    expect(() => parseReceiptCorrectionOutcome(out, ids.rev, ids.rep)).toThrow()
    expect(() => parseReceiptCorrectionOutcome({ ...out, purchase_id: ids.root }, ids.rev, ids.root)).toThrow()
  })
  it('reads the effective material card: corrected first row must equal its audit members', () => {
    const row = { movement_id: ids.roll, physical_at: at, recorded_at: at, movement_type: 'PURCHASE', qty_signed: '80.000000', original_qty_signed: '100.000000', running_qty: '80.000000', correction_count: '2', last_correction_recorded_at: at,
      corrections: [{ movement_id: ids.roll, qty_signed: '100.000000', movement_type: 'PURCHASE', recorded_at: at, physical_at: at, source_type: 'MATERIAL_PURCHASE_ROLL', reversal_of_id: null, note: null },
        { movement_id: ids.rev, qty_signed: '-100.000000', movement_type: 'REVERSAL', recorded_at: at, physical_at: at, source_type: 'MATERIAL_PURCHASE_REVERSAL', reversal_of_id: ids.roll, note: null },
        { movement_id: ids.rep, qty_signed: '80.000000', movement_type: 'PURCHASE', recorded_at: at, physical_at: at, source_type: 'MATERIAL_PURCHASE_ROLL', reversal_of_id: null, note: null }],
      source_type: 'MATERIAL_PURCHASE_ROLL', source_id: ids.roll, reversal_of_id: null, note: null }
    const card = { contract_version: 'cp7.material-ledger.v2', material_id: ids.mat, roll_id: ids.roll, location_id: ids.loc, read_at: at, financial_captured: false, history_basis: 'CORRECTED_EFFECTIVE_ROWS_CURRENT_RESTATED', page: { rows: [row], total: '1', offset: 0, limit: 25, next_offset: null } }
    expect(parseMaterialCard(card, false).page.rows[0].qty_signed).toBe('80.000000')
    expect(() => parseMaterialCard({ ...card, page: { ...card.page, rows: [{ ...row, qty_signed: '70.000000' }] } }, false)).toThrow()
    expect(() => parseMaterialCard(card, true)).toThrow()
  })
})
