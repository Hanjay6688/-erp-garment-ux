#!/usr/bin/env python3
"""Build the BA T1 family install: product fixes from the independent CP6 audit (writer handoff 25 Sep 2026) and the owner
decisions D02 and D03 (OWNER_CONFIRMED_CHAT, 25 Sep 2026, option A).

Every function is taken from the definition the chain currently runs (AR, AP, AV and CP5 19 migrations; AW and AZ T1 files) with
checked substitutions only, like the AY and AZ builders:
  A1 (CP6-09, P1) erp.post_opening_balance: an import batch may not post an opening item that another import batch already
     posted with the same identity. AR compared only import with legacy (the XOR on migration_batch_id), so two import
     batches of the same material, warehouse, quantity and cost doubled stock and value. Identity per balance type: plain
     material stock by material, warehouse and roll; finished goods by product, warehouse and grade (AR's rule); cash by
     account; WIP and BS without a PO source by AR's model/stage/holder rule. Distinct sources stay admissible: another
     warehouse, roll, product or grade; stock that both batches tie to their own uninvoiced receipt (the receipt identity
     is unique across batches); WIP and BS that both carry a PO source (a batch creates its own POs, PO numbers are
     unique). Party balances and advances keep their existing document identity checks. The check runs after AR's shared
     lock, so two sessions are refused the same way.
  A3 (CP6-02, P1) erp.complete_initial_import_wip_v1 COMPLETE: the output needs its pieces in the source stage on its date
     and on every later day (the remaining per date), so a completion dated before an earlier output's reversal cannot use
     the pieces the reversal returned later. A backdated completion that fits every later day stays allowed. On the day of a
     reversal the output is recorded after it, so the physical stage timeline stays non-negative within that day too.
  A10 (CP6-18, owner D03=A) same function: a product filled in on the opening WIP binds the output (the same product
     identity, i.e. its version on the output date; another product, brand, colour or size is refused). Without a product,
     the brand and colour given on the source row must match; the PO model and the size are matched as before. What was
     checked and what stayed unknown is recorded with the output in erp.initial_import_wip_output_identity_v1: unknown
     data is recorded as unknown, never as matched (D03: "Data yang belum diketahui tidak dianggap cocok otomatis").
     The new table's two product references are classified in the AV coverage registry (erp.assert_new_stock_cutoff_coverage_v1,
     class DERIVED), whose fail-closed check runs at the end of the install.
  A9 (CP6-07, owner D02=A) erp.manage_initial_prepayment_v1: an apply, refund, lowering correction or reversal that lowers
     the advance is refused when its remaining capacity on its date or any later day would be negative (read from the
     advance account lines of the advance's own events and payments, as the ledger shows it). The same owner rule for
     material stock (AUD-S04) is already enforced: the material recalculation (AO erp._recalculate_material_cost_core)
     refuses any movement that makes the effective history of a warehouse/roll negative
     (AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY; native BA probe 'before' run 36085934997); BA adds nothing
     there.
  A4 (CP6-03) erp.sync_material_cost_revaluation: the recost of a consuming movement is its value now minus what was
     posted for it, both in whole cents; the value now by differences of the rounded stock value before and after it
     (material_cost_history), the posted value by cumulative rounding inside its posting document (a cutting group posts one
     rounded total for its rolls). The movements that empty the stock take exactly the rest, so zero stock keeps zero value
     (a one-unit correction no longer leaves 0.01 in inventory). Reversed movements keep AZ rev2.1's rule.
  A6 (CP6-24) erp.close_accounting_through: closing the date that is already closed is refused (filings are immutable, a
     second close would file twice); a close after a reopen stays allowed.
  A5 (CP6-04) selectors: erp.get_bs_resolution_workspace_v1 lists every Laundry source that can still be claimed or used
     (deliveries without capacity are left out before any ordering; no 100-row cut), erp.get_initial_import_workspace_v1
     lists every batch not posted yet with the latest 50, and the open payrolls and advance targets of a batch in full.
     The pages keep their public facades and get a search box for long lists. Reviewed without change: the pocket rolls,
     materials and history and the accessory materials and history are searched on the server with a total count; the
     pocket periods list (newest 50) is an allocation history, not an open-item selector.
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW -> AX -> AY -> AZ, not a release package.

Usage: python3 scripts/cp6_ba_build.py            # writes supabase/dev/cp6_ba_t1_family.sql
       python3 scripts/cp6_ba_build.py --check
"""
from pathlib import Path
import hashlib,sys

ROOT=Path(__file__).resolve().parents[1]
AR=ROOT/'supabase/migrations/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql'
AP=ROOT/'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql'
AV=ROOT/'supabase/migrations/20260923110000_erp_v2_6_20av_cp6_identity_new_stock_cutoff.sql'
CP5=ROOT/'supabase/migrations/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql'
AW=ROOT/'supabase/dev/cp6_aw_t1_family.sql'
AZ=ROOT/'supabase/dev/cp6_az_t1_family.sql'
OUT=ROOT/'supabase/dev/cp6_ba_t1_family.sql'
VERSION='v2.6.20ba'

# ---------------------------------------------------------------- A1 erp.post_opening_balance (AR)
OPEN_HEAD='CREATE OR REPLACE FUNCTION erp.post_opening_balance(p_opening_id uuid)'
OPEN_DECLARE_OLD="""  v_product_at timestamptz;v_source erp.initial_import_production_sources%rowtype;v_bs uuid;
begin"""
OPEN_DECLARE_NEW="""  v_product_at timestamptz;v_source erp.initial_import_production_sources%rowtype;v_bs uuid;
  v_dup_type text;v_dup_batch text;
begin"""
OPEN_OLD="""    raise exception 'AR_OPENING_ROUTE_OVERLAP: saldo/stok awal sudah disahkan melalui jalur lain; rekonsiliasi sumber sebelum mengesahkan';
  end if;
"""
OPEN_NEW=OPEN_OLD+"""
  -- BA (audit A1, CP6-09): an import batch may not post an opening item another import batch already posted with the same
  -- identity (AR above compares only import with legacy). Plain material stock: material, warehouse and roll; finished
  -- goods: product, warehouse and grade; cash: account; WIP and BS without a PO source: AR's model/stage/holder rule.
  -- Distinct sources stay admissible: stock both batches tie to their own uninvoiced receipt (receipt identity is unique
  -- across batches) and WIP/BS both carrying a PO source (each batch creates its own, uniquely numbered POs). Party
  -- balances and advances keep their document identity checks. Runs after the shared lock above, like AR.
  if h.migration_batch_id is not null then
    select i.balance_type,ob.batch_code into v_dup_type,v_dup_batch
    from erp.opening_balance_items i
    join erp.opening_balance_items o on o.balance_type=i.balance_type
    join erp.opening_balance_headers oh on oh.id=o.opening_id
    join erp.migration_batches ob on ob.id=oh.migration_batch_id
    left join erp.products ip on ip.id=i.product_id
    left join erp.products op on op.id=o.product_id
    where i.opening_id=h.id and oh.id<>h.id and oh.status='POSTED'
      and oh.migration_batch_id is not null and oh.migration_batch_id<>h.migration_batch_id
      and case i.balance_type
        when 'CASH_BANK' then i.cash_account_id=o.cash_account_id
        when 'MATERIAL' then i.material_id=o.material_id
          and i.location_id=o.location_id
          and i.roll_id is not distinct from o.roll_id
          and not (exists(select 1 from erp.initial_import_receipt_lines rl where rl.opening_item_id=o.id)
            and exists(select 1 from erp.initial_import_opening_stock_sources ss
              join erp.migration_staging_rows x on x.batch_id=ss.batch_id and x.entity_type='UNINVOICED_RECEIPT'
                and x.normalized_payload->>'opening_source_key'=ss.source_key
              where ss.opening_item_id=i.id))
        when 'FINISHED_GOODS' then i.product_id=o.product_id and exists(
          select 1 from erp.fg_stock_movements fm
          where fm.source_type='OPENING_BALANCE_ITEM' and fm.source_id=o.id
            and fm.movement_type='OPENING'
            and fm.location_id=coalesce(i.location_id,v_default_fg_location)
            and fm.quality_grade=coalesce(i.quality_grade,'GRADE_A'))
        when 'WIP' then
          not (exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=i.id)
            and exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=o.id))
          and (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.stage is null or o.stage is null or i.stage=o.stage)
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
        when 'BS' then
          not (exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=i.id)
            and exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=o.id))
          and (i.product_id is null or o.product_id is null or i.product_id=o.product_id)
          and (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
          and (i.vendor_id is null or o.vendor_id is null or i.vendor_id=o.vendor_id)
        else false end
    order by i.id,oh.id limit 1;
    if v_dup_type is not null then
      raise exception 'BA_IMPORT_OPENING_ALREADY_POSTED: saldo % yang sama sudah dibukukan oleh batch impor %; tambahan untuk item yang sama dicatat lewat penyesuaian, bukan saldo awal kedua',v_dup_type,v_dup_batch;
    end if;
  end if;
"""

# ---------------------------------------------------------------- A3/A10 erp.complete_initial_import_wip_v1 (AZ)
WIP_HEAD='CREATE OR REPLACE FUNCTION erp.complete_initial_import_wip_v1(p_payload jsonb)'
WIP_DECLARE_OLD=""" v_reason text;v_hpp numeric;v_prior record;v_movement uuid;v_po_status text;v_op text:=coalesce(p_payload->>'operation','COMPLETE');
begin"""
WIP_DECLARE_NEW=""" v_reason text;v_hpp numeric;v_prior record;v_movement uuid;v_po_status text;v_op text:=coalesce(p_payload->>'operation','COMPLETE');
 v_floor integer;v_bound uuid;v_src jsonb;v_basis text;
begin"""
WIP_DATE_OLD="""    or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'date: tanggal hasil harus sejak cutover dan tidak di masa depan';end if;
"""
WIP_DATE_NEW=WIP_DATE_OLD+"""  -- BA (audit A3, CP6-02): the pieces must be in the source stage on the output date and on every later day; a completion
  -- dated before an earlier output's reversal cannot use the pieces that reversal returned later.
  select min(x.left_qty) into v_floor from (
    select s.qty_pcs
      -coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_outputs o
          where o.opening_item_id=i.id and erp._cp3_business_date(o.physical_at)<=d.day),0)
      +coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_output_reversals rv
          join erp.initial_import_wip_outputs o on o.id=rv.output_id
          where o.opening_item_id=i.id and erp._cp3_business_date(rv.physical_at)<=d.day),0) left_qty
    from (select v_date as day
          union select erp._cp3_business_date(o.physical_at) from erp.initial_import_wip_outputs o where o.opening_item_id=i.id
          union select erp._cp3_business_date(rv.physical_at) from erp.initial_import_wip_output_reversals rv
            join erp.initial_import_wip_outputs o on o.id=rv.output_id where o.opening_item_id=i.id) d
    where d.day>=v_date) x;
  if v_qty>v_floor then
    raise exception 'BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING: pada % atau sesudahnya hanya % pcs tersisa di tahap sumber; hasil bertanggal lebih awal tidak boleh memakai potongan yang baru kembali kemudian',v_date,v_floor;
  end if;
"""
WIP_PRODUCT_OLD="""  if v_product_count<>1 then raise exception 'AS_WIP_PRODUCT_AMBIGUOUS: SKU ada pada beberapa identitas produk; pilih merek atau identitas produk yang tepat';end if;
"""
WIP_PRODUCT_NEW=WIP_PRODUCT_OLD+"""  -- BA (audit A10, CP6-18; owner D03=A): a product filled in on the opening WIP binds its output (the same product identity,
  -- i.e. its version on the output date); another product, brand, colour or size is refused. Without a product the brand
  -- and colour the source row gives must match (the PO model and the size are matched above). The output records what
  -- was checked and what stayed unknown; unknown data is never recorded as matched.
  select coalesce(p.identity_root_id,p.id) into v_bound from erp.products p where p.id=i.product_id;
  if v_bound is not null then
    if not exists(select 1 from erp.products p where p.id=v_product and coalesce(p.identity_root_id,p.id)=v_bound) then
      raise exception 'BA_WIP_OUTPUT_PRODUCT_BOUND: saldo WIP awal ini terikat pada produk yang diisi di sumbernya; hasil tidak boleh menjadi produk, merek, warna, atau ukuran lain';
    end if;
    v_basis:='OPENING_PRODUCT';
  else
    select x.normalized_payload into v_src from erp.migration_staging_rows x where x.id=s.source_row_id;
    if exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id where p.id=v_product and (
        (nullif(btrim(v_src->>'brand_code'),'') is not null and lower(btrim(b.brand_code))<>lower(btrim(v_src->>'brand_code')))
        or (nullif(btrim(v_src->>'color_name'),'') is not null and lower(btrim(coalesce(p.color_name,'')))<>lower(btrim(v_src->>'color_name'))))) then
      raise exception 'BA_WIP_OUTPUT_SOURCE_MISMATCH: merek atau warna hasil tidak cocok dengan rincian WIP awal';
    end if;
    v_basis:=case when nullif(btrim(v_src->>'brand_code'),'') is null and nullif(btrim(v_src->>'color_name'),'') is null
      then 'ASSIGNED_AT_COMPLETION' else 'SOURCE_ATTRIBUTES' end;
  end if;
"""
WIP_AT_OLD="""  v_at:=erp.product_opening_physical_at(v_product,v_date);v_output:=gen_random_uuid();
"""
WIP_AT_NEW=WIP_AT_OLD+"""  -- BA (audit A3): on the day of a reversal the output is recorded after it, so the physical stage timeline never shows the
  -- pieces leaving before they came back (the dated check above counts that day's reversals).
  v_at:=greatest(v_at,(select max(rv.physical_at)+interval '1 microsecond' from erp.initial_import_wip_output_reversals rv
    join erp.initial_import_wip_outputs o on o.id=rv.output_id
    where o.opening_item_id=i.id and erp._cp3_business_date(rv.physical_at)=v_date));
"""
WIP_OUTPUT_OLD="""  insert into erp.initial_import_wip_outputs(id,opening_item_id,lot_id,qty_pcs,physical_at,reason,created_by)
   values(v_output,i.id,v_lot,v_qty,v_at,v_reason,erp.current_app_user_id());
"""
WIP_OUTPUT_NEW=WIP_OUTPUT_OLD+"""  insert into erp.initial_import_wip_output_identity_v1(output_id,basis,opening_product_id,output_product_id,checked,unknown,source_attributes)
   values(v_output,v_basis,i.product_id,v_product,
     case when v_basis='OPENING_PRODUCT' then array['PRODUCT_IDENTITY','PO_MODEL','SIZE']
       else array_remove(array['PO_MODEL','SIZE',case when nullif(btrim(v_src->>'brand_code'),'') is not null then 'BRAND' end,
         case when nullif(btrim(v_src->>'color_name'),'') is not null then 'COLOR' end],null) end,
     case when v_basis='OPENING_PRODUCT' then array[]::text[]
       else array_remove(array[case when nullif(btrim(v_src->>'brand_code'),'') is null then 'BRAND' end,
         case when nullif(btrim(v_src->>'color_name'),'') is null then 'COLOR' end,'PATTERN','MATERIAL'],null) end,
     jsonb_build_object('product_sku',p_payload->>'product_sku','brand_code',v_src->>'brand_code','color_name',v_src->>'color_name'));
"""

# ---------------------------------------------------------------- A9 erp.manage_initial_prepayment_v1 (AP)
ADV_HEAD='CREATE OR REPLACE FUNCTION erp.manage_initial_prepayment_v1(p_payload jsonb)'
ADV_OLD=""" insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('initial_import_prepayments',a.id,'UPDATE',jsonb_build_object('operation',v_op,'payment_id',v_payment,'event_id',v_id),erp.current_app_user_id(),v_reason);
"""
ADV_NEW=""" -- BA (audit A9, CP6-07; owner D02=A): what lowers the advance uses only the capacity it has on its own date and keeps every
 -- later day non-negative; a later correction does not fund an earlier refund or use.
 if v_op in('APPLY','REFUND') or (v_op in('CORRECT','REVERSE_EVENT') and v_delta<0) then
   if erp.initial_prepayment_dated_floor_v1(a.id,v_date)<0 then
     raise exception 'BA_ADVANCE_DATED_CAPACITY: sisa uang muka pada % dan tanggal sesudahnya tidak mencukupi; kapasitas dari tanggal yang lebih akhir tidak boleh dipakai lebih awal',v_date;
   end if;
 end if;
"""+ADV_OLD
FLOOR="""CREATE OR REPLACE FUNCTION erp.initial_prepayment_dated_floor_v1(p_advance_id uuid,p_from date)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_floor numeric;
begin
  -- BA (audit A9): the lowest remaining capacity of one advance on p_from and every later day, from the lines on its own
  -- account of its events and of its payments and their reversals (economic date), on top of its opening amount.
  with a as (select * from erp.initial_import_prepayments where id=p_advance_id),
  js as (
    select e.journal_entry_id id from erp.initial_import_prepayment_events e where e.advance_id=p_advance_id and e.journal_entry_id is not null
    union select j.id from erp.journal_entries j join erp.initial_import_prepayment_payments l on l.payment_id=j.source_id
      where l.advance_id=p_advance_id
    union select r.id from erp.journal_entries r join erp.journal_entries j on j.id=r.reversal_of_id
      join erp.initial_import_prepayment_payments l on l.payment_id=j.source_id where l.advance_id=p_advance_id),
  moves as (
    select je.economic_date as day,case when a.party_type='CUSTOMER' then jl.credit-jl.debit else jl.debit-jl.credit end as amount
    from js join erp.journal_entries je on je.id=js.id and je.status in('POSTED','REVERSED')
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    cross join a where jl.account_id=a.coa_account_id)
  select min(a.amount+coalesce((select sum(m.amount) from moves m where m.day<=d.day),0)) into v_floor
  from a cross join (select p_from as day union select m.day from moves m where m.day>p_from) d;
  return v_floor;
end;$function$;
revoke all on function erp.initial_prepayment_dated_floor_v1(uuid,date) from public,anon,authenticated,service_role;
"""

# ---------------------------------------------------------------- A5 selectors (CP6-04)
# BS Resolution lookups (CP5 erp.get_bs_resolution_workspace_v1): the sources that can still be claimed or used are open
# items, so all of them are listed (no 100-row cut; a delivery without capacity is left out before any ordering). The
# page keeps its two public facades; a long list gets a search box in the page.
BS_HEAD='create function erp.get_bs_resolution_workspace_v1('
BS_DELIVERY_OLD="""          where d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')
          group by d.id,d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,d.physical_at
          order by d.physical_at desc,d.id limit 100
        ) s),'[]'::jsonb),"""
BS_DELIVERY_NEW="""          where d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')
          group by d.id,d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,d.physical_at
        ) s where s.qty_claimable_pcs>0),'[]'::jsonb),"""
BS_RECEIPT_OLD="""          order by r.physical_at desc,r.id desc,rl.id desc limit 100
        ) s where s.qty_claimable_pcs>0),'[]'::jsonb),"""
BS_RECEIPT_NEW="""        ) s where s.qty_claimable_pcs>0),'[]'::jsonb),"""
BS_SETTLED_OLD="""          order by c.resolved_at desc,c.id desc limit 100
        ) s where s.available_qty>0 and s.available_amount>0),'[]'::jsonb)"""
BS_SETTLED_NEW="""        ) s where s.available_qty>0 and s.available_amount>0),'[]'::jsonb)"""
# Initial import workspace (AP erp.get_initial_import_workspace_v1): every batch not posted yet stays listed with the
# latest 50 of any status; the open payrolls and the open advance targets of a batch are listed in full.
IMPORT_HEAD='CREATE OR REPLACE FUNCTION erp.get_initial_import_workspace_v1(p_batch_id uuid DEFAULT NULL)'
IMPORT_RECENT_OLD=""" return jsonb_build_object('batch',v_batch,'recent',coalesce((select jsonb_agg(x order by x.created_at desc,x.id)
   from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches
     order by created_at desc,id limit 50) x),'[]'::jsonb));"""
IMPORT_RECENT_NEW=""" -- BA (audit A5, CP6-04): every batch not posted yet stays listed (an older editable draft is never cut off), with
 -- the latest 50 of any status.
 return jsonb_build_object('batch',v_batch,'recent',coalesce((select jsonb_agg(x order by x.created_at desc,x.id)
   from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches where status<>'POSTED'
     union select * from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches
       order by created_at desc,id limit 50) latest) x),'[]'::jsonb));"""
IMPORT_PAYROLL_OLD="""       order by p.period_end,p.id limit 100) x),'[]'::jsonb),"""
IMPORT_PAYROLL_NEW="""       ) x),'[]'::jsonb),"""
IMPORT_TARGET_OLD="""         select * from erp.initial_prepayment_targets_v1(a.id) where remaining_amount::numeric>0 order by target_date,id limit 100) t),'[]'::jsonb),"""
IMPORT_TARGET_NEW="""         select * from erp.initial_prepayment_targets_v1(a.id) where remaining_amount::numeric>0) t),'[]'::jsonb),"""

# ---------------------------------------------------------------- AV coverage registry (erp.assert_new_stock_cutoff_coverage_v1)
# The AV guard refuses any product reference it has not classified; the A10 provenance table adds two. Both are derived
# records of an opening WIP output: the stock fact is the output's fg_lots lot (class NEW_STOCK_FACT already).
COVER_HEAD='CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()'
COVER_OLD='''"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},'''
COVER_NEW=COVER_OLD+'''"erp.initial_import_wip_output_identity_v1.opening_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output: the product filled in on its opening item"},"erp.initial_import_wip_output_identity_v1.output_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output; the stock fact is its fg_lots lot"},'''

# ---------------------------------------------------------------- A4 erp.sync_material_cost_revaluation (AZ)
REVAL_HEAD='CREATE OR REPLACE FUNCTION erp.sync_material_cost_revaluation(p_material_id uuid)'
REVAL_DECLARE_OLD="""  v_would numeric(24,6);
  q record;
begin"""
REVAL_DECLARE_NEW="""  v_would numeric(24,6);
  q record;
  v_now numeric(24,2);
  v_posted numeric(24,2);
begin"""
REVAL_OLD="""    else
      v_target:=round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2);
    end if;
"""
REVAL_NEW="""    else
      -- BA (audit A4, CP6-03): the recost is the movement's value now minus what was posted for it, both in whole cents. Value
      -- now: difference of the rounded stock value before and after it (material_cost_history), so the movements that
      -- empty the stock take exactly the rest and zero stock keeps zero value. Posted: cumulative rounding inside its
      -- posting document (same source and movement type; a cutting group posts one rounded total for its rolls).
      select round(h.stock_after*h.average_after,2)-round(h.stock_before*h.average_before,2) into v_now
      from erp.material_cost_history h where h.movement_id=r.id;
      select round(sum(abs(x.qty_signed)*coalesce(x.original_unit_cost_snapshot,x.unit_cost_snapshot)),2)
        -coalesce(round(sum(abs(x.qty_signed)*coalesce(x.original_unit_cost_snapshot,x.unit_cost_snapshot))
            filter(where (x.physical_at,x.system_created_at,x.id)<(r.physical_at,r.system_created_at,r.id)),2),0)
        into v_posted
      from erp.material_stock_movements x
      where x.material_id=r.material_id and x.source_type=r.source_type and x.source_id=r.source_id
        and x.movement_type=r.movement_type and x.reversal_of_id is null
        and (x.physical_at,x.system_created_at,x.id)<=(r.physical_at,r.system_created_at,r.id);
      v_target:=case when v_now is null then round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2)
        else v_now-sign(r.qty_signed)*v_posted end;
    end if;
"""

# ---------------------------------------------------------------- A6 erp.close_accounting_through (AW)
CLOSE_HEAD='CREATE OR REPLACE FUNCTION erp.close_accounting_through(p_closed_through date, p_reason text)'
CLOSE_OLD="""  if v_old is not null and p_closed_through<v_old then
    raise exception 'Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai %',v_old;
  end if;
"""
CLOSE_NEW=CLOSE_OLD+"""  -- BA (audit A6, CP6-24): the date already closed files nothing new; filings are immutable, so a second close would file
  -- twice. A close after a reopen stays allowed.
  if v_old is not null and p_closed_through=v_old then
    raise exception 'CLOSE_ALREADY_CLOSED: periode sudah ditutup sampai %; tidak ada filing baru',v_old;
  end if;
"""

SCHEMA="""create table erp.initial_import_wip_output_identity_v1(
  output_id uuid primary key references erp.initial_import_wip_outputs(id),
  basis text not null check(basis in('OPENING_PRODUCT','SOURCE_ATTRIBUTES','ASSIGNED_AT_COMPLETION')),
  opening_product_id uuid references erp.products(id),
  output_product_id uuid not null references erp.products(id),
  checked text[] not null,
  unknown text[] not null,
  source_attributes jsonb not null,
  created_at timestamptz not null default statement_timestamp(),
  check((basis='OPENING_PRODUCT')=(opening_product_id is not null))
);
comment on table erp.initial_import_wip_output_identity_v1 is 'BA (audit A10, owner D03=A): why each opening WIP output got its product (OPENING_PRODUCT: the product filled in on the opening WIP; SOURCE_ATTRIBUTES: the brand/colour of its source row matched; ASSIGNED_AT_COMPLETION: no product, brand or colour on the source, the PO model and size matched), what was checked and what stayed unknown (never recorded as matched).';
alter table erp.initial_import_wip_output_identity_v1 enable row level security;
revoke all on erp.initial_import_wip_output_identity_v1 from public,anon,authenticated,service_role;"""

REPLACED=['erp.post_opening_balance(uuid)','erp.complete_initial_import_wip_v1(jsonb)','erp.manage_initial_prepayment_v1(jsonb)',
          'erp.sync_material_cost_revaluation(uuid)','erp.close_accounting_through(date,text)','erp.assert_new_stock_cutoff_coverage_v1()',
          'erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','erp.get_initial_import_workspace_v1(uuid)']
NEW_FUNCTIONS=['erp.initial_prepayment_dated_floor_v1(uuid,date)']
NEW_TABLES=['initial_import_wip_output_identity_v1']


def function(path,head,subs,end='$function$;'):
    text=path.read_text()
    assert text.count(head)==1,(path.name,head)
    start=text.index(head);stop=text.index(end,start)+len(end)
    body=text[start:stop]
    if end!='$function$;':body=body[:-len(end)]+'$function$;'
    for old,new in subs:
        assert body.count(old)==1,(head,old[:70],body.count(old))
        body=body.replace(old,new)
    return body


def build():
    opening=function(AR,OPEN_HEAD,[(OPEN_DECLARE_OLD,OPEN_DECLARE_NEW),(OPEN_OLD,OPEN_NEW)])
    wip=function(AZ,WIP_HEAD,[(WIP_DECLARE_OLD,WIP_DECLARE_NEW),(WIP_DATE_OLD,WIP_DATE_NEW),(WIP_PRODUCT_OLD,WIP_PRODUCT_NEW),
                              (WIP_AT_OLD,WIP_AT_NEW),(WIP_OUTPUT_OLD,WIP_OUTPUT_NEW)])
    advance=function(AP,ADV_HEAD,[(ADV_OLD,ADV_NEW)])
    cover=function(AV,COVER_HEAD,[(COVER_OLD,COVER_NEW)])
    bs=function(CP5,BS_HEAD,[(BS_DELIVERY_OLD,BS_DELIVERY_NEW),(BS_RECEIPT_OLD,BS_RECEIPT_NEW),(BS_SETTLED_OLD,BS_SETTLED_NEW)])
    bs='CREATE OR REPLACE FUNCTION'+bs[len('create function'):]
    imports=function(AP,IMPORT_HEAD,[(IMPORT_RECENT_OLD,IMPORT_RECENT_NEW),(IMPORT_PAYROLL_OLD,IMPORT_PAYROLL_NEW),(IMPORT_TARGET_OLD,IMPORT_TARGET_NEW)])
    reval=function(AZ,REVAL_HEAD,[(REVAL_DECLARE_OLD,REVAL_DECLARE_NEW),(REVAL_OLD,REVAL_NEW)])
    close=function(AW,CLOSE_HEAD,[(CLOSE_OLD,CLOSE_NEW)])
    parts=['-- CP6 BA audit closure (writer handoff 25 Sep 2026, owner D02/D03): T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_ba_build.py from the AR/AP/AV/CP5-19 migrations and the AW/AZ T1 files; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax','v2.6.20ay','v2.6.20az'))<>5 then raise exception 'BA_T1_REQUIRES_AV_AW_AX_AY_AZ'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regclass('erp.initial_import_wip_output_identity_v1') is not null then raise exception 'BA_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',SCHEMA,FLOOR.rstrip('\n'),opening,wip,advance,reval,close,cover,bs,imports,
           'do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;',
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of BA (CP6 audit closure: import identity, dated WIP remaining, WIP product binding, dated advance capacity, recost cents, selectors, single close filing); not a release package');",'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_ba_t1_family.sql is stale; rerun scripts/cp6_ba_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
