-- A fixed platform capability, not a financial caller or arbitrary SQL API.
-- Install only through trusted maintenance authority in an explicit transaction.
-- The ordinary product creator cannot SET ROLE supabase_admin: that refusal is
-- intentional. There is no new role or catalog DML/MAINTAIN grant to postgres.
set local role supabase_admin;
set local search_path='';
do $platform_owner$begin
 if current_user<>'supabase_admin'or not(select rolsuper from pg_catalog.pg_roles where rolname=current_user)then
  raise exception 'CP7_GLOBAL_PLATFORM_CATALOG_OWNER_REQUIRED';end if;
end $platform_owner$;
create schema cp7_global_catalog_fence authorization supabase_admin;
revoke all on schema cp7_global_catalog_fence from public,anon,authenticated,service_role;

create function cp7_global_catalog_fence.lock_v1()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare catalogs_ jsonb;entry_ jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then
  raise exception 'CP7_GLOBAL_FRESH_CURRENT_READ_COMMITTED_REQUIRED';end if;
 -- No caller arguments or configurable target schemas. The first two locks
 -- freeze the complete identity domain before enumerating catalog tables.
 lock table pg_catalog.pg_class,pg_catalog.pg_namespace in share mode nowait;
 select coalesce(jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,
   c.relpersistence::text,pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
   case when c.relacl is null then null else to_jsonb(array(
    select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
   order by n.nspname collate "C",c.relname collate "C"),'[]'::jsonb)
 into catalogs_ from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
 where n.nspname='pg_catalog'and c.relkind in('r','p');
 for entry_ in select value from jsonb_array_elements(catalogs_)loop
  execute format('lock table pg_catalog.%I in share mode nowait',entry_->>1);
 end loop;
 return catalogs_;
end $$;

-- Normalize only the single new function under its actual owner, including
-- any ambient default grants. Existing defaults/functions are never changed.
do $platform_acl$declare row_ record;grantee_ text;begin
 for row_ in select x.grantee from pg_proc p
  cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))x
  where p.oid='cp7_global_catalog_fence.lock_v1()'::regprocedure and x.grantee<>p.proowner loop
  grantee_:=case when row_.grantee=0 then'PUBLIC'else quote_ident(pg_get_userbyid(row_.grantee))end;
  execute format('revoke all on function cp7_global_catalog_fence.lock_v1()from %s',grantee_);
 end loop;
end $platform_acl$;
grant usage on schema cp7_global_catalog_fence to postgres;
grant execute on function cp7_global_catalog_fence.lock_v1()to postgres;
reset role;
