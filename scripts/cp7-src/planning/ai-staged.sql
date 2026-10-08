-- AI v2 (owner decision 8 Oct 2026; docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md §6).
-- A bounded brief of ONE staged run of the actor for the "Tanya AI" handoff:
-- its identity and time ("data per"), the freshness now (changes since the
-- snapshot, last full check), the whole-run totals, the targets with the
-- largest open need (at most 25) and the targets the user selected (at most
-- 20), each from the retained per-target index (plan_targets) with the page
-- that holds it. The brief is analysis of the snapshot: it carries no finance
-- (a staged run has none); actual finance is read by the client from the
-- accepted owner finance report at the time of the question. Nothing is
-- written; no AI is called by the server.

-- One indexed target as the brief shows it (values exactly as the index holds them).
create function cp7_analysis_stage.ai_row(r jsonb,p_ord integer,p_page integer)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('ord',p_ord,'page_index',p_page,'target_key',r->'target_key',
  'sku',coalesce(r->'products'->0->'commercial'->0->'sku',r->'products'->0->'sku'),'product_name',r->'products'->0->'product_name',
  'production_state',r->'production_policy'->'policy'->'state','available_fg_pcs',r->'available_fg_pcs','target_pcs',r->'target'->'target_pcs',
  'raw_gap_pcs',r->'raw_gap_pcs','base_gap_pcs',r->'base_gap_pcs','conditional_gap_pcs',r->'conditional_gap_pcs',
  'directed_on_time_good_pcs',r->'directed_on_time_good_pcs','candidate_allocated_good_pcs',r->'candidate_allocated_good_pcs',
  'assumption_ids',(select coalesce(jsonb_agg(distinct x.v->>'id'),'[]'::jsonb)from jsonb_array_elements(
   coalesce(r->'assumptions','[]'::jsonb)||coalesce(r->'fabric_assumptions','[]'::jsonb))x(v)where jsonb_typeof(x.v)='object'and x.v->>'id'is not null))
$$;

create function cp7_analysis_stage.ai_brief(p_run uuid,p_targets jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs%rowtype;s cp7_analysis_stage.page_sets%rowtype;h cp7_analysis_stage.headers%rowtype;
 fresh jsonb;keys text[];missing text;priority jsonb;selected jsonb;counts jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if jsonb_typeof(p_targets)is distinct from 'array'or jsonb_array_length(p_targets)>20
  or exists(select 1 from jsonb_array_elements(p_targets)x(v)where jsonb_typeof(x.v)<>'string'
   or x.v#>>'{}'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
  or(select count(distinct x.v)from jsonb_array_elements(p_targets)x(v))<>jsonb_array_length(p_targets)then raise exception 'CP7_AI_V2_TARGETS';end if;
 select *into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 perform cp7_analysis_stage.require_kept(j.id);
 select *into s from cp7_analysis_stage.page_sets x where x.run_id=j.run_id;
 select *into h from cp7_analysis_stage.headers x where x.run_id=j.run_id;
 if j.id is null or s.run_id is null or h.run_id is null then raise exception using errcode='42501',message='CP7_AI_V2_SNAPSHOT_UNAVAILABLE';end if;
 if not exists(select 1 from cp7_analysis_stage.plan_scope x where x.job_id=j.id)then raise exception 'CP7_AI_V2_SNAPSHOT_INDEX_MISSING';end if;
 keys:=array(select x.v#>>'{}'from jsonb_array_elements(p_targets)x(v));
 select min(k)into missing from unnest(keys)k where not exists(select 1 from cp7_analysis_stage.plan_targets t where t.job_id=j.id and t.target_key=k);
 if missing is not null then raise exception 'CP7_AI_V2_TARGET';end if;
 fresh:=cp7_analysis_stage.freshness(p_run);
 with cuts as materialized(select(c.o-1)::integer idx,(c.v->>0)::integer lo,(c.v->>1)::integer hi from jsonb_array_elements(h.cuts)with ordinality c(v,o)),
 rows as materialized(select t.ord,t.target_key,t.row,c.idx,case when t.row->>'conditional_gap_pcs'~'^-?[0-9]+(\.[0-9]+)?$'then(t.row->>'conditional_gap_pcs')::numeric end gap
  from cp7_analysis_stage.plan_targets t join cuts c on t.ord between c.lo and c.hi where t.job_id=j.id),
 top as materialized(select *from rows r where r.gap>0 order by r.gap desc,r.ord limit 25)
 select(select coalesce(jsonb_agg(cp7_analysis_stage.ai_row(x.row,x.ord,x.idx)order by x.gap desc,x.ord),'[]'::jsonb)from top x),
  (select coalesce(jsonb_agg(cp7_analysis_stage.ai_row(x.row,x.ord,x.idx)order by x.ord),'[]'::jsonb)from rows x where x.target_key=any(keys)),
  (select jsonb_build_object('targets',count(*),'with_open_need',count(*)filter(where x.gap>0),'need_unknown',count(*)filter(where x.gap is null))from rows x)
  into priority,selected,counts;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-ai-brief-staged.v1','actor_scope_id',a->>'actor','run_id',j.run_id,'request_id',j.request_id,
  'identity_hash',s.identity_hash,'data_as_of',j.captured_at,'query',j.query,'targets_total',h.targets_total,'page_count',h.page_count,'totals',s.totals,
  'freshness',fresh,'need_counts',counts,'priority',priority,'selected',selected,'bounds',jsonb_build_object('priority',25,'selected',20),
  'finance','NOT_IN_SNAPSHOT','apply_enabled',false,'production_go',false);
end $$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_analysis_stage'and p.proname in('ai_row','ai_brief')loop
  execute format('alter function %s owner to cp7_capture',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
 end loop;
end $$;
grant create on schema public to cp7_capture;
create function public.erp_cp7_get_staged_ai_brief_v1(p_run uuid,p_targets jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.ai_brief(p_run,p_targets)$$;
alter function public.erp_cp7_get_staged_ai_brief_v1(uuid,jsonb)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_get_staged_ai_brief_v1(uuid,jsonb)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_staged_ai_brief_v1(uuid,jsonb)to authenticated;
