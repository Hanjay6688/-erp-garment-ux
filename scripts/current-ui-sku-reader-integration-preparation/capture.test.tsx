// @vitest-environment jsdom
// Actual connected component markup; synthetic read/auth providers only.
import {act}from'react'
import{createRoot}from'react-dom/client'
import{it,expect,vi}from'vitest'
import{mkdirSync,writeFileSync}from'node:fs'
import{resolve}from'node:path'
import ConnectedFgStockPage from '../../src/ConnectedFgStockPage'
import{recoveryIdentity}from'../../tests/fixtures/productionRecovery'
import pool from'../../tests/fixtures/skuMovingAverageReaderPg17.json'
import{persistProductionEnvelope}from'../../src/productionRecovery'
const current=vi.hoisted(()=>({auth:null as unknown,mode:'known',calls:[] as string[]}))
const reader=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../src/auth/AuthProvider',()=>({useAuth:()=>current.auth}))
vi.mock('../../src/lib/supabase',()=>({getUatSupabaseClient:()=>reader}))
vi.mock('../../src/NativeDemandHistoryPanel',()=>({default:()=>null}))
const id='11111111-1111-4111-8111-111111111111',lot='22222222-2222-4222-8222-222222222222',at='2026-11-03T03:00:00Z'
const position={product_id:id,product_sku:'SKU-PHYSICAL',commercial_sku:'LUNA',product_name:'Celana denim',size_code:'M',brand_name:'Vivo',lot_id:lot,lot_number:'LOT-01',location_id:id,location_name:'Gudang barang jadi utama',quality_grade:'GRADE_A'}
const balances={physical_qty:'2',reserved_qty:'1',available_qty:'1',quality:'KNOWN'}
const page=<T,>(rows:T[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
const modes=['known','unknown','empty','loading','error','pending','operations']
it('captures all seven connected FG reader states with no business write calls',async()=>{
 const directory=process.env.CP7_UI_FG_CAPTURE_DIRECTORY
 if(!directory)throw Error('CP7_UI_FG_CAPTURE_DIRECTORY_REQUIRED')
 mkdirSync(directory,{recursive:true});Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true})
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:unknown,_o:unknown,fn:(l:object)=>unknown)=>fn({})}})
 const observations=[]
 for(const mode of modes){
  localStorage.clear();current.mode=mode;current.calls=[];const a=structuredClone(recoveryIdentity)
  a.identity.permissions.push('warehouse.stock.view',...(mode==='operations'?[]:['finance.hpp.view']));current.auth=a
  if(mode==='pending'){
   const intent={action:'SAVE_PAIR',payload:{source_product_id:id,target_product_id:lot},expectedVersion:null}
   persistProductionEnvelope('disposable:actor-1','SKU',{...intent,fingerprint:JSON.stringify(intent),id,createdAt:at})
  }
  reader.rpc.mockImplementation(async(name:string,args:{p_query:Record<string,unknown>})=>{
   current.calls.push(name)
   if(!['erp_cp7_get_fg_v1','erp_cp7_get_fg_ledger_v2'].includes(name))throw Error('UNEXPECTED_READ_OR_WRITE:'+name)
   if(mode==='loading')return new Promise(()=>{})
   if(mode==='error')return{data:null,error:{status:503,message:'Stok belum berhasil dimuat. Coba muat ulang.'}}
   const finance=mode!=='operations',known=mode!=='unknown',empty=mode==='empty'
   if(name==='erp_cp7_get_fg_v1')return{error:null,data:{contract_version:'cp7.fg-workspace.v1',purpose:'CARD',read_at:at,knowledge:'CURRENT',quantity_basis:'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION',financial_captured:finance,capabilities:{card:true},unit_code:'PCS',totals:empty?{...balances,physical_qty:'0',reserved_qty:'0',available_qty:'0'}:balances,page:page(empty?[]:[{...position,...balances,last_movement_at:at,...(finance?{valuation:known?pool.known:pool.unknown}:{})}])}}
   const movement={id,physical_at:at,recorded_at:at,movement_type:'SALE_RESERVE',source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,customer_name:'Toko contoh',notes:'Cadangan penjualan tetap termasuk stok milik perusahaan.',book_order:'1',original_physical_delta:'0',correction_count:'0',correction_recorded_at:null,audit_movements:[{id,physical_at:at,recorded_at:at,lot_id:lot,source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,available_delta:'-1',reservation_delta:'1'}],commercial_sku_at_transaction:'LUNA',qty_signed:'-1',reservation_delta:'1',physical_delta:'0',available_balance:'1',reserved_balance:'1',physical_balance:'2',...(finance?{valuation:{state:known?'KNOWN':'UNKNOWN',unit_cost:known?pool.known.unit_cost:null,basis:'CURRENT_RESTATED_SKU_POOL_MOVEMENT_SNAPSHOT'}}:{})}
   return{error:null,data:{contract_version:'cp7.fg-ledger.v2',purpose:'CARD',read_at:at,knowledge:'CURRENT',financial_captured:finance,position,balances,balance_basis:'COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',page:{...page([movement]),list:{q:args.p_query.q,movement_type:args.p_query.movement_type,order:args.p_query.order,movement_types:['SALE_RESERVE']}}}}
  })
  const container=document.createElement('div');document.body.append(container);const root=createRoot(container)
  try{
   await act(async()=>root.render(<ConnectedFgStockPage purpose="CARD"/>));await act(async()=>{await new Promise(r=>setTimeout(r,0))})
   if(['known','unknown','operations'].includes(mode)){
    const button=container.querySelector<HTMLButtonElement>('.cfg-position button');expect(button).toBeTruthy()
    await act(async()=>button!.click());await act(async()=>{await new Promise(r=>setTimeout(r,0))})
   }
   if(mode==='known'){expect(container.textContent).toContain('HPP SKU saat ini Rp23,75');expect(container.textContent).toContain('47,5')}
   if(mode==='unknown'){expect(container.textContent).toContain('Biaya belum lengkap');expect(container.textContent).not.toContain('Rp0')}
   if(mode==='operations')expect(container.textContent).not.toContain('Rp')
   if(mode==='loading')expect(container.textContent).toContain('Memuat stok barang jadi')
   if(mode==='error')expect(container.textContent).toContain('Layanan UAT belum dapat dihubungi. Coba lagi setelah status diperiksa.')
   if(mode==='pending')expect(container.textContent).toContain('Hasil transaksi belum diketahui')
   if(mode==='empty')expect(container.querySelector('.cfg-position')).toBeNull()
   writeFileSync(resolve(directory,mode+'.html'),container.innerHTML)
   observations.push({mode,calls:[...current.calls],html:mode+'.html',actual_ERP_cases:0})
  }finally{await act(async()=>root.unmount());container.remove()}
 }
 localStorage.clear();Reflect.deleteProperty(navigator,'locks')
 writeFileSync(resolve(directory,'FG_DOM_CAPTURE.json'),JSON.stringify({status:'PASS',classification:'ACTUAL_COMPONENT_MARKUP_WITH_SYNTHETIC_READ_AUTH_PROVIDERS',observations,actual_ERP_cases:0,actual_Auth_cases:0,production_go:false},null,2)+'\n')
})
