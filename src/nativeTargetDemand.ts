import type {NativeDemandQuery} from './nativeDemandHistory'
import {stagedInstant} from './nativeAnalysisPages'

export const demandBases=['OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE','SELECTED_MANUAL_ASSUMPTION','REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION','UNKNOWN'] as const
export type TargetDemandBasis=typeof demandBases[number]
export type TargetDemand={targetKey:string;sizeId:string;capturedAt:string;query:NativeDemandQuery;basis:TargetDemandBasis
 ownTotalPcs:string;ownAvailableDays:string;dailyTotalPcs:string|null;countedDays:string|null;dailySd:string|null;targetPcs:string|null;reorderPointPcs:string|null
 analog:null|{state:'READY'|'UNAVAILABLE';reason:string;choiceId:string;revision:string;recordedAt:string;sourceKey:string|null;sourceSku:string|null;sourceName:string|null
 scale:string|null;reviewReason:string;sourceTotalPcs:string|null;availableDays:string|null;scaledTotalPcs:string|null;scaledDailySd:string|null}}
type Obj=Record<string,unknown>
function fail():never{throw Error('Dasar kebutuhan belum sesuai data perhitungan tersimpan.')}
const obj=(v:unknown):Obj=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Obj:fail()
const keys=(v:Obj,ks:string[])=>{if(Object.keys(v).length!==ks.length||ks.some(k=>!Object.hasOwn(v,k)))fail()}
const label=(v:unknown,max=1000)=>typeof v==='string'&&v.trim()&&v.length<=max?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const whole=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,99})$/.test(v)?v:fail()
const decimal=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,99})(\.[0-9]{1,100})?$/.test(v)?v:fail()
const maybe=<T>(v:unknown,f:(v:unknown)=>T):T|null=>v===null?null:f(v)
const target=(v:unknown)=>{const s=label(v),parts=s.split(':');if(parts.length!==2)fail();uuid(parts[0]);uuid(parts[1]);return s}
const fraction=(s:string)=>{const[a,b='']=s.split('.');return[numeric(a+b),10n**BigInt(b.length)]as const}
const numeric=(s:string)=>BigInt(s)
const equalDecimal=(a:string,b:string)=>{const[x,y]=fraction(a),[z,w]=fraction(b);return x*w===z*y}
const productEqual=(a:string,b:string,c:string)=>{const[x,y]=fraction(a),[z,w]=fraction(b),[n,d]=fraction(c);return x*z*d===n*y*w}
function instantMicros(v:unknown){
 const s=stagedInstant(v).replace(/\+00:00$/,'Z');if(!s.endsWith('Z'))fail()
 day(s.slice(0,10));if(Number(s.slice(11,13))>23||Number(s.slice(14,16))>59||Number(s.slice(17,19))>59)fail()
 const[seconds,f='']=s.slice(0,-1).split('.');return{value:s,micros:BigInt(Date.parse(seconds+'Z'))*1000n+BigInt(f.padEnd(6,'0'))}
}
function day(v:unknown){const s=label(v,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(s))fail();const t=Date.parse(s+'T00:00:00Z');if(!Number.isFinite(t)||new Date(t).toISOString().slice(0,10)!==s)fail();return s}
export function parseTargetDemand(value:unknown,binding:{targetKey:string;capturedAt?:string;query?:NativeDemandQuery}):TargetDemand{
 const o=obj(value);keys(o,['contract_version','target_key','size_id','captured_at','query','basis','own_total_pcs','own_available_days','daily_total_pcs','counted_days','daily_sd','target_pcs','reorder_point_pcs','analog'])
 if(o.contract_version!=='cp7.target-demand-provenance.v1'||o.target_key!==binding.targetKey)fail()
 const targetKey=target(o.target_key),sizeId=uuid(o.size_id),captured=instantMicros(o.captured_at),q=obj(o.query)
 keys(q,['from_date','through_date','group_mode']);const query:NativeDemandQuery={from_date:day(q.from_date),through_date:day(q.through_date),group_mode:q.group_mode==='AS_SOLD'||q.group_mode==='RESTATED'?q.group_mode:fail()}
 const windowDays=BigInt((Date.parse(query.through_date)-Date.parse(query.from_date))/86400000+1)
 const capturedWibDay=new Date(Number(captured.micros/1000n)+7*3600000).toISOString().slice(0,10)
 if(query.through_date>=capturedWibDay)fail()
 if(windowDays<1n||windowDays>3661n||targetKey.split(':')[1]!==sizeId||binding.capturedAt&&captured.micros!==instantMicros(binding.capturedAt).micros)fail()
 if(binding.query&&(query.from_date!==binding.query.from_date||query.through_date!==binding.query.through_date||query.group_mode!==binding.query.group_mode))fail()
 if(!(demandBases as readonly unknown[]).includes(o.basis))fail()
 const result:TargetDemand={targetKey,sizeId,capturedAt:captured.value,query,basis:o.basis as TargetDemandBasis,
  ownTotalPcs:whole(o.own_total_pcs),ownAvailableDays:whole(o.own_available_days),dailyTotalPcs:maybe(o.daily_total_pcs,decimal),countedDays:maybe(o.counted_days,whole),dailySd:maybe(o.daily_sd,decimal),targetPcs:maybe(o.target_pcs,whole),reorderPointPcs:maybe(o.reorder_point_pcs,whole),analog:null}
 if(BigInt(result.ownAvailableDays)>windowDays||result.ownAvailableDays==='0'&&result.ownTotalPcs!=='0'||result.countedDays!==null&&(BigInt(result.countedDays)<1n||BigInt(result.countedDays)>3660n))fail()
 if(result.basis==='UNKNOWN'&&(result.dailyTotalPcs!==null||result.targetPcs!==null||result.reorderPointPcs!==null))fail()
 if(result.basis!=='UNKNOWN'&&(result.dailyTotalPcs===null||result.countedDays===null))fail()
 if(result.basis==='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'&&(!equalDecimal(result.dailyTotalPcs!,result.ownTotalPcs)||result.countedDays!==result.ownAvailableDays))fail()
 if(result.basis==='SELECTED_MANUAL_ASSUMPTION'&&result.countedDays!=='1')fail()
 if(o.analog!==null){
  const a=obj(o.analog);keys(a,['state','reason','choice_id','choice_revision','recorded_at','source_key','source_sku','source_name','scale_factor','review_reason','source_total_pcs','available_days','scaled_total_pcs','scaled_daily_sd'])
  const recorded=instantMicros(a.recorded_at),revision=whole(a.choice_revision),reason=label(a.reason,100)
  if(recorded.micros>captured.micros||BigInt(revision)<1n||BigInt(revision)>9223372036854775807n)fail()
  if(a.state!=='READY'&&a.state!=='UNAVAILABLE')fail()
  const analog:NonNullable<TargetDemand['analog']>={state:a.state,reason,choiceId:uuid(a.choice_id),revision,recordedAt:recorded.value,
   sourceKey:maybe(a.source_key,target),sourceSku:maybe(a.source_sku,label),sourceName:maybe(a.source_name,label),scale:maybe(a.scale_factor,decimal),reviewReason:label(a.review_reason),sourceTotalPcs:maybe(a.source_total_pcs,whole),availableDays:maybe(a.available_days,whole),scaledTotalPcs:maybe(a.scaled_total_pcs,decimal),scaledDailySd:maybe(a.scaled_daily_sd,decimal)}
  const cleared=reason==='ANALOG_CHOICE_CLEARED'
  if(cleared?[analog.sourceKey,analog.sourceSku,analog.sourceName,analog.scale].some(x=>x!==null):[analog.sourceKey,analog.sourceSku,analog.sourceName,analog.scale].some(x=>x===null))fail()
  if(analog.sourceKey&&(analog.sourceKey===targetKey||analog.sourceKey.split(':')[1]!==sizeId))fail()
  if(analog.scale&&fraction(analog.scale)[0]===0n)fail()
  if(a.state==='READY'){
   if(reason!=='EXPLICIT_REVIEWED_ANALOG_CURRENT_QUERY_HISTORY'||result.basis!=='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'||analog.sourceTotalPcs===null||analog.availableDays===null||analog.scaledTotalPcs===null||analog.scale===null)fail()
   if(BigInt(analog.availableDays)<1n||BigInt(analog.availableDays)>windowDays||!productEqual(analog.sourceTotalPcs,analog.scale,analog.scaledTotalPcs)||!equalDecimal(result.dailyTotalPcs!,analog.scaledTotalPcs)||result.countedDays!==analog.availableDays)fail()
   if(result.dailySd!==null&&(analog.scaledDailySd===null||!equalDecimal(result.dailySd,analog.scaledDailySd)))fail()
  }else{
   if(!['ANALOG_CHOICE_CLEARED','ANALOG_PROFILE_UNREVIEWED','ANALOG_PROFILE_CHANGED','ANALOG_SOURCE_UNAVAILABLE','ANALOG_PRODUCT_IDENTITY_CHANGED','ANALOG_CURRENT_HISTORY_INSUFFICIENT'].includes(reason)||result.basis!=='UNKNOWN'||[analog.sourceTotalPcs,analog.availableDays,analog.scaledTotalPcs,analog.scaledDailySd].some(x=>x!==null))fail()
  }
  result.analog=analog
 }
 if(result.basis==='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'&&result.analog?.state!=='READY')fail()
 return result
}

export function targetDemandBasisLabel(basis:TargetDemandBasis){return basis==='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'?'Riwayat produk saat stok tersedia':basis==='SELECTED_MANUAL_ASSUMPTION'?'Kebutuhan manual yang dipilih':basis==='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'?'Asumsi dari pembanding yang diperiksa':'Kebutuhan belum diketahui'}
export function analogUnavailableLabel(reason:string){return({ANALOG_CHOICE_CLEARED:'Pilihan pembanding sudah dicabut.',ANALOG_PROFILE_UNREVIEWED:'Profil perencanaan belum diperiksa.',ANALOG_PROFILE_CHANGED:'Profil perencanaan berubah setelah pembanding dipilih.',ANALOG_SOURCE_UNAVAILABLE:'Produk pembanding tidak tersedia dalam sumber perhitungan.',ANALOG_PRODUCT_IDENTITY_CHANGED:'Identitas atau ukuran produk berubah setelah pembanding dipilih.',ANALOG_CURRENT_HISTORY_INSUFFICIENT:'Riwayat pembanding pada periode ini belum cukup.'}as Record<string,string>)[reason]??'Dasar pembanding belum tersedia.'}
