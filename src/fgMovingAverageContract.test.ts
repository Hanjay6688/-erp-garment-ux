import {describe,expect,it}from'vitest'
import {parseFgWorkspace,parseFgLedger}from'./fgContract'
import original from'../tests/fixtures/skuMovingAverageReaderPg17.json'

const id='11111111-1111-4111-8111-111111111111',lot='22222222-2222-4222-8222-222222222222',at='2026-11-03T03:00:00Z'
const position={product_id:id,product_sku:'SKU-A',commercial_sku:'SKU-A',product_name:'Celana',size_code:'M',brand_name:'A',lot_id:lot,lot_number:'LOT-A',location_id:id,location_name:'Gudang',quality_grade:'GRADE_A'}
const balances={physical_qty:'2',reserved_qty:'1',available_qty:'1',quality:'KNOWN'}
const page=(rows:unknown[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
function workspace(valuation:unknown=original.known){return{contract_version:'cp7.fg-workspace.v1',purpose:'SUMMARY',read_at:at,knowledge:'CURRENT',quantity_basis:'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION',financial_captured:true,capabilities:{card:true},unit_code:'PCS',totals:balances,page:page([{...position,...balances,last_movement_at:at,valuation}])}}
function ledger(basis='CURRENT_RESTATED_SKU_POOL_MOVEMENT_SNAPSHOT',state='KNOWN',cost:string|null='23.750000'){
 const movement={id,physical_at:at,recorded_at:at,movement_type:'SALE_RESERVE',source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,customer_name:'A',notes:null,book_order:'1',commercial_sku_at_transaction:'SKU-A',qty_signed:'-1',reservation_delta:'1',physical_delta:'0',available_balance:'1',reserved_balance:'1',physical_balance:'2',original_physical_delta:'0',correction_count:'0',correction_recorded_at:null,audit_movements:[{id,physical_at:at,recorded_at:at,lot_id:lot,source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,available_delta:'-1',reservation_delta:'1'}],valuation:{state,unit_cost:cost,basis}}
 return{contract_version:'cp7.fg-ledger.v2',purpose:'CARD',read_at:at,knowledge:'CURRENT',financial_captured:true,position,balances,balance_basis:'COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',page:page([movement])}
}
describe('exact PostgreSQL17 pool reader output',()=>{
 it.each(['known','unknown','empty']as const)('accepts the actual isolated %s output without inventing a value',key=>{
  const value=parseFgWorkspace(workspace(original[key]),true,'SUMMARY').page.rows[0].valuation!
  expect(value).toEqual(original[key]);if(key!=='known'){expect(value.unit_cost).toBeNull();expect(value.value).toBeNull()}
 })
 it.each([
  {reserved_included:false},{reserved_included:undefined},{pool_revision:null},{pool_revision:'untrusted'},
  {hpp_version_id:id},{cost_state:'KNOWN'},{unit_cost:'23.7500001'},{state:'EMPTY'},
  {state:'UNKNOWN',unit_cost:'0',value:'0'},{unreviewed:1},
 ])('rejects a malformed pool valuation %j',mutation=>{
  expect(()=>parseFgWorkspace(workspace({...original.known,...mutation}),true,'SUMMARY')).toThrow()
 })
 it('refuses pooled valuation on another grade or without finance permission',()=>{
  const w=workspace();(w.page.rows[0]as Record<string,unknown>).quality_grade='BS'
  expect(()=>parseFgWorkspace(w,true,'SUMMARY')).toThrow()
  w.financial_captured=false;expect(()=>parseFgWorkspace(w,false,'SUMMARY')).toThrow()
 })
 it('preserves the exact original lot contract without accepting pool fields',()=>{
  const {pool_revision:_,reserved_included:__,...legacy}=original.known
  expect(parseFgWorkspace(workspace({...legacy,basis:'CURRENT_RESTATED_LOT_VALUE'}),true,'SUMMARY').page.rows).toHaveLength(1)
  expect(()=>parseFgWorkspace(workspace({...original.known,basis:'CURRENT_RESTATED_LOT_VALUE'}),true,'SUMMARY')).toThrow()
 })
 it('accepts known and unknown current SKU card values',()=>{
  expect(parseFgLedger(ledger(),true,'CARD',true).page.rows[0].valuation?.basis).toBe('CURRENT_RESTATED_SKU_POOL_MOVEMENT_SNAPSHOT')
  expect(parseFgLedger(ledger(undefined,'UNKNOWN',null),true,'CARD',true).page.rows[0].valuation?.unit_cost).toBeNull()
 })
 it('refuses pool card claims on the legacy endpoint or another grade',()=>{
  const v=ledger();v.contract_version='cp7.fg-ledger.v1'
  expect(()=>parseFgLedger(v,true,'CARD',false)).toThrow()
  v.contract_version='cp7.fg-ledger.v2';v.position={...position,quality_grade:'BS'}
  expect(()=>parseFgLedger(v,true,'CARD',true)).toThrow()
 })
})
