-- Unactivated Native-header identity hook. Existing sales owns all invoice,
-- stock, HPP, cash and ledger operations. This hook only records buyer facts.
create function cp7_mandor_shop.sales_identity()returns trigger
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'
 set lock_timeout='1s'as $$
declare account_ cp7_mandor_shop.contractor_accounts;posted_ cp7_mandor_shop.sales;
 contractor_ erp.contractors;customer_ erp.customers;actor_ uuid;action_ text;
 own_context_ boolean:=false;context_ cp7_mandor_shop.command_context;hash_ text;
begin
 if tg_table_schema<>'erp'or tg_table_name<>'sales_headers'or tg_when<>'AFTER'
  or tg_level<>'ROW'or tg_op not in('INSERT','UPDATE')then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_SALE_IDENTITY_TRIGGER_REQUIRED';end if;
 select *into posted_ from cp7_mandor_shop.sales where sale_id=new.id;
 if posted_.sale_id is not null then
  if new.customer_id is distinct from posted_.customer_id then
   raise exception 'CP7_MANDOR_SHOP_POSTED_BUYER_CHANGED';end if;
  if new.status in('DRAFT','CANCELLED')then
   raise exception 'CP7_MANDOR_SHOP_POSTED_IDENTITY_CANNOT_RETURN_TO_DRAFT';end if;
  -- Payments, lawful reversals and returns keep the original immutable buyer
  -- snapshot, including when the master has since been renamed/deactivated.
  return new;
 end if;
 select *into account_ from cp7_mandor_shop.contractor_accounts where customer_id=new.customer_id;
 if account_.contractor_id is null or new.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID')then
  if exists(select 1 from cp7_mandor_shop.draft_buyers where sale_id=new.id)then
   perform erp.require_internal();
   delete from cp7_mandor_shop.draft_buyers where sale_id=new.id;
  end if;
  return new;
 end if;
 actor_:=auth.uid();
 if actor_ is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_NATIVE_SALE_ACTOR_REQUIRED';end if;
 if current_setting('transaction_isolation')<>'read committed'then
  raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 -- Keep the existing FG lock order. Native sales already owns FG; NOWAIT
 -- also protects callers using another lawful Native posting route.
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))
  or not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP|'||account_.contractor_id::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_SOURCE_BUSY_REVIEW_AGAIN';end if;
 lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;
 select *into strict contractor_ from erp.contractors where id=account_.contractor_id for share nowait;
 select *into strict customer_ from erp.customers where id=account_.customer_id for share nowait;
 perform erp.require_internal();
 if not contractor_.is_active or contractor_.contractor_type<>'MANDOR'or not customer_.is_active then
  raise exception 'CP7_MANDOR_SHOP_ACTIVE_POSTING_BUYER_REQUIRED';end if;
 action_:=case when new.status='DRAFT'then'SAVE_SALE'else'POST_SALE'end;
 select *into context_ from cp7_mandor_shop.command_context
  where backend_pid=pg_backend_pid()and transaction_id=txid_current_if_assigned();
 if context_.actor is null then
  hash_:=encode(extensions.digest(convert_to(jsonb_build_array(
   'cp7.mandor-shop-native-sale-identity.v1',new.id,new.customer_id,new.status,new.row_version)::text,
   'UTF8'),'sha256'),'hex');
  -- Sale UUID identifies this technical identity context, not a second
  -- financial command or a fabricated payment request.
  insert into cp7_mandor_shop.command_context values(
   pg_backend_pid(),txid_current(),actor_,new.id,action_,hash_);
  own_context_:=true;
 elsif context_.actor is distinct from actor_ or context_.action is distinct from action_ then
  raise exception 'CP7_MANDOR_SHOP_NATIVE_SALE_CONTEXT_CONFLICT';end if;
 if new.status='DRAFT'then
  insert into cp7_mandor_shop.draft_buyers(sale_id,contractor_id,customer_id,selected_by)
   values(new.id,account_.contractor_id,account_.customer_id,actor_)
   on conflict(sale_id)do update set contractor_id=excluded.contractor_id,
    customer_id=excluded.customer_id,selected_by=excluded.selected_by,selected_at=statement_timestamp();
 else
  insert into cp7_mandor_shop.sales(sale_id,contractor_id,customer_id,contractor_name_at_post,posted_by)
   values(new.id,account_.contractor_id,account_.customer_id,contractor_.contractor_name,actor_);
  delete from cp7_mandor_shop.draft_buyers where sale_id=new.id;
 end if;
 if own_context_ then
  delete from cp7_mandor_shop.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 end if;
 return new;
end $$;
alter function cp7_mandor_shop.sales_identity()owner to postgres;
revoke all on function cp7_mandor_shop.sales_identity()from public,anon,authenticated,service_role;

create trigger cp7_mandor_shop_sales_identity
 after insert or update of customer_id,status on erp.sales_headers
 for each row execute function cp7_mandor_shop.sales_identity();
