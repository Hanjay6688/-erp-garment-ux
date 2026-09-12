-- Independent exact numeric oracle: no production tolerance or cost helper
-- decides the expected quantity, completion state, or money vector.
-- Requires disposable M/N/O fixture helpers. Calls the owned V2 writer envelope.
create function pg_temp.q_invoice_draft(p_purchase uuid,p_qty numeric,p_price numeric default 10000)
returns jsonb language plpgsql as $$
declare v_payload jsonb;
begin
  select jsonb_build_object('invoice_number','Q-INV-'||gen_random_uuid(),
    'supplier_id',h.supplier_id,'invoice_date','2026-09-02',
    'change_reason','Q exact invoice quantity oracle','lines',jsonb_agg(
      jsonb_build_object('purchase_item_id',i.id,'qty_invoiced',p_qty,'unit_price',p_price)
      order by i.id)) into v_payload
  from erp.material_purchase_headers h join erp.material_purchase_items i on i.purchase_id=h.id
  where h.id=p_purchase group by h.id;
  return erp.save_material_supplier_invoice_draft_v2(v_payload,gen_random_uuid(),null);
end
$$;

create function pg_temp.q_post(p_draft jsonb,p_request uuid default gen_random_uuid())
returns jsonb language sql as $$
  select erp.post_material_supplier_invoice_v2((p_draft->>'supplier_invoice_id')::uuid,
    p_request,(p_draft->>'row_version')::bigint,'Q exact invoice quantity oracle')
$$;

create function pg_temp.q_state(p_purchase uuid) returns jsonb language sql as $$
  select jsonb_build_object('receipt_qty',i.qty,'match_state',i.invoice_match_state,
    'price_state',i.price_state,
    'matched',coalesce((select sum(l.qty_invoiced) from erp.material_supplier_invoice_lines l
      join erp.material_supplier_invoices h on h.id=l.invoice_id and h.status='POSTED'
      where l.purchase_item_id=i.id),0),
    'stock',coalesce((select sum(m.qty_signed) from erp.material_rolls r
      join erp.material_stock_movements m on m.roll_id=r.id where r.purchase_item_id=i.id),0),
    'ledger',pg_temp.n_ledger())
  from erp.material_purchase_items i where i.purchase_id=p_purchase
$$;

create function pg_temp.q_case(p_case text,p_fixed boolean) returns jsonb
language plpgsql as $$
declare
  v_purchase uuid;v_return uuid;v_invoice uuid;v_request uuid:=gen_random_uuid();
  v_draft jsonb;v_response jsonb;v_repeat jsonb;v_state jsonb;v_before jsonb;
  v_boundary jsonb;v_initial jsonb;v_fault jsonb;
  v_qty numeric:=1;v_invoice_qty numeric:=1;v_prior_qty numeric:=0;
  v_over boolean:=false;v_under boolean:=false;v_control boolean:=false;
  v_accepted boolean:=false;v_atomic boolean;v_code text;v_message text;
  v_definition text;v_identity text;v_count bigint;v_expected numeric;
begin
  if pg_temp.m_report()<>'READY' then raise exception 'Q_CLEAN_BASELINE_REQUIRED';end if;
  v_initial:=pg_temp.n_ledger();
  if p_case='OVER_ONE_MICRO' then v_invoice_qty:=1.000001;v_over:=true;
  elsif p_case='SPLIT_OVER_ONE_MICRO' then
    v_prior_qty:=.5;v_invoice_qty:=.500001;v_over:=true;
  elsif p_case='RETURN_ADJUSTED_OVER_ONE_MICRO' then
    v_qty:=2;v_invoice_qty:=1.000001;v_over:=true;
  elsif p_case='MICRO_REMAINDER_STATUS' then v_invoice_qty:=.999999;v_under:=true;
  elsif p_case='REVERSED_COMPLETION_STATUS' then v_invoice_qty:=.999999;v_under:=true;
  elsif p_case='DETECTOR_MICRO_OVER' or p_case='DETECTOR_MICRO_STATUS' then
    -- A tester temporarily replays the preserved P function in a subtransaction
    -- to model existing bad history. This is not an operator-access bypass claim.
    begin
      v_identity:=case when p_case='DETECTOR_MICRO_OVER'
        then 'erp.post_material_supplier_invoice(uuid)'
        else 'erp.refresh_material_purchase_item_match_state(uuid)' end;
      select pg_get_functiondef(to_regprocedure(v_identity)) into v_definition;
      if p_fixed then
        execute (select object_definition from erp.cp6_v2620q_rollback_capsule
          where object_regidentity=v_identity);
      end if;
      v_purchase:=pg_temp.o_purchase(array[1]::numeric[],10000,false);
      v_draft:=pg_temp.q_invoice_draft(v_purchase,
        case when p_case='DETECTOR_MICRO_OVER' then 1.000001 else .999999 end);
      perform pg_temp.q_post(v_draft);
      execute v_definition;
      select issue_count into v_count from erp.run_v267_financial_truth_checks()
      where check_name=case when p_case='DETECTOR_MICRO_OVER'
        then 'V267_INVOICE_MATCH_OVER_RECEIPT' else 'V2620P_SUPPLIER_RETURN_MATCH_STATE' end;
      v_fault:=jsonb_build_object('issue_count',v_count,'report',pg_temp.m_report(),
        'state',pg_temp.q_state(v_purchase),'tester_preserved_p_function',p_fixed);
      if v_count is distinct from (case when p_fixed then 1 else 0 end)
         or pg_temp.m_report() is distinct from (case when p_fixed then 'BLOCKED' else 'READY' end) then
        raise exception 'Q_DETECTOR_EXPECTATION_FAILED: %',v_fault;
      end if;
      raise exception 'Q_TESTER_ROLLBACK' using errcode='Q0001';
    exception when sqlstate 'Q0001' then null;
    end;
    if pg_temp.n_ledger() is distinct from v_initial then raise exception 'Q_FAULT_RESIDUE';end if;
    return jsonb_build_object('status',case when p_fixed then 'PASS' else 'KNOWN_P_BUG_REPRODUCED' end,
      'fault',v_fault,'fault_rolled_back',true);
  elsif p_case='EXACT_CAPACITY' then v_control:=true;
  elsif p_case='EXACT_SPLIT_COMPLETION' then v_prior_qty:=.5;v_invoice_qty:=.5;v_control:=true;
  elsif p_case='OVER_TWO_MICRO_REFUSED' then v_invoice_qty:=1.000002;v_over:=true;v_control:=true;
  elsif p_case='FULL_RETURN_MICRO_SPLIT' then v_invoice_qty:=.999999;v_control:=true;
  else raise exception 'Q_UNKNOWN_CASE: %',p_case;
  end if;

  v_purchase:=pg_temp.o_purchase(array[v_qty]::numeric[],10000,false);
  if p_case='RETURN_ADJUSTED_OVER_ONE_MICRO' then
    v_return:=pg_temp.o_return_draft(v_purchase,array[1]::numeric[],10000);
    perform erp.post_material_supplier_return(v_return);
  end if;
  if v_prior_qty>0 then
    perform pg_temp.q_post(pg_temp.q_invoice_draft(v_purchase,v_prior_qty));
  end if;
  v_draft:=pg_temp.q_invoice_draft(v_purchase,v_invoice_qty);
  v_before:=pg_temp.q_state(v_purchase);v_boundary:=pg_temp.o_boundary();
  begin
    v_response:=pg_temp.q_post(v_draft,v_request);v_accepted:=true;
  exception when sqlstate 'P0001' then
    get stacked diagnostics v_code=returned_sqlstate,v_message=message_text;
  end;
  v_atomic:=pg_temp.o_boundary() is not distinct from v_boundary;
  v_state:=pg_temp.q_state(v_purchase);
  if v_over then
    if p_fixed or v_control then
      if v_accepted or v_code is distinct from 'P0001' or not v_atomic
         or v_message not like 'Invoice quantity exceeds unmatched receipt quantity%' then
        raise exception 'Q_OVERCAP_NOT_ATOMIC: %',v_state;
      end if;
    else
      if not v_accepted or (v_state->>'matched')::numeric<>1.000001
         or (v_state->'ledger'->>'ap')::numeric-(v_initial->>'ap')::numeric<>10000.01
         or (v_state->'ledger'->>'variance')::numeric-(v_initial->>'variance')::numeric<>.01
         or (v_state->'ledger'->>'grni')::numeric-(v_initial->>'grni')::numeric<>0
         or (v_state->'ledger'->>'inventory')::numeric-(v_initial->>'inventory')::numeric<>10000
         or pg_temp.m_report()<>'READY' then raise exception 'Q_P_OVERCAP_NOT_REPRODUCED: %',v_state;end if;
    end if;
  else
    if not v_accepted then raise exception 'Q_LAWFUL_INVOICE_REJECTED: %',v_message;end if;
    v_boundary:=pg_temp.o_boundary();
    v_repeat:=pg_temp.q_post(v_draft,v_request);
    if v_repeat is distinct from v_response or pg_temp.o_boundary() is distinct from v_boundary then
      raise exception 'Q_REPLAY_CHANGED_BUSINESS_FACTS';
    end if;
    if p_case='REVERSED_COMPLETION_STATUS' then
      v_response:=pg_temp.q_post(pg_temp.q_invoice_draft(v_purchase,.000001));
      v_invoice:=(v_response->>'supplier_invoice_id')::uuid;
      if (pg_temp.q_state(v_purchase)->>'match_state')<>'MATCHED' then raise exception 'Q_EXACT_COMPLETION_FAILED';end if;
      perform erp.reverse_material_supplier_invoice(v_invoice,'Q micro completion inverse');
    elsif p_case='FULL_RETURN_MICRO_SPLIT' then
      v_return:=pg_temp.o_return_draft(v_purchase,array[1]::numeric[],10000);
      perform erp.post_material_supplier_return(v_return);
      if pg_temp.o_snapshot(array[v_return])->>'ap_qty'<>'0.999999'
         or (pg_temp.o_snapshot(array[v_return])->>'grni_qty')::numeric<>.000001 then
        raise exception 'Q_RETURN_QUANTITY_NOT_CONSERVED';end if;
    end if;
    v_state:=pg_temp.q_state(v_purchase);
    if v_under then
      if v_state->>'match_state' is distinct from (case when p_fixed then 'PARTIAL' else 'MATCHED' end)
         or v_state->>'price_state' is distinct from (case when p_fixed then 'PARTIAL' else 'FINAL' end)
         or (v_state->>'matched')::numeric<>.999999
         or (v_state->'ledger'->>'ap')::numeric-(v_initial->>'ap')::numeric<>9999.99
         or (v_state->'ledger'->>'grni')::numeric-(v_initial->>'grni')::numeric<>.01 then
        raise exception 'Q_PARTIAL_STATE_EXPECTATION_FAILED: %',v_state;end if;
    else
      v_expected:=case when p_case='FULL_RETURN_MICRO_SPLIT' then 0 else 10000 end;
      if v_state->>'match_state'<>'MATCHED' or v_state->>'price_state'<>'FINAL'
         or (v_state->'ledger'->>'ap')::numeric-(v_initial->>'ap')::numeric<>v_expected
         or (v_state->'ledger'->>'inventory')::numeric-(v_initial->>'inventory')::numeric<>v_expected
         or (v_state->'ledger'->>'grni')::numeric-(v_initial->>'grni')::numeric<>0 then
        raise exception 'Q_EXACT_MONEY_EXPECTATION_FAILED: %',v_state;end if;
    end if;
    if (v_state->'ledger'->>'variance')::numeric-(v_initial->>'variance')::numeric<>0
       or pg_temp.m_report()<>'READY' then raise exception 'Q_LAWFUL_RESULT_NOT_READY: %',v_state;end if;
  end if;
  return jsonb_build_object('status',case when p_fixed then 'PASS' when v_control then 'CONTROL_PASS' else 'KNOWN_P_BUG_REPRODUCED' end,
    'accepted',v_accepted,'code',v_code,'atomic_refusal',not v_accepted and v_atomic,
    'before',v_before,'after',v_state,'source_purchase',v_purchase,
    'v2_envelope',true,'authority','OWNER_CLAIMS_IN_TRUSTED_SQL_SESSION');
end
$$;
