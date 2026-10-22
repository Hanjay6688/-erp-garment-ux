-- OW-12a (owner D17-16: "pembanding periode … tetap dikerjakan"): two published staged reports of the actor compared
-- metric by metric, after minus before, with the rules of the v1 comparison (cp7_analysis_native.report_compare): the
-- official finance metrics (finance_apply over each report's own stored finance), matched by metric id and unit, and a
-- difference only when both values are known. Each side is read through report_document, so another actor's report or
-- finance the actor may no longer see is refused exactly as when opening it. Nothing is recomputed from current data.
create function cp7_analysis_stage.report_compare(p_before uuid,p_after uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;l jsonb;r jsonb;fl jsonb;fr jsonb;ml jsonb:='{}';mr jsonb:='{}';k text;rows jsonb:='[]';x jsonb;y jsonb;diff jsonb;
 empty jsonb:=jsonb_build_object('metrics','[]'::jsonb,'financial_readiness',null,'quality','{}'::jsonb,'snapshot',jsonb_build_object('fact_count',0),
  'dependencies','[]'::jsonb,'generation_warnings','[]'::jsonb);
begin
 if p_before is null or p_after is null or p_before=p_after then raise exception 'CP7_REPORT_COMPARE_PAIR';end if;
 a:=cp7_schedule_native.access_now(false);
 l:=cp7_analysis_stage.report_document(p_before);r:=cp7_analysis_stage.report_document(p_after);
 select x.body->'finance'into fl from cp7_analysis_stage.report_reads x join cp7_analysis_stage.report_publications p on p.job_id=x.job_id
  where p.id=p_before and x.kind='ACTUALS';
 select x.body->'finance'into fr from cp7_analysis_stage.report_reads x join cp7_analysis_stage.report_publications p on p.job_id=x.job_id
  where p.id=p_after and x.kind='ACTUALS';
 if coalesce(fl,'null'::jsonb)<>'null'::jsonb then
  select coalesce(jsonb_object_agg(m->>'metric_id',m),'{}'::jsonb)into ml
  from jsonb_array_elements(cp7_analysis_native.finance_apply(empty,jsonb_build_object('financial_source',fl))->'metrics')m;
 end if;
 if coalesce(fr,'null'::jsonb)<>'null'::jsonb then
  select coalesce(jsonb_object_agg(m->>'metric_id',m),'{}'::jsonb)into mr
  from jsonb_array_elements(cp7_analysis_native.finance_apply(empty,jsonb_build_object('financial_source',fr))->'metrics')m;
 end if;
 for k in select s.key from(select jsonb_object_keys(ml)key union select jsonb_object_keys(mr))s order by s.key collate "C" loop
  x:=ml->k;y:=mr->k;
  diff:=jsonb_build_object('state','UNKNOWN','unit','IDR','reason',case when x is null or y is null then 'FINANCE_NOT_IN_BOTH_REPORTS'
   when x->'value'->>'unit'is distinct from y->'value'->>'unit'then 'METRIC_SCOPE_NOT_COMPARABLE'else 'ONE_OR_BOTH_VALUES_UNKNOWN'end);
  if x is not null and y is not null and x->'value'->>'unit'=y->'value'->>'unit'and x->'value'->>'state'in('KNOWN','ASSUMED')
   and y->'value'->>'state'in('KNOWN','ASSUMED')and x->'value'->>'value'is not null and y->'value'->>'value'is not null then
   diff:=jsonb_build_object('state',case when x->'value'->>'state'='ASSUMED'or y->'value'->>'state'='ASSUMED'then 'ASSUMED'else 'KNOWN'end,
    'unit',y->'value'->>'unit','value',((y->'value'->>'value')::numeric-(x->'value'->>'value')::numeric)::text);
  end if;
  rows:=rows||jsonb_build_array(jsonb_build_object('metric_id',k,'before',x,'after',y,'difference',diff));
 end loop;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-comparison.v2','actor_scope_id',a->>'actor','before',l-'summary','after',r-'summary',
  'rows',rows,'comparison_basis','AFTER_MINUS_BEFORE_OFFICIAL_FINANCE_METRICS_MATCHED_ID_UNIT','production_go',false);
end $$;
alter function cp7_analysis_stage.report_compare(uuid,uuid)owner to cp7_capture;
revoke all on function cp7_analysis_stage.report_compare(uuid,uuid)from public,anon,authenticated,service_role;

create function public.erp_cp7_compare_reports_v2(p_before uuid,p_after uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_compare(p_before,p_after)$$;
do $$begin
 if has_schema_privilege('cp7_capture','public','CREATE')then
  alter function public.erp_cp7_compare_reports_v2(uuid,uuid)owner to cp7_capture;
 else
  grant create on schema public to cp7_capture;
  alter function public.erp_cp7_compare_reports_v2(uuid,uuid)owner to cp7_capture;
  revoke create on schema public from cp7_capture;
 end if;
end $$;
revoke all on function public.erp_cp7_compare_reports_v2(uuid,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_compare_reports_v2(uuid,uuid)to authenticated;
