-- Private buyer identity preparation. No public RPC, invoice, stock or payment.
-- Native sales command permissions are checked again after every acquired lock.
create function cp7_mandor_shop.buyer_access(p_action text)returns jsonb
language plpgsql stable security definer set search_path=''as $$
begin
 if p_action is null or p_action not in('CREATE','EDIT')then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_BUYER_ACTION_DENIED';end if;
 return cp7_sales.command_access(p_action);
end $$;

-- All 128 UUID bits are preserved. MD- plus 25 base36 digits fits the actual
-- Native varchar(30) customer code; no name, truncated UUID or code lookup links
-- an ordinary store customer to a mandor.
create function cp7_mandor_shop.customer_code(p_contractor uuid)returns text
language plpgsql immutable set search_path=''as $$
declare bytes_ bytea;n_ numeric:=0;digits_ text:='';remainder_ integer;i_ integer;
begin
 if p_contractor is null then raise exception 'CP7_MANDOR_SHOP_MANDOR_ID_REQUIRED';end if;
 bytes_:=decode(replace(p_contractor::text,'-',''),'hex');
 for i_ in 0..15 loop n_:=n_*256+get_byte(bytes_,i_);end loop;
 while n_>0 loop
  remainder_:=mod(n_,36)::integer;
  digits_:=substr('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',remainder_+1,1)||digits_;
  n_:=div(n_,36);
 end loop;
 return 'MD-'||lpad(digits_,25,'0');
end $$;

create function cp7_mandor_shop.buyer_basis(p_contractor uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare contractor_ erp.contractors;account_ cp7_mandor_shop.contractor_accounts;
 customer_ erp.customers;
begin
 select *into contractor_ from erp.contractors where id=p_contractor;
 if contractor_.id is null then raise exception 'CP7_MANDOR_SHOP_MANDOR_NOT_FOUND';end if;
 select *into account_ from cp7_mandor_shop.contractor_accounts where contractor_id=p_contractor;
 if account_.contractor_id is not null then
  select *into strict customer_ from erp.customers where id=account_.customer_id;
 end if;
 return jsonb_build_object('contractor',to_jsonb(contractor_),
  'account',case when account_.contractor_id is not null then to_jsonb(account_)else null end,
  'customer',case when customer_.id is not null then to_jsonb(customer_)else null end);
end $$;

create function cp7_mandor_shop.buyer_review(p_action text,p_access jsonb,p_basis jsonb)
returns text language sql immutable set search_path=''as $$
 select encode(extensions.digest(convert_to(jsonb_build_array(
  'cp7.mandor-shop-buyer-review.v1',p_action,p_access,p_basis)::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_mandor_shop.buyer_options(p_action text,p_query text default '',
 p_after uuid default null,p_limit integer default 25)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare access_ jsonb;query_ text;basis_ jsonb;rows_ jsonb:='[]';r_ record;
 seen_ integer:=0;more_ boolean:=false;last_ uuid;
begin
 access_:=cp7_mandor_shop.buyer_access(p_action);
 if p_query is null or length(p_query)>120 or p_limit is null or p_limit not between 1 and 100 then
  raise exception 'CP7_MANDOR_SHOP_BUYER_QUERY_FIELDS';end if;
 query_:=lower(btrim(p_query));
 for r_ in select c.id,c.contractor_code,c.contractor_name from erp.contractors c
  where c.is_active and c.contractor_type='MANDOR'and(p_after is null or c.id>p_after)
   and(query_=''or position(query_ in lower(c.contractor_code||' '||c.contractor_name))>0)
  order by c.id limit p_limit+1 loop
  seen_:=seen_+1;if seen_>p_limit then more_:=true;exit;end if;
  basis_:=cp7_mandor_shop.buyer_basis(r_.id);last_:=r_.id;
  rows_:=rows_||jsonb_build_array(jsonb_build_object('contractor_id',r_.id,
   'code',r_.contractor_code,'name',r_.contractor_name,
   'customer_id',basis_#>>'{account,customer_id}',
   'can_select',basis_->'customer'='null'::jsonb or basis_#>'{customer,is_active}'='true'::jsonb,
   'review_token',cp7_mandor_shop.buyer_review(p_action,access_,basis_)));
 end loop;
 return jsonb_build_object('contract_version','cp7.mandor-shop-buyer-options.v1',
  'buyer_category','MANDOR','sales_action',p_action,'rows',rows_,
  'has_more',more_,'next_after',case when more_ then last_ else null end);
end $$;

create function cp7_mandor_shop.buyer_command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'
 set lock_timeout='1s'as $$
declare action_ text;actor_ uuid;contractor_ uuid;access_ jsonb;basis_ jsonb;
 hash_ text;old_ cp7_mandor_shop.requests;customer_ erp.customers;
 code_ text;result_ jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then
  raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'object'or p_request is null then
  raise exception 'CP7_MANDOR_SHOP_BUYER_COMMAND_FIELDS';end if;
 if not p?&array['contract_version','sales_action','contractor_id','review_token']
  or p->>'contract_version'is distinct from'cp7.mandor-shop-buyer-command.v1'
  or exists(select 1 from jsonb_each(p)e where e.key not in(
   'contract_version','sales_action','contractor_id','review_token')or jsonb_typeof(e.value)<>'string')
  or coalesce(p->>'contractor_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'review_token','')!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_MANDOR_SHOP_BUYER_COMMAND_FIELDS';end if;
 action_:=p->>'sales_action';access_:=cp7_mandor_shop.buyer_access(action_);
 actor_:=auth.uid();contractor_:=(p->>'contractor_id')::uuid;
 hash_:=encode(extensions.digest(convert_to(jsonb_build_array('PREPARE_BUYER',p)::text,'UTF8'),'sha256'),'hex');
 if not pg_try_advisory_xact_lock(hashtextextended(
  'CP7_MANDOR_SHOP_REQUEST|'||actor_::text||'|'||p_request::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_REQUEST_BUSY';end if;
 lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;
 if not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP|'||contractor_::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_SOURCE_BUSY_REVIEW_AGAIN';end if;
 perform 1 from erp.contractors where id=contractor_ for share nowait;
 perform 1 from erp.customers c join cp7_mandor_shop.contractor_accounts a on a.customer_id=c.id
  where a.contractor_id=contractor_ for share of c nowait;
 if cp7_mandor_shop.buyer_access(action_)is distinct from access_ then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;
 select *into old_ from cp7_mandor_shop.requests where actor=actor_ and request_id=p_request;
 if old_.actor is not null then
  if old_.action is distinct from'PREPARE_BUYER'or old_.payload is distinct from p
   or old_.payload_sha256 is distinct from hash_ then
   raise exception 'CP7_MANDOR_SHOP_REQUEST_CHANGED';end if;
  return old_.response;
 end if;
 basis_:=cp7_mandor_shop.buyer_basis(contractor_);
 if basis_#>'{contractor,is_active}'is distinct from'true'::jsonb
  or basis_#>>'{contractor,contractor_type}'is distinct from'MANDOR'then
  raise exception 'CP7_MANDOR_SHOP_ACTIVE_MANDOR_REQUIRED';end if;
 if cp7_mandor_shop.buyer_review(action_,access_,basis_)is distinct from p->>'review_token'then
  raise exception 'CP7_MANDOR_SHOP_REVIEW_CHANGED';end if;
 if basis_->'account'<>'null'::jsonb then
  select *into strict customer_ from erp.customers where id=(basis_#>>'{account,customer_id}')::uuid;
  if not customer_.is_active then raise exception 'CP7_MANDOR_SHOP_CUSTOMER_INACTIVE';end if;
 else
  code_:=cp7_mandor_shop.customer_code(contractor_);
  if exists(select 1 from erp.customers where customer_code=code_)then
   raise exception 'CP7_MANDOR_SHOP_ACCOUNT_CODE_COLLISION_REVIEW_REQUIRED';end if;
  if exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid()
   and transaction_id=txid_current_if_assigned())or exists(
   select 1 from cp7_mandor_shop.command_context where backend_pid=pg_backend_pid()
    and transaction_id=txid_current_if_assigned())then
   raise exception 'CP7_MANDOR_SHOP_BUYER_NESTED_CONTEXT_REFUSED';end if;
  -- Only this narrow command establishes the existing Native sales context.
  -- No caller-controlled setting supplies internal ERP authority.
  insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),actor_,null,action_);
  insert into cp7_mandor_shop.command_context values(
   pg_backend_pid(),txid_current(),actor_,p_request,'PREPARE_BUYER',hash_);
  insert into erp.customers(customer_code,customer_name)
   values(code_,basis_#>>'{contractor,contractor_name}')returning *into customer_;
  insert into cp7_mandor_shop.contractor_accounts(contractor_id,customer_id,created_by)
   values(contractor_,customer_.id,actor_);
  delete from cp7_mandor_shop.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 end if;
 if cp7_mandor_shop.buyer_access(action_)is distinct from access_ then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;
 result_:=jsonb_build_object('contract_version','cp7.mandor-shop-buyer-outcome.v1',
  'buyer_category','MANDOR','contractor_id',contractor_,'name',basis_#>>'{contractor,contractor_name}',
  'customer_id',customer_.id,'customer_code',customer_.customer_code,'request_id',p_request);
 insert into cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response)
  values(actor_,p_request,'PREPARE_BUYER',p,hash_,result_);
 return result_;
end $$;

alter function cp7_mandor_shop.buyer_access(text)owner to postgres;
alter function cp7_mandor_shop.customer_code(uuid)owner to postgres;
alter function cp7_mandor_shop.buyer_basis(uuid)owner to postgres;
alter function cp7_mandor_shop.buyer_review(text,jsonb,jsonb)owner to postgres;
alter function cp7_mandor_shop.buyer_options(text,text,uuid,integer)owner to postgres;
alter function cp7_mandor_shop.buyer_command(jsonb,uuid)owner to postgres;
revoke all on function cp7_mandor_shop.buyer_access(text)from public,anon,authenticated,service_role;
revoke all on function cp7_mandor_shop.customer_code(uuid)from public,anon,authenticated,service_role;
revoke all on function cp7_mandor_shop.buyer_basis(uuid)from public,anon,authenticated,service_role;
revoke all on function cp7_mandor_shop.buyer_review(text,jsonb,jsonb)from public,anon,authenticated,service_role;
revoke all on function cp7_mandor_shop.buyer_options(text,text,uuid,integer)from public,anon,authenticated,service_role;
revoke all on function cp7_mandor_shop.buyer_command(jsonb,uuid)from public,anon,authenticated,service_role;
