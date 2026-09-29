-- Development family bundle. Install only in the isolated CP7 runner.
-- Public API wrappers are owned by a NOLOGIN principal with no business writes.
create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_private authorization cp7_capture;
revoke all on schema cp7_private from public,anon,authenticated,service_role;
grant usage on schema erp,auth,extensions to cp7_capture;
grant select on erp.products,erp.bf_sku_members_v1,erp.bf_sku_versions_v1,
 erp.bf_skus_v1,erp.production_orders,erp.cutting_groups,erp.cutting_group_size_slots,
 erp.cutting_group_rolls,erp.cutting_roll_yields,erp.fg_stock_movements,
 erp.sales_headers,erp.sales_items,erp.fg_lots,erp.hpp_versions to cp7_capture;
grant execute on function erp.get_my_access_v1(),erp.has_permission(text),
 erp.bd_lot_laundry_unknown_v1(uuid),erp.get_hpp_completeness(uuid) to cp7_capture;
grant execute on function auth.uid(),auth.jwt(),extensions.digest(bytea,text) to cp7_capture;

create table cp7_private.analysis_runs(
 id uuid primary key default gen_random_uuid(),
 actor uuid not null,
 request_id uuid not null,
 root_id uuid not null,
 financial_captured boolean not null,
 captured_at timestamptz not null,
 access_at_capture jsonb not null,
 payload jsonb not null check(payload->>'status'='COMPLETE'),
 dependencies jsonb not null,
 unique(actor,request_id)
);
alter table cp7_private.analysis_runs enable row level security;
revoke all on cp7_private.analysis_runs from public,anon,authenticated,service_role;
grant select,insert on cp7_private.analysis_runs to cp7_capture;

create function cp7_private.immutable_run() returns trigger
language plpgsql set search_path='' as $$
begin raise exception using errcode='55000',message='CP7_RUN_IMMUTABLE'; end $$;
create trigger cp7_immutable_run before update or delete on cp7_private.analysis_runs
for each row execute function cp7_private.immutable_run();

create function cp7_private.access_now() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb; k text;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then
  raise exception using errcode='42501',message='CP7_ACCESS_DENIED';
 end if;
 a:=erp.get_my_access_v1();
 if (a->>'allowed')::boolean is distinct from true then
  raise exception using errcode='42501',message='CP7_ACCESS_DENIED';
 end if;
 foreach k in array array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'] loop
  if not erp.has_permission(k) then
   raise exception using errcode='42501',message='CP7_ACCESS_DENIED';
  end if;
 end loop;
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile',
  'permissions',a->'permissions','financial',erp.has_permission('finance.hpp.view'));
end $$;

create function cp7_private.project(p jsonb, money boolean) returns jsonb
language sql immutable security invoker set search_path='' as $$
 with v as (select case when money then p->'sources' else (p->'sources')-'lot_cost' end s,
                   case when money then p->'counts' else (p->'counts')-'lot_cost' end c)
 select (p-'sources'-'counts'-'snapshot_hash')||jsonb_build_object('sources',s,'counts',c,
  'snapshot_hash',encode(extensions.digest(convert_to(s::text,'UTF8'),'sha256'),'hex')) from v
$$;

create function cp7_private.dependencies(p jsonb) returns jsonb
language sql immutable security invoker set search_path='' as $$
 select jsonb_build_object('semantics','cp7.source-probe.v1','scope','SIX_DOMAINS_ONLY',
  'domains',jsonb_object_agg(key,encode(extensions.digest(convert_to(value::text,'UTF8'),'sha256'),'hex')))
 from jsonb_each(p->'sources')
$$;
