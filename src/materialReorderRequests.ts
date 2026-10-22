import {reorderWire as w} from './fgReorderContract'
import {materialPayload,type FabricRule,type MaterialDraft,type MaterialPayload,type MaterialType} from './materialReorderContract'

export type MaterialRequest={id:string;label:string;payload:MaterialPayload}
const bad=():never=>{throw Error('Catatan penyimpanan bahan belum bisa dibaca. Catatan tetap disimpan; jangan membuat penyimpanan pengganti sebelum hasilnya jelas.')}
export const materialRequestPrefix=(scope:string,type:MaterialType)=>'cp7:material-reorder:pending:v1:'+encodeURIComponent(scope)+':'+type+':'
const text=(v:unknown)=>typeof v==='string'?v:bad()
const maybeText=(v:unknown)=>v===null?'':text(v)
function request(raw:unknown,type:MaterialType):MaterialRequest{
 const x=w.obj(raw,'catatan penyimpanan bahan');w.keys(x,['contract_version','material_type','id','label','payload'],'catatan penyimpanan bahan')
 if(x.contract_version!=='cp7.material-request.v1'||x.material_type!==type)bad()
 const id=w.uuidText(x.id,'catatan penyimpanan bahan'),label=text(x.label),p=w.obj(x.payload,'catatan penyimpanan bahan')
 if(!label.trim()||label.length>400)bad()
 const choice=p.fabric_rule===undefined?undefined:w.oneOf(p.fabric_rule,['LEGACY_MINIMUM','FORMULA'] as const,'aturan kain')
 const draft:MaterialDraft={lead:maybeText(p.lead_days),manual:maybeText(p.manual_point),moq:maybeText(p.moq??null),usageMonth:maybeText(p.usage_month_qty??null),
  buffer:maybeText(p.buffer_days??null),reason:text(p.reason),...(choice?{fabricRule:choice as FabricRule}:{})}
 if(type==='FABRIC'&&p.manual_point!==null)bad()
 let legacy:string|null|undefined
 if(choice){legacy=p.expected_legacy_minimum_qty===null?null:text(p.expected_legacy_minimum_qty);if(legacy!==null&&!/^[0-9]{1,14}(\.[0-9]{1,6})?$/.test(legacy))bad()}
 const payload=materialPayload({materialId:w.uuidText(p.material_id,'catatan penyimpanan bahan'),settingRevision:w.count(p.expected_revision,'catatan penyimpanan bahan'),legacyMinimumQty:legacy},type,draft)
 const a=payload as unknown as Record<string,unknown>
 if(Object.keys(a).sort().join('|')!==Object.keys(p).sort().join('|')||Object.keys(a).some(k=>a[k]!==p[k]))bad()
 return{id,label,payload}
}
const envelope=(r:MaterialRequest,type:MaterialType)=>({contract_version:'cp7.material-request.v1',material_type:type,...r})
export function readMaterialRequests(scope:string,type:MaterialType):{pending:MaterialRequest[];error:string}{
 const pending:MaterialRequest[]=[]
 try{
  const prefix=materialRequestPrefix(scope,type)
  for(let i=0;i<localStorage.length;i++){
   const key=localStorage.key(i);if(!key?.startsWith(prefix))continue
   const saved=localStorage.getItem(key);if(saved===null)continue
   const r=request(JSON.parse(saved),type);if(key!==prefix+r.id)bad();pending.push(r)
  }
  pending.sort((a,b)=>a.id.localeCompare(b.id));return{pending,error:''}
 }catch{return{pending,error:'Catatan penyimpanan bahan belum bisa dibaca. Catatan tetap disimpan; periksa hasil penyimpanan yang sama sebelum membuat perubahan baru.'}}
}
export function persistMaterialRequest(scope:string,type:MaterialType,r:MaterialRequest){
 const checked=request(envelope(r,type),type),key=materialRequestPrefix(scope,type)+checked.id
 if(localStorage.getItem(key)!==null)bad()
 // Separate UUID keys retain both intents if two tabs race; neither overwrites
 // the other's unanswered request. The server's expected revision decides.
 try{localStorage.setItem(key,JSON.stringify(envelope(checked,type)))}
 catch{throw Error('Catatan penyimpanan belum bisa disimpan di perangkat ini. Data belum dikirim ke server.')}
}
export function clearMaterialRequest(scope:string,type:MaterialType,r:MaterialRequest){
 const key=materialRequestPrefix(scope,type)+r.id,raw=localStorage.getItem(key)
 if(raw===null)return
 const saved=request(JSON.parse(raw),type)
 if(JSON.stringify(saved)!==JSON.stringify(r))bad()
 try{localStorage.removeItem(key)}
 catch{throw Error('Jawaban server diterima, tetapi catatan di perangkat belum bisa diperbarui. Periksa penyimpanan yang sama.')}
}
/** These refusals occur after exact UUID replay lookup but before INSERT.
 * A previously committed same request would have returned its old outcome. */
export function materialRequestDefinitelyRefused(error:unknown){
 const message=error&&typeof error==='object'?(error as{message?:unknown}).message:null
 return typeof message==='string'&&/\bCP7_FORMULA_(MATERIAL_STALE|FABRIC_REFERENCE_CHANGED|FABRIC_REFERENCE_NOT_SET)\b/.test(message)
}
export function materialAccessDenied(error:unknown){
 if(!error||typeof error!=='object')return false
 const e=error as{status?:unknown;code?:unknown;message?:unknown}
 return e.status===403||e.code==='42501'||typeof e.message==='string'&&/\bCP7_FORMULA_(ACCESS_DENIED|MATERIAL_ACCESS_CHANGED)\b/.test(e.message)
}
