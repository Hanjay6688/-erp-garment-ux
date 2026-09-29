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
 pool text;sz text;src text;dst text;ref jsonb;qty numeric;amt numeric;cnt integer;result jsonb;
 drows jsonb:='[]';rrows jsonb:='[]';bsnodes jsonb:='{}';scope_at timestamptz:=(capture->>'captured_at')::timestamptz;
begin
 if capture->>'contract_version' is distinct from 'cp7.cutting-facts.v1' or capture->>'status' is distinct from 'COMPLETE' then
  return jsonb_build_object('status','UNKNOWN','reason','SOURCE_CAPTURE_INCOMPLETE');
 end if;
 if exists(select 1 from jsonb_array_elements(f->'groups') where value->'material_issue_posted'<>'true'::jsonb) then
  return jsonb_build_object('status','UNKNOWN','reason','CUTTING_NOT_POSTED');
 end if;
 -- Exceptional custody needs its own range normalization; do not publish an
 -- ordinary-delivery balance when returned/reused participants exist.
 if jsonb_array_length(f->'failed')>0 or jsonb_array_length(f->'redispatch')>0 then
  return jsonb_build_object('status','UNKNOWN','reason','REWASH_PARTICIPANTS_REQUIRE_NORMALIZATION');
 end if;
 g:=jsonb_build_object('contract_version','cp7.wip-graph.v1','snapshot_id',capture->>'captured_at','complete',true,'pools','[]'::jsonb,'nodes','[]'::jsonb,'events','[]'::jsonb);
 for y in select value->>'group_id' group_id,value->>'size_id' size_id,sum((value->>'qty_pcs')::numeric) qty
  from jsonb_array_elements(f->'yields') group by 1,2 order by 1,2 loop
  select value into grp from jsonb_array_elements(f->'groups') where value->>'id'=y.group_id;
  pool:='CUT:'||y.group_id||':'||y.size_id;ref:=cp7_wip.ref('erp.cutting_groups',y.group_id,grp->>'revision');
  g:=jsonb_set(g,'{pools}',g->'pools'||jsonb_build_array(jsonb_build_object('key',pool,'size_id',y.size_id,'input_pcs',y.qty::text,
   'origin','CUTTING','ownership','COMPANY','refs',jsonb_build_array(ref))));
  g:=cp7_wip.transition(g,pool,null,pool||':PRE',case when grp->'picked_up_at'='null'::jsonb then 'CUT_UNASSIGNED' else 'SEWING_UNRESOLVED' end,y.qty,ref);
 end loop;
 if exists(select 1 from jsonb_array_elements(f->'groups') x where not exists(select 1 from jsonb_array_elements(f->'yields') z where z->>'group_id'=x->>'id')) then
  return jsonb_build_object('status','UNKNOWN','reason','CUTTING_YIELDS_MISSING');
 end if;
 -- Normalize each active delivery's exact sizes. Legacy parent-only records
 -- resolve only when the entire group has one exact size, never by proportion.
 for d in select value from jsonb_array_elements(f->'deliveries') where value->>'status' not in ('DRAFT','REVERSED') order by value->>'physical_at',value->>'id' loop
  select count(*),coalesce(sum((value->>'qty_pcs')::numeric),0) into cnt,qty from jsonb_array_elements(f->'delivery_sizes') where value->>'delivery_line_id'=d->>'id';
  if cnt=0 then
   select count(distinct value->>'size_id'),min(value->>'size_id') into cnt,sz from jsonb_array_elements(f->'yields') where value->>'group_id'=d->>'group_id';
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','DELIVERY_EXACT_SIZE_UNPROVEN','source_id',d->'id');end if;
   drows:=drows||jsonb_build_array(jsonb_build_object('id',d->>'id','line',d->>'id','size',sz,'group',d->>'group_id','qty',d->>'qty_pcs'));
  else
   if qty<>(d->>'qty_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','DELIVERY_SIZE_TOTAL_MISMATCH','source_id',d->'id');end if;
   for s in select value from jsonb_array_elements(f->'delivery_sizes') where value->>'delivery_line_id'=d->>'id' order by value->>'id' loop
    -- An explicit batch reference must point to posted distribution of that size.
    if not exists(select 1 from jsonb_array_elements(f->'batches') a join jsonb_array_elements(f->'yields') y on y->>'id'=a->>'yield_id'
       where a->>'batch_id'=s->>'batch_id' and a->>'group_id'=d->>'group_id' and a->>'status'='POSTED' and y->>'size_id'=s->>'size_id') then
     return jsonb_build_object('status','CONFLICT','reason','DELIVERY_BATCH_LINEAGE_UNPROVEN','source_id',s->'id');end if;
    drows:=drows||jsonb_build_array(jsonb_build_object('id',s->>'id','line',d->>'id','size',s->>'size_id','group',d->>'group_id','qty',s->>'qty_pcs'));
   end loop;
  end if;
  for s in select value from jsonb_array_elements(drows) where value->>'line'=d->>'id' order by value->>'id' loop
   sz:=s->>'size';pool:='CUT:'||(d->>'group_id')||':'||sz;ref:=cp7_wip.ref('erp.laundry_delivery_lines',d->>'id',d->>'revision');
   g:=cp7_wip.transition(g,pool,pool||':PRE','D:'||(d->>'id')||':'||sz,'LAUNDRY_OUTSTANDING',(s->>'qty')::numeric,ref);
  end loop;
 end loop;
 for r in select value from jsonb_array_elements(f->'receipts') where value->>'status'='POSTED' order by value->>'physical_at',value->>'id' loop
  select count(*),coalesce(sum((value->>'good_pcs')::numeric+(value->>'bs_pcs')::numeric),0) into cnt,qty
   from jsonb_array_elements(f->'receipt_sizes') where value->>'receipt_line_id'=r->>'id';
  if cnt=0 then
   select count(distinct value->>'size'),min(value->>'size') into cnt,sz from jsonb_array_elements(drows) where value->>'line'=r->>'delivery_line_id';
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','RECEIPT_EXACT_SIZE_UNPROVEN','source_id',r->'id');end if;
   rrows:=rrows||jsonb_build_array(jsonb_build_object('id',r->>'id','line',r->>'id','size',sz,'group',r->>'group_id','good',r->>'good_pcs','bs',r->>'bs_pcs'));
  else
   if qty<>(r->>'good_pcs')::numeric+(r->>'bs_pcs')::numeric
     or (select coalesce(sum((value->>'good_pcs')::numeric),0) from jsonb_array_elements(f->'receipt_sizes') where value->>'receipt_line_id'=r->>'id')<>(r->>'good_pcs')::numeric
     or (select coalesce(sum((value->>'bs_pcs')::numeric),0) from jsonb_array_elements(f->'receipt_sizes') where value->>'receipt_line_id'=r->>'id')<>(r->>'bs_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','RECEIPT_SIZE_TOTAL_MISMATCH','source_id',r->'id');end if;
   for s in select value from jsonb_array_elements(f->'receipt_sizes') where value->>'receipt_line_id'=r->>'id' order by value->>'id' loop
    if not exists(select 1 from jsonb_array_elements(drows) d where d->>'id'=s->>'delivery_size_id' and d->>'line'=r->>'delivery_line_id' and d->>'size'=s->>'size_id') then
     return jsonb_build_object('status','CONFLICT','reason','RECEIPT_DELIVERY_LINEAGE_MISMATCH','source_id',s->'id');end if;
    rrows:=rrows||jsonb_build_array(jsonb_build_object('id',s->>'id','line',r->>'id','size',s->>'size_id','group',r->>'group_id','good',s->>'good_pcs','bs',s->>'bs_pcs'));
   end loop;
  end if;
  for s in select value from jsonb_array_elements(rrows) where value->>'line'=r->>'id' order by value->>'id' loop
   sz:=s->>'size';pool:='CUT:'||(r->>'group_id')||':'||sz;src:='D:'||(r->>'delivery_line_id')||':'||sz;
   ref:=cp7_wip.ref('erp.laundry_receipt_lines',r->>'id',r->>'revision');
   g:=cp7_wip.transition(g,pool,src,'R:'||(r->>'id')||':'||sz,'AWAIT_QC',(s->>'good')::numeric,ref);
   g:=cp7_wip.transition(g,pool,src,'LBS:'||(r->>'id')||':'||sz,'BS',(s->>'bs')::numeric,ref);
  end loop;
  if (r->>'missing_pcs')::numeric+(r->>'stuck_pcs')::numeric>0 then
   select count(distinct value->>'size'),min(value->>'size') into cnt,sz from jsonb_array_elements(drows) where value->>'line'=r->>'delivery_line_id';
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','MISSING_STUCK_SIZE_UNPROVEN','source_id',r->'id');end if;
   pool:='CUT:'||(r->>'group_id')||':'||sz;src:='D:'||(r->>'delivery_line_id')||':'||sz;ref:=cp7_wip.ref('erp.laundry_receipt_lines',r->>'id',r->>'revision');
   g:=cp7_wip.transition(g,pool,src,'MISSING:'||(r->>'id'),'MISSING',(r->>'missing_pcs')::numeric,ref);
   g:=cp7_wip.transition(g,pool,src,'STUCK:'||(r->>'id'),'STUCK',(r->>'stuck_pcs')::numeric,ref);
  end if;
 end loop;
 for q in select value from jsonb_array_elements(f->'qc') where value->>'status'='POSTED' order by value->>'physical_at',value->>'id' loop
  sz:=q->>'size_id';pool:='CUT:'||(q->>'group_id')||':'||sz;src:=pool||':PRE';
  if q->'receipt_line_id'<>'null'::jsonb then
   if not exists(select 1 from jsonb_array_elements(rrows) r where r->>'line'=q->>'receipt_line_id' and r->>'size'=sz
     and (q->'receipt_size_id'='null'::jsonb or r->>'id'=q->>'receipt_size_id')) then
    return jsonb_build_object('status','CONFLICT','reason','QC_RECEIPT_LINEAGE_MISMATCH','source_id',q->'id');end if;
   src:='R:'||(q->>'receipt_line_id')||':'||sz;
  elsif q->'receipt_size_id'<>'null'::jsonb then return jsonb_build_object('status','CONFLICT','reason','QC_RECEIPT_PARENT_MISSING','source_id',q->'id');end if;
  ref:=cp7_wip.ref('erp.qc_inspection_items',q->>'id',q->>'revision');
  g:=cp7_wip.transition(g,pool,src,'FGQC:'||(q->>'id'),'FG',(q->>'good_pcs')::numeric,ref);
  g:=cp7_wip.transition(g,pool,src,'BSQC:'||(q->>'id'),'BS',(q->>'bs_pcs')::numeric,ref);
 end loop;
 -- Cases identify original BS; resolutions/rework returns do not add cut input.
 for b in select value from jsonb_array_elements(f->'bs') order by value->>'physical_at',value->>'id' loop
  sz:=b->>'size_id';
  if sz is null then select count(distinct value->>'size_id'),min(value->>'size_id') into cnt,sz from jsonb_array_elements(f->'yields') where value->>'group_id'=b->>'group_id';
   if cnt<>1 then return jsonb_build_object('status','UNKNOWN','reason','BS_EXACT_SIZE_UNPROVEN','source_id',b->'id');end if;end if;
  pool:='CUT:'||(b->>'group_id')||':'||sz;
  if b->'qc_item_id'<>'null'::jsonb then src:='BSQC:'||(b->>'qc_item_id');
  elsif b->'receipt_line_id'<>'null'::jsonb then src:='LBS:'||(b->>'receipt_line_id')||':'||sz;
  else
   src:='BSMANUAL:'||(b->>'id');
   g:=cp7_wip.transition(g,pool,pool||':PRE',src,'BS',(b->>'qty_pcs')::numeric,cp7_wip.ref('erp.bs_cases',b->>'id',b->>'revision'));
  end if;
  if not exists(select 1 from jsonb_array_elements(g->'nodes') n where n->>'key'=src and n->>'pool_key'=pool) then
   return jsonb_build_object('status','CONFLICT','reason','BS_SOURCE_LINEAGE_MISMATCH','source_id',b->'id');end if;
  bsnodes:=bsnodes||jsonb_build_object(b->>'id',jsonb_build_object('pool',pool,'node',src));
 end loop;
 for rw in select value from jsonb_array_elements(f->'reworks') where value->>'status'<>'CANCELLED' order by value->>'physical_sent_at',value->>'id' loop
  b:=bsnodes->(rw->>'bs_case_id');
  if b is null then return jsonb_build_object('status','UNKNOWN','reason','REWORK_BS_SOURCE_UNPROVEN','source_id',rw->'id');end if;
  pool:=b->>'pool';src:=b->>'node';dst:='REWORK:'||(rw->>'id');ref:=cp7_wip.ref('erp.rework_orders',rw->>'id',rw->>'revision');
  g:=cp7_wip.transition(g,pool,src,dst,'REWORK',(rw->>'sent_pcs')::numeric,ref);
  if rw->>'status'='PARTIAL' then return jsonb_build_object('status','UNKNOWN','reason','PARTIAL_REWORK_RETURN_TIME_UNPROVEN','source_id',rw->'id');end if;
  if rw->>'status'='COMPLETED' and (rw->>'completed_at')::timestamptz<=scope_at then
   if (rw->>'good_pcs')::numeric+(rw->>'bs_pcs')::numeric<>(rw->>'sent_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','REWORK_COMPLETION_MISMATCH','source_id',rw->'id');end if;
   g:=cp7_wip.transition(g,pool,dst,'FGREWORK:'||(rw->>'id'),'FG',(rw->>'good_pcs')::numeric,ref);
   g:=cp7_wip.transition(g,pool,dst,src,'BS',(rw->>'bs_pcs')::numeric,ref);
  end if;
 end loop;
 result:=cp7_wip.reconcile(g);
 return result||jsonb_build_object('graph',g,'source_basis','CUTTING_GROUP_EXACT_SIZE_SHARED_POOL',
  'fg_basis','PRODUCTION_DISPOSITION_NOT_CURRENT_ON_HAND','sewing_detail','SUBSTAGE_NOT_ALLOCATABLE_FROM_GROUP_EVENTS',
  'scope','SELECTED_CUTTING_GROUPS_ONLY_NO_OPENING_OR_NON_PO');
end $$;
