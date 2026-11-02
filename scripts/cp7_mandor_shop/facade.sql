-- Unactivated narrow browser facade. Installation still requires the actual
-- accepted final parent, exact Native profile review and complete qualification.
create role cp7_mandor_shop_api nologin noinherit nosuperuser nocreatedb
 nocreaterole noreplication nobypassrls connection limit 0;
grant usage on schema public,cp7_mandor_shop to cp7_mandor_shop_api;
grant execute on function cp7_mandor_shop.buyer_options(text,text,uuid,integer),
 cp7_mandor_shop.buyer_command(jsonb,uuid),cp7_mandor_shop.workspace(uuid,uuid),
 cp7_mandor_shop.allocation_command(text,jsonb,uuid)to cp7_mandor_shop_api;

-- Each existing private owner validates the live actor, original permissions,
-- selected mandor/source and exact request. No caller-controlled internal flag.
create function public.erp_cp7_get_mandor_shop_buyers_v1(p_sales_action text,
 p_query text default '',p_after uuid default null,p_limit integer default 25)
returns jsonb language sql stable security definer set search_path=''as $$
 select cp7_mandor_shop.buyer_options(p_sales_action,p_query,p_after,p_limit)
$$;
create function public.erp_cp7_prepare_mandor_shop_buyer_v1(p_payload jsonb,p_request uuid)
returns jsonb language sql volatile security definer set search_path=''as $$
 select cp7_mandor_shop.buyer_command(p_payload,p_request)
$$;
create function public.erp_cp7_get_mandor_shop_payroll_v1(p_payroll uuid,p_after uuid default null)
returns jsonb language sql stable security definer set search_path=''as $$
 select cp7_mandor_shop.workspace(p_payroll,p_after)
$$;
create function public.erp_cp7_save_mandor_shop_allocation_v1(p_action text,p_payload jsonb,p_request uuid)
returns jsonb language sql volatile security definer set search_path=''as $$
 select cp7_mandor_shop.allocation_command(p_action,p_payload,p_request)
$$;

alter function public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)owner to cp7_mandor_shop_api;
revoke all on function public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer),
 public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid),
 public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid),
 public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer),
 public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid),
 public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid),
 public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)to authenticated;
-- No schema/table access, direct payment primitive or role membership is
-- granted to browser roles. The facade role receives only four private calls.
