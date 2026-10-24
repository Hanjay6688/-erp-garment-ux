import {fixedModelDefinitions,parseModelPolicySource,type ModelDefinition,type ModelPolicySource} from './nativeModelPolicy'
import type {TargetDemand} from './nativeTargetDemand'
import type {ReorderRow} from './fgReorderContract'

type Obj=Record<string,unknown>
type Fraction=readonly[bigint,bigint]
export type ModelTarget={state:'MODEL_PROJECTED'|'BASELINE_RETAINED';reason:string;model:ModelDefinition|null;forecastFrom:string|null;forecasts:string[]|null;policy:ModelPolicySource|null;baselineTarget:string|null;baselineReorderPoint:string|null;mode:'DAYS'|'STATISTICAL';expectedTarget:Obj;signature:string}
function fail():never{throw Error('Dasar model dan target tersimpan tidak cocok. Muat ulang sumber perhitungan.')}
const obj=(x:unknown):Obj=>x!==null&&typeof x==='object'&&!Array.isArray(x)?x as Obj:fail()
const exact=(x:Obj,ks:string[])=>{if(Object.keys(x).sort().join('|')!==[...ks].sort().join('|'))fail()}
const text=(x:unknown)=>typeof x==='string'&&x.length>0&&x.length<=1000?x:fail()
const uuid=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x)?x:fail()
const hash=(x:unknown,n=64)=>typeof x==='string'&&new RegExp('^[0-9a-f]{'+n+'}$').test(x)?x:fail()
const decimal=(x:unknown)=>typeof x==='string'&&/^(0|[1-9][0-9]{0,99})(\.[0-9]{1,100})?$/.test(x)?x:fail()
const whole=(x:unknown)=>typeof x==='string'&&/^(0|[1-9][0-9]{0,99})$/.test(x)?x:fail()
const maybe=<T>(x:unknown,f:(x:unknown)=>T)=>x===null?null:f(x)
const canonical=(x:unknown):string=>JSON.stringify(x,(_k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v)
const day=(x:unknown)=>{const s=text(x);if(!/^\d{4}-\d{2}-\d{2}$/.test(s)||!Number.isFinite(Date.parse(s))||new Date(s).toISOString().slice(0,10)!==s)fail();return s}
const micros=(x:unknown)=>{const s=text(x).replace(/\+00:00$/,'Z'),m=s.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/);if(!m||!Number.isFinite(Date.parse(m[1]+'Z'))||Number(s.slice(11,13))>23||Number(s.slice(14,16))>59||Number(s.slice(17,19))>59)fail();day(s.slice(0,10));return BigInt(Date.parse(m[1]+'Z'))*1000n+BigInt((m[2]??'').padEnd(6,'0'))}
const fraction=(x:unknown):Fraction=>{const[a,b='']=decimal(x).split('.');return[BigInt(a+b),10n**BigInt(b.length)]}
const gcd=(a:bigint,b:bigint):bigint=>b===0n?a:gcd(b,a%b)
const reduce=(n:bigint,d:bigint):Fraction=>{const g=gcd(n,d);return[n/g,d/g]}
const add=(a:Fraction,b:Fraction)=>reduce(a[0]*b[1]+b[0]*a[1],a[1]*b[1])
const sub=(a:Fraction,b:Fraction)=>reduce(a[0]*b[1]-b[0]*a[1],a[1]*b[1])
const mul=(a:Fraction,b:Fraction)=>reduce(a[0]*b[0],a[1]*b[1])
const cmp=(a:Fraction,b:Fraction)=>a[0]*b[1]-b[0]*a[1]
const same=(a:unknown,b:unknown)=>a===null||b===null?a===b:cmp(fraction(a),fraction(b))===0n
const ceil=(a:Fraction)=>((a[0]+a[1]-1n)/a[1]).toString()
const stringify=(a:Fraction)=>{const integer=a[0]/a[1];let rest=a[0]%a[1],digits='';while(rest!==0n&&digits.length<200){rest*=10n;digits+=String(rest/a[1]);rest%=a[1]}if(rest!==0n)fail();return String(integer)+(digits?'.'+digits:'')}
function sum(values:string[],from:Fraction,to:Fraction):Fraction{
 if(cmp(from,[0n,1n])<0n||cmp(from,to)>0n||cmp(to,[BigInt(values.length),1n])>0n)fail()
 let total:Fraction=[0n,1n]
 values.forEach((v,i)=>{const lo:Fraction=[BigInt(i),1n],hi:Fraction=[BigInt(i+1),1n],start=cmp(from,lo)>0n?from:lo,end=cmp(to,hi)<0n?to:hi;if(cmp(end,start)>0n)total=add(total,mul(fraction(v),sub(end,start)))})
 return total
}

// Validate the server-owned admission and exact vector arithmetic. This is a
// wire consistency check, not a client authorization or an independent backtest.
export function parseModelTarget(value:unknown,d:TargetDemand):ModelTarget{
 const m=obj(value);exact(m,['contract_version','state','reason','source_hash','actor_scope_id','access_epoch','run_id','history_run_id','history_query','model_source_hash','captured_at','policy_source','engine_hash','consumer_engine_hash','forecast_from_date','selected_model','forecast','baseline_target','forecast_applied','production_go'])
 if(m.contract_version!=='cp7.model-target-resolution.v1'||!['MODEL_PROJECTED','BASELINE_RETAINED'].includes(String(m.state))||m.production_go!==false||m.forecast_applied!==(m.state==='MODEL_PROJECTED'))fail()
 hash(m.source_hash);hash(m.access_epoch);hash(m.engine_hash,32);hash(m.consumer_engine_hash,32);uuid(m.actor_scope_id)
 const reason=text(m.reason),policy=maybe(m.policy_source,parseModelPolicySource),captured=micros(d.capturedAt),forecastFrom=maybe(m.forecast_from_date,day)
 if(policy&&micros(policy.policy.recorded_at)>captured)fail()
 if(m.run_id===null){if([m.history_run_id,m.history_query,m.model_source_hash,m.captured_at,m.forecast_from_date,m.selected_model,m.forecast].some(x=>x!==null))fail()}
 else{
  uuid(m.run_id);uuid(m.history_run_id);hash(m.model_source_hash);if(micros(m.captured_at)>captured||forecastFrom===null)fail()
  const q=obj(m.history_query);exact(q,['from_date','through_date','group_mode']);if(day(q.from_date)>day(q.through_date)||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))fail()
 }
 let model:ModelDefinition|null=null
 if(m.selected_model!==null){const s=obj(m.selected_model);exact(s,['id','method','params','registered_at']);model=fixedModelDefinitions().find(x=>x.id===s.id)??fail();if(model.method==='MEAN'||s.method!==model.method||canonical(s.params)!==canonical(model.params)||!policy||micros(s.registered_at)!==micros(policy.policy.recorded_at)||micros(s.registered_at)>micros(m.captured_at))fail()}
 const base=obj(m.baseline_target),i=obj(base.inputs),scenario=base.status==='SCENARIO'
 exact(base,scenario?['status','kernel_version','horizon_days','lead_demand_pcs','review_demand_pcs','lead_safety_pcs','horizon_safety_pcs','reorder_point_pcs','target_pcs','inputs','reason']:['status','reason','target_pcs','reorder_point_pcs','inputs'])
 exact(i,['contract_version','snapshot_id','scope_id','mode','daily_total_pcs','counted_days','daily_sd','lead_days','review_days','buffer_days','service_level','refs'])
 if(i.contract_version!=='cp7.target-input.v2'||i.scope_id!=='GLOBAL_CURRENT_PHYSICAL_ROOTS'||!['DAYS','STATISTICAL'].includes(String(i.mode))||!Array.isArray(i.refs))fail();hash(i.snapshot_id)
 for(const raw of i.refs){const r=obj(raw);exact(r,['kind','id','revision']);text(r.kind);text(r.id);whole(r.revision)}
 for(const key of['daily_total_pcs','daily_sd','lead_days','review_days','buffer_days'])maybe(i[key],decimal)
 const counted=maybe(i.counted_days,whole);if(counted!==null&&(BigInt(counted)<1n||BigInt(counted)>3660n))fail()
 if(!same(i.daily_total_pcs,d.dailyTotalPcs)||(d.countedDays!==null&&i.counted_days!==d.countedDays))fail()
 if(i.mode==='DAYS'?(i.daily_sd!==null||i.service_level!==null):(i.buffer_days!==null||!same(i.daily_sd,d.dailySd)||i.service_level!==null&&!['0.90','0.95','0.99'].includes(String(i.service_level))))fail()
 const baselineTarget=maybe(base.target_pcs,whole),baselineReorderPoint=maybe(base.reorder_point_pcs,whole)
 if(scenario){
  if(base.kernel_version!=='target-unified-2'||baselineTarget===null||baselineReorderPoint===null||i.lead_days===null||i.review_days===null||i.daily_total_pcs===null||counted===null)fail()
  for(const k of['horizon_days','lead_demand_pcs','review_demand_pcs','lead_safety_pcs','horizon_safety_pcs'])decimal(base[k])
  const l=fraction(i.lead_days),h=add(l,fraction(i.review_days)),total=fraction(i.daily_total_pcs),mean=mul(total,[1n,BigInt(counted)])
  if(cmp(fraction(base.horizon_days),h)!==0n)fail()
  if(i.mode==='DAYS'){
   if(base.reason!=='ONE_EXPLICIT_DAYS_BUFFER'||i.buffer_days===null||!same(base.lead_safety_pcs,base.horizon_safety_pcs))fail()
   const b=fraction(i.buffer_days);if(baselineTarget!==ceil(mul(mean,add(h,b)))||baselineReorderPoint!==ceil(mul(mean,add(l,b))))fail()
  }else if(base.reason!=='BASELINE_INDEPENDENT_DAILY_VARIATION_ASSUMPTION'||BigInt(counted)<14n||i.daily_sd===null||i.service_level===null||baselineTarget!==ceil(add(mul(mean,h),fraction(base.horizon_safety_pcs)))||baselineReorderPoint!==ceil(add(mul(mean,l),fraction(base.lead_safety_pcs))))fail()
 }else if(base.status!=='UNKNOWN'||baselineTarget!==null||baselineReorderPoint!==null)fail()
 let forecasts:string[]|null=null,expectedTarget=structuredClone(base)
 if(m.state==='MODEL_PROJECTED'){
  if(!scenario||!model||!policy||policy.policy.state!=='ACTIVE'||!policy.policy.config.allowed_methods.some(x=>x===model!.method)||d.basis!=='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'||canonical(m.history_query)!==canonical(d.query)||forecastFrom!==new Date(Number(captured/1000n)+7*3600000).toISOString().slice(0,10)||new Date(Date.parse(d.query.through_date)+86400000).toISOString().slice(0,10)!==forecastFrom)fail()
  const f=obj(m.forecast);exact(f,['method','params','reason','status','forecasts','kernel_version','training_count'])
  if(f.status!=='ELIGIBLE'||f.method!==model.method||canonical(f.params)!==canonical(model.params)||f.kernel_version!==model.method.toLowerCase()+'-1'||!Number.isInteger(f.training_count)||Number(f.training_count)<Number(policy.policy.config.minimum_training_days)||Number(f.training_count)>366||!Array.isArray(f.forecasts)||f.forecasts.length<1||f.forecasts.length>Number(policy.policy.config.maximum_horizon_days))fail();text(f.reason)
  forecasts=f.forecasts.map(x=>{if(typeof x!=='string'||!/^(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$/.test(x))fail();return x})
  const l=fraction(i.lead_days),h=add(l,fraction(i.review_days)),b=i.mode==='DAYS'?fraction(i.buffer_days):[0n,1n]as const
  const lead=sum(forecasts,[0n,1n],l),review=sum(forecasts,l,h),ls=i.mode==='DAYS'?sum(forecasts,l,add(l,b)):fraction(base.lead_safety_pcs),hs=i.mode==='DAYS'?sum(forecasts,h,add(h,b)):fraction(base.horizon_safety_pcs)
  const expectedReason=i.mode==='DAYS'?'ONE_DATED_VECTOR_WITH_ONE_EXPLICIT_DAYS_BUFFER':'DATED_POINT_FORECAST_WITH_EXISTING_HISTORICAL_VARIATION_ASSUMPTION'
  if(reason!==expectedReason||d.targetPcs!==ceil(add(add(lead,review),hs))||d.reorderPointPcs!==ceil(add(lead,ls)))fail()
  expectedTarget={...base,kernel_version:'target-forecast-vector-1',reason,model_input:structuredClone(m),forecast_applied:true,calibrated_forecast_interval:false,buffer_basis:i.mode==='DAYS'?'ONE_EXPLICIT_DAYS_BUFFER':'BASELINE_INDEPENDENT_DAILY_VARIATION_ASSUMPTION',lead_demand_pcs:stringify(lead),review_demand_pcs:stringify(review),lead_safety_pcs:stringify(ls),horizon_safety_pcs:stringify(hs),target_pcs:d.targetPcs,reorder_point_pcs:d.reorderPointPcs}
 }else if(m.forecast!==null||d.targetPcs!==baselineTarget||d.reorderPointPcs!==baselineReorderPoint||['ONE_DATED_VECTOR_WITH_ONE_EXPLICIT_DAYS_BUFFER','DATED_POINT_FORECAST_WITH_EXISTING_HISTORICAL_VARIATION_ASSUMPTION'].includes(reason))fail()
 return{state:m.state as ModelTarget['state'],reason,model,forecastFrom,forecasts,policy,baselineTarget,baselineReorderPoint,mode:i.mode as ModelTarget['mode'],expectedTarget,signature:canonical(m)}
}
export function assertModelTargetBinding(value:unknown,resolution:unknown,m:ModelTarget){
 const t=obj(value),expected=m.expectedTarget;exact(t,Object.keys(expected));if(canonical(resolution)!==m.signature)fail()
 const quantities=['horizon_days','lead_demand_pcs','review_demand_pcs','lead_safety_pcs','horizon_safety_pcs']
 for(const k of Object.keys(expected))if(quantities.includes(k)?!same(t[k],expected[k]):canonical(t[k])!==canonical(expected[k]))fail()
}
export function assertModelReorderBinding(r:ReorderRow,m:ModelTarget){
 const t=m.expectedTarget,i=obj(t.inputs)
 if(r.bufferMode!==m.mode||!same(r.leadDays,i.lead_days)||!same(r.bufferDays,i.buffer_days)||r.serviceLevel!==i.service_level||!same(r.safetyPcs,t.lead_safety_pcs??null))fail()
}
export function modelTargetReasonLabel(reason:string){return({MODEL_CURRENT_ACCESS_REQUIRED:'Hak akses evaluasi model belum tersedia; perhitungan dasar tetap dipakai.',EXISTING_REORDER_DEFAULTS_RETAINED_UNREVIEWED_PROFILE:'Profil perencanaan belum diperiksa; titik pesan ulang memakai aturan dasar yang sudah berlaku.',EXPLICIT_MANUAL_DEMAND_RETAINS_PRIORITY:'Angka kebutuhan manual tetap dipakai.',OWN_HISTORY_MINIMUM_REQUIRED_BEFORE_MODEL:'Riwayat produk belum memenuhi syarat profil untuk memakai model.',NO_OWN_MODEL_EVALUATION:'Belum ada evaluasi model untuk produk ini.',NO_EXPLICITLY_ALLOWED_CHALLENGER:'Belum ada metode model yang diizinkan dalam kebijakan.',ACTIVATION_POLICY_CHANGED:'Kebijakan model berubah; perhitungan ini memakai dasar kebutuhan semula.',ACTIVATION_POLICY_SUSPENDED:'Kebijakan model sedang dihentikan.',MODEL_HISTORY_QUERY_DIFFERS_FROM_TARGET:'Periode atau dasar riwayat model berbeda dari perhitungan target.',FULL_DATED_TARGET_AND_REORDER_VECTOR_REQUIRED:'Perkiraan belum mencakup seluruh waktu proses, pemeriksaan dan cadangan.',NATIVE_HISTORY_SOURCE_CHANGED:'Sumber riwayat model berubah atau belum lengkap.',MODEL_FORECAST_ORIGIN_NOT_CURRENT:'Tanggal awal perkiraan model sudah tidak sesuai.',MODEL_ENGINE_CHANGED:'Perhitungan model berubah; evaluasi perlu diperbarui.'}as Record<string,string>)[reason]??'Syarat penggunaan model belum terpenuhi; dasar kebutuhan semula tetap dipakai.'}
