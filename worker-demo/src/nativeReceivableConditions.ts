import {parseNativeAnalysis,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'
import {parseSalesRead,type SalesHeader} from './salesReadContract'
import {cp6WibDateTimeInput} from './cp6BusinessTime'
export const receivableStates=['DRAFT_ONLY','INACTIVE_DOCUMENT','UNKNOWN_BALANCE','CREDIT_REVIEW','ZERO_BALANCE','MISSING_DUE_DATE','OVERDUE','DUE_TODAY','NOT_DUE_YET']as const
type ReceivableState=typeof receivableStates[number]
type Condition={key:string;source_id:string;source_revision:string;native_source_hash:string;state:ReceivableState;business_resolved:boolean}
export type NativeReceivableConditions={analysis:NativeAnalysis;rows:{document:SalesHeader;condition:Condition}[];sourceHash:string;asOf:string;readAt:string;source:Record<string,unknown>}
const date=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const stamp=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&date(v.slice(0,10))&&Number.isFinite(Date.parse(v))&&Number(v.slice(11,13))<24
const fail=():never=>{throw Error('Sumber piutang belum lengkap atau tidak sesuai hak akses saat ini.')}
function closed(v:unknown,keys:string[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))return fail();return v as Record<string,unknown>}
function expectedState(h:SalesHeader,asOf:string):ReceivableState{
 const f=h.financial;if(!f)return fail()
 if(f.state==='DRAFT_PREVIEW')return'DRAFT_ONLY'
 if(f.state!=='ACTIVE_RECEIVABLE')return'INACTIVE_DOCUMENT'
 if(f.open_balance===null)return'UNKNOWN_BALANCE'
 if(/^-0(?:\.0{1,2})?$/.test(f.open_balance)||/^0(?:\.0{1,2})?$/.test(f.open_balance))return'ZERO_BALANCE'
 if(f.open_balance.startsWith('-'))return'CREDIT_REVIEW'
 if(h.due_date===null)return'MISSING_DUE_DATE'
 if(!date(h.due_date))return fail()
 return h.due_date<asOf?'OVERDUE':h.due_date===asOf?'DUE_TODAY':'NOT_DUE_YET'
}
export function parseNativeReceivableConditions(v:unknown,q:NativeDemandQuery,actor:string,finance:AnalysisFinanceAccess,canViewAR:boolean):NativeReceivableConditions{
 if(!canViewAR)return fail()
 const e=closed(v,['contract_version','actor_scope_id','analysis','source'])
 if(e.contract_version!=='cp7.native-ar-conditions.v1'||e.actor_scope_id!==actor)return fail()
 const analysis=parseNativeAnalysis(e.analysis,q,actor,finance),s=closed(e.source,['contract_version','basis','as_of','read_at','source_hash','pages','conditions','page_complete','total'])
 if(s.contract_version!=='cp7.native-ar-source.v1'||s.basis!=='ACCEPTED_P11_CURRENT_NATIVE_DOCUMENT'||s.page_complete!==true||!date(s.as_of)||!stamp(s.read_at)||cp6WibDateTimeInput(s.read_at).slice(0,10)!==s.as_of||!hash(s.source_hash)||typeof s.total!=='string'||!/^(0|[1-9][0-9]{0,3})$/.test(s.total)||BigInt(s.total)>5000n||!Array.isArray(s.pages)||!s.pages.length||s.pages.length>200||JSON.stringify(s.pages).length>4000000||!Array.isArray(s.conditions)||s.conditions.length!==Number(s.total))return fail()
 const documents:SalesHeader[]=[];let next=0
 for(let i=0;i<s.pages.length;i++){
  const p=parseSalesRead(s.pages[i],true)
  if(p.page.total!==s.total||p.page.offset!==next||p.page.limit!==25||p.detail!==null||!stamp(p.read_at)||p.read_at!==s.read_at||i<s.pages.length-1&&p.page.next_offset===null||i===s.pages.length-1&&p.page.next_offset!==null)return fail()
  documents.push(...structuredClone(p.page.rows));next+=p.page.rows.length
 }
 if(documents.length!==Number(s.total)||new Set(documents.map(h=>h.id)).size!==documents.length)return fail()
 const rows=documents.map((document,i)=>{
  if(document.due_date!==null&&!date(document.due_date)||!stamp(document.physical_at))return fail()
  const c=closed((s.conditions as unknown[])[i],['key','source_id','source_revision','native_source_hash','state','business_resolved']),state=expectedState(document,s.as_of as string)
  if(c.key!=='AR:'+document.id||c.source_id!==document.id||c.source_revision!==document.row_version||!hash(c.native_source_hash)||c.state!==state||c.business_resolved!==(state==='ZERO_BALANCE'))return fail()
  return{document,condition:structuredClone(c)as Condition}
 })
 return{analysis,rows,sourceHash:s.source_hash as string,asOf:s.as_of,readAt:s.read_at,source:structuredClone(s)}
}
export const receivableStateLabel:Record<ReceivableState,string>={DRAFT_ONLY:'Draft, belum menjadi piutang',INACTIVE_DOCUMENT:'Invoice tidak aktif',UNKNOWN_BALANCE:'Sisa tagihan belum diketahui',CREDIT_REVIEW:'Kredit pada invoice, perlu pemeriksaan',ZERO_BALANCE:'Tagihan tersisa nol',MISSING_DUE_DATE:'Jatuh tempo belum tercatat',OVERDUE:'Sudah lewat jatuh tempo',DUE_TODAY:'Jatuh tempo hari ini',NOT_DUE_YET:'Belum jatuh tempo'}
