-- A second narrow platform capability. Targets come only from the existing
-- private immutable installation profile; the caller supplies no identifiers.
-- It locks application relations and returns metadata, never application rows.
set local role supabase_admin;
set local search_path='';
create function cp7_global_catalog_fence.lock_relations_v1(p_profile text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare targets_ jsonb;entry_ jsonb;actual_ jsonb;result_ jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then
  raise exception 'CP7_GLOBAL_FRESH_CURRENT_READ_COMMITTED_REQUIRED';end if;
 if coalesce(p_profile,'')!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_GLOBAL_EXACT_SEALED_PROFILE_REQUIRED';end if;
 -- No metadata is trusted before the complete catalog fence and a fresh
 -- permanent-XID review. Old catalog writers can release relation locks while
 -- their uncommitted tuple changes remain; a snapshot xip list is insufficient.
 if exists(select 1 from pg_catalog.pg_class c
  join pg_catalog.pg_namespace n on n.oid=c.relnamespace
  where n.nspname='pg_catalog'and c.relkind in('r','p')and not exists(
   select 1 from pg_catalog.pg_locks l where l.pid=pg_backend_pid()
    and l.locktype='relation'and l.relation=c.oid and l.mode='ShareLock'and l.granted))then
  raise exception 'CP7_GLOBAL_COMPLETE_CATALOG_FENCE_REQUIRED_FIRST';end if;
 if exists(select 1 from pg_catalog.pg_locks where locktype='transactionid'
  and mode='ExclusiveLock'and granted and pid is distinct from pg_backend_pid())then
  raise exception using errcode='55P03',message='CP7_GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN';end if;
 -- Every delegated relation acquisition takes this profile lock first, then
 -- the declared targets in C order. All acquisitions are NOWAIT.
 lock table cp7_global_nonpo_envelope.profiles in exclusive mode nowait;
 if(select count(*)from cp7_global_nonpo_envelope.profiles)<>1 then
  raise exception 'CP7_GLOBAL_ONE_ACTUAL_FINAL_PARENT_PROFILE_REQUIRED';end if;
 select expected_relations into targets_ from cp7_global_nonpo_envelope.profiles where id=p_profile;
 if targets_ is null or jsonb_typeof(targets_)<>'array'or jsonb_array_length(targets_)<42
  or jsonb_array_length(targets_)<>(select count(distinct (e->>0)||'.'||(e->>1))from jsonb_array_elements(targets_)e)then
  raise exception 'CP7_GLOBAL_COMPLETE_EXACT_RELATION_PROFILE_REQUIRED';end if;
 for entry_ in select value from jsonb_array_elements(targets_)
  order by(value->>0)collate "C",(value->>1)collate "C"loop
  if jsonb_typeof(entry_)<>'array'or jsonb_array_length(entry_)<>8
   or coalesce(entry_->>0,'')!~'^[a-z_][a-z0-9_]*$'
   or coalesce(entry_->>1,'')!~'^[a-z_][a-z0-9_]*$'
   or entry_->>0~'^pg_'or entry_->>0=any(array[
    'information_schema','cron','auth','storage','_realtime','realtime','vault',
    'supabase_functions','supabase_migrations','graphql','graphql_public','extensions',
    'pgbouncer','cp7_global_catalog_fence'])
   or coalesce(entry_->>2,'')not in('r','p')or coalesce(entry_->>3,'')not in('p','u')then
   raise exception 'CP7_GLOBAL_TYPED_APPLICATION_RELATION_PROFILE_REQUIRED';end if;
  execute format('lock table %I.%I in exclusive mode nowait',entry_->>0,entry_->>1);
  select jsonb_build_array(n.nspname,c.relname,c.relkind::text,c.relpersistence::text,
   pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
   case when c.relacl is null then null else to_jsonb(array(
    select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
  into actual_ from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
  where n.nspname=entry_->>0 and c.relname=entry_->>1;
  if actual_ is distinct from entry_ then raise exception 'CP7_GLOBAL_RELATION_IDENTITY_OR_AUTHORITY_CHANGED';end if;
 end loop;
 -- Build the response from fresh actual catalog values in the original
 -- profile order; never relabel the expected projection as an observation.
 select jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,c.relpersistence::text,
  pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
  case when c.relacl is null then null else to_jsonb(array(
   select a::text from unnest(c.relacl)a order by a::text collate "C"))end)order by e.ordinality)
 into result_ from jsonb_array_elements(targets_)with ordinality e(value,ordinality)
 join pg_catalog.pg_namespace n on n.nspname=e.value->>0
 join pg_catalog.pg_class c on c.relnamespace=n.oid and c.relname=e.value->>1;
 if result_ is distinct from targets_ then raise exception 'CP7_GLOBAL_FINAL_RELATION_PROFILE_CHANGED';end if;
 return result_;
end $$;
do $relation_acl$declare row_ record;grantee_ text;begin
 for row_ in select x.grantee from pg_proc p
  cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))x
  where p.oid='cp7_global_catalog_fence.lock_relations_v1(text)'::regprocedure and x.grantee<>p.proowner loop
  grantee_:=case when row_.grantee=0 then'PUBLIC'else quote_ident(pg_get_userbyid(row_.grantee))end;
  execute format('revoke all on function cp7_global_catalog_fence.lock_relations_v1(text)from %s',grantee_);
 end loop;
end $relation_acl$;
grant execute on function cp7_global_catalog_fence.lock_relations_v1(text)to postgres;
reset role;
