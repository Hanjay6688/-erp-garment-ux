-- Accepted pre-optimization authority oracle from source6127ec8; no business writer.
create function cp7_sales.reference_command_access(p_action text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;
begin
 if not cp7_sales.access_now() or p_action is null or p_action not in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
  or not erp.has_permission(case when p_action='POST' then 'sales.invoice.post' when p_action='CREATE' then 'sales.invoice.create' when p_action='PAYMENT' then 'sales.payment.create' when p_action='PAYMENT_REVERSE' then 'sales.payment.reverse' when p_action='RETURN' then 'sales.return.create' when p_action='RETURN_REVERSE' then 'sales.return.reverse' when p_action='SALE_REVERSE' then 'sales.invoice.reverse' else 'sales.invoice.edit_draft' end)
  or(p_action in('PAYMENT','PAYMENT_REVERSE') and not erp.has_permission('sales.payment.view'))
  or(p_action='PAYMENT' and not erp.has_permission('sales.payment.post'))
  or(p_action in('RETURN','RETURN_REVERSE') and not erp.has_permission('sales.return.view'))
  or(p_action='RETURN' and not erp.has_permission('sales.return.post'))
 then raise exception using errcode='42501',message='CP7_SALES_WRITE_DENIED';end if;
 a:=erp.get_my_access_v1();
 if p_action in('PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE') and coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_SALES_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $$;
