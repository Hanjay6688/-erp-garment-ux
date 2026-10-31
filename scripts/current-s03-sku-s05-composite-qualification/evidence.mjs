import assert from 'node:assert/strict'
export {readable} from '../current-vendor-money-browser/visual.mjs'

export const IDS=[
 'S03_BROWSER_OWNER_EXPENSE_CORRECT_REVERSE_DESKTOP',
 'S03_BROWSER_OWNER_CARRY_ALLOCATE_CANCEL_MOBILE390',
 'S03_BROWSER_ACTUAL_STALE_AND_LOST_REPLY_SAME_UUID',
 'S03_BROWSER_CURRENT_AUTH_RIGHTS_AND_DELAYED_CONTEXT',
]
export const RPC={read:'erp_cp7_get_attendance_choice_v1',preview:'erp_cp7_preview_attendance_choice_v1',save:'erp_cp7_save_attendance_choice_v1',poolRead:'erp_cp7_get_hpp_pools_v1',poolSave:'erp_cp7_save_hpp_pool_v1'}
export function cents(value){const m=/^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value));assert.ok(m,'EXACT_MONEY_REQUIRED');const fraction=m[3]??'';assert.match(fraction.slice(2),/^0*$/,'NO_FRACTIONAL_CENT');return(BigInt(m[2])*100n+BigInt(fraction.slice(0,2).padEnd(2,'0')))*(m[1]?-1n:1n)}
export function input(day,choice=null,output=null,reason='Sumber tanggal dan biaya diperiksa Owner melalui layar'){return{period_start:day,period_end:day,choice,output_start:output,output_end:output,reason}}
export function equalCensus(a,b){
 for(const s of[a,b]){assert.equal(s.catalog_groups,22);assert.deepEqual(s.dropped_catalog_fields,[]);assert.deepEqual(s.dropped_row_columns,[]);assert.deepEqual(s.dropped_data_or_sequence_keys,[])}
 assert.equal(a.catalog_sha256,b.catalog_sha256,'ALL22_CATALOG_CHANGED');assert.deepEqual(a.data_and_sequences,b.data_and_sequences,'ROWS_OR_ALL_SEQUENCES_CHANGED');assert.equal(a.raw_all_rows_and_sequences_sha256,b.raw_all_rows_and_sequences_sha256,'RAW_ROWS_OR_SEQUENCES_CHANGED')
}
export function immutableFacts(before,after){
 assert.deepEqual(after.original_accrual,before.original_accrual,'ORIGINAL_ACCRUAL_CHANGED')
 for(const row of before.decisions)assert.deepEqual(after.decisions.find(x=>x.id===row.id),row,'APPEND_ONLY_DECISION_CHANGED')
 for(const row of before.requests)assert.deepEqual(after.requests.find(x=>x.actor===row.actor&&x.request_id===row.request_id),row,'HISTORICAL_RECEIPT_CHANGED')
 physicalFacts(before,after)
 historyFacts(before,after)
 for(const row of after.dated_WIP)assert.ok(BigInt(row.available_cents)>=0n,'NEGATIVE_DATED_WIP')
}
export const FG_FIELDS=['id','product_id','lot_id','location_id','quality_grade','movement_type','qty_signed','unit_hpp_snapshot','customer_id','source_type','source_id','physical_at','system_created_at','created_by','reversal_of_id','notes','book_order'].sort()
function decimal(value){const match=/^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value));assert.ok(match,'EXACT_NATIVE_DECIMAL_REQUIRED');const whole=match[2].replace(/^0+(?=\d)/,''),fraction=(match[3]??'').replace(/0+$/,'');return(match[1]&&!(whole==='0'&&!fraction)?'-':'')+whole+(fraction?'.'+fraction:'')}
export function physicalFacts(before,after){
 const old=before.physical_rows,next=after.physical_rows
 assert.deepEqual(next.map(r=>r.id),old.map(r=>r.id),'FG_ROWSET_CHANGED')
 for(const facts of[before,after]){const raw=Object.values(facts.finished_native??{}).flatMap(v=>v.FG).sort((a,b)=>a.id.localeCompare(b.id));assert.deepEqual(raw,facts.physical_rows,'WHOLE_NATIVE_FG_ROWS_REQUIRED')}
 const current=new Map(Object.values(after.finished_native??{}).flatMap(f=>f.current_HPP).map(r=>[r.lot_id,r]))
 for(let i=0;i<old.length;i++){
  const row=old[i],actual=next[i];assert.deepEqual(Object.keys(row).sort(),FG_FIELDS,'UNKNOWN_FG_COLUMNS');assert.deepEqual(Object.keys(actual).sort(),FG_FIELDS,'UNKNOWN_FG_COLUMNS')
  if(['QC_GOOD','REWORK_IN'].includes(row.movement_type)){
   const omit=r=>Object.fromEntries(Object.entries(r).filter(([key])=>key!=='unit_hpp_snapshot'))
   assert.deepEqual(omit(actual),omit(row),'ALL16_PHYSICAL_FIELDS_MUST_REMAIN_EXACT');assert.ok(current.has(row.lot_id),'CURRENT_NATIVE_HPP_MISSING')
   assert.equal(decimal(actual.unit_hpp_snapshot),decimal(current.get(row.lot_id).hpp_per_pcs),'RECEIPT_CACHE_MUST_EQUAL_CURRENT_NATIVE_HPP')
  }else assert.deepEqual(actual,row,'WHOLE_SALE_AND_NON_RECEIPT_ROWS_MUST_REMAIN_EXACT')
 }
 return{all16_non_cost_fields_exact:true,whole_SALE_rows_exact:true,only_Native_receiving_cache:true}
}
export function historyFacts(before,after){
 for(const[po,old]of Object.entries(before.finished_native??{})){
  const next=after.finished_native?.[po];assert.ok(next,'FINISHED_NATIVE_PO_HISTORY_MISSING')
  for(const name of['journal_lines','HPP_components']){
   assert.ok(Array.isArray(old[name])&&Array.isArray(next[name]),'FULL_POSTED_NATIVE_HISTORY_REQUIRED')
   assert.equal(new Set(next[name].map(r=>r.id)).size,next[name].length,'DUPLICATE_NATIVE_HISTORY_ROW')
   for(const row of old[name])assert.deepEqual(next[name].find(x=>x.id===row.id),row,name==='journal_lines'?'POSTED_JOURNAL_LINE_HISTORY_CHANGED':'HPP_COMPONENT_HISTORY_CHANGED')
  }
  for(const row of old.journal_headers){const current=next.journal_headers.find(x=>x.id===row.id);assert.ok(current,'POSTED_JOURNAL_HEADER_REMOVED')
   if(current.status!==row.status){assert.equal(row.status,'POSTED');assert.equal(current.status,'REVERSED');assert.deepEqual({...current,status:row.status},row,'JOURNAL_HISTORY_FACT_CHANGED');assert.equal(next.journal_headers.filter(x=>x.reversal_of_id===row.id&&x.source_type==='JOURNAL_REVERSAL'&&x.source_id===row.id&&x.status==='POSTED').length,1,'ACTUAL_LINKED_NATIVE_INVERSE_REQUIRED')}
   else assert.deepEqual(current,row,'POSTED_JOURNAL_HEADER_HISTORY_CHANGED')
  }
  for(const row of old.HPP_history){const current=next.HPP_history.find(x=>x.id===row.id);assert.ok(current,'HPP_HISTORY_REMOVED');const omit=r=>Object.fromEntries(Object.entries(r).filter(([key])=>key!=='is_current'));assert.deepEqual(omit(current),omit(row),'HPP_HISTORY_FACT_CHANGED');assert.ok(current.is_current===row.is_current||row.is_current===true&&current.is_current===false,'HPP_CURRENT_POINTER_REACTIVATED')}
 }
 return{posted_and_inverse_history_retained:true,HPP_history_append_only:true}
}
export function exactEnvelope(args,action,payload,token){assert.deepEqual(Object.keys(args).sort(),['p_action','p_payload','p_request']);assert.equal(args.p_action,action);assert.match(args.p_request,/^[0-9a-f-]{36}$/);assert.match(token,/^[a-f0-9]{64}$/);assert.deepEqual(args.p_payload,{...payload,review_token:token})}
export function accessRefusals(admin,anon){assert.equal(admin.status,403,JSON.stringify(admin.body));assert.equal(admin.body?.code,'42501');assert.ok(String(admin.body?.message).includes('CP7_S03_OWNER_REQUIRED'));assert.ok([401,403].includes(anon.status),JSON.stringify(anon.body));assert.equal(anon.body?.code,'42501');assert.match(String(anon.body?.message),/permission denied for function erp_cp7_get_attendance_choice_v1\b/);return{Admin:{status:admin.status,code:admin.body.code,message:admin.body.message},anonymous:{status:anon.status,code:anon.body.code,message:anon.body.message},anonymous_boundary:'ACTUAL_PUBLIC_FUNCTION_EXECUTE_ACL_BEFORE_OWNING_BODY'}}
export function observeConsole(page){const errors=[],pageErrors=[];const c=m=>{if(m.type()==='error')errors.push({text:m.text(),location:m.location()})},e=x=>pageErrors.push(String(x.message||x));page.on('console',c);page.on('pageerror',e);return{errors,pageErrors,stop(){page.off('console',c);page.off('pageerror',e)}}}
export function consoleEvidence(observed,expected){const unused=expected.map(x=>({...x})),accepted=[],unexpected=[];for(const error of observed.errors){const n=unused.findIndex(x=>x.url===error.location.url&&x.text===error.text);if(n<0)unexpected.push(error);else accepted.push({...error,reason:unused.splice(n,1)[0].reason})}assert.deepEqual(observed.pageErrors,[],'UNEXPECTED_PAGE_ERROR');assert.deepEqual(unexpected,[],'UNEXPECTED_CONSOLE_ERROR');return{observed:observed.errors,causally_verified_network_errors:accepted,unexpected,page_errors:observed.pageErrors}}
