// Binding controls on PGlite with an explicitly controlled compiler/source.
// These controls grant no Native, arithmetic, factory, HTTP or access credit.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8')
const block=(s,n)=>{const m=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,n);return m[0]}
const value=async(s,args=[])=>(await db.query(s,args)).rows[0]?.v
const j=JSON.stringify,producer='d'.repeat(64),cases=[]
const query={from_date:'2026-10-01',through_date:'2026-10-02',group_mode:'AS_SOLD'}
const root='11111111-1111-4111-8111-111111111111',size='22222222-2222-4222-8222-222222222222'
const key=root+':'+size
const raw={contract_version:'cp7.native-demand-facts.v1',scope:'GLOBAL_CURRENT_PHYSICAL_ROOTS',status:'COMPLETE',
 captured_at:'2026-10-25T05:06:07.123456Z',stock_raw_omitted:false,stock_rows_at_least:0,
 facts:{products:[{id:root,root_id:root,size_id:size,commercial:[]}],stock:[],sales:[],sale_journals:[],returns:[],return_journals:[]},
 profiles:[],production_sources:{scope:'EXPLICIT_SYNTHETIC_CONTROL',facts:{}},sentinel:'all source fields retained'}
const stock={contract_version:'cp7.native-stock-row-digest.v2',encoding:'POSTGRES17_RECORD_SEND_TEXT_AS_UTF8_BYTEA_V1',
 layout_sha256:'9fa5d22b53d337a6472898a5eec99ae7b221aea93313d693588e69cc6e83f32a',
 scope:'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS',captured_at:raw.captured_at,row_count:'0',rows_sha256:'b'.repeat(64),
 raw_rows_truncated:false,raw_rows_materialized_as_JSON_array:false,raw_native_capture_status_overridden:false,apply_enabled:false,production_go:false}
const inputs={contract_version:'cp7.reorder-native-inputs.v1',captured_at:raw.captured_at,query,products:raw.facts.products,
 source_hash:'a'.repeat(64),history_hash:'c'.repeat(64),history:[{target_key:key}],current_stock:[{target_key:key}],targets:[{target_key:key}]}
const compiled={contract_version:'cp7.bounded-history-inputs.v1',coverage:'COMPLETE',captured_at:raw.captured_at,query,
 raw_native_capture_status:'COMPLETE',raw_native_status_overridden:false,apply_enabled:false,production_go:false,inputs}
const call=async(name,args)=>value('select cp7_frozen_analysis_v2.'+name+'('+args.map((_,i)=>'$'+(i+1)+(name==='work_fingerprint'||i<4?'::jsonb':i===4?'::text':'::integer')).join(',')+')v',args.map((x,i)=>x===null?null:name==='work_fingerprint'||i<4?j(x):x))
const seal=async(c=raw,q=query,s=stock,sum=null,p=producer,cap=5000)=>call('seal',[c,q,s,sum,p,cap])
const verify=async(c,q=query)=>value('select cp7_frozen_analysis_v2.verify_capsule($1::jsonb,$2::jsonb,5000)v',[j(c),j(q)])
const prepare=async(c,q=query)=>value('select cp7_frozen_analysis_v2.prepare($1::jsonb,$2::jsonb,5000)v',[j(c),j(q)])
async function test(id,fn){await fn();cases.push({id,status:'PASS'})}
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create schema extensions;create schema cp7_analysis_stage;create schema cp7_planning;create schema cp7_bounded_analysis_stage;create schema cp7_history_bounded;')
 await db.exec("create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)where $2='sha256'$$")
 for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql'])await db.exec(await read(p))
 await db.exec(block(await read('scripts/cp7-src/planning/analysis-stages.sql'),'cp7_analysis_stage.bounds'))
 await db.exec(block(await read('scripts/cp7-src/planning/bootstrap.sql'),'cp7_planning.utc'))
 await db.exec(block(await read('scripts/cp7_model_target_consumer_v2_stage/hooks.sql'),'cp7_bounded_analysis_stage.native_work_fingerprint'))
 await db.exec("create function cp7_bounded_analysis_stage.producer_hash()returns text language sql stable as $$select repeat('d',64)$$")
 await db.exec(`create function cp7_history_bounded.compile(c jsonb,q jsonb,s jsonb,n integer)returns jsonb language plpgsql immutable as $$begin
  if current_setting('frozen_control.compiler_forbidden',true)='true'then raise exception 'CONTROLLED_COMPILER_FORBIDDEN';end if;
  if c is distinct from current_setting('frozen_control.expected_base')::jsonb or q is distinct from current_setting('frozen_control.expected_query')::jsonb
   or s is distinct from nullif(current_setting('frozen_control.expected_summary')::jsonb,'null'::jsonb)or n<>5000 then raise exception 'CONTROLLED_COMPILER_ARGUMENT_MISMATCH';end if;
  return current_setting('frozen_control.compiled')::jsonb;end$$;`)
 await db.exec(await read('scripts/cp7_frozen_analysis_v2/capsule.sql'))
 const setting=async(k,v)=>db.query('select set_config($1,$2,false)',['frozen_control.'+k,typeof v==='string'?v:j(v)])
 await setting('expected_base',raw);await setting('expected_query',query);await setting('expected_summary',null);await setting('compiled',compiled)
 let capsule
 await test('CAPTURE_SEALS_WITHOUT_COMPILING_OR_OVERRIDING_RAW_STATUS',async()=>{
  await setting('compiler_forbidden','true');capsule=await seal();assert.equal(capsule.bounded_input_coverage,'PENDING');assert.equal(capsule.bounded_history_inputs,null)
  assert.equal(capsule.status,'COMPLETE');assert.deepEqual(await verify(capsule),raw)
  assert.deepEqual(await value('select cp7_frozen_analysis_v2.base($1::jsonb)v',[j(capsule)]),raw)
 })
 await test('PURE_PREPARE_PASSES_EXACT_FROZEN_ARGUMENTS_NO_REFERENCE_MUTATION',async()=>{
  await setting('compiler_forbidden','false');const saved=j(capsule);assert.deepEqual(await prepare(capsule),compiled);assert.equal(j(capsule),saved)
  // Any accidental live capture/summary call now raises instead of succeeding.
  for(const [sig,returns]of[['cp7_bounded_analysis_stage.analysis_source(integer,integer)','jsonb'],['cp7_reorder_inputs.stock_summary(jsonb,timestamptz,jsonb)','jsonb']]){
   await db.exec('create schema if not exists '+sig.split('.')[0]);await db.exec('create function '+sig+'returns '+returns+" language plpgsql stable as $$begin raise exception 'LIVE_READ_FORBIDDEN';end$$;")
  }
  assert.deepEqual(await prepare(capsule),compiled)
 })
 await test('EVERY_FROZEN_CAPSULE_OPERAND_AND_MARKER_TAMPER_REFUSED',async()=>{
  const mutations=[c=>{c.captured_at='2026-10-25T05:06:07.123457Z'},c=>{c.sentinel='changed'},c=>{c.facts.products[0].size_id=root},
   c=>{c.facts.products[0].product_name='changed'},c=>{c.bounded_query.group_mode='RESTATED'},c=>{c.bounded_stock_reference.rows_sha256='e'.repeat(64)},
   c=>{c.bounded_stock_reference.encoding='OTHER'},c=>{c.bounded_producer_hash='e'.repeat(64)},c=>{c.bounded_capsule_hash='e'.repeat(64)},
   c=>{c.bounded_request_contract='cp7.bounded-analysis-request.v1'},c=>{c.bounded_reference_contract='cp7.bounded-analysis-reference.v1'},
   c=>{c.bounded_capture_state='REFERENCE_ONLY'},c=>{c.bounded_history_inputs=compiled},c=>{c.bounded_input_coverage='COMPLETE'},
   c=>{c.bounded_frozen_stock_summary={}},c=>{c.unknown_new_source_field=true}]
  for(const mutate of mutations){const c=structuredClone(capsule);mutate(c);await assert.rejects(()=>verify(c))}
  await assert.rejects(()=>verify(capsule,{...query,group_mode:'RESTATED'}));assert.equal(mutations.length,16)
 })
 await test('WORK_IDENTITY_STABLE_ACROSS_CLOCK_QUERY_AND_PENDING_DERIVATION',async()=>{
  const fp=c=>call('work_fingerprint',[c]);const first=await fp(capsule)
  const changed=structuredClone(capsule);changed.captured_at='2026-10-25T06:07:08.123456Z';changed.bounded_stock_reference.captured_at=changed.captured_at
  changed.bounded_query.group_mode='RESTATED';changed.bounded_history_inputs=compiled;changed.bounded_input_coverage='COMPLETE'
  assert.equal(await fp(changed),first)
  for(const mutate of[c=>{c.bounded_stock_reference.rows_sha256='e'.repeat(64)},c=>{c.bounded_stock_reference.row_count='1'},c=>{c.bounded_producer_hash='e'.repeat(64)},c=>{c.facts.products[0].size_id=root}]){
   const c=structuredClone(capsule);mutate(c);assert.notEqual(await fp(c),first)
  }
  const old={...capsule,bounded_request_contract:'cp7.bounded-analysis-request.v1'};await assert.rejects(()=>fp(old),/REFERENCE_SHAPE/)
 })
 await test('EARLY_ADMISSION_RETAINS_NON_STOCK_AND_QUERY_REFUSALS',async()=>{
  const mutations=[c=>{c.facts.products.push(c.facts.products[0])},c=>{c.facts.products[0].commercial=[{},{}]},
   c=>{c.facts.sales=[{sold_commercial:[{},{}]}]},c=>{c.facts.sales=[{sale_id:root,status:'POSTED',sold_commercial:[]}]},
   c=>{c.facts.sales=Array(50001).fill({})},c=>{c.status='UNKNOWN'},c=>{c.facts.extra=[]}]
  for(const mutate of mutations){const c=structuredClone(raw);mutate(c);await assert.rejects(()=>seal(c))}
  for(const q of[{...query,through_date:'2026-10-25'},{...query,through_date:'2026-09-30'},{...query,group_mode:'OTHER'},{...query,extra:1}])await assert.rejects(()=>seal(raw,q))
  const c=structuredClone(raw);c.bounded_query=query;await assert.rejects(()=>seal(c),/BASE_OR_PRODUCER/)
 })
 await test('OMITTED_STOCK_COUNTS_EXACT_RAW_STATUS_PENDING_AND_SUMMARY_TAMPER',async()=>{
  const c={...structuredClone(raw),status:'INCOMPLETE',stock_raw_omitted:true,stock_rows_at_least:50001}
  const s={...stock,row_count:'50001'},sum={contract_version:'cp7.reorder-stock-summary.v1',captured_at:raw.captured_at,query,
   products:1,raw_rows_read:50001,availability:[],current_stock:[],data_hash:'8'.repeat(64),history_data_hash:'9'.repeat(64),
   raw_rows_truncated:false,Native_capture_status_overridden:false}
  const cap=await seal(c,query,s,sum);assert.equal(cap.status,'INCOMPLETE');assert.equal(cap.bounded_input_coverage,'PENDING');assert.deepEqual(await verify(cap),c)
  const other=structuredClone(cap);other.bounded_frozen_stock_summary.current_stock=[{changed:true}];await assert.rejects(()=>verify(other),/CAPSULE_BINDING/)
  await assert.rejects(()=>seal(c,query,s,{...sum,raw_rows_read:50002}),/FULL_STOCK_COUNT/)
  await assert.rejects(()=>seal(c,query,s,null),/SNAPSHOT_MISMATCH/)
  await assert.rejects(()=>seal(c,query,{...s,raw_rows_truncated:true},sum),/STOCK_REFERENCE/)
  await assert.rejects(()=>seal(c,query,{...s,row_count:'9223372036854775808'},sum),/STOCK_REFERENCE/)
 })
 await test('COMPILED_BINDINGS_AND_ALL_TARGET_COLLECTIONS_FAIL_CLOSED',async()=>{
  for(const mutate of[r=>{r.query.group_mode='RESTATED'},r=>{r.raw_native_capture_status='INCOMPLETE'},r=>{r.inputs.products=[]},
   r=>{r.inputs.history=[]},r=>{r.inputs.targets=[{target_key:'OTHER'}]},r=>{r.inputs.current_stock.push(r.inputs.current_stock[0])},
   r=>{r.coverage='PENDING'},r=>{r.raw_native_status_overridden=true}]){
   const r=structuredClone(compiled);mutate(r);await setting('compiled',r);await assert.rejects(()=>prepare(capsule),/INPUT_(BINDING|TARGETS)/)
  }
  await setting('compiled',compiled);assert.deepEqual(await prepare(capsule),compiled)
 })
 const text=await read('scripts/cp7_frozen_analysis_v2/capsule.sql')
 const report={contract:'cp7.frozen-analysis-capsule-local-controls.v2',status:'PASS',cases,counts:{PASS:cases.length},
  sql_sha256:createHash('sha256').update(text).digest('hex'),server_version:await value('select version()v'),
  controlled_compiler_and_capture:true,actual_compiler_arithmetic_parity:false,actual_Native:false,
  actual_Auth_HTTP_credit:false,full_factory_qualified:false,request_or_unit_integrated:false,production_go:false}
 if(process.env.CP7_FROZEN_LOCAL_REPORT)await writeFile(process.env.CP7_FROZEN_LOCAL_REPORT,j(report)+'\n')
 console.log(j(report))
}finally{await db.close()}
