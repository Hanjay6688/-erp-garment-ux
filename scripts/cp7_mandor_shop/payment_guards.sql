-- Native-table boundaries for the private FG offset. Still unactivated.
-- Only the owning payroll command may create/reverse its protected journals;
-- complete immutable settlement/event/account facts must exist at COMMIT.
create function cp7_mandor_shop.has_active_offset(p_sale uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_mandor_shop.settlement_lines l
  where l.sale_id=p_sale and not exists(select 1 from cp7_mandor_shop.settlement_reversals r
   where r.settlement_id=l.settlement_id))
  or exists(select 1 from cp7_mandor_shop.allocation_states where sale_id=p_sale and state='SETTLED')
$$;

create function cp7_mandor_shop.protected_journal(p erp.journal_entries)returns boolean
language sql stable security definer set search_path=''as $$
 with recursive ancestry as(
  select j.id,j.source_type,j.source_id,j.reversal_of_id,array[j.id]as seen
   from erp.journal_entries j where j.id in(p.source_id,p.reversal_of_id)
  union all
  select j.id,j.source_type,j.source_id,j.reversal_of_id,a.seen||j.id
   from ancestry a join erp.journal_entries j on j.id in(a.source_id,a.reversal_of_id)
   where not j.id=any(a.seen)
 )
 select coalesce(p.source_type='FG_MANDOR_PAYROLL_OFFSET',false)
  or exists(select 1 from ancestry where source_type='FG_MANDOR_PAYROLL_OFFSET')
$$;

create function cp7_mandor_shop.guard_payment_journal()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare j_ erp.journal_entries;old_ erp.journal_entries;original_ erp.journal_entries;
 ctx_ cp7_mandor_shop.command_context;work_ cp7_mandor_shop.payment_work;s_ cp7_mandor_shop.settlements;
 protected_ boolean;old_protected_ boolean:=false;
begin
 if tg_op='DELETE'then j_:=old;else j_:=new;end if;
 protected_:=cp7_mandor_shop.protected_journal(j_);
 if tg_op='UPDATE'then old_:=old;old_protected_:=cp7_mandor_shop.protected_journal(old_);end if;
 if not(protected_ or old_protected_)then
  if tg_op='DELETE'then return old;else return new;end if;
 end if;
 if tg_op='DELETE'then raise exception 'CP7_MANDOR_SHOP_PROTECTED_JOURNAL_HISTORY_IMMUTABLE';end if;
 if old_protected_ and not protected_ then raise exception 'CP7_MANDOR_SHOP_PROTECTED_JOURNAL_IDENTITY_IMMUTABLE';end if;
 ctx_:=cp7_mandor_shop.require_context(array['SETTLE','REOPEN','REVERSE']);
 select *into strict work_ from cp7_mandor_shop.payment_work
  where backend_pid=pg_backend_pid()and transaction_id=txid_current_if_assigned()
   and actor=ctx_.actor and request_id=ctx_.request_id and mode=ctx_.action;
 if j_.source_type='FG_MANDOR_PAYROLL_OFFSET'then
  if tg_op='INSERT'then
   if ctx_.action is distinct from'SETTLE'or j_.status is distinct from'POSTED'
    or j_.source_id is null or j_.reversal_of_id is not null
    or not exists(select 1 from erp.payroll_settlements h where h.id=work_.payroll_id
     and h.status='PAID'and h.payment_date=j_.economic_date)then
    raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_JOURNAL_INSERT_REQUIRED';end if;
  else
   select *into s_ from cp7_mandor_shop.settlements where journal_id=j_.id and id=j_.source_id;
   if ctx_.action not in('REOPEN','REVERSE')or work_.native_before_status is distinct from'PAID'
    or s_.id is null or s_.payroll_id is distinct from work_.payroll_id
    or old_.status is distinct from'POSTED'or j_.status is distinct from'REVERSED'
    or(to_jsonb(j_)-array['status','updated_at'])is distinct from(to_jsonb(old_)-array['status','updated_at'])then
    raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_REVERSAL_REQUIRED';end if;
  end if;
 else
  select *into original_ from erp.journal_entries where id=j_.source_id and source_type='FG_MANDOR_PAYROLL_OFFSET';
  select *into s_ from cp7_mandor_shop.settlements where journal_id=original_.id and id=original_.source_id;
  if j_.source_type is distinct from'JOURNAL_REVERSAL'or original_.id is null or s_.id is null
   or s_.payroll_id is distinct from work_.payroll_id or ctx_.action not in('REOPEN','REVERSE')
   or work_.native_before_status is distinct from'PAID'or j_.status is distinct from'POSTED'
   or(j_.reversal_of_id is not null and j_.reversal_of_id is distinct from original_.id)then
   raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_INVERSE_REQUIRED';end if;
  if tg_op='UPDATE'and(old_.reversal_of_id is not null or j_.reversal_of_id is distinct from original_.id
   or(to_jsonb(j_)-array['reversal_of_id','updated_at'])is distinct from(to_jsonb(old_)-array['reversal_of_id','updated_at']))then
   raise exception 'CP7_MANDOR_SHOP_PROTECTED_INVERSE_HISTORY_IMMUTABLE';end if;
 end if;
 return new;
end $$;

create function cp7_mandor_shop.guard_payment_journal_line()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare j_ erp.journal_entries;old_j_ erp.journal_entries;ctx_ cp7_mandor_shop.command_context;
 work_ cp7_mandor_shop.payment_work;s_ cp7_mandor_shop.settlements;
begin
 if tg_op='DELETE'then select *into j_ from erp.journal_entries where id=old.journal_entry_id;
 else select *into j_ from erp.journal_entries where id=new.journal_entry_id;end if;
 if tg_op='UPDATE'then select *into old_j_ from erp.journal_entries where id=old.journal_entry_id;end if;
 if not(cp7_mandor_shop.protected_journal(j_)or cp7_mandor_shop.protected_journal(old_j_))then
  if tg_op='DELETE'then return old;else return new;end if;
 end if;
 if tg_op<>'INSERT'then raise exception 'CP7_MANDOR_SHOP_PROTECTED_JOURNAL_LEGS_IMMUTABLE';end if;
 ctx_:=cp7_mandor_shop.require_context(array['SETTLE','REOPEN','REVERSE']);
 select *into strict work_ from cp7_mandor_shop.payment_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current_if_assigned()and actor=ctx_.actor and request_id=ctx_.request_id and mode=ctx_.action;
 if j_.source_type='FG_MANDOR_PAYROLL_OFFSET'then
  if ctx_.action is distinct from'SETTLE'
   or exists(select 1 from cp7_mandor_shop.settlements where journal_id=j_.id)then
   raise exception 'CP7_MANDOR_SHOP_PROTECTED_OFFSET_LEGS_OWNING_INITIAL_INSERT_ONLY';end if;
 else
  select *into s_ from cp7_mandor_shop.settlements where journal_id=j_.source_id;
  if ctx_.action not in('REOPEN','REVERSE')or s_.id is null
   or s_.payroll_id is distinct from work_.payroll_id
   or exists(select 1 from cp7_mandor_shop.settlement_reversals where reversal_journal_id=j_.id)then
   raise exception 'CP7_MANDOR_SHOP_PROTECTED_INVERSE_LEGS_OWNING_INITIAL_INSERT_ONLY';end if;
 end if;
 return new;
end $$;

create function cp7_mandor_shop.deferred_payment_journal()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare ident_ uuid;j_ erp.journal_entries;s_ cp7_mandor_shop.settlements;
begin
 if tg_table_name='journal_entries'then ident_:=new.id;
 elsif tg_op='DELETE'then ident_:=old.journal_entry_id;else ident_:=new.journal_entry_id;end if;
 select *into j_ from erp.journal_entries where id=ident_;
 if not cp7_mandor_shop.protected_journal(j_)then return null;end if;
 if j_.source_type='FG_MANDOR_PAYROLL_OFFSET'then
  select *into s_ from cp7_mandor_shop.settlements where id=j_.source_id and journal_id=j_.id;
 else
  select s.*into s_ from cp7_mandor_shop.settlements s
   join cp7_mandor_shop.settlement_reversals r on r.settlement_id=s.id
   where s.journal_id=j_.source_id and r.reversal_journal_id=j_.id;
 end if;
 if s_.id is null then raise exception 'CP7_MANDOR_SHOP_PROTECTED_JOURNAL_EXACT_FACTS_REQUIRED_AT_COMMIT';end if;
 perform cp7_mandor_shop.offset_proof(s_.id);return null;
end $$;

create function cp7_mandor_shop.guard_invoice_offset_exposure()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare sale_ uuid;prior_sale_ uuid;old_status_ text;new_status_ text;
begin
 if tg_table_name='sales_headers'then
  if tg_op='DELETE'then sale_:=old.id;else sale_:=new.id;end if;
  if not cp7_mandor_shop.has_active_offset(sale_)then
   if tg_op='DELETE'then return old;else return new;end if;
  end if;
  if tg_op='DELETE'then raise exception 'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_INVOICE_CORRECTION';end if;
  if new.status is null or new.status not in('POSTED','PARTIAL_PAID','PAID')
   or(to_jsonb(new)-array['status','row_version','updated_at'])is distinct from(to_jsonb(old)-array['status','row_version','updated_at'])then
   raise exception 'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_INVOICE_CORRECTION';end if;
 else
  if tg_op='DELETE'then sale_:=old.sale_id;old_status_:=old.status;
  else sale_:=new.sale_id;new_status_:=new.status;
   if tg_op='UPDATE'then old_status_:=old.status;prior_sale_:=old.sale_id;end if;end if;
  if(cp7_mandor_shop.has_active_offset(sale_)
    or(prior_sale_ is not null and cp7_mandor_shop.has_active_offset(prior_sale_)))
   and(old_status_='POSTED'or new_status_='POSTED')then
   raise exception 'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_SALES_RETURN';end if;
 end if;
 if tg_op='DELETE'then return old;else return new;end if;
end $$;

create trigger mandor_shop_journal_owner before insert or update or delete on erp.journal_entries
 for each row execute function cp7_mandor_shop.guard_payment_journal();
create trigger mandor_shop_journal_line_owner before insert or update or delete on erp.journal_lines
 for each row execute function cp7_mandor_shop.guard_payment_journal_line();
create constraint trigger mandor_shop_journal_exact_at_commit after insert or update on erp.journal_entries
 deferrable initially deferred for each row execute function cp7_mandor_shop.deferred_payment_journal();
create constraint trigger mandor_shop_journal_lines_exact_at_commit after insert or update or delete on erp.journal_lines
 deferrable initially deferred for each row execute function cp7_mandor_shop.deferred_payment_journal();
create trigger mandor_shop_invoice_offset_exposure before update or delete on erp.sales_headers
 for each row execute function cp7_mandor_shop.guard_invoice_offset_exposure();
create trigger mandor_shop_return_offset_exposure before insert or update or delete on erp.sales_returns
 for each row execute function cp7_mandor_shop.guard_invoice_offset_exposure();

alter function cp7_mandor_shop.has_active_offset(uuid)owner to postgres;
alter function cp7_mandor_shop.protected_journal(erp.journal_entries)owner to postgres;
alter function cp7_mandor_shop.guard_payment_journal()owner to postgres;
alter function cp7_mandor_shop.guard_payment_journal_line()owner to postgres;
alter function cp7_mandor_shop.deferred_payment_journal()owner to postgres;
alter function cp7_mandor_shop.guard_invoice_offset_exposure()owner to postgres;
revoke all on function cp7_mandor_shop.has_active_offset(uuid),cp7_mandor_shop.protected_journal(erp.journal_entries),
 cp7_mandor_shop.guard_payment_journal(),cp7_mandor_shop.guard_payment_journal_line(),
 cp7_mandor_shop.deferred_payment_journal(),cp7_mandor_shop.guard_invoice_offset_exposure()
 from public,anon,authenticated,service_role;
