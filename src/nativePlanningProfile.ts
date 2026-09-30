import {parseNativeDemandHistory,type NativeDemandQuery} from './nativeDemandHistory'
export type PlanningConfig={mean_mode:'OWN_AVAILABLE_HISTORY'|'SELECTED_MANUAL';daily_pcs:string|null;minimum_available_days:string;lead_days:string|null;review_days:string|null;buffer_days:string|null}
export type PlanningProfile={rootId:string;productVersionId:string;sizeId:string;sku:string;productName:string;profileId:string|null;revision:string;quality:'UNREVIEWED'|'SELECTED_ASSUMPTION'|'PHYSICAL_VERSION_CHANGED';config:PlanningConfig|null;reason:string|null}
export type PlanningPayload={root_id:string;product_version_id:string;expected_revision:string;config:PlanningConfig;reason:string}
export type PlanningRequest={id:string;payload:PlanningPayload}
export type NativeBaseline={runId:string;requestId:string;capturedAt:string;sourceHash:string;state:'UNCHANGED'|'ARCHIVED_STALE';query:NativeDemandQuery;rows:BaselineRow[]}
export type BaselineRow={rootId:string;sizeId:string;sku:string;productName:string;available:string;daily:string|null;meanBasis:string;target:string|null;horizon:string|null;productionState:'ACTIVE'|'PAUSED'|'STOPPED'|null;startNew:'0'|null;profileRevision:string;profileId:string|null}
const fail=():never=>{throw Error('Aturan atau hasil target dari server berubah atau belum lengkap. Muat ulang sumber.')}
const obj=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const str=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const id=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const integer=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)?v:fail()
const targetQuantity=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,33})$/.test(v)?v:fail()
const decimal=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$/.test(v)?v:fail()
const nullable=(v:unknown,parse:(v:unknown)=>string)=>v===null?null:parse(v)
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).sort().join('|')!==keys.sort().join('|'))fail()}
export function parsePlanningConfig(v:unknown):PlanningConfig{
 const c=obj(v);exact(c,['mean_mode','daily_pcs','minimum_available_days','lead_days','review_days','buffer_days'])
 if(c.mean_mode!=='OWN_AVAILABLE_HISTORY'&&c.mean_mode!=='SELECTED_MANUAL')fail()
 const daily=nullable(c.daily_pcs,decimal),minimum=integer(c.minimum_available_days)
 if(BigInt(minimum)<1n||BigInt(minimum)>3660n||(c.mean_mode==='OWN_AVAILABLE_HISTORY'&&daily!==null)||(c.mean_mode==='SELECTED_MANUAL'&&daily===null))fail()
 const lead=nullable(c.lead_days,decimal),review=nullable(c.review_days,decimal),buffer=nullable(c.buffer_days,decimal)
 // Exact decimal comparison against an integer bound, never target arithmetic.
 for(const x of[lead,review,buffer])if(x!==null){const [whole,fraction='']=x.split('.');if(BigInt(whole)>3660n||(BigInt(whole)===3660n&&/[1-9]/.test(fraction)))fail()}
 return{mean_mode:c.mean_mode as PlanningConfig['mean_mode'],daily_pcs:daily,minimum_available_days:minimum,lead_days:lead,review_days:review,buffer_days:buffer}
}
function profile(raw:unknown):PlanningProfile{
 const p=obj(raw),quality=str(p.quality);if(!['UNREVIEWED','SELECTED_ASSUMPTION','PHYSICAL_VERSION_CHANGED'].includes(quality))fail()
 const revision=integer(p.revision),profileId=nullable(p.profile_id,id),config=p.config===null?null:parsePlanningConfig(p.config)
 if(quality==='UNREVIEWED'?(revision!=='0'||profileId!==null||config!==null):(revision==='0'||profileId===null||config===null))fail()
 return{rootId:id(p.root_id),productVersionId:id(p.product_version_id),sizeId:id(p.size_id),sku:str(p.sku),productName:str(p.product_name),profileId,revision,quality:quality as PlanningProfile['quality'],config,reason:nullable(p.reason,str)}
}
export function parsePlanningProfile(raw:unknown,rootId:string,sizeId:string):PlanningProfile{
 const w=obj(raw),rows=Array.isArray(w.rows)?w.rows:fail();if(w.contract_version!=='cp7.planning-profile.v1'||rows.length!==1)fail()
 const p=profile(rows[0]);if(p.rootId!==rootId||p.sizeId!==sizeId)fail();return p
}
export function planningPayload(p:PlanningProfile,config:PlanningConfig,reason:string):PlanningPayload{
 const clean=reason.trim();if(!clean||clean.length>1000)throw Error('Isi alasan pemeriksaan aturan, maksimal1000 karakter.')
 return{root_id:p.rootId,product_version_id:p.productVersionId,expected_revision:p.revision,config:parsePlanningConfig(config),reason:clean}
}
export function checkPlanningOutcome(raw:unknown,r:PlanningRequest){
 const o=obj(raw);if(o.contract_version!=='cp7.planning-profile-outcome.v1'||o.request_id!==r.id||o.root_id!==r.payload.root_id||o.quality!=='SELECTED_ASSUMPTION'||BigInt(integer(o.revision))!==BigInt(r.payload.expected_revision)+1n)fail();id(o.profile_id)
}
export function parseNativeBaseline(raw:unknown,q:NativeDemandQuery):NativeBaseline{
 const v=obj(raw);if(v.contract_version!=='cp7.native-baseline.v1'||v.scope!=='GLOBAL_CURRENT_PHYSICAL_ROOTS'||v.apply_enabled!==false||v.production_go!==false||v.model_basis!=='BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN'||v.target_basis!=='DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS')fail()
 const run=id(v.run_id),request=id(v.request_id),hash=str(v.source_hash);if(!/^[0-9a-f]{64}$/.test(hash)||(v.source_state!=='UNCHANGED'&&v.source_state!=='ARCHIVED_STALE'))fail()
 const h=parseNativeDemandHistory({...obj(v.history_run_result),run_id:run,request_id:request,source_state:v.source_state})
 const rawRows=Array.isArray(v.rows)?v.rows:fail()
 if(h.from!==q.from_date||h.through!==q.through_date||h.basis!==q.group_mode||h.capturedAt!==v.captured_at||rawRows.length!==h.rows.length)fail()
 const seen=new Set<string>(),rows:BaselineRow[]=[]
 for(const rawRow of rawRows){
  const r=obj(rawRow),key=str(r.target_key),native=h.rows.find(x=>x.targetKey===key)??fail(),p=profile(r.profile),estimate=obj(r.demand_estimate),ei=obj(estimate.inputs),target=obj(r.target),ti=obj(target.inputs)
  if(seen.has(key)||p.rootId!==native.rootId||p.sizeId!==native.sizeId||r.size_id!==native.sizeId||r.available_fg_pcs!==native.available||r.sku!==native.sku||r.product_name!==native.productName)fail();seen.add(key)
  if(r.final_gap_pcs!==null||['supply_state','capacity_state','timeline_state'].some(k=>r[k]!=='UNKNOWN'))fail()
  for(const inputs of[ei,ti])if(inputs.snapshot_id!==hash||inputs.scope_id!==v.scope)fail()
  if(ei.target_key!==key||ei.size_id!==native.sizeId||ti.mode!=='DAYS'||ti.quantile!==null||!Array.isArray(ti.horizon_samples)||ti.horizon_samples.length!==0)fail()
  const daily=nullable(estimate.daily_pcs,decimal);if(estimate.status==='UNKNOWN'?daily!==null:estimate.status!=='SCENARIO'||daily===null)fail()
  if(ti.daily_mean!==daily)fail()
  if(p.quality==='SELECTED_ASSUMPTION'){
   const c=p.config!;if(ti.lead_days!==c.lead_days||ti.review_days!==c.review_days||ti.buffer_days!==c.buffer_days)fail()
   if(c.mean_mode==='SELECTED_MANUAL'&&(daily!==c.daily_pcs||estimate.basis!=='SELECTED_MANUAL_ASSUMPTION'))fail()
   if(!Array.isArray(r.refs)||!r.refs.some(x=>{const ref=obj(x);return ref.kind==='PLANNING_PROFILE'&&ref.id===p.profileId&&ref.revision===p.revision}))fail()
  }else if(daily!==null||['lead_days','review_days','buffer_days'].some(k=>ti[k]!==null))fail()
  let targetPcs:string|null=null,horizon:string|null=null
  if(target.status==='SCENARIO'){if(target.kernel_version!=='target-days-1'||daily===null)fail();targetPcs=targetQuantity(target.target_pcs);horizon=decimal(target.horizon_days)}else if(target.status!=='UNKNOWN')fail()
  const policy=r.production_policy===null?null:obj(obj(r.production_policy).policy),known=policy?.quality==='KNOWN',state=known?str(policy!.state):null
  if(state!==null&&!['ACTIVE','PAUSED','STOPPED'].includes(state))fail()
  const disabled=state==='PAUSED'||state==='STOPPED';if(r.start_new_pcs!==(disabled?'0':null))fail()
  rows.push({rootId:p.rootId,sizeId:p.sizeId,sku:native.sku,productName:native.productName,available:native.available,daily,meanBasis:estimate.status==='UNKNOWN'?'UNKNOWN':str(estimate.basis),target:targetPcs,horizon,productionState:state as BaselineRow['productionState'],startNew:disabled?'0':null,profileId:p.profileId,profileRevision:p.revision})
 }
 return{runId:run,requestId:request,capturedAt:h.capturedAt,sourceHash:hash,state:v.source_state as NativeBaseline['state'],query:{...q},rows}
}
export const planningRequestKey=(scope:string)=>'erp.cp7.planning-profile-request.v1:'+scope
export function readPlanningRequest(scope:string):{pending:PlanningRequest|null;error:string}{
 try{const raw=localStorage.getItem(planningRequestKey(scope));if(raw===null)return{pending:null,error:''};const r=obj(JSON.parse(raw)),p=obj(r.payload);exact(r,['id','payload']);exact(p,['root_id','product_version_id','expected_revision','config','reason']);const config=parsePlanningConfig(p.config),reason=str(p.reason);if(reason.trim()!==reason||reason.length>1000)fail();return{pending:{id:id(r.id),payload:{root_id:id(p.root_id),product_version_id:id(p.product_version_id),expected_revision:integer(p.expected_revision),config,reason}},error:''}}
 catch{return{pending:null,error:'Permintaan simpan aturan belum bisa dibaca. Pulihkan catatan sebelum menyimpan lagi.'}}
}
export function persistPlanningRequest(scope:string,r:PlanningRequest){
 const old=readPlanningRequest(scope);if(old.error||old.pending)throw Error('Pastikan permintaan tersimpan yang sama terlebih dahulu.')
 const raw=JSON.stringify(r);localStorage.setItem(planningRequestKey(scope),raw);if(localStorage.getItem(planningRequestKey(scope))!==raw||readPlanningRequest(scope).pending?.id!==r.id)throw Error('Permintaan simpan belum tersimpan. Periksa penyimpanan.')
}
export function clearPlanningRequest(scope:string,id:string){
 const old=readPlanningRequest(scope);if(old.error||old.pending?.id!==id)throw Error('Catatan simpan aturan berubah. Periksa permintaan yang sama.')
 localStorage.removeItem(planningRequestKey(scope));if(localStorage.getItem(planningRequestKey(scope))!==null)throw Error('Catatan simpan aturan belum dapat diselesaikan.')
}
