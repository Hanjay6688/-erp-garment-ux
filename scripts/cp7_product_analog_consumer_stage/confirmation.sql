-- The second full-source check may normalize exactly its own new choice.
-- Every other choice and every other source field remains part of freshness.
create function cp7_product_analog_consumer.normalize_confirmed_delta(before_source jsonb,after_source jsonb,receipt jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare before_choices jsonb:=before_source->'product_analog_choices';after_choices jsonb:=after_source->'product_analog_choices';
 expected_choices jsonb;previous_choice jsonb;target text;expected_choice jsonb;
begin
 if jsonb_typeof(before_choices)is distinct from'array'or jsonb_typeof(after_choices)is distinct from'array'
  or receipt->>'contract_version'is distinct from'cp7.product-analog-choice-outcome.v1'
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
alter function cp7_product_analog_consumer.normalize_confirmed_delta(jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_product_analog_consumer.normalize_confirmed_delta(jsonb,jsonb,jsonb)from public,anon,authenticated,service_role;

create function cp7_product_analog_consumer.engine_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in('cp7_product_analog_consumer','cp7_product_analog_choice')and p.prokind='f'
$$;
alter function cp7_product_analog_consumer.engine_hash()owner to cp7_capture;
revoke all on function cp7_product_analog_consumer.engine_hash()from public,anon,authenticated,service_role;
