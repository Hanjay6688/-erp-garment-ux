-- Shared native/PGlite oracles. Caller owns an isolated disposable transaction
-- and rolls back each case, including every privileged detector fault.
create or replace function pg_temp.l_line(a uuid,d numeric,c numeric,v uuid default null)
returns jsonb language sql as $$
 select jsonb_build_object('account_id',a,'debit',d,'credit',c,'vendor_id',v)
$$;
create or replace function pg_temp.l_post(lines jsonb) returns uuid language sql as $$
 select erp.post_journal('COMPETITION_L',gen_random_uuid(),current_date,
   'CP6 exact ledger conservation oracle',lines)
$$;
create or replace function pg_temp.l_boundary() returns jsonb language sql as $$
 select jsonb_build_object(
 'journals',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'')) from erp.journal_entries t),
 'lines',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'')) from erp.journal_lines t),
 'daily',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by balance_date,account_id)::text,'')) from erp.account_daily_balances t),
 'claims',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'')) from erp.laundry_claims t),
 'idempotency',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text)::text,'')) from erp.idempotency_requests t),
 'stock',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'')) from erp.fg_stock_movements t),
 'audit',(select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'')) from erp.audit_logs t))
$$;
create or replace function pg_temp.l_report() returns text language sql as $$
 select case when exists(select 1 from erp.run_v268_financial_report_checks()
 where issue_count>0 and severity='CRITICAL') then 'BLOCKED' else 'READY' end
$$;
create or replace function pg_temp.l_ap(v uuid) returns numeric language sql as $$
 select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l
 join erp.journal_entries j on j.id=l.journal_entry_id
 where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id=v
$$;
create or replace function pg_temp.l_case(kind text, fixed boolean, vendor uuid, delivery uuid default null)
returns jsonb language plpgsql as $$
declare cash uuid; equity uuid; ap uuid; j1 uuid; j2 uuid; lines jsonb;
 before_state jsonb; after_state jsonb; observed jsonb; claim jsonb; claim_id uuid;
 accepted boolean:=false; code text; debit numeric; credit numeric; state text;
 faults jsonb; variant text; variants jsonb:='[]'::jsonb; required_check text;
begin
 select coa_account_id into cash from erp.cash_accounts where is_active order by cash_account_code limit 1;
 equity:=erp.account_id('OPENING_EQUITY'); ap:=erp.account_id('AP_VENDOR');
 if pg_temp.l_report()<>'READY' or pg_temp.l_ap(vendor)<>0 then
   raise exception 'L_READY_ZERO_AP_BASELINE_REQUIRED';
 end if;
 if kind in('CENT_CONTROL','NORMALIZED_CONTROL','SPLIT_HALF_CENT') then
   if kind='NORMALIZED_CONTROL' then
     lines:=jsonb_build_array(pg_temp.l_line(cash,.01,0),pg_temp.l_line(equity,0,.014));
   elsif kind='SPLIT_HALF_CENT' then
     lines:=jsonb_build_array(pg_temp.l_line(cash,.005,0),pg_temp.l_line(cash,.005,0),pg_temp.l_line(equity,0,.01));
   else
     lines:=jsonb_build_array(pg_temp.l_line(cash,.01,0),pg_temp.l_line(cash,.01,0),pg_temp.l_line(equity,0,.02));
   end if;
   before_state:=pg_temp.l_boundary();
   begin j1:=pg_temp.l_post(lines); accepted:=true;
   exception when raise_exception then code:=sqlstate; end;
   after_state:=pg_temp.l_boundary();state:=pg_temp.l_report();
   if accepted then
     select sum(l.debit),sum(l.credit) into debit,credit from erp.journal_lines l where journal_entry_id=j1;
   end if;
   if kind='SPLIT_HALF_CENT' then
     if fixed then
       if accepted or code<>'P0001' or before_state<>after_state or state<>'READY' then
         raise exception 'L_IMBALANCED_STORAGE_NOT_ATOMICALLY_REJECTED'; end if;
     elsif not accepted or debit<>.02 or credit<>.01 or state<>'READY' then
       raise exception 'K_SPLIT_HALF_CENT_COUNTEREXAMPLE_NOT_REPRODUCED';
     end if;
   elsif not accepted or debit<>credit or debit<>(case when kind='CENT_CONTROL' then .02 else .01 end) or state<>'READY' then
     raise exception 'L_VALID_CENT_NORMALIZATION_FAILED';
   end if;
   observed:=jsonb_build_object('accepted',accepted,'sqlstate',code,'stored_debit',debit,'stored_credit',credit,
     'report',state,'refusal_boundary_unchanged',case when not accepted then before_state=after_state end);
 elsif kind in('NONFINITE','NEGATIVE_INPUT','MALFORMED_LINES') then
   for variant in select unnest(case kind when 'NONFINITE' then array['NaN','Infinity','-Infinity']
     when 'NEGATIVE_INPUT' then array['-0.004','-0.01'] else array['null','{}','[]','[1,2]'] end) loop
     if kind='MALFORMED_LINES' then lines:=variant::jsonb;
     else lines:=jsonb_build_array(pg_temp.l_line(cash,variant::numeric,0),pg_temp.l_line(equity,0,variant::numeric)); end if;
     before_state:=pg_temp.l_boundary();accepted:=false;code:=null;
     begin perform pg_temp.l_post(lines);accepted:=true;
     exception when raise_exception then code:=sqlstate; end;
     after_state:=pg_temp.l_boundary();
     if accepted or code<>'P0001' or before_state<>after_state or pg_temp.l_report()<>'READY' then
       raise exception 'L_INVALID_MONEY_NOT_ATOMICALLY_REJECTED'; end if;
     variants:=variants||jsonb_build_array(jsonb_build_object('variant',variant,'accepted',false,'sqlstate',code,'boundary_unchanged',true));
   end loop;
   observed:=jsonb_build_object('variants',variants,'report','READY');
 elsif kind in('CACHE_CENT','JOURNAL_WASH','EMPTY_JOURNAL','NONFINITE_CACHE','NEGATIVE_AP_FAULT') then
   j1:=pg_temp.l_post(jsonb_build_array(pg_temp.l_line(cash,1,0),pg_temp.l_line(equity,0,1)));
   j2:=pg_temp.l_post(jsonb_build_array(pg_temp.l_line(cash,1,0),pg_temp.l_line(equity,0,1)));
   if pg_temp.l_report()<>'READY' then raise exception 'L_VALID_LEDGER_CONTROL_FAILED'; end if;
   -- Utility SET is required on the pinned native Supabase image; no role or
   -- parameter privilege is granted. Only these disposable detector cases use it.
   set local session_replication_role='replica';
   if kind='CACHE_CENT' then
     update erp.account_daily_balances set debit_total=debit_total+.01 where balance_date=current_date and account_id=cash;
     update erp.account_daily_balances set credit_total=credit_total+.01 where balance_date=current_date and account_id=equity;
     required_check:='V268_DAILY_BALANCE_LEDGER_MISMATCH';
   elsif kind='JOURNAL_WASH' then
     update erp.journal_lines l set credit=l.credit+.01 where journal_entry_id=j1 and account_id=equity;
     update erp.journal_lines l set credit=l.credit-.01 where journal_entry_id=j2 and account_id=equity;
     required_check:='V268_UNBALANCED_POSTED_JOURNAL';
   elsif kind='EMPTY_JOURNAL' then
     delete from erp.journal_lines where journal_entry_id=j1;
     required_check:='V268_UNBALANCED_POSTED_JOURNAL';
   elsif kind='NONFINITE_CACHE' then
     update erp.account_daily_balances set debit_total='NaN'::numeric where balance_date=current_date and account_id=cash;
     required_check:='V2620L_NONFINITE_LEDGER_MONEY';
   else
     update erp.journal_lines set account_id=ap,vendor_id=vendor,debit=.01 where journal_entry_id=j1 and account_id=cash;
     required_check:='V2620L_NEGATIVE_VENDOR_AP';
   end if;
   set local session_replication_role='origin';
   state:=pg_temp.l_report();
   select coalesce(jsonb_agg(jsonb_build_object('check',check_name,'count',issue_count)),'[]'::jsonb)
     into faults from erp.run_v268_financial_report_checks() where issue_count>0;
   if fixed then
     if state<>'BLOCKED' or not exists(select 1 from erp.run_v268_financial_report_checks()
       where check_name=required_check and issue_count>0) then raise exception 'L_LEDGER_DETECTOR_FAILED'; end if;
   elsif kind<>'CACHE_CENT' or state<>'READY' then raise exception 'K_CACHE_CENT_COUNTEREXAMPLE_NOT_REPRODUCED'; end if;
   observed:=jsonb_build_object('classification','PRIVILEGED_DISPOSABLE_FAULT_INJECTION','report',state,'issues',faults);
 elsif kind in('AP_OVERDRAW','AP_ZERO_CONTROL','CLAIM_OVERDRAW','CLAIM_ZERO_CONTROL') then
   if kind in('AP_ZERO_CONTROL','CLAIM_ZERO_CONTROL') then
     perform pg_temp.l_post(jsonb_build_array(pg_temp.l_line(cash,.01,0),pg_temp.l_line(ap,0,.01,vendor)));
   end if;
   if kind like 'CLAIM_%' then
     if delivery is null then raise exception 'L_REAL_DELIVERY_FIXTURE_REQUIRED'; end if;
     claim:=erp.save_laundry_claim_v2(jsonb_build_object('claim_number','COMP-L-'||gen_random_uuid(),
       'vendor_id',vendor,'delivery_id',delivery,'qty_claimed',1,'claim_type','MISSING',
       'compensation_amount',.01,'change_reason','CP6 exact payable admission oracle'),gen_random_uuid(),null);
     claim_id:=(claim->>'laundry_claim_id')::uuid;
   end if;
   before_state:=pg_temp.l_boundary();debit:=pg_temp.l_ap(vendor);
   begin
     if claim_id is not null then
       perform erp.resolve_laundry_claim_v2(claim_id,'SETTLED','CP6 exact payable settlement',
         gen_random_uuid(),(claim->>'row_version')::bigint);
     else perform pg_temp.l_post(jsonb_build_array(pg_temp.l_line(ap,.01,0,vendor),pg_temp.l_line(cash,0,.01,vendor)));
     end if;
     accepted:=true;
   exception when raise_exception then code:=sqlstate; end;
   after_state:=pg_temp.l_boundary();credit:=pg_temp.l_ap(vendor);state:=pg_temp.l_report();
   if kind in('AP_OVERDRAW','CLAIM_OVERDRAW') then
     if fixed then
       if accepted or code<>'P0001' or before_state<>after_state or credit<>0 or state<>'READY' then
         raise exception 'L_NEGATIVE_VENDOR_AP_NOT_ATOMICALLY_REJECTED'; end if;
     elsif kind<>'CLAIM_OVERDRAW' or not accepted or debit<>0 or credit<>-.01 or state<>'READY'
       or (select status from erp.laundry_claims where id=claim_id)<>'SETTLED' then
       raise exception 'K_REAL_CLAIM_COUNTEREXAMPLE_NOT_REPRODUCED'; end if;
   elsif not accepted or debit<>.01 or credit<>0 or state<>'READY' then
     raise exception 'L_LAST_CENT_SETTLEMENT_CONTROL_FAILED';
   end if;
   observed:=jsonb_build_object('accepted',accepted,'sqlstate',code,'ap_before',debit,'ap_after',credit,
     'claim_status',(select status from erp.laundry_claims where id=claim_id),'report',state,
     'refusal_boundary_unchanged',case when not accepted then before_state=after_state end);
 else raise exception 'L_UNKNOWN_ORACLE_CASE'; end if;
 return observed||jsonb_build_object('kind',kind,'status',case when fixed then 'PASS' else 'KNOWN_K_BUG_REPRODUCED' end);
end
$$;
