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
