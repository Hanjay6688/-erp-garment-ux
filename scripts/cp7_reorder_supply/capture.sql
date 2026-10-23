-- Retain the actual global projected-good/ETA budgets before K3 cleanup.
-- No yield math, queue, matching or allocation is repeated here.
create function cp7_reorder_supply.budgets(wip jsonb,etas jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare p jsonb;e jsonb;k text;seen jsonb:='{}';eta_seen jsonb:='{}';by_eta jsonb;
 qty text;at_text text;rows jsonb[]:='{}';
begin
 if jsonb_typeof(wip)is distinct from'object'then raise exception 'CP7_REORDER_CAPTURE_WIP_SHAPE';end if;
 if wip->>'status'is distinct from'COMPLETE'then
  return jsonb_build_object('contract_version','cp7.reorder-supply-budget.v1','status','UNKNOWN',
   'snapshot_id',wip->'snapshot_id','rows',null,'reason','GLOBAL_WIP_INCOMPLETE');
 end if;
 if wip->>'contract_version'is distinct from'cp7.wip-position.v1'then raise exception 'CP7_REORDER_CAPTURE_WIP_CONTRACT';end if;
 perform cp7_wip.key(wip->'snapshot_id');perform cp7_demand.items(wip->'positions',1000);perform cp7_demand.items(etas,1000);
 for e in select value from jsonb_array_elements(etas)loop
  k:=cp7_wip.key(e->'position_key');
  if eta_seen?k then raise exception 'CP7_REORDER_CAPTURE_DUPLICATE_ETA';end if;eta_seen:=eta_seen||jsonb_build_object(k,true);
  if jsonb_typeof(e->'result')is distinct from'object'or jsonb_typeof(e->'result'->'status')is distinct from'string'then raise exception 'CP7_REORDER_CAPTURE_ETA_SHAPE';end if;
 end loop;
 select coalesce(jsonb_object_agg(x->>'position_key',x->'result'),'{}')into by_eta from jsonb_array_elements(etas)x;
 for p in select value from jsonb_array_elements(wip->'positions')loop
  k:=cp7_wip.key(p->'key');
  if seen?k then raise exception 'CP7_REORDER_CAPTURE_DUPLICATE_POSITION';end if;seen:=seen||jsonb_build_object(k,true);
  if jsonb_typeof(p->'eligible_company_wip')is distinct from'boolean'then raise exception 'CP7_REORDER_CAPTURE_ELIGIBILITY_UNKNOWN';end if;
  if p->'eligible_company_wip'='false'::jsonb then continue;end if;
  perform cp7_wip.key(p->'size_id');
  if jsonb_typeof(p->'projection')is distinct from'object'or p->'projection'->>'quality'is null
   or p->'projection'->>'quality'not in('SCENARIO','UNKNOWN')then raise exception 'CP7_REORDER_CAPTURE_PROJECTION_SHAPE';end if;
  qty:=null;at_text:=null;
  if p->'projection'->>'quality'='SCENARIO'then
   qty:=cp7_wip.pcs(p->'projection'->'projected_good_pcs')::text;
  end if;
  e:=by_eta->k;
  if e->>'status'in('KNOWN','CONDITIONAL')then
   -- remaining_eta() emits a typed timestamptz as JSON in UTC (+00:00),
   -- while netting stores cp7_planning.utc() text. Accept these absolute UTC
   -- forms only, validate the actual instant, and use that same formatter.
   at_text:=e->>'eta';
   if jsonb_typeof(e->'eta')is distinct from'string'then raise exception 'CP7_REORDER_CAPTURE_ETA_UNKNOWN';end if;
   if right(at_text,6)='+00:00'then at_text:=left(at_text,length(at_text)-6)||'Z';end if;
   at_text:=cp7_planning.utc(cp7_demand.instant(to_jsonb(at_text)));
  end if;
  rows:=array_append(rows,jsonb_build_object('physical_key',k,'snapshot_id',wip->'snapshot_id',
   'size_id',p->'size_id','projected_good_pcs',qty,'eta',at_text,'eligible',true));
 end loop;
 return jsonb_build_object('contract_version','cp7.reorder-supply-budget.v1','status','COMPLETE',
  'snapshot_id',wip->'snapshot_id','rows',to_jsonb(rows),'reason',null);
end $$;
alter function cp7_reorder_supply.budgets(jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_supply.budgets(jsonb,jsonb)from public,anon,authenticated,service_role;
