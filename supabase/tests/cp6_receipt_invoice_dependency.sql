-- Receipt/invoice document dependency oracle. Money expectations are constants,
-- and refusal equality covers source documents, stock, journals and audit facts.
-- Owner claims in a trusted disposable SQL session; this is not HTTP/UI proof.
create function pg_temp.r_invoice_draft(p_purchases uuid[],p_qty numeric default 1)
returns jsonb language plpgsql as $$
declare v_payload jsonb;
begin
  select jsonb_build_object('invoice_number','R-INV-'||gen_random_uuid(),
    'supplier_id',h.supplier_id,'invoice_date','2026-09-02',
    'change_reason','R receipt/invoice dependency oracle','lines',jsonb_agg(
      jsonb_build_object('purchase_item_id',i.id,'qty_invoiced',p_qty,'unit_price',10000)
      order by i.id)) into v_payload
  from erp.material_purchase_headers h join erp.material_purchase_items i on i.purchase_id=h.id
  where h.id=any(p_purchases) group by h.supplier_id;
  return erp.save_material_supplier_invoice_draft_v2(v_payload,gen_random_uuid(),null);
end
$$;

create function pg_temp.r_case(p_case text,p_fixed boolean) returns jsonb
language plpgsql as $$
declare
  p uuid;p2 uuid;invoice uuid;first_invoice uuid;draft jsonb;response jsonb;
  initial_ledger jsonb;before_state jsonb;after_state jsonb;boundary jsonb;fault jsonb;
  accepted boolean:=false;atomic boolean;code text;message text;definition text;
  control boolean:=false;guard_control boolean:=false;qty numeric:=1;
  expected_ap numeric:=10000;expected_grni numeric:=-10000;expected_inventory numeric:=0;
  count_issue bigint;count_report bigint;recovery_code text;recovery_message text;
begin
  if pg_temp.m_report()<>'READY' then raise exception 'R_CLEAN_BASELINE_REQUIRED';end if;
  initial_ledger:=pg_temp.n_ledger();
  if p_case='DETECTOR_SOURCE_STATE' then
    -- Replay preserved Q code only inside a tester subtransaction. This models
    -- existing corrupt history and makes no claim about operator DDL access.
    begin
      p:=pg_temp.o_purchase(array[1]::numeric[],10000,false);
      perform pg_temp.q_post(pg_temp.r_invoice_draft(array[p]));
      select pg_get_functiondef('erp.reverse_material_purchase(uuid,text)'::regprocedure) into definition;
      if p_fixed then execute(select object_definition from erp.cp6_v2620r_rollback_capsule
        where object_regidentity='erp.reverse_material_purchase(uuid,text)');end if;
      perform erp.reverse_material_purchase(p,'R preserved Q source-state counterexample');
      execute definition;
      select issue_count into count_issue from erp.run_v267_financial_truth_checks()
        where check_name='V2620R_SUPPLIER_INVOICE_SOURCE_STATE';
      select issue_count into count_report from erp.run_v268_financial_report_checks()
        where check_name='V2620R_SUPPLIER_INVOICE_SOURCE_STATE';
      if count_issue is distinct from (case when p_fixed then 1::bigint end)
         or count_report is distinct from count_issue or pg_temp.m_report()<>'BLOCKED' then
        raise exception 'R_SOURCE_DETECTOR_NOT_CONNECTED';end if;
      fault:=jsonb_build_object('direct_issue_count',count_issue,'report_issue_count',count_report,
        'report',pg_temp.m_report(),'issues',pg_temp.m_issues(),'state',pg_temp.q_state(p),
        'tester_preserved_q_function',p_fixed);
      raise exception using errcode='PZ001',message='R_ROLLBACK_DETECTOR_FAULT';
    exception when sqlstate 'PZ001' then null;end;
    if pg_temp.m_report()<>'READY' then raise exception 'R_DETECTOR_RESTORE_FAILED';end if;
    return jsonb_build_object('status',case when p_fixed then 'PASS' else 'KNOWN_Q_BUG_REPRODUCED' end,
      'fault',fault,'restored_ready',true,'authority','TESTER_SUBTRANSACTION');
  elsif p_case='POSTED_PARTIAL_INVOICE' or p_case='REMAINING_POSTED_INVOICE' then
    qty:=.5;expected_ap:=5000;expected_grni:=-5000;
  elsif p_case in('REVERSE_INVOICE_THEN_RECEIPT','REVERSED_AND_DRAFT_INVOICES',
    'DRAFT_INVOICE_LATE_POST','DIRECT_FINAL_NO_INVOICE','RECEIPT_REPEAT_REVERSE',
    'POSTED_RETURN_GUARD','POSTED_PAYMENT_GUARD','POSTED_CORRECTION_GUARD') then
    control:=true;
    guard_control:=p_case in('POSTED_RETURN_GUARD','POSTED_PAYMENT_GUARD','POSTED_CORRECTION_GUARD');
  elsif p_case not in('POSTED_FULL_INVOICE','MULTI_RECEIPT_INVOICE') then
    raise exception 'R_UNKNOWN_CASE: %',p_case;
  end if;
  p:=pg_temp.o_purchase(array[1]::numeric[],10000,
    p_case in('DIRECT_FINAL_NO_INVOICE','POSTED_PAYMENT_GUARD','POSTED_CORRECTION_GUARD'));
  if p_case='MULTI_RECEIPT_INVOICE' then
    p2:=pg_temp.o_purchase(array[1]::numeric[],10000,false);
    draft:=pg_temp.r_invoice_draft(array[p,p2]);expected_ap:=20000;expected_inventory:=10000;
  elsif p_case='REMAINING_POSTED_INVOICE' then
    response:=pg_temp.q_post(pg_temp.r_invoice_draft(array[p],.5));
    first_invoice:=(response->>'supplier_invoice_id')::uuid;
    draft:=pg_temp.r_invoice_draft(array[p],.5);
  elsif not control or p_case in('REVERSE_INVOICE_THEN_RECEIPT','REVERSED_AND_DRAFT_INVOICES','DRAFT_INVOICE_LATE_POST') then
    draft:=pg_temp.r_invoice_draft(array[p],qty);
  end if;
  if draft is not null and p_case<>'DRAFT_INVOICE_LATE_POST' then
    response:=pg_temp.q_post(draft);invoice:=(response->>'supplier_invoice_id')::uuid;
    if first_invoice is not null then
      perform erp.reverse_material_supplier_invoice(first_invoice,'R leave exactly one posted invoice');
    elsif p_case in('REVERSE_INVOICE_THEN_RECEIPT','REVERSED_AND_DRAFT_INVOICES') then
      perform erp.reverse_material_supplier_invoice(invoice,'R lawful invoice-first inverse');
      if p_case='REVERSED_AND_DRAFT_INVOICES' then draft:=pg_temp.r_invoice_draft(array[p]);end if;
    end if;
  end if;
  if p_case='POSTED_RETURN_GUARD' then perform pg_temp.m_return(p,.5);
  elsif p_case='POSTED_PAYMENT_GUARD' then perform pg_temp.m_pay(p,1);
  elsif p_case='POSTED_CORRECTION_GUARD' then perform pg_temp.m_correct(p,10001);end if;
  if pg_temp.m_report()<>'READY' then raise exception 'R_LEGAL_SETUP_NOT_READY';end if;
  before_state:=pg_temp.q_state(p);boundary:=pg_temp.o_boundary();
  begin
    perform erp.reverse_material_purchase(p,'R independent receipt dependency inverse');accepted:=true;
  exception when raise_exception then code:=sqlstate;message:=sqlerrm;end;
  atomic:=pg_temp.o_boundary() is not distinct from boundary;
  after_state:=pg_temp.q_state(p);
  if (not control and p_fixed) or guard_control then
    if accepted or code is distinct from 'P0001' or not atomic
       or pg_temp.m_report()<>'READY'
       or (select status from erp.material_purchase_headers where id=p)<>'POSTED' then
      raise exception 'R_DEPENDENCY_REFUSAL_NOT_ATOMIC: %',after_state;end if;
    if not control and message is distinct from 'Reverse posted supplier invoices before reversing this receipt' then
      raise exception 'R_INVOICE_DEPENDENCY_NOT_GUARDED: %',message;end if;
    if p2 is not null then
      accepted:=false;code:=null;message:=null;
      begin perform erp.reverse_material_purchase(p2,'R multi-receipt second source');accepted:=true;
      exception when raise_exception then code:=sqlstate;message:=sqlerrm;end;
      if accepted or code is distinct from 'P0001' or pg_temp.o_boundary() is distinct from boundary
         or message is distinct from 'Reverse posted supplier invoices before reversing this receipt' then
        raise exception 'R_MULTI_RECEIPT_SECOND_SOURCE_UNPROTECTED';end if;
    end if;
  elsif not control then
    if not accepted or (after_state->>'stock')::numeric<>0
       or (select status from erp.material_purchase_headers where id=p)<>'REVERSED'
       or pg_temp.o_delta(initial_ledger,pg_temp.n_ledger()) is distinct from
         jsonb_build_object('ap',expected_ap,'grni',expected_grni,'inventory',expected_inventory,'variance',0)
       or pg_temp.m_report()<>'BLOCKED' then
      raise exception 'R_Q_BROKEN_DEPENDENCY_NOT_REPRODUCED: %',after_state;end if;
    boundary:=pg_temp.o_boundary();
    begin perform erp.reverse_material_supplier_invoice(invoice,'R attempt recovery after Q wrong order');
    exception when raise_exception then recovery_code:=sqlstate;recovery_message:=sqlerrm;end;
    if recovery_code is distinct from 'P0001' or recovery_message is distinct from 'Source purchase must be POSTED'
       or pg_temp.o_boundary() is distinct from boundary then
      raise exception 'R_Q_RECOVERY_REFUSAL_NOT_REPRODUCED';end if;
  else
    if not accepted or (after_state->>'stock')::numeric<>0
       or (select status from erp.material_purchase_headers where id=p)<>'REVERSED'
       or pg_temp.n_ledger() is distinct from initial_ledger or pg_temp.m_report()<>'READY' then
      raise exception 'R_LAWFUL_INVERSE_FAILED: %',after_state;end if;
    boundary:=pg_temp.o_boundary();
    if p_case='DRAFT_INVOICE_LATE_POST' then
      accepted:=false;code:=null;message:=null;
      begin perform pg_temp.q_post(draft);accepted:=true;
      exception when raise_exception then code:=sqlstate;message:=sqlerrm;end;
      atomic:=pg_temp.o_boundary() is not distinct from boundary;
      if accepted or code is distinct from 'P0001' or message is distinct from 'Source purchase must be POSTED'
         or pg_temp.o_boundary() is distinct from boundary
         or (select status from erp.material_supplier_invoices where id=(draft->>'supplier_invoice_id')::uuid)<>'DRAFT' then
        raise exception 'R_STALE_INVOICE_POST_NOT_ATOMIC';end if;
    elsif p_case='RECEIPT_REPEAT_REVERSE' then
      perform erp.reverse_material_purchase(p,'R repeated receipt inverse');
      if pg_temp.o_boundary() is distinct from boundary then raise exception 'R_REPEAT_REVERSE_MUTATED_FACTS';end if;
    end if;
  end if;
  return jsonb_build_object('status',case when p_fixed then 'PASS' when control then 'CONTROL_PASS' else 'KNOWN_Q_BUG_REPRODUCED' end,
    'accepted',accepted,'code',code,'message',message,'atomic_refusal',not accepted and atomic,
    'before',before_state,'after',after_state,'report',pg_temp.m_report(),
    'recovery_refusal',recovery_message,'source_purchase',p,'second_purchase',p2,
    'authority','OWNER_CLAIMS_IN_TRUSTED_SQL_SESSION','http_ui_reachability_proven',false);
end
$$;
