-- Private event owner. Public commands and Native payment hooks remain pending.
create function cp7_mandor_shop.require_context(p_actions text[])
returns cp7_mandor_shop.command_context
language plpgsql stable security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;
begin
 select *into ctx_ from cp7_mandor_shop.command_context c
 where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current_if_assigned()
  and c.actor=auth.uid()and c.action=any(p_actions);
 if ctx_.actor is null then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_OWNING_COMMAND_REQUIRED';
 end if;
 return ctx_;
end $$;
alter function cp7_mandor_shop.require_context(text[])owner to postgres;
revoke all on function cp7_mandor_shop.require_context(text[])from public,anon,authenticated,service_role;

create function cp7_mandor_shop.guard_identity()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;allowed_ boolean;
begin
 ctx_:=cp7_mandor_shop.require_context(case tg_table_name
  when'draft_buyers'then array['SAVE_SALE']when'sales'then array['POST_SALE']
  when'payroll_identities'then array['RESERVE']when'deduction_links'then array['RESERVE']
  when'settlements'then array['SETTLE']when'settlement_reversals'then array['REOPEN','REVERSE']
  else array[]::text[]end);
 if tg_table_name='draft_buyers'then
  select exists(select 1 from erp.sales_headers h
   join cp7_mandor_shop.contractor_accounts a on a.customer_id=h.customer_id
   join erp.contractors c on c.id=a.contractor_id
   join erp.customers customer_ on customer_.id=a.customer_id
   where h.id=new.sale_id and h.status='DRAFT'and c.is_active and customer_.is_active
    and a.contractor_id=new.contractor_id and a.customer_id=new.customer_id)into allowed_;
 elsif tg_table_name='sales'then
  select exists(select 1 from erp.sales_headers h
   join cp7_mandor_shop.contractor_accounts a on a.customer_id=h.customer_id
   where h.id=new.sale_id and h.status in('POSTED','PARTIAL_PAID','PAID')
    and a.contractor_id=new.contractor_id and a.customer_id=new.customer_id)into allowed_;
 elsif tg_table_name='payroll_identities'then
  select exists(select 1 from erp.payroll_settlements p where p.id=new.payroll_id
   and p.contractor_id=new.contractor_id and p.status in('DRAFT','CALCULATED','REVIEW'))into allowed_;
 elsif tg_table_name='deduction_links'then
  select exists(select 1 from erp.payroll_deductions d where d.id=new.deduction_id
   and d.payroll_id=new.payroll_id and d.deduction_type='OTHER'and d.amount=new.amount
   and d.contractor_issue_item_id is null and d.bs_resolution_id is null
   and d.opening_cash_advance_balance_id is null)into allowed_;
 elsif tg_table_name='settlements'then
  select exists(select 1 from erp.journal_entries j
   join erp.payroll_settlements p on p.id=new.payroll_id
   where j.id=new.journal_id and j.source_type='FG_MANDOR_PAYROLL_OFFSET'
    and j.source_id=new.id and j.status='POSTED'
    and j.economic_date=new.economic_date and j.transaction_date=new.book_date
    and p.contractor_id=new.contractor_id and p.status='PAID')into allowed_;
 elsif tg_table_name='settlement_reversals'then
  select exists(select 1 from cp7_mandor_shop.settlements s
   join erp.journal_entries original_ on original_.id=s.journal_id
   join erp.journal_entries reversal_ on reversal_.reversal_of_id=original_.id
   where s.id=new.settlement_id and original_.status='REVERSED'
    and reversal_.id=new.reversal_journal_id and reversal_.status='POSTED')into allowed_;
 else raise exception 'CP7_MANDOR_SHOP_UNDECLARED_IDENTITY_GUARD';
 end if;
 if allowed_ is distinct from true then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_IDENTITY_OR_LIFECYCLE_MISMATCH';
 end if;
 return new;
end $$;
alter function cp7_mandor_shop.guard_identity()owner to postgres;
revoke all on function cp7_mandor_shop.guard_identity()from public,anon,authenticated,service_role;
create trigger exact_draft_buyer before insert or update on cp7_mandor_shop.draft_buyers
 for each row execute function cp7_mandor_shop.guard_identity();
create trigger exact_posted_sale before insert on cp7_mandor_shop.sales
 for each row execute function cp7_mandor_shop.guard_identity();
create trigger exact_payroll_identity before insert on cp7_mandor_shop.payroll_identities
 for each row execute function cp7_mandor_shop.guard_identity();
create trigger exact_native_deduction before insert or update on cp7_mandor_shop.deduction_links
 for each row execute function cp7_mandor_shop.guard_identity();
create trigger exact_settlement_journal before insert on cp7_mandor_shop.settlements
 for each row execute function cp7_mandor_shop.guard_identity();
create trigger exact_settlement_reversal before insert on cp7_mandor_shop.settlement_reversals
 for each row execute function cp7_mandor_shop.guard_identity();

create function cp7_mandor_shop.apply_allocation_event()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare ctx_ cp7_mandor_shop.command_context;a_ cp7_mandor_shop.allocations;
 s_ cp7_mandor_shop.allocation_states;next_state_ text;next_settlement_ uuid;
begin
 ctx_:=cp7_mandor_shop.require_context(case new.kind
  when'RESERVE'then array['RESERVE']when'RELEASE'then array['RELEASE','CANCEL']
  when'SETTLE'then array['SETTLE']when'REOPEN'then array['REOPEN']
  when'REVERSE'then array['REVERSE']else array[]::text[]end);
 if(new.actor,new.request_id)is distinct from(ctx_.actor,ctx_.request_id)then
  raise exception 'CP7_MANDOR_SHOP_EVENT_ACTOR_REQUEST_MISMATCH';end if;
 select *into a_ from cp7_mandor_shop.allocations a where a.id=new.allocation_id for update;
 if a_.id is null then raise exception 'CP7_MANDOR_SHOP_ALLOCATION_MISSING';end if;
 select *into s_ from cp7_mandor_shop.allocation_states s where s.allocation_id=a_.id for update;
 if new.ordinal<>coalesce(s_.last_ordinal,0)+1 or new.predecessor_id is distinct from s_.last_event_id then
  raise exception 'CP7_MANDOR_SHOP_STALE_EVENT_PREFIX';end if;
 if new.kind='RESERVE'then
  if s_.allocation_id is not null then raise exception 'CP7_MANDOR_SHOP_ALLOCATION_ALREADY_STARTED';end if;
  next_state_:='RESERVED';
 elsif new.kind='RELEASE'then
  if s_.state is distinct from'RESERVED'then raise exception 'CP7_MANDOR_SHOP_RELEASE_RESERVED_ONLY';end if;
  next_state_:='RELEASED';
 elsif new.kind='SETTLE'then
  if s_.state is distinct from'RESERVED'or not exists(
   select 1 from cp7_mandor_shop.settlement_lines line_
   where line_.settlement_id=new.settlement_id and line_.allocation_id=a_.id
    and line_.sale_id=a_.sale_id and line_.payroll_id=a_.payroll_id
    and line_.contractor_id=a_.contractor_id and line_.amount=a_.amount)then
   raise exception 'CP7_MANDOR_SHOP_SETTLE_EXACT_RESERVED_LINE_ONLY';end if;
  next_state_:='SETTLED';next_settlement_:=new.settlement_id;
 elsif new.kind in('REOPEN','REVERSE')then
  if s_.state is distinct from'SETTLED'or new.settlement_id is distinct from s_.settlement_id
   or not exists(select 1 from cp7_mandor_shop.settlement_reversals reversal_
    where reversal_.id=new.reversal_id and reversal_.settlement_id=s_.settlement_id)then
   raise exception 'CP7_MANDOR_SHOP_EXACT_ACTIVE_SETTLEMENT_REVERSAL_REQUIRED';end if;
  next_state_:=case new.kind when'REOPEN'then'RESERVED'else'RELEASED'end;
 else raise exception 'CP7_MANDOR_SHOP_EVENT_KIND_REQUIRED';
 end if;
 insert into cp7_mandor_shop.allocation_states(allocation_id,sale_id,payroll_id,contractor_id,amount,
  state,last_ordinal,last_event_id,settlement_id)
 values(a_.id,a_.sale_id,a_.payroll_id,a_.contractor_id,a_.amount,next_state_,new.ordinal,new.id,next_settlement_)
 on conflict(allocation_id)do update set state=excluded.state,last_ordinal=excluded.last_ordinal,
  last_event_id=excluded.last_event_id,settlement_id=excluded.settlement_id;
 return new;
end $$;
alter function cp7_mandor_shop.apply_allocation_event()owner to postgres;
revoke all on function cp7_mandor_shop.apply_allocation_event()from public,anon,authenticated,service_role;
create trigger apply_allocation_event after insert on cp7_mandor_shop.allocation_events
 for each row execute function cp7_mandor_shop.apply_allocation_event();
