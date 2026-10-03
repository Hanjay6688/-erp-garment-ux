import type { MaterialPage } from './materialContract'

export type FgPurpose = 'SUMMARY' | 'CARD' | 'MOVEMENTS'
export type FgPosition = { product_id:string; product_sku:string; commercial_sku:string; product_name:string; size_code:string; brand_name:string; lot_id:string|null; lot_number:string|null; location_id:string; location_name:string; quality_grade:string }
type Balances = { available_qty:string; reserved_qty:string; physical_qty:string; quality:'KNOWN'|'CONFLICT' }
type Valuation = { state:'KNOWN'|'UNKNOWN'; hpp_version_id:string|null; hpp_version:string|null; cost_state:string|null; calculated_at:string|null; unit_cost:string|null; value:string|null; basis:'CURRENT_RESTATED_LOT_VALUE' }
export type FgRow = FgPosition & Balances & { last_movement_at:string; valuation?:Valuation }
export type FgWorkspace = { contract_version:'cp7.fg-workspace.v1'; purpose:FgPurpose; read_at:string; knowledge:'CURRENT'; quantity_basis:'PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION'; financial_captured:boolean; capabilities:{card:boolean}; unit_code:'PCS'; totals:Balances; page:MaterialPage<FgRow> }
export type FgMovement = { id:string; physical_at:string; recorded_at:string; movement_type:string; source_type:string; source_id:string|null; reversal_of_id:string|null; customer_name:string|null; notes:string|null; book_order:string; commercial_sku_at_transaction:string; qty_signed:string; reservation_delta:string; physical_delta:string; available_balance:string; reserved_balance:string; physical_balance:string; valuation?:{state:'KNOWN'|'UNKNOWN';unit_cost:string|null;basis:'CURRENT_RESTATED_MOVEMENT_SNAPSHOT'}; original_physical_delta?:string;correction_count?:string;correction_recorded_at?:string|null;audit_movements?:FgAuditMovement[] }
export type FgAuditMovement={id:string;physical_at:string;recorded_at:string;lot_id:string|null;source_type:string;source_id:string|null;reversal_of_id:string|null;available_delta:string;reservation_delta:string}
export type FgLedger = { contract_version:'cp7.fg-ledger.v1'|'cp7.fg-ledger.v2'; purpose:'CARD'|'MOVEMENTS'; read_at:string; knowledge:'CURRENT'; financial_captured:boolean; position:FgPosition; balances:Balances; balance_basis:'COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE'; page:MaterialPage<FgMovement> }
const fail = ():never => { throw Error('Data barang jadi belum lengkap atau tidak cocok dengan hak akses. Muat ulang.') }
const text = (v:unknown):v is string => typeof v==='string'
const id = (v:unknown):v is string => text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const nullableId = (v:unknown)=>v===null||id(v)
const nullableText = (v:unknown)=>v===null||text(v)
const whole = (v:unknown):v is string => text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const signed = (v:unknown):v is string => text(v)&&/^-?(0|[1-9][0-9]{0,29})$/.test(v)
const decimal = (v:unknown):v is string => text(v)&&/^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,6})?$/.test(v)
const instant = (v:unknown)=>text(v)&&Number.isFinite(Date.parse(v))
function closed(v:unknown,keys:string[],optional:string[]=[]){
  if(!v||typeof v!=='object'||Array.isArray(v))return fail()
  const r=v as Record<string,unknown>
  if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)&&!optional.includes(k)))fail()
  return r
}
const positionKeys=['product_id','product_sku','commercial_sku','product_name','size_code','brand_name','lot_id','lot_number','location_id','location_name','quality_grade']
function position(r:Record<string,unknown>){
  if(!id(r.product_id)||!id(r.location_id)||!nullableId(r.lot_id)||!nullableText(r.lot_number)||!['product_sku','commercial_sku','product_name','size_code','brand_name','location_name','quality_grade'].every(k=>text(r[k])))fail()
}
function balances(r:Record<string,unknown>){
  if(!signed(r.available_qty)||!signed(r.reserved_qty)||!signed(r.physical_qty)||!['KNOWN','CONFLICT'].includes(String(r.quality)))return fail()
  if(BigInt(r.physical_qty)!==BigInt(r.available_qty)+BigInt(r.reserved_qty))fail()
  if(r.quality==='KNOWN'&&[r.available_qty,r.reserved_qty,r.physical_qty].some(x=>BigInt(x)<0n))fail()
}
function page(v:unknown,check:(r:unknown)=>string){
  const p=closed(v,['rows','total','offset','limit','next_offset'])
  if(!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
  const end=BigInt(Number(p.offset))+BigInt(p.rows.length),total=BigInt(p.total)
  if(p.rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+p.rows.length||!p.rows.length||end>=total))fail()
  const keys=p.rows.map(check);if(new Set(keys).size!==keys.length)fail()
}
export function fgPositionKey(p:FgPosition){return `${p.product_id}:${p.lot_id}:${p.location_id}:${p.quality_grade}`}
export function parseFgWorkspace(v:unknown,finance:boolean,purpose:FgPurpose):FgWorkspace{
  const w=closed(v,['contract_version','purpose','read_at','knowledge','quantity_basis','financial_captured','capabilities','unit_code','totals','page'])
  if(w.contract_version!=='cp7.fg-workspace.v1'||w.purpose!==purpose||!instant(w.read_at)||w.knowledge!=='CURRENT'||w.quantity_basis!=='PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION'||w.financial_captured!==finance||w.unit_code!=='PCS')fail()
  if(typeof closed(w.capabilities,['card']).card!=='boolean')fail()
  balances(closed(w.totals,['available_qty','reserved_qty','physical_qty','quality']))
  page(w.page,v=>{
    const r=closed(v,[...positionKeys,'available_qty','reserved_qty','physical_qty','quality','last_movement_at'],finance?['valuation']:[])
    position(r);balances(r);if(!instant(r.last_movement_at))fail()
    if(finance){
      const x=closed(r.valuation,['state','hpp_version_id','hpp_version','cost_state','calculated_at','unit_cost','value','basis'])
      if(!nullableId(x.hpp_version_id)||x.hpp_version!==null&&!whole(x.hpp_version)||!nullableText(x.cost_state)||x.calculated_at!==null&&!instant(x.calculated_at)||x.basis!=='CURRENT_RESTATED_LOT_VALUE')fail()
      if(x.state==='KNOWN'){if(!decimal(x.unit_cost)||!decimal(x.value))fail()}
      else if(x.state!=='UNKNOWN'||x.unit_cost!==null||x.value!==null)fail()
    }
    return fgPositionKey(r as unknown as FgPosition)
  });return w as unknown as FgWorkspace
}
export function parseFgLedger(v:unknown,finance:boolean,purpose:'CARD'|'MOVEMENTS',corrected=false):FgLedger{
  const w=closed(v,['contract_version','purpose','read_at','knowledge','financial_captured','position','balances','balance_basis','page'])
  if(w.contract_version!==(corrected?'cp7.fg-ledger.v2':'cp7.fg-ledger.v1')||w.purpose!==purpose||!instant(w.read_at)||w.knowledge!=='CURRENT'||w.financial_captured!==finance||w.balance_basis!=='COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE')fail()
  position(closed(w.position,positionKeys));balances(closed(w.balances,['available_qty','reserved_qty','physical_qty','quality']))
  page(w.page,v=>{
    const r=closed(v,['id','physical_at','recorded_at','movement_type','source_type','source_id','reversal_of_id','customer_name','notes','book_order','commercial_sku_at_transaction','qty_signed','reservation_delta','physical_delta','available_balance','reserved_balance','physical_balance',...(corrected?['original_physical_delta','correction_count','correction_recorded_at','audit_movements']:[])],finance?['valuation']:[])
    if(!id(r.id)||!instant(r.physical_at)||!instant(r.recorded_at)||![r.movement_type,r.source_type,r.commercial_sku_at_transaction].every(text)||!nullableId(r.source_id)||!nullableId(r.reversal_of_id)||!nullableText(r.customer_name)||!nullableText(r.notes)||!signed(r.book_order)||!['qty_signed','reservation_delta','physical_delta','available_balance','reserved_balance','physical_balance'].every(k=>signed(r[k])))return fail()
    if(BigInt(String(r.physical_balance))!==BigInt(String(r.available_balance))+BigInt(String(r.reserved_balance))||BigInt(String(r.physical_delta))!==BigInt(String(r.qty_signed))+BigInt(String(r.reservation_delta)))fail()
    if(corrected){
      if(!signed(r.original_physical_delta)||!whole(r.correction_count)||r.correction_recorded_at!==null&&!instant(r.correction_recorded_at)||!Array.isArray(r.audit_movements)||!r.audit_movements.length)fail()
      if((BigInt(String(r.correction_count))===0n)!==(r.correction_recorded_at===null))fail()
      const selected=w.position as unknown as FgPosition,seen=new Set<string>();let available=0n,reserved=0n
      for(const value of r.audit_movements as unknown[]){const m=closed(value,['id','physical_at','recorded_at','lot_id','source_type','source_id','reversal_of_id','available_delta','reservation_delta'])
        if(!id(m.id)||seen.has(m.id)||!instant(m.physical_at)||!instant(m.recorded_at)||m.lot_id!==selected.lot_id||!text(m.source_type)||!nullableId(m.source_id)||!nullableId(m.reversal_of_id)||!signed(m.available_delta)||!signed(m.reservation_delta))fail()
        seen.add(m.id as string);available+=BigInt(String(m.available_delta));reserved+=BigInt(String(m.reservation_delta))
      }
      if(available!==BigInt(String(r.qty_signed))||reserved!==BigInt(String(r.reservation_delta)))fail()
    }
    if(finance){const f=closed(r.valuation,['state','unit_cost','basis']);if(f.basis!=='CURRENT_RESTATED_MOVEMENT_SNAPSHOT'||(f.state==='KNOWN'?!decimal(f.unit_cost):f.state!=='UNKNOWN'||f.unit_cost!==null))fail()}
    return r.id
  });return w as unknown as FgLedger
}
