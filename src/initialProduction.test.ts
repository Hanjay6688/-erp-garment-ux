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
