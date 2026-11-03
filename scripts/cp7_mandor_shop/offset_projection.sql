-- Private noncash proof/projection only. No Native payment hook or installer.
-- Posted account identities survive later configuration changes unchanged.
create table cp7_mandor_shop.offset_accounts(
 settlement_id uuid primary key references cp7_mandor_shop.settlements(id),
 payable_account_id uuid not null references erp.chart_accounts(id),
 receivable_account_id uuid not null references erp.chart_accounts(id),
 customer_id uuid not null references erp.customers(id),
 actor uuid not null,
 request_id uuid not null,
 check(payable_account_id<>receivable_account_id),
 foreign key(actor,request_id)references cp7_mandor_shop.requests(actor,request_id)deferrable initially deferred
);
alter table cp7_mandor_shop.offset_accounts enable row level security;
revoke all on cp7_mandor_shop.offset_accounts from public,anon,authenticated,service_role;
create trigger immutable_offset_accounts before update or delete on cp7_mandor_shop.offset_accounts
 for each row execute function cp7_mandor_shop.immutable_fact();

create function cp7_mandor_shop.offset_proof(p_settlement uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare s_ cp7_mandor_shop.settlements;a_ cp7_mandor_shop.offset_accounts;
 j_ erp.journal_entries;r_ cp7_mandor_shop.settlement_reversals;inverse_ erp.journal_entries;
 payroll_ erp.payroll_settlements;total_ numeric;count_ integer;ok_ boolean;
begin
 select *into s_ from cp7_mandor_shop.settlements where id=p_settlement;
 select *into a_ from cp7_mandor_shop.offset_accounts where settlement_id=p_settlement;
 select *into j_ from erp.journal_entries where id=s_.journal_id;
 select *into payroll_ from erp.payroll_settlements where id=s_.payroll_id;
 if(s_.id is null or a_.settlement_id is null or j_.id is null or payroll_.id is null
  or payroll_.contractor_id is distinct from s_.contractor_id
  or(a_.actor,a_.request_id)is distinct from(s_.actor,s_.request_id)
  or j_.source_type is distinct from'FG_MANDOR_PAYROLL_OFFSET'or j_.source_id is distinct from s_.id
  or j_.economic_date is distinct from s_.economic_date or j_.transaction_date is distinct from s_.book_date
  or j_.reversal_of_id is not null)then raise exception 'CP7_MANDOR_SHOP_EXACT_OFFSET_IDENTITY_REQUIRED';end if;
 select count(*),sum(l.amount),coalesce(bool_and(coalesce(
  sale_.contractor_id=s_.contractor_id and sale_.customer_id=a_.customer_id
  and header_.customer_id=a_.customer_id,false)),false)
 into count_,total_,ok_
 from cp7_mandor_shop.settlement_lines l
 join cp7_mandor_shop.sales sale_ on sale_.sale_id=l.sale_id
 join erp.sales_headers header_ on header_.id=l.sale_id
 where l.settlement_id=s_.id;
 if count_=0 or total_ is distinct from s_.total_amount or ok_ is distinct from true then
  raise exception 'CP7_MANDOR_SHOP_EXACT_OFFSET_INVOICE_LINES_REQUIRED';end if;
 -- Exactly two legs, including every Native party/PO/product dimension.
 select count(*)=2
  and count(*)filter(where account_id=a_.payable_account_id and debit=s_.total_amount and credit=0
   and contractor_id=s_.contractor_id and customer_id is null and vendor_id is null
   and po_id is null and product_id is null)=1
  and count(*)filter(where account_id=a_.receivable_account_id and credit=s_.total_amount and debit=0
   and customer_id=a_.customer_id and contractor_id is null and vendor_id is null
   and po_id is null and product_id is null)=1 into ok_
 from erp.journal_lines where journal_entry_id=j_.id;
 if ok_ is distinct from true then raise exception 'CP7_MANDOR_SHOP_EXACT_NONCASH_OFFSET_LEGS_REQUIRED';end if;
 select *into r_ from cp7_mandor_shop.settlement_reversals where settlement_id=s_.id;
 if r_.id is null then
  if j_.status is distinct from'POSTED'or payroll_.status is distinct from'PAID'then
   raise exception 'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REQUIRES_PAID_PAYROLL';end if;
  if exists(select 1 from erp.journal_entries where reversal_of_id=j_.id)then
   raise exception 'CP7_MANDOR_SHOP_UNRECORDED_OFFSET_REVERSAL';end if;
  if exists(select 1 from cp7_mandor_shop.settlement_lines l
   left join cp7_mandor_shop.allocation_states st on st.allocation_id=l.allocation_id
   left join cp7_mandor_shop.allocation_events e on e.id=st.last_event_id
   left join cp7_mandor_shop.deduction_links dl on dl.allocation_id=l.allocation_id
   left join erp.payroll_deductions d on d.id=dl.deduction_id
   where l.settlement_id=s_.id and(
    st.state is distinct from'SETTLED'or st.settlement_id is distinct from s_.id
    or e.kind is distinct from'SETTLE'or e.settlement_id is distinct from s_.id
    or(dl.sale_id,dl.payroll_id,dl.contractor_id,dl.amount)is distinct from
      (l.sale_id,l.payroll_id,l.contractor_id,l.amount)
    or d.id is null or d.payroll_id is distinct from s_.payroll_id
    or d.deduction_type is distinct from'OTHER'or d.amount is distinct from l.amount
    or d.contractor_issue_item_id is not null or d.bs_resolution_id is not null
    or d.opening_cash_advance_balance_id is not null))then
   raise exception 'CP7_MANDOR_SHOP_EXACT_SETTLED_PREFIX_AND_NATIVE_DEDUCTION_REQUIRED';end if;
 else
  select *into inverse_ from erp.journal_entries where id=r_.reversal_journal_id;
  if j_.status is distinct from'REVERSED'or inverse_.id is null
   or inverse_.status is distinct from'POSTED'or inverse_.source_type is distinct from'JOURNAL_REVERSAL'
   or inverse_.source_id is distinct from j_.id or inverse_.reversal_of_id is distinct from j_.id
   or(select count(*)from erp.journal_entries where reversal_of_id=j_.id)<>1 then
   raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_OFFSET_REVERSAL_REQUIRED';end if;
  select count(*)=2
   and count(*)filter(where account_id=a_.payable_account_id and credit=s_.total_amount and debit=0
    and contractor_id=s_.contractor_id and customer_id is null and vendor_id is null
    and po_id is null and product_id is null)=1
   and count(*)filter(where account_id=a_.receivable_account_id and debit=s_.total_amount and credit=0
    and customer_id=a_.customer_id and contractor_id is null and vendor_id is null
    and po_id is null and product_id is null)=1 into ok_
  from erp.journal_lines where journal_entry_id=inverse_.id;
  if ok_ is distinct from true then raise exception 'CP7_MANDOR_SHOP_EXACT_INVERSE_OFFSET_LEGS_REQUIRED';end if;
  -- Inspect the immutable historical successor, not today's allocation state:
  -- an allocation may subsequently settle again under a NEW journal.
  if exists(select 1 from cp7_mandor_shop.settlement_lines l where l.settlement_id=s_.id
   and not exists(select 1 from cp7_mandor_shop.allocation_events e
    join cp7_mandor_shop.allocation_events next_ on next_.predecessor_id=e.id
    where e.allocation_id=l.allocation_id and e.kind='SETTLE'and e.settlement_id=s_.id
     and next_.allocation_id=l.allocation_id and next_.ordinal=e.ordinal+1
     and next_.kind in('REOPEN','REVERSE')and next_.settlement_id=s_.id and next_.reversal_id=r_.id))
   or exists(select 1 from cp7_mandor_shop.allocation_states
    where settlement_id=s_.id and state='SETTLED')then
   raise exception 'CP7_MANDOR_SHOP_EXACT_OFFSET_REVERSAL_EVENT_REQUIRED';end if;
 end if;
 return jsonb_build_object('settlement_id',s_.id,'journal_id',j_.id,'amount',s_.total_amount,
  'customer_id',a_.customer_id,'payroll_id',s_.payroll_id,'active',r_.id is null,
  'noncash',true,'Native_payment_or_reversal_executed',false);
end $$;

create function cp7_mandor_shop.guard_offset_accounts()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;s_ cp7_mandor_shop.settlements;
 payable_ uuid;receivable_ uuid;income_ uuid;customer_ uuid;
begin
 if tg_when='AFTER'then
  perform cp7_mandor_shop.offset_proof(new.settlement_id);return null;
 end if;
 ctx_:=cp7_mandor_shop.require_context(array['SETTLE']);
 select *into s_ from cp7_mandor_shop.settlements where id=new.settlement_id;
 if(s_.id is null or(new.actor,new.request_id)is distinct from(ctx_.actor,ctx_.request_id)
  or(s_.actor,s_.request_id)is distinct from(ctx_.actor,ctx_.request_id))then
  raise exception 'CP7_MANDOR_SHOP_EXACT_OFFSET_ACCOUNT_COMMAND_REQUIRED';end if;
 lock table erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts in share mode nowait;
 select account_id into payable_ from erp.accounting_account_mappings where mapping_key='CONTRACTOR_PAYABLE';
 select account_id into receivable_ from erp.accounting_account_mappings where mapping_key='AR_CUSTOMER';
 select account_id into income_ from erp.accounting_account_mappings where mapping_key='OTHER_INCOME';
 select customer_id into customer_ from cp7_mandor_shop.contractor_accounts where contractor_id=s_.contractor_id;
 if(payable_ is null or receivable_ is null or income_ is null or customer_ is null
  or(new.payable_account_id,new.receivable_account_id,new.customer_id)is distinct from(payable_,receivable_,customer_)
  or payable_=receivable_ or income_ in(payable_,receivable_)
  or exists(select 1 from erp.cash_accounts where coa_account_id in(payable_,receivable_))
  or(select count(*)from erp.chart_accounts where id in(payable_,receivable_)and is_active and is_postable)<>2)then
  raise exception 'CP7_MANDOR_SHOP_ACTIVE_NONCASH_NATIVE_OFFSET_ACCOUNTS_REQUIRED';end if;
 return new;
end $$;
create trigger exact_offset_accounts before insert on cp7_mandor_shop.offset_accounts
 for each row execute function cp7_mandor_shop.guard_offset_accounts();
create constraint trigger offset_proof_at_settlement_commit after insert on cp7_mandor_shop.offset_accounts
 deferrable initially deferred for each row execute function cp7_mandor_shop.guard_offset_accounts();
create constraint trigger offset_proof_at_reversal_commit after insert on cp7_mandor_shop.settlement_reversals
 deferrable initially deferred for each row execute function cp7_mandor_shop.guard_offset_accounts();

create function cp7_mandor_shop.invoice_offset_paid(p_sale uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare sale_ cp7_mandor_shop.sales;h_ erp.sales_headers;r_ record;proof_ jsonb;paid_ numeric:=0;
begin
 select *into sale_ from cp7_mandor_shop.sales where sale_id=p_sale;
 if sale_.sale_id is null then return 0;end if;
 select *into h_ from erp.sales_headers where id=p_sale;
 if h_.id is null or h_.customer_id is distinct from sale_.customer_id then
  raise exception 'CP7_MANDOR_SHOP_OFFSET_INVOICE_BUYER_CHANGED';end if;
 if exists(select 1 from erp.journal_entries j where j.source_type='FG_MANDOR_PAYROLL_OFFSET'
  and j.status in('POSTED','REVERSED')and not exists(select 1 from cp7_mandor_shop.settlements s
   where s.journal_id=j.id and s.id=j.source_id))then
  raise exception 'CP7_MANDOR_SHOP_UNCLAIMED_NATIVE_OFFSET_JOURNAL';end if;
 for r_ in select settlement_id,sum(amount)as amount from cp7_mandor_shop.settlement_lines
  where sale_id=p_sale group by settlement_id order by settlement_id loop
  proof_:=cp7_mandor_shop.offset_proof(r_.settlement_id);
  if(proof_->>'active')::boolean then paid_:=paid_+r_.amount;end if;
 end loop;
 if paid_>0 and not coalesce(h_.status in('POSTED','PARTIAL_PAID','PAID'),false)then
  raise exception 'CP7_MANDOR_SHOP_INACTIVE_INVOICE_ACTIVE_OFFSET_REVIEW_REQUIRED';end if;
 return paid_;
end $$;
alter function cp7_mandor_shop.offset_proof(uuid)owner to postgres;
alter function cp7_mandor_shop.guard_offset_accounts()owner to postgres;
alter function cp7_mandor_shop.invoice_offset_paid(uuid)owner to postgres;
revoke all on function cp7_mandor_shop.offset_proof(uuid),cp7_mandor_shop.guard_offset_accounts(),
 cp7_mandor_shop.invoice_offset_paid(uuid)from public,anon,authenticated,service_role;
