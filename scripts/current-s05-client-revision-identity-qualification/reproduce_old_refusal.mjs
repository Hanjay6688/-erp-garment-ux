// Exact retained SQL responses through the unchanged client parser. Browser/Native credit0.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'

const [repoArg,originalArg,outputArg]=process.argv.slice(2)
assert.ok(repoArg&&originalArg&&outputArg,'Usage: node replay_s05_responses.mjs EXACT_S05_REPO ORIGINAL_CASE_JSON OUTPUT_JSON')
const repo=resolve(repoArg),source='src/accessoryStandardReport.ts',head='519d1760a3bad06a346b3d4b3cc0203664615634'
const hash=b=>createHash('sha256').update(b).digest('hex')
const raw=readFileSync(resolve(originalArg)),code=readFileSync(resolve(repo,source))
assert.equal(raw.length,232514)
assert.equal(hash(raw),'7b13beaa9d369398a2e6c3762d9649303e92e6c835aba8b476a5d51842f3d79a')
assert.equal(hash(code),'982988ce7a48c624294bcb22a6663ae8bd842825ecfa74c72b8f1fa697a6f1a1')
assert.deepEqual(code,execFileSync('/usr/bin/git',['-C',repo,'show',head+':'+source]))
const {parseAccessoryReportWorkspace}=await import(pathToFileURL(resolve(repo,source)).href)
const original=JSON.parse(raw),results=[],errors=[]
assert.equal(original.status,'PASS');assert.deepEqual(original.counts,{PASS:10})
let reads=0,denials=0
for(const [id,entry]of Object.entries(original.cases)){
 assert.equal(entry.status,'PASS')
 for(const [index,row]of entry.actual_raw_reads.entries()){
  if(!Object.hasOwn(row,'actual')){assert.equal(row.actual_error.sqlstate,'42501');denials++;continue}
  assert.equal(row.query.length,7)
  const [start,end,contractor,po,q,offset,limit]=row.query
  assert.match(offset,/^\d+$/);assert.match(limit,/^\d+$/)
  const query={period_start:start,period_end:end,contractor_id:contractor,po_id:po,q,offset:Number(offset),limit:Number(limit)}
  try{
   const result=parseAccessoryReportWorkspace(row.actual,query)
   const {definitions,...financialReport}=row.actual.report
   assert.deepEqual(definitions,{actual:'POSTED_ISSUE_PHYSICAL_WIB',comparison:'PERIOD_COHORTS_NOT_PO_WASTE',
    cost:'NATIVE_EFFECTIVE_SNAPSHOTS_WITH_REVISIONS',standard:'ACCEPTED_GOOD_PRODUCED_WIB'})
   assert.deepEqual(result.report,financialReport)
   assert.deepEqual(result.po_options,row.actual.po_options)
   assert.deepEqual(result.contractors,row.actual.contractors)
   assert.deepEqual(result.selected_contractor,row.actual.selected_contractor)
   reads++;results.push({case_id:id,read_index:index,status:'PASS',report_status:result.report?.status??null})
  }catch(error){errors.push({case_id:id,read_index:index,type:error.name,message:error.message})}
 }
}
const report={status:errors.length?'INCOMPLETE':'PASS',classification:'EXACT_RETAINED_NATIVE_RESPONSES_THROUGH_UNCHANGED_CLIENT_PARSER',
 source_head:head,source_path:source,source_sha256:hash(code),original_bytes:raw.length,original_sha256:hash(raw),
 successful_originals:22,parsed_unchanged_responses:reads,original_access_denials:denials,results,errors,
 additional_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false}
writeFileSync(resolve(outputArg),JSON.stringify(report,null,2)+'\n')
assert.equal(denials,4);assert.equal(reads,22,JSON.stringify(errors));assert.equal(errors.length,0)
console.log(JSON.stringify({status:report.status,parsed_unchanged_responses:reads,original_access_denials:denials,new_browser_credit:0}))
