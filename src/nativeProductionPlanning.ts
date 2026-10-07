import {parseNativeBaseline,type NativeBaseline,type BaselineRow} from './nativePlanningProfile'
import type {NativeDemandQuery} from './nativeDemandHistory'

export type SourceState='UNCHANGED'|'ARCHIVED_STALE'
export type WorkPosition={key:string;poolKey:string;stage:string;sizeId:string;ownership:'COMPANY'|'CUSTOMER';eligible:boolean;remaining:string}
export type NativeSupply={runId:string;requestId:string;sourceHash:string;capturedAt:string;state:SourceState;baseline:NativeBaseline;positions:WorkPosition[];complete:boolean}
export type SchedulePosition={position_key:string;target_key:string|null;eligible_input_pcs:string;yield_numerator:string|null;yield_denominator:string|null;remaining_steps:{stage:string;remaining_minutes:string|null}[]}
export type ScheduleConfig={basis:'SELECTED_ASSUMPTIONS';resource_scope:'SINGLE_HOMOGENEOUS_SELECTED_CENTRE';work_centre_key:string;through_at:string;unit_minutes:string|null;windows:{key:string;starts_at:string;ends_at:string;other_load_minutes:string|null}[];positions:SchedulePosition[]}
export type ScheduleRequirement=WorkPosition&{route:string[];targets:{key:string;versionId:string;sku:string;name:string}[]}
export type ScheduleWorkspace={sourceRun:string;sourceHash:string;currentHash:string;capturedAt:string;state:SourceState;revision:string;planState:'UNREVIEWED'|'SELECTED_ASSUMPTIONS'|'SOURCE_CHANGED';config:ScheduleConfig|null;requirements:ScheduleRequirement[]}
export type SchedulePayload={source_run:string;source_hash:string;expected_revision:string;config:ScheduleConfig;reason:string}
export type ScheduleRequest={id:string;payload:SchedulePayload}
export type NettingRow=BaselineRow&{key:string;rawGap:string|null;directed:string|null;baseGap:string|null;conditionalGap:string|null;candidate:string|null;firstGapAt:string|null;timelineState:string;reason:string}
export type NativeNetting={runId:string;requestId:string;capturedAt:string;sourceHash:string;state:SourceState;status:'SCENARIO'|'PARTIAL'|'UNKNOWN';query:NativeDemandQuery;rows:NettingRow[];capacity:string|null;allocationState:string;scheduleState:string;positions:WorkPosition[];etas:{key:string;at:string|null}[]}

const fail=():never=>{throw Error('Data stok proses atau jadwal dari server berubah atau belum lengkap. Muat ulang sumber.')}
const obj=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const str=(v:unknown)=>typeof v==='string'&&v.length>0&&v.length<=2000?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const pcs=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,33})$/.test(v)?v:fail()
const decimal=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$/.test(v)?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const instant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const nativeEtaInstant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|\+00:00)$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const list=(v:unknown,max=1000)=>Array.isArray(v)&&v.length<=max?v:fail()
const nullable=(v:unknown,parse:(v:unknown)=>string)=>v===null?null:parse(v)
const state=(v:unknown):SourceState=>v==='UNCHANGED'||v==='ARCHIVED_STALE'?v:fail()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))fail()}
const unique=(keys:string[])=>{if(new Set(keys).size!==keys.length)fail()}
function position(raw:unknown):WorkPosition{
 const p=obj(raw);if(p.ownership!=='COMPANY'&&p.ownership!=='CUSTOMER'||typeof p.eligible_company_wip!=='boolean'||p.ownership==='CUSTOMER'&&p.eligible_company_wip)fail()
 return{key:str(p.key??p.position_key),poolKey:str(p.pool_key),stage:str(p.stage),sizeId:uuid(p.size_id),ownership:p.ownership as WorkPosition['ownership'],eligible:p.eligible_company_wip as boolean,remaining:pcs(p.remaining_pcs)}
}
function positions(raw:unknown){const w=obj(raw);if(w.status!=='COMPLETE')return{complete:false,rows:[] as WorkPosition[]};if(w.contract_version!=='cp7.wip-position.v1'||w.scope!=='GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS')fail();const rows=list(w.positions,20000).map(position);unique(rows.map(p=>p.key));return{complete:true,rows}}
// v2 (PL-8): posted cutting groups proven exhausted are listed in
// production_scope.exhausted_cutting_groups instead of carrying zero positions.
// v1 remains readable for runs archived before it.
const SUPPLY_CONTRACTS=['cp7.native-supply.v1','cp7.native-supply.v2']
export function parseNativeSupply(raw:unknown,q:NativeDemandQuery):NativeSupply{
 const v=obj(raw);if(!SUPPLY_CONTRACTS.includes(str(v.contract_version))||v.scope!=='GLOBAL_CURRENT_PHYSICAL_ROOTS_AND_POSTED_PRODUCTION_ORIGINS'||v.apply_enabled!==false||v.production_go!==false)fail()
 const run=uuid(v.run_id),request=uuid(v.request_id),sourceHash=hash(v.source_hash),capturedAt=instant(v.captured_at),s=state(v.source_state)
 const baseline=parseNativeBaseline({...obj(v.baseline_run_result),run_id:run,request_id:request,source_state:s},q),w=positions(v.wip)
 if(baseline.capturedAt!==capturedAt)fail()
 return{runId:run,requestId:request,sourceHash,capturedAt,state:s,baseline,positions:w.rows,complete:w.complete}
}
export function parseScheduleConfig(raw:unknown):ScheduleConfig{
 const c=obj(raw);exact(c,['basis','resource_scope','work_centre_key','through_at','unit_minutes','windows','positions'])
 if(c.basis!=='SELECTED_ASSUMPTIONS'||c.resource_scope!=='SINGLE_HOMOGENEOUS_SELECTED_CENTRE')fail()
 const windows=list(c.windows).map(raw=>{const w=obj(raw);exact(w,['key','starts_at','ends_at','other_load_minutes']);return{key:str(w.key),starts_at:instant(w.starts_at),ends_at:instant(w.ends_at),other_load_minutes:nullable(w.other_load_minutes,decimal)}})
 unique(windows.map(w=>w.key))
 const selected=list(c.positions).map(raw=>{const p=obj(raw);exact(p,['position_key','target_key','eligible_input_pcs','yield_numerator','yield_denominator','remaining_steps']);const numerator=nullable(p.yield_numerator,pcs),denominator=nullable(p.yield_denominator,pcs);if((numerator===null)!==(denominator===null)||denominator!==null&&(BigInt(denominator)===0n||BigInt(numerator!)>BigInt(denominator)))fail()
  return{position_key:str(p.position_key),target_key:nullable(p.target_key,str),eligible_input_pcs:pcs(p.eligible_input_pcs),yield_numerator:numerator,yield_denominator:denominator,remaining_steps:list(p.remaining_steps,5).map(raw=>{const s=obj(raw);exact(s,['stage','remaining_minutes']);return{stage:str(s.stage),remaining_minutes:nullable(s.remaining_minutes,pcs)}})}})
 unique(selected.map(p=>p.position_key));const unit=nullable(c.unit_minutes,decimal);if(unit!==null&&!/[1-9]/.test(unit))fail()
 return{basis:'SELECTED_ASSUMPTIONS',resource_scope:'SINGLE_HOMOGENEOUS_SELECTED_CENTRE',work_centre_key:str(c.work_centre_key),through_at:instant(c.through_at),unit_minutes:unit,windows,positions:selected}
}
export function parseScheduleWorkspace(raw:unknown,supply:NativeSupply):ScheduleWorkspace{
 const v=obj(raw);if(v.contract_version!=='cp7.planning-schedule.v1'||v.production_go!==false||v.source_run!==supply.runId||v.source_hash!==supply.sourceHash||v.captured_at!==supply.capturedAt)fail()
 const revision=pcs(v.revision),s=state(v.source_state),currentHash=hash(v.current_source_hash);if((currentHash===supply.sourceHash)!==(s==='UNCHANGED'))fail()
 if(!['UNREVIEWED','SELECTED_ASSUMPTIONS','SOURCE_CHANGED'].includes(str(v.plan_state)))fail()
 let config:ScheduleConfig|null=null
 if(v.plan===null){if(revision!=='0'||v.plan_state!=='UNREVIEWED')fail()}else{const plan=obj(v.plan);uuid(plan.plan_id);uuid(plan.source_run);hash(plan.source_hash);instant(plan.recorded_at);if(plan.revision!==revision||revision==='0'||(plan.source_hash===currentHash)!==(v.plan_state==='SELECTED_ASSUMPTIONS'))fail();config=parseScheduleConfig(plan.config)}
 const requirements=list(v.position_requirements).map(raw=>{const p=obj(raw),r=position(p),native=supply.positions.find(x=>x.key===r.key)??fail();if(JSON.stringify(r)!==JSON.stringify(native)||r.remaining==='0')fail();const route=list(p.remaining_route,5).map(str);if(!route.length)fail();const targets=list(p.target_candidates).map(raw=>{const t=obj(raw),key=str(t.target_key);if(!supply.baseline.rows.some(x=>x.rootId+':'+x.sizeId===key)||!r.eligible)fail();return{key,versionId:uuid(t.product_version_id),sku:str(t.sku),name:str(t.product_name)}});unique(targets.map(t=>t.key));return{...r,route,targets}})
 unique(requirements.map(p=>p.key));return{sourceRun:supply.runId,sourceHash:supply.sourceHash,currentHash,capturedAt:supply.capturedAt,state:s,revision,planState:v.plan_state as ScheduleWorkspace['planState'],config,requirements}
}
export function schedulePayload(w:ScheduleWorkspace,config:ScheduleConfig,reason:string):SchedulePayload{
 if(w.state!=='UNCHANGED')throw Error('Sumber stok proses berubah. Ambil sumber terbaru sebelum menyimpan jadwal.')
 const clean=reason.trim();if(!clean||clean.length>1000)throw Error('Isi alasan pemeriksaan jadwal, maksimal 1000 karakter.')
 return{source_run:w.sourceRun,source_hash:w.sourceHash,expected_revision:w.revision,config:parseScheduleConfig(config),reason:clean}
}
export function checkScheduleOutcome(raw:unknown,r:ScheduleRequest){const o=obj(raw);if(o.contract_version!=='cp7.planning-schedule-outcome.v1'||o.request_id!==r.id||o.source_hash!==r.payload.source_hash||o.quality!=='SELECTED_ASSUMPTIONS'||o.production_go!==false||BigInt(pcs(o.revision))!==BigInt(r.payload.expected_revision)+1n)fail();uuid(o.plan_id)}
export function parseNativeNetting(raw:unknown,q:NativeDemandQuery):NativeNetting{
 const v=obj(raw);if(v.contract_version!=='cp7.native-netting.v1'||v.apply_enabled!==false||v.production_go!==false||!['SCENARIO','PARTIAL','UNKNOWN'].includes(str(v.status)))fail()
 const run=uuid(v.run_id),request=uuid(v.request_id),s=state(v.source_state),capturedAt=instant(v.captured_at),sourceHash=hash(v.source_hash),scenario=obj(v.schedule_run_result)
 if(scenario.contract_version!=='cp7.native-planning-scenario.v1'||scenario.captured_at!==capturedAt||scenario.apply_enabled!==false||scenario.production_go!==false||!['UNREVIEWED','SOURCE_CHANGED','SELECTED_ASSUMPTIONS'].includes(str(scenario.schedule_state)))fail()
 const supply=parseNativeSupply({...obj(scenario.supply_run_result),run_id:run,request_id:request,source_state:s},q),w=positions(scenario.wip),allocation=obj(v.allocation),capacity=obj(scenario.capacity)
 if(supply.capturedAt!==capturedAt)fail()
 const capacityPcs=nullable(capacity.capacity_pcs,pcs);if(capacity.status==='UNKNOWN'?capacityPcs!==null:!['SCENARIO','KNOWN'].includes(str(capacity.status))||capacityPcs===null)fail()
 const rows=list(v.rows).map(raw=>{const r=obj(raw),key=str(r.target_key),b=supply.baseline.rows.find(x=>x.rootId+':'+x.sizeId===key)??fail();if(r.size_id!==b.sizeId||r.sku!==b.sku||r.product_name!==b.productName||r.available_fg_pcs!==b.available||r.final_gap_pcs!==null||r.start_new_pcs!==b.startNew||r.material_state!=='UNKNOWN'||r.apply_enabled!==false)fail()
  const rawGap=nullable(r.raw_gap_pcs,pcs),directed=nullable(r.directed_on_time_good_pcs,pcs),baseGap=nullable(r.base_gap_pcs,pcs),conditionalGap=nullable(r.conditional_gap_pcs,pcs),candidate=nullable(r.candidate_allocated_good_pcs,pcs)
  if(r.net!==null){const net=obj(r.net),input=obj(net.inputs);if(!['SCENARIO','UNKNOWN'].includes(str(net.status))||input.snapshot_id!==obj(scenario.wip).snapshot_id||input.scope_id!=='GLOBAL_NATIVE_PLANNING'||input.target_key!==key||input.size_id!==b.sizeId||input.available_fg_pcs!==b.available||input.target_pcs!==b.target||net.q_base_pcs!==baseGap||net.q_conditional_pcs!==conditionalGap&&allocation.status==='SCENARIO'||(net.directed_on_time_pcs??null)!==directed)fail()}
  if(allocation.status!=='SCENARIO'&&(conditionalGap!==null||candidate!==null))fail();const timeline=obj(r.timeline),first=timeline.first_known_gap===null||timeline.first_known_gap===undefined?null:obj(timeline.first_known_gap)
  return{...b,key,rawGap,directed,baseGap,conditionalGap,candidate,firstGapAt:first===null?null:instant(first.at),timelineState:str(timeline.status),reason:str(r.reason)}
 });unique(rows.map(r=>r.key));if(w.complete&&rows.length!==supply.baseline.rows.length||!w.complete&&rows.length!==0)fail()
 const etas=list(scenario.etas).map(raw=>{const e=obj(raw),key=str(e.position_key),result=obj(e.result);if(!w.rows.some(p=>p.key===key))fail();const at=nullable(result.eta,nativeEtaInstant);if(!['KNOWN','CONDITIONAL','UNKNOWN'].includes(str(result.status))||result.status==='UNKNOWN'&&at!==null)fail();return{key,at}});unique(etas.map(e=>e.key))
 return{runId:run,requestId:request,capturedAt,sourceHash,state:s,status:v.status as NativeNetting['status'],query:{...q},rows,capacity:capacityPcs,allocationState:str(allocation.status),scheduleState:str(scenario.schedule_state),positions:w.rows,etas}
}

export const scheduleRequestKey=(scope:string)=>'erp.cp7.schedule-request.v1:'+scope
export function readScheduleRequest(scope:string):{pending:ScheduleRequest|null;error:string}{try{const raw=localStorage.getItem(scheduleRequestKey(scope));if(raw===null)return{pending:null,error:''};const r=obj(JSON.parse(raw)),p=obj(r.payload);exact(r,['id','payload']);exact(p,['source_run','source_hash','expected_revision','config','reason']);const reason=str(p.reason);if(reason.trim()!==reason||reason.length>1000)fail();return{pending:{id:uuid(r.id),payload:{source_run:uuid(p.source_run),source_hash:hash(p.source_hash),expected_revision:pcs(p.expected_revision),config:parseScheduleConfig(p.config),reason}},error:''}}catch{return{pending:null,error:'Permintaan jadwal tersimpan belum bisa dibaca. Pulihkan catatan sebelum menyimpan lagi.'}}}
export function persistScheduleRequest(scope:string,r:ScheduleRequest){const held=readScheduleRequest(scope);if(held.error||held.pending)throw Error('Pastikan hasil permintaan jadwal tersimpan terlebih dahulu.');const raw=JSON.stringify(r);localStorage.setItem(scheduleRequestKey(scope),raw);if(localStorage.getItem(scheduleRequestKey(scope))!==raw||readScheduleRequest(scope).pending?.id!==r.id)throw Error('Permintaan jadwal belum tersimpan. Periksa penyimpanan.')}
export function clearScheduleRequest(scope:string,id:string){const held=readScheduleRequest(scope);if(held.error||held.pending?.id!==id)throw Error('Catatan permintaan jadwal berubah. Ulangi permintaan yang sama.');localStorage.removeItem(scheduleRequestKey(scope));if(localStorage.getItem(scheduleRequestKey(scope))!==null)throw Error('Catatan jadwal belum dapat diselesaikan.')}

// WIB input conversion only; no demand, supply, ETA, capacity or money arithmetic.
export function instantToWibInput(value:string){return new Date(Date.parse(instant(value))+7*3600000).toISOString().slice(0,19)}
export function wibInputToInstant(value:string,original:string|null=null){const full=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)?value+':00':value;if(original!==null&&instantToWibInput(original)===full)return original;if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(full))throw Error('Isi tanggal dan jam WIB dengan lengkap.');const parsed=new Date(full+'+07:00');if(!Number.isFinite(parsed.getTime())||instantToWibInput(parsed.toISOString())!==full)throw Error('Tanggal atau jam WIB tidak valid.');return parsed.toISOString()}
