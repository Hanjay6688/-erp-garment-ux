/** Real unchanged pure SQL arithmetic, PGlite 0.3.14; no Native/Auth/money writer proof. */
import {readFile} from 'node:fs/promises'
import {fileURLToPath,pathToFileURL} from 'node:url'
import assert from 'node:assert/strict'
const here=new URL('./',import.meta.url)
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const db=new PGlite()
try{
 await db.exec('create role anon;create role authenticated;create role service_role;')
 for(const file of ['../cp7_customer_credit/kernel/kernel.sql','../cp7_customer_credit/ordinal-wrapper/wrapper.sql','review.sql'])await db.exec(await readFile(new URL(file,here),'utf8'))
 const sha='a'.repeat(64),event=(id,kind,amount,economic_date='2026-10-01',transaction_date=economic_date)=>({id,kind,amount,economic_date,transaction_date,source_sha256:sha})
 const movement=(id,amount,economic_date='2026-10-02',transaction_date=economic_date)=>({id,amount,economic_date,transaction_date,source_sha256:sha})
 const family=(n,amount,credit,consumptions=[])=>({family_id:'family-'+n,first_return_id:'return-'+n,ordinal:String(n),registration_sha256:sha,
  events:[event('return-journal-'+n,'NET','-'+amount,'2026-10-02')],retained_recognition:[movement('part-'+n,credit)],consumptions})
 const input=families=>({contract_version:'ow04.ordinal-input.v1',family_root_sale_id:'sale',base_events:[event('sale-journal','NET','1000.00'),event('payment-journal','FUNDING','1000.00')],families})
 const review=async(b,a)=>(await db.query('select cp7_credit_correction_de.review_vectors_v1($1::jsonb,$2::jsonb)v',[b,a])).rows[0].v
 const modify=(b,amount)=>{const a=structuredClone(b);a.families[0].events[0].amount='-'+amount;return a}
 const tests=[]
 for(const [name,consumers]of [['FREE',[]],['ACTIVE_APPLY',[movement('applied','150.00','2026-10-03')]],['INITIAL_REFUND',[movement('refunded','200.00','2026-10-03')]]]){
  const b=input([family(1,'200.00','200.00',consumers)]),q=await review(b,modify(b,'250.00'))
  assert.equal(q.credit_delta,'50.00');assert.equal(q.requires_undo,false);assert.equal(q.source_authority_proven,false)
  assert.equal(q.after_available,name==='FREE'?'250.00':name==='ACTIVE_APPLY'?'100.00':'50.00');tests.push(name+'_POSITIVE_INCREMENT')
 }
 {
  const b=input([family(1,'200.00','200.00',[movement('used','180.00','2026-10-03')])]),q=await review(b,modify(b,'100.00'))
  assert.equal(q.requires_undo,true);assert.equal(q.credit_delta,'-100.00');tests.push('SHORTFALL_REFUSED')
 }
 {
  const b=input([family(1,'200.00','200.00',[movement('used','180.00','2026-10-03'),movement('named-undo','-180.00','2026-10-04')])]),q=await review(b,modify(b,'250.00'))
  assert.equal(q.requires_undo,false);assert.equal(q.after_available,'250.00');tests.push('NAMED_UNDO_RETAINS_SIGNED_HISTORY')
 }
 {
  const b=input([family(1,'200.00','200.00'),family(2,'100.00','100.00')]),q=await review(b,modify(b,'250.00'))
  assert.equal(q.families.length,2);assert.equal(q.families[0].delta,'50.00');assert.equal(q.families[1].delta,'0.00');tests.push('FAMILY_ORDINAL_RETAINED')
 }
 {
  const b=input([family(1,'200.00','200.00')]),a=modify(b,'250.00');a.families[0].retained_recognition[0].amount='199.99'
  await assert.rejects(()=>review(b,a),/CP7_CREDIT_DE_RETAINED_HISTORY_CHANGED/);tests.push('NO_REWRITE_OF_RETAINED_RECOGNITION')
 }
 {
  const b=input([family(1,'200.00','200.00')]);b.base_events[1].amount='1100.00'
  await assert.rejects(()=>review(b,modify(b,'250.00')),/BASE_OVERFLOW_NONZERO/);tests.push('OVERPAYMENT_AUTO_CREDIT_STAYS_REFUSED')
 }
 console.log(JSON.stringify({status:'PASS',tests,actual_unchanged_SQL_kernel:true,Native_execution:false,Auth_browser:false,financial_writer_tested:false,standins:'supplied closed arithmetic vectors only'},null,2))
}finally{await db.close()}
