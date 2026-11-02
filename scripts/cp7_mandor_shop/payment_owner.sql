-- Closed private Native adapters' owner. No installer, public RPC or grant.
-- Native wages/cash stay with the original payroll functions. This owner
-- posts only the exact noncash Dr payable / Cr invoice receivable settlement.
create table cp7_mandor_shop.payment_work(
 backend_pid integer not null,
 transaction_id bigint not null,
 actor uuid not null,
 request_id uuid not null,
 payroll_id uuid not null references erp.payroll_settlements(id),
 source text not null check(source in('PAYROLL','INSTALLMENT')),
 native_action text not null,
 mode text not null check(mode in('SETTLE','REOPEN','REVERSE','CANCEL')),
 native_before_status text not null,
 payload jsonb not null,
 expected_version text not null,
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 access_snapshot jsonb not null,
 invoices_before jsonb not null,
 invoice_delta jsonb not null default '{}',
 settlement_id uuid references cp7_mandor_shop.settlements(id),
 primary key(backend_pid,transaction_id)
);
alter table cp7_mandor_shop.payment_work enable row level security;
revoke all on cp7_mandor_shop.payment_work from public,anon,authenticated,service_role;

create function cp7_mandor_shop.payment_begin(p_source text,p_action text,p jsonb,p_request uuid,p_expected text)
returns void language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare payroll_ uuid;h_ erp.payroll_settlements;native_ text;mode_ text;access_ jsonb;
 digest_ text;r_ record;basis_ jsonb;invoices_ jsonb:='{}';net_ numeric;date_ date;
begin
 if p_source is null or p_source not in('PAYROLL','INSTALLMENT')then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_PAYMENT_OWNER_REQUIRED';end if;
 if p_source='PAYROLL'and p_action in('PREPARE','APPROVE')then return;end if;
 if(p_source='PAYROLL'and coalesce(p_action,'')not in('PAY','CANCEL','REVERSE'))
  or(p_source='INSTALLMENT'and coalesce(p_action,'')not in('PAY','REVERSE_PAYMENT','REVERSE_PAYROLL'))then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_PAYMENT_ACTION_REQUIRED';end if;
 payroll_:=(p->>case p_source when'PAYROLL'then'id'else'payroll_id'end)::uuid;
 select *into strict h_ from erp.payroll_settlements where id=payroll_ for update nowait;
 -- Ordinary payrolls gain no FG context, journal, request, or new permission.
 if not exists(select 1 from cp7_mandor_shop.allocation_states
  where payroll_id=payroll_ and state in('RESERVED','SETTLED'))then return;end if;
 if current_setting('transaction_isolation')<>'read committed'or auth.uid()is null
  or p_request is null or p_expected is null or jsonb_typeof(p)is distinct from'object'then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_EXACT_NATIVE_PAYMENT_CONTEXT_REQUIRED';end if;
 mode_:=case when p_action='PAY'then'SETTLE'when p_action='REVERSE_PAYMENT'then'REOPEN'
  when p_action='CANCEL'then'CANCEL'else'REVERSE'end;
 native_:=case when p_source='PAYROLL'then p_action
  when p_action='REVERSE_PAYROLL'then case h_.status when'PAID'then'REVERSE'else'CANCEL'end else'PAY'end;
 if not exists(select 1 from cp7_payroll.settlement_context c
  where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current_if_assigned()
   and c.actor=auth.uid()and c.payroll_id=payroll_ and c.action=native_)
  or(p_source='PAYROLL'and not exists(select 1 from cp7_payroll.settlement_requests n
   where n.actor=auth.uid()and n.request_id=p_request and n.action=p_action
    and n.payload=p and n.expected_version=p_expected and n.response is null))
  or(p_source='INSTALLMENT'and not exists(select 1 from cp7_installment.command_context n
   where n.backend_pid=pg_backend_pid()and n.transaction_id=txid_current_if_assigned()
    and n.actor=auth.uid()and n.request_id=p_request and n.action=p_action
    and n.payload=p and n.expected_version=p_expected))then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_EXPLICIT_ORIGINAL_NATIVE_REQUEST_REQUIRED';end if;
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))
  or not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP|'||h_.contractor_id::text,0))
  or not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP_REQUEST|'||auth.uid()::text||'|'||p_request::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_SOURCE_BUSY_REVIEW_AGAIN';end if;
 lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;
 lock table erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts in share mode nowait;
 access_:=case p_source when'PAYROLL'then cp7_payroll.settlement_access(p_action)
  else cp7_installment.access_now(p_action)end;
 if erp.has_permission('finance.ar.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_DENIED';end if;
 if exists(select 1 from cp7_mandor_shop.requests where actor=auth.uid()and request_id=p_request)then
  -- Native replay returns its original response BEFORE this owner is entered.
  -- Re-entering with a missing/different Native cache must never post again.
  raise exception 'CP7_MANDOR_SHOP_NATIVE_REQUEST_ALREADY_OWNED';end if;
 perform 1 from erp.contractors where id=h_.contractor_id for share nowait;
 perform 1 from erp.sales_headers sale_ where exists(select 1 from cp7_mandor_shop.allocation_states a
  where a.payroll_id=payroll_ and a.sale_id=sale_.id and a.state in('RESERVED','SETTLED'))
  order by sale_.id for update nowait;
 perform 1 from erp.payroll_work_items where payroll_id=payroll_ order by id for update nowait;
 perform 1 from erp.payroll_attendance_items where payroll_id=payroll_ order by id for update nowait;
 perform 1 from erp.payroll_reimbursements where payroll_id=payroll_ order by id for update nowait;
 perform 1 from erp.payroll_deductions where payroll_id=payroll_ order by id for update nowait;
 basis_:=cp7_mandor_shop.payroll_basis(payroll_);net_:=(basis_->>'calculated_net')::numeric;
 if p_action='PAY'and(h_.status is distinct from'APPROVED'or net_<0 or net_ is distinct from h_.net_payable)then
  raise exception 'CP7_MANDOR_SHOP_APPROVED_NATIVE_PAYROLL_MEANING_CHANGED';end if;
 if p_action='PAY'then date_:=(p->>'payment_date')::date;end if;
 for r_ in select distinct sale_id from cp7_mandor_shop.allocation_states
  where payroll_id=payroll_ and state in('RESERVED','SETTLED')order by sale_id loop
  basis_:=cp7_mandor_shop.invoice_basis(r_.sale_id);
  if(basis_#>>'{posted_buyer,contractor_id}')::uuid is distinct from h_.contractor_id then
   raise exception 'CP7_MANDOR_SHOP_WRONG_MANDOR';end if;
  if p_action='PAY'and(basis_#>>'{header,status}'not in('POSTED','PARTIAL_PAID')
   or(basis_->>'available_to_reserve')::numeric<0
   or date_ is null or date_<(select(sale_date at time zone'Asia/Jakarta')::date
    from erp.sales_headers where id=r_.sale_id))then
   raise exception 'CP7_MANDOR_SHOP_INVOICE_BALANCE_OR_PHYSICAL_DATE_CHANGED_REVIEW_REQUIRED';end if;
  invoices_:=invoices_||jsonb_build_object(r_.sale_id::text,basis_->>'effective_paid');
 end loop;
 digest_:=encode(extensions.digest(convert_to(jsonb_build_array(p_source,p_action,p,p_expected)::text,'UTF8'),'sha256'),'hex');
 insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,mode_,digest_);
 insert into cp7_mandor_shop.payment_work(backend_pid,transaction_id,actor,request_id,payroll_id,source,
  native_action,mode,native_before_status,payload,expected_version,payload_sha256,access_snapshot,invoices_before)
 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,payroll_,p_source,p_action,mode_,h_.status,p,p_expected,digest_,access_,invoices_);
end $$;

create function cp7_mandor_shop.settle_payroll(p_payroll uuid)returns uuid
language plpgsql volatile security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;work_ cp7_mandor_shop.payment_work;
 h_ erp.payroll_settlements;s_ record;j_ erp.journal_entries;amount_ numeric;settlement_ uuid;journal_ uuid;
 payable_ uuid;ar_ uuid;customer_ uuid;
begin
 if not exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=p_payroll
  and state in('RESERVED','SETTLED'))then return null;end if;
 ctx_:=cp7_mandor_shop.require_context(array['SETTLE']);
 select *into strict work_ from cp7_mandor_shop.payment_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current_if_assigned()and actor=ctx_.actor and request_id=ctx_.request_id
  and payroll_id=p_payroll and mode='SETTLE'for update;
 if work_.settlement_id is not null then
  perform cp7_mandor_shop.offset_proof(work_.settlement_id);return work_.settlement_id;end if;
 select *into strict h_ from erp.payroll_settlements where id=p_payroll for update;
 if h_.status is distinct from'PAID'or h_.net_payable<0
  or h_.net_payable is distinct from(cp7_mandor_shop.payroll_basis(p_payroll)->>'calculated_net')::numeric
  or exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state='SETTLED')then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NEW_PAID_PAYROLL_REQUIRED';end if;
 select sum(amount)into amount_ from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state='RESERVED';
 if amount_ is null or amount_<=0 then raise exception 'CP7_MANDOR_SHOP_RESERVED_AMOUNT_REQUIRED';end if;
 lock table erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts in share mode nowait;
 select account_id into payable_ from erp.accounting_account_mappings where mapping_key='CONTRACTOR_PAYABLE';
 select account_id into ar_ from erp.accounting_account_mappings where mapping_key='AR_CUSTOMER';
 select customer_id into strict customer_ from cp7_mandor_shop.contractor_accounts where contractor_id=h_.contractor_id;
 settlement_:=gen_random_uuid();
 journal_:=erp.post_journal('FG_MANDOR_PAYROLL_OFFSET',settlement_,h_.payment_date,
  'Pelunasan belanja FG melalui payroll '||h_.payroll_number,jsonb_build_array(
   jsonb_build_object('account_id',payable_,'debit',amount_,'credit',0,'contractor_id',h_.contractor_id),
   jsonb_build_object('account_id',ar_,'debit',0,'credit',amount_,'customer_id',customer_)));
 select *into strict j_ from erp.journal_entries where id=journal_;
 insert into cp7_mandor_shop.settlements(id,payroll_id,contractor_id,journal_id,total_amount,economic_date,book_date,actor,request_id)
 values(settlement_,p_payroll,h_.contractor_id,journal_,amount_,j_.economic_date,j_.transaction_date,ctx_.actor,ctx_.request_id);
 insert into cp7_mandor_shop.offset_accounts values(settlement_,payable_,ar_,customer_,ctx_.actor,ctx_.request_id);
 for s_ in select *from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state='RESERVED'
  order by sale_id,allocation_id for update loop
  insert into cp7_mandor_shop.settlement_lines values(settlement_,s_.allocation_id,s_.sale_id,p_payroll,s_.contractor_id,s_.amount);
  insert into cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,predecessor_id,kind,settlement_id,actor,request_id)
  values(gen_random_uuid(),s_.allocation_id,s_.last_ordinal+1,s_.last_event_id,'SETTLE',settlement_,ctx_.actor,ctx_.request_id);
  update cp7_mandor_shop.payment_work set invoice_delta=invoice_delta||jsonb_build_object(s_.sale_id::text,
   (coalesce((invoice_delta->>s_.sale_id::text)::numeric,0)+s_.amount)::text)
  where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 end loop;
 update cp7_mandor_shop.payment_work set settlement_id=settlement_ where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 perform cp7_mandor_shop.offset_proof(settlement_);return settlement_;
end $$;

create function cp7_mandor_shop.reverse_payroll_offsets(p_payroll uuid,p_reason text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;work_ cp7_mandor_shop.payment_work;
 h_ erp.payroll_settlements;s_ record;l_ record;inverse_ uuid;reversal_ uuid;kind_ text;
begin
 if not exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=p_payroll
  and state in('RESERVED','SETTLED'))then return;end if;
 ctx_:=cp7_mandor_shop.require_context(array['REOPEN','REVERSE','CANCEL']);
 select *into strict work_ from cp7_mandor_shop.payment_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current_if_assigned()and actor=ctx_.actor and request_id=ctx_.request_id
  and payroll_id=p_payroll and mode=ctx_.action for update;
 select *into strict h_ from erp.payroll_settlements where id=p_payroll for update;
 if nullif(btrim(p_reason),'')is null
  or(ctx_.action='REOPEN'and h_.status is distinct from'APPROVED')
  or(ctx_.action in('REVERSE','CANCEL')and h_.status is distinct from'REVERSED')then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_REOPEN_OR_REVERSE_REQUIRED';end if;
 kind_:=case ctx_.action when'REOPEN'then'REOPEN'else'REVERSE'end;
 for s_ in select s.*from cp7_mandor_shop.settlements s where s.payroll_id=p_payroll
  and not exists(select 1 from cp7_mandor_shop.settlement_reversals r where r.settlement_id=s.id)
  order by s.created_at desc,s.id desc loop
  if work_.native_before_status is distinct from'PAID'or ctx_.action='CANCEL'then
   raise exception 'CP7_MANDOR_SHOP_ONLY_NATIVE_PAID_OFFSET_CAN_BE_REVERSED';end if;
  inverse_:=erp._cp3_r4_reverse_journal_internal(s_.journal_id,p_reason);reversal_:=gen_random_uuid();
  insert into cp7_mandor_shop.settlement_reversals(id,settlement_id,reversal_journal_id,reason,actor,request_id)
  values(reversal_,s_.id,inverse_,p_reason,ctx_.actor,ctx_.request_id);
  for l_ in select st.*from cp7_mandor_shop.allocation_states st
   where st.settlement_id=s_.id and st.state='SETTLED'order by st.allocation_id for update loop
   insert into cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,predecessor_id,kind,settlement_id,reversal_id,actor,request_id)
   values(gen_random_uuid(),l_.allocation_id,l_.last_ordinal+1,l_.last_event_id,kind_,s_.id,reversal_,ctx_.actor,ctx_.request_id);
   update cp7_mandor_shop.payment_work set invoice_delta=invoice_delta||jsonb_build_object(l_.sale_id::text,
    (coalesce((invoice_delta->>l_.sale_id::text)::numeric,0)-l_.amount)::text)
   where backend_pid=pg_backend_pid()and transaction_id=txid_current();
   if kind_='REVERSE'then delete from cp7_mandor_shop.deduction_links where allocation_id=l_.allocation_id;end if;
  end loop;
  perform cp7_mandor_shop.offset_proof(s_.id);
 end loop;
 if ctx_.action<>'REOPEN'then
  -- RELEASE uses the existing cancellation event owner. Keep actor/request/hash
  -- exact; restore the original mode before returning to the Native caller.
  update cp7_mandor_shop.command_context set action='CANCEL'where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  for l_ in select *from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state='RESERVED'
   order by allocation_id for update loop
   delete from cp7_mandor_shop.deduction_links where allocation_id=l_.allocation_id;
   insert into cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,predecessor_id,kind,actor,request_id)
   values(gen_random_uuid(),l_.allocation_id,l_.last_ordinal+1,l_.last_event_id,'RELEASE',ctx_.actor,ctx_.request_id);
  end loop;
  update cp7_mandor_shop.command_context set action=ctx_.action where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 end if;
end $$;

create function cp7_mandor_shop.payment_finish(p_payroll uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;work_ cp7_mandor_shop.payment_work;h_ erp.payroll_settlements;
 access_ jsonb;r_ record;paid_ numeric;net_ numeric;expected_ numeric;status_ text;
 other_ numeric;other_journals_ integer;other_posted_ numeric;other_legs_ integer;
begin
 select *into work_ from cp7_mandor_shop.payment_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current_if_assigned()and actor=auth.uid()and payroll_id=p_payroll;
 if work_.payroll_id is null then return;end if;
 ctx_:=cp7_mandor_shop.require_context(array[work_.mode]);
 if(ctx_.actor,ctx_.request_id,ctx_.payload_sha256)is distinct from(work_.actor,work_.request_id,work_.payload_sha256)then
  raise exception 'CP7_MANDOR_SHOP_NATIVE_PAYMENT_CONTEXT_CHANGED';end if;
 select *into strict h_ from erp.payroll_settlements where id=p_payroll;
 if(work_.mode='SETTLE'and(h_.status not in('APPROVED','PAID')
   or(h_.status='PAID'and exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state='RESERVED'))
   or(h_.status='APPROVED'and work_.settlement_id is not null)))
  or(work_.mode='REOPEN'and(h_.status is distinct from'APPROVED'
   or exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state='SETTLED')))
  or(work_.mode in('REVERSE','CANCEL')and(h_.status is distinct from'REVERSED'
   or exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=p_payroll and state in('RESERVED','SETTLED'))))then
  raise exception 'CP7_MANDOR_SHOP_NATIVE_PAYMENT_DID_NOT_COMPLETE_EXACT_FG_LIFECYCLE';end if;
 if work_.mode='SETTLE'and h_.status='PAID'then
  select coalesce(sum(d.amount),0)into other_ from erp.payroll_deductions d
   where d.payroll_id=p_payroll and d.deduction_type not in('MATERIAL_KASBON','CASH_ADVANCE')
    and not exists(select 1 from cp7_mandor_shop.deduction_links l where l.deduction_id=d.id);
  select count(distinct j.id),coalesce(sum(l.credit)filter(where l.account_id=(
   select account_id from erp.accounting_account_mappings where mapping_key='OTHER_INCOME')),0),count(l.id)
  into other_journals_,other_posted_,other_legs_
  from erp.journal_entries j left join erp.journal_lines l on l.journal_entry_id=j.id
  where j.source_type='PAYROLL_OTHER_DEDUCTION'and j.source_id=p_payroll and j.status='POSTED';
  if other_posted_ is distinct from other_
   or other_journals_<>(case when other_>0 then 1 else 0 end)
   or other_legs_<>(case when other_>0 then 2 else 0 end)then
   raise exception 'CP7_MANDOR_SHOP_FG_MUST_NOT_ENTER_NATIVE_OTHER_INCOME';end if;
 end if;
 for r_ in select key,value from jsonb_each_text(work_.invoices_before)order by key loop
  expected_:=r_.value::numeric+coalesce((work_.invoice_delta->>r_.key)::numeric,0);
  paid_:=cp7_credit.current_effective_paid(r_.key::uuid);net_:=erp.sale_net_total(r_.key::uuid);
  if paid_ is distinct from expected_ or paid_<0 or paid_>net_ then
   raise exception 'CP7_MANDOR_SHOP_SAME_AUTHORITATIVE_INVOICE_PAID_PROJECTION_REQUIRED';end if;
  status_:=case when paid_=net_ and net_>=0 then'PAID'when paid_>0 then'PARTIAL_PAID'else'POSTED'end;
  if coalesce((work_.invoice_delta->>r_.key)::numeric,0)<>0 then
   update erp.sales_headers set status=status_ where id=r_.key::uuid and status is distinct from status_;
  end if;
 end loop;
 access_:=case work_.source when'PAYROLL'then cp7_payroll.settlement_access(work_.native_action)
  else cp7_installment.access_now(work_.native_action)end;
 if access_ is distinct from work_.access_snapshot or erp.has_permission('finance.ar.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;
 insert into cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response)
 values(work_.actor,work_.request_id,work_.source||':'||work_.native_action,
  jsonb_build_object('native_owner',work_.source,'action',work_.native_action,'payload',work_.payload,'expected_version',work_.expected_version),
  work_.payload_sha256,jsonb_build_object('payroll_id',p_payroll,'native_status',h_.status,
   'settlement_id',work_.settlement_id,'invoice_delta',work_.invoice_delta,'noncash',true,'cash_created_by_this_owner',false));
 delete from cp7_mandor_shop.payment_work where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 delete from cp7_mandor_shop.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
end $$;

alter function cp7_mandor_shop.payment_begin(text,text,jsonb,uuid,text)owner to postgres;
alter function cp7_mandor_shop.settle_payroll(uuid)owner to postgres;
alter function cp7_mandor_shop.reverse_payroll_offsets(uuid,text)owner to postgres;
alter function cp7_mandor_shop.payment_finish(uuid)owner to postgres;
revoke all on function cp7_mandor_shop.payment_begin(text,text,jsonb,uuid,text),
 cp7_mandor_shop.settle_payroll(uuid),cp7_mandor_shop.reverse_payroll_offsets(uuid,text),
 cp7_mandor_shop.payment_finish(uuid)from public,anon,authenticated,service_role;
-- settlement_command is the existing invoker function owned by this internal
-- NOLOGIN role. Grant only its two entry/exit adapters, never private tables
-- or the journal/event owners. Other Native hooks already execute as postgres.
grant usage on schema cp7_mandor_shop to cp7_payroll_write;
grant execute on function cp7_mandor_shop.payment_begin(text,text,jsonb,uuid,text),
 cp7_mandor_shop.payment_finish(uuid)to cp7_payroll_write;
