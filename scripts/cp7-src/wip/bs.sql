-- Apply each case's existing BS resource through rework, disposition and HOLD.
-- Resolution rows for rework GOOD are provenance, not a second FG movement.
-- Linear form: the graph's nodes and events are held as arrays with a hashed
-- node map, and every move still goes through cp7_wip.transition on a graph
-- that holds only the destination node, so each move checks and fails exactly
-- as before. Source rows are looked up in maps built where the first scan ran.
create function cp7_wip.settle_bs(g jsonb,f jsonb,bsnodes jsonb,scope_at timestamptz) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare rw jsonb;b jsonb;d jsonb;x jsonb;held jsonb;positions jsonb;ref jsonb;
 pool text;src text;dst text;qty numeric;cnt integer;
 nodes jsonb[];events jsonb[];nm jsonb[];n jsonb;t jsonb;k text;h integer;here jsonb;ne integer;
 reworks_by_id jsonb;fg_by_resolution jsonb;holds_by_case jsonb;remaining jsonb;
begin
 select coalesce(array_agg(value order by ordinality),'{}') into nodes from jsonb_array_elements(g->'nodes') with ordinality;
 select coalesce(array_agg(value order by ordinality),'{}') into events from jsonb_array_elements(g->'events') with ordinality;
 ne:=cardinality(events);
 select array_agg(coalesce(m.v,'{}'::jsonb) order by s.h) into nm from generate_series(1,1024) s(h) left join(
  select (hashtext(z.k)&1023)+1 h,jsonb_object_agg(z.k,z.value) v from(select distinct on(value->>'key')value->>'key' k,value
   from jsonb_array_elements(g->'nodes') with ordinality where value->>'key' is not null order by value->>'key',ordinality)z group by 1)m on m.h=s.h;
 for rw in select value from jsonb_array_elements(f->'reworks') where value->>'status'<>'CANCELLED' order by value->>'physical_sent_at',value->>'id' loop
  b:=bsnodes->(rw->>'bs_case_id');
  if b is null then return jsonb_build_object('status','UNKNOWN','reason','REWORK_BS_SOURCE_UNPROVEN','source_id',rw->'id');end if;
  pool:=b->>'pool';src:=b->>'node';dst:='REWORK:'||(rw->>'id');ref:=cp7_wip.ref('erp.rework_orders',rw->>'id',rw->>'revision');
  k:=dst;n:=nm[(hashtext(k)&1023)+1]->k;
  t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'REWORK',(rw->>'sent_pcs')::numeric,ref);
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  if rw->>'status'='COMPLETED' and rw->'completion_posted'<>'true'::jsonb then
   return jsonb_build_object('status','UNKNOWN','reason','REWORK_COMPLETION_NOT_POSTED','source_id',rw->'id');end if;
  if rw->>'status'='COMPLETED' and (rw->>'completed_at')::timestamptz<=scope_at then
   if (rw->>'good_pcs')::numeric+(rw->>'bs_pcs')::numeric<>(rw->>'sent_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','REWORK_COMPLETION_MISMATCH','source_id',rw->'id');end if;
   k:='FGREWORK:'||(rw->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,dst,k,'FG',(rw->>'good_pcs')::numeric,ref);
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
   k:=src;n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,dst,k,'BS',(rw->>'bs_pcs')::numeric,ref);
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  end if;
 end loop;
 for d in select value from jsonb_array_elements(f->'resolutions') order by value->>'physical_at',value->>'id' loop
  b:=bsnodes->(d->>'bs_case_id');
  if b is null then return jsonb_build_object('status','CONFLICT','reason','DISPOSITION_BS_SOURCE_UNPROVEN','source_id',d->'id');end if;
  if d->'source_rework_order_id'<>'null'::jsonb then
   -- Same predicate over the reworks that carry this id, in source order.
   if reworks_by_id is null then
    select coalesce(jsonb_object_agg(z.k,z.v),'{}') into reworks_by_id from(select value->>'id' k,jsonb_agg(value order by ordinality) v
     from jsonb_array_elements(f->'reworks') with ordinality where value->>'id' is not null group by 1)z;
   end if;
   if not exists(select 1 from jsonb_array_elements(coalesce(reworks_by_id->(d->>'source_rework_order_id'),'[]'::jsonb)) rework_entry
     where rework_entry->>'id'=d->>'source_rework_order_id' and rework_entry->>'bs_case_id'=d->>'bs_case_id'
      and rework_entry->>'status'='COMPLETED' and rework_entry->'completion_posted'='true'::jsonb
      and (rework_entry->>'good_pcs')::numeric=(d->>'qty_pcs')::numeric
      and d->>'resolution_type' in ('REWORK_SEWING','REWORK_LAUNDRY')) then
    return jsonb_build_object('status','CONFLICT','reason','REWORK_RESOLUTION_LINEAGE_MISMATCH','source_id',d->'id');end if;
   continue;
  end if;
  if d->>'resolution_type' not in ('CASH_COMPENSATION','SCRAP','WRITE_OFF','OTHER') then
   return jsonb_build_object('status','UNKNOWN','reason','DISPOSITION_TYPE_UNPROVEN','source_id',d->'id');end if;
  pool:=b->>'pool';src:=b->>'node';ref:=cp7_wip.ref('erp.bs_resolutions',d->>'id',d->>'physical_at');
  if fg_by_resolution is null then
   select coalesce(jsonb_object_agg(z.k,z.v),'{}') into fg_by_resolution from(select value->>'bs_resolution_id' k,jsonb_agg(value order by ordinality) v
    from jsonb_array_elements(f->'bs_fg') with ordinality where value->>'bs_resolution_id' is not null and value->>'status'='POSTED' group by 1)z;
  end if;
  x:=coalesce(fg_by_resolution->(d->>'id'),'[]'::jsonb);cnt:=jsonb_array_length(x);
  if cnt>1 then return jsonb_build_object('status','CONFLICT','reason','DUPLICATE_BS_FG_DISPOSITION','source_id',d->'id');end if;
  if cnt=1 then
   x:=x->0;
   if x->>'bs_case_id'<>d->>'bs_case_id' or (x->>'qty_pcs')::numeric<>(d->>'qty_pcs')::numeric then
    return jsonb_build_object('status','CONFLICT','reason','BS_FG_DISPOSITION_MISMATCH','source_id',d->'id');end if;
   k:='FGDISPOSITION:'||(d->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'FG',(d->>'qty_pcs')::numeric,ref);
  else
   k:='DISPOSITION:'||(d->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'EXIT',(d->>'qty_pcs')::numeric,ref);
  end if;
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
 end loop;
 g:=g||jsonb_build_object('nodes',to_jsonb(nodes),'events',to_jsonb(events));
 positions:=cp7_wip.reconcile(g);
 if positions->>'status'<>'COMPLETE' then return positions;end if;
 -- A source reversal retires the case, including its historical hold state.
 -- Active children above still require an active physical case node.
 for b in select value from jsonb_array_elements(f->'bs') where value->>'status'<>'CANCELLED' loop
  if holds_by_case is null then
   select coalesce(jsonb_object_agg(z.k,z.v),'{}') into holds_by_case from(select value->>'bs_case_id' k,jsonb_agg(value order by ordinality) v
    from jsonb_array_elements(f->'holds') with ordinality where value->>'bs_case_id' is not null group by 1)z;
  end if;
  select value into held from jsonb_array_elements(coalesce(holds_by_case->(b->>'id'),'[]'::jsonb)) where value->>'bs_case_id'=b->>'id'
   order by (value->>'physical_at')::timestamptz desc,(value->>'created_at')::timestamptz desc,value->>'id' desc limit 1;
  if (b->>'status'='ON_HOLD') is distinct from coalesce(held->>'action'='HOLD',false) then
   return jsonb_build_object('status','UNKNOWN','reason','BS_HOLD_STATE_UNPROVEN','source_id',b->'id');end if;
  if b->>'status'='ON_HOLD' then
   x:=bsnodes->(b->>'id');src:=x->>'node';pool:=x->>'pool';
   if remaining is null then
    select coalesce(jsonb_object_agg(z.k,z.v),'{}') into remaining from(select distinct on(value->>'key')value->>'key' k,value->'remaining_pcs' v
     from jsonb_array_elements(positions->'positions') with ordinality where value->>'key' is not null order by value->>'key',ordinality)z;
   end if;
   qty:=(remaining->>src)::numeric;
   if qty is null or qty<=0 then return jsonb_build_object('status','CONFLICT','reason','BS_HOLD_QUANTITY_UNPROVEN','source_id',b->'id');end if;
   k:='HOLD:'||(b->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'HOLD',qty,cp7_wip.ref('erp.bs_case_hold_events',held->>'id',held->>'created_at'));
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  end if;
 end loop;
 return g||jsonb_build_object('nodes',to_jsonb(nodes),'events',to_jsonb(events));
end $$;
