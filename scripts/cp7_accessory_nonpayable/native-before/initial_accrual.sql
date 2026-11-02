CREATE OR REPLACE FUNCTION erp.post_accessory_reimbursement_accrual(p_lot_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  v_hpp numeric(24,6);
  v_reimburse numeric(24,6);
  v_entitlement_total numeric(24,6);
  v_variance numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
  v_contractor uuid;
  v_contractor_count integer;
begin
  perform erp.require_internal();
  perform erp.ensure_fg_accessory_cost_snapshot(p_lot_id);
  select * into l from erp.fg_lots where id=p_lot_id;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select coalesce(sum(total_hpp_cost),0),coalesce(sum(total_reimbursement),0)
  into v_hpp,v_reimburse
  from erp.fg_accessory_cost_snapshots where lot_id=l.id;
  if v_hpp=0 and v_reimburse=0 then return; end if;
  if exists(
    select 1 from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
      and source_id=l.id and status='POSTED'
  ) then return; end if;
  select count(distinct e.contractor_id),
    (array_agg(distinct e.contractor_id order by e.contractor_id))[1],
    coalesce(sum(e.amount),0)
  into v_contractor_count,v_contractor,v_entitlement_total
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.lot_id=l.id and e.payroll_status<>'CANCELLED';
  if abs(v_entitlement_total-v_reimburse)>0.005 then
    raise exception 'Accessory entitlement total does not match immutable snapshot reimbursement';
  end if;
  if v_reimburse>0 and v_contractor_count<>1 then
    raise exception 'Accessory reimbursement requires exactly one authoritative Mandor';
  end if;
  if v_hpp>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','WIP','debit',round(v_hpp,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  v_variance:=v_reimburse-v_hpp;
  if v_variance>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',round(v_variance,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  elsif v_variance< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',0,'credit',round(abs(v_variance),2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_reimburse,2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse=0 and v_hpp>0 then
    raise exception 'Accessory HPP snapshot has cost but zero Mandor reimbursement; configure reimbursement or use normal material issue flow';
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal(
      'ACCESSORY_REIMBURSE_ACCRUAL',l.id,(l.produced_at AT TIME ZONE 'Asia/Jakarta')::date,
      'Selected accessory HPP + Mandor reimbursement from GOOD rework/FG',v_lines
    );
  end if;
end
$function$
