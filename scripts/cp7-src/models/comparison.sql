-- Bounded plan-linked additive PCS outcome comparison. No plan/ledger writes.
-- Events are immutable normalized POSTs and linked partial/full corrections.
-- A REVERSAL inherits the original metric's effective date; known_at records
-- when that correction became knowable. Ordinary returns are not automatically
-- reversals of gross demand. The authoritative adapter must define each metric.
create function cp7_models.compare_plan(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare p jsonb;planned jsonb;e jsonb;original jsonb;dedup jsonb;event_map jsonb;selected jsonb;
 ekey text;mode text;actual jsonb;actual_refs jsonb;reason text;coverage text;
 assessment timestamptz;captured timestamptz;cutoff timestamptz;through_at timestamptz;
 lo timestamptz;hi timestamptz;created timestamptz;plan_known timestamptz;
 known_at timestamptz;effective_at timestamptz;version integer;known_subtotal numeric:=0;
 planned_qty numeric;net_qty numeric;sum_reversed numeric;unknown boolean:=false;missing_original boolean:=false;
 late_count integer;selected_count integer;variance numeric;remaining numeric;assumption jsonb;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','assessment_at','known_as_of','effective_through','knowledge_mode','capture_complete','history_reconstructible','plan','events','refs']);
 perform cp7_demand.context(v,'cp7.plan-comparison-input.v1');perform cp7_wip.refs(v->'refs');
 assessment:=cp7_demand.instant(v->'assessment_at');captured:=cp7_demand.instant(v->'known_as_of');through_at:=cp7_demand.instant(v->'effective_through');
 mode:=v->>'knowledge_mode';
 if mode is null or mode not in ('AS_KNOWN','RESTATED') then raise exception 'CP7_PLAN_KNOWLEDGE_MODE';end if;
 if jsonb_typeof(v->'capture_complete') is distinct from 'boolean' or jsonb_typeof(v->'history_reconstructible') is distinct from 'boolean' then raise exception 'CP7_PLAN_CAPTURE_FLAGS';end if;
 if captured<assessment or through_at>assessment then raise exception 'CP7_PLAN_CUTOFF_ORDER';end if;
 cutoff:=case when mode='AS_KNOWN' then assessment else captured end;
 p:=v->'plan';
 perform cp7_wip.fields(p,array['plan_id','plan_version','snapshot_id','scope_id','created_at','known_as_of','target_key','size_id','metric_id','period_start','period_end','planned','refs']);
 perform cp7_wip.key(p->'plan_id');perform cp7_wip.key(p->'snapshot_id');perform cp7_wip.key(p->'scope_id');
 perform cp7_wip.key(p->'target_key');perform cp7_wip.key(p->'size_id');perform cp7_wip.key(p->'metric_id');perform cp7_wip.refs(p->'refs');
 if p->'scope_id'<>v->'scope_id' then raise exception 'CP7_PLAN_SCOPE';end if;
 if jsonb_typeof(p->'plan_version') is distinct from 'number' or (p->>'plan_version') !~ '^(0|[1-9][0-9]{0,8})$' then raise exception 'CP7_PLAN_VERSION';end if;
 version:=(p->>'plan_version')::integer;
 lo:=cp7_demand.instant(p->'period_start');hi:=cp7_demand.instant(p->'period_end');
 created:=cp7_demand.instant(p->'created_at');plan_known:=cp7_demand.instant(p->'known_as_of');
 if hi<=lo or through_at<lo or plan_known>created or created>assessment then raise exception 'CP7_PLAN_PERIOD_OR_ORIGIN';end if;
 planned:=p->'planned';
 if planned->>'state'='KNOWN' then
  perform cp7_wip.fields(planned,array['state','value','unit','refs']);planned_qty:=cp7_wip.pcs(planned->'value');
 elsif planned->>'state'='ASSUMED' then
  perform cp7_wip.fields(planned,array['state','value','unit','refs','assumption_ids']);planned_qty:=cp7_wip.pcs(planned->'value');
  perform cp7_demand.items(planned->'assumption_ids',128);
  if jsonb_array_length(planned->'assumption_ids')=0 then raise exception 'CP7_PLAN_ASSUMPTION';end if;
  for assumption in select value from jsonb_array_elements(planned->'assumption_ids') loop perform cp7_wip.key(assumption);end loop;
  if (select count(distinct value) from jsonb_array_elements(planned->'assumption_ids'))<>jsonb_array_length(planned->'assumption_ids') then raise exception 'CP7_PLAN_ASSUMPTION';end if;
 elsif planned->>'state' in ('UNKNOWN','CONFLICT','NOT_APPLICABLE') then
  perform cp7_wip.fields(planned,array['state','unit','reason','refs']);perform cp7_wip.key(planned->'reason');
 else raise exception 'CP7_PLAN_PLANNED_STATE';end if;
 if planned->>'unit' is distinct from 'PCS' then raise exception 'CP7_PLAN_UNIT';end if;perform cp7_wip.refs(planned->'refs');
 perform cp7_demand.items(v->'events',10000);
 for e in select value from jsonb_array_elements(v->'events') loop
  perform cp7_wip.fields(e,array['event_key','scope_id','plan_id','plan_version','target_key','size_id','metric_id','kind','reverses_event_key','quantity_pcs','effective_at','known_at','refs']);
  perform cp7_wip.key(e->'event_key');perform cp7_wip.refs(e->'refs');
  if e->'scope_id' is distinct from p->'scope_id' or e->'plan_id' is distinct from p->'plan_id'
     or e->'plan_version' is distinct from p->'plan_version' or e->'target_key' is distinct from p->'target_key'
     or e->'size_id' is distinct from p->'size_id' or e->'metric_id' is distinct from p->'metric_id' then raise exception 'CP7_PLAN_ATTRIBUTION';end if;
  known_at:=cp7_demand.instant(e->'known_at');effective_at:=cp7_demand.instant(e->'effective_at');
  if effective_at>known_at then raise exception 'CP7_PLAN_UNREALIZED_EVENT';end if;
  if e->'quantity_pcs'<>'null'::jsonb then perform cp7_wip.pcs(e->'quantity_pcs');end if;
  if e->>'kind'='POST' then
   if e->'reverses_event_key'<>'null'::jsonb then raise exception 'CP7_PLAN_POST_REVERSE_LINK';end if;
  elsif e->>'kind'='REVERSAL' then perform cp7_wip.key(e->'reverses_event_key');
  else raise exception 'CP7_PLAN_EVENT_KIND';end if;
 end loop;
 if exists(select 1 from jsonb_array_elements(v->'events') group by value->>'event_key' having count(distinct value)>1) then raise exception 'CP7_PLAN_EVENT_CONFLICT';end if;
 select coalesce(jsonb_agg(value order by value->>'event_key' collate "C"),'[]') into dedup from (select distinct value from jsonb_array_elements(v->'events')) unique_events;
 select coalesce(jsonb_object_agg(value->>'event_key',value),'{}') into event_map from jsonb_array_elements(dedup);
 -- Validate links before arithmetic; a correction cannot point to a correction,
 -- change the period being corrected, or become known before its original.
 for e in select value from jsonb_array_elements(dedup) where value->>'kind'='REVERSAL' loop
  original:=event_map->(e->>'reverses_event_key');
  if original is null then
   if v->'capture_complete'='true'::jsonb then raise exception 'CP7_PLAN_ORPHAN_REVERSAL';end if;
  elsif original->>'kind'<>'POST' or cp7_demand.instant(e->'effective_at')<>cp7_demand.instant(original->'effective_at')
      or cp7_demand.instant(e->'known_at')<cp7_demand.instant(original->'known_at') then raise exception 'CP7_PLAN_REVERSAL_LINK';end if;
 end loop;
 for ekey,sum_reversed in select value->>'reverses_event_key',sum((value->>'quantity_pcs')::numeric)
  from jsonb_array_elements(dedup) where value->>'kind'='REVERSAL' group by value->>'reverses_event_key' loop
  original:=event_map->ekey;
  if sum_reversed>(original->>'quantity_pcs')::numeric then raise exception 'CP7_PLAN_OVER_REVERSAL';end if;
 end loop;
 select coalesce(jsonb_agg(value order by cp7_demand.instant(value->'effective_at'),value->>'event_key' collate "C"),'[]') into selected
  from jsonb_array_elements(dedup) where cp7_demand.instant(value->'known_at')<=cutoff
  and cp7_demand.instant(value->'effective_at')>=lo and cp7_demand.instant(value->'effective_at')<hi
  and cp7_demand.instant(value->'effective_at')<=through_at;
 unknown:=v->'capture_complete'='false'::jsonb or (mode='AS_KNOWN' and v->'history_reconstructible'='false'::jsonb);
 for e in select value from jsonb_array_elements(selected) loop
  if e->'quantity_pcs'='null'::jsonb then unknown:=true;
  else known_subtotal:=known_subtotal+(case when e->>'kind'='REVERSAL' then -1 else 1 end)*cp7_wip.pcs(e->'quantity_pcs');end if;
  if e->>'kind'='REVERSAL' and not (event_map ? (e->>'reverses_event_key')) then missing_original:=true;unknown:=true;end if;
 end loop;
 select count(*)::integer,count(*) filter(where cp7_demand.instant(value->'known_at')>assessment)::integer into selected_count,late_count from jsonb_array_elements(selected);
 select jsonb_agg(value order by value::text collate "C") into actual_refs from (
  select value from jsonb_array_elements(v->'refs') union
  select r.value from jsonb_array_elements(selected) x cross join lateral jsonb_array_elements(x.value->'refs') r) all_refs;
 coverage:=case when through_at>=hi then 'FULL_PERIOD' else 'PERIOD_IN_PROGRESS' end;
 reason:=case when v->'capture_complete'='false'::jsonb then 'CAPTURE_INCOMPLETE'
  when mode='AS_KNOWN' and v->'history_reconstructible'='false'::jsonb then 'HISTORY_NOT_RECONSTRUCTIBLE'
  when missing_original then 'MISSING_ORIGINAL' when unknown then 'UNKNOWN_EVENT_QUANTITY' else 'OBSERVED_POSTS_MINUS_LINKED_CORRECTIONS' end;
 if unknown then actual:=jsonb_build_object('state','UNKNOWN','unit','PCS','reason',reason,'refs',actual_refs);
 else
  net_qty:=known_subtotal;actual:=jsonb_build_object('state','KNOWN','value',net_qty::text,'unit','PCS','refs',actual_refs);
  if planned_qty is not null then remaining:=greatest(0,planned_qty-net_qty);
   if coverage='FULL_PERIOD' then variance:=net_qty-planned_qty;end if;end if;
 end if;
 return jsonb_build_object('kernel_version','plan-pcs-outcome-1','status',case when unknown or planned_qty is null then 'UNKNOWN' else 'COMPARABLE' end,
  'comparison',jsonb_build_object('plan_id',p->>'plan_id','plan_version',version,'metric_id',p->>'metric_id',
   'planned',planned,'actual',actual,'knowledge_mode',mode,
   'interpretation',case when mode='RESTATED' then 'Restated outcome using later knowledge; original plan and its information cutoff are unchanged.' else 'Outcome using only knowledge available at the assessment cutoff; original plan is unchanged.' end),
  'original_plan',p,'knowledge_cutoff',case when mode='AS_KNOWN' then v->'assessment_at' else v->'known_as_of' end,
  'coverage',coverage,'variance_pcs',variance::text,'remaining_to_plan_pcs',remaining::text,
  'selected_event_count',selected_count,'later_known_event_count',late_count,'known_signed_subtotal_pcs',known_subtotal::text,
  'events',selected,'reason',reason,'decision_verdict','NOT_INFERRED_FROM_OUTCOME','inputs',v);
end $$;
