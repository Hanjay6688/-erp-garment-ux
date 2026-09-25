-- CP6 BB production part (ALL-W02, ALL-W04, ALL-W06). New objects only; the existing opening WIP functions are changed by
-- checked substitutions in scripts/cp6_bb_build.py.
-- W04: cut pieces waiting for pickup at cutover are an opening WIP of stage CUTTING held at a cutting location (no mandor
--      yet). PICKUP hands all of them to one active mandor (stage SEWING from the pickup date; the PO takes that mandor when
--      it has none, like a native cutting pickup); nothing is completed, split or reworked before it. REVERSE_PICKUP only
--      while no output, split or posted work of that mandor on the PO exists.
-- W02: pieces of an opening WIP found BS after cutover are split off as a native BS case (LEGACY/UNKNOWN like opening BS,
--      legacy_reference OPENING_SPLIT:<split>, detected at QC, holder recorded) through the same checks as a completion
--      (dated remaining, product binding). Their value stays in WIP at the source's per-piece value until the native BS
--      flow disposes them (WIP -> OTHER_EXPENSE, like opening BS) or reworks them GOOD (the lot carries that value).
--      REVERSE_SPLIT only while the case has no resolution (a claim resolves through one), rework or hold. Wages after cutover are native work
--      completions on the opening PO (proved by the probe; no BB object).
-- W06: a rework sent before cutover and still out is imported (OPENING_REWORK + OPENING_REWORK_COMPONENT) as a native rework
--      order of its open quantity on the BS case of its opening BS row, created by erp.save_rework_order_v2 at FINALIZE; the
--      component baseline (pieces whose component was already done before BS) and the rate are stated and checked against
--      the native rate. Completion, GOOD lot, wages and reversal are native (COMPLETE_REWORK). History before cutover (sent,
--      returned) is kept on the import record only (M:369).

alter table erp.initial_import_production_sources drop constraint initial_import_production_sources_stage_check;
alter table erp.initial_import_production_sources add constraint initial_import_production_sources_stage_check
  check(stage=any(array['CUTTING','SEWING','LAUNDRY','QC']));

create table erp.bb_wip_pickups_v1(
  id uuid primary key default gen_random_uuid(),
  opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
  contractor_id uuid not null references erp.contractors(id),
  physical_at timestamptz not null,
  reason text not null check(btrim(reason)<>''),
  po_contractor_assigned boolean not null,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_at timestamptz,
  reversed_by uuid,
  reverse_reason text,
  check((reversed_at is null)=(reverse_reason is null))
);
create unique index bb_wip_pickups_v1_active on erp.bb_wip_pickups_v1(opening_item_id) where reversed_at is null;
comment on table erp.bb_wip_pickups_v1 is 'BB (ALL-W04): pickup of opening CUTTING WIP by one mandor; reversal keeps the row.';
alter table erp.bb_wip_pickups_v1 enable row level security;
revoke all on erp.bb_wip_pickups_v1 from public,anon,authenticated,service_role;

create table erp.bb_wip_bs_splits_v1(
  id uuid primary key,
  opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
  bs_case_id uuid not null unique references erp.bs_cases(id),
  product_id uuid not null references erp.products(id),
  qty_pcs integer not null check(qty_pcs>0),
  stage_from text not null check(stage_from in('SEWING','LAUNDRY')),
  holder_contractor_id uuid references erp.contractors(id),
  holder_vendor_id uuid references erp.laundry_vendors(id),
  basis text not null,
  physical_at timestamptz not null,
  reason text not null check(btrim(reason)<>''),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_at timestamptz,
  reversed_by uuid,
  reverse_reason text,
  check((reversed_at is null)=(reverse_reason is null))
);
create index bb_wip_bs_splits_v1_item on erp.bb_wip_bs_splits_v1(opening_item_id);
comment on table erp.bb_wip_bs_splits_v1 is 'BB (ALL-W02): pieces of an opening WIP split off as a native BS case; value stays at the source per-piece value.';
alter table erp.bb_wip_bs_splits_v1 enable row level security;
revoke all on erp.bb_wip_bs_splits_v1 from public,anon,authenticated,service_role;

create table erp.bb_wip_split_value_events_v1(
  id uuid primary key,
  split_id uuid not null references erp.bb_wip_bs_splits_v1(id),
  disposed_qty integer not null check(disposed_qty>=0),
  previous_amount numeric(20,2) not null,
  target_amount numeric(20,2) not null,
  economic_date date not null,
  journal_entry_id uuid not null references erp.journal_entries(id),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp()
);
create index bb_wip_split_value_events_v1_split on erp.bb_wip_split_value_events_v1(split_id);
comment on table erp.bb_wip_split_value_events_v1 is 'BB (ALL-W02): WIP value of disposed split BS pieces moved to OTHER_EXPENSE (journal source INITIAL_IMPORT_BS_VALUE, like opening BS).';
alter table erp.bb_wip_split_value_events_v1 enable row level security;
revoke all on erp.bb_wip_split_value_events_v1 from public,anon,authenticated,service_role;

create table erp.bb_opening_reworks_v1(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  rework_order_id uuid not null unique references erp.rework_orders(id),
  bs_case_id uuid not null references erp.bs_cases(id),
  opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
  legacy_rework_number text not null,
  legacy_sent_date date not null,
  qty_sent_original integer not null check(qty_sent_original>0),
  qty_returned_before_cutover integer not null check(qty_returned_before_cutover>=0),
  qty_open integer not null check(qty_open>0),
  components jsonb not null,
  created_at timestamptz not null default statement_timestamp(),
  check(qty_open=qty_sent_original-qty_returned_before_cutover)
);
comment on table erp.bb_opening_reworks_v1 is 'BB (ALL-W06): import record of a rework open at cutover and the native rework order made for its open quantity.';
alter table erp.bb_opening_reworks_v1 enable row level security;
revoke all on erp.bb_opening_reworks_v1 from public,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION erp.bb_guard_wip_history_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO ''
AS $function$
begin
  -- Pickups and splits are history: only their reversal is written, once.
  if TG_OP='DELETE' then raise exception 'BB_WIP_HISTORY_IMMUTABLE: riwayat pickup/pisah BS tidak boleh dihapus';end if;
  if old.reversed_at is not null or new.reversed_at is null
     or (to_jsonb(new)-'reversed_at'-'reversed_by'-'reverse_reason') is distinct from (to_jsonb(old)-'reversed_at'-'reversed_by'-'reverse_reason') then
    raise exception 'BB_WIP_HISTORY_IMMUTABLE: riwayat pickup/pisah BS hanya boleh dibalik sekali';
  end if;
  return new;
end;$function$;
create trigger bb_wip_pickups_v1_immutable before update or delete on erp.bb_wip_pickups_v1 for each row execute function erp.bb_guard_wip_history_v1();
create trigger bb_wip_bs_splits_v1_immutable before update or delete on erp.bb_wip_bs_splits_v1 for each row execute function erp.bb_guard_wip_history_v1();

CREATE OR REPLACE FUNCTION erp.bb_guard_append_only_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO ''
AS $function$
begin
  raise exception 'BB_APPEND_ONLY: % tidak boleh diubah atau dihapus',TG_TABLE_NAME;
end;$function$;
create trigger bb_wip_split_value_events_v1_immutable before update or delete on erp.bb_wip_split_value_events_v1 for each row execute function erp.bb_guard_append_only_v1();
create trigger bb_opening_reworks_v1_immutable before update or delete on erp.bb_opening_reworks_v1 for each row execute function erp.bb_guard_append_only_v1();

-- ---------------------------------------------------------------- stage, holder and split quantities of an opening WIP

CREATE OR REPLACE FUNCTION erp.bb_wip_active_pickup_v1(p_item uuid)
 RETURNS erp.bb_wip_pickups_v1 LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select p.* from erp.bb_wip_pickups_v1 p where p.opening_item_id=p_item and p.reversed_at is null $function$;

CREATE OR REPLACE FUNCTION erp.bb_wip_stage_v1(p_item uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case when s.stage='CUTTING' and exists(select 1 from erp.bb_wip_pickups_v1 p where p.opening_item_id=s.opening_item_id
    and p.reversed_at is null) then 'SEWING' else s.stage end
  from erp.initial_import_production_sources s where s.opening_item_id=p_item
$function$;

CREATE OR REPLACE FUNCTION erp.bb_wip_holder_v1(p_item uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce((select p.contractor_id from erp.bb_wip_pickups_v1 p where p.opening_item_id=i.id and p.reversed_at is null),i.contractor_id)
  from erp.opening_balance_items i where i.id=p_item
$function$;

CREATE OR REPLACE FUNCTION erp.bb_wip_split_active_qty_v1(p_item uuid)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(qty_pcs),0)::integer from erp.bb_wip_bs_splits_v1 where opening_item_id=p_item and reversed_at is null $function$;

-- Pieces split off on or before a day, less the splits reversed on or before it (the A3 dated remaining counts both).
CREATE OR REPLACE FUNCTION erp.bb_wip_split_net_asof_v1(p_item uuid,p_day date)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select (coalesce(sum(qty_pcs) filter(where erp._cp3_business_date(physical_at)<=p_day),0)
    -coalesce(sum(qty_pcs) filter(where reversed_at is not null and erp._cp3_business_date(reversed_at)<=p_day),0))::integer
  from erp.bb_wip_bs_splits_v1 where opening_item_id=p_item
$function$;

CREATE OR REPLACE FUNCTION erp.bb_wip_split_days_v1(p_item uuid)
 RETURNS SETOF date LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select erp._cp3_business_date(physical_at) from erp.bb_wip_bs_splits_v1 where opening_item_id=p_item
  union select erp._cp3_business_date(reversed_at) from erp.bb_wip_bs_splits_v1 where opening_item_id=p_item and reversed_at is not null
$function$;

-- The earliest instant an output or split of a day may take: after the active pickup and after that day's split reversals
-- (BA A3 already places it after that day's output reversals).
CREATE OR REPLACE FUNCTION erp.bb_wip_min_output_at_v1(p_item uuid,p_day date)
 RETURNS timestamptz LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select greatest((select p.physical_at+interval '1 microsecond' from erp.bb_wip_pickups_v1 p where p.opening_item_id=p_item and p.reversed_at is null),
    (select max(x.reversed_at)+interval '1 microsecond' from erp.bb_wip_bs_splits_v1 x where x.opening_item_id=p_item
      and x.reversed_at is not null and erp._cp3_business_date(x.reversed_at)=p_day))
$function$;

CREATE OR REPLACE FUNCTION erp.bb_assert_wip_ready_v1(p_item uuid,p_day date)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_stage text;p erp.bb_wip_pickups_v1%rowtype;
begin
  select stage into v_stage from erp.initial_import_production_sources where opening_item_id=p_item;
  if v_stage='CUTTING' then
    select * into p from erp.bb_wip_pickups_v1 where opening_item_id=p_item and reversed_at is null;
    if p.id is null or erp._cp3_business_date(p.physical_at)>p_day then
      raise exception 'BB_WIP_NOT_PICKED_UP: potongan ini masih menunggu pickup pada tanggal itu; catat pickup ke mandor dahulu';
    end if;
  end if;
end;$function$;

-- A PO's mandor is bound once pickup, issue, work, payroll, snapshot, reimbursement, rework or an opening output uses it
-- (the native guard's conditions, which a SECURITY DEFINER writer bypasses, plus the opening WIP's own facts).
CREATE OR REPLACE FUNCTION erp.bb_po_contractor_used_v1(p_po uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.cutting_groups cg where cg.po_id=p_po and (cg.picked_up_at is not null or cg.material_issue_posted or cg.status<>'CUT'))
    or exists(select 1 from erp.contractor_material_issues i where i.po_id=p_po and i.status<>'DRAFT')
    or exists(select 1 from erp.work_completion_events w where w.po_id=p_po and w.status<>'DRAFT')
    or exists(select 1 from erp.payroll_work_items pwi where pwi.po_id=p_po and exists(select 1 from erp.payroll_settlements ps where ps.id=pwi.payroll_id and ps.status<>'REVERSED'))
    or exists(select 1 from erp.po_work_component_snapshots s where s.po_id=p_po)
    or exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.po_id=p_po and e.payroll_status<>'CANCELLED')
    or exists(select 1 from erp.rework_orders r join erp.bs_cases b on b.id=r.bs_case_id where b.po_id=p_po and r.status<>'CANCELLED')
    or exists(select 1 from erp.fg_lots f where f.po_id=p_po and f.lot_origin='PRODUCTION')
    or exists(select 1 from erp.bb_wip_pickups_v1 p join erp.initial_import_production_sources s on s.opening_item_id=p.opening_item_id
      where s.po_id=p_po and p.reversed_at is null)
$function$;

-- ---------------------------------------------------------------- PICKUP, REVERSE_PICKUP, REVERSE_SPLIT

CREATE OR REPLACE FUNCTION erp.bb_manage_opening_wip_v1(p_payload jsonb,p_item uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare v_op text:=upper(coalesce(nullif(btrim(p_payload->>'operation'),''),''));v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  s erp.initial_import_production_sources%rowtype;i erp.opening_balance_items%rowtype;p erp.bb_wip_pickups_v1%rowtype;
  x erp.bb_wip_bs_splits_v1%rowtype;v_contractor uuid;v_po_contractor uuid;v_date date;v_at timestamptz;v_cutover date;
  v_last date;v_assigned boolean:=false;v_case erp.bs_cases%rowtype;
begin
  select * into strict s from erp.initial_import_production_sources where opening_item_id=p_item for update;
  select * into strict i from erp.opening_balance_items where id=p_item;
  select opening_date into strict v_cutover from erp.opening_balance_headers where id=i.opening_id;
  if v_op='PICKUP' then
    if s.stage<>'CUTTING' then raise exception 'BB_WIP_PICKUP_NOT_CUTTING: hanya potongan yang menunggu pickup yang dapat di-pickup';end if;
    if exists(select 1 from erp.bb_wip_pickups_v1 where opening_item_id=s.opening_item_id and reversed_at is null) then
      raise exception 'BB_WIP_ALREADY_PICKED_UP: potongan ini sudah di-pickup';end if;
    select c.id into v_contractor from erp.contractors c where c.contractor_code=p_payload->>'contractor_code' and c.is_active and c.contractor_type='MANDOR';
    if v_contractor is null then raise exception 'BB_WIP_PICKUP_MANDOR: pilih mandor aktif';end if;
    if coalesce(p_payload->>'date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or (p_payload->>'date')::date::text<>p_payload->>'date' then
      raise exception 'date: gunakan YYYY-MM-DD';end if;
    v_date:=(p_payload->>'date')::date;
    select max(erp._cp3_business_date(reversed_at)) into v_last from erp.bb_wip_pickups_v1 where opening_item_id=s.opening_item_id;
    if v_date<greatest(v_cutover,coalesce(v_last,v_cutover)) or v_date>erp._cp3_business_date(statement_timestamp()) then
      raise exception 'BB_WIP_PICKUP_DATE: tanggal pickup harus sejak cutover (dan sejak pickup terakhir dibatalkan) dan tidak di masa depan';
    end if;
    -- Pieces are handed over at the start of the pickup day, never before a return of that day.
    v_at:=greatest(v_date::timestamp at time zone 'Asia/Jakarta',
      (select max(reversed_at)+interval '1 microsecond' from erp.bb_wip_pickups_v1 where opening_item_id=s.opening_item_id));
    select contractor_id into v_po_contractor from erp.production_orders where id=s.po_id for update;
    if v_po_contractor is not null and v_po_contractor<>v_contractor then
      raise exception 'BB_WIP_PO_OTHER_MANDOR: PO ini sudah milik mandor lain; pickup harus oleh mandor PO';end if;
    if v_po_contractor is null then
      update erp.production_orders set contractor_id=v_contractor,updated_at=clock_timestamp() where id=s.po_id;
      v_assigned:=true;
    end if;
    insert into erp.bb_wip_pickups_v1(opening_item_id,contractor_id,physical_at,reason,po_contractor_assigned,created_by)
    values(s.opening_item_id,v_contractor,v_at,v_reason,v_assigned,erp.current_app_user_id()) returning * into p;
    insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
    values(s.po_id,'CUTTING','SEWING',s.qty_pcs,v_contractor,'BB_OPENING_WIP_PICKUP',p.id,v_at,erp.current_app_user_id(),v_reason);
    return jsonb_build_object('operation',v_op,'pickup_id',p.id,'po_contractor_assigned',v_assigned);
  elsif v_op='REVERSE_PICKUP' then
    select * into p from erp.bb_wip_pickups_v1 where opening_item_id=s.opening_item_id and reversed_at is null for update;
    if p.id is null then raise exception 'BB_WIP_PICKUP_NOT_FOUND: tidak ada pickup aktif';end if;
    if exists(select 1 from erp.initial_import_wip_outputs o where o.opening_item_id=s.opening_item_id
        and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id))
       or exists(select 1 from erp.bb_wip_bs_splits_v1 where opening_item_id=s.opening_item_id and reversed_at is null)
       or exists(select 1 from erp.work_completion_events w where w.po_id=s.po_id and w.contractor_id=p.contractor_id
         and w.status<>'DRAFT' and w.physical_at>=p.physical_at) then
      raise exception 'BB_WIP_PICKUP_HAS_DOWNSTREAM: batalkan hasil, pisah BS, dan upah mandor sesudah pickup dahulu';
    end if;
    v_at:=statement_timestamp();
    update erp.bb_wip_pickups_v1 set reversed_at=v_at,reversed_by=erp.current_app_user_id(),reverse_reason=v_reason where id=p.id;
    insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
    values(s.po_id,'SEWING','CUTTING',s.qty_pcs,p.contractor_id,'BB_OPENING_WIP_PICKUP_REVERSE',p.id,v_at,erp.current_app_user_id(),v_reason);
    if p.po_contractor_assigned and not erp.bb_po_contractor_used_v1(s.po_id) then
      update erp.production_orders set contractor_id=null,updated_at=clock_timestamp() where id=s.po_id and contractor_id=p.contractor_id;
    end if;
    return jsonb_build_object('operation',v_op,'pickup_id',p.id,
      'po_contractor_released',p.po_contractor_assigned and (select contractor_id is null from erp.production_orders where id=s.po_id));
  elsif v_op='REVERSE_SPLIT' then
    select * into x from erp.bb_wip_bs_splits_v1 where id=nullif(p_payload->>'split_id','')::uuid and opening_item_id=s.opening_item_id
      and reversed_at is null for update;
    if x.id is null then raise exception 'BB_WIP_SPLIT_NOT_FOUND: pisah BS tidak ditemukan atau sudah dibatalkan';end if;
    select * into v_case from erp.bs_cases where id=x.bs_case_id for update;
    if v_case.status<>'OPEN' or exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id)
       or exists(select 1 from erp.rework_orders where bs_case_id=v_case.id)
       or exists(select 1 from erp.bs_case_hold_events where bs_case_id=v_case.id) then
      raise exception 'BB_WIP_SPLIT_HAS_DOWNSTREAM: kasus BS ini sudah diproses; batalkan penyelesaian (termasuk klaim), rework, atau hold-nya dahulu';
    end if;
    v_at:=statement_timestamp();
    update erp.bs_cases set status='CANCELLED',notes=concat_ws(E'\n',notes,'Pisah BS saldo awal dibatalkan: '||v_reason),updated_at=clock_timestamp()
      where id=v_case.id;
    update erp.bb_wip_bs_splits_v1 set reversed_at=v_at,reversed_by=erp.current_app_user_id(),reverse_reason=v_reason where id=x.id;
    insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
    values(s.po_id,'QC',x.stage_from,x.qty_pcs,x.holder_contractor_id,'BB_OPENING_WIP_SPLIT_BS_REVERSE',x.id,v_at,erp.current_app_user_id(),v_reason);
    return jsonb_build_object('operation',v_op,'split_id',x.id,'bs_case_id',x.bs_case_id);
  end if;
  raise exception 'Aksi hasil WIP tidak dikenal';
end;$function$;

-- The BS case of a split, written by erp.complete_initial_import_wip_v1 (SPLIT_BS) after the completion checks.
CREATE OR REPLACE FUNCTION erp.bb_split_opening_wip_bs_v1(p_item uuid,p_product uuid,p_qty integer,p_at timestamptz,p_basis text,p_reason text)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.initial_import_production_sources%rowtype;i erp.opening_balance_items%rowtype;v_stage text;v_contractor uuid;v_vendor uuid;
  v_split uuid:=gen_random_uuid();v_case uuid;
begin
  select * into strict s from erp.initial_import_production_sources where opening_item_id=p_item;
  select * into strict i from erp.opening_balance_items where id=p_item;
  v_stage:=erp.bb_wip_stage_v1(p_item);
  if v_stage not in('SEWING','LAUNDRY') then raise exception 'BB_WIP_NOT_PICKED_UP: potongan ini masih menunggu pickup';end if;
  if v_stage='SEWING' then v_contractor:=erp.bb_wip_holder_v1(p_item);else v_vendor:=i.vendor_id;end if;
  insert into erp.bs_cases(bs_number,po_id,product_id,detected_at_stage,cause_source,untracked_type,responsible_contractor_id,responsible_vendor_id,
    qty_pcs,status,physical_at,notes,legacy_reference)
  values('OWBS-'||v_split::text,s.po_id,p_product,'QC','UNKNOWN','LEGACY',v_contractor,v_vendor,p_qty,'OPEN',p_at,p_reason,'OPENING_SPLIT:'||v_split::text)
  returning id into v_case;
  insert into erp.bb_wip_bs_splits_v1(id,opening_item_id,bs_case_id,product_id,qty_pcs,stage_from,holder_contractor_id,holder_vendor_id,basis,physical_at,reason,created_by)
  values(v_split,p_item,v_case,p_product,p_qty,v_stage,v_contractor,v_vendor,p_basis,p_at,p_reason,erp.current_app_user_id());
  insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
  values(s.po_id,v_stage,'QC',p_qty,v_contractor,'BB_OPENING_WIP_SPLIT_BS',v_split,p_at,erp.current_app_user_id(),p_reason);
  return v_split;
end;$function$;

-- ---------------------------------------------------------------- split BS value (the opening BS rule of AP/AZ, per split)

CREATE OR REPLACE FUNCTION erp.bb_sync_split_bs_value_v1(p_split uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare x erp.bb_wip_bs_splits_v1%rowtype;s erp.initial_import_production_sources%rowtype;v_qty integer;v_target numeric;v_prior numeric;
  v_delta numeric;v_event uuid;v_journal uuid;d record;v_left numeric;v_part numeric;v_run numeric;v_done integer:=0;
begin
  perform erp.require_internal();
  if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0)) then raise exception 'WIP_VALUE_BUSY: penilaian stok sedang berubah, coba ulang';end if;
  select * into x from erp.bb_wip_bs_splits_v1 where id=p_split for update;
  if x.id is null then return;end if;
  select * into strict s from erp.initial_import_production_sources where opening_item_id=x.opening_item_id;
  select coalesce(sum(qty_pcs),0) into v_qty from erp.bs_resolutions where bs_case_id=x.bs_case_id
    and source_rework_order_id is null and resolution_type not in('REWORK_SEWING','REWORK_LAUNDRY');
  if v_qty>x.qty_pcs then raise exception 'Pengeluaran BS melebihi jumlah pisah BS';end if;
  v_target:=round(erp.initial_import_source_value_v1(x.opening_item_id)*v_qty/s.qty_pcs,2);
  select coalesce(sum(target_amount-previous_amount),0) into v_prior from erp.bb_wip_split_value_events_v1 where split_id=x.id;
  v_delta:=v_target-v_prior;if v_delta=0 then return;end if;
  -- AZ: a late supplier invoice with an open date reaches each disposed piece on its disposal day (pro rata by pieces).
  if erp.invoice_recost_economic_date_v1() is not null and v_qty>0 and not exists(select 1 from erp.accounting_period_control c
      where c.singleton_id=1 and c.closed_through is not null and p_date<=c.closed_through) then
    v_left:=v_delta;v_run:=v_prior;
    for d in select least(greatest(p_date,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) bday,sum(r.qty_pcs) q
      from erp.bs_resolutions r where r.bs_case_id=x.bs_case_id and r.source_rework_order_id is null
        and r.resolution_type not in('REWORK_SEWING','REWORK_LAUNDRY') group by 1 order by 1 loop
      v_done:=v_done+d.q;
      v_part:=case when v_done>=v_qty then v_left else round(v_delta*d.q/v_qty,2) end;
      v_left:=v_left-v_part;
      if v_part<>0 then
        v_event:=gen_random_uuid();
        v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,d.bday,'Nilai pisah BS WIP saldo awal yang dikeluarkan atau dikembalikan · tanggal pengeluaran BS',jsonb_build_array(
          jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_part,0),'credit',greatest(-v_part,0),'po_id',s.po_id),
          jsonb_build_object('mapping_key','WIP','debit',greatest(-v_part,0),'credit',greatest(v_part,0),'po_id',s.po_id)));
        insert into erp.bb_wip_split_value_events_v1(id,split_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
        values(v_event,x.id,least(v_done,v_qty),v_run,v_run+v_part,d.bday,v_journal,erp.current_app_user_id());
        v_run:=v_run+v_part;
      end if;
    end loop;
    if v_left<>0 then raise exception 'BB_SPLIT_BS_VALUE_REMAINDER %',v_left;end if;
    return;
  end if;
  v_event:=gen_random_uuid();
  v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,p_date,'Nilai pisah BS WIP saldo awal yang dikeluarkan atau dikembalikan',jsonb_build_array(
    jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0),'po_id',s.po_id),
    jsonb_build_object('mapping_key','WIP','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0),'po_id',s.po_id)));
  insert into erp.bb_wip_split_value_events_v1(id,split_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
  values(v_event,x.id,v_qty,v_prior,v_target,p_date,v_journal,erp.current_app_user_id());
end;$function$;

-- Called by erp.sync_initial_import_bs_disposition_v1 (AP trigger on bs_resolutions) for every case.
CREATE OR REPLACE FUNCTION erp.bb_sync_split_bs_disposition_v1(p_case uuid,p_date date,p_delete boolean)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_split uuid;v_po_status text;
begin
  select id into v_split from erp.bb_wip_bs_splits_v1 where bs_case_id=p_case;
  if v_split is null then return;end if;
  if p_delete then
    if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0)) then raise exception 'WIP_VALUE_BUSY: penilaian stok sedang berubah, coba ulang';end if;
    select p.status into v_po_status from erp.production_orders p join erp.bs_cases b on b.po_id=p.id where b.id=p_case for update of p;
    if v_po_status in('FINISHED','CANCELLED') then raise exception 'Buka kembali PO sebelum mengembalikan saldo BS';end if;
  end if;
  perform erp.bb_sync_split_bs_value_v1(v_split,p_date);
end;$function$;

-- Called by erp.recost_initial_import_origins_v1 after a late invoice changed an opening WIP's value.
CREATE OR REPLACE FUNCTION erp.bb_sync_item_split_values_v1(p_item uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_split uuid;
begin
  for v_split in select id from erp.bb_wip_bs_splits_v1 where opening_item_id=p_item order by created_at,id loop
    perform erp.bb_sync_split_bs_value_v1(v_split,p_date);
  end loop;
end;$function$;

-- A PO may not finish while a split BS still has unresolved pieces (AP guard extended).
CREATE OR REPLACE FUNCTION erp.bb_po_open_split_bs_v1(p_po uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.bb_wip_bs_splits_v1 x join erp.initial_import_production_sources s on s.opening_item_id=x.opening_item_id
    where s.po_id=p_po and x.reversed_at is null
      and x.qty_pcs>coalesce((select sum(r.qty_pcs) from erp.bs_resolutions r where r.bs_case_id=x.bs_case_id),0))
$function$;

CREATE OR REPLACE FUNCTION erp.bb_wip_row_part_v1(p_item uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'pickup',(select jsonb_build_object('id',p.id,'contractor_code',c.contractor_code,'contractor_name',c.contractor_name,
        'date',erp._cp3_business_date(p.physical_at),'po_contractor_assigned',p.po_contractor_assigned)
      from erp.bb_wip_pickups_v1 p join erp.contractors c on c.id=p.contractor_id where p.opening_item_id=p_item and p.reversed_at is null),
    'split_qty_pcs',erp.bb_wip_split_active_qty_v1(p_item),
    'splits',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'bs_case_id',x.bs_case_id,'bs_number',b.bs_number,'bs_status',b.status,
        'qty_pcs',x.qty_pcs,'stage_from',x.stage_from,'date',erp._cp3_business_date(x.physical_at),'reversed',x.reversed_at is not null,
        'resolved_qty_pcs',coalesce((select sum(r.qty_pcs) from erp.bs_resolutions r where r.bs_case_id=x.bs_case_id),0)) order by x.created_at,x.id)
      from erp.bb_wip_bs_splits_v1 x join erp.bs_cases b on b.id=x.bs_case_id where x.opening_item_id=p_item),'[]'::jsonb))
$function$;

-- ---------------------------------------------------------------- W02 wages after cutover on an opening WIP
-- A native work completion needs a Potongan (AI guard); an opening WIP has none. Its source may instead be the opening WIP
-- (bb_opening_item_id, never both): the pieces must be in SEWING with that mandor on the work date (after the pickup of cut
-- pieces), and each component is paid at most once per opening piece after cutover. Allocation to lots stays the native
-- PO-shared rule (cp6_lot_work_cost_v2620c) for completions without a Potongan.
alter table erp.work_completion_events add column bb_opening_item_id uuid references erp.initial_import_production_sources(opening_item_id);
alter table erp.work_completion_events add constraint work_completion_events_bb_source_check check(bb_opening_item_id is null or cutting_group_id is null);
create index work_completion_events_bb_opening_item on erp.work_completion_events(bb_opening_item_id) where bb_opening_item_id is not null;

CREATE OR REPLACE FUNCTION erp.bb_opening_work_source_v1(p_item uuid,p_po uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select p_item is not null and exists(select 1 from erp.initial_import_production_sources s where s.opening_item_id=p_item and s.po_id=p_po and s.bs_case_id is null)
$function$;

CREATE OR REPLACE FUNCTION erp.bb_check_opening_work_v1(p_completion uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare e erp.work_completion_events%rowtype;s erp.initial_import_production_sources%rowtype;v_start timestamptz;r record;v_completed bigint;v_payable bigint;
begin
  select * into strict e from erp.work_completion_events where id=p_completion;
  select * into s from erp.initial_import_production_sources where opening_item_id=e.bb_opening_item_id for update;
  if s.opening_item_id is null or s.po_id<>e.po_id or s.bs_case_id is not null then
    raise exception 'BB_WORK_OPENING_SOURCE: sumber kerja harus WIP saldo awal dari PO yang sama';
  end if;
  if erp.bb_wip_stage_v1(s.opening_item_id)<>'SEWING' or erp.bb_wip_holder_v1(s.opening_item_id) is distinct from e.contractor_id then
    raise exception 'BB_WORK_OPENING_NOT_SEWING: upah jahit hanya untuk WIP saldo awal yang sedang dijahit mandor ini';
  end if;
  select greatest((h.opening_date::timestamp at time zone 'Asia/Jakarta'),coalesce((select p.physical_at from erp.bb_wip_pickups_v1 p
      where p.opening_item_id=s.opening_item_id and p.reversed_at is null),'-infinity'::timestamptz))
    into v_start from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where i.id=s.opening_item_id;
  if e.physical_at<v_start or e.physical_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'BB_WORK_OPENING_DATE: tanggal hasil kerja harus sejak cutover (dan sejak pickup) dan tidak di masa depan';
  end if;
  for r in select l.work_component_id,sum(l.qty_completed) q,sum(l.qty_payable) p,min(wc.component_name) n from erp.work_completion_lines l
      join erp.work_components wc on wc.id=l.work_component_id where l.completion_id=e.id group by l.work_component_id loop
    select coalesce(sum(l.qty_completed),0),coalesce(sum(l.qty_payable),0) into v_completed,v_payable from erp.work_completion_lines l
      join erp.work_completion_events x on x.id=l.completion_id
      where x.bb_opening_item_id=s.opening_item_id and x.status='POSTED' and x.id<>e.id and l.work_component_id=r.work_component_id;
    if v_completed+r.q>s.qty_pcs or v_payable+r.p>s.qty_pcs then
      raise exception 'BB_WORK_OPENING_EXCEEDS: komponen % melebihi % pcs WIP saldo awal (sudah %, input %)',r.n,s.qty_pcs,v_completed,r.q;
    end if;
  end loop;
end;$function$;

-- ---------------------------------------------------------------- W04 import check: CUTTING WIP row

CREATE OR REPLACE FUNCTION erp.bb_check_cutting_wip_row_v1(p_batch uuid,j jsonb)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if upper(j->>'balance_type')<>'WIP' then raise exception 'stage: CUTTING hanya untuk WIP';end if;
  if nullif(btrim(j->>'contractor_code'),'') is not null or nullif(btrim(j->>'vendor_code'),'') is not null then
    raise exception 'BB_CUTTING_WIP_HOLDER: potongan yang menunggu pickup belum dipegang mandor atau laundry; kosongkan contractor_code dan vendor_code';
  end if;
  if nullif(btrim(j->>'location_code'),'') is null
     or not (exists(select 1 from erp.locations l where l.location_code=j->>'location_code' and l.is_active and l.location_type='CUTTING_WIP')
       or exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='LOCATION' and x.validation_status='VALID'
         and x.normalized_payload->>'location_code'=j->>'location_code' and upper(x.normalized_payload->>'location_type')='CUTTING_WIP'
         and coalesce(lower(x.normalized_payload->>'is_active'),'true') in('true','1','yes','ya'))) then
    raise exception 'BB_CUTTING_WIP_LOCATION: isi location_code lokasi potong aktif (jenis CUTTING_WIP) tempat potongan menunggu';
  end if;
end;$function$;

-- ---------------------------------------------------------------- W06 import: OPENING_REWORK and its components

CREATE OR REPLACE FUNCTION erp.bb_parse_count_v1(p_value text,p_field text,p_min integer)
 RETURNS integer LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
begin
  if p_value is null or p_value !~ '^[0-9]{1,9}$' or p_value::integer<p_min then
    raise exception 'BB_COUNT_INVALID: % harus bilangan bulat % atau lebih',p_field,p_min;
  end if;
  return p_value::integer;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_check_rework_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_bs erp.migration_staging_rows%rowtype;b jsonb;v_po jsonb;
  w erp.migration_staging_rows%rowtype;wj jsonb;v_sent integer;v_returned integer;v_open integer;v_date date;v_total integer;
  v_product uuid;v_root uuid;v_model uuid;v_contractor uuid;v_component uuid;v_rate numeric;v_found numeric;v_before integer;v_qty integer;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
  if r.id is null then raise exception 'Baris impor tidak ditemukan';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  if r.entity_type='OPENING_REWORK' then w:=r;
  else
    j:=r.normalized_payload;
    foreach k in array array['rework_number','work_component_code','completed_before_bs_qty','qty_performed','rate_per_pcs'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk komponen rework terbuka',k;end if;
    end loop;
    select * into w from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number'));
    if w.id is null then raise exception 'BB_REWORK_UNKNOWN: nomor rework tidak ada di file rework terbuka impor ini';end if;
  end if;
  wj:=w.normalized_payload;
  foreach k in array array['rework_number','bs_source_key','destination_type','sent_date','qty_sent_original','qty_returned_before_cutover','qty_open'] loop
    if nullif(btrim(wj->>k),'') is null then raise exception '%: wajib diisi untuk rework terbuka',k;end if;
  end loop;
  if length(btrim(wj->>'rework_number'))>50 then raise exception 'rework_number: maksimal 50 karakter';end if;
  if (select count(*) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number')))>1
     or exists(select 1 from erp.rework_orders ro where lower(ro.rework_number)=lower('ORW-'||btrim(wj->>'rework_number'))) then
    raise exception 'BB_REWORK_NUMBER_DUPLICATE: nomor rework sudah dipakai';
  end if;
  select * into v_bs from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_BALANCE_ITEM'
    and upper(x.normalized_payload->>'balance_type')='BS' and nullif(x.normalized_payload->>'po_number','') is not null
    and x.normalized_payload->>'opening_source_key'=wj->>'bs_source_key' and x.validation_status='VALID';
  if v_bs.id is null then
    raise exception 'BB_REWORK_BS_SOURCE_REQUIRED: bs_source_key harus menunjuk baris BS ber-PO yang valid di impor ini';
  end if;
  b:=v_bs.normalized_payload;
  v_sent:=erp.bb_parse_count_v1(wj->>'qty_sent_original','qty_sent_original',1);
  v_returned:=erp.bb_parse_count_v1(wj->>'qty_returned_before_cutover','qty_returned_before_cutover',0);
  v_open:=erp.bb_parse_count_v1(wj->>'qty_open','qty_open',1);
  if v_open<>v_sent-v_returned then
    raise exception 'BB_REWORK_OPEN_QTY_MISMATCH: sisa di rework (%) harus sama dengan dikirim (%) dikurangi kembali sebelum cutover (%)',v_open,v_sent,v_returned;
  end if;
  select coalesce(sum((x.normalized_payload->>'qty_open')::integer),0) into v_total from erp.migration_staging_rows x
    where x.batch_id=p_batch and x.entity_type='OPENING_REWORK' and x.normalized_payload->>'bs_source_key'=wj->>'bs_source_key'
      and x.normalized_payload->>'qty_open' ~ '^[0-9]{1,9}$';
  if v_total>(b->>'qty')::numeric then raise exception 'BB_REWORK_EXCEEDS_BS: rework terbuka melebihi jumlah BS asalnya';end if;
  v_date:=erp.bb_parse_date_v1(wj->>'sent_date','sent_date');
  if v_date>v_cutover then raise exception 'BB_REWORK_SENT_DATE: rework terbuka dikirim sebelum atau pada tanggal saldo awal';end if;
  if upper(wj->>'destination_type')='CONTRACTOR' then
    if nullif(btrim(wj->>'vendor_code'),'') is not null or nullif(btrim(wj->>'contractor_code'),'') is null
       or wj->>'contractor_code' is distinct from b->>'contractor_code' then
      raise exception 'BB_REWORK_HOLDER_MISMATCH: rework ke mandor harus ke mandor pemegang baris BS asalnya';
    end if;
    select c.id into v_contractor from erp.contractors c where c.contractor_code=wj->>'contractor_code' and c.is_active and c.contractor_type='MANDOR';
    if v_contractor is null then raise exception 'BB_REWORK_MANDOR: mandor rework harus mandor aktif yang sudah ada';end if;
    if not exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number'))) then
      raise exception 'BB_REWORK_COMPONENT_REQUIRED: rework ke mandor memerlukan komponen kerja';
    end if;
  elsif upper(wj->>'destination_type')='LAUNDRY' then
    if nullif(btrim(wj->>'contractor_code'),'') is not null or nullif(btrim(wj->>'vendor_code'),'') is null
       or wj->>'vendor_code' is distinct from b->>'vendor_code' then
      raise exception 'BB_REWORK_HOLDER_MISMATCH: rework ke laundry harus ke laundry pemegang baris BS asalnya';
    end if;
    if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number'))) then
      raise exception 'BB_REWORK_LAUNDRY_COMPONENT: rework laundry tidak memakai komponen upah mandor';
    end if;
  else raise exception 'destination_type: isi CONTRACTOR atau LAUNDRY';
  end if;
  -- The native rework of a BS with PO and product needs the product's accessory BOM (an explicit empty one is enough).
  select p.id,p.identity_root_id,p.model_id into v_product,v_root,v_model from erp.products p
    where lower(btrim(p.sku))=lower(btrim(b->>'product_sku')) and p.effective_from<((v_cutover+1)::timestamp at time zone 'Asia/Jakarta')
    order by p.effective_from desc,p.id limit 1;
  if v_product is null or not exists(select 1 from erp.accessory_bom_versions a where a.product_id=v_root and a.is_active
      and a.effective_from<=((v_cutover+1)::timestamp at time zone 'Asia/Jakarta')
      and (a.effective_to is null or a.effective_to>(v_cutover::timestamp at time zone 'Asia/Jakarta'))) then
    raise exception 'BB_REWORK_ACCESSORY_BOM_REQUIRED: produk BS asal belum punya BOM aksesori yang berlaku (BOM kosong pun harus dicatat)';
  end if;
  if r.entity_type='OPENING_REWORK' then
    return jsonb_build_object('kind','REWORK','open_qty',v_open,'sent_qty',v_sent,'returned_qty',v_returned,'sent_date',v_date);
  end if;
  -- Component row.
  if upper(wj->>'destination_type')<>'CONTRACTOR' then raise exception 'BB_REWORK_LAUNDRY_COMPONENT: rework laundry tidak memakai komponen upah mandor';end if;
  select id into v_component from erp.work_components where component_code=j->>'work_component_code' and is_active;
  if v_component is null then raise exception 'BB_REWORK_COMPONENT_UNKNOWN: komponen kerja aktif tidak ditemukan';end if;
  if (select count(*) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number'))
      and x.normalized_payload->>'work_component_code'=j->>'work_component_code')>1 then
    raise exception 'BB_REWORK_COMPONENT_DUPLICATE: komponen yang sama tercatat dua kali pada rework ini';
  end if;
  v_qty:=erp.bb_parse_count_v1(j->>'qty_performed','qty_performed',1);
  if v_qty>v_open then raise exception 'BB_REWORK_COMPONENT_QTY: qty dikerjakan tidak boleh melebihi sisa di rework';end if;
  v_before:=erp.bb_parse_count_v1(j->>'completed_before_bs_qty','completed_before_bs_qty',0);
  if v_before>(b->>'qty')::numeric then raise exception 'BB_REWORK_BASELINE: pcs yang sudah selesai sebelum BS tidak boleh melebihi jumlah BS';end if;
  if exists(select 1 from erp.migration_staging_rows x join erp.migration_staging_rows y on y.batch_id=x.batch_id and y.entity_type='OPENING_REWORK'
      and lower(btrim(y.normalized_payload->>'rework_number'))=lower(btrim(x.normalized_payload->>'rework_number'))
      where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT' and x.id<>r.id
        and y.normalized_payload->>'bs_source_key'=wj->>'bs_source_key' and x.normalized_payload->>'work_component_code'=j->>'work_component_code'
        and x.normalized_payload->>'completed_before_bs_qty' is distinct from j->>'completed_before_bs_qty') then
    raise exception 'BB_REWORK_BASELINE_CONFLICT: pcs selesai sebelum BS untuk komponen yang sama harus sama pada setiap rework BS itu';
  end if;
  v_rate:=erp.bb_parse_amount_v1(j->>'rate_per_pcs','rate_per_pcs',true);
  select po.normalized_payload into v_po from erp.migration_staging_rows po where po.batch_id=p_batch and po.entity_type='OPEN_PO'
    and po.normalized_payload->>'po_number'=b->>'po_number' and po.validation_status='VALID';
  select m.id into v_model from erp.product_models m where m.model_code=v_po->>'model_code';
  select cwr.rate_per_pcs into v_found from erp.contractor_work_rates cwr where cwr.contractor_id=v_contractor and cwr.model_id=v_model
    and cwr.work_component_id=v_component and cwr.effective_from<=(v_cutover::timestamp at time zone 'Asia/Jakarta')
    and (cwr.effective_to is null or cwr.effective_to>(v_cutover::timestamp at time zone 'Asia/Jakarta'))
    order by cwr.effective_from desc,cwr.id desc limit 1;
  if v_found is null then raise exception 'BB_REWORK_RATE_MISSING: tarif mandor untuk model dan komponen ini belum berlaku pada cutover';end if;
  if v_found<>v_rate then raise exception 'BB_REWORK_RATE_MISMATCH: tarif baris (%) berbeda dengan tarif mandor yang berlaku (%)',v_rate,v_found;end if;
  return jsonb_build_object('kind','COMPONENT','work_component_id',v_component,'qty_performed',v_qty,'completed_before_bs_qty',v_before,'rate',v_rate);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_validate_production_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_REWORK','OPENING_REWORK_COMPONENT')
      order by entity_type desc,source_row_no loop
    begin
      perform erp.bb_check_rework_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_apply_production_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;c record;j jsonb;v jsonb;v_item uuid;v_case erp.bs_cases%rowtype;v_components jsonb;v_lines jsonb;v_payload jsonb;
  v_result jsonb;v_order uuid;v_bc uuid;v_before integer;v_line jsonb;v_row_rate numeric;v_recorded jsonb:='[]';
begin
  perform erp.require_owner_admin();
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_REWORK' and posted_entity_id is null
      order by source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Rework terbuka belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;v:=erp.bb_check_rework_import_row_v1(p_batch,r.id);
    select k.opening_item_id into v_item from erp.initial_import_opening_stock_sources k join erp.initial_import_production_sources s
      on s.opening_item_id=k.opening_item_id where k.batch_id=p_batch and k.source_key=j->>'bs_source_key' and s.bs_case_id is not null;
    if v_item is null then raise exception 'BB_REWORK_BS_SOURCE_REQUIRED: kasus BS asal belum dibukukan';end if;
    select b.* into strict v_case from erp.bs_cases b join erp.initial_import_production_sources s on s.bs_case_id=b.id where s.opening_item_id=v_item;
    v_components:='[]';v_recorded:='[]';
    for c in select x.* from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number')) order by x.source_row_no loop
      if c.validation_status<>'VALID' then raise exception 'Komponen rework terbuka belum lolos pemeriksaan';end if;
      v:=erp.bb_check_rework_import_row_v1(p_batch,c.id);
      insert into erp.bs_case_components(bs_case_id,work_component_id,completed_before_bs_qty,notes)
      values(v_case.id,(v->>'work_component_id')::uuid,(v->>'completed_before_bs_qty')::integer,'Saldo awal: pcs yang komponennya sudah selesai sebelum BS')
      on conflict(bs_case_id,work_component_id) do nothing;
      select id,completed_before_bs_qty into v_bc,v_before from erp.bs_case_components where bs_case_id=v_case.id and work_component_id=(v->>'work_component_id')::uuid;
      if v_before<>(v->>'completed_before_bs_qty')::integer then
        raise exception 'BB_REWORK_BASELINE_CONFLICT: pcs selesai sebelum BS berbeda dengan kasus BS yang sudah ada';
      end if;
      v_components:=v_components||jsonb_build_array(jsonb_build_object('bs_case_component_id',v_bc,'qty_performed',(v->>'qty_performed')::integer));
      v_recorded:=v_recorded||jsonb_build_array(jsonb_build_object('source_row_id',c.id,'bs_case_component_id',v_bc,'work_component_code',
        c.normalized_payload->>'work_component_code','completed_before_bs_qty',(v->>'completed_before_bs_qty')::integer,
        'qty_performed',(v->>'qty_performed')::integer,'rate_per_pcs',v->>'rate'));
    end loop;
    v:=erp.bb_check_rework_import_row_v1(p_batch,r.id);
    v_payload:=jsonb_build_object('rework_number','ORW-'||btrim(j->>'rework_number'),'bs_case_id',v_case.id,'destination_type',upper(j->>'destination_type'),
      'contractor_id',(select id from erp.contractors where contractor_code=nullif(j->>'contractor_code','')),
      'vendor_id',(select id from erp.laundry_vendors where vendor_code=nullif(j->>'vendor_code','')),
      'qty_sent',(v->>'open_qty')::integer,'physical_sent_at',v_case.physical_at,'status','IN_PROGRESS','accessory_bom_item_ids','[]'::jsonb,
      'components',v_components,'notes',concat_ws(' · ','Rework terbuka saldo awal '||btrim(j->>'rework_number'),'dikirim '||(v->>'sent_date'),
        'asal '||(v->>'sent_qty')||' pcs, kembali sebelum cutover '||(v->>'returned_qty')||' pcs',nullif(btrim(j->>'notes'),'')),
      'change_reason','Impor saldo awal: rework terbuka '||btrim(j->>'rework_number'));
    v_result:=erp.save_rework_order_v2(v_payload,r.id,null);
    v_order:=(v_result->>'rework_order_id')::uuid;
    for v_line in select value from jsonb_array_elements(v_result->'components') loop
      select (x->>'rate_per_pcs')::numeric into v_row_rate from jsonb_array_elements(v_recorded) x
        where (x->>'bs_case_component_id')::uuid=(v_line->>'bs_case_component_id')::uuid;
      if (v_line->>'rate_snapshot')::numeric is distinct from v_row_rate then
        raise exception 'BB_REWORK_RATE_MISMATCH: tarif native rework (%) berbeda dengan tarif baris (%)',v_line->>'rate_snapshot',v_row_rate;
      end if;
      update erp.migration_staging_rows set posted_entity_id=(v_line->>'rework_component_line_id')::uuid,posted_entity_type='OPENING_REWORK_COMPONENT',
        posted_at=statement_timestamp(),updated_at=statement_timestamp()
      where id=(select (x->>'source_row_id')::uuid from jsonb_array_elements(v_recorded) x
        where (x->>'bs_case_component_id')::uuid=(v_line->>'bs_case_component_id')::uuid);
    end loop;
    insert into erp.bb_opening_reworks_v1(batch_id,source_row_id,rework_order_id,bs_case_id,opening_item_id,legacy_rework_number,legacy_sent_date,
      qty_sent_original,qty_returned_before_cutover,qty_open,components)
    values(p_batch,r.id,v_order,v_case.id,v_item,btrim(j->>'rework_number'),(v->>'sent_date')::date,(v->>'sent_qty')::integer,
      (v->>'returned_qty')::integer,(v->>'open_qty')::integer,v_recorded);
    update erp.migration_staging_rows set posted_entity_id=v_order,posted_entity_type='OPENING_REWORK',posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_REWORK_COMPONENT' and posted_entity_id is null) then
    raise exception 'BB_REWORK_COMPONENT_NOT_POSTED: komponen rework tanpa rework yang dibukukan';
  end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_production_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('opening_reworks',coalesce((select jsonb_agg(jsonb_build_object('id',o.id,'rework_order_id',ro.id,
      'rework_number',ro.rework_number,'legacy_rework_number',o.legacy_rework_number,'legacy_sent_date',o.legacy_sent_date,
      'bs_case_id',o.bs_case_id,'bs_number',b.bs_number,'destination_type',ro.destination_type,
      'holder_name',coalesce(c.contractor_name,v.vendor_name),'qty_sent_original',o.qty_sent_original,
      'qty_returned_before_cutover',o.qty_returned_before_cutover,'qty_open',o.qty_open,'status',ro.status,
      'qty_good_returned',ro.qty_good_returned,'qty_bs_returned',ro.qty_bs_returned,'row_version',ro.row_version::text,
      'components',o.components) order by o.legacy_rework_number)
    from erp.bb_opening_reworks_v1 o join erp.rework_orders ro on ro.id=o.rework_order_id join erp.bs_cases b on b.id=o.bs_case_id
    left join erp.contractors c on c.id=ro.contractor_id left join erp.laundry_vendors v on v.id=ro.vendor_id
    where o.batch_id=p_batch),'[]'::jsonb))
$function$;

CREATE OR REPLACE FUNCTION erp.bb_production_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'pickups',coalesce((select jsonb_agg(to_jsonb(p) order by p.id) from erp.bb_wip_pickups_v1 p join erp.initial_import_production_sources s
      on s.opening_item_id=p.opening_item_id where s.batch_id=p_batch),'[]'::jsonb),
    'splits',coalesce((select jsonb_agg(to_jsonb(x)||jsonb_build_object('bs_row_version',b.row_version) order by x.id) from erp.bb_wip_bs_splits_v1 x
      join erp.initial_import_production_sources s on s.opening_item_id=x.opening_item_id join erp.bs_cases b on b.id=x.bs_case_id
      where s.batch_id=p_batch),'[]'::jsonb),
    'reworks',coalesce((select jsonb_agg(jsonb_build_object('id',o.id,'row_version',ro.row_version,'status',ro.status) order by o.id)
      from erp.bb_opening_reworks_v1 o join erp.rework_orders ro on ro.id=o.rework_order_id where o.batch_id=p_batch),'[]'::jsonb))
$function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.proname like 'bb\_%' loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
