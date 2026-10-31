// Reproduce the captured timestamp error against the real product parser/prompt.
// Offline controls only: no browser, Auth, DB, HTTP or new qualification credit.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import test from 'node:test'
import {assertManualPrompt,HOSTILE_QUESTION,promptSections} from './staged_ai_cases.mjs'
const HERE=dirname(fileURLToPath(import.meta.url)),ROOT=resolve(HERE,'../..')
const require=createRequire(resolve(process.env.SKU27_NODE_ROOT||ROOT,'package.json'))
const {buildSync}=require('esbuild')
function product(path){
 const code=buildSync({entryPoints:[resolve(ROOT,path)],bundle:true,write:false,platform:'node',format:'cjs',target:'es2022',logLevel:'silent'}).outputFiles[0].text
 const module={exports:{}};new Function('require','module','exports',code)(require,module,module.exports);return module.exports
}
const actual=product('src/nativeStagedAi.ts'),f=product('tests/fixtures/nativeStagedAi.ts')
const original=readFileSync(resolve(HERE,'retained_e925/staged_ai_cases.mjs.txt'),'utf8')
const start=original.indexOf('export function assertManualPrompt('),end=original.indexOf('\nexport function assertExactState(',start)
assert.ok(start>=0&&end>start)
const old=new Function('assert','promptSections','HOSTILE_QUESTION',
 'const instant=v=>new Date(v).toISOString(),hash=()=>"offline",promptRow=({ord,...r})=>r;\n'+original.slice(start,end).replace('export function','function')+'\nreturn assertManualPrompt;')(assert,promptSections,HOSTILE_QUESTION)
const failure=JSON.parse(readFileSync(resolve(HERE,'FIRST_E925_TIMESTAMP_FAILURE.json')))
const stamps=[...failure.captured_timestamps,'2026-10-31T03:08:16.000001+07:00','2026-10-30T20:08:16.999999Z']
function wire(stamp,checked){
 const value=f.brief([f.keys[2]]);value.freshness=structuredClone(value.freshness)
 const freshness=value.freshness
 freshness.changes_since.find(row=>row.rows>0).last_recorded_at=stamp
 if(checked){
  freshness.last_full_check={source_state:'UNCHANGED',checked_at:stamp,boundary:'SNAPSHOT',changes_after_check:0}
  freshness.changes_since.forEach(row=>{row.rows_after_check=0})
  freshness.freshness_state='VERIFIED_SAME';freshness.same_as_of=stamp
 }
 return value
}
test('captured microseconds and offsets survive actual product parser, prompt and new oracle',()=>{
 for(const stamp of stamps)for(const checked of [false,true]){
  const value=wire(stamp,checked),brief=actual.parseStagedAiBrief(value,f.actor,f.set,f.query,[f.keys[2]])
  const prompt=actual.stagedAiPrompt(brief,HOSTILE_QUESTION,null)
  assert.throws(()=>old(prompt,value,HOSTILE_QUESTION,[f.keys[2]]),assert.AssertionError)
  assertManualPrompt(prompt,value,HOSTILE_QUESTION,[f.keys[2]])
  const {data}=promptSections(prompt)
  assert.equal(data.changes_since_analysis[0].last_recorded_at,stamp)
  if(checked)assert.equal(data.last_full_check.checkedAt,stamp)
 }
})
test('even one lost microsecond is refused in either copied timestamp',()=>{
 const value=wire('2026-10-30T20:08:16.832213+00:00',true)
 const prompt=actual.stagedAiPrompt(actual.parseStagedAiBrief(value,f.actor,f.set,f.query,[f.keys[2]]),HOSTILE_QUESTION,null)
 for(const key of ['changes_since_analysis','last_full_check']){
  const {data}=promptSections(prompt),changed=structuredClone(data)
  if(key==='last_full_check')changed.last_full_check.checkedAt='2026-10-30T20:08:16.832212+00:00'
  else changed.changes_since_analysis[0].last_recorded_at='2026-10-30T20:08:16.832212+00:00'
  const encode=x=>JSON.stringify(x).replaceAll('<','\\u003c').replaceAll('>','\\u003e')
  const wrong=prompt.replace(encode(data),encode(changed));assert.notEqual(wrong,prompt)
  assert.throws(()=>assertManualPrompt(wrong,value,HOSTILE_QUESTION,[f.keys[2]]),assert.AssertionError)
 }
})
