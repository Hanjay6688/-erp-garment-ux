#!/usr/bin/env python3
"""Build the AZ T1 family install: material recost corrections dated from the physical movement (owner, 24 Sep 2026).

Owner decisions (quoted): "WIP: setujui prinsip max(tanggal ekonomi invoice, tanggal fisik potong) saat tanggal ekonomi
masih terbuka. WIP belum ada pada 1-2 Sep, jadi koreksi -Rp10 tidak boleh membuat saldo WIP negatif di dua hari itu."
and, for the AS fixture that cuts on 22 Sep, "Ikut prinsip WIP" (the material-to-WIP revaluation follows the cutting
day, the invoice journal stays on the invoice date). Same family as AY (a value correction must not precede the
physical fact it corrects), so every branch of the material recost is dated the same way.

Finding: the supplier invoice journal (MATERIAL_SUPPLIER_INVOICE, date E) corrects MATERIAL_INVENTORY for the whole
received quantity; then erp.sync_material_cost_revaluation moves the correction of every consuming movement out of
MATERIAL_INVENTORY (to WIP for cutting, cutting returns and contractor issues, to ACCESSORY_RECOVERY_COGS for issued
accessories, to MATERIAL_PURCHASE_VARIANCE for supplier returns), and erp._cp6_sync_material_adjustment_revaluation does
the same for material adjustment documents, both on E. When the movement happened after E, WIP (or the other account)
receives the correction before the material was there and MATERIAL_INVENTORY loses it while the material is still in
stock: with a lower invoice price WIP is negative between E and the cutting day.

AZ changes only the date of those two postings (and, as their consequence, of the finished-PO residual WIP close below): D = greatest(E, business date of the movement's physical_at) (for an
adjustment document, of the document's physical_at) when E is open; when E is already closed every posting stays on E
exactly as before (one journal with economic date E that post_journal posts on the recognition day, the rule AY rev3
keeps). A physical date after today (the product allows a few minutes of clock skew) is capped at today. Amounts,
accounts, state and events are unchanged. Outside an invoice E is today and nothing moves; the residual close below is
changed on the invoice path only (independent review 24 Sep: its other callers pass other dates).
AZ rev2 (round seven, writer; handoff §23.7 and the independent review of AY rev7), same rule for the rest of the family:
  - pocket-fabric recost (erp.guard_pocket_period_v1): not before the period's allocation (its end day) while open;
  - opening WIP/BS value (erp.sync_initial_import_bs_value_v1): on a late invoice the change reaches each disposed BS piece
    on its disposal day (pro rata by pieces);
  - opening (non-PO) lots (erp.sync_non_po_product_hpp_to_gl_v2620f): on a late invoice the COGS/other legs follow each
    sale, return and adjustment day (per-lot HPP change x pieces), FG balancing;
  - accessory recost (erp.refresh_accessory_hpp_after_material_recost): an accrued lot's accessory HPP change enters WIP
    against the reimbursement variance, dated as the PO HPP sync dates it (it moved it out of WIP without a WIP debit);
  - batch partners: no change needed; the product keeps a cutting batch inside one PO (fixture AZ:BATCH_PARTNER_PO).
  Closed dates and every non-invoice caller keep their previous posting.
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW -> AX -> AY, not a release package.

Usage: python3 scripts/cp6_az_build.py            # writes supabase/dev/cp6_az_t1_family.sql
       python3 scripts/cp6_az_build.py --check
"""
from pathlib import Path
import hashlib,sys

ROOT=Path(__file__).resolve().parents[1]
AS=ROOT/'supabase/migrations/20260922210815_erp_v2_6_20as_cp6_event_dates_product_identity.sql'
AO=ROOT/'supabase/migrations/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql'
OUT=ROOT/'supabase/dev/cp6_az_t1_family.sql'
VERSION='v2.6.20az'

E_EXPR='coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()))'
CLOSED="""exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through)"""

# ---------------------------------------------------------------- erp.sync_material_cost_revaluation (AS)
REVAL_HEAD='CREATE OR REPLACE FUNCTION erp.sync_material_cost_revaluation(p_material_id uuid)'
REVAL_DECLARE_OLD="""  v_journal uuid;
begin
  perform erp.require_internal();
"""
REVAL_DECLARE_NEW="""  v_journal uuid;
  v_e date;
  v_closed boolean;
  v_date date;
begin
  perform erp.require_internal();
  -- AZ (owner, 24 Sep 2026): a correction is dated from the physical movement it corrects when the recost date E is
  -- open, D = greatest(E, business date of the movement); a closed E keeps every posting on E (post_journal posts it
  -- on the recognition day with economic date E), as before.
  v_e:="""+E_EXPR+""";
  v_closed:="""+CLOSED+""";
"""
REVAL_DIFF_OLD="""    if abs(v_diff)>0.005 then
      if v_diff>0 then"""
REVAL_DIFF_NEW="""    if abs(v_diff)>0.005 then
      v_date:=case when v_closed then v_e
        else least(greatest(v_e,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) end;
      if v_diff>0 then"""
REVAL_EVENT_OLD="values(p_material_id,r.id,"+E_EXPR+",v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)"
REVAL_EVENT_NEW="values(p_material_id,r.id,v_date,v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)"
REVAL_JOURNAL_OLD="v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,"+E_EXPR+","
REVAL_JOURNAL_NEW="v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,v_date,"

# ---------------------------------------------------------------- erp._cp6_sync_material_adjustment_revaluation (AO)
ADJ_HEAD='CREATE OR REPLACE FUNCTION erp._cp6_sync_material_adjustment_revaluation(p_adjustment uuid, p_material uuid)'
ADJ_DECLARE_OLD="declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;\nbegin"
ADJ_DECLARE_NEW="declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;v_e date;\nbegin"
ADJ_DATE_OLD=" v_event:=gen_random_uuid();v_date:="+E_EXPR+";"
ADJ_DATE_NEW=""" v_event:=gen_random_uuid();
 -- AZ: dated from the adjustment document's physical day when the recost date E is open; a closed E stays on E.
 v_e:="""+E_EXPR+""";
 v_date:=case when """+CLOSED+""" then v_e
   else least(greatest(v_e,(select erp._cp3_business_date(a.physical_at) from erp.material_adjustments a where a.id=p_adjustment)),
              erp._cp3_business_date(statement_timestamp())) end;"""


# ---------------------------------------------------------------- erp.sync_finished_po_wip_residual (AC)
# A consequence of AZ (and AY) the writer found before T2: the invoice path closes a FINISHED PO's residual WIP on E; with
# the revaluation on the cutting day and the HPP legs on the goods/sale days, a close on an earlier open E would leave the
# PO's WIP non-zero between E and those days. The close is therefore not dated before the PO's last WIP posting when the
# date is open; a closed date stays (post_journal posts it on the recognition day, as before).
RESIDUAL_AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
RESIDUAL_HEAD="CREATE OR REPLACE FUNCTION erp.sync_finished_po_wip_residual(p_po_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date, p_reason text DEFAULT 'Finished PO residual WIP close'::text)"
RESIDUAL_OLD='''  if abs(v_residual)<=0.005 then return; end if;
  insert into erp.po_wip_close_events'''
RESIDUAL_NEW='''  if abs(v_residual)<=0.005 then return; end if;
  -- AZ: on the invoice path only (a late supplier invoice), not before the PO's last WIP posting while the date is open,
  -- never after today; a closed date and every other caller (finish, laundry estimate, pocket) stay as before.
  if erp.invoice_recost_economic_date_v1() is not null and not exists(select 1 from erp.accounting_period_control c
                where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    select least(greatest(p_effective_date,coalesce(max(je.transaction_date),p_effective_date)),erp._cp3_business_date(statement_timestamp()))
      into p_effective_date
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED')
      and jl.po_id=p_po_id and jl.account_id=v_wip_account;
  end if;
  insert into erp.po_wip_close_events'''


# ================================================================ AZ rev2 (writer, 24 Sep 2026, round six): the rest of the family
# "a value correction must not be dated before the physical fact it corrects" (handoff §23.7, independent review of AY rev7).
AP=ROOT/'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql'
F20=ROOT/'supabase/migrations/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.sql'
TODAY="erp._cp3_business_date(statement_timestamp())"
def closed(expr):
    return ("exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and "
            +expr+"<=c.closed_through)")

# ---------------------------------------------------------------- erp.guard_pocket_period_v1 (AP): pocket-fabric recost
POCKET_HEAD="create or replace function erp.guard_pocket_period_v1() returns trigger"
POCKET_OLD=""" perform erp.sync_pocket_period_v1(v_pool,new.effective_date,'RECOST','Koreksi harga kain kantong');end loop;"""
POCKET_NEW=""" -- AZ: a pocket recost is not dated before the period's own allocation (its end day) while the date is open; a closed date
   -- keeps its economic date (post_journal posts it on the recognition day), a non-invoice recost stays on today.
   perform erp.sync_pocket_period_v1(v_pool,case when """+closed("new.effective_date")+""" then new.effective_date
     else least(greatest(new.effective_date,(select p.period_end from erp.pocket_periods p where p.id=v_pool)),"""+TODAY+""") end,
     'RECOST','Koreksi harga kain kantong');end loop;"""

# ---------------------------------------------------------------- erp.sync_initial_import_bs_value_v1 (AP): opening BS value
BSV_HEAD="create or replace function erp.sync_initial_import_bs_value_v1(p_item uuid,p_date date) returns void"
BSV_DECLARE_OLD="declare s erp.initial_import_production_sources%rowtype;v_qty integer;v_target numeric;v_prior numeric;v_delta numeric;v_event uuid;v_journal uuid;\nbegin"
BSV_DECLARE_NEW="declare s erp.initial_import_production_sources%rowtype;v_qty integer;v_target numeric;v_prior numeric;v_delta numeric;v_event uuid;v_journal uuid;\n d record;v_left numeric;v_part numeric;v_run numeric;v_done integer:=0;\nbegin"
BSV_OLD=""" v_delta:=v_target-v_prior;if v_delta=0 then return;end if;
 v_event:=gen_random_uuid();"""
BSV_NEW=""" v_delta:=v_target-v_prior;if v_delta=0 then return;end if;
 -- AZ: on a late supplier invoice with an open date the change reaches each disposed BS piece on the day it was disposed
 -- (bs_resolutions.physical_at), pro rata by pieces, never before the invoice date nor after today; the last day takes the
 -- remainder. Every other caller (the disposition trigger on its physical day, a closed date) posts once, as before.
 if erp.invoice_recost_economic_date_v1() is not null and v_qty>0 and not """+closed("p_date")+""" then
  v_left:=v_delta;v_run:=v_prior;
  for d in select least(greatest(p_date,erp._cp3_business_date(r.physical_at)),"""+TODAY+""") bday,sum(r.qty_pcs) q
    from erp.bs_resolutions r where r.bs_case_id=s.bs_case_id and r.source_rework_order_id is null
      and r.resolution_type not in('REWORK_SEWING','REWORK_LAUNDRY') group by 1 order by 1 loop
   v_done:=v_done+d.q;
   v_part:=case when v_done>=v_qty then v_left else round(v_delta*d.q/v_qty,2) end;
   v_left:=v_left-v_part;
   if v_part<>0 then
    v_event:=gen_random_uuid();
    v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,d.bday,'Nilai BS saldo awal yang dikeluarkan atau dikembalikan · tanggal pengeluaran BS',jsonb_build_array(
     jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_part,0),'credit',greatest(-v_part,0),'po_id',s.po_id),
     jsonb_build_object('mapping_key','WIP','debit',greatest(-v_part,0),'credit',greatest(v_part,0),'po_id',s.po_id)));
    insert into erp.initial_import_bs_value_events(id,opening_item_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
    values(v_event,p_item,least(v_done,v_qty),v_run,v_run+v_part,d.bday,v_journal,erp.current_app_user_id());
    v_run:=v_run+v_part;
   end if;
  end loop;
  if v_left<>0 then raise exception 'INITIAL_IMPORT_BS_VALUE_SPLIT_REMAINDER %',v_left;end if;
  return;
 end if;
 v_event:=gen_random_uuid();"""

# ---------------------------------------------------------------- erp.sync_non_po_product_hpp_to_gl_v2620f (20f): opening lots
NONPO_HEAD="create function erp.sync_non_po_product_hpp_to_gl_v2620f("
NONPO_DECLARE_OLD="""  v_lines jsonb:='[]'::jsonb;
begin"""
NONPO_DECLARE_NEW="""  v_lines jsonb:='[]'::jsonb;
  r record;v_acc jsonb:='{}'::jsonb;v_c numeric(20,2);v_o numeric(20,2);v_f numeric(20,2);
  v_sc numeric(20,2):=0;v_so numeric(20,2):=0;v_end date;v_ev uuid;v_rf numeric;v_rc numeric;v_ro numeric;
begin"""
NONPO_OLD="""  if abs(v_df)<=0.005 and abs(v_dc)<=0.005 and abs(v_do)<=0.005 then
    return;
  end if;
"""
NONPO_NEW="""  if abs(v_df)<=0.005 and abs(v_dc)<=0.005 and abs(v_do)<=0.005 then
    return;
  end if;

  -- AZ (handoff §23.7): on a late supplier invoice with an open date the COGS and other legs follow each piece: the change
  -- of a lot's HPP in this statement (per piece) times its pieces sold (sales, returns, their reversals) or out otherwise
  -- (adjustment, BS, relabel, their reversals) as of each day of those movements, never before the invoice date nor after
  -- today; each day posts the change of those balances, FG balancing, and the last day takes the exact remainder. The FG
  -- source leg of the opening lot itself (OPENING_HPP_SOURCE, at the invoice date) is unchanged: the lot exists since
  -- cutover. Every other caller and a closed date post one journal on the caller's date, as before.
  if erp.invoice_recost_economic_date_v1() is not null and (abs(v_dc)>0.005 or abs(v_do)>0.005)
     and not """+closed("p_effective_date")+""" then
    for r in
      with lots as(
        select fl.id,
          coalesce((select case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end
            from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)
          -- Independent review of AZ rev2 (3): against what the last opening-lot sync posted (its state is written after
          -- this call), so a second sync in the same statement does not count the first one's change again.
          -coalesce((select os.current_hpp from erp.opening_lot_hpp_gl_state os where os.lot_id=fl.id),
            (select case when coalesce(pv.qty_basis_pcs,0)>0 then pv.total_cost/pv.qty_basis_pcs else 0 end
            from erp.hpp_versions pv where pv.lot_id=fl.id and pv.calculated_at<statement_timestamp()
            order by pv.calculated_at desc,pv.version_no desc limit 1),0) dh
        from erp.fg_lots fl where fl.product_id=p_product_id and fl.po_id is null
          and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      ), ev as(
        select greatest(p_effective_date,least("""+TODAY+""",erp._cp3_business_date(m.physical_at))) d,l.dh,
          coalesce(o.movement_type,m.movement_type) k,m.qty_signed::numeric q
        from erp.fg_stock_movements m join lots l on l.id=m.lot_id and l.dh<>0
        left join erp.fg_stock_movements o on m.movement_type='REVERSAL' and o.id=m.reversal_of_id
        where coalesce(o.movement_type,m.movement_type) in('SALE','SALE_RETURN','ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')
      )
      select d,sum(sum(case when k in('SALE','SALE_RETURN') then -q*dh else 0 end)) over(order by d) c,
        sum(sum(case when k in('SALE','SALE_RETURN') then 0 else -q*dh end)) over(order by d) o
      from ev group by d order by d
    loop
      v_c:=round(r.c,2);v_o:=round(r.o,2);
      v_acc:=v_acc||jsonb_build_object(r.d::text,jsonb_build_object('c',v_c-v_sc,'o',v_o-v_so));
      v_sc:=v_c;v_so:=v_o;v_end:=greatest(coalesce(v_end,r.d),r.d);
    end loop;
    v_end:=coalesce(v_end,p_effective_date);
    v_acc:=v_acc||jsonb_build_object(v_end::text,jsonb_build_object(
      'c',coalesce((v_acc->(v_end::text)->>'c')::numeric,0)+v_dc-v_sc,
      'o',coalesce((v_acc->(v_end::text)->>'o')::numeric,0)+v_do-v_so));
    v_rf:=b.fg_value;v_rc:=b.cogs_value;v_ro:=b.other_out_value;
    for r in select key::date d,value v from jsonb_each(v_acc) order by 1 loop
      v_c:=(r.v->>'c')::numeric;v_o:=(r.v->>'o')::numeric;v_f:=-(v_c+v_o);
      continue when abs(v_c)<=0.005 and abs(v_o)<=0.005;
      v_lines:='[]'::jsonb;
      if abs(v_f)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY',
        'debit',greatest(v_f,0),'credit',greatest(-v_f,0),'product_id',p_product_id)); end if;
      if abs(v_c)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','COGS',
        'debit',greatest(v_c,0),'credit',greatest(-v_c,0),'product_id',p_product_id)); end if;
      -- The other bucket stays on the one account the single journal would use for the product's total other change.
      if abs(v_o)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key',
        case when v_do>0 then 'OTHER_EXPENSE' else 'OTHER_INCOME' end,
        'debit',greatest(v_o,0),'credit',greatest(-v_o,0),'product_id',p_product_id)); end if;
      v_ev:=gen_random_uuid();
      v_journal:=erp.post_journal('NON_PO_HPP_GL_SYNC_V2620F',v_ev,r.d,
        'Cumulative non-PO HPP redistribution · dated from the goods · '||p_reason,v_lines);
      insert into erp.non_po_hpp_gl_sync_events_v2620f(
        id,product_id,trigger_source_type,trigger_source_id,effective_date,
        old_fg_value,new_fg_value,fg_delta,old_cogs_value,new_cogs_value,cogs_delta,
        old_other_out_value,new_other_out_value,other_delta,journal_entry_id,reason,created_by
      ) values(
        v_ev,p_product_id,p_trigger_source_type,p_trigger_source_id,r.d,
        v_rf,v_rf+v_f,v_f,v_rc,v_rc+v_c,v_c,v_ro,v_ro+v_o,v_o,v_journal,p_reason,erp.current_app_user_id());
      v_rf:=v_rf+v_f;v_rc:=v_rc+v_c;v_ro:=v_ro+v_o;
    end loop;
    perform erp.assert_non_po_product_hpp_target_book_v2620f(p_product_id);
    return;
  end if;
"""

# ---------------------------------------------------------------- erp.refresh_accessory_hpp_after_material_recost (AC)
ACC_AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
ACC_HEAD="CREATE OR REPLACE FUNCTION erp.refresh_accessory_hpp_after_material_recost(p_material_id uuid, p_reason text DEFAULT 'Accessory historical moving-average recost'::text)"
ACC_DECLARE_OLD="""  v_po uuid;
begin"""
ACC_DECLARE_NEW="""  v_po uuid;
  v_rev uuid;v_old numeric;v_newtot numeric;v_d numeric;v_lot uuid;v_lot_po uuid;v_prod uuid;v_lotday date;v_e date;v_date date;
begin"""
ACC_OLD="""      insert into erp.fg_accessory_cost_revisions(snapshot_id,material_id,old_category_avg_cost,new_category_avg_cost,old_hpp_unit_cost,new_hpp_unit_cost,reason,changed_by)
      values(r.id,p_material_id,r.category_avg_cost_base_snapshot,v_new,r.hpp_unit_cost_base_snapshot,v_new,coalesce(nullif(trim(p_reason),''),'Accessory historical moving-average recost'),erp.current_app_user_id());
      update erp.fg_accessory_cost_snapshots
      set category_avg_cost_base_snapshot=v_new,hpp_unit_cost_base_snapshot=v_new
      where id=r.id;"""
ACC_NEW="""      insert into erp.fg_accessory_cost_revisions(snapshot_id,material_id,old_category_avg_cost,new_category_avg_cost,old_hpp_unit_cost,new_hpp_unit_cost,reason,changed_by)
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
      v_d:=round(coalesce(v_newtot,0)-coalesce(v_old,0),2);
      if abs(v_d)>0.005 and exists(select 1 from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
                                     and source_id=v_lot and status='POSTED') then
        select fl.po_id,fl.product_id,erp._cp3_business_date(fl.produced_at) into v_lot_po,v_prod,v_lotday from erp.fg_lots fl where fl.id=v_lot;
        v_e:=erp.invoice_recost_economic_date_v1();
        v_date:=case when v_e is null then """+TODAY+"""
                     when """+closed("v_e")+""" then v_e
                     else least(greatest(v_e,v_lotday),"""+TODAY+""") end;
        perform erp.post_journal('ACCESSORY_HPP_RECOST',v_rev,v_date,'Accessory HPP recost of an accrued lot: WIP against the reimbursement variance',
          jsonb_build_array(
            jsonb_build_object('mapping_key','WIP','debit',greatest(v_d,0),'credit',greatest(-v_d,0),'po_id',v_lot_po,'product_id',v_prod),
            jsonb_build_object('mapping_key','ACCESSORY_REIMBURSE_VARIANCE','debit',greatest(-v_d,0),'credit',greatest(v_d,0),'po_id',v_lot_po,'product_id',v_prod)));
      end if;"""

# erp._recalculate_material_cost_core is NOT changed: the native fixture AZ:BATCH_PARTNER_PO (T1 run 35992859006) showed the
# product refuses a cutting group of another PO in a cutting batch (validate_cutting_batch_link: "Cutting batch must belong
# to the same production order"), so every PO of a batch is already the PO whose groups used the material.

# ---------------------------------------------------------------- accrual reversals (AC, AT): the accessory recost goes too
# Independent review of AZ rev2 (4): QC reversal, rework reversal and initial-import WIP output reversal reverse the lot's
# ACCESSORY_REIMBURSE_ACCRUAL; the lot's ACCESSORY_HPP_RECOST journals (source: fg_accessory_cost_revisions) go with it.
def recost_reversal(lot,var,reason):
    return ("    -- AZ rev2: the lot's accessory HPP recost journals go with its accrual.\n"
            "    for "+var+" in select je.id from erp.journal_entries je join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id\n"
            "      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id\n"
            "      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id="+lot+" order by je.posting_at,je.id\n"
            "    loop perform erp.reverse_journal("+var+","+reason+"); end loop;\n")
RQC_HEAD="CREATE OR REPLACE FUNCTION erp.reverse_qc(p_qc_id uuid, p_reason text)"
RQC_OLD="""    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=l.id and payroll_status='UNALLOCATED';
"""
RQC_NEW="""    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
"""+recost_reversal('l.id','v_journal','p_reason')+"""    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=l.id and payroll_status='UNALLOCATED';
"""
RRW_HEAD="CREATE OR REPLACE FUNCTION erp.reverse_rework_completion(p_rework_order_id uuid, p_reason text)"
RRW_OLD="""    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=r.good_fg_lot_id and payroll_status='UNALLOCATED';
"""
RRW_NEW="""    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
"""+recost_reversal('r.good_fg_lot_id','v_journal','p_reason')+"""    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=r.good_fg_lot_id and payroll_status='UNALLOCATED';
"""
AT_MIG=ROOT/'supabase/migrations/20260923005153_erp_v2_6_20at_cp6_wip_temporal_identity.sql'
WIP_HEAD="CREATE OR REPLACE FUNCTION erp.complete_initial_import_wip_v1(p_payload jsonb)"
WIP_OLD="""  for v_movement in select id from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=v_prior.lot_id and status='POSTED' loop
   perform erp.reverse_journal(v_movement,v_reason);
  end loop;
"""
WIP_NEW=WIP_OLD+recost_reversal('v_prior.lot_id','v_movement','v_reason')


def function(path,head,subs,once=True):
    text=path.read_text()
    assert text.count(head)==1,(path.name,head)
    start=text.index(head);end=text.index('$function$;',start)+len('$function$;')
    body=text[start:end]
    for old,new in subs:
        assert body.count(old)==1,(head,old[:60])
        body=body.replace(old,new)
    if once:assert 'invoice_recost_economic_date_v1()' in body and body.count(E_EXPR)==1,(head,'E computed once')
    return body


def build():
    reval=function(AS,REVAL_HEAD,[(REVAL_DECLARE_OLD,REVAL_DECLARE_NEW),(REVAL_DIFF_OLD,REVAL_DIFF_NEW),
                                  (REVAL_EVENT_OLD,REVAL_EVENT_NEW),(REVAL_JOURNAL_OLD,REVAL_JOURNAL_NEW)])
    adj=function(AO,ADJ_HEAD,[(ADJ_DECLARE_OLD,ADJ_DECLARE_NEW),(ADJ_DATE_OLD,ADJ_DATE_NEW)])
    residual=function(RESIDUAL_AC,RESIDUAL_HEAD,[(RESIDUAL_OLD,RESIDUAL_NEW)],once=False)
    pocket=function(AP,POCKET_HEAD,[(POCKET_OLD,POCKET_NEW)],once=False)
    bsv=function(AP,BSV_HEAD,[(BSV_DECLARE_OLD,BSV_DECLARE_NEW),(BSV_OLD,BSV_NEW)],once=False)
    nonpo=function(F20,NONPO_HEAD,[(NONPO_DECLARE_OLD,NONPO_DECLARE_NEW),(NONPO_OLD,NONPO_NEW)],once=False).replace(NONPO_HEAD,'CREATE OR REPLACE FUNCTION erp.sync_non_po_product_hpp_to_gl_v2620f(',1)
    acc=function(ACC_AC,ACC_HEAD,[(ACC_DECLARE_OLD,ACC_DECLARE_NEW),(ACC_OLD,ACC_NEW)],once=False)
    rqc=function(ACC_AC,RQC_HEAD,[(RQC_OLD,RQC_NEW)],once=False)
    rrw=function(ACC_AC,RRW_HEAD,[(RRW_OLD,RRW_NEW)],once=False)
    wip=function(AT_MIG,WIP_HEAD,[(WIP_OLD,WIP_NEW)],once=False)
    parts=['-- CP6 AZ material recost corrections dated from the physical movement: T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_az_build.py from the AS/AO definitions; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax','v2.6.20ay'))<>4 then raise exception 'AZ_T1_REQUIRES_AV_AW_AX_AY'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') then raise exception 'AZ_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',reval,adj,residual,pocket,bsv,nonpo,acc,rqc,rrw,wip,
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of AZ (material recost corrections dated from the physical movement); not a release package');",'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_az_t1_family.sql is stale; rerun scripts/cp6_az_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
