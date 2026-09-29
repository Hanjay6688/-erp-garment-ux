create function cp7_wip.normalize_other(capture jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare f jsonb:=capture->'facts';g jsonb;origin jsonb;x jsonb;c jsonb;b jsonb;ref jsonb;result jsonb;bsnodes jsonb:='{}';
 at_time timestamptz:=(capture->>'captured_at')::timestamptz;pool text;src text;stage text;qty numeric;recovered numeric;cnt integer;
begin
 if capture->>'contract_version' is distinct from 'cp7.other-wip-facts.v1' or capture->>'status' is distinct from 'COMPLETE' then
  return jsonb_build_object('status','UNKNOWN','reason','OTHER_SOURCE_CAPTURE_INCOMPLETE');end if;
 g:=jsonb_build_object('contract_version','cp7.wip-graph.v1','snapshot_id',capture->>'captured_at','complete',true,'pools','[]'::jsonb,'nodes','[]'::jsonb,'events','[]'::jsonb);
 for origin in select value from jsonb_array_elements(f->'origins') order by value->>'id' loop
  stage:=null;
  if origin->>'header_status'<>'POSTED' or origin->>'batch_status'<>'POSTED' then return jsonb_build_object('status','UNKNOWN','reason','OPENING_NOT_POSTED','source_id',origin->'id');end if;
  if origin->>'size_id' is null then return jsonb_build_object('status','UNKNOWN','reason','OPENING_SIZE_UNPROVEN','source_id',origin->'id');end if;
  if (origin->>'opening_qty_pcs')::numeric is distinct from cp7_wip.pcs(origin->'qty_pcs') then
   return jsonb_build_object('status','CONFLICT','reason','OPENING_ORIGIN_QUANTITY_MISMATCH','source_id',origin->'id');end if;
  pool:='OPEN:'||(origin->>'id');src:=pool||':PRE';ref:=cp7_wip.ref('erp.initial_import_production_sources',origin->>'id',origin->>'batch_id');
  g:=jsonb_set(g,'{pools}',g->'pools'||jsonb_build_array(jsonb_build_object('key',pool,'size_id',origin->'size_id','input_pcs',origin->'qty_pcs',
   'origin','OPENING','ownership',case when origin->>'customer_id' is null then 'COMPANY' else 'CUSTOMER' end,'refs',jsonb_build_array(ref))));
  if origin->>'balance_type'='BS' and origin->>'bs_case_id' is not null then
   stage:='BS';bsnodes:=bsnodes||jsonb_build_object(origin->>'bs_case_id',jsonb_build_object('pool',pool,'node',src));
  elsif origin->>'balance_type'='WIP' and origin->>'bs_case_id' is null then
   stage:=case origin->>'stage' when 'CUTTING' then 'CUT_UNASSIGNED' when 'SEWING' then 'SEWING_UNRESOLVED' when 'LAUNDRY' then 'LAUNDRY_OUTSTANDING' when 'QC' then 'AWAIT_QC' end;
   if stage='CUT_UNASSIGNED' then
    select count(*) into cnt from jsonb_array_elements(f->'pickups') where value->>'opening_item_id'=origin->>'id'
      and (value->>'reversed_at' is null or (value->>'reversed_at')::timestamptz>at_time);
    if cnt>1 then return jsonb_build_object('status','CONFLICT','reason','OPENING_MULTIPLE_ACTIVE_PICKUPS','source_id',origin->'id');end if;
    if cnt=1 then stage:='SEWING_UNRESOLVED';end if;
   end if;
  end if;
  if stage is null then return jsonb_build_object('status','UNKNOWN','reason','OPENING_STAGE_UNPROVEN','source_id',origin->'id');end if;
  g:=cp7_wip.transition(g,pool,null,src,stage,cp7_wip.pcs(origin->'qty_pcs'),ref);
  for x in select value from jsonb_array_elements(f->'outputs') where value->>'opening_item_id'=origin->>'id'
    and (value->>'reversed_at' is null or (value->>'reversed_at')::timestamptz>at_time) order by value->>'physical_at',value->>'id' loop
   if x->>'size_id' is distinct from origin->>'size_id' then return jsonb_build_object('status','CONFLICT','reason','OPENING_OUTPUT_SIZE_MISMATCH','source_id',x->'id');end if;
   g:=cp7_wip.transition(g,pool,src,'FGOPEN:'||(x->>'id'),'FG',cp7_wip.pcs(x->'qty_pcs'),cp7_wip.ref('erp.initial_import_wip_outputs',x->>'id',x->>'physical_at'));
  end loop;
  for x in select value from jsonb_array_elements(f->'splits') where value->>'opening_item_id'=origin->>'id'
    and (value->>'reversed_at' is null or (value->>'reversed_at')::timestamptz>at_time) order by value->>'physical_at',value->>'id' loop
   if x->>'size_id' is distinct from origin->>'size_id' or bsnodes ? (x->>'bs_case_id') then return jsonb_build_object('status','CONFLICT','reason','OPENING_SPLIT_LINEAGE_MISMATCH','source_id',x->'id');end if;
   g:=cp7_wip.transition(g,pool,src,'BSOPEN:'||(x->>'id'),'BS',cp7_wip.pcs(x->'qty_pcs'),cp7_wip.ref('erp.bb_wip_bs_splits_v1',x->>'id',x->>'physical_at'));
   bsnodes:=bsnodes||jsonb_build_object(x->>'bs_case_id',jsonb_build_object('pool',pool,'node','BSOPEN:'||(x->>'id')));
  end loop;
  for c in select value from jsonb_array_elements(f->'claims') where value->>'opening_item_id'=origin->>'id'
    and (value->>'cancelled_at' is null or (value->>'cancelled_at')::timestamptz>at_time) order by value->>'id' loop
   select coalesce(sum((value->>'qty_pcs')::numeric),0) into recovered from jsonb_array_elements(f->'claim_events')
    where value->>'claim_id'=c->>'id' and value->>'event_kind'='RECOVER'
    and (value->>'reversed_at' is null or (value->>'reversed_at')::timestamptz>at_time);
   qty:=cp7_wip.pcs(c->'qty_pcs')-recovered;
   if qty<0 or c->>'claim_type' not in ('MISSING','STUCK') then return jsonb_build_object('status','CONFLICT','reason','OPENING_CLAIM_RECONCILIATION','source_id',c->'id');end if;
   -- Settlement changes the monetary right, never makes these pieces GOOD.
   g:=cp7_wip.transition(g,pool,src,'OPENCLAIM:'||(c->>'id'),c->>'claim_type',qty,cp7_wip.ref('erp.bd_opening_laundry_claims_v1',c->>'id',c->>'revision'));
  end loop;
 end loop;
 for origin in select value from jsonb_array_elements(f->'non_po') order by value->>'id' loop
  if origin->>'size_id' is null then return jsonb_build_object('status','UNKNOWN','reason','UNSOURCED_BS_SIZE_UNPROVEN','source_id',origin->'id');end if;
  pool:='NONPO:'||(origin->>'id');src:=pool||':BS';ref:=cp7_wip.ref('erp.bs_cases',origin->>'id',origin->>'revision');
  g:=jsonb_set(g,'{pools}',g->'pools'||jsonb_build_array(jsonb_build_object('key',pool,'size_id',origin->'size_id','input_pcs',origin->'qty_pcs',
   'origin','NON_PO','ownership','COMPANY','refs',jsonb_build_array(ref))));
  g:=cp7_wip.transition(g,pool,null,src,'BS',cp7_wip.pcs(origin->'qty_pcs'),ref);
  bsnodes:=bsnodes||jsonb_build_object(origin->>'id',jsonb_build_object('pool',pool,'node',src));
 end loop;
 for b in select value from jsonb_array_elements(f->'bs') loop
  if not bsnodes ? (b->>'id') then return jsonb_build_object('status','CONFLICT','reason','OTHER_BS_ORIGIN_UNPROVEN','source_id',b->'id');end if;
 end loop;
 if (select count(*) from jsonb_each(bsnodes))<>jsonb_array_length(f->'bs') then return jsonb_build_object('status','CONFLICT','reason','OTHER_BS_CASE_MISSING');end if;
 g:=cp7_wip.settle_bs(g,f,bsnodes,at_time);
 if g ? 'status' then return g;end if;
 result:=cp7_wip.reconcile(g);
 return result||jsonb_build_object('graph',g,'source_basis','EXPLICIT_OPENING_OR_UNSOURCED_ORIGIN',
  'fg_basis','PRODUCTION_DISPOSITION_NOT_CURRENT_ON_HAND');
end $$;
