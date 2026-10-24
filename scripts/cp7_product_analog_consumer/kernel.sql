-- Private resolver for the existing demand/target kernels. No caller is
-- replaced here, no data is written, and no model is activated.
create schema cp7_product_analog_consumer authorization cp7_capture;
revoke all on schema cp7_product_analog_consumer from public,anon,authenticated,service_role;

create function cp7_product_analog_consumer.capture(c jsonb)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_product_analog_choice.source_at(coalesce(array_agg(
  (p->>'root_id')||':'||(p->>'size_id')order by p->>'root_id'),array[]::text[]),
  (c->>'captured_at')::timestamptz)from jsonb_array_elements(c->'facts'->'products')p
$$;

create function cp7_product_analog_consumer.refs(v jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare result jsonb;
begin
 select coalesce(jsonb_agg(x order by x::text collate"C"),'[]')into result
  from(select distinct value x from jsonb_array_elements(v))items;
 perform cp7_wip.refs(result);
 return result;
end $$;

create function cp7_product_analog_consumer.prepare(c jsonb,h jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare products jsonb;histories jsonb;choices jsonb;at timestamptz;lo date;hi date;
 count_products integer;row_value jsonb;k text;selected jsonb:=c->'product_analog_choices';
begin
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 at:=cp7_demand.instant(c->'captured_at');lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(at at time zone'Asia/Jakarta')::date
  or q->>'group_mode'is null or q->>'group_mode'not in('AS_SOLD','RESTATED')then raise exception 'CP7_ANALOG_CONSUMER_QUERY';end if;
 if jsonb_typeof(c->'facts'->'products')is distinct from'array'or jsonb_typeof(h)is distinct from'array'
  or jsonb_typeof(selected)is distinct from'array'then raise exception 'CP7_ANALOG_CONSUMER_CAPTURE_REQUIRED';end if;
 count_products:=jsonb_array_length(c->'facts'->'products');
 if count_products>5000 or jsonb_array_length(h)<>count_products or jsonb_array_length(selected)<>count_products then
  raise exception 'CP7_ANALOG_CONSUMER_ALL_HISTORY_REQUIRED';end if;
 select coalesce(jsonb_object_agg((p->>'root_id')||':'||(p->>'size_id'),p),'{}')into products from jsonb_array_elements(c->'facts'->'products')p;
 select coalesce(jsonb_object_agg(p->>'target_key',p),'{}')into histories from jsonb_array_elements(h)p;
 select coalesce(jsonb_object_agg(p->>'target_key',p),'{}')into choices from jsonb_array_elements(selected)p;
 if(select count(*)from jsonb_each(products))<>count_products or(select count(*)from jsonb_each(histories))<>count_products
  or(select count(*)from jsonb_each(choices))<>count_products then raise exception 'CP7_ANALOG_CONSUMER_DUPLICATE';end if;
 for k in select key from jsonb_each(products)loop
  perform cp7_wip.key(to_jsonb(k));
  if not(histories?k)or not(choices?k)or histories->k->'size_id'is distinct from products->k->'size_id'then
   raise exception 'CP7_ANALOG_CONSUMER_SCOPE';end if;
  row_value:=choices->k;
  perform cp7_wip.fields(row_value,array['target_key','choice_id','revision','action','evidence','reason','actor_scope_id','recorded_at','request_id','state']);
  if row_value->>'state'='UNREVIEWED'then
   if row_value->>'revision'is distinct from'0'or exists(select 1 from jsonb_each(row_value)where key not in('target_key','revision','state')and value<>'null'::jsonb)then
    raise exception 'CP7_ANALOG_CONSUMER_UNREVIEWED';end if;
  elsif row_value->>'state'in('CONFIRMED_ASSUMPTION','CLEARED')then
   if cp7_wip.pcs(row_value->'revision')<1 or cp7_demand.instant(to_jsonb(regexp_replace(row_value->>'recorded_at','\+00:00$','Z')))>at
    or row_value->>'action'is distinct from (case when row_value->>'state'='CLEARED'then'CLEAR'else'CONFIRM'end)
    or(row_value->>'state'='CLEARED'and row_value->'evidence'is distinct from'null'::jsonb)then raise exception 'CP7_ANALOG_CONSUMER_RECORDED_CHOICE';end if;
   perform cp7_wip.key(row_value->'choice_id')::uuid;perform cp7_wip.key(row_value->'actor_scope_id')::uuid;perform cp7_wip.key(row_value->'request_id')::uuid;
   if jsonb_typeof(row_value->'reason')is distinct from'string'or length(btrim(row_value->>'reason'))not between 1 and 1000 then raise exception 'CP7_ANALOG_CONSUMER_REASON';end if;
  else raise exception 'CP7_ANALOG_CONSUMER_CHOICE_STATE';end if;
 end loop;
 return jsonb_build_object('contract_version','cp7.analog-consumer-context.v1','captured_at',c->'captured_at',
  'query',q,'products',products,'histories',histories,'choices',choices);
end $$;

create function cp7_product_analog_consumer.resolve(v jsonb,p_target text,p_profile jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare choice jsonb;evidence jsonb;target_product jsonb;source_product jsonb;history jsonb;outcome jsonb;
 reason text;source text;minimum numeric;scale numeric;days numeric;total numeric;sd numeric;count_days integer;refs jsonb;
begin
 if v->>'contract_version'is distinct from'cp7.analog-consumer-context.v1'then raise exception 'CP7_ANALOG_CONSUMER_CONTEXT';end if;
 perform cp7_wip.key(to_jsonb(p_target));
 choice:=v->'choices'->p_target;target_product:=v->'products'->p_target;
 if choice is null or target_product is null then raise exception 'CP7_ANALOG_CONSUMER_TARGET';end if;
 outcome:=jsonb_build_object('contract_version','cp7.analog-demand-resolution.v1','state','UNAVAILABLE',
  'choice_id',choice->'choice_id','choice_revision',choice->'revision','reason',null,'analog',null,
  'scaled_total_pcs',null,'available_days',null,'scaled_daily_sd',null,'refs','[]'::jsonb);
 if choice->>'state'='UNREVIEWED'then reason:='NO_REVIEWED_ANALOG_CHOICE';
 elsif choice->>'state'='CLEARED'then reason:='ANALOG_CHOICE_CLEARED';
 elsif p_profile->>'quality'is distinct from'SELECTED_ASSUMPTION'then reason:='ANALOG_PROFILE_UNREVIEWED';
 end if;
 if reason is not null then return outcome||jsonb_build_object('reason',reason);end if;
 evidence:=choice->'evidence';source:=evidence->>'source_key';
 if evidence->>'contract_version'is distinct from'cp7.product-analog-material.v1'or evidence->>'target_key'is distinct from p_target
  or evidence->'reviewed'is distinct from'true'::jsonb or source is null or source=p_target then raise exception 'CP7_ANALOG_CONSUMER_EVIDENCE';end if;
 if evidence->'profile_id'is distinct from p_profile->'profile_id'or evidence->'profile_revision'is distinct from p_profile->'revision'
  or evidence->'minimum_available_days'is distinct from p_profile->'config'->'minimum_available_days'
  or p_profile->'root_id'is distinct from target_product->'root_id'or p_profile->'product_version_id'is distinct from target_product->'id'then
  return outcome||jsonb_build_object('reason','ANALOG_PROFILE_CHANGED');end if;
 source_product:=v->'products'->source;
 if source_product is null then return outcome||jsonb_build_object('reason','ANALOG_SOURCE_UNAVAILABLE');end if;
 if evidence->'target_product'is distinct from target_product or evidence->'source_product'is distinct from source_product
  or target_product->'size_id'is distinct from source_product->'size_id'then
  return outcome||jsonb_build_object('reason','ANALOG_PRODUCT_IDENTITY_CHANGED');end if;
 minimum:=cp7_wip.pcs(p_profile->'config'->'minimum_available_days');scale:=cp7_demand.decimal(evidence->'scale_factor');
 if minimum<1 or scale<=0 then raise exception 'CP7_ANALOG_CONSUMER_ASSUMPTION';end if;
 history:=v->'histories'->source;
 if history is null or history->'size_id'is distinct from source_product->'size_id'or jsonb_typeof(history->'days')is distinct from'array'then
  raise exception 'CP7_ANALOG_CONSUMER_SOURCE_HISTORY';end if;
 count_days:=cp7_demand.day(v->'query'->'through_date')-cp7_demand.day(v->'query'->'from_date')+1;
 if jsonb_array_length(history->'days')<>count_days or exists(
  select 1 from jsonb_array_elements(history->'days')with ordinality d(day,ord)
  where cp7_demand.day(day->'date')<>cp7_demand.day(v->'query'->'from_date')+(ord::integer-1)
   or day->>'state'is null or day->>'state'not in('AVAILABLE','STOCKOUT','UNKNOWN'))then raise exception 'CP7_ANALOG_CONSUMER_HISTORY_DAYS';end if;
 select count(*),coalesce(sum(cp7_wip.pcs(day->'gross_observed_pcs')),0),stddev_samp(cp7_wip.pcs(day->'gross_observed_pcs'))
  into days,total,sd from jsonb_array_elements(history->'days')day where day->>'state'='AVAILABLE';
 if days<>cp7_wip.pcs(to_jsonb(history->>'available_days'))then raise exception 'CP7_ANALOG_CONSUMER_HISTORY_COUNT';end if;
 if days<minimum then return outcome||jsonb_build_object('reason','ANALOG_CURRENT_HISTORY_INSUFFICIENT');end if;
 -- Preserve the existing target kernel's counted-day bound.
 if days>3660 then raise exception 'CP7_BASELINE_COUNTED_DAYS';end if;
 refs:=cp7_product_analog_consumer.refs(history->'refs'||jsonb_build_array(jsonb_build_object(
  'kind','ANALOG_CHOICE','id',choice->'choice_id','revision',choice->'revision')));
 return outcome||jsonb_build_object('state','READY','reason','EXPLICIT_REVIEWED_ANALOG_CURRENT_QUERY_HISTORY',
  'analog',jsonb_build_object('source_key',source,'source_size_id',source_product->'size_id',
   'available_total_pcs',total::text,'available_days',days::text,'scale_factor',scale::text,
   'reason','REVIEWED_CHOICE:'||(choice->>'choice_id'),'reviewed',true,'refs',refs),
  'review_reason',choice->'reason','scaled_total_pcs',(total*scale)::text,'available_days',days::text,
  'scaled_daily_sd',(sd*scale)::text,'refs',refs);
end $$;

alter function cp7_product_analog_consumer.capture(jsonb)owner to cp7_capture;
alter function cp7_product_analog_consumer.refs(jsonb)owner to cp7_capture;
alter function cp7_product_analog_consumer.prepare(jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_product_analog_consumer.resolve(jsonb,text,jsonb)owner to cp7_capture;
revoke all on all functions in schema cp7_product_analog_consumer from public,anon,authenticated,service_role;
