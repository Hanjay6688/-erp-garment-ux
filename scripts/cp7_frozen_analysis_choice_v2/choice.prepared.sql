create schema cp7_frozen_analysis_choice_v2 authorization cp7_capture;
revoke all on schema cp7_frozen_analysis_choice_v2 from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_choice_v2.review_context(p_request uuid,p_target text,p_offset integer,p_limit integer,p_access text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;jid uuid;j cp7_analysis_stage.jobs%rowtype;sealed jsonb;candidates jsonb;producer text;c jsonb;reviewed jsonb;
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
 if j.reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or j.reference->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v2'then
  raise exception 'CP7_PRODUCT_ANALOG_BOUNDED_REQUIRED';end if;
 if j.query is distinct from j.reference->'bounded_query'
  or (j.reference->>'captured_at')::timestamptz is distinct from j.captured_at
  or (sealed#>>'{reference,captured_at}')::timestamptz is distinct from j.captured_at
  or sealed#>>'{reference,source_hash}'is distinct from j.source_hash then
  raise exception 'CP7_PRODUCT_ANALOG_REFERENCE_CHANGED';end if;
 c:=cp7_frozen_analysis_readers_v2.reference(j);
 candidates:=cp7_product_analog_stage.candidates(c,p_target,p_offset,p_limit);
 producer:=cp7_frozen_analysis_units_v2.producer_hash();
 if producer is distinct from j.reference->>'bounded_producer_hash'then
  raise exception using errcode='40001',message='CP7_PRODUCT_ANALOG_PRODUCER_CHANGED';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 reviewed:=jsonb_build_object('contract_version','cp7.product-analog-candidates-read.v3',
  'bounded_request_contract',c->'bounded_request_contract','bounded_reference_contract',c->'bounded_reference_contract',
  'actor_scope_id',a->'actor','request_id',p_request,'run_id',j.run_id,'query',j.query,
  'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),
  'identity_hash',sealed->'identity_hash','access_epoch',p_access,'producer_hash',producer,
  'source_state','CAPTURED_NOT_CHECKED','captured_source_only',true,
  'consumer_capability','REVIEWED_ANALOG_FOR_FRESH_CAPTURES',
  'target_demand',(select x->'demand_provenance'from jsonb_array_elements(c#>'{bounded_history_inputs,inputs,targets}')x where x->>'target_key'=p_target),
  'result',candidates,'selected',false,'reviewed',false,'forecast_applied',false,'production_go',false);
 return jsonb_build_object('reviewed',reviewed,'reference',c);
end $$;
alter function cp7_frozen_analysis_choice_v2.review_context(uuid,text,integer,integer,text)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_choice_v2.review_context(uuid,text,integer,integer,text)from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_choice_v2.material(c jsonb,p_target text,p_source text,p_envelope jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare prepared jsonb;envelope jsonb;target_product jsonb;source_product jsonb;history_row jsonb;
 n integer;days numeric;total numeric;minimum numeric;
begin
 prepared:=cp7_bounded_analysis_stage.require_inputs(c,c->'bounded_query');
 -- Reuse the advisory's target/profile validation and explicit minimum.
 envelope:=p_envelope;
 if envelope->>'state'='PLANNING_CONFIG_REQUIRED'then raise exception 'CP7_ANALOG_CHOICE_PROFILE_REQUIRED';end if;
 minimum:=cp7_wip.pcs(envelope->'minimum_available_days');
 perform cp7_wip.key(to_jsonb(p_source));
 if p_source=p_target then raise exception 'CP7_ANALOG_CHOICE_SELF';end if;
 select count(*),(jsonb_agg(p))->0 into n,source_product from jsonb_array_elements(c->'facts'->'products')p
  where(p->>'root_id')||':'||(p->>'size_id')=p_source;
 if n<>1 then raise exception 'CP7_ANALOG_CHOICE_SOURCE';end if;
 select p into target_product from jsonb_array_elements(c->'facts'->'products')p
  where(p->>'root_id')||':'||(p->>'size_id')=p_target;
 if source_product->'size_id'is distinct from target_product->'size_id'then raise exception 'CP7_ANALOG_CHOICE_SIZE';end if;
 select count(*),(jsonb_agg(h))->0 into n,history_row from jsonb_array_elements(prepared->'history')h
  where h->>'target_key'=p_source;
 if n<>1 then raise exception 'CP7_ANALOG_CHOICE_HISTORY';end if;
 days:=cp7_wip.pcs(to_jsonb(history_row->>'available_days'));
 if days<minimum or history_row->>'available_sales_mean'is null then raise exception 'CP7_ANALOG_CHOICE_INSUFFICIENT';end if;
 select count(*),coalesce(sum(cp7_wip.pcs(d->'gross_observed_pcs')),0)into n,total
  from jsonb_array_elements(history_row->'days')d where d->>'state'='AVAILABLE';
 if n<>days then raise exception 'CP7_ANALOG_CHOICE_AVAILABLE_COUNT';end if;
 -- The exact integer numerator comes from AVAILABLE day facts, never mean*days.
 return jsonb_build_object('contract_version','cp7.product-analog-material.v1',
  'target_key',p_target,'source_key',p_source,'target_product',target_product,'source_product',source_product,
  'profile_id',envelope->'profile_id','profile_revision',envelope->'profile_revision',
  'minimum_available_days',minimum::text,'available_total_pcs',total::text,'available_days',days::text,
  'history_hash',prepared->'history_hash','source_hash',prepared->'source_hash',
  'captured_at',c->'captured_at','query',c->'bounded_query','refs',history_row->'refs');
end $$;
alter function cp7_frozen_analysis_choice_v2.material(jsonb,text,text,jsonb)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_choice_v2.material(jsonb,text,text,jsonb)from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_choice_v2.normalize_confirmed_delta(before_source jsonb,after_source jsonb,receipt jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare before_choices jsonb:=before_source->'product_analog_choices';after_choices jsonb:=after_source->'product_analog_choices';
 expected_choices jsonb;previous_choice jsonb;target text;expected_choice jsonb;
begin
 if jsonb_typeof(before_choices)is distinct from'array'or jsonb_typeof(after_choices)is distinct from'array'
  or receipt->>'contract_version'is distinct from'cp7.product-analog-choice-outcome.v2'
  or receipt->>'action'is distinct from'CONFIRM'or receipt->>'state'is distinct from'CONFIRMED_ASSUMPTION'
  or receipt->'forecast_applied'is distinct from'false'::jsonb or receipt->'production_go'is distinct from'false'::jsonb then
  raise exception 'CP7_ANALOG_CONSUMER_OWN_DELTA_SHAPE';end if;
 target:=cp7_wip.key(receipt->'target_key');
 if jsonb_array_length(before_choices)<>(select count(distinct x->>'target_key')from jsonb_array_elements(before_choices)x)
  or(select count(*)from jsonb_array_elements(before_choices)x where x->>'target_key'=target)<>1 then
  raise exception 'CP7_ANALOG_CONSUMER_OWN_DELTA_SCOPE';end if;
 select x into previous_choice from jsonb_array_elements(before_choices)x where x->>'target_key'=target;
 if cp7_wip.pcs(receipt->'revision')<>cp7_wip.pcs(previous_choice->'revision')+1 then
  raise exception 'CP7_ANALOG_CONSUMER_OWN_DELTA_REVISION';end if;
 expected_choice:=receipt-'contract_version'-'forecast_applied'-'production_go';
 perform cp7_wip.fields(expected_choice,array['target_key','choice_id','revision','action','evidence','reason','actor_scope_id','recorded_at','request_id','state']);
 select jsonb_agg(case when x->>'target_key'=target then expected_choice else x end order by ord)
  into expected_choices from jsonb_array_elements(before_choices)with ordinality items(x,ord);
 if after_choices is distinct from expected_choices then
  raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_UNEXPECTED_CHOICE_DELTA';end if;
 return after_source||jsonb_build_object('product_analog_choices',before_choices);
end $$;
alter function cp7_frozen_analysis_choice_v2.normalize_confirmed_delta(jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_choice_v2.normalize_confirmed_delta(jsonb,jsonb,jsonb)from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_choice_v2.apply(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_product_analog_choice.commands%rowtype;saved cp7_product_analog_choice.choices%rowtype;
 j cp7_analysis_stage.jobs%rowtype;target text;action text;reason text;expected bigint;rev bigint;
 reviewed jsonb;review_context jsonb;material jsonb;current_source jsonb;outcome jsonb;scale numeric;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);
 if p_request is null then raise exception 'CP7_ANALOG_CHOICE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['contract_version','source_request','source_hash','access_epoch',
  'target_key','source_key','scale_factor','reason','reviewed','expected_revision','action']);
 if p_payload->>'contract_version'is distinct from'cp7.product-analog-choice-command.v2' then raise exception 'CP7_ANALOG_CHOICE_CONTRACT';end if;
 -- Take the Native envelope before either metadata lock; recheck access after waits.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALOG:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select *into old from cp7_product_analog_choice.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_ANALOG_CHOICE_REQUEST_CHANGED';end if;
  return old.result;
 end if;
 if p_payload->>'access_epoch'is distinct from encode(pg_catalog.sha256(convert_to(cp7_schedule_native.access_now(false)::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 target:=cp7_wip.key(p_payload->'target_key');action:=p_payload->>'action';reason:=btrim(p_payload->>'reason');
 if action is null or action not in('CONFIRM','CLEAR')or p_payload->'reviewed'is distinct from'true'::jsonb
  or jsonb_typeof(p_payload->'reason')is distinct from'string'or reason is null or length(reason)not between 1 and 1000
  or jsonb_typeof(p_payload->'expected_revision')is distinct from'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'then raise exception 'CP7_ANALOG_CHOICE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALOG:TARGET:'||target,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into rev from cp7_product_analog_choice.choices x where x.target_key=target;
 if expected<>rev then raise exception 'CP7_ANALOG_CHOICE_REVISION_CHANGED';end if;
 if action='CONFIRM'then
  scale:=cp7_demand.decimal(p_payload->'scale_factor');
  if scale<=0 then raise exception 'CP7_ANALOG_CHOICE_SCALE';end if;
  review_context:=cp7_frozen_analysis_choice_v2.review_context((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');
  reviewed:=review_context->'reviewed';
  if reviewed#>>'{reference,source_hash}'is distinct from p_payload->>'source_hash'then raise exception 'CP7_ANALOG_CHOICE_REFERENCE_CHANGED';end if;
  select *into j from cp7_analysis_stage.jobs where run_id=(reviewed->>'run_id')::uuid;
  current_source:=cp7_bounded_analysis_stage.source_for(j.reference,j.query);
  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then
   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
  material:=cp7_frozen_analysis_choice_v2.material(review_context->'reference',target,p_payload->>'source_key',reviewed->'result')||jsonb_build_object(
   'source_request',p_payload->'source_request','source_run',j.run_id,'analysis_source_hash',j.source_hash,
   'identity_hash',reviewed->'identity_hash','producer_hash',reviewed->'producer_hash',
   'scale_factor',scale::text,'reviewed',true);
 else
  if rev=0 then raise exception 'CP7_ANALOG_CHOICE_NOT_SELECTED';end if;
  if p_payload->'source_request'is distinct from'null'::jsonb or p_payload->'source_hash'is distinct from'null'::jsonb
   or p_payload->'source_key'is distinct from'null'::jsonb or p_payload->'scale_factor'is distinct from'null'::jsonb then
   raise exception 'CP7_ANALOG_CHOICE_CLEAR_FIELDS';end if;
  material:='null'::jsonb;
 end if;
 insert into cp7_product_analog_choice.choices(target_key,revision,action,evidence,reason,actor,request_id)
 values(target,rev+1,action,material,reason,(a->>'actor')::uuid,p_request)returning *into saved;
 outcome:=jsonb_build_object('contract_version','cp7.product-analog-choice-outcome.v2','choice_id',saved.id,
  'target_key',target,'revision',saved.revision::text,'action',action,'request_id',p_request,
  'recorded_at',saved.recorded_at,'evidence',material,'reason',reason,'actor_scope_id',a->'actor',
  'state',case when action='CLEAR'then'CLEARED'else'CONFIRMED_ASSUMPTION'end,
  'forecast_applied',false,'production_go',false);
 insert into cp7_product_analog_choice.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if action='CONFIRM'then
  current_source:=cp7_frozen_analysis_choice_v2.normalize_confirmed_delta(j.reference,cp7_bounded_analysis_stage.source_for(j.reference,j.query),outcome);
  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then
   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
 end if;
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return outcome;
end $$;
alter function cp7_frozen_analysis_choice_v2.apply(jsonb,uuid)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_choice_v2.apply(jsonb,uuid)from public,anon,authenticated,service_role;

create function public.erp_cp7_save_product_analog_choice_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_frozen_analysis_choice_v2.apply(p_payload,p_request)
$$;
alter function public.erp_cp7_save_product_analog_choice_v2(jsonb,uuid)owner to cp7_capture;
revoke all on function public.erp_cp7_save_product_analog_choice_v2(jsonb,uuid)from public,anon,authenticated,service_role,postgres;
grant execute on function public.erp_cp7_save_product_analog_choice_v2(jsonb,uuid)to authenticated;
