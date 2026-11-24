import type {PlanSaved} from './nativePlanDraft'
export type PlanActualFact={state:'KNOWN';unit:'PCS';value:string;refs:PlanActualRef[]}|{state:'UNKNOWN';unit:'PCS';reason:string;refs:PlanActualRef[]}
type PlanActualRef={kind:string;id:string;revision:string|null}
export const planActualLabels={input_pcs:'Potongan tercatat',wip_pcs:'Masih dalam proses',group_fg_pcs:'FG dari kelompok ini',bs_pcs:'BS tercatat',withheld_pcs:'Ditahan, hilang, atau tersangkut',exited_pcs:'Keluar dari produksi',matched_fg_pcs:'FG sesuai produk dan size rencana',other_root_fg_pcs:'FG untuk produk lain'} as const
type Metric=keyof typeof planActualLabels
export type PlanActual={planned:string;capturedAt:string;state:'NOT_STARTED'|'COMPLETE'|'UNKNOWN'|'CONFLICT';reason:string;originalState:'UNCHANGED'|'ARCHIVED_STALE';sourceHash:string;nativeGroup:{id:string;number:string;revision:string;posted:boolean}|null;facts:Record<Metric,PlanActualFact>;remaining:PlanActualFact;positions:{key:string;stage:string;quantity:string;rootId:string|null;refs:PlanActualRef[]}[]}
const fail=():never=>{throw Error('Hasil produksi belum dapat dicocokkan dengan rencana dan sumber ERP.')}
const record=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
function closed(v:unknown,keys:string[]){const r=record(v);if(Object.keys(r).sort().join('|')!==keys.sort().join('|'))return fail();return r}
const text=(v:unknown):string=>typeof v==='string'&&v.length>0&&v.length<=4000?v:fail()
const guid=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const hash=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const pcs=(v:unknown):string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)?v:fail()
const revision=(v:unknown):string=>typeof v==='string'&&/^[1-9][0-9]{0,18}$/.test(v)?v:fail()
function refs(v:unknown):PlanActualRef[]{if(!Array.isArray(v)||v.length>1000)return fail();return v.map((x:unknown)=>{const r=closed(x,['kind','id','revision']);return{kind:text(r.kind),id:text(r.id),revision:r.revision===null?null:text(r.revision)}})}
function fact(v:unknown):PlanActualFact{const r=record(v);if(r.unit!=='PCS')return fail();if(r.state==='KNOWN'){closed(r,['state','unit','value','refs']);return{state:'KNOWN',unit:'PCS',value:pcs(r.value),refs:refs(r.refs)}}if(r.state==='UNKNOWN'){closed(r,['state','unit','reason','refs']);return{state:'UNKNOWN',unit:'PCS',reason:text(r.reason),refs:refs(r.refs)}}return fail()}
const wipStages=['CUT_UNASSIGNED','SEWING_ACTIVE','SEWING_UNRESOLVED','LAUNDRY_OUTSTANDING','AWAIT_QC','REWORK','REWASH']
export function parsePlanActual(v:unknown,actor:string,saved:PlanSaved):PlanActual{
 const r=closed(v,['contract_version','actor_scope_id','draft_id','plan_id','revision','run_id','target_key','original_source_hash','composition_hash','planned_pcs','planned_basis','native_intent_id','actual','remaining_to_plan_pcs','comparison_scope','reservation_created','production_go'])
 if(r.contract_version!=='cp7.plan-actual.v1'||r.actor_scope_id!==actor||r.draft_id!==saved.id||r.plan_id!==saved.planId||r.revision!==saved.revision||r.run_id!==saved.runId||r.target_key!==saved.targetKey||r.original_source_hash!==saved.sourceHash||r.native_intent_id!==(saved.native?.id??null)||r.planned_basis!=='IMMUTABLE_OPERATOR_DRAFT_ESTIMATE'||r.comparison_scope!=='LINKED_DRAFT_ONLY_NOT_ALL_PO_OR_WAREHOUSE'||r.reservation_created!==false||r.production_go!==false)return fail()
 guid(r.draft_id);guid(r.plan_id);guid(r.run_id);revision(r.revision);hash(r.original_source_hash);hash(r.composition_hash)
 const parts=saved.targetKey.split(':');if(parts.length!==2)return fail();parts.forEach(guid)
 const a=closed(r.actual,['captured_at','source_hash','state','reason','original_source_state','native_group','size_id','physical_root_id','facts','positions','scope','fg_basis'])
 if(a.size_id!==parts[1]||a.physical_root_id!==parts[0]||a.scope!=='ONE_LINKED_NATIVE_GROUP_EXACT_SIZE'||a.fg_basis!=='PRODUCTION_DISPOSITION_NOT_CURRENT_ON_HAND'||!['NOT_STARTED','COMPLETE','UNKNOWN','CONFLICT'].includes(String(a.state))||!['UNCHANGED','ARCHIVED_STALE'].includes(String(a.original_source_state)))return fail()
 const capturedAt=text(a.captured_at);if(!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(capturedAt)||!Number.isFinite(Date.parse(capturedAt)))return fail()
 let nativeGroup:PlanActual['nativeGroup']=null
 if(a.native_group!==null){const g=closed(a.native_group,['id','number','po_id','model_id','revision','cut_at','material_issue_posted','status']);if(g.id!==saved.native?.groupId||typeof g.material_issue_posted!=='boolean'||!Number.isFinite(Date.parse(text(g.cut_at))))return fail();guid(g.po_id);guid(g.model_id);text(g.status);nativeGroup={id:guid(g.id),number:text(g.number),revision:revision(g.revision),posted:g.material_issue_posted}}
 if(a.state==='COMPLETE'&&!nativeGroup?.posted||a.state==='NOT_STARTED'&&nativeGroup?.posted||saved.native===null&&a.state!=='NOT_STARTED')return fail()
 const rawFacts=closed(a.facts,Object.keys(planActualLabels));const facts={}as PlanActual['facts'];for(const key of Object.keys(planActualLabels)as Metric[])facts[key]=fact(rawFacts[key]);const remaining=fact(r.remaining_to_plan_pcs),planned=pcs(r.planned_pcs)
 if(a.state==='UNKNOWN'||a.state==='CONFLICT'){if(Object.values(facts).some(f=>f.state!=='UNKNOWN'))return fail()}
 else if(a.state==='NOT_STARTED'){if(Object.values(facts).some(f=>f.state!=='KNOWN'||f.value!=='0'))return fail()}
 else{const base=(['input_pcs','wip_pcs','group_fg_pcs','bs_pcs','withheld_pcs','exited_pcs']as Metric[]).map(k=>facts[k]);if(base.some(f=>f.state!=='KNOWN'))return fail();const n=base.map(f=>BigInt((f as Extract<PlanActualFact,{state:'KNOWN'}>).value));if(n[0]!==n.slice(1).reduce((x,y)=>x+y,0n))return fail()}
 const matched=facts.matched_fg_pcs,other=facts.other_root_fg_pcs,group=facts.group_fg_pcs
 if((matched.state==='KNOWN')!==(other.state==='KNOWN'))return fail()
 if(matched.state==='KNOWN'){if(group.state!=='KNOWN'||other.state!=='KNOWN'||BigInt(matched.value)+BigInt(other.value)!==BigInt(group.value)||remaining.state!=='KNOWN'||BigInt(remaining.value)!==(BigInt(planned)>BigInt(matched.value)?BigInt(planned)-BigInt(matched.value):0n))return fail()}else if(remaining.state!=='UNKNOWN')return fail()
 if(!Array.isArray(a.positions)||a.positions.length>10000)return fail()
 const stages=[...wipStages,'FG','BS','MISSING','STUCK','HOLD','EXIT'],sum={wip:0n,fg:0n,bs:0n,withheld:0n,exited:0n,matched:0n,other:0n};let fgIdentified=true
 const positions=a.positions.map((value:unknown)=>{const p=closed(value,['key','pool_key','stage','refs','size_id','ownership','remaining_pcs','quantity_quality','eligible_company_wip','fg_identity']),stage=text(p.stage),quantity=pcs(p.remaining_pcs),n=BigInt(quantity)
  if(p.pool_key!==`CUT:${saved.native?.groupId}:${parts[1]}`||p.size_id!==parts[1]||p.ownership!=='COMPANY'||p.quantity_quality!=='KNOWN'||!stages.includes(stage)||p.eligible_company_wip!==wipStages.includes(stage))return fail()
  const category=wipStages.includes(stage)?'wip':stage==='FG'?'fg':stage==='BS'?'bs':stage==='EXIT'?'exited':'withheld';sum[category]+=n
  let rootId:string|null=null
  if(p.fg_identity!==null){const i=closed(p.fg_identity,['position_key','root_id','size_id']);if(stage!=='FG'||n===0n||i.position_key!==p.key||i.size_id!==parts[1])return fail();rootId=guid(i.root_id);sum[rootId===parts[0]?'matched':'other']+=n}else if(stage==='FG'&&n>0n)fgIdentified=false
  return{key:text(p.key),stage,quantity,rootId,refs:refs(p.refs)}
 })
 if(new Set(positions.map(p=>p.key)).size!==positions.length)return fail()
 if(a.state!=='COMPLETE'&&positions.length>0)return fail()
 if(a.state==='COMPLETE'){for(const[key,category]of[['wip_pcs','wip'],['group_fg_pcs','fg'],['bs_pcs','bs'],['withheld_pcs','withheld'],['exited_pcs','exited']]as const){const f=facts[key];if(f.state!=='KNOWN'||BigInt(f.value)!==sum[category])return fail()}if(fgIdentified!== (matched.state==='KNOWN'))return fail();if(fgIdentified&&(matched.state!=='KNOWN'||other.state!=='KNOWN'||BigInt(matched.value)!==sum.matched||BigInt(other.value)!==sum.other))return fail()}
 return{planned,capturedAt,state:a.state as PlanActual['state'],reason:text(a.reason),originalState:a.original_source_state as PlanActual['originalState'],sourceHash:hash(a.source_hash),nativeGroup,facts,remaining,positions}
}
export function planActualValue(f:PlanActualFact){return f.state==='KNOWN'?`${f.value} PCS`:'Belum diketahui'}
export function planActualStage(stage:string){return({CUT_UNASSIGNED:'Belum diambil',SEWING_ACTIVE:'Dalam jahit',SEWING_UNRESOLVED:'Sebelum laundry; rincian potong dan jahit belum terbukti',LAUNDRY_OUTSTANDING:'Di laundry',AWAIT_QC:'Menunggu QC',FG:'FG',BS:'BS',MISSING:'Hilang',STUCK:'Tersangkut',HOLD:'Ditahan',REWORK:'Perbaikan',REWASH:'Cuci ulang',EXIT:'Keluar'}as Record<string,string>)[stage]??stage}
