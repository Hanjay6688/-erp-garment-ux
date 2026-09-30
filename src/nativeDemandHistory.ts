export type NativeDemandRow={targetKey:string;rootId:string;sizeId:string;sku:string;productName:string;active:boolean;physical:string;reserved:string;available:string;gross:string;returns:string;availableDays:number;unknownDays:number;stockoutDays:number;trainingAvailable:boolean}
export type NativeDemandHistory={runId:string;requestId:string;capturedAt:string;sourceHash:string;state:'UNCHANGED'|'ARCHIVED_STALE';from:string;through:string;basis:'AS_SOLD'|'RESTATED';rows:NativeDemandRow[]}
export type NativeDemandQuery={from_date:string;through_date:string;group_mode:'AS_SOLD'|'RESTATED'}
export type NativeDemandRequest={id:string;q:NativeDemandQuery}
const fail=():never=>{throw Error('Data permintaan dari server belum lengkap atau berubah. Muat ulang.')}
const object=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const text=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const pcs=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,29})$/.test(v)?v:fail()
const signedPcs=(v:unknown)=>typeof v==='string'&&/^(0|-?[1-9][0-9]{0,29})$/.test(v)?v:fail()
const count=(v:unknown)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:fail()
const array=(v:unknown,max:number)=>Array.isArray(v)&&v.length<=max?v:fail()
const day=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v?v:fail()
const instant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const refs=(v:unknown)=>{for(const r of array(v,50000)){const x=object(r);text(x.kind);text(x.id);pcs(x.revision)}}
export function parseNativeDemandHistory(value:unknown):NativeDemandHistory{
 const v=object(value),h=object(v.history),versions=object(v.versions)
 if(v.contract_version!=='cp7.native-demand-history.v1'||v.scope!=='GLOBAL_CURRENT_PHYSICAL_ROOTS'||v.capture_complete!==true||v.production_go!==false
  ||v.availability_knowledge_basis!=='CURRENT_CAPTURE_RESTATED_LEDGER'||v.model_eligibility!=='HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED'
  ||versions.producer!=='native-demand-1'||versions.history!=='demand-1'||versions.availability!=='availability-1')fail()
 const hash=text(v.source_hash);if(!/^[0-9a-f]{64}$/.test(hash))fail()
 const captured=instant(v.captured_at);if(v.training_known_at!==captured||h.known_as_of!==captured||h.effective_as_of!==captured||h.snapshot_id!==hash||h.scope_id!==v.scope
  ||h.contract_version!=='cp7.demand-result.v1'||h.kernel_version!=='demand-1'||h.status!=='CAPTURE_COMPLETE')fail()
 if(v.source_state!=='UNCHANGED'&&v.source_state!=='ARCHIVED_STALE')fail()
 if(h.group_mode!=='AS_SOLD'&&h.group_mode!=='RESTATED')fail()
 const from=day(h.from_date),through=day(h.through_date);if(from>through)fail()
 const days=(Date.parse(through)-Date.parse(from))/86400000+1;if(days>3661)fail()
 const histories=new Map<string,Record<string,unknown>>()
 for(const raw of array(h.rows,1000)){
  const r=object(raw),key=text(r.target_key);if(histories.has(key))fail();histories.set(key,r)
  uuid(r.size_id);pcs(r.gross_observed_pcs);pcs(r.draft_reserved_pcs);refs(r.refs)
  if(count(r.available_days)+count(r.unknown_days)+count(r.stockout_days)!==days)fail()
  const daily=array(r.days,3661);if(daily.length!==days)fail()
  let gross=0n;for(let i=0;i<daily.length;i++){
   const d=object(daily[i]);if(day(d.date)!==new Date(Date.parse(from)+i*86400000).toISOString().slice(0,10))fail()
   if(!['AVAILABLE','STOCKOUT','UNKNOWN'].includes(text(d.state)))fail()
   const g=pcs(d.gross_observed_pcs),returned=pcs(d.returned_pcs);if(BigInt(returned)>BigInt(g))fail();gross+=BigInt(g)
   if(d.state==='AVAILABLE'){if(pcs(d.training_pcs)!==g)fail()}else if(d.training_pcs!==null)fail()
  }
  if(gross!==BigInt(pcs(r.gross_observed_pcs)))fail()
 }
 const seen=new Set<string>(),rows:NativeDemandRow[]=[]
 for(const raw of array(v.current_stock,1000)){
  const r=object(raw),root=uuid(r.root_id),size=uuid(r.size_id),key=text(r.target_key),a=object(r.availability),inputs=object(a.inputs)
  if(key!==root+':'+size||seen.has(key)||typeof r.is_active!=='boolean'||r.grade_basis!=='NATIVE_SELLABLE_GRADE_A_AND_B'||r.projection_basis!=='CURRENT_STOCK_ONLY_NO_FORECAST')fail();seen.add(key)
  if(a.status!=='KNOWN'||a.kernel_version!=='availability-1'||inputs.snapshot_id!==hash||inputs.scope_id!==v.scope||inputs.target_key!==key||inputs.size_id!==size||inputs.residual_future_pcs!=='0')fail()
  const physical=pcs(a.physical_fg_pcs),reserved=pcs(a.reserved_pcs),available=signedPcs(a.available_fg_pcs)
  if(BigInt(physical)-BigInt(reserved)!==BigInt(available)||r.native_available_pcs!==available)fail();refs(r.refs)
  const hr=histories.get(key)??fail();if(hr.size_id!==size)fail()
  let returned=0n;for(const rawDay of array(hr.days,3661))returned+=BigInt(pcs(object(rawDay).returned_pcs))
  rows.push({targetKey:key,rootId:root,sizeId:size,sku:text(r.sku),productName:text(r.product_name),active:r.is_active as boolean,physical,reserved,available,
   gross:pcs(hr.gross_observed_pcs),returns:returned.toString(),availableDays:count(hr.available_days),unknownDays:count(hr.unknown_days),stockoutDays:count(hr.stockout_days),trainingAvailable:count(hr.available_days)>0})
 }
 if(seen.size!==histories.size)fail()
 return {runId:uuid(v.run_id),requestId:uuid(v.request_id),capturedAt:captured,sourceHash:hash,state:v.source_state as NativeDemandHistory['state'],from,through,basis:h.group_mode as NativeDemandHistory['basis'],rows}
}

export function yesterdayWib(now=new Date()){
 const y=new Date(now.getTime()+7*3600000-86400000);return y.toISOString().slice(0,10)
}

export function nativeDemandRequestKey(scope:string){return 'erp.cp7.native-demand-request.v1:'+scope}
export function readNativeDemandRequest(scope:string):{pending:NativeDemandRequest|null;error:string}{
 try{
  const raw=localStorage.getItem(nativeDemandRequestKey(scope));if(raw===null)return{pending:null,error:''}
  const v=object(JSON.parse(raw)),q=object(v.q)
  if(Object.keys(v).sort().join('|')!=='id|q'||Object.keys(q).sort().join('|')!=='from_date|group_mode|through_date'||!['AS_SOLD','RESTATED'].includes(text(q.group_mode)))fail()
  const from=day(q.from_date),through=day(q.through_date);if(from>through)fail()
  return{pending:{id:uuid(v.id),q:{from_date:from,through_date:through,group_mode:q.group_mode as NativeDemandQuery['group_mode']}},error:''}
 }catch{return{pending:null,error:'Permintaan tersimpan belum bisa dibaca. Jangan hapus catatan ini; pulihkan penyimpanan sebelum membuat analisis baru.'}}
}
export function persistNativeDemandRequest(scope:string,r:NativeDemandRequest){
 const before=readNativeDemandRequest(scope);if(before.error||before.pending)throw Error('Selesaikan permintaan tersimpan sebelum membuat analisis baru.')
 const raw=JSON.stringify(r);localStorage.setItem(nativeDemandRequestKey(scope),raw)
 if(localStorage.getItem(nativeDemandRequestKey(scope))!==raw||readNativeDemandRequest(scope).pending?.id!==r.id)throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')
}
export function clearNativeDemandRequest(scope:string,id:string){
 const held=readNativeDemandRequest(scope);if(held.error||held.pending?.id!==id)throw Error('Catatan permintaan berubah. Ulangi permintaan tersimpan.')
 localStorage.removeItem(nativeDemandRequestKey(scope));if(localStorage.getItem(nativeDemandRequestKey(scope))!==null)throw Error('Catatan permintaan belum bisa diselesaikan.')
}
