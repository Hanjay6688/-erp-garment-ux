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
 with snapshot as materialized(
  select cp7_mandor_shop.workspace(p_payroll,p_after)as document
 )
 select jsonb_set(document,'{cards}',coalesce((
  select jsonb_agg(jsonb_set(card,'{allocations}',coalesce((
   select jsonb_agg(jsonb_set(assigned,'{allocation,amount}',
     to_jsonb(assigned#>>'{allocation,amount}'))order by allocation_order)
   from jsonb_array_elements(card->'allocations')with ordinality as allocation_rows(assigned,allocation_order)
  ),'[]'::jsonb))order by card_order)
  from jsonb_array_elements(document->'cards')with ordinality as cards(card,card_order)
 ),'[]'::jsonb))from snapshot
$$;
create function public.erp_cp7_save_mandor_shop_allocation_v1(p_action text,p_payload jsonb,p_request uuid)
returns jsonb language sql volatile security definer set search_path=''as $$
 select cp7_mandor_shop.allocation_command(p_action,p_payload,p_request)
$$;


-- No schema/table access, direct payment primitive or role membership is
-- granted to browser roles. The facade role receives only four private calls.

-- Unactivated integration: one existing Native sales intent owns both buyer
-- identity and draft save. Native POST, stock, COGS and payment stay unchanged.
create function cp7_mandor_shop.is_mandor_customer(p_customer uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_mandor_shop.contractor_accounts where customer_id=p_customer)
$$;

create function cp7_mandor_shop.customer_buyer(p_action text,p_customer uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare access_ jsonb;customer_ erp.customers;account_ cp7_mandor_shop.contractor_accounts;basis_ jsonb;
begin
 access_:=cp7_mandor_shop.buyer_access(p_action);
 select *into strict customer_ from erp.customers where id=p_customer;
 select *into account_ from cp7_mandor_shop.contractor_accounts where customer_id=p_customer;
 if account_.contractor_id is not null then basis_:=cp7_mandor_shop.buyer_basis(account_.contractor_id);end if;
 return jsonb_build_object('contract_version','cp7.mandor-shop-customer-buyer.v1','sales_action',p_action,
  'customer_id',customer_.id,'buyer_category',case when account_.contractor_id is null then'TOKO'else'MANDOR'end,
  'mandor',case when account_.contractor_id is null then null else jsonb_build_object(
   'contractor_id',account_.contractor_id,'code',basis_#>>'{contractor,contractor_code}',
   'name',basis_#>>'{contractor,contractor_name}','customer_id',customer_.id,
   'can_select',customer_.is_active and basis_#>'{contractor,is_active}'='true'::jsonb
     and basis_#>>'{contractor,contractor_type}'='MANDOR',
   'review_token',cp7_mandor_shop.buyer_review(p_action,access_,basis_))end);
end $$;

create function cp7_mandor_shop.save_sale(p_action text,p jsonb,p_request uuid,p_expected text)
returns jsonb language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare access_ jsonb;actor_ uuid;buyer_ jsonb;prepared_ jsonb;native_ jsonb;intent_ jsonb;
 request_hash_ text;buyer_request_ uuid;old_ cp7_mandor_shop.requests;result_ jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_:=cp7_mandor_shop.buyer_access(p_action);actor_:=auth.uid();
 if p_request is null or jsonb_typeof(p)is distinct from'object'
  or jsonb_typeof(p->'mandor_buyer')is distinct from'object'
  or not(p->'mandor_buyer')?&array['contractor_id','review_token']
  or exists(select 1 from jsonb_each(p->'mandor_buyer')e
    where e.key not in('contractor_id','review_token')or jsonb_typeof(e.value)<>'string')
  or coalesce(p#>>'{mandor_buyer,contractor_id}','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p#>>'{mandor_buyer,review_token}','')!~'^[0-9a-f]{64}$'
  or not p?'customer_id'or jsonb_typeof(p->'customer_id')not in('null','string')then
  raise exception 'CP7_MANDOR_SHOP_SALE_FIELDS';end if;
 intent_:=jsonb_build_object('action',p_action,'document',p,'expected_version',p_expected);
 request_hash_:=encode(extensions.digest(convert_to(jsonb_build_array('SALE_'||p_action,intent_)::text,'UTF8'),'sha256'),'hex');
 if not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP_REQUEST|'||actor_::text||'|'||p_request::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_REQUEST_BUSY';end if;
 select *into old_ from cp7_mandor_shop.requests where actor=actor_ and request_id=p_request;
 if old_.actor is not null then
  if old_.action is distinct from'SALE_'||p_action or old_.payload is distinct from intent_
   or old_.payload_sha256 is distinct from request_hash_ then raise exception 'CP7_MANDOR_SHOP_REQUEST_CHANGED';end if;
  return old_.response;
 end if;
 -- Separate internal buyer request from the complete external sale intent.
 -- Any collision is still checked against the exact actor/action/payload by
 -- buyer_command; a caller's previous standalone buyer UUID cannot be reused.
 buyer_request_:=substr(encode(extensions.digest(convert_to(jsonb_build_array(
  'cp7.mandor-shop-sale-buyer.v1',actor_,p_request)::text,'UTF8'),'sha256'),'hex'),1,32)::uuid;
 if buyer_request_=p_request then raise exception 'CP7_MANDOR_SHOP_REQUEST_NAMESPACE_COLLISION';end if;
 buyer_:=jsonb_build_object('contract_version','cp7.mandor-shop-buyer-command.v1',
  'sales_action',p_action,'contractor_id',p#>>'{mandor_buyer,contractor_id}',
  'review_token',p#>>'{mandor_buyer,review_token}');
 prepared_:=cp7_mandor_shop.buyer_command(buyer_,buyer_request_);
 if p->>'customer_id'is not null and p->>'customer_id'is distinct from prepared_->>'customer_id'then
  raise exception 'CP7_MANDOR_SHOP_SALE_BUYER_MISMATCH';end if;
 native_:=jsonb_set(p-'mandor_buyer','{customer_id}',prepared_->'customer_id');
 -- The original command retains its own validation, source version, actor,
 -- request identity, transaction context and unchanged draft engine.
 result_:=cp7_sales.command(p_action,native_,p_request,p_expected);
 if cp7_mandor_shop.buyer_access(p_action)is distinct from access_ then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;
 insert into cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response)
  values(actor_,p_request,'SALE_'||p_action,intent_,request_hash_,result_);
 return result_;
end $$;

alter function cp7_mandor_shop.is_mandor_customer(uuid)owner to postgres;
alter function cp7_mandor_shop.customer_buyer(text,uuid)owner to postgres;
alter function cp7_mandor_shop.save_sale(text,jsonb,uuid,text)owner to postgres;
revoke all on function cp7_mandor_shop.is_mandor_customer(uuid),cp7_mandor_shop.customer_buyer(text,uuid),
 cp7_mandor_shop.save_sale(text,jsonb,uuid,text)from public,anon,authenticated,service_role;
grant usage on schema cp7_mandor_shop to cp7_sales_read;
grant execute on function cp7_mandor_shop.is_mandor_customer(uuid)to cp7_sales_read;
grant execute on function cp7_mandor_shop.customer_buyer(text,uuid),
 cp7_mandor_shop.save_sale(text,jsonb,uuid,text)to cp7_mandor_shop_api;

create function public.erp_cp7_get_mandor_shop_customer_buyer_v1(p_sales_action text,p_customer uuid)
returns jsonb language sql stable security definer set search_path=''as $$
 select cp7_mandor_shop.customer_buyer(p_sales_action,p_customer)
$$;
create function public.erp_cp7_save_mandor_shop_sale_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text)
returns jsonb language sql volatile security definer set search_path=''as $$
 select cp7_mandor_shop.save_sale(p_action,p_payload,p_request,p_expected)
$$;


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
