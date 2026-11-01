// Pure future browser-oracle checks and actual closed-parent refusal, zero browser credit.
import assert from 'node:assert/strict'
import {spawnSync} from 'node:child_process'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {IDS,cases,dateChanges} from './browser.mjs'

const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const before=()=>({catalog_groups:22,catalog_sha256:'all22',dropped_catalog_fields:[],dropped_data_or_sequence_keys:[],
  active_good:{hpp:'20',reimbursement:'0',entitlements:[],stock:'997'},
  data_and_sequences:{'erp.journal_lines':[2,'money'],'erp.app_users':[1,'actor'],
    'sequence:erp.audit_logs_id_seq':['10',true],'cp7_accessory_nonpayable.category_versions_v1':[1,'history'],
    'cp7_accessory_nonpayable.date_requests_v1':[1,'requests']},
  date_versions:[{id:'v1',day:'2026-11-01'}],date_requests:[{request_id:'r1',intent:'old'}],original:{name:'synthetic-census'}})
const checks=[]
function test(name,operation){operation();checks.push({name,status:'PASS'})}

test('COMPLETE_BROWSER_CENSUS_AND_EXACT_APPEND_ONLY_DATE_REQUEST_ORACLE',()=>{
  const a=before();dateChanges(a,structuredClone(a))
  const b=structuredClone(a);b.date_versions.push({id:'v2',day:'2026-11-02'});b.date_requests.push({request_id:'r2',intent:'new'})
  b.data_and_sequences['cp7_accessory_nonpayable.category_versions_v1']=[2,'new-history']
  b.data_and_sequences['cp7_accessory_nonpayable.date_requests_v1']=[2,'new-request']
  assert.deepEqual(dateChanges(a,b,{requests:['r2'],versions:['v2']}).actual_changed_tables,
    ['cp7_accessory_nonpayable.category_versions_v1','cp7_accessory_nonpayable.date_requests_v1'])
})
test('BROWSER_ORACLE_REFUSES_MONEY_ACCESS_SEQUENCE_AND_CENSUS_OMISSION',()=>{
  for(const mode of['money','access','sequence','missing-key','catalog','active-good']){
    const a=before(),b=structuredClone(a)
    if(mode==='money')b.data_and_sequences['erp.journal_lines']=[2,'wrong']
    else if(mode==='access')b.data_and_sequences['erp.app_users']=[2,'wrong']
    else if(mode==='sequence')b.data_and_sequences['sequence:erp.audit_logs_id_seq']=['11',true]
    else if(mode==='missing-key')delete b.data_and_sequences['erp.journal_lines']
    else if(mode==='catalog')b.catalog_sha256='changed'
    else b.active_good.hpp='0'
    assert.throws(()=>dateChanges(a,b),undefined,mode)
  }
})
test('BROWSER_ORACLE_REFUSES_ERASED_CHANGED_OR_DUPLICATE_POSTED_DATE_HISTORY',()=>{
  for(const mode of['erased','changed','duplicate']){
    const a=before(),b=structuredClone(a)
    if(mode==='erased')b.date_versions=[]
    else if(mode==='changed')b.date_versions[0].day='2026-11-03'
    else b.date_versions.push(structuredClone(b.date_versions[0]))
    assert.throws(()=>dateChanges(a,b),undefined,mode)
  }
})
test('BROWSER_FACTORY_REFUSES_MISSING_ACTUAL_PARENT_BEFORE_UI_OR_AUTH',()=>{
  assert.equal(IDS.length,2);assert.equal(new Set(IDS).size,2)
  assert.throws(()=>cases(Object.freeze({})),error=>String(error.stderr).includes('NONPAYABLE_ACTUAL_FREE3_ROOT_INTAKE_PENDING'))
})
test('NATIVE_BROWSER_PREPARATION_REFUSES_CLOSED_PARENT_BEFORE_CURSOR_USE',()=>{
  const script="import sys;sys.path.insert(0,'scripts');from datetime import date;from cp7_accessory_nonpayable.browser_prepare import prepare\ntry:prepare(object(),date(2026,11,1),{})\nexcept ValueError as error:\n assert str(error)=='NONPAYABLE_ACTUAL_FREE3_ROOT_INTAKE_PENDING';print('CLOSED_BEFORE_SQL')\nelse:raise AssertionError('MISSING_PARENT_BYPASSED')"
  const child=spawnSync('python',['-B','-c',script],{cwd:ROOT,encoding:'utf8',timeout:30000})
  assert.equal(child.status,0,child.stderr);assert.equal(child.stdout.trim(),'CLOSED_BEFORE_SQL')
})
console.log(JSON.stringify({status:'BROWSER2_SOURCE_PREPARATION_CONTROLS_PASS',checks,actual_Native_cases:0,
  actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false}))
