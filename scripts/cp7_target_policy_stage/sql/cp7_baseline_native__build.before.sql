create or replace function cp7_baseline_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h jsonb;r jsonb;cfg jsonb;p jsonb;stock jsonb;estimate jsonb;target jsonb;manual jsonb;own jsonb;
 refs jsonb;profile_refs jsonb;hash text;total numeric;policy jsonb;state text;rows jsonb[]:='{}';root text;
 profiles jsonb;profiles_repeated jsonb;stocks jsonb;stocks_repeated jsonb;policies jsonb;
begin
 h:=cp7_planning.history_build(c,q);
 hash:=encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex');
 for r in select value from jsonb_array_elements(h->'history'->'rows')order by value->>'target_key'loop
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
  select coalesce(sum((value->>'gross_observed_pcs')::numeric),0)into total from jsonb_array_elements(r->'days')where value->>'state'='AVAILABLE';
  own:=jsonb_build_object('available_total_pcs',total::text,'available_days',(r->>'available_days')::text,'capture_complete',true,'refs',refs);
  manual:=case when cfg->>'mean_mode'='SELECTED_MANUAL'then jsonb_build_object('daily_pcs',cfg->'daily_pcs',
   'assumption_id',p->>'profile_id','selected',true,'refs',profile_refs)else null end;
  estimate:=cp7_demand.estimate(jsonb_build_object('contract_version','cp7.demand-estimate-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',r->>'target_key','size_id',r->>'size_id',
   'minimum_own_available_days',coalesce(cfg->'minimum_available_days','"1"'::jsonb),
   'own',case when cfg is null then null else own end,'analog',null,'manual',manual,'refs',refs||profile_refs));
  target:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v2','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode','DAYS',
   'daily_total_pcs',case when estimate->>'basis'='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then own->'available_total_pcs'else estimate->'daily_pcs'end,
   'counted_days',case when estimate->>'basis'='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then own->'available_days'else'"1"'::jsonb end,
   'daily_sd',null,'service_level',null,'lead_days',cfg->'lead_days','review_days',cfg->'review_days','buffer_days',cfg->'buffer_days',
   'refs',refs||profile_refs));
  -- (value->'members')?root: string array elements, object keys, or the string itself.
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
   'refs',refs||profile_refs));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-baseline.v1','captured_at',c->>'captured_at',
  'source_hash',hash,'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS','history_run_result',h,
  'rows',to_jsonb(rows),'target_basis','DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS','apply_enabled',false,
  'model_basis','BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN','production_go',false);
end $$;
