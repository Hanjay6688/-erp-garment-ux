import {parseSalesRead,type SalesRead} from './salesReadContract'
const fail=():never=>{throw Error('Pembetulan nota belum cocok dengan sumber yang diperiksa. Muat ulang nota.')}
const object=(v:unknown)=>{if(!v||typeof v!=='object'||Array.isArray(v))return fail();return v as Record<string,unknown>}
const id=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
function instantMicros(v:unknown):bigint|null{
 if(typeof v!=='string')return null
 const m=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/.exec(v),ms=Date.parse(v)
 if(!m||!Number.isFinite(ms))return null
 return BigInt(ms)*1000n+BigInt((m[1]??'').padEnd(6,'0').slice(3))
}
const at=(v:unknown):v is string=>instantMicros(v)!==null
function closed(v:unknown,keys:string[]){const r=object(v);if(keys.some(k=>!(k in r))||Object.keys(r).some(k=>!keys.includes(k)))fail();return r}
export type NoteCorrectionHistory={revision_id:string;revision:string;previous_sale_id:string;replacement_sale_id:string;effective_at:string;recorded_at:string;reason:string}
export type NoteCorrectionWorkspace={contract_version:'cp7.note-correction-workspace.v1';read_at:string;root_sale_id:string;current_sale_id:string;history:NoteCorrectionHistory[];current:SalesRead;original_note_number:string;production_go:false}
export function parseNoteCorrectionWorkspace(v:unknown,requested:string):NoteCorrectionWorkspace{
 const r=closed(v,['contract_version','read_at','root_sale_id','current_sale_id','history','current','original_note_number','production_go'])
 if(r.contract_version!=='cp7.note-correction-workspace.v1'||!at(r.read_at)||!id(r.root_sale_id)||!id(r.current_sale_id)||!Array.isArray(r.history)||typeof r.original_note_number!=='string'||r.production_go!==false)return fail()
 let previous=r.root_sale_id;const seen=new Set<string>([previous]);let revision=0n
 for(const value of r.history){
  const h=closed(value,['revision_id','revision','previous_sale_id','replacement_sale_id','effective_at','recorded_at','reason'])
  if(!id(h.revision_id)||!id(h.previous_sale_id)||!id(h.replacement_sale_id)||h.previous_sale_id!==previous||seen.has(h.replacement_sale_id)||typeof h.revision!=='string'||!/^[1-9][0-9]{0,18}$/.test(h.revision)||BigInt(h.revision)!==revision+1n||!at(h.effective_at)||!at(h.recorded_at)||typeof h.reason!=='string'||h.reason.trim().length<5)return fail()
  previous=h.replacement_sale_id;seen.add(previous);revision++
 }
 if(previous!==r.current_sale_id||!seen.has(requested))return fail()
 const current=parseSalesRead(r.current,true);if(current.detail?.id!==r.current_sale_id)return fail()
 return {...r,current}as NoteCorrectionWorkspace
}
export function parseNoteCorrectionOutcome(v:unknown,request:string,source:string,effectiveAt:string){
 const r=closed(v,['contract_version','kind','action','request_id','root_sale_id','previous_sale_id','sale_id','revision_id','revision','effective_at'])
 if(r.contract_version!=='cp7.note-correction-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!=='CORRECT'||r.request_id!==request||r.previous_sale_id!==source||!id(r.root_sale_id)||!id(r.sale_id)||r.sale_id===source||!id(r.revision_id)||typeof r.revision!=='string'||!/^[1-9][0-9]{0,18}$/.test(r.revision)||!at(r.effective_at)||instantMicros(r.effective_at)!==instantMicros(effectiveAt))return fail()
 return r as typeof r&{sale_id:string}
}
