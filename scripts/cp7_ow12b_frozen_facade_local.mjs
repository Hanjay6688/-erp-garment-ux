// Local authority/forwarding controls with an explicit controlled request.
// Actual Auth, access policy, Native catalog22 and request flow are not simulated.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),cases=[],j=JSON.stringify
const query={from_date:'2026-10-01',through_date:'2026-10-02',group_mode:'AS_SOLD'},id='11111111-1111-4111-8111-111111111111'
const value=async(s,a=[])=>(await db.query(s,a)).rows[0]?.v
const call=q=>value('select public.erp_cp7_request_bounded_staged_analysis_v2($1::jsonb,$2::uuid)v',[j(q),id])
async function test(name,fn){await fn();cases.push({id:name,status:'PASS'})}
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create role cp7_alert;revoke create on schema public from public;create schema cp7_frozen_analysis_units_v2 authorization cp7_capture;')
 await db.exec(await readFile('scripts/cp7-src/wip/bootstrap.sql','utf8'))
 await db.exec(`create function cp7_frozen_analysis_units_v2.request(q jsonb,r uuid)returns jsonb language plpgsql volatile security invoker set search_path=''as $$begin
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 if r is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 return jsonb_build_object('controlled_request',true,'effective_role',current_user,'query',q,'request',r);end$$;
 alter function cp7_frozen_analysis_units_v2.request(jsonb,uuid)owner to cp7_capture;
 revoke all on function cp7_frozen_analysis_units_v2.request(jsonb,uuid)from public,anon,authenticated,service_role,cp7_alert;`)
 const sql=await readFile('scripts/cp7_frozen_analysis_facade_v2/facade.sql','utf8');await db.exec(sql)
 await test('ACTUAL_FACADE_OWNER_SEARCH_PATH_AND_ONLY_AUTHENTICATED_EXECUTE',async()=>{
  const row=await value("select jsonb_build_object('owner',pg_get_userbyid(p.proowner),'definer',p.prosecdef,'volatile',p.provolatile,'settings',p.proconfig)v from pg_proc p where p.oid='public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)'::regprocedure")
  assert.deepEqual(row,{owner:'cp7_capture',definer:true,volatile:'v',settings:['search_path=""','TimeZone=UTC']})
  assert.equal(await value("select has_schema_privilege('cp7_capture','public','CREATE')v"),false)
  for(const role of['anon','authenticated','service_role','cp7_alert'])assert.equal(await value("select has_function_privilege($1,'public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)','EXECUTE')v",[role]),role==='authenticated')
 })
 await test('WRAPPER_FORWARDS_EXACT_QUERY_UUID_WITH_PRIVATE_OWNER_ONLY',async()=>{
  await db.exec('set role authenticated')
  assert.deepEqual(await call(query),{controlled_request:true,effective_role:'cp7_capture',query,request:id})
  await assert.rejects(()=>db.query('select cp7_frozen_analysis_units_v2.request($1::jsonb,$2::uuid)',[j(query),id]),/permission denied/)
  await assert.rejects(()=>call({...query,actor:id}),/CP7_WIP_FIELDS/)
  await db.exec('reset role')
 })
 await test('ANON_SERVICE_AND_ALERT_CANNOT_EXECUTE_FACADE',async()=>{
  for(const role of['anon','service_role','cp7_alert']){
   await db.exec('set role '+role);await assert.rejects(()=>call(query),/permission denied/);await db.exec('reset role')
  }
 })
 await test('DEPENDENT_VIEW_BLOCKS_DROP_WITHOUT_PARTIAL_REMOVAL',async()=>{
  await db.exec('create view public.frozen_facade_local_guard as select public.erp_cp7_request_bounded_staged_analysis_v2(null,null)v')
  await assert.rejects(()=>db.exec('drop function public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)restrict'),/depend/)
  assert.equal(await value("select to_regprocedure('public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)')is not null v"),true)
  await db.exec('drop view public.frozen_facade_local_guard;drop function public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)restrict')
  assert.equal(await value("select to_regprocedure('public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)')is null v"),true)
 })
 const report={contract:'cp7.frozen-facade-local-controls.v2',status:'PASS',cases,counts:{PASS:cases.length},sql_sha256:createHash('sha256').update(sql).digest('hex'),
  server_version:await value('select version()v'),controlled_private_request:true,actual_Auth_HTTP_credit:false,actual_Native:false,actual_private_access_policy_qualified:false,
  Python_catalog_installer_qualified:false,public_or_default_request_adopted:false,production_go:false}
 if(process.env.CP7_FROZEN_FACADE_REPORT)await writeFile(process.env.CP7_FROZEN_FACADE_REPORT,j(report)+'\n')
 console.log(j(report))
}finally{await db.close()}
