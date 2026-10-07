import {readFileSync} from 'node:fs'
import {functionBlocks} from './schedule-scenario-fixture.mjs'
// Explicit kernel-only access/source stand-ins. Native Auth and HTTP are
// exercised separately by p19-staged12; these helpers never accept a DB URL.
export async function installStagedApiControls(db){
 const jobs=functionBlocks(readFileSync('scripts/cp7-src/planning/analysis-jobs.sql','utf8'))
 const analysis=functionBlocks(readFileSync('scripts/cp7-src/planning/analysis.sql','utf8'))
 await db.execute(`
 create table public.stage_capture(c jsonb not null);
 grant select on public.stage_capture to cp7_capture;
 create function cp7_schedule_native.access_now(writing boolean)returns jsonb language plpgsql stable set search_path='' as $$
 begin
  if coalesce(current_setting('test.actor',true),'')='' then raise exception using errcode='42501',message='CP7_ACCESS_DENIED';end if;
  return jsonb_build_object('actor',current_setting('test.actor'),'permissions',coalesce(current_setting('test.perm',true),'view'));
 end $$;
 create function cp7_planning.history_query(q jsonb)returns jsonb language sql immutable as $$select q$$;
 create function cp7_analysis_native.source_within(products integer,matching integer)returns jsonb language sql stable set search_path='' as $$select c from public.stage_capture$$;
 ${['cp7_analysis_native.finance_mode','cp7_analysis_native.serve','cp7_analysis_native.capture','public.erp_cp7_read_analysis_v1'].map(n=>analysis.get(n)).join('\n')}
 ${['cp7_analysis_jobs.compute_key','cp7_analysis_jobs.worker_active','cp7_analysis_jobs.status','cp7_analysis_jobs.manifest','cp7_analysis_jobs.segment','cp7_analysis_jobs.request','public.erp_cp7_request_analysis_job_v1','public.erp_cp7_read_analysis_manifest_v1'].map(n=>jobs.get(n)).join('\n')}
 create function cp7_analysis_native.source_for(q jsonb,finance text)returns jsonb language sql stable as $$select c from public.stage_capture$$;
 do $$declare r record;begin
  for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname in('cp7_schedule_native','cp7_analysis_native','cp7_analysis_jobs')loop execute format('alter function %s owner to cp7_capture',r.sig);end loop;
 end $$;
 alter function public.erp_cp7_read_analysis_v1(uuid)owner to cp7_capture;
 alter function public.erp_cp7_read_analysis_manifest_v1(uuid)owner to cp7_capture;
 alter function public.erp_cp7_request_analysis_job_v1(jsonb,uuid)owner to cp7_capture;
 revoke all on function public.erp_cp7_read_analysis_v1(uuid),public.erp_cp7_read_analysis_manifest_v1(uuid),public.erp_cp7_request_analysis_job_v1(jsonb,uuid)from public,anon,service_role;
 grant execute on function public.erp_cp7_read_analysis_v1(uuid),public.erp_cp7_read_analysis_manifest_v1(uuid),public.erp_cp7_request_analysis_job_v1(jsonb,uuid)to authenticated;
 grant usage on schema public to authenticated;`)
}
// Each invocation resets every test setting: Native runtime uses independent
// psql sessions, whereas explicit local WASM uses one connection.
export async function callAs(db,actor,sql,extra=''){
 const out=await db.execute(`reset role;set test.actor='${actor}';set test.perm='view';${extra}set role authenticated;select (${sql})::text as result;reset role;`)
 if(Array.isArray(out))return JSON.parse(out.find(x=>x.rows?.length)?.rows[0].result)
 return JSON.parse(String(out).trim().split('\n').at(-1))
}
export async function refuseAs(db,actor,sql,code,extra=''){
 let message='';try{await callAs(db,actor,sql,extra)}catch(e){message=String(e.stderr??e)}finally{await db.execute('reset role;')}
 if(!message.includes(code))throw Error(`Expected ${code}; received ${message.slice(0,500)}`)
}
