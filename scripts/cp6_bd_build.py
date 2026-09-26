#!/usr/bin/env python3
"""Build the BD T1 family install: priced laundry deliveries (LAU-05b: package, components with partial coverage, lump sum per
batch, minimum charge, scoped rates per model/size/colour) and the laundry policy settings LAU-DEC01..06 (owner decision
25 Sep 2026: every CR and every ALL state built and tested in CP6; policy rows are application settings with a fail-closed
default).

New objects come from scripts/cp6_bd_objects_{policy,master,pricing,import,invoice,router}.sql; every existing function is taken from the
definition the chain currently runs (AC/20 migrations, the AW, AY and BA T1 files) with checked substitutions only:
  L1 erp.save_laundry_qc_action_v1 (BA):
     POST_DELIVERY  inside the BD facade (context POST_PRICED_DELIVERY) the line takes the priced average rate (NULL while a
                    component price is unknown, status PENDING) and the priced charge lines are attached after the size lines;
                    outside it, a vendor/process that needs BD pricing is refused (BD_PRICING_REQUIRED) instead of being
                    priced at the base rate.
     POST_RECEIPT   a BD-priced delivery is received with the process it was priced for (BD_PROCESS_CHANGED otherwise) and
                    each size takes its exact share of the estimate (erp.bd_allocate_receipt_v1; the last return of a size
                    takes the residual).
  L2 erp.post_laundry_delivery (AC): a BD line with an unknown price keeps its NULL rate (no base-rate fill).
  L3 erp.desired_laundry_accrual (20) and erp.rebuild_po_hpp (AY): the uncosted part of a BD line is its estimate less the
     shares already taken by posted receipts (erp.bd_uncosted_estimate_v1; exactly the old formula for any other line); a BD
     line with an unknown price keeps the PO's HPP pending; a lot sourced from a BD receipt size takes that size's own amount.
  L4 erp.period_blockers_v1 (AW): BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN blocks close while a BD component price is unknown and
     the old LAUNDRY_PRICE_UNKNOWN does not already report the line.
  L5 erp.set_laundry_rate_owner_estimate_v1 (AW): refused for a BD line (its price is set per charge, SET_CHARGE_PRICE).
  L6 erp.validate_laundry_receipt_line (20): a receipt line of a priced delivery costs the sum of its exact size shares
     (ESTIMATED, the known part while a component price is unknown); the old qty x rate rule stays for every other line.
  L7 erp.cp6_lot_failed_wash_cost_v2620e (AJ): a failed-wash attempt's lot cost includes its invoice product variance.
  L9 erp.post_sale (AG): goods whose laundry price is still unknown are sold only if the owner set LAU-DEC04 ALLOW_PENDING.
  L8 erp.guard_cp6_vendor_invoice_receipt_on_post_v2620 (20): a payable posted by the BD invoice facade is checked against
     its BD document (same vendor and total, with lines) instead of baseline vendor_invoice_items; every other invoice is
     checked as before.
Laundry vendor invoices (scripts/cp6_bd_objects_invoice.sql, LAU-T16..T19, T21..T23): L3 also subtracts the estimate a posted
invoice line released from the accrual, adds its product-cost variance to HPP (PO, group and lot), and stops a fully invoiced
source from keeping the HPP pending.
ALL-W05 physical (scripts/cp6_bd_objects_import.sql, src/initialImportCatalogBD.json):
  L10 import pipeline (BC texts of erp.stage_migration_row, erp._validate_migration_batch_base, erp.finalize_migration_batch,
      erp.save_initial_import_action_v1, erp.get_initial_import_workspace_v1, erp.initial_import_revision_v1): the files
      OPENING_LAUNDRY_CLAIM and OPENING_LAUNDRY_UNINVOICED are validated and applied after BC's.
  L11 erp.complete_initial_import_wip_v1, erp.initial_import_production_rows_v1, erp.guard_initial_import_po_completion_v1 (BB):
      pieces held by a laundry claim are not in the remaining WIP (today and on every dated check of BA A3); pieces a resolved
      claim lost count as done when the PO finishes; WIP_OUTPUT takes the claim operations (OPEN_CLAIM, RECOVER_CLAIM,
      RESOLVE_CLAIM, CANCEL_CLAIM, REVERSE_CLAIM_EVENT) under the same locks and remaining check as a completion.
  L12 erp.get_wip_control_v1 (AP): an opening row whose pieces a laundry claim still holds unresolved is listed as active.
  L4 also reports BD_OPENING_LAUNDRY_PRICE_UNKNOWN: an opening uninvoiced record without an estimate, not yet fully billed.
D07 (not laundry; carried by BD as the next unreleased family, R12 handoff task 1): scripts/cp6_bd_objects_d07.sql replaces
  erp.run_v255_material_cost_integrity_checks() whole (its v2.5.5 text is not in a repository file: it comes with the restored
  AC runtime). MATERIAL_RECOST_GL_STATE_DRIFT keeps its name and severity and is reset from per movement to document level
  (per material, one cent per purchase document; adjustments from the v2.6.20t facts; a corrected movement with no recost at
  all is still flagged); MATERIAL_GL_VALUATION_MISMATCH is unchanged. It is a replaced function (captured and restored by the
  rollback), not a new one, so it stays out of objects().
D09 (owner 26 Sep 2026, ACC-C12 option a; not laundry, carried by BD): scripts/cp6_bd_objects_d09.sql (table
  erp.bd_custody_sources_v1, erp.bd_custody_source_identity_v1) and checked substitutions of the BC texts of
  erp.bc_check_import_row_v1 (every OPENING_ACCESSORY_CUSTODY row names its source, count sheet + line or source lot; the same
  source is refused under any custody key, BC_C12_SAME_SOURCE) and erp.bc_apply_imports_v1 (the source is recorded with the
  goods). The file's fields come from the _extend part of src/initialImportCatalogBD.json.
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW..BA -> BB -> BC, not a release package.

Usage: python3 scripts/cp6_bd_build.py            # writes supabase/dev/cp6_bd_t1_family.sql
       python3 scripts/cp6_bd_build.py --check
"""
from pathlib import Path
import hashlib,json,re,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cp6_bc_build import last_definition,substitute
import cp6_bc_build as bc

M20=ROOT/'supabase/migrations/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql'
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
AW=ROOT/'supabase/dev/cp6_aw_t1_family.sql'
AY=ROOT/'supabase/dev/cp6_ay_t1_family.sql'
BA=ROOT/'supabase/dev/cp6_ba_t1_family.sql'
OBJECTS=[ROOT/f'scripts/cp6_bd_objects_{p}.sql' for p in ('policy','master','pricing','import','invoice','d09','router')]
D07=ROOT/'scripts/cp6_bd_objects_d07.sql'
BB=ROOT/'supabase/dev/cp6_bb_t1_family.sql'
BC=ROOT/'supabase/dev/cp6_bc_t1_family.sql'
CATALOG_BD=ROOT/'src/initialImportCatalogBD.json'
NEW_ENTITIES=['OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED']
AJ=ROOT/'supabase/migrations/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.sql'
OUT=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
VERSION='v2.6.20bd'

# ---------------------------------------------------------------- L1 laundry facade (BA)
DELIVERY_RATE_OLD='''    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
'''
DELIVERY_RATE_NEW='''    if coalesce((erp.bd_context_v1()).action,'')='POST_PRICED_DELIVERY' then
      -- BD (LAU-05b): the BD facade priced this delivery; the line keeps the exact average rate when every price is known and
      -- NULL while a component price is unknown (the charge lines are attached below).
      v_rate:=((erp.bd_context_v1()).pricing->>'avg_rate')::numeric;v_rate_count:=1;
    elsif erp.bd_vendor_needs_pricing_v1(v_vendor_id,v_process_id) then
      raise exception 'BD_PRICING_REQUIRED: vendor ini memakai harga paket/komponen/borongan/minimum/tarif khusus; kirim lewat tab Harga & tagihan di halaman Laundry (Kirim dengan harga)';
    else
'''+'\n'.join('  '+l if l else l for l in DELIVERY_RATE_OLD.rstrip('\n').split('\n'))+'''
    end if;
'''
DELIVERY_STATUS_OLD="      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,'ESTIMATED',\n"
DELIVERY_STATUS_NEW="      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,case when v_rate is null then 'PENDING' else 'ESTIMATED' end,\n"
DELIVERY_ATTACH_OLD='''    ) select v_delivery_line_id,v_batch_id,x.size_id,x.qty_sent_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
'''
DELIVERY_ATTACH_NEW=DELIVERY_ATTACH_OLD+'''    -- BD: the priced charge lines and per-size estimates of this delivery (only inside the BD facade's context).
    perform erp.bd_attach_delivery_pricing_v1(v_delivery_line_id);
'''
RECEIPT_RATE_OLD='''    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_delivery.physical_at
      and(r.effective_to is null or r.effective_to>v_delivery.physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative actual Laundry rate must be effective for this vendor/process/time; found % (rate of the send time)',v_rate_count;
    end if;
'''
RECEIPT_RATE_NEW='''    if exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_id=v_delivery.id) then
      -- BD (LAU-05b): a priced delivery is received at its own exact estimate (erp.bd_allocate_receipt_v1 below), with the
      -- process it was priced for; its rate snapshot is the priced average (NULL while a component price is unknown).
      if v_process_id is distinct from v_delivery.target_wash_process_id then
        raise exception 'BD_PROCESS_CHANGED: kiriman dengan harga paket/komponen/borongan hanya diterima dengan proses yang dihargai saat kirim';
      end if;
      select dl.estimated_rate_snapshot into v_rate from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
      v_rate_count:=1;
    else
'''+'\n'.join('  '+l if l else l for l in RECEIPT_RATE_OLD.rstrip('\n').split('\n'))+'''
    end if;
'''
RECEIPT_ALLOC_OLD='''    insert into erp.laundry_receipt_bs_product_allocations(
      receipt_line_id,product_id,qty_bs,notes,created_by
    ) select v_receipt_line_id,x.bs_product_id,sum(x.qty_bs_laundry)::integer,
        'CP6 immutable Laundry-BS product/size declaration',v_actor
'''
RECEIPT_ALLOC_NEW='''    -- BD: each size of a priced delivery takes its exact share of the estimate; the receipt line's cost is their sum.
    perform erp.bd_allocate_receipt_v1(v_receipt_line_id);
'''+RECEIPT_ALLOC_OLD
RECEIPT_RESPONSE_OLD="      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),\n      'cost_status','ESTIMATED_UNBILLED','accrual_effect'"
RECEIPT_RESPONSE_NEW=("      'rate_per_pcs',v_rate,'actual_cost',coalesce((select sum(ba.amount) from erp.bd_laundry_receipt_allocations_v1 ba\n"
                      "        where ba.receipt_line_id=v_receipt_line_id),round(v_total*v_rate,2)),\n      'cost_status','ESTIMATED_UNBILLED','accrual_effect'")
FACADE_SUBS=[(DELIVERY_RATE_OLD,DELIVERY_RATE_NEW),(DELIVERY_STATUS_OLD,DELIVERY_STATUS_NEW),(DELIVERY_ATTACH_OLD,DELIVERY_ATTACH_NEW),
             (RECEIPT_RATE_OLD,RECEIPT_RATE_NEW),(RECEIPT_ALLOC_OLD,RECEIPT_ALLOC_NEW),(RECEIPT_RESPONSE_OLD,RECEIPT_RESPONSE_NEW)]

# ---------------------------------------------------------------- L2 delivery posting (AC)
POST_DELIVERY_SUBS=[("    if v_rate is null and h.target_wash_process_id is not null then\n",
                     "    -- BD: a priced line with an unknown component price keeps its NULL rate (never the base rate).\n"
                     "    if v_rate is null and h.target_wash_process_id is not null\n"
                     "       and not exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_line_id=r.id) then\n")]

# ---------------------------------------------------------------- L3 accrual and HPP
ACCRUAL_SUBS=[("      coalesce(sum(lrl.actual_cost) filter(\n        where lr.status='POSTED' and lrl.actual_cost_status='ESTIMATED'\n",
               "      -- BD: less the estimate a posted laundry invoice line has already replaced (erp.bd_released_estimate_v1).\n"
               "      coalesce(sum(lrl.actual_cost-erp.bd_released_estimate_v1(lrl.id)) filter(\n        where lr.status='POSTED' and lrl.actual_cost_status='ESTIMATED'\n"),
              ("    select coalesce(sum(rl.actual_cost),0)::numeric amount\n    from erp.laundry_failed_wash_attempts a\n",
               "    select coalesce(sum(rl.actual_cost-erp.bd_released_estimate_v1(rl.id)),0)::numeric amount\n    from erp.laundry_failed_wash_attempts a\n"),
              ("    select\n      ldl.qty_sent_pcs,\n      ldl.estimated_rate_snapshot,","    select\n      ldl.id,\n      ldl.qty_sent_pcs,\n      ldl.estimated_rate_snapshot,"),
              ("      +greatest(qty_sent_pcs-costed_qty,0)*coalesce(estimated_rate_snapshot,0)\n",
               "      -- BD: a priced line's estimate less the shares taken by posted receipts; the old formula for any other line.\n"
               "      +erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,costed_qty,estimated_rate_snapshot)\n")]
REBUILD_SUBS=[
    ("\n           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost,\n"
     "           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED')) as has_pending_receipt\n",
     "\n           -- BD: plus the product-cost variance of posted laundry invoice lines; a fully invoiced source is no longer pending.\n"
     "           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0)+erp.bd_product_variance_v1(lrl.id) else 0 end),0) as actual_cost,\n"
     "           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED') and not erp.bd_receipt_invoiced_v1(lrl.id)) as has_pending_receipt\n"),
    ("\n               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost\n",
     "\n               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0)+erp.bd_product_variance_v1(lrl.id) else 0 end),0) as actual_cost\n"),
    ("  select v_laundry+coalesce(sum(rl.actual_cost),0)\n","  select v_laundry+coalesce(sum(rl.actual_cost+erp.bd_product_variance_v1(rl.id)),0)\n"),
    ("      select v_group_laundry+coalesce(sum(rl.actual_cost),0)\n","      select v_group_laundry+coalesce(sum(rl.actual_cost+erp.bd_product_variance_v1(rl.id)),0)\n"),
    ("    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED'\n  );\n",
     "    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED' and not erp.bd_receipt_invoiced_v1(rl.id)\n  );\n"),
    ("  select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0),\n"
     "         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual),false)\n",
     "  -- BD: uncosted part of a priced line by its exact shares; an unknown component price keeps the HPP pending.\n"
     "  select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0),\n"
     "         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual or not erp.bd_line_complete_v1(id)),false)\n"),
    ("      select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0)\n"
     "      into v_group_laundry from dl;\n",
     "      select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0)\n"
     "      into v_group_laundry from dl;\n"),
    ("            then rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)\n",
     "            -- BD: a lot from a priced receipt size takes that size's own amount (sizes may be priced differently).\n"
     "            then coalesce((select ba.amount/nullif(ba.qty,0) from erp.bd_laundry_receipt_allocations_v1 ba where ba.receipt_batch_size_line_id=rx.id),\n"
     "              rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0))\n"
     "              +erp.bd_product_variance_v1(rl.id)/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)\n")]

# ---------------------------------------------------------------- L7 failed-wash lot cost (AJ): plus invoice product variance
ATTEMPT_SUBS=[("    coalesce(rl.actual_cost,a.qty_attempted_pcs*coalesce(rl.actual_rate_snapshot,0))\n      *(ax.qty_attempted_pcs::numeric/nullif(a.qty_attempted_pcs,0)) size_cost,\n",
               "    -- BD: plus the product-cost variance of posted laundry invoice lines on the attempt.\n"
               "    (coalesce(rl.actual_cost,a.qty_attempted_pcs*coalesce(rl.actual_rate_snapshot,0))+erp.bd_product_variance_v1(rl.id))\n"
               "      *(ax.qty_attempted_pcs::numeric/nullif(a.qty_attempted_pcs,0)) size_cost,\n")]

# ---------------------------------------------------------------- L4 close blocker
BLOCKER_ANCHOR="  -- LAUNDRY: a delivery rate that is not a finite non-negative number is not a known price (P-02).\n"
BLOCKER_NEW='''  -- BD (LAU-05b, LAU-T12): a component price of a priced delivery still unknown on or before the date, reported here when
  -- LAUNDRY_PRICE_UNKNOWN does not (every piece already returned and costed at the known part only).
  return query
  select 'LAUNDRY'::text,'BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',bp.delivery_line_id,'po_id',ld.po_id,
      'unknown_charges',(select count(*) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=bp.delivery_line_id and c.rate_status='UNKNOWN')),
    format('Harga komponen laundry kiriman %s belum diketahui; isi harga komponen di halaman harga laundry.',ld.delivery_number)
  from erp.bd_laundry_priced_lines_v1 bp
  join erp.laundry_delivery_lines ldl on ldl.id=bp.delivery_line_id
  join erp.laundry_deliveries ld on ld.id=bp.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED' and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
  where not bp.total_complete and ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and not(ldl.estimated_rate_snapshot is null and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0);

  -- BD (ALL-W05): laundry work returned before cutover whose value is still unknown (no estimate, not fully billed).
  return query
  select 'LAUNDRY'::text,'BD_OPENING_LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,u.receipt_date,
    jsonb_build_object('opening_uninvoiced_id',u.id,'document_number',u.document_number,'vendor_id',u.vendor_id,'category',u.category,'qty',u.qty),
    format('Nilai laundry saldo awal %s (%s) belum diketahui; isi estimasi atau posting invoice vendornya.',u.document_number,u.category)
  from erp.bd_opening_laundry_uninvoiced_v1 u
  where u.estimated_amount is null and u.receipt_date<=p_through and not erp.bd_opening_invoiced_v1(u.id);

'''+BLOCKER_ANCHOR
BLOCKER_SUBS=[(BLOCKER_ANCHOR,BLOCKER_NEW)]

# ---------------------------------------------------------------- L5 owner estimate
ESTIMATE_SUBS=[("  if v_line.estimated_rate_snapshot is not null then raise exception 'LAUNDRY_ESTIMATE_RATE_ALREADY_KNOWN'; end if;\n",
                "  if v_line.estimated_rate_snapshot is not null then raise exception 'LAUNDRY_ESTIMATE_RATE_ALREADY_KNOWN'; end if;\n"
                "  -- BD: a priced delivery's unknown price is set per charge line (SET_CHARGE_PRICE), never as one flat rate.\n"
                "  if exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_line_id=v_line.id) then\n"
                "    raise exception 'BD_USE_CHARGE_PRICE: kiriman ini dihargai per komponen; isi harga komponen yang belum diketahui di halaman harga laundry';\n"
                "  end if;\n")]

# ---------------------------------------------------------------- L8 vendor invoice status guard (20)
GUARD_OLD='''  if not(
    (old.status='DRAFT' and new.status='POSTED')
    or (old.status='POSTED' and new.status='REVERSED')
  ) then return new; end if;
'''
GUARD_NEW=GUARD_OLD+'''  -- BD (LAU-05b): a laundry invoice posted by the BD facade bills its receipts through erp.bd_laundry_invoice_lines_v1
  -- (partial quantities, categories, corrections), not through vendor_invoice_items; its payable must match its BD document.
  if exists(select 1 from erp.bd_laundry_invoices_v1 b where b.id=new.id) then
    if not exists(select 1 from erp.bd_laundry_invoices_v1 b where b.id=new.id and b.vendor_id=new.vendor_id and b.header_total=new.total_amount
        and exists(select 1 from erp.bd_laundry_invoice_lines_v1 l where l.invoice_id=b.id)) then
      raise exception 'BD_VENDOR_INVOICE_MISMATCH: invoice vendor laundry tidak cocok dengan dokumen BD-nya';
    end if;
    return new;
  end if;
'''


def invoice_guard():
    text=M20.read_text()
    head='create function erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()'
    assert text.count(head)==1
    start=text.index(head);stop=text.index('$function$;',start)+len('$function$;')
    body='CREATE OR REPLACE FUNCTION'+text[start+len('create function'):stop]
    return substitute(body,[(GUARD_OLD,GUARD_NEW)],'invoice guard')


# ---------------------------------------------------------------- L9 sale posting (AG): LAU-04 / LAU-DEC04
AG=ROOT/'supabase/migrations/20260916050822_erp_v2_6_20ag_cp6_sale_reservation_lineage.sql'
SALE_SUBS=[("  update erp.sales_headers set status='POSTED' where id=h.id;\n  if abs(v_sales)>0.005 then\n",
            "  -- BD (LAU-04, LAU-DEC04): goods whose laundry price is still unknown are sold only if the owner allows it.\n"
            "  perform erp.bd_assert_sale_laundry_known_v1(h.id);\n"
            "  update erp.sales_headers set status='POSTED' where id=h.id;\n  if abs(v_sales)>0.005 then\n")]


# ---------------------------------------------------------------- L6 receipt line cost
RECEIPT_LINE_OLD='''  if new.actual_cost_status='FINAL' and new.actual_cost is not null then
    return new;
  end if;
'''
RECEIPT_LINE_NEW=RECEIPT_LINE_OLD+'''  -- BD: a receipt line of a priced delivery costs the exact shares of its sizes (erp.bd_allocate_receipt_v1), not qty x rate.
  if exists(select 1 from erp.bd_laundry_receipt_allocations_v1 a where a.receipt_line_id=new.id) then
    new.actual_cost:=(select sum(a.amount) from erp.bd_laundry_receipt_allocations_v1 a where a.receipt_line_id=new.id);
    new.actual_cost_status:='ESTIMATED';
    return new;
  end if;
'''
RECEIPT_LINE_SUBS=[(RECEIPT_LINE_OLD,RECEIPT_LINE_NEW)]

# ---------------------------------------------------------------- L10 import pipeline (BC texts)
BC_LIST="'OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY'"
BD_LIST=BC_LIST+','+bc.entities(NEW_ENTITIES)
STAGE_SUBS=[(BC_LIST+") then\n    raise exception 'Unsupported migration entity_type %'",BD_LIST+") then\n    raise exception 'Unsupported migration entity_type %'")]
BASE_SUBS=[(BC_LIST+")\n",BD_LIST+")\n")]
FINAL_SUBS=[(BC_LIST+") and posted_entity_id is null)",BD_LIST+") and posted_entity_id is null)")]
ROUTER_SUBS=[("     perform erp.bc_validate_imports_v1(b.id);\n","     perform erp.bc_validate_imports_v1(b.id);\n     perform erp.bd_validate_imports_v1(b.id);\n"),
             ("       perform erp.bc_apply_imports_v1(b.id);\n","       perform erp.bc_apply_imports_v1(b.id);\n       perform erp.bd_apply_imports_v1(b.id);\n")]
WS_SUBS=[("||erp.bc_import_workspace_v1(b.id);","||erp.bc_import_workspace_v1(b.id)||erp.bd_import_workspace_v1(b.id);")]
REV_SUBS=[("   'bc',erp.bc_import_revision_part_v1(p_batch_id)\n )::text","   'bc',erp.bc_import_revision_part_v1(p_batch_id),\n   'bd',erp.bd_import_revision_part_v1(p_batch_id)\n )::text")]

# ---------------------------------------------------------------- L11 opening WIP remaining (BB texts)
COMPLETE_SUBS=[
    (" select s.qty_pcs-coalesce(sum(o.qty_pcs),0)-erp.bb_wip_split_active_qty_v1(i.id) into v_remaining",
     " select s.qty_pcs-coalesce(sum(o.qty_pcs),0)-erp.bb_wip_split_active_qty_v1(i.id)-erp.bd_opening_claim_held_qty_v1(i.id) into v_remaining"),
    (" if v_op in('PICKUP','REVERSE_PICKUP','REVERSE_SPLIT') then return erp.bb_manage_opening_wip_v1(p_payload,s.opening_item_id);end if;\n",
     " if v_op in('PICKUP','REVERSE_PICKUP','REVERSE_SPLIT') then return erp.bb_manage_opening_wip_v1(p_payload,s.opening_item_id);end if;\n"
     " -- BD (ALL-W05): a laundry claim on opening WIP at a laundry vendor (open, recover, resolve, cancel, reverse an event).\n"
     " if v_op in('OPEN_CLAIM','RECOVER_CLAIM','RESOLVE_CLAIM','CANCEL_CLAIM','REVERSE_CLAIM_EVENT') then\n"
     "  return erp.bd_manage_opening_claim_v1(p_payload,s.opening_item_id);end if;\n"),
    ("      -erp.bb_wip_split_net_asof_v1(i.id,d.day) left_qty\n",
     "      -erp.bb_wip_split_net_asof_v1(i.id,d.day)-erp.bd_opening_claim_held_asof_v1(i.id,d.day) left_qty\n"),
    ("          union select x.day from erp.bb_wip_split_days_v1(i.id) x(day)) d\n",
     "          union select x.day from erp.bb_wip_split_days_v1(i.id) x(day)\n          union select x.day from erp.bd_opening_claim_days_v1(i.id) x(day)) d\n")]
ROWS_SUBS=[("    s.qty_pcs-case when s.bs_case_id is null then coalesce(o.qty,0)+erp.bb_wip_split_active_qty_v1(s.opening_item_id) else coalesce(br.qty,0) end,",
            "    s.qty_pcs-case when s.bs_case_id is null then coalesce(o.qty,0)+erp.bb_wip_split_active_qty_v1(s.opening_item_id)+erp.bd_opening_claim_held_qty_v1(s.opening_item_id) else coalesce(br.qty,0) end,"),
           ("'bb',erp.bb_wip_row_part_v1(s.opening_item_id),","'bb',erp.bb_wip_row_part_v1(s.opening_item_id),'bd',erp.bd_wip_row_part_v1(s.opening_item_id),")]
# ---------------------------------------------------------------- L12 WIP status (AP): an opening row with an open claim is active
AP_MIG=ROOT/'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql'
WIP_CONTROL_SUBS=[("     where p_pattern_id is null and (v_filter='ALL' or ((x->>'remaining_qty_pcs')::integer>0)=(v_filter='ACTIVE'))\n",
                   "     where p_pattern_id is null and (v_filter='ALL' or ((x->>'remaining_qty_pcs')::integer>0\n"
                   "       -- BD (ALL-W05): pieces a laundry claim still holds unresolved keep the row active.\n"
                   "       or coalesce((x->'bd'->>'held_qty_pcs')::integer-(x->'bd'->>'lost_qty_pcs')::integer,0)>0)=(v_filter='ACTIVE'))\n")]
PO_GUARD_SUBS=[("      +erp.bb_wip_split_active_qty_v1(s.opening_item_id) end\n",
                "      +erp.bb_wip_split_active_qty_v1(s.opening_item_id)+erp.bd_opening_claim_lost_qty_v1(s.opening_item_id) end\n")]


def catalog():
    base=bc.catalog();extra=json.loads(CATALOG_BD.read_text())
    extend=extra.pop('_extend',{})
    assert not set(base)&set(extra),'BD_CATALOG_OVERLAP'
    # D09: the count sheet / source lot fields of the opening accessory custody file (after its own fields).
    for entity,more in extend.items():
        assert entity in base and not set(more['fields'])&set(base[entity]['fields']),('BD_CATALOG_EXTEND',entity)
        base[entity]['fields'].update(more['fields'])
    for e in NEW_ENTITIES:assert e in extra,('BD_CATALOG_ENTITY_MISSING',e)
    return {**base,**extra}


def router():
    body=substitute(last_definition(BC,'save_initial_import_action_v1'),ROUTER_SUBS,'router')
    old=re.search(r"v_catalog constant jsonb:=('.*?')::jsonb;",body,re.S)
    assert old and body.count(old.group(0))==1
    return body.replace(old.group(0),'v_catalog constant jsonb:='+"'"+json.dumps(catalog(),ensure_ascii=False).replace("'","''")+"'"+'::jsonb;')


# ---------------------------------------------------------------- D09 ACC-C12 option a (BC texts of the custody import)
D09_CHECK_SUBS=[
    ("  v_zone text;v_total numeric;\nbegin","  v_zone text;v_total numeric;v_source text;\nbegin"),
    ("    raise exception 'BC_C03_DUPLICATE: custody_key sudah dipakai; satu barang fisik hanya satu baris';end if;\n",
     "    raise exception 'BC_C03_DUPLICATE: custody_key sudah dipakai; satu barang fisik hanya satu baris';end if;\n"
     "  -- D09 (owner 26 Sep 2026, ACC-C12 option a): the pending item names its source (count sheet + line, or source lot); the same\n"
     "  -- source is one item whatever custody key a later request uses. Other lines of the same sheet are other goods.\n"
     "  v_source:=erp.bd_custody_source_identity_v1(j);\n"
     "  if exists(select 1 from erp.bd_custody_sources_v1 s where s.source_identity=v_source)\n"
     "    or exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_CUSTODY' and x.id<>r.id\n"
     "      and erp.bd_custody_source_identity_v1(x.normalized_payload,false)=v_source) then\n"
     "    raise exception 'BC_C12_SAME_SOURCE: rujukan sumber % sudah dipakai; barang yang sama tetap satu item walau kunci permintaan baru',v_source;end if;\n"),
    ("  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric);",
     "  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric,'source',v_source);")]
D09_APPLY_SUBS=[
    ("    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),\n",
     "    -- D09: the source identity stays with the goods (one row per source; a concurrent import of the same source fails here).\n"
     "    if r.entity_type='OPENING_ACCESSORY_CUSTODY' then\n"
     "      begin\n"
     "        insert into erp.bd_custody_sources_v1(source_identity,custody_kind,record_id,batch_id,source_row_id,count_sheet,sheet_line,source_lot)\n"
     "        values(c->>'source',c->>'kind',v_id,p_batch,r.id,nullif(btrim(j->>'count_sheet'),''),nullif(btrim(j->>'sheet_line'),''),nullif(btrim(j->>'source_lot'),''));\n"
     "      exception when unique_violation then\n"
     "        raise exception 'BC_C12_SAME_SOURCE: rujukan sumber % sudah dipakai; barang yang sama tetap satu item walau kunci permintaan baru',c->>'source';\n"
     "      end;\n"
     "    end if;\n"
     "    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),\n")]


REPLACED=['erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','erp.post_laundry_delivery(uuid)','erp.desired_laundry_accrual(uuid)',
          'erp.rebuild_po_hpp(uuid,text)','erp.period_blockers_v1(date,date)','erp.set_laundry_rate_owner_estimate_v1(uuid,numeric,text)',
          'erp.validate_laundry_receipt_line()','erp.cp6_lot_failed_wash_cost_v2620e(uuid)','erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()','erp.post_sale(uuid)',
          'erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)',
          'erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)',
          'erp.get_initial_import_workspace_v1(uuid)','erp.initial_import_revision_v1(uuid)','erp.complete_initial_import_wip_v1(jsonb)',
          'erp.initial_import_production_rows_v1(uuid)','erp.guard_initial_import_po_completion_v1()','erp.get_wip_control_v1(text,uuid,text,text)',
          'erp.run_v255_material_cost_integrity_checks()','erp.bc_check_import_row_v1(uuid,uuid)','erp.bc_apply_imports_v1(uuid)']
NEW_TABLES=['bd_policy_settings_v1','bd_policy_setting_events_v1','bd_execution_context_v1','bd_laundry_vendor_terms_v1','bd_laundry_components_v1',
            'bd_laundry_component_rates_v1','bd_laundry_packages_v1','bd_laundry_package_components_v1','bd_laundry_package_rates_v1',
            'bd_laundry_scoped_rates_v1','bd_requests_v1','bd_laundry_priced_lines_v1','bd_laundry_charge_lines_v1','bd_laundry_charge_shares_v1',
            'bd_laundry_size_estimates_v1','bd_laundry_receipt_allocations_v1','bd_laundry_invoices_v1','bd_laundry_invoice_lines_v1',
            'bd_opening_laundry_claims_v1','bd_opening_laundry_claim_events_v1','bd_opening_laundry_uninvoiced_v1','bd_custody_sources_v1']


def objects():
    return '\n'.join(p.read_text().rstrip('\n') for p in OBJECTS)


def new_functions():
    return [m.group(1) for m in re.finditer(r'(?i)create or replace function ((?:erp|public)\.[a-z0-9_]+)\(',objects())]


def build():
    facade=substitute(last_definition(BA,'save_laundry_qc_action_v1'),FACADE_SUBS,'laundry facade')
    post_delivery=substitute(last_definition(AC,'post_laundry_delivery'),POST_DELIVERY_SUBS,'post delivery')
    accrual=substitute(last_definition(M20,'desired_laundry_accrual'),ACCRUAL_SUBS,'accrual')
    rebuild=substitute(last_definition(AY,'rebuild_po_hpp'),REBUILD_SUBS,'rebuild')
    blockers=substitute(last_definition(AW,'period_blockers_v1'),BLOCKER_SUBS,'blockers')
    estimate=substitute(last_definition(AW,'set_laundry_rate_owner_estimate_v1'),ESTIMATE_SUBS,'owner estimate')
    receipt_line=substitute(last_definition(M20,'validate_laundry_receipt_line'),RECEIPT_LINE_SUBS,'receipt line')
    sale=substitute(last_definition(AG,'post_sale',end='$function$\n$definition$;')[:-len('\n$definition$;')]+';',SALE_SUBS,'post sale')
    attempt=substitute(last_definition(AJ,'cp6_lot_failed_wash_cost_v2620e',end='$function$\n$definition$;')[:-len('\n$definition$;')]+';',ATTEMPT_SUBS,'attempt lot cost')
    stage=substitute(last_definition(BC,'stage_migration_row'),STAGE_SUBS,'stage')
    base=substitute(last_definition(BC,'_validate_migration_batch_base'),BASE_SUBS,'base')
    final=substitute(last_definition(BC,'finalize_migration_batch'),FINAL_SUBS,'finalize')
    ws=substitute(last_definition(BC,'get_initial_import_workspace_v1'),WS_SUBS,'import workspace')
    rev=substitute(last_definition(BC,'initial_import_revision_v1'),REV_SUBS,'revision')
    complete=substitute(last_definition(BB,'complete_initial_import_wip_v1'),COMPLETE_SUBS,'complete wip')
    rows=substitute(last_definition(BB,'initial_import_production_rows_v1'),ROWS_SUBS,'production rows')
    po_guard=substitute(last_definition(BB,'guard_initial_import_po_completion_v1'),PO_GUARD_SUBS,'po guard')
    wip_control=substitute(last_definition(AP_MIG,'get_wip_control_v1'),WIP_CONTROL_SUBS,'wip control')
    d09_check=substitute(last_definition(BC,'bc_check_import_row_v1'),D09_CHECK_SUBS,'d09 check')
    d09_apply=substitute(last_definition(BC,'bc_apply_imports_v1'),D09_APPLY_SUBS,'d09 apply')
    parts=['-- CP6 BD priced laundry deliveries (LAU-05b) and laundry policy settings LAU-DEC01..06 (owner decision 25 Sep 2026): T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_bd_build.py from scripts/cp6_bd_objects_*.sql, the 20/AC/AG/AJ migrations and the AW/AY/BA/BB/BC T1 files; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if not exists(select 1 from erp.schema_migrations where version='v2.6.20bc') then raise exception 'BD_T1_REQUIRES_BC'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regclass('erp.bd_laundry_priced_lines_v1') is not null then raise exception 'BD_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',objects(),facade,post_delivery,accrual,rebuild,blockers,estimate,receipt_line,attempt,invoice_guard(),sale,
           stage,base,final,router(),ws,rev,complete,rows,po_guard,wip_control,D07.read_text().rstrip('\n'),d09_check,d09_apply,
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of BD (priced laundry deliveries: package, components with partial coverage, lump sum per batch, minimum charge, scoped rates; exact per-size receipt shares; laundry vendor invoices; policy settings LAU-DEC01..06; ALL-W05 laundry claims and uninvoiced returns at cutover); not a release package');",
           'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_bd_t1_family.sql is stale; rerun scripts/cp6_bd_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
