create or replace function cp7_baseline.net(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare target numeric;fg numeric;directed numeric:=0;incoming numeric:=0;candidate numeric:=0;base numeric; q numeric;
 s jsonb;k text;seen jsonb:='{}';excluded jsonb:='[]';deadline timestamptz;uncertain boolean:=false;
 modern boolean:=v->>'contract_version'='cp7.net-input.v2';legacy jsonb;horizon_net jsonb;lead_net jsonb;point numeric;
 lead_position numeric;conditional_position numeric;
begin
 if modern then
  perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','scenario_id','target_key','size_id','deadline',
   'target_pcs','available_fg_pcs','supplies','refs','reorder_point_pcs','lead_deadline']);
  perform cp7_demand.context(v,'cp7.net-input.v2');
  if v->'reorder_point_pcs'<>'null'::jsonb then point:=cp7_wip.pcs(v->'reorder_point_pcs');end if;
  if v->'target_pcs'<>'null'::jsonb and point>cp7_wip.pcs(v->'target_pcs')then raise exception 'CP7_BASELINE_POINT_ABOVE_TARGET';end if;
  if v->'lead_deadline'<>'null'::jsonb and cp7_demand.instant(v->'lead_deadline')>cp7_demand.instant(v->'deadline')then
   raise exception 'CP7_BASELINE_LEAD_AFTER_HORIZON';end if;
  legacy:=(v-'reorder_point_pcs'-'lead_deadline')||jsonb_build_object('contract_version','cp7.net-input.v1');
  -- Two readings of the same conserved allocation, never two allocations.
  -- The lead reading excludes supply arriving between L and L+R. Its point
  -- already includes the one selected buffer; no safety is added here.
  horizon_net:=cp7_baseline.net(legacy);
  if v->'lead_deadline'='null'::jsonb then
   lead_net:=jsonb_build_object('status','UNKNOWN','reason','LEAD_DEADLINE_UNKNOWN','q_base_pcs',null,'q_conditional_pcs',null);
  else
   lead_net:=cp7_baseline.net(legacy||jsonb_build_object('deadline',v->'lead_deadline','target_pcs',v->'reorder_point_pcs'));
  end if;
  if lead_net->>'status'='SCENARIO'then
   lead_position:=(v->>'available_fg_pcs')::numeric+(lead_net->>'directed_on_time_pcs')::numeric+(lead_net->>'incoming_on_time_pcs')::numeric;
   conditional_position:=lead_position+(lead_net->>'candidate_on_time_pcs')::numeric;
  end if;
  return horizon_net||jsonb_build_object('kernel_version','net-dual-horizon-2','inputs',v,'lead_net',lead_net,
   'lead_position_base_pcs',lead_position::text,'lead_position_conditional_pcs',conditional_position::text,
   'base_reorder_state',case when point is null or lead_position is null then'UNKNOWN'when point=0 then'NO_POINT'
     when lead_position<=point then'AT_OR_BELOW'else'ABOVE'end,
   'conditional_reorder_state',case when point is null or conditional_position is null then'UNKNOWN'when point=0 then'NO_POINT'
     when conditional_position<=point then'AT_OR_BELOW'else'ABOVE'end);
 end if;
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','scenario_id','target_key','size_id','deadline','target_pcs','available_fg_pcs','supplies','refs']);
 perform cp7_demand.context(v,'cp7.net-input.v1');perform cp7_wip.key(v->'scenario_id');perform cp7_wip.key(v->'target_key');perform cp7_wip.key(v->'size_id');perform cp7_wip.refs(v->'refs');
 deadline:=cp7_demand.instant(v->'deadline');perform cp7_demand.items(v->'supplies',10000);
 for s in select value from jsonb_array_elements(v->'supplies') loop
  perform cp7_wip.fields(s,array['physical_key','snapshot_id','target_key','size_id','kind','qty_pcs','eta','eligible','refs']);
  k:=cp7_wip.key(s->'physical_key');perform cp7_wip.refs(s->'refs');
  if s->>'snapshot_id' is distinct from v->>'snapshot_id' or s->>'target_key' is distinct from v->>'target_key' or s->>'size_id' is distinct from v->>'size_id' then raise exception 'CP7_BASELINE_SUPPLY_BINDING';end if;
  if s->>'kind' is null or s->>'kind' not in ('DIRECTED','INCOMING','ALLOCATED_CANDIDATE') or jsonb_typeof(s->'eligible') is distinct from 'boolean' then raise exception 'CP7_BASELINE_SUPPLY_KIND';end if;
  if seen ? k then
   if seen->k<>s then raise exception 'CP7_BASELINE_PHYSICAL_SOURCE_CONFLICT';end if;continue;
  end if;
  seen:=seen||jsonb_build_object(k,s);
  if s->'qty_pcs'<>'null'::jsonb then q:=cp7_wip.pcs(s->'qty_pcs');end if;
  if s->'eta'<>'null'::jsonb then perform cp7_demand.instant(s->'eta');end if;
  if s->'eligible'='false'::jsonb then excluded:=excluded||jsonb_build_array(jsonb_build_object('physical_key',k,'reason','INELIGIBLE'));continue;end if;
  if s->'qty_pcs'='null'::jsonb or s->'eta'='null'::jsonb then uncertain:=true;excluded:=excluded||jsonb_build_array(jsonb_build_object('physical_key',k,'reason','QUANTITY_OR_ETA_UNKNOWN'));continue;end if;
  if cp7_demand.instant(s->'eta')>deadline then excluded:=excluded||jsonb_build_array(jsonb_build_object('physical_key',k,'reason','AFTER_DEADLINE'));continue;end if;
  if s->>'kind'='DIRECTED' then directed:=directed+q;elsif s->>'kind'='INCOMING' then incoming:=incoming+q;else candidate:=candidate+q;end if;
 end loop;
 if v->'target_pcs'='null'::jsonb or v->'available_fg_pcs'='null'::jsonb or uncertain then
  return jsonb_build_object('status','UNKNOWN','q_base_pcs',null,'q_conditional_pcs',null,'reason','TARGET_FG_OR_ELIGIBLE_SUPPLY_UNKNOWN','excluded',excluded,'inputs',v);end if;
 target:=cp7_wip.pcs(v->'target_pcs');
 -- Reservations can exceed on-hand. Preserve that signed shortage, never clamp FG.
 if jsonb_typeof(v->'available_fg_pcs') is distinct from 'string' or v->>'available_fg_pcs' !~ '^-?(0|[1-9][0-9]{0,29})$' then raise exception 'CP7_BASELINE_AVAILABLE_FG';end if;
 fg:=(v->>'available_fg_pcs')::numeric;base:=greatest(0,target-fg-directed-incoming);
 return jsonb_build_object('status','SCENARIO','kernel_version','net-1','q_base_pcs',base::text,'q_conditional_pcs',greatest(0,base-candidate)::text,
  'directed_on_time_pcs',directed::text,'incoming_on_time_pcs',incoming::text,'candidate_on_time_pcs',candidate::text,'excluded',excluded,
  'reason','TARGET_MINUS_AVAILABLE_FG_MINUS_UNIQUE_ON_TIME_SUPPLY_PER_PHYSICAL_SIZE','inputs',v);
end $$;
