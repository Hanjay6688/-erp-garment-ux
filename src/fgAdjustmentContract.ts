import type { Json } from './types/database.preconnect'
import type { MaterialPage } from './materialContract'
export type FgAdjustmentHeader={id:string;number:string;location_id:string;location_name:string;physical_at:string;reason_code:string;reason:string;notes:string|null;status:'DRAFT'|'POSTED'|'REVERSED';row_version:string;managed:boolean;line_count:string}
export type FgAdjustmentItem={id:string;product_id:string;product_sku:string;commercial_sku:string;size_code:string;lot_id:string;lot_number:string;quality_grade:string;qty_signed:string;notes:string|null;valuation?:{state:'KNOWN'|'UNKNOWN';hpp_version_id:string|null;hpp_version:string|null;cost_state:string|null;calculated_at:string|null;unit_cost:string|null;value:string|null;basis:'CURRENT_RESTATED_LOT_VALUE'}}
export type FgAdjustmentDetail=FgAdjustmentHeader&{items:FgAdjustmentItem[];editable:boolean}
export type FgAdjustments={contract_version:'cp7.fg-adjustments.v1';read_at:string;financial_captured:boolean;can_adjust:boolean;page:MaterialPage<FgAdjustmentHeader>;detail:FgAdjustmentDetail|null}
const fail=():never=>{throw Error('Dokumen penyesuaian FG belum lengkap atau tidak sesuai. Muat ulang.')}
const text=(v:unknown):v is string=>typeof v==='string'
const nullable=(v:unknown)=>v===null||text(v)
const id=(v:unknown):v is string=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const instant=(v:unknown)=>text(v)&&Number.isFinite(Date.parse(v))
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,29})$/.test(v)
const decimal=(v:unknown)=>text(v)&&/^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,6})?$/.test(v)
export const fgAdjustmentQty=(v:string)=>/^-?[1-9][0-9]{0,8}$/.test(v)?v:null
export function fgAdjustmentObject(v:unknown){if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
function closed(v:unknown,keys:string[],optional:string[]=[]){const r=fgAdjustmentObject(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)&&!optional.includes(k)))fail();return r}
const headerKeys=['id','number','location_id','location_name','physical_at','reason_code','reason','notes','status','row_version','managed','line_count']
function header(v:unknown,detail=false){
 const r=closed(v,headerKeys,detail?['items','editable']:[])
 if(!id(r.id)||!id(r.location_id)||!['number','location_name','reason_code','reason'].every(k=>text(r[k]))||!nullable(r.notes)||!instant(r.physical_at)||!['DRAFT','POSTED','REVERSED'].includes(String(r.status))||!whole(r.row_version)||r.row_version==='0'||typeof r.managed!=='boolean'||!whole(r.line_count))fail()
 return r
}
export function parseFgAdjustments(v:unknown,finance:boolean):FgAdjustments{
 const w=closed(v,['contract_version','read_at','financial_captured','can_adjust','page','detail'])
 if(w.contract_version!=='cp7.fg-adjustments.v1'||!instant(w.read_at)||w.financial_captured!==finance||typeof w.can_adjust!=='boolean')fail()
 const p=closed(w.page,['rows','total','offset','limit','next_offset'])
 if(!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||p.rows.length>Number(p.limit))return fail()
 const rows=p.rows.map(x=>header(x)),end=BigInt(Number(p.offset))+BigInt(rows.length),total=BigInt(p.total)
 if(new Set(rows.map(r=>r.id)).size!==rows.length||rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+rows.length||!rows.length||end>=total))fail()
 if(w.detail!==null){
  const d=header(w.detail,true)
  if(!Array.isArray(d.items)||BigInt(d.line_count as string)!==BigInt(d.items.length)||d.items.length>100||typeof d.editable!=='boolean'||d.editable&&(!d.managed||d.status!=='DRAFT'||!w.can_adjust))return fail()
  const items=d.items.map(v=>{const i=closed(v,['id','product_id','product_sku','commercial_sku','size_code','lot_id','lot_number','quality_grade','qty_signed','notes'],finance?['valuation']:[])
   if(!id(i.id)||!id(i.product_id)||!id(i.lot_id)||!['product_sku','commercial_sku','size_code','lot_number','quality_grade'].every(k=>text(i[k]))||!text(i.qty_signed)||!fgAdjustmentQty(i.qty_signed)||!nullable(i.notes))fail()
   if(finance){const x=closed(i.valuation,['state','hpp_version_id','hpp_version','cost_state','calculated_at','unit_cost','value','basis'])
    if(x.hpp_version_id!==null&&!id(x.hpp_version_id)||x.hpp_version!==null&&!whole(x.hpp_version)||!nullable(x.cost_state)||x.calculated_at!==null&&!instant(x.calculated_at)||x.basis!=='CURRENT_RESTATED_LOT_VALUE')fail()
    if(x.state==='KNOWN'){if(!decimal(x.unit_cost)||!decimal(x.value))fail()}else if(x.state!=='UNKNOWN'||x.unit_cost!==null||x.value!==null)fail()
   }return i
  });if(new Set(items.map(i=>i.id)).size!==items.length)fail()
 }
 return w as unknown as FgAdjustments
}
export function parseFgAdjustmentOutcome(v:unknown,request:string,action:string,payload:Json){
 const r=closed(v,['contract_version','kind','action','request_id','adjustment_id','status','row_version']),p=fgAdjustmentObject(payload)
 const status=action==='SAVE'?'DRAFT':action==='POST'?'POSTED':action==='DELETE'?'DELETED':'REVERSED',expected=p.id??p.adjustment_id
 if(r.contract_version!=='cp7.fg-adjustment-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.request_id!==request||r.action!==action||r.status!==status||!id(r.adjustment_id)||expected&&r.adjustment_id!==expected||status==='DELETED'&&r.row_version!==null||status!=='DELETED'&&(!whole(r.row_version)||r.row_version==='0'))fail()
 return r as unknown as {adjustment_id:string;status:string;row_version:string|null}
}
