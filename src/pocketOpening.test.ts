import { describe, it, expect } from 'vitest'
import { parsePocketOpening } from './pocketOpening'
const id = 'aaaabbbb-1234-4123-8234-000000000001'
const source = { id, document_number:'K1', line_number:'1', date:'2026-09-15', material_sku:'K', material_name:'Kantong', qty:'5.000000', original_amount:'11.25', amount:'11.25', allocation_status:'UNALLOCATED', prior_allocation_reference:null, receipt_backed:false, active_period:null }
const response = () => ({ opening_usage:[{...source}], opening_usage_count:1, opening_sewing:[], opening_sewing_count:0 })
describe('historical pocket workspace boundary',()=>{
  it('distinguishes absent predecessor extension from a known empty history',()=>{
    expect(parsePocketOpening({})).toBeNull()
    expect(parsePocketOpening({...response(), opening_usage:[], opening_usage_count:0})?.usage).toEqual([])
    expect(()=>parsePocketOpening({opening_usage:[]})).toThrow()
  })
  it('requires provenance, fixed money and matching source totals',()=>{
    expect(parsePocketOpening(response())?.usage[0].amount).toBe('11.25')
    expect(()=>parsePocketOpening({...response(), opening_usage_count:0})).toThrow()
    expect(()=>parsePocketOpening({...response(), opening_usage:[{...source, amount:null}]})).toThrow()
    expect(()=>parsePocketOpening({...response(), opening_usage:[{...source, allocation_status:'ALLOCATED'}]})).toThrow()
  })
  it('never converts malformed history into an empty or zero result',()=>{
    expect(()=>parsePocketOpening({...response(), opening_usage:[source,source], opening_usage_count:2})).toThrow()
    expect(()=>parsePocketOpening({...response(), opening_sewing:[{id,document_number:'J1',line_number:'1',date:'2026-09-15',contractor_name:'Afui',qty:2,target_kind:'COGS',sold_reference:null,target_reference:'SKU',allocated_amount:'2.25'}],opening_sewing_count:1})).toThrow()
  })
})
