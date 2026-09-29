-- Isolated CP7 policy authority. Existing ERP operational tables remain read-only.
create role cp7_policy nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_identity authorization cp7_policy;
revoke all on schema cp7_identity from public,anon,authenticated,service_role;
grant usage on schema cp7_identity to cp7_capture;
grant usage on schema erp,auth,extensions,public to cp7_policy;
grant select on erp.bf_skus_v1,erp.bf_sku_versions_v1,erp.bf_sku_members_v1,erp.products to cp7_policy;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_policy;
grant execute on function extensions.digest(bytea,text) to cp7_policy;

create table cp7_identity.production_policy (
 id uuid primary key default gen_random_uuid(),
 sku_id uuid not null references erp.bf_skus_v1(id),
 revision bigint not null check(revision>0),
 state text not null check(state in ('ACTIVE','PAUSED','STOPPED')),
 reason text not null check(length(btrim(reason)) between 1 and 1000),
 review_at timestamptz,
 actor uuid not null,
 request_id uuid not null,
 reviewed_commercial_version uuid not null,
 reviewed_commercial_revision bigint not null,
 reviewed_members uuid[] not null check(cardinality(reviewed_members)>0),
 recorded_at timestamptz not null default clock_timestamp(),
 unique(sku_id,revision),unique(actor,request_id,sku_id)
);
create table cp7_identity.commands (
 actor uuid not null,request_id uuid not null,payload_hash text not null,
 result jsonb not null,recorded_at timestamptz not null default clock_timestamp(),
 primary key(actor,request_id)
);
alter table cp7_identity.production_policy enable row level security;
alter table cp7_identity.commands enable row level security;
revoke all on all tables in schema cp7_identity from public,anon,authenticated,service_role;
grant select,insert on cp7_identity.production_policy,cp7_identity.commands to cp7_policy;
grant select on cp7_identity.production_policy to cp7_capture;

create function cp7_identity.immutable_row() returns trigger
language plpgsql security invoker set search_path='' as $$
begin raise exception using errcode='55000',message='CP7_POLICY_HISTORY_IMMUTABLE'; end $$;
create trigger immutable_policy before update or delete on cp7_identity.production_policy
 for each row execute function cp7_identity.immutable_row();
create trigger immutable_command before update or delete on cp7_identity.commands
 for each row execute function cp7_identity.immutable_row();

create function cp7_identity.access_now(writing boolean) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then
  raise exception using errcode='42501',message='CP7_POLICY_ACCESS_DENIED';
 end if;
 a:=erp.get_my_access_v1();
 if not coalesce((a->>'allowed')::boolean,false)
    or not erp.has_permission('master.product.view') or not erp.has_permission('production.wip.view')
    or (writing and not erp.has_permission('master.product.manage')) then
  raise exception using errcode='42501',message='CP7_POLICY_ACCESS_DENIED';
 end if;
 return a;
end $$;

-- Price-only revisions do not invalidate an already reviewed member set.
create function cp7_identity.membership(p_sku uuid,p_at timestamptz) returns jsonb
language sql stable security invoker set search_path='' as $$
 with version as materialized (
  select s.id,s.sku,s.brand_id,s.revision,v.id version_id
  from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id
  where s.id=p_sku and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at)
 ), members as materialized (
  select m.product_root from erp.bf_sku_members_v1 m join version v on v.version_id=m.version_id
 )
 select case when (select count(*) from version)=1 and (select count(*) from members)>0 then
  jsonb_build_object('sku_id',id,'sku',sku,'brand_id',brand_id,'commercial_version_id',version_id,
    'commercial_revision',revision::text,'members',(select jsonb_agg(product_root order by product_root) from members))
  else null end from version limit 1
$$;
