-- bootstrap lines 7570-7628
CREATE OR REPLACE FUNCTION erp.complete_rework_order_v2(p_rework_order_id uuid, p_qty_good integer, p_qty_bs integer, p_completed_at timestamp with time zone, p_return_fg_location_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_order erp.rework_orders%rowtype;v_case erp.bs_cases%rowtype;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason),'') is null then raise exception 'Completion reason is required'; end if;
  if p_completed_at is null or p_completed_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Valid non-future completed_at is required';
  end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'rework_order_id',p_rework_order_id,'good',p_qty_good,'bs',p_qty_bs,
    'completed_at',p_completed_at,'location',p_return_fg_location_id,
    'reason',btrim(p_reason),'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('complete_rework_order_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_order from erp.rework_orders where id=p_rework_order_id for update;
  if v_order.id is null then raise exception 'Rework order not found'; end if;
  if v_order.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_order.row_version;
  end if;
  if v_order.status not in('OPEN','IN_PROGRESS','PARTIAL') or v_order.cost_posted then
    raise exception 'Only active unposted rework can be completed';
  end if;
  if coalesce(p_qty_good,0)<0 or coalesce(p_qty_bs,0)<0
     or coalesce(p_qty_good,0)+coalesce(p_qty_bs,0)<>v_order.qty_sent then
    raise exception 'Completion must reconcile exactly: GOOD + BS = qty sent';
  end if;
  if v_order.destination_type='CONTRACTOR' and not exists(
    select 1 from erp.rework_component_lines where rework_order_id=v_order.id
  ) then raise exception 'Contractor rework requires component lines'; end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  update erp.rework_orders
  set qty_good_returned=coalesce(p_qty_good,0),qty_bs_returned=coalesce(p_qty_bs,0),
      completed_at=p_completed_at,status='COMPLETED',
      return_fg_location_id=coalesce(p_return_fg_location_id,return_fg_location_id),
      notes=concat_ws(E'\n',notes,'COMPLETED: '||btrim(p_reason)),updated_at=now()
  where id=v_order.id;
  perform erp.post_rework_completion(v_order.id);
  select * into v_order from erp.rework_orders where id=v_order.id;
  select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
  v_response:=jsonb_build_object(
    'rework_order_id',v_order.id,'status',v_order.status,'row_version',v_order.row_version,
    'cost_posted',v_order.cost_posted,'good_fg_lot_id',v_order.good_fg_lot_id,
    'bs_case_id',v_case.id,'bs_case_status',v_case.status,'bs_case_row_version',v_case.row_version
  );
  return erp._idempotency_complete('complete_rework_order_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."complete_rework_order_v2"(p_rework_order_id uuid, p_qty_good integer, p_qty_bs integer, p_completed_at timestamp with time zone, p_return_fg_location_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
