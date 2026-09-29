import { materialObject, type MaterialPage } from './materialContract'
import type { Json } from './types/database.preconnect'
export type CountPreviewLine = { material_id:string; material_sku:string; material_name:string; unit_code:string; roll_id:string|null; roll_number:string|null; system_qty:string; physical_qty:string; qty_signed:string; basis_token:string }
export type CountPreview = { contract_version:'cp7.material-count-preview.v1'; read_at:string; location_id:string; physical_at:string; basis:'POSTED_PHYSICAL_AT_COUNT_CURRENT_KNOWLEDGE'; items:CountPreviewLine[] }
export type CountRow = { id:string; number:string; location_id:string|null; location_name:string|null; physical_at:string; reason_code:string; status:'DRAFT'|'POSTED'|'REVERSED'; row_version:string; notes:string|null; managed_count:boolean; line_count:string }
export type CountItem = { id:string; material_id:string; material_sku:string; material_name:string; unit_code:string; roll_id:string|null; roll_number:string|null; qty_signed:string; physical_qty:string|null; notes:string|null; valuation?:{input_unit_cost:string|null;restated_value:string|null;basis:'CURRENT_RESTATED_DOCUMENT_NOT_STOCK'} }
export type CountDetail = CountRow & {items:CountItem[];edit:{physical_qty:string;input_unit_cost?:string|null}|null}
export type CountWorkspace = {contract_version:'cp7.material-counts.v1';read_at:string;financial_captured:boolean;capabilities:{adjust:boolean;reverse:boolean};page:MaterialPage<CountRow>;detail:CountDetail|null}
const fail=():never=>{throw Error('Data hitung fisik belum lengkap. Muat ulang sebelum melanjutkan.')}
const text=(v:unknown):v is string=>typeof v==='string'
const nullable=(v:unknown)=>v===null||text(v)
const exact=(v:unknown):v is string=>text(v)&&/^-?(0|[1-9][0-9]{0,29})(\.[0-9]{1,6})?$/.test(v)
const id=(v:unknown):v is string=>text(v)&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const at=(v:unknown)=>text(v)&&Number.isFinite(Date.parse(v))
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,18})$/.test(v)
const version=(v:unknown)=>whole(v)&&v!=='0'
const closed=(v:unknown,keys:string[])=>{const o=materialObject(v);if(keys.some(k=>!(k in o))||Object.keys(o).some(k=>!keys.includes(k)))fail();return o}
export function countNonzero(v:string){return /[1-9]/.test(v)}
export function countPositive(v:string){return !v.startsWith('-')&&countNonzero(v)}
export function parseCountPreview(v:unknown):CountPreview {
 const p=closed(v,['contract_version','read_at','location_id','physical_at','basis','items'])
 if(p.contract_version!=='cp7.material-count-preview.v1'||!at(p.read_at)||!id(p.location_id)||!at(p.physical_at)||p.basis!=='POSTED_PHYSICAL_AT_COUNT_CURRENT_KNOWLEDGE'||!Array.isArray(p.items)||!p.items.length||p.items.length>100)fail()
 const keys=(p.items as unknown[]).map(v=>{const r=closed(v,['material_id','material_sku','material_name','unit_code','roll_id','roll_number','system_qty','physical_qty','qty_signed','basis_token']);if(!id(r.material_id)||r.roll_id!==null&&!id(r.roll_id)||!nullable(r.roll_number)||![r.material_sku,r.material_name,r.unit_code].every(text)||![r.system_qty,r.physical_qty,r.qty_signed].every(exact)||!text(r.basis_token)||!/^[0-9a-f]{32}$/.test(r.basis_token))fail();return `${r.material_id}:${r.roll_id}`})
 if(new Set(keys).size!==keys.length)fail();return p as unknown as CountPreview
}
const headerKeys=['id','number','location_id','location_name','physical_at','reason_code','status','row_version','notes','managed_count','line_count']
function header(v:unknown,detail=false){const r=closed(v,[...headerKeys,...(detail?['items','edit']:[])]);if(!id(r.id)||r.location_id!==null&&!id(r.location_id)||!nullable(r.location_name)||![r.number,r.reason_code].every(text)||!at(r.physical_at)||!['DRAFT','POSTED','REVERSED'].includes(String(r.status))||!version(r.row_version)||!nullable(r.notes)||typeof r.managed_count!=='boolean'||!whole(r.line_count))fail();return r}
export function parseCounts(v:unknown,finance:boolean):CountWorkspace {
 const w=closed(v,['contract_version','read_at','financial_captured','capabilities','page','detail'])
 if(w.contract_version!=='cp7.material-counts.v1'||!at(w.read_at)||w.financial_captured!==finance)fail()
 const c=closed(w.capabilities,['adjust','reverse']);if(Object.values(c).some(v=>typeof v!=='boolean')||c.reverse&&!c.adjust)fail()
 const p=closed(w.page,['rows','total','offset','limit','next_offset']);if(!Array.isArray(p.rows)||!whole(p.total)||!Number.isSafeInteger(p.offset)||Number(p.offset)<0||!Number.isSafeInteger(p.limit)||Number(p.limit)<1||Number(p.limit)>100||(p.rows as unknown[]).length>Number(p.limit))fail()
 const rows=p.rows as unknown[],end=BigInt(Number(p.offset))+BigInt(rows.length),total=BigInt(String(p.total))
 if(rows.length&&end>total||end<total&&p.next_offset===null||p.next_offset!==null&&(p.next_offset!==Number(p.offset)+rows.length||!rows.length||end>=total))fail()
 const ids=rows.map(x=>header(x).id);if(new Set(ids).size!==ids.length)fail()
 if(w.detail!==null){const d=header(w.detail,true);if(!Array.isArray(d.items)||d.items.length>100||String(d.items.length)!==d.line_count)fail()
  const keys=(d.items as unknown[]).map(v=>{const r=closed(v,['id','material_id','material_sku','material_name','unit_code','roll_id','roll_number','qty_signed','physical_qty','notes',...(finance?['valuation']:[])]);if(!id(r.id)||!id(r.material_id)||r.roll_id!==null&&!id(r.roll_id)||!nullable(r.roll_number)||![r.material_sku,r.material_name,r.unit_code].every(text)||!exact(r.qty_signed)||r.physical_qty!==null&&!exact(r.physical_qty)||!nullable(r.notes))fail()
   if(finance){const a=closed(r.valuation,['input_unit_cost','restated_value','basis']);if(a.basis!=='CURRENT_RESTATED_DOCUMENT_NOT_STOCK'||a.input_unit_cost!==null&&!exact(a.input_unit_cost)||a.restated_value!==null&&!exact(a.restated_value))fail()}return r.id})
  if(new Set(keys).size!==keys.length)fail()
  if(d.edit!==null){const e=closed(d.edit,['physical_qty',...(finance?['input_unit_cost']:[])]);if(d.status!=='DRAFT'||!d.managed_count||keys.length!==1||!exact(e.physical_qty)||e.physical_qty.startsWith('-')||finance&&e.input_unit_cost!==null&&!exact(e.input_unit_cost))fail()}
 }
 return w as unknown as CountWorkspace
}
export function parseCountOutcome(v:unknown,request:string,action:string,payload:Json){const r=closed(v,['contract_version','kind','action','request_id','adjustment_id','status','row_version']);const p=materialObject(payload)
 if(r.contract_version!=='cp7.material-count-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!==action||r.request_id!==request||!id(r.adjustment_id)||r.status!==({SAVE:'DRAFT',POST:'POSTED',DELETE:'DELETED',REVERSE:'REVERSED'} as Record<string,string>)[action]||(action==='DELETE'?r.row_version!==null:!version(r.row_version))||action!=='SAVE'&&r.adjustment_id!==p.adjustment_id||action==='SAVE'&&p.id&&r.adjustment_id!==p.id)fail()
 return r as {adjustment_id:string;status:string;row_version:string|null}
}
