-- Explicit planning intent -> unchanged Native cutting draft. No reservation,
-- posting, stock/HPP calculator, or future physical-production fact is created.
create role cp7_plan_writer nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_plan_native authorization cp7_plan_writer;
revoke all on schema cp7_plan_native from public,anon,authenticated,service_role;
grant usage on schema erp,public,auth,extensions,cp7_private to cp7_plan_writer;
grant usage on schema cp7_plan_native to cp7_capture;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),extensions.digest(bytea,text),cp7_private.immutable_run() to cp7_plan_writer;
grant execute on function public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint) to cp7_plan_writer;
grant select on erp.production_orders,erp.production_patterns,erp.products,erp.sizes,erp.product_model_sizes,
 erp.materials,erp.material_rolls,erp.material_stock_movements,erp.locations,erp.cutting_groups,erp.cutting_group_rolls to cp7_plan_writer;
create table cp7_plan_native.drafts(
 id uuid primary key default gen_random_uuid(),plan_id uuid not null,revision bigint not null check(revision>0),
 actor uuid not null,request_id uuid not null,payload jsonb not null,run_id uuid not null,
 target_key text not null,source_hash text not null,core_hash text not null,composition_hash text not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(actor,request_id),unique(plan_id,revision));
create table cp7_plan_native.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id));
create table cp7_plan_native.intents(
 id uuid primary key default gen_random_uuid(),draft_id uuid not null unique references cp7_plan_native.drafts(id),
 actor uuid not null,target_key text not null,core_hash text not null,cutting_group_id uuid not null,
 request_id uuid not null,recorded_at timestamptz not null default clock_timestamp());
alter table cp7_plan_native.drafts owner to cp7_plan_writer;
alter table cp7_plan_native.commands owner to cp7_plan_writer;
alter table cp7_plan_native.intents owner to cp7_plan_writer;
alter table cp7_plan_native.drafts enable row level security;
alter table cp7_plan_native.commands enable row level security;
alter table cp7_plan_native.intents enable row level security;
create policy plan_drafts_private on cp7_plan_native.drafts for all to public using(false)with check(false);
create policy plan_commands_private on cp7_plan_native.commands for all to public using(false)with check(false);
create policy plan_intents_private on cp7_plan_native.intents for all to public using(false)with check(false);
revoke all on all tables in schema cp7_plan_native from public,anon,authenticated,service_role;
create trigger immutable_plan_draft before update or delete on cp7_plan_native.drafts for each row execute function cp7_private.immutable_run();
create trigger immutable_plan_command before update or delete on cp7_plan_native.commands for each row execute function cp7_private.immutable_run();
create trigger immutable_plan_intent before update or delete on cp7_plan_native.intents for each row execute function cp7_private.immutable_run();
create index plan_target_intents on cp7_plan_native.intents(target_key,cutting_group_id);
-- The shared analysis reads which unposted Native draft each intent links to;
-- it never reads drafts/commands payloads or gains any plan writer right.
grant select(id,target_key,cutting_group_id)on cp7_plan_native.intents to cp7_capture;
create function cp7_plan_native.access_now(mode text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;k text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if mode not in('READ','DRAFT','APPLY')or auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if coalesce((a->>'allowed')::boolean,false)is not true then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_DENIED';end if;
 foreach k in array array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','production.cutting.view']loop
  if not erp.has_permission(k)then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_DENIED';end if;
 end loop;
 if mode in('DRAFT','APPLY')and not erp.has_permission('production.cutting.create')then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_DENIED';end if;
 -- APPLY creates a Native SAVE_DRAFT, never POST. Posting continues through the
 -- existing Cutting page and its own current posting permission/recovery fence.
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions');
end $$;
create function cp7_plan_native.fields(v jsonb,names text[])returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if jsonb_typeof(v)is distinct from'object'or(select array_agg(k order by k)from jsonb_object_keys(v)k)is distinct from(select array_agg(k order by k)from unnest(names)k)then raise exception 'CP7_PLAN_FIELDS';end if;
end $$;
create function cp7_plan_native.decimal(v jsonb,pcs boolean default false)returns numeric
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare n numeric;
begin
 if jsonb_typeof(v)is distinct from'string'or v#>>'{}'!~'^(0|[1-9][0-9]{0,11})([.][0-9]{1,6})?$'then raise exception 'CP7_PLAN_QUANTITY';end if;
 n:=(v#>>'{}')::numeric;if pcs and trunc(n)<>n then raise exception 'CP7_PLAN_PCS';end if;return n;
end $$;
