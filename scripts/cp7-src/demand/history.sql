-- A lineage is one physical sales line throughout draft/post/cancel revisions.
-- posted_at is the original demand instant, preserved by later return revisions.
-- returned_pcs is cumulative separate evidence, never subtracted from gross demand.
create function cp7_demand.history(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare k text; r jsonb; old jsonb; t jsonb; latest jsonb:='{}'; av jsonb:='{}'; seen jsonb:='{}'; targets jsonb:='{}';
 known timestamptz; effective timestamptz; lo date; hi date; d date; day_key text; state text;
 qty numeric; returns_qty numeric; reserved numeric; total numeric; observed_total numeric; available_count int; unknown_count int; stockout_count int;
 rows_out jsonb:='[]'; days_out jsonb; groups_out jsonb:='[]'; selected_events jsonb:='[]'; group_key text;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','known_as_of','effective_as_of','from_date','through_date','history_complete','group_mode','targets','events','availability']);
 perform cp7_demand.context(v,'cp7.demand-input.v1');
 known:=cp7_demand.instant(v->'known_as_of');effective:=cp7_demand.instant(v->'effective_as_of');
 lo:=cp7_demand.day(v->'from_date');hi:=cp7_demand.day(v->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(effective at time zone 'Asia/Jakarta')::date then raise exception 'CP7_DEMAND_COMPLETE_DAYS_REQUIRED';end if;
 if jsonb_typeof(v->'history_complete') is distinct from 'boolean' or v->>'group_mode' not in ('AS_SOLD','RESTATED') or v->>'group_mode' is null then raise exception 'CP7_DEMAND_POLICY';end if;
 perform cp7_demand.items(v->'targets',1000);perform cp7_demand.items(v->'events',50000);perform cp7_demand.items(v->'availability',100000);
 if jsonb_array_length(v->'targets')*(hi-lo+1)>100000 then raise exception 'CP7_DEMAND_GRID_LIMIT';end if;
 for t in select value from jsonb_array_elements(v->'targets') loop
  perform cp7_wip.fields(t,array['key','size_id','current_group_key','refs']);k:=cp7_wip.key(t->'key');
  perform cp7_wip.key(t->'size_id');perform cp7_wip.key(t->'current_group_key');perform cp7_wip.refs(t->'refs');
  if targets ? k then raise exception 'CP7_DEMAND_DUPLICATE_TARGET';end if;targets:=targets||jsonb_build_object(k,t);
 end loop;
 for r in select value from jsonb_array_elements(v->'events') loop
  perform cp7_wip.fields(r,array['lineage_key','revision','known_at','effective_at','posted_at','status','target_key','size_id','sold_group_key','qty_pcs','returned_pcs','refs']);
  k:=cp7_wip.key(r->'lineage_key');perform cp7_wip.pcs(r->'revision');perform cp7_wip.refs(r->'refs');
  perform cp7_demand.instant(r->'known_at');perform cp7_demand.instant(r->'effective_at');
  perform cp7_wip.key(r->'target_key');perform cp7_wip.key(r->'sold_group_key');perform cp7_wip.key(r->'size_id');
  qty:=cp7_wip.pcs(r->'qty_pcs');returns_qty:=cp7_wip.pcs(r->'returned_pcs');
  if r->>'status' is null or r->>'status' not in ('DRAFT','POSTED','CANCELLED') or returns_qty>qty then raise exception 'CP7_DEMAND_LIFECYCLE';end if;
  if r->>'status'='POSTED' then
   if cp7_demand.instant(r->'posted_at')>cp7_demand.instant(r->'effective_at') then raise exception 'CP7_DEMAND_POSTED_AT';end if;
  elsif r->'posted_at'<>'null'::jsonb or returns_qty<>0 then raise exception 'CP7_DEMAND_UNPOSTED_RETURN';end if;
  -- Validate duplicate revisions even when outside the cutoff; fail closed on corruption.
  day_key:=jsonb_build_array(k,r->>'revision')::text;
  if seen ? day_key and seen->day_key<>r then raise exception 'CP7_DEMAND_REVISION_CONFLICT';end if;
  seen:=seen||jsonb_build_object(day_key,r);
  if cp7_demand.instant(r->'known_at')>known or cp7_demand.instant(r->'effective_at')>effective then continue;end if;
  t:=targets->(r->>'target_key');
  if t is null or t->>'size_id'<>r->>'size_id' then raise exception 'CP7_DEMAND_TARGET_SIZE';end if;
  old:=latest->k;
  if old is not null and (old->>'target_key'<>r->>'target_key' or old->>'size_id'<>r->>'size_id') then raise exception 'CP7_DEMAND_LINEAGE_IDENTITY';end if;
  if old is null or cp7_wip.pcs(r->'revision')>cp7_wip.pcs(old->'revision') then latest:=latest||jsonb_build_object(k,r);end if;
 end loop;
 for r in select value from jsonb_array_elements(v->'availability') loop
  perform cp7_wip.fields(r,array['target_key','date','revision','known_at','state','refs']);
  perform cp7_wip.key(r->'target_key');perform cp7_demand.day(r->'date');perform cp7_wip.pcs(r->'revision');
  perform cp7_wip.refs(r->'refs');perform cp7_demand.instant(r->'known_at');
  if r->>'state' is null or r->>'state' not in ('AVAILABLE','STOCKOUT','UNKNOWN') then raise exception 'CP7_DEMAND_AVAILABILITY';end if;
  k:=jsonb_build_array(r->>'target_key',r->>'date')::text;
  day_key:=jsonb_build_array('availability',k,r->>'revision')::text;
  if seen ? day_key and seen->day_key<>r then raise exception 'CP7_DEMAND_REVISION_CONFLICT';end if;
  seen:=seen||jsonb_build_object(day_key,r);
  if cp7_demand.instant(r->'known_at')>known then continue;end if;
  if not targets ? (r->>'target_key') then raise exception 'CP7_DEMAND_TARGET_SIZE';end if;
  old:=av->k;
  if old is null or cp7_wip.pcs(r->'revision')>cp7_wip.pcs(old->'revision') then av:=av||jsonb_build_object(k,r);end if;
 end loop;
 for r in select value from jsonb_each(latest) order by key loop
  selected_events:=selected_events||jsonb_build_array(r);
 end loop;
 for t in select value from jsonb_array_elements(v->'targets') order by value->>'key' loop
  total:=0;observed_total:=0;available_count:=0;unknown_count:=0;stockout_count:=0;reserved:=0;days_out:='[]';
  select coalesce(sum(cp7_wip.pcs(value->'qty_pcs')),0) into reserved from jsonb_each(latest)
   where value->>'target_key'=t->>'key' and value->>'status'='DRAFT';
  for d in select lo+i from generate_series(0,hi-lo) i loop
   day_key:=jsonb_build_array(t->>'key',d::text)::text;old:=av->day_key;
   state:=case when v->'history_complete'='true'::jsonb then coalesce(old->>'state','UNKNOWN') else 'UNKNOWN' end;
   select coalesce(sum(cp7_wip.pcs(value->'qty_pcs')),0),coalesce(sum(cp7_wip.pcs(value->'returned_pcs')),0)
    into qty,returns_qty from jsonb_each(latest) where value->>'target_key'=t->>'key' and value->>'status'='POSTED'
    and (cp7_demand.instant(value->'posted_at') at time zone 'Asia/Jakarta')::date=d;
   total:=total+qty;
   if state='AVAILABLE' then available_count:=available_count+1;observed_total:=observed_total+qty;
   elsif state='STOCKOUT' then stockout_count:=stockout_count+1;else unknown_count:=unknown_count+1;end if;
   days_out:=days_out||jsonb_build_array(jsonb_build_object('date',d::text,'state',state,'gross_observed_pcs',qty::text,
    'returned_pcs',returns_qty::text,'training_pcs',case when state='AVAILABLE' then qty::text else null end,'availability_refs',old->'refs'));
  end loop;
  rows_out:=rows_out||jsonb_build_array(jsonb_build_object('target_key',t->'key','size_id',t->'size_id','gross_observed_pcs',total::text,
   'draft_reserved_pcs',reserved::text,'available_days',available_count,'stockout_days',stockout_count,'unknown_days',unknown_count,
   'calendar_sales_mean',case when v->'history_complete'='true'::jsonb then (total/(hi-lo+1))::text else null end,
   'available_sales_mean',case when available_count>0 then (observed_total/available_count)::text else null end,
   'demand_estimate_basis',case when available_count>0 then 'ASSUMED_AVAILABLE_DAYS_REPRESENTATIVE' else 'UNKNOWN' end,
   'lost_sales_pcs',null,'days',days_out,'refs',t->'refs'));
 end loop;
 for r in select value from jsonb_array_elements(selected_events) where value->>'status'='POSTED' loop
  d:=(cp7_demand.instant(r->'posted_at') at time zone 'Asia/Jakarta')::date;
  if d<lo or d>hi then continue;end if;
  group_key:=case when v->>'group_mode'='AS_SOLD' then r->>'sold_group_key' else targets->(r->>'target_key')->>'current_group_key' end;
  groups_out:=groups_out||jsonb_build_array(jsonb_build_object('group_key',group_key,'size_id',r->'size_id','qty_pcs',r->'qty_pcs','lineage_key',r->'lineage_key','refs',r->'refs'));
 end loop;
 return jsonb_build_object('contract_version','cp7.demand-result.v1','kernel_version','demand-1','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'known_as_of',v->'known_as_of','effective_as_of',v->'effective_as_of','from_date',v->'from_date','through_date',v->'through_date',
  'status',case when v->'history_complete'='true'::jsonb then 'CAPTURE_COMPLETE' else 'UNKNOWN' end,
  'group_mode',v->'group_mode','rows',rows_out,'group_events',groups_out,'selected_events',selected_events,
  'reason','POSTED_ONCE_RETURNS_SEPARATE_DRAFT_RESERVED_CENSORED_NOT_ZERO');
end $$;

create function cp7_demand.availability(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare fg numeric; reserved numeric:=0; future numeric; e jsonb; seen jsonb:='{}';k text;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','target_key','size_id','fg_basis','fg_pcs','open_drafts','residual_future_pcs','refs']);
 perform cp7_demand.context(v,'cp7.available-input.v1');perform cp7_wip.key(v->'target_key');perform cp7_wip.key(v->'size_id');perform cp7_wip.refs(v->'refs');
 if v->>'fg_basis' is distinct from 'ON_HAND_AFTER_POSTED' then raise exception 'CP7_DEMAND_FG_BASIS';end if;
 perform cp7_demand.items(v->'open_drafts',10000);
 for e in select value from jsonb_array_elements(v->'open_drafts') loop
  perform cp7_wip.fields(e,array['lineage_key','qty_pcs','refs']);k:=cp7_wip.key(e->'lineage_key');perform cp7_wip.refs(e->'refs');
  if seen ? k then
   if seen->k<>e then raise exception 'CP7_DEMAND_DRAFT_CONFLICT';end if;continue;
  end if;
  reserved:=reserved+cp7_wip.pcs(e->'qty_pcs');seen:=seen||jsonb_build_object(k,e);
 end loop;
 if v->'fg_pcs'='null'::jsonb or v->'residual_future_pcs'='null'::jsonb then
  return jsonb_build_object('status','UNKNOWN','reason','FG_OR_RESIDUAL_UNKNOWN','inputs',v);end if;
 fg:=cp7_wip.pcs(v->'fg_pcs');future:=cp7_demand.decimal(v->'residual_future_pcs');
 return jsonb_build_object('status','KNOWN','kernel_version','availability-1','physical_fg_pcs',fg::text,'reserved_pcs',reserved::text,
  'available_fg_pcs',(fg-reserved)::text,'projected_residual_pcs',(fg-reserved-future)::text,'inputs',v,
  'reason','POSTED_ALREADY_IN_FG_OPEN_DRAFT_ONCE_RESIDUAL_FUTURE_ONLY');
end $$;
