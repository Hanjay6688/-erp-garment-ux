-- Graph construction from the explicit current-cutting capture. Group + exact
-- size is the shared pool while sewing lacks child/size completion attribution.
-- Batch IDs remain provenance, not independent copies of that pool's balance.
create function cp7_wip.transition(g jsonb,pool text,src text,dst text,stage text,qty numeric,ref jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare n jsonb;ev jsonb;key text;
begin
 if qty=0 then return g;end if;
 if qty<0 or trunc(qty)<>qty then raise exception 'CP7_WIP_TRANSITION_QUANTITY';end if;
 perform cp7_wip.refs(jsonb_build_array(ref));
 select value into n from jsonb_array_elements(g->'nodes') where value->>'key'=dst;
 if n is null then
  g:=jsonb_set(g,'{nodes}',g->'nodes'||jsonb_build_array(jsonb_build_object('key',dst,'pool_key',pool,'stage',stage,'refs',jsonb_build_array(ref))));
 elsif n->>'pool_key'<>pool or n->>'stage'<>stage then raise exception 'CP7_WIP_TRANSITION_NODE';end if;
 key:='T:'||jsonb_array_length(g->'events')::text;
 ev:=jsonb_build_object('key',key,'pool_key',pool,'from_node',src,'to_node',dst,'qty_pcs',qty::text,
  'ordinal',(jsonb_array_length(g->'events')+1)::text,'reverses_key',null,'refs',jsonb_build_array(ref));
 return jsonb_set(g,'{events}',g->'events'||jsonb_build_array(ev));
end $$;
create function cp7_wip.ref(kind text,id text,revision text) returns jsonb
language sql immutable security invoker set search_path='' as $$
 select jsonb_build_object('kind',kind,'id',id,'revision',revision)
$$;
create function cp7_wip.normalize_cutting(capture jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare f jsonb:=capture->'facts';g jsonb;grp jsonb;y record;d jsonb;s jsonb;r jsonb;q jsonb;b jsonb;rw jsonb;
 pool text;sz text;src text;dst text;ref jsonb;claim jsonb;line_id text;qty numeric;amt numeric;cnt integer;result jsonb;
 bsnodes jsonb:='{}';scope_at timestamptz:=(capture->>'captured_at')::timestamptz;
 pools jsonb[]:='{}';nodes jsonb[]:='{}';events jsonb[]:='{}';ne integer:=0;n jsonb;t jsonb;k text;h integer;here jsonb;
 nm jsonb[]:=array_fill('{}'::jsonb,array[1024]);dl jsonb[]:=array_fill('{}'::jsonb,array[1024]);rl jsonb[]:=array_fill('{}'::jsonb,array[1024]);
 fresh jsonb[];sizes jsonb;cases jsonb[]:='{}';by_group jsonb;by_yield_group jsonb;by_line jsonb;lineage jsonb;failed_lines jsonb;
 by_receipt jsonb;by_delivery jsonb;reversed_qc jsonb;reversed_receipts jsonb;
begin
 -- Linear form. The graph is built in arrays with a hashed node map and every
 -- move still goes through cp7_wip.transition on a graph that holds only the
 -- destination node, so each move checks and fails exactly as before. Derived
 -- delivery/receipt rows are kept per source line in hashed buckets, in their
 -- original order. Fact lookups use maps built where the first scan used to
 -- run; each map keeps the rows the scan matched, in source order, so the same
 -- rows are cast, summed and sorted and the same input fails at the same point.
 if capture->>'contract_version' is distinct from 'cp7.cutting-facts.v1' or capture->>'status' is distinct from 'COMPLETE' then
  return jsonb_build_object('status','UNKNOWN','reason','SOURCE_CAPTURE_INCOMPLETE');
 end if;
 if exists(select 1 from jsonb_array_elements(f->'groups') where value->'material_issue_posted'<>'true'::jsonb) then
  return jsonb_build_object('status','UNKNOWN','reason','CUTTING_NOT_POSTED');
 end if;
 if not cp7_wip.redispatch_valid(f) then
  return jsonb_build_object('status','CONFLICT','reason','REDISPATCH_RANGE_LINEAGE_CONFLICT');
 end if;
 for y in select value->>'group_id' group_id,value->>'size_id' size_id,sum((value->>'qty_pcs')::numeric) qty
  from jsonb_array_elements(f->'yields') group by 1,2 order by 1,2 loop
  if by_group is null then
   select coalesce(jsonb_object_agg(z.k,z.value),'{}') into by_group from(select distinct on(value->>'id')value->>'id' k,value
    from jsonb_array_elements(f->'groups') with ordinality where value->>'id' is not null order by value->>'id',ordinality)z;
  end if;
  grp:=by_group->y.group_id;
  pool:='CUT:'||y.group_id||':'||y.size_id;ref:=cp7_wip.ref('erp.cutting_groups',y.group_id,grp->>'revision');
  pools:=array_append(pools,jsonb_build_object('key',pool,'size_id',y.size_id,'input_pcs',y.qty::text,
   'origin','CUTTING','ownership','COMPANY','refs',jsonb_build_array(ref)));
  k:=pool||':PRE';n:=nm[(hashtext(k)&1023)+1]->k;
  t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,null,k,case when grp->'picked_up_at'='null'::jsonb then 'CUT_UNASSIGNED' else 'SEWING_UNRESOLVED' end,y.qty,ref);
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
 end loop;
 if exists(select 1 from jsonb_array_elements(f->'groups') x where not exists(select 1 from jsonb_array_elements(f->'yields') z where z->>'group_id'=x->>'id')) then
  return jsonb_build_object('status','UNKNOWN','reason','CUTTING_YIELDS_MISSING');
 end if;
 -- Normalize each active delivery's exact sizes. Legacy parent-only records
 -- resolve only when the entire group has one exact size, never by proportion.
 for d in select value from jsonb_array_elements(f->'deliveries') where value->>'status' not in ('DRAFT','REVERSED') order by value->>'physical_at',value->>'id' loop
  if by_line is null then
   select coalesce(jsonb_object_agg(z.k,z.v),'{}') into by_line from(select value->>'delivery_line_id' k,jsonb_agg(value order by ordinality) v
    from jsonb_array_elements(f->'delivery_sizes') with ordinality where value->>'delivery_line_id' is not null group by 1)z;
  end if;
  sizes:=coalesce(by_line->(d->>'id'),'[]'::jsonb);fresh:='{}';
  select count(*),coalesce(sum((value->>'qty_pcs')::numeric),0) into cnt,qty from jsonb_array_elements(sizes);
  if cnt=0 then
   if by_yield_group is null then
    select coalesce(jsonb_object_agg(z.k,jsonb_build_array(z.c,z.m)),'{}') into by_yield_group from(select value->>'group_id' k,
     count(distinct value->>'size_id') c,min(value->>'size_id') m from jsonb_array_elements(f->'yields') where value->>'group_id' is not null group by 1)z;
   end if;
   cnt:=coalesce((by_yield_group->(d->>'group_id')->>0)::integer,0);sz:=by_yield_group->(d->>'group_id')->>1;
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','DELIVERY_EXACT_SIZE_UNPROVEN','source_id',d->'id');end if;
   fresh:=array_append(fresh,jsonb_build_object('id',d->>'id','line',d->>'id','size',sz,'group',d->>'group_id','qty',d->>'qty_pcs'));
  else
   if qty<>(d->>'qty_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','DELIVERY_SIZE_TOTAL_MISMATCH','source_id',d->'id');end if;
   for s in select value from jsonb_array_elements(sizes) order by value->>'id' loop
    -- An explicit batch reference must point to posted distribution of that size.
    if lineage is null then
     select coalesce(jsonb_object_agg(z.k,true),'{}') into lineage from(select distinct jsonb_build_array(batch_entry->>'batch_id',batch_entry->>'group_id',yield_entry->>'size_id')::text k
      from jsonb_array_elements(f->'batches') batch_entry join jsonb_array_elements(f->'yields') yield_entry on yield_entry->>'id'=batch_entry->>'yield_id'
      where batch_entry->>'status'='POSTED' and batch_entry->>'batch_id' is not null and batch_entry->>'group_id' is not null and yield_entry->>'size_id' is not null)z;
    end if;
    if not coalesce(lineage ? jsonb_build_array(s->>'batch_id',d->>'group_id',s->>'size_id')::text and s->>'batch_id' is not null
      and d->>'group_id' is not null and s->>'size_id' is not null,false) then
     return jsonb_build_object('status','CONFLICT','reason','DELIVERY_BATCH_LINEAGE_UNPROVEN','source_id',s->'id');end if;
    fresh:=array_append(fresh,jsonb_build_object('id',s->>'id','line',d->>'id','size',s->>'size_id','group',d->>'group_id','qty',s->>'qty_pcs'));
   end loop;
  end if;
  if d->>'id' is not null and cardinality(fresh)>0 then
   h:=(hashtext(d->>'id')&1023)+1;here:=dl[h]||jsonb_build_object(d->>'id',coalesce(dl[h]->(d->>'id'),'[]'::jsonb)||to_jsonb(fresh));dl[h]:=here;
  end if;
  for s in select value from jsonb_array_elements(coalesce(dl[(hashtext(d->>'id')&1023)+1]->(d->>'id'),'[]'::jsonb)) order by value->>'id' loop
   sz:=s->>'size';pool:='CUT:'||(d->>'group_id')||':'||sz;ref:=cp7_wip.ref('erp.laundry_delivery_lines',d->>'id',d->>'revision');
   k:='D:'||(d->>'id')||':'||sz;n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,pool||':PRE',k,'LAUNDRY_OUTSTANDING',(s->>'qty')::numeric,ref);
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  end loop;
 end loop;
 for r in select value from jsonb_array_elements(f->'receipts') where value->>'status'='POSTED' order by value->>'physical_at',value->>'id' loop
  if failed_lines is null then
   select coalesce(jsonb_object_agg(z.k,true),'{}') into failed_lines from(select distinct value->>'receipt_line_id' k
    from jsonb_array_elements(f->'failed') where value->>'receipt_line_id' is not null)z;
  end if;
  if coalesce(failed_lines ? (r->>'id'),false) then
   if (r->>'good_pcs')::numeric+(r->>'bs_pcs')::numeric+(r->>'missing_pcs')::numeric+(r->>'stuck_pcs')::numeric<>0 then
    return jsonb_build_object('status','CONFLICT','reason','FAILED_ATTEMPT_IS_NOT_PHYSICAL_RECEIPT','source_id',r->'id');end if;
   -- Retry remains in the existing delivery. Full unprocessed returns have a
   -- REVERSED delivery, so the original resource remains in the shared PRE pool.
   -- Multiple failed invoices and redispatches never manufacture extra input.
   continue;
  end if;
  if by_receipt is null then
   select coalesce(jsonb_object_agg(z.k,z.v),'{}') into by_receipt from(select value->>'receipt_line_id' k,jsonb_agg(value order by ordinality) v
    from jsonb_array_elements(f->'receipt_sizes') with ordinality where value->>'receipt_line_id' is not null group by 1)z;
  end if;
  sizes:=coalesce(by_receipt->(r->>'id'),'[]'::jsonb);fresh:='{}';
  select count(*),coalesce(sum((value->>'good_pcs')::numeric+(value->>'bs_pcs')::numeric),0) into cnt,qty
   from jsonb_array_elements(sizes);
  if cnt=0 then
   select count(distinct value->>'size'),min(value->>'size') into cnt,sz from jsonb_array_elements(coalesce(dl[(hashtext(r->>'delivery_line_id')&1023)+1]->(r->>'delivery_line_id'),'[]'::jsonb));
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','RECEIPT_EXACT_SIZE_UNPROVEN','source_id',r->'id');end if;
   fresh:=array_append(fresh,jsonb_build_object('id',r->>'id','line',r->>'id','size',sz,'group',r->>'group_id','good',r->>'good_pcs','bs',r->>'bs_pcs'));
  else
   if qty<>(r->>'good_pcs')::numeric+(r->>'bs_pcs')::numeric
     or (select coalesce(sum((value->>'good_pcs')::numeric),0) from jsonb_array_elements(sizes))<>(r->>'good_pcs')::numeric
     or (select coalesce(sum((value->>'bs_pcs')::numeric),0) from jsonb_array_elements(sizes))<>(r->>'bs_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','RECEIPT_SIZE_TOTAL_MISMATCH','source_id',r->'id');end if;
   for s in select value from jsonb_array_elements(sizes) order by value->>'id' loop
    if not exists(select 1 from jsonb_array_elements(coalesce(dl[(hashtext(r->>'delivery_line_id')&1023)+1]->(r->>'delivery_line_id'),'[]'::jsonb)) delivery_entry where delivery_entry->>'id'=s->>'delivery_size_id' and delivery_entry->>'line'=r->>'delivery_line_id' and delivery_entry->>'size'=s->>'size_id') then
     return jsonb_build_object('status','CONFLICT','reason','RECEIPT_DELIVERY_LINEAGE_MISMATCH','source_id',s->'id');end if;
    fresh:=array_append(fresh,jsonb_build_object('id',s->>'id','line',r->>'id','size',s->>'size_id','group',r->>'group_id','good',s->>'good_pcs','bs',s->>'bs_pcs'));
   end loop;
  end if;
  if r->>'id' is not null and cardinality(fresh)>0 then
   h:=(hashtext(r->>'id')&1023)+1;here:=rl[h]||jsonb_build_object(r->>'id',coalesce(rl[h]->(r->>'id'),'[]'::jsonb)||to_jsonb(fresh));rl[h]:=here;
  end if;
  for s in select value from jsonb_array_elements(coalesce(rl[(hashtext(r->>'id')&1023)+1]->(r->>'id'),'[]'::jsonb)) order by value->>'id' loop
   sz:=s->>'size';pool:='CUT:'||(r->>'group_id')||':'||sz;src:='D:'||(r->>'delivery_line_id')||':'||sz;
   ref:=cp7_wip.ref('erp.laundry_receipt_lines',r->>'id',r->>'revision');
   k:='R:'||(r->>'id')||':'||sz;n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'AWAIT_QC',(s->>'good')::numeric,ref);
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
   k:='LBS:'||(r->>'id')||':'||sz;n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'BS',(s->>'bs')::numeric,ref);
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  end loop;
  if (r->>'missing_pcs')::numeric+(r->>'stuck_pcs')::numeric>0 then
   return jsonb_build_object('status','UNKNOWN','reason','LEGACY_RECEIPT_CUSTODY_REQUIRES_RECONCILIATION','source_id',r->'id');
  end if;
 end loop;
 -- Missing/stuck claims consume unreturned input once. A financial settlement
 -- does not recreate the lost/held goods. Rejected claims cease to reserve it.
 for claim in select value from jsonb_array_elements(f->'claims') where value->>'claim_type' in ('MISSING','STUCK')
  and value->>'status'<>'REJECTED' order by value->>'opened_at',value->>'id' loop
  line_id:=null;
  if claim->'receipt_line_id'<>'null'::jsonb then
   return jsonb_build_object('status','CONFLICT','reason','MISSING_STUCK_CLAIM_REQUIRES_DELIVERY_SOURCE','source_id',claim->'id');
  end if;
  if by_delivery is null then
   select coalesce(jsonb_object_agg(z.k,jsonb_build_array(z.c,z.m)),'{}') into by_delivery from(select value->>'delivery_id' k,count(*) c,min(value->>'id') m
    from jsonb_array_elements(f->'deliveries') where value->>'delivery_id' is not null group by 1)z;
  end if;
  cnt:=coalesce((by_delivery->(claim->>'delivery_id')->>0)::integer,0);line_id:=by_delivery->(claim->>'delivery_id')->>1;
  if cnt<>1 or (claim->>'delivery_line_count')::int<>1 then line_id:=null;end if;
  select count(distinct value->>'size'),min(value->>'size'),min(value->>'group') into cnt,sz,pool
   from jsonb_array_elements(coalesce(dl[(hashtext(line_id)&1023)+1]->(line_id),'[]'::jsonb));
  if line_id is null or cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','CLAIM_EXACT_SIZE_OR_SOURCE_UNPROVEN','source_id',claim->'id');end if;
  pool:='CUT:'||pool||':'||sz;src:='D:'||line_id||':'||sz;
  k:='CLAIM:'||(claim->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
  t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,claim->>'claim_type',(claim->>'qty_pcs')::numeric,cp7_wip.ref('erp.laundry_claims',claim->>'id',claim->>'revision'));
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
 end loop;
 for q in select value from jsonb_array_elements(f->'qc') where value->>'status'='POSTED' order by value->>'physical_at',value->>'id' loop
  sz:=q->>'size_id';pool:='CUT:'||(q->>'group_id')||':'||sz;src:=pool||':PRE';
  if q->'receipt_line_id'<>'null'::jsonb then
   if not exists(select 1 from jsonb_array_elements(coalesce(rl[(hashtext(q->>'receipt_line_id')&1023)+1]->(q->>'receipt_line_id'),'[]'::jsonb)) receipt_entry where receipt_entry->>'line'=q->>'receipt_line_id' and receipt_entry->>'size'=sz
     and (q->'receipt_size_id'='null'::jsonb or receipt_entry->>'id'=q->>'receipt_size_id')) then
    return jsonb_build_object('status','CONFLICT','reason','QC_RECEIPT_LINEAGE_MISMATCH','source_id',q->'id');end if;
   src:='R:'||(q->>'receipt_line_id')||':'||sz;
  elsif q->'receipt_size_id'<>'null'::jsonb then return jsonb_build_object('status','CONFLICT','reason','QC_RECEIPT_PARENT_MISSING','source_id',q->'id');end if;
  ref:=cp7_wip.ref('erp.qc_inspection_items',q->>'id',q->>'revision');
  k:='FGQC:'||(q->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
  t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'FG',(q->>'good_pcs')::numeric,ref);
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  k:='BSQC:'||(q->>'id');n:=nm[(hashtext(k)&1023)+1]->k;
  t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'BS',(q->>'bs_pcs')::numeric,ref);
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
 end loop;
 -- Cases identify original BS; resolutions/rework returns do not add cut input.
 for b in select value from jsonb_array_elements(f->'bs') order by value->>'physical_at',value->>'id' loop
  -- Ordinary source reversal retains the cancelled case as history. Keep it
  -- in the captured dependency set, but do not recreate its physical slice.
  -- A cancellation may only suppress a linked source that was also reversed.
  if b->>'status'='CANCELLED' then
   if b->'qc_item_id'<>'null'::jsonb then
    if reversed_qc is null then
     select coalesce(jsonb_object_agg(z.k,true),'{}') into reversed_qc from(select distinct jsonb_build_array(value->>'id',value->>'group_id')::text k
      from jsonb_array_elements(f->'qc') where value->>'status'='REVERSED' and value->>'id' is not null and value->>'group_id' is not null)z;
    end if;
    if not coalesce(reversed_qc ? jsonb_build_array(b->>'qc_item_id',b->>'group_id')::text and b->>'qc_item_id' is not null and b->>'group_id' is not null,false) then
     return jsonb_build_object('status','CONFLICT','reason','CANCELLED_BS_SOURCE_UNPROVEN','source_id',b->'id');end if;
   elsif b->'receipt_line_id'<>'null'::jsonb then
    if reversed_receipts is null then
     select coalesce(jsonb_object_agg(z.k,true),'{}') into reversed_receipts from(select distinct jsonb_build_array(value->>'id',value->>'group_id')::text k
      from jsonb_array_elements(f->'receipts') where value->>'status'='REVERSED' and value->>'id' is not null and value->>'group_id' is not null)z;
    end if;
    if not coalesce(reversed_receipts ? jsonb_build_array(b->>'receipt_line_id',b->>'group_id')::text and b->>'receipt_line_id' is not null and b->>'group_id' is not null,false) then
     return jsonb_build_object('status','CONFLICT','reason','CANCELLED_BS_SOURCE_UNPROVEN','source_id',b->'id');end if;
   else return jsonb_build_object('status','UNKNOWN','reason','CANCELLED_BS_SOURCE_UNPROVEN','source_id',b->'id');end if;
   continue;
  end if;
  sz:=b->>'size_id';
  if sz is null then
   if by_yield_group is null then
    select coalesce(jsonb_object_agg(z.k,jsonb_build_array(z.c,z.m)),'{}') into by_yield_group from(select value->>'group_id' k,
     count(distinct value->>'size_id') c,min(value->>'size_id') m from jsonb_array_elements(f->'yields') where value->>'group_id' is not null group by 1)z;
   end if;
   cnt:=coalesce((by_yield_group->(b->>'group_id')->>0)::integer,0);sz:=by_yield_group->(b->>'group_id')->>1;
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','BS_EXACT_SIZE_UNPROVEN','source_id',b->'id');end if;end if;
  pool:='CUT:'||(b->>'group_id')||':'||sz;
  if b->'qc_item_id'<>'null'::jsonb then src:='BSQC:'||(b->>'qc_item_id');
  elsif b->'receipt_line_id'<>'null'::jsonb then src:='LBS:'||(b->>'receipt_line_id')||':'||sz;
  else
   src:='BSMANUAL:'||(b->>'id');
   k:=src;n:=nm[(hashtext(k)&1023)+1]->k;
   t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,pool||':PRE',k,'BS',(b->>'qty_pcs')::numeric,cp7_wip.ref('erp.bs_cases',b->>'id',b->>'revision'));
   if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
    if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
   if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  end if;
  if not coalesce((nm[(hashtext(src)&1023)+1]->src)->>'pool_key'=pool,false) then
   return jsonb_build_object('status','CONFLICT','reason','BS_SOURCE_LINEAGE_MISMATCH','source_id',b->'id');end if;
  -- Several laundry cases may share a size-level receipt node. Give each case
  -- its own slice before HOLD/rework; never hold the whole shared receipt twice.
  dst:='BSCASE:'||(b->>'id');
  k:=dst;n:=nm[(hashtext(k)&1023)+1]->k;
  t:=cp7_wip.transition(jsonb_build_object('nodes',case when n is null then '[]'::jsonb else jsonb_build_array(n) end,'events','[]'::jsonb),pool,src,k,'BS',(b->>'qty_pcs')::numeric,cp7_wip.ref('erp.bs_cases',b->>'id',b->>'revision'));
  if n is null and jsonb_array_length(t->'nodes')=1 then n:=t->'nodes'->0;nodes:=array_append(nodes,n);
   if k is not null then h:=(hashtext(k)&1023)+1;here:=nm[h]||jsonb_build_object(k,n);nm[h]:=here;end if;end if;
  if jsonb_array_length(t->'events')=1 then here:=(t->'events'->0)||jsonb_build_object('key','T:'||ne,'ordinal',(ne+1)::text);events:=array_append(events,here);ne:=ne+1;end if;
  cases:=array_append(cases,jsonb_build_object(b->>'id',jsonb_build_object('pool',pool,'node',dst)));
 end loop;
 -- The last case with an id names its node, as successive merges did.
 select coalesce(jsonb_object_agg(z.key,z.value),'{}') into bsnodes from(select distinct on(e.key)e.key,e.value
  from unnest(cases) with ordinality c(item,o) cross join jsonb_each(c.item) e order by e.key,c.o desc)z;
 g:=jsonb_build_object('contract_version','cp7.wip-graph.v1','snapshot_id',capture->>'captured_at','complete',true,
  'pools',to_jsonb(pools),'nodes',to_jsonb(nodes),'events',to_jsonb(events));
 g:=cp7_wip.settle_bs(g,f,bsnodes,scope_at);
 if g ? 'status' then return g;end if;
 result:=cp7_wip.reconcile(g);
 return result||jsonb_build_object('graph',g,'source_basis','CUTTING_GROUP_EXACT_SIZE_SHARED_POOL',
  'fg_basis','PRODUCTION_DISPOSITION_NOT_CURRENT_ON_HAND','sewing_detail','SUBSTAGE_NOT_ALLOCATABLE_FROM_GROUP_EVENTS',
  'scope','SELECTED_CUTTING_GROUPS_ONLY_NO_OPENING_OR_NON_PO',
  'partial_rework_basis','REPORTED_RETURN_REMAINS_WIP_UNTIL_COMPLETION_POSTED',
  'allocation_review_required',exists(select 1 from jsonb_array_elements(f->'flags') where value->>'status'='OPEN' and value->>'flag_type' in ('PENDING_CORRECTION','PENDING_REVERSAL')),
  'attention',coalesce((select jsonb_agg(value order by value->>'id') from jsonb_array_elements(f->'flags') where value->>'status'='OPEN'),'[]'::jsonb),
  'rewash_review_required',exists(select 1 from jsonb_array_elements(f->'failed') attempt_entry join jsonb_array_elements(f->'receipts') receipt_entry on receipt_entry->>'id'=attempt_entry->>'receipt_line_id' where receipt_entry->>'status'='POSTED'),
  'rewash_basis','RETRY_REMAINS_IN_DELIVERY_RETURN_UNPROCESSED_REUSES_ORIGINAL_POOL');
end $$;