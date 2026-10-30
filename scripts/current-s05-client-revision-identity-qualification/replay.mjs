// Reuse all exact Native10 response bytes; this is client-contract evidence, not a browser run.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {resolve,dirname} from 'node:path'
import {pathToFileURL,fileURLToPath} from 'node:url'

const HERE=dirname(fileURLToPath(import.meta.url)),ROOT=resolve(HERE,'../..')
const [oldRepoArg,originalArg,outputArg]=process.argv.slice(2)
assert.ok(oldRepoArg&&originalArg&&outputArg,'Supply exact519 repository, original CASE JSON and outside-repository output')
const oldRepo=resolve(oldRepoArg),source='src/accessoryStandardReport.ts',head='519d1760a3bad06a346b3d4b3cc0203664615634'
const hash=b=>createHash('sha256').update(b).digest('hex')
const raw=readFileSync(resolve(originalArg)),old=readFileSync(resolve(oldRepo,source)),current=readFileSync(resolve(ROOT,source))
assert.equal(raw.length,232514);assert.equal(hash(raw),'7b13beaa9d369398a2e6c3762d9649303e92e6c835aba8b476a5d51842f3d79a')
assert.equal(hash(old),'982988ce7a48c624294bcb22a6663ae8bd842825ecfa74c72b8f1fa697a6f1a1')
assert.deepEqual(old,execFileSync('/usr/bin/git',['-C',ROOT,'show',head+':'+source]))
const before='return { id: idText(x.id), material_id:',after='return { id: uuid(x.id), material_id:'
assert.equal(old.toString().split(before).length,2);assert.equal(current.toString(),old.toString().replace(before,after))
const oldParse=(await import(pathToFileURL(resolve(oldRepo,source)).href)).parseAccessoryReportWorkspace
const parse=(await import(pathToFileURL(resolve(ROOT,source)).href)).parseAccessoryReportWorkspace
const original=JSON.parse(raw),results=[],oldRefusals=[],newErrors=[]
assert.equal(original.status,'PASS');assert.deepEqual(original.counts,{PASS:10})
let oldPass=0,reads=0,denials=0
for(const [id,entry]of Object.entries(original.cases)){
 assert.equal(entry.status,'PASS')
 for(const [index,row]of entry.actual_raw_reads.entries()){
  if(!Object.hasOwn(row,'actual')){assert.equal(row.actual_error.sqlstate,'42501');denials++;continue}
  assert.equal(row.query.length,7)
  const [period_start,period_end,contractor_id,po_id,q,offset,limit]=row.query
  assert.match(offset,/^\d+$/);assert.match(limit,/^\d+$/)
  const query={period_start,period_end,contractor_id,po_id,q,offset:Number(offset),limit:Number(limit)}
  let prior
  try{prior=oldParse(row.actual,query);oldPass++}catch(error){oldRefusals.push({case_id:id,read_index:index,message:error.message})}
  try{
   const result=parse(row.actual,query)
   const {definitions,...financialReport}=row.actual.report
   assert.deepEqual(definitions,{actual:'POSTED_ISSUE_PHYSICAL_WIB',comparison:'PERIOD_COHORTS_NOT_PO_WASTE',
    cost:'NATIVE_EFFECTIVE_SNAPSHOTS_WITH_REVISIONS',standard:'ACCEPTED_GOOD_PRODUCED_WIB'})
   assert.deepEqual(result.report,financialReport)
   for(const key of ['po_options','contractors','selected_contractor','captured_at'])assert.deepEqual(result[key],row.actual[key])
   if(prior)assert.deepEqual(result,prior)
   reads++;results.push({case_id:id,read_index:index,status:'PASS',report_status:result.report?.status??null})
  }catch(error){newErrors.push({case_id:id,read_index:index,type:error.name,message:error.message})}
 }
}
const report={status:newErrors.length?'INCOMPLETE':'PASS',classification:'EXACT_RETAINED_NATIVE_RESPONSES_CLIENT_CONTRACT_SUCCESSOR',
 source_parent:head,source_path:source,before_sha256:hash(old),after_sha256:hash(current),original_bytes:raw.length,original_sha256:hash(raw),
 old_parser_pass:oldPass,old_parser_refusals:oldRefusals,new_parser_pass:reads,original_access_denials:denials,results,new_errors:newErrors,
 all_report_money_quantity_source_fields_exact:newErrors.length===0&&reads===22,successful_old_answers_unchanged:newErrors.length===0&&oldPass===21,
 audit_bigint_IDs_remain_exact_decimal_strings:true,cost_revision_IDs_are_Native_UUID_strings:true,
 additional_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false}
writeFileSync(resolve(outputArg),JSON.stringify(report,null,2)+'\n')
assert.equal(denials,4);assert.equal(oldPass,21)
assert.deepEqual(oldRefusals.map(x=>[x.case_id,x.read_index]),[['S05_NATIVE_LATE_INVOICE_COST_REVISIONS',1]])
assert.equal(reads,22,JSON.stringify(newErrors));assert.equal(newErrors.length,0)
console.log(JSON.stringify({status:report.status,old_parser_pass:oldPass,old_parser_refusals:oldRefusals.length,new_parser_pass:reads,original_access_denials:denials,new_browser_credit:0}))
