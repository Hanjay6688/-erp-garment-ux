-- Advisory read from the actor's retained, sealed Native DONE snapshot.
-- No source-current claim, configuration selection or production write.
create function cp7_product_analog_stage.read_candidates(p_request uuid,p_target text,p_offset integer,p_limit integer,p_access text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;jid uuid;j cp7_analysis_stage.jobs%rowtype;sealed jsonb;candidates jsonb;producer text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_access is distinct from encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 select *into j from cp7_analysis_stage.jobs where id=jid;
 if j.id is null or j.state is distinct from'DONE'then
  raise exception using errcode='42501',message='CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE';end if;
 sealed:=cp7_analysis_stage.page_set(j.run_id);
 if sealed->>'access_epoch'is distinct from p_access or sealed->>'request_id'is distinct from p_request::text
  or sealed->>'run_id'is distinct from j.run_id::text then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 if j.reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
  or j.reference->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v1'then
  raise exception 'CP7_PRODUCT_ANALOG_BOUNDED_REQUIRED';end if;
 if j.query is distinct from j.reference->'bounded_query'
  or (j.reference->>'captured_at')::timestamptz is distinct from j.captured_at
  or (sealed#>>'{reference,captured_at}')::timestamptz is distinct from j.captured_at
  or sealed#>>'{reference,source_hash}'is distinct from j.source_hash then
  raise exception 'CP7_PRODUCT_ANALOG_REFERENCE_CHANGED';end if;
 candidates:=cp7_product_analog_stage.candidates(j.reference,p_target,p_offset,p_limit);
 producer:=cp7_bounded_analysis_stage.producer_hash();
 if producer is distinct from j.reference->>'bounded_producer_hash'then
  raise exception using errcode='40001',message='CP7_PRODUCT_ANALOG_PRODUCER_CHANGED';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.product-analog-candidates-read.v1',
  'actor_scope_id',a->'actor','request_id',p_request,'run_id',j.run_id,'query',j.query,
  'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),
  'identity_hash',sealed->'identity_hash','access_epoch',p_access,'producer_hash',producer,
  'source_state','CAPTURED_NOT_CHECKED','captured_source_only',true,
  'result',candidates,'selected',false,'reviewed',false,'forecast_applied',false,'production_go',false);
end $$;
alter function cp7_product_analog_stage.read_candidates(uuid,text,integer,integer,text)owner to cp7_capture;
revoke all on function cp7_product_analog_stage.read_candidates(uuid,text,integer,integer,text)from public,anon,authenticated,service_role;

create function public.erp_cp7_read_product_analog_candidates_v1(p_request uuid,p_target text,p_offset integer,p_limit integer,p_access text)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_product_analog_stage.read_candidates(p_request,p_target,p_offset,p_limit,p_access)
$$;
grant create on schema public to cp7_capture;
alter function public.erp_cp7_read_product_analog_candidates_v1(uuid,text,integer,integer,text)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_read_product_analog_candidates_v1(uuid,text,integer,integer,text)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_read_product_analog_candidates_v1(uuid,text,integer,integer,text)to authenticated;
