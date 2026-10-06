-- A lineage is one physical sales line throughout draft/post/cancel revisions.
-- posted_at is the original demand instant, preserved by later return revisions.
-- returned_pcs is cumulative separate evidence, never subtracted from gross demand.
create function cp7_demand.history(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
-- Linear form of demand-1 (P19): the same validations run row by row in the
-- same order, but every check that needed an accumulated map (seen revision,
-- latest lineage, duplicate target) is a window flag computed once. Maps are
-- built once after validation and the daily grid is one grouped statement.
declare k text; r jsonb; t jsonb; targets jsonb; i bigint; known timestamptz; effective timestamptz; lo date; hi date;
 qty numeric; returns_qty numeric; target_duplicate boolean[]; event_conflict boolean[]; event_identity boolean[];
 availability_conflict boolean[]; latest jsonb; av jsonb; rows_out jsonb; groups_out jsonb; selected_events jsonb;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','known_as_of','effective_as_of','from_date','through_date','history_complete','group_mode','targets','events','availability']);
 perform cp7_demand.context(v,'cp7.demand-input.v1');
 known:=cp7_demand.instant(v->'known_as_of');effective:=cp7_demand.instant(v->'effective_as_of');
 lo:=cp7_demand.day(v->'from_date');hi:=cp7_demand.day(v->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(effective at time zone 'Asia/Jakarta')::date then raise exception 'CP7_DEMAND_COMPLETE_DAYS_REQUIRED';end if;
 if jsonb_typeof(v->'history_complete') is distinct from 'boolean' or v->>'group_mode' not in ('AS_SOLD','RESTATED') or v->>'group_mode' is null then raise exception 'CP7_DEMAND_POLICY';end if;
 perform cp7_demand.items(v->'targets',1000);perform cp7_demand.items(v->'events',50000);perform cp7_demand.items(v->'availability',100000);
 if jsonb_array_length(v->'targets')*(hi-lo+1)>100000 then raise exception 'CP7_DEMAND_GRID_LIMIT';end if;
 -- Row flags never cast unvalidated text: a row that is invalid raises in its
 -- own loop turn first, and a flag only looks at rows before it.
 select coalesce(array_agg(z.dup order by z.n),'{}') into target_duplicate from(
  select x.n,count(*)over(partition by x.value->>'key' order by x.n rows unbounded preceding)>1 dup
  from jsonb_array_elements(v->'targets')with ordinality x(value,n))z;
 for t,i in select x.value,x.n from jsonb_array_elements(v->'targets')with ordinality x(value,n) order by x.n loop
  perform cp7_wip.fields(t,array['key','size_id','current_group_key','refs']);k:=cp7_wip.key(t->'key');
  perform cp7_wip.key(t->'size_id');perform cp7_wip.key(t->'current_group_key');perform cp7_wip.refs(t->'refs');
  if target_duplicate[i] then raise exception 'CP7_DEMAND_DUPLICATE_TARGET';end if;
 end loop;
 select coalesce(jsonb_object_agg(x.value->>'key',x.value),'{}') into targets from jsonb_array_elements(v->'targets')x;
 select coalesce(array_agg(z.conflict order by z.n),'{}'),coalesce(array_agg(coalesce(z.identity,false) order by z.n),'{}')
 into event_conflict,event_identity from(
  select y.n,y.r<>first_value(y.r)over(partition by jsonb_build_array(y.r->>'lineage_key',y.r->>'revision')::text order by y.n) conflict,
   y.incut and(y.fl->>'target_key'<>y.r->>'target_key' or y.fl->>'size_id'<>y.r->>'size_id') identity
  from(select w.n,w.r,w.incut,first_value(w.r)over(partition by w.r->>'lineage_key',w.incut order by w.n) fl from(
    select x.n,x.r,case when pg_input_is_valid(x.r->>'known_at','timestamptz') and pg_input_is_valid(x.r->>'effective_at','timestamptz')
     then not((x.r->>'known_at')::timestamptz>known or(x.r->>'effective_at')::timestamptz>effective) else false end incut
    from jsonb_array_elements(v->'events')with ordinality x(r,n))w)y)z;
 for r,i in select x.value,x.n from jsonb_array_elements(v->'events')with ordinality x(value,n) order by x.n loop
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
  if event_conflict[i] then raise exception 'CP7_DEMAND_REVISION_CONFLICT';end if;
  if cp7_demand.instant(r->'known_at')>known or cp7_demand.instant(r->'effective_at')>effective then continue;end if;
  t:=targets->(r->>'target_key');
  if t is null or t->>'size_id'<>r->>'size_id' then raise exception 'CP7_DEMAND_TARGET_SIZE';end if;
  if event_identity[i] then raise exception 'CP7_DEMAND_LINEAGE_IDENTITY';end if;
 end loop;
 select coalesce(array_agg(z.conflict order by z.n),'{}') into availability_conflict from(
  select x.n,x.r<>first_value(x.r)over(partition by jsonb_build_array('availability',jsonb_build_array(x.r->>'target_key',x.r->>'date')::text,x.r->>'revision')::text order by x.n) conflict
  from jsonb_array_elements(v->'availability')with ordinality x(r,n))z;
 for r,i in select x.value,x.n from jsonb_array_elements(v->'availability')with ordinality x(value,n) order by x.n loop
  perform cp7_wip.fields(r,array['target_key','date','revision','known_at','state','refs']);
  perform cp7_wip.key(r->'target_key');perform cp7_demand.day(r->'date');perform cp7_wip.pcs(r->'revision');
  perform cp7_wip.refs(r->'refs');perform cp7_demand.instant(r->'known_at');
  if r->>'state' is null or r->>'state' not in ('AVAILABLE','STOCKOUT','UNKNOWN') then raise exception 'CP7_DEMAND_AVAILABILITY';end if;
  if availability_conflict[i] then raise exception 'CP7_DEMAND_REVISION_CONFLICT';end if;
  if cp7_demand.instant(r->'known_at')>known then continue;end if;
  if not targets ? (r->>'target_key') then raise exception 'CP7_DEMAND_TARGET_SIZE';end if;
 end loop;
 -- Every row is valid now. The kept revision is the first row holding the
 -- highest revision of its lineage (or target day) within the cutoff.
 select coalesce(jsonb_object_agg(z.k,z.r),'{}') into latest from(
  select distinct on(x.r->>'lineage_key') x.r->>'lineage_key' k,x.r from jsonb_array_elements(v->'events')with ordinality x(r,n)
  where not(cp7_demand.instant(x.r->'known_at')>known or cp7_demand.instant(x.r->'effective_at')>effective)
  order by x.r->>'lineage_key',cp7_wip.pcs(x.r->'revision') desc,x.n)z;
 select coalesce(jsonb_object_agg(z.k,z.r),'{}') into av from(
  select distinct on(jsonb_build_array(x.r->>'target_key',x.r->>'date')::text) jsonb_build_array(x.r->>'target_key',x.r->>'date')::text k,x.r
  from jsonb_array_elements(v->'availability')with ordinality x(r,n) where not cp7_demand.instant(x.r->'known_at')>known
  order by jsonb_build_array(x.r->>'target_key',x.r->>'date')::text,cp7_wip.pcs(x.r->'revision') desc,x.n)z;
 select coalesce(jsonb_agg(e.value order by e.key),'[]') into selected_events from jsonb_each(latest)e;
 with ev as materialized(select e.value ev_row from jsonb_each(latest)e),
 posted as(select ev.ev_row->>'target_key' tk,(cp7_demand.instant(ev.ev_row->'posted_at') at time zone 'Asia/Jakarta')::date d,
   sum(cp7_wip.pcs(ev.ev_row->'qty_pcs')) q,sum(cp7_wip.pcs(ev.ev_row->'returned_pcs')) rq from ev where ev.ev_row->>'status'='POSTED' group by 1,2),
 drafts as(select ev.ev_row->>'target_key' tk,sum(cp7_wip.pcs(ev.ev_row->'qty_pcs')) q from ev where ev.ev_row->>'status'='DRAFT' group by 1),
 days as materialized(select x.n,x.target,g.d,a.value old,
   case when v->'history_complete'='true'::jsonb then coalesce(a.value->>'state','UNKNOWN') else 'UNKNOWN' end day_state,
   coalesce(p.q,0) day_qty,coalesce(p.rq,0) day_returns
  from jsonb_array_elements(v->'targets')with ordinality x(target,n)
  cross join lateral(select lo+s d from generate_series(0,hi-lo)s)g
  left join jsonb_each(av)a on a.key=jsonb_build_array(x.target->>'key',g.d::text)::text
  left join posted p on p.tk=x.target->>'key' and p.d=g.d),
 per_target as(select days.n,days.target,sum(days.day_qty) total,coalesce(sum(days.day_qty)filter(where days.day_state='AVAILABLE'),0) observed_total,
   count(*)filter(where days.day_state='AVAILABLE') available_count,count(*)filter(where days.day_state='STOCKOUT') stockout_count,
   count(*)filter(where days.day_state not in('AVAILABLE','STOCKOUT')) unknown_count,
   jsonb_agg(jsonb_build_object('date',days.d::text,'state',days.day_state,'gross_observed_pcs',days.day_qty::text,'returned_pcs',days.day_returns::text,
    'training_pcs',case when days.day_state='AVAILABLE' then days.day_qty::text else null end,'availability_refs',days.old->'refs') order by days.d) day_rows
  from days group by days.n,days.target)
 select coalesce(jsonb_agg(jsonb_build_object('target_key',p.target->'key','size_id',p.target->'size_id','gross_observed_pcs',p.total::text,
   'draft_reserved_pcs',coalesce(dr.q,0)::text,'available_days',p.available_count,'stockout_days',p.stockout_count,'unknown_days',p.unknown_count,
   'calendar_sales_mean',case when v->'history_complete'='true'::jsonb then (p.total/(hi-lo+1))::text else null end,
   'available_sales_mean',case when p.available_count>0 then (p.observed_total/p.available_count)::text else null end,
   'demand_estimate_basis',case when p.available_count>0 then 'ASSUMED_AVAILABLE_DAYS_REPRESENTATIVE' else 'UNKNOWN' end,
   'lost_sales_pcs',null,'days',p.day_rows,'refs',p.target->'refs') order by p.target->>'key'),'[]') into rows_out
 from per_target p left join drafts dr on dr.tk=p.target->>'key';
 select coalesce(jsonb_agg(jsonb_build_object('group_key',case when v->>'group_mode'='AS_SOLD' then e.value->>'sold_group_key' else targets->(e.value->>'target_key')->>'current_group_key' end,
   'size_id',e.value->'size_id','qty_pcs',e.value->'qty_pcs','lineage_key',e.value->'lineage_key','refs',e.value->'refs') order by e.key),'[]') into groups_out
 from jsonb_each(latest)e where e.value->>'status'='POSTED'
  and (cp7_demand.instant(e.value->'posted_at') at time zone 'Asia/Jakarta')::date between lo and hi;
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
