CREATE OR REPLACE FUNCTION erp.initial_prepayment_checks_v1()
RETURNS TABLE(check_name text,severity text,issue_count bigint,details text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select 'AP_PREPAYMENT_CAPACITY','CRITICAL',count(*)::bigint,'Current opening minus refunds and native posted applications must remain nonnegative'
 from erp.initial_import_prepayments a cross join lateral(select erp.initial_prepayment_state_v1(a.id) s) v
 where (s->>'remaining_amount')::numeric<0 or (s->>'opening_amount')::numeric<0 or (s->>'refunded_amount')::numeric<0
 union all
 select 'AP_PREPAYMENT_PAYMENT_SOURCE','CRITICAL',count(*)::bigint,'Every application retains its source, exact payment snapshot, and party; cash is absent'
 from erp.initial_import_prepayments a cross join lateral erp.initial_prepayment_payments_v1(a.id) p
 join erp.initial_import_prepayment_payments l on l.payment_id=p.payment_id
 where p.party_id<>a.party_id or p.party_type<>a.party_type or p.amount<=0 or p.cash_account_id is not null
   or p.payment_snapshot is distinct from l.payment_snapshot or p.payment_snapshot->>'payment_method' is distinct from 'OPENING_ADVANCE'
   or erp._cp3_business_date(p.payment_date)<a.cutover_date
 union all
 select 'AP_PREPAYMENT_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,'Applied advances retain exact native liability/receivable journals and their linked inverses'
 from erp.initial_import_prepayments a cross join lateral erp.initial_prepayment_payments_v1(a.id) p
 cross join lateral(select case a.party_type when 'SUPPLIER' then erp.account_id('AP_SUPPLIER') when 'CUSTOMER' then erp.account_id('AR_CUSTOMER') else erp.account_id('AP_VENDOR') end account_id,
   case when a.party_type='CUSTOMER' then 1 else -1 end sign) k
 where (p.status='DRAFT' and exists(select 1 from erp.journal_entries where source_type=p.source_type and source_id=p.payment_id))
   or(p.status in('POSTED','REVERSED') and (
     (select count(*) from erp.journal_entries where source_type=p.source_type and source_id=p.payment_id)<>1
     or not exists(select 1 from erp.journal_entries j where j.source_type=p.source_type and j.source_id=p.payment_id
       and j.status=p.status and j.economic_date=erp._cp3_business_date(p.payment_date)
       and (select count(*) from erp.journal_lines where journal_entry_id=j.id)=2
       and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(a.coa_account_id::text,p.amount*k.sign,k.account_id::text,-p.amount*k.sign)
       and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and
         (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null))
       and (select count(*) from erp.journal_entries where reversal_of_id=j.id)=case when p.status='REVERSED' then 1 else 0 end
       and (p.status<>'REVERSED' or exists(select 1 from erp.journal_entries x where x.reversal_of_id=j.id and x.status='POSTED'
         and erp._cp6_supplier_cent_ledger(array[j.id,x.id])='{}'::jsonb)))))
 union all
 select 'AP_PREPAYMENT_OPENING_JOURNAL','CRITICAL',count(*)::bigint,'Opening prepayment posts only the carried balance once at cutover, without historical cash'
 from erp.initial_import_prepayments a
 where (select count(*) from erp.journal_entries where source_type='OPENING_PREPAYMENT' and source_id=a.id)<>1
   or not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_PREPAYMENT' and j.source_id=a.id
     and j.status='POSTED' and j.economic_date=a.cutover_date
     and (select count(*) from erp.journal_lines where journal_entry_id=j.id)=2
     and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(
       a.coa_account_id::text,case when a.party_type='CUSTOMER' then -a.amount else a.amount end,
       erp.account_id('OPENING_EQUITY')::text,case when a.party_type='CUSTOMER' then a.amount else -a.amount end)
     and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
       and (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null)))
 union all
 select 'AP_PREPAYMENT_EVENT_JOURNAL','CRITICAL',count(*)::bigint,'Corrections, cash refunds, and append-only reversals retain exact money and economic dates'
 from erp.initial_import_prepayment_events e join erp.initial_import_prepayments a on a.id=e.advance_id
 left join erp.initial_import_prepayment_events prior on prior.id=e.reverses_event_id
 left join erp.journal_entries j on j.id=e.journal_entry_id
 cross join lateral(select case when a.party_type='CUSTOMER' then -e.delta else e.delta end amount,
   case when e.component='CORRECTION' then erp.account_id('OPENING_EQUITY') else (select coa_account_id from erp.cash_accounts where id=e.cash_account_id) end account_id) k
 where j.id is null or j.economic_date<>e.effective_date or e.effective_date<a.cutover_date
   or j.source_type<>case when e.event_type='REVERSAL' then 'JOURNAL_REVERSAL' else 'PREPAYMENT_EVENT' end
   or (e.event_type<>'REVERSAL' and j.source_id<>e.id)
   or (e.event_type='REVERSAL' and (prior.advance_id is distinct from e.advance_id or prior.event_type='REVERSAL'
     or e.delta<>-prior.delta or e.component<>prior.component or j.reversal_of_id is distinct from prior.journal_entry_id))
   or j.status<>case when exists(select 1 from erp.initial_import_prepayment_events x where x.reverses_event_id=e.id) then 'REVERSED' else 'POSTED' end
   or (select count(*) from erp.journal_lines where journal_entry_id=j.id)<>2
   or erp._cp6_supplier_cent_ledger(array[j.id]) is distinct from jsonb_build_object(a.coa_account_id::text,k.amount,k.account_id::text,-k.amount)
   or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
     and (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null))
 union all
 select 'AP_PREPAYMENT_GL_SUBLEDGER','CRITICAL',count(*)::bigint,'Each dedicated advance account equals current remaining balances across all sources'
 from (select a.coa_account_id,sum((erp.initial_prepayment_state_v1(a.id)->>'remaining_amount')::numeric
   *case when a.party_type='CUSTOMER' then -1 else 1 end) expected from erp.initial_import_prepayments a group by a.coa_account_id) x
 where x.expected is distinct from (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
   join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=x.coa_account_id and j.status in('POSTED','REVERSED'));
$function$;
