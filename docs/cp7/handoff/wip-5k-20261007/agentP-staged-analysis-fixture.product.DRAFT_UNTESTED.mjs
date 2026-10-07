// DRAFT (UNTESTED) — intended replacement of tests/cp7/families/f04/staged-analysis-fixture.mjs
// once the staged tests move to the PRODUCT file. Not committed: the committed tests still load the prototypes.
import { readFileSync } from 'node:fs'
import { jsonArg } from './runtime.mjs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
import { installNettingControls, nettingInput } from './netting-fixture.mjs'
import { rng } from './demand-history-fixture.mjs'
// P19 staged analysis (the PRODUCT file scripts/cp7-src/planning/analysis-stages.sql)
// against the single compiler on the same runtime. Stand-ins, as in the netting
// and assembly fixtures: the schedule build (c->'stub_scenario'), fabric
// plan/needs and accessory needs; and, TEST ONLY, the job's scenario units
// (this corpus plants netting faults inside a stub scenario, so its SCENARIO
// unit must be the stub schedule build: cp7_analysis_stage.run_scenario_unit
// is replaced by a stand-in that plans SCENARIO -> NET_PREP). The product has
// no such switch. Kernel comparisons only, never Native/Auth/HTTP qualification.
export const ACTOR = '03000000-0000-4000-8000-000000000001'
export const ACCESS = { actor: ACTOR, profile: { role_code: 'OWNER' } }
export const QUERY = { from_date: '2026-05-01', through_date: '2026-05-30', group_mode: 'AS_SOLD' }
export const PRODUCT = 'scripts/cp7-src/planning/analysis-stages.sql'
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }
const read = path => readFileSync(path, 'utf8')
export const bounds = b => `create or replace function cp7_analysis_stage.bounds()returns jsonb language sql immutable as $$select '${JSON.stringify(b)}'::jsonb$$;`

// TEST STAND-IN for the stub-scenario corpus: no history/baseline/supply units;
// the SCENARIO unit is the single (stub) schedule build, stored as the real
// SCENARIO unit stores it (BASE/STOCK/HIST rows + the skeleton).
export const SCENARIO_STAND_IN = `
create or replace function cp7_analysis_stage.run_scenario_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units,c jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare scenario jsonb;
begin
 if u.kind='HIST_PREP'then
  insert into cp7_analysis_stage.units values(j.id,1,'SCENARIO',0,null,null),(j.id,2,'NET_PREP',0,null,null);
  update cp7_analysis_stage.jobs set unit_count=3 where id=j.id;
  return jsonb_build_object('stand_in','EXPLICIT_STAGED_KERNEL_ONLY_STUB_SCENARIO');
 end if;
 if u.kind='SCENARIO'then
  scenario:=cp7_schedule_native.build(c,j.query);
  insert into cp7_analysis_stage.target_rows select j.id,'BASE',x.o,x.v->>'target_key',x.v
   from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')with ordinality x(v,o);
  insert into cp7_analysis_stage.target_rows select j.id,'STOCK',x.o,x.v->>'target_key',x.v
   from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'history_run_result'->'current_stock')with ordinality x(v,o);
  insert into cp7_analysis_stage.target_rows select j.id,'HIST',x.o,x.v->>'target_key',x.v
   from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'history_run_result'->'history'->'rows')with ordinality x(v,o);
  return jsonb_build_object('scenario',scenario#-'{supply_run_result,baseline_run_result,rows}'
   #-'{supply_run_result,baseline_run_result,history_run_result,current_stock}'#-'{supply_run_result,baseline_run_result,history_run_result,history,rows}',
   'rows_null',scenario->'supply_run_result'->'baseline_run_result'->'rows'is null);
 end if;
 raise exception 'CP7_ANALYSIS_STAGE_UNKNOWN_UNIT';
end $$;`

// Independent of the page builder: reads the job's header, every page and the
// page index, checks each (canonical text, UTF8 size, sha256, binding,
// contiguity, counts/offsets/totals, identity hash), rebuilds the analysis and
// the Original from header + pages, and compares them with the single build's
// analysis (jsonb) when one is given: as jsonb and as canonical text, the
// single build's semantic_hash recomputed from the reassembled text, the
// Original = cp7_analysis_jobs.original() of a run row holding the single
// build, the header = that Original without the analysis, and per paged array
// the page items (in page order) = the per-target items of the single analysis.
export const VERIFY_SQL = `
create function public.sv_sha(t text)returns text language sql immutable as $$select encode(pg_catalog.sha256(convert_to(t,'UTF8')),'hex')$$;
create function public.sv_verify(p_job uuid,single jsonb)returns jsonb language plpgsql as $s$
declare j cp7_analysis_stage.jobs%rowtype;h cp7_analysis_stage.headers%rowtype;ps cp7_analysis_stage.page_sets%rowtype;b jsonb:=cp7_analysis_stage.bounds();
 hdr jsonb;pj jsonb;p record;i integer:=0;expect integer:=1;running jsonb:='{}';bad text[]:='{}';cuts jsonb:='[]';
 k text;v jsonb;pref bigint;n bigint;rebuilt jsonb;without jsonb;hash text;full_text text;original_text text;identity text;orig jsonb;
 items_text text;single_text text;rec jsonb;unreviewed bigint;
 header_keys text[]:=array['contract_version','analysis_header','paged','targets_total','page_count'];
begin
 select *into j from cp7_analysis_stage.jobs where id=p_job;
 if j.state<>'DONE'then
  return jsonb_build_object('state',j.state,'page_set',exists(select 1 from cp7_analysis_stage.page_sets where run_id=j.run_id),
   'header',exists(select 1 from cp7_analysis_stage.headers where run_id=j.run_id),'pages',(select count(*)from cp7_analysis_stage.pages where run_id=j.run_id));
 end if;
 select *into h from cp7_analysis_stage.headers where run_id=j.run_id;select *into ps from cp7_analysis_stage.page_sets where run_id=j.run_id;
 if h.run_id is null or ps.run_id is null then return jsonb_build_object('state',j.state,'page_set',false,'header',h.run_id is not null);end if;
 hdr:=h.body::jsonb;
 if h.body<>hdr::text then bad:=bad||'header_not_canonical'::text;end if;
 if h.sha256<>public.sv_sha(h.body)or h.utf8_bytes<>octet_length(h.body)or h.utf8_bytes>(b->>'header_utf8_bytes')::integer then bad:=bad||'header_hash'::text;end if;
 if hdr->>'contract_version'<>'cp7.native-analysis-header.v1'or hdr->'paged'<>h.paged or(hdr->>'targets_total')::integer<>h.targets_total
  or(hdr->>'page_count')::integer<>h.page_count or hdr->>'run_id'<>j.run_id::text or hdr->>'request_id'<>j.request_id::text or hdr->'query'<>j.query
  or hdr->'apply_enabled'<>'false'or hdr->'production_go'<>'false'or hdr?'analysis'or hdr->'financial_source'<>'null'::jsonb
  or hdr->'analysis_header'?'semantic_hash'or hdr?'semantic_hash'or hdr?'document_sha256'
  or(select array_agg(x order by x)from jsonb_object_keys(hdr)x)<>(select array_agg(x order by x)from unnest(header_keys||array['run_id','request_id','query','financial_source','product_labels','apply_enabled','production_go'])x)
  then bad:=bad||'header_binding'::text;end if;
 for p in select *from cp7_analysis_stage.pages x where x.run_id=j.run_id order by x.idx loop
  pj:=p.body::jsonb;cuts:=cuts||jsonb_build_array(jsonb_build_array(p.target_lo,p.target_hi));
  if p.body<>pj::text then bad:=bad||('page_not_canonical:'||p.idx);end if;
  if p.sha256<>public.sv_sha(p.body)or p.utf8_bytes<>octet_length(p.body)or p.utf8_bytes>(b->>'page_utf8_bytes')::integer then bad:=bad||('page_hash:'||p.idx);end if;
  if pj->>'contract_version'<>'cp7.native-analysis-page.v1'or pj->>'run_id'<>j.run_id::text or pj->>'request_id'<>j.request_id::text
   or(pj->>'index')::integer<>i or p.idx<>i or(pj->>'target_lo')::integer<>expect or p.target_lo<>expect or(pj->>'target_hi')::integer<>p.target_hi
   or(pj->>'page_count')::integer<>h.page_count or(pj->>'targets_total')::integer<>h.targets_total or pj->>'header_sha256'<>h.sha256
   or pj->'apply_enabled'<>'false'or pj->'production_go'<>'false'or pj->'counts'<>p.counts or pj->'offsets'<>p.offsets or pj->'summary'<>p.summary
   or pj?'document_sha256'or pj?'semantic_hash'
   or(select array_agg(x order by x)from jsonb_object_keys(pj->'items')x)is distinct from(select array_agg(x order by x)from jsonb_object_keys(h.paged)x)
  then bad:=bad||('page_binding:'||p.idx);end if;
  for k,v in select key,value from jsonb_each(h.paged)loop
   if(pj->'counts'->>k)::bigint<>jsonb_array_length(pj->'items'->k)or(pj->'offsets'->>k)::bigint<>coalesce((running->>k)::bigint,0)
    or pj->'totals'->k<>v->'items'then bad:=bad||('page_counts:'||p.idx||':'||k);end if;
   running:=running||jsonb_build_object(k,coalesce((running->>k)::bigint,0)+jsonb_array_length(pj->'items'->k));
  end loop;
  if pj->'summary'<>cp7_analysis_stage.page_summary(pj->'items')then bad:=bad||('page_summary:'||p.idx);end if;
  expect:=p.target_hi+1;i:=i+1;
 end loop;
 if i<>h.page_count or expect<>h.targets_total+1 or(h.page_count=0)<>(h.targets_total=0)then bad:=bad||'page_range'::text;end if;
 if cuts<>h.cuts then bad:=bad||'cuts'::text;end if;
 select public.sv_sha(h.sha256||E'\\n'||coalesce(string_agg(x.sha256,E'\\n'order by x.idx),''))into identity from cp7_analysis_stage.pages x where x.run_id=j.run_id;
 if identity<>ps.identity_hash then bad:=bad||'identity'::text;end if;
 rebuilt:=hdr->'analysis_header';
 for k,v in select key,value from jsonb_each(h.paged)loop
  pref:=(v->>'prefix')::bigint;n:=(v->>'items')::bigint;
  if(running->>k)::bigint is distinct from n then bad:=bad||('items_total:'||k);end if;
  rebuilt:=jsonb_set(rebuilt,array[k],(select coalesce(jsonb_agg(z.e order by z.g,z.o),'[]'::jsonb)from(
   select 0 g,x.o,x.e from jsonb_array_elements(hdr->'analysis_header'->k)with ordinality x(e,o)where x.o<=pref
   union all select 1+q.idx,y.o,y.e from cp7_analysis_stage.pages q cross join lateral jsonb_array_elements(q.body::jsonb->'items'->k)with ordinality y(e,o)where q.run_id=j.run_id
   union all select 1000000000,x.o,x.e from jsonb_array_elements(hdr->'analysis_header'->k)with ordinality x(e,o)where x.o>pref)z));
 end loop;
 hash:=public.sv_sha(rebuilt::text);
 full_text:=(rebuilt||jsonb_build_object('semantic_hash',hash))::text;
 orig:=cp7_analysis_jobs.original(row(j.run_id,j.actor,j.request_id,j.query,j.captured_at,j.access_at_capture,j.reference,coalesce(single,'null'::jsonb),j.source_hash)::cp7_analysis_native.runs);
 original_text:=((hdr-header_keys)||jsonb_build_object('contract_version','cp7.native-analysis-run.v1','analysis',full_text::jsonb))::text;
 if(hdr-header_keys)::text<>(orig-'contract_version'-'analysis')::text then bad:=bad||'header_original'::text;end if;
 select jsonb_build_object('ACTIVE',count(*)filter(where r->>'production_state'='ACTIVE'),'PAUSED',count(*)filter(where r->>'production_state'='PAUSED'),
   'STOPPED',count(*)filter(where r->>'production_state'='STOPPED'),'OTHER',count(*)filter(where r->>'production_state'is null or r->>'production_state'not in('ACTIVE','PAUSED','STOPPED')))
  into rec from jsonb_array_elements(coalesce(rebuilt->'recommendations','[]'))r;
 select count(*)into unreviewed from jsonb_array_elements(coalesce(rebuilt->'actions','[]'))x where x->>'primary_reason'='PRODUCTION_POLICY_UNREVIEWED';
 if ps.totals<>jsonb_build_object('targets',h.targets_total,'items',(select coalesce(jsonb_object_agg(x.key,x.value->'items'),'{}'::jsonb)from jsonb_each(h.paged)x),
   'recommendations',rec,'policy_unreviewed',unreviewed)
  or h.targets_total<>(select coalesce(sum(y.hi-y.lo+1),0)from cp7_analysis_stage.units y where y.job_id=j.id and y.kind='ANA_TARGETS')then bad:=bad||'totals'::text;end if;
 if single is not null then
  single_text:=single::text;without:=single-'semantic_hash';
  for k,v in select key,value from jsonb_each(h.paged)loop
   pref:=(v->>'prefix')::bigint;n:=(v->>'items')::bigint;
   select string_agg(x.e::text,', 'order by x.o)into full_text from jsonb_array_elements(single->k)with ordinality x(e,o)where x.o>pref and x.o<=pref+n;
   select string_agg(y.e::text,', 'order by q.idx,y.o)into items_text from cp7_analysis_stage.pages q
    cross join lateral jsonb_array_elements(q.body::jsonb->'items'->k)with ordinality y(e,o)where q.run_id=j.run_id;
   if full_text is distinct from items_text or jsonb_array_length(single->k)<>jsonb_array_length(hdr->'analysis_header'->k)+n then bad:=bad||('items:'||k);end if;
   without:=jsonb_set(without,array[k],(select coalesce(jsonb_agg(x.e order by x.o),'[]'::jsonb)from jsonb_array_elements(single->k)with ordinality x(e,o)where x.o<=pref or x.o>pref+n));
  end loop;
  if(hdr->'analysis_header')::text<>without::text then bad:=bad||'header_analysis'::text;end if;
  full_text:=(rebuilt||jsonb_build_object('semantic_hash',hash))::text;
 end if;
 return jsonb_build_object('state',j.state,'page_set',true,'bad',to_jsonb(bad),'pages',h.page_count,'targets',h.targets_total,'paged',h.paged,
  'header_bytes',h.utf8_bytes,'max_page_bytes',(select max(utf8_bytes)from cp7_analysis_stage.pages where run_id=j.run_id),
  'min_page_bytes',(select min(utf8_bytes)from cp7_analysis_stage.pages where run_id=j.run_id),'identity_hash',ps.identity_hash,
  'analysis_bytes',octet_length(full_text),'semantic_hash',hash,
  'same',case when single is not null then full_text::jsonb=single end,
  'text_same',case when single is not null then full_text=single_text end,
  'hash_same',case when single is not null then hash=single->>'semantic_hash'end,
  'document_same',case when single is not null then original_text=orig::text end);
end $s$;`

export async function installStagedControls(db, { bounds: b = null } = {}) {
  await installNettingControls(db)
  const analysis = read('scripts/cp7-src/planning/analysis.sql'), finance = read('scripts/cp7-src/planning/analysis-finance.sql'), jobs = read('scripts/cp7-src/planning/analysis-jobs.sql')
  const runs = analysis.slice(analysis.indexOf('create table cp7_analysis_native.runs('), analysis.indexOf('create function cp7_analysis_native.serve('))
  const jobTables = jobs.slice(jobs.indexOf('create schema cp7_analysis_jobs'), jobs.indexOf('-- The capture compiler'))
  await db.execute(`create schema cp7_private;
   create function cp7_private.immutable_run()returns trigger language plpgsql set search_path='' as $$
    begin raise exception using errcode='55000',message='CP7_RUN_IMMUTABLE';end $$;
   create schema cp7_analysis_native authorization cp7_capture;create schema cp7_fabric_native;create schema cp7_supply_native;
   grant usage on schema cp7_private,cp7_planning,cp7_schedule_native,cp7_netting_native,cp7_fabric_native,cp7_supply_native,extensions to cp7_capture;
   ${pick(analysis, 'cp7_analysis_native.fact', 'cp7_analysis_native.fingerprint')}
   ${pick(analysis, 'cp7_analysis_native.build').replace('create function cp7_analysis_native.build(', 'create function cp7_analysis_native.build_operational(')}
   ${pick(finance, 'cp7_analysis_native.finance_apply', 'cp7_analysis_native.finance_overlay')}
   ${[...functionBlocks(finance)].filter(([name]) => name === 'cp7_analysis_native.build').map(([, b]) => b).join('')}
   create function cp7_supply_native.fingerprint(c jsonb)returns text language sql immutable as $$select 'EXPLICIT_STAGED_KERNEL_ONLY'::text$$;
   create function cp7_fabric_native.plan(c jsonb,n jsonb)returns jsonb language sql immutable as $$
    select jsonb_build_object('stand_in','EXPLICIT_STAGED_KERNEL_ONLY','rows',jsonb_array_length(coalesce(n->'rows','[]')),
     'match_results',jsonb_array_length(coalesce(n->'match_results','[]')))$$;
   create function cp7_fabric_native.needs(c jsonb,r jsonb,a jsonb,p jsonb)returns jsonb language sql immutable as $$
    select case when r?'sql_null_fabric'then null else coalesce(r->'test_fabric','[]'::jsonb)end$$;
   create function cp7_analysis_native.material_needs(c jsonb,r jsonb,a jsonb)returns jsonb language sql immutable as $$
    select case when r?'sql_null_accessory'then null else coalesce(r->'test_accessory','[]'::jsonb)end$$;
   ${runs}
   ${jobTables}
   ${pick(jobs, 'cp7_analysis_jobs.original', 'cp7_analysis_jobs.store')}
   ${read(PRODUCT)}
   ${SCENARIO_STAND_IN}
   ${b ? bounds(b) : ''}
   ${VERIFY_SQL}
   create function public.st_single(c jsonb,q jsonb,p_run uuid,a jsonb)returns jsonb language plpgsql as $s$
   declare r jsonb;begin r:=cp7_analysis_native.build(c||'{}'::jsonb,q,p_run,a);
    return jsonb_build_object('state','DONE','sha256',encode(pg_catalog.sha256(convert_to(r::text,'UTF8')),'hex'),'bytes',octet_length(r::text),'body',r);
   exception when others then return jsonb_build_object('state','REFUSED','sqlstate',sqlstate,'code',sqlerrm);end $s$;
   create function public.st_netting(c jsonb,q jsonb)returns jsonb language plpgsql as $s$
   declare r jsonb;begin r:=cp7_netting_native.build(c||'{}'::jsonb,q);return r;exception when others then return null;end $s$;
   create function public.st_case(c jsonb,p_request uuid)returns jsonb language plpgsql as $s$
   declare job uuid;st jsonb;single jsonb;n jsonb;rid uuid;g jsonb;staged_rows jsonb;staged_matches jsonb;staged_alloc jsonb;ek jsonb;ver jsonb;
   begin
    job:=cp7_analysis_stage.create_job('${ACTOR}',p_request,'${JSON.stringify(QUERY)}'::jsonb,'${JSON.stringify(ACCESS)}'::jsonb,c);
    loop st:=cp7_analysis_stage.step(job);exit when st->>'state'<>'RUNNING';end loop;
    select run_id into rid from cp7_analysis_stage.jobs where id=job;
    single:=public.st_single(c,'${JSON.stringify(QUERY)}'::jsonb,rid,'${JSON.stringify(ACCESS)}'::jsonb);
    n:=public.st_netting(c,'${JSON.stringify(QUERY)}'::jsonb);
    ver:=public.sv_verify(job,case when single->>'state'='DONE'then single->'body'end);
    select coalesce(jsonb_agg(x.payload order by x.ord),'[]')into staged_rows from cp7_analysis_stage.target_rows x where x.job_id=job and x.kind='NETROW';
    g:=cp7_analysis_stage.output(job,'NET_PREP');
    select jsonb_agg(x->'key'order by o)into ek from jsonb_array_elements(g->'eligible')with ordinality e(x,o);
    select coalesce(jsonb_agg(jsonb_build_object('position_key',ek->(y.i-1),'target_key',g->'row_target_keys'->(q.o::integer-1),'result',q.v)order by y.i,q.o),'[]')
     into staged_matches from cp7_analysis_stage.pair_rows y cross join lateral jsonb_array_elements(y.pair_row)with ordinality q(v,o)where y.job_id=job;
    staged_alloc:=coalesce(nullif(cp7_analysis_stage.output(job,'ALLOC_FINAL'),'null'),nullif(cp7_analysis_stage.output(job,'NET_PLAN')->'alloc','null'),nullif(g->'alloc','null'));
    return ver||jsonb_build_object('job',st->>'state','failure',st->'failure',
     'failure_message',(select failure_message from cp7_analysis_stage.jobs where id=job),
     'single',single->>'state','single_sqlstate',single->>'sqlstate','single_code',single->>'code','bytes',ver->'analysis_bytes',
     'netting_rows_same',staged_rows::text=coalesce(n->'rows','[]')::text,
     'match_results_same',case when g->'wip_complete'='true'::jsonb then staged_matches::text=coalesce(n->'match_results','[]')::text else n->'match_results'is null end,
     'allocation_same',case when jsonb_typeof(staged_alloc)='object'and jsonb_typeof(n->'allocation')='object'then(staged_alloc-'inputs')::text=((n->'allocation')-'inputs')::text else false end,
     'allocation',n->'allocation'->>'status','edges',coalesce(jsonb_array_length(n->'allocation'->'allocation'->'edges'),0),
     'confirmed',coalesce(jsonb_array_length(jsonb_path_query_array(n,'$.match_results[*] ? (@.result.match == "CONFIRMED_TARGET")')),0),
     'recommendations',coalesce(jsonb_array_length(single->'body'->'recommendations'),0),'rows',jsonb_array_length(staged_rows),
     'units',(select jsonb_object_agg(k,v)from(select kind k,count(*)v from cp7_analysis_stage.units where job_id=job group by 1)u));
   end $s$;
   create function public.st_alloc(v jsonb,p_step integer)returns jsonb language plpgsql as $s$
   declare s0 jsonb;carry jsonb;o jsonb;edges jsonb:='[]';rows jsonb:='[]';reviews jsonb:='[]';r0 jsonb;r1 jsonb;
    s0s text:='NO_ERROR';s1s text:='NO_ERROR';n integer:=0;lo integer:=1;steps integer:=0;
   begin
    begin r0:=cp7_baseline.allocate(v);exception when others then s0s:=sqlstate||':'||sqlerrm;end;
    begin
     s0:=cp7_analysis_stage.alloc_prep(v,1000,100000);
     if s0?'result'then r1:=s0->'result';
     else
      carry:=s0->'carry';n:=jsonb_array_length(s0->'ordered');
      while lo<=n loop
       o:=cp7_analysis_stage.alloc_step(s0,carry,lo,least(n,lo+p_step-1),100000);steps:=steps+1;
       carry:=o->'carry';edges:=edges||(o->'edges');rows:=rows||(o->'rows');reviews:=reviews||(o->'reviews');lo:=lo+p_step;
      end loop;
      r1:=cp7_analysis_stage.alloc_final(v,carry,edges,rows,reviews);
     end if;
    exception when others then s1s:=sqlstate||':'||sqlerrm;end;
    return jsonb_build_object('s0',s0s,'s1',s1s,'same',r0::text is not distinct from r1::text,'status',r0->>'status','steps',steps,
     'edges',coalesce(jsonb_array_length(r0->'allocation'->'edges'),0));
   end $s$;`)
}
// stagedInput / STAGED_DEFECTS / runJob: unchanged from the committed fixture (copy them over when adopting this draft).
