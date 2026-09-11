-- Independent competition counterexamples and positive controls.
-- Requires a disposable transaction, CP6 fixture foundation and OWNER claims.
-- Each caller rolls back the entire case, including privileged detector faults.
create or replace function pg_temp.m_report() returns text language sql as $$
 select case when exists(select 1 from erp.run_v268_financial_report_checks()
   where severity='CRITICAL' and issue_count>0) then 'BLOCKED' else 'READY' end
$$;
create or replace function pg_temp.m_issues() returns jsonb language sql as $$
 select coalesce(jsonb_agg(jsonb_build_object('check',check_name,'count',issue_count)),'[]')
 from erp.run_v268_financial_report_checks() where issue_count>0
$$;
create or replace function pg_temp.m_boundary() returns jsonb language plpgsql as $$
declare t text; digest text; result jsonb:='{}';begin
 foreach t in array array['journal_entries','journal_lines','account_daily_balances','audit_logs',
  'idempotency_requests','opening_balance_headers','opening_balance_items','opening_subledger_balances',
  'opening_subledger_settlements','opening_financial_corrections','supplier_payments','material_purchase_headers',
  'material_purchase_items','material_stock_movements','material_rolls','material_supplier_invoices',
  'material_supplier_invoice_lines','material_supplier_returns','material_supplier_return_items',
  'material_purchase_cost_corrections','material_purchase_cost_correction_items','cost_adjustments','cost_recalc_queue'] loop
  execute format('select md5(coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text)::text,'''')) from erp.%I x',t) into digest;
  result:=result||jsonb_build_object(t,digest);
 end loop;return result;end
$$;
create or replace function pg_temp.m_opening(kind text default 'CUSTOMER_RECEIVABLE', money numeric default 100)
returns uuid language plpgsql as $$
declare h uuid:=gen_random_uuid();i uuid:=gen_random_uuid();customer uuid;cid uuid;begin
 if kind='CUSTOMER_RECEIVABLE' then
  customer:=gen_random_uuid();insert into erp.customers(id,customer_code,customer_name,is_active)
  values(customer,'M-C-'||substr(customer::text,1,16),'Independent opening customer',true);
 end if;
 if kind like 'CONTRACTOR_%' then select id into cid from erp.contractors where is_active order by id limit 1;end if;
 insert into erp.opening_balance_headers(id,opening_number,opening_date,status)
 values(h,'M-OPEN-'||h,'2026-09-01','DRAFT');
 insert into erp.opening_balance_items(id,opening_id,balance_type,customer_id,supplier_id,vendor_id,contractor_id,amount)
 values(i,h,kind,customer,
  case when kind='SUPPLIER_PAYABLE' then 'c8c30000-0000-4000-8000-000000000001'::uuid end,
  case when kind='VENDOR_PAYABLE' then 'c8c20000-0000-4000-8000-000000000002'::uuid end,cid,money);
 perform erp.post_opening_balance(h);
 return (select id from erp.opening_subledger_balances where opening_item_id=i);
end
$$;
create or replace function pg_temp.m_settle(balance uuid,money numeric) returns uuid language plpgsql as $$
declare id uuid:=gen_random_uuid();cash uuid;begin
 select c.id into cash from erp.cash_accounts c where is_active order by cash_account_code limit 1;
 insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status)
 values(id,balance,'M-SETTLE-'||id,'2026-09-02T12:00:00Z',money,cash,'DRAFT');
 perform erp.post_opening_subledger_settlement(id);return id;
end
$$;
create or replace function pg_temp.m_open_state(balance uuid) returns jsonb language sql as $$
 select jsonb_build_object('original',b.original_amount,'settled',b.settled_amount,
   'remaining',b.original_amount-b.settled_amount,'status',b.status,'report',pg_temp.m_report())
 from erp.opening_subledger_balances b where b.id=balance
$$;
create or replace function pg_temp.m_purchase(quantity numeric default 10,price numeric default 10,final_price boolean default true)
returns uuid language plpgsql as $$
declare location uuid:=gen_random_uuid();draft jsonb;begin
 insert into erp.locations(id,location_code,location_name,location_type,is_active)
 values(location,'M-RAW-'||substr(location::text,1,16),'Independent raw warehouse','RAW_MATERIAL_WAREHOUSE',true);
 draft:=erp.save_material_purchase_draft_v2(jsonb_build_object(
  'purchase_number','M-PUR-'||gen_random_uuid(),'supplier_id','c8c30000-0000-4000-8000-000000000001',
  'location_id',location,'physical_at','2026-09-01T08:00:00Z','change_reason','Independent legal material receipt',
  'lines',jsonb_build_array(jsonb_build_object('material_id','c8c30000-0000-4000-8000-000000000002',
   'qty',quantity,'unit_price',price,'price_state',case when final_price then 'FINAL' else 'ESTIMATED' end,
   'price_source',case when final_price then 'SUPPLIER_INVOICE' else 'MANUAL_ESTIMATE' end,
   'rolls',jsonb_build_array(jsonb_build_object('roll_number','M-ROLL-'||gen_random_uuid(),'qty',quantity))))),gen_random_uuid(),null);
 perform erp.post_material_purchase_v2((draft->>'purchase_id')::uuid,gen_random_uuid(),(draft->>'row_version')::bigint,'Independent exact receipt posting');
 return (draft->>'purchase_id')::uuid;
end
$$;
create or replace function pg_temp.m_pay(purchase uuid,money numeric) returns uuid language plpgsql as $$
declare id uuid:=gen_random_uuid();cash uuid;begin
 select c.id into cash from erp.cash_accounts c where is_active order by cash_account_code limit 1;
 insert into erp.supplier_payments(id,purchase_id,payment_number,payment_date,amount,cash_account_id,status)
 values(id,purchase,'M-PAY-'||id,'2026-09-02T12:00:00Z',money,cash,'DRAFT');
 perform erp.post_supplier_payment(id);return id;
end
$$;
create or replace function pg_temp.m_purchase_state(purchase uuid) returns jsonb language sql as $$
 select jsonb_build_object('status',h.payment_status,'payable',round(erp.material_purchase_final_ap_total(h.id),2),
 'paid',coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0),
 'ap_gl',coalesce((select sum(l.credit-l.debit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
   where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_SUPPLIER')),0),'report',pg_temp.m_report())
 from erp.material_purchase_headers h where h.id=purchase
$$;
create or replace function pg_temp.m_correct(purchase uuid,price numeric) returns uuid language plpgsql as $$
declare v_new_id uuid:=gen_random_uuid();begin
 insert into erp.material_purchase_cost_corrections(id,correction_number,purchase_id,invoice_date,reason,status)
 values(v_new_id,'M-CORR-'||v_new_id,purchase,'2026-09-03','Independent exact invoice correction','DRAFT');
 insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price)
 select v_new_id,i.id,price from erp.material_purchase_items i where i.purchase_id=purchase;
 perform erp.post_material_purchase_cost_correction(v_new_id);return v_new_id;
end
$$;
create or replace function pg_temp.m_return(purchase uuid,quantity numeric) returns uuid language plpgsql as $$
declare rid uuid:=gen_random_uuid();begin
 insert into erp.material_supplier_returns(id,return_number,supplier_id,location_id,physical_at,status,reason)
 select rid,'M-RETURN-'||rid,h.supplier_id,h.location_id,'2026-09-03T12:00:00Z','DRAFT','Independent physical supplier return'
 from erp.material_purchase_headers h where h.id=purchase;
 insert into erp.material_supplier_return_items(return_id,material_id,roll_id,qty,purchase_item_id,supplier_credit_unit_price)
 select rid,i.material_id,r.id,quantity,i.id,erp.material_purchase_current_unit_cost(i.id)
 from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=purchase;
 perform erp.post_material_supplier_return(rid);return rid;
end
$$;
create or replace function pg_temp.m_invoice(purchase uuid) returns uuid language plpgsql as $$
declare v_new_id uuid:=gen_random_uuid();begin
 insert into erp.material_supplier_invoices(id,invoice_number,supplier_id,invoice_date,status,posting_reason)
 select v_new_id,'M-INV-'||v_new_id,h.supplier_id,'2026-09-03','DRAFT','Independent final invoice' from erp.material_purchase_headers h where h.id=purchase;
 insert into erp.material_supplier_invoice_lines(invoice_id,purchase_item_id,qty_invoiced,unit_price)
 select v_new_id,i.id,i.qty,10 from erp.material_purchase_items i where i.purchase_id=purchase;
 perform erp.post_material_supplier_invoice(v_new_id);return v_new_id;
end
$$;
create or replace function pg_temp.m_case(kind text,fixed boolean) returns jsonb language plpgsql as $$
declare b uuid;p uuid;q uuid;first uuid;last uuid;item uuid;correction uuid;before jsonb;after jsonb;
 partial jsonb;boundary jsonb;accepted boolean:=false;code text;variant text;cases jsonb:='[]';faults jsonb;
 expected text;result jsonb;begin
 if pg_temp.m_report()<>'READY' then raise exception 'M_CLEAN_BASELINE_REQUIRED';end if;
 if kind='OPENING_READY' then
  b:=pg_temp.m_opening();after:=pg_temp.m_open_state(b);
  if after->>'report'<>(case when fixed then 'READY' else 'BLOCKED' end) then raise exception 'M_OPENING_REPORT_ORACLE_FAILED';end if;
  result:=jsonb_build_object('actual',after,'issues',pg_temp.m_issues(),'expected','Valid opening receivable must be READY');
 elsif kind in('OPENING_LAST_CENT','OPENING_OVERPAY','OPENING_CORRECTION','OPENING_REVERSE_CORRECTION','OPENING_REVERSE_SETTLEMENT') then
  b:=pg_temp.m_opening();before:=pg_temp.m_open_state(b);
  select opening_item_id into item from erp.opening_subledger_balances where id=b;
  if kind='OPENING_LAST_CENT' then
   first:=pg_temp.m_settle(b,99.99);partial:=pg_temp.m_open_state(b);boundary:=pg_temp.m_boundary();
   begin last:=pg_temp.m_settle(b,.01);accepted:=true;exception when raise_exception then code:=sqlstate;end;
   after:=pg_temp.m_open_state(b);
   if fixed then
    if partial->>'status'<>'PARTIAL' or (partial->>'remaining')::numeric<>.01 or not accepted
      or after->>'status'<>'SETTLED' or (after->>'remaining')::numeric<>0 then raise exception 'M_LAST_OPENING_CENT_FAILED';end if;
   elsif partial->>'status'<>'SETTLED' or accepted or code<>'P0001' then raise exception 'L_LAST_OPENING_CENT_NOT_REPRODUCED';end if;
  elsif kind='OPENING_REVERSE_SETTLEMENT' then
   first:=pg_temp.m_settle(b,.01);last:=pg_temp.m_settle(b,99.99);
   perform erp.reverse_opening_subledger_settlement(last,'Independent non-FIFO opening inverse');
   after:=pg_temp.m_open_state(b);
   if (after->>'settled')::numeric<>.01 or after->>'status'<>(case when fixed then 'PARTIAL' else 'OPEN' end) then raise exception 'M_INVERSE_OPENING_CENT_FAILED';end if;
  else
   if kind='OPENING_CORRECTION' then perform pg_temp.m_settle(b,100);end if;
   if kind='OPENING_REVERSE_CORRECTION' then
    correction:=erp.post_opening_financial_correction(item,100.01,'Independent lawful increase','2026-09-02');
    perform pg_temp.m_settle(b,100.01);
   end if;
   boundary:=pg_temp.m_boundary();
   begin
    if kind='OPENING_OVERPAY' then perform pg_temp.m_settle(b,100.01);
    elsif kind='OPENING_CORRECTION' then perform erp.post_opening_financial_correction(item,99.99,'Cannot erase a collected cent','2026-09-03');
    else perform erp.reverse_opening_financial_correction(correction,'Cannot restore less than collected');end if;
    accepted:=true;
   exception when raise_exception then code:=sqlstate;end;
   after:=pg_temp.m_open_state(b);
   if fixed then
    if accepted or code<>'P0001' or boundary<>pg_temp.m_boundary() then raise exception 'M_OPENING_OVERSETTLEMENT_NOT_ATOMIC';end if;
   elsif not accepted or (after->>'remaining')::numeric<>-.01 then raise exception 'L_OPENING_OVERSETTLEMENT_NOT_REPRODUCED';end if;
  end if;
  if fixed and after->>'report'<>'READY' then raise exception 'M_OPENING_LIFECYCLE_FALSE_BLOCKED';end if;
  result:=jsonb_build_object('before',before,'partial',partial,'actual',after,'accepted',accepted,'sqlstate',code,
    'atomic_refusal',case when not accepted and boundary is not null then boundary=pg_temp.m_boundary() end);
 elsif kind='OPENING_PARTIES' then
  foreach variant in array array['CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE'] loop
   b:=pg_temp.m_opening(variant);before:=pg_temp.m_open_state(b);
   if before->>'report'<>'READY' then raise exception 'M_VALID_PARTY_OPENING_FALSE_BLOCKED';end if;
   first:=pg_temp.m_settle(b,99.99);partial:=pg_temp.m_open_state(b);
   if partial->>'status'<>'PARTIAL' or partial->>'report'<>'READY' then raise exception 'M_PARTY_PARTIAL_FAILED';end if;
   last:=pg_temp.m_settle(b,.01);after:=pg_temp.m_open_state(b);
   if after->>'status'<>'SETTLED' or after->>'report'<>'READY' then raise exception 'M_PARTY_LAST_CENT_FAILED';end if;
   perform erp.reverse_opening_subledger_settlement(last,'Independent exact opening inverse');
   if pg_temp.m_open_state(b)->>'status'<>'PARTIAL' then raise exception 'M_PARTY_INVERSE_CENT_FAILED';end if;
   perform erp.reverse_opening_subledger_settlement(first,'Independent reverse remaining opening payment');
   if pg_temp.m_open_state(b)->>'status'<>'OPEN' or pg_temp.m_report()<>'READY' then raise exception 'M_PARTY_LIFECYCLE_FAILED';end if;
   cases:=cases||jsonb_build_array(jsonb_build_object('party',variant,'partial',partial,'settled',after,'restored',pg_temp.m_open_state(b)));
  end loop;result:=jsonb_build_object('cases',cases);
 elsif kind in('SUPPLIER_LAST_CENT','SUPPLIER_OVERPAY','SUPPLIER_REVERSE_PAYMENT','SUPPLIER_CORRECTION','SUPPLIER_REVERSE_CORRECTION','SUPPLIER_RETURN') then
  p:=pg_temp.m_purchase();before:=pg_temp.m_purchase_state(p);
  if before->>'report'<>'READY' then raise exception 'M_SUPPLIER_BASELINE_FALSE_BLOCKED';end if;
  if kind in('SUPPLIER_LAST_CENT','SUPPLIER_REVERSE_PAYMENT') then
   first:=pg_temp.m_pay(p,99.99);partial:=pg_temp.m_purchase_state(p);last:=pg_temp.m_pay(p,.01);
   if kind='SUPPLIER_REVERSE_PAYMENT' then perform erp.reverse_supplier_payment(last,'Independent inverse last supplier cent');end if;
   after:=pg_temp.m_purchase_state(p);
   if partial->>'status'<>(case when fixed then 'PARTIAL' else 'PAID' end)
    or after->>'status'<>(case when kind='SUPPLIER_REVERSE_PAYMENT' and fixed then 'PARTIAL' else 'PAID' end)
    or after->>'report'<>'READY' then raise exception 'M_SUPPLIER_STATUS_ORACLE_FAILED';end if;
  else
   if kind in('SUPPLIER_CORRECTION','SUPPLIER_RETURN') then perform pg_temp.m_pay(p,100);end if;
   if kind='SUPPLIER_REVERSE_CORRECTION' then correction:=pg_temp.m_correct(p,10.001);perform pg_temp.m_pay(p,100.01);end if;
   boundary:=pg_temp.m_boundary();
   begin
    if kind='SUPPLIER_OVERPAY' then perform pg_temp.m_pay(p,100.01);
    elsif kind='SUPPLIER_CORRECTION' then perform pg_temp.m_correct(p,9.999);
    elsif kind='SUPPLIER_RETURN' then perform pg_temp.m_return(p,.001);
    else perform erp.reverse_material_purchase_cost_correction(correction,'Cannot restore AP below payment');end if;
    accepted:=true;
   exception when raise_exception then code:=sqlstate;end;
   after:=pg_temp.m_purchase_state(p);
   if fixed then
    if accepted or code<>'P0001' or boundary<>pg_temp.m_boundary() or after->>'report'<>'READY' then raise exception 'M_SUPPLIER_OVERPAY_NOT_ATOMIC';end if;
   elsif not accepted or (after->>'ap_gl')::numeric<>-.01 or after->>'report'<>'READY' then raise exception 'L_SUPPLIER_OVERPAY_NOT_REPRODUCED';end if;
  end if;
  result:=jsonb_build_object('before',before,'partial',partial,'actual',after,'accepted',accepted,'sqlstate',code,
    'atomic_refusal',case when not accepted and boundary is not null then boundary=pg_temp.m_boundary() end);
 elsif kind='SUPPLIER_VALID_LIFECYCLE' then
  p:=pg_temp.m_purchase();first:=pg_temp.m_pay(p,99.99);correction:=pg_temp.m_correct(p,9.999);
  if pg_temp.m_purchase_state(p)->>'status'<>'PAID' or pg_temp.m_report()<>'READY' then raise exception 'M_LAWFUL_COST_DECREASE_FAILED';end if;
  perform erp.reverse_material_purchase_cost_correction(correction,'Independent lawful correction inverse');
  if pg_temp.m_purchase_state(p)->>'status'<>'PARTIAL' then raise exception 'M_COST_INVERSE_STATUS_FAILED';end if;
  last:=pg_temp.m_return(p,.001);
  if pg_temp.m_purchase_state(p)->>'status'<>'PAID' or pg_temp.m_report()<>'READY' then raise exception 'M_LAWFUL_RETURN_FAILED';end if;
  perform erp.reverse_material_supplier_return(last,'Independent lawful return inverse');
  if pg_temp.m_purchase_state(p)->>'status'<>'PARTIAL' or pg_temp.m_report()<>'READY' then raise exception 'M_RETURN_INVERSE_STATUS_FAILED';end if;
  perform erp.reverse_supplier_payment(first,'Independent clean supplier lifecycle');
  if pg_temp.m_purchase_state(p)->>'status'<>'UNPAID' or pg_temp.m_report()<>'READY' then raise exception 'M_SUPPLIER_LIFECYCLE_RESTORE_FAILED';end if;
  result:=jsonb_build_object('actual',pg_temp.m_purchase_state(p),'corrected_returned_reversed',true);
 elsif kind='SUPPLIER_INVOICE_LIFECYCLE' then
  p:=pg_temp.m_purchase(10,10,false);
  if pg_temp.m_report()<>'READY' then raise exception 'M_ESTIMATED_GRNI_FAILED';end if;
  correction:=pg_temp.m_invoice(p);first:=pg_temp.m_pay(p,99.99);
  if pg_temp.m_purchase_state(p)->>'status'<>'PARTIAL' or pg_temp.m_report()<>'READY' then raise exception 'M_INVOICE_PARTIAL_FAILED';end if;
  boundary:=pg_temp.m_boundary();
  begin perform erp.reverse_material_supplier_invoice(correction,'Cannot erase paid final invoice');accepted:=true;exception when raise_exception then code:=sqlstate;end;
  if accepted or code<>'P0001' or boundary<>pg_temp.m_boundary() then raise exception 'M_PAID_INVOICE_INVERSE_NOT_ATOMIC';end if;
  perform erp.reverse_supplier_payment(first,'Independent remove payment dependency');
  perform erp.reverse_material_supplier_invoice(correction,'Independent final invoice inverse');
  if pg_temp.m_report()<>'READY' then raise exception 'M_INVOICE_REVERSE_FALSE_BLOCKED';end if;
  result:=jsonb_build_object('actual',pg_temp.m_purchase_state(p),'dependency_refusal_atomic',true);
 elsif kind='FRACTIONAL_PURCHASES' then
  p:=pg_temp.m_purchase(.5,.01);q:=pg_temp.m_purchase(.5,.01);
  before:=pg_temp.m_purchase_state(p);
  if (before->>'ap_gl')::numeric<>.02 or before->>'report'<>'READY' then raise exception 'M_PER_PURCHASE_CENT_TOTAL_FAILED';end if;
  perform pg_temp.m_pay(p,.01);perform pg_temp.m_pay(q,.01);after:=pg_temp.m_purchase_state(p);
  if (after->>'ap_gl')::numeric<>0 or after->>'report'<>'READY' then raise exception 'M_FRACTIONAL_FINAL_AP_NOT_CONSERVED';end if;
  result:=jsonb_build_object('before',before,'actual',after);
 elsif kind in('SUPPLIER_AMOUNT_WASH','OPENING_PARTY_WASH','OPENING_STATUS_FAULT','PAYMENT_INVERSE_FAULT') then
  if kind='SUPPLIER_AMOUNT_WASH' then
   p:=pg_temp.m_purchase();q:=pg_temp.m_purchase();first:=pg_temp.m_pay(p,40);last:=pg_temp.m_pay(q,40);
  else
   b:=pg_temp.m_opening();first:=pg_temp.m_settle(b,40);
   if kind='OPENING_PARTY_WASH' then q:=pg_temp.m_opening();last:=pg_temp.m_settle(q,40);end if;
   if kind='PAYMENT_INVERSE_FAULT' then perform erp.reverse_opening_subledger_settlement(first,'Independent lawful inverse');end if;
  end if;
  if pg_temp.m_report()<>'READY' then raise exception 'M_FAULT_POSITIVE_CONTROL_NOT_READY';end if;
  set local session_replication_role='replica';
  if kind='SUPPLIER_AMOUNT_WASH' then
   update erp.supplier_payments set amount=amount+.01 where id=first;
   update erp.supplier_payments set amount=amount-.01 where id=last;
  elsif kind='OPENING_STATUS_FAULT' then update erp.opening_subledger_balances set status='SETTLED' where id=b;
  elsif kind='OPENING_PARTY_WASH' then
   update erp.opening_subledger_balances set customer_id=(select customer_id from erp.opening_subledger_balances where id=q) where id=b;
  else
   update erp.journal_lines set customer_id=null where journal_entry_id in(
    select inv.id from erp.journal_entries inv join erp.journal_entries j on j.id=inv.reversal_of_id
    where j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and j.source_id=first);
  end if;
  set local session_replication_role='origin';
  faults:=pg_temp.m_issues();
  if pg_temp.m_report()<>'BLOCKED' or not exists(select 1 from erp.run_v268_financial_report_checks()
    where check_name like 'V2620M_%' and issue_count>0) then raise exception 'M_SOURCE_FAULT_NOT_DETECTED';end if;
  result:=jsonb_build_object('report','BLOCKED','issues',faults,'classification','PRIVILEGED_DISPOSABLE_FAULT_INJECTION');
 else raise exception 'M_UNKNOWN_ORACLE_CASE';end if;
 return result||jsonb_build_object('kind',kind,'status',case when fixed then 'PASS' else 'KNOWN_L_BUG_REPRODUCED' end);
end
$$;
