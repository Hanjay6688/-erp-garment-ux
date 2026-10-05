import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {dirname} from 'node:path'
import {openRuntime,jsonArg,digest} from './runtime.mjs'

// A byte-pinned prior complete SQL function is a separate execution oracle.
// Literal outcomes additionally guard its opening/intraday/WIB semantics.
// This private compiler fixture grants no Native business/Auth/browser credit.
const previous=readFileSync('tests/cp7/fixtures/history-availability-before-e206.sql','utf8')
assert.equal(digest(previous),'82b49380ecb8f0ae61415414fa0cc4fce08718012b795cd19c2c22754fd50c95')
const source=readFileSync('scripts/cp7-src/planning/history.sql','utf8')
const candidate=source.slice(0,source.indexOf('create function cp7_planning.history_build'))
const root='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222'
const product=(id=root,established='2025-01-01T00:00:00Z')=>({id,root_id:id,size_id:id,established_at:established})
let serial=0
const movement=(qty,at,options={})=>({id:String(++serial).padStart(8,'0'),root_id:root,qty_signed:String(qty),physical_at:at,book_order:String(serial),quality_grade:'GRADE_A',...options})
const context=(stock=[],products=[product()])=>({captured_at:'2026-10-05T07:00:00.000001Z',facts:{products,stock}})
const query={from_date:'2026-10-01',through_date:'2026-10-03'}
const opening=()=>movement('10','2026-09-30T16:59:59.999999Z')
const cases=[
 ['empty_scope',context([],[]),[]],
 ['no_stock',context(),['STOCKOUT','STOCKOUT','STOCKOUT']],
 ['strict_before_WIB_midnight',context([opening()]),['AVAILABLE','AVAILABLE','AVAILABLE']],
 ['incoming_at_WIB_midnight',context([movement('10','2026-09-30T17:00:00Z')]),['STOCKOUT','AVAILABLE','AVAILABLE']],
 ['zero_then_replenished_within_day',context([opening(),movement('-10','2026-10-01T00:00:00Z'),movement('10','2026-10-01T00:00:01Z')]),['STOCKOUT','AVAILABLE','AVAILABLE']],
 ['negative_intraday_then_replenished',context([opening(),movement('-11','2026-10-01T00:00:00Z'),movement('11','2026-10-01T00:00:01Z')]),['UNKNOWN','AVAILABLE','AVAILABLE']],
 ['negative_opening',context([movement('-1','2026-09-30T16:00:00Z')]),['UNKNOWN','UNKNOWN','UNKNOWN']],
 ['established_one_microsecond_after_open',context([opening()],[product(root,'2026-09-30T17:00:00.000001Z')]),['UNKNOWN','AVAILABLE','AVAILABLE']],
 ['same_clock_numeric_book_order',context([opening(),movement('-11','2026-10-01T00:00:00Z',{book_order:'2'}),movement('11','2026-10-01T00:00:00Z',{book_order:'10'})]),['UNKNOWN','AVAILABLE','AVAILABLE']],
 ['same_clock_ID_tie_break',context([opening(),movement('-10','2026-10-01T00:00:00Z',{book_order:'9',id:'A'}),movement('10','2026-10-01T00:00:00Z',{book_order:'9',id:'B'})]),['STOCKOUT','AVAILABLE','AVAILABLE']],
 ['sellable_grade_B_and_non_sellable_excluded',context([movement('10','2026-09-30T16:00:00Z',{quality_grade:'GRADE_B'}),movement('-99','2026-10-01T00:00:00Z',{quality_grade:'BS'})]),['AVAILABLE','AVAILABLE','AVAILABLE']],
 ['precise_tiny_positive_opening',context([movement('0.000000000001','2026-09-30T16:00:00Z')]),['AVAILABLE','AVAILABLE','AVAILABLE']],
 ['last_day_upper_boundary_excluded',context([opening(),movement('-11','2026-10-03T17:00:00Z')]),['AVAILABLE','AVAILABLE','AVAILABLE']],
 ['one_root_never_uses_another_stock',context([opening()],[product(),product(other)]),['AVAILABLE','AVAILABLE','AVAILABLE','STOCKOUT','STOCKOUT','STOCKOUT']],
]
const db=await openRuntime(),results=[]
try{
 await db.execute('create schema cp7_planning;'+previous.replace('cp7_planning.history_availability(','cp7_planning.history_availability_previous(')+candidate)
 const boundary=async()=> (await db.query("select md5(jsonb_agg(to_jsonb(x)order by id)::text)as hash from public.f04_ledger_canary x"))[0].hash
 const before=await boundary()
 const compare=async(name,c,q,expected)=>{
  const args=jsonArg(c)+','+jsonArg(q)
  const old=(await db.query('select cp7_planning.history_availability_previous('+args+')as result'))[0].result
  const current=(await db.query('select cp7_planning.history_availability('+args+')as result'))[0].result
  assert.deepEqual(current,old,name+' complete prior-SQL parity')
  if(expected)assert.deepEqual(current.map(x=>x.state),expected,name+' literal business oracle')
  results.push({id:name,status:'PASS',rows:current.length,complete_prior_SQL_parity:true,literal_oracle:!!expected})
 }
 for(const[name,c,expected]of cases)await compare(name,c,query,expected)
 // Deterministic disordered multi-root events exercise numeric order, offset
 // representations, WIB boundaries, positive/zero/negative balances and days.
 let random=23456789;const next=()=>{random=(Math.imul(random,1664525)+1013904223)>>>0;return random}
 for(let i=0;i<12;i++){
  const roots=Array.from({length:7},(_,j)=>product('ROOT-'+j,j%3===0?'2026-09-30T17:00:00.000001Z':'2025-01-01T00:00:00Z'))
  const stock=Array.from({length:90},(_,j)=>movement(String((next()%31)-15)+'.000001',new Date(Date.parse('2026-09-29T17:00:00Z')+(next()%432000)*1000).toISOString(),{root_id:'ROOT-'+next()%7,book_order:String(next()%20),quality_grade:next()%5===0?'BS':j%2?'GRADE_A':'GRADE_B'})).reverse()
  await compare('multi_root_ordered_prefix_'+i,context(stock,roots),query)
 }
 for(const timezone of['Asia/Jakarta','America/Los_Angeles']){
  await db.execute("set timezone='"+timezone+"'")
  await compare('observing_timezone_'+timezone,context([opening(),movement('-11','2026-10-01T07:00:00+07:00')]),query,['UNKNOWN','UNKNOWN','UNKNOWN'])
 }
 assert.equal(await boundary(),before)
 const receipt={contract:'cp7.history-availability-full-SQL-parity.v1',status:'PASS',runtime:db.flavor,version:db.version,previous_source_sha256:digest(previous),candidate_source_sha256:digest(candidate),cases:results,passed:results.length,operational_boundary_unchanged:true,Native_business_case_credit:0,Auth_HTTP_credit:0,browser_credit:0,full_P19_acceptance:false,source_caps_changed:false,statement_timeouts_changed:false,cleanup:'CLOSED_DISPOSABLE_RUNTIME'}
 if(process.env.F04_RECEIPT_PATH){mkdirSync(dirname(process.env.F04_RECEIPT_PATH),{recursive:true});writeFileSync(process.env.F04_RECEIPT_PATH,JSON.stringify(receipt,null,2)+'\n')}
 console.log(JSON.stringify(receipt))
}finally{await db.close()}
