-- CP6 AX: finished goods without a production source. Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_ax_t1_family.sql (sha256 c5f9df1202a0d379908be4965dd158b10d064913061cd1481cb3e543034ca3c4): the T1 body below is unchanged apart from the
-- ledger description; guards follow AO..AV. Catalog pins are placeholders until the T3 capture (refuse as is).
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';
set local role postgres;
do $closed_admission$
begin
 if session_user not in('postgres','supabase_admin')
  or (select datallowconn from pg_database where datname=current_database())
  or exists(select 1 from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()) then
  raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE';
 end if;
end $closed_admission$;
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
do $lock_business$
declare n text;
begin
 for n in select c.relname from pg_class c join pg_namespace s on s.oid=c.relnamespace where s.nspname='erp' and c.relkind in('r','p') order by 1 loop
  execute format('lock table erp.%I in share row exclusive mode',n);
 end loop;
end $lock_business$;
do $predecessor$
begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20aw')
  or exists(select 1 from erp.schema_migrations where version='v2.6.20ax')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20aw_cp6_close_readiness_engine')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260924010000' and name='erp_v2_6_20aw_cp6_close_readiness_engine'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='72e1f6169b9ab93bbedcf4082bef4e9c31167b24bcce92812161775fde08f61a')
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260924010000') then raise exception 'AX_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule')
), objects as (
 select 'FUNCTION:'||format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) k,
 jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text) end) v
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')
 union all
 select 'RELATION:'||format('%I.%I',nspname,relname),jsonb_build_array(relkind,pg_get_userbyid(relowner),
  case when relacl is null then null else array(select a::text from unnest(relacl)a order by a::text) end,
  relrowsecurity,relforcerowsecurity,relreplident,relpersistence,relispartition,reloptions)
 from relations
 union all
 select 'COLUMN:'||format('%I.%I.%I',r.nspname,r.relname,a.attname),
 jsonb_build_array((select count(*) from pg_attribute visible where visible.attrelid=a.attrelid and visible.attnum>0 and not visible.attisdropped and visible.attnum<=a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
  pg_get_expr(d.adbin,d.adrelid),a.attcollation::regcollation::text,
  case when a.attacl is null then null else array(select x::text from unnest(a.attacl)x order by x::text) end)
 from relations r join pg_attribute a on a.attrelid=r.oid and a.attnum>0 and not a.attisdropped
 left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
 union all
 select 'CONSTRAINT:'||format('%I.%I.%I',r.nspname,r.relname,c.conname),
 jsonb_build_array(c.contype,pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.connoinherit)
 from relations r join pg_constraint c on c.conrelid=r.oid
 union all
 select 'INDEX:'||format('%I.%I',r.nspname,c.relname),
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,i.indisexclusion,i.indisvalid,i.indisready,i.indisclustered,i.indisreplident,c.reloptions)
 from relations r join pg_index i on i.indrelid=r.oid join pg_class c on c.oid=i.indexrelid
 union all
 select 'TRIGGER:'||format('%I.%I.%I',r.nspname,r.relname,t.tgname),jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)
 from relations r join pg_trigger t on t.tgrelid=r.oid and not t.tgisinternal
 union all
 select 'POLICY:'||format('%I.%I.%I',r.nspname,r.relname,p.polname),jsonb_build_array(p.polcmd,p.polpermissive,
  array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(p.polroles)x order by 1),
  pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))
 from relations r join pg_policy p on p.polrelid=r.oid
 union all
 select 'VIEW:'||format('%I.%I',nspname,relname),to_jsonb(pg_get_viewdef(oid,false)) from relations where relkind in('v','m')
 union all
 select 'SEQUENCE:'||format('%I.%I',r.nspname,r.relname),jsonb_build_array(format_type(s.seqtypid,null),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle)
 from relations r join pg_sequence s on s.seqrelid=r.oid
 union all
 select 'SCHEMA:'||nspname,jsonb_build_array(pg_get_userbyid(nspowner),
  case when nspacl is null then null else array(select a::text from unnest(nspacl)a order by a::text) end)
 from pg_namespace where nspname in('erp','public')
 union all
 select 'DEFAULT_ACL:'||pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,
 to_jsonb(array(select a::text from unnest(d.defaclacl)a order by a::text))
 from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
 where n.nspname in('erp','public') or d.defaclnamespace=0
 union all
 select 'ENUM:'||format('%I.%I',n.nspname,t.typname),jsonb_build_array(pg_get_userbyid(t.typowner),
  (select jsonb_agg(e.enumlabel order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid))
 from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname in('erp','public') and t.typtype='e'
)
select coalesce(jsonb_object_agg(k,encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex')),'{}'::jsonb) from objects
) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>0 or fingerprint is distinct from '0000000000000000000000000000000000000000000000000000000000000000' then
  raise exception 'AX_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';
do $t1_guard$
begin
 if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw'))<>2 then raise exception 'AX_T1_REQUIRES_AV_AND_AW'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ax') or to_regclass('erp.fg_unsourced_receipts_v1') is not null then raise exception 'AX_T1_ALREADY_INSTALLED'; end if;
end $t1_guard$;
create table erp.fg_unsourced_receipts_v1 (
  id uuid primary key default gen_random_uuid(),
  source_kind text not null check (source_kind in('FOUND_AT_OPNAME','GOOD_FROM_UNSOURCED_BS','REDYE_MIXED')),
  lot_id uuid not null unique references erp.fg_lots(id),
  bs_case_id uuid references erp.bs_cases(id),
  bs_resolution_id uuid,
  location_id uuid not null references erp.locations(id),
  quality_grade text not null,
  qty_pcs integer not null check (qty_pcs>0),
  physical_at timestamptz not null,
  unit_value numeric(18,2) not null check (unit_value>=0 and unit_value<>'NaN'::numeric),
  total_value numeric(20,2) not null check (total_value>=0 and total_value<>'NaN'::numeric),
  valuation jsonb not null check (valuation ? 'tier'),
  reason text not null check (length(btrim(reason))>0),
  status text not null default 'POSTED' check (status in('POSTED','REVERSED')),
  journal_entry_id uuid references erp.journal_entries(id),
  movement_id uuid not null,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_by uuid,
  reversed_at timestamptz,
  reversal_reason text,
  check ((source_kind='GOOD_FROM_UNSOURCED_BS')=(bs_case_id is not null)),
  check ((status='REVERSED')=(reversed_at is not null))
);
alter table erp.fg_unsourced_receipts_v1 enable row level security;
revoke all on erp.fg_unsourced_receipts_v1 from public,anon,authenticated,service_role;
create index idx_fg_unsourced_receipts_v1_bs_case on erp.fg_unsourced_receipts_v1(bs_case_id) where bs_case_id is not null;
CREATE OR REPLACE FUNCTION erp.guard_fg_unsourced_receipt_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  -- Only the reversal RPC may change a receipt, and only POSTED -> REVERSED with its reversal fields.
  if tg_op='UPDATE' and current_setting('erp.fg_unsourced_reversal',true)='on' and old.status='POSTED' and new.status='REVERSED'
     and (to_jsonb(new)-array['status','reversed_by','reversed_at','reversal_reason'])
       =(to_jsonb(old)-array['status','reversed_by','reversed_at','reversal_reason']) then
    return new;
  end if;
  raise exception 'FG_UNSOURCED_RECEIPT_IMMUTABLE: penerimaan barang tanpa sumber hanya bisa dibatalkan lewat RPC pembatalan';
end
$function$;
CREATE OR REPLACE FUNCTION erp.guard_bs_resolution_fg_unsourced_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
  -- A BS resolution written by a POSTED AX receipt is part of that receipt: removing or changing it elsewhere (the BS
  -- workspace REVERSE_DISPOSITION) would reopen the case while the lot and its journal stay, and the same pieces could
  -- enter again. Only the AX reversal removes it, after the receipt has left POSTED.
  if exists(select 1 from erp.fg_unsourced_receipts_v1 r where r.bs_resolution_id=old.id and r.status='POSTED') then
    raise exception 'FG_UNSOURCED_BS_RESOLUTION_OWNED: resolusi BS ini dibuat penerimaan barang tanpa sumber; batalkan penerimaan itu lewat pembatalan AX';
  end if;
  return case when tg_op='DELETE' then old else new end;
end
$function$;
CREATE OR REPLACE FUNCTION erp.fg_unsourced_valuation_v1(p_product_id uuid, p_physical_at timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- AX valuation (owner §15.1-FG, §19.2): average HPP per pcs at the physical instant, only for goods without an
-- origin value. Tiers stop at the first positive value: SKU (every version of the same identity) -> same model and
-- size, other colour -> same model -> owner input. Within a tier the stock on hand at the instant is weighted by
-- quantity (sum qty x current lot HPP / sum qty); with no stock on hand, lots produced up to the instant are weighted
-- by their initial quantity. Only production, opening, conversion and return lots count; unsourced (OTHER) and voided
-- lots never feed the average. Pieces reserved by a draft sale are still in the warehouse, so the draft reservation
-- (SALE_RESERVE, and the reversal that releases it) is not counted as an outflow; a posted sale turns the same row
-- into SALE and then counts (the ownership rule of compute_non_po_product_hpp_targets_v2620f). Each lot uses its
-- current (corrected) HPP: a later correction states the true cost of the same pieces, and the posting freezes the result. Pattern and fabric are not SKU attributes: they exist only through a SKU's own production lineage,
-- which already gives tier SKU a value, so they are reported as not available instead of guessed.
declare
  v_product erp.products%rowtype;
  v_tier text;
  r record;
begin
  if p_product_id is null or p_physical_at is null then raise exception 'FG_UNSOURCED_VALUATION_INPUT_REQUIRED'; end if;
  select * into v_product from erp.products where id=p_product_id;
  if v_product.id is null then raise exception 'FG_UNSOURCED_PRODUCT_NOT_FOUND'; end if;
  foreach v_tier in array array['SKU','MODEL_SIZE','MODEL'] loop
    if v_tier<>'SKU' and v_product.model_id is null then continue; end if;
    select sum(l.q) filter(where l.q>0) stock_qty,sum(l.q*l.hpp) filter(where l.q>0) stock_value,
      sum(l.initial_qty) produced_qty,sum(l.initial_qty*l.hpp) produced_value,
      coalesce(bool_or(l.cost_state='ESTIMATED'),false) has_estimated,
      to_jsonb((array_agg(jsonb_build_object('lot_id',l.id,'product_id',l.product_id,'qty_at_instant',l.q,
        'initial_qty',l.initial_qty,'hpp_per_pcs',l.hpp,'cost_state',l.cost_state) order by l.produced_at,l.id))[1:50]) lots
    into r
    from (
      select fl.id,fl.product_id,fl.produced_at,fl.initial_qty_pcs::numeric initial_qty,hv.hpp_per_pcs::numeric hpp,hv.cost_state,
        coalesce((select sum(m.qty_signed) from erp.fg_stock_movements m where m.lot_id=fl.id and m.physical_at<=p_physical_at
          and m.movement_type<>'SALE_RESERVE'
          and not exists(select 1 from erp.fg_stock_movements rm where rm.id=m.reversal_of_id and rm.movement_type='SALE_RESERVE')),0)::numeric q
      from erp.fg_lots fl
      join erp.products p on p.id=fl.product_id
      join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
      where fl.lot_origin in('PRODUCTION','OPENING','CONVERSION','RETURN') and fl.produced_at<=p_physical_at
        and hv.hpp_per_pcs is not null
        and case v_tier when 'SKU' then coalesce(p.identity_root_id,p.id)=coalesce(v_product.identity_root_id,v_product.id)
                        when 'MODEL_SIZE' then p.model_id=v_product.model_id and p.size_id is not distinct from v_product.size_id
                        else p.model_id=v_product.model_id end
    ) l;
    if coalesce(r.stock_qty,0)>0 and round(r.stock_value/r.stock_qty,2)>0 then
      return jsonb_build_object('tier',v_tier,'method','STOCK_ON_HAND_WEIGHTED','unit_value',round(r.stock_value/r.stock_qty,2),
        'raw_average',r.stock_value/r.stock_qty,'basis_qty',r.stock_qty,'contains_estimated_hpp',r.has_estimated,
        'physical_at',p_physical_at,'pattern_fabric','NOT_AVAILABLE_WITHOUT_OWN_LINEAGE','lots',r.lots);
    elsif coalesce(r.produced_qty,0)>0 and round(r.produced_value/r.produced_qty,2)>0 then
      return jsonb_build_object('tier',v_tier,'method','PRODUCED_WEIGHTED','unit_value',round(r.produced_value/r.produced_qty,2),
        'raw_average',r.produced_value/r.produced_qty,'basis_qty',r.produced_qty,'contains_estimated_hpp',r.has_estimated,
        'physical_at',p_physical_at,'pattern_fabric','NOT_AVAILABLE_WITHOUT_OWN_LINEAGE','lots',r.lots);
    end if;
  end loop;
  return jsonb_build_object('tier','OWNER_INPUT_REQUIRED','method',null,'unit_value',null,'physical_at',p_physical_at,
    'reason','Tidak ada lot pembanding bernilai; owner wajib mengisi nilai per pcs dengan alasan (tidak pernah Rp0 otomatis).');
end
$function$;
CREATE OR REPLACE FUNCTION erp.post_fg_unsourced_receipt_v1(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- AX (owner §15.1-FG, §19.2): finished goods entering without a production source: found at stock opname, GOOD from a
-- found (OUT_OF_NOWHERE) BS case, or a rare mixed re-dye. A new non-PO lot (origin OTHER) valued at the average HPP of
-- erp.fg_unsourced_valuation_v1 at the physical instant and frozen at posting; never Rp0 unless the owner enters it
-- with a reason. Journal Dr FG_INVENTORY (with product) / Cr OTHER_INCOME (without product, like the opening equity
-- side, so the non-PO HPP book stays equal to its target) on the physical date; post_journal moves the GL date into
-- the open period when that date is closed. GOOD from an ordinary BS stays on rework (decision 2A).
declare
  v_kind text:=upper(nullif(btrim(p_payload->>'source_kind'),''));
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_id uuid:=gen_random_uuid();
  v_hash text;v_cached jsonb;
  v_product uuid;v_location uuid;v_grade text;v_qty numeric;v_at timestamptz;
  v_bs erp.bs_cases%rowtype;v_open bigint;v_in_rework bigint;v_root uuid;v_override numeric;v_override_text text;
  v_valuation jsonb;v_unit numeric(18,2);v_total numeric(20,2);
  v_lot uuid;v_movement uuid;v_journal uuid;v_resolution uuid;
begin
  perform erp.require_owner_admin();
  if p_client_request_id is null then raise exception 'FG_UNSOURCED_REQUEST_ID_REQUIRED'; end if;
  if v_reason is null then raise exception 'FG_UNSOURCED_REASON_REQUIRED'; end if;
  if v_kind is null or v_kind not in('FOUND_AT_OPNAME','GOOD_FROM_UNSOURCED_BS','REDYE_MIXED') then
    raise exception 'FG_UNSOURCED_KIND_INVALID';
  end if;
  v_hash:=erp._request_hash(p_payload);
  v_cached:=erp._idempotency_begin('post_fg_unsourced_receipt_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  -- Numbers: whole positive pieces; an owner value is a finite, non-negative amount with at most two decimals.
  begin v_qty:=(p_payload->>'qty_pcs')::numeric;
  exception when others then raise exception 'FG_UNSOURCED_QTY_INVALID'; end;
  if v_qty is null or v_qty='NaN'::numeric or v_qty<=0 or v_qty>2147483647 or v_qty<>trunc(v_qty) then
    raise exception 'FG_UNSOURCED_QTY_INVALID';
  end if;
  v_override_text:=nullif(btrim(p_payload->>'owner_unit_value'),'');
  if v_override_text is not null then
    begin v_override:=v_override_text::numeric;
    exception when others then raise exception 'FG_UNSOURCED_VALUE_INVALID'; end;
    -- Storage bound: lot HPP per pcs and movement unit HPP are numeric(18,6), so a unit value stays below 1e12.
    if v_override='NaN'::numeric or v_override<0 or v_override>=1000000000000::numeric or v_override<>round(v_override,2) then
      raise exception 'FG_UNSOURCED_VALUE_INVALID';
    end if;
    if nullif(btrim(p_payload->>'owner_value_reason'),'') is null then raise exception 'FG_UNSOURCED_VALUE_REASON_REQUIRED'; end if;
  end if;
  begin v_at:=(p_payload->>'physical_at')::timestamptz;
  exception when others then raise exception 'FG_UNSOURCED_PHYSICAL_AT_INVALID'; end;
  if v_at is null or not isfinite(v_at) then raise exception 'FG_UNSOURCED_PHYSICAL_AT_INVALID'; end if;
  if v_at>statement_timestamp()+interval '5 minutes' then raise exception 'FG_UNSOURCED_PHYSICAL_AT_FUTURE'; end if;
  begin
    v_location:=(p_payload->>'location_id')::uuid;
    v_product:=(p_payload->>'product_id')::uuid;
  exception when others then raise exception 'FG_UNSOURCED_REFERENCE_INVALID'; end;
  v_grade:=coalesce(nullif(btrim(p_payload->>'quality_grade'),''),'GRADE_A');
  -- GOOD goods only: reservations, sales and conversions handle GRADE_A stock, anything else could never leave.
  if v_grade<>'GRADE_A' then raise exception 'FG_UNSOURCED_GRADE_INVALID: barang masuk lewat jalur ini harus GRADE_A'; end if;
  -- One lock order with every FG posting (sale, adjustment, conversion, reversal): the FG/HPP advisory lock first,
  -- then rows; the reversal holds this lock before its BS trigger locks the case.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));

  if v_kind='GOOD_FROM_UNSOURCED_BS' then
    select * into v_bs from erp.bs_cases where id=(p_payload->>'bs_case_id')::uuid for update;
    if v_bs.id is null then raise exception 'FG_UNSOURCED_BS_NOT_FOUND'; end if;
    if not exists(select 1 from erp.bs_case_manual_origins_v1 o where o.bs_case_id=v_bs.id and o.origin_type='OUT_OF_NOWHERE') then
      raise exception 'FG_UNSOURCED_BS_HAS_ORIGIN_VALUE: GOOD dari BS biasa memakai rework (2A)';
    end if;
    if v_bs.status in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED','ON_HOLD') then
      raise exception 'FG_UNSOURCED_BS_NOT_OPEN: status %',v_bs.status;
    end if;
    -- GOOD is new stock at its own physical instant (decision 1C): it takes the version of the BS product's identity
    -- that is in force then, which may be a successor started after the BS was found.
    select coalesce(p.identity_root_id,p.id) into v_root from erp.products p where p.id=v_bs.product_id;
    if v_root is null then raise exception 'FG_UNSOURCED_BS_PRODUCT_MISMATCH'; end if;
    if v_product is null then
      select p.id into v_product from erp.products p
      where coalesce(p.identity_root_id,p.id)=v_root and p.effective_from<=v_at and (p.effective_to is null or v_at<p.effective_to)
      order by p.effective_from desc,p.id limit 1;
      v_product:=coalesce(v_product,v_bs.product_id);
    elsif not exists(select 1 from erp.products p where p.id=v_product and coalesce(p.identity_root_id,p.id)=v_root) then
      raise exception 'FG_UNSOURCED_BS_PRODUCT_MISMATCH';
    end if;
    -- Same availability rule as the platform's disposition and rework guards: pieces out at an active rework order
    -- are not available.
    select coalesce(sum(r.qty_pcs),0) into v_open from erp.bs_resolutions r where r.bs_case_id=v_bs.id;
    select coalesce(sum(ro.qty_sent),0) into v_in_rework from erp.rework_orders ro
      where ro.bs_case_id=v_bs.id and ro.status in('OPEN','IN_PROGRESS','PARTIAL');
    v_open:=greatest(v_bs.qty_pcs-v_open-v_in_rework,0);
    if v_qty>v_open then raise exception 'FG_UNSOURCED_BS_QTY_EXCEEDS_OPEN: % > %',v_qty,v_open; end if;
    if v_at<v_bs.physical_at then raise exception 'FG_UNSOURCED_BEFORE_BS_FOUND'; end if;
  elsif nullif(p_payload->>'bs_case_id','') is not null then
    raise exception 'FG_UNSOURCED_BS_ONLY_FOR_GOOD_FROM_BS';
  end if;
  if v_product is null then raise exception 'FG_UNSOURCED_PRODUCT_REQUIRED'; end if;
  if v_location is null then raise exception 'FG_UNSOURCED_LOCATION_REQUIRED'; end if;

  -- The SKU version must be active at the physical instant (NEW_STOCK, owner decision 1C).
  perform erp.assert_product_identity_time(v_product,v_at,'NEW_STOCK');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);

  v_valuation:=erp.fg_unsourced_valuation_v1(v_product,v_at);
  -- Owner decision: the average is the value whenever a reference exists; an owner value is only the last tier.
  if v_override is not null and v_valuation->>'tier'<>'OWNER_INPUT_REQUIRED' then
    raise exception using message='FG_UNSOURCED_OWNER_VALUE_NOT_ALLOWED: ada pembanding HPP; nilai mengikuti rata-rata pada tanggal fisik',
      detail=v_valuation::text;
  end if;
  if v_override is not null then
    v_valuation:=jsonb_build_object('tier','OWNER_VALUE','unit_value',v_override,
      'owner_value_reason',btrim(p_payload->>'owner_value_reason'),'computed',v_valuation);
  elsif v_valuation->>'tier'='OWNER_INPUT_REQUIRED' then
    raise exception using message='FG_UNSOURCED_VALUE_REQUIRED: tidak ada pembanding HPP; owner wajib mengisi nilai per pcs dengan alasan',
      detail=v_valuation::text;
  end if;
  v_unit:=(v_valuation->>'unit_value')::numeric;
  if v_unit*v_qty>=1000000000000000000::numeric then raise exception 'FG_UNSOURCED_VALUE_INVALID: total melebihi batas penyimpanan'; end if;
  v_total:=round(v_unit*v_qty,2);

  insert into erp.fg_lots(lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
  values('AX-'||to_char(v_at at time zone 'Asia/Jakarta','YYYYMMDD')||'-'||substr(v_id::text,1,8),null,null,v_product,
    v_qty::integer,0,v_at,true,'OTHER')
  returning id into v_lot;
  insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,calculation_reason,created_by)
  values(v_lot,1,'ADJUSTED',v_qty::integer,v_total,true,
    'Unsourced FG valued at '||(v_valuation->>'tier')||' average HPP; frozen at posting',erp.current_app_user_id());
  v_movement:=erp.post_fg_movement(v_product,v_lot,v_location,v_grade,'ADJUSTMENT',v_qty::integer,v_unit,null,
    'FG_UNSOURCED_RECEIPT',v_id,v_at,'Barang jadi tanpa sumber produksi: '||v_kind,false);
  if v_total>0 then
    v_journal:=erp.post_journal('FG_UNSOURCED_RECEIPT',v_id,(v_at at time zone 'Asia/Jakarta')::date,
      'Barang jadi tanpa sumber produksi · '||v_reason,
      jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_total,'credit',0,'product_id',v_product),
                        jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',v_total)));
  end if;
  if v_kind='GOOD_FROM_UNSOURCED_BS' then
    insert into erp.bs_resolutions(bs_case_id,resolution_type,qty_pcs,compensation_amount,physical_at,notes)
    values(v_bs.id,'OTHER',v_qty::integer,0,v_at,'GOOD dari BS temuan, penerimaan '||v_id)
    returning id into v_resolution;
    perform erp.refresh_bs_case_status(v_bs.id);
  end if;
  insert into erp.fg_unsourced_receipts_v1(id,source_kind,lot_id,bs_case_id,bs_resolution_id,location_id,quality_grade,qty_pcs,
    physical_at,unit_value,total_value,valuation,reason,journal_entry_id,movement_id,created_by)
  values(v_id,v_kind,v_lot,v_bs.id,v_resolution,v_location,v_grade,v_qty::integer,v_at,v_unit,v_total,v_valuation,v_reason,
    v_journal,v_movement,erp.current_app_user_id());
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('fg_unsourced_receipts_v1',v_id,'POST',erp.current_app_user_id(),v_reason);
  return erp._idempotency_complete('post_fg_unsourced_receipt_v1',p_client_request_id,jsonb_build_object(
    'receipt_id',v_id,'lot_id',v_lot,'product_id',v_product,'source_kind',v_kind,'qty_pcs',v_qty::integer,
    'unit_value',v_unit,'total_value',v_total,'valuation',v_valuation,'journal_entry_id',v_journal,
    'bs_resolution_id',v_resolution));
end
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_fg_unsourced_receipt_v1(p_receipt_id uuid, p_reason text, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- AX reversal: allowed only while the lot has no downstream use (sale, reservation, conversion). The inflow is
-- reversed, the lot is voided (it leaves the non-PO HPP target), the journal is reversed and a BS resolution created
-- by the receipt is removed, so the found BS is open again.
declare
  v erp.fg_unsourced_receipts_v1%rowtype;
  v_product uuid;v_hash text;v_cached jsonb;v_reversal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'FG_UNSOURCED_REVERSAL_REASON_REQUIRED'; end if;
  if p_client_request_id is null then raise exception 'FG_UNSOURCED_REQUEST_ID_REQUIRED'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('receipt_id',p_receipt_id,'reason',btrim(p_reason)));
  v_cached:=erp._idempotency_begin('reverse_fg_unsourced_receipt_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into v from erp.fg_unsourced_receipts_v1 where id=p_receipt_id for update;
  if v.id is null then raise exception 'FG_UNSOURCED_RECEIPT_NOT_FOUND'; end if;
  if v.status<>'POSTED' then raise exception 'FG_UNSOURCED_RECEIPT_ALREADY_REVERSED'; end if;
  select product_id into v_product from erp.fg_lots where id=v.lot_id for update;
  if erp.fg_lot_has_active_downstream(v.lot_id,'ADJUSTMENT','FG_UNSOURCED_RECEIPT',v.id) then
    raise exception 'FG_UNSOURCED_LOT_IN_USE: lot sudah dipakai transaksi lain; batalkan transaksi itu lebih dulu';
  end if;
  perform erp.reverse_fg_movement(v.movement_id,btrim(p_reason));
  update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=v.lot_id;
  if v.journal_entry_id is not null then v_reversal:=erp.reverse_journal(v.journal_entry_id,btrim(p_reason)); end if;
  perform set_config('erp.fg_unsourced_reversal','on',true);
  update erp.fg_unsourced_receipts_v1 set status='REVERSED',reversed_by=erp.current_app_user_id(),
    reversed_at=clock_timestamp(),reversal_reason=btrim(p_reason) where id=v.id;
  perform set_config('erp.fg_unsourced_reversal','off',true);
  if v.bs_resolution_id is not null then
    delete from erp.bs_resolutions where id=v.bs_resolution_id;
    if not found then raise exception 'FG_UNSOURCED_BS_RESOLUTION_MISSING: resolusi BS penerimaan ini sudah tidak ada'; end if;
    perform erp.refresh_bs_case_status(v.bs_case_id);
  end if;
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('fg_unsourced_receipts_v1',v.id,'REVERSE',erp.current_app_user_id(),btrim(p_reason));
  return erp._idempotency_complete('reverse_fg_unsourced_receipt_v1',p_client_request_id,jsonb_build_object(
    'receipt_id',v.id,'status','REVERSED','lot_id',v.lot_id,'reversal_journal_entry_id',v_reversal));
end
$function$;
CREATE OR REPLACE FUNCTION public.erp_preview_fg_unsourced_value_v1(p_product_id uuid, p_physical_at timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
  perform erp.require_owner_admin();
  return erp.fg_unsourced_valuation_v1(p_product_id,p_physical_at);
end
$function$;
CREATE OR REPLACE FUNCTION public.erp_post_fg_unsourced_receipt_v1(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.post_fg_unsourced_receipt_v1(p_payload,p_client_request_id);
$function$;
CREATE OR REPLACE FUNCTION public.erp_reverse_fg_unsourced_receipt_v1(p_receipt_id uuid, p_reason text, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.reverse_fg_unsourced_receipt_v1(p_receipt_id,p_reason,p_client_request_id);
$function$;
create trigger trg_guard_fg_unsourced_receipts_v1_immutable before update or delete on erp.fg_unsourced_receipts_v1
  for each row execute function erp.guard_fg_unsourced_receipt_immutable_v1();
create trigger trg_guard_fg_unsourced_receipts_v1_truncate before truncate on erp.fg_unsourced_receipts_v1
  for each statement execute function erp.guard_fg_unsourced_receipt_immutable_v1();
create trigger trg_guard_bs_resolution_fg_unsourced_v1 before update or delete on erp.bs_resolutions
  for each row execute function erp.guard_bs_resolution_fg_unsourced_v1();
revoke all on function erp.guard_fg_unsourced_receipt_immutable_v1() from public,anon,authenticated,service_role;
revoke all on function erp.guard_bs_resolution_fg_unsourced_v1() from public,anon,authenticated,service_role;
revoke all on function erp.fg_unsourced_valuation_v1(uuid,timestamp with time zone) from public,anon,authenticated,service_role;
revoke all on function erp.post_fg_unsourced_receipt_v1(jsonb,uuid) from public,anon,authenticated,service_role;
revoke all on function erp.reverse_fg_unsourced_receipt_v1(uuid,text,uuid) from public,anon,authenticated,service_role;
revoke all on function public.erp_preview_fg_unsourced_value_v1(uuid,timestamp with time zone) from public,anon;
grant execute on function public.erp_preview_fg_unsourced_value_v1(uuid,timestamp with time zone) to authenticated,service_role;
revoke all on function public.erp_post_fg_unsourced_receipt_v1(jsonb,uuid) from public,anon;
grant execute on function public.erp_post_fg_unsourced_receipt_v1(jsonb,uuid) to authenticated,service_role;
revoke all on function public.erp_reverse_fg_unsourced_receipt_v1(uuid,text,uuid) from public,anon;
grant execute on function public.erp_reverse_fg_unsourced_receipt_v1(uuid,text,uuid) to authenticated,service_role;
do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;
insert into erp.schema_migrations(version,description) values('v2.6.20ax','Finished goods without a production source: owner receipt with average HPP and reversal');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule')
), objects as (
 select 'FUNCTION:'||format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) k,
 jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text) end) v
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')
 union all
 select 'RELATION:'||format('%I.%I',nspname,relname),jsonb_build_array(relkind,pg_get_userbyid(relowner),
  case when relacl is null then null else array(select a::text from unnest(relacl)a order by a::text) end,
  relrowsecurity,relforcerowsecurity,relreplident,relpersistence,relispartition,reloptions)
 from relations
 union all
 select 'COLUMN:'||format('%I.%I.%I',r.nspname,r.relname,a.attname),
 jsonb_build_array((select count(*) from pg_attribute visible where visible.attrelid=a.attrelid and visible.attnum>0 and not visible.attisdropped and visible.attnum<=a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
  pg_get_expr(d.adbin,d.adrelid),a.attcollation::regcollation::text,
  case when a.attacl is null then null else array(select x::text from unnest(a.attacl)x order by x::text) end)
 from relations r join pg_attribute a on a.attrelid=r.oid and a.attnum>0 and not a.attisdropped
 left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
 union all
 select 'CONSTRAINT:'||format('%I.%I.%I',r.nspname,r.relname,c.conname),
 jsonb_build_array(c.contype,pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.connoinherit)
 from relations r join pg_constraint c on c.conrelid=r.oid
 union all
 select 'INDEX:'||format('%I.%I',r.nspname,c.relname),
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,i.indisexclusion,i.indisvalid,i.indisready,i.indisclustered,i.indisreplident,c.reloptions)
 from relations r join pg_index i on i.indrelid=r.oid join pg_class c on c.oid=i.indexrelid
 union all
 select 'TRIGGER:'||format('%I.%I.%I',r.nspname,r.relname,t.tgname),jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)
 from relations r join pg_trigger t on t.tgrelid=r.oid and not t.tgisinternal
 union all
 select 'POLICY:'||format('%I.%I.%I',r.nspname,r.relname,p.polname),jsonb_build_array(p.polcmd,p.polpermissive,
  array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(p.polroles)x order by 1),
  pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))
 from relations r join pg_policy p on p.polrelid=r.oid
 union all
 select 'VIEW:'||format('%I.%I',nspname,relname),to_jsonb(pg_get_viewdef(oid,false)) from relations where relkind in('v','m')
 union all
 select 'SEQUENCE:'||format('%I.%I',r.nspname,r.relname),jsonb_build_array(format_type(s.seqtypid,null),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle)
 from relations r join pg_sequence s on s.seqrelid=r.oid
 union all
 select 'SCHEMA:'||nspname,jsonb_build_array(pg_get_userbyid(nspowner),
  case when nspacl is null then null else array(select a::text from unnest(nspacl)a order by a::text) end)
 from pg_namespace where nspname in('erp','public')
 union all
 select 'DEFAULT_ACL:'||pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,
 to_jsonb(array(select a::text from unnest(d.defaclacl)a order by a::text))
 from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
 where n.nspname in('erp','public') or d.defaclnamespace=0
 union all
 select 'ENUM:'||format('%I.%I',n.nspname,t.typname),jsonb_build_array(pg_get_userbyid(t.typowner),
  (select jsonb_agg(e.enumlabel order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid))
 from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname in('erp','public') and t.typtype='e'
)
select coalesce(jsonb_object_agg(k,encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex')),'{}'::jsonb) from objects
) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>0 or fingerprint is distinct from '0000000000000000000000000000000000000000000000000000000000000000' then
  raise exception 'AX_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
commit;
