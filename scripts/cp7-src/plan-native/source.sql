-- Private capability into one currently authorized, immutable own Original.
-- Its owner remains the read-only analysis principal, without any writer grant.
create function cp7_plan_native.analysis_source(p_run uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r cp7_analysis_native.runs%rowtype;a jsonb;e jsonb;n jsonb;
begin
 a:=cp7_private.access_now();select *into r from cp7_analysis_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_ORIGINAL_UNAVAILABLE';end if;
 if a is distinct from r.access_at_capture then raise exception using errcode='42501',message='CP7_PLAN_ORIGINAL_ACCESS_CHANGED';end if;
 e:=cp7_analysis_native.serve(p_run);
 if e->>'source_state'<>'UNCHANGED'or r.result->'snapshot'->'capture_complete'<>'true'::jsonb then raise exception using errcode='40001',message='CP7_PLAN_SOURCE_CHANGED';end if;
 n:=cp7_netting_native.build(r.facts,r.query);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ORIGINAL_ACCESS_CHANGED';end if;
 return jsonb_build_object('run_id',r.id,'source_hash',r.dependency_hash,'core_hash',cp7_netting_native.fingerprint(r.facts),
  'captured_at',r.captured_at,'analysis',r.result,'netting',n,'products',r.facts->'facts'->'products');
end $$;
