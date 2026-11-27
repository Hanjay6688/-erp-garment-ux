do $good_source$ begin
 if exists (select from (values ('erp.bc_free_basis_v1(uuid,uuid,timestamp with time zone)','8d514efa74707dbc2f275a225f081095d1311558a9ef7819c8b8ef5aca98260e'),
('erp.be_reverse_rework_target_v1(uuid,text)','3dd30156e24e23cfee1834286dd4f20771b7ff3907f1431611d9f00c6bfcd340'),
('erp.ensure_fg_accessory_cost_snapshot(uuid)','1634377e32f56f4bab27232be686df6585aee54655953f93b1597ae912cb93bc'),
('erp.post_accessory_reimbursement_accrual(uuid)','b10b63a72b2915cc5a6d1f3331fcbb4fe072c121112df31bbad8306856fcdacc'),
('erp.refresh_accessory_hpp_after_material_recost(uuid,text)','b2151dcfc3b10659454fc8d7d63412f7affb5e698049e4ec67ff82531fc8faee'),
('erp.reverse_qc(uuid,text)','48f0cb850a38bb69ea59f49cec777f7c6020645a9a43e8f5ded21221614c7dc0'),
('erp.reverse_rework_completion(uuid,text)','3436545141606c346544d15ed6dd6342b73d0a51b1a7208e54a32ff94b0654ac'),
('erp.save_accessory_issue_action_v1(text,jsonb,uuid)','4346b5e5bc58d97d1b1d0cb6bfb9b5c0b62689853aeffded6f012bbd6d4e2045')) as p(sig,sha)
  where encode(sha256(convert_to(pg_get_functiondef(to_regprocedure(p.sig)),'UTF8')),'hex') is distinct from p.sha)
 then raise exception 'GOOD native definition differs from the qualified Enteng Uji predecessor'; end if;
 end $good_source$;
CREATE OR REPLACE FUNCTION erp.bc_free_basis_v1(p_material uuid, p_contractor uuid, p_at timestamp with time zone)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select jsonb_build_object('category_id',m.accessory_category_id,'policy_version',erp.bc_policy_version_v1('ERP_DEC02')::text)
  from erp.materials m
  where m.id=p_material and m.material_type='ACCESSORY'
    and coalesce(erp.bc_policy_v1('ERP_DEC02')->'special_free_category_ids','[]'::jsonb) ? m.accessory_category_id::text
    and exists(select 1 from erp.contractor_hpp_policy_versions v where v.contractor_id=p_contractor and v.is_special
      and v.effective_from<=(p_at at time zone 'Asia/Jakarta')::date and (v.effective_to is null or v.effective_to>=(p_at at time zone 'Asia/Jakarta')::date))
$function$
;
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

-- Immutable provenance for the reimbursement rate chosen at initial GOOD.
-- Load after policy.sql; no Native function is replaced by this file.
create table cp7_accessory_nonpayable.good_bases_v1(
  snapshot_id uuid primary key references erp.fg_accessory_cost_snapshots(id),
  lot_id uuid not null references erp.fg_lots(id),
  contractor_id uuid not null references erp.contractors(id),
  category_policy_id uuid references cp7_accessory_nonpayable.category_versions_v1(id),
  special_policy_id uuid not null references erp.contractor_hpp_policy_versions(id),
  good_date date not null,
  nonpayable boolean not null,
  original_reimbursement_rate numeric(18,6) not null check(original_reimbursement_rate>=0),
  fixed_snapshot jsonb not null,
  basis jsonb not null,
  recorded_at timestamptz not null default statement_timestamp(),
  check(not nonpayable or category_policy_id is not null)
);
alter table cp7_accessory_nonpayable.good_bases_v1 owner to postgres;
alter table cp7_accessory_nonpayable.good_bases_v1 enable row level security;
revoke all on cp7_accessory_nonpayable.good_bases_v1 from public,anon,authenticated,service_role;
create index good_bases_lot_v1 on cp7_accessory_nonpayable.good_bases_v1(lot_id);
create index good_bases_special_policy_v1 on cp7_accessory_nonpayable.good_bases_v1(special_policy_id,good_date);
create index good_bases_category_policy_v1 on cp7_accessory_nonpayable.good_bases_v1(category_policy_id);
create index good_bases_contractor_day_v1 on cp7_accessory_nonpayable.good_bases_v1(contractor_id,good_date);
create trigger good_bases_immutable_v1 before update or delete
  on cp7_accessory_nonpayable.good_bases_v1 for each row
  execute function cp7_accessory_nonpayable.immutable_v1();
create trigger good_bases_no_truncate_v1 before truncate
  on cp7_accessory_nonpayable.good_bases_v1 for each statement
  execute function cp7_accessory_nonpayable.immutable_v1();

create function cp7_accessory_nonpayable.snapshot_identity_v1(p_snapshot uuid)
returns jsonb language sql stable security invoker set search_path='' as $$
  select jsonb_build_object('id',s.id,'lot_id',s.lot_id,'po_id',s.po_id,'product_id',s.product_id,
    'bom_version_id',s.bom_version_id,'bom_item_id',s.bom_item_id,'category_id',s.category_id,
    'good_qty_pcs',s.good_qty_pcs::text,'qty_per_good_fg_base',s.qty_per_good_fg_base::text,
    'hpp_method',s.hpp_method,'reimbursement_unit_rate_base_snapshot',s.reimbursement_unit_rate_base_snapshot::text,
    'costing_basis_at',to_char(s.costing_basis_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'costing_basis_source',s.costing_basis_source)
  from erp.fg_accessory_cost_snapshots s where s.id=p_snapshot
$$;

create function cp7_accessory_nonpayable.capture_basis_v1(
  p_snapshot uuid,p_contractor uuid,p_original_rate numeric,p_basis jsonb
) returns void language plpgsql volatile security definer set search_path='' as $$
declare
  snap erp.fg_accessory_cost_snapshots%rowtype;
  lot erp.fg_lots%rowtype;
  authoritative uuid;
  rework_id uuid;
  actual jsonb;
begin
  perform erp.require_internal();
  if p_original_rate is null or p_original_rate<0 or p_original_rate::text in('NaN','Infinity','-Infinity') then
    raise exception 'NONPAYABLE_ORIGINAL_BOM_RATE_REQUIRED';
  end if;
  select * into snap from erp.fg_accessory_cost_snapshots s where s.id=p_snapshot for share;
  select * into lot from erp.fg_lots l where l.id=snap.lot_id for share;
  if snap.id is null or lot.id is null or lot.lot_origin<>'PRODUCTION' or snap.costing_basis_at<>lot.produced_at
     or snap.po_id is distinct from lot.po_id or snap.product_id is distinct from lot.product_id then
    raise exception 'NONPAYABLE_EXACT_NEW_GOOD_SNAPSHOT_REQUIRED';
  end if;
  select ro.id,d.reimbursement_contractor_id into rework_id,authoritative
    from erp.rework_orders ro join erp.rework_accessory_decisions d on d.rework_order_id=ro.id
    where ro.good_fg_lot_id=lot.id;
  if rework_id is null then
    select p.contractor_id into authoritative from erp.production_orders p where p.id=lot.po_id;
  end if;
  if authoritative is null or authoritative is distinct from p_contractor then
    raise exception 'NONPAYABLE_AUTHORITATIVE_GOOD_CONTRACTOR_REQUIRED';
  end if;
  actual:=cp7_accessory_nonpayable.good_basis_v1(p_contractor,snap.category_id,lot.produced_at);
  if actual is distinct from p_basis or snap.reimbursement_unit_rate_base_snapshot is distinct from
     (case when (actual->>'nonpayable')::boolean then 0::numeric else p_original_rate end) then
    raise exception 'NONPAYABLE_FROZEN_POLICY_AND_RATE_MUST_MATCH';
  end if;
  if exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 b where b.snapshot_id=p_snapshot) then
    raise exception 'NONPAYABLE_GOOD_BASIS_ALREADY_CAPTURED';
  end if;
  insert into cp7_accessory_nonpayable.good_bases_v1(snapshot_id,lot_id,contractor_id,category_policy_id,
    special_policy_id,good_date,nonpayable,original_reimbursement_rate,fixed_snapshot,basis)
  values(snap.id,lot.id,p_contractor,(actual->>'category_policy_id')::uuid,(actual->>'special_policy_id')::uuid,
    (actual->>'good_date')::date,(actual->>'nonpayable')::boolean,p_original_rate,
    cp7_accessory_nonpayable.snapshot_identity_v1(snap.id),actual);
end;$$;

create function cp7_accessory_nonpayable.guard_category_date_v1()
returns trigger language plpgsql security definer set search_path='' as $$
declare next_from date;
begin
  select min(v.effective_from) into next_from from cp7_accessory_nonpayable.category_versions_v1 v
    where v.effective_from>new.effective_from;
  if exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 b join erp.fg_lots l on l.id=b.lot_id
    where l.lot_origin='PRODUCTION' and b.category_policy_id is not null and b.good_date>=new.effective_from
      and (next_from is null or b.good_date<next_from)) then
    raise exception 'NONPAYABLE_POSTED_GOOD_POLICY_REVIEW_REQUIRED: koreksi/balik GOOD terkait dahulu';
  end if;
  return new;
end;$$;
create trigger category_date_used_guard_v1 before insert
  on cp7_accessory_nonpayable.category_versions_v1 for each row
  execute function cp7_accessory_nonpayable.guard_category_date_v1();

create function cp7_accessory_nonpayable.guard_special_change_v1()
returns trigger language plpgsql security definer set search_path='' as $$
begin
  if tg_op='DELETE' then
    if exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 b join erp.fg_lots l on l.id=b.lot_id
      where b.special_policy_id=old.id and l.lot_origin='PRODUCTION') then
      raise exception 'NONPAYABLE_POSTED_GOOD_SPECIAL_POLICY_USED';
    end if;
    return old;
  end if;
  if exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 b join erp.fg_lots l on l.id=b.lot_id
    where l.lot_origin='PRODUCTION' and b.contractor_id=new.contractor_id
      and b.good_date>=new.effective_from and (new.effective_to is null or b.good_date<=new.effective_to)
      and (tg_op='INSERT' or b.special_policy_id<>new.id)) then
    raise exception 'NONPAYABLE_POSTED_GOOD_SPECIAL_POLICY_REVIEW_REQUIRED';
  end if;
  if tg_op='UPDATE' and exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 b join erp.fg_lots l on l.id=b.lot_id
    where b.special_policy_id=old.id and l.lot_origin='PRODUCTION' and
      (new.id<>old.id or new.contractor_id<>old.contractor_id or new.is_special<>old.is_special
       or b.good_date<new.effective_from or (new.effective_to is not null and b.good_date>new.effective_to))) then
    raise exception 'NONPAYABLE_POSTED_GOOD_SPECIAL_POLICY_USED';
  end if;
  return new;
end;$$;
create trigger nonpayable_special_used_guard_v1 before insert or update or delete
  on erp.contractor_hpp_policy_versions for each row
  execute function cp7_accessory_nonpayable.guard_special_change_v1();

-- A zero-reimbursement exception is lawful only for frozen company-funded
-- components with one explicit contractor. Unproven positive-cost lines keep
-- the Native refusal, including lines that became positive during recost.
create function cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(p_lot uuid)
returns uuid language plpgsql volatile security definer set search_path='' as $$
declare found_contractor uuid;
begin
  perform erp.require_internal();
  if not exists(select 1 from erp.fg_lots l where l.id=p_lot and l.lot_origin='PRODUCTION') then return null;end if;
  select (array_agg(distinct b.contractor_id) filter(where b.nonpayable))[1] into found_contractor
    from erp.fg_accessory_cost_snapshots s
    left join cp7_accessory_nonpayable.good_bases_v1 b on b.snapshot_id=s.id
    where s.lot_id=p_lot
    having count(*)>0 and sum(s.total_reimbursement)=0
      and count(*) filter(where b.nonpayable)>0
      and count(distinct b.contractor_id) filter(where b.nonpayable)=1
      and bool_and(s.total_hpp_cost=0 or (b.nonpayable is true and b.lot_id=p_lot
        and b.fixed_snapshot=cp7_accessory_nonpayable.snapshot_identity_v1(s.id)))
      and bool_and(b.nonpayable is not true or b.fixed_snapshot=cp7_accessory_nonpayable.snapshot_identity_v1(s.id));
  return found_contractor;
end;$$;

create function cp7_accessory_nonpayable.booked_hpp_v1(p_lot uuid)
returns numeric language plpgsql volatile security definer set search_path='' as $$
declare amount numeric;
begin
  perform erp.require_internal();
  select coalesce(sum(jl.debit-jl.credit),0) into amount from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.status='POSTED' and jl.account_id=erp.account_id('WIP') and
      ((je.source_type='ACCESSORY_REIMBURSE_ACCRUAL' and je.source_id=p_lot)
       or(je.source_type='ACCESSORY_HPP_RECOST' and exists(select 1 from erp.fg_accessory_cost_revisions rv
         join erp.fg_accessory_cost_snapshots s on s.id=rv.snapshot_id where rv.id=je.source_id and s.lot_id=p_lot)));
  return amount;
end;$$;

create function cp7_accessory_nonpayable.recost_delta_v1(p_lot uuid)
returns numeric language plpgsql volatile security definer set search_path='' as $$
declare total_hpp numeric;total_reimbursement numeric;contractor uuid;
begin
  perform erp.require_internal();
  -- Native recost also visits retained snapshots of lawfully voided GOOD.
  -- Their basis stays immutable, but no active company-funded HPP remains.
  -- Use the unchanged Native historical-cost path without a new accrual.
  if not exists(select 1 from erp.fg_lots l where l.id=p_lot and l.lot_origin='PRODUCTION') then return null;end if;
  if not exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 b where b.lot_id=p_lot and b.nonpayable) then return null;end if;
  select sum(s.total_hpp_cost),sum(s.total_reimbursement) into total_hpp,total_reimbursement
    from erp.fg_accessory_cost_snapshots s where s.lot_id=p_lot;
  if total_reimbursement<>0 then return null;end if;
  contractor:=cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(p_lot);
  if contractor is null then raise exception 'NONPAYABLE_RECOST_REQUIRES_COMPLETE_FROZEN_BASIS';end if;
  -- Cumulative cents also cover an originally zero or sub-cent GOOD without
  -- manufacturing a zero journal. Native recost dates and source UUID remain.
  return round(total_hpp,2)-cp7_accessory_nonpayable.booked_hpp_v1(p_lot);
end;$$;

create function cp7_accessory_nonpayable.already_recosted_v1(p_lot uuid,p_hpp numeric,p_reimbursement numeric)
returns boolean language plpgsql volatile security definer set search_path='' as $$
begin
  perform erp.require_internal();
  return p_reimbursement=0 and cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(p_lot) is not null
    and exists(select 1 from erp.journal_entries je join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id
      join erp.fg_accessory_cost_snapshots s on s.id=rv.snapshot_id
      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and s.lot_id=p_lot)
    and cp7_accessory_nonpayable.booked_hpp_v1(p_lot)=round(p_hpp,2);
end;$$;

alter function cp7_accessory_nonpayable.snapshot_identity_v1(uuid) owner to postgres;
alter function cp7_accessory_nonpayable.capture_basis_v1(uuid,uuid,numeric,jsonb) owner to postgres;
alter function cp7_accessory_nonpayable.guard_category_date_v1() owner to postgres;
alter function cp7_accessory_nonpayable.guard_special_change_v1() owner to postgres;
alter function cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(uuid) owner to postgres;
alter function cp7_accessory_nonpayable.booked_hpp_v1(uuid) owner to postgres;
alter function cp7_accessory_nonpayable.recost_delta_v1(uuid) owner to postgres;
alter function cp7_accessory_nonpayable.already_recosted_v1(uuid,numeric,numeric) owner to postgres;
revoke all on all functions in schema cp7_accessory_nonpayable from public,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION erp.ensure_fg_accessory_cost_snapshot(p_lot_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  p erp.production_orders%rowtype;
  v_bom uuid;
  r record;
  v_category_avg numeric(18,6);
  v_hpp_factor numeric(18,6);
  v_reimburse_factor numeric(18,6);
  v_hpp_base numeric(18,6);
  v_reimburse_base numeric(18,6);
  v_snapshot uuid;
  v_nonpayable_basis jsonb;
  v_original_reimburse numeric(18,6);
  v_commit_at timestamptz;
  v_rework uuid;
  v_decision uuid;
  v_recipient uuid;
  v_selected_count integer;
  v_snapshot_count integer;
begin
  perform erp.require_internal();
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select * into p from erp.production_orders where id=l.po_id;
  if p.id is null then return; end if;

  select ro.id,d.id,d.bom_version_id,d.reimbursement_contractor_id,d.selected_item_count
  into v_rework,v_decision,v_bom,v_recipient,v_selected_count
  from erp.rework_orders ro
  join erp.rework_accessory_decisions d on d.rework_order_id=ro.id
  where ro.good_fg_lot_id=l.id;

  if v_rework is not null then
    select count(*) into v_snapshot_count
    from erp.fg_accessory_cost_snapshots s where s.lot_id=l.id;
    if v_snapshot_count>0 then
      if v_snapshot_count<>v_selected_count
         or exists(
           select 1 from erp.fg_accessory_cost_snapshots s
           left join erp.rework_accessory_selection_lines sl
             on sl.decision_id=v_decision and sl.bom_item_id=s.bom_item_id
           where s.lot_id=l.id and sl.id is null
         ) then
        raise exception 'Rework accessory snapshot set diverges from immutable selection lineage';
      end if;
      return;
    end if;
    if v_selected_count=0 then return; end if;
    if v_bom is null then raise exception 'Selected rework accessory lineage has no BOM version'; end if;
    if not exists(
      select 1 from erp.po_accessory_bom_commitments c
      where c.po_id=l.po_id and c.product_id=l.product_id and c.bom_version_id=v_bom
    ) then raise exception 'Rework accessory BOM commitment is missing or changed'; end if;

    for r in
      select sl.*,c.category_code
      from erp.rework_accessory_selection_lines sl
      join erp.accessory_categories c on c.id=sl.category_id
      where sl.decision_id=v_decision
      order by c.category_code,sl.id
    loop
      v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
      if r.hpp_method_snapshot='CATEGORY_MOVING_AVG' then
        if v_category_avg is null then
          raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
        end if;
        v_hpp_base:=v_category_avg;
      else
        v_hpp_base:=r.hpp_standard_unit_cost_base_snapshot;
      end if;
      v_reimburse_base:=r.reimbursement_unit_rate_base_snapshot;
      v_original_reimburse:=v_reimburse_base;v_nonpayable_basis:=null;
      if v_recipient is not null then
        v_nonpayable_basis:=cp7_accessory_nonpayable.good_basis_v1(v_recipient,r.category_id,l.produced_at);
        if (v_nonpayable_basis->>'nonpayable')::boolean then v_reimburse_base:=0;end if;
      end if;
      insert into erp.fg_accessory_cost_snapshots(
        lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
        good_qty_pcs,qty_per_good_fg_base,hpp_method,
        category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
        reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
      ) values(
        l.id,l.po_id,l.product_id,v_bom,r.bom_item_id,r.category_id,
        l.initial_qty_pcs,r.qty_per_good_fg_base_snapshot,r.hpp_method_snapshot,
        v_category_avg,v_hpp_base,v_reimburse_base,l.produced_at,'FG_ACCEPTANCE'
      ) returning id into v_snapshot;
      if v_nonpayable_basis is not null then
        perform cp7_accessory_nonpayable.capture_basis_v1(v_snapshot,v_recipient,v_original_reimburse,v_nonpayable_basis);
      end if;
      if v_recipient is null and v_reimburse_base>0 then
        raise exception 'Selected rework accessory reimbursement has no authoritative Mandor';
      end if;
      if v_recipient is not null and v_reimburse_base>0 then
        insert into erp.contractor_accessory_reimbursement_entitlements(
          snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
        ) select
          v_snapshot,v_recipient,l.po_id,l.id,l.product_id,r.category_id,
          l.produced_at,total_reimbursement
        from erp.fg_accessory_cost_snapshots where id=v_snapshot;
      end if;
    end loop;
    return;
  end if;

  if exists(select 1 from erp.initial_import_wip_outputs o join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id where o.lot_id=l.id and s.accessory_cost_included) then return;end if;
  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=l.id) then return; end if;
  v_bom:=erp.commit_accessory_bom_for_lot(l.id);
  if v_bom is null then return; end if;
  select committed_at into v_commit_at
  from erp.po_accessory_bom_commitments
  where po_id=l.po_id and product_id=l.product_id;
  for r in
    select i.*,c.base_uom_code
    from erp.accessory_bom_items i
    join erp.accessory_categories c on c.id=i.category_id
    where i.bom_version_id=v_bom order by c.category_code
  loop
    v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
    if r.hpp_method='CATEGORY_MOVING_AVG' then
      if v_category_avg is null then
        raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
      end if;
      v_hpp_base:=v_category_avg;
    else
      v_hpp_factor:=erp.accessory_uom_factor(r.category_id,r.hpp_uom_code,l.produced_at);
      v_hpp_base:=r.hpp_standard_rate/v_hpp_factor;
    end if;
    v_reimburse_factor:=erp.accessory_uom_factor(
      r.category_id,r.reimbursement_uom_code,l.produced_at
    );
    v_reimburse_base:=r.reimbursement_rate/v_reimburse_factor;
    v_original_reimburse:=v_reimburse_base;v_nonpayable_basis:=null;
    if p.contractor_id is not null then
      v_nonpayable_basis:=cp7_accessory_nonpayable.good_basis_v1(p.contractor_id,r.category_id,l.produced_at);
      if (v_nonpayable_basis->>'nonpayable')::boolean then v_reimburse_base:=0;end if;
    end if;
    insert into erp.fg_accessory_cost_snapshots(
      lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
      good_qty_pcs,qty_per_good_fg_base,hpp_method,
      category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
      reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
    ) values(
      l.id,l.po_id,l.product_id,v_bom,r.id,r.category_id,l.initial_qty_pcs,
      r.qty_per_good_fg_base,r.hpp_method,v_category_avg,v_hpp_base,
      v_reimburse_base,l.produced_at,
      case when v_commit_at=l.produced_at then 'FIRST_FINANCIAL_USE' else 'FG_ACCEPTANCE' end
    ) returning id into v_snapshot;
    if v_nonpayable_basis is not null then
      perform cp7_accessory_nonpayable.capture_basis_v1(v_snapshot,p.contractor_id,v_original_reimburse,v_nonpayable_basis);
    end if;
    if p.contractor_id is null and v_reimburse_base>0 then
      raise exception 'PO % has accessory reimbursement BOM but no mandor/contractor',p.po_number;
    end if;
    if p.contractor_id is not null and v_reimburse_base>0 then
      insert into erp.contractor_accessory_reimbursement_entitlements(
        snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
      ) select
        v_snapshot,p.contractor_id,l.po_id,l.id,l.product_id,r.category_id,
        l.produced_at,total_reimbursement
      from erp.fg_accessory_cost_snapshots where id=v_snapshot;
    end if;
  end loop;
end
$function$
;
CREATE OR REPLACE FUNCTION erp.post_accessory_reimbursement_accrual(p_lot_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  v_hpp numeric(24,6);
  v_reimburse numeric(24,6);
  v_entitlement_total numeric(24,6);
  v_variance numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
  v_contractor uuid;
  v_contractor_count integer;
begin
  perform erp.require_internal();
  perform erp.ensure_fg_accessory_cost_snapshot(p_lot_id);
  select * into l from erp.fg_lots where id=p_lot_id;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select coalesce(sum(total_hpp_cost),0),coalesce(sum(total_reimbursement),0)
  into v_hpp,v_reimburse
  from erp.fg_accessory_cost_snapshots where lot_id=l.id;
  if v_hpp=0 and v_reimburse=0 then return; end if;
  if exists(
    select 1 from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
      and source_id=l.id and status='POSTED'
  ) then return; end if;
  if cp7_accessory_nonpayable.already_recosted_v1(l.id,v_hpp,v_reimburse) then return;end if;
  select count(distinct e.contractor_id),
    (array_agg(distinct e.contractor_id order by e.contractor_id))[1],
    coalesce(sum(e.amount),0)
  into v_contractor_count,v_contractor,v_entitlement_total
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.lot_id=l.id and e.payroll_status<>'CANCELLED';
  if abs(v_entitlement_total-v_reimburse)>0.005 then
    raise exception 'Accessory entitlement total does not match immutable snapshot reimbursement';
  end if;
  if v_reimburse>0 and v_contractor_count<>1 then
    raise exception 'Accessory reimbursement requires exactly one authoritative Mandor';
  end if;
  if v_hpp>0 and v_reimburse=0 then
    v_contractor:=cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(l.id);
  end if;
  if v_hpp>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','WIP','debit',round(v_hpp,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  v_variance:=v_reimburse-v_hpp;
  if v_reimburse=0 and v_contractor is not null then v_variance:=-round(v_hpp,2);end if;
  if v_variance>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',round(v_variance,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  elsif v_variance< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',0,'credit',round(abs(v_variance),2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_reimburse,2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse=0 and v_hpp>0 and v_contractor is null then
    raise exception 'Accessory HPP snapshot has cost but zero Mandor reimbursement; configure reimbursement or use normal material issue flow';
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal(
      'ACCESSORY_REIMBURSE_ACCRUAL',l.id,(l.produced_at AT TIME ZONE 'Asia/Jakarta')::date,
      'Selected accessory HPP + Mandor reimbursement from GOOD rework/FG',v_lines
    );
  end if;
end
$function$
;
CREATE OR REPLACE FUNCTION erp.refresh_accessory_hpp_after_material_recost(p_material_id uuid, p_reason text DEFAULT 'Accessory historical moving-average recost'::text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_category uuid;
  r record;
  v_new numeric(18,6);
  v_changed integer:=0;
  v_po uuid;
  v_rev uuid;v_old numeric;v_newtot numeric;v_d numeric;v_lot uuid;v_lot_po uuid;v_prod uuid;v_lotday date;v_e date;v_date date;
begin
  perform erp.require_internal();
  select accessory_category_id into v_category from erp.materials where id=p_material_id and material_type='ACCESSORY';
  if v_category is null then return 0; end if;
  perform pg_advisory_xact_lock(hashtextextended('ACCESSORY_HPP_CATEGORY|'||v_category::text,0));

  create temporary table if not exists pg_temp.erp_accessory_hpp_changed_pos(po_id uuid primary key) on commit drop;
  truncate pg_temp.erp_accessory_hpp_changed_pos;

  for r in
    select s.id,s.po_id,s.costing_basis_at,s.category_avg_cost_base_snapshot,s.hpp_unit_cost_base_snapshot
    from erp.fg_accessory_cost_snapshots s
    where s.category_id=v_category and s.hpp_method='CATEGORY_MOVING_AVG'
    order by s.costing_basis_at,s.id
    for update
  loop
    v_new:=erp.accessory_category_weighted_avg_cost_at(v_category,r.costing_basis_at);
    if v_new is null then
      raise exception 'Historical accessory recost would remove the valuation basis for FG accessory snapshot %. Correct/reverse the upstream inventory event first.',r.id;
    end if;
    if abs(v_new-r.hpp_unit_cost_base_snapshot)>0.000001 then
      insert into erp.fg_accessory_cost_revisions(snapshot_id,material_id,old_category_avg_cost,new_category_avg_cost,old_hpp_unit_cost,new_hpp_unit_cost,reason,changed_by)
      values(r.id,p_material_id,r.category_avg_cost_base_snapshot,v_new,r.hpp_unit_cost_base_snapshot,v_new,coalesce(nullif(trim(p_reason),''),'Accessory historical moving-average recost'),erp.current_app_user_id())
      returning id into v_rev;
      select total_hpp_cost,lot_id into v_old,v_lot from erp.fg_accessory_cost_snapshots where id=r.id;
      update erp.fg_accessory_cost_snapshots
      set category_avg_cost_base_snapshot=v_new,hpp_unit_cost_base_snapshot=v_new
      where id=r.id;
      -- AZ (independent review of AY rev7): the lot's accessory HPP entered WIP once, with the accrual
      -- (ACCESSORY_REIMBURSE_ACCRUAL: WIP against the Mandor reimbursement and its variance); the PO HPP sync below moves the
      -- change of that HPP out of WIP, so an accrued lot's change enters WIP against the reimbursement variance (the
      -- reimbursement itself is fixed), dated as the sync dates it: the lot day (never before the invoice date, never after
      -- today) on a late invoice with an open date, the invoice date when closed, today otherwise.
      select total_hpp_cost into v_newtot from erp.fg_accessory_cost_snapshots where id=r.id;
      v_d:=coalesce(cp7_accessory_nonpayable.recost_delta_v1(v_lot),round(coalesce(v_newtot,0)-coalesce(v_old,0),2));
      if abs(v_d)>0.005 and (exists(select 1 from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
                                     and source_id=v_lot and status='POSTED')
          or cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(v_lot) is not null) then
        select fl.po_id,fl.product_id,erp._cp3_business_date(fl.produced_at) into v_lot_po,v_prod,v_lotday from erp.fg_lots fl where fl.id=v_lot;
        v_e:=erp.invoice_recost_economic_date_v1();
        v_date:=case when v_e is null then erp._cp3_business_date(statement_timestamp())
                     when exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through) then v_e
                     else least(greatest(v_e,v_lotday),erp._cp3_business_date(statement_timestamp())) end;
        perform erp.post_journal('ACCESSORY_HPP_RECOST',v_rev,v_date,case when exists(select 1 from erp.journal_entries je where je.source_type='ACCESSORY_REIMBURSE_ACCRUAL' and je.source_id=v_lot and je.status='POSTED')
          then 'Accessory HPP recost of an accrued lot: WIP against the reimbursement variance'
          else 'Accessory HPP recost of frozen nonpayable GOOD: WIP against the reimbursement variance' end,
          jsonb_build_array(
            jsonb_build_object('mapping_key','WIP','debit',greatest(v_d,0),'credit',greatest(-v_d,0),'po_id',v_lot_po,'product_id',v_prod),
            jsonb_build_object('mapping_key','ACCESSORY_REIMBURSE_VARIANCE','debit',greatest(-v_d,0),'credit',greatest(v_d,0),'po_id',v_lot_po,'product_id',v_prod)));
      end if;
      insert into pg_temp.erp_accessory_hpp_changed_pos(po_id) values(r.po_id) on conflict do nothing;
      v_changed:=v_changed+1;
    end if;
  end loop;

  for v_po in select po_id from pg_temp.erp_accessory_hpp_changed_pos order by po_id loop
    perform erp.rebuild_po_hpp(v_po,'Accessory moving-average recost: '||coalesce(nullif(trim(p_reason),''),'historical material recost'));
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end loop;
  return v_changed;
end;
$function$
;
CREATE OR REPLACE FUNCTION erp.reverse_rework_completion(p_rework_order_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.rework_orders%rowtype;
  b erp.bs_cases%rowtype;
  x record;
  v_journal uuid;
  v_total numeric(24,6):=0;
  v_remaining integer:=0;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal hasil rework wajib diisi'; end if;
  select * into r from erp.rework_orders where id=p_rework_order_id for update;
  if r.id is null then raise exception 'Rework order tidak ditemukan'; end if;
  if r.status='CANCELLED' and r.cost_posted then return; end if;
  if r.status<>'COMPLETED' or not r.cost_posted then raise exception 'Hanya rework COMPLETED yang sudah diposting biayanya yang dapat direverse'; end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;

  if exists(
    select 1 from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    join erp.rework_component_lines rcl on rcl.id=pwi.source_id
    where pwi.source_type='REWORK' and rcl.rework_order_id=r.id and ps.status<>'REVERSED'
  ) then raise exception 'Upah rework ini sudah masuk payroll. Cancel/reverse payroll aktif terlebih dahulu.'; end if;

  perform erp.be_reverse_rework_target_v1(r.id,p_reason);
  if r.good_fg_lot_id is not null then
    if erp.fg_lot_has_active_downstream(r.good_fg_lot_id,'REWORK_IN','REWORK_ORDER',r.id) then
      raise exception 'FG hasil rework masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.';
    end if;
    if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.lot_id=r.good_fg_lot_id and e.payroll_status<>'UNALLOCATED') then
      raise exception 'Reimbursement aksesori hasil rework sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.';
    end if;
  end if;

  select coalesce(sum(amount_payable),0) into v_total from erp.rework_component_lines where rework_order_id=r.id;
  select id into v_journal from erp.journal_entries where source_type='REWORK_COMPLETION' and source_id=r.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if r.destination_type='CONTRACTOR' and v_total>0.005 and v_journal is null then raise exception 'Jurnal biaya/upah rework tidak ditemukan; reversal dibatalkan agar hutang mandor/HPP tidak rusak'; end if;

  if r.good_fg_lot_id is not null then
    select id into v_journal from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=r.good_fg_lot_id and status='POSTED' order by posting_at desc,id desc limit 1;
    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    for v_journal in select je.id from erp.journal_entries je
      join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id
      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id
      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id=r.good_fg_lot_id
        and exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 np_basis where np_basis.lot_id=sn.lot_id and np_basis.nonpayable)
      order by je.posting_at,je.id
    loop perform erp.reverse_journal(v_journal,p_reason);end loop;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=r.good_fg_lot_id and payroll_status='UNALLOCATED';
    for x in select fm.id from erp.fg_stock_movements fm where fm.lot_id=r.good_fg_lot_id and fm.movement_type='REWORK_IN' and fm.source_type='REWORK_ORDER' and fm.source_id=r.id and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    loop perform erp.reverse_fg_movement(x.id,p_reason); end loop;
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=r.good_fg_lot_id and lot_origin='PRODUCTION';
  end if;

  select id into v_journal from erp.journal_entries where source_type='REWORK_COMPLETION' and source_id=r.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  delete from erp.bs_resolutions where source_rework_order_id=r.id;
  update erp.rework_orders set status='CANCELLED',updated_at=statement_timestamp(),notes=concat_ws(E'\n',notes,'CANCELLED after posted completion reversal: '||p_reason) where id=r.id;

  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  if v_remaining<=0 then update erp.bs_cases set status='RESOLVED',updated_at=statement_timestamp() where id=b.id;
  elsif exists(select 1 from erp.rework_orders ro where ro.bs_case_id=b.id and ro.id<>r.id and ro.status in ('OPEN','IN_PROGRESS','PARTIAL')) then update erp.bs_cases set status='IN_REWORK',updated_at=statement_timestamp() where id=b.id;
  elsif v_remaining<b.qty_pcs then update erp.bs_cases set status='PARTIAL',updated_at=statement_timestamp() where id=b.id;
  else update erp.bs_cases set status='OPEN',updated_at=statement_timestamp() where id=b.id; end if;

  if b.po_id is not null then
    perform erp.rebuild_po_hpp(b.po_id,'Rework completion reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(b.po_id);
    perform erp.sync_po_hpp_to_gl(b.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason) values('rework_orders',r.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$
;
CREATE OR REPLACE FUNCTION erp.save_accessory_issue_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;v_free jsonb;
 v_id uuid;v_version bigint;v_contractor uuid;v_location uuid;v_po uuid;v_at timestamptz;v_reason text;v_items jsonb:='[]'::jsonb;
 h erp.contractor_material_issues%rowtype;
begin
 perform erp.require_permission('finance.contractor_accessory.view');
 if v_action not in('SAVE_DRAFT','POST','DELETE','REVERSE') or v_action is null then raise exception 'Tindakan nota tidak dikenal';end if;
 if v_action in('SAVE_DRAFT','POST','DELETE') then perform erp.require_permission('finance.contractor_accessory.create');end if;
 if v_action='POST' then perform erp.require_permission('finance.contractor_accessory.post');end if;
 if v_action='REVERSE' then perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');end if;
 perform erp.require_internal();
 perform erp._cp3_assert_closed_json_object(p_payload,array['reason'],array['id','expected_version','number','contractor_id','location_id','po_id','physical_at','notes','items','reason'],'accessory issue payload');
 if jsonb_typeof(p_payload->'reason')<>'string' or nullif(btrim(p_payload->>'reason'),'') is null or length(p_payload->>'reason')>1000 then raise exception 'Alasan nota wajib diisi';end if;
 v_reason:=btrim(p_payload->>'reason');v_id:=nullif(p_payload->>'id','')::uuid;
 if p_payload->>'expected_version' is not null and (jsonb_typeof(p_payload->'expected_version')<>'string' or (p_payload->>'expected_version')!~'^[1-9][0-9]{0,18}$') then raise exception 'Versi nota wajib berupa teks bilangan bulat';end if;
 v_version:=(p_payload->>'expected_version')::bigint;
 v_cached:=erp._idempotency_begin('save_accessory_issue_action_v1',p_client_request_id,erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached;end if;
 if v_id is not null then
  select * into h from erp.contractor_material_issues where id=v_id for update;
  if h.id is null then raise exception 'Nota tidak ditemukan';end if;
  if v_version is null or h.row_version<>v_version then raise exception 'STALE_VERSION: nota berubah, muat ulang';end if;
  if exists(select 1 from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id
   join erp.uom_definitions u on u.unit_code=m.unit_code where i.issue_id=v_id and (m.material_type<>'ACCESSORY' or u.dimension<>'COUNT')) then raise exception 'Form ini hanya untuk nota aksesori hitung';end if;
 elsif v_version is not null or v_action in('DELETE','REVERSE') then raise exception 'Identitas dan versi nota tidak cocok';end if;
 if v_action in('SAVE_DRAFT','POST') then
  if v_id is not null and h.status<>'DRAFT' then raise exception 'Nota disahkan tidak dapat diedit';end if;
  if jsonb_typeof(p_payload->'number') is distinct from 'string' or nullif(btrim(p_payload->>'number'),'') is null or length(p_payload->>'number')>60 then raise exception 'Nomor nota wajib diisi';end if;
  if jsonb_typeof(p_payload->'physical_at') is distinct from 'string' or (p_payload->>'physical_at')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$' then raise exception 'Waktu pengambilan wajib memakai tanggal dan jam WIB';end if;
  v_at:=(p_payload->>'physical_at')::timestamptz;
  if (to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00')<>(p_payload->>'physical_at')
   or erp._cp3_business_date(v_at)>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pengambilan tidak valid atau di masa depan';end if;
  v_contractor:=(p_payload->>'contractor_id')::uuid;v_location:=(p_payload->>'location_id')::uuid;v_po:=nullif(p_payload->>'po_id','')::uuid;
  if not exists(select 1 from erp.contractors where id=v_contractor and is_active and contractor_type='MANDOR') then raise exception 'Pilih mandor aktif';end if;
  if not exists(select 1 from erp.locations where id=v_location and is_active and location_type='RAW_MATERIAL_WAREHOUSE') then raise exception 'Pilih gudang bahan aktif';end if;
  if v_po is not null then
   perform 1 from erp.production_orders where id=v_po and contractor_id=v_contractor and status not in('FINISHED','CANCELLED') for update;
   if not found then raise exception 'PO harus aktif dan milik mandor yang sama';end if;
  end if;
  if jsonb_typeof(p_payload->'items') is distinct from 'array' then raise exception 'Rincian aksesori wajib diisi';end if;
  if jsonb_array_length(p_payload->'items') not between 1 and 100 then raise exception 'Isi 1 sampai 100 aksesori';end if;
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x group by x->>'material_id' having count(*)>1) then raise exception 'Aksesori yang sama tidak boleh dua baris';end if;
  for v_line in select value from jsonb_array_elements(p_payload->'items') loop
   perform erp._cp3_assert_closed_json_object(v_line,array['material_id','qty','mode'],array['material_id','qty','mode','manual_price','price_version_id','factor','free_policy_version'],'accessory issue line');
   if jsonb_typeof(v_line->'qty') is distinct from 'string' or (v_line->>'qty')!~'^[1-9][0-9]{0,11}$' then raise exception 'Jumlah aksesori harus PCS utuh positif';end if;
   v_quote:=erp.accessory_issue_quote_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
   if v_quote is null then raise exception 'Aksesori hitung aktif tidak ditemukan';end if;
   if v_line->>'mode'='MANUAL' then
    if jsonb_typeof(v_line->'manual_price') is distinct from 'string' or (v_line->>'manual_price')!~'^[0-9]{1,12}(\.[0-9]{1,2})?$' then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;
    -- BC (M:5023, ERP-DEC02): a price of 0 is free; free is never a way around the note price, only an owner-listed Special category.
    if (v_line->>'manual_price')::numeric=0 then raise exception 'BC_FREE_REQUIRES_POLICY: harga eceran 0 hanya lewat gratis Special yang ditetapkan owner (ERP-DEC02)';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price',v_line->>'manual_price'));
   elsif v_line->>'mode'='MASTER' then
    if v_line->>'manual_price' is not null then raise exception 'Pilih satu dasar harga';end if;
    if v_quote->>'price_version_id' is null or v_line->>'price_version_id' is distinct from v_quote->>'price_version_id'
     or v_line->>'factor' is distinct from v_quote->>'factor' then raise exception 'STALE_PRICE: harga master berubah atau belum tersedia, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty'));
   elsif v_line->>'mode'='FREE' then
    -- BC (ERP-DEC02): only a category on the owner's Special free list, for a Special contractor at the physical time.
    if v_line ? 'manual_price' or v_line ? 'price_version_id' or v_line ? 'factor' then raise exception 'Pilih satu dasar harga';end if;
    perform 1 from erp.bc_policy_settings_v1 where policy_key='ERP_DEC02' for share;
    v_free:=erp.bc_free_basis_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
    if v_free is null then raise exception 'BC_FREE_NOT_ALLOWED: aksesori ini tidak gratis untuk mandor pada tanggal nota (ERP-DEC02 belum ditetapkan atau kategori/mandor tidak termasuk)';end if;
    if v_line->>'free_policy_version' is distinct from v_free->>'policy_version' then raise exception 'STALE_PRICE: daftar kategori gratis berubah, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price','0'));
   else raise exception 'Pilih harga master, eceran per pcs, atau gratis Special';end if;
  end loop;
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'issue_number',btrim(p_payload->>'number'),
   'contractor_id',v_contractor,'location_id',v_location,'po_id',v_po,'physical_at',v_at,'notes',p_payload->>'notes','change_reason',v_reason,'items',v_items),p_client_request_id,v_version);
  v_id:=(v_native->>'contractor_material_issue_id')::uuid;
  -- Native save takes the configured-price locks. Verify the actually selected
  -- versions there, so a concurrent tariff/conversion edit cannot pass preview.
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x
   join erp.contractor_material_issue_items i on i.issue_id=v_id and i.material_id=(x->>'material_id')::uuid
   where x->>'mode'='MASTER' and (i.accessory_price_version_id::text is distinct from x->>'price_version_id'
    or i.base_qty_per_transaction_uom is distinct from (x->>'factor')::numeric)) then
   raise exception 'STALE_PRICE: harga master berubah, muat ulang';end if;
  -- BC (ERP-DEC02): the free lines of this note with the policy version they used.
  delete from erp.bc_free_issue_lines_v1 where issue_id=v_id;
  insert into erp.bc_free_issue_lines_v1(issue_id,material_id,category_id,policy_version)
  select v_id,m.id,m.accessory_category_id,(x->>'free_policy_version')::bigint from jsonb_array_elements(p_payload->'items') x
   join erp.materials m on m.id=(x->>'material_id')::uuid where x->>'mode'='FREE';
  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;
  -- A zero collectible is already settled; use the Native status projection
  -- before committing the same note request, without a payment or new journal.
  perform erp.refresh_contractor_issue_payroll_status(i.id)
    from erp.contractor_material_issue_items i
    where i.issue_id=v_id and erp.bc_note_item_collectible_v1(i.id)<=0
      and i.payroll_status is distinct from 'SETTLED'
    order by i.id;
 elsif v_action='DELETE' then
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'action','DELETE','change_reason',v_reason),p_client_request_id,v_version);
 else v_native:=erp.reverse_contractor_material_issue_v2(v_id,v_reason,p_client_request_id,v_version);
 end if;
 select * into h from erp.contractor_material_issues where id=v_id;
 v_result:=jsonb_build_object('id',v_id,'action',v_action,'request_id',p_client_request_id,'status',case when v_action='DELETE' then 'DELETED' else h.status end,'row_version',h.row_version::text);
 return erp._idempotency_complete('save_accessory_issue_action_v1',p_client_request_id,v_result);
end;$function$
;
-- Prepared owner date-confirmation facade, installed only by its gated stage.
-- Changes no category setting, stock, HPP, journal, payroll or pickup note.
create role cp7_good_policy_date nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;

create table cp7_accessory_nonpayable.date_requests_v1(
  request_id uuid primary key,
  actor_id uuid not null references erp.app_users(id),
  request_body jsonb not null,
  response jsonb not null,
  recorded_at timestamptz not null default statement_timestamp()
);
alter table cp7_accessory_nonpayable.date_requests_v1 owner to postgres;
alter table cp7_accessory_nonpayable.date_requests_v1 enable row level security;
revoke all on cp7_accessory_nonpayable.date_requests_v1 from public,anon,authenticated,service_role,cp7_good_policy_date;
create index date_requests_actor_v1 on cp7_accessory_nonpayable.date_requests_v1(actor_id);
create trigger date_requests_immutable_v1 before update or delete
  on cp7_accessory_nonpayable.date_requests_v1 for each row
  execute function cp7_accessory_nonpayable.immutable_v1();
create trigger date_requests_no_truncate_v1 before truncate
  on cp7_accessory_nonpayable.date_requests_v1 for each statement
  execute function cp7_accessory_nonpayable.immutable_v1();

create function cp7_accessory_nonpayable.settings_access_v1(p_write boolean)
returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare access_value jsonb;profile_id uuid;role_code text;can_write boolean;
begin
  if current_setting('transaction_isolation')<>'read committed' then
    raise exception 'NONPAYABLE_FRESH_ACCESS_REQUIRED';
  end if;
  if auth.uid() is null or coalesce(auth.jwt()->>'role','') is distinct from 'authenticated' then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_DENIED';
  end if;
  access_value:=erp.get_my_access_v1();
  role_code:=access_value->'profile'->>'role_code';
  profile_id:=erp.current_app_user_id();
  if access_value->'allowed' is distinct from 'true'::jsonb or role_code not in('OWNER','ADMIN')
     or role_code is null or profile_id is null
     or access_value->'profile'->>'id' is distinct from profile_id::text
     or access_value->'profile'->>'row_version' is null
     or access_value->'profile'->>'role_row_version' is null
     or not erp.has_permission('settings.erp.view') or not erp.has_permission('warehouse.accessory.view') then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_DENIED';
  end if;
  can_write:=role_code='OWNER' and erp.has_permission('settings.erp.manage');
  if p_write and not can_write then
    raise exception using errcode='42501',message='NONPAYABLE_OWNER_DATE_REQUIRED';
  end if;
  return jsonb_build_object('actor',profile_id,'can_write',can_write,
    'epoch',encode(sha256(convert_to(jsonb_build_object('auth_user_id',auth.uid(),
      'profile',access_value->'profile','permissions',access_value->'permissions')::text,'UTF8')),'hex'));
end;$$;

create function cp7_accessory_nonpayable.settings_event_v1(p_event uuid)
returns jsonb language sql stable security definer set search_path='' as $$
  select jsonb_build_object('id',e.id,'version',e.version::text,'status',e.status,
    'recorded_at',to_char(e.set_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'reason',e.reason,'categories',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'name',c.category_name)
      order by c.id) from jsonb_array_elements_text(coalesce(e.value->'special_free_category_ids','[]'::jsonb)) x(id)
      left join erp.accessory_categories c on c.id=x.id::uuid),'[]'::jsonb))
  from erp.bc_policy_setting_events_v1 e where e.id=p_event and e.policy_key='ERP_DEC02'
$$;

create function cp7_accessory_nonpayable.settings_workspace_v1(p_payload jsonb)
returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare
  access_value jsonb;source_row erp.bc_policy_settings_v1%rowtype;
  current_event erp.bc_policy_setting_events_v1%rowtype;
  before_version bigint;before_day date;events jsonb;versions jsonb;
  events_more boolean;versions_more boolean;
begin
  access_value:=cp7_accessory_nonpayable.settings_access_v1(false);
  if jsonb_typeof(p_payload) is distinct from 'object' or not p_payload?&array['before_version','before_date']
     or (select count(*) from jsonb_object_keys(p_payload))<>2 then
    raise exception 'NONPAYABLE_SETTINGS_READ_FIELDS';
  end if;
  if p_payload->'before_version' is distinct from 'null'::jsonb then
    if jsonb_typeof(p_payload->'before_version') is distinct from 'string'
       or p_payload->>'before_version'!~'^[1-9][0-9]{0,18}$' then
      raise exception 'NONPAYABLE_SOURCE_CURSOR_REQUIRED';
    end if;
    before_version:=(p_payload->>'before_version')::bigint;
  end if;
  if p_payload->'before_date' is distinct from 'null'::jsonb then
    if jsonb_typeof(p_payload->'before_date') is distinct from 'string'
       or p_payload->>'before_date'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
      raise exception 'NONPAYABLE_DATE_CURSOR_REQUIRED';
    end if;
    before_day:=(p_payload->>'before_date')::date;
    if not isfinite(before_day) then raise exception 'NONPAYABLE_FINITE_DATE_REQUIRED';end if;
  end if;
  select * into source_row from erp.bc_policy_settings_v1 s where s.policy_key='ERP_DEC02' for share;
  if not found then raise exception 'NONPAYABLE_ERP_DEC02_SOURCE_REQUIRED';end if;
  perform pg_advisory_xact_lock_shared(hashtextextended('CP7_NONPAYABLE_CATEGORY_TIMELINE',0));
  access_value:=cp7_accessory_nonpayable.settings_access_v1(false);
  select * into current_event from erp.bc_policy_setting_events_v1 e
    where e.policy_key='ERP_DEC02' and e.version=source_row.version;
  if current_event.id is null or current_event.status<>source_row.status
     or current_event.value is distinct from source_row.value then
    raise exception 'NONPAYABLE_EXACT_CURRENT_SOURCE_EVENT_REQUIRED';
  end if;
  select coalesce(jsonb_agg(cp7_accessory_nonpayable.settings_event_v1(e.id) order by e.version desc),'[]'::jsonb)
    into events from(select se.id,se.version from erp.bc_policy_setting_events_v1 se where se.policy_key='ERP_DEC02'
      and(before_version is null or se.version<before_version) order by se.version desc limit 31)e;
  events_more:=jsonb_array_length(events)>30;
  if events_more then events:=events-30;end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',v.id,'effective_from',to_char(v.effective_from,'YYYY-MM-DD'),
      'source_event',cp7_accessory_nonpayable.settings_event_v1(v.source_event_id),'reason',v.reason,
      'recorded_at',to_char(v.recorded_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))
      order by v.effective_from desc),'[]'::jsonb)
    into versions from(select cv.* from cp7_accessory_nonpayable.category_versions_v1 cv
      where before_day is null or cv.effective_from<before_day order by cv.effective_from desc limit 31)v;
  versions_more:=jsonb_array_length(versions)>30;
  if versions_more then versions:=versions-30;end if;
  return jsonb_build_object('contract_version','cp7.good-policy-date-workspace.v1',
    'actor',access_value->'actor','access_epoch',access_value->'epoch','can_write',access_value->'can_write',
    'timeline_token',cp7_accessory_nonpayable.timeline_token_v1(),
    'current_source',cp7_accessory_nonpayable.settings_event_v1(current_event.id),
    'current_source_registered',exists(select 1 from cp7_accessory_nonpayable.category_versions_v1 cv where cv.source_version=source_row.version),
    'source_events',events,'source_has_more',events_more,
    'next_source_before',case when events_more then events->-1->>'version' else null end,
    'versions',versions,'version_has_more',versions_more,
    'next_version_before',case when versions_more then versions->-1->>'effective_from' else null end);
end;$$;

create function cp7_accessory_nonpayable.settings_save_v1(p_payload jsonb,p_request uuid,p_cancel boolean)
returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare
  access_value jsonb;fresh_access jsonb;previous cp7_accessory_nonpayable.date_requests_v1%rowtype;
  source_version bigint;effective_day date;source_event uuid;reason_text text;made jsonb;reply_value jsonb;
begin
  access_value:=cp7_accessory_nonpayable.settings_access_v1(true);
  if p_request is null or p_cancel is null or jsonb_typeof(p_payload) is distinct from 'object'
     or not p_payload?&array['contract_version','actor','access_epoch','effective_from','source_event_id',
       'expected_current_version','expected_timeline','reason','reviewed']
     or (select count(*) from jsonb_object_keys(p_payload))<>9
     or p_payload->>'contract_version' is distinct from 'cp7.good-policy-date-command.v1'
     or p_payload->'reviewed' is distinct from 'true'::jsonb
     or p_payload->>'actor' is distinct from access_value->>'actor' then
    raise exception 'NONPAYABLE_DATE_COMMAND_REVIEW_REQUIRED';
  end if;
  if jsonb_typeof(p_payload->'source_event_id') is distinct from 'string'
     or p_payload->>'source_event_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
     or jsonb_typeof(p_payload->'effective_from') is distinct from 'string'
     or p_payload->>'effective_from'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     or jsonb_typeof(p_payload->'expected_current_version') is distinct from 'string'
     or p_payload->>'expected_current_version'!~'^[1-9][0-9]{0,18}$'
     or jsonb_typeof(p_payload->'expected_timeline') is distinct from 'string'
     or p_payload->>'expected_timeline'!~'^[0-9a-f]{64}$'
     or jsonb_typeof(p_payload->'access_epoch') is distinct from 'string'
     or p_payload->>'access_epoch'!~'^[0-9a-f]{64}$'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'NONPAYABLE_DATE_COMMAND_FIELDS';
  end if;
  source_event:=(p_payload->>'source_event_id')::uuid;
  effective_day:=(p_payload->>'effective_from')::date;
  reason_text:=p_payload->>'reason';
  if not isfinite(effective_day) or length(btrim(reason_text)) not between 1 and 1000
     or btrim(reason_text)<>reason_text then raise exception 'NONPAYABLE_DATE_AND_REASON_REQUIRED';end if;
  -- Use the same outer financial lock order as GOOD and the existing Native
  -- policy writers, then the BC row and the private timeline lock.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select s.version into source_version from erp.bc_policy_settings_v1 s where s.policy_key='ERP_DEC02' for share;
  if not found then raise exception 'NONPAYABLE_ERP_DEC02_SOURCE_REQUIRED';end if;
  perform pg_advisory_xact_lock(hashtextextended('CP7_NONPAYABLE_CATEGORY_TIMELINE',0));
  fresh_access:=cp7_accessory_nonpayable.settings_access_v1(true);
  if fresh_access is distinct from access_value then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_ACCESS_CHANGED';
  end if;
  select * into previous from cp7_accessory_nonpayable.date_requests_v1 r where r.request_id=p_request;
  if previous.request_id is not null then
    if previous.actor_id::text is distinct from access_value->>'actor' or previous.request_body is distinct from p_payload then
      raise exception 'NONPAYABLE_DATE_REQUEST_INTENT_CHANGED';
    end if;
    return previous.response;
  end if;
  -- A lost reply must not trap the owner behind an unconfirmable request.
  -- Cancel only an absent request under the same locks, storing an immutable
  -- tombstone. A late arrival replays CANCELLED. If already SAVED, the stored
  -- success above is returned; an effective policy is never silently undone.
  if p_cancel then
    reply_value:=jsonb_build_object('contract_version','cp7.good-policy-date-outcome.v1',
      'request_id',p_request,'actor',access_value->'actor','effective_from',p_payload->'effective_from',
      'id',null,'source_event_id',p_payload->'source_event_id','source_version',null,
      'reason',reason_text,'status','CANCELLED');
    insert into cp7_accessory_nonpayable.date_requests_v1(request_id,actor_id,request_body,response)
      values(p_request,(access_value->>'actor')::uuid,p_payload,reply_value);
    return reply_value;
  end if;
  if p_payload->>'access_epoch' is distinct from access_value->>'epoch' then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_ACCESS_CHANGED';
  end if;
  if p_payload->>'expected_current_version' is distinct from source_version::text then
    raise exception 'NONPAYABLE_CURRENT_SOURCE_STALE: kategori berubah; baca ulang';
  end if;
  made:=cp7_accessory_nonpayable.record_version_v1(effective_day,source_event,p_request,
    p_payload->>'expected_timeline',reason_text);
  reply_value:=jsonb_build_object('contract_version','cp7.good-policy-date-outcome.v1',
    'request_id',p_request,'actor',access_value->'actor','effective_from',made->'effective_from',
    'id',made->'id','source_event_id',made->'source_event_id','source_version',made->'source_version',
    'reason',reason_text,'status','SAVED');
  insert into cp7_accessory_nonpayable.date_requests_v1(request_id,actor_id,request_body,response)
    values(p_request,(access_value->>'actor')::uuid,p_payload,reply_value);
  return reply_value;
end;$$;

create function public.erp_cp7_get_good_policy_dates_v1(p_payload jsonb)
returns jsonb language sql volatile security definer set search_path='' as $$
  select cp7_accessory_nonpayable.settings_workspace_v1(p_payload)
$$;
create function public.erp_cp7_save_good_policy_date_v1(p_payload jsonb,p_request uuid,p_cancel boolean default false)
returns jsonb language sql volatile security definer set search_path='' as $$
  select cp7_accessory_nonpayable.settings_save_v1(p_payload,p_request,p_cancel)
$$;

alter function cp7_accessory_nonpayable.settings_access_v1(boolean) owner to postgres;
alter function cp7_accessory_nonpayable.settings_event_v1(uuid) owner to postgres;
alter function cp7_accessory_nonpayable.settings_workspace_v1(jsonb) owner to postgres;
alter function cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean) owner to postgres;
-- Normalize only these six newly created functions while postgres still owns
-- them. Schema/global default EXECUTE grants and PUBLIC must not survive the
-- later owner transfer; no default privilege or existing routine is changed.
do $settings_new_acl$declare item_ record;grantee_ text;begin
 for item_ in select p.oid::regprocedure::text signature,x.grantee
  from pg_proc p cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))x
  where p.oid in(
   'cp7_accessory_nonpayable.settings_access_v1(boolean)'::regprocedure,
   'cp7_accessory_nonpayable.settings_event_v1(uuid)'::regprocedure,
   'cp7_accessory_nonpayable.settings_workspace_v1(jsonb)'::regprocedure,
   'cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean)'::regprocedure,
   'public.erp_cp7_get_good_policy_dates_v1(jsonb)'::regprocedure,
   'public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean)'::regprocedure)
   and x.grantee<>p.proowner loop
  grantee_:=case when item_.grantee=0 then'PUBLIC'else quote_ident(pg_get_userbyid(item_.grantee))end;
  execute format('revoke all on function %s from %s',item_.signature,grantee_);
 end loop;
end $settings_new_acl$;
grant usage on schema cp7_accessory_nonpayable to cp7_good_policy_date;
grant execute on function cp7_accessory_nonpayable.settings_workspace_v1(jsonb),
  cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean) to cp7_good_policy_date;
grant execute on function public.erp_cp7_get_good_policy_dates_v1(jsonb),
  public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean) to authenticated;

-- The gated installer verifies public's raw ACL is explicit and restored.
-- PostgreSQL 17 gives a non-superuser creator ADMIN, but no SET option.
-- Ownership transfer needs SET temporarily; all ACL work above uses the actual
-- creator/owner before that authority is relinquished.
grant cp7_good_policy_date to postgres with admin false, inherit false, set true;
grant create on schema public to cp7_good_policy_date;
alter function public.erp_cp7_get_good_policy_dates_v1(jsonb) owner to cp7_good_policy_date;
alter function public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean) owner to cp7_good_policy_date;
revoke create on schema public from cp7_good_policy_date;
revoke cp7_good_policy_date from postgres granted by postgres;
