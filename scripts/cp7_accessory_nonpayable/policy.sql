-- D17-20: eligibility follows the physical GOOD date in Asia/Jakarta.
-- Source preparation only. No installer/public RPC or Native writer hook yet.
-- No configured category values or historical effective dates are seeded.
create schema cp7_accessory_nonpayable authorization postgres;
revoke all on schema cp7_accessory_nonpayable from public,anon,authenticated,service_role;

create table cp7_accessory_nonpayable.category_versions_v1(
  id uuid primary key default gen_random_uuid(),
  effective_from date not null unique check(isfinite(effective_from)),
  source_event_id uuid not null references erp.bc_policy_setting_events_v1(id),
  source_version bigint not null check(source_version>0),
  source_status text not null check(source_status in('SET','PENDING_POLICY_VALUE')),
  category_ids uuid[] not null,
  reason text not null check(length(btrim(reason)) between 1 and 1000),
  request_id uuid not null unique,
  request_body jsonb not null,
  recorded_at timestamptz not null default statement_timestamp(),
  recorded_by uuid,
  check(array_position(category_ids,null) is null),
  check(cardinality(category_ids)<=50),
  check(source_status='SET' or cardinality(category_ids)=0)
);
alter table cp7_accessory_nonpayable.category_versions_v1 owner to postgres;
alter table cp7_accessory_nonpayable.category_versions_v1 enable row level security;
revoke all on cp7_accessory_nonpayable.category_versions_v1 from public,anon,authenticated,service_role;
create index category_versions_source_event_v1
  on cp7_accessory_nonpayable.category_versions_v1(source_event_id);

create function cp7_accessory_nonpayable.immutable_v1()
returns trigger language plpgsql security invoker set search_path='' as $$
begin
  raise exception 'NONPAYABLE_POLICY_HISTORY_IMMUTABLE: tulis versi baru; jangan ubah riwayat';
end;$$;
create trigger category_versions_immutable_v1 before update or delete
  on cp7_accessory_nonpayable.category_versions_v1 for each row
  execute function cp7_accessory_nonpayable.immutable_v1();
create trigger category_versions_no_truncate_v1 before truncate
  on cp7_accessory_nonpayable.category_versions_v1 for each statement
  execute function cp7_accessory_nonpayable.immutable_v1();

create function cp7_accessory_nonpayable.timeline_token_v1()
returns text language sql stable security invoker set search_path='' as $$
  select encode(sha256(convert_to(coalesce(jsonb_agg(jsonb_build_object(
    'id',v.id,'effective_from',to_char(v.effective_from,'YYYY-MM-DD'),
    'source_event_id',v.source_event_id,'source_version',v.source_version::text,
    'source_status',v.source_status,'category_ids',v.category_ids)
    order by v.effective_from,v.id),'[]'::jsonb)::text,'UTF8')),'hex')
  from cp7_accessory_nonpayable.category_versions_v1 v
$$;

-- The enclosing owning command must supply a real owner session and request
-- identity. This private function has no browser grant and changes no BC
-- setting; it records the effective date explicitly confirmed by the owner.
create function cp7_accessory_nonpayable.record_version_v1(
  p_effective_from date,p_source_event uuid,p_request uuid,p_expected_timeline text,p_reason text
) returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare
  source_row erp.bc_policy_setting_events_v1%rowtype;
  held_row cp7_accessory_nonpayable.category_versions_v1%rowtype;
  made_row cp7_accessory_nonpayable.category_versions_v1%rowtype;
  intended jsonb;
  categories uuid[]:=array[]::uuid[];
  item jsonb;
  category uuid;
begin
  perform erp.require_internal();
  perform erp.require_owner_admin();
  if p_effective_from is null or not isfinite(p_effective_from) or p_source_event is null
     or p_request is null or p_expected_timeline is null or p_expected_timeline!~'^[0-9a-f]{64}$'
     or p_reason is null or length(btrim(p_reason)) not between 1 and 1000 then
    raise exception 'NONPAYABLE_POLICY_INPUT_REQUIRED: tanggal berlaku, sumber, tinjauan, request dan alasan wajib';
  end if;
  intended:=jsonb_build_object('effective_from',to_char(p_effective_from,'YYYY-MM-DD'),
    'source_event_id',p_source_event,'expected_timeline',p_expected_timeline,'reason',p_reason);
  -- The BC setter already locks this row. Use the same source row before the
  -- private timeline lock, so a source update cannot race this observation.
  perform 1 from erp.bc_policy_settings_v1 s where s.policy_key='ERP_DEC02' for share;
  if not found then raise exception 'NONPAYABLE_ERP_DEC02_SOURCE_REQUIRED';end if;
  perform pg_advisory_xact_lock(hashtextextended('CP7_NONPAYABLE_CATEGORY_TIMELINE',0));
  -- Recheck current authority after the potentially blocking locks.
  perform erp.require_internal();
  perform erp.require_owner_admin();
  select * into held_row from cp7_accessory_nonpayable.category_versions_v1 v where v.request_id=p_request;
  if held_row.id is not null then
    if held_row.request_body is distinct from intended then
      raise exception 'NONPAYABLE_REQUEST_INTENT_CHANGED';
    end if;
    return jsonb_build_object('id',held_row.id,'effective_from',to_char(held_row.effective_from,'YYYY-MM-DD'),
      'source_event_id',held_row.source_event_id,'source_version',held_row.source_version::text);
  end if;
  if cp7_accessory_nonpayable.timeline_token_v1() is distinct from p_expected_timeline then
    raise exception 'NONPAYABLE_TIMELINE_STALE: kebijakan berubah; muat ulang';
  end if;
  select * into source_row from erp.bc_policy_setting_events_v1 e where e.id=p_source_event for share;
  if source_row.id is null or source_row.policy_key<>'ERP_DEC02' then
    raise exception 'NONPAYABLE_EXACT_ERP_DEC02_EVENT_REQUIRED';
  end if;
  if exists(select 1 from cp7_accessory_nonpayable.category_versions_v1 v where v.effective_from=p_effective_from) then
    raise exception 'NONPAYABLE_EFFECTIVE_DATE_ALREADY_RECORDED';
  end if;
  if source_row.status='SET' then
    if jsonb_typeof(source_row.value) is distinct from 'object'
       or (select count(*) from jsonb_object_keys(source_row.value))<>1
       or jsonb_typeof(source_row.value->'special_free_category_ids') is distinct from 'array'
       or jsonb_array_length(source_row.value->'special_free_category_ids')>50 then
      raise exception 'NONPAYABLE_SOURCE_CATEGORY_LIST_INVALID';
    end if;
    for item in select value from jsonb_array_elements(source_row.value->'special_free_category_ids') loop
      if jsonb_typeof(item) is distinct from 'string' or item#>>'{}'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
        raise exception 'NONPAYABLE_SOURCE_CATEGORY_ID_INVALID';
      end if;
      category:=(item#>>'{}')::uuid;
      if category=any(categories) or not exists(select 1 from erp.accessory_categories c where c.id=category) then
        raise exception 'NONPAYABLE_SOURCE_CATEGORY_ID_DUPLICATE_OR_MISSING';
      end if;
      categories:=array_append(categories,category);
    end loop;
    select coalesce(array_agg(x order by x),array[]::uuid[]) into categories from unnest(categories) x;
  elsif source_row.status<>'PENDING_POLICY_VALUE' or source_row.value is not null then
    raise exception 'NONPAYABLE_SOURCE_STATUS_INVALID';
  end if;
  insert into cp7_accessory_nonpayable.category_versions_v1(
    effective_from,source_event_id,source_version,source_status,category_ids,reason,request_id,request_body,recorded_by
  ) values(p_effective_from,source_row.id,source_row.version,source_row.status,categories,p_reason,p_request,intended,
    erp.current_app_user_id()) returning * into made_row;
  return jsonb_build_object('id',made_row.id,'effective_from',to_char(made_row.effective_from,'YYYY-MM-DD'),
    'source_event_id',made_row.source_event_id,'source_version',made_row.source_version::text);
end;$$;

-- Resolve from dated, explicitly recorded policies, never from today's
-- category list. This result is to be frozen with the new GOOD cost snapshot.
-- It is not a valuation or accrual command and changes no money or stock.
create function cp7_accessory_nonpayable.good_basis_v1(
  p_contractor uuid,p_category uuid,p_good_at timestamptz
) returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare
  day date;
  special_row erp.contractor_hpp_policy_versions%rowtype;
  category_row cp7_accessory_nonpayable.category_versions_v1%rowtype;
  current_version bigint;
  matches integer;
  free boolean:=false;
begin
  perform erp.require_internal();
  if p_contractor is null or p_category is null or p_good_at is null or not isfinite(p_good_at) then
    raise exception 'NONPAYABLE_GOOD_IDENTITIES_AND_PHYSICAL_TIME_REQUIRED';
  end if;
  day:=(p_good_at at time zone 'Asia/Jakarta')::date;
  select s.version into current_version from erp.bc_policy_settings_v1 s where s.policy_key='ERP_DEC02' for share;
  if not found then raise exception 'NONPAYABLE_ERP_DEC02_SOURCE_REQUIRED';end if;
  perform pg_advisory_xact_lock_shared(hashtextextended('CP7_NONPAYABLE_CATEGORY_TIMELINE',0));
  perform pg_advisory_xact_lock_shared(hashtextextended('CONTRACTOR_HPP_POLICY|'||p_contractor::text,0));
  perform erp.require_internal();
  if not exists(select 1 from erp.contractors c where c.id=p_contractor and c.contractor_type='MANDOR')
     or not exists(select 1 from erp.accessory_categories c where c.id=p_category) then
    raise exception 'NONPAYABLE_EXACT_CONTRACTOR_AND_CATEGORY_REQUIRED';
  end if;
  select count(*) into matches from erp.contractor_hpp_policy_versions p
    where p.contractor_id=p_contractor and p.effective_from<=day and (p.effective_to is null or p.effective_to>=day);
  if matches<>1 then raise exception 'NONPAYABLE_EXACT_DATED_SPECIAL_POLICY_REQUIRED';end if;
  select * into special_row from erp.contractor_hpp_policy_versions p
    where p.contractor_id=p_contractor and p.effective_from<=day and (p.effective_to is null or p.effective_to>=day);
  if special_row.is_special then
    if not exists(select 1 from cp7_accessory_nonpayable.category_versions_v1 v where v.source_version=current_version) then
      raise exception 'NONPAYABLE_CURRENT_POLICY_EFFECTIVE_DATE_REQUIRED: tetapkan tanggal berlaku ERP-DEC02';
    end if;
    select * into category_row from cp7_accessory_nonpayable.category_versions_v1 v
      where v.effective_from<=day order by v.effective_from desc limit 1;
    if category_row.id is null or category_row.source_status<>'SET' then
      raise exception 'NONPAYABLE_GOOD_DATE_CATEGORY_POLICY_REQUIRED';
    end if;
    free:=p_category=any(category_row.category_ids);
  end if;
  return jsonb_build_object('contract','cp7.accessory-good-nonpayable-basis.v1','owner_decision','D17-20',
    'contractor_id',p_contractor,'category_id',p_category,'good_date',to_char(day,'YYYY-MM-DD'),
    'good_at',to_char(p_good_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'special_policy_id',special_row.id,'special_policy_version',special_row.row_version::text,
    'special_effective_from',to_char(special_row.effective_from,'YYYY-MM-DD'),
    'special_effective_to',to_char(special_row.effective_to,'YYYY-MM-DD'),
    'is_special',special_row.is_special,'category_policy_id',category_row.id,
    'category_source_event_id',category_row.source_event_id,'category_source_version',category_row.source_version::text,
    'category_effective_from',to_char(category_row.effective_from,'YYYY-MM-DD'),'nonpayable',free);
end;$$;

alter function cp7_accessory_nonpayable.immutable_v1() owner to postgres;
alter function cp7_accessory_nonpayable.timeline_token_v1() owner to postgres;
alter function cp7_accessory_nonpayable.record_version_v1(date,uuid,uuid,text,text) owner to postgres;
alter function cp7_accessory_nonpayable.good_basis_v1(uuid,uuid,timestamptz) owner to postgres;
revoke all on all functions in schema cp7_accessory_nonpayable from public,anon,authenticated,service_role;
