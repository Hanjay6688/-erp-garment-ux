-- The same timestamp must book to the canonical Jakarta business date.
-- Requires m_* / o_* disposable helpers. Detector probes replay the recorded
-- predecessor payment function in an owned tester subtransaction, then restore
-- S before reading its detector. All fixture facts and DDL are rolled back.
create function pg_temp.s_payment_draft(p_purchase uuid,p_date timestamptz,p_amount numeric default 40)
returns uuid language plpgsql as $$
declare v_id uuid:=gen_random_uuid();begin
  insert into erp.supplier_payments(id,purchase_id,payment_number,payment_date,amount,cash_account_id,status)
  select v_id,p_purchase,'S-PAY-'||v_id,p_date,p_amount,c.id,'DRAFT'
  from erp.cash_accounts c where c.is_active order by c.cash_account_code limit 1;
  return v_id;
end$$;

create function pg_temp.s_payment_state(p_id uuid) returns jsonb language sql as $$
  select jsonb_build_object('payment_status',p.status,'instant_utc',to_char(p.payment_date at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    'canonical_date',erp._cp3_business_date(p.payment_date)::text,
    'original_date',j.economic_date::text,'original_status',j.status,
    'original_cash_credit',coalesce((select sum(l.credit-l.debit) from erp.journal_lines l
      join erp.cash_accounts c on c.coa_account_id=l.account_id and c.id=p.cash_account_id
      where l.journal_entry_id=j.id),0),
    'report',pg_temp.m_report(),'issues',pg_temp.m_issues())
  from erp.supplier_payments p left join erp.journal_entries j
    on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id and j.status in('POSTED','REVERSED')
  where p.id=p_id
$$;

create function pg_temp.s_case(p_case text,p_fixed boolean) returns jsonb language plpgsql as $$
declare v_purchase uuid;v_pay uuid;v_second uuid;v_date timestamptz:='2026-09-03T00:30:00+07';
 v_zone text:='UTC';v_expected text:='2026-09-03';v_state jsonb;v_after jsonb;v_before jsonb;
 v_detector bigint;v_report text;v_affected boolean:=false;v_fault boolean:=false;v_reversed boolean:=false;
 v_rejected boolean:=false;v_result jsonb;v_fault_pay uuid;
 v_current_definition text;v_predecessor_definition text;
begin
 if pg_temp.m_report()<>'READY' then raise exception 'S_BASELINE_NOT_READY';end if;
 if p_case in('UTC_LOCAL_MIDNIGHT','NEW_YORK_LOCAL_MIDNIGHT','UTC_EVENING','REVERSED_WRONG_ORIGINAL') then
   v_affected:=true;
 elsif p_case in('DETECTOR_POSTED_DATE','DETECTOR_REVERSED_DATE') then
   v_affected:=true;v_fault:=true;v_zone:='Asia/Jakarta';
 elsif p_case='JAKARTA_LOCAL_MIDNIGHT' then v_zone:='Asia/Jakarta';
 elsif p_case='TOKYO_LOCAL_MIDNIGHT' then v_zone:='Asia/Tokyo';
 elsif p_case='MIDDAY_UTC' then v_date:='2026-09-03T12:00:00Z';
 elsif p_case='EQUIVALENT_OFFSET' then v_zone:='Asia/Jakarta';
 elsif p_case not in('DRAFT_NO_JOURNAL','OVERPAY_ATOMIC') then raise exception 'S_UNKNOWN_CASE';
 end if;
 if p_case='NEW_YORK_LOCAL_MIDNIGHT' then v_zone:='America/New_York';end if;
 if p_case='UTC_EVENING' then v_date:='2026-09-02T23:30:00Z';end if;
 v_reversed:=p_case in('REVERSED_WRONG_ORIGINAL','DETECTOR_REVERSED_DATE');
 v_purchase:=pg_temp.m_purchase(10,10,true);
 v_pay:=pg_temp.s_payment_draft(v_purchase,v_date,case when p_case='OVERPAY_ATOMIC' then 101 else 40 end);
 perform set_config('TimeZone',v_zone,true);
 if p_case='DRAFT_NO_JOURNAL' then
   v_state:=pg_temp.s_payment_state(v_pay);
   if v_state->>'payment_status'<>'DRAFT' or v_state->>'original_date' is not null
      or v_state->>'report'<>'READY' then raise exception 'S_DRAFT_NOT_INERT';end if;
 elsif p_case='OVERPAY_ATOMIC' then
   v_before:=pg_temp.o_boundary();
   begin perform erp.post_supplier_payment(v_pay);
   exception when sqlstate 'P0001' then
     if sqlerrm not like 'Supplier payment exceeds remaining payable.%' then raise;end if;
     v_rejected:=true;
   end;
   if not v_rejected or pg_temp.o_boundary() is distinct from v_before then raise exception 'S_OVERPAY_NOT_ATOMIC';end if;
   v_state:=pg_temp.s_payment_state(v_pay);
 else
   perform erp.post_supplier_payment(v_pay);
   if v_reversed then perform erp.reverse_supplier_payment(v_pay,'S original date lifecycle control');end if;
   v_state:=pg_temp.s_payment_state(v_pay);
   if v_state->>'report'<>'READY' or (v_state->>'original_cash_credit')::numeric<>40
      or v_state->>'canonical_date'<>v_expected then raise exception 'S_POSTED_MONEY_OR_REPORT %',v_state;end if;
   if not v_fault and v_state->>'original_date'<>(case when p_fixed or not v_affected then v_expected else '2026-09-02' end) then
     raise exception 'S_BUSINESS_DATE_EXPECTATION %',v_state;
   end if;
   if p_case='EQUIVALENT_OFFSET' then
     v_second:=pg_temp.s_payment_draft(v_purchase,'2026-09-02T17:30:00Z',40);
     perform erp.post_supplier_payment(v_second);v_after:=pg_temp.s_payment_state(v_second);
     if v_after->>'original_date' is distinct from v_state->>'original_date'
       or v_after->>'instant_utc' is distinct from v_state->>'instant_utc'
       or v_after->>'report'<>'READY' then raise exception 'S_EQUIVALENT_INSTANT_DRIFT';end if;
   end if;
   if v_fault then
     v_before:=pg_temp.o_boundary();
     begin
       v_fault_pay:=pg_temp.s_payment_draft(v_purchase,v_date,40);
       if p_fixed then
         select pg_get_functiondef('erp.post_supplier_payment(uuid)'::regprocedure)
           into v_current_definition;
         select object_definition into v_predecessor_definition
           from erp.cp6_v2620s_rollback_capsule
           where object_regidentity='erp.post_supplier_payment(uuid)';
         if encode(extensions.digest(convert_to(v_predecessor_definition,'UTF8'),'sha256'),'hex')
           is distinct from '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8' then
           raise exception 'S_DETECTOR_PREDECESSOR_PIN_MISMATCH';
         end if;
         execute v_predecessor_definition;
       end if;
       perform set_config('TimeZone','UTC',true);
       perform erp.post_supplier_payment(v_fault_pay);
       if p_fixed then execute v_current_definition;end if;
       if v_reversed then
         perform erp.reverse_supplier_payment(v_fault_pay,'S historical original-date detector fixture');
       end if;
       select coalesce(sum(issue_count),0) into v_detector from erp.run_v267_financial_truth_checks()
         where check_name='V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE';
       v_report:=pg_temp.m_report();v_after:=pg_temp.s_payment_state(v_fault_pay);
       raise exception using errcode='ZX001',message='S_FAULT_ROLLBACK';
     exception when sqlstate 'ZX001' then null;
     end;
     if p_fixed and pg_get_functiondef('erp.post_supplier_payment(uuid)'::regprocedure)
       is distinct from v_current_definition then raise exception 'S_DETECTOR_RUNTIME_NOT_RESTORED';end if;
     if v_detector<>(case when p_fixed then 1 else 0 end)
       or v_report<>(case when p_fixed then 'BLOCKED' else 'READY' end)
       or pg_temp.o_boundary() is distinct from v_before or pg_temp.m_report()<>'READY' then
       raise exception 'S_DETECTOR_EXPECTATION count=% report=%',v_detector,v_report;
     end if;
   end if;
   -- Reading the same immutable journal under another timezone must not move it.
   perform set_config('TimeZone','America/New_York',true);
   if (pg_temp.s_payment_state(v_pay)->>'original_date') is distinct from v_state->>'original_date'
      or pg_temp.m_report()<>'READY' then raise exception 'S_READ_TIMEZONE_DRIFT';end if;
 end if;
 perform set_config('TimeZone','UTC',true);
 v_result:=jsonb_build_object('status',case when p_fixed then 'PASS' when v_affected then 'KNOWN_R_BUG_REPRODUCED' else 'CONTROL_PASS' end,
   'case',p_case,'posting_timezone',v_zone,'state',v_state,'second_or_fault_state',v_after,
   'detector_issue_count',v_detector,'detector_report',v_report,'fault_rolled_back',v_fault,
   'overpay_refused_atomically',v_rejected,'http_ui_reachability_proven',false);
 return v_result;
end$$;
