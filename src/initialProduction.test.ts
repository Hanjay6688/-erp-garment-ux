import { describe, expect, it } from 'vitest'
import { parseInitialProductionSources } from './initialProduction'

const row = { opening_item_id:'11111111-1111-4111-8111-111111111111', batch_id:'22222222-2222-4222-8222-222222222222',
  source_key:'001', po_number:'PO-001', balance_type:'WIP', stage:'SEWING', size_code:'M', qty_pcs:8, completed_qty_pcs:3, remaining_qty_pcs:5,
  contractor_name:'Epi', vendor_name:null, original_amount:'9007199254740993.01', current_amount:'9007199254740994.02', outputs:[] }
describe('opening production response boundary', () => {
  it('preserves exact money as text and distinct physical quantities', () => {
    expect(parseInitialProductionSources([row], true)[0]).toMatchObject({ original_amount:row.original_amount, current_amount:row.current_amount, remaining_qty_pcs:5 })
  })
  it('keeps the production reader free of finance values', () => {
    const result = parseInitialProductionSources([row])[0]
    expect(result).not.toHaveProperty('original_amount')
    expect(result).not.toHaveProperty('current_amount')
  })
  it.each([{remaining_qty_pcs:6}, {qty_pcs:8.5}, {stage:'MISSING'}, {outputs:null}, {original_amount:1.25}])('rejects inconsistent source responses %j', patch => {
    expect(() => parseInitialProductionSources([{...row, ...patch}], true)).toThrow()
  })
  it('refuses duplicated sources before rendering control totals', () => {
    expect(() => parseInitialProductionSources([row, row])).toThrow('dua kali')
  })
  it('treats a missing collection as unreadable and only an explicit list as zero', () => {
    expect(() => parseInitialProductionSources(undefined)).toThrow('tidak terbaca lengkap')
    expect(parseInitialProductionSources([])).toEqual([])
  })
})

describe('opening laundry claims (BD, ALL-W05)', () => {
  const claim = { claim_id:'33333333-3333-4333-8333-333333333333', claim_number:'KL-1', claim_type:'MISSING', origin:'IMPORT', qty_claimed:2,
    recovered:1, lost:0, state:'OPEN', claim_date:'2026-09-10', dispatch_number:'KRM-7', vendor_code:'LDR', row_version:'2',
    events:[{ event_id:'44444444-4444-4444-8444-444444444444', kind:'RECOVER', qty:1, date:'2026-09-20', resolution:null, reversed:false }] }
  const laundry = { ...row, stage:'LAUNDRY', contractor_name:null, vendor_name:'Laundry', qty_pcs:8, completed_qty_pcs:3, remaining_qty_pcs:4,
    bd:{ held_qty_pcs:1, lost_qty_pcs:0, claims:[claim] } }
  it('counts held pieces apart from the remaining WIP (remaining + completed + held = pieces away)', () => {
    const result = parseInitialProductionSources([laundry])[0]
    expect(result.bd).toMatchObject({ held_qty_pcs:1, lost_qty_pcs:0 })
    expect(result.bd?.claims[0]).toMatchObject({ claim_number:'KL-1', recovered:1, state:'OPEN' })
  })
  it.each([
    { remaining_qty_pcs:5 },
    { bd:{ held_qty_pcs:2, lost_qty_pcs:0, claims:[claim] } },
    { bd:{ held_qty_pcs:1, lost_qty_pcs:0, claims:[{ ...claim, recovered:0 }] } },
    { bd:{ held_qty_pcs:1, lost_qty_pcs:0, claims:[{ ...claim, state:'SOLD' }] } },
    { bd:{ held_qty_pcs:1, lost_qty_pcs:0 } },
    { stage:'SEWING' },
  ])('rejects a claim part that does not add up %j', patch => {
    expect(() => parseInitialProductionSources([{ ...laundry, ...patch }])).toThrow()
  })
  it('keeps a cancelled claim out of the held pieces', () => {
    const cancelled = { ...claim, origin:'CONTINUATION', state:'CANCELLED', recovered:0, events:[] }
    const result = parseInitialProductionSources([{ ...laundry, remaining_qty_pcs:5, bd:{ held_qty_pcs:0, lost_qty_pcs:0, claims:[cancelled] } }])[0]
    expect(result.bd?.held_qty_pcs).toBe(0)
  })
})
