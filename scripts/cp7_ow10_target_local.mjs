// Actual private kernel SQL with actual existing validators; no Native proof.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite()
await db.exec('create role cp7_capture nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;')
for(const path of['wip/bootstrap.sql','demand/bootstrap.sql','baseline/target.sql'])await db.exec(await readFile('scripts/cp7-src/'+path,'utf8'))
const before=execFileSync('git',['show','245b59505274ab7df6d15ed5d63080267da42988:scripts/cp7-src/baseline/target.sql'],{encoding:'utf8'})
await db.exec(before.slice(0,before.indexOf('-- Supply here')).replace('cp7_baseline.target(v','cp7_baseline.target_before(v'))
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,2200)})}}
const call=async(v,fn='target')=>(await db.query('select cp7_baseline.'+fn+'($1::jsonb) value',[JSON.stringify(v)])).rows[0].value
const base={contract_version:'cp7.target-input.v1',snapshot_id:'same-snapshot',scope_id:'same-scope',mode:'DAYS',daily_mean:'1',lead_days:'3',review_days:'7',buffer_days:'2',quantile:null,horizon_samples:[],refs:[{kind:'LOCAL_TEST',id:'source',revision:'1'}]}
await test('OW10_LEGACY_DAYS_EXACT_EQUIVALENCE',async()=>{
 let count=0
 for(const daily of['0','0.1','1','7.666666666667','1000000000000'])for(const lead of['0','0.5','3','7.25'])for(const review of['1','7'])for(const buffer of['0','0.1','2']){
  const v={...base,daily_mean:daily,lead_days:lead,review_days:review,buffer_days:buffer}
  assert.deepEqual(await call(v),await call(v,'target_before'));++count
 }
 for(const v of[{...base,lead_days:null},{...base,buffer_days:null},{...base,daily_mean:null},{...base,daily_mean:'invalid',buffer_days:null}]){
  assert.deepEqual(await call(v),await call(v,'target_before'));++count
 }
 return {identical_full_JSON:count}
})
await test('OW10_LEGACY_EMPIRICAL_EXACT_EQUIVALENCE',async()=>{
 for(const quantile of['0.5','0.90','0.95','0.99','1']){
  const v={...base,mode:'STATISTICAL',daily_mean:null,buffer_days:null,quantile,horizon_samples:['1','30','4','100','20']}
  assert.deepEqual(await call(v),await call(v,'target_before'))
 }
 return {identical_full_JSON:5}
})
await test('OW10_INDEPENDENT_RATIONAL_AND_DECIMAL_ORACLE',async()=>{
 const rows=JSON.parse(execFileSync('python',['scripts/cp7_ow10_target_oracle.py'],{encoding:'utf8'}))
 for(const {input,expected}of rows){const got=await call(input);assert.equal(got.status,'SCENARIO');assert.equal(got.reorder_point_pcs,expected.reorder_point_pcs,JSON.stringify(input));assert.equal(got.target_pcs,expected.target_pcs,JSON.stringify(input))}
 return{independent_cases:rows.length,exact_repeating_mean_whole_PCS:true,separate_reorder_and_target:true}
})
await test('OW10_UNKNOWN_AND_DOUBLE_SAFETY_REFUSAL',async()=>{
 const v=JSON.parse(execFileSync('python',['scripts/cp7_ow10_target_oracle.py'],{encoding:'utf8'}))[1].input
 for(const delta of[{daily_sd:null},{service_level:null},{counted_days:'13'},{lead_days:null}]){
  const got=await call({...v,...delta});assert.equal(got.status,'UNKNOWN');assert.equal(got.reorder_point_pcs,null);assert.equal(got.target_pcs,null)
 }
 for(const delta of[{buffer_days:'2'},{service_level:'0.96'},{daily_sd:'NaN'},{extra:'smuggle'}])await assert.rejects(()=>call({...v,...delta}))
 return{unknown_not_zero:4,invalid_or_double_buffer_refused:4}
})
const report={classification:'LOCAL_ACTUAL_KERNEL_SQL_NOT_NATIVE_OR_HTTP',status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',
 source_sha256:createHash('sha256').update(await readFile('scripts/cp7-src/baseline/target.sql')).digest('hex'),cases:results,OW10_complete:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-kernel.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
