create schema cp7_frozen_analysis_choice_v2 authorization cp7_capture;
revoke all on schema cp7_frozen_analysis_choice_v2 from public,anon,authenticated,service_role;

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
 reviewed jsonb;material jsonb;current_source jsonb;outcome jsonb;scale numeric;
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
  reviewed:=cp7_frozen_analysis_readers_v2.read_candidates((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');
  if reviewed#>>'{reference,source_hash}'is distinct from p_payload->>'source_hash'then raise exception 'CP7_ANALOG_CHOICE_REFERENCE_CHANGED';end if;
  select *into j from cp7_analysis_stage.jobs where run_id=(reviewed->>'run_id')::uuid;
  current_source:=cp7_bounded_analysis_stage.source_for(j.reference,j.query);
  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then
   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
  material:=cp7_product_analog_choice.material(cp7_frozen_analysis_readers_v2.reference(j),target,p_payload->>'source_key')||jsonb_build_object(
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
