import type {AnalysisPageSet,StagedAnalysis} from '../../src/nativeAnalysisPages'
// AI v2 brief wire shape as ai-staged.sql returns it, bound to a small synthetic page set. Synthetic;
// the Native and HTTP evidence is the P19 AI v2 suite.
type Json=Record<string,any>
export const actor='11111111-1111-4111-8111-111111111111'
export const run='22222222-2222-4222-8222-222222222222'
export const requestId='66666666-6666-4666-8666-666666666666'
export const identityHash='e'.repeat(64)
export const dataAsOf='2026-10-08T01:00:00.000000+00:00'
export const query={from_date:'2026-01-01',through_date:'2026-10-07',group_mode:'AS_SOLD'} as const
const key=(i:number)=>`00000000-0000-4000-8000-${String(i).padStart(12,'0')}:44444444-4444-4444-8444-444444444444`
export const keys=[1,2,3,4,5].map(key)
export const set={runId:run,requestId,identityHash,reference:{capturedAt:dataAsOf,sourceHash:'a'.repeat(64)},targetsTotal:5,pageCount:2,
 pages:[{index:0,targetLo:1,targetHi:3},{index:1,targetLo:4,targetHi:5}],totals:{targets:5,items:{recommendations:5},recommendations:{ACTIVE:4,PAUSED:1,STOPPED:0,OTHER:0},policyUnreviewed:0}} as unknown as AnalysisPageSet
export const staged={kind:'STAGED',set,header:{query,labels:keys.map((k,i)=>({key:k,sku:'SKU-'+(i+1),name:'Produk '+(i+1)}))}} as unknown as StagedAnalysis
export function row(i:number,gap:string|null){return{ord:i,page_index:i<=3?0:1,target_key:key(i),sku:'SKU-'+i,product_name:'Produk '+i,production_state:'ACTIVE',available_fg_pcs:'5',
 target_pcs:'20',raw_gap_pcs:'15',base_gap_pcs:'12',conditional_gap_pcs:gap,directed_on_time_good_pcs:null,candidate_allocated_good_pcs:null,assumption_ids:['SCHED']}}
export const freshness={contract_version:'cp7.native-analysis-snapshot-freshness.v1',run_id:run,identity_hash:identityHash,data_as_of:dataAsOf,evaluated_at:'2026-10-08T02:00:00.000000+00:00',
 freshness_state:'CHANGES_RECORDED',capture_boundary:'SNAPSHOT',changes_since:['SALES','FG_STOCK','MATERIAL_STOCK','PRODUCTION','PRODUCTION_ORDERS','MASTER_DATA','MATERIAL_PURCHASES','PLANNING_POLICIES']
  .map(c=>({category:c,rows:c==='FG_STOCK'?2:0,deleted:0,rows_after_check:null,last_recorded_at:c==='FG_STOCK'?'2026-10-08T01:30:00.000000+00:00':null})),
 changes_total:2,last_full_check:null,same_as_of:null,apply_enabled:false,production_go:false}
export function brief(selected:string[]=[],extra:Json={}){return{contract_version:'cp7.native-ai-brief-staged.v1',actor_scope_id:actor,run_id:run,request_id:requestId,identity_hash:identityHash,
 data_as_of:dataAsOf,query,targets_total:5,page_count:2,totals:{targets:5,items:{recommendations:5},recommendations:{OTHER:0,ACTIVE:4,PAUSED:1,STOPPED:0},policy_unreviewed:0},
 freshness,need_counts:{targets:5,with_open_need:3,need_unknown:1},priority:[row(4,'9'),row(1,'4'),row(2,'4')],
 selected:selected.map(k=>row(keys.indexOf(k)+1,'4')),bounds:{priority:25,selected:20},finance:'NOT_IN_SNAPSHOT',apply_enabled:false,production_go:false,...extra}}
