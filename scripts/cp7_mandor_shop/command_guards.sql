-- Fail before Native business writes; retain the table guards as the final
-- boundary for every other lawful Native route. No browser/private grants.
create function cp7_mandor_shop.payroll_current_access(text,text,uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare source_ alias for $1;action_ alias for $2;payroll_ alias for $3;
begin
 if source_ not in('PAYROLL','INSTALLMENT')or source_ is null then
  raise exception 'CP7_MANDOR_SHOP_EXACT_NATIVE_PAYMENT_OWNER_REQUIRED';end if;
 -- A payroll with no Mandor history keeps its original permission contract.
 if not exists(select 1 from cp7_mandor_shop.allocation_states where payroll_id=payroll_)then return;end if;
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;
 -- Keep the same original Native action checks, including on cached replay.
 if source_='PAYROLL'then perform cp7_payroll.settlement_access(action_);
 else perform cp7_installment.access_now(action_);end if;
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'
  or erp.has_permission('finance.ar.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_DENIED';end if;
end $$;

create function cp7_mandor_shop.sale_change_preflight(text,uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare action_ alias for $1;sale_ alias for $2;contractor_ uuid;
begin
 if action_ not in('RETURN','RETURN_REVERSE','SALE_REVERSE','CORRECT')or action_ is null then return;end if;
 select contractor_id into contractor_ from cp7_mandor_shop.sales where sale_id=sale_;
 if contractor_ is null then return;end if;
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))
  or not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP|'||contractor_::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_SOURCE_BUSY_REVIEW_AGAIN';end if;
 lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;
 perform 1 from erp.sales_headers where id=sale_ for update nowait;
 if action_='CORRECT'then perform cp7_note.access_now();
 else perform cp7_sales.command_access(action_);end if;
 if cp7_mandor_shop.has_active_offset(sale_)then
  if action_ in('RETURN','RETURN_REVERSE')then
   raise exception 'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_SALES_RETURN';
  else raise exception 'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_INVOICE_CORRECTION';end if;
 end if;
end $$;

alter function cp7_mandor_shop.payroll_current_access(text,text,uuid)owner to postgres;
alter function cp7_mandor_shop.sale_change_preflight(text,uuid)owner to postgres;
revoke all on function cp7_mandor_shop.payroll_current_access(text,text,uuid),
 cp7_mandor_shop.sale_change_preflight(text,uuid)from public,anon,authenticated,service_role;
