-- Single work-centre / homogeneous selected unit-time scenario. Different routes
-- must be constrained separately by the integrator; this is not a factory optimizer.
create function cp7_baseline.capacity(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare e jsonb;k text;seen jsonb:='{}';previous_end timestamptz;starts timestamptz;ends timestamptz;lo timestamptz;hi timestamptz;
 available numeric:=0;overbooked numeric:=0;minutes numeric;load_minutes numeric;unit_minutes numeric;unknown boolean:=false;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','work_centre_id','from_at','through_at','unit_minutes','unit_time_basis','windows','refs']);
 perform cp7_demand.context(v,'cp7.capacity-input.v1');perform cp7_wip.key(v->'work_centre_id');perform cp7_wip.refs(v->'refs');
 lo:=cp7_demand.instant(v->'from_at');hi:=cp7_demand.instant(v->'through_at');if hi<=lo then raise exception 'CP7_CAPACITY_RANGE';end if;
 if v->>'unit_time_basis' is null or v->>'unit_time_basis' not in ('MEASURED','SELECTED_ASSUMPTION','UNKNOWN') then raise exception 'CP7_CAPACITY_UNIT_BASIS';end if;
 if v->'unit_minutes'='null'::jsonb or v->>'unit_time_basis'='UNKNOWN' then unknown:=true;
 else unit_minutes:=cp7_demand.decimal(v->'unit_minutes');if unit_minutes=0 then raise exception 'CP7_CAPACITY_UNIT_TIME';end if;end if;
 perform cp7_demand.items(v->'windows',10000);
 for e in select value from jsonb_array_elements(v->'windows') order by cp7_demand.instant(value->'starts_at'),value->>'key' loop
  perform cp7_wip.fields(e,array['key','starts_at','ends_at','existing_load_minutes','refs']);k:=cp7_wip.key(e->'key');perform cp7_wip.refs(e->'refs');
  if seen ? k then raise exception 'CP7_CAPACITY_DUPLICATE_WINDOW';end if;seen:=seen||jsonb_build_object(k,true);
  starts:=cp7_demand.instant(e->'starts_at');ends:=cp7_demand.instant(e->'ends_at');
  if starts<lo or ends>hi or ends<=starts or starts<previous_end then raise exception 'CP7_CAPACITY_WINDOW_OVERLAP_OR_RANGE';end if;previous_end:=ends;
  if e->'existing_load_minutes'='null'::jsonb then unknown:=true;continue;end if;
  minutes:=extract(epoch from ends-starts)/60;load_minutes:=cp7_demand.decimal(e->'existing_load_minutes');
  -- Load a window cannot hold carries into the next one (it is still owed work);
  -- whatever is left after the last window makes capacity UNKNOWN, as the
  -- composer does for captured work beyond the selected calendar. Loads have
  -- twelve decimals, so a load equal to the window's minutes rounded up to that
  -- resolution fills the window exactly; only load beyond it is carried.
  overbooked:=overbooked+load_minutes;available:=available+greatest(0,minutes-overbooked);
  overbooked:=case when overbooked<=ceil(minutes*1000000000000)/1000000000000 then 0 else overbooked-minutes end;
 end loop;
 return jsonb_build_object('status',case when unknown or overbooked>0 then 'UNKNOWN' else 'SCENARIO' end,'kernel_version','calendar-capacity-2',
  'available_minutes',case when unknown then null else available::text end,'overbooked_minutes',case when unknown then null else overbooked::text end,
  'capacity_pcs',case when unknown or overbooked>0 then null else floor(available/unit_minutes)::text end,'inputs',v,
  'reason',case when not unknown and overbooked>0 then 'EXISTING_LOAD_EXCEEDS_CALENDAR' else 'DATED_WINDOWS_MINUS_EXISTING_LOAD_WITH_EXPLICIT_UNIT_TIME' end);
end $$;
