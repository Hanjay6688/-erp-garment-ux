// Actual two SQL functions plus the existing scoped identity. Synthetic facts
// and complete row digests; no Native capture, Auth, target caller or SLA credit.
import assert from 'node:assert/strict'
import {randomUUID,createHash} from 'node:crypto'
import {readFile,writeFile} from 'node:fs/promises'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),cases=[],root=randomUUID(),other=randomUUID(),size=randomUUID(),target=root+':'+size,producer='1'.repeat(64),at='2026-10-24T12:00:00.000000Z'
await db.exec(`create role cp7_capture;create role anon;create role authenticated;create role service_role;
create schema cp7_demand;create schema cp7_wip;create schema cp7_model_history_scope;create schema extensions;
create function cp7_demand.instant(x jsonb)returns timestamptz language plpgsql immutable as $$declare t timestamptz;begin t:=(x#>>'{}')::timestamptz;if t is null or not isfinite(t)then raise exception 'BAD_CLOCK';end if;return t;end$$;
create function cp7_wip.fields(x jsonb,k text[])returns void language plpgsql immutable as $$begin if jsonb_typeof(x)is distinct from'object'or(select array_agg(key order by key)from jsonb_object_keys(x)key)is distinct from(select array_agg(v order by v)from unnest(k)v)then raise exception 'BAD_FIELDS';end if;end$$;
create function extensions.digest(x bytea,algorithm text)returns bytea language sql immutable as $$select pg_catalog.sha256(x)$$;`)
const source=await readFile('scripts/cp7_model_target_binding/binding.sql','utf8'),identity=await readFile('scripts/cp7_model_history_scope/identity.sql','utf8')
await db.exec(identity);await db.exec(source)
const sql=async(s,p=[])=>(await db.query(s,p)).rows[0]?.v
const product=r=>({id:r,root_id:r,size_id:size,commercial:[]}),stock=r=>({id:randomUUID(),root_id:r,size_id:size,qty_signed:'100',physical_at:at,system_created_at:at})
const sale={id:randomUUID(),sale_id:randomUUID(),root_id:root,sold_commercial:[],status:'POSTED',qty_pcs:'24'},foreignSale={id:randomUUID(),sale_id:randomUUID(),root_id:other,sold_commercial:[],status:'DRAFT'}
const journal={id:randomUUID(),sale_id:sale.sale_id,reversal_of_id:null},inverse={id:randomUUID(),sale_id:randomUUID(),reversal_of_id:journal.id}
const ret={id:randomUUID(),return_id:randomUUID(),sale_item_id:sale.id},rj={id:randomUUID(),return_id:ret.return_id,reversal_of_id:null},ri={id:randomUUID(),return_id:randomUUID(),reversal_of_id:rj.id}
const ownStock=stock(root),foreignStock=stock(other),sort=rows=>rows.sort((a,b)=>a.id.localeCompare(b.id))
const ownFacts={products:[product(root)],stock:[ownStock],sales:[sale],sale_journals:sort([journal,inverse]),returns:[ret],return_journals:sort([rj,ri])}
const capture={contract_version:'cp7.native-demand-facts.v1',scope:'GLOBAL_CURRENT_PHYSICAL_ROOTS',captured_at:at,status:'COMPLETE',stock_raw_omitted:false,stock_rows_at_least:2,
 facts:{products:sort([product(root),product(other)]),stock:sort([ownStock,foreignStock]),sales:sort([sale,foreignSale]),sale_journals:sort([journal,inverse]),returns:[ret],return_journals:sort([rj,ri])}}
const digest=async(rows,clock=at)=>({contract_version:'cp7.native-stock-row-digest.v1',scope:'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS',captured_at:clock,row_count:String(rows.length),
 rows_sha256:await sql("select encode(sha256(convert_to(E'cp7.native-stock-row-digest.v1\\n'||count(*)::text||E'\\n'||coalesce(string_agg(encode(sha256(convert_to(x::text,'UTF8')),'hex'),E'\\n'order by x->>'id'),''),'UTF8')),'hex')v from jsonb_array_elements($1::jsonb)x",[JSON.stringify(rows)]),raw_rows_truncated:false,raw_native_capture_status_overridden:false})
const dg=await digest([ownStock]),raw={contract_version:'cp7.model-history-facts.v1',scope:'SINGLE_CURRENT_PHYSICAL_ROOT',captured_at:at,status:'COMPLETE',target_key:target,producer_hash:producer,facts:ownFacts,stock_reference:dg,stock_raw_omitted:false,stock_rows_at_least:1}
const bind=(c=capture,d=dg,t=target,lim=5000,p=producer)=>sql('select cp7_model_target_binding.reference($1::jsonb,$2,$3,$4::jsonb,$5)v',[JSON.stringify(c),t,lim,JSON.stringify(d),p])
const scoped=r=>sql('select cp7_model_history_scope.identity($1::jsonb)v',[JSON.stringify(r)])
const clone=structuredClone
const test=async(id,fn)=>{try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,1800)})}console.log(id+': '+cases.at(-1).status)}
await test('EXACT_SCOPED_IDENTITY_FROM_GLOBAL_CAPTURE',async()=>{
 const x=await bind();assert.equal(x.scoped_source_hash,await scoped(raw));assert.equal(x.global_raw_capture_status,'COMPLETE');assert.equal(x.raw_native_capture_status_overridden,false)
 assert.deepEqual(await sql('select cp7_model_target_binding.non_stock($1::jsonb,$2,5000)v',[JSON.stringify(capture),target]),Object.fromEntries(Object.entries(ownFacts).filter(([k])=>k!=='stock')))
 return{same_target_exact_products_sales_returns_and_reversal_chains:true}
})
await test('GLOBAL_STOCK_OMISSION_NOT_ZERO_OR_RELABELED',async()=>{
 const c=clone(capture);c.status='INCOMPLETE';c.stock_raw_omitted=true;c.stock_rows_at_least=50001;c.facts.stock=[]
 const x=await bind(c);assert.equal(x.scoped_source_hash,await scoped(raw));assert.equal(x.global_raw_capture_status,'INCOMPLETE');assert.equal(x.stock_reference.row_count,'1');assert.equal(x.raw_native_capture_status_overridden,false)
 const changed=await bind(c,{...dg,rows_sha256:'2'.repeat(64)});assert.notEqual(x.scoped_source_hash,changed.scoped_source_hash)
 return{separate_complete_target_digest_retained:true,no_global_raw_status_override:true}
})
await test('TARGET_CHANGES_BIND_FOREIGN_TARGET_DOES_NOT',async()=>{
 const original=await bind(),foreign=clone(capture);foreign.facts.sales.find(x=>x.id===foreignSale.id).qty_pcs='999';assert.equal((await bind(foreign)).scoped_source_hash,original.scoped_source_hash)
 const own=clone(capture);own.facts.sales.find(x=>x.id===sale.id).qty_pcs='25';assert.notEqual((await bind(own)).scoped_source_hash,original.scoped_source_hash)
 assert.notEqual((await bind(capture,dg,target,5000,'3'.repeat(64))).scoped_source_hash,original.scoped_source_hash)
 return{own_fact_and_producer_changes_hash:true,unrelated_target_stays_out:true}
})
await test('RAW_COMPLETE_STOCK_DIGEST_CANNOT_DISAGREE',async()=>{
 await assert.rejects(()=>bind(capture,{...dg,rows_sha256:'4'.repeat(64)}),/CP7_MODEL_TARGET_BINDING_STOCK_MISMATCH/)
 await assert.rejects(()=>bind(capture,{...dg,row_count:'0'}),/CP7_MODEL_TARGET_BINDING_STOCK_MISMATCH/)
 const changed=clone(capture);changed.facts.stock.find(x=>x.id===ownStock.id).system_created_at='2026-10-24T12:00:01.000000Z';await assert.rejects(()=>bind(changed),/CP7_MODEL_TARGET_BINDING_STOCK_MISMATCH/)
 return{full_raw_rows_and_system_clock_bound:true}
})
await test('NON_STOCK_INCOMPLETE_NEVER_REPAIRED_BY_STOCK_DIGEST',async()=>{
 const c=clone(capture);c.status='INCOMPLETE';c.stock_raw_omitted=true;c.stock_rows_at_least=50001;c.facts.stock=[]
 for(const mutate of[x=>{x.facts.sales=Array(50001).fill(foreignSale)},x=>{x.facts.products.push(product(root))},x=>{x.facts.products[0].commercial=[{},{}]},x=>{x.facts.sale_journals=x.facts.sale_journals.filter(j=>j.id!==journal.id)}]){
  const bad=clone(c);mutate(bad);await assert.rejects(()=>bind(bad),/CP7_MODEL_TARGET_BINDING_NON_STOCK_INCOMPLETE/)
 }
 await assert.rejects(()=>bind(c,dg,target,1),/CP7_MODEL_TARGET_BINDING_NON_STOCK_INCOMPLETE/)
 return{all_global_non_stock_bounds_retained:true}
})
await test('CLOSED_SCOPE_CLOCK_AND_RAW_STATUS',async()=>{
 await assert.rejects(()=>bind(capture,dg,root+':'+randomUUID()),/CP7_MODEL_TARGET_BINDING_TARGET_UNAVAILABLE/)
 await assert.rejects(()=>bind(capture,{...dg,captured_at:'2026-10-24T12:00:01.000000Z'}),/CP7_MODEL_TARGET_BINDING_STOCK_REFERENCE/)
 await assert.rejects(()=>bind({...capture,status:'INCOMPLETE'}),/CP7_MODEL_TARGET_BINDING_RAW_STATUS/)
 await assert.rejects(()=>bind({...capture,stock_raw_omitted:true}),/CP7_MODEL_TARGET_BINDING_RAW_STATUS/)
 for(const d of[{...dg,raw_rows_truncated:true},{...dg,raw_native_capture_status_overridden:true},{...dg,row_count:null}])await assert.rejects(()=>bind(capture,d),/CP7_MODEL_TARGET_BINDING_STOCK_REFERENCE/)
 return{unavailable_target_mismatched_clock_and_fabricated_completeness_refused:true}
})
await test('PRIVATE_SQL_ONLY_NO_PUBLIC_ENTRY',async()=>{
 for(const role of['anon','authenticated','service_role'])assert.equal(await sql("select has_function_privilege($1,'cp7_model_target_binding.reference(jsonb,text,integer,jsonb,text)','EXECUTE')v",[role]),false)
 assert.equal(await sql("select count(*)::integer v from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_model_target_binding'and not p.prosecdef and p.provolatile='i'and pg_get_userbyid(p.proowner)='cp7_capture'"),2)
 return{private_invoker_functions_only:true}
})
const report={contract:'cp7.model-target-physical-binding-local.v1',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',expected:7,counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,
 sql_sha256:createHash('sha256').update(source).digest('hex'),existing_identity_sha256:createHash('sha256').update(identity).digest('hex'),actual_SQL:true,synthetic_facts_and_digests:true,actual_Native:false,actual_Auth_HTTP_credit:false,target_caller_integrated:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-physical-binding-local.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
