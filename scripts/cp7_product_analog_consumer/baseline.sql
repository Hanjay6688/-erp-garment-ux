-- Private opt-in consumer adapter, derived from the pinned qualified baseline.
-- Existing public/default/staged callers remain unchanged until full overlay.
create function cp7_product_analog_consumer.baseline_rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text,context jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h jsonb:=jsonb_build_object('current_stock',current_stock);r jsonb;cfg jsonb;p jsonb;stock jsonb;estimate jsonb;target jsonb;manual jsonb;own jsonb;
 refs jsonb;profile_refs jsonb;total numeric;sd numeric;policy jsonb;state text;rows jsonb[]:='{}';root text;
 profiles jsonb;profiles_repeated jsonb;stocks jsonb;stocks_repeated jsonb;policies jsonb;resolution jsonb;all_refs jsonb;
begin
 if context->>'contract_version'is distinct from'cp7.analog-consumer-context.v1'
  or context->'captured_at'is distinct from c->'captured_at'then raise exception 'CP7_ANALOG_CONSUMER_CONTEXT';end if;
 for r in select x.value from jsonb_array_elements(history_rows)with ordinality x(value,o)order by x.o loop
  if context->'histories'->(r->>'target_key')is distinct from r then raise exception 'CP7_ANALOG_CONSUMER_ROW_CONTEXT';end if;
  root:=split_part(r->>'target_key',':',1);
  if profiles is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into profiles,profiles_repeated
    from(select x->>'root_id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'profiles')with ordinality a(x,o)
     where x->>'root_id'is not null group by 1)f;
  end if;
  if profiles_repeated?root then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  p:=profiles->root;
  if stocks is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into stocks,stocks_repeated
    from(select x->>'target_key' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(h->'current_stock')with ordinality a(x,o)
     where x->>'target_key'is not null group by 1)f;
  end if;
  if stocks_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  stock:=stocks->(r->>'target_key');
  refs:=r->'refs';cfg:=case when p->>'quality'='SELECTED_ASSUMPTION'then p->'config'else null end;
  profile_refs:=case when cfg is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object('kind','PLANNING_PROFILE','id',p->>'profile_id','revision',p->>'revision'))end;
  select coalesce(sum((value->>'gross_observed_pcs')::numeric),0),stddev_samp((value->>'gross_observed_pcs')::numeric)into total,sd from jsonb_array_elements(r->'days')where value->>'state'='AVAILABLE';
  own:=jsonb_build_object('available_total_pcs',total::text,'available_days',(r->>'available_days')::text,'capture_complete',true,'refs',refs);
  manual:=case when cfg->>'mean_mode'='SELECTED_MANUAL'then jsonb_build_object('daily_pcs',cfg->'daily_pcs',
   'assumption_id',p->>'profile_id','selected',true,'refs',profile_refs)else null end;
  resolution:=null;all_refs:=refs||profile_refs;
  -- Resolve fallback only after the existing manual/own priority is known.
  if manual is null and cfg is not null and cp7_wip.pcs(own->'available_days')<cp7_wip.pcs(cfg->'minimum_available_days')
   and context->'choices'->(r->>'target_key')->>'state'is distinct from'UNREVIEWED'then
   resolution:=cp7_product_analog_consumer.resolve(context,r->>'target_key',p);
   if resolution->>'state'='READY'then all_refs:=cp7_product_analog_consumer.refs(all_refs||(resolution->'refs'));end if;
  end if;
  estimate:=cp7_demand.estimate(jsonb_build_object('contract_version','cp7.demand-estimate-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',r->>'target_key','size_id',r->>'size_id',
   'minimum_own_available_days',coalesce(cfg->'minimum_available_days','"1"'::jsonb),
   'own',case when cfg is null then null else own end,'analog',resolution->'analog','manual',manual,'refs',all_refs));
  target:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v2','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode',coalesce(cfg->>'buffer_mode','DAYS'),
   'daily_total_pcs',case when estimate->>'basis'='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then own->'available_total_pcs'when estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'then resolution->'scaled_total_pcs'else estimate->'daily_pcs'end,
   'counted_days',case when estimate->>'basis'='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then own->'available_days'when estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'then resolution->'available_days'else'"1"'::jsonb end,
   'daily_sd',case when cfg->>'buffer_mode'='STATISTICAL'then case when estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'then resolution->>'scaled_daily_sd'else sd::text end end,'service_level',case when cfg->>'buffer_mode'='STATISTICAL'then cfg->>'service_level'end,'lead_days',cfg->'lead_days','review_days',cfg->'review_days','buffer_days',cfg->'buffer_days',
   'refs',all_refs));
  if policies is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into policies
    from(select m.k,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'production_policies'->'rows')with ordinality a(x,o)
     cross join lateral(select e#>>'{}' k from jsonb_array_elements(case when jsonb_typeof(x->'members')='array'then x->'members'end)e
       where jsonb_typeof(e)='string'
      union select jsonb_object_keys(case when jsonb_typeof(x->'members')='object'then x->'members'end)
      union select x->'members'#>>'{}' where jsonb_typeof(x->'members')='string')m group by 1)f;
  end if;
  policy:=policies->root;
  state:=case when policy->'policy'->>'quality'='KNOWN'then policy->'policy'->>'state'else null end;
  rows:=array_append(rows,jsonb_build_object('target_key',r->>'target_key','size_id',r->>'size_id',
   'sku',stock->>'sku','product_name',stock->>'product_name','available_fg_pcs',stock->>'native_available_pcs',
   'profile',p,'demand_estimate',estimate,'target',target,'production_policy',policy,
   'start_new_pcs',case when state in('PAUSED','STOPPED')then '0'else null end,
   'final_gap_pcs',null,'supply_state','UNKNOWN','capacity_state','UNKNOWN','timeline_state','UNKNOWN',
   'reason',case when state in('PAUSED','STOPPED')then 'PRODUCTION_DISABLED_EXISTING_STOCK_STILL_SELLABLE'
    when state is null then 'PRODUCTION_POLICY_UNREVIEWED_OR_IDENTITY_UNAVAILABLE'
    else 'AUTHORITATIVE_WIP_MATCHING_CALENDAR_CAPACITY_NOT_CAPTURED'end,
   'refs',all_refs)||case when resolution is null then'{}'::jsonb else jsonb_build_object('analog_resolution',resolution)end);
 end loop;
 return to_jsonb(rows);
end $$;

alter function cp7_product_analog_consumer.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)owner to cp7_capture;
revoke all on function cp7_product_analog_consumer.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)from public,anon,authenticated,service_role;
