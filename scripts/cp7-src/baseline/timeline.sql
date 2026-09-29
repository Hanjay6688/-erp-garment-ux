create function cp7_baseline.timeline(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare e jsonb;k text;seen jsonb:='{}';orders jsonb:='{}';out_events jsonb:='[]';balance numeric;qty numeric;gap numeric;minimum numeric;
 unmet numeric:=0;first_gap jsonb:=null;uncertain boolean:=false;lo timestamptz;hi timestamptz;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','target_key','size_id','mode','initial_fg_pcs','from_at','through_at','events','refs']);
 perform cp7_demand.context(v,'cp7.timeline-input.v1');perform cp7_wip.key(v->'target_key');perform cp7_wip.key(v->'size_id');perform cp7_wip.refs(v->'refs');
 if v->>'mode' is null or v->>'mode' not in ('BACKLOG','LOST_SALES') then raise exception 'CP7_BASELINE_UNMET_MODE';end if;
 lo:=cp7_demand.instant(v->'from_at');hi:=cp7_demand.instant(v->'through_at');if hi<lo then raise exception 'CP7_BASELINE_TIMELINE_RANGE';end if;
 if v->'initial_fg_pcs'='null'::jsonb then uncertain:=true;else balance:=cp7_wip.pcs(v->'initial_fg_pcs');minimum:=balance;end if;
 perform cp7_demand.items(v->'events',20000);
 for e in select value from jsonb_array_elements(v->'events') loop
  perform cp7_wip.fields(e,array['key','at','sequence','kind','qty_pcs','refs']);k:=cp7_wip.key(e->'key');perform cp7_wip.refs(e->'refs');perform cp7_wip.pcs(e->'sequence');
  if cp7_demand.instant(e->'at')<lo or cp7_demand.instant(e->'at')>hi then raise exception 'CP7_BASELINE_EVENT_RANGE';end if;
  if e->>'kind' is null or e->>'kind' not in ('SUPPLY','DEMAND') then raise exception 'CP7_BASELINE_EVENT_KIND';end if;
  if e->'qty_pcs'<>'null'::jsonb then perform cp7_demand.decimal(e->'qty_pcs');end if;
  if seen ? k then
   if seen->k<>e then raise exception 'CP7_BASELINE_EVENT_CONFLICT';end if;continue;
  end if;
  seen:=seen||jsonb_build_object(k,e);
  k:=jsonb_build_array(cp7_demand.instant(e->'at'),e->>'sequence')::text;
  if orders ? k then raise exception 'CP7_BASELINE_INTRADAY_ORDER_REQUIRED';end if;orders:=orders||jsonb_build_object(k,true);
 end loop;
 for e in select value from jsonb_each(seen) order by cp7_demand.instant(value->'at'),cp7_wip.pcs(value->'sequence'),value->>'key' loop
  if e->'qty_pcs'='null'::jsonb then uncertain:=true;end if;
  gap:=null;
  if not uncertain then
   qty:=cp7_demand.decimal(e->'qty_pcs');
   if e->>'kind'='SUPPLY' then balance:=balance+qty;
   else
    gap:=greatest(0,qty-greatest(balance,0));
    if gap>0 then
     unmet:=unmet+gap;
     if first_gap is null then first_gap:=jsonb_build_object('at',e->'at','event_key',e->'key','gap_pcs',gap::text);end if;
    end if;
    balance:=case when v->>'mode'='BACKLOG' then balance-qty else greatest(0,balance-qty) end;
   end if;
   minimum:=least(minimum,balance);
  end if;
  out_events:=out_events||jsonb_build_array(jsonb_build_object('event',e,'status',case when uncertain then 'UNKNOWN' else 'KNOWN' end,
   'balance_pcs',case when uncertain then null else balance::text end,'new_unmet_pcs',gap::text));
 end loop;
 return jsonb_build_object('status',case when uncertain then 'UNKNOWN' else 'SCENARIO' end,'kernel_version','timeline-1',
  'mode',v->'mode','end_balance_pcs',case when uncertain then null else balance::text end,
  'minimum_balance_pcs',case when uncertain then null else minimum::text end,'first_known_gap',first_gap,
  'unmet_pcs',case when uncertain then null else unmet::text end,'events',out_events,'inputs',v,
  'reason',case when uncertain then 'UNKNOWN_EVENT_PRESERVED_KNOWN_PREFIX_ONLY' else 'ORDERED_EVENTS_LATE_ARRIVAL_DOES_NOT_ERASE_PRIOR_GAP' end);
end $$;
