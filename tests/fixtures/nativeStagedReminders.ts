import type {AnalysisPageSet,StagedAnalysis} from '../../src/nativeAnalysisPages'
// Reminders v2 wire shapes as staged-reminders.sql returns them, bound to a small synthetic staged run. Synthetic;
// the Native and HTTP evidence is the P19 reminders v2 suite.
type Json=Record<string,any>
export const actor='11111111-1111-4111-8111-111111111111'
export const run='22222222-2222-4222-8222-222222222222'
export const identityHash='e'.repeat(64)
export const dataAsOf='2026-10-08T01:00:00.000000+00:00'
export const query={from_date:'2026-01-01',through_date:'2026-10-07',group_mode:'AS_SOLD'} as const
const key=(i:number)=>`00000000-0000-4000-8000-${String(i).padStart(12,'0')}:44444444-4444-4444-8444-444444444444`
export const keys=[1,2,3].map(key)
export const set={runId:run,requestId:'66666666-6666-4666-8666-666666666666',identityHash,reference:{capturedAt:dataAsOf,sourceHash:'a'.repeat(64)},targetsTotal:3,pageCount:2,
 pages:[{index:0,targetLo:1,targetHi:2},{index:1,targetLo:3,targetHi:3}],totals:{targets:3,items:{recommendations:3},recommendations:{ACTIVE:3,PAUSED:0,STOPPED:0,OTHER:0},policyUnreviewed:0}} as unknown as AnalysisPageSet
export const staged={kind:'STAGED',set,header:{query,labels:keys.map((k,i)=>({key:k,sku:'SKU-'+(i+1),name:'Produk '+(i+1)}))}} as unknown as StagedAnalysis
export const policyId='77777777-7777-4777-8777-777777777777'
export const bindingId='88888888-8888-4888-8888-888888888888'
export const claimId='99999999-9999-4999-8999-999999999999'
export const fence='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
export const config={enabled:true,threshold_value:'1',threshold_unit:'PCS',cooldown_minutes:'0',quiet:{enabled:false,starts_at:null,ends_at:null,timezone:'Asia/Jakarta'}}
const policy={policy_id:policyId,rule_id:'PRODUCTION_GAP',scope_kind:'GLOBAL',scope_key:'*',revision:'1',previous_id:null,config,reason:'fixture',created_at:'2026-10-08T01:10:00.000000+00:00',created_by:actor}
export function setStatus(state:'RUNNING'|'DONE'|'FAILED',unitsDone:number,extra:Json={}){return{contract_version:'cp7.reminder-condition-set.v2',run_id:run,identity_hash:identityHash,data_as_of:dataAsOf,
 state,stage:state==='RUNNING'?(unitsDone<2?'PAGE':'SEAL'):null,units_done:unitsDone,unit_count:3,unit_attempts:0,pages_done:Math.min(unitsDone,2),page_count:2,targets_total:3,
 totals:state==='DONE'?{conditions:3,by_rule:{PRODUCTION_GAP:{ACTIVE:3}}}:null,set_hash:state==='DONE'?'f'.repeat(64):null,last_progress_at:'2026-10-08T01:20:00.000000+00:00',
 failure:state==='FAILED'?{unit:1,sqlstate:'P0001',code:'CP7_REMINDER_V2_SNAPSHOT_INVARIANT'}:null,worker_active:false,sent:false,...extra}}
export function condition(i:number,extra:Json={}){return{key:'PRODUCTION_GAP:'+key(i),rule_id:'PRODUCTION_GAP',target_key:key(i),source_id:key(i).split(':')[0],material_key:null,
 state:'ACTIVE',reason:'EXACT_SIZE_GAP_AT_SNAPSHOT',value:{state:'KNOWN',unit:'PCS',refs:[],value:String(3+i)},production_state:'ACTIVE',domain:'PRODUCTION',label:'SKU-'+i+' · Produk '+i,
 page_index:i<=2?0:1,ord:i,condition_hash:String(i).repeat(64).slice(0,64).replace(/[^0-9a-f]/g,'a'),kind:'SNAPSHOT',data_as_of:dataAsOf,economic_state:'NOT_APPLICABLE',
 financial_source:null,business_resolved:false,policy_binding:{rule_id:'PRODUCTION_GAP',target_key:key(i),basis:'GLOBAL',policy},
 policy_timing:{status:'READY',ready:true,checked_at:'2026-10-08T02:00:00.000000+00:00',next_at:null,meaning:'LOCAL_PREVIEW_ELIGIBILITY_ONLY_NOT_DELIVERY_OR_BUSINESS_RESOLUTION'},
 eligibility:'LOCAL_PREVIEW_ELIGIBLE',delivery_sent:false,eligibility_meaning:'LOCAL_PREVIEW_ONLY_NOT_BUSINESS_RESOLUTION',...extra}}
export function page(q:Json,rows=[condition(1),condition(2),condition(3)],extra:Json={}){return{contract_version:'cp7.reminder-conditions.v2',actor_scope_id:actor,run_id:run,identity_hash:identityHash,
 data_as_of:dataAsOf,set:setStatus('DONE',3),query:q,total:rows.length,rows,read_at:'2026-10-08T02:00:00.000000+00:00',eligibility_basis:'SNAPSHOT_VALUE_POLICY_AT_READ',
 recheck_required_before_preview:true,external_delivery_enabled:false,sent:false,...extra}}
export function binding(extra:Json={}){return{id:bindingId,revision:'1',previous_id:null,enabled:true,label:'Pratinjau lokal',environment:'LOCAL_TEST_SINK',rules:['PRODUCTION_GAP'],
 reason:'fixture',created_at:'2026-10-08T01:10:00.000000+00:00',...extra}}
export const body='PRATINJAU LOKAL — BELUM DIKIRIM\nKebutuhan produksi\nSKU-1 · Produk 1\nData analisis per 2026-10-08 08:00:00 WIB: kurang 4 PCS.\nDiperiksa ulang 2026-10-08 09:00:00 WIB: masih kurang sedikitnya 4 PCS (stok jadi dan barang dalam proses naik 0 PCS sejak analisis).\nIni pratinjau lokal. Masalah tetap diperiksa dari transaksi ERP.'
export function claim(extra:Json={}){return{id:claimId,run_id:run,identity_hash:identityHash,status:'CLAIMED',occurrence_key:'b'.repeat(64),binding_id:bindingId,environment:'LOCAL_TEST_SINK',
 condition_key:'PRODUCTION_GAP:'+key(1),rule_id:'PRODUCTION_GAP',kind:'SNAPSHOT',condition_hash:'1'.repeat(64),episode_id:'cccccccc-cccc-4ccc-8ccc-cccccccccccc',policy_id:policyId,
 recheck_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',finish_recheck_id:null,body_sha256:'c'.repeat(64),body,fence,created_at:'2026-10-08T02:00:00.000000+00:00',finished_at:null,reason:null,resolution:null,...extra}}
export function recheck(verdict:string,numbers:Json={},extra:Json={}){return{id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',request_id:'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',run_id:run,identity_hash:identityHash,
 condition_key:'PRODUCTION_GAP:'+key(1),rule_id:'PRODUCTION_GAP',kind:'SNAPSHOT',phase:'CLAIM',data_as_of:dataAsOf,checked_at:'2026-10-08T02:00:00.000000+00:00',verdict,
 reason:verdict==='RESOLVED_NOW'?'FINISHED_STOCK_AND_WIP_COVER_THE_NEED_NOW':'NEED_STILL_OPEN_NOW',numbers:{need_snapshot_pcs:'4',increase_pcs:verdict==='RESOLVED_NOW'?'4':'0',need_now_pcs:verdict==='RESOLVED_NOW'?'0':'4',threshold:'1',...numbers},
 policy_id:policyId,episode_id:null,created_at:'2026-10-08T02:00:00.000000+00:00',...extra}}
export function liveRecheck(verdict:string,i=1){const{id,request_id,run_id,identity_hash,phase,episode_id,created_at,policy_id,...rest}=recheck(verdict,{},{condition_key:'PRODUCTION_GAP:'+key(i)})
 void id;void request_id;void run_id;void identity_hash;void phase;void episode_id;void created_at;void policy_id
 return{contract_version:'cp7.reminder-recheck.v2',actor_scope_id:actor,run_id:run,...rest,label:'SKU-'+i+' · Produk '+i,target_key:key(i),snapshot_state:'ACTIVE',condition_hash:'1'.repeat(64),
  policy_binding:{rule_id:'PRODUCTION_GAP',target_key:key(i),basis:'GLOBAL',policy},recorded:false,external_delivery_enabled:false,sent:false}}
export function workspace(manage=true,extra:Json={}){return{contract_version:'cp7.reminder-workspace.v2',actor_scope_id:actor,run_id:run,identity_hash:identityHash,data_as_of:dataAsOf,
 conditions:setStatus('DONE',3),policies:[{policy_id:policyId,rule_id:'PRODUCTION_GAP',scope_kind:'GLOBAL',scope_key:'*',revision:'1',previous_id:null,config,reason:'fixture',
  created_at:'2026-10-08T01:10:00.000000+00:00',created_by:actor}],allowed_rules:['ACCESSORY_NEED','FABRIC_NEED','PRODUCTION_GAP'],manage_allowed:manage,
 missing_policy:'UNCONFIGURED_NOT_ZERO_NOT_DISABLED',binding:manage?binding():null,claims:[],rechecks:[],read_at:'2026-10-08T02:00:00.000000+00:00',
 external_delivery_enabled:false,scheduler_enabled:false,sent:false,...extra}}
export function command(operation:string,requestId:string,result:Json,c:Json|null=null,r:Json|null=null){return{contract_version:'cp7.reminder-command.v2',actor_scope_id:actor,operation,
 run_id:run,identity_hash:identityHash,result:{request_id:requestId,...result},claim:c,recheck:r,external_delivery_enabled:false,scheduler_enabled:false,sent:false}}
