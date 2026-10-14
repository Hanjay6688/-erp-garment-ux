-- bootstrap lines 17086-17182
CREATE OR REPLACE FUNCTION erp.resolve_bs_case_disposition_v2(p_bs_case_id uuid, p_resolution_type text, p_qty_pcs integer, p_compensation_amount numeric, p_source_laundry_claim_id uuid, p_physical_at timestamp with time zone, p_notes text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_type text:=upper(coalesce(p_resolution_type,''));
  v_hash text;v_cached jsonb;v_response jsonb;
  v_case erp.bs_cases%rowtype;v_claim erp.laundry_claims%rowtype;
  v_resolved integer;v_in_rework integer;v_remaining integer;
  v_used_amount numeric(20,2);v_used_qty integer;v_resolution uuid;
begin
  perform erp.require_internal();
  if v_type not in('CASH_COMPENSATION','SCRAP','WRITE_OFF','OTHER') then
    raise exception 'Disposition must be CASH_COMPENSATION, SCRAP, WRITE_OFF, or OTHER';
  end if;
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if coalesce(p_qty_pcs,0)<=0 then raise exception 'qty_pcs must be positive'; end if;
  if p_physical_at is null or p_physical_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Valid non-future physical_at is required';
  end if;
  if nullif(btrim(p_notes),'') is null then raise exception 'Disposition reason/notes are required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'bs_case_id',p_bs_case_id,'type',v_type,'qty',p_qty_pcs,
    'amount',coalesce(p_compensation_amount,0),'claim',p_source_laundry_claim_id,
    'physical_at',p_physical_at,'notes',btrim(p_notes),'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('resolve_bs_case_disposition_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null then raise exception 'BS case not found'; end if;
  if v_case.status not in('OPEN','PARTIAL','IN_REWORK') then raise exception 'BS case is already closed/cancelled'; end if;
  if v_case.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
  end if;
  if p_physical_at<v_case.physical_at then raise exception 'Disposition cannot predate BS detection'; end if;
  select coalesce(sum(qty_pcs),0)::integer into v_resolved from erp.bs_resolutions where bs_case_id=v_case.id;
  select coalesce(sum(qty_sent),0)::integer into v_in_rework from erp.rework_orders
  where bs_case_id=v_case.id and status in('OPEN','IN_PROGRESS','PARTIAL');
  v_remaining:=greatest(v_case.qty_pcs-v_resolved-v_in_rework,0);
  if p_qty_pcs>v_remaining then
    raise exception 'Disposition qty % exceeds currently available unresolved/non-rework qty %',p_qty_pcs,v_remaining;
  end if;

  if v_type='CASH_COMPENSATION' then
    if p_source_laundry_claim_id is null then raise exception 'CASH_COMPENSATION requires a settled laundry claim'; end if;
    if coalesce(p_compensation_amount,0)<=0 then raise exception 'CASH_COMPENSATION amount must be positive'; end if;
    select * into v_claim from erp.laundry_claims where id=p_source_laundry_claim_id for update;
    if v_claim.id is null or v_claim.status<>'SETTLED' then raise exception 'Linked laundry claim must be SETTLED'; end if;
    if v_case.responsible_vendor_id is null or v_claim.vendor_id<>v_case.responsible_vendor_id then
      raise exception 'Linked claim vendor does not match the BS responsible vendor';
    end if;
    if v_case.source_laundry_receipt_line_id is not null and not(
      v_claim.receipt_line_id=v_case.source_laundry_receipt_line_id
      or v_claim.delivery_id=(
        select lr.delivery_id from erp.laundry_receipt_lines l
        join erp.laundry_receipts lr on lr.id=l.receipt_id
        where l.id=v_case.source_laundry_receipt_line_id
      )
    ) then raise exception 'Linked claim does not belong to the BS laundry source'; end if;
    select coalesce(sum(compensation_amount),0),coalesce(sum(qty_pcs),0)::integer
    into v_used_amount,v_used_qty from erp.bs_resolutions
    where source_laundry_claim_id=v_claim.id;
    if v_used_amount+coalesce(p_compensation_amount,0)>v_claim.compensation_amount+0.005 then
      raise exception 'BS cash dispositions exceed settled laundry claim compensation';
    end if;
    if v_used_qty+p_qty_pcs>v_claim.qty_claimed then
      raise exception 'BS cash disposition qty exceeds settled laundry claim qty';
    end if;
  else
    if coalesce(p_compensation_amount,0)<>0 or p_source_laundry_claim_id is not null then
      raise exception 'Only CASH_COMPENSATION may carry claim/compensation amount';
    end if;
  end if;
  perform set_config('app.change_reason',btrim(p_notes),true);
  insert into erp.bs_resolutions(
    bs_case_id,resolution_type,qty_pcs,compensation_amount,
    responsible_contractor_id,responsible_vendor_id,
    source_laundry_claim_id,physical_at,notes
  ) values(
    v_case.id,v_type,p_qty_pcs,coalesce(p_compensation_amount,0),
    v_case.responsible_contractor_id,v_case.responsible_vendor_id,
    p_source_laundry_claim_id,p_physical_at,btrim(p_notes)
  ) returning id into v_resolution;
  perform erp.refresh_bs_case_status(v_case.id);
  select * into v_case from erp.bs_cases where id=v_case.id;
  v_response:=jsonb_build_object(
    'bs_resolution_id',v_resolution,'bs_case_id',v_case.id,'status',v_case.status,
    'row_version',v_case.row_version,'resolution_type',v_type,'qty_pcs',p_qty_pcs
  );
  return erp._idempotency_complete('resolve_bs_case_disposition_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."resolve_bs_case_disposition_v2"(p_bs_case_id uuid, p_resolution_type text, p_qty_pcs integer, p_compensation_amount numeric, p_source_laundry_claim_id uuid, p_physical_at timestamp with time zone, p_notes text, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
