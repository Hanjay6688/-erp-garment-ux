-- Run in the same transaction as the composed CREATE statements, while the
-- actual non-superuser postgres still owns all nine newly created functions.
-- No existing function ACL or ALTER DEFAULT PRIVILEGES is changed.
do $mandor_new_acl$declare item_ record;grantee_ text;begin
 for item_ in select p.oid::regprocedure::text signature,x.grantee
  from pg_proc p cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))x
  where p.oid in(
   'public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer)'::regprocedure,
   'public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid)'::regprocedure,
   'public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)'::regprocedure,
   'public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)'::regprocedure,
   'public.erp_cp7_get_mandor_shop_customer_buyer_v1(text,uuid)'::regprocedure,
   'public.erp_cp7_save_mandor_shop_sale_v1(text,jsonb,uuid,text)'::regprocedure,
   'cp7_mandor_shop.is_mandor_customer(uuid)'::regprocedure,
   'cp7_mandor_shop.customer_buyer(text,uuid)'::regprocedure,
   'cp7_mandor_shop.save_sale(text,jsonb,uuid,text)'::regprocedure)
   and x.grantee<>p.proowner loop
  grantee_:=case when item_.grantee=0 then'PUBLIC'else quote_ident(pg_get_userbyid(item_.grantee))end;
  execute format('revoke all on function %s from %s',item_.signature,grantee_);
 end loop;
end $mandor_new_acl$;
grant execute on function cp7_mandor_shop.is_mandor_customer(uuid)to cp7_sales_read;
grant execute on function cp7_mandor_shop.customer_buyer(text,uuid),
 cp7_mandor_shop.save_sale(text,jsonb,uuid,text)to cp7_mandor_shop_api;
grant execute on function public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer),
 public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid),
 public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid),
 public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid),
 public.erp_cp7_get_mandor_shop_customer_buyer_v1(text,uuid),
 public.erp_cp7_save_mandor_shop_sale_v1(text,jsonb,uuid,text)to authenticated;
grant cp7_mandor_shop_api to postgres with admin false,inherit false,set true;
grant create on schema public to cp7_mandor_shop_api;
alter function public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_get_mandor_shop_customer_buyer_v1(text,uuid)owner to cp7_mandor_shop_api;
alter function public.erp_cp7_save_mandor_shop_sale_v1(text,jsonb,uuid,text)owner to cp7_mandor_shop_api;
revoke create on schema public from cp7_mandor_shop_api;
revoke cp7_mandor_shop_api from postgres granted by postgres;
