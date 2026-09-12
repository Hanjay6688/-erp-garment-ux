-- O counterexamples and P controls for return-adjusted invoice match state.
-- Requires the disposable CP6 fixture plus m_*, n_* and o_* temporary helpers.
create function pg_temp.p_state(p_purchase uuid) returns jsonb language sql as $$
  select jsonb_build_object(
    'match_state',i.invoice_match_state,'price_state',i.price_state,
    'capacity',erp.material_purchase_invoice_capacity(i.id),
    'invoiced',erp.material_purchase_posted_invoice_qty(i.id),
    'grni_return',erp.material_purchase_grni_return_qty(i.id),
    'ap',erp.material_purchase_final_ap_total(i.purchase_id),
    'grni',erp.material_purchase_grni_total(i.purchase_id),
    'report',pg_temp.m_report(),
    'p_issues',case when exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.proname='run_v267_financial_truth_checks'
        and pg_get_functiondef(p.oid) like '%V2620P_SUPPLIER_RETURN_MATCH_STATE%')
      then (select issue_count from erp.run_v267_financial_truth_checks()
        where check_name='V2620P_SUPPLIER_RETURN_MATCH_STATE') else null end
  )
  from erp.material_purchase_items i where i.purchase_id=p_purchase
$$;

create function pg_temp.p_post_return(p_purchase uuid,p_qtys numeric[]) returns uuid
language plpgsql as $$
declare v_return uuid;
begin
  v_return:=pg_temp.o_return_draft(p_purchase,p_qtys,null);
  perform erp.post_material_supplier_return(v_return);
  return v_return;
end
$$;

create function pg_temp.p_case(p_case text,p_fixed boolean) returns jsonb
language plpgsql as $$
declare
  v_purchase uuid;v_invoice uuid;v_return uuid;v_first uuid;
  v_before jsonb;v_posted jsonb;v_after jsonb;v_fault jsonb;v_restored jsonb;
begin
  if pg_temp.m_report()<>'READY' then raise exception 'P_CLEAN_BASELINE_REQUIRED';end if;
  if p_case='ONE_DOCUMENT_CLOSES_REMAINING_GRNI' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);v_before:=pg_temp.p_state(v_purchase);
    v_return:=pg_temp.p_post_return(v_purchase,array[5,5]);v_after:=pg_temp.p_state(v_purchase);
    if (v_before->>'match_state')<>'PARTIAL' or (v_after->>'capacity')::numeric<>5
       or (v_after->>'invoiced')::numeric<>5 or (v_after->>'ap')::numeric<>0
       or (v_after->>'grni')::numeric<>0 then raise exception 'P_ONE_DOCUMENT_FACT_MISMATCH';end if;
  elsif p_case='TWO_DOCUMENTS_CLOSE_REMAINING_GRNI' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);v_before:=pg_temp.p_state(v_purchase);
    v_first:=pg_temp.p_post_return(v_purchase,array[5,0]);
    v_return:=pg_temp.p_post_return(v_purchase,array[0,5]);v_after:=pg_temp.p_state(v_purchase);
    if (v_after->>'capacity')::numeric<>5 or (v_after->>'invoiced')::numeric<>5
       or (v_after->>'ap')::numeric<>0 or (v_after->>'grni')::numeric<>0 then
      raise exception 'P_TWO_DOCUMENT_FACT_MISMATCH';end if;
  elsif p_case='RETURN_REVERSE_RESTORE' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);v_before:=pg_temp.p_state(v_purchase);
    v_return:=pg_temp.p_post_return(v_purchase,array[5,5]);v_posted:=pg_temp.p_state(v_purchase);
    perform erp.reverse_material_supplier_return(v_return,'P exact match-state inverse');
    v_after:=pg_temp.p_state(v_purchase);
    if (v_after->>'match_state')<>'PARTIAL' or (v_after->>'price_state')<>'PARTIAL'
       or (v_after->>'capacity')::numeric<>10 or (v_after->>'invoiced')::numeric<>5
       or (v_after->>'ap')::numeric<>50 or (v_after->>'grni')::numeric<>50 then
      raise exception 'P_RETURN_INVERSE_STATE_MISMATCH';end if;
  elsif p_case='PARTIAL_REMAINS_PARTIAL' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);
    v_return:=pg_temp.p_post_return(v_purchase,array[3,3]);v_after:=pg_temp.p_state(v_purchase);
    if (v_after->>'match_state')<>'PARTIAL' or (v_after->>'price_state')<>'PARTIAL'
       or (v_after->>'capacity')::numeric<>9 or (v_after->>'grni')::numeric<>40 then
      raise exception 'P_PARTIAL_CONTROL_MISMATCH';end if;
  elsif p_case='NO_INVOICE_FULL_RETURN' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_return:=pg_temp.p_post_return(v_purchase,array[5,5]);v_after:=pg_temp.p_state(v_purchase);
    if (v_after->>'match_state')<>'UNMATCHED' or (v_after->>'price_state')<>'ESTIMATED'
       or (v_after->>'capacity')::numeric<>0 or (v_after->>'grni')::numeric<>0 then
      raise exception 'P_UNMATCHED_CONTROL_MISMATCH';end if;
  elsif p_case='DIRECT_FINAL_FULL_RETURN' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,true);
    v_return:=pg_temp.p_post_return(v_purchase,array[5,5]);v_after:=pg_temp.p_state(v_purchase);
    if (v_after->>'match_state')<>'DIRECT_FINAL' or (v_after->>'price_state')<>'FINAL'
       or (v_after->>'ap')::numeric<>0 or (v_after->>'grni')::numeric<>0 then
      raise exception 'P_DIRECT_FINAL_CONTROL_MISMATCH';end if;
  elsif p_case='FOLLOWUP_INVOICE_CAPACITY_REFUSAL' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);
    v_return:=pg_temp.p_post_return(v_purchase,array[5,5]);v_before:=pg_temp.o_boundary();
    begin
      perform pg_temp.o_invoice(v_purchase,1,10);
      raise exception 'P_FOLLOWUP_OVERINVOICE_ACCEPTED';
    exception when raise_exception then
      if sqlerrm='P_FOLLOWUP_OVERINVOICE_ACCEPTED' then raise;end if;
    end;
    if v_before<>pg_temp.o_boundary() then raise exception 'P_FOLLOWUP_REFUSAL_NOT_ATOMIC';end if;
    v_after:=pg_temp.p_state(v_purchase);
  elsif p_case='MATCH_STATE_DETECTOR' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);v_before:=pg_temp.p_state(v_purchase);
    update erp.material_purchase_items set invoice_match_state='MATCHED',price_state='FINAL'
    where purchase_id=v_purchase;
    v_fault:=pg_temp.p_state(v_purchase);
    perform erp.refresh_material_purchase_item_match_state(id)
    from erp.material_purchase_items where purchase_id=v_purchase;
    v_restored:=pg_temp.p_state(v_purchase);v_after:=v_restored;
    if (v_restored->>'report')<>'READY' then raise exception 'P_DETECTOR_RESTORE_FAILED';end if;
  elsif p_case='O_ALLOCATION_DETECTOR_SCOPE' then
    v_purchase:=pg_temp.o_purchase(array[5,5],10,false);
    v_invoice:=pg_temp.o_invoice(v_purchase,5,10);
    v_return:=pg_temp.p_post_return(v_purchase,array[3,3]);v_before:=pg_temp.p_state(v_purchase);
    alter table erp.material_supplier_return_items
      disable trigger trg_parent_status_guard_material_supplier_return_items;
    with ordered as(select id,row_number() over(order by id) ord
      from erp.material_supplier_return_items where return_id=v_return)
    update erp.material_supplier_return_items ri
    set ap_relief_qty_snapshot=case when o.ord=1 then 2 else 3 end,
        grni_relief_qty_snapshot=case when o.ord=1 then 1 else 0 end
    from ordered o where ri.id=o.id;
    alter table erp.material_supplier_return_items
      enable trigger trg_parent_status_guard_material_supplier_return_items;
    v_fault:=jsonb_build_object('report',pg_temp.m_report(),
      'o_issues',(select issue_count from erp.run_v267_financial_truth_checks()
        where check_name='V2620O_SUPPLIER_RETURN_ALLOCATION'));
    alter table erp.material_supplier_return_items
      disable trigger trg_parent_status_guard_material_supplier_return_items;
    with allocation as(
      select id,qty,greatest(least(qty,5-coalesce(sum(qty) over(
        order by id rows between unbounded preceding and 1 preceding),0)),0) ap_qty
      from erp.material_supplier_return_items where return_id=v_return
    )
    update erp.material_supplier_return_items ri
    set ap_relief_qty_snapshot=a.ap_qty,grni_relief_qty_snapshot=a.qty-a.ap_qty,
        ap_relief_amount_snapshot=a.ap_qty*ri.supplier_credit_unit_price,
        grni_relief_amount_snapshot=(a.qty-a.ap_qty)*10
    from allocation a where ri.id=a.id;
    alter table erp.material_supplier_return_items
      enable trigger trg_parent_status_guard_material_supplier_return_items;
    v_restored:=pg_temp.p_state(v_purchase);v_after:=v_restored;
    if (v_restored->>'report')<>'READY' then raise exception 'P_O_DETECTOR_RESTORE_FAILED state=% issues=%',v_restored,pg_temp.m_issues();end if;
  else raise exception 'P_UNKNOWN_CASE: %',p_case;end if;

  if p_case in('ONE_DOCUMENT_CLOSES_REMAINING_GRNI','TWO_DOCUMENTS_CLOSE_REMAINING_GRNI') then
    if p_fixed and ((v_after->>'match_state')<>'MATCHED' or (v_after->>'price_state')<>'FINAL') then
      raise exception 'P_VALID_RETURN_LEFT_STALE_STATE: %',v_after;
    elsif not p_fixed and ((v_after->>'match_state')<>'PARTIAL' or (v_after->>'price_state')<>'PARTIAL') then
      raise exception 'P_O_COUNTEREXAMPLE_NOT_REPRODUCED: %',v_after;
    end if;
  elsif p_case='RETURN_REVERSE_RESTORE' then
    if p_fixed and ((v_posted->>'match_state')<>'MATCHED' or (v_posted->>'price_state')<>'FINAL') then
      raise exception 'P_INVERSE_POST_STATE_NOT_FIXED';
    elsif not p_fixed and ((v_posted->>'match_state')<>'PARTIAL' or (v_posted->>'price_state')<>'PARTIAL') then
      raise exception 'P_INVERSE_O_COUNTEREXAMPLE_NOT_REPRODUCED';end if;
  elsif p_case='MATCH_STATE_DETECTOR' then
    if p_fixed and ((v_fault->>'report')<>'BLOCKED' or (v_fault->>'p_issues')::bigint<>1) then
      raise exception 'P_MATCH_STATE_FAULT_NOT_DETECTED: %',v_fault;
    elsif not p_fixed and (v_fault->>'report')<>'READY' then
      raise exception 'P_O_DETECTOR_GAP_NOT_REPRODUCED: %',v_fault;end if;
  elsif p_case='O_ALLOCATION_DETECTOR_SCOPE' then
    if (v_fault->>'o_issues')::bigint<>1 then raise exception 'P_O_ALLOCATION_FAULT_NOT_CREATED';end if;
    if p_fixed and (v_fault->>'report')<>'BLOCKED' then
      raise exception 'P_O_ALLOCATION_FAULT_NOT_CONNECTED: %',v_fault;
    elsif not p_fixed and (v_fault->>'report')<>'READY' then
      raise exception 'P_O_ALLOCATION_SCOPE_GAP_NOT_REPRODUCED: %',v_fault;end if;
  end if;
  if pg_temp.m_report()<>'READY' then raise exception 'P_CASE_REPORT_NOT_READY';end if;
  return jsonb_build_object('status',case when p_fixed then 'PASS'
      when p_case in('ONE_DOCUMENT_CLOSES_REMAINING_GRNI','TWO_DOCUMENTS_CLOSE_REMAINING_GRNI',
        'RETURN_REVERSE_RESTORE','MATCH_STATE_DETECTOR','O_ALLOCATION_DETECTOR_SCOPE') then 'KNOWN_O_BUG_REPRODUCED'
      else 'CONTROL_PASS' end,'case',p_case,'before',v_before,'posted',v_posted,
      'after',v_after,'fault',v_fault,'restored',v_restored,'report',pg_temp.m_report());
end
$$;
