create function cp7_baseline.feasibility(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare need numeric;multiple numeric;rounded numeric;capacity numeric;material numeric;feasible numeric;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','target_key','size_id','production_status','need_pcs','multiple_pcs','capacity_pcs','material_cap_pcs','refs']);
 perform cp7_demand.context(v,'cp7.feasibility-input.v1');perform cp7_wip.key(v->'target_key');perform cp7_wip.key(v->'size_id');perform cp7_wip.refs(v->'refs');
 if v->>'production_status' is null or v->>'production_status' not in ('ACTIVE','STOP') then raise exception 'CP7_BASELINE_PRODUCTION_STATUS';end if;
 if v->'need_pcs'='null'::jsonb then return jsonb_build_object('status','UNKNOWN','reason','NEED_UNKNOWN','inputs',v);end if;
 need:=cp7_wip.pcs(v->'need_pcs');
 if v->>'production_status'='STOP' then return jsonb_build_object('status','STOP','need_pcs',need::text,'start_new_pcs','0','unresolved_pcs',need::text,'reason','STOP_DOES_NOT_HIDE_SHORTAGE','inputs',v);end if;
 if v->'multiple_pcs'='null'::jsonb or v->'capacity_pcs'='null'::jsonb or v->'material_cap_pcs'='null'::jsonb then
  return jsonb_build_object('status','UNKNOWN','need_pcs',need::text,'start_new_pcs',null,'unresolved_pcs',null,'reason','BATCH_CAPACITY_OR_MATERIAL_UNKNOWN','inputs',v);end if;
 multiple:=cp7_wip.pcs(v->'multiple_pcs');capacity:=cp7_wip.pcs(v->'capacity_pcs');material:=cp7_wip.pcs(v->'material_cap_pcs');
 if multiple=0 then raise exception 'CP7_BASELINE_MULTIPLE';end if;
 rounded:=ceil(need/multiple)*multiple;feasible:=floor(least(rounded,capacity,material)/multiple)*multiple;
 return jsonb_build_object('status','SCENARIO','kernel_version','feasibility-1','need_pcs',need::text,'rounded_need_pcs',rounded::text,
  'rounding_extra_pcs',(rounded-need)::text,'start_new_pcs',feasible::text,'unresolved_pcs',greatest(0,need-feasible)::text,
  'reason','NEED_PRESERVED_BATCH_MULTIPLE_WITHIN_KNOWN_CAPACITY_AND_MATERIAL','inputs',v);
end $$;

create function cp7_baseline.material(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare gross numeric;installed numeric;remaining numeric;unused numeric:=0;incoming numeric:=0;qty numeric;deadline timestamptz;
 e jsonb;k text;seen jsonb:='{}';excluded jsonb:='[]';unknown boolean:=false;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','material_id','unit','gross_need','proven_installed','deadline','supplies','refs']);
 perform cp7_demand.context(v,'cp7.material-need-input.v1');perform cp7_wip.key(v->'material_id');perform cp7_wip.key(v->'unit');perform cp7_wip.refs(v->'refs');deadline:=cp7_demand.instant(v->'deadline');
 perform cp7_demand.items(v->'supplies',10000);
 for e in select value from jsonb_array_elements(v->'supplies') loop
  perform cp7_wip.fields(e,array['physical_key','kind','quantity','verified_eligible_allocated','eta','refs']);k:=cp7_wip.key(e->'physical_key');perform cp7_wip.refs(e->'refs');
  if e->>'kind' is null or e->>'kind' not in ('UNUSED','INCOMING','ISSUED') or jsonb_typeof(e->'verified_eligible_allocated') is distinct from 'boolean' then raise exception 'CP7_BASELINE_MATERIAL_SUPPLY';end if;
  if seen ? k then if seen->k<>e then raise exception 'CP7_BASELINE_MATERIAL_DUPLICATE';end if;continue;end if;seen:=seen||jsonb_build_object(k,e);
  if e->'quantity'<>'null'::jsonb then qty:=cp7_demand.decimal(e->'quantity');end if;
  if e->'eta'<>'null'::jsonb then perform cp7_demand.instant(e->'eta');end if;
  if e->>'kind'='ISSUED' or e->'verified_eligible_allocated'='false'::jsonb then excluded:=excluded||jsonb_build_array(jsonb_build_object('physical_key',k,'reason','ISSUE_NOT_CONSUMPTION_OR_UNVERIFIED'));continue;end if;
  if e->'quantity'='null'::jsonb or (e->>'kind'='INCOMING' and e->'eta'='null'::jsonb) then unknown:=true;continue;end if;
  if e->>'kind'='UNUSED' then unused:=unused+qty;
  elsif cp7_demand.instant(e->'eta')<=deadline then incoming:=incoming+qty;
  else excluded:=excluded||jsonb_build_array(jsonb_build_object('physical_key',k,'reason','AFTER_DEADLINE'));end if;
 end loop;
 if v->'gross_need'='null'::jsonb or v->'proven_installed'='null'::jsonb or unknown then
  return jsonb_build_object('status','UNKNOWN','remaining_need',null,'external_need',null,'reason','CONSUMPTION_OR_ELIGIBLE_SUPPLY_UNKNOWN','excluded',excluded,'inputs',v);end if;
 gross:=cp7_demand.decimal(v->'gross_need');installed:=cp7_demand.decimal(v->'proven_installed');remaining:=greatest(0,gross-installed);
 return jsonb_build_object('status','SCENARIO','kernel_version','material-need-1','remaining_need',remaining::text,
  'external_need',greatest(0,remaining-unused-incoming)::text,'unit',v->'unit','excluded',excluded,
  'reason','GROSS_MINUS_PROVEN_INSTALLED_MINUS_VERIFIED_ALLOCATED_UNUSED_AND_ON_TIME_INCOMING','inputs',v);
end $$;
