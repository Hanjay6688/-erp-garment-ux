create or replace function cp7_baseline_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_baseline_native.runs%rowtype;c jsonb;hash text;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();select *into r from cp7_baseline_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_BASELINE_RUN_UNAVAILABLE';end if;
 c:=cp7_baseline_native.source();hash:=encode(extensions.digest(convert_to(jsonb_build_object('native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex');
 outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,'source_state',
  case when c->>'status'='COMPLETE'and hash=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_BASELINE_ACCESS_CHANGED';end if;
 return outcome;
end $$;
