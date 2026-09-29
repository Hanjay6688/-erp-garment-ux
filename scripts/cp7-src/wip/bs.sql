-- Apply each case's existing BS resource through rework, disposition and HOLD.
-- Resolution rows for rework GOOD are provenance, not a second FG movement.
create function cp7_wip.settle_bs(g jsonb,f jsonb,bsnodes jsonb,scope_at timestamptz) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare rw jsonb;b jsonb;d jsonb;x jsonb;held jsonb;positions jsonb;ref jsonb;
 pool text;src text;dst text;qty numeric;cnt integer;
begin
 for rw in select value from jsonb_array_elements(f->'reworks') where value->>'status'<>'CANCELLED' order by value->>'physical_sent_at',value->>'id' loop
  b:=bsnodes->(rw->>'bs_case_id');
  if b is null then return jsonb_build_object('status','UNKNOWN','reason','REWORK_BS_SOURCE_UNPROVEN','source_id',rw->'id');end if;
  pool:=b->>'pool';src:=b->>'node';dst:='REWORK:'||(rw->>'id');ref:=cp7_wip.ref('erp.rework_orders',rw->>'id',rw->>'revision');
  g:=cp7_wip.transition(g,pool,src,dst,'REWORK',(rw->>'sent_pcs')::numeric,ref);
  if rw->>'status'='COMPLETED' and rw->'completion_posted'<>'true'::jsonb then
   return jsonb_build_object('status','UNKNOWN','reason','REWORK_COMPLETION_NOT_POSTED','source_id',rw->'id');end if;
  if rw->>'status'='COMPLETED' and (rw->>'completed_at')::timestamptz<=scope_at then
   if (rw->>'good_pcs')::numeric+(rw->>'bs_pcs')::numeric<>(rw->>'sent_pcs')::numeric then return jsonb_build_object('status','CONFLICT','reason','REWORK_COMPLETION_MISMATCH','source_id',rw->'id');end if;
   g:=cp7_wip.transition(g,pool,dst,'FGREWORK:'||(rw->>'id'),'FG',(rw->>'good_pcs')::numeric,ref);
   g:=cp7_wip.transition(g,pool,dst,src,'BS',(rw->>'bs_pcs')::numeric,ref);
  end if;
 end loop;
 for d in select value from jsonb_array_elements(f->'resolutions') order by value->>'physical_at',value->>'id' loop
  b:=bsnodes->(d->>'bs_case_id');
  if b is null then return jsonb_build_object('status','CONFLICT','reason','DISPOSITION_BS_SOURCE_UNPROVEN','source_id',d->'id');end if;
  if d->'source_rework_order_id'<>'null'::jsonb then
   if not exists(select 1 from jsonb_array_elements(f->'reworks') rework_entry
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
  select count(*) into cnt from jsonb_array_elements(f->'bs_fg') receipt_entry
   where receipt_entry->>'bs_resolution_id'=d->>'id' and receipt_entry->>'status'='POSTED';
  if cnt>1 then return jsonb_build_object('status','CONFLICT','reason','DUPLICATE_BS_FG_DISPOSITION','source_id',d->'id');end if;
  if cnt=1 then
   select value into x from jsonb_array_elements(f->'bs_fg') where value->>'bs_resolution_id'=d->>'id' and value->>'status'='POSTED';
   if x->>'bs_case_id'<>d->>'bs_case_id' or (x->>'qty_pcs')::numeric<>(d->>'qty_pcs')::numeric then
    return jsonb_build_object('status','CONFLICT','reason','BS_FG_DISPOSITION_MISMATCH','source_id',d->'id');end if;
   g:=cp7_wip.transition(g,pool,src,'FGDISPOSITION:'||(d->>'id'),'FG',(d->>'qty_pcs')::numeric,ref);
  else
   g:=cp7_wip.transition(g,pool,src,'DISPOSITION:'||(d->>'id'),'EXIT',(d->>'qty_pcs')::numeric,ref);
  end if;
 end loop;
 positions:=cp7_wip.reconcile(g);
 if positions->>'status'<>'COMPLETE' then return positions;end if;
 -- A source reversal retires the case, including its historical hold state.
 -- Active children above still require an active physical case node.
 for b in select value from jsonb_array_elements(f->'bs') where value->>'status'<>'CANCELLED' loop
  select value into held from jsonb_array_elements(f->'holds') where value->>'bs_case_id'=b->>'id'
   order by (value->>'physical_at')::timestamptz desc,(value->>'created_at')::timestamptz desc,value->>'id' desc limit 1;
  if (b->>'status'='ON_HOLD') is distinct from coalesce(held->>'action'='HOLD',false) then
   return jsonb_build_object('status','UNKNOWN','reason','BS_HOLD_STATE_UNPROVEN','source_id',b->'id');end if;
  if b->>'status'='ON_HOLD' then
   x:=bsnodes->(b->>'id');src:=x->>'node';pool:=x->>'pool';
   select (value->>'remaining_pcs')::numeric into qty from jsonb_array_elements(positions->'positions') where value->>'key'=src;
   if qty is null or qty<=0 then return jsonb_build_object('status','CONFLICT','reason','BS_HOLD_QUANTITY_UNPROVEN','source_id',b->'id');end if;
   g:=cp7_wip.transition(g,pool,src,'HOLD:'||(b->>'id'),'HOLD',qty,cp7_wip.ref('erp.bs_case_hold_events',held->>'id',held->>'created_at'));
  end if;
 end loop;
 return g;
end $$;
