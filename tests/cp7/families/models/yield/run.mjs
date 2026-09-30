import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { openYieldRuntime, sourceFile } from './runtime.mjs'
import { context, demoHistory, input, request } from './history.mjs'

const db=await openYieldRuntime(), cases=[]
const clone=value=>structuredClone(value)
const test=async(id,run)=>{try {await run();cases.push({id,status:'PASS'})} catch(error) {cases.push({id,status:'FAIL',reason:error.message})}}
const ready=async(req,expected)=>{const result=await db.review(req);assert.equal(result.status,'READY');assert.equal(result.interval.lower,expected[0]);assert.equal(result.interval.upper,expected[1]);return result}
try {
 await test('width-blank-actual-cohort',async()=>{const r=await ready(request(),['80','120']);assert.equal(r.peers.length,72);assert.equal(r.interval.basis,'WITHOUT_WIDTH')})
 await test('width-known-only-exact',async()=>{const r=await ready(request(input('small','150')),['90','110']);assert.equal(r.peers.length,24)})
 await test('width-narrow-exact',()=>ready(request(input('small','140','100','94')),['84','104']))
 await test('mixed-multiplicity-changes-cohort',()=>ready(request(input('unique',null,'100','94')),['74','114']))
 await test('jumbo-separate',()=>ready(request(input('jumbo',null,'100','80')),['60','100']))
 await test('short-length-has-own-history',()=>ready(request(input('small',null,'80','80')),['64','96']))
 await test('no-linear-length-extrapolation',async()=>assert.equal((await db.review(request(input('small',null,'90')))).status,'UNSEEN_COMBINATION'))
 await test('unseen-all30-abstains',async()=>assert.equal((await db.review(request(input('all30')))).status,'UNSEEN_COMBINATION'))
 await test('unseen-width-abstains',async()=>assert.equal((await db.review(request(input('small','147')))).status,'UNSEEN_COMBINATION'))
 await test('marker-null-not-imputed',async()=>assert.equal((await db.review(request({...input(),markerRevision:null}))).status,'UNSEEN_COMBINATION'))
 await test('pcs-missing-not-zero',async()=>assert.equal((await db.review(request({...input(),outputComplete:false,observedCutPcs:null}))).status,'INCOMPLETE'))
 await test('not-enough-peers',async()=>assert.equal((await db.review(request(input(),demoHistory().slice(0,19)))).status,'INSUFFICIENT'))
 await test('slots-order-not-multiplicity',()=>ready(request({...input(),sizeSlots:[...input().sizeSlots].reverse()}),['80','120']))
 await test('numeric-equivalent-length-width',()=>ready(request(input('small','150.0','100.00')),['90','110']))
 for(const [actual,assessment] of [['79','LOW'],['80','NORMAL'],['120','NORMAL'],['121','HIGH'],['0','LOW']]) await test(`classification-${actual}`,async()=>assert.equal((await db.review(request(input('small',null,'100',actual)))).assessment,assessment))
 await test('actual-not-a-model-feature',async()=>{const a=await ready(request(),['80','120']),b=await ready(request(input('small',null,'100','999999')),['80','120']);assert.deepEqual(a.peers,b.peers)})
 await test('duplicate-source-counts-once',async()=>{const h=demoHistory();h.push(clone(h[0]));assert.equal((await ready(request(input(),h),['80','120'])).peers.length,72)})
 await test('conflicting-same-revision-rejected',async()=>{const h=demoHistory(),r=clone(h[0]);r.input.observedCutPcs='999';h.push(r);await assert.rejects(db.review(request(input(),h)),/YIELD_CONFLICTING_REVISION/)})
 await test('latest-revision-wins',async()=>{const h=demoHistory().slice(0,24);for(const row of clone(h)){row.revisionSequence='2';row.sourceRevision='fixture-r2';row.input.observedCutPcs='222';h.push(row)}const r=await ready(request(input(),h),['222','222']);assert.equal(r.peers.length,24);assert.ok(r.peers.every(p=>p.sourceRevision==='fixture-r2'))})
 await test('void-latest-does-not-resurrect',async()=>{const h=demoHistory().slice(0,24);for(const row of clone(h)){row.revisionSequence='2';row.state='VOID';h.push(row)}assert.equal((await db.review(request(input(),h))).status,'UNSEEN_COMBINATION')})
 await test('late-revision-as-known-cutoff',async()=>{const h=demoHistory().slice(0,24);for(const row of clone(h)){row.revisionSequence='2';row.knownOn='2026-10-01';row.input.observedCutPcs='222';h.push(row)}await ready(request(input(),h),['80','120'])})
 await test('current-roll-excluded',async()=>{const h=demoHistory(),r=clone(h[0]);r.input={...input(),observedCutPcs:'99999'};h.push(r);assert.equal((await ready(request(input(),h),['80','120'])).peers.length,72)})
 await test('cross-scope-excluded',async()=>{const h=demoHistory('other-scope');assert.equal((await db.review(request(input(),h))).status,'UNSEEN_COMBINATION')})
 await test('future-and-pre-window-excluded',async()=>{const h=demoHistory().slice(0,24);for(const row of h){row.occurredOn='2026-02-01'}assert.equal((await db.review(request(input(),h))).status,'UNSEEN_COMBINATION');for(const row of h){row.occurredOn='2026-10-01';row.knownOn='2026-10-01'}assert.equal((await db.review(request(input(),h))).status,'UNSEEN_COMBINATION')})
 await test('incomplete-history-excluded',async()=>{const h=demoHistory().slice(0,24);for(const row of h){row.input.outputComplete=false;row.input.observedCutPcs=null}assert.equal((await db.review(request(input(),h))).status,'UNSEEN_COMBINATION')})
 for(const field of ['materialId','patternRevision']) await test(`${field}-separate`,async()=>assert.equal((await db.review(request({...input(),[field]:'other'}))).status,'UNSEEN_COMBINATION'))
 await test('mill-separate',async()=>assert.equal((await db.review(request({...input(),materialFamily:{...input().materialFamily,millId:'other'}}))).status,'UNSEEN_COMBINATION'))
 for(const value of [0,'NaN','-1','1e2','01',null]) await test(`bad-length-${String(value)}`,async()=>await assert.rejects(db.review(request({...input(),consumed:{value,unit:'M'}}))))
 await test('bad-policy-rejected',async()=>{const req=request();req.policy={...req.policy,lowerQuantile:'0.9',upperQuantile:'0.1'};await assert.rejects(db.review(req),/YIELD_POLICY/)})
 await test('bad-future-date-rejected',async()=>{const req=request();req.history[0].knownOn='2026-02-01';await assert.rejects(db.review(req),/YIELD_HISTORY_DATE/)})
 await test('null-history-state-rejected',async()=>{const req=request();req.history[0].state=null;await assert.rejects(db.review(req),/YIELD_HISTORY_REVISION/)})
 await test('history-limit-rejected',async()=>{const req=request();req.history=Array.from({length:1001},()=>clone(req.history[0]));await assert.rejects(db.review(req),/YIELD_REQUEST/)})
 await test('exact-large-pcs',async()=>{const h=demoHistory().slice(0,24);for(const row of h)row.input.observedCutPcs='9007199254740993';await ready(request(input(),h),['9007199254740993','9007199254740993'])})
 for(const role of ['anon','authenticated','service_role']) await test(`private-acl-${role}`,async()=>{await db.execute(`set role ${role}`);try{await assert.rejects(db.review(request()),/permission denied/)}finally{await db.execute('reset role')}})
 await test('invoker-empty-search-path-owner',async()=>{const rows=await db.query("select p.prosecdef,p.proconfig,pg_get_userbyid(p.proowner) as owner from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_yield'");assert.equal(rows.length,6);assert.ok(rows.every(r=>!r.prosecdef&&r.owner==='cp7_capture'&&r.proconfig.includes('search_path=""')))})
 await test('ledger-unchanged',async()=>assert.equal((await db.query('select amount::text as amount from public.yield_ledger_canary'))[0].amount,'12345.67'))
} finally {await db.close()}
const hash=file=>createHash('sha256').update(readFileSync(file)).digest('hex')
const receipt={contract:'f04.yield-kernel-proof.v1',runtime:db.runtime,version:db.version,source_sha256:Object.fromEntries([sourceFile,...['runtime.mjs','history.mjs','run.mjs'].map(f=>`tests/cp7/families/models/yield/${f}`)].map(f=>[f,hash(f)])),passed:cases.filter(c=>c.status==='PASS').length,failures:cases.filter(c=>c.status!=='PASS'),cases,cleanup:'CLOSED_DISPOSABLE_RUNTIME'}
if(process.env.F04_YIELD_RECEIPT_PATH)writeFileSync(process.env.F04_YIELD_RECEIPT_PATH,JSON.stringify(receipt,null,2)+'\n')
console.log(JSON.stringify(receipt));process.exitCode=receipt.failures.length?1:0
