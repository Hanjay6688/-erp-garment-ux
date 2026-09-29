-- Cold-start fallback is explicit and evidence-bearing. No default batch or demand.
create function cp7_demand.estimate(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare own jsonb;analog jsonb;manual jsonb;minimum_days numeric;days numeric;total numeric;mean numeric;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','target_key','size_id','minimum_own_available_days','own','analog','manual','refs']);
 perform cp7_demand.context(v,'cp7.demand-estimate-input.v1');perform cp7_wip.key(v->'target_key');perform cp7_wip.key(v->'size_id');perform cp7_wip.refs(v->'refs');
 minimum_days:=cp7_wip.pcs(v->'minimum_own_available_days');if minimum_days<1 then raise exception 'CP7_DEMAND_MINIMUM_DAYS';end if;
 own:=v->'own';analog:=v->'analog';manual:=v->'manual';
 if manual<>'null'::jsonb then
  perform cp7_wip.fields(manual,array['daily_pcs','assumption_id','selected','refs']);perform cp7_wip.key(manual->'assumption_id');perform cp7_wip.refs(manual->'refs');mean:=cp7_demand.decimal(manual->'daily_pcs');
  if jsonb_typeof(manual->'selected') is distinct from 'boolean' then raise exception 'CP7_DEMAND_MANUAL_SELECTION';end if;
  if manual->'selected'='true'::jsonb then return jsonb_build_object('status','SCENARIO','basis','SELECTED_MANUAL_ASSUMPTION','daily_pcs',mean::text,'inputs',v);end if;
 end if;
 if own<>'null'::jsonb then
  perform cp7_wip.fields(own,array['available_total_pcs','available_days','capture_complete','refs']);perform cp7_wip.refs(own->'refs');
  total:=cp7_wip.pcs(own->'available_total_pcs');days:=cp7_wip.pcs(own->'available_days');
  if jsonb_typeof(own->'capture_complete') is distinct from 'boolean' or (days=0 and total>0) then raise exception 'CP7_DEMAND_OWN_HISTORY';end if;
  if days>=minimum_days and own->'capture_complete'='true'::jsonb then return jsonb_build_object('status','SCENARIO','basis','OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE','daily_pcs',round(total/days,12)::text,'inputs',v);end if;
 end if;
 if analog<>'null'::jsonb then
  perform cp7_wip.fields(analog,array['source_key','source_size_id','available_total_pcs','available_days','scale_factor','reason','reviewed','refs']);
  perform cp7_wip.key(analog->'source_key');perform cp7_wip.key(analog->'source_size_id');perform cp7_wip.key(analog->'reason');perform cp7_wip.refs(analog->'refs');
  total:=cp7_wip.pcs(analog->'available_total_pcs');days:=cp7_wip.pcs(analog->'available_days');mean:=cp7_demand.decimal(analog->'scale_factor');
  if jsonb_typeof(analog->'reviewed') is distinct from 'boolean' or (days=0 and total>0) then raise exception 'CP7_DEMAND_ANALOG';end if;
  if days>0 and analog->'reviewed'='true'::jsonb and analog->>'source_size_id'=v->>'size_id' then
   return jsonb_build_object('status','SCENARIO','basis','REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION','daily_pcs',round(total/days*mean,12)::text,'inputs',v);
  end if;
 end if;
 return jsonb_build_object('status','UNKNOWN','daily_pcs',null,'reason','OWN_HISTORY_INSUFFICIENT_NO_REVIEWED_ANALOG_OR_SELECTED_MANUAL','inputs',v);
end $$;
