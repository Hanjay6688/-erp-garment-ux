export type CuttingYieldRequest={id:string;groupId:string}
export type NativeCuttingYieldRow={sliceId:string;groupId:string;rollId:string;materialId:string;materialSku:string;patternId:string|null;patternRevision:string|null;physicalAt:string;knownAt:string;actual:null|{consumed:string;unit:string;totalPcs:string;bySize:{yieldId:string;sizeId:string;qtyPcs:string}[]};reason:string}
export type NativeCuttingYield={runId:string;requestId:string;sourceHash:string;capturedAt:string;state:'UNCHANGED'|'ARCHIVED_STALE';rows:NativeCuttingYieldRow[]}
const fail=():never=>{throw Error('Sumber hasil potong belum lengkap atau tidak cocok. Muat ulang sumber.')}
const obj=(v:unknown)=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const text=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const pcs=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)?v:fail()
const decimal=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?$/.test(v)?v:fail()
const array=(v:unknown,max:number)=>Array.isArray(v)&&v.length<=max?v as unknown[]:fail()
function micros(v:unknown){if(typeof v!=='string')return fail();const m=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/.exec(v),n=Date.parse(v);if(!m||!Number.isFinite(n))return fail();return BigInt(n)*1000n+BigInt((m[1]??'').padEnd(6,'0').slice(3))}
function closed(v:unknown,fields:string[]){const r=obj(v);if(Object.keys(r).length!==fields.length||fields.some(k=>!(k in r)))fail();return r}
export function parseNativeCuttingYield(value:unknown,groupId:string):NativeCuttingYield{
 const v=closed(value,['contract_version','rows','knowledge_basis','model_qualified','automatic_activation','business_write','production_go','run_id','request_id','source_hash','captured_at','source_state'])
 if(v.contract_version!=='cp7.native-cutting-yield-source.v1'||v.knowledge_basis!=='CURRENT_CAPTURE_ONLY'||v.model_qualified!==false||v.automatic_activation!==false||v.business_write!==false||v.production_go!==false||!Array.isArray(v.rows)||v.rows.length>1000||!['UNCHANGED','ARCHIVED_STALE'].includes(text(v.source_state)))fail()
 uuid(groupId);const capturedAt=text(v.captured_at);micros(capturedAt);const sourceHash=text(v.source_hash);if(!/^[a-f0-9]{64}$/.test(sourceHash))fail()
 const seen=new Set<string>();const rows:NativeCuttingYieldRow[]=array(v.rows,1000).map(raw=>{
  const r=closed(raw,['slice_id','group_id','roll_id','material_id','material_sku','pattern_id','pattern_revision','physical_at','known_at','actual','family','planned_mix','recorded_width_cm','measured_remaining','interval','assessment','reason','calculated_remaining_is_not_physical_measurement','output_mix_is_not_preknown_planned_mix','later_laundry_BS_is_not_cutting_cause'])
  const sliceId=uuid(r.slice_id);if(seen.has(sliceId)||uuid(r.group_id)!==groupId||micros(r.known_at)!==micros(capturedAt)||r.assessment!=='UNAVAILABLE'||r.family!==null||r.planned_mix!==null||r.recorded_width_cm!==null||r.measured_remaining!==null||r.interval!==null||r.calculated_remaining_is_not_physical_measurement!==true||r.output_mix_is_not_preknown_planned_mix!==true||r.later_laundry_BS_is_not_cutting_cause!==true)fail();seen.add(sliceId)
  const reason=text(r.reason);if(!['NATIVE_CUTTING_NOT_POSTED','NATIVE_OUTPUT_OR_CONSUMPTION_INCOMPLETE','PROSPECTIVE_FAMILY_MIX_AND_VALIDATED_INTERVAL_REQUIRED'].includes(reason))fail()
  let actual:NativeCuttingYieldRow['actual']=null
  if(r.actual!==null){const a=closed(r.actual,['consumed','unit','total_pcs','by_size']);if(reason!=='PROSPECTIVE_FAMILY_MIX_AND_VALIDATED_INTERVAL_REQUIRED'||!Array.isArray(a.by_size))fail();const bySize:NonNullable<NativeCuttingYieldRow['actual']>['bySize']=[],ids=new Set<string>();let sum=0n
   for(const rawSize of array(a.by_size,10000)){const y=closed(rawSize,['yield_id','size_id','qty_pcs']),yieldId=uuid(y.yield_id),qtyPcs=pcs(y.qty_pcs);if(ids.has(yieldId))fail();ids.add(yieldId);sum+=BigInt(qtyPcs);bySize.push({yieldId,sizeId:uuid(y.size_id),qtyPcs})}
   const totalPcs=pcs(a.total_pcs),consumed=decimal(a.consumed);if(sum!==BigInt(totalPcs)||sum<=0n||!/[1-9]/.test(consumed))fail();actual={consumed,unit:text(a.unit),totalPcs,bySize}
  }else if(reason==='PROSPECTIVE_FAMILY_MIX_AND_VALIDATED_INTERVAL_REQUIRED')fail()
  const physicalAt=text(r.physical_at);micros(physicalAt);const patternId=r.pattern_id===null?null:uuid(r.pattern_id),patternRevision=r.pattern_revision===null?null:text(r.pattern_revision);if((patternId===null)!==(patternRevision===null))fail()
  return{sliceId,groupId,rollId:uuid(r.roll_id),materialId:uuid(r.material_id),materialSku:text(r.material_sku),patternId,patternRevision,physicalAt,knownAt:text(r.known_at),actual,reason}
 })
 return{runId:uuid(v.run_id),requestId:uuid(v.request_id),sourceHash,capturedAt,state:v.source_state as NativeCuttingYield['state'],rows}
}
export const cuttingYieldRequestKey=(scope:string)=>'erp.cp7.cutting-yield-request.v1:'+scope
export function readCuttingYieldRequest(scope:string):{pending:CuttingYieldRequest|null;error:string}{
 try{const raw=localStorage.getItem(cuttingYieldRequestKey(scope));if(raw===null)return{pending:null,error:''};const r=closed(JSON.parse(raw),['id','groupId']);return{pending:{id:uuid(r.id),groupId:uuid(r.groupId)},error:''}}
 catch{return{pending:null,error:'Catatan pembacaan belum dapat dipulihkan. Periksa penyimpanan sebelum membuat permintaan baru.'}}
}
export function persistCuttingYieldRequest(scope:string,r:CuttingYieldRequest){const held=readCuttingYieldRequest(scope);if(held.pending||held.error)throw Error('Pulihkan pembacaan tersimpan terlebih dahulu.');uuid(r.id);uuid(r.groupId);const raw=JSON.stringify(r);localStorage.setItem(cuttingYieldRequestKey(scope),raw);if(localStorage.getItem(cuttingYieldRequestKey(scope))!==raw)throw Error('Permintaan belum tersimpan; pembacaan ditahan.')}
export function clearCuttingYieldRequest(scope:string,r:CuttingYieldRequest){const held=readCuttingYieldRequest(scope);if(held.error||held.pending?.id!==r.id||held.pending.groupId!==r.groupId)throw Error('Permintaan pembacaan berubah.');localStorage.removeItem(cuttingYieldRequestKey(scope));if(localStorage.getItem(cuttingYieldRequestKey(scope))!==null)throw Error('Catatan pembacaan belum selesai.')}
