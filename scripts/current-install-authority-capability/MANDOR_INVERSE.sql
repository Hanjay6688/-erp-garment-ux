grant cp7_mandor_shop_api to postgres with admin false,inherit false,set true;
set local role cp7_mandor_shop_api;
drop function public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer),public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid),public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid),public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid),public.erp_cp7_get_mandor_shop_customer_buyer_v1(text,uuid),public.erp_cp7_save_mandor_shop_sale_v1(text,jsonb,uuid,text);
reset role;
drop function cp7_mandor_shop.is_mandor_customer(uuid),cp7_mandor_shop.customer_buyer(text,uuid),cp7_mandor_shop.save_sale(text,jsonb,uuid,text);
revoke usage on schema public,cp7_mandor_shop from cp7_mandor_shop_api;
revoke execute on function cp7_mandor_shop.buyer_options(text,text,uuid,integer),cp7_mandor_shop.buyer_command(jsonb,uuid),cp7_mandor_shop.workspace(uuid,uuid),cp7_mandor_shop.allocation_command(text,jsonb,uuid)from cp7_mandor_shop_api;
revoke usage on schema cp7_mandor_shop from cp7_sales_read;
drop role cp7_mandor_shop_api;
