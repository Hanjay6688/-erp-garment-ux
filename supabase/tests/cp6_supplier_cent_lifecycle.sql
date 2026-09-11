-- Independent M counterexamples and N controls. Requires m_* temporary fixture helpers.
create function pg_temp.n_ledger() returns jsonb language sql as $$
 select jsonb_build_object('ap',coalesce(sum(l.credit-l.debit) filter(where l.account_id=erp.account_id('AP_SUPPLIER')),0),
  'grni',coalesce(sum(l.credit-l.debit) filter(where l.account_id=erp.account_id('GRNI_MATERIAL')),0),
  'inventory',coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('MATERIAL_INVENTORY')),0),
  'variance',coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('MATERIAL_PURCHASE_VARIANCE')),0),
  'report',pg_temp.m_report(),'issues',pg_temp.m_issues())
 from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id and j.status in('POSTED','REVERSED')
$$;
create function pg_temp.n_invoice(p_purchases uuid[],p_qty numeric,p_price numeric) returns uuid language plpgsql as $$
declare v_id uuid:=gen_random_uuid();begin
 insert into erp.material_supplier_invoices(id,invoice_number,supplier_id,invoice_date,status,posting_reason)
 values(v_id,'N-INV-'||v_id,'c8c30000-0000-4000-8000-000000000001','2026-09-03','DRAFT','Independent cumulative cent invoice');
 insert into erp.material_supplier_invoice_lines(invoice_id,purchase_item_id,qty_invoiced,unit_price)
 select v_id,i.id,p_qty,p_price from erp.material_purchase_items i where i.purchase_id=any(p_purchases);
 perform erp.post_material_supplier_invoice(v_id);return v_id;
end
$$;
create function pg_temp.n_assert_ready() returns void language plpgsql as $$begin
 if pg_temp.m_report()<>'READY' then raise exception 'N_EXPECTED_READY %',pg_temp.m_issues();end if;
end$$;
create function pg_temp.n_case(p_case text,p_fixed boolean) returns jsonb language plpgsql as $$
declare p uuid;q uuid;c uuid;r uuid;ids uuid[]:='{}';before jsonb;after jsonb;trace jsonb:='[]';
 n int;accepted boolean:=true;code text;expected_ap numeric;expected_inventory numeric;expected_grni numeric:=0;
begin
 perform pg_temp.n_assert_ready();
 if p_case in('CORRECTION_ROUND_DELTA','CORRECTION_HALF_CENT','CORRECTION_ZERO_INVERSE','CORRECTION_CHAIN') then
  p:=pg_temp.m_purchase(1,case when p_case='CORRECTION_HALF_CENT' then .01 else .005 end);before:=pg_temp.n_ledger();
  c:=pg_temp.m_correct(p,case when p_case='CORRECTION_HALF_CENT' then .015 else .014 end);
  expected_ap:=case when p_case='CORRECTION_HALF_CENT' then .02 else .01 end;expected_inventory:=expected_ap;
  if p_case='CORRECTION_ZERO_INVERSE' then
   perform erp.reverse_material_purchase_cost_correction(c,'Independent zero-cent correction inverse');
  elsif p_case='CORRECTION_CHAIN' then
   r:=pg_temp.m_correct(p,.026);perform pg_temp.n_assert_ready();
   perform erp.reverse_material_purchase_cost_correction(r,'Independent latest correction inverse');perform pg_temp.n_assert_ready();
   perform erp.reverse_material_purchase_cost_correction(c,'Independent earlier zero-cent inverse');
  end if;
 elsif p_case='MULTI_PURCHASE_INVOICE' then
  p:=pg_temp.m_purchase(1,.015,false);q:=pg_temp.m_purchase(1,.015,false);before:=pg_temp.n_ledger();
  c:=pg_temp.n_invoice(array[p,q],1,.015);expected_ap:=.04;expected_inventory:=.04;
 elsif p_case in('PARTIAL_INVOICE','NONFIFO_INVOICE_INVERSE','INVOICE_PAY_REVERSE','INVOICE_RETURN_INVERSE') then
  p:=pg_temp.m_purchase(3,.01,false);before:=pg_temp.n_ledger();
  for n in 1..3 loop
   begin c:=pg_temp.n_invoice(array[p],1,.015);ids:=array_append(ids,c);
   exception when raise_exception then accepted:=false;code:=sqlstate;exit;end;
   trace:=trace||jsonb_build_array(pg_temp.n_ledger());
  end loop;
  expected_ap:=.05;expected_inventory:=.05;
  if p_fixed and not accepted then raise exception 'N_LEGAL_PARTIAL_INVOICE_REFUSED';end if;
  if p_case='NONFIFO_INVOICE_INVERSE' then
   foreach n in array array[2,1,3] loop
    perform erp.reverse_material_supplier_invoice(ids[n],'Independent non FIFO supplier invoice inverse');perform pg_temp.n_assert_ready();
    trace:=trace||jsonb_build_array(pg_temp.n_ledger());
   end loop;expected_ap:=0;expected_grni:=.03;expected_inventory:=.03;
  elsif p_case='INVOICE_PAY_REVERSE' then
   r:=pg_temp.m_pay(p,.05);perform pg_temp.n_assert_ready();
   begin perform erp.reverse_material_supplier_invoice(ids[1],'Must preserve already paid capacity');accepted:=true;
   exception when raise_exception then accepted:=false;end;
   if accepted then raise exception 'N_PAID_INVOICE_INVERSE_ACCEPTED';end if;
   perform erp.reverse_supplier_payment(r,'Independent unwind supplier payment');
   foreach n in array array[3,2,1] loop perform erp.reverse_material_supplier_invoice(ids[n],'Independent paid invoice unwind');perform pg_temp.n_assert_ready();end loop;
   expected_ap:=0;expected_grni:=.03;expected_inventory:=.03;accepted:=true;
  elsif p_case='INVOICE_RETURN_INVERSE' then
   r:=pg_temp.m_return(p,1);perform pg_temp.n_assert_ready();
   perform erp.reverse_material_supplier_return(r,'Independent final invoiced return unwind');perform pg_temp.n_assert_ready();
  end if;
 elsif p_case in('SPLIT_RETURN','NONFIFO_RETURN_INVERSE','SUBCENT_RETURN_INVERSE') then
  p:=pg_temp.m_purchase(case when p_case='SUBCENT_RETURN_INVERSE' then 2 else 3 end,
    case when p_case='SUBCENT_RETURN_INVERSE' then .004 else .015 end);before:=pg_temp.n_ledger();
  for n in 1..(case when p_case='SUBCENT_RETURN_INVERSE' then 2 else 3 end) loop
   r:=pg_temp.m_return(p,1);ids:=array_append(ids,r);trace:=trace||jsonb_build_array(pg_temp.n_ledger());
   if p_fixed then perform pg_temp.n_assert_ready();end if;
  end loop;expected_ap:=0;expected_inventory:=0;
  if p_case='NONFIFO_RETURN_INVERSE' then
   foreach n in array array[2,1,3] loop perform erp.reverse_material_supplier_return(ids[n],'Independent non FIFO return inverse');perform pg_temp.n_assert_ready();trace:=trace||jsonb_build_array(pg_temp.n_ledger());end loop;
   expected_ap:=.05;expected_inventory:=.05;
  elsif p_case='SUBCENT_RETURN_INVERSE' then
   foreach n in array array[1,2] loop perform erp.reverse_material_supplier_return(ids[n],'Independent subcent return inverse');perform pg_temp.n_assert_ready();end loop;
   expected_ap:=.01;expected_inventory:=.01;
  end if;
 elsif p_case='ZERO_CENT_POSTING_FACT' then
  p:=pg_temp.m_purchase(1,.005);c:=pg_temp.m_correct(p,.014);
  if not exists(select 1 from erp.supplier_cent_posting_facts where source_id=c and phase='POST' and journal_entry_id is null and ledger_delta='{}') then raise exception 'N_ZERO_CENT_FACT_MISSING';end if;
  begin update erp.supplier_cent_posting_facts set ledger_delta='{}' where source_id=c;accepted:=true;
  exception when insufficient_privilege then accepted:=false;end;
  if accepted then raise exception 'N_POSTED_CENT_FACT_MUTABLE';end if;
  expected_ap:=.01;expected_inventory:=.01;accepted:=true;
 elsif p_case='FACT_LEDGER_FAULT' then
  p:=pg_temp.m_purchase(1,.01);c:=pg_temp.m_correct(p,.025);q:=pg_temp.m_purchase(1,.01);r:=pg_temp.m_correct(q,.025);before:=pg_temp.n_ledger();
  begin
   update erp.journal_lines l set debit=case when l.debit>0 then l.debit+x.delta else 0 end,credit=case when l.credit>0 then l.credit+x.delta else 0 end
   from(select journal_entry_id,case when source_id=c then .01 else -.01 end delta from erp.supplier_cent_posting_facts where source_id in(c,r) and phase='POST') x
   where l.journal_entry_id=x.journal_entry_id;
   if not exists(select 1 from erp.run_v267_financial_truth_checks() where check_name='V2620N_SUPPLIER_CENT_FACT_LEDGER' and issue_count=2) then raise exception 'N_LEDGER_FAULT_FALSE_READY';end if;
   raise exception using errcode='ZXN01',message='rollback privileged detector fault';
  exception when sqlstate 'ZXN01' then null;end;
  expected_ap:=.06;expected_inventory:=.06;
 else raise exception 'N_UNKNOWN_ORACLE';end if;
 after:=pg_temp.n_ledger();
 if p_fixed then
  perform pg_temp.n_assert_ready();
  if (after->>'ap')::numeric<>expected_ap or (after->>'grni')::numeric<>expected_grni or (after->>'inventory')::numeric<>expected_inventory then
   raise exception 'N_SOURCE_CENT_BALANCE_MISMATCH %',after;end if;
 elsif p_case='PARTIAL_INVOICE' then
  if accepted or code is distinct from 'P0001' then raise exception 'N_M_PARTIAL_REFUSAL_NOT_REPRODUCED';end if;
 elsif after->>'report'<>'BLOCKED' then raise exception 'N_M_COUNTEREXAMPLE_NOT_REPRODUCED';end if;
 return jsonb_build_object('status',case when p_fixed then 'PASS' else 'KNOWN_M_BUG_REPRODUCED' end,
  'case',p_case,'before',before,'after',after,'trace',trace,'accepted',accepted,'code',code,
  'expected_ap',expected_ap,'expected_grni',expected_grni,'expected_inventory',expected_inventory);
end
$$;
