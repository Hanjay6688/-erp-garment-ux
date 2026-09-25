import { describe, expect, it } from 'vitest'
import { parseInitialImportBD } from './initialImportBD'

const claim = { claim_id:'33333333-3333-4333-8333-333333333333', opening_item_id:'11111111-1111-4111-8111-111111111111', source_key:'WIP', po_number:'PO-1',
  claim_number:'KL-1', claim_type:'MISSING', origin:'IMPORT', vendor_code:'LDR', qty_claimed:1, recovered:0, claim_date:'2026-09-10',
  dispatch_number:null, cancelled:false, row_version:'1', compensation_amount:null }
const uninvoiced = { id:'55555555-5555-4555-8555-555555555555', vendor_code:'LDR', document_number:'TRM-1', receipt_date:'2026-09-10', category:'GOOD',
  qty:10, billed:6, estimate_status:'KNOWN', estimated_amount:'70000.00', released:'42000.00', invoiced:false, po_number:null, dispatch_number:'KRM-3', row_version:'1' }

describe('BD opening laundry states (ALL-W05)', () => {
  it('is absent on a server without BD and complete on one with BD', () => {
    expect(parseInitialImportBD({})).toBeNull()
    expect(parseInitialImportBD({ laundry_claims:[claim], laundry_uninvoiced:[uninvoiced] })).toMatchObject({
      laundry_claims:[{ claim_number:'KL-1' }], laundry_uninvoiced:[{ billed:6, released:'42000.00' }] })
  })
  it('refuses one collection without the other (an incomplete read is never "nothing")', () => {
    expect(() => parseInitialImportBD({ laundry_claims:[] })).toThrow('tidak terbaca lengkap')
  })
  it.each([
    { estimate_status:'KNOWN', estimated_amount:null },
    { estimate_status:'UNKNOWN', estimated_amount:'1.00' },
    { billed:11 },
    { category:'SPRAY' },
    { released:70000 },
  ])('refuses an uninvoiced return that does not add up %j', patch => {
    expect(() => parseInitialImportBD({ laundry_claims:[], laundry_uninvoiced:[{ ...uninvoiced, ...patch }] })).toThrow()
  })
  it('keeps an unknown estimate unknown (never zero)', () => {
    const result = parseInitialImportBD({ laundry_claims:[], laundry_uninvoiced:[{ ...uninvoiced, estimate_status:'UNKNOWN', estimated_amount:null, billed:0, released:'0.00' }] })
    expect(result?.laundry_uninvoiced[0].estimated_amount).toBeNull()
  })
})
