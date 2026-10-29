// Local harness/oracle controls. These are not Native/Auth/browser results.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFileSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import test from 'node:test'
import {IDS,HOSTILE_QUESTION,cases,assertManualPrompt,assertExactState,assertOneSourceCheck,holdNativeResponse} from './cases.mjs'

const HERE=dirname(fileURLToPath(import.meta.url)),REPO=resolve(HERE,'../..')
const clone=value=>structuredClone(value)
const a='00000000-0000-4000-8000-000000000001:00000000-0000-4000-8000-000000000002'
const stamp='2026-10-28T20:30:00.000Z'
function sample(){
  const row={ord:1,page_index:0,target_key:a,sku:'SKU-LOCAL-ORACLE',product_name:'Local synthetic oracle control',production_state:'ACTIVE',available_fg_pcs:'0',target_pcs:'100',raw_gap_pcs:'100',base_gap_pcs:'93',conditional_gap_pcs:'93',directed_on_time_good_pcs:null,candidate_allocated_good_pcs:'7',assumption_ids:['YIELD_ASSUMED']}
  const wire={run_id:'local-run',identity_hash:'local-hash',data_as_of:stamp,query:{from_date:'2026-10-01',through_date:'2026-10-28',group_mode:'AS_SOLD'},targets_total:1,totals:{items:{sources:1},targets:1,recommendations:{ACTIVE:1},policy_unreviewed:0},need_counts:{targets:1,with_open_need:1,need_unknown:0},priority:[row],selected:[row],freshness:{freshness_state:'NO_RECORDED_CHANGE',evaluated_at:stamp,changes_since:[],last_full_check:null}}
  const {ord,...selected}=row
  const scope={contract_version:'cp7.native-ai-handoff-staged.v1',run_id:wire.run_id,identity_hash:wire.identity_hash,data_analysis_as_of:stamp,data_analysis_as_of_wib:'2026-10-29 03:30:00 WIB',freshness_state:wire.freshness.freshness_state,freshness_evaluated_at:stamp,history_query:wire.query,targets_total:1,finance:'NOT_INCLUDED'}
  const data={totals:{items:wire.totals.items,targets:1,recommendations:wire.totals.recommendations,policyUnreviewed:0},need_counts:{targets:1,withOpenNeed:1,needUnknown:0},priority_targets_largest_open_need:[clone(selected)],selected_targets:[clone(selected)],changes_since_analysis:[],last_full_check:null,actual_finance:null}
  const json=value=>JSON.stringify(value).replaceAll('<','\\u003c').replaceAll('>','\\u003e')
  const make=(value=data,question=HOSTILE_QUESTION)=>['Angka analisis adalah keadaan per tanggal fixture, bukan angka saat ini.','Keuangan dan HPP tidak disertakan; nyatakan belum diketahui, jangan menebak.','CAKUPAN SUMBER',json(scope),'<DATA_ERP_JSON>',json(value),'</DATA_ERP_JSON>','<PERTANYAAN_JSON>',json(question),'</PERTANYAAN_JSON>'].join('\n\n')
  return {wire,data,make}
}
function states(){
  const before={data:{'erp.fg_stock_movements':[3,'stock-hash'],'erp.journal_lines':[5,'journal-hash'],'cp7_credit.applications':[2,'credit-hash'],'sequence:erp.invoice_id_seq':['18',true],'cp7_analysis_stage.source_checks':[0,'empty-hash'],'sequence:cp7_analysis_stage.source_checks_id_seq':['1',false]},source_checks:[],census_keys:6,table_keys:4,sequence_keys:2,excluded_catalog_keys:[]}
  const after=clone(before),row={id:1,actor:'actual-actor',run_id:'actual-run',checked_at:stamp,recorded_at:stamp,source_state:'UNCHANGED',source_snapshot:'1:3:'}
  after.source_checks.push(row);after.data['cp7_analysis_stage.source_checks']=[1,'check-hash'];after.data['sequence:cp7_analysis_stage.source_checks_id_seq']=['1',true]
  const wire={contract_version:'cp7.native-analysis-snapshot-check.v1',run_id:row.run_id,source_state:'UNCHANGED',checked_at:stamp,boundary:'SNAPSHOT'}
  return {before,after,wire}
}

test('exactly two host closures plan desktop/mobile without login, fixtures or a new server',()=>{
  const ui=new Proxy({}, {get(){throw Error('PLANNING_MUST_HAVE_NO_RUNTIME_SIDE_EFFECT')}})
  const rows=cases(ui,'2026-10-29')
  assert.deepEqual(rows.map(([id])=>id),IDS);assert.equal(rows.length,2)
  assert.ok(rows.every(([,operation])=>typeof operation==='function'))
  assert.ok(HOSTILE_QUESTION.length>7000&&HOSTILE_QUESTION.length<10000)
})

test('manual oracle preserves long hostile JSON, exact Native known values and unknowns',()=>{
  const {wire,make}=sample(),text=make()
  assert.equal(assertManualPrompt(text,wire,HOSTILE_QUESTION,[a]).characters,text.length)
})

test('manual oracle rejects silent truncation, wrong selected target, changed numeric facts and unknown-to-zero',()=>{
  const {wire,data,make}=sample()
  assert.throws(()=>assertManualPrompt(make(data,HOSTILE_QUESTION.slice(0,-1)),wire,HOSTILE_QUESTION,[a]),/TRUNCATED_OR_CHANGED/)
  for(const mutation of [d=>{d.selected_targets[0].target_key='other'},d=>{d.selected_targets[0].conditional_gap_pcs='92'},d=>{d.selected_targets[0].directed_on_time_good_pcs='0'}]){
    const wrong=clone(data);mutation(wrong)
    assert.throws(()=>assertManualPrompt(make(wrong),wire,HOSTILE_QUESTION,[a]),/SELECTED_NATIVE_FACT_CHANGED/)
  }
})

test('absolute AI-only census rejects business updates, sequence allocations, deleted keys and excluded schemas',()=>{
  const {before}=states();assertExactState(before,clone(before))
  for(const mutation of [s=>{s.data['cp7_credit.applications'][1]='changed'},s=>{s.data['sequence:erp.invoice_id_seq'][0]='19'},s=>{delete s.data['erp.journal_lines']},s=>{s.excluded_catalog_keys=['auth']}] ){
    const wrong=clone(before);mutation(wrong);assert.throws(()=>assertExactState(before,wrong))
  }
})

test('source-check census allows only its exact append/allocation, rejects any business change or second append',()=>{
  const {before,after,wire}=states();assertOneSourceCheck(before,after,wire,'actual-actor','actual-run')
  for(const mutation of [s=>{s.data['erp.fg_stock_movements'][1]='changed'},s=>{s.data['cp7_credit.applications'][1]='changed'},s=>{s.data['sequence:erp.invoice_id_seq'][0]='19'},s=>{s.source_checks.push(clone(s.source_checks[0]))},s=>{s.data['sequence:cp7_analysis_stage.source_checks_id_seq'][0]='2'},s=>{s.source_checks[0].actor='other'}]){
    const wrong=clone(after);mutation(wrong);assert.throws(()=>assertOneSourceCheck(before,wrong,wire,'actual-actor','actual-run'))
  }
})

test('response-delay control forwards the same real response object without replacing its body/status',async()=>{
  let handler,completed=false,fulfilled
  const response={status:()=>200,text:async()=>'{"original_native_fact":"93","unknown":null}'}
  const route={request:()=>({url:()=> 'http://127.0.0.1:43210/rest/v1/rpc/example',postDataJSON:()=>({p_run:'run'})}),fetch:async()=>response,fulfill:async value=>{fulfilled=value;completed=true},abort:async()=>{throw Error('UNEXPECTED_ABORT')}}
  const page={route:async(_match,h)=>{handler=h},unroute:async(_match,h)=>assert.equal(h,handler)}
  const gate=await holdNativeResponse(page,'http://127.0.0.1:43210','example'),running=handler(route)
  await new Promise(ok=>setImmediate(ok));assert.equal(completed,false)
  assert.deepEqual(gate.record.body,{original_native_fact:'93',unknown:null})
  await gate.release();await running;assert.deepEqual(Object.keys(fulfilled),['response']);assert.equal(fulfilled.response,response)
  await gate.close()
})

test('source plan pins product fix, qualified reused host/helper inputs and every new namespace source',()=>{
  const source=JSON.parse(readFileSync(resolve(HERE,'SOURCE.json'),'utf8'))
  assert.equal(source.status,'PREPARED');assert.equal(source.actual_native_auth_browser_executed,false)
  assert.equal(source.ai_source_commit,'4827530938a9cba85cbde8bff896acab6713c72e')
  assert.ok(source.files.length>=12)
  for(const {path,bytes,sha256} of source.files){
    assert.ok(!path.startsWith('/')&&!path.split('/').includes('..'))
    const raw=readFileSync(resolve(REPO,path));assert.equal(raw.length,bytes,path)
    assert.equal(createHash('sha256').update(raw).digest('hex'),sha256,path)
  }
  const bindings=new Set(source.files.map(row=>row.path))
  for(const name of ['src/NativeStagedAiPanel.tsx','src/nativeStagedAi.ts','scripts/cp6_auditor_browser_host.mjs','scripts/current-finance-combined-browser-qualification/console_evidence.mjs','scripts/current-frozen-public-native-qualification/public_finance_cases.py','scripts/cp7_ow04_restore_bundle.py'])assert.ok(bindings.has(name),name)
})
