-- Explicit owner-reviewed planning assumptions. Native operational facts stay
-- read-only; these rows never authorize production or replace WIP/calendar data.
create schema cp7_profile authorization cp7_policy;
revoke all on schema cp7_profile from public,anon,authenticated,service_role;
grant usage on schema cp7_profile to cp7_capture;
grant usage on schema cp7_demand,cp7_wip to cp7_policy;
grant execute on function cp7_demand.decimal(jsonb),cp7_wip.fields(jsonb,text[])to cp7_policy;

create table cp7_profile.profiles(
 id uuid primary key default gen_random_uuid(),root_id uuid not null,
 product_version_id uuid not null,size_id uuid not null,revision bigint not null check(revision>0),
 config jsonb not null,reason text not null,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(root_id,revision)
);
create table cp7_profile.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_profile.profiles owner to cp7_policy;
alter table cp7_profile.commands owner to cp7_policy;
alter table cp7_profile.profiles enable row level security;
alter table cp7_profile.commands enable row level security;
create policy cp7_profile_no_access on cp7_profile.profiles for all to public using(false)with check(false);
create policy cp7_profile_command_no_access on cp7_profile.commands for all to public using(false)with check(false);
revoke all on cp7_profile.profiles,cp7_profile.commands from public,anon,authenticated,service_role;
grant select on cp7_profile.profiles to cp7_capture;
create trigger immutable_profile before update or delete on cp7_profile.profiles
 for each row execute function cp7_identity.immutable_row();
create trigger immutable_profile_command before update or delete on cp7_profile.commands
 for each row execute function cp7_identity.immutable_row();

create function cp7_profile.source(p_roots uuid[],p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with products as(
  select p.id product_version_id,p.identity_root_id root_id,p.size_id,p.sku,p.product_name,
   count(*)over(partition by p.identity_root_id)root_count
  from erp.products p where p.identity_root_id=any(p_roots)and p.effective_from<=p_at
   and(p.effective_to is null or p.effective_to>p_at)
 ),rows as(
  select p.*,cfg.id profile_id,cfg.revision,cfg.config,cfg.reason,cfg.recorded_at,
   cfg.product_version_id reviewed_product_version_id
  from products p left join lateral(select x.*from cp7_profile.profiles x
   where x.root_id=p.root_id and x.recorded_at<=p_at order by x.revision desc limit 1)cfg on true
 )select coalesce(jsonb_agg(jsonb_build_object('root_id',root_id,'product_version_id',product_version_id,
  'size_id',size_id,'sku',sku,'product_name',product_name,'profile_id',profile_id,
  'revision',coalesce(revision,0)::text,'config',config,'reason',reason,'recorded_at',recorded_at,
  'quality',case when root_count<>1 then 'IDENTITY_CONFLICT'when profile_id is null then 'UNREVIEWED'
   when product_version_id<>reviewed_product_version_id then 'PHYSICAL_VERSION_CHANGED'else 'SELECTED_ASSUMPTION'end)
  order by root_id,product_version_id),'[]')from rows
$$;

create function cp7_profile.workspace(p_roots uuid[])returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_identity.access_now(false);
 if p_roots is null or array_ndims(p_roots)<>1 or cardinality(p_roots)not between 1 and 200
  or(select count(distinct x)from unnest(p_roots)x)<>cardinality(p_roots)then raise exception 'CP7_PROFILE_SCOPE';end if;
 outcome:=jsonb_build_object('contract_version','cp7.planning-profile.v1','rows',cp7_profile.source(p_roots,clock_timestamp()));
 if cp7_identity.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_profile.apply(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_profile.commands%rowtype;p cp7_profile.profiles%rowtype;
 sid uuid;pid uuid;sz uuid;expected bigint;current_revision bigint;config jsonb;reason text;
 mode text;minimum numeric;lead numeric;review numeric;buffer numeric;source jsonb;outcome jsonb;k text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_identity.access_now(true);
 if p_request is null then raise exception 'CP7_PROFILE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['root_id','product_version_id','expected_revision','config','reason']);
 perform pg_advisory_xact_lock(hashtextextended('CP7:PROFILE:REQUEST:'||auth.uid()::text||':'||p_request::text,0));
 if cp7_identity.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 select *into old from cp7_profile.commands where actor=auth.uid()and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_PROFILE_REQUEST_CHANGED';end if;
  return old.result;
 end if;
 sid:=(p_payload->>'root_id')::uuid;pid:=(p_payload->>'product_version_id')::uuid;
 if sid is null or pid is null or jsonb_typeof(p_payload->'expected_revision')is distinct from 'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'then raise exception 'CP7_PROFILE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PROFILE:ROOT:'||sid::text,0));
 if cp7_identity.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 source:=cp7_profile.source(array[sid],clock_timestamp());
 if jsonb_array_length(source)<>1 or source->0->>'product_version_id'<>pid::text
  or source->0->>'quality'='IDENTITY_CONFLICT'then raise exception 'CP7_PROFILE_SOURCE_CHANGED';end if;
 sz:=(source->0->>'size_id')::uuid;
 select coalesce(max(revision),0)into current_revision from cp7_profile.profiles where root_id=sid;
 if expected<>current_revision then raise exception 'CP7_PROFILE_REVISION_CHANGED';end if;
 config:=p_payload->'config';reason:=btrim(p_payload->>'reason');
 perform cp7_wip.fields(config,array['mean_mode','daily_pcs','minimum_available_days','lead_days','review_days','buffer_days']);
 mode:=config->>'mean_mode';
 if mode is null or mode not in('OWN_AVAILABLE_HISTORY','SELECTED_MANUAL')or jsonb_typeof(p_payload->'reason')is distinct from 'string'or reason is null
  or length(reason)not between 1 and 1000 then raise exception 'CP7_PROFILE_CONFIG';end if;
 minimum:=cp7_demand.decimal(config->'minimum_available_days');
 if minimum<>trunc(minimum)or minimum not between 1 and 3660 then raise exception 'CP7_PROFILE_MINIMUM_DAYS';end if;
 if mode='SELECTED_MANUAL'then perform cp7_demand.decimal(config->'daily_pcs');
 elsif config->'daily_pcs'is distinct from 'null'::jsonb then raise exception 'CP7_PROFILE_DOUBLE_MEAN';end if;
 foreach k in array array['lead_days','review_days','buffer_days']loop
  if config->k is distinct from 'null'::jsonb then
   if cp7_demand.decimal(config->k)>3660 then raise exception 'CP7_PROFILE_DAY_LIMIT';end if;
  end if;
 end loop;
 if config->'lead_days'<>'null'::jsonb and config->'review_days'<>'null'::jsonb then
  lead:=cp7_demand.decimal(config->'lead_days');review:=cp7_demand.decimal(config->'review_days');
  if lead+review<=0 or lead+review>3660 then raise exception 'CP7_PROFILE_HORIZON';end if;
 end if;
 insert into cp7_profile.profiles(root_id,product_version_id,size_id,revision,config,reason,actor,request_id)
 values(sid,pid,sz,current_revision+1,config,reason,auth.uid(),p_request)returning *into p;
 if cp7_identity.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 if cp7_profile.source(array[sid],clock_timestamp())->0->>'product_version_id'<>pid::text then raise exception 'CP7_PROFILE_SOURCE_CHANGED';end if;
 outcome:=jsonb_build_object('contract_version','cp7.planning-profile-outcome.v1','request_id',p_request,
  'profile_id',p.id,'root_id',sid,'revision',p.revision::text,'quality','SELECTED_ASSUMPTION');
 insert into cp7_profile.commands(actor,request_id,payload,result)values(auth.uid(),p_request,p_payload,outcome);
 return outcome;
end $$;

alter function cp7_profile.source(uuid[],timestamptz)owner to cp7_policy;
alter function cp7_profile.workspace(uuid[])owner to cp7_capture;
alter function cp7_profile.apply(jsonb,uuid)owner to cp7_policy;
revoke all on all functions in schema cp7_profile from public,anon,authenticated,service_role;
grant execute on function cp7_profile.source(uuid[],timestamptz)to cp7_capture;
grant create on schema public to cp7_capture,cp7_policy;
create function public.erp_cp7_get_planning_profiles_v1(p_roots uuid[])returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_profile.workspace(p_roots)$$;
create function public.erp_cp7_save_planning_profile_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_profile.apply(p_payload,p_request)$$;
alter function public.erp_cp7_get_planning_profiles_v1(uuid[])owner to cp7_capture;
alter function public.erp_cp7_save_planning_profile_v1(jsonb,uuid)owner to cp7_policy;
revoke create on schema public from cp7_capture,cp7_policy;
revoke all on function public.erp_cp7_get_planning_profiles_v1(uuid[]),public.erp_cp7_save_planning_profile_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_planning_profiles_v1(uuid[]),public.erp_cp7_save_planning_profile_v1(jsonb,uuid)to authenticated;
