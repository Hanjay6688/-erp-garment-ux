-- Bounded source inverse after every outgoing consumer has its exact named
-- full undo. Retain the entire signed history and all joint-cut capacity tests.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

-- The qualified source coordinator already owns the FG lock and source graph.
-- This factual helper acquires no later lock or authority of its own. Incoming
-- applications need a separate historical Native source-vector adapter.
create function cp7_credit.consumer_source_undone_v1(p_sale uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.cohorts;active jsonb;
begin
 if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then
  raise exception 'CP7_CREDIT_SOURCE_INCOMING_HISTORY_ADAPTER_REQUIRED';end if;
 for c in select ch.*from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id
  where f.family_root_sale_id=p_sale order by ch.id loop
  active:=cp7_credit.consumer_active_events_v1(c.id);
  if jsonb_array_length(active)>0 then
   raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO'using detail=active::text;end if;
 end loop;
end $$;

-- Historical membership is the immutable operation's actual before-profile,
-- not today's net-C, UUID chronology or the clock. A later consumer cannot
-- enter an old source operation's input. Verify every included real event and
-- require its named inverse to be in that same retained historical set.
create function cp7_credit.consumer_source_historical_v1(p_operation uuid,p_family uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare op jsonb;objects jsonb;ids uuid[];e cp7_credit.consumption_events;answer jsonb:='[]';
begin
 op:=cp7_credit.source_operation_binding_payload_v1(p_operation)->'operation';
 if not exists(select 1 from cp7_credit.return_families where id=p_family and family_root_sale_id=(op->>'sale_id')::uuid)then
  raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_FAMILY_CHANGED';end if;
 objects:=op#>'{before_financial_profile,actual_objects}';
 if jsonb_typeof(objects)is distinct from'array'
  or exists(select 1 from jsonb_array_elements(objects)x where x->>'object_kind'='CONSUMPTION'
   group by x->>'object_id'having count(*)<>1)then
  raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_CONSUMER_SET_CHANGED';end if;
 select coalesce(array_agg(e0.id order by e0.id),'{}'::uuid[])into ids
  from cp7_credit.consumption_events e0 join cp7_credit.cohorts c on c.id=e0.cohort_id
  where c.family_id=p_family and exists(select 1 from jsonb_array_elements(objects)x
   where x->>'object_kind'='CONSUMPTION'and(x->>'object_id')::uuid=e0.id);
 for e in select *from cp7_credit.consumption_events where id=any(ids)order by id loop
  perform cp7_credit.consumer_event_data_v1(e.id);
  if(e.amount<0 and not(e.restores_event_id=any(ids)))
   or(e.amount>0 and not exists(select 1 from cp7_credit.consumption_events u
    where u.id=any(ids)and u.restores_event_id=e.id))then
   raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_NAMED_UNDO_REQUIRED';end if;
  answer:=answer||jsonb_build_array(jsonb_build_object('id','consumption:'||e.id::text,
   'amount',cp7_credit.cent_text(e.amount),'economic_date',e.economic_date::text,
   'transaction_date',e.transaction_date::text,'source_sha256',e.source_sha256));
 end loop;
 return answer;
end $$;

do $private$declare sig text;begin
 foreach sig in array array['consumer_source_undone_v1(uuid)','consumer_source_historical_v1(uuid,uuid)']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private$;
