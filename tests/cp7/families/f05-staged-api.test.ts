// @vitest-environment node
import {expect,test} from 'vitest'
import {parseStagedJob} from '../../../src/nativeStagedJob'
import {installScenarioControls,scenarioCapture} from './f04/staged-scenario-fixture.mjs'
import {openRuntime,jsonArg} from './f04/runtime.mjs'
import {ACTOR,QUERY,installStagedControls,stagedInput} from './f04/staged-analysis-fixture.mjs'
import {installStagedApiControls,callAs,refuseAs} from './f04/staged-api-fixture.mjs'
const uuid=(n:number)=>`03000000-0000-4000-8000-${n.toString(16).padStart(12,'0')}`

test('P19 staged API: idempotent request, fixed capture, status has no side effects, lost step reply resumes, access revoked stops',async()=>{
 const db=await openRuntime({commandTimeoutMs:600000})
 try{
  await installStagedControls(db);await installStagedApiControls(db)
  const c=stagedInput(7010,{targets:20,positions:6,roots:8,models:2,complete:true})
  await db.execute(`insert into public.stage_capture values(${jsonArg(c)})`)
  const req=uuid(1),request=`public.erp_cp7_request_staged_analysis_v1(${jsonArg(QUERY)},'${req}')`
  const a=await callAs(db,ACTOR,request),b=await callAs(db,ACTOR,request)
  expect(b).toEqual(a);expect(a).toMatchObject({contract_version:'cp7.native-analysis-staged-job.v1',state:'RUNNING',units_done:0,apply_enabled:false,production_go:false})
  await refuseAs(db,ACTOR,`public.erp_cp7_request_staged_analysis_v1(${jsonArg({...QUERY,group_mode:'RESTATED'})},'${req}')`,'CP7_ANALYSIS_REQUEST_CHANGED')
  await refuseAs(db,ACTOR,`public.erp_cp7_request_analysis_job_v1(${jsonArg(QUERY)},'${req}')`,'CP7_ANALYSIS_REQUEST_CHANGED')
  // The direct capture must reject the staged UUID too, under the same lock.
  await expect(db.execute(`reset role;set test.actor='${ACTOR}';set test.perm='view';select cp7_analysis_native.capture(${jsonArg(QUERY)},'${req}','DEFERRED')`)).rejects.toThrow(/CP7_ANALYSIS_REQUEST_CHANGED/)
  await db.execute(`reset role;update public.stage_capture set c=c||'{"analysis_engine_signature":"changed-after-capture"}'::jsonb`)
  expect((await callAs(db,ACTOR,request)).reference).toEqual(a.reference)
  const first=await callAs(db,ACTOR,`public.erp_cp7_step_staged_analysis_v1('${req}')`)
  expect(first.units_done).toBe(1)
  // Treat the previous reply as lost: only get(), never re-create the job.
  const reread=await callAs(db,ACTOR,`public.erp_cp7_get_staged_analysis_v1('${req}')`)
  expect(reread).toEqual(first);expect((await callAs(db,ACTOR,`public.erp_cp7_get_staged_analysis_v1('${req}')`)).units_done).toBe(1)
  const stopped=await callAs(db,ACTOR,`public.erp_cp7_step_staged_analysis_v1('${req}')`,"set test.perm='revoked';")
  expect(stopped).toMatchObject({state:'FAILED',units_done:1,failure:{code:'CP7_ANALYSIS_ACCESS_CHANGED',sqlstate:'42501'}})
  expect((await callAs(db,ACTOR,`public.erp_cp7_step_staged_analysis_v1('${req}')`)).units_done).toBe(1)
  await refuseAs(db,uuid(99),`public.erp_cp7_get_staged_analysis_v1('${req}')`,'CP7_ANALYSIS_JOB_UNAVAILABLE')
  const ordinary=uuid(2)
  await callAs(db,ACTOR,`public.erp_cp7_request_analysis_job_v1(${jsonArg(QUERY)},'${ordinary}')`)
  await refuseAs(db,ACTOR,`public.erp_cp7_request_staged_analysis_v1(${jsonArg(QUERY)},'${ordinary}')`,'CP7_ANALYSIS_REQUEST_CHANGED')
  const rows=await db.query(`select count(*) n from cp7_analysis_stage.jobs where request_id='${req}'`);expect(rows[0].n).toBe(1)
  // Above capacity, the initial status remains a valid contract. The real
  // HIST_PREP refusal is tested on the real scenario chain below.
  await db.execute(`reset role;update public.stage_capture set c=jsonb_set(c,'{facts,products}',
   (select jsonb_agg((c#>'{facts,products,0}')||jsonb_build_object('id','over-'||i,'root_id','over-'||i))from generate_series(1,5001)i))`)
  const over=uuid(5)
  const accepted=parseStagedJob(await callAs(db,ACTOR,`public.erp_cp7_request_staged_analysis_v1(${jsonArg(QUERY)},'${over}')`),over)
  expect(accepted.targetsTotal).toBeNull()
 }finally{await db.close()}
},900000)

test('P19 staged API: exact six public boundaries and deny-all private tables, immutable reference and retained completed pages',async()=>{
 const db=await openRuntime({commandTimeoutMs:600000})
 try{
  await installStagedControls(db);await installStagedApiControls(db)
  const p=await db.query(`select p.proname name,pg_get_userbyid(p.proowner) owner,p.prosecdef definer,p.proconfig config,
   has_function_privilege('authenticated',p.oid,'EXECUTE') authenticated,has_function_privilege('anon',p.oid,'EXECUTE') anon,
   has_function_privilege('service_role',p.oid,'EXECUTE') service from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='public'and p.proname like '%staged_analysis%'order by 1`)
  expect(p).toHaveLength(6)
  for(const r of p)expect(r).toMatchObject({owner:'cp7_capture',definer:true,config:['search_path=""'],authenticated:true,anon:false,service:false})
  const priv=await db.query(`select bool_or(has_schema_privilege(r,'cp7_analysis_stage','USAGE')) schemas,
   bool_or(has_table_privilege(r,c.oid,'SELECT,INSERT,UPDATE,DELETE')) tables,bool_and(c.relrowsecurity) rls
   from pg_class c join pg_namespace n on n.oid=c.relnamespace cross join unnest(array['anon','authenticated','service_role'])r
   where n.nspname='cp7_analysis_stage'and c.relkind='r'`)
  expect(priv[0]).toEqual({schemas:false,tables:false,rls:true})
  const c=stagedInput(7011,{targets:9,positions:3,roots:4,models:2,complete:true})
  await db.execute(`insert into public.stage_capture values(${jsonArg(c)})`)
  const req=uuid(3)
  let s=await callAs(db,ACTOR,`public.erp_cp7_request_staged_analysis_v1(${jsonArg(QUERY)},'${req}')`)
  await expect(db.execute(`reset role;update cp7_analysis_stage.jobs set reference=reference where request_id='${req}'`)).rejects.toThrow(/CP7_RUN_IMMUTABLE/)
  for(let i=0;i<500&&s.state==='RUNNING';i++)s=await callAs(db,ACTOR,`public.erp_cp7_step_staged_analysis_v1('${req}')`)
  expect(s.state).toBe('DONE')
  const before=await callAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_pages_v1('${s.run_id}')`)
  const [{job}]=await db.query(`select id job from cp7_analysis_stage.jobs where request_id='${req}'`)
  await db.execute(`reset role;select cp7_analysis_stage.purge_intermediates('${job}')`)
  expect(await callAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_pages_v1('${s.run_id}')`)).toEqual(before)
  expect((await callAs(db,ACTOR,`public.erp_cp7_step_staged_analysis_v1('${req}')`)).state).toBe('DONE')
 }finally{await db.close()}
},900000)


test('P19 real scenario status is accepted by the frontend at every unit; pairs are not target progress',async()=>{
 const db=await openRuntime({commandTimeoutMs:600000})
 try{
  await installScenarioControls(db,{bounds:{sales_per_events_unit:4,targets_per_chunk:7,history_cells_per_unit:37,pairs_per_chunk:45}})
  const {c,q}=scenarioCapture(410,{targets:20,days:3,sales:3,groups:20,reviewed:true})
  const req=uuid(4)
  const [{job}]=await db.query(`select cp7_analysis_stage.create_job('${ACTOR}','${req}',${jsonArg(q)},'{"actor":"${ACTOR}","profile":{"role_code":"OWNER"}}',public.ss_complete(${jsonArg(c)},410)) job`)
  let s=(await db.query(`select cp7_analysis_stage.status('${job}') s`))[0].s,events=0,pairs=0
  parseStagedJob(s,req)
  for(let i=0;i<500&&s.state==='RUNNING';i++){
   s=(await db.query(`select cp7_analysis_stage.step('${job}') s`))[0].s;parseStagedJob(s,req)
   if(s.stage==='HIST_EVENTS'){events++;expect(s.targets_done_in_stage).toBe(0)}
   if(s.stage==='NET_PAIRS'){pairs++;expect(s.targets_done_in_stage).toBe(0)}
  }
  if(s.state!=='DONE')console.log(JSON.stringify({s,details:await db.query(`select failure_message from cp7_analysis_stage.jobs where request_id='${req}'`)}))
  expect(events).toBeGreaterThan(5);expect(pairs).toBeGreaterThan(1);expect(s.state).toBe('DONE')
  const over=uuid(6)
  const [{extra}]=await db.query(`select cp7_analysis_stage.create_job('${ACTOR}','${over}',query,access_at_capture,
   jsonb_set(reference,'{facts,products}',(select jsonb_agg((reference#>'{facts,products,0}')||jsonb_build_object('id','over-'||i,'root_id','over-'||i))from generate_series(1,5001)i))) extra
   from cp7_analysis_stage.jobs where id='${job}'`)
  expect(parseStagedJob((await db.query(`select cp7_analysis_stage.status('${extra}') s`))[0].s,over).targetsTotal).toBeNull()
  const refused=parseStagedJob((await db.query(`select cp7_analysis_stage.step('${extra}') s`))[0].s,over)
  expect(refused).toMatchObject({state:'FAILED',failure:{code:'CP7_ANALYSIS_STAGED_TARGET_LIMIT'}})
 }finally{await db.close()}
},900000)
